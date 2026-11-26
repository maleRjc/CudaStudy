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
import time
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
from pipeline.deepseek_director import DeepSeekDirector


class FullBookOrchestrator:
    def __init__(self, pdf_path: Optional[Path] = None, api_key: Optional[str] = None, voice: Optional[str] = None):
        self.parser = FullBookPdfParser(pdf_path)
        self.deck_gen = DeepPedagogicalDeckGenerator(api_key=api_key)
        self.audio_engine = AudioTimingEngine(voice=voice)
        self.slide_renderer = SlideVideoRenderer()
        self.manim_engine = ManimEngine()
        self.composer = VideoComposer()
        self.director = DeepSeekDirector(api_key=api_key)
        self.output_dir = config.OUTPUT_DIR / "videos"

    def _update_status(self, sec_id: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Updates persistent checkpoint progress in output/curriculum/production_status.json."""
        status_file = config.OUTPUT_DIR / "curriculum" / "production_status.json"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[sec_id] = {
            "status": status,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            **(details or {})
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def produce_section_video(
        self,
        section: Dict[str, Any],
        quality: str = "-ql",
        resume: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Produces a complete, exhaustive lecture video for ANY section in the book.
        Supports seamless checkpoint resume and caching to avoid duplicate compute.
        """
        sec_title = section["title"]
        sec_id = section["sec_id"]
        final_video_path = config.OUTPUT_DIR / "videos" / f"{sec_id}_final.mp4"
        md_ppt = config.OUTPUT_DIR / "decks" / f"{sec_id}_presentation.md"
        html_ppt = config.OUTPUT_DIR / "decks" / f"{sec_id}_presentation.html"

        # Checkpoint Resume: If master video already produced and not forcing re-render
        if resume and not force and final_video_path.exists() and final_video_path.stat().st_size > 50000:
            print(f"\n======================================================================")
            print(f"⏩ [Checkpoint Resume] Found completed video for {sec_title}!")
            print(f"    Video: {final_video_path} ({round(final_video_path.stat().st_size / 1024 / 1024, 2)} MB)")
            print(f"======================================================================")
            self._update_status(sec_id, "COMPLETED", {"video": str(final_video_path)})
            return {
                "sec_id": sec_id,
                "topic": sec_title,
                "slides_count": 0,
                "deck_md": md_ppt,
                "deck_html": html_ppt,
                "final_video": final_video_path,
                "timeline": {}
            }

        self._update_status(sec_id, "IN_PROGRESS")
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
            clip_path = clip_dir / f"clip_slide_{s_id}.mp4"

            # Check individual slide cache
            if resume and not force and clip_path.exists() and clip_path.stat().st_size > 5000:
                print(f"    - Slide {s_id}: ⏩ [Cached] Reusing existing clip ({clip_path.name})")
                sub_clips.append(clip_path)
                continue

            # Intelligent Animation Curation via DeepSeek Director
            anim_eval = self.director.evaluate_animation_necessity(s.get("title", ""), s.get("narrative_script", ""))
            should_animate = (
                s_type == "manim_physics_demo"
                or anim_eval.get("needs_animation", False)
                or "collision" in s.get("visual_spec", {}).get("layout", "")
            )

            # If slide is designated for Manim microarchitecture simulation, render via Manim
            if should_animate:
                reason = anim_eval.get("reason", "微架构动态演进仿真")
                print(f"    - Slide {s_id}: Rendering 3Blue1Brown-style Manim Physics Animation ({reason})...")
                slide_timeline = {
                    "chunk_id": f"{sec_id}_slide_{s_id}",
                    "beats": s.get("beats", []),
                    "title": s.get("title", sec_title)
                }
                scene_f, scene_c = self.manim_engine.generate_code_for_timeline(slide_timeline)
                raw_manim = self.manim_engine.render_scene(scene_f, scene_c, quality=quality)
                if raw_manim and raw_manim.exists():
                    composed_manim = self.composer.compose_clip_with_audio(raw_manim, audio_path, clip_path, duration)
                    if composed_manim and composed_manim.exists():
                        sub_clips.append(composed_manim)
                        continue

            # Otherwise, render high-definition PPT Lecture Slide Card
            print(f"    - Slide {s_id}: Rendering High-Def PPT Lecture Card ({s.get('title')})...")
            img_path = self.slide_renderer.render_slide_image(s, topic=topic)
            rendered_clip = self.slide_renderer.create_slide_video_clip(img_path, audio_path, clip_path, duration)
            if rendered_clip and rendered_clip.exists():
                sub_clips.append(rendered_clip)

        # 6. Generate Subtitles & Stitch Sub-Clips into Synchronized Master Video with Burned Subtitles
        print(f"[*] Step 5: Generating sentence-level subtitles & stitching {len(sub_clips)} clips into Section Video...")
        srt_path = config.OUTPUT_DIR / "videos" / f"{sec_id}_subtitles.srt"
        self.composer.generate_srt_subtitles(timeline, srt_path)

        section_video_name = f"{sec_id}_final.mp4"
        final_video = self.composer.concatenate_course_videos(
            sub_clips,
            output_filename=section_video_name,
            srt_path=srt_path,
            burn_subtitles=True
        )


        self._update_status(sec_id, "COMPLETED", {"video": str(final_video), "clips": len(sub_clips)})
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
