# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"E:\\CudaStudy")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, HostDeviceFlowDiagram

class CudaPlatformArchitectureScene(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA 平台架构与软硬件执行全景", "基于 NVIDIA 13.3 · Host 软件抽象到 Device 硬件物理执行")
        code_badge = self.create_code_badge("vectorAdd<<<Grid(Blocks), Block(Threads)>>>(d_A, d_B, d_C);", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time=1.2)

        flow_diagram = HostDeviceFlowDiagram()
        flow_diagram.move_to(DOWN * 0.1)

        self.play(
            FadeIn(flow_diagram.host_group),
            FadeIn(flow_diagram.launch_arrow),
            FadeIn(flow_diagram.launch_lbl),
            FadeIn(flow_diagram.device_group),
            run_time=1.8
        )
        self.wait(1.0)

        # Pulse GigaThread and SM allocation
        clarify_badge = self.create_code_badge("重要澄清：1. Block不等于SM; 2. Warp不等于SM; 3. 多Block并发驻留SM", position=UP * 2.0)
        self.play(
            FadeOut(code_badge), FadeIn(clarify_badge),
            flow_diagram.device_group.animate.set_color(NVIDIA_GREEN),
            Flash(flow_diagram.device_group, color=NVIDIA_GREEN, flash_radius=1.8),
            run_time=3.2
        )
        self.deliberate_pause(2.0)
