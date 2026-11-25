---
marp: true
theme: gaia
_class: lead
paginate: true
backgroundColor: #0D1117
color: #FFFFFF
style: |
  section { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; }
  h1 { color: #76B900; }
  h2 { color: #58A6FF; }
  code { background-color: #161B22; color: #7EE787; padding: 2px 6px; border-radius: 4px; }
  blockquote { background: #161B22; border-left: 6px solid #76B900; padding: 10px 16px; margin: 15px 0; }
---

# Writing Tile Kernels
### 《CUDA C++ Programming Guide》权威深度精讲

> 基于认知冲突驱动 · PPT图文精讲 + 3Blue1Brown风格Manim动态微架构推演

---

## Slide 1：从 SIMT 到 Tile：编程范式的跃迁
*类型：`title_overview`*

```cuda
import cuda.tile as ct  //  namespace ct = cuda::tiles
```

### 📌 核心知识点与板书：
- **Tile 编程将最低层级的并行映射交给编译器，程序员以“块”为单位思考**
- **Tile 内核可自动利用 TMA 和 Tensor Core 等新硬件特性**
- **Python 通过 cuda.tile 使用，C++ 通过 cuda::tiles 使用，共享 CUDA Tile IR 后端**

### 🎙️ 讲师详细逐字口播讲稿：
> 同学们，之前我们一直用 SIMT 模型写核函数，每个线程都要自己算全局索引、加载自己的元素、做运算、再存回去。现在 CUDA 13.3 引入了 Tile 编程，它把视角从“单个线程”提升到“整个线程块”。你只需要描述“加载一个瓦片、对整块做运算、存回结果”，编译器会自动把瓦片操作映射到硬件线程上，并利用 TMA 和 Tensor Core 这些新硬件。Python 里用 cuda.tile，C++ 里用 cuda::tiles，两者共享同一个 CUDA Tile IR 后端，所以语义完全一致。记住，核函数外面的内存分配、数据传输和启动方式完全不变，变的只是核函数内部的写法。

---

## Slide 2：SIMT 与 Tile 的心智模型对比
*类型：`concept_breakdown`*

```cuda
SIMT: idx = blockIdx.x * blockDim.x + threadIdx.x;  Tile: tile = ct.load(...)
```

### 📌 核心知识点与板书：
- **SIMT：程序员显式计算线程索引，处理单个元素**
- **Tile：程序员操作整个数据块，编译器负责线程映射**
- **Tile 简化了代码，但要求程序员理解块级数据流**

### 🎙️ 讲师详细逐字口播讲稿：
> 我们来对比两种心智模型。在 SIMT 里，你写代码时脑子里想的是“我是第几个线程，我该处理哪个元素”，所以你会看到 threadIdx.x、blockIdx.x 这些索引计算。而在 Tile 里，你不再关心单个线程，你写的是“加载一个 128x128 的瓦片到片上，然后做矩阵乘，再存回去”。编译器会把这个瓦片操作拆分成许多线程去执行，并且自动使用 TMA 做高效的数据搬运。这就像你从“手工作坊”升级到“流水线”：你只需要设计流水线的工序，具体每个工人怎么动，由调度系统安排。

---

## Slide 3：Tile 内核的代码结构：入口与操作
*类型：`code_misconception`*

```cuda
auto tile = ct::load(global_ptr, ct::shape<128,128>{}, ct::stride{ld});
```

### 📌 核心知识点与板书：
- **Tile 内核入口使用 __global__ 或 ct.kernel 装饰器**
- **瓦片操作包括 load、store、mma 等，均以块为单位**
- **常见误区：以为 Tile 内核不需要考虑数据布局**

### 🎙️ 讲师详细逐字口播讲稿：
> 很多同学第一次写 Tile 内核，以为只要把 load 和 store 一写就完事了，结果性能很差。问题出在数据布局上。Tile 操作虽然隐藏了线程映射，但瓦片在全局内存中的布局仍然影响合并访问和 TMA 效率。比如你加载一个二维瓦片，如果全局内存的行跨度不是连续的，TMA 就需要多次传输。所以写 Tile 内核时，你仍然要像优化 SIMT 那样考虑内存对齐和连续性，只是现在你通过瓦片的形状和步长来描述，而不是通过线程索引。

---

## Slide 4：硬件加速：TMA 与 Tensor Core 的自动利用
*类型：`manim_physics_demo`*

```cuda
ct.load -> TMA; ct.mma -> Tensor Core MMA
```

### 📌 核心知识点与板书：
- **Tile 编译器自动将瓦片加载映射为 TMA 异步拷贝**
- **矩阵乘瓦片操作自动映射到 Tensor Core 的 MMA 指令**
- **数据流：全局内存 -> 共享内存 -> 寄存器 -> Tensor Core**

### 🎙️ 讲师详细逐字口播讲稿：
> 现在让我们通过动画看看 Tile 内核在硬件上到底发生了什么。当你写 ct.load 加载一个瓦片时，编译器会生成 TMA 指令，由 TMA 引擎异步地把一大块数据从全局内存搬到共享内存，这个过程不占用线程的寄存器。接着，当你写 ct.mma 做矩阵乘时，编译器会生成 Tensor Core 的 MMA 指令，数据从共享内存加载到寄存器，再送入 Tensor Core 阵列进行并行乘加。整个过程中，线程只需要发出指令，实际的数据搬运和计算由专用硬件完成，这就是 Tile 编程能轻松获得高性能的原因。

---

## Slide 5：Tile 内核的启动与内存管理
*类型：`math_architecture_resolution`*

```cuda
kernel<<<grid, block>>>(d_A, d_B, d_C);  // 主机端不变
```

### 📌 核心知识点与板书：
- **主机端代码与 SIMT 完全相同：cudaMalloc、cudaMemcpy、<<<>>>**
- **Tile 内核操作标准 CUDA 全局内存**
- **核函数内部通过 ct 命名空间调用瓦片操作**

### 🎙️ 讲师详细逐字口播讲稿：
> 有些同学担心 Tile 内核需要特殊的内存分配方式，其实完全不用。主机端的代码，包括 cudaMalloc 分配设备内存、cudaMemcpy 传输数据、以及用 <<<grid, block>>> 启动核函数，都和以前一模一样。Tile 内核只是核函数内部写法不同，它操作的是标准的 CUDA 全局内存。你甚至可以在同一个程序里混合使用 SIMT 内核和 Tile 内核。唯一需要注意的是，Tile 内核的 block 大小通常由瓦片形状决定，编译器会帮你推导出合适的线程数，所以你不需要手动指定 blockDim。

---

## Slide 6：性能调优：占用率与寄存器控制
*类型：`summary_best_practice`*

```cuda
nvcc --maxrregcount=32 ...
```

### 📌 核心知识点与板书：
- **占用率受线程块大小和共享内存用量影响，可由程序员调整**
- **寄存器用量由编译器优化，但可用 --maxrregcount 限制**
- **限制寄存器可能导致溢出到本地内存，需权衡占用率与溢出**

### 🎙️ 讲师详细逐字口播讲稿：
> 最后我们回顾一下性能调优的关键点。占用率取决于每个 SM 上能驻留多少线程块，这又受限于线程块大小和共享内存用量。比如一个 SM 有 2048 个线程和 233KB 共享内存，如果你每个块用 100KB 共享内存，那么最多只能放两个块。寄存器用量虽然由编译器决定，但你可以用 --maxrregcount 限制每个线程的寄存器数，从而让更多块驻留。但要注意，限制太狠会导致寄存器溢出到本地内存，反而变慢。所以调优时要找到平衡点，有时牺牲一点溢出换取更高占用率，整体性能反而提升。

---
