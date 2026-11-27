"""
Full-book orchestrator.

Pipeline per section:
  1. parse the PDF section (text, paragraphs, real code blocks)
  2. generate the pedagogical deck with DeepSeek (API key required, no fallback)
  3. synthesize narration + build the audio clock
  4. render every slide: a dedicated Manim storyboard (most slides) or a card
  5. normalize all clips, concatenate, burn subtitles into the 88px band

Every slide has its own scene plan, so the animation changes page by page.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.l1_full_parser import FullBookPdfParser
from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator
from pipeline.l2b_slide_exporter import export_deck_to_html_presentation, export_deck_to_markdown_ppt
from pipeline.l3_audio_timing import AudioTimingEngine
from pipeline.l4b_slide_renderer import SlideVideoRenderer
from pipeline.l5_video_composer import VideoComposer
from pipeline.manim_renderer import StoryboardRenderer
from pipeline.storyboard import normalize_plan, plan_fingerprint, slide_wants_animation

ProgressFn = Optional[Callable[[str, str, float], None]]


def _slug(text: str, limit: int = 60) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", str(text)).strip("_")
    return (cleaned or "section")[:limit]


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


class FullBookOrchestrator:
    def __init__(
        self,
        pdf_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        voice: Optional[str] = None,
        quality: str = "-qm",
        progress: ProgressFn = None,
    ):
        if api_key:
            config.set_api_key(api_key)
        self.api_key = config.api_key()
        self.pdf_path = Path(pdf_path) if pdf_path else config.DEFAULT_PDF_PATH
        self.progress = progress

        self.parser = FullBookPdfParser(self.pdf_path)
        self.deck_gen = DeepPedagogicalDeckGenerator(api_key=self.api_key)
        self.audio_engine = AudioTimingEngine(voice=voice)
        self.slide_renderer = SlideVideoRenderer()
        self.composer = VideoComposer()
        self.renderer: Optional[StoryboardRenderer] = None
        self.renderer_error = ""

        self.output_dir = config.OUTPUT_DIR / "videos"
        self.status_file = config.OUTPUT_DIR / "curriculum" / "production_status.json"

        print(
            f"[*] Orchestrator: pdf={self.pdf_path.name} "
            f"deepseek={'ON (' + self._key_hint() + ')' if self.api_key else 'MISSING (generation will fail)'} "
            f"video={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT} "
            f"(content {config.CONTENT_WIDTH}x{config.CONTENT_HEIGHT} + band {config.SUBTITLE_BAND_HEIGHT})"
        )

    # ------------------------------------------------------------------
    def _key_hint(self) -> str:
        from pipeline.deepseek_client import key_fingerprint

        return f"sha256:{key_fingerprint(self.api_key)}"

    def _emit(self, stage: str, message: str, pct: float = 0.0):
        print(message)
        if self.progress:
            try:
                self.progress(stage, message, max(0.0, min(1.0, pct)))
            except Exception:
                pass

    def _get_renderer(self) -> Optional[StoryboardRenderer]:
        if self.renderer is not None:
            return self.renderer
        if self.renderer_error:
            return None
        try:
            self.renderer = StoryboardRenderer()
            return self.renderer
        except Exception as exc:
            self.renderer_error = str(exc)
            print(f"[!] Manim renderer unavailable: {exc}")
            return None

    # ------------------------------------------------------------------
    def _update_status(self, sec_id: str, status: str, details: Optional[Dict[str, Any]] = None):
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if self.status_file.exists():
                try:
                    data = json.loads(self.status_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    data = {}
            data[sec_id] = {
                "status": status,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                **(details or {}),
            }
            tmp = self.status_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.status_file)
        except OSError as exc:
            print(f"[!] Could not update status: {exc}")

    # ------------------------------------------------------------------
    def produce_section_video(
        self,
        section: Dict[str, Any],
        quality: str = "-qm",
        resume: bool = True,
        force: bool = False,
        max_slides: Optional[int] = None,
    ) -> Dict[str, Any]:
        sec_id = section["sec_id"]
        sec_title = section["title"]
        safe_id = _slug(sec_id, 70)

        if not config.has_api_key():
            message = (
                "未配置 DEEPSEEK_API_KEY：本版本已移除「无 Key 兜底」模式，"
                "不会再生成模板讲稿。请在项目根目录 .env 填入 Key，或在 GUI 输入框中填写后重试。"
            )
            print(f"[!] {message}")
            self._update_status(sec_id, "FAILED", {"error": message})
            return {
                "sec_id": sec_id,
                "topic": sec_title,
                "slides_count": 0,
                "deck_md": None,
                "deck_html": None,
                "final_video": None,
                "timeline": {},
                "source": "error",
                "error": message,
            }

        final_video = self.output_dir / f"{safe_id}_final.mp4"
        manifest_path = self.output_dir / f"{safe_id}_manifest.json"
        srt_path = self.output_dir / f"{safe_id}_subtitles.srt"
        deck_md = config.OUTPUT_DIR / "decks" / f"{safe_id}_presentation.md"
        deck_html = config.OUTPUT_DIR / "decks" / f"{safe_id}_presentation.html"

        started = time.time()
        self._emit("section", f"\n{'=' * 72}\n📘 {sec_title}  (P{section.get('start_page')}-P{section.get('end_page')})\n{'=' * 72}", 0.02)

        try:
            # 1. Parse ---------------------------------------------------
            section_data = self.parser.extract_section_text_and_code(section)
            self._emit(
                "parse",
                f"[1/6] 原文解析完成：{section_data['text_length']} 字，"
                f"{len(section_data['code_snippets'])} 段真实代码",
                0.08,
            )

            # 2. Deck ----------------------------------------------------
            deck = self.deck_gen.generate_deck_from_section(section_data, force=force, max_slides=max_slides)
            deck_fingerprint = _hash(
                {
                    "deck": deck.get("slides"),
                    "schema": config.SCHEMA_VERSION,
                    "voice": self.audio_engine.voice,
                    "rate": self.audio_engine.rate,
                    "subtitle": config.SUBTITLE_VERSION,
                    "geometry": [config.VIDEO_WIDTH, config.VIDEO_HEIGHT, config.VIDEO_FPS],
                }
            )

            if resume and not force and final_video.exists() and final_video.stat().st_size > 50_000:
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    manifest = {}
                if manifest.get("fingerprint") == deck_fingerprint:
                    self._emit("done", f"⏩ 断点续跑：命中已完成视频 {final_video.name}", 1.0)
                    self._update_status(sec_id, "COMPLETED", {"video": str(final_video), "cached": True})
                    return {
                        "sec_id": sec_id,
                        "topic": deck.get("topic", sec_title),
                        "slides_count": len(deck.get("slides", [])),
                        "deck_md": deck_md,
                        "deck_html": deck_html,
                        "final_video": final_video,
                        "timeline": {},
                        "source": deck.get("source", "cache"),
                        "cached": True,
                    }
            elif resume and final_video.exists():
                self._emit("deck", "[!] 检测到旧成片但讲稿已变化，重新渲染（分页缓存仍会复用）", 0.1)

            export_deck_to_markdown_ppt(deck, deck_md)
            export_deck_to_html_presentation(deck, deck_html)
            self._emit(
                "deck",
                f"[2/6] 讲稿就绪：{len(deck.get('slides', []))} 页（来源：{deck.get('source')}）",
                0.18,
            )

            # 3. Audio + timeline ---------------------------------------
            timeline = self.audio_engine.run(deck)
            timeline_slides = timeline["slides"]
            self._emit("audio", f"[3/6] 配音与时间轴完成：{timeline['total_video_duration']:.1f}s", 0.34)

            # 4. Clips ---------------------------------------------------
            clip_dir = self.output_dir / safe_id
            clip_dir.mkdir(parents=True, exist_ok=True)
            renderer = self._get_renderer()
            clips: List[Path] = []
            total = max(1, len(timeline_slides))

            for position, item in enumerate(timeline_slides, start=1):
                slide = next((s for s in deck["slides"] if int(s.get("slide_id", -1)) == int(item["slide_id"])), item)
                duration = float(item["total_beat_duration"])
                audio_path = Path(item["audio_file"]) if item.get("audio_file") else None

                raw_plan = item.get("scene_plan") or {}
                windows = raw_plan.get("windows") if isinstance(raw_plan, dict) else None
                plan = normalize_plan(raw_plan, slide, topic=deck.get("topic", ""), duration=duration)
                plan["duration"] = round(max(2.5, duration), 3)
                if windows:
                    plan["windows"] = windows
                clip_key = _hash(
                    {
                        "plan": plan,
                        "duration": round(duration, 2),
                        "geometry": [config.VIDEO_WIDTH, config.VIDEO_HEIGHT, config.VIDEO_FPS],
                        "schema": config.SCHEMA_VERSION,
                    }
                )
                clip_path = clip_dir / f"clip_{position:02d}_{clip_key}.mp4"

                if resume and not force and clip_path.exists() and clip_path.stat().st_size > 5000:
                    print(f"    - Slide {item['slide_id']}: ⏩ cached clip")
                    clips.append(clip_path)
                    self._emit("render", f"[4/6] 第 {position}/{total} 页：复用已渲染片段", 0.34 + 0.5 * position / total)
                    continue

                animated = slide_wants_animation(slide) and renderer is not None
                rendered = False

                if animated:
                    print(
                        f"    - Slide {item['slide_id']}: Manim storyboard kind={plan['kind']} "
                        f"steps={len(plan['steps'])} ({duration:.1f}s)"
                    )
                    raw = renderer.render(plan, work_key=f"{safe_id}_{position:02d}_{clip_key}")
                    if raw is not None:
                        normalized = self.composer.normalize_clip(raw, clip_path, duration, audio=audio_path)
                        if normalized is not None:
                            clips.append(normalized)
                            rendered = True
                            try:
                                raw.unlink()
                            except OSError:
                                pass
                    if not rendered:
                        print(f"    - Slide {item['slide_id']}: Manim failed -> falling back to slide card")

                if not rendered:
                    image = self.slide_renderer.render_slide_image(slide, topic=deck.get("topic", ""))
                    raw_clip = clip_dir / f".raw_{position:02d}.mp4"
                    raw_clip = self.slide_renderer.create_slide_video_clip(image, audio_path, raw_clip, duration)
                    if raw_clip is not None:
                        normalized = self.composer.normalize_clip(raw_clip, clip_path, duration)
                        if normalized is not None:
                            clips.append(normalized)
                            try:
                                raw_clip.unlink()
                            except OSError:
                                pass

                if not clips or clips[-1] != clip_path:
                    raise RuntimeError(f"slide {item['slide_id']} 渲染失败（Manim 与卡片均未产出）")

                self._emit(
                    "render",
                    f"[4/6] 第 {position}/{total} 页完成：{item['title'][:28]}",
                    0.34 + 0.5 * position / total,
                )

            # 5. Subtitles + concatenation -------------------------------
            self.composer.generate_srt_subtitles(timeline, srt_path)
            self._emit("compose", f"[5/6] 拼接 {len(clips)} 个片段并烧录字幕（底部独立条带）...", 0.88)

            final = self.composer.concatenate_course_videos(
                clips,
                output_filename=final_video.name,
                srt_path=srt_path,
                burn_subtitles=True,
            )
            if final is None or not final.exists():
                raise RuntimeError("最终视频合成失败（FFmpeg concat/burn 返回空）")

            # 6. Manifest -------------------------------------------------
            self._update_status(
                sec_id,
                "COMPLETED",
                {
                    "video": str(final),
                    "slides": len(timeline_slides),
                    "deepseek": deck.get("source"),
                },
            )
            try:
                manifest_path.write_text(
                    json.dumps(
                        {
                            "fingerprint": deck_fingerprint,
                            "deck_source": deck.get("source"),
                            "slides": len(timeline_slides),
                            "duration": probe_duration(final),
                            "video": str(final),
                            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except OSError:
                pass

            elapsed = time.time() - started
            self._emit(
                "done",
                f"[6/6] 🎉 完成：{final.name} "
                f"({round(final.stat().st_size / 1024 / 1024, 1)} MB, {probe_duration(final):.0f}s, 用时 {elapsed:.0f}s)",
                1.0,
            )
            return {
                "sec_id": sec_id,
                "topic": deck.get("topic", sec_title),
                "slides_count": len(deck.get("slides", [])),
                "deck_md": deck_md,
                "deck_html": deck_html,
                "final_video": final,
                "timeline": timeline,
                "source": deck.get("source"),
                "cached": False,
            }

        except Exception as exc:
            import traceback

            self._update_status(sec_id, "FAILED", {"error": str(exc)[:400]})
            print(f"[!] Section failed: {sec_id}: {exc}")
            print(traceback.format_exc())
            return {
                "sec_id": sec_id,
                "topic": sec_title,
                "slides_count": 0,
                "deck_md": deck_md,
                "deck_html": deck_html,
                "final_video": None,
                "timeline": {},
                "source": "error",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    def produce_many(
        self,
        sections: List[Dict[str, Any]],
        resume: bool = True,
        force: bool = False,
        limit: Optional[int] = None,
        max_slides: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        selected = sections[:limit] if limit else sections
        for idx, section in enumerate(selected, start=1):
            print(f"\n[{idx}/{len(selected)}] {section.get('title')}")
            results.append(
                self.produce_section_video(section, resume=resume, force=force, max_slides=max_slides)
            )
        return results


def probe_duration(path: Path) -> float:
    from pipeline.manim_renderer import probe_duration as _probe

    return _probe(path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Produce CUDA section videos")
    parser.add_argument("--section", type=int, default=2, help="1-based curriculum index")
    parser.add_argument("--episode", type=int, default=0, help="1-based syllabus episode (ep_XX)")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-slides", type=int, default=0)
    args = parser.parse_args()

    orchestrator = FullBookOrchestrator()
    if not config.has_api_key():
        raise SystemExit(
            "DEEPSEEK_API_KEY 未配置。本版本已移除无 Key 兜底模式；"
            "请先复制 .env.example 为 .env 并填入 Key。"
        )
    curriculum = orchestrator.parser.extract_full_curriculum(min_level=1, max_level=1)
    if not curriculum:
        raise SystemExit("No curriculum extracted from the PDF.")

    if args.episode:
        from pipeline.deepseek_director import CURRICULUM_30_EPISODES
        from pipeline.episode_router import describe_match, resolve_episode_section

        episode = next((e for e in CURRICULUM_30_EPISODES if int(e["ep_id"]) == args.episode), None)
        if episode is None:
            raise SystemExit(f"Episode {args.episode} not found.")
        resolved = resolve_episode_section(curriculum, episode, args.episode)
        print(f"[*] Episode route: {describe_match(resolved)}")
        chosen = [resolved]
    else:
        start = max(1, min(args.section, len(curriculum))) - 1
        chosen = curriculum[start: start + max(1, args.limit)]

    orchestrator.produce_many(
        chosen,
        resume=not args.force,
        force=args.force,
        limit=None,
        max_slides=args.max_slides or None,
    )
