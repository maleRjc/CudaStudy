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

# NVCC: The NVIDIA CUDA Compiler
### 《CUDA C++ Programming Guide》权威深度精讲

> 基于认知冲突驱动 · PPT图文精讲 + 3Blue1Brown风格Manim动态微架构推演

---

## Slide 1：NVCC：CUDA 编译工具链全景
*类型：`title_overview`*

```cuda
nvcc -v my_kernel.cu
```

### 📌 核心知识点与板书：
- **nvcc 是 NVIDIA 官方 CUDA C/C++ 与 PTX 代码的编译工具链，属于 CUDA Toolkit 的一部分**
- **工具链包含编译器、链接器、PTX 汇编器和 Cubin 汇编器，由顶层 nvcc 工具统一协调**
- **nvcc 驱动离线编译，与 CUDA 运行时编译器 nvrtc 驱动的在线/JIT 编译形成对比**

### 🎙️ 讲师详细逐字口播讲稿：
> 同学们，今天我们要深入 CUDA 编程的核心工具——NVCC。你可以把 nvcc 想象成一个交响乐团的指挥，它本身不演奏乐器，但协调着编译器、链接器、PTX 汇编器和 Cubin 汇编器这些乐手，共同完成从源代码到可执行文件的华丽乐章。nvcc 属于 CUDA Toolkit，是离线编译的入口，而 nvrtc 则负责运行时在线编译，两者场景不同。理解 nvcc 的协调机制，是掌握 CUDA 构建过程的第一步。

---

## Slide 2：源文件与头文件：扩展名的秘密
*类型：`concept_breakdown`*

```cuda
.cu / .cuh / .cpp
```

### 📌 核心知识点与板书：
- **.c、.cpp、.cc、.cxx 为纯主机代码，nvcc 可接受但也可直接由主机编译器处理**
- **.cu 文件包含设备代码或主机/设备混合代码，是 CUDA 的核心源文件**
- **.cuh 头文件通常包含设备代码，与纯主机头文件 .h/.hpp 等区分**

### 🎙️ 讲师详细逐字口播讲稿：
> 在 CUDA 的世界里，文件扩展名不是随便起的，它告诉 nvcc 这个文件里藏着什么。.cu 文件是 CUDA 的主战场，里面可能既有 CPU 上跑的主机代码，也有 GPU 上跑的设备代码。而 .cuh 头文件则专门用来存放设备代码，比如 __device__ 函数声明。纯主机代码可以用 .c 或 .cpp，nvcc 也能处理，但更常见的是直接交给 gcc 或 clang。记住：扩展名是 nvcc 决定如何分流编译的第一线索。

---

## Slide 3：编译工作流：主机与设备的分离
*类型：`concept_breakdown`*

```cuda
nvcc -c file.cu -o file.o
```

### 📌 核心知识点与板书：
- **nvcc 首先将设备代码与主机代码分离，分别派发给 GPU 编译器和主机编译器**
- **主机编译需要兼容的宿主编译器（如 gcc、clang、MSVC），CUDA Toolkit 定义了支持策略**
- **纯主机代码文件可由 nvcc 或主机编译器直接构建，生成的目标文件可在链接时与 GPU 代码合并**

### 🎙️ 讲师详细逐字口播讲稿：
> nvcc 编译的第一步是“分家”：它把源代码中的设备代码和主机代码拆开。设备代码交给 GPU 编译器，主机代码交给宿主编译器。这就像翻译一本双语书，英文部分给英文编辑，中文部分给中文编辑。宿主编译器必须是 CUDA Toolkit 支持的版本，否则会出问题。纯主机代码的文件可以单独用 gcc 编译，生成 .o 文件，最后和 nvcc 生成的 GPU 目标文件链接在一起。这种分离机制是 CUDA 异构编程的基石。

---

## Slide 4：从 PTX 到 Cubin：虚拟与真实的桥梁
*类型：`manim_physics_demo`*

```cuda
nvcc -arch=sm_90 -code=sm_90,compute_90
```

### 📌 核心知识点与板书：
- **GPU 编译器将设备代码编译为 PTX 汇编，针对每个虚拟架构（如 compute_90）生成**
- **PTX 代码由 ptxas 工具汇编为 Cubin，针对具体硬件 ISA（SM 版本）**
- **多个 PTX 和 Cubin 目标可嵌入单个 Fatbin 容器，使一个二进制支持多种架构**

### 🎙️ 讲师详细逐字口播讲稿：
> 现在让我们用动态几何来可视化这个过程。想象 PTX 是一种“中间语言”，就像 Java 的字节码，它针对虚拟架构 compute_90 生成。然后 ptxas 工具把 PTX 翻译成 Cubin——这是 GPU 真正能执行的机器码，针对具体的 SM 版本，比如 sm_90。你可以把多个 PTX 和 Cubin 打包进一个 Fatbin 容器，就像瑞士军刀一样，一个二进制文件适配多种 GPU。nvcc 自动协调这一切，用 -v 选项可以看到完整流程，-keep 选项则保留中间文件供你研究。

---

## Slide 5：统一内存的限制与 NVLink C2C 的突破
*类型：`concept_breakdown`*

```cuda
__managed__ int global_var;
```

### 📌 核心知识点与板书：
- **cudaMallocFromPoolAsync 使用 allocType=cudaMemAllocationTypeManaged 的池时有特定行为**
- **__managed__ 说明符修饰的全局变量受统一内存管理**
- **Windows 和 Tegra 处理器上统一内存有限制；NVLink C2C 配合 ATS 时，cudaMallocManaged 分配的设备内存可被 CPU 或其他 GPU 直接访问**

### 🎙️ 讲师详细逐字口播讲稿：
> 统一内存并非万能。在 Windows 和 Tegra 上，它有硬件限制。但 NVLink C2C 连接的系统配合 ATS 技术，能让 CPU 或其他 GPU 直接访问 cudaMallocManaged 分配的内存，实现真正的对等访问。另外，使用 cudaMallocFromPoolAsync 时，如果池的分配类型是 cudaMemAllocationTypeManaged，行为会有所不同。__managed__ 全局变量也遵循统一内存规则。理解这些边界，才能写出可移植的高性能代码。

---

## Slide 6：实战：用 -v 和 -keep 洞察编译过程
*类型：`summary_best_practice`*

```cuda
nvcc -v -keep file.cu
```

### 📌 核心知识点与板书：
- **使用 nvcc -v 显示完整编译工作流和工具调用细节**
- **使用 nvcc -keep 保留中间文件（如 .ptx、.cubin）在当前目录或指定目录**
- **理解 Fatbin 容器如何嵌入多个 PTX 和 Cubin 目标以支持多架构**

### 🎙️ 讲师详细逐字口播讲稿：
> 最后，给大家两个实用技巧。-v 选项让 nvcc 变得“话痨”，它会打印出每一步调用了哪个工具、用了什么参数，是调试编译问题的利器。-keep 选项则把中间文件保留下来，比如生成的 PTX 和 Cubin，你可以用编辑器打开看看 GPU 汇编长什么样。结合 Fatbin 的概念，你能真正理解一个 CUDA 二进制如何同时支持多种 GPU 架构。多动手实验，编译过程就不再是黑盒。

---
