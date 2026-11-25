"""
Layer 4: Manim Scene Code Generation, Rendering & Self-Healing Execution Engine.
Generates robust Python Manim code utilizing CUDA prefabs, executes headless rendering,
and autonomously fixes syntax/runtime tracebacks.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def find_python_interpreter() -> Path:
    """Finds a valid Python interpreter that has Manim installed."""
    candidates = [
        config.BASE_DIR / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable).resolve().parent / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable).resolve().parent.parent / ".venv" / "Scripts" / "python.exe",
        Path(r"C:\Users\inno\AppData\Local\Programs\Python\Python311\python.exe"),
        Path(r"C:\Python314\python.exe"),
    ]
    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    for c in candidates:
        if c.exists() and "python" in c.name.lower():
            try:
                res = subprocess.run(
                    [str(c), "-c", "import manim"],
                    capture_output=True,
                    timeout=6,
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                )
                if res.returncode == 0:
                    return c
            except Exception:
                pass

    for c in candidates:
        if c.exists() and "python" in c.name.lower():
            return c
    return Path(sys.executable)


# ==========================================
# TEMPLATE 1: Global ID Indexing
# ==========================================
SCENE_TEMPLATE_GLOBAL_ID = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadGrid, MemoryLane, ThreadItem

class CudaGlobalIdScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("CUDA 全局索引映射", "CPU 串行循环思维 vs GPU 空间升维")
        code_badge = self.create_code_badge("int idx = threadIdx.x;  // 隐患：单块正常，多块冲突", position=UP * 2.0)
        
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        grid = ThreadGrid(num_blocks=1, threads_per_block=4, block_spacing=0.8)
        grid.move_to(UP * 0.2 + LEFT * 3.0)

        memory = MemoryLane(num_slots=8, slot_width=0.85)
        memory.move_to(DOWN * 2.5)

        self.play(FadeIn(grid), FadeIn(memory), run_time={b1_action_time} * 0.6)

        t0 = grid.get_thread(0, 0)
        arrow_t0 = Arrow(start=t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_DEFAULT, buff=0.1)
        
        self.play(GrowArrow(arrow_t0), run_time=0.8)
        memory.get_slot(0).set_value("T0", color=THREAD_DEFAULT)
        self.wait({b1_pause})

        new_grid = ThreadGrid(num_blocks=2, threads_per_block=4, block_spacing=1.2)
        new_grid.move_to(UP * 0.2)

        self.play(
            ReplacementTransform(grid, new_grid),
            FadeOut(arrow_t0),
            run_time={b2_action_time} * 0.4
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
            run_time={b2_action_time} * 0.6
        )

        memory.get_slot(0).flash_collision()
        warning = Text("! 致命物理地址覆写冲突 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        warning.next_to(code_badge, DOWN, buff=0.2)
        self.play(FadeIn(warning), run_time=0.5)
        self.wait({b2_pause})

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
            run_time={b3_action_time} * 0.7
        )
        self.deliberate_pause({b3_pause})
'''


# ==========================================
# TEMPLATE 2: Warp Divergence
# ==========================================
SCENE_TEMPLATE_WARP_DIVERGENCE = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadItem

class CudaWarpDivergenceScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("Warp 线程束分支分化", "SIMT 硬件锁步 vs 独立多分支假象")
        code_badge = self.create_code_badge("if (tid % 2 == 0) {{ ... }} else {{ ... }}", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(ORIGIN)
        warp_label = Text("Mini-Warp (4 线程锁步推进)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(threads, UP, buff=0.3)

        self.play(FadeIn(threads), FadeIn(warp_label), run_time={b1_action_time} * 0.6)
        self.wait({b1_pause})

        mask_label = Text("阶段 1: 分支 A 执行 (t1, t3 被硬件强制挂起)", font_size=FONT_SUBTITLE_SIZE - 4, color=WARP_COLOR_A)
        mask_label.move_to(DOWN * 1.5)

        self.play(
            threads[0].circle.animate.set_color(WARP_COLOR_A),
            threads[2].circle.animate.set_color(WARP_COLOR_A),
            threads[1].circle.animate.set_color(THREAD_IDLE),
            threads[3].circle.animate.set_color(THREAD_IDLE),
            FadeIn(mask_label),
            run_time={b2_action_time} * 0.5
        )

        mask_label_b = Text("阶段 2: 分支 B 执行 (t0, t2 被硬件强制挂起)", font_size=FONT_SUBTITLE_SIZE - 4, color=WARP_COLOR_B)
        mask_label_b.move_to(DOWN * 1.5)

        self.play(
            threads[0].circle.animate.set_color(THREAD_IDLE),
            threads[2].circle.animate.set_color(THREAD_IDLE),
            threads[1].circle.animate.set_color(WARP_COLOR_B),
            threads[3].circle.animate.set_color(WARP_COLOR_B),
            ReplacementTransform(mask_label, mask_label_b),
            run_time={b2_action_time} * 0.5
        )
        self.wait({b2_pause})

        self.play(FadeOut(mask_label_b), FadeOut(code_badge), run_time=0.4)
        summary_badge = self.create_code_badge("消除分支分化 = 算力吞吐翻倍 (Zero Divergence)", position=UP * 2.0)
        
        self.play(
            FadeIn(summary_badge),
            *[t.circle.animate.set_color(NVIDIA_GREEN) for t in threads],
            run_time={b3_action_time} * 0.6
        )

        self.deliberate_pause({b3_pause})
'''


# ==========================================
# TEMPLATE 3: Shared Memory Bank Conflict
# ==========================================
SCENE_TEMPLATE_BANK_CONFLICT = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaBankConflictScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("共享内存架构与 Bank 冲突", "32 Bank 并发访问 vs 串行排队陷阱")
        code_badge = self.create_code_badge("float val = s_data[tid]; // 无冲突：1 对 1 物理映射", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.4)
        t_label = Text("Threads (t0 - t3)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(threads, UP, buff=0.2)

        banks = VGroup(*[MemorySlot(address_idx=i, width=1.1, height=1.1) for i in range(4)]).arrange(RIGHT, buff=0.35)
        for i, b in enumerate(banks):
            b.addr_label.become(Text(f"Bank {{i}}", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(b.box, DOWN, buff=0.1))
            b.set_value(f"B{{i}}")
        banks.move_to(DOWN * 2.0)
        b_label = Text("Shared Memory Banks (32路并发物理模块)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(banks, UP, buff=0.2)

        self.play(FadeIn(threads), FadeIn(t_label), FadeIn(banks), FadeIn(b_label), run_time={b1_action_time} * 0.6)

        arrows = [
            Arrow(start=threads[i].circle.get_bottom(), end=banks[i].box.get_top(), color=NVIDIA_GREEN, buff=0.1)
            for i in range(4)
        ]
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), run_time=1.0)
        self.wait({b1_pause})

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
            run_time={b2_action_time} * 0.6
        )

        warning_lbl = Text("! 2-way Bank Conflict: 硬件被迫串行排队执行 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        warning_lbl.next_to(conflict_badge, DOWN, buff=0.2)
        self.play(FadeIn(warning_lbl), run_time=0.6)
        self.wait({b2_pause})

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
            run_time={b3_action_time} * 0.7
        )

        self.deliberate_pause({b3_pause})
'''


# ==========================================
# TEMPLATE 4: Coalesced Memory Access
# ==========================================
SCENE_TEMPLATE_COALESCED = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaCoalescedScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("全局内存合并访问 (Coalescing)", "128 字节总线事务 vs 离散跨步浪费")
        code_badge = self.create_code_badge("float val = d_in[idx]; // 连续线程访连续内存：100% 效率", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.5)

        bus_rect = RoundedRectangle(corner_radius=0.15, width=6.5, height=0.6, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9)
        bus_rect.move_to(DOWN * 0.6)
        bus_label = Text("GPU 显存总线事务 (128-Byte Transaction)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).move_to(bus_rect.get_center())

        slots = VGroup(*[MemorySlot(address_idx=i, width=0.85, height=0.85) for i in range(6)]).arrange(RIGHT, buff=0.2)
        slots.move_to(DOWN * 2.2)

        self.play(FadeIn(threads), FadeIn(bus_rect), FadeIn(bus_label), FadeIn(slots), run_time={b1_action_time} * 0.6)

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
            slots[i].set_value(f"t{{i}}", color=NVIDIA_GREEN)
        self.wait({b1_pause})

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
            run_time={b2_action_time} * 0.6
        )
        self.wait({b2_pause})

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
            run_time={b3_action_time} * 0.7
        )
        self.deliberate_pause({b3_pause})
'''


# ==========================================
# TEMPLATE 5: Atomic Operations & Race
# ==========================================
SCENE_TEMPLATE_ATOMIC = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaAtomicScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("原子操作与竞态条件", "并发覆写丢失 vs 硬件独占锁")
        code_badge = self.create_code_badge("*counter = *counter + 1; // 读改写非原子：海量增量丢失", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        t0 = ThreadItem(block_id=0, thread_id=0).move_to(UP * 0.4 + LEFT * 2.5)
        t1 = ThreadItem(block_id=0, thread_id=1).move_to(UP * 0.4 + RIGHT * 2.5)

        counter_box = Square(side_length=1.4, color=MEMORY_BORDER, fill_color=CARD_BG, fill_opacity=0.9).move_to(DOWN * 1.5)
        counter_lbl = Text("Counter: 0", font_size=FONT_SUBTITLE_SIZE, color=TEXT_PRIMARY, weight=BOLD).move_to(counter_box.get_center())
        c_desc = Text("Global Memory 共享累加器", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(counter_box, DOWN, buff=0.15)

        self.play(FadeIn(t0), FadeIn(t1), FadeIn(counter_box), FadeIn(counter_lbl), FadeIn(c_desc), run_time={b1_action_time} * 0.6)

        a0 = Arrow(start=t0.circle.get_bottom(), end=counter_box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        a1 = Arrow(start=t1.circle.get_bottom(), end=counter_box.get_top(), color=THREAD_CONFLICT, buff=0.1)

        self.play(GrowArrow(a0), GrowArrow(a1), run_time=0.8)
        counter_lbl.become(Text("Counter: 1 (!)", font_size=FONT_SUBTITLE_SIZE, color=THREAD_CONFLICT, weight=BOLD).move_to(counter_box.get_center()))
        counter_box.set_color(THREAD_CONFLICT)
        warn_text = Text("两线程并发加 1，结果竟然还是 1 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD).move_to(UP * 1.2)
        self.play(FadeIn(warn_text), run_time=0.6)
        self.wait({b1_pause})

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
        self.wait({b2_pause})

        summary_badge = self.create_code_badge("先局部规约，再全局原子 = 兼顾安全与超高吞吐", position=UP * 2.0)
        self.play(FadeOut(atomic_badge), FadeIn(summary_badge), run_time=0.5)
        self.play(
            t0.circle.animate.set_color(THREAD_RESOLVED),
            t1.circle.animate.set_color(THREAD_RESOLVED),
            run_time={b3_action_time} * 0.7
        )
        self.deliberate_pause({b3_pause})
'''


# ==========================================
# TEMPLATE 6: Syncthreads & Barrier Safety
# ==========================================
SCENE_TEMPLATE_SYNCTHREADS = '''# -*- coding: utf-8 -*-
from manim import *
import sys
from pathlib import Path

# Load project modules
sys.path.insert(0, r"{project_root}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class CudaSyncthreadsScene(CUDAThemeScene):
    def construct(self):
        super().construct()

        header = self.create_header("块内线程同步屏障 (__syncthreads)", "步调异步脏读 vs 分支内屏障死锁禁忌")
        code_badge = self.create_code_badge("if (tid % 2 == 0) {{ __syncthreads(); }} // 致命禁忌：死锁挂起！", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={b1_action_time} * 0.4)

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=1.0)
        threads.move_to(UP * 0.5)

        barrier = DashedLine(start=LEFT * 4.5, end=RIGHT * 4.5, color=THREAD_CONFLICT, dash_length=0.2, stroke_width=4)
        barrier.move_to(DOWN * 1.0)
        barrier_lbl = Text("同步栅栏 (__syncthreads Barrier)", font_size=FONT_BADGE_SIZE, color=THREAD_CONFLICT).next_to(barrier, UP, buff=0.15)

        self.play(FadeIn(threads), FadeIn(barrier), FadeIn(barrier_lbl), run_time={b1_action_time} * 0.6)

        self.play(
            threads[0].animate.move_to(DOWN * 0.8 + LEFT * 1.5),
            threads[2].animate.move_to(DOWN * 0.8 + RIGHT * 1.5),
            threads[1].animate.move_to(UP * 1.5 + LEFT * 0.5),
            threads[3].animate.move_to(UP * 1.5 + RIGHT * 0.5),
            run_time={b2_action_time} * 0.5
        )

        deadlock_box = Text("! 硬件永久死锁 (Deadlock): 未走分支线程永不到达 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD)
        deadlock_box.next_to(barrier, DOWN, buff=0.3)
        self.play(FadeIn(deadlock_box), run_time=0.6)
        self.wait({b2_pause})

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
            run_time={b3_action_time} * 0.7
        )
        self.deliberate_pause({b3_pause})
'''


class ManimEngine:
    def __init__(self):
        self.scenes_dir = config.OUTPUT_DIR / "manim_scenes"
        self.videos_dir = config.OUTPUT_DIR / "videos"
        self.scenes_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.python_bin = find_python_interpreter()
        print(f"[*] ManimEngine: Using Python Interpreter -> {self.python_bin}")

    def generate_code_for_timeline(self, timeline: Dict[str, Any]) -> Tuple[Path, str]:
        """Generates Python Manim code dynamically populated with audio timeline durations."""
        chunk_id = timeline["chunk_id"]
        beats = timeline.get("beats", [])

        num_beats = len(beats)
        if num_beats >= 3:
            b1_time = beats[0].get("action_duration", 2.0)
            b1_pause = beats[0].get("pause_buffer", 0.5)

            # Sum middle beats for Chapter 2
            b2_time = sum(b.get("action_duration", 2.0) for b in beats[1:-1])
            b2_pause = sum(b.get("pause_buffer", 0.8) for b in beats[1:-1])

            # Final beat for Chapter 3
            b3_time = beats[-1].get("action_duration", 3.0)
            b3_pause = beats[-1].get("pause_buffer", 2.0)
        elif num_beats == 2:
            b1_time = beats[0].get("action_duration", 2.0)
            b1_pause = beats[0].get("pause_buffer", 0.5)
            b2_time = beats[1].get("action_duration", 2.5)
            b2_pause = beats[1].get("pause_buffer", 0.8)
            b3_time, b3_pause = 3.0, 2.0
        else:
            b1_time, b1_pause = 2.0, 0.5
            b2_time, b2_pause = 2.5, 0.8
            b3_time, b3_pause = 3.0, 2.0

        # Intelligent Semantic Router for all CUDA architectural topics
        cid = chunk_id.lower()
        if any(k in cid for k in ["warp", "diverge", "simt", "branch", "lockstep"]):
            template = SCENE_TEMPLATE_WARP_DIVERGENCE
            scene_class = "CudaWarpDivergenceScene"
        elif any(k in cid for k in ["bank", "shared", "smem", "tile"]):
            template = SCENE_TEMPLATE_BANK_CONFLICT
            scene_class = "CudaBankConflictScene"
        elif any(k in cid for k in ["coalesce", "dram", "global_mem", "memory_space", "stride"]):
            template = SCENE_TEMPLATE_COALESCED
            scene_class = "CudaCoalescedScene"
        elif any(k in cid for k in ["atomic", "race", "mutex", "lock", "conflict"]):
            template = SCENE_TEMPLATE_ATOMIC
            scene_class = "CudaAtomicScene"
        elif any(k in cid for k in ["sync", "barrier", "cooperative", "async"]):
            template = SCENE_TEMPLATE_SYNCTHREADS
            scene_class = "CudaSyncthreadsScene"
        else:
            # Default to Thread Hierarchy, Grid & Linear Mapping
            template = SCENE_TEMPLATE_GLOBAL_ID
            scene_class = "CudaGlobalIdScene"

        code_str = template.format(
            project_root=str(config.BASE_DIR).replace("\\", "\\\\"),
            b1_action_time=round(b1_time, 2),
            b1_pause=round(b1_pause, 2),
            b2_action_time=round(b2_time, 2),
            b2_pause=round(b2_pause, 2),
            b3_action_time=round(b3_time, 2),
            b3_pause=round(b3_pause, 2)
        )

        scene_file = self.scenes_dir / f"{chunk_id}_scene.py"
        with open(scene_file, "w", encoding="utf-8") as f:
            f.write(code_str)

        print(f"[+] Layer 4: Generated Manim scene code in {scene_file.name}")
        return scene_file, scene_class

    def render_scene(self, scene_file: Path, scene_class: str, quality: str = "-qm") -> Optional[Path]:
        """Executes Manim rendering with automatic traceback capture and self-healing loop."""
        print(f"[*] Layer 4: Rendering scene '{scene_class}' via Manim ({quality})...")

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            cmd = [
                str(self.python_bin),
                "-m", "manim",
                quality,
                "--disable_caching",
                str(scene_file),
                scene_class,
                "--media_dir", str(config.OUTPUT_DIR / "manim_media")
            ]

            env = os.environ.copy()
            scripts_dir = str(config.BASE_DIR / ".venv" / "Scripts")
            env["PATH"] = f"{scripts_dir};" + env.get("PATH", "")

            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )

            if proc.returncode == 0:
                print(f"[+] Render succeeded on attempt {attempt}!")
                media_root = config.OUTPUT_DIR / "manim_media" / "videos" / scene_file.stem
                if not media_root.exists():
                    media_root = config.OUTPUT_DIR / "manim_media"

                # Filter out partial movie clips
                candidates = [f for f in media_root.rglob("*.mp4") if "partial_movie_files" not in str(f)]
                candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                if candidates:
                    raw_mp4 = candidates[0]
                    target_mp4 = self.videos_dir / f"{scene_file.stem}_raw.mp4"
                    if target_mp4.exists():
                        target_mp4.unlink()
                    shutil.copy2(raw_mp4, target_mp4)
                    print(f"[+] Output Raw Video: {target_mp4}")
                    return target_mp4
                else:
                    # Fallback search across output dir
                    fallback = [
                        f for f in config.OUTPUT_DIR.rglob("*.mp4")
                        if "partial_movie_files" not in str(f)
                        and not f.name.endswith("_final.mp4")
                        and not f.name.endswith("_raw.mp4")
                    ]
                    fallback.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    if fallback:
                        raw_mp4 = fallback[0]
                        target_mp4 = self.videos_dir / f"{scene_file.stem}_raw.mp4"
                        if target_mp4.exists():
                            target_mp4.unlink()
                        shutil.copy2(raw_mp4, target_mp4)
                        print(f"[+] Output Raw Video (via fallback): {target_mp4}")
                        return target_mp4

                    print(f"[Warning] Could not find rendered mp4 in {media_root}.")
                    return None
            else:
                stderr_text = proc.stderr
                print(f"[!] Render failed on attempt {attempt}: {stderr_text[-500:]}")
                if attempt < max_retries:
                    self._self_heal_script(scene_file, stderr_text)

        return None

    def _self_heal_script(self, scene_file: Path, traceback_text: str):
        """Autonomous self-healing logic for known Manim edge cases."""
        print("[*] Running Autonomous Self-Healing on scene file...")
        content = scene_file.read_text(encoding="utf-8")

        if "font" in traceback_text.lower():
            content = re.sub(r'font="[^"]*"', '', content)

        if "latex" in traceback_text.lower() or "dvisvgm" in traceback_text.lower():
            content = content.replace("MathTex", "Text")

        if "AttributeError" in traceback_text and "ReplacementTransform" in traceback_text:
            content = content.replace("ReplacementTransform", "Transform")

        scene_file.write_text(content, encoding="utf-8")
        print("[+] Applied self-healing patches to script.")
