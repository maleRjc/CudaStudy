"""
Master End-to-End Orchestrator for CUDA Document to Video Pipeline.
Runs the entire 5-layer workflow automatically from PDF to final synced MP4 video.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config
from pipeline.l1_chunker import CudaChunker
from pipeline.l2_deepseek_beats import DeepSeekBeatGenerator
from pipeline.l3_audio_timing import AudioTimingEngine
from pipeline.l4_manim_generator import ManimEngine
from pipeline.l5_video_composer import VideoComposer


def run_pipeline_for_chunk(chunk_data: dict, quality: str = "-qm") -> dict:
    """Executes the complete 5-layer pipeline for a single cognitive conflict chunk."""
    chunk_id = chunk_data["chunk_id"]
    print("=" * 70)
    print(f"🎬 [STARTING PIPELINE] Chunk: {chunk_id} - '{chunk_data['title']}'")
    print("=" * 70)

    start_total_time = time.time()

    # Layer 2: DeepSeek Cognitive Bottlenecks & Visual Beats
    l2_gen = DeepSeekBeatGenerator()
    beats_manifest = l2_gen.generate_for_chunk(chunk_data)

    # Layer 3: Audio TTS & Audio-Clock Driven Timeline
    l3_engine = AudioTimingEngine()
    timeline = l3_engine.run(beats_manifest)

    # Layer 4: Manim Code Generation & Self-Healing Rendering
    l4_engine = ManimEngine()
    scene_file, scene_class = l4_engine.generate_code_for_timeline(timeline)
    raw_video = l4_engine.render_scene(scene_file, scene_class, quality=quality)

    if not raw_video or not raw_video.exists():
        print(f"[!] Layer 4 failed to render video for {chunk_id}")
        return {"chunk_id": chunk_id, "success": False, "error": "Manim rendering failed"}

    # Layer 5: AV Muxing, Synced Subtitles, and Delivery
    l5_composer = VideoComposer()
    final_video = l5_composer.compose_final_video(raw_video, timeline)

    elapsed = round(time.time() - start_total_time, 2)
    print("=" * 70)
    if final_video and final_video.exists():
        print(f"🎉 [PIPELINE SUCCESS] Produced: {final_video}")
        print(f"⏱️ Total processing time: {elapsed}s | Video Duration: {timeline['total_video_duration']}s")
        print("=" * 70)
        return {
            "chunk_id": chunk_id,
            "success": True,
            "final_video": str(final_video),
            "subtitles": str(config.OUTPUT_DIR / "videos" / f"{chunk_id}_subtitles.srt"),
            "duration": timeline["total_video_duration"],
            "elapsed_time": elapsed
        }
    else:
        print(f"[!] Pipeline completed but final video composition failed.")
        return {"chunk_id": chunk_id, "success": False, "error": "FFmpeg composition failed"}


def main():
    parser = argparse.ArgumentParser(description="CUDA Guide to Pedagogical Animation Generator")
    parser.add_argument("--chunk", type=str, default="01_global_thread_indexing", help="Chunk ID to process")
    parser.add_argument("--quality", type=str, default="ql", choices=["ql", "qm", "qh", "qk"],
                        help="Manim quality flag: ql (480p fast), qm (720p), qh (1080p), qk (4k)")
    parser.add_argument("--all", action="store_true", help="Process all extracted chunks")
    args = parser.parse_args()

    quality_flag = f"-{args.quality}"

    # Step 1: Ensure Chunks are extracted from PDF
    chunker = CudaChunker()
    chunks = chunker.process_and_save_chunks()

    if args.all:
        results = []
        for ch in chunks:
            res = run_pipeline_for_chunk(ch, quality=quality_flag)
            results.append(res)
        print("\nAll pipeline tasks finished. Summary:")
        for r in results:
            print(f"- {r.get('chunk_id')}: {'SUCCESS' if r.get('success') else 'FAILED'}")
    else:
        # Match single chunk
        selected = next((c for c in chunks if c["chunk_id"] == args.chunk), None)
        if not selected:
            print(f"Chunk '{args.chunk}' not found, falling back to first chunk '{chunks[0]['chunk_id']}'")
            selected = chunks[0]
        run_pipeline_for_chunk(selected, quality=quality_flag)


if __name__ == "__main__":
    main()
