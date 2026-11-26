"""
Multi-Modal Technical Visualization Suite (pipeline/visual_toolbox.py).
Provides rich, zero-dependency visual cards to elucidate complex systems:
1. Code Diff Card (Side-by-side Naive vs Optimized with syntax highlighting & badges)
2. Benchmark Speedup Chart (Dark-themed empirical performance bar chart)
3. Nsight Systems Timeline Trace (Multi-stream concurrency & latency overlap)
4. Hardware Memory Bank Layout (32-Bank Shared Memory conflict detection)
5. Mental Model / Metaphor Whiteboard Card (Intuitive physical analogy)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# Theme Palette (Consistent with NVIDIA & Modern Dark IDEs)
COLOR_BG = (13, 17, 23)          # #0D1117 (Deep Obsidian)
COLOR_CARD_BG = (22, 27, 34)     # #161B22 (Card Surface)
COLOR_PANEL_BG = (30, 36, 46)    # #1E242E (Nested Panel)
COLOR_BORDER = (48, 54, 61)      # #30363D (Border Subtle)
COLOR_NVIDIA = (118, 185, 0)     # #76B900 (NVIDIA Green)
COLOR_BLUE = (88, 166, 255)      # #58A6FF (Accent Blue)
COLOR_RED = (248, 81, 73)        # #F85149 (Conflict/Error Red)
COLOR_YELLOW = (227, 179, 65)    # #E3B341 (Warning/Pending Yellow)
COLOR_PURPLE = (188, 140, 255)   # #BC8CFF (Memory D2H / Accent)
COLOR_TEXT_MAIN = (240, 246, 252)# Pure Light Text
COLOR_TEXT_MUTED = (139, 148, 158)
COLOR_CODE_BG_BAD = (35, 18, 20)
COLOR_CODE_BG_GOOD = (18, 35, 20)


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Helper to load standard Windows YaHei or fallback font."""
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


