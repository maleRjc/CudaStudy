"""
Layer 5: normalize, concatenate and burn subtitles.

Every clip is first normalized to the exact delivery format:
    1280x720, 30 fps, H.264 yuv420p, AAC 44.1 kHz stereo
with the bottom 88 px kept pure black. Subtitles are then burned *into that
band*, so they never cover slide content or Manim animation.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from pipeline.manim_renderer import probe_duration
from pipeline.subtitle_engine import SubtitleEngine


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


class VideoComposer:
    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "videos"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.ffmpeg_bin = config.ffmpeg_binary()
        print(f"[*] VideoComposer: ffmpeg -> {self.ffmpeg_bin}")

    # ------------------------------------------------------------------
    def _run(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            startupinfo=startupinfo,
            cwd=str(cwd) if cwd else None,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _has_audio(path: Path) -> bool:
        try:
            import av

            with av.open(str(path)) as container:
                return bool(container.streams.audio)
        except Exception:
            return False

    def normalize_clip(
        self,
        source: Path,
        target: Path,
        duration: float,
        audio: Optional[Path] = None,
    ) -> Optional[Path]:
        """Convert any clip to the delivery format and pad the subtitle band."""
        duration = max(1.0, float(duration))
        target.parent.mkdir(parents=True, exist_ok=True)

        vf = (
            f"scale={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"tpad=stop_mode=clone:stop_duration=3600,fps={config.VIDEO_FPS},"
            f"pad={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:0:0:black"
        )

        cmd = [str(self.ffmpeg_bin), "-y", "-i", str(source)]
        if audio is not None and Path(audio).exists():
            cmd += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-af", "apad",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k"]
        elif self._has_audio(source):
            cmd += ["-map", "0:v:0", "-map", "0:a:0", "-af", "apad",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k"]
        else:
            cmd += [
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-map", "0:v:0", "-map", "1:a:0", "-af", "apad",
                "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
            ]

        cmd += [
            "-vf", vf,
            "-t", f"{duration:.3f}",
            "-r", str(config.VIDEO_FPS),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(target),
        ]

        proc = self._run(cmd)
        if proc.returncode == 0 and target.exists() and target.stat().st_size > 3000:
            return target
        print(f"[!] normalize_clip failed for {source.name}: {(proc.stderr or '')[-400:]}")
        return None

    # ------------------------------------------------------------------
    def generate_srt_subtitles(self, timeline: Dict[str, Any], srt_path: Path) -> Path:
        return SubtitleEngine.generate_full_srt(timeline, srt_path)

    # ------------------------------------------------------------------
    def burn_subtitles(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Path,
        font_size: int = 20,
        margin_v: int = 12,
    ) -> Optional[Path]:
        if not srt_path.exists() or srt_path.stat().st_size < 5:
            print("[!] No subtitle file to burn")
            return None

        # libass on Windows dislikes absolute paths with drive letters inside a
        # filter string; run from the SRT directory with a relative name.
        work_dir = srt_path.parent
        style = (
            "FontName=Microsoft YaHei,FontSize=%d,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BackColour=&H80000000,"
            "BorderStyle=1,Outline=1.4,Shadow=0,Alignment=2,MarginV=%d,MarginL=30,MarginR=30,"
            "WrapStyle=2"
        ) % (font_size, margin_v)

        cmd = [
            str(self.ffmpeg_bin), "-y",
            "-i", str(video_path.resolve()),
            "-vf", f"subtitles={srt_path.name}:force_style='{style}'",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path.resolve()),
        ]
        proc = self._run(cmd, cwd=work_dir)
        if proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 3000:
            return output_path
        print(f"[!] Subtitle burn failed: {(proc.stderr or '')[-500:]}")
        return None

    # ------------------------------------------------------------------
    def concatenate_course_videos(
        self,
        video_paths: List[Path],
        output_filename: str = "master.mp4",
        srt_path: Optional[Path] = None,
        burn_subtitles: bool = True,
    ) -> Optional[Path]:
        valid = [Path(p) for p in video_paths if p and Path(p).exists() and Path(p).stat().st_size > 3000]
        if not valid:
            print("[!] No valid clips to concatenate")
            return None

        master = self.output_dir / output_filename
        raw_master = self.output_dir / f".raw_{output_filename}"

        concat_list = self.output_dir / f".concat_{output_filename}.txt"
        concat_list.write_text(
            "\n".join(f"file '{str(p.resolve()).replace(chr(92), '/')}'" for p in valid) + "\n",
            encoding="utf-8",
        )

        cmd = [
            str(self.ffmpeg_bin), "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(raw_master),
        ]
        proc = self._run(cmd)

        expected = sum(probe_duration(p) for p in valid)
        actual = probe_duration(raw_master) if raw_master.exists() else 0.0
        if proc.returncode != 0 or actual <= 0 or abs(actual - expected) > max(3.0, expected * 0.02):
            print(
                f"[!] Stream-copy concat failed or duration mismatch "
                f"(expected {expected:.1f}s, got {actual:.1f}s); re-encoding."
            )
            if raw_master.exists():
                raw_master.unlink()
            cmd = [str(self.ffmpeg_bin), "-y"]
            for path in valid:
                cmd += ["-i", str(path)]
            streams = "".join(f"[{i}:v][{i}:a]" for i in range(len(valid)))
            filter_complex = f"{streams}concat=n={len(valid)}:v=1:a=1[v][a]"
            cmd += [
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-r", str(config.VIDEO_FPS),
                "-c:a", "aac", "-ar", "44100", "-ac", "2",
                str(raw_master),
            ]
            proc = self._run(cmd)
            if proc.returncode != 0 or not raw_master.exists():
                print(f"[!] Concat re-encode failed: {(proc.stderr or '')[-500:]}")
                return None

        final = master
        if burn_subtitles and srt_path and Path(srt_path).exists():
            print(f"[*] Burning subtitles into the dedicated 88px band: {Path(srt_path).name}")
            burned = self.burn_subtitles(raw_master, Path(srt_path), master)
            if burned is None and raw_master.exists():
                shutil.copy2(raw_master, master)
        else:
            shutil.copy2(raw_master, master)

        for temp in (raw_master, concat_list):
            try:
                Path(temp).unlink()
            except OSError:
                pass

        if master.exists():
            size_mb = round(master.stat().st_size / 1024 / 1024, 2)
            print(f"[+] Master video: {master.name} ({size_mb} MB, {probe_duration(master):.1f}s)")
            return master
        return None

    # ------------------------------------------------------------------
    # Compatibility helpers for the legacy orchestrators
    # ------------------------------------------------------------------
    def compose_clip_with_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_clip_path: Path,
        target_duration: float,
    ) -> Optional[Path]:
        return self.normalize_clip(video_path, output_clip_path, target_duration, audio=audio_path)

    def compose_final_video(
        self,
        raw_video_path: Path,
        timeline: Dict[str, Any],
        output_mp4: Optional[Path] = None,
    ) -> Optional[Path]:
        """Legacy single-track composition: normalize then mux delayed narration."""
        chunk_id = timeline.get("chunk_id") or timeline.get("sec_id") or "clip"
        final_mp4 = output_mp4 or (self.output_dir / f"{chunk_id}_final.mp4")
        srt_file = self.output_dir / f"{chunk_id}_subtitles.srt"
        self.generate_srt_subtitles(timeline, srt_file)

        beats = timeline.get("slides") or timeline.get("beats") or []
        audio_beats = [b for b in beats if b.get("narration") and Path(b.get("audio_file", "")).exists()]
        if not audio_beats:
            return self.normalize_clip(raw_video_path, final_mp4, timeline.get("total_video_duration", 10))

        cmd = [str(self.ffmpeg_bin), "-y", "-i", str(raw_video_path)]
        for beat in audio_beats:
            cmd += ["-i", str(beat["audio_file"])]
        filters, mix_inputs = [], []
        for idx, beat in enumerate(audio_beats, start=1):
            delay = int(float(beat.get("start_time", 0)) * 1000)
            filters.append(f"[{idx}:a]adelay={delay}:all=1[a{idx}]")
            mix_inputs.append(f"[a{idx}]")
        filter_str = ";".join(filters) + f";{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0[aout]"
        cmd += [
            "-filter_complex", filter_str,
            "-map", "0:v:0", "-map", "[aout]",
            "-vf", (
                f"scale={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                f"pad={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:0:0:black,fps={config.VIDEO_FPS}"
            ),
            "-t", f"{float(timeline.get('total_video_duration') or 0):.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            str(final_mp4),
        ]
        proc = self._run(cmd)
        if proc.returncode == 0 and final_mp4.exists():
            return final_mp4
        print(f"[!] compose_final_video failed: {(proc.stderr or '')[-400:]}")
        return None

