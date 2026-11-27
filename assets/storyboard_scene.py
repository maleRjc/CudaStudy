"""
High-contrast, data-driven Manim renderer for CudaStudy storyboards (v2).

Design goals:
- never look "dark and empty": white type on deep navy, bright accent fills,
  large panels and wide composition (1280x632 content area).
- concept-specific figures for the CUDA mental models that matter:
  warp divergence, shared-memory bank conflicts, memory coalescing, tiled GEMM.
- continuous motion during narration: each phase cross-fades to a new figure
  state, then breathes/pulses instead of freezing.
- deterministic: it renders a JSON plan, never LLM-written Python.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from manim import *  # noqa: F401,F403

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from assets.styles import *  # noqa: F401,F403
from assets.cuda_manim_lib import CUDAThemeScene

_FONT = "Microsoft YaHei" if sys.platform == "win32" else None

L_X, R_X = -6.75, 6.75
T_Y, B_Y = 3.42, -3.42

BG = "#05080D"
PANEL = "#0E1621"
PANEL_2 = "#14202E"
BORDER = "#2C3E50"
WHITE = "#FFFFFF"
DIM = "#B6C6D8"
CYAN = "#22D3EE"
GREEN = "#A3E635"
NV = "#76B900"
AMBER = "#FBBF24"
RED = "#FF5D73"
MAGENTA = "#F472B6"
VIOLET = "#A78BFA"

SPLIT_KINDS = {"warp", "banks", "coalesce", "grid", "boxes"}
FULL_KINDS = {"timeline", "code", "compare", "bars", "matrix"}
KIND_METRIC = {
    "warp": ("32", "threads / warp"),
    "banks": ("32", "banks / SM"),
    "coalesce": ("128B", "per transaction"),
    "matrix": ("TILE", "on-chip reuse"),
    "grid": ("1D", "global index"),
    "boxes": ("→", "data flow"),
    "timeline": ("2×", "streams overlap"),
    "code": ("1", "line at a time"),
    "compare": ("A/B", "wrong vs right"),
    "bars": ("×", "measured"),
}


def T(text, size=16, color=WHITE, weight=NORMAL, **kwargs):
    if _FONT:
        return Text(text, font=_FONT, font_size=size, color=color, weight=weight, **kwargs)
    return Text(text, font_size=size, color=color, weight=weight, **kwargs)


def fit(mobject, max_width: float, max_height: float | None = None):
    if max_width and mobject.width > max_width and mobject.width > 0:
        mobject.scale_to_fit_width(max_width)
    if max_height and mobject.height > max_height and mobject.height > 0:
        mobject.scale_to_fit_height(max_height)
    return mobject


def panel_rect(width: float, height: float, color=PANEL, stroke=BORDER, radius=0.12):
    return RoundedRectangle(
        corner_radius=radius,
        width=width,
        height=height,
        color=stroke,
        fill_color=color,
        fill_opacity=1.0,
        stroke_width=1.6,
    )


class StoryboardScene(CUDAThemeScene):
    """Renders one slide from a JSON plan."""

    PLAN: dict = {}

    # ------------------------------------------------------------------
    def construct(self):
        self.camera.background_color = BG
        plan = self.PLAN if isinstance(self.PLAN, dict) else {}
        self.plan = plan
        self.kind = str(plan.get("kind") or "boxes")
        self.steps = plan.get("steps") or [{"heading": plan.get("title", ""), "bullets": [], "focus": []}]
        self.plan_duration = float(plan.get("duration") or 8.0)
        self.split_layout = self.kind in SPLIT_KINDS
        self._current_focus = []

        self._build_header(plan)
        self._build_stage()
        self._build_progress()
        self._play_steps()

    # ------------------------------------------------------------------
    def _build_header(self, plan):
        title = fit(T(plan.get("title") or "CUDA", 32, WHITE, BOLD), 10.4)
        title.move_to([L_X + title.width / 2 + 0.05, 3.0, 0])
        self.add(title)

        subtitle = str(plan.get("subtitle") or "").strip()
        if subtitle:
            sub = fit(T(subtitle, 16, CYAN), 9.6)
            sub.next_to(title, DOWN, buff=0.08)
            sub.align_to(title, LEFT)
            self.add(sub)

        badge_text = f"SLIDE {plan.get('slide_id', '')}  ·  {self.kind.upper()}".replace("  ·  ", " · ")
        badge = T(badge_text.strip(), 13, NV, BOLD)
        badge.move_to([R_X - badge.width / 2 - 0.05, 3.02, 0])
        self.add(badge)

        self.add(Line([L_X, 2.48, 0], [R_X, 2.48, 0], color=BORDER, stroke_width=2))

    def _build_stage(self):
        """A subtle elevated panel behind the diagram: separates it from the void."""
        if self.split_layout:
            rect = panel_rect(8.05, 3.42, PANEL, BORDER)
            rect.move_to([2.35, -0.02, 0])
            accent = Line([2.35 - 4.025, 1.67, 0], [2.35 - 4.025, -1.71, 0], color=CYAN, stroke_width=3)
        else:
            rect = panel_rect(13.0, 3.42, PANEL, BORDER)
            rect.move_to([0, -0.02, 0])
            accent = Line([-6.5, 1.67, 0], [-5.6, 1.67, 0], color=CYAN, stroke_width=3)
        self.add(rect, accent)

        glow = RoundedRectangle(
            corner_radius=0.12,
            width=rect.width,
            height=rect.height,
            color=CYAN,
            fill_opacity=0.0,
            stroke_width=2.0,
            stroke_opacity=0.0,
        ).move_to(rect.get_center())
        self.stage_glow = glow
        self.stage_rect = rect
        self.add(glow)

        scan = Line(
            [rect.get_left()[0] + 0.08, rect.get_center()[1] - rect.height / 2 + 0.05, 0],
            [rect.get_left()[0] + 0.08, rect.get_center()[1] + rect.height / 2 - 0.05, 0],
            color=CYAN,
            stroke_width=2.0,
            stroke_opacity=0.0,
        )
        self.scan_line = scan
        self.add(scan)

    def _build_progress(self):
        self.progress_dots = VGroup()
        count = max(1, len(self.steps))
        for idx in range(count):
            dot = Circle(radius=0.045, color=BORDER, fill_color=BORDER, fill_opacity=1)
            self.progress_dots.add(dot)
        self.progress_dots.arrange(RIGHT, buff=0.12).move_to([L_X + 0.35, -3.15, 0])
        self.add(self.progress_dots)
        self.progress_ratio = 0.0
        self.progress_line = Line([L_X + 0.8, -3.15, 0], [R_X, -3.15, 0], color="#1A2634", stroke_width=2)
        self.add(self.progress_line)

    def _advance(self, ratio: float, index: int):
        ratio = max(0.0, min(1.0, ratio))
        if ratio > self.progress_ratio:
            target = Line(
                [L_X + 0.8, -3.15, 0],
                [L_X + 0.8 + (R_X - L_X - 0.8) * ratio, -3.15, 0],
                color=GREEN,
                stroke_width=2.5,
            )
            self.play(Transform(self.progress_line, target), run_time=0.3)
            self.progress_ratio = ratio
        if 0 <= index < len(self.progress_dots):
            self.progress_dots[index].set_fill(CYAN, opacity=1).set_stroke(CYAN, 1)

    # ------------------------------------------------------------------
    def _play_steps(self):
        windows = self.plan.get("windows") or []
        count = max(1, len(self.steps))
        overhead = 0.5 + count * (0.4 + 0.25)
        per_step = max(1.0, (self.plan_duration - overhead) / count)

        current = VGroup()
        first = True
        for idx, step in enumerate(self.steps):
            if idx < len(windows) and isinstance(windows[idx], dict):
                window_start = float(windows[idx].get("start", 0.0))
                window_end = float(windows[idx].get("end", window_start + per_step))
            else:
                window_start = idx * per_step
                window_end = window_start + per_step

            self._wait_until(window_start)

            self._current_focus = step.get("focus") or []
            figure = self._build_figure(idx)
            figure.move_to(self._figure_center())
            text_group = self._build_step_text(step, idx)
            new_group = VGroup(figure, text_group)

            if first:
                self.play(FadeIn(new_group, shift=UP * 0.08), run_time=0.4)
                first = False
            else:
                self.play(
                    FadeOut(current, shift=DOWN * 0.05),
                    FadeIn(new_group, shift=UP * 0.05),
                    run_time=0.2,
                )

            current = new_group
            self._advance((idx + 1) / count, idx)
            self._ambient_until(window_end)

        self._wait_until(self.plan_duration)
        self.wait(0.1)

    def _wait_until(self, target: float):
        remaining = float(target) - float(self.renderer.time)
        if remaining > 0.02:
            self.wait(remaining)

    def _ambient_until(self, end: float):
        """Pulse/scan while waiting; never cross the window end."""
        while self.renderer.time < end - 1.5:
            self.wait(1.1)
            try:
                self.play(self.stage_glow.animate.set_stroke(opacity=0.4), run_time=0.3)
                left = self.stage_rect.get_left()[0] + 0.08
                right = self.stage_rect.get_right()[0] - 0.08
                self.scan_line.move_to([left, self.stage_rect.get_center()[1], 0])
                self.play(
                    self.scan_line.animate.move_to([right, self.stage_rect.get_center()[1], 0]).set_stroke(opacity=0.35),
                    run_time=0.7,
                )
                self.play(
                    self.scan_line.animate.set_stroke(opacity=0.0),
                    self.stage_glow.animate.set_stroke(opacity=0.0),
                    run_time=0.25,
                )
            except Exception:
                break
        self._wait_until(end)

    def _figure_center(self):
        if self.split_layout:
            return [2.4, 0.0, 0]
        return [0, 0.0, 0]

    def _figure_box(self):
        if self.split_layout:
            return (7.9, 3.3)
        return (12.7, 3.3)

    # ------------------------------------------------------------------
    def _build_step_text(self, step, index):
        heading = str(step.get("heading") or f"Step {index + 1}")
        bullets = [str(b) for b in (step.get("bullets") or []) if str(b).strip()][:2]

        if self.split_layout:
            group = VGroup()
            head = fit(T(heading, 23, WHITE, BOLD), 4.1)
            head.move_to([-4.35, 1.45, 0])
            group.add(head)
            y = 0.85
            for bullet in bullets:
                shown = bullet if len(bullet) <= 30 else bullet[:29].rstrip() + "…"
                item = T("▍ " + shown, 16, DIM)
                if item.width > 4.1:
                    item = fit(item, 4.1)
                item.move_to([-4.35, y, 0])
                item.align_to(head, LEFT)
                y -= max(0.52, item.height + 0.18)
                group.add(item)

            metric_value, metric_label = KIND_METRIC.get(self.kind, ("", ""))
            if self.kind == "grid":
                labels = (self.plan.get("figure") or {}).get("labels") or []
                is_2d = any("," in str(label) or "，" in str(label) for label in labels)
                metric_value = "2D" if is_2d else "1D"
                metric_label = "grid index"
            if metric_value:
                big = T(metric_value, 54, GREEN, BOLD)
                big.move_to([-4.75, -1.35, 0])
                lab = fit(T(metric_label, 14, DIM), 4.0)
                lab.next_to(big, DOWN, buff=0.08)
                group.add(big, lab)

            accent = Line([-6.5, 1.8, 0], [-6.5, 0.4, 0], color=CYAN, stroke_width=3)
            group.add(accent)
            return group

        group = VGroup()
        head = fit(T(heading, 25, WHITE, BOLD), 11.8)
        head.move_to([0, 1.95, 0])
        group.add(head)
        y = -2.15
        for bullet in bullets:
            shown = bullet if len(bullet) <= 40 else bullet[:39].rstrip() + "…"
            item = fit(T(shown, 18, DIM), 11.4)
            item.move_to([0, y, 0])
            y -= 0.42
            group.add(item)
        return group

    # ==================================================================
    # Figures
    # ==================================================================
    def _build_figure(self, step_index):
        fig = self.plan.get("figure") or {}
        builder = getattr(self, f"_fig_{self.kind}", None) or self._fig_boxes
        try:
            group = builder(fig, step_index)
        except Exception:
            group = self._fig_boxes({}, step_index)
        max_w, max_h = self._figure_box()
        fit(group, max_w, max_h)
        # Fill the stage instead of leaving the diagram small in a dark void.
        if group.width > 0 and group.height > 0:
            scale = min(max_w / group.width, max_h / group.height) * 0.94
            if scale > 1.0:
                group.scale(min(scale, 1.32))
        return group

    # -- generic helpers -------------------------------------------------
    def _cell(self, label, size, active=True, accent=CYAN, text_size=18):
        box = RoundedRectangle(
            corner_radius=0.07,
            width=size * 1.35,
            height=size,
            color=accent if active else "#42566C",
            fill_color=PANEL_2 if active else "#1A2430",
            fill_opacity=1.0,
            stroke_width=2.0 if active else 1.4,
        )
        text = T(str(label), text_size, WHITE if active else "#9FB2C6", BOLD)
        fit(text, size * 1.15)
        text.move_to(box.get_center())
        return VGroup(box, text)

    # -- grid ------------------------------------------------------------
    def _fig_grid(self, fig, phase):
        rows = max(1, min(int(fig.get("rows") or 4), 8))
        cols = max(1, min(int(fig.get("cols") or 8), 12))
        labels = list(fig.get("labels") or [])
        group = VGroup()
        focus = self._current_focus or []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if focus:
                    active = idx in focus
                else:
                    active = idx < 8 if phase == 0 else (idx % cols) in (0, 1) if phase == 1 else True
                cell = self._cell(labels[idx] if idx < len(labels) else idx, 0.56, active=active)
                group.add(cell)
            group.add(VGroup())  # row separator group
        rows_group = VGroup()
        cells = [m for m in group if isinstance(m, VGroup) and len(m) == 2]
        for i in range(0, len(cells), cols):
            row = VGroup(*cells[i:i + cols])
            row.arrange(RIGHT, buff=0.14)
            rows_group.add(row)
        rows_group.arrange(DOWN, buff=0.16)
        return rows_group

    # -- boxes -----------------------------------------------------------
    def _fig_boxes(self, fig, phase):
        nodes = fig.get("nodes") or [{"id": "a", "label": "Host"}, {"id": "b", "label": "Device"}]
        edges = fig.get("edges") or []
        count = max(1, len(nodes))
        box_w = min(2.25, 7.6 / count - 0.25)
        box_h = 1.0

        node_layer = VGroup()
        positions = {}
        focus = self._current_focus or []
        for idx, node in enumerate(nodes):
            x = 0 if count == 1 else -3.6 + idx * (box_w + 0.55)
            active = idx in focus if focus else idx == phase % count
            box = panel_rect(box_w, box_h, PANEL_2, CYAN if active else BORDER)
            box.move_to([x, 0, 0])
            label = fit(T(str(node.get("label", ""))[:16], 15, WHITE, BOLD), box_w * 0.88)
            label.move_to(box.get_center())
            node_layer.add(VGroup(box, label))
            positions[str(node.get("id"))] = (x, idx)

        def chip(text, position):
            label = T(text[:12], 11, DIM)
            bg = RoundedRectangle(
                corner_radius=0.05,
                width=label.width + 0.22,
                height=label.height + 0.12,
                color=BORDER,
                fill_color=PANEL,
                fill_opacity=1.0,
                stroke_width=1.0,
            )
            return VGroup(bg, label).move_to(position)

        arrow_layer = VGroup()
        label_layer = VGroup()
        for edge in edges:
            if not isinstance(edge, (list, tuple)) or len(edge) < 2:
                continue
            sid, eid = str(edge[0]), str(edge[1])
            if sid not in positions or eid not in positions:
                continue
            xi, i = positions[sid]
            xj, j = positions[eid]
            if i == j:
                continue

            if j == i + 1:
                start = [xi + box_w / 2 + 0.08, 0, 0]
                end = [xj - box_w / 2 - 0.08, 0, 0]
                arrow = Arrow(
                    start, end, color=CYAN, buff=0.0,
                    stroke_width=2.4, max_tip_length_to_length_ratio=0.16,
                )
                label_pos = [(start[0] + end[0]) / 2, 0.82, 0]
            elif j > i:
                # Skip over intermediate nodes instead of cutting through them.
                start = [xi + box_w / 2, 0.28, 0]
                end = [xj - box_w / 2, 0.28, 0]
                arrow = CurvedArrow(start, end, angle=-0.85, color=CYAN, stroke_width=2.2, tip_length=0.16)
                label_pos = arrow.point_from_proportion(0.5) + UP * 0.2
            else:
                # Backward edge: route below the row.
                start = [xi - box_w / 2, -0.28, 0]
                end = [xj + box_w / 2, -0.28, 0]
                arrow = CurvedArrow(start, end, angle=0.85, color=AMBER, stroke_width=2.2, tip_length=0.16)
                label_pos = arrow.point_from_proportion(0.5) + DOWN * 0.2

            arrow_layer.add(arrow)
            if len(edge) > 2 and str(edge[2]).strip():
                label_layer.add(chip(str(edge[2]).strip(), label_pos))

        # Arrows below nodes; labels above everything.
        arrow_layer.set_z_index(0)
        node_layer.set_z_index(2)
        label_layer.set_z_index(3)
        return VGroup(arrow_layer, node_layer, label_layer)

    # -- warp ------------------------------------------------------------
    def _fig_warp(self, fig, phase):
        phase = min(int(phase), 3)
        group = VGroup()
        cells = VGroup()
        alternating = phase in (1, 2)
        for idx in range(32):
            if phase == 1:
                active = idx % 2 == 0
                accent = CYAN
            elif phase == 2:
                active = idx % 2 == 1
                accent = MAGENTA
            elif phase == 3:
                active = True
                accent = GREEN
            else:
                active = True
                accent = CYAN
            cell = self._cell(idx, 0.5, active=active, accent=accent, text_size=15)
            cells.add(cell)
        rows = VGroup()
        for i in range(4):
            row = VGroup(*cells[i * 8:(i + 1) * 8])
            row.arrange(RIGHT, buff=0.12)
            rows.add(row)
        rows.arrange(DOWN, buff=0.14)
        group.add(rows)

        label = {
            0: "一个 Warp = 32 个线程，同一时钟锁步执行",
            1: "分支 A：偶数线程执行，奇数线程被掩码挂起",
            2: "分支 B：奇数线程执行，偶数线程被掩码挂起",
            3: "重新收敛：两条分支串行完成，代价是时间翻倍",
        }.get(phase, "")
        tag = T(label, 16, CYAN if phase < 3 else GREEN, BOLD)
        tag.next_to(rows, UP, buff=0.18)
        group.add(tag)

        if phase in (1, 2):
            idle = "掩码挂起" if phase == 1 else "掩码挂起"
            note = T("MASKED · 奇数线程挂起", 13, AMBER)
            note.next_to(rows, DOWN, buff=0.12)
            group.add(note)
        return group

    # -- banks -----------------------------------------------------------
    def _fig_banks(self, fig, phase):
        phase = min(int(phase), 2)
        stride = int(fig.get("stride") or 2)
        display = 8  # a readable window onto the 32 banks
        group = VGroup()

        title = T("Shared Memory：32 个 Bank（图中展示 Bank 0-7）", 14, DIM, BOLD)
        title.move_to([0, 1.55, 0])
        group.add(title)

        bank_x = [-3.15 + idx * 0.9 for idx in range(display)]
        targets = []
        for tid in range(display):
            if phase == 0:
                targets.append(tid % display)
            elif phase == 1:
                targets.append((tid * stride) % display)
            else:
                targets.append((tid * (stride + 1)) % display)

        hot = {t for t in targets if targets.count(t) > 1} if phase == 1 else set()
        cells = VGroup()
        for bank in range(display):
            color = RED if bank in hot else (GREEN if phase == 2 else CYAN)
            box = RoundedRectangle(
                corner_radius=0.06,
                width=0.74,
                height=0.8,
                color=color,
                fill_color="#2A1118" if bank in hot else PANEL_2,
                fill_opacity=1.0,
                stroke_width=2.6 if bank in hot else 1.8,
            ).move_to([bank_x[bank], 0, 0])
            label = T(str(bank), 16, WHITE, BOLD).move_to(box.get_center())
            cells.add(VGroup(box, label))
        group.add(cells)

        more = T("… 共 32 个", 12, DIM).next_to(cells, RIGHT, buff=0.18)
        group.add(more)

        for tid in range(display):
            x = bank_x[tid]
            dot = Circle(radius=0.17, color=CYAN if phase < 2 else GREEN, fill_color=CYAN if phase < 2 else GREEN, fill_opacity=1)
            dot.move_to([x, 1.05, 0])
            label = T(f"t{tid}", 11, BG, BOLD).move_to(dot.get_center())
            group.add(VGroup(dot, label))

            conflict = phase == 1 and targets.count(targets[tid]) > 1
            arrow = Arrow(
                [x, 0.86, 0],
                [bank_x[targets[tid]], 0.45, 0],
                color=RED if conflict else (GREEN if phase == 2 else CYAN),
                buff=0.02,
                stroke_width=2.2 if conflict else 1.6,
                max_tip_length_to_length_ratio=0.18,
            )
            group.add(arrow)

        if phase == 1:
            note = T("冲突：stride=2，多个线程命中同一个 Bank，被迫串行", 15, RED, BOLD)
        elif phase == 2:
            note = T("修复：Padding 把 stride 变成奇数，每个线程独占一个 Bank", 15, GREEN, BOLD)
        else:
            note = T("无冲突：线程 i 访问 Bank i，一个周期并发完成", 15, CYAN, BOLD)
        note.move_to([0, -1.35, 0])
        group.add(note)
        return group

    # -- coalesce --------------------------------------------------------
    def _fig_coalesce(self, fig, phase):
        phase = min(int(phase), 2)
        threads = int(fig.get("threads") or 8)
        group = VGroup()

        thread_row = VGroup()
        for tid in range(threads):
            box = panel_rect(0.62, 0.62, PANEL_2, CYAN)
            label = T(f"t{tid}", 13, WHITE, BOLD).move_to(box.get_center())
            thread_row.add(VGroup(box, label))
        thread_row.arrange(RIGHT, buff=0.26)
        thread_row.move_to([0, 1.35, 0])
        group.add(thread_row)

        segments = 4
        seg_row = VGroup()
        for seg in range(segments):
            box = RoundedRectangle(
                corner_radius=0.06, width=1.72, height=0.85,
                color=GREEN if phase != 1 else BORDER,
                fill_color="#10251A" if phase != 1 else PANEL,
                fill_opacity=1.0, stroke_width=2.2,
            )
            label = T(f"32B · sector {seg}", 13, WHITE if phase != 1 else DIM)
            label.move_to(box.get_center())
            seg_row.add(VGroup(box, label))
        seg_row.arrange(RIGHT, buff=0.18)
        seg_row.move_to([0, -0.85, 0])
        group.add(seg_row)

        badge_text = "4 × 32B（拆分）" if phase == 1 else "1 × 128B（合并）"
        badge = T(badge_text, 15, RED if phase == 1 else GREEN, BOLD)
        badge.move_to([0, -1.55, 0])
        group.add(badge)

        for tid in range(threads):
            if phase == 1:
                target = tid * 3 % segments
                color = RED
            elif phase == 2:
                target = tid // 2 % segments
                color = GREEN
            else:
                target = tid // 2 % segments
                color = CYAN
            start = thread_row[tid].get_bottom()
            end = seg_row[target].get_top()
            group.add(Arrow(start, end, color=color, buff=0.06, stroke_width=1.5,
                            max_tip_length_to_length_ratio=0.16))

        if phase == 1:
            note = T("错误：跨步访问把 Warp 的访问拆成多次总线事务，带宽被浪费", 15, RED, BOLD)
        elif phase == 2:
            note = T("正确：连续线程 + 合并事务，一次 128B 传输满足整个 Warp", 15, GREEN, BOLD)
        else:
            note = T("连续线程访问连续地址 → 硬件自动合并为一次宽事务", 15, CYAN, BOLD)
        note.move_to([0, -1.95, 0])
        group.add(note)
        return group

    # -- matrix ----------------------------------------------------------
    def _fig_matrix(self, fig, phase):
        phase = min(int(phase), 2)
        size = int(fig.get("size") or 4)
        tile = int(fig.get("tile") or 2)
        group = VGroup()

        def matrix(title, color, highlight=None):
            cells = VGroup()
            for r in range(size):
                row = VGroup()
                for c in range(size):
                    hot = highlight and (r // tile, c // tile) == highlight
                    box = Square(
                        side_length=0.32,
                        color=color if hot else BORDER,
                        fill_color=color if hot else PANEL_2,
                        fill_opacity=0.75 if hot else 1.0,
                        stroke_width=2 if hot else 1,
                    )
                    row.add(box)
                row.arrange(RIGHT, buff=0.04)
                cells.add(row)
            cells.arrange(DOWN, buff=0.04)
            label = T(title, 13, WHITE, BOLD).next_to(cells, UP, buff=0.1)
            return VGroup(cells, label)

        a = matrix("A", CYAN, highlight=(1, 0) if phase == 0 else None)
        b = matrix("B", VIOLET, highlight=(0, 1) if phase == 0 else None)
        c = matrix("C", GREEN, highlight=(1, 1) if phase >= 1 else None)
        a.move_to([-4.2, 0, 0])
        b.move_to([0, 0, 0])
        c.move_to([4.2, 0, 0])
        group.add(a, b, c)

        group.add(Arrow(a.get_right() + RIGHT * 0.1, b.get_left() + LEFT * 0.1, color=DIM, buff=0.05, stroke_width=2))
        group.add(Arrow(b.get_right() + RIGHT * 0.1, c.get_left() + LEFT * 0.1, color=DIM, buff=0.05, stroke_width=2))

        if phase == 0:
            note = T(f"把 {tile}×{tile} 的 tile 搬进 Shared Memory，块内复用", 15, CYAN, BOLD)
        elif phase == 1:
            note = T("每个线程读 A 的一行、B 的一列，乘加写回 C 的 tile", 15, AMBER, BOLD)
        else:
            note = T("全局内存只读一次，Shared Memory 被复用 tile 次", 15, GREEN, BOLD)
        note.move_to([0, -1.45, 0])
        group.add(note)
        return group

    # -- timeline --------------------------------------------------------
    def _fig_timeline(self, fig, phase):
        rows = fig.get("rows") or []
        span = max([seg.get("end", 1) for row in rows for seg in row.get("segments", [])] + [1])
        group = VGroup()
        lane_x = -4.25
        lane_w = 9.4
        colors = [CYAN, AMBER, GREEN, VIOLET]
        focus = self._current_focus or []

        for r_idx, row in enumerate(rows):
            y = 1.0 - r_idx * 1.0
            focused = (r_idx in focus) if focus else r_idx == phase % max(1, len(rows))
            label = fit(T(str(row.get("label", ""))[:18], 13, WHITE if focused else DIM, BOLD), 2.3)
            label.move_to([-5.6, y, 0])
            group.add(label)
            row_group = VGroup()
            for s_idx, seg in enumerate(row.get("segments", [])):
                start = float(seg.get("start", 0))
                end = float(seg.get("end", start + 1))
                width = max(0.3, lane_w * (end - start) / span)
                x = lane_x + lane_w * (start + (end - start) / 2) / span
                color = colors[(r_idx + s_idx) % len(colors)]
                box = RoundedRectangle(
                    corner_radius=0.06, width=width, height=0.52,
                    color=color, fill_color=color, fill_opacity=0.85, stroke_width=1.4,
                ).move_to([x, y, 0])
                text = T(str(seg.get("label", ""))[:10], 11, BG, BOLD)
                fit(text, width * 0.86)
                text.move_to(box.get_center())
                row_group.add(VGroup(box, text))
            row_group.set_opacity(1.0 if focused else 0.55)
            group.add(row_group)

        axis_y = 1.0 - len(rows) * 1.0 + 0.25
        group.add(Line([lane_x, axis_y, 0], [lane_x + lane_w, axis_y, 0], color=BORDER, stroke_width=1.4))
        group.add(T("time →", 11, DIM).next_to([lane_x + lane_w, axis_y, 0], RIGHT, buff=0.08))

        if phase == 0:
            note = T("默认流：H2D → Kernel → D2H 串行排队，硬件引擎轮流空转", 15, AMBER, BOLD)
        else:
            note = T("多流：搬运与计算落在不同引擎上，时间轴出现重叠", 15, GREEN, BOLD)
        note.move_to([0, max(-1.5, axis_y - 0.5), 0])
        group.add(note)
        return group

    # -- code ------------------------------------------------------------
    def _fig_code(self, fig, phase):
        lines = [str(line) for line in (fig.get("lines") or []) if str(line).strip()][:9]
        group = VGroup()
        width = 12.2
        panel_h = 0.4 * len(lines) + 0.35
        panel = RoundedRectangle(
            corner_radius=0.1, width=width, height=panel_h,
            color=BORDER, fill_color="#070C12", fill_opacity=1.0, stroke_width=1.6,
        )
        group.add(panel)

        top = panel.get_top()[1] - 0.28
        focus = [i for i in (self._current_focus or []) if 0 <= i < len(lines)]
        targets = set(focus) if focus else {phase % max(1, len(lines))}
        for idx, line in enumerate(lines):
            y = top - idx * 0.36
            hl = Rectangle(
                width=width - 0.25, height=0.33,
                color=AMBER, fill_color=AMBER, fill_opacity=0.22 if idx in targets else 0.0,
                stroke_width=0,
            ).move_to([0, y - 0.04, 0])
            num = T(f"{idx + 1:>2}", 12, "#5B6B7E").move_to([panel.get_left()[0] + 0.35, y, 0])
            text = T(line, 16, WHITE)
            fit(text, 10.4)
            text.next_to(num, RIGHT, buff=0.3)
            text.align_to([0, y, 0], UP)
            group.add(hl, num, text)

        note = T("黄色高亮 = 当前正在讲解的代码行", 13, AMBER)
        note.next_to(panel, DOWN, buff=0.12)
        group.add(note)
        return group

    # -- compare ---------------------------------------------------------
    def _fig_compare(self, fig, phase):
        left = fig.get("left") or {"title": "反例", "lines": ["bad"]}
        right = fig.get("right") or {"title": "规范", "lines": ["good"]}
        focus = self._current_focus or []
        group = VGroup()
        for idx, (spec, color) in enumerate(((left, RED), (right, GREEN))):
            active = idx in focus if focus else idx == phase % 2
            box = RoundedRectangle(
                corner_radius=0.1, width=5.9, height=3.05,
                color=color, fill_color=PANEL, fill_opacity=1.0,
                stroke_width=2.6 if active else 1.4,
            )
            title = fit(T(str(spec.get("title", ""))[:20], 17, color, BOLD), 5.3)
            title.next_to(box.get_top(), DOWN, buff=0.16)
            lines = VGroup()
            for line in list(spec.get("lines") or [])[:5]:
                chunks = textwrap.wrap(str(line), width=42, break_long_words=True) or [""]
                for chunk in chunks[:3]:
                    item = fit(T(chunk, 11, WHITE), 5.2)
                    lines.add(item)
                if len(lines) >= 9:
                    break
            lines.arrange(DOWN, aligned_edge=LEFT, buff=0.12)
            lines.next_to(title, DOWN, buff=0.18)
            panel = VGroup(box, title, lines).move_to([-3.15 if idx == 0 else 3.15, 0.05, 0])
            group.add(panel)
        return group

    # -- bars ------------------------------------------------------------
    def _fig_bars(self, fig, phase):
        items = fig.get("items") or []
        peak = max([float(i.get("value") or 0) for i in items] + [1.0])
        group = VGroup()
        base = -1.0
        focus = self._current_focus or []
        for idx, item in enumerate(items):
            value = float(item.get("value") or 0)
            height = max(0.18, 2.5 * value / peak)
            x = -3.6 + idx * 2.2
            active = idx in focus if focus else idx == phase % max(1, len(items))
            color = GREEN if active else CYAN
            bar = Rectangle(width=1.0, height=height, color=color, fill_color=color, fill_opacity=0.85)
            bar.move_to([x, base + height / 2, 0])
            label = fit(T(str(item.get("label", ""))[:12], 12, WHITE), 1.6).move_to([x, base - 0.32, 0])
            val = T(f"{value:g}{item.get('unit', '')}", 13, WHITE, BOLD).move_to([x, base + height + 0.24, 0])
            group.add(VGroup(bar, label, val))
        group.add(Line([-5.0, base, 0], [5.0, base, 0], color=BORDER, stroke_width=2))
        return group

    # ==================================================================
    # Ambient motion (keep the frame alive during narration)
    # ==================================================================
    def _ambient(self, seconds: float, figure, step):
        remaining = max(0.0, seconds)
        while remaining > 0.2:
            chunk = min(3.2, remaining)
            settle = max(0.4, chunk * 0.55)
            self.wait(settle)
            remaining -= settle
            if remaining > 0.5:
                try:
                    self.play(self.stage_glow.animate.set_stroke(opacity=0.45), run_time=0.35)
                    left = self.stage_rect.get_left()[0] + 0.08
                    right = self.stage_rect.get_right()[0] - 0.08
                    self.scan_line.move_to([left, self.stage_rect.get_center()[1], 0])
                    self.play(
                        self.scan_line.animate.move_to([right, self.stage_rect.get_center()[1], 0]).set_stroke(opacity=0.4),
                        run_time=0.9,
                    )
                    self.play(
                        self.scan_line.animate.set_stroke(opacity=0.0),
                        self.stage_glow.animate.set_stroke(opacity=0.0),
                        run_time=0.35,
                    )
                    remaining -= 1.6
                except Exception:
                    pass