class VisualToolbox:
    """Generates rich multi-modal visual cards for technical video slides."""

    @staticmethod
    def render_code_diff_card(
        bad_title: str,
        bad_code: List[str],
        bad_tip: str,
        good_title: str,
        good_code: List[str],
        good_tip: str,
        width: int = 1140,
        height: int = 340
    ) -> Image.Image:
        """Renders an impactful 2-column Side-by-Side Code Diff Card."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        col_w = (width - 24) // 2
        font_h = get_font(18, bold=True)
        font_code = get_font(16, bold=False)
        font_tip = get_font(14, bold=False)

        # Left Column: Naive / Bad Code
        left_box = [0, 0, col_w, height]
        draw.rounded_rectangle(left_box, radius=12, fill=COLOR_CODE_BG_BAD, outline=COLOR_RED, width=2)
        # Bad Header
        draw.rounded_rectangle([0, 0, col_w, 42], radius=10, fill=(55, 22, 25))
        draw.text((20, 10), f"❌  {bad_title}", fill=COLOR_RED, font=font_h)

        # Code Lines
        for i, line in enumerate(bad_code[:6]):
            y = 56 + i * 28
            draw.text((15, y), f"{i+1:2d} |", fill=(160, 90, 95), font=font_code)
            draw.text((55, y), line, fill=(255, 180, 185), font=font_code)

        # Bad Tip Banner
        tip_y = height - 42
        draw.rounded_rectangle([10, tip_y, col_w - 10, height - 10], radius=6, fill=(45, 15, 18))
        draw.text((20, tip_y + 6), f"⚠️ {bad_tip}", fill=(255, 140, 145), font=font_tip)

        # Right Column: Optimized / Correct Code
        right_x = col_w + 24
        right_box = [right_x, 0, right_x + col_w, height]
        draw.rounded_rectangle(right_box, radius=12, fill=COLOR_CODE_BG_GOOD, outline=COLOR_NVIDIA, width=2)
        # Good Header
        draw.rounded_rectangle([right_x, 0, right_x + col_w, 42], radius=10, fill=(22, 50, 25))
        draw.text((right_x + 20, 10), f"✅  {good_title}", fill=COLOR_NVIDIA, font=font_h)

        # Code Lines
        for i, line in enumerate(good_code[:6]):
            y = 56 + i * 28
            draw.text((right_x + 15, y), f"{i+1:2d} |", fill=(90, 160, 95), font=font_code)
            draw.text((right_x + 55, y), line, fill=(185, 255, 195), font=font_code)

        # Good Tip Banner
        draw.rounded_rectangle([right_x + 10, tip_y, right_x + col_w - 10, height - 10], radius=6, fill=(18, 45, 22))
        draw.text((right_x + 20, tip_y + 6), f"🚀 {good_tip}", fill=COLOR_NVIDIA, font=font_tip)

        return img

    @staticmethod
    def render_benchmark_chart_card(
        title: str,
        categories: List[str],
        baseline_vals: List[float],
        optimized_vals: List[float],
        metric_unit: str = "吞吐量 (GB/s)",
        speedup_text: str = "8.4x 吞吐跃升",
        width: int = 1140,
        height: int = 340
    ) -> Image.Image:
        """Renders an empirical benchmark comparison bar chart with speedup badge."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background Container
        draw.rounded_rectangle([0, 0, width, height], radius=12, fill=COLOR_PANEL_BG, outline=COLOR_BORDER, width=2)

        font_title = get_font(20, bold=True)
        font_axis = get_font(15, bold=False)
        font_val = get_font(15, bold=True)
        font_badge = get_font(16, bold=True)

        # Header Title
        draw.text((25, 18), f"📊 实测性能基准对比 · {title}", fill=COLOR_TEXT_MAIN, font=font_title)

        # Speedup Badge on Top-Right
        badge_rect = [width - 240, 15, width - 25, 52]
        draw.rounded_rectangle(badge_rect, radius=18, fill=(30, 60, 15), outline=COLOR_NVIDIA, width=2)
        draw.text((width - 225, 22), f"🔥 {speedup_text}", fill=COLOR_NVIDIA, font=font_badge)

        # Chart Axes Area
        chart_x, chart_y = 120, 80
        chart_w, chart_h = width - 180, height - 140

        # Determine Max Value
        max_v = max(max(baseline_vals), max(optimized_vals)) * 1.25
        if max_v <= 0:
            max_v = 100.0

        # Draw Grid Lines
        for step in range(4):
            val = round(max_v * step / 3.0, 1)
            gy = chart_y + chart_h - int(chart_h * (step / 3.0))
            draw.line([chart_x, gy, chart_x + chart_w, gy], fill=(50, 58, 70), width=1)
            draw.text((chart_x - 75, gy - 8), f"{val} ", fill=COLOR_TEXT_MUTED, font=font_axis)

        # Draw Y-axis Unit
        draw.text((25, chart_y - 25), metric_unit, fill=COLOR_BLUE, font=font_axis)

        # Draw Grouped Bars
        n_groups = len(categories)
        group_w = chart_w / n_groups
        bar_w = min(60, int(group_w * 0.28))

        for idx, cat in enumerate(categories):
            gx = chart_x + idx * group_w + group_w * 0.22

            # Baseline Bar (Gray/Red)
            b_val = baseline_vals[idx]
            b_h = int((b_val / max_v) * chart_h)
            b_y = chart_y + chart_h - b_h
            draw.rounded_rectangle([gx, b_y, gx + bar_w, chart_y + chart_h], radius=6, fill=(100, 110, 125))
            draw.text((gx + 4, b_y - 20), f"{b_val}", fill=COLOR_TEXT_MUTED, font=font_val)

            # Optimized Bar (NVIDIA Green)
            o_val = optimized_vals[idx]
            o_h = int((o_val / max_v) * chart_h)
            o_y = chart_y + chart_h - o_h
            draw.rounded_rectangle([gx + bar_w + 14, o_y, gx + bar_w * 2 + 14, chart_y + chart_h], radius=6, fill=COLOR_NVIDIA)
            draw.text((gx + bar_w + 18, o_y - 22), f"{o_val}", fill=COLOR_NVIDIA, font=font_val)

            # Category Label
            cat_x = gx + bar_w - 15
            draw.text((cat_x, chart_y + chart_h + 10), cat, fill=COLOR_TEXT_MAIN, font=font_axis)

        # Legend at Bottom
        leg_y = height - 32
        draw.rectangle([chart_x, leg_y, chart_x + 18, leg_y + 12], fill=(100, 110, 125))
        draw.text((chart_x + 25, leg_y - 2), "朴素实现 (Baseline)", fill=COLOR_TEXT_MUTED, font=font_axis)

        draw.rectangle([chart_x + 220, leg_y, chart_x + 238, leg_y + 12], fill=COLOR_NVIDIA)
        draw.text((chart_x + 245, leg_y - 2), "架构优化版 (Optimized)", fill=COLOR_NVIDIA, font=font_axis)

        return img

    @staticmethod
    def render_nsight_timeline_card(
        title: str = "NVIDIA Nsight Systems 并发与时序追踪 (Trace Timeline)",
        width: int = 1140,
        height: int = 340
    ) -> Image.Image:
        """Renders an authentic Nsight Systems GPU timeline trace showing Stream overlap."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Container
        draw.rounded_rectangle([0, 0, width, height], radius=12, fill=COLOR_PANEL_BG, outline=COLOR_BORDER, width=2)

        font_title = get_font(20, bold=True)
        font_track = get_font(15, bold=True)
        font_bar = get_font(13, bold=True)
        font_axis = get_font(13, bold=False)

        # Title
        draw.text((25, 18), f"⏱️ {title}", fill=COLOR_TEXT_MAIN, font=font_title)

        # Time Axis / Ruler
        ruler_x, ruler_y = 170, 65
        ruler_w = width - 210
        draw.line([ruler_x, ruler_y, ruler_x + ruler_w, ruler_y], fill=(90, 100, 120), width=2)
        ticks = ["0.0ms", "0.5ms", "1.0ms", "1.5ms", "2.0ms", "2.5ms", "3.0ms"]
        for i, t in enumerate(ticks):
            tx = ruler_x + int(ruler_w * (i / (len(ticks) - 1)))
            draw.line([tx, ruler_y - 4, tx, ruler_y + 4], fill=(120, 130, 150), width=1)
            draw.text((tx - 18, ruler_y - 22), t, fill=COLOR_TEXT_MUTED, font=font_axis)

        # Track 1: Default Stream (Sequential Stalling)
        t1_y = 90
        draw.text((25, t1_y + 10), "Stream 0 (默认流):", fill=COLOR_RED, font=font_track)
        # Block 1: Copy H2D
        draw.rounded_rectangle([ruler_x + 10, t1_y, ruler_x + 130, t1_y + 36], radius=6, fill=COLOR_BLUE)
        draw.text((ruler_x + 22, t1_y + 9), "cudaMemcpy(H2D)", fill=COLOR_BG, font=font_bar)
        # Block 2: Kernel (Waiting)
        draw.rounded_rectangle([ruler_x + 135, t1_y, ruler_x + 310, t1_y + 36], radius=6, fill=COLOR_NVIDIA)
        draw.text((ruler_x + 155, t1_y + 9), "Kernel<<<Grid>>>", fill=COLOR_BG, font=font_bar)
        # Block 3: Copy D2H
        draw.rounded_rectangle([ruler_x + 315, t1_y, ruler_x + 435, t1_y + 36], radius=6, fill=COLOR_PURPLE)
        draw.text((ruler_x + 325, t1_y + 9), "cudaMemcpy(D2H)", fill=COLOR_BG, font=font_bar)
        # Stalling notice
        draw.text((ruler_x + 455, t1_y + 9), "❌ 硬件大量时间处于空转气泡等待 (Bubble)", fill=COLOR_RED, font=font_axis)

        # Track 2: Async Stream 1 (Pipelined)
        t2_y = 155
        draw.text((25, t2_y + 10), "Stream 1 (异步):", fill=COLOR_BLUE, font=font_track)
        draw.rounded_rectangle([ruler_x + 10, t2_y, ruler_x + 130, t2_y + 34], radius=6, fill=COLOR_BLUE)
        draw.text((ruler_x + 28, t2_y + 8), "Chunk 0: H2D", fill=COLOR_BG, font=font_bar)
        draw.rounded_rectangle([ruler_x + 135, t2_y, ruler_x + 290, t2_y + 34], radius=6, fill=COLOR_NVIDIA)
        draw.text((ruler_x + 155, t2_y + 8), "Chunk 0: Kernel", fill=COLOR_BG, font=font_bar)
        draw.rounded_rectangle([ruler_x + 295, t2_y, ruler_x + 410, t2_y + 34], radius=6, fill=COLOR_PURPLE)
        draw.text((ruler_x + 310, t2_y + 8), "Chunk 0: D2H", fill=COLOR_BG, font=font_bar)

        # Track 3: Async Stream 2 (Overlapped)
        t3_y = 210
        draw.text((25, t3_y + 10), "Stream 2 (异步):", fill=COLOR_PURPLE, font=font_track)
        draw.rounded_rectangle([ruler_x + 135, t3_y, ruler_x + 255, t3_y + 34], radius=6, fill=COLOR_BLUE)
        draw.text((ruler_x + 152, t3_y + 8), "Chunk 1: H2D", fill=COLOR_BG, font=font_bar)
        draw.rounded_rectangle([ruler_x + 295, t3_y, ruler_x + 450, t3_y + 34], radius=6, fill=COLOR_NVIDIA)
        draw.text((ruler_x + 315, t3_y + 8), "Chunk 1: Kernel", fill=COLOR_BG, font=font_bar)
        draw.rounded_rectangle([ruler_x + 455, t3_y, ruler_x + 570, t3_y + 34], radius=6, fill=COLOR_PURPLE)
        draw.text((ruler_x + 470, t3_y + 8), "Chunk 1: D2H", fill=COLOR_BG, font=font_bar)

        # Overlap Highlight Bracket
        ov_rect = [ruler_x + 135, t2_y - 5, ruler_x + 255, t3_y + 39]
        draw.rectangle(ov_rect, outline=COLOR_YELLOW, width=2)
        font_ov = get_font(13, bold=True)
        draw.text((ruler_x + 265, t3_y + 10), "⚡ 100% PCIe 搬运与 SM 算力时序重叠 (零空闲！)", fill=COLOR_YELLOW, font=font_ov)

        # Summary Banner at Bottom
        draw.rounded_rectangle([25, height - 52, width - 25, height - 12], radius=8, fill=(20, 45, 20), outline=COLOR_NVIDIA, width=1)
        font_sum = get_font(14, bold=False)
        draw.text((40, height - 42), "💡 [Nsight 架构启示] 使用双缓冲/多流异步流水线，将显存搬运耗时完全隐藏在计算之下。", fill=COLOR_NVIDIA, font=font_sum)

        return img

    @staticmethod
    def render_memory_bank_grid_card(
        title: str = "Shared Memory 32-Bank 物理分布与并发冲突探测",
        stride: int = 2,
        width: int = 1140,
        height: int = 340
    ) -> Image.Image:
        """Renders 32-Bank Shared memory layout with conflict detection visual."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle([0, 0, width, height], radius=12, fill=COLOR_PANEL_BG, outline=COLOR_BORDER, width=2)

        font_title = get_font(20, bold=True)
        font_bank = get_font(13, bold=True)
        font_thread = get_font(13, bold=True)
        font_tip = get_font(14, bold=False)

        draw.text((25, 18), f"🗄️ {title}", fill=COLOR_TEXT_MAIN, font=font_title)

        # 16 Bank Slots Display (Bank 0 to 15 for crystal clear rendering)
        num_slots = 16
        slot_w = (width - 120) // num_slots
        slot_y = 110

        draw.text((30, slot_y + 12), "Banks:", fill=COLOR_TEXT_MUTED, font=font_bank)

        for b in range(num_slots):
            bx = 100 + b * slot_w
            # Bank 0 is conflict target if stride is 2 or 4
            is_conflict = (stride > 1 and b == 0)
            col = COLOR_RED if is_conflict else COLOR_BLUE
            bg_col = (55, 20, 25) if is_conflict else (20, 32, 50)

            draw.rounded_rectangle([bx, slot_y, bx + slot_w - 6, slot_y + 45], radius=6, fill=bg_col, outline=col, width=2)
            draw.text((bx + 6, slot_y + 12), f"B{b}", fill=col, font=font_bank)

        # Thread Access Mapping (Threads 0 to 7)
        t_y = 200
        draw.text((30, t_y + 8), "Threads:", fill=COLOR_TEXT_MUTED, font=font_thread)

        for t in range(8):
            target_bank = (t * stride) % num_slots
            tx = 100 + t * (slot_w * 2)
            bx = 100 + target_bank * slot_w + (slot_w // 2) - 3

            is_bad = (stride > 1 and target_bank == 0 and t > 0)
            t_col = COLOR_RED if is_bad else COLOR_NVIDIA

            draw.ellipse([tx, t_y, tx + 34, t_y + 34], fill=(20, 45, 20) if not is_bad else (50, 20, 20), outline=t_col, width=2)
            draw.text((tx + 7, t_y + 8), f"T{t}", fill=t_col, font=font_thread)

            # Arrow to Target Bank
            draw.line([tx + 17, t_y, bx, slot_y + 45], fill=t_col, width=2)

        # Conflict Banner
        if stride > 1:
            draw.rounded_rectangle([25, height - 60, width - 25, height - 15], radius=8, fill=(50, 18, 22), outline=COLOR_RED, width=2)
            draw.text((40, height - 48), f"⚠️ [严重冲突] 跨步 Stride={stride}: 线程 T0 与 T{num_slots // stride if num_slots // stride < 8 else 8} 同时并发命中 Bank 0！硬件被迫串行排队降速！", fill=COLOR_RED, font=font_tip)
        else:
            draw.rounded_rectangle([25, height - 60, width - 25, height - 15], radius=8, fill=(20, 45, 20), outline=COLOR_NVIDIA, width=1)
            draw.text((40, height - 48), "✅ [完美无冲突] 跨步 Stride=1: 线程与 Bank 实现 1 对 1 物理独占，100% 满带宽并发执行！", fill=COLOR_NVIDIA, font=font_tip)

        return img

    @staticmethod
    def render_metaphor_sketch_card(
        metaphor_title: str,
        analogy_bullets: List[str],
        punchline: str,
        width: int = 1140,
        height: int = 340
    ) -> Image.Image:
        """Renders an intuitive whiteboard mental model analogy card."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Whiteboard aesthetic container
        draw.rounded_rectangle([0, 0, width, height], radius=14, fill=(24, 28, 36), outline=(90, 110, 140), width=2)

        font_title = get_font(22, bold=True)
        font_bullet = get_font(17, bold=False)
        font_punch = get_font(18, bold=True)

        # Top Badge & Title
        draw.rounded_rectangle([25, 20, 180, 52], radius=10, fill=(38, 55, 80))
        draw.text((38, 26), "💡 [心智模型比喻]", fill=COLOR_BLUE, font=get_font(15, bold=True))
        draw.text((195, 25), metaphor_title, fill=COLOR_TEXT_MAIN, font=font_title)

        # Bullets
        y = 75
        for b in analogy_bullets[:4]:
            draw.text((35, y), "✏️", fill=COLOR_YELLOW, font=font_bullet)
            draw.text((70, y), b, fill=(225, 232, 240), font=font_bullet)
            y += 42

        # Punchline Banner
        draw.rounded_rectangle([25, height - 65, width - 25, height - 18], radius=8, fill=(35, 45, 20), outline=COLOR_NVIDIA, width=2)
        draw.text((40, height - 52), f"🎯 核心心智升华: {punchline}", fill=COLOR_NVIDIA, font=font_punch)

        return img
