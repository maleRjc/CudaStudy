# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaCoalescedScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("全局内存合并访问 (Coalescing)", "128 字节总线事务 vs 离散跨步浪费")
        code_badge = self.create_code_badge("float val = d_in[idx]; // 连续线程访连续内存：100% 效率", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=50.06 * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.5)

        bus_rect = RoundedRectangle(corner_radius=0.15, width=6.5, height=0.6, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9)
        bus_rect.move_to(DOWN * 0.6)
        bus_label = Text("GPU 显存总线事务 (128-Byte Transaction)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).move_to(bus_rect.get_center())

        slots = VGroup(*[MemorySlot(address_idx=i, width=0.85, height=0.85) for i in range(6)]).arrange(RIGHT, buff=0.2)
        slots.move_to(DOWN * 2.2)

        self.play(FadeIn(threads), FadeIn(bus_rect), FadeIn(bus_label), FadeIn(slots), run_time=50.06 * 0.6)

        t_arrows = [
            Arrow(start=threads[i].circle.get_bottom(), end=bus_rect.get_top(), color=NVIDIA_GREEN, buff=0.1)
            for i in range(4)
        ]
        b_arrows = [
            Arrow(start=bus_rect.get_bottom(), end=slots[i].box.get_top(), color=NVIDIA_GREEN, buff=0.1)
            for i in range(4)
        ]

        self.play(
            LaggedStart(*[GrowArrow(a) for a in t_arrows], lag_ratio=0.08),
            LaggedStart(*[GrowArrow(b) for b in b_arrows], lag_ratio=0.08),
            run_time=1.0
        )
        for i in range(4):
            slots[i].set_value(f"t{i}", color=NVIDIA_GREEN)
        self.wait(1.8)

        bad_badge = self.create_code_badge("float val = d_in[idx * 4]; // 跨步访问：总线多次反复搬运", position=UP * 2.0)
        self.play(
            FadeOut(code_badge),
            FadeIn(bad_badge),
            FadeOut(VGroup(*t_arrows)),
            FadeOut(VGroup(*b_arrows)),
            run_time=0.5
        )

        bad_arrow = Arrow(start=threads[0].circle.get_bottom(), end=slots[0].box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        bad_arrow2 = Arrow(start=threads[1].circle.get_bottom(), end=slots[4].box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        bus_rect.set_color(THREAD_CONFLICT)
        bus_label.become(Text("多次总线事务裂变 (利用率暴跌至 25% !)", font_size=FONT_BADGE_SIZE, color=THREAD_CONFLICT).move_to(bus_rect.get_center()))

        self.play(
            GrowArrow(bad_arrow),
            GrowArrow(bad_arrow2),
            threads[0].circle.animate.set_color(THREAD_CONFLICT),
            threads[1].circle.animate.set_color(THREAD_CONFLICT),
            run_time=173.26 * 0.6
        )
        self.wait(7.2)

        fix_badge = self.create_code_badge("数据排布重构：AoS 转 SoA (对齐硬件扇区)", position=UP * 2.0)
        self.play(
            FadeOut(bad_badge),
            FadeOut(bad_arrow),
            FadeOut(bad_arrow2),
            FadeIn(fix_badge),
            bus_rect.animate.set_color(NVIDIA_GREEN),
            run_time=0.5
        )
        bus_label.become(Text("对齐内存扇区 · 100% 极速带宽打满", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).move_to(bus_rect.get_center()))
        self.play(
            *[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads],
            run_time=41.62 * 0.7
        )
        self.deliberate_pause(1.8)
