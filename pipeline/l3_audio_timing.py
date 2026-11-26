"""
Layer 3: Audio-Clock Driven TTS Synthesis and Timeline Engine.
Synthesizes voiceover per visual beat via Edge-TTS, extracts exact millisecond durations,
and constructs the absolute audio-visual timeline manifest.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import edge_tts
import av

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


class AudioTimingEngine:
    def __init__(self, voice: str = "", rate: str = "", volume: str = ""):
        self.voice = voice or config.TTS_VOICE
        self.rate = rate or config.TTS_RATE
        self.volume = volume or config.TTS_VOLUME
        self.audio_dir = config.OUTPUT_DIR / "audio"
        self.timeline_dir = config.OUTPUT_DIR / "beats"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.timeline_dir.mkdir(parents=True, exist_ok=True)

    async def _synthesize_clip(self, text: str, output_path: Path):
        """Asynchronously synthesizes an audio clip using edge-tts."""
        communicate = edge_tts.Communicate(text=text, voice=self.voice, rate=self.rate, volume=self.volume)
        await communicate.save(str(output_path))

    def get_audio_duration(self, audio_path: Path) -> float:
        """Reads exact audio duration in seconds using PyAV."""
        try:
            with av.open(str(audio_path)) as container:
                stream = container.streams.audio[0]
                # Duration in seconds
                duration = float(stream.duration * stream.time_base)
                return round(duration, 3)
        except Exception as e:
            print(f"[Warning] PyAV failed to probe {audio_path}: {e}")
            # Fallback estimation: 4 chars per second
            return 2.5

    async def process_manifest(self, beat_manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes all narrations in manifest/deck and builds timeline schedule."""
        chunk_id = beat_manifest.get("sec_id") or beat_manifest.get("concept_id") or beat_manifest.get("chunk_id", "unnamed_concept")
        slides = beat_manifest.get("slides")
        beats = slides if slides is not None else beat_manifest.get("beats", [])
        print(f"[*] Layer 3: Synthesizing TTS & building Audio-Clock timeline for {chunk_id} ({len(beats)} units)...")

        timeline_beats = []
        current_time_cursor = 0.0

        for idx, b in enumerate(beats, 1):
            b_id = b.get("slide_id") or b.get("beat_id", idx)
            # Support both narration_script (from Deck) and narration (from Beat)
            narration = b.get("narration_script") or b.get("narration", "")
            pause_buf = float(b.get("pause_buffer", config.DEFAULT_PAUSE_BUFFER))

            audio_file = self.audio_dir / f"{chunk_id}_slide_{b_id}.mp3"

            # Synthesize narration if non-empty
            if narration:
                await self._synthesize_clip(narration, audio_file)
                audio_duration = self.get_audio_duration(audio_file)
            else:
                audio_duration = 0.0

            action_duration = max(audio_duration, config.MIN_ACTION_DURATION)
            total_beat_duration = round(action_duration + pause_buf, 3)

            timeline_item = {
                "beat_id": b_id,
                "slide_id": b_id,
                "title": b.get("title", ""),
                "slide_type": b.get("slide_type", "concept"),
                "key_points": b.get("key_points", []),
                "layout_zone": b.get("layout_zone", "center"),
                "visual_spec": b.get("visual_spec", {}),
                "visual_action": b.get("visual_action", ""),
                "narration": narration,
                "audio_file": str(audio_file),
                "audio_duration": audio_duration,
                "action_duration": action_duration,
                "pause_buffer": pause_buf,
                "total_beat_duration": total_beat_duration,
                "start_time": round(current_time_cursor, 3),
                "end_time": round(current_time_cursor + total_beat_duration, 3)
            }

            timeline_beats.append(timeline_item)
            current_time_cursor += total_beat_duration
            print(f"    - Slide {b_id}: Voice {audio_duration}s + Pause {pause_buf}s = Total {total_beat_duration}s (Starts @ {timeline_item['start_time']}s)")

        full_timeline = {
            "sec_id": chunk_id,
            "chunk_id": chunk_id,
            "concept_id": chunk_id,
            "title": beat_manifest.get("topic") or beat_manifest.get("title", ""),
            "total_video_duration": round(current_time_cursor, 3),
            "slides": timeline_beats,
            "beats": timeline_beats
        }


        timeline_path = self.timeline_dir / f"{chunk_id}_timeline.json"
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump(full_timeline, f, ensure_ascii=False, indent=2)

        print(f"[+] Layer 3 Success: Full video timeline ({full_timeline['total_video_duration']}s) saved to {timeline_path.name}")
        return full_timeline

    def run(self, beat_manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for execution."""
        return asyncio.run(self.process_manifest(beat_manifest))


if __name__ == "__main__":
    from pipeline.l2_deepseek_beats import DeepSeekBeatGenerator
    from pipeline.l1_chunker import CORE_COGNITIVE_UNITS

    gen = DeepSeekBeatGenerator()
    manifest = gen.generate_for_chunk(CORE_COGNITIVE_UNITS[0])

    engine = AudioTimingEngine()
    timeline = engine.run(manifest)
    print("Timeline generated successfully!")
