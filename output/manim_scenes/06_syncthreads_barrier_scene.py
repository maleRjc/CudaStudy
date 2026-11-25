# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaSyncthreadsScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("块内线程同步屏障 (__syncthreads)", "步调异步脏读 vs 分支内屏障死锁禁忌")
        code_badge = self.create_code_badge("if (tid % 2 == 0) { __syncthreads(); } // 致命禁忌：死锁挂起！", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=47.06 * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=1.0)
        threads.move_to(UP * 0.5)

        barrier = DashedLine(start=LEFT * 4.5, end=RIGHT * 4.5, color=THREAD_CONFLICT, dash_length=0.2, stroke_width=4)
        barrier.move_to(DOWN * 1.0)
        barrier_lbl = Text("同步栅栏 (__syncthreads Barrier)", font_size=FONT_BADGE_SIZE, color=THREAD_CONFLICT).next_to(barrier, UP, buff=0.15)

        self.play(FadeIn(threads), FadeIn(barrier), FadeIn(barrier_lbl), run_time=47.06 * 0.6)

        self.play(
            threads[0].animate.move_to(DOWN * 0.8 + LEFT * 1.5),
            threads[2].animate.move_to(DOWN * 0.8 + RIGHT * 1.5),
            threads[1].animate.move_to(UP * 1.5 + LEFT * 0.5),
            threads[3].animate.move_to(UP * 1.5 + RIGHT * 0.5),
            run_time=162.86 * 0.5
        )

        deadlock_box = Text("! 硬件永久死锁 (Deadlock): 未走分支线程永不到达 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        deadlock_box.next_to(barrier, DOWN, buff=0.3)
        self.play(FadeIn(deadlock_box), run_time=0.6)
        self.wait(7.2)

        safe_badge = self.create_code_badge("__syncthreads(); // 必须放置在公共无条件控制流中", position=UP * 2.0)
        self.play(
            FadeOut(code_badge),
            FadeOut(deadlock_box),
            FadeIn(safe_badge),
            barrier.animate.set_color(NVIDIA_GREEN),
            run_time=0.5
        )
        barrier_lbl.become(Text("全员集合 · 屏障平稳通过", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).next_to(barrier, UP, buff=0.15))

        self.play(
            threads.animate.arrange(RIGHT, buff=1.0).move_to(DOWN * 2.0),
            *[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads],
            run_time=38.21 * 0.7
        )
        self.deliberate_pause(1.8)
