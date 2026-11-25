"""
Full-Book Dynamic Course Orchestrator (full_book_orchestrator.py).
Takes ANY section from ANY technical PDF:
1. Extracts real section text, page range, and code
2. Generates comprehensive 6~10 slide pedagogical PPT lecture deck (with exhaustive narrations)
3. Exports standalone HTML and Markdown presentation decks for user preview
4. Synthesizes synchronized speech audio per slide
5. Renders dual-track video clips: High-res PPT visual slide cards + 3Blue1Brown Manim physics simulations
6. Stitches into complete, high-density chapter video (3~8 minutes)
7. Stitches all chosen chapters into a comprehensive master course
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.l1_full_parser import FullBookPdfParser
from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator
from pipeline.l2b_slide_exporter import export_deck_to_markdown_ppt, export_deck_to_html_presentation
from pipeline.l3_audio_timing import AudioTimingEngine
from pipeline.l4_manim_generator import ManimEngine
from pipeline.l4b_slide_renderer import SlideVideoRenderer
from pipeline.l5_video_composer import VideoComposer


class FullBookOrchestrator:
    def __init__(self, pdf_path: Optional[Path] = None, api_key: Optional[str] = None, voice: Optional[str] = None):
        self.parser = FullBookPdfParser(pdf_path)
        self.deck_gen = DeepPedagogicalDeckGenerator(api_key=api_key)
        self.audio_engine = AudioTimingEngine(voice=voice)
        self.slide_renderer = SlideVideoRenderer()
        self.manim_engine = ManimEngine()
        self.composer = VideoComposer()
        self.output_dir = config.OUTPUT_DIR / "videos"

    def produce_section_video(self, section: Dict[str, Any], quality: str = "-ql") -> Dict[str, Any]:
        """Produces a complete, exhaustive lecture video for ANY section in the book."""
        sec_title = section["title"]
        sec_id = section["sec_id"]

        print(f"\n======================================================================")
        print(f"📘 [Full Book Section Production] {sec_title} (P{section.get('start_page')}-P{section.get('end_page')})")
        print(f"======================================================================")

        # 1. Extract verbatim text and code from PDF
        print(f"[*] Step 1: Extracting text & code from PDF pages {section.get('start_page')} to {section.get('end_page')}...")
        section_data = self.parser.extract_section_text_and_code(section)

        # 2. Generate comprehensive PPT lecture deck
        print(f"[*] Step 2: Synthesizing deep pedagogical PPT lecture deck...")
        deck = self.deck_gen.generate_deck_from_section(section_data)
        topic = deck.get("topic", sec_title)
        slides = deck.get("slides", [])

        # 3. Export standalone presentations (HTML & Markdown)
        md_ppt = config.OUTPUT_DIR / "decks" / f"{sec_id}_presentation.md"
        html_ppt = config.OUTPUT_DIR / "decks" / f"{sec_id}_presentation.html"
        export_deck_to_markdown_ppt(deck, md_ppt)
        export_deck_to_html_presentation(deck, html_ppt)

        # 4. Synthesize speech voiceover per slide
        print(f"[*] Step 3: Synthesizing full narration speech for all {len(slides)} slides...")
        timeline = self.audio_engine.run(deck)
        timeline_slides = timeline.get("slides", [])

        # 5. Render dual-track clips (PPT Cards + Manim Microarchitecture)
        print(f"[*] Step 4: Rendering visual video tracks (PPT Cards + 3Blue1Brown Manim)...")
        sub_clips: List[Path] = []
        clip_dir = config.OUTPUT_DIR / "videos" / f"{sec_id}_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)

        for s in timeline_slides:
            s_id = s.get("slide_id", 1)
            s_type = s.get("slide_type", "")
            duration = s.get("total_beat_duration", 5.0)
            audio_path = Path(s.get("audio_file", ""))

            # If slide is designated for Manim physics simulation, render via Manim
            if s_type == "manim_physics_demo" or "collision" in s.get("visual_spec", {}).get("layout", ""):
                print(f"    - Slide {s_id}: Rendering 3Blue1Brown-style Manim Physics Animation...")
                scene_f, scene_c = self.manim_engine.generate_code_for_timeline(timeline)
                raw_manim = self.manim_engine.render_scene(scene_f, scene_c, quality=quality)
                if raw_manim and raw_manim.exists():
                    manim_clip = clip_dir / f"clip_slide_{s_id}.mp4"
                    composed_manim = self.composer.compose_final_video(raw_manim, timeline, output_mp4=manim_clip)
                    if composed_manim and composed_manim.exists():
                        sub_clips.append(composed_manim)
                        continue

            # Otherwise, render high-definition PPT Lecture Slide Card
            print(f"    - Slide {s_id}: Rendering High-Def PPT Lecture Card ({s.get('title')})...")
            img_path = self.slide_renderer.render_slide_image(s, topic=topic)
            clip_path = clip_dir / f"clip_slide_{s_id}.mp4"
            rendered_clip = self.slide_renderer.create_slide_video_clip(img_path, audio_path, clip_path, duration)
            if rendered_clip and rendered_clip.exists():
                sub_clips.append(rendered_clip)

        # 6. Stitch Sub-Clips into Single Seamless Section Master Video
        print(f"[*] Step 5: Stitching {len(sub_clips)} clips into Section Video...")
        section_video_name = f"{sec_id}_final.mp4"
        final_video = self.composer.concatenate_course_videos(sub_clips, output_filename=section_video_name)

        print(f"\n🎉 [Section Completed] Final Video: {final_video}")
        return {
            "sec_id": sec_id,
            "topic": topic,
            "slides_count": len(slides),
            "deck_md": md_ppt,
            "deck_html": html_ppt,
            "final_video": final_video,
            "timeline": timeline
        }


if __name__ == "__main__":
    orch = FullBookOrchestrator()
    curriculum = orch.parser.extract_full_curriculum(min_level=1, max_level=1)
    res = orch.produce_section_video(curriculum[1], quality="-ql")
    print("\nOrchestrator Result:", res.get("final_video"))
