# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class CudaCpuVsGpuScene(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CPU 延迟优化 vs GPU 吞吐优化架构", "少数顶尖数学家 vs 海量并行计算核心")
        code_badge = self.create_code_badge("CPU: 大片上缓存与复杂乱序预测 | GPU: 80% 面积密布原生算力 ALU", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=1.2)

        # CPU Die (Left)
        cpu_box = RoundedRectangle(corner_radius=0.15, width=4.0, height=2.6, color=BLUE_C, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 3.6 + DOWN * 0.1)
        cpu_lbl = Text("CPU (延迟优先架构)", font_size=FONT_BADGE_SIZE, color=BLUE_C, weight=BOLD).next_to(cpu_box, UP, buff=0.1)
        cache_rect = Rectangle(width=3.5, height=0.7, color=BLUE_E, fill_color=BLUE_E, fill_opacity=0.7).move_to(cpu_box.get_center() + UP * 0.5)
        cache_lbl = Text("巨幅片上缓存 (L3 Cache · 占面积 40%)", font_size=FONT_BADGE_SIZE - 4, color=TEXT_PRIMARY).move_to(cache_rect.get_center())
        ctrl_rect = Rectangle(width=3.5, height=0.5, color=PURPLE, fill_color=PURPLE, fill_opacity=0.6).move_to(cpu_box.get_center() + DOWN * 0.2)
        ctrl_lbl = Text("复杂分支预测与乱序发射逻辑", font_size=FONT_BADGE_SIZE - 4, color=TEXT_PRIMARY).move_to(ctrl_rect.get_center())
        cpu_alus = VGroup(*[Square(side_length=0.42, color=YELLOW, fill_color=YELLOW, fill_opacity=0.8) for _ in range(4)]).arrange(RIGHT, buff=0.25).move_to(cpu_box.get_center() + DOWN * 0.8)
        alu_lbl = Text("4 强核 ALU", font_size=FONT_BADGE_SIZE - 5, color=BG_DARK, weight=BOLD).move_to(cpu_alus.get_center())
        cpu_group = VGroup(cpu_box, cpu_lbl, cache_rect, cache_lbl, ctrl_rect, ctrl_lbl, cpu_alus, alu_lbl)

        # GPU Die (Right)
        gpu_box = RoundedRectangle(corner_radius=0.15, width=4.6, height=2.6, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 3.3 + DOWN * 0.1)
        gpu_lbl = Text("GPU (吞吐优先架构)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN, weight=BOLD).next_to(gpu_box, UP, buff=0.1)
        gpu_cores = VGroup()
        for r in range(4):
            row = VGroup(*[Square(side_length=0.28, color=NVIDIA_GREEN, fill_color=NVIDIA_GREEN, fill_opacity=0.85) for _ in range(8)]).arrange(RIGHT, buff=0.08)
            gpu_cores.add(row)
        gpu_cores.arrange(DOWN, buff=0.08).move_to(gpu_box.get_center() + UP * 0.2)
        core_lbl = Text("数千个高能效计算核心 (SIMD/SIMT ALU 阵列)", font_size=FONT_BADGE_SIZE - 4, color=NVIDIA_GREEN, weight=BOLD).next_to(gpu_cores, DOWN, buff=0.15)
        gpu_group = VGroup(gpu_box, gpu_lbl, gpu_cores, core_lbl)

        self.play(FadeIn(cpu_group), FadeIn(gpu_group), run_time=1.8)
        self.wait(1.0)

        # Action: Compare execution
        self.play(
            LaggedStart(*[c.animate.set_color(WARP_COLOR_A).set_fill(WARP_COLOR_A, opacity=1.0) for row in gpu_cores for c in row], lag_ratio=0.02),
            code_badge.animate.become(self.create_code_badge("GPU 架构真谛：用芯片物理面积换取极限数据并行吞吐！", position=UP * 2.0)),
            run_time=2.8
        )
        self.deliberate_pause(2.0)
