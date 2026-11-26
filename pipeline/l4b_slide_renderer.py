"""
Layer 4B: Graphic Slide Renderer (PPT Slide to High-Res Video Track).
Renders structured PPT lecture slides into high-resolution visual video clips (1080p/720p).
Combines:
- Modern dark-themed slide card layout
- Topic title & slide badge
- Highlighted code block with syntax container
- Bullet points with icons
- Realtime slide video duration matched to speech audio
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.visual_toolbox import VisualToolbox


# Colors
COLOR_BG = (13, 17, 23)        # #0D1117
COLOR_CARD = (22, 27, 34)      # #161B22
COLOR_BORDER = (48, 54, 61)    # #30363D
COLOR_ACCENT = (118, 185, 0)   # #76B900 (NVIDIA Green)
COLOR_BLUE = (88, 166, 255)    # #58A6FF
COLOR_TEXT_MAIN = (240, 246, 252)
COLOR_TEXT_MUTED = (139, 148, 158)
COLOR_CODE_BG = (9, 13, 19)
COLOR_CODE_TEXT = (126, 231, 135)


def get_system_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Gets standard Microsoft YaHei or fallback font."""
    font_names = [
        "msyhbd.ttc" if bold else "msyh.ttc",
        "simhei.ttf",
        "arial.ttf"
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    return ImageFont.load_default()


class SlideVideoRenderer:
    """Renders structured slide deck items into slide video clips."""

    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "slide_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = config.BASE_DIR / ".venv" / "Scripts" / "ffmpeg.exe"

    def render_slide_image(self, slide: Dict[str, Any], topic: str, width: int = 1280, height: int = 720) -> Path:
        """Draws a clean, professional slide card image."""
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Main Card Container
        margin_x, margin_y = 60, 45
        card_rect = [margin_x, margin_y, width - margin_x, height - margin_y]
        draw.rounded_rectangle(card_rect, radius=16, fill=COLOR_CARD, outline=COLOR_BORDER, width=2)

        # Header Title & Badge
        font_badge = get_system_font(18, bold=True)
        font_title = get_system_font(30, bold=True)
        font_topic = get_system_font(18, bold=False)
        font_bullet = get_system_font(22, bold=False)
        font_code = get_system_font(20, bold=True)

        slide_id = slide.get("slide_id", 1)
        s_type = slide.get("slide_type", "概念精讲")
        title = slide.get("title", f"Slide {slide_id}")

        badge_text = f"  Slide {slide_id} · {s_type}  "
        draw.rounded_rectangle([margin_x + 35, margin_y + 30, margin_x + 35 + len(badge_text) * 11, margin_y + 60], radius=12, fill=(28, 45, 15), outline=COLOR_ACCENT, width=1)
        draw.text((margin_x + 42, margin_y + 35), badge_text, fill=COLOR_ACCENT, font=font_badge)

        draw.text((margin_x + 35, margin_y + 75), title, fill=COLOR_BLUE, font=font_title)
        draw.text((margin_x + 35, margin_y + 125), f"《CUDA C++ Programming Guide》专题：{topic}", fill=COLOR_TEXT_MUTED, font=font_topic)

        # Divider
        draw.line([margin_x + 35, margin_y + 155, width - margin_x - 35, margin_y + 155], fill=COLOR_BORDER, width=2)

        # Check Multi-Modal Slide Types
        cursor_y = margin_y + 170
        card_w = width - 2 * margin_x - 70
        card_h = height - margin_y - 250

        visual = slide.get("visual_spec", {})
        special_card = None

        if s_type == "code_diff":
            bad_code = visual.get("bad_code", [
                "int idx = threadIdx.x; // 错误：多块严重冲突",
                "d_out[idx] = input[idx] * 2.0f;"
            ])
            good_code = visual.get("good_code", [
                "int idx = blockIdx.x * blockDim.x + threadIdx.x;",
                "if (idx < N) { d_out[idx] = input[idx] * 2.0f; }"
            ])
            special_card = VisualToolbox.render_code_diff_card(
                bad_title=visual.get("bad_title", "朴素实现 / 隐患反例"),
                bad_code=bad_code,
                bad_tip=visual.get("bad_tip", "缺少块偏移升维或边界判断"),
                good_title=visual.get("good_title", "工业级安全规范实现"),
                good_code=good_code,
                good_tip=visual.get("good_tip", "全网格线性寻址并包含边界防护"),
                width=card_w,
                height=card_h
            )
        elif s_type == "benchmark_chart":
            special_card = VisualToolbox.render_benchmark_chart_card(
                title=visual.get("chart_title", "算力与显存吞吐实测对比"),
                categories=visual.get("categories", ["Small", "Medium", "Large"]),
                baseline_vals=visual.get("baseline_vals", [110.0, 240.0, 320.0]),
                optimized_vals=visual.get("optimized_vals", [880.0, 1920.0, 2750.0]),
                metric_unit=visual.get("metric_unit", "吞吐量 (GB/s)"),
                speedup_text=visual.get("speedup_text", "8.5x 性能跃升"),
                width=card_w,
                height=card_h
            )
        elif s_type == "profiler_timeline":
            special_card = VisualToolbox.render_nsight_timeline_card(
                title=visual.get("timeline_title", "NVIDIA Nsight Systems 并发与时序追踪 (Trace Timeline)"),
                width=card_w,
                height=card_h
            )
        elif s_type == "memory_layout":
            special_card = VisualToolbox.render_memory_bank_grid_card(
                title=visual.get("bank_title", "Shared Memory 32-Bank 物理分布与并发冲突探测"),
                stride=visual.get("stride", 2),
                width=card_w,
                height=card_h
            )
        elif s_type == "metaphor_sketch":
            bullets = slide.get("key_points", [
                "把庞大并发任务比作日常生活中的真实场景",
                "消除抽象硬件术语，建立直观的物理第一性原理"
            ])
            special_card = VisualToolbox.render_metaphor_sketch_card(
                metaphor_title=visual.get("metaphor_title", title),
                analogy_bullets=bullets,
                punchline=visual.get("punchline", "从物理本质理解并发调度，知其然更知其所以然"),
                width=card_w,
                height=card_h
            )

        if special_card:
            img.paste(special_card, (margin_x + 35, cursor_y), special_card)
        else:
            # Code Badge if exists
            code = visual.get("code_badge", "")
            if code:
                code_lines = [c for c in code.split("\n") if c.strip()][:4]
                code_h = len(code_lines) * 32 + 25
                draw.rounded_rectangle([margin_x + 35, cursor_y, width - margin_x - 35, cursor_y + code_h], radius=10, fill=COLOR_CODE_BG, outline=COLOR_BORDER, width=1)
                for i, line in enumerate(code_lines):
                    draw.text((margin_x + 55, cursor_y + 12 + i * 32), line, fill=COLOR_CODE_TEXT, font=font_code)
                cursor_y += code_h + 20

            # Bullet Points
            key_points = slide.get("key_points", [])
            for pt in key_points:
                draw.text((margin_x + 40, cursor_y), "●", fill=COLOR_ACCENT, font=font_bullet)
                draw.text((margin_x + 70, cursor_y), pt, fill=COLOR_TEXT_MAIN, font=font_bullet)
                cursor_y += 44


        # Deliberate Digestion & Schema Consolidation Banner at Bottom
        digest_rect = [margin_x + 35, height - margin_y - 60, width - margin_x - 35, height - margin_y - 20]
        draw.rounded_rectangle(digest_rect, radius=8, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
        font_digest = get_system_font(15, bold=False)
        digest_hint = "💡 [认知沉淀 · 消化思考] 请对照板书理解核心心智模型，思考其与 CPU 串行设计的本质区别"
        draw.text((margin_x + 55, height - margin_y - 48), digest_hint, fill=(147, 197, 253), font=font_digest)

        img_path = self.output_dir / f"slide_{slide_id}.png"
        img.save(img_path)
        return img_path

    def create_slide_video_clip(self, slide_img_path: Path, audio_path: Path, output_clip_path: Path, duration: float) -> Optional[Path]:
        """Combines single slide image + speech audio into a synchronized MP4 video clip."""
        cmd = [
            str(self.ffmpeg_bin),
            "-y",
            "-loop", "1",
            "-i", str(slide_img_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            str(output_clip_path)
        ]

        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            startupinfo=startupinfo
        )

        if proc.returncode == 0 and output_clip_path.exists():
            return output_clip_path
        else:
            print(f"[!] Slide video clip creation failed: {proc.stderr[-300:]}")
            return None
