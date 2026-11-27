"""
Build CudaVideoStudio.exe with PyInstaller.

Design notes:
- Manim is NOT bundled: rendering happens in the project's .venv via
  ``python -m manim`` (a frozen exe cannot serve as the Manim interpreter).
  The exe therefore needs to live next to ``.venv/`` and ``assets/``.
- Everything the GUI itself needs (customtkinter, av, pypdf, edge-tts, requests)
  is bundled.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
APP_NAME = "CudaVideoStudio"

HIDDEN_IMPORTS = [
    "check_env",
    "customtkinter",
    "darkdetect",
    "PIL",
    "PIL.Image",
    "PIL.ImageFont",
    "PIL.ImageDraw",
    "av",
    "pypdf",
    "edge_tts",
    "requests",
    "imageio_ffmpeg",
    "pipeline.storyboard",
    "pipeline.deepseek_client",
    "pipeline.manim_renderer",
    "pipeline.l4b_slide_renderer",
    "pipeline.l5_video_composer",
    "pipeline.full_book_orchestrator",
    "pipeline.deepseek_director",
    "pipeline.l4_manim_generator",
    "pipeline.pedagogy_curriculum",
    "pipeline.episode_router",
]

EXCLUDES = [
    # Rendering is delegated to the external .venv interpreter.
    "manim",
    "manimlib",
    "manimpango",
    "moderngl",
    "moderngl_window",
    "cairo",
    "pycairo",
    # Heavy scientific stack that the GUI never touches.
    "numpy",
    "scipy",
    "matplotlib",
    "sympy",
    "pandas",
    "sklearn",
    "torch",
    "tensorflow",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "tkinter.test",
    "test",
]


def build() -> bool:
    if not PYTHON.exists():
        print(f"[!] Python not found: {PYTHON}")
        return False

    print("=" * 70)
    print("🔨 Building CudaVideoStudio.exe")
    print("=" * 70)

    for directory in (BUILD_DIR, DIST_DIR):
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)

    cmd = [
        str(PYTHON), "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        "--paths", str(BASE_DIR),
        "--add-data", f"{BASE_DIR / 'assets'};assets",
        "--collect-data", "customtkinter",
    ]
    for module in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", module]
    for module in EXCLUDES:
        cmd += ["--exclude-module", module]
    cmd.append(str(BASE_DIR / "app_gui.py"))

    print(f"[*] Python: {PYTHON}")
    print("[*] Bundling GUI only; Manim renders via .venv at runtime.\n")
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(BASE_DIR))
    elapsed = time.time() - started

    dist_exe = DIST_DIR / f"{APP_NAME}.exe"
    if proc.returncode != 0 or not dist_exe.exists():
        print(f"\n[!] Build failed (exit={proc.returncode}, elapsed={elapsed:.0f}s)")
        return False

    root_exe = BASE_DIR / f"{APP_NAME}.exe"
    try:
        shutil.copy2(dist_exe, root_exe)
    except PermissionError:
        print(f"\n[!] 无法覆盖根目录 exe：{root_exe} 正在运行。请先关闭 GUI，再复制 dist 中的文件。")
        return False
    size_mb = round(root_exe.stat().st_size / 1024 / 1024, 1)
    print("=" * 70)
    print(f"🎉 Build success in {elapsed:.0f}s")
    print(f"   dist: {dist_exe} ({size_mb} MB)")
    print(f"   root: {root_exe}")
    print("=" * 70)
    return True


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
