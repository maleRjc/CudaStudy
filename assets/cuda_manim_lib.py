"""
CUDA Educational Manim Prefabs Library (cuda_manim_lib)
Provides high-level, rock-solid reusable visual components for CUDA architectural animations.
Prevents LLMs from writing brittle raw low-level coordinates.
"""

from manim import *
import sys
from pathlib import Path

# Add project root to path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assets.styles import *


class CUDAThemeScene(Scene):
    """Base scene configured with modern dark aesthetic and pedagogical helpers."""
    def construct(self):
        self.camera.background_color = BG_DARK

    def create_header(self, title_text: str, subtitle_text: str = ""):
        """Creates standard top zone header banner."""
        title = Text(title_text, font_size=FONT_TITLE_SIZE, color=TEXT_PRIMARY, weight=BOLD)
        title.to_edge(UP, buff=0.4)
        group = VGroup(title)

        if subtitle_text:
            sub = Text(subtitle_text, font_size=FONT_SUBTITLE_SIZE, color=NVIDIA_GREEN)
            sub.next_to(title, DOWN, buff=0.15)
            group.add(sub)

        return group

    def create_code_badge(self, code_text: str, position=UP):
        """Creates a modern rounded code block container."""
        code_lbl = Text(code_text, font="Consolas", font_size=FONT_CODE_SIZE, color=TEXT_CODE)
        bg = SurroundingRectangle(code_lbl, color=CARD_BORDER, fill_color=CARD_BG, fill_opacity=0.9, corner_radius=0.15, buff=0.2)
        return VGroup(bg, code_lbl).move_to(position)

    def deliberate_pause(self, seconds: float = 1.8, label: str = "工作记忆整合 · 认知沉淀"):
        """Pedagogical deliberate silence moment to let viewers digest the insight."""
        if seconds <= 0:
            return
        # Subtle progress indicator or simple wait
        self.wait(seconds)


class ThreadItem(VGroup):
    """Visual entity representing a single CUDA Thread with its local and global identities."""
    def __init__(self, block_id: int, thread_id: int, global_id: int = None, radius: float = 0.28, **kwargs):
        super().__init__(**kwargs)
        self.block_id = block_id
        self.thread_id = thread_id
        self.global_id = global_id if global_id is not None else (block_id * 4 + thread_id)
        
        # Circle body
        self.circle = Circle(radius=radius, color=THREAD_DEFAULT, fill_color=THREAD_DEFAULT, fill_opacity=0.85)
        # ThreadIdx label
        self.label = Text(f"t{thread_id}", font_size=FONT_BADGE_SIZE, color=BG_DARK, weight=BOLD)
        self.label.move_to(self.circle.get_center())
        
        self.add(self.circle, self.label)

    def set_conflict_state(self):
        """Visually indicate a race condition / write conflict."""
        self.circle.set_color(THREAD_CONFLICT)
        self.circle.set_fill(THREAD_CONFLICT, opacity=0.95)

    def set_resolved_state(self, new_label: str = None):
        """Visually indicate correct identity mapping."""
        self.circle.set_color(THREAD_RESOLVED)
        self.circle.set_fill(THREAD_RESOLVED, opacity=0.9)
        if new_label:
            new_text = Text(new_label, font_size=FONT_BADGE_SIZE - 2, color=BG_DARK, weight=BOLD)
            new_text.move_to(self.circle.get_center())
            self.remove(self.label)
            self.label = new_text
            self.add(self.label)


class BlockContainer(VGroup):
    """A CUDA Thread Block container holding threads."""
    def __init__(self, block_id: int, num_threads: int = 4, thread_spacing: float = 0.8, **kwargs):
        super().__init__(**kwargs)
        self.block_id = block_id
        self.threads = []

        # Create threads in a horizontal row
        thread_group = VGroup()
        for t_idx in range(num_threads):
            t = ThreadItem(block_id=block_id, thread_id=t_idx)
            t.shift(RIGHT * (t_idx * thread_spacing))
            self.threads.append(t)
            thread_group.add(t)

        thread_group.move_to(ORIGIN)

        # Surrounding dashed box
        padding = 0.35
        rect = RoundedRectangle(
            corner_radius=0.2,
            width=thread_group.width + padding * 2,
            height=thread_group.height + padding * 2,
            color=NVIDIA_GREEN,
            stroke_width=2,
            stroke_opacity=0.7
        )
        rect.move_to(thread_group.get_center())

        # Block label at top
        lbl = Text(f"Block {block_id}", font_size=FONT_SUBTITLE_SIZE - 4, color=NVIDIA_GREEN, weight=BOLD)
        lbl.next_to(rect, UP, buff=0.15)

        self.box = rect
        self.block_label = lbl
        self.thread_group = thread_group

        self.add(self.box, self.block_label, self.thread_group)

    def get_thread(self, thread_idx: int) -> ThreadItem:
        return self.threads[thread_idx]


