"""
Manim rendering for storyboard scenes.

The scene file is tiny and deterministic: it imports ``StoryboardScene`` and
embeds a JSON-able plan. No LLM-authored Python is ever executed.

Rendering uses the project's own interpreter (the one that can ``import manim``)
and always runs with a timeout and a sanitized environment.
"""

from __future__ import annotations

import json
import os
import pprint
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import av

import config


def probe_duration(path: Path) -> float:
    try:
        with av.open(str(path)) as container:
            if container.duration:
                return round(float(container.duration) / 1_000_000, 3)
            stream = container.streams.video[0] if container.streams.video else None
            if stream and stream.duration and stream.time_base:
                return round(float(stream.duration * stream.time_base), 3)
    except Exception:
        pass
    return 0.0


def probe_video(path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"width": 0, "height": 0, "fps": 0.0, "duration": 0.0}
    try:
        with av.open(str(path)) as container:
            if container.duration:
                info["duration"] = round(float(container.duration) / 1_000_000, 3)
            if container.streams.video:
                stream = container.streams.video[0]
                info["width"] = int(stream.codec_context.width)
                info["height"] = int(stream.codec_context.height)
                info["fps"] = float(stream.average_rate or 0)
    except Exception:
        pass
    return info


def find_manim_python() -> Optional[Tuple[Path, str]]:
    """Return (interpreter, version) that can import manim. Never the frozen exe."""
    if not getattr(sys, "frozen", False):
        try:
            import manim

            return Path(sys.executable), str(getattr(manim, "__version__", "?"))
        except Exception:
            pass

    candidates = [
        config.BASE_DIR / ".venv" / "Scripts" / "python.exe",
        config.BASE_DIR / ".venv" / "bin" / "python",
        Path(sys.executable).resolve().parent / "python.exe",
    ]
    for candidate in candidates:
        if not candidate.exists() or candidate.resolve() == Path(sys.executable).resolve():
            continue
        try:
            result = subprocess.run(
                [str(candidate), "-c", "import manim; print(manim.__version__)"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            if result.returncode == 0:
                return candidate, result.stdout.strip()
        except Exception:
            continue
    return None


class StoryboardRenderer:
    """Writes and renders one Manim scene per slide plan."""

    def __init__(self, timeout: int = 900):
        self.scenes_dir = config.OUTPUT_DIR / "manim_scenes"
        self.videos_dir = config.OUTPUT_DIR / "videos"
        self.media_root = config.OUTPUT_DIR / "manim_media"
        for directory in (self.scenes_dir, self.videos_dir, self.media_root):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        self.timeout = timeout
        found = find_manim_python()
        if found is None:
            raise RuntimeError(
                "找不到可用的 Python + Manim 解释器。请在项目 .venv 中安装 manim，"
                "或让 Manim 与主程序使用同一个解释器。"
            )
        self.python_bin, self.manim_version = found
        print(f"[*] Manim: {self.manim_version} via {self.python_bin}")

    # ------------------------------------------------------------------
    def render(self, plan: Dict[str, Any], work_key: str) -> Optional[Path]:
        class_name = "Storyboard" + str(abs(hash(json.dumps(plan, ensure_ascii=False, sort_keys=True))) % 10**8)
        scene_file = self.scenes_dir / f"scene_{work_key}.py"

        source = (
            "# -*- coding: utf-8 -*-\n"
            "# Auto-generated storyboard scene (data only, no LLM code).\n"
            "import sys\n"
            f"sys.path.insert(0, r'{config.BASE_DIR}')\n"
            "from assets.storyboard_scene import StoryboardScene\n\n"
            f"PLAN = {pprint.pformat(plan, width=120, sort_dicts=False)}\n\n\n"
            f"class {class_name}(StoryboardScene):\n"
            "    PLAN = PLAN\n"
        )
        scene_file.write_text(source, encoding="utf-8")

        media_dir = self.media_root / "runs" / work_key
        if media_dir.exists():
            shutil.rmtree(media_dir, ignore_errors=True)
        media_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.python_bin),
            "-m", "manim",
            "--disable_caching",
            "-r", config.MANIM_RESOLUTION,
            "--frame_rate", config.MANIM_FRAME_RATE,
            "--media_dir", str(media_dir),
            str(scene_file),
            class_name,
        ]

        env = self._sanitized_env()
        started = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                env=env,
                cwd=str(config.BASE_DIR),
            )
        except subprocess.TimeoutExpired:
            print(f"[!] Manim timed out after {self.timeout}s for {work_key}")
            return None
        except Exception as exc:
            print(f"[!] Manim failed to start: {exc}")
            return None

        elapsed = time.time() - started
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-700:]
            print(f"[!] Manim exit={proc.returncode} ({elapsed:.0f}s) for {work_key}:\n{tail}")
            return None

        videos = [
            path
            for path in media_dir.rglob("*.mp4")
            if "partial_movie_files" not in str(path)
        ]
        if not videos:
            print(f"[!] Manim produced no mp4 for {work_key}")
            return None
        videos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        out_path = self.videos_dir / f"{work_key}_raw.mp4"
        if out_path.exists():
            out_path.unlink()
        shutil.copy2(videos[0], out_path)

        info = probe_video(out_path)
        print(
            f"[+] Manim {work_key}: {info['width']}x{info['height']} "
            f"{info['duration']}s in {elapsed:.0f}s"
        )
        return out_path

    # ------------------------------------------------------------------
    def _sanitized_env(self) -> Dict[str, str]:
        keep = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE",
                "LOCALAPPDATA", "APPDATA", "COMSPEC", "PATHEXT", "LANG", "LC_ALL"}
        env = {key: value for key, value in os.environ.items() if key in keep or key.startswith(("PYTHON", "MANIM", "CAIRO", "PANGOCAIRO"))}
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        venv_scripts = str(config.BASE_DIR / ".venv" / "Scripts")
        env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")
        # Never leak API credentials into the render subprocess.
        for key in list(env):
            if "DEEPSEEK" in key.upper() or "API_KEY" in key.upper():
                env.pop(key, None)
        return env
