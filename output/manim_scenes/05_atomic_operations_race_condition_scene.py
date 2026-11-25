# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaAtomicScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("原子操作与竞态条件", "并发覆写丢失 vs 硬件独占锁")
        code_badge = self.create_code_badge("*counter = *counter + 1; // 读改写非原子：海量增量丢失", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=29.64 * 0.4)

        t0 = ThreadItem(block_id=0, thread_id=0).move_to(UP * 0.4 + LEFT * 2.5)
        t1 = ThreadItem(block_id=0, thread_id=1).move_to(UP * 0.4 + RIGHT * 2.5)

        counter_box = Square(side_length=1.4, color=MEMORY_BORDER, fill_color=CARD_BG, fill_opacity=0.9).move_to(DOWN * 1.5)
        counter_lbl = Text("Counter: 0", font_size=FONT_SUBTITLE_SIZE, color=TEXT_PRIMARY, weight=BOLD).move_to(counter_box.get_center())
        c_desc = Text("Global Memory 共享累加器", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(counter_box, DOWN, buff=0.15)

        self.play(FadeIn(t0), FadeIn(t1), FadeIn(counter_box), FadeIn(counter_lbl), FadeIn(c_desc), run_time=29.64 * 0.6)

        a0 = Arrow(start=t0.circle.get_bottom(), end=counter_box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        a1 = Arrow(start=t1.circle.get_bottom(), end=counter_box.get_top(), color=THREAD_CONFLICT, buff=0.1)

        self.play(GrowArrow(a0), GrowArrow(a1), run_time=0.8)
        counter_lbl.become(Text("Counter: 1 (!)", font_size=FONT_SUBTITLE_SIZE, color=THREAD_CONFLICT, weight=BOLD).move_to(counter_box.get_center()))
        counter_box.set_color(THREAD_CONFLICT)
        warn_text = Text("两线程并发加 1，结果竟然还是 1 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD).move_to(UP * 1.2)
        self.play(FadeIn(warn_text), run_time=0.6)
        self.wait(1.8)

        atomic_badge = self.create_code_badge("atomicAdd(counter, 1); // 硬件级排队互斥锁", position=UP * 2.0)
        self.play(
            FadeOut(code_badge),
            FadeOut(warn_text),
            FadeOut(a0),
            FadeOut(a1),
            FadeIn(atomic_badge),
            counter_box.animate.set_color(NVIDIA_GREEN),
            run_time=0.5
        )

        q_arrow0 = Arrow(start=t0.circle.get_bottom(), end=counter_box.get_top(), color=NVIDIA_GREEN, buff=0.1)
        self.play(GrowArrow(q_arrow0), run_time=0.6)
        counter_lbl.become(Text("Counter: 1", font_size=FONT_SUBTITLE_SIZE, color=NVIDIA_GREEN, weight=BOLD).move_to(counter_box.get_center()))
        self.play(FadeOut(q_arrow0), run_time=0.3)

        q_arrow1 = Arrow(start=t1.circle.get_bottom(), end=counter_box.get_top(), color=NVIDIA_GREEN, buff=0.1)
        self.play(GrowArrow(q_arrow1), run_time=0.6)
        counter_lbl.become(Text("Counter: 2", font_size=FONT_SUBTITLE_SIZE, color=NVIDIA_GREEN, weight=BOLD).move_to(counter_box.get_center()))
        self.play(FadeOut(q_arrow1), run_time=0.3)
        self.wait(5.4)

        summary_badge = self.create_code_badge("先局部规约，再全局原子 = 兼顾安全与超高吞吐", position=UP * 2.0)
        self.play(FadeOut(atomic_badge), FadeIn(summary_badge), run_time=0.5)
        self.play(
            t0.circle.animate.set_color(THREAD_RESOLVED),
            t1.circle.animate.set_color(THREAD_RESOLVED),
            run_time=55.73 * 0.7
        )
        self.deliberate_pause(1.8)