class ThreadGrid(VGroup):
    """Grid of multiple Blocks."""
    def __init__(self, num_blocks: int = 2, threads_per_block: int = 4, block_spacing: float = 0.6, **kwargs):
        super().__init__(**kwargs)
        self.blocks = []

        for b_idx in range(num_blocks):
            blk = BlockContainer(block_id=b_idx, num_threads=threads_per_block)
            self.blocks.append(blk)
            self.add(blk)

        self.arrange(RIGHT, buff=block_spacing)

    def get_thread(self, block_idx: int, thread_idx: int) -> ThreadItem:
        return self.blocks[block_idx].get_thread(thread_idx)


class MemorySlot(VGroup):
    """Individual address cell in linear physical memory."""
    def __init__(self, address_idx: int, width: float = 0.9, height: float = 0.9, **kwargs):
        super().__init__(**kwargs)
        self.address_idx = address_idx
        
        self.box = Square(side_length=width, color=MEMORY_BORDER, fill_color=MEMORY_BG, fill_opacity=0.85)
        self.addr_label = Text(f"[{address_idx}]", font_size=FONT_BADGE_SIZE - 2, color=TEXT_SECONDARY)
        self.addr_label.next_to(self.box, DOWN, buff=0.1)
        
        self.val_label = Text("", font_size=FONT_BADGE_SIZE, color=TEXT_PRIMARY, weight=BOLD)
        self.val_label.move_to(self.box.get_center())

        self.add(self.box, self.addr_label, self.val_label)

    def set_value(self, text: str, color=TEXT_PRIMARY):
        self.val_label.become(Text(text, font_size=FONT_BADGE_SIZE, color=color, weight=BOLD).move_to(self.box.get_center()))

    def flash_collision(self):
        self.box.set_color(THREAD_CONFLICT)
        self.box.set_fill(THREAD_CONFLICT, opacity=0.8)


class MemoryLane(VGroup):
    """Contiguous horizontal linear memory strip."""
    def __init__(self, num_slots: int = 8, slot_width: float = 0.85, **kwargs):
        super().__init__(**kwargs)
        self.slots = []

        for i in range(num_slots):
            slot = MemorySlot(address_idx=i, width=slot_width)
            self.slots.append(slot)
            self.add(slot)

        self.arrange(RIGHT, buff=0.15)

        title = Text("Global Memory (Linear DRAM)", font_size=FONT_SUBTITLE_SIZE - 6, color=TEXT_SECONDARY)
        title.next_to(self, UP, buff=0.2)
        self.header = title
        self.add(title)

    def get_slot(self, idx: int) -> MemorySlot:
        return self.slots[idx]


