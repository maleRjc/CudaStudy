"""
DeepSeek-Powered Pedagogical Director & Autonomous Animation Choreographer for CUDA.
Adheres strictly to 'CUDA原理与实现教学视频项目实施文档.docx' and 'CUDA GPU执行架构流程图.png'.
Provides end-to-end Course Design, Animation Opportunity Curation, Visual Choreography,
and Dynamic Manim Code Generation via DeepSeek API with resilient fallback.
"""

import json
import os
import re
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import config


# =====================================================================
# 1. Comprehensive Pedagogical Knowledge Base (from Project Implementation Doc)
# =====================================================================
CURRICULUM_30_EPISODES: List[Dict[str, Any]] = [
    # 模块一：认识 GPU 和 CUDA
    {
        "ep_id": "01",
        "module": "模块一：认识 GPU 和 CUDA",
        "title": "为什么需要 GPU？CPU 和 GPU 的本质区别",
        "duration": "10 分钟",
        "question": "既然 CPU 主频高达 5GHz 且单核极强，为什么图像渲染和 AI 计算还需要 GPU？",
        "metaphor": "数位顶尖数学家 (CPU 强单核低延迟) vs 数千名小学生组成的高速算盘阵列 (GPU 极高吞吐)",
        "needs_animation": True,
        "animation_reason": "宏观硬件拓扑与算力密度差异必须动态呈现，展示 CPU 缓存/控制单元占主导 vs GPU 计算单元 (ALU) 密布占主导。",
        "animation_spec": {
            "type": "2D 硬件微架构对比",
            "visual_focus": "芯片晶圆面积结构对比：CPU 的大面积 L3 Cache 与分支预测器 vs GPU 的海量计算核阵列与高带宽显存总线",
            "beats": [
                {"title": "吞吐困境", "action": "单任务串行流水线 vs 海量数据点同时到达", "duration": 4.0},
                {"title": "芯片解构", "action": "动态切分展示 CPU 与 GPU 的晶圆资源占比动画", "duration": 5.0},
                {"title": "架构定论", "action": "展示延迟优化型架构与吞吐优化型架构的本质分工", "duration": 4.0}
            ]
        },
        "guide_pages": "P1-P15"
    },
    {
        "ep_id": "02",
        "module": "模块一：认识 GPU 和 CUDA",
        "title": "CUDA 是什么？它解决什么问题？",
        "duration": "10 分钟",
        "question": "在没有 CUDA 之前人们怎么用显卡计算？CUDA 如何打通通用计算 (GPGPU) 的软件栈？",
        "metaphor": "从必须伪装成三角形着色器的图形画笔，到可以直接书写 C++ 的通用工业母机",
        "needs_animation": True,
        "animation_reason": "CUDA 软件栈层级（Driver API, Runtime API, Toolkit, NVCC）及其与硬件的映射是抽象概念，动态调用栈流动能直观建构认知。",
        "animation_spec": {
            "type": "分层系统架构与调用流",
            "visual_focus": "CUDA Runtime -> NVIDIA Driver -> GPU Compute Engine 的层级渗透与指令流向",
            "beats": [
                {"title": "历史痛点", "action": "图形渲染 API (OpenGL/DirectX) 复杂伪装", "duration": 3.5},
                {"title": "CUDA 栈层", "action": "分层展开 CUDA Runtime, Driver, NVCC 编译流", "duration": 5.0},
                {"title": "全景落地", "action": "展示标准 C++ 扩展语法如何直达硬件指令", "duration": 4.0}
            ]
        },
        "guide_pages": "P15-P25"
    },
    {
        "ep_id": "03",
        "module": "模块一：认识 GPU 和 CUDA",
        "title": "CPU 和 GPU 如何协同工作？Host 与 Device 的执行流",
        "duration": "12 分钟",
        "question": "CPU 和 GPU 拥有各自独立的物理内存，一段程序到底是在哪一侧运行？任务是如何分工提交的？",
        "metaphor": "项目经理 (Host CPU 负责调度和统筹) 与 工厂车间 (Device GPU 负责高并发流水线加工)",
        "needs_animation": True,
        "animation_reason": "必须完整展示从 Host 到 Device 的任务调度流程，这是《CUDA GPU执行架构流程图》的核心骨架。",
        "animation_spec": {
            "type": "Host-Device 全链路时空流",
            "visual_focus": "应用程序调用 Kernel -> PCIe 总线传输数据与启动参数 -> GigaThread 引擎派发至 SM 阵列",
            "beats": [
                {"title": "Host 侧提交", "action": "CPU 准备内存指针并调用 kernel<<<grid, block>>>", "duration": 4.0},
                {"title": "PCIe 飞跃", "action": "数据从 Host 内存经 PCIe 灌入 Device 显存并触发指令队列", "duration": 5.0},
                {"title": "Device 接管", "action": "硬件调度器接管任务，多 SM 并行启动，CPU 异步继续向下执行", "duration": 4.5}
            ]
        },
        "guide_pages": "P20-P30"
    },
    {
        "ep_id": "04",
        "module": "模块一：认识 GPU 和 CUDA",
        "title": "GPU 内部结构：SM 是什么？",
        "duration": "12 分钟",
        "question": "常说的 128 个 SM、数千个 CUDA Core 究竟是如何组织的？SM 内部包含哪些关键硬件？",
        "metaphor": "GPU 是一个工业园区，每个 SM 就是一个具备独立供水供电、车间主任和流水线的现代化车间",
        "needs_animation": True,
        "animation_reason": "SM 内部包含 Warp Schedulers, Register File, Shared Memory, Warp Instruction Dispatchers，静态图无法看清调度脉络。",
        "animation_spec": {
            "type": "SM 物理微架构剖析",
            "visual_focus": "SM 切分为 4 个 Processing Block，每个子块配备独立 Warp 调度器和计算单元",
            "beats": [
                {"title": "芯片俯瞰", "action": "GPU 晶圆展开展示几十上百个 SM 阵列", "duration": 4.0},
                {"title": "SM 局部放大", "action": "拆解 SM：寄存器堆、共享内存/L1缓存、调度器与执行单元", "duration": 5.5},
                {"title": "资源边界", "action": "展示一个 SM 上同时驻留多个 Block 的硬件资源限制", "duration": 4.0}
            ]
        },
        "guide_pages": "P25-P40"
    },
    # 模块二：CUDA 并行编程模型
    {
        "ep_id": "05",
        "module": "模块二：CUDA 并行编程模型",
        "title": "Thread、Block、Grid 三者的关系：软件抽象模型",
        "duration": "15 分钟",
        "question": "数百万个线程是如何被逻辑组织的？为什么 CUDA 不直接分配一维线程池，而是设计 Block 和 Grid？",
        "metaphor": "士兵 (Thread) -> 作战班组 (Block 内可协作同步) -> 集团军 (Grid 宏观独立任务网格)",
        "needs_animation": True,
        "animation_reason": "核心心智模型：必须区分'软件逻辑层级'（Grid/Block）与'硬件执行资源'（SM），杜绝一个 Block 只能对应一个 SM 的新手误区。",
        "animation_spec": {
            "type": "层次化多维网格升维与物理分配",
            "visual_focus": "Grid 由多个 Block 组成，Block 由多个 Thread 组成；调度器将各 Block 动态分配到空闲 SM",
            "beats": [
                {"title": "逻辑网格划分", "action": "一维/二维 Grid 动态细分为多个 Thread Block", "duration": 4.5},
                {"title": "Block 内协作界限", "action": "展示 Block 内线程可通过片上共享内存和屏障同步协作，跨 Block 互不干扰", "duration": 5.0},
                {"title": "硬件动态派发", "action": "多个 Block 被硬件 GigaThread 调度器弹性分配到各个物理 SM", "duration": 5.0}
            ]
        },
        "guide_pages": "P20-P35"
    },
    {
        "ep_id": "06",
        "module": "模块二：CUDA 并行编程模型",
        "title": "Warp 和 SIMT：GPU 如何真正执行线程？",
        "duration": "15 分钟",
        "question": "GPU 真的能独立执行每个线程吗？32 线程的 Warp 锁步执行机制是如何工作的？",
        "metaphor": "32 位舞者组成的整齐仪仗队 (SIMT 锁步前进)：同喊一声口令，32 人同步踏出相同舞步",
        "needs_animation": True,
        "animation_reason": "Warp 是 GPU 硬件的基本执行束，SIMT 锁步与分支分化（Warp Divergence）必须通过动画展示掩码激活与串行执行！",
        "animation_spec": {
            "type": "32 线程 Warp 硬件网格与分支掩码",
            "visual_focus": "4x8 阵列的 32 个物理线程，面对 if-else 分支时，不同线程掩码激活/挂起的硬件时序",
            "beats": [
                {"title": "SIMT 锁步推进", "action": "单条指令发射，32 个绿色线程格子同时执行相同加法运算", "duration": 4.5},
                {"title": "分支分化撕裂", "action": "执行 if (tid % 2 == 0)：偶数线程亮起执行，奇数线程变灰挂起；随后倒转串行执行", "duration": 5.5},
                {"title": "性能断崖警示", "action": "吞吐减半警告与现代分支消除重构代码演示", "duration": 4.5}
            ]
        },
        "guide_pages": "P35-P50"
    },
    {
        "ep_id": "07",
        "module": "模块二：CUDA 并行编程模型",
        "title": "Kernel 是什么？如何启动 GPU 计算？",
        "duration": "12 分钟",
        "question": "带有 __global__ 修饰的函数有什么特殊之处？<<<grid, block>>> 这个神圣的三括号执行配置究竟传递了什么？",
        "metaphor": "印章指令与任务工单：CPU 刻下一枚印章模具，并指定生产几万个相同批次的产品",
        "needs_animation": False,
        "animation_reason": "本节重点在于 CUDA C++ 语法边界、Host 侧与 Device 侧符号修饰符，更适合左右对照式代码演练与卡片板书。",
        "guide_pages": "P25-P35"
    },
    {
        "ep_id": "08",
        "module": "模块二：CUDA 并行编程模型",
        "title": "从零编写第一个 CUDA 程序：Vector Add 全流程落地",
        "duration": "15 分钟",
        "question": "如何从零写出可以编译、运行并在 GPU 上产出正确结果的代码？内存申请、数据拷贝、Kernel 启动和释放全过程怎么串？",
        "metaphor": "从原料运入车间 (cudaMemcpy H2D)、机床加工 (kernel)、到成品送回仓库 (cudaMemcpy D2H) 的完整工单",
        "needs_animation": True,
        "animation_reason": "代码与硬件状态双向同步：左侧代码逐行高亮，右侧同步显示 CPU 内存与 GPU 显存内的数据状态变化。",
        "animation_spec": {
            "type": "代码执行与内存状态双轨联动",
            "visual_focus": "cudaMalloc -> cudaMemcpy -> VectorAdd<<<>>> -> cudaMemcpy 的全程数据指针流动",
            "beats": [
                {"title": "空间开辟", "action": "Host 和 Device 分别分配 1024 元素数组空间", "duration": 4.0},
                {"title": "核函数点火", "action": "代码高亮 kernel<<<4, 256>>>，GPU 瞬间唤醒 1024 个并行线程", "duration": 5.0},
                {"title": "结果验真", "action": "数据回传 Host 校验，显示加速比与正确性对比", "duration": 4.5}
            ]
        },
        "guide_pages": "P30-P45"
    },
    {
        "ep_id": "09",
        "module": "模块二：CUDA 并行编程模型",
        "title": "GPU 线程索引如何计算？从多维网格到一维物理地址的映射公式",
        "duration": "12 分钟",
        "question": "为什么每个初学者都必须死记硬背 int idx = blockIdx.x * blockDim.x + threadIdx.x？多维 (x, y, z) 索引如何推导？",
        "metaphor": "居民楼门牌号寻址：哪个单元 (blockIdx) * 每单元几户 (blockDim) + 几号房 (threadIdx)",
        "needs_animation": True,
        "animation_reason": "初学者最大的思维障碍是从 CPU 单指针循环转换为高维空间坐标投影，必须用几何展开动画直接破局！",
        "animation_spec": {
            "type": "高维几何网格展开映射至一维线性数组",
            "visual_focus": "二维 Block(x,y) 和 Thread(x,y) 如何通过行优先公式精确射向内存槽位",
            "beats": [
                {"title": "局部索引重合危机", "action": "只用 threadIdx.x 导致多个 Block 写入同一内存地址发生致命覆盖", "duration": 4.5},
                {"title": "全局升维公式推导", "action": "块基址 (blockIdx * blockDim) + 块内偏移几何拼接演示", "duration": 5.5},
                {"title": "二维矩阵平铺", "action": "二维图像坐标 (row, col) 映射为 row * width + col 的空间展开动画", "duration": 4.5}
            ]
        },
        "guide_pages": "P35-P55"
    },
    {
        "ep_id": "10",
        "module": "模块二：CUDA 并行编程模型",
        "title": "GPU 如何调度大量线程？Warp 调度器与延迟隐藏机制",
        "duration": "15 分钟",
        "question": "为什么 GPU 没有庞大的乱序执行引擎，却能轻松跑赢 CPU？什么是用算力换并发的'延迟隐藏'？",
        "metaphor": "餐厅服务员绝不等厨房炒好一道菜，而是立刻转身为下一桌点单（零开销上下文切换）",
        "needs_animation": True,
        "animation_reason": "Warp 调度器在长延迟访存期间无开销切换到下一个就绪 Warp，是理解 GPU 架构灵魂的核心。",
        "animation_spec": {
            "type": "Warp 调度时间轴与零开销切换",
            "visual_focus": "Warp 0 发起全局内存读取进入等待，Warp 调度器瞬间切到 Warp 1 执行算术指令",
            "beats": [
                {"title": "显存高延迟阻塞", "action": "Warp 0 停滞在加载指令，显存延迟倒计时 (400 周期)", "duration": 4.0},
                {"title": "调度器零开销切换", "action": "无需寄存器写回与栈保护，调度器在 1 个周期内切换到就绪的 Warp 1", "duration": 5.0},
                {"title": "管道填满延迟隐藏", "action": "海量活跃 Warp 轮番推进，算力单元利用率打满 100%", "duration": 5.0}
            ]
        },
        "guide_pages": "P45-P65"
    },
    # 模块三：GPU 内存体系
    {
        "ep_id": "11",
        "module": "模块三：GPU 内存体系",
        "title": "GPU 内存体系全解析：从寄存器到全局内存的物理版图",
        "duration": "18 分钟",
        "question": "为什么一个程序运行速度能相差数百倍？不同存储空间的容量、延迟、作用域和生命周期有何本质区别？",
        "metaphor": "办公桌桌面 (寄存器 · 瞬时随手可取) -> 办公室文件柜 (共享内存 · 部门共享) -> 郊区总仓库 (全局显存 · 远距离运输)",
        "needs_animation": True,
        "animation_reason": "必须完整展示 GPU 金字塔存储体系与数据在不同层级之间的流动关系与带宽落差。",
        "animation_spec": {
            "type": "GPU 存储金字塔与带宽延迟阶梯",
            "visual_focus": "Registers (0 周期) -> Shared Mem (数周期) -> L2 Cache -> Global Memory (数百周期)",
            "beats": [
                {"title": "金字塔层级展开", "action": "从 SM 内部片上资源逐级拉远到外部 GDDR/HBM 芯片", "duration": 5.0},
                {"title": "物理距离与时延对比", "action": "光信号走过不同层级所需时钟周期水银柱对比动画", "duration": 5.5},
                {"title": "作用域生命周期矩阵", "action": "线程私有、块内共享与跨块全局可见的视觉边界框", "duration": 4.5}
            ]
        },
        "guide_pages": "P60-P85"
    },
    {
        "ep_id": "12",
        "module": "模块三：GPU 内存体系",
        "title": "Global Memory 与数据传输：显存带宽极限与总线瓶颈",
        "duration": "15 分钟",
        "question": "为什么说 PCIe 总线是 CUDA 计算的第一大杀手？如何避免数据在 Host 与 Device 之间做低效搬运？",
        "metaphor": "高铁飞驰却被城际公路收费站卡死：计算只需 1 毫秒，数据搬运却花 100 毫秒",
        "needs_animation": True,
        "animation_reason": "展示计算强度（Arithmetic Intensity）与 Roofline 模型，直观揭示访存受限（Memory Bound）现象。",
        "animation_spec": {
            "type": "Roofline 模型与带宽瓶颈管道流",
            "visual_focus": "PCIe 带宽 (数十 GB/s) vs HBM 显存带宽 (数 TB/s) vs 核心算力 (数十 TFLOPS)",
            "beats": [
                {"title": "总线吞吐对比", "action": "两条粗细相差数十倍的管道灌水动画直观对比带宽差距", "duration": 4.5},
                {"title": "原地计算原则", "action": "多次 Kernel 计算保持数据留在显存中，避免频繁倒回 CPU", "duration": 5.0},
                {"title": "异步流传输预告", "action": "多流重叠传输与计算的时序预演", "duration": 4.5}
            ]
        },
        "guide_pages": "P70-P95"
    },
    {
        "ep_id": "13",
        "module": "模块三：GPU 内存体系",
        "title": "Shared Memory 的工作原理：片上高速协作缓存与数据复用",
        "duration": "18 分钟",
        "question": "同一个 Block 内的几百个线程如何高效共享中间结果？为什么共享内存能让矩阵乘法提速数十倍？",
        "metaphor": "车间内部的零件周转箱：大家把原材料集中搬到车间桌子上，互相传阅使用，不再每次跑仓库",
        "needs_animation": True,
        "animation_reason": "核心优化手段：展示数据从全局内存分批搬运到片上共享内存，以及被多线程反复读取利用的生命周期。",
        "animation_spec": {
            "type": "片上协作缓存与空间时间复用",
            "visual_focus": "多线程协作搬运分块 (Tile) -> __syncthreads() 集合点 -> 多次高频原地读取计算",
            "beats": [
                {"title": "显存重复读取浪费", "action": "每个线程独立访全局显存，产生海量重复长延迟请求", "duration": 4.5},
                {"title": "协同搬运进片上", "action": "每人搬一个元素装满 __shared__ 数组，一次搬运多次重用", "duration": 5.5},
                {"title": "性能爆发提速", "action": "显存访问次数降低 N 倍，吞吐量跃升", "duration": 4.5}
            ]
        },
        "guide_pages": "P85-P110"
    },
    {
        "ep_id": "14",
        "module": "模块三：GPU 内存体系",
        "title": "Register、Local Memory 与 Cache：警惕寄存器溢出 (Spilling)",
        "duration": "15 分钟",
        "question": "Local Memory 真的在'本地'吗？为什么寄存器用多了反而会导致程序性能急剧暴跌？",
        "metaphor": "桌面放不下堆到了地下仓库（Local Memory 实质上落入高延迟显存空间）",
        "needs_animation": True,
        "animation_reason": "Local Memory 命名的巨大误导性：必须通过动画揭示它虽然私有，物理上却落在极其缓慢的全局显存中。",
        "animation_spec": {
            "type": "寄存器溢出到高延迟物理显存的穿透图",
            "visual_focus": "线程寄存器超标时，编译器自动将变量溢出 (Spill) 到底层 DRAM，引发严重延迟",
            "beats": [
                {"title": "极速寄存器堆分配", "action": "物理寄存器资源按线程配额划分，超高速零延迟访问", "duration": 4.0},
                {"title": "溢出危机爆发", "action": "局部数组过大或变量过多，变量穿透落到底层 DRAM", "duration": 5.5},
                {"title": "编译器报告核查", "action": "--ptxas-options=-v 输出的 Spilling 警告解读", "duration": 4.0}
            ]
        },
        "guide_pages": "P95-P115"
    },
    {
        "ep_id": "15",
        "module": "模块三：GPU 内存体系",
        "title": "Unified Memory (统一内存) 的原理和底层 Page Fault 机制",
        "duration": "15 分钟",
        "question": "cudaMallocManaged 到底施了什么魔法让指针在 CPU 和 GPU 之间随意穿梭？缺页异常 (Page Fault) 是如何发生的？",
        "metaphor": "按需订购快递：不用提前把整车货物拉来，走到哪一页数据，顺丰专线立刻飞送哪一页",
        "needs_animation": True,
        "animation_reason": "统一内存让新手不用显式写 cudaMemcpy，但背后依赖缺页中断与页面迁移，动画展示页面按需搬运。",
        "animation_spec": {
            "type": "虚拟内存页表与按需页面迁移 (Page Fault)",
            "visual_focus": "GPU 访问未迁移页面触发 Page Fault -> 驱动通过 PCIe 迁移 4KB/2MB 内存页",
            "beats": [
                {"title": "单一指针假象", "action": "CPU 与 GPU 共享同个虚地址指针，掩盖物理隔离", "duration": 4.0},
                {"title": "Page Fault 缺页中断", "action": "GPU 第一次读取时停顿，驱动发起硬件页面迁移中断", "duration": 5.5},
                {"title": "cudaMemPrefetch 预取优化", "action": "引入预取 API 消除运行时阻塞停顿", "duration": 4.5}
            ]
        },
        "guide_pages": "P115-P135"
    },
    {
        "ep_id": "16",
        "module": "模块三：GPU 内存体系",
        "title": "为什么 GPU 内存访问会影响性能？访存与计算的失衡陷阱",
        "duration": "15 分钟",
        "question": "算力单元一直在空转？如何识别程序是 Compute-Bound 还是 Memory-Bound？",
        "metaphor": "超级大厨手速飞快，却一直眼巴巴等着送菜工把葱姜蒜送进厨房",
        "needs_animation": False,
        "animation_reason": "本节重点在于理论分析、Nsight Compute 指标解读与算力带宽平衡公式，适合板书与性能对照卡片。",
        "guide_pages": "P135-P150"
    },
    {
        "ep_id": "17",
        "module": "模块三：GPU 内存体系",
        "title": "Memory Coalescing (合并访问) 与 Bank Conflict (Bank冲突)：双重性能杀手",
        "duration": "18 分钟",
        "question": "为什么线程连续访问地址速度快 4 倍？为什么共享内存 32 个 Bank 会撞车串行？如何用 Padding 巧妙化解？",
        "metaphor": "合并访问：超市收银员一次扫描连号条形码；Bank冲突：32 个人同时挤向同一个取款机插槽",
        "needs_animation": True,
        "animation_reason": "这是整个 CUDA 性能优化的基石！必须用严谨的 128 字节总线扇区与 32 个物理 Bank 排队动画彻底讲透！",
        "animation_spec": {
            "type": "128-Byte 总线事务合并 vs 32-Bank 交叉互连交叉冲突",
            "visual_focus": "连续访存对齐 128-Byte 单次事务 vs 跨步离散分裂多次事务；Bank 0 双命中串行排队与 Padding 错位",
            "beats": [
                {"title": "合并访问完美合流", "action": "Warp 32 线程连续访存，硬件整合成 1 次 128 字节总线事务", "duration": 5.0},
                {"title": "跨步访问事务裂变", "action": "stride=2/4 访问导致事务分裂为 2 次、4 次甚至 32 次，带宽利用率断崖下跌", "duration": 5.5},
                {"title": "Bank 冲突与 Padding 破局", "action": "二维共享内存数组增加 padding 列消除对角线冲突动画", "duration": 5.5}
            ]
        },
        "guide_pages": "P150-P180"
    },
    # 模块四：CUDA 程序从代码到执行
    {
        "ep_id": "18",
        "module": "模块四：CUDA 程序从代码到执行",
        "title": "CUDA 程序的完整生命周期：从源码编写到硬件执行全链路",
        "duration": "18 分钟",
        "question": "一段包含 __global__ 的 .cu 代码，是怎样一步步变成 GPU 硅片上旋转跳跃的高低电平的？",
        "metaphor": "剧本创作 -> 导演分镜 (NVCC 分离) -> 道具准备与演员进场 (Runtime 加载) -> 舞台大幕拉开 (Kernel Launch)",
        "needs_animation": True,
        "animation_reason": "宏观全链路复盘，串联源代码、编译工具链、驱动加载、GPU 执行与结果回收，建立全局大地图。",
        "animation_spec": {
            "type": "全链路生命周期时间与空间演进",
            "visual_focus": "源代码 -> NVCC 双路分离 -> 驱动动态加载 -> GigaThread 调度 -> 计算输出",
            "beats": [
                {"title": "源码双路分离", "action": "Host 代码与 Device 代码在编译前端被切分", "duration": 4.5},
                {"title": "二进制封装与加载", "action": "生成的 cubin 嵌入可执行文件并由驱动注入设备", "duration": 5.0},
                {"title": "硬件闭环收尾", "action": "计算完成，通知 CPU，释放设备资源", "duration": 4.5}
            ]
        },
        "guide_pages": "P180-P210"
    },
    {
        "ep_id": "19",
        "module": "模块四：CUDA 程序从代码到执行",
        "title": "NVCC、PTX、Cubin 与 Fatbin：解密 CUDA 编译黑盒",
        "duration": "18 分钟",
        "question": "什么是虚拟架构与真实架构？为什么写了一段 CUDA 代码可以在不同显卡上无缝运行？PTX 是什么？",
        "metaphor": "世界通用语 (PTX 虚拟汇编中间件) vs 各地当地方言 (Cubin 特定硬件机器码)",
        "needs_animation": False,
        "animation_reason": "以命令行终端演示、编译产物拆解 (cuobjdump) 和编译选项图解为主，适合精细图表呈现。",
        "guide_pages": "P210-P240"
    },
    {
        "ep_id": "20",
        "module": "模块四：CUDA 程序从代码到执行",
        "title": "CPU 与 GPU 的同步与异步机制：错误处理与同步禁忌",
        "duration": "12 分钟",
        "question": "为什么明明 Kernel 发生了越界段错误，程序却在很久之后的下一行 cudaMemcpy 处才报错？",
        "metaphor": "餐厅后厨起火但前台还在给客人倒茶，直到前台去后厨端菜时才发现厨房早已炸锅",
        "needs_animation": True,
        "animation_reason": "异步发射 (Launch) 与同步回收的时间差概念，异步错误 (Asynchronous Error) 捕捉时序必须可视化。",
        "animation_spec": {
            "type": "异步调用时间差与延迟报错链",
            "visual_focus": "CPU 异步返回向下飞奔，GPU 内部异步崩溃，直至 cudaDeviceSynchronize() 抛出异常",
            "beats": [
                {"title": "异步非阻塞发射", "action": "Kernel Launch 返回 0 耗时，CPU 继续推进", "duration": 4.0},
                {"title": "隐蔽的越界崩溃", "action": "GPU 线程计算越界非法访存，产生未决异常状态", "duration": 5.0},
                {"title": "同步点精准捕获", "action": "cudaGetLastError() 与同步栅栏的正确防线位置", "duration": 4.5}
            ]
        },
        "guide_pages": "P240-P260"
    },
    # 模块五：并发、异步与高级执行机制
    {
        "ep_id": "21",
        "module": "模块五：并发、异步与高级执行机制",
        "title": "CUDA Stream 异步执行原理：打破默认流的串行停滞",
        "duration": "18 分钟",
        "question": "默认流 (Default Stream) 为什么会让整个 GPU 陷入串行停摆？多流 (Multi-Stream) 如何实现并发？",
        "metaphor": "单一收费通道排队导致拥堵 vs 开启多条 ETC 专用高速通道各自畅通",
        "needs_animation": True,
        "animation_reason": "Stream 时间轴是并发的核心图示，展示同一个 Stream 内严格保序、不同 Stream 间允许交叉并发重叠。",
        "animation_spec": {
            "type": "多流并发时间轴与队列调度",
            "visual_focus": "默认流阻塞所有流 vs 独立流中的操作在满足资源时并发并行",
            "beats": [
                {"title": "默认流串行阻塞", "action": "默认流上的任何操作强行阻断所有流的并发前进", "duration": 4.5},
                {"title": "创建独立工作流", "action": "cudaStreamCreate 创建 stream0, stream1，分别绑定任务", "duration": 5.0},
                {"title": "多流并发吞吐倍增", "action": "两路独立 Kernel 在不同 SM 上同时运行", "duration": 5.0}
            ]
        },
        "guide_pages": "P260-P290"
    },
    {
        "ep_id": "22",
        "module": "模块五：并发、异步与高级执行机制",
        "title": "CUDA Event 与多流重叠：数据传输与计算完美重叠 (Overlap)",
        "duration": "15 分钟",
        "question": "如何做到 GPU 一边拼命算上一批数据，一边通过 PCIe 悄悄运入下一批数据？双缓冲流水线怎么写？",
        "metaphor": "双缓冲炒菜流水线：厨师在锅里炒第一道菜，配菜员在案板上切第二道菜，无缝衔接绝不停歇",
        "needs_animation": True,
        "animation_reason": "经典双缓冲/多缓冲异步流水线：PCIe 传输引擎（Copy Engine）与计算引擎（Kernel Engine）时间轴 100% 重叠。",
        "animation_spec": {
            "type": "多缓冲流水线双引擎时间轴重叠",
            "visual_focus": "Stream 1 的 Copy H2D 与 Stream 0 的 Kernel 执行完全处于相同时隙",
            "beats": [
                {"title": "传统串行断层", "action": "Copy -> Kernel -> Copy -> Kernel，引擎交替空转浪费", "duration": 4.5},
                {"title": "多流流水线交错", "action": "页锁定内存 (Pinned Memory) 支撑下，双向引擎同时拉满", "duration": 5.5},
                {"title": "总耗时压缩 50%", "action": "数据传输延迟被计算时间完全掩盖 (Latency Hiding)", "duration": 4.5}
            ]
        },
        "guide_pages": "P290-P320"
    },
    {
        "ep_id": "23",
        "module": "模块五：并发、异步与高级执行机制",
        "title": "CUDA Graph 的实现原理：消除 CPU 启动开销的终极武器",
        "duration": "18 分钟",
        "question": "当有几千个超短的小 Kernel 频繁发射时，为什么 CPU 成了瓶颈？CUDA Graph 如何一键把整张图固化在硬件中？",
        "metaphor": "不要每发一颗子弹都找司令部盖章打报告，直接把整个射击弹链固定好连发",
        "needs_animation": True,
        "animation_reason": "图捕获 (Stream Capture)、拓扑构建、实例化 (Instantiate) 与高速重放 (Replay) 的硬件拓扑映射。",
        "animation_spec": {
            "type": "动态拓扑图固化与硬件级极速重放",
            "visual_focus": "杂乱的小 Kernel 调用被固化为静态有向无环图 (DAG)，直接由 GPU 硬件调度器秒级触发",
            "beats": [
                {"title": "CPU 发射延迟累积", "action": "每个 Kernel 5 微秒发射开销累积成巨大空白等待", "duration": 4.5},
                {"title": "CUDA Graph 捕获与固化", "action": "cudaStreamBeginCapture 记录节点与依赖边形成 DAG", "duration": 5.0},
                {"title": "一键重放零开销", "action": "cudaGraphLaunch 单次触发整网运行，CPU 彻底解放", "duration": 4.5}
            ]
        },
        "guide_pages": "P320-P350"
    },
    {
        "ep_id": "24",
        "module": "模块五：并发、异步与高级执行机制",
        "title": "原子操作与线程同步：__syncthreads() 与硬件互斥锁",
        "duration": "15 分钟",
        "question": "万千线程同时对一个全局变量做累加为什么会严重少计？为什么在 if 分支里写 __syncthreads() 会直接死锁？",
        "metaphor": "原子操作：旋转门一次只过一人；同步死锁：拔河比赛一半队员躲进休息室，裁判吹哨所有人必须集合，全场永久僵死",
        "needs_animation": True,
        "animation_reason": "原子操作的读-改-写竞态条件以及条件分支内屏障同步死锁（Deadlock）的硬件行为必须用动画予以严厉警示！",
        "animation_spec": {
            "type": "硬件竞态丢失与条件同步死锁禁忌",
            "visual_focus": "无锁并发写入覆盖丢失数值 vs atomicAdd 硬件排队；分歧分支中的屏障死锁红光警告",
            "beats": [
                {"title": "并发覆写灾难", "action": "两个线程同时读取 0，加 1 后写回，结果为 1 而非 2", "duration": 4.5},
                {"title": "硬件原子排队锁", "action": "显存控制单元独占锁，原子操作平稳得到 2", "duration": 5.0},
                {"title": "分支死锁致命陷阱", "action": "条件分支内 syncthreads 导致硬件永久挂起停滞", "duration": 5.0}
            ]
        },
        "guide_pages": "P350-P380"
    },
    {
        "ep_id": "25",
        "module": "模块五：并发、异步与高级执行机制",
        "title": "Occupancy 与 GPU 资源调度：活跃 Warp 饱和度与吞吐平衡",
        "duration": "15 分钟",
        "question": "为什么 Occupancy (占用率) 不是越高越好？寄存器占用与共享内存大小如何钳制 SM 的驻留能力？",
        "metaphor": "宾馆客房安排：每个客人行李太多 (寄存器大)，整栋楼就只能住下一半客人",
        "needs_animation": True,
        "animation_reason": "SM 资源限制模型（寄存器堆上限、共享内存上限、活跃 Warp 上限）如何共同决定理论 Occupancy。",
        "animation_spec": {
            "type": "多维度物理资源约束木桶效应",
            "visual_focus": "SM 资源配额柱状图，当单个线程寄存器增加时，活跃 Block 数量阶梯式下降",
            "beats": [
                {"title": "资源约束木桶", "action": "展示寄存器、共享内存容量对驻留 Block 数量的硬性限制", "duration": 4.5},
                {"title": "Occupancy 曲线波动", "action": "绘制占用率随 Block 大小变化的阶梯台阶图", "duration": 5.0},
                {"title": "性能并非越高越好", "action": "揭示高 Occupancy 伴随低 ILP 时的性能反转真相", "duration": 4.5}
            ]
        },
        "guide_pages": "P380-P410"
    },
    # 模块六：性能优化与现代 CUDA 实现
    {
        "ep_id": "26",
        "module": "模块六：性能优化与现代 CUDA 实现",
        "title": "矩阵乘法 (GEMM) 的 GPU 并行实现：从朴素暴力到分块共享内存",
        "duration": "20 分钟",
        "question": "为什么朴素矩阵乘法只能跑出显卡 2% 的理论算力？如何用 Tiled GEMM 算法将吞吐提升数十倍？",
        "metaphor": "魔方分块还原：不要一次端着整座大山，切成 32x32 的小拼图放到贴身口袋里算",
        "needs_animation": True,
        "animation_reason": "CUDA 世界最重要的黄金标准案例！分块滑动窗口（Sliding Window Tile）的移动与数据复用必须动画呈现。",
        "animation_spec": {
            "type": "Tiled GEMM 分块滑动窗口与数据复用",
            "visual_focus": "矩阵 A 横向分块滑动、矩阵 B 纵向分块滑动，片上 Shared Memory 协作搬运计算",
            "beats": [
                {"title": "朴素显存读写灾难", "action": "每个元素计算都反复跨步读取全局矩阵，显存总线挤爆", "duration": 5.0},
                {"title": "分块滑动窗口推进", "action": "矩阵 A 和 B 的小方块同时加载进共享内存，线程协作求和", "duration": 6.0},
                {"title": "算力爆炸式释放", "action": "数据复用比率提升 TILE 倍，计算核心跑满", "duration": 4.5}
            ]
        },
        "guide_pages": "P410-P450"
    },
    {
        "ep_id": "27",
        "module": "模块六：性能优化与现代 CUDA 实现",
        "title": "Tile 编程模型与 Tensor Core：驾驭现代 AI 核心专用加速硬件",
        "duration": "20 分钟",
        "question": "现代大模型训练背后的杀手锏 Tensor Core 是如何工作的？WMMA (Warp Matrix Multiply and Accumulate) 怎么用？",
        "metaphor": "从手摇纺织机 (传统单指令 ALU) 到全自动数控织布机 (Tensor Core 单周期完成 16x16 矩阵乘积)",
        "needs_animation": True,
        "animation_reason": "Tensor Core 硬件矩阵乘加单元（4x4/16x16 微矩阵单时钟计算）必须用专用几何立体模型动态展示。",
        "animation_spec": {
            "type": "Tensor Core 矩阵乘加硬件执行管道",
            "visual_focus": "D = A * B + C 矩阵片元在单时钟周期内被 Tensor Core 硬件阵列瞬间折叠吸收",
            "beats": [
                {"title": "传统 ALU 繁重循环", "action": "数千次乘加指令按部就班耗时数百周期", "duration": 4.5},
                {"title": "WMMA 片元载入", "action": "Warp 32 线程协同载入 16x16 半精度矩阵片元", "duration": 5.0},
                {"title": "Tensor Core 瞬间折叠", "action": "专用硬件矩阵单元单周期完成乘加并输出", "duration": 5.5}
            ]
        },
        "guide_pages": "P450-P500"
    },
    {
        "ep_id": "28",
        "module": "模块六：性能优化与现代 CUDA 实现",
        "title": "CUDA 性能优化完整实战：基准测试、Nsight 分析与逐步调优",
        "duration": "20 分钟",
        "question": "面对一个慢如蜗牛的 CUDA Kernel，专业工程师该如何使用 Nsight Systems 和 Nsight Compute 定位瓶颈并彻底解决？",
        "metaphor": "医生使用听诊器与核磁共振：先看全局时间线心电图，再做微架构细胞切片病理分析",
        "needs_animation": False,
        "animation_reason": "以 NVIDIA 官方性能分析工具 Nsight Systems / Compute 真实界面分析、指标解读与代码优化为主。",
        "guide_pages": "P500-P550"
    },
    {
        "ep_id": "29",
        "module": "模块六：性能优化与现代 CUDA 实现",
        "title": "多 GPU 编程与数据通信：NVLink、P2P 与分布式并行雏形",
        "duration": "18 分钟",
        "question": "单张卡显存装不下超大模型怎么办？多张 GPU 之间如何通过 NVLink 做到点对点 (P2P) 极速直通？",
        "metaphor": "跨省普通国道 (PCIe 中转 Host) vs 专属跨海磁悬浮高铁通道 (NVLink 点对点直连)",
        "needs_animation": True,
        "animation_reason": "多 GPU 拓扑、NVLink 高速互联结构与跨卡直接访存 (cudaMemcpyPeer) 必须用多卡通信动画呈现。",
        "animation_spec": {
            "type": "多 GPU 拓扑与 NVLink 高速点对点网络",
            "visual_focus": "GPU 0 与 GPU 1 绕过 Host CPU，通过 NVLink 交叉开关直读彼此显存",
            "beats": [
                {"title": "传统跨卡绕行痛点", "action": "GPU 0 传 CPU，CPU 传 GPU 1，PCIe 双向严重拥堵", "duration": 4.5},
                {"title": "NVLink 点对点直连", "action": "启用 P2P Access，两卡之间建立数百 GB/s 极速通道", "duration": 5.0},
                {"title": "分布式并行初窥", "action": "数据并行与模型并行切分雏形演示", "duration": 4.5}
            ]
        },
        "guide_pages": "P550-P600"
    },
    {
        "ep_id": "30",
        "module": "模块六：性能优化与现代 CUDA 实现",
        "title": "从源码到硅片执行全复盘：CUDA 核心知识图谱与终极心智闭环",
        "duration": "20 分钟",
        "question": "历经 30 讲锤炼，能否在脑海中完整重演一次从编写一行 C++ 代码到硬件晶圆数万个电平跳跃的完整世界？",
        "metaphor": "登上山巅俯瞰全景地图：所有概念、内存、硬件单元与编译指令在此刻融会贯通",
        "needs_animation": True,
        "animation_reason": "全书知识图谱总结大动画，将 30 讲的核心视觉概念汇聚于一体，形成完整心智模型闭环！",
        "animation_spec": {
            "type": "全景知识图谱与硬件运行总装配",
            "visual_focus": "Host CPU 提交 -> PCIe -> GigaThread -> SM 阵列 -> 32 线程 Warp -> 128B 总线 -> 结果输出",
            "beats": [
                {"title": "宏观全景汇聚", "action": "全部六大模块核心图表拼合成完整技术全景地图", "duration": 6.0},
                {"title": "典型任务穿越", "action": "一个真实 GEMM 任务自上而下穿越整张架构图的动态光效", "duration": 6.5},
                {"title": "结课心智升华", "action": "从初学者蜕变为精通底层的专业 CUDA 工程师", "duration": 5.0}
            ]
        },
        "guide_pages": "P1-P698"
    }
]


