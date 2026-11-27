"""
Single-line subtitle generation.

Every cue is packed to fit one line inside the 1280px frame (see
pipeline/cue_text.py). Cues that come from the shared step schedule are used
directly; otherwise the narration is split and distributed proportionally.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from pipeline.cue_text import MAX_CUE_EM, estimate_em, segment_cue, single_line


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


class SubtitleEngine:
    """Generates single-line, sentence-level synchronized subtitles."""

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        if not text:
            return []
        raw_chunks = re.split(r"([。！？；\n]+)", text)
        sentences: List[str] = []
        for i in range(0, len(raw_chunks) - 1, 2):
            sentence = (raw_chunks[i] + raw_chunks[i + 1]).strip()
            if sentence:
                sentences.append(sentence)
        if len(raw_chunks) % 2 == 1 and raw_chunks[-1].strip():
            sentences.append(raw_chunks[-1].strip())
        return sentences or ([text.strip()] if text.strip() else [])

    @staticmethod
    def _append_pieces(
        entries: List[str],
        entry_idx: int,
        start: float,
        end: float,
        text: str,
    ) -> int:
        """Split ``text`` into single-line cues and distribute the time span."""
        pieces = segment_cue(single_line(text), MAX_CUE_EM)
        if not pieces:
            return entry_idx
        if end <= start:
            end = start + max(0.6, len(pieces) * 0.8)

        weights = [max(0.5, estimate_em(piece)) for piece in pieces]
        total_weight = sum(weights) or 1.0
        cursor = start
        for piece, weight in zip(pieces, weights):
            duration = (end - start) * weight / total_weight
            cue_end = min(end, cursor + duration)
            if cue_end <= cursor + 0.05:
                cue_end = min(end, cursor + 0.3)
            entries.append(
                f"{entry_idx}\n"
                f"{format_srt_time(cursor)} --> {format_srt_time(max(cue_end, cursor + 0.25))}\n"
                f"{piece}\n"
            )
            entry_idx += 1
            cursor = cue_end
        return entry_idx

    @classmethod
    def generate_full_srt(cls, timeline: Dict[str, Any], output_srt_path: Path) -> Path:
        slides = timeline.get("slides") or timeline.get("beats", [])
        entries: List[str] = []
        entry_idx = 1

        for slide in slides:
            slide_start = float(slide.get("start_time", 0.0))
            audio_dur = float(slide.get("audio_duration", 0.0))
            narration = slide.get("narration_script") or slide.get("narration", "")

            timeline_cues = slide.get("cues") or []
            if timeline_cues:
                for cue in timeline_cues:
                    cue_start = max(slide_start, float(cue.get("start", 0.0)))
                    cue_end = max(cue_start + 0.25, float(cue.get("end", cue_start + 0.6)))
                    entry_idx = cls._append_pieces(
                        entries, entry_idx, cue_start, cue_end, str(cue.get("text", ""))
                    )
                continue

            if not narration or audio_dur <= 0.1:
                continue

            sentences = cls.split_into_sentences(narration)
            if not sentences:
                continue
            weights = [max(0.5, estimate_em(sentence)) for sentence in sentences]
            total_weight = sum(weights) or 1.0

            cursor = slide_start
            for sentence, weight in zip(sentences, weights):
                duration = audio_dur * weight / total_weight
                sentence_end = min(slide_start + audio_dur, cursor + duration)
                entry_idx = cls._append_pieces(entries, entry_idx, cursor, sentence_end, sentence)
                cursor = sentence_end

        output_srt_path.parent.mkdir(parents=True, exist_ok=True)
        output_srt_path.write_text("\n".join(entries), encoding="utf-8")
        print(f"[+] SubtitleEngine: Generated {len(entries)} single-line cues -> {output_srt_path.name}")
        return output_srt_path


if __name__ == "__main__":
    sample = (
        "欢迎来到 GPU 高性能计算与 CUDA 架构精讲。今天我们聚焦官方文档核心章节：Programming Model。"
        "在 GPU 异构计算的宏大世界里，这一章节具有承前启后的关键战略意义。"
    )
    for index, sentence in enumerate(SubtitleEngine.split_into_sentences(sample), 1):
        print(index, sentence)