class Warp32Grid(VGroup):
    """
    32-Thread Hardware Warp Execution Unit (Based on NVIDIA CUDA 13.3 SIMT Architecture).
    Organized as 4 rows x 8 columns = 32 physical threads in lockstep execution.
    """
    def __init__(self, warp_id: int = 0, cell_size: float = 0.42, buff: float = 0.08, **kwargs):
        super().__init__(**kwargs)
        self.warp_id = warp_id
        self.cell_size = cell_size
        self.threads = []

        grid_group = VGroup()
        for r in range(4):
            row_group = VGroup()
            for c in range(8):
                tid = r * 8 + c
                box = Square(side_length=cell_size, color=NVIDIA_GREEN, fill_color=BG_DARK, fill_opacity=0.9, stroke_width=1.5)
                lbl = Text(str(tid), font_size=FONT_BADGE_SIZE - 4, color=TEXT_PRIMARY, weight=BOLD)
                lbl.move_to(box.get_center())
                t_item = VGroup(box, lbl)
                t_item.tid = tid
                t_item.box = box
                t_item.lbl = lbl
                self.threads.append(t_item)
                row_group.add(t_item)
            row_group.arrange(RIGHT, buff=buff)
            grid_group.add(row_group)

        grid_group.arrange(DOWN, buff=buff)
        self.grid_group = grid_group

        # Outer Warp Boundary
        self.outer_border = SurroundingRectangle(
            grid_group,
            color=NVIDIA_GREEN,
            buff=0.15,
            corner_radius=0.12,
            stroke_width=2
        )
        self.title_lbl = Text(f"Warp {warp_id} · 32 硬件线程 (SIMT 锁步执行束)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN, weight=BOLD)
        self.title_lbl.next_to(self.outer_border, UP, buff=0.12)

        self.add(self.outer_border, self.title_lbl, self.grid_group)

    def get_thread(self, tid: int) -> VGroup:
        return self.threads[tid]

    def set_thread_active(self, tid: int, is_active: bool, active_color=NVIDIA_GREEN, idle_color=THREAD_IDLE):
        t = self.threads[tid]
        if is_active:
            t.box.set_color(active_color)
            t.box.set_fill(active_color, opacity=0.85)
            t.lbl.set_color(BG_DARK)
        else:
            t.box.set_color(idle_color)
            t.box.set_fill(CARD_BG, opacity=0.4)
            t.lbl.set_color(TEXT_SECONDARY)

    def set_divergence_mask(self, branch_a_tids: list, branch_b_tids: list):
        """Highlights SIMT branch divergence between two sets of thread IDs."""
        for tid in branch_a_tids:
            self.set_thread_active(tid, True, active_color=WARP_COLOR_A)
        for tid in branch_b_tids:
            self.set_thread_active(tid, False, idle_color=WARP_COLOR_B)


class HostDeviceFlowDiagram(VGroup):
    """
    Host to Device Pipeline Overview (Derived from 'CUDA GPU执行架构流程图.png').
    Shows CPU Host Software layer -> PCIe Launch -> GPU Device Hardware SM layer.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Host Box (Left)
        host_bg = RoundedRectangle(corner_radius=0.15, width=3.8, height=3.6, color=BLUE_C, fill_color=CARD_BG, fill_opacity=0.9)
        host_title = Text("CPU 端 (Host 软件抽象)", font_size=FONT_BADGE_SIZE + 2, color=BLUE_C, weight=BOLD).next_to(host_bg.get_top(), DOWN, buff=0.2)
        host_app = Text("1. 应用程序 (CUDA App)", font_size=FONT_BADGE_SIZE - 2, color=TEXT_PRIMARY).next_to(host_title, DOWN, buff=0.25)
        host_launch = Text("2. vectorAdd<<<Grid, Block>>>()", font_size=FONT_BADGE_SIZE - 4, color=TEXT_CODE).next_to(host_app, DOWN, buff=0.2)
        host_pcie = Text("3. 提交任务至硬件队列", font_size=FONT_BADGE_SIZE - 2, color=TEXT_SECONDARY).next_to(host_launch, DOWN, buff=0.2)
        self.host_group = VGroup(host_bg, host_title, host_app, host_launch, host_pcie).move_to(LEFT * 4.2)

        # Device Box (Right)
        dev_bg = RoundedRectangle(corner_radius=0.15, width=4.8, height=3.6, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9)
        dev_title = Text("GPU 端 (Device 硬件执行)", font_size=FONT_BADGE_SIZE + 2, color=NVIDIA_GREEN, weight=BOLD).next_to(dev_bg.get_top(), DOWN, buff=0.2)
        grid_lbl = Text("Grid -> [Block 0] [Block 1] ... [Block N-1]", font_size=FONT_BADGE_SIZE - 3, color=TEXT_PRIMARY).next_to(dev_title, DOWN, buff=0.25)
        sched_lbl = Text("硬件调度器 (GigaThread Scheduler)", font_size=FONT_BADGE_SIZE - 4, color=WARP_COLOR_A).next_to(grid_lbl, DOWN, buff=0.2)
        sm_lbl = Text("分配至 SM 阵列 · 32 线程 Warp 锁步执行", font_size=FONT_BADGE_SIZE - 3, color=NVIDIA_GREEN).next_to(sched_lbl, DOWN, buff=0.2)
        self.device_group = VGroup(dev_bg, dev_title, grid_lbl, sched_lbl, sm_lbl).move_to(RIGHT * 2.2)

        # PCIe Launch Arrow (Center)
        self.launch_arrow = Arrow(
            start=self.host_group.get_right(),
            end=self.device_group.get_left(),
            color=NVIDIA_GREEN,
            stroke_width=4,
            buff=0.15
        )
        self.launch_lbl = Text("PCIe 启动\n(Kernel Launch)", font_size=FONT_BADGE_SIZE - 4, color=NVIDIA_GREEN, weight=BOLD).next_to(self.launch_arrow, UP, buff=0.1)

        self.add(self.host_group, self.device_group, self.launch_arrow, self.launch_lbl)


class DRAMBusTransaction(VGroup):
    """
    128-Byte DRAM Bus Transaction Alignment & Coalescing Visualizer.
    Demonstrates 32 threads coalescing into a single memory sector transaction.
    """
    def __init__(self, is_coalesced: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.is_coalesced = is_coalesced

        # Main Bus Bar
        color = NVIDIA_GREEN if is_coalesced else THREAD_CONFLICT
        self.bus_bar = RoundedRectangle(corner_radius=0.1, width=7.2, height=0.6, color=color, fill_color=CARD_BG, fill_opacity=0.95)
        status_txt = "128-Byte 连续物理扇区对齐 (1 次总线事务 · 100% 满带宽)" if is_coalesced else "非对齐跨步离散访存 (事务分裂为多次 · 吞吐暴跌至 25%)"
        self.bus_lbl = Text(status_txt, font_size=FONT_BADGE_SIZE - 2, color=color, weight=BOLD).move_to(self.bus_bar.get_center())

        self.add(self.bus_bar, self.bus_lbl)
