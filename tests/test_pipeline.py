"""
Contract tests for the v2 pipeline (no network, no LLM key required).

Run with:
    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
from pipeline.deepseek_client import DeepSeekClient, DeepSeekAuthError, parse_json_payload
from pipeline.storyboard import KINDS, normalize_plan, plan_for_slide
from pipeline.subtitle_engine import SubtitleEngine


def make_slide(idx: int, title: str, kind_text: str = "") -> dict:
    return {
        "slide_id": idx,
        "title": title,
        "slide_type": "concept_breakdown",
        "key_points": [f"{title} 的要点 A", f"{title} 的要点 B", f"{title} 的要点 C"],
        "narration_script": f"这是关于{title}的讲稿。我们要理解它的硬件含义。不要只看代码表面。",
        "visual_spec": {"layout": "header_and_bullets", "code_badge": kind_text},
    }


class KindRoutingTests(unittest.TestCase):
    def test_concept_keywords_beat_generic_warp_mentions(self):
        from pipeline.storyboard import choose_kind

        self.assertEqual(
            choose_kind("Shared Memory 与 32 个 Bank 的冲突", "同一 Warp 命中同一 Bank 会排队"),
            "banks",
        )
        self.assertEqual(
            choose_kind("合并访存：一次事务搬完一个 Warp", "跨步访问浪费带宽"),
            "coalesce",
        )
        self.assertEqual(choose_kind("Warp 与 SIMT：32 个线程如何锁步执行", "分支分化"), "warp")

    def test_episode_router_maps_index_episode_to_programming_model(self):
        from pipeline.episode_router import resolve_episode_section

        curriculum = [
            {"sec_id": "sec_002", "title": "Programming Model", "start_page": 20, "end_page": 30, "page_count": 11},
            {
                "sec_id": "sec_030",
                "title": "Programming Systems with Multiple GPUs",
                "start_page": 187,
                "end_page": 191,
                "page_count": 5,
            },
        ]
        resolved = resolve_episode_section(
            curriculum,
            {"title": "GPU 线程索引如何计算？从多维网格到一维物理地址的映射公式"},
            9,
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["start_page"], 20)

    def test_episode_router_maps_warp_episode_to_simt_section(self):
        from pipeline.episode_router import resolve_episode_section

        curriculum = [
            {"sec_id": "sec_004", "title": "Intro to CUDA C++", "start_page": 35, "end_page": 52, "page_count": 18},
            {"sec_id": "sec_006", "title": "Writing SIMT Kernels", "start_page": 61, "end_page": 87, "page_count": 27},
            {"sec_id": "sec_008", "title": "Asynchronous Execution", "start_page": 101, "end_page": 115, "page_count": 15},
        ]
        resolved = resolve_episode_section(curriculum, {"title": "Warp 和 SIMT：GPU 如何真正执行线程？"}, 6)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["start_page"], 61)
        self.assertEqual(resolved["sec_id"], "ep_06")


class StoryboardTests(unittest.TestCase):
    def test_plans_vary_and_are_bounded(self):
        slides = [
            make_slide(1, "线程层级与全局索引"),
            make_slide(2, "异步流水线与多流重叠", "cudaMemcpyAsync(stream);"),
            make_slide(3, "共享内存 Bank 冲突"),
        ]
        plans = [plan_for_slide(s, "Programming Model", 12.0) for s in slides]
        kinds = {p["kind"] for p in plans}
        self.assertGreaterEqual(len(kinds), 2, f"expected visual variety, got {kinds}")
        for plan in plans:
            self.assertGreaterEqual(len(plan["steps"]), 3)
            self.assertLessEqual(len(plan["steps"]), 5)
            self.assertEqual(plan["schema"], "plan-v2")
            self.assertIn(plan["kind"], KINDS)

    def test_malformed_llm_plan_is_repaired(self):
        slide = make_slide(1, "边界检查")
        plan = normalize_plan(
            {"kind": "nonsense", "steps": [{"heading": "", "bullets": "not-a-list"}], "figure": "bad"},
            slide,
            topic="t",
            duration=9,
        )
        self.assertIn(plan["kind"], KINDS)
        self.assertGreaterEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["duration"], 9.0)
        self.assertTrue(all(isinstance(step["bullets"], list) for step in plan["steps"]))

    def test_bullets_filled_from_narration(self):
        slide = make_slide(1, "Warp 分化")
        plan = normalize_plan({"kind": "grid", "steps": [{"heading": "步骤一"}]}, slide, "t", 8)
        self.assertTrue(plan["steps"][0]["bullets"], "narration should provide bullet text")


class KeyPersistenceTests(unittest.TestCase):
    def test_save_api_key_reuses_env_and_preserves_settings(self):
        previous_base = config.BASE_DIR
        previous_key = config.api_key()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                config.BASE_DIR = Path(tmp)
                env_path = Path(tmp) / ".env"
                env_path.write_text(
                    "# my settings\nTTS_VOICE=zh-CN-YunxiNeural\nDEEPSEEK_API_KEY=old-key\n",
                    encoding="utf-8",
                )
                saved = config.save_api_key("sk-new-key")
                self.assertEqual(saved, env_path)
                text = env_path.read_text(encoding="utf-8")
                self.assertIn("DEEPSEEK_API_KEY=sk-new-key", text)
                self.assertNotIn("old-key", text)
                self.assertIn("TTS_VOICE=zh-CN-YunxiNeural", text)
                self.assertEqual(text.count("DEEPSEEK_API_KEY="), 1)

                config.save_api_key("sk-third-key")
                text = env_path.read_text(encoding="utf-8")
                self.assertEqual(text.count("DEEPSEEK_API_KEY="), 1)
                self.assertIn("DEEPSEEK_API_KEY=sk-third-key", text)
        finally:
            config.BASE_DIR = previous_base
            config.set_api_key(previous_key)

    def test_clear_api_key_preserves_other_settings(self):
        previous_base = config.BASE_DIR
        previous_key = config.api_key()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                config.BASE_DIR = Path(tmp)
                env_path = Path(tmp) / ".env"
                env_path.write_text(
                    "TTS_VOICE=zh-CN-YunxiNeural\nDEEPSEEK_API_KEY=sk-to-remove\n",
                    encoding="utf-8",
                )
                config.clear_api_key()
                text = env_path.read_text(encoding="utf-8")
                self.assertNotIn("DEEPSEEK_API_KEY=", text)
                self.assertIn("TTS_VOICE=zh-CN-YunxiNeural", text)
                self.assertEqual(config.api_key(), "")
        finally:
            config.BASE_DIR = previous_base
            config.set_api_key(previous_key)

    def test_save_api_key_rejects_empty(self):
        with self.assertRaises(ValueError):
            config.save_api_key("   ")


class DeckTests(unittest.TestCase):
    def test_duplicate_narration_is_rejected(self):
        from pipeline.l2_deep_deck import DeckOutputError, DeepPedagogicalDeckGenerator

        repeated = "这段讲解在多页中完全重复，应该被反重复校验拦截并触发重写。"
        slides = [
            {
                "title": f"Page {index}",
                "visual_spec": {"scene_plan": {"steps": [{"heading": "步骤", "narration": repeated}]}},
            }
            for index in range(3)
        ]
        with self.assertRaises(DeckOutputError):
            DeepPedagogicalDeckGenerator._check_repetition(slides)

    def test_hallucinated_code_is_dropped(self):
        from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator

        gen = DeepPedagogicalDeckGenerator(api_key="")
        section = {
            "sec_id": "sec_x",
            "title": "Test",
            "start_page": 1,
            "end_page": 2,
            "page_count": 2,
            "full_text": "text",
            "paragraphs": ["这是一个足够长的段落，用来生成讲稿。" * 4],
            "code_snippets": ["int idx = blockIdx.x * blockDim.x + threadIdx.x;"],
        }
        narr1 = "第一页说明为什么要在生成阶段拦截系统调用等危险代码。"
        narr2 = "第二页只讲 blockIdx 与 threadIdx 如何合成全局索引。"
        narr3 = "第三页用三条检查项收束：索引、边界、内存层级。"
        fake = {
            "topic": "Test",
            "slides": [
                {
                    "slide_id": 1,
                    "title": "A",
                    "slide_type": "concept_breakdown",
                    "key_points": ["p1", "p2"],
                    "narration_script": "",
                    "visual_spec": {
                        "code_badge": "os.system('rm -rf /')",
                        "scene_plan": {"kind": "code", "steps": [{"heading": "危险代码", "focus": [0], "narration": narr1}]},
                    },
                },
                {
                    "slide_id": 2,
                    "title": "B",
                    "slide_type": "concept_breakdown",
                    "key_points": ["p1", "p2"],
                    "narration_script": "",
                    "visual_spec": {
                        "code_badge": "int idx = blockIdx.x * blockDim.x + threadIdx.x;",
                        "scene_plan": {"kind": "code", "steps": [{"heading": "索引", "focus": [0], "narration": narr2}]},
                    },
                },
                {
                    "slide_id": 3,
                    "title": "C",
                    "slide_type": "summary_best_practice",
                    "key_points": ["p1", "p2"],
                    "narration_script": "",
                    "visual_spec": {
                        "scene_plan": {"kind": "boxes", "steps": [{"heading": "总结", "focus": [0], "narration": narr3}]}
                    },
                },
            ],
        }
        deck = gen._validate_and_repair(fake, section)
        self.assertEqual(deck["slides"][0]["visual_spec"]["code_badge"], "")
        self.assertIn("blockIdx", deck["slides"][1]["visual_spec"]["code_badge"])
        self.assertGreaterEqual(len(deck["slides"]), 3)


class SlideTimingTests(unittest.TestCase):
    def test_step_audio_windows_are_exact(self):
        from pipeline.slide_timing import schedule_from_steps

        schedule = schedule_from_steps(
            ["第一段讲索引。", "第二段讲边界判断。"],
            [3.0, 4.5],
        )
        self.assertEqual(schedule["windows"][0], {"start": 0.0, "end": 3.0})
        self.assertEqual(schedule["windows"][1], {"start": 3.0, "end": 7.5})
        self.assertEqual(schedule["cues"][0]["start"], 0.0)
        self.assertEqual(schedule["cues"][-1]["start"], 3.0)

    def test_code_focus_repair_follows_narration_identifier(self):
        from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator

        plan = {
            "kind": "code",
            "figure": {"lines": ["int a = 1;", "int idx = blockIdx.x * blockDim.x + threadIdx.x;"]},
            "steps": [
                {"heading": "看索引", "focus": [0], "narration": "这里用 blockIdx 和 threadIdx 计算全局索引。"}
            ],
        }
        DeepPedagogicalDeckGenerator._repair_code_focus(plan)
        self.assertEqual(plan["steps"][0]["focus"], [1])

    def test_step_windows_share_cue_boundaries(self):
        from pipeline.slide_timing import build_schedule

        narration = "第一句讲索引。第二句讲边界。第三句讲内存。第四句讲总结。"
        steps = [{"heading": f"step{i}"} for i in range(4)]
        schedule = build_schedule(narration, steps, audio_duration=40.0, pause=2.0)
        windows, cues = schedule["windows"], schedule["cues"]

        self.assertEqual(len(windows), 4)
        self.assertAlmostEqual(windows[0]["start"], 0.0, places=2)
        self.assertAlmostEqual(windows[-1]["end"], 40.0, places=1)
        for prev, nxt in zip(windows, windows[1:]):
            self.assertLessEqual(prev["end"], nxt["start"] + 0.01)

        for window in windows:
            starts = [cue["start"] for cue in cues if abs(cue["start"] - window["start"]) < 0.02]
            self.assertTrue(starts, f"window {window} has no cue starting at its boundary")

        for cue in cues:
            self.assertLess(cue["start"], cue["end"])
            self.assertGreaterEqual(cue["start"], 0.0)
            self.assertLessEqual(cue["end"], 40.05)

    def test_code_focus_line_index_is_preserved(self):
        slide = {
            "slide_id": 1,
            "title": "code",
            "slide_type": "manim_physics_demo",
            "key_points": ["a", "b"],
            "narration_script": "第一句。第二句。" * 5,
            "visual_spec": {},
        }
        plan = normalize_plan(
            {
                "kind": "code",
                "figure": {"lines": ["line0", "line1", "line2"]},
                "steps": [{"heading": "讲 line2", "focus": [2]}],
            },
            slide,
            topic="code",
            duration=8,
        )
        self.assertEqual(plan["steps"][0]["focus"], [2])

    def test_step_partition_keeps_english_words(self):
        from pipeline.slide_timing import build_schedule

        narration = (
            "First we compute the global index using blockIdx. "
            "Then we check the boundary with cudaMemcpyAsync. "
            "Finally we write the result back to global memory."
        )
        steps = [{"heading": "one"}, {"heading": "two"}, {"heading": "three"}]
        schedule = build_schedule(narration, steps, audio_duration=30.0)
        vocabulary = set(re.findall(r"[A-Za-z]+", narration))
        for cue in schedule["cues"]:
            for word in re.findall(r"[A-Za-z]+", cue["text"]):
                self.assertIn(word, vocabulary, f"word split across cues: {word} in {cue['text']!r}")
            self.assertNotIn("\n", cue["text"])

    def test_srt_prefers_explicit_cues(self):
        timeline = {
            "slides": [
                {
                    "slide_id": 1,
                    "start_time": 10.0,
                    "audio_duration": 6.0,
                    "narration": "不该被使用的讲稿。",
                    "cues": [
                        {"start": 10.0, "end": 12.5, "text": "讲第一行代码"},
                        {"start": 12.5, "end": 16.0, "text": "讲第二行代码"},
                    ],
                }
            ],
            "total_video_duration": 16.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = SubtitleEngine.generate_full_srt(timeline, Path(tmp) / "b.srt")
            content = path.read_text(encoding="utf-8")
        self.assertIn("讲第一行代码", content)
        self.assertNotIn("不该被使用", content)
        self.assertIn("00:00:10,000 --> 00:00:12,500", content)


class SpeechTextTests(unittest.TestCase):
    def test_kernel_launch_syntax_is_spoken(self):
        from pipeline.tts_text import normalize_for_speech

        spoken = normalize_for_speech("启动 MyKernel<<<1000,128>>>(p0)，继续执行。")
        self.assertNotIn("<<<", spoken)
        self.assertNotIn(">>>", spoken)
        self.assertIn("启动配置为", spoken)
        self.assertIn("1000", spoken)

    def test_intrinsics_are_spoken(self):
        from pipeline.tts_text import normalize_for_speech

        spoken = normalize_for_speech("在分支内调用 __syncthreads()，并用 blockIdx.x 计算索引。")
        self.assertNotIn("__syncthreads", spoken)
        self.assertIn("同步屏障", spoken)
        self.assertIn("块索引变量的 x 分量", spoken)


class SubtitleTests(unittest.TestCase):
    def test_cues_are_single_line_and_fit_width(self):
        from pipeline.cue_text import estimate_em, segment_cue

        text = "Getting Started Quickly There are many ways to leverage cudaMemcpyAsync in a kernel"
        pieces = segment_cue(text, 24)
        self.assertGreaterEqual(len(pieces), 2)
        for piece in pieces:
            self.assertNotIn("\n", piece)
            self.assertLessEqual(estimate_em(piece), 24.5)
        self.assertTrue(any("cudaMemcpyAsync" in piece for piece in pieces), "identifier was split")

    def test_srt_cues_never_contain_newlines(self):
        timeline = {
            "slides": [
                {
                    "slide_id": 1,
                    "start_time": 0.0,
                    "audio_duration": 8.0,
                    "narration": "这是一段很长的旁白，用来验证字幕每一段都只占一行而不会换行。" * 3,
                }
            ],
            "total_video_duration": 8.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = SubtitleEngine.generate_full_srt(timeline, Path(tmp) / "one.srt")
            content = path.read_text(encoding="utf-8")
        for block in [b for b in content.strip().split("\n\n") if "-->" in b]:
            self.assertEqual(len(block.splitlines()), 3, f"cue is not single-line: {block!r}")

    def test_srt_stays_inside_slide_windows(self):
        timeline = {
            "slides": [
                {
                    "slide_id": 1,
                    "start_time": 0.0,
                    "audio_duration": 3.0,
                    "narration": "第一句。第二句比较长一些。第三句。",
                },
                {
                    "slide_id": 2,
                    "start_time": 5.0,
                    "audio_duration": 4.0,
                    "narration": "第四句。第五句。",
                },
            ],
            "total_video_duration": 9.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = SubtitleEngine.generate_full_srt(timeline, Path(tmp) / "a.srt")
            content = path.read_text(encoding="utf-8")

        def ts(value: str) -> float:
            h, m, rest = value.split(":")
            s, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        blocks = [b for b in content.strip().split("\n\n") if "-->" in b]
        self.assertGreaterEqual(len(blocks), 4)
        for block in blocks:
            start, end = block.splitlines()[1].split(" --> ")
            self.assertLess(ts(start), ts(end))
            self.assertLessEqual(ts(end), 9.05)


class DeepSeekClientTests(unittest.TestCase):
    def test_truncated_json_is_salvaged(self):
        truncated = '{"slides":[{"slide_id":1,"title":"A"},{"slide_id":2,"title":"B"},{"slide_id":3'
        parsed = parse_json_payload(truncated)
        self.assertTrue(parsed.get("__salvaged__"))
        self.assertEqual(len(parsed["slides"]), 2)

    def test_parse_json_with_fence(self):
        self.assertEqual(parse_json_payload('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(parse_json_payload('prefix {"b": 2} suffix'), {"b": 2})

    def test_http_success_and_auth_error(self):
        state = {"mode": "ok"}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                if state["mode"] == "auth":
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'{"error":"bad key"}')
                    return
                body = json.dumps(
                    {"choices": [{"message": {"content": '{"hello":"world"}'}, "finish_reason": "stop"}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/v1"
            client = DeepSeekClient(api_key="test-key", base_url=base, model="mock")
            self.assertEqual(client.chat_json("s", "u"), {"hello": "world"})
            state["mode"] = "auth"
            with self.assertRaises(DeepSeekAuthError):
                client.chat_json("s", "u")
        finally:
            server.shutdown()


def _ffmpeg() -> str | None:
    binary = config.ffmpeg_binary()
    if Path(binary).exists() or shutil.which(str(binary)):
        return str(binary)
    return None


@unittest.skipUnless(_ffmpeg(), "ffmpeg not available")
class VideoBandTests(unittest.TestCase):
    def setUp(self):
        from pipeline.l5_video_composer import VideoComposer

        self.ffmpeg = _ffmpeg()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.composer = VideoComposer()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, cmd):
        subprocess.run(cmd, check=True, capture_output=True)

    def test_normalize_pads_subtitle_band(self):
        src = self.dir / "in.mp4"
        self._run(
            [
                self.ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#123456:s=854x480:r=15:d=1",
                "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(src),
            ]
        )
        out = self.composer.normalize_clip(src, self.dir / "out.mp4", 2.0)
        self.assertIsNotNone(out)

        from pipeline.manim_renderer import probe_video

        info = probe_video(out)
        self.assertEqual((info["width"], info["height"]), (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
        self.assertGreaterEqual(info["duration"], 1.9)

        frame = self.dir / "frame.png"
        self._run([self.ffmpeg, "-y", "-v", "error", "-ss", "1.0", "-i", str(out), "-frames:v", "1", str(frame)])

        from PIL import Image

        image = Image.open(frame).convert("RGB")
        band = image.crop((0, config.CONTENT_HEIGHT, config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
        content = image.crop((0, 0, config.VIDEO_WIDTH, config.CONTENT_HEIGHT))
        self.assertLess(sum(band.convert("L").getdata()) / (band.width * band.height), 12, "band must be black")
        self.assertGreater(sum(content.convert("L").getdata()) / (content.width * content.height), 10, "content missing")

    def test_subtitles_are_burned_only_into_band(self):
        src = self.dir / "in.mp4"
        self._run(
            [
                self.ffmpeg, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=#203040:s=1280x720:r=30:d=2",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(src),
            ]
        )
        srt = self.dir / "sub.srt"
        srt.write_text("1\n00:00:00,200 --> 00:00:01,600\n字幕测试 SUBTITLE\n", encoding="utf-8")
        out = self.composer.burn_subtitles(src, srt, self.dir / "burned.mp4")
        self.assertIsNotNone(out)

        frame = self.dir / "burned.png"
        self._run([self.ffmpeg, "-y", "-v", "error", "-ss", "0.8", "-i", str(out), "-frames:v", "1", str(frame)])

        from PIL import Image

        image = Image.open(frame).convert("RGB")
        band = image.crop((0, config.CONTENT_HEIGHT, config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
        content = image.crop((0, 0, config.VIDEO_WIDTH, config.CONTENT_HEIGHT))
        band_peak = max(band.convert("L").getdata())
        content_peak = max(content.convert("L").getdata())
        self.assertGreater(band_peak, 150, "subtitle text should appear in the band")
        self.assertLess(content_peak, 90, "content area must stay dark/untouched")


class NoFallbackTests(unittest.TestCase):
    def test_missing_key_raises_instead_of_templating(self):
        from pipeline.l2_deep_deck import DeckGenerationError, DeepPedagogicalDeckGenerator

        previous = config.api_key()
        config.set_api_key("")
        try:
            generator = DeepPedagogicalDeckGenerator(api_key="")
            section = {
                "sec_id": "sec_no_key_contract_test",
                "title": "No Key",
                "start_page": 1,
                "end_page": 1,
                "page_count": 1,
                "full_text": "text",
                "paragraphs": ["paragraph"],
                "code_snippets": [],
            }
            with self.assertRaises(DeckGenerationError):
                generator.generate_deck_from_section(section, force=True)
        finally:
            config.set_api_key(previous)


class MockDeepSeekDeckTests(unittest.TestCase):
    """Proves the DeepSeek path is wired end-to-end without needing a real key."""

    def test_deck_is_generated_from_http_response(self):
        narr1 = "先给出全景：本讲要解决的核心问题、原文位置与学习目标。"
        narr2 = "这一步只讲全局索引：blockIdx、blockDim 与 threadIdx 如何合成唯一编号。"
        narr3 = "这一步讲内存层级：寄存器、共享内存与全局内存的延迟差异。"
        narr4 = "这一步讲异步：默认流串行与多流重叠的时间轴区别。"
        narr5 = "最后用三句话收束：索引、边界、内存层级，不重复前文细节。"
        deck_payload = {
            "topic": "Mock 章节",
            "slides": [
                {
                    "slide_id": 1,
                    "title": "全景",
                    "slide_type": "title_overview",
                    "key_points": ["原文位置", "核心问题", "学习目标"],
                    "narration_script": "这是一段用于测试的讲稿。" * 8,
                    "visual_spec": {
                        "layout": "header_and_bullets",
                        "scene_plan": {"kind": "boxes", "steps": [{"heading": "全景", "bullets": ["a"], "focus": [0], "narration": narr1}]},
                    },
                },
                {
                    "slide_id": 2,
                    "title": "索引计算",
                    "slide_type": "manim_physics_demo",
                    "key_points": ["blockIdx", "threadIdx", "边界"],
                    "narration_script": "索引由块与线程共同决定。" * 10,
                    "visual_spec": {
                        "layout": "collision_animation",
                        "code_badge": "int idx = blockIdx.x * blockDim.x + threadIdx.x;",
                        "scene_plan": {"kind": "code", "steps": [{"heading": "读代码", "bullets": ["b"], "focus": [0], "narration": narr2}]},
                    },
                },
                {
                    "slide_id": 3,
                    "title": "内存层级",
                    "slide_type": "concept_breakdown",
                    "key_points": ["寄存器", "共享内存", "全局内存"],
                    "narration_script": "不同层级的延迟差异巨大。" * 10,
                    "visual_spec": {
                        "layout": "header_and_bullets",
                        "scene_plan": {
                            "kind": "grid",
                            "figure": {"rows": 2, "cols": 4, "labels": list("ABCDEFGH")},
                            "steps": [{"heading": "寄存器", "focus": [0], "narration": narr3}],
                        },
                    },
                },
                {
                    "slide_id": 4,
                    "title": "异步",
                    "slide_type": "profiler_timeline",
                    "key_points": ["默认流", "多流", "重叠"],
                    "narration_script": "把时间轴画出来就清楚了。" * 10,
                    "visual_spec": {
                        "layout": "collision_animation",
                        "scene_plan": {
                            "kind": "timeline",
                            "figure": {"rows": [{"label": "S0", "segments": [{"start": 0, "end": 2, "label": "H2D"}]}]},
                            "steps": [{"heading": "默认流", "focus": [0], "narration": narr4}],
                        },
                    },
                },
                {
                    "slide_id": 5,
                    "title": "总结",
                    "slide_type": "summary_best_practice",
                    "key_points": ["索引", "边界", "层级"],
                    "narration_script": "最后收束本节内容。" * 10,
                    "visual_spec": {
                        "layout": "summary_and_checklist",
                        "scene_plan": {"kind": "boxes", "steps": [{"heading": "总结", "focus": [0], "narration": narr5}]},
                    },
                },
            ],
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                body = json.dumps(
                    {"choices": [{"message": {"content": json.dumps(deck_payload, ensure_ascii=False)}, "finish_reason": "stop"}]}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        old = (config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL)
        try:
            config.set_api_key("mock-key")
            config.DEEPSEEK_BASE_URL = f"http://127.0.0.1:{server.server_port}/v1"
            from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator

            section = {
                "sec_id": "sec_mock",
                "title": "Mock 章节",
                "start_page": 1,
                "end_page": 3,
                "page_count": 3,
                "full_text": "text " * 100,
                "paragraphs": ["这是原文段落，用来测试。" * 5],
                "code_snippets": ["int idx = blockIdx.x * blockDim.x + threadIdx.x;"],
            }
            generator = DeepPedagogicalDeckGenerator(api_key="mock-key")
            with tempfile.TemporaryDirectory() as tmp:
                generator.output_dir = Path(tmp)  # keep the repo's output/ clean
                deck = generator.generate_deck_from_section(section, force=True)
            self.assertEqual(deck["source"], "deepseek")
            self.assertEqual(len(deck["slides"]), 5)
            kinds = {s["visual_spec"]["scene_plan"]["kind"] for s in deck["slides"]}
            self.assertGreaterEqual(len(kinds), 3)
            self.assertEqual(deck["slides"][1]["visual_spec"]["code_badge"], section["code_snippets"][0])
            # every slide carries an independent plan
            for slide in deck["slides"]:
                self.assertIn("scene_plan", slide["visual_spec"])
                self.assertGreaterEqual(len(slide["visual_spec"]["scene_plan"]["steps"]), 1)
        finally:
            server.shutdown()
            config.set_api_key(old[0])
            config.DEEPSEEK_BASE_URL = old[1]


if __name__ == "__main__":
    unittest.main(verbosity=2)

