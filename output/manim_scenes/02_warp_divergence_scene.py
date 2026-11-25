# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadItem

class CudaWarpDivergenceScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("Warp 线程束分支分化", "SIMT 硬件锁步 vs 独立多分支假象")
        code_badge = self.create_code_badge("if (tid % 2 == 0) { ... } else { ... }", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=37.2 * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(ORIGIN)
        warp_label = Text("Mini-Warp (4 线程锁步推进)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(threads, UP, buff=0.3)

        self.play(FadeIn(threads), FadeIn(warp_label), run_time=37.2 * 0.6)
        self.wait(1.8)

        mask_label = Text("阶段 1: 分支 A 执行 (t1, t3 被硬件强制挂起)", font_size=FONT_SUBTITLE_SIZE - 4, color=WARP_COLOR_A)
        mask_label.move_to(DOWN * 1.5)

        self.play(
            threads[0].circle.animate.set_color(WARP_COLOR_A),
            threads[2].circle.animate.set_color(WARP_COLOR_A),
            threads[1].circle.animate.set_color(THREAD_IDLE),
            threads[3].circle.animate.set_color(THREAD_IDLE),
            FadeIn(mask_label),
            run_time=180.07 * 0.5
        )

        mask_label_b = Text("阶段 2: 分支 B 执行 (t0, t2 被硬件强制挂起)", font_size=FONT_SUBTITLE_SIZE - 4, color=WARP_COLOR_B)
        mask_label_b.move_to(DOWN * 1.5)

        self.play(
            threads[0].circle.animate.set_color(THREAD_IDLE),
            threads[2].circle.animate.set_color(THREAD_IDLE),
            threads[1].circle.animate.set_color(WARP_COLOR_B),
            threads[3].circle.animate.set_color(WARP_COLOR_B),
            ReplacementTransform(mask_label, mask_label_b),
            run_time=180.07 * 0.5
        )
        self.wait(5.4)

        self.play(FadeOut(mask_label_b), FadeOut(code_badge), run_time=0.4)
        summary_badge = self.create_code_badge("消除分支分化 = 算力吞吐翻倍 (Zero Divergence)", position=UP * 2.0)
        
        self.play(
            FadeIn(summary_badge),
            *[t.circle.animate.set_color(NVIDIA_GREEN) for t in threads],
            run_time=45.43 * 0.6
        )

        self.deliberate_pause(1.8)
