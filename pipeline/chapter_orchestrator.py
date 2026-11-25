"""
Master Chapter Orchestrator (chapter_orchestrator.py).
Takes a technical section from the documentation, executes the complete dual-track workflow:
1. Generates structured PPT Deck (Markdown & HTML presentations)
2. Synthesizes Speech Voiceover per slide
3. Renders Presentation Slide Video Track for concept overview, misconceptions & best practices
4. Renders Manim 3Blue1Brown Animation Track for the core physical microarchitecture conflict
5. Stitches both tracks into a complete, rich, structured Chapter Master Video (3~5 minutes)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.l2_deck_generator import LectureDeckGenerator
from pipeline.l2b_slide_exporter import export_deck_to_markdown_ppt, export_deck_to_html_presentation
from pipeline.l3_audio_timing import AudioTimingEngine
from pipeline.l4_manim_generator import ManimEngine
from pipeline.l4b_slide_renderer import SlideVideoRenderer
from pipeline.l5_video_composer import VideoComposer


class ChapterOrchestrator:
    def __init__(self, api_key: Optional[str] = None, voice: Optional[str] = None):
        self.deck_gen = LectureDeckGenerator(api_key=api_key)
        self.audio_engine = AudioTimingEngine(voice=voice)
        self.slide_renderer = SlideVideoRenderer()
        self.manim_engine = ManimEngine()
        self.composer = VideoComposer()
        self.output_dir = config.OUTPUT_DIR / "videos"

    def produce_chapter_video(self, chunk: Dict[str, Any], quality: str = "-ql") -> Dict[str, Any]:
        """Produces full chapter video with both PPT slides and Manim animation."""
        concept_id = chunk["chunk_id"]
        print(f"\n======================================================================")
        print(f"🎬 [Chapter Production] Starting: {chunk.get('title', concept_id)}")
        print(f"======================================================================")

        # Step 1: Generate PPT Lecture Deck
        print(f"[*] Step 1: Generating structured PPT lecture deck from documentation...")
        deck = self.deck_gen.generate_deck_for_chunk(chunk)
        topic = deck.get("topic", chunk.get("title", concept_id))
        slides = deck.get("slides", [])

        # Export presentations
        md_ppt = config.OUTPUT_DIR / "decks" / f"{concept_id}_presentation.md"
        html_ppt = config.OUTPUT_DIR / "decks" / f"{concept_id}_presentation.html"
        export_deck_to_markdown_ppt(deck, md_ppt)
        export_deck_to_html_presentation(deck, html_ppt)

        # Step 2: Synthesize voiceover and build audio timeline
        print(f"[*] Step 2: Synthesizing TTS speech and constructing millisecond audio-clock...")
        timeline = self.audio_engine.run(deck)
        timeline_slides = timeline.get("slides", [])

        # Step 3: Render Sub-Clips (PPT Slides + Manim Microarchitecture Animation)
        print(f"[*] Step 3: Rendering dual-track visual assets (PPT Slides + Manim Scene)...")
        sub_clips: List[Path] = []
        clip_dir = config.OUTPUT_DIR / "videos" / f"{concept_id}_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)

        for s in timeline_slides:
            s_id = s.get("slide_id", 1)
            s_type = s.get("slide_type", "")
            duration = s.get("total_beat_duration", 5.0)
            audio_path = Path(s.get("audio_file", ""))

            # If slide is the dedicated physics/hardware simulation, render via Manim!
            if s_type == "manim_physics_demo" or "collision" in s.get("visual_spec", {}).get("layout", ""):
                print(f"    - Rendering Slide {s_id} via 3Blue1Brown-style Manim engine (Physics Simulation)...")
                scene_f, scene_c = self.manim_engine.generate_code_for_timeline(timeline)
                raw_manim = self.manim_engine.render_scene(scene_f, scene_c, quality=quality)
                if raw_manim and raw_manim.exists():
                    manim_clip = clip_dir / f"clip_slide_{s_id}.mp4"
                    composed_manim = self.composer.compose_final_video(raw_manim, timeline, output_mp4=manim_clip)
                    if composed_manim and composed_manim.exists():
                        sub_clips.append(composed_manim)
                        continue

            # Otherwise, render high-definition PPT lecture slide video card
            print(f"    - Rendering Slide {s_id} via PPT Slide Card Engine: {s.get('title')}...")
            img_path = self.slide_renderer.render_slide_image(s, topic=topic)
            clip_path = clip_dir / f"clip_slide_{s_id}.mp4"
            rendered_clip = self.slide_renderer.create_slide_video_clip(img_path, audio_path, clip_path, duration)
            if rendered_clip and rendered_clip.exists():
                sub_clips.append(rendered_clip)

        # Step 4: Stitch Chapter Sub-Clips into Single Seamless Chapter Master Video
        print(f"[*] Step 4: Stitching {len(sub_clips)} clips into Chapter Master Video...")
        chapter_master_name = f"{concept_id}_chapter_final.mp4"
        chapter_video = self.composer.concatenate_course_videos(sub_clips, output_filename=chapter_master_name)

        print(f"\n🎉 [Chapter Finished] Master Chapter Video: {chapter_video}")
        return {
            "concept_id": concept_id,
            "topic": topic,
            "slides_count": len(slides),
            "deck_md": md_ppt,
            "deck_html": html_ppt,
            "chapter_video": chapter_video,
            "timeline": timeline
        }


if __name__ == "__main__":
    from pipeline.l1_chunker import CudaChunker
    c = CudaChunker()
    chunks = c.process_and_save_chunks()
    orch = ChapterOrchestrator()
    res = orch.produce_chapter_video(chunks[0], quality="-ql")
    print("\nResult:", res)
