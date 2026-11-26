"""
Sentence-Level Dynamic Subtitle Generator (pipeline/subtitle_engine.py).
Splits long continuous narration paragraphs into natural, short spoken sentences,
calculates proportional millisecond start/end timestamps,
and exports publication-grade SRT files and FFmpeg subtitle filter arguments.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Tuple


def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT timestamp (HH:MM:SS,mmm)."""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


class SubtitleEngine:
    """Generates fine-grained, sentence-level synchronized subtitles from audio timeline."""

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Splits continuous narration into clear, concise spoken subtitle lines."""
        if not text:
            return []
        # Split on standard Chinese/English sentence boundaries
        raw_chunks = re.split(r'([。！？；\n]+)', text)
        sentences = []
        for i in range(0, len(raw_chunks) - 1, 2):
            s = (raw_chunks[i] + raw_chunks[i + 1]).strip()
            if s:
                # If a sentence is very long (>30 chars), split by comma or pause
                if len(s) > 30 and ("，" in s or "," in s):
                    sub_parts = re.split(r'([，,])', s)
                    for j in range(0, len(sub_parts) - 1, 2):
                        sub_s = (sub_parts[j] + sub_parts[j + 1]).strip()
                        if sub_s:
                            sentences.append(sub_s)
                    if len(sub_parts) % 2 == 1 and sub_parts[-1].strip():
                        sentences.append(sub_parts[-1].strip())
                else:
                    sentences.append(s)

        if len(raw_chunks) % 2 == 1 and raw_chunks[-1].strip():
            last = raw_chunks[-1].strip()
            if last:
                sentences.append(last)

        # Fallback if no punctuation matched
        if not sentences and text.strip():
            sentences = [text.strip()]

        return sentences

    @classmethod
    def generate_full_srt(cls, timeline: Dict[str, Any], output_srt_path: Path) -> Path:
        """
        Builds a complete, sentence-level synchronized SRT subtitle file
        from the chapter's audio-visual timeline schedule.
        """
        slides = timeline.get("slides") or timeline.get("beats", [])
        srt_entries = []
        entry_idx = 1

        for s in slides:
            slide_start = float(s.get("start_time", 0.0))
            audio_dur = float(s.get("audio_duration", 0.0))
            narration = s.get("narration_script") or s.get("narration", "")

            if not narration or audio_dur <= 0.1:
                continue

            sentences = cls.split_into_sentences(narration)
            if not sentences:
                continue

            # Calculate character counts (excluding punctuation) to apportion time
            clean_lengths = [max(1, len(re.sub(r'[^\w\u4e00-\u9fff]', '', sent))) for sent in sentences]
            total_chars = sum(clean_lengths)

            curr_offset = 0.0
            for idx, (sent, char_len) in enumerate(zip(sentences, clean_lengths)):
                prop = char_len / total_chars
                sent_dur = audio_dur * prop

                sent_start = slide_start + curr_offset
                sent_end = sent_start + sent_dur

                # Add tiny gap at end of sentence
                sent_end_clamped = min(slide_start + audio_dur, sent_end - 0.05)
                if sent_end_clamped <= sent_start:
                    sent_end_clamped = sent_end

                srt_entries.append(
                    f"{entry_idx}\n"
                    f"{format_srt_time(sent_start)} --> {format_srt_time(sent_end_clamped)}\n"
                    f"{sent}\n"
                )
                entry_idx += 1
                curr_offset += sent_dur

        output_srt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_entries))

        print(f"[+] SubtitleEngine: Generated {len(srt_entries)} sentence-level subtitle entries -> {output_srt_path.name}")
        return output_srt_path


if __name__ == "__main__":
    sample_text = (
        "欢迎来到 GPU 高性能计算与 CUDA 架构精讲。今天我们聚焦官方文档核心章节：Programming Model。"
        "在 GPU 异构计算的宏大世界里，这一章节具有承前启后的关键战略意义。"
        "很多初学者在阅读这部分文档时，往往因为缺少物理空间直觉而感到晦涩难懂。"
    )
    sents = SubtitleEngine.split_into_sentences(sample_text)
    print("Split sentences:")
    for i, s in enumerate(sents, 1):
        print(f"  {i}. {s}")
