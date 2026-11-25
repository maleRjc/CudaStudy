# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadGrid, MemoryLane, ThreadItem

class CudaGlobalIdScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("CUDA 全局索引映射", "CPU 串行循环思维 vs GPU 空间升维")
        code_badge = self.create_code_badge("int idx = threadIdx.x;  // 隐患：单块正常，多块冲突", position=UP * 2.0)
        
        self.play(FadeIn(header), FadeIn(code_badge), run_time=38.78 * 0.4)

        grid = ThreadGrid(num_blocks=1, threads_per_block=4, block_spacing=0.8)
        grid.move_to(UP * 0.2 + LEFT * 3.0)

        memory = MemoryLane(num_slots=8, slot_width=0.85)
        memory.move_to(DOWN * 2.5)

        self.play(FadeIn(grid), FadeIn(memory), run_time=38.78 * 0.6)

        t0 = grid.get_thread(0, 0)
        arrow_t0 = Arrow(start=t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_DEFAULT, buff=0.1)
        
        self.play(GrowArrow(arrow_t0), run_time=0.8)
        memory.get_slot(0).set_value("T0", color=THREAD_DEFAULT)
        self.wait(3.5)

        new_grid = ThreadGrid(num_blocks=2, threads_per_block=4, block_spacing=1.2)
        new_grid.move_to(UP * 0.2)

        self.play(
            ReplacementTransform(grid, new_grid),
            FadeOut(arrow_t0),
            run_time=167.4 * 0.4
        )

        b0_t0 = new_grid.get_thread(0, 0)
        b1_t0 = new_grid.get_thread(1, 0)

        arrow_b0 = Arrow(start=b0_t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        arrow_b1 = Arrow(start=b1_t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_CONFLICT, buff=0.1)

        self.play(
            GrowArrow(arrow_b0),
            GrowArrow(arrow_b1),
            b0_t0.circle.animate.set_color(THREAD_CONFLICT),
            b1_t0.circle.animate.set_color(THREAD_CONFLICT),
            run_time=167.4 * 0.6
        )

        memory.get_slot(0).flash_collision()
        warning = Text("! 致命物理地址覆写冲突 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        warning.next_to(code_badge, DOWN, buff=0.2)
        self.play(FadeIn(warning), run_time=0.5)
        self.wait(14.0)

        aha_formula = self.create_code_badge("int idx = blockIdx.x * blockDim.x + threadIdx.x;", position=UP * 2.0)
        self.play(
            FadeOut(code_badge),
            FadeOut(warning),
            FadeOut(arrow_b0),
            FadeOut(arrow_b1),
            FadeIn(aha_formula),
            run_time=0.6
        )

        resolved_arrows = []
        for b in range(2):
            for t in range(4):
                g_id = b * 4 + t
                t_obj = new_grid.get_thread(b, t)
                t_obj.set_resolved_state("g" + str(g_id))
                arr = Arrow(start=t_obj.circle.get_bottom(), end=memory.get_slot(g_id).box.get_top(), color=NVIDIA_GREEN, stroke_width=2, buff=0.1)
                resolved_arrows.append(arr)

        self.play(
            LaggedStart(*[GrowArrow(a) for a in resolved_arrows], lag_ratio=0.08),
            run_time=36.17 * 0.7
        )
        self.deliberate_pause(3.5)