class DeepSeekDirector:
    """
    Central AI Director leveraging DeepSeek API for:
    1. Intelligent Course & Curriculum Design
    2. Rigorous Pedagogical Animation Curation (Deciding what and when to animate)
    3. Visual Choreography & Storyboard Definition
    4. Bespoke, Bug-Free Manim Code Generation with Self-Healing
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.model = model or config.DEEPSEEK_MODEL

    @staticmethod
    def test_api_key(api_key: str, base_url: str = None, model: str = None) -> Tuple[bool, str]:
        """Tests whether the given DeepSeek API key is valid and responsive."""
        if not api_key or not api_key.strip():
            return False, "API Key 为空，未配置。"
        url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or config.DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 10
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=12)
            if r.status_code == 200:
                return True, "✅ DeepSeek API Key 验证通过！模型连接与响应正常。"
            elif r.status_code == 401:
                return False, f"❌ 认证失败 (HTTP 401)：当前 API Key 无效或已过期。\n{r.text}"
            else:
                return False, f"⚠️ API 返回状态码 {r.status_code}：{r.text[:200]}"
        except Exception as e:
            return False, f"❌ 网络连接异常：{str(e)}"

    def _call_deepseek_api(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> Optional[Dict[str, Any]]:
        """Invokes DeepSeek API with error handling, diagnostic reporting and fallback."""
        if not self.api_key or "sk-" not in self.api_key:
            return None

        masked_key = (self.api_key[:6] + "..." + self.api_key[-4:]) if len(self.api_key) > 10 else "***"
        print(f"[*] [DeepSeek AI] 📡 正在调用 DeepSeek API (模型: {self.model}, Key: {masked_key})...")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 3000
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                print(f"[+] [DeepSeek AI] ✅ API 调用成功 (HTTP 200)！成功由 DeepSeek 智能模型产出内容。")
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if json_mode:
                    return json.loads(content)
                return {"raw_text": content}
            elif resp.status_code == 401:
                print(f"[!] [DeepSeek AI] ❌ API Key 认证失败 (HTTP 401: Invalid API Key)！")
                print(f"    当前使用的 Key: {masked_key} 无效或已过期。")
                print(f"    【智能回退】系统已自动激活《实施文档》内置的 30 集金标专家知识库，确保生成继续进行。")
                return None
            else:
                print(f"[!] [DeepSeek AI] ⚠️ API 返回异常状态码 {resp.status_code}: {resp.text[:150]}")
                print(f"    【智能回退】系统已自动激活内置专家知识库。")
                return None
        except Exception as e:
            print(f"[!] [DeepSeek AI] 网络请求异常: {e}，自动启用本地专家知识库。")
            return None

    def get_full_30_episodes_curriculum(self) -> List[Dict[str, Any]]:
        """Returns the structured 30-episode curriculum adhering to docx."""
        return CURRICULUM_30_EPISODES

    def find_episode_by_id_or_title(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds matched episode specification."""
        q = query.lower()
        for ep in CURRICULUM_30_EPISODES:
            if ep["ep_id"] == query or ep["title"].lower() in q or q in ep["title"].lower():
                return ep
        return None

    def evaluate_animation_necessity(self, topic: str, content_snippet: str = "") -> Dict[str, Any]:
        """
        Determines whether a given concept strictly requires an animation vs static slide,
        and provides exact pedagogical reasoning.
        """
        # Try online DeepSeek API first
        sys_prompt = (
            "你是一个资深 CUDA 架构师和教学视频编导。请参考《CUDA原理与实现教学视频项目实施文档》和"
            "《CUDA GPU执行架构流程图》，对给定的教学知识点进行严格评估：\n"
            "1. 判断是否需要制作动态动画（动态状态变化、微架构隐蔽过程、并发重叠、时钟时序等必须动画；单纯语法/API列表/静态配置不要动画）。\n"
            "2. 输出 JSON 格式：\n"
            "{\n"
            '  "needs_animation": true/false,\n'
            '  "reason": "严格技术理由",\n'
            '  "cognitive_barrier": "学习者在此处的认知卡点",\n'
            '  "visual_metaphor": "直观生活类比及明确局限性边界说明",\n'
            '  "animation_type": "2D流程/3D架构/代码-硬件双轨联动",\n'
            '  "key_hardware_units": ["SM", "Warp", "DRAM", ...]\n'
            "}"
        )
        user_prompt = f"请评估该 CUDA 知识点：主题={topic}\n上下文描述={content_snippet}"
        res = self._call_deepseek_api(sys_prompt, user_prompt, json_mode=True)
        if res and "needs_animation" in res:
            return res

        # Resilient Deep Pedagogical Fallback
        matched_ep = self.find_episode_by_id_or_title(topic)
        if matched_ep:
            return {
                "needs_animation": matched_ep.get("needs_animation", True),
                "reason": matched_ep.get("animation_reason", "核心硬件概念必须通过动态流向展示"),
                "cognitive_barrier": matched_ep.get("question", ""),
                "visual_metaphor": matched_ep.get("metaphor", ""),
                "animation_type": matched_ep.get("animation_spec", {}).get("type", "2D 流程图"),
                "key_hardware_units": ["SM", "Warp", "Thread Block", "Global Memory"]
            }

        # General Heuristic Fallback
        keywords = ["warp", "divergence", "coalesc", "bank", "shared", "gemm", "stream", "atomic", "sync", "sm", "schedul"]
        needs = any(k in topic.lower() for k in keywords)
        return {
            "needs_animation": needs,
            "reason": "该知识点包含硬件微架构动态时序与状态变化" if needs else "该知识点适合通过高清对比卡片与代码演练呈现",
            "cognitive_barrier": f"如何建立关于 {topic} 的底层物理心智模型",
            "visual_metaphor": "流水线加工与分布式工单调度",
            "animation_type": "2D 硬件微架构流程图",
            "key_hardware_units": ["GPU", "SM", "Warp"]
        }

    def choreograph_animation(self, topic: str, timeline_beats: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates full 3-Beat Visual Storyboard and spatial choreographies based on
        'CUDA GPU执行架构流程图.png' and the project guidelines.
        """
        sys_prompt = (
            "你是一个精通 3Blue1Brown 风格 Manim CE 的 CUDA 教学视频视觉总监。请依据《CUDA原理与实现教学视频项目实施文档》"
            "和《CUDA GPU执行架构流程图.png》，为指定知识点编排分镜脚本（Storyboard）：\n"
            "严格要求：\n"
            "1. 严谨区分编程模型抽象（Grid, Block, Thread）与硬件执行资源（SM, Warp Scheduler, ALU）。\n"
            "2. 动画布局严格遵守底部字幕安全带标准（y < -1.8 严禁放置任何视觉元素，保留给硬字幕）。\n"
            "3. 必须采用'三幕式认知冲突'：第1幕（常规直觉/设定）、第2幕（硬件现实/冲突暴露/瓶颈灾难）、第3幕（顿悟破解/架构优化/刻意留白）。\n"
            "4. 输出 JSON 格式：\n"
            "{\n"
            '  "scene_class_name": "CudaCustomScene",\n'
            '  "title": "主题标题",\n'
            '  "subtitle": "认知冲突副标题",\n'
            '  "visual_metaphor": "物理直觉类比",\n'
            '  "beats": [\n'
            '    {"beat_index": 1, "name": "设定", "duration": 4.0, "mobjects": [...], "visual_actions": [...]},\n'
            '    {"beat_index": 2, "name": "冲突", "duration": 5.0, "mobjects": [...], "visual_actions": [...]},\n'
            '    {"beat_index": 3, "name": "顿悟", "duration": 4.5, "mobjects": [...], "visual_actions": [...]}\n'
            '  ]\n'
            "}"
        )
        user_prompt = f"请为以下 CUDA 概念编排三幕式 Manim 动画分镜：\n主题：{topic}\n当前时间轴节奏：{json.dumps(timeline_beats or [], ensure_ascii=False)}"
        res = self._call_deepseek_api(sys_prompt, user_prompt, json_mode=True)
        if res and "beats" in res:
            return res

        # Fallback from curated knowledge base
        matched_ep = self.find_episode_by_id_or_title(topic)
        title = matched_ep["title"] if matched_ep else topic
        metaphor = matched_ep["metaphor"] if matched_ep else "工单分发与微架构协同"

        return {
            "scene_class_name": "CudaArchitecturalScene",
            "title": title,
            "subtitle": "编程模型抽象 vs 硬件执行实体",
            "visual_metaphor": metaphor,
            "beats": [
                {
                    "beat_index": 1,
                    "name": "抽象设定",
                    "duration": 4.0,
                    "visual_actions": ["展开 Host 软件抽象到 Device 硬件映射全景", "初始化 32 线程 Warp 或 ThreadGrid"]
                },
                {
                    "beat_index": 2,
                    "name": "硬件冲突",
                    "duration": 5.5,
                    "visual_actions": ["展示显存高延迟阻塞、分支分化挂起或 Bank 访问排队", "红色警告高亮闪烁，警示吞吐断崖下跌"]
                },
                {
                    "beat_index": 3,
                    "name": "架构破解与顿悟",
                    "duration": 4.5,
                    "visual_actions": ["引入对齐合并、共享内存 Tile 缓存或无分歧重构代码", "全员高亮 NVIDIA 翠绿色，刻意顿悟留白"]
                }
            ]
        }

    def generate_manim_code_for_concept(
        self,
        topic: str,
        timeline_beats: List[Dict[str, Any]],
        project_root: Path
    ) -> Tuple[str, str]:
        """
        Uses DeepSeek API to write production-grade, bug-free Manim CE Python code for the topic,
        incorporating cuda_manim_lib components and respecting subtitle boundaries.
        Returns (python_code_str, scene_class_name).
        """
        sys_prompt = (
            "你是一个顶尖的 3Blue1Brown 风格 Manim CE 动画生成引擎，精通 Python 和 NVIDIA CUDA 底层架构。\n"
            "请参考《CUDA原理与实现教学视频项目实施文档.docx》和《CUDA GPU执行架构流程图.png》，生成一段高质量、可以直接运行渲染的 Manim Python 脚本。\n\n"
            "关键规则要求：\n"
            "1. 必须导入项目预置模块：\n"
            "   sys.path.insert(0, r'<PROJECT_ROOT>')\n"
            "   from assets.styles import *\n"
            "   from assets.cuda_manim_lib import CUDAThemeScene, ThreadGrid, MemoryLane, ThreadItem, Warp32Grid, HostDeviceFlowDiagram, DRAMBusTransaction\n"
            "2. 继承 CUDAThemeScene，在 construct(self) 中执行动画。\n"
            "3. 严格禁止把任何元素放置在 y < -1.8 区域（例如 DOWN * 2.2 或 DOWN * 2.5 严禁使用），该区域被保留作为视频硬字幕专属安全带。\n"
            "4. 颜色规范必须采用 tokens：NVIDIA_GREEN, BG_DARK, CARD_BG, THREAD_DEFAULT, THREAD_CONFLICT, WARP_COLOR_A, WARP_COLOR_B。\n"
            "5. 节奏严格契合传入的三幕式动作时间（b1_time, b2_time, b3_time, b3_pause）。\n"
            "6. 仅输出合法的 Python 代码，不要用 markdown 解释包围（纯代码字符串）。"
        )

        b1_time = timeline_beats[0].get("action_duration", 3.0) if len(timeline_beats) > 0 else 3.0
        b2_time = sum(b.get("action_duration", 3.0) for b in timeline_beats[1:-1]) if len(timeline_beats) > 2 else 4.0
        b3_time = timeline_beats[-1].get("action_duration", 3.5) if len(timeline_beats) > 0 else 3.5
        b3_pause = timeline_beats[-1].get("pause_buffer", 2.0) if len(timeline_beats) > 0 else 2.0

        user_prompt = (
            f"目标主题：{topic}\n"
            f"项目根目录：{str(project_root)}\n"
            f"动作耗时参数：b1_time={b1_time}, b2_time={b2_time}, b3_time={b3_time}, b3_pause={b3_pause}\n"
            f"请生成完整的 Manim Python 类代码。"
        )

        # Call online DeepSeek API
        res = self._call_deepseek_api(sys_prompt, user_prompt, json_mode=False)
        if res and res.get("raw_text"):
            code = res["raw_text"]
            # Clean markdown codeblocks
            code = re.sub(r"^```python\s*", "", code, flags=re.MULTILINE)
            code = re.sub(r"^```\s*$", "", code, flags=re.MULTILINE).strip()
            # Extract class name
            match = re.search(r"class\s+([A-Za-z0-9_]+)\s*\(\s*CUDAThemeScene\s*\):", code)
            scene_class = match.group(1) if match else "CudaGeneratedScene"
            return code, scene_class

        # Fallback to rich architectural generator using specialized microarchitecture templates
        return self._build_architectural_fallback_scene(topic, b1_time, b2_time, b3_time, b3_pause, project_root)

    def _build_architectural_fallback_scene(
        self,
        topic: str,
        b1_time: float,
        b2_time: float,
        b3_time: float,
        b3_pause: float,
        project_root: Path
    ) -> Tuple[str, str]:
        """Intelligent semantic router that produces a dedicated bespoke Manim scene for every topic."""
        t = topic.lower()
        if any(k in t for k in ["nvcc", "compiler", "ptx", "cubin", "fatbin", "010"]):
            return self._scene_nvcc_compilation(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["unified", "managed", "page", "fault", "system_memory", "009"]):
            return self._scene_unified_memory(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["stream", "async", "overlap", "pipeline", "008"]):
            return self._scene_stream_overlap(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["tile", "gemm", "matrix", "matmul", "007"]):
            return self._scene_tiled_gemm(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["simt", "warp", "diverge", "branch", "lockstep", "006"]):
            return self._scene_warp_divergence(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["python", "numba", "cupy", "jit", "005"]):
            return self._scene_python_jit(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["cuda_c", "vector", "c++", "kernel", "004"]):
            return self._scene_vector_add_flow(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["platform", "driver", "runtime", "capability", "003"]):
            return self._scene_platform_architecture(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["model", "index", "grid", "dim", "threadidx", "002"]):
            return self._scene_global_id(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["intro", "why", "difference", "cpu", "gpu_evolution", "001"]):
            return self._scene_cpu_vs_gpu(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["bank", "shared"]):
            return self._scene_bank_conflict(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["coalesc", "dram", "stride"]):
            return self._scene_coalesced(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["atomic", "race", "mutex"]):
            return self._scene_atomic(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        elif any(k in t for k in ["sync", "barrier"]):
            return self._scene_syncthreads(topic, b1_time, b2_time, b3_time, b3_pause, project_root)
        else:
            return self._scene_cpu_vs_gpu(topic, b1_time, b2_time, b3_time, b3_pause, project_root)

    # ----------------- SECTION 1: CPU vs GPU Architecture -----------------
    def _scene_cpu_vs_gpu(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaCpuVsGpuScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CPU 延迟优化 vs GPU 吞吐优化架构", "少数顶尖数学家 vs 海量并行计算核心")
        code_badge = self.create_code_badge("CPU: 大片上缓存与复杂乱序预测 | GPU: 80% 面积密布原生算力 ALU", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

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

        self.play(FadeIn(cpu_group), FadeIn(gpu_group), run_time={round(b1 * 0.6, 2)})
        self.wait(1.0)

        # Action: Compare execution
        self.play(
            LaggedStart(*[c.animate.set_color(WARP_COLOR_A).set_fill(WARP_COLOR_A, opacity=1.0) for row in gpu_cores for c in row], lag_ratio=0.02),
            code_badge.animate.become(self.create_code_badge("GPU 架构真谛：用芯片物理面积换取极限数据并行吞吐！", position=UP * 2.0)),
            run_time={round(b2 * 0.7, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 2: Programming Model (Global ID) -----------------
    def _scene_global_id(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaGlobalIdScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadGrid, MemoryLane

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA 全局索引映射与网格升维", "CPU 串行循环思维 vs GPU 空间立体点阵")
        code_badge = self.create_code_badge("int idx = threadIdx.x;  // 隐患：单块正常，多块发生物理冲突", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        grid = ThreadGrid(num_blocks=1, threads_per_block=4, block_spacing=0.8)
        grid.move_to(UP * 0.2 + LEFT * 3.0)
        memory = MemoryLane(num_slots=8, slot_width=0.85)
        memory.move_to(DOWN * 1.8)
        self.play(FadeIn(grid), FadeIn(memory), run_time={round(b1 * 0.6, 2)})

        t0 = grid.get_thread(0, 0)
        arrow_t0 = Arrow(start=t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_DEFAULT, buff=0.1)
        self.play(GrowArrow(arrow_t0), run_time=0.8)
        memory.get_slot(0).set_value("T0", color=THREAD_DEFAULT)
        self.wait(1.0)

        new_grid = ThreadGrid(num_blocks=2, threads_per_block=4, block_spacing=1.2)
        new_grid.move_to(UP * 0.2)
        self.play(ReplacementTransform(grid, new_grid), FadeOut(arrow_t0), run_time={round(b2 * 0.4, 2)})

        b0_t0 = new_grid.get_thread(0, 0)
        b1_t0 = new_grid.get_thread(1, 0)
        arrow_b0 = Arrow(start=b0_t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        arrow_b1 = Arrow(start=b1_t0.circle.get_bottom(), end=memory.get_slot(0).box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        self.play(GrowArrow(arrow_b0), GrowArrow(arrow_b1), b0_t0.circle.animate.set_color(THREAD_CONFLICT), b1_t0.circle.animate.set_color(THREAD_CONFLICT), run_time={round(b2 * 0.6, 2)})
        memory.get_slot(0).flash_collision()

        aha_formula = self.create_code_badge("int idx = blockIdx.x * blockDim.x + threadIdx.x; // 空间平铺", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeOut(arrow_b0), FadeOut(arrow_b1), FadeIn(aha_formula), run_time=0.6)

        resolved_arrows = []
        for b in range(2):
            for t in range(4):
                g_id = b * 4 + t
                t_obj = new_grid.get_thread(b, t)
                t_obj.set_resolved_state("g" + str(g_id))
                arr = Arrow(start=t_obj.circle.get_bottom(), end=memory.get_slot(g_id).box.get_top(), color=NVIDIA_GREEN, stroke_width=2, buff=0.1)
                resolved_arrows.append(arr)
        self.play(LaggedStart(*[GrowArrow(a) for a in resolved_arrows], lag_ratio=0.08), run_time={round(b3 * 0.7, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 3: The CUDA Platform (Host to Device Flow) -----------------
    def _scene_platform_architecture(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaPlatformArchitectureScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, HostDeviceFlowDiagram

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA 平台架构与软硬件执行全景", "基于 NVIDIA 13.3 · Host 软件抽象到 Device 硬件物理执行")
        code_badge = self.create_code_badge("vectorAdd<<<Grid(Blocks), Block(Threads)>>>(d_A, d_B, d_C);", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        flow_diagram = HostDeviceFlowDiagram()
        flow_diagram.move_to(DOWN * 0.1)

        self.play(
            FadeIn(flow_diagram.host_group),
            FadeIn(flow_diagram.launch_arrow),
            FadeIn(flow_diagram.launch_lbl),
            FadeIn(flow_diagram.device_group),
            run_time={round(b1 * 0.6, 2)}
        )
        self.wait(1.0)

        # Pulse GigaThread and SM allocation
        clarify_badge = self.create_code_badge("重要澄清：1. Block不等于SM; 2. Warp不等于SM; 3. 多Block并发驻留SM", position=UP * 2.0)
        self.play(
            FadeOut(code_badge), FadeIn(clarify_badge),
            flow_diagram.device_group.animate.set_color(NVIDIA_GREEN),
            Flash(flow_diagram.device_group, color=NVIDIA_GREEN, flash_radius=1.8),
            run_time={round(b2 * 0.8, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 4: Intro to CUDA C++ (VectorAdd Lifecycle) -----------------
    def _scene_vector_add_flow(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaVectorAddFlowScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA C++ 向量加法全生命周期", "显存开辟 -> 数据飞跃 -> 并发点火 -> 结果回收")
        code_badge = self.create_code_badge("1. cudaMalloc(&d_A, N * sizeof(float)); // 设备端物理开辟", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        host_ram = RoundedRectangle(corner_radius=0.12, width=3.4, height=2.0, color=BLUE_C, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 3.8 + DOWN * 0.2)
        host_lbl = Text("Host 内存 (CPU RAM)", font_size=FONT_BADGE_SIZE - 2, color=BLUE_C, weight=BOLD).next_to(host_ram, UP, buff=0.1)
        h_data = VGroup(*[Rectangle(width=0.45, height=0.45, color=BLUE_E, fill_color=BLUE_E, fill_opacity=0.8) for _ in range(4)]).arrange(RIGHT, buff=0.1).move_to(host_ram.get_center())

        dev_ram = RoundedRectangle(corner_radius=0.12, width=3.8, height=2.0, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 3.4 + DOWN * 0.2)
        dev_lbl = Text("Device 显存 (VRAM / HBM)", font_size=FONT_BADGE_SIZE - 2, color=NVIDIA_GREEN, weight=BOLD).next_to(dev_ram, UP, buff=0.1)
        d_data = VGroup(*[Rectangle(width=0.45, height=0.45, color=CARD_BORDER, fill_color=BG_DARK, fill_opacity=0.5) for _ in range(4)]).arrange(RIGHT, buff=0.1).move_to(dev_ram.get_center())

        pcie_arrow = Arrow(start=host_ram.get_right(), end=dev_ram.get_left(), color=YELLOW, buff=0.2)
        pcie_lbl = Text("PCIe 数据灌入", font_size=FONT_BADGE_SIZE - 4, color=YELLOW).next_to(pcie_arrow, UP, buff=0.1)

        self.play(FadeIn(host_ram), FadeIn(host_lbl), FadeIn(h_data), FadeIn(dev_ram), FadeIn(dev_lbl), FadeIn(d_data), run_time={round(b1 * 0.6, 2)})

        self.play(
            GrowArrow(pcie_arrow), FadeIn(pcie_lbl),
            code_badge.animate.become(self.create_code_badge("2. cudaMemcpy(d_A, h_A, size, cudaMemcpyHostToDevice);", position=UP * 2.0)),
            *[d.animate.set_color(NVIDIA_GREEN).set_fill(NVIDIA_GREEN, opacity=0.85) for d in d_data],
            run_time={round(b2 * 0.5, 2)}
        )

        ignite_badge = self.create_code_badge("3. vectorAdd<<<Blocks, Threads>>>(d_A, d_B, d_C); // 并发点火！", position=UP * 2.0)
        self.play(
            FadeOut(code_badge), FadeIn(ignite_badge),
            Flash(dev_ram, color=NVIDIA_GREEN, flash_radius=1.6),
            run_time={round(b2 * 0.5, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 5: Intro to CUDA Python -----------------
    def _scene_python_jit(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaPythonJitScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA Python 运行时与 JIT 编译流水线", "动态高级语言抽象 vs 静态机器码原生硬件极速执行")
        code_badge = self.create_code_badge("@cuda.jit\\ndef vector_add(a, b, c): ...", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        b1_rect = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.3, color=BLUE, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 4.2 + DOWN * 0.2)
        l1 = Text("Python 脚本\\n(@cuda.jit)", font_size=FONT_BADGE_SIZE - 2, color=BLUE, weight=BOLD).move_to(b1_rect.get_center())

        b2_rect = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.3, color=PURPLE, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 1.4 + DOWN * 0.2)
        l2 = Text("Numba JIT\\n(LLVM IR 前端)", font_size=FONT_BADGE_SIZE - 2, color=PURPLE, weight=BOLD).move_to(b2_rect.get_center())

        b3_rect = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.3, color=YELLOW, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 1.4 + DOWN * 0.2)
        l3 = Text("NVVM / PTX\\n(虚拟中间表示)", font_size=FONT_BADGE_SIZE - 2, color=YELLOW, weight=BOLD).move_to(b3_rect.get_center())

        b4_rect = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.3, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 4.2 + DOWN * 0.2)
        l4 = Text("GPU 物理核\\n(SASS 机器码)", font_size=FONT_BADGE_SIZE - 2, color=NVIDIA_GREEN, weight=BOLD).move_to(b4_rect.get_center())

        arr1 = Arrow(start=b1_rect.get_right(), end=b2_rect.get_left(), color=TEXT_SECONDARY, buff=0.1)
        arr2 = Arrow(start=b2_rect.get_right(), end=b3_rect.get_left(), color=TEXT_SECONDARY, buff=0.1)
        arr3 = Arrow(start=b3_rect.get_right(), end=b4_rect.get_left(), color=TEXT_SECONDARY, buff=0.1)

        self.play(
            FadeIn(b1_rect), FadeIn(l1), FadeIn(b2_rect), FadeIn(l2),
            FadeIn(b3_rect), FadeIn(l3), FadeIn(b4_rect), FadeIn(l4),
            GrowArrow(arr1), GrowArrow(arr2), GrowArrow(arr3),
            run_time={round(b1 * 0.6, 2)}
        )

        pulse_badge = self.create_code_badge("JIT 瞬时编译完成 · Python 代码直接在 GPU 硅片原生跑满！", position=UP * 2.0)
        self.play(
            b4_rect.animate.set_color(NVIDIA_GREEN).set_fill(NVIDIA_GREEN, opacity=0.35),
            FadeOut(code_badge), FadeIn(pulse_badge),
            Flash(b4_rect, color=NVIDIA_GREEN, flash_radius=1.2),
            run_time={round(b2 * 0.8, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 6: Writing SIMT Kernels (32-Warp Divergence) -----------------
    def _scene_warp_divergence(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaWarpDivergenceScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, Warp32Grid

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("Warp 线程束与 SIMT 分支分化", "32 线程锁步推进 vs 条件分支串行化撕裂")
        code_badge = self.create_code_badge("if (tid % 2 == 0) {{ ... }} else {{ ... }}", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        warp32 = Warp32Grid(warp_id=0, cell_size=0.42)
        warp32.move_to(DOWN * 0.2)
        self.play(FadeIn(warp32), run_time={round(b1 * 0.6, 2)})
        self.wait(1.0)

        # Stage 1: Branch A active (even threads), Branch B masked
        evens = [i for i in range(32) if i % 2 == 0]
        odds = [i for i in range(32) if i % 2 != 0]

        mask_a_badge = self.create_code_badge("分支 A 执行中: 偶数线程活跃 (奇数线程被硬件强制挂起锁定)", position=UP * 2.0)
        self.play(
            FadeOut(code_badge), FadeIn(mask_a_badge),
            *[warp32.threads[i].box.animate.set_color(WARP_COLOR_A).set_fill(WARP_COLOR_A, opacity=0.85) for i in evens],
            *[warp32.threads[i].box.animate.set_color(THREAD_IDLE).set_fill(CARD_BG, opacity=0.3) for i in odds],
            run_time={round(b2 * 0.5, 2)}
        )

        # Stage 2: Branch B active (odd threads), Branch A masked
        mask_b_badge = self.create_code_badge("分支 B 执行中: 奇数线程活跃 (偶数线程挂起) · 吞吐断崖腰斩至 50% !", position=UP * 2.0)
        self.play(
            FadeOut(mask_a_badge), FadeIn(mask_b_badge),
            *[warp32.threads[i].box.animate.set_color(THREAD_IDLE).set_fill(CARD_BG, opacity=0.3) for i in evens],
            *[warp32.threads[i].box.animate.set_color(WARP_COLOR_B).set_fill(WARP_COLOR_B, opacity=0.85) for i in odds],
            run_time={round(b2 * 0.5, 2)}
        )

        # Stage 3: Zero Divergence Resolution
        resolved_badge = self.create_code_badge("消除分支分歧 = 32 线程全速锁步并发 (Zero Divergence)！", position=UP * 2.0)
        self.play(
            FadeOut(mask_b_badge), FadeIn(resolved_badge),
            *[warp32.threads[i].box.animate.set_color(NVIDIA_GREEN).set_fill(NVIDIA_GREEN, opacity=0.85) for i in range(32)],
            run_time={round(b3 * 0.7, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 7: Writing Tile Kernels (Shared Memory & Tiled GEMM) -----------------
    def _scene_tiled_gemm(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaTiledGemmScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("共享内存分块矩阵乘法 (Tiled GEMM)", "高延迟显存瓶颈 vs 片上缓存空间复用")
        code_badge = self.create_code_badge("C[row][col] += A[row][k] * B[k][col]; // 原始显存暴力访存", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        mat_a = Square(side_length=2.0, color=BLUE_D, fill_color=CARD_BG, fill_opacity=0.8).move_to(LEFT * 3.5 + UP * 0.1)
        mat_b = Square(side_length=2.0, color=BLUE_E, fill_color=CARD_BG, fill_opacity=0.8).move_to(RIGHT * 3.5 + UP * 0.1)
        mat_c = Square(side_length=2.0, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.8).move_to(UP * 0.1)

        lbl_a = Text("Matrix A (Global)", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(mat_a, UP, buff=0.15)
        lbl_b = Text("Matrix B (Global)", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(mat_b, UP, buff=0.15)
        lbl_c = Text("Matrix C (Global)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).next_to(mat_c, UP, buff=0.15)

        self.play(FadeIn(mat_a), FadeIn(lbl_a), FadeIn(mat_b), FadeIn(lbl_b), FadeIn(mat_c), FadeIn(lbl_c), run_time={round(b1 * 0.6, 2)})
        self.wait(1.0)

        tile_badge = self.create_code_badge("__shared__ float s_A[TILE][TILE], s_B[TILE][TILE];", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeIn(tile_badge), run_time=0.5)

        tile_a = Square(side_length=0.8, color=YELLOW, fill_color=YELLOW, fill_opacity=0.3).move_to(mat_a.get_center())
        tile_b = Square(side_length=0.8, color=YELLOW, fill_color=YELLOW, fill_opacity=0.3).move_to(mat_b.get_center())
        smem_box = RoundedRectangle(corner_radius=0.15, width=4.5, height=0.9, color=YELLOW, fill_color=CARD_BG, fill_opacity=0.9).move_to(DOWN * 1.6)
        smem_lbl = Text("SM 片上高速缓存 (Shared Memory Tiles)", font_size=FONT_BADGE_SIZE, color=YELLOW).move_to(smem_box.get_center())

        self.play(FadeIn(tile_a), FadeIn(tile_b), FadeIn(smem_box), FadeIn(smem_lbl), run_time={round(b2 * 0.5, 2)})

        flow_a = Arrow(start=tile_a.get_bottom(), end=smem_box.get_left(), color=YELLOW, buff=0.1)
        flow_b = Arrow(start=tile_b.get_bottom(), end=smem_box.get_right(), color=YELLOW, buff=0.1)
        self.play(GrowArrow(flow_a), GrowArrow(flow_b), run_time=0.6)

        opt_badge = self.create_code_badge("算力复用：每个全局数据被线程块重用 TILE 次 (算力暴涨数十倍)！", position=UP * 2.0)
        self.play(
            FadeOut(tile_badge), FadeOut(flow_a), FadeOut(flow_b), FadeIn(opt_badge),
            mat_c.animate.set_color(NVIDIA_GREEN), Flash(mat_c, color=NVIDIA_GREEN, flash_radius=1.5),
            run_time={round(b3 * 0.7, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 8: Asynchronous Execution (Stream Overlap) -----------------
    def _scene_stream_overlap(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaStreamOverlapScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("CUDA 多流并发与时序重叠 (Stream Overlap)", "默认流串行阻塞 vs 双缓冲异步隐藏延迟")
        code_badge = self.create_code_badge("cudaMemcpy(H2D); kernel<<<...>>>(); cudaMemcpy(D2H); // 串行停滞", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        time_axis = Arrow(start=LEFT * 5.0, end=RIGHT * 5.0, color=TEXT_SECONDARY).move_to(DOWN * 1.8)
        time_lbl = Text("时间轴 (Timeline)", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(time_axis, DOWN, buff=0.1)

        b_copy1 = Rectangle(width=2.5, height=0.7, color=BLUE, fill_color=BLUE, fill_opacity=0.6).move_to(LEFT * 3.5 + UP * 0.4)
        lbl_c1 = Text("Copy H2D", font_size=FONT_BADGE_SIZE, color=TEXT_PRIMARY).move_to(b_copy1.get_center())

        b_kern1 = Rectangle(width=2.5, height=0.7, color=NVIDIA_GREEN, fill_color=NVIDIA_GREEN, fill_opacity=0.6).move_to(LEFT * 0.5 + UP * 0.4)
        lbl_k1 = Text("Kernel<<<>>>", font_size=FONT_BADGE_SIZE, color=TEXT_PRIMARY).move_to(b_kern1.get_center())

        b_copy2 = Rectangle(width=2.5, height=0.7, color=PURPLE, fill_color=PURPLE, fill_opacity=0.6).move_to(RIGHT * 2.5 + UP * 0.4)
        lbl_c2 = Text("Copy D2H", font_size=FONT_BADGE_SIZE, color=TEXT_PRIMARY).move_to(b_copy2.get_center())

        self.play(FadeIn(time_axis), FadeIn(time_lbl), FadeIn(b_copy1), FadeIn(lbl_c1), FadeIn(b_kern1), FadeIn(lbl_k1), FadeIn(b_copy2), FadeIn(lbl_c2), run_time={round(b1 * 0.6, 2)})
        self.wait(1.0)

        async_badge = self.create_code_badge("cudaMemcpyAsync(..., stream1); kernel<<<..., stream2>>>(); // 多流流水线", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeIn(async_badge), FadeOut(b_copy1), FadeOut(lbl_c1), FadeOut(b_kern1), FadeOut(lbl_k1), FadeOut(b_copy2), FadeOut(lbl_c2), run_time=0.5)

        s1_copy = Rectangle(width=2.2, height=0.6, color=BLUE, fill_color=BLUE, fill_opacity=0.7).move_to(LEFT * 2.5 + UP * 0.6)
        s1_lbl = Text("Stream 0: Copy", font_size=FONT_BADGE_SIZE - 2, color=TEXT_PRIMARY).move_to(s1_copy.get_center())

        s2_kern = Rectangle(width=2.2, height=0.6, color=NVIDIA_GREEN, fill_color=NVIDIA_GREEN, fill_opacity=0.7).move_to(LEFT * 0.5 + DOWN * 0.2)
        s2_lbl = Text("Stream 1: Kernel", font_size=FONT_BADGE_SIZE - 2, color=TEXT_PRIMARY).move_to(s2_kern.get_center())

        s3_copy = Rectangle(width=2.2, height=0.6, color=PURPLE, fill_color=PURPLE, fill_opacity=0.7).move_to(RIGHT * 1.5 + DOWN * 0.9)
        s3_lbl = Text("Stream 2: Next Copy", font_size=FONT_BADGE_SIZE - 2, color=TEXT_PRIMARY).move_to(s3_copy.get_center())

        overlap_rect = DashedVMobject(Rectangle(width=3.5, height=2.2, color=YELLOW)).move_to(LEFT * 0.5 + DOWN * 0.2)
        overlap_lbl = Text("PCIe 传输与 SM 算力 100% 完美重叠！", font_size=FONT_BADGE_SIZE, color=YELLOW, weight=BOLD).next_to(overlap_rect, UP, buff=0.15)

        self.play(FadeIn(s1_copy), FadeIn(s1_lbl), FadeIn(s2_kern), FadeIn(s2_lbl), FadeIn(s3_copy), FadeIn(s3_lbl), Create(overlap_rect), FadeIn(overlap_lbl), run_time={round(b2 * 0.8, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 9: Unified and System Memory -----------------
    def _scene_unified_memory(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaUnifiedMemoryScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("统一内存与底层 Page Fault 缺页迁移", "单一虚拟指针假象 vs 物理页按需跨 PCIe 迁移")
        code_badge = self.create_code_badge("cudaMallocManaged(&data, N * sizeof(float)); // 统一指针", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        cpu_mem = RoundedRectangle(corner_radius=0.15, width=3.6, height=2.4, color=BLUE_C, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 3.8 + DOWN * 0.3)
        cpu_lbl = Text("CPU 主存 (物理页面驻留)", font_size=FONT_BADGE_SIZE - 2, color=BLUE_C, weight=BOLD).next_to(cpu_mem, UP, buff=0.1)
        page1 = Rectangle(width=1.2, height=0.6, color=BLUE_E, fill_color=BLUE_E, fill_opacity=0.8).move_to(cpu_mem.get_center())
        p_lbl = Text("4KB 物理页", font_size=FONT_BADGE_SIZE - 4, color=TEXT_PRIMARY).move_to(page1.get_center())

        gpu_mem = RoundedRectangle(corner_radius=0.15, width=3.6, height=2.4, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 3.8 + DOWN * 0.3)
        gpu_lbl = Text("GPU 显存 (虚拟映射区)", font_size=FONT_BADGE_SIZE - 2, color=NVIDIA_GREEN, weight=BOLD).next_to(gpu_mem, UP, buff=0.1)

        self.play(FadeIn(cpu_mem), FadeIn(cpu_lbl), FadeIn(page1), FadeIn(p_lbl), FadeIn(gpu_mem), FadeIn(gpu_lbl), run_time={round(b1 * 0.6, 2)})

        pf_text = Text("! GPU 访存发生 Page Fault 缺页中断 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD).move_to(UP * 1.3)
        self.play(FadeIn(pf_text), gpu_mem.animate.set_color(THREAD_CONFLICT), run_time=0.6)

        self.play(
            page1.animate.move_to(gpu_mem.get_center()).set_color(NVIDIA_GREEN).set_fill(NVIDIA_GREEN, opacity=0.8),
            p_lbl.animate.move_to(gpu_mem.get_center()),
            gpu_mem.animate.set_color(NVIDIA_GREEN),
            FadeOut(pf_text),
            code_badge.animate.become(self.create_code_badge("cudaMemPrefetchAsync(...) 预取优化：消除运行时缺页停顿！", position=UP * 2.0)),
            run_time={round(b2 * 0.8, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- SECTION 10: NVCC the NVIDIA CUDA Compiler -----------------
    def _scene_nvcc_compilation(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaNvccCompilationScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("NVCC 编译黑盒与二进制产物全景", "Host/Device 双路分离 -> PTX 虚拟指令 -> Cubin 真实机器码")
        code_badge = self.create_code_badge("nvcc -arch=compute_80 -code=sm_80,sm_90 main.cu -o main", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        src_box = RoundedRectangle(corner_radius=0.1, width=2.2, height=1.4, color=TEXT_PRIMARY, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 4.6 + DOWN * 0.3)
        src_lbl = Text("main.cu\\n(CUDA 源码)", font_size=FONT_BADGE_SIZE - 2, color=TEXT_PRIMARY, weight=BOLD).move_to(src_box.get_center())

        ptx_box = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.4, color=YELLOW, fill_color=CARD_BG, fill_opacity=0.9).move_to(LEFT * 1.5 + DOWN * 0.3)
        ptx_lbl = Text("PTX 虚拟汇编\\n(跨架构前向兼容)", font_size=FONT_BADGE_SIZE - 3, color=YELLOW, weight=BOLD).move_to(ptx_box.get_center())

        cubin_box = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.4, color=BLUE_D, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 1.6 + DOWN * 0.3)
        cubin_lbl = Text("Cubin 真实机器码\\n(特定硬件 SASS)", font_size=FONT_BADGE_SIZE - 3, color=BLUE_D, weight=BOLD).move_to(cubin_box.get_center())

        fat_box = RoundedRectangle(corner_radius=0.1, width=2.4, height=1.4, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(RIGHT * 4.6 + DOWN * 0.3)
        fat_lbl = Text("Fatbin 胖二进制\\n(打包多架构镜像)", font_size=FONT_BADGE_SIZE - 3, color=NVIDIA_GREEN, weight=BOLD).move_to(fat_box.get_center())

        a1 = Arrow(start=src_box.get_right(), end=ptx_box.get_left(), color=TEXT_SECONDARY, buff=0.1)
        a2 = Arrow(start=ptx_box.get_right(), end=cubin_box.get_left(), color=TEXT_SECONDARY, buff=0.1)
        a3 = Arrow(start=cubin_box.get_right(), end=fat_box.get_left(), color=TEXT_SECONDARY, buff=0.1)

        self.play(
            FadeIn(src_box), FadeIn(src_lbl),
            FadeIn(ptx_box), FadeIn(ptx_lbl),
            FadeIn(cubin_box), FadeIn(cubin_lbl),
            FadeIn(fat_box), FadeIn(fat_lbl),
            GrowArrow(a1), GrowArrow(a2), GrowArrow(a3),
            run_time={round(b1 * 0.6, 2)}
        )

        opt_badge = self.create_code_badge("Fatbin 兼顾极致性能 (Cubin 直跑) 与未来新卡兼容性 (JIT PTX)！", position=UP * 2.0)
        self.play(
            FadeOut(code_badge), FadeIn(opt_badge),
            fat_box.animate.set_color(NVIDIA_GREEN).set_fill(NVIDIA_GREEN, opacity=0.35),
            Flash(fat_box, color=NVIDIA_GREEN, flash_radius=1.3),
            run_time={round(b2 * 0.8, 2)}
        )
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    # ----------------- OTHER SUPPORTED ARCHITECTURAL TOPICS -----------------
    def _scene_bank_conflict(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaBankConflictScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("共享内存架构与 32-Bank 冲突", "32 Bank 并发访问 vs 硬件串行排队陷阱")
        code_badge = self.create_code_badge("float val = s_data[tid]; // 无冲突：1 对 1 物理映射", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.4)
        t_label = Text("Threads (t0 - t3)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(threads, UP, buff=0.2)

        banks = VGroup(*[MemorySlot(address_idx=i, width=1.1, height=1.1) for i in range(4)]).arrange(RIGHT, buff=0.35)
        for i, b in enumerate(banks):
            b.addr_label.become(Text(f"Bank {{i}}", font_size=FONT_BADGE_SIZE, color=TEXT_SECONDARY).next_to(b.box, DOWN, buff=0.1))
            b.set_value(f"B{{i}}")
        banks.move_to(DOWN * 1.6)
        b_label = Text("Shared Memory Banks (32路并发物理模块)", font_size=FONT_SUBTITLE_SIZE - 4, color=TEXT_SECONDARY).next_to(banks, UP, buff=0.2)
        self.play(FadeIn(threads), FadeIn(t_label), FadeIn(banks), FadeIn(b_label), run_time={round(b1 * 0.6, 2)})

        conflict_badge = self.create_code_badge("float val = s_data[tid * 2]; // 2路冲突：同时命中 Bank 0", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeIn(conflict_badge), run_time=0.5)

        c_arrow_0 = Arrow(start=threads[0].circle.get_bottom(), end=banks[0].box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        c_arrow_2 = Arrow(start=threads[2].circle.get_bottom(), end=banks[0].box.get_top(), color=THREAD_CONFLICT, buff=0.1)
        self.play(GrowArrow(c_arrow_0), GrowArrow(c_arrow_2), threads[0].circle.animate.set_color(THREAD_CONFLICT), threads[2].circle.animate.set_color(THREAD_CONFLICT), banks[0].box.animate.set_color(THREAD_CONFLICT), run_time={round(b2 * 0.6, 2)})

        fix_badge = self.create_code_badge("__shared__ float s[32][33]; // 填充列 (Padding) 错位消除冲突！", position=UP * 2.0)
        self.play(FadeOut(conflict_badge), FadeOut(c_arrow_0), FadeOut(c_arrow_2), FadeIn(fix_badge), run_time=0.5)
        self.play(*[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads], banks[0].box.animate.set_color(MEMORY_BORDER), run_time={round(b3 * 0.7, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    def _scene_coalesced(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaCoalescedScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, MemorySlot, ThreadItem

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("全局内存合并访问 (Coalescing)", "128 字节总线事务 vs 离散跨步浪费")
        code_badge = self.create_code_badge("float val = d_in[idx]; // 连续线程访连续内存：100% 带宽利用率", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=0.9)
        threads.move_to(UP * 0.5)
        bus_rect = RoundedRectangle(corner_radius=0.15, width=6.5, height=0.6, color=NVIDIA_GREEN, fill_color=CARD_BG, fill_opacity=0.9).move_to(DOWN * 0.4)
        bus_label = Text("GPU 显存总线事务 (128-Byte Transaction)", font_size=FONT_BADGE_SIZE, color=NVIDIA_GREEN).move_to(bus_rect.get_center())

        slots = VGroup(*[MemorySlot(address_idx=i, width=0.85, height=0.85) for i in range(6)]).arrange(RIGHT, buff=0.2)
        slots.move_to(DOWN * 1.7)
        self.play(FadeIn(threads), FadeIn(bus_rect), FadeIn(bus_label), FadeIn(slots), run_time={round(b1 * 0.6, 2)})

        bad_badge = self.create_code_badge("float val = d_in[idx * 4]; // 跨步访问：总线多次反复搬运，吞吐暴跌！", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeIn(bad_badge), bus_rect.animate.set_color(THREAD_CONFLICT), run_time={round(b2 * 0.6, 2)})

        fix_badge = self.create_code_badge("数据排布重构：AoS 转 SoA (对齐硬件扇区打满带宽)！", position=UP * 2.0)
        self.play(FadeOut(bad_badge), FadeIn(fix_badge), bus_rect.animate.set_color(NVIDIA_GREEN), *[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads], run_time={round(b3 * 0.7, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    def _scene_atomic(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaAtomicScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadItem

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("原子操作与竞态条件", "并发覆写丢失 vs 硬件独占锁")
        code_badge = self.create_code_badge("*counter = *counter + 1; // 读改写非原子：海量增量丢失", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        t0 = ThreadItem(block_id=0, thread_id=0).move_to(UP * 0.4 + LEFT * 2.5)
        t1 = ThreadItem(block_id=0, thread_id=1).move_to(UP * 0.4 + RIGHT * 2.5)
        counter_box = Square(side_length=1.4, color=MEMORY_BORDER, fill_color=CARD_BG, fill_opacity=0.9).move_to(DOWN * 1.3)
        counter_lbl = Text("Counter: 0", font_size=FONT_SUBTITLE_SIZE, color=TEXT_PRIMARY, weight=BOLD).move_to(counter_box.get_center())
        self.play(FadeIn(t0), FadeIn(t1), FadeIn(counter_box), FadeIn(counter_lbl), run_time={round(b1 * 0.6, 2)})

        atomic_badge = self.create_code_badge("atomicAdd(counter, 1); // 硬件级排队互斥锁", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeIn(atomic_badge), counter_box.animate.set_color(NVIDIA_GREEN), run_time={round(b2 * 0.6, 2)})
        counter_lbl.become(Text("Counter: 2", font_size=FONT_SUBTITLE_SIZE, color=NVIDIA_GREEN, weight=BOLD).move_to(counter_box.get_center()))
        self.play(t0.circle.animate.set_color(THREAD_RESOLVED), t1.circle.animate.set_color(THREAD_RESOLVED), run_time={round(b3 * 0.7, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class

    def _scene_syncthreads(self, topic: str, b1: float, b2: float, b3: float, pause: float, root: Path) -> Tuple[str, str]:
        scene_class = "CudaSyncthreadsScene"
        root_str = str(root).replace("\\", "\\\\")
        code = f'''# -*- coding: utf-8 -*-
from manim import *
import sys
sys.path.insert(0, r"{root_str}")
from assets.styles import *
from assets.cuda_manim_lib import CUDAThemeScene, ThreadItem

class {scene_class}(CUDAThemeScene):
    def construct(self):
        super().construct()
        header = self.create_header("块内线程同步屏障 (__syncthreads)", "步调异步脏读 vs 分支内屏障死锁禁忌")
        code_badge = self.create_code_badge("if (tid % 2 == 0) {{ __syncthreads(); }} // 致命禁忌：死锁挂起！", position=UP * 2.0)
        self.play(FadeIn(header), FadeIn(code_badge), run_time={round(b1 * 0.4, 2)})

        threads = VGroup(*[ThreadItem(block_id=0, thread_id=i) for i in range(4)]).arrange(RIGHT, buff=1.0).move_to(UP * 0.5)
        barrier = DashedLine(start=LEFT * 4.5, end=RIGHT * 4.5, color=THREAD_CONFLICT, dash_length=0.2, stroke_width=4).move_to(DOWN * 0.8)
        barrier_lbl = Text("同步栅栏 (__syncthreads Barrier)", font_size=FONT_BADGE_SIZE, color=THREAD_CONFLICT).next_to(barrier, UP, buff=0.15)
        self.play(FadeIn(threads), FadeIn(barrier), FadeIn(barrier_lbl), run_time={round(b1 * 0.6, 2)})

        deadlock_box = Text("! 硬件永久死锁 (Deadlock): 未走分支线程永不到达 !", font_size=FONT_SUBTITLE_SIZE - 2, color=THREAD_CONFLICT, weight=BOLD).next_to(barrier, DOWN, buff=0.25)
        self.play(FadeIn(deadlock_box), run_time={round(b2 * 0.5, 2)})

        safe_badge = self.create_code_badge("__syncthreads(); // 必须放置在公共无条件控制流中平稳通过！", position=UP * 2.0)
        self.play(FadeOut(code_badge), FadeOut(deadlock_box), FadeIn(safe_badge), barrier.animate.set_color(NVIDIA_GREEN), run_time=0.5)
        self.play(threads.animate.arrange(RIGHT, buff=1.0).move_to(DOWN * 1.8), *[t.circle.animate.set_color(THREAD_RESOLVED) for t in threads], run_time={round(b3 * 0.7, 2)})
        self.deliberate_pause({round(pause, 2)})
'''
        return code, scene_class
