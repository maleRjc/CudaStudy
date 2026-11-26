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
        """
        Draws a clean, professional slide card image with a dedicated subtitle safe zone.
        No content ever enters the bottom 88px reserved exclusively for burnt-in subtitles.
        """
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        # 1. Main Slide Content Container (Strictly bounded above y=630)
        margin_x = 50
        card_rect = [margin_x, 15, width - margin_x, 626]
        draw.rounded_rectangle(card_rect, radius=14, fill=COLOR_CARD, outline=COLOR_BORDER, width=2)

        # 2. Dedicated Subtitle Safe Strip at Bottom (y=632 to 720)
        draw.rectangle([0, 632, width, height], fill=(9, 12, 16))
        draw.line([0, 632, width, 632], fill=(35, 42, 54), width=1)

        # Fonts
        font_badge = get_system_font(15, bold=True)
        font_title = get_system_font(26, bold=True)
        font_topic = get_system_font(15, bold=False)
        font_digest = get_system_font(13, bold=False)
        font_bullet = get_system_font(19, bold=False)
        font_code = get_system_font(17, bold=True)

        slide_id = slide.get("slide_id", 1)
        s_type = slide.get("slide_type", "概念精讲")
        title = slide.get("title", f"Slide {slide_id}")

        # Top Badge
        badge_text = f"  Slide {slide_id} · {s_type}  "
        badge_w = len(badge_text) * 9 + 10
        draw.rounded_rectangle([margin_x + 30, 26, margin_x + 30 + badge_w, 52], radius=10, fill=(28, 45, 15), outline=COLOR_ACCENT, width=1)
        draw.text((margin_x + 36, 31), badge_text, fill=COLOR_ACCENT, font=font_badge)

        # Title & Topic
        draw.text((margin_x + 30, 58), title, fill=COLOR_BLUE, font=font_title)
        draw.text((margin_x + 30, 96), f"《CUDA C++ Programming Guide》专题：{topic}", fill=COLOR_TEXT_MUTED, font=font_topic)

        # Compact Schema & Cognitive Digestion Pill below header
        digest_pill = [margin_x + 30, 122, width - margin_x - 30, 150]
        draw.rounded_rectangle(digest_pill, radius=6, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
        digest_hint = "💡 [认知图式沉淀] 请对照板书理解核心心智模型，把握其与 CPU 串行执行的本质区别"
        draw.text((margin_x + 45, 128), digest_hint, fill=(147, 197, 253), font=font_digest)

        # Divider
        draw.line([margin_x + 30, 158, width - margin_x - 30, 158], fill=COLOR_BORDER, width=1)

        # 3. Middle Visual Area (y=168 to 618)
        cursor_y = 168
        card_w = width - 2 * margin_x - 60
        card_h = 440

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
            img.paste(special_card, (margin_x + 30, cursor_y), special_card)
        else:
            # Code Badge if exists
            code = visual.get("code_badge", "")
            if code:
                code_lines = [c for c in code.split("\n") if c.strip()][:4]
                code_h = len(code_lines) * 30 + 20
                draw.rounded_rectangle([margin_x + 30, cursor_y, width - margin_x - 30, cursor_y + code_h], radius=10, fill=COLOR_CODE_BG, outline=COLOR_BORDER, width=1)
                for i, line in enumerate(code_lines):
                    draw.text((margin_x + 48, cursor_y + 10 + i * 30), line, fill=COLOR_CODE_TEXT, font=font_code)
                cursor_y += code_h + 20

            # Bullet Points
            key_points = slide.get("key_points", [])
            for pt in key_points:
                draw.text((margin_x + 35, cursor_y), "●", fill=COLOR_ACCENT, font=font_bullet)
                draw.text((margin_x + 65, cursor_y), pt, fill=COLOR_TEXT_MAIN, font=font_bullet)
                cursor_y += 42

        img_path = self.output_dir / f"slide_{slide_id}.png"
        img.save(img_path)
        return img_path


    def create_slide_video_clip(self, slide_img_path: Path, audio_path: Path, output_clip_path: Path, duration: float) -> Optional[Path]:
        """
        Combines single slide image + speech audio into a synchronized MP4 video clip.
        Pads audio stream with silence using apad filter to ensure audio and video durations match 100%.
        """
        dur_str = f"{duration:.3f}"
        cmd = [
            str(self.ffmpeg_bin),
            "-y",
            "-loop", "1",
            "-i", str(slide_img_path),
            "-i", str(audio_path),
            "-af", f"apad=whole_dur={dur_str}",
            "-t", dur_str,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "192k",
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
