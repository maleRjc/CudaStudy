"""
Layer 5: Multi-Track Video-Audio Muxing and Final Delivery Engine.
Uses FFmpeg complex filters to place audio clips at exact millisecond timeline anchors,
generates synced subtitles (SRT), and renders the final publication-ready MP4.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT timestamp (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def find_ffmpeg_binary() -> Path:
    """Finds a valid FFmpeg binary."""
    candidates = [
        config.BASE_DIR / ".venv" / "Scripts" / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / ".venv" / "Scripts" / "ffmpeg.exe",
        Path(sys.executable).resolve().parent.parent / ".venv" / "Scripts" / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return Path("ffmpeg")


class VideoComposer:
    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = find_ffmpeg_binary()
        print(f"[*] VideoComposer: Using FFmpeg -> {self.ffmpeg_bin}")

    def generate_srt_subtitles(self, timeline: Dict[str, Any], srt_path: Path):
        """Generates clean SRT subtitle track from timeline beats."""
        beats = timeline.get("beats", [])
        lines = []

        for idx, b in enumerate(beats, 1):
            start = b.get("start_time", 0.0)
            # Subtitle displays during narration speech
            duration = b.get("audio_duration", 2.0)
            end = start + duration
            text = b.get("narration", "")

            if text:
                lines.append(f"{idx}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{text}\n")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[+] Layer 5: Generated Subtitles in {srt_path.name}")

    def compose_final_video(self, raw_video_path: Path, timeline: Dict[str, Any], output_mp4: Optional[Path] = None) -> Optional[Path]:
        """Muxes video track and accurately delayed audio streams using FFmpeg."""
        chunk_id = timeline["chunk_id"]
        beats = timeline.get("beats", [])
        final_mp4 = output_mp4 if output_mp4 is not None else (self.output_dir / f"{chunk_id}_final.mp4")
        srt_file = self.output_dir / f"{chunk_id}_subtitles.srt"

        print(f"[*] Layer 5: Composing final video for {chunk_id}...")

        # 1. Create subtitles
        self.generate_srt_subtitles(timeline, srt_file)

        # 2. Build FFmpeg command inputs
        audio_beats = [b for b in beats if b.get("narration") and Path(b.get("audio_file", "")).exists()]
        if not audio_beats:
            print("[Warning] No valid audio clips found, exporting silent video.")
            return raw_video_path

        cmd = [str(self.ffmpeg_bin), "-y", "-i", str(raw_video_path)]

        # Add each audio input
        for b in audio_beats:
            cmd.extend(["-i", str(b["audio_file"])])

        # Construct complex filter with adelay and amix
        filter_parts = []
        amix_inputs = []
        for i, b in enumerate(audio_beats, 1):
            delay_ms = int(b.get("start_time", 0.0) * 1000)
            filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
            amix_inputs.append(f"[a{i}]")

        filter_str = ";".join(filter_parts) + f";{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:dropout_transition=0:normalize=0[aout]"

        cmd.extend([
            "-filter_complex", filter_str,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(final_mp4)
        ])

        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        if proc.returncode == 0 and final_mp4.exists():
            print(f"[+] Layer 5 Success! Final production video created: {final_mp4.name} ({round(final_mp4.stat().st_size / 1024 / 1024, 2)} MB)")
            return final_mp4
        else:
            print(f"[!] FFmpeg composition failed:\n{proc.stderr[-600:]}")
            return None

    def concatenate_course_videos(self, video_paths: List[Path], output_filename: str = "00_cuda_full_course.mp4") -> Optional[Path]:
        """Concatenates multiple episodic concept videos into a comprehensive, continuous master lecture."""
        valid_videos = [p for p in video_paths if p and Path(p).exists()]
        if not valid_videos:
            print("[!] No valid video files to concatenate.")
            return None

        if len(valid_videos) == 1:
            return valid_videos[0]

        concat_list_file = self.output_dir / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for vp in valid_videos:
                # Escape backslashes for FFmpeg
                clean_path = str(vp.resolve()).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        master_video_path = self.output_dir / output_filename
        cmd = [
            str(self.ffmpeg_bin),
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(master_video_path)
        ]

        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )

        if proc.returncode == 0 and master_video_path.exists():
            print(f"[🎉] Master Course Video stitched successfully: {master_video_path.name} ({round(master_video_path.stat().st_size / 1024 / 1024, 2)} MB)")
            return master_video_path
        else:
            print(f"[!] Concatenation failed: {proc.stderr[-500:]}")
            return None


if __name__ == "__main__":
    from pipeline.l3_audio_timing import AudioTimingEngine
    from pipeline.l2_deepseek_beats import DeepSeekBeatGenerator
    from pipeline.l1_chunker import CORE_COGNITIVE_UNITS

    gen = DeepSeekBeatGenerator()
    manifest = gen.generate_for_chunk(CORE_COGNITIVE_UNITS[0])
    engine = AudioTimingEngine()
    timeline = engine.run(manifest)

    composer = VideoComposer()
    raw_mp4 = config.OUTPUT_DIR / "videos" / "01_global_thread_indexing_scene_raw.mp4"
    if raw_mp4.exists():
        composer.compose_final_video(raw_mp4, timeline)
