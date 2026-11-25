# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaBankConflictScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("共享内存架构与 Bank 冲突", "32 Bank 并发访问 vs 串行排队陷阱")
        code_badge = self.create_code_badge("float val = s_data[tid]; // 无冲突：1 对 1 物理映射", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=43.18 * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.4)
        t_label = Text("Threads (t0 - t3)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(threads, UP, buff=0.2)

        banks = VGroup(*[MemorySlot(address_idx=i, width=1.1, height=1.1) for i in range(4)]).arrange(RIGHT, buff=0.35)
        for i, b in enumerate(banks):
            b.addr_label.become(Text(f"Bank {i}", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(b.box, DOWN, buff=0.1))
            b.set_value(f"B{i}")
        banks.move_to(DOWN * 2.0)
        b_label = Text("Shared Memory Banks (32路并发物理模块)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(banks, UP, buff=0.2)

        self.play(FadeIn(threads), FadeIn(t_label), FadeIn(banks), FadeIn(b_label), run_time=43.18 * 0.6)

        arrows = [
            Arrow(start=threads[i].circle.get_bottom(), end=banks[i].box.get_top(), color=NVIDIA_GREEN, buff=0.1)
            for i in range(4)
        ]
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), run_time=1.0)
        self.wait(1.8)

        conflict_badge = self.create_code_badge("float val = s_data[tid * 2]; // 2路冲突：同时命中 Bank 0", position=UP * 2.0)
        self.play(
            FadeOut(code_badge),
            FadeIn(conflict_badge),
            FadeOut(VGroup(*arrows)),
            run_time=0.5
        )

        c_arrow_0 = Arrow(start=threads[0].circle.get_bottom(), end=banks[0].box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        c_arrow_2 = Arrow(start=threads[2].circle.get_bottom(), end=banks[0].box.get_top(), color=THREAD_CONFLICT, buff=0.1)

        self.play(
            GrowArrow(c_arrow_0),
            GrowArrow(c_arrow_2),
            threads[0].circle.animate.set_color(THREAD_CONFLICT),
            threads[2].circle.animate.set_color(THREAD_CONFLICT),
            banks[0].box.animate.set_color(THREAD_CONFLICT),
            run_time=193.82 * 0.6
        )

        warning_lbl = Text("! 2-way Bank Conflict: 硬件被迫串行排队执行 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        warning_lbl.next_to(conflict_badge, DOWN, buff=0.2)
        self.play(FadeIn(warning_lbl), run_time=0.6)
        self.wait(7.2)

        fix_badge = self.create_code_badge("__shared__ float s[32][33]; // 填充列 (Padding) 消除冲突", position=UP * 2.0)
        self.play(
            FadeOut(conflict_badge),
            FadeOut(warning_lbl),
            FadeOut(c_arrow_0),
            FadeOut(c_arrow_2),
            FadeIn(fix_badge),
            run_time=0.5
        )

        resolved_arrows = [
            Arrow(start=threads[i].circle.get_bottom(), end=banks[i].box.get_top(), color=NVIDIA_GREEN, buff=0.1)
            for i in range(4)
        ]
        self.play(
            *[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads],
            banks[0].box.animate.set_color(MEMORY_BORDER),
            LaggedStart(*[GrowArrow(a) for a in resolved_arrows], lag_ratio=0.08),
            run_time=47.23 * 0.7
        )

        self.deliberate_pause(1.8)
