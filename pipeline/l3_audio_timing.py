"""
Layer 3: audio-clock driven timeline.

Synthesizes one narration clip per slide (Edge-TTS), measures the real audio
duration, and builds the absolute timeline used by every downstream layer.

Two durations are recorded per slide:
- ``audio_duration``  : measured narration length
- ``total_beat_duration`` : audio + deliberate pause (the on-screen slot)

Audio files are keyed by a hash of the narration text, so editing a script
never reuses stale audio.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import av
import edge_tts

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.slide_timing import build_schedule, schedule_from_steps
from pipeline.tts_text import normalize_for_speech


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


class AudioTimingEngine:
    def __init__(self, voice: str = "", rate: str = "", volume: str = ""):
        self.voice = voice or config.TTS_VOICE
        self.rate = rate or config.TTS_RATE
        self.volume = volume or config.TTS_VOLUME
        self.audio_dir = config.OUTPUT_DIR / "audio"
        self.timeline_dir = config.OUTPUT_DIR / "beats"
        for directory in (self.audio_dir, self.timeline_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------
    async def _synthesize_clip(self, text: str, output_path: Path) -> bool:
        if output_path.exists() and output_path.stat().st_size > 1000:
            return True

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=self.rate,
                    volume=self.volume,
                )
                await communicate.save(str(output_path))
                if output_path.exists() and output_path.stat().st_size > 500:
                    return True
            except Exception as exc:  # network flake, service busy, ...
                print(f"[Warning] Edge-TTS attempt {attempt}/{max_retries} failed ({exc}). Retrying...")
                await asyncio.sleep(1.5 * attempt)

        print(f"[!] Edge-TTS unavailable for '{output_path.name}'. Writing silent placeholder.")
        try:
            import subprocess

            est_seconds = max(round(len(text) / 4.5, 1), 3.0)
            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.run(
                [
                    str(config.ffmpeg_binary()),
                    "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", str(est_seconds), "-c:a", "libmp3lame", str(output_path),
                ],
                capture_output=True,
                check=True,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            return output_path.exists()
        except Exception as exc:
            print(f"[!] Silent placeholder failed: {exc}")
            return False

    def get_audio_duration(self, audio_path: Path) -> float:
        try:
            with av.open(str(audio_path)) as container:
                stream = container.streams.audio[0]
                duration = float(stream.duration * stream.time_base)
                if duration > 0.05:
                    return round(duration, 3)
        except Exception as exc:
            print(f"[Warning] PyAV probe failed for {audio_path.name}: {exc}")
        return 2.5

    # ------------------------------------------------------------------
    def _concat_audio(self, paths: List[Path], output_path: Path) -> bool:
        """Concatenate per-step narration clips into one slide audio track."""
        if not paths:
            return False
        if output_path.exists() and output_path.stat().st_size > 1000:
            return True
        cmd = [str(config.ffmpeg_binary()), "-y"]
        for path in paths:
            cmd += ["-i", str(path)]
        inputs = "".join(f"[{index}:a]" for index in range(len(paths)))
        cmd += [
            "-filter_complex",
            f"{inputs}concat=n={len(paths)}:v=0:a=1[aout]",
            "-map", "[aout]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            if proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000:
                return True
            print(f"[!] Step audio concat failed: {(proc.stderr or '')[-300:]}")
        except Exception as exc:
            print(f"[!] Step audio concat error: {exc}")
        return False

    async def process_manifest(self, beat_manifest: Dict[str, Any]) -> Dict[str, Any]:
        chunk_id = (
            beat_manifest.get("sec_id")
            or beat_manifest.get("concept_id")
            or beat_manifest.get("chunk_id")
            or "unnamed"
        )
        slides = beat_manifest.get("slides")
        if slides is None:
            slides = beat_manifest.get("beats") or []
        topic = beat_manifest.get("topic") or beat_manifest.get("title", "")

        print(f"[*] Layer 3: TTS + audio clock for {chunk_id} ({len(slides)} slides)...")

        timeline_slides: List[Dict[str, Any]] = []
        cursor = 0.0

        for idx, slide in enumerate(slides, start=1):
            slide_id = int(slide.get("slide_id") or slide.get("beat_id") or idx)
            narration = str(slide.get("narration_script") or slide.get("narration") or "").strip()
            pause = float(slide.get("pause_buffer", config.DEFAULT_PAUSE_BUFFER))

            plan = (slide.get("visual_spec") or {}).get("scene_plan") or {}
            plan = dict(plan) if isinstance(plan, dict) else {}
            steps = plan.get("steps") or []
            step_texts = [str(step.get("narration") or "").strip() for step in steps]
            per_step_audio = len(step_texts) >= 2 and all(len(text) >= 20 for text in step_texts)

            audio_file = Path("")
            audio_duration = 0.0
            schedule = None

            if per_step_audio:
                speech_texts = [normalize_for_speech(text) for text in step_texts]
                step_files: List[Path] = []
                step_durations: List[float] = []
                for step_index, step_text in enumerate(speech_texts):
                    step_path = self.audio_dir / (
                        f"{chunk_id}_s{slide_id:02d}_step{step_index:02d}_{_text_hash(step_text)}.mp3"
                    )
                    ok = await self._synthesize_clip(step_text, step_path)
                    step_durations.append(
                        self.get_audio_duration(step_path) if ok else max(2.0, len(step_text) / 4.5)
                    )
                    step_files.append(step_path)
                combined = self.audio_dir / (
                    f"{chunk_id}_s{slide_id:02d}_steps_{_text_hash('|'.join(speech_texts))}.mp3"
                )
                if self._concat_audio(step_files, combined):
                    audio_file = combined
                    audio_duration = round(sum(step_durations), 3)
                    narration = " ".join(speech_texts)
                    schedule = schedule_from_steps(speech_texts, step_durations)
                else:
                    per_step_audio = False

            if not per_step_audio:
                speech_narration = normalize_for_speech(narration)
                digest = _text_hash(speech_narration) if speech_narration else "silent"
                audio_file = self.audio_dir / f"{chunk_id}_s{slide_id:02d}_{digest}.mp3"
                if speech_narration:
                    ok = await self._synthesize_clip(speech_narration, audio_file)
                    audio_duration = (
                        self.get_audio_duration(audio_file)
                        if ok
                        else max(2.0, len(speech_narration) / 4.5)
                    )
                else:
                    audio_duration = 0.0
                    audio_file = Path("")
                schedule = build_schedule(speech_narration, steps, audio_duration, pause)

            # The visual slot must cover the narration plus the deliberate pause.
            total = round(audio_duration + pause, 3)
            # Leave a little headroom so the animation does not get trimmed.
            plan["duration"] = round(max(3.0, total - 0.6), 3)
            plan["windows"] = schedule["windows"] if schedule else []
            absolute_cues = [
                {
                    "start": round(cursor + cue["start"], 3),
                    "end": round(cursor + cue["end"], 3),
                    "text": cue["text"],
                }
                for cue in (schedule["cues"] if schedule else [])
            ]

            item = {
                "slide_id": slide_id,
                "beat_id": slide_id,
                "index": idx,
                "title": slide.get("title", ""),
                "slide_type": slide.get("slide_type", "concept_breakdown"),
                "key_points": slide.get("key_points", []),
                "layout": (slide.get("visual_spec") or {}).get("layout", ""),
                "visual_spec": slide.get("visual_spec", {}),
                "scene_plan": plan,
                "narration": narration,
                "audio_file": str(audio_file) if audio_file else "",
                "audio_duration": audio_duration,
                "pause_buffer": pause,
                "total_beat_duration": total,
                "start_time": round(cursor, 3),
                "end_time": round(cursor + total, 3),
                "cues": absolute_cues,
            }
            timeline_slides.append(item)
            cursor += total
            print(
                f"    - Slide {slide_id}: audio {audio_duration:.1f}s + pause {pause:.1f}s "
                f"= {total:.1f}s (start {item['start_time']:.1f}s)"
            )

        timeline = {
            "sec_id": chunk_id,
            "chunk_id": chunk_id,
            "concept_id": chunk_id,
            "title": topic,
            "total_video_duration": round(cursor, 3),
            "slides": timeline_slides,
            "beats": timeline_slides,
        }

        timeline_path = self.timeline_dir / f"{chunk_id}_timeline.json"
        try:
            payload = {k: v for k, v in timeline.items() if k != "beats"}
            timeline_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"[!] Could not write timeline: {exc}")

        print(f"[+] Layer 3 done: {timeline['total_video_duration']}s -> {timeline_path.name}")
        return timeline

    def run(self, beat_manifest: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.run(self.process_manifest(beat_manifest))
