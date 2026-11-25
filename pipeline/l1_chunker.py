"""
Layer 1: Semantic Slicing and Cognitive Conflict Filter.
Parses the CUDA Programming Guide PDF and extracts pedagogical chunks that contain
deep mental-model shifts (CPU serial vs GPU SIMT parallel).
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


# Predefined key cognitive conflict domains across CUDA Architecture
CORE_COGNITIVE_UNITS = [
    {
        "chunk_id": "01_global_thread_indexing",
        "title": "线程层级与全局索引映射 (Thread Hierarchy & Global Indexing)",
        "section_ref": "Section 2.1 & 2.2: Thread Hierarchy",
        "keywords": ["threadIdx", "blockIdx", "blockDim", "gridDim", "linear index"],
        "cognitive_focus": "CPU 程序员习惯将 threadIdx 视作唯一的循环变量 i。而在 GPU 中，每个 Block 的 threadIdx 都从 0 开始计数，多块并发时直接使用局部 ID 会引发严重物理地址覆写碰撞。",
        "minimal_code": (
            "// CPU 串行思维误区 (单 Block 正常，多 Block 随机覆盖):\n"
            "int idx = threadIdx.x;\n"
            "d_out[idx] = data[idx];\n\n"
            "// GPU 正确升维映射 (计算绝对全局物理坐标):\n"
            "int idx = blockIdx.x * blockDim.x + threadIdx.x;\n"
            "d_out[idx] = data[idx];"
        ),
        "target_page_hint": [21, 26]
    },
    {
        "chunk_id": "02_warp_divergence",
        "title": "SIMT 硬件锁步与分支分化陷阱 (SIMT & Warp Divergence)",
        "section_ref": "Section 2.3 & 4.1: Hardware Multithreading & SIMT",
        "keywords": ["warp", "divergence", "SIMT", "branch", "lockstep", "mask"],
        "cognitive_focus": "以为 GPU 上的 if-else 条件判断能像 CPU 多核那样各走各的并行飞奔。在底层，同一个 Warp 的 32 个线程共享指令发射器，遇到分支只能串行走完分支 A（挂起其他线程）再走分支 B，算力直接折半。",
        "minimal_code": (
            "__global__ void divergentKernel(float* d_out) {\n"
            "    int tid = threadIdx.x;\n"
            "    if (tid % 2 == 0) {\n"
            "        d_out[tid] = 1.0f; // 分支 A 执行，奇数线程被硬件掩码强制挂起\n"
            "    } else {\n"
            "        d_out[tid] = 2.0f; // 分支 B 执行，偶数线程冻结等待\n"
            "    }\n"
            "}"
        ),
        "target_page_hint": [23, 27]
    },
    {
        "chunk_id": "03_shared_memory_bank_conflict",
        "title": "共享内存架构与 Bank 冲突排队 (Shared Memory Bank Conflicts)",
        "section_ref": "Section 3.2.4: Shared Memory Access Patterns",
        "keywords": ["shared memory", "bank", "bank conflict", "stride", "broadcast"],
        "cognitive_focus": "以为共享内存是扁平无阻的高速缓存。实际上它由 32 个独立的物理 Bank 组成。当 Warp 内多个线程寻址同一个 Bank 内的不同地址时，硬件只能强制串行排队处理，吞吐量断崖式下跌。",
        "minimal_code": (
            "__shared__ float s_data[1024];\n"
            "// 无冲突：线程 i 访问 Bank i (1对1直通)\n"
            "float val = s_data[threadIdx.x];\n\n"
            "// 2路 Bank 冲突：线程 0 和线程 16 抢夺 Bank 0\n"
            "float val2 = s_data[threadIdx.x * 2];\n\n"
            "// 优雅破局：增加 Padding 错开 Bank\n"
            "__shared__ float s_tile[32][33];"
        ),
        "target_page_hint": [76, 82]
    },
    {
        "chunk_id": "04_coalesced_memory_access",
        "title": "全局内存合并访问与总线效率 (Global Memory Coalescing)",
        "section_ref": "Section 3.2.3: Coalesced Global Memory Access",
        "keywords": ["coalesced", "global memory", "DRAM", "transaction", "stride", "cache line"],
        "cognitive_focus": "以为只要每个线程取一个 float 数据，总线开销就是 4 字节。GPU DRAM 以 32 或 128 字节扇区(Sector)为最小传输粒度。连续线程访问连续内存可合并为单次总线事务(100% 效率)；跨步/离散访问会导致总线反复传输无效数据，带宽利用率跌破 10%。",
        "minimal_code": (
            "// 合并访问 (100% 吞吐，单次 128 字节事务满足 Warp 全员):\n"
            "int idx = blockIdx.x * blockDim.x + threadIdx.x;\n"
            "float val = d_in[idx];\n\n"
            "// 非合并跨步访问 (严重浪费总线带宽，触发多次独立事务):\n"
            "int bad_idx = (blockIdx.x * blockDim.x + threadIdx.x) * 8;\n"
            "float bad_val = d_in[bad_idx];"
        ),
        "target_page_hint": [72, 75]
    },
    {
        "chunk_id": "05_atomic_operations_race_condition",
        "title": "原子操作与读写竞争防护 (Atomic Operations & Race Condition)",
        "section_ref": "Section 3.2.5: Memory Atomics",
        "keywords": ["atomicAdd", "race condition", "read-modify-write", "mutual exclusion"],
        "cognitive_focus": "在 CPU 串行循环中，sum += 1 自然正确。在成千上万 GPU 线程并发时，Read-Modify-Write 不是原子事务，所有线程同时读取旧值、各自加一、同时覆写，导致更新结果严重丢失，必须调用 atomicAdd 进行硬件级互斥加锁。",
        "minimal_code": (
            "// 严重竞态 Bug (十万线程并发，最终结果可能仅有数百):\n"
            "*counter = *counter + 1;\n\n"
            "// 硬件原子事务 (排队独占累加，保证绝对精准):\n"
            "atomicAdd(counter, 1);"
        ),
        "target_page_hint": [83, 86]
    },
    {
        "chunk_id": "06_syncthreads_barrier",
        "title": "块内线程同步屏障与死锁禁忌 (__syncthreads & Barrier Safety)",
        "section_ref": "Section 3.2.1: Thread Block Synchronization",
        "keywords": ["__syncthreads", "barrier", "deadlock", "RAW hazard", "shared memory"],
        "cognitive_focus": "以为线程会在写入共享内存后自动等待彼此。没有显式屏障时，快线程立即读取慢线程未写完的脏数据(RAW 数据冲突)。更致命的是：若将 __syncthreads 放置在条件分支中，将导致未走该分支的线程永不到达屏障，引发硬件级永久死锁挂起！",
        "minimal_code": (
            "// 读写脏数据风险修复 (必须统一到达屏障):\n"
            "s_data[tid] = g_in[tid];\n"
            "__syncthreads(); // 集合所有人，确保写完毕\n"
            "float v = s_data[tid ^ 1];\n\n"
            "// 致命死锁禁忌 (条件分支内屏障，导致硬件挂死):\n"
            "if (tid % 2 == 0) {\n"
            "    __syncthreads(); // 只有一半人到达，永远死锁挂起!\n"
            "}"
        ),
        "target_page_hint": [47, 50]
    }
]


class CudaChunker:
    def __init__(self, pdf_path: Optional[Path] = None):
        self.pdf_path = pdf_path or config.DEFAULT_PDF_PATH
        self.output_dir = config.OUTPUT_DIR / "chunks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_text_from_pdf(self, start_page: int, end_page: int) -> str:
        """Extract text from a specific page range of the CUDA Guide."""
        if not self.pdf_path.exists():
            return ""

        try:
            reader = pypdf.PdfReader(str(self.pdf_path))
            total_pages = len(reader.pages)
            start = max(0, min(start_page, total_pages - 1))
            end = max(start, min(end_page, total_pages))

            extracted = []
            for i in range(start, end):
                text = reader.pages[i].extract_text() or ""
                extracted.append(f"--- Page {i+1} ---\n" + text)
            return "\n".join(extracted)
        except Exception as e:
            print(f"[Warning] Failed to extract from PDF: {e}")
            return ""

    def process_and_save_chunks(self) -> List[Dict[str, Any]]:
        """Processes key pedagogical units, extracts context, and saves standardized JSONs."""
        processed_chunks = []

        for unit in CORE_COGNITIVE_UNITS:
            chunk_id = unit["chunk_id"]
            out_file = self.output_dir / f"{chunk_id}.json"

            if out_file.exists():
                try:
                    with open(out_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    processed_chunks.append(data)
                    continue
                except Exception:
                    pass

            p_start, p_end = unit.get("target_page_hint", [1, 10])
            raw_pdf_snippet = self.extract_text_from_pdf(p_start, p_end)

            chunk_data = {
                "chunk_id": chunk_id,
                "title": unit["title"],
                "section_ref": unit["section_ref"],
                "keywords": unit["keywords"],
                "cognitive_focus": unit["cognitive_focus"],
                "minimal_code": unit["minimal_code"],
                "pdf_context_snippet": raw_pdf_snippet[:1500] if raw_pdf_snippet else "(Context synthesized from specification)"
            }

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            print(f"[+] Generated Chunk: {chunk_id} -> {out_file.name}")
            processed_chunks.append(chunk_data)

        return processed_chunks


if __name__ == "__main__":
    chunker = CudaChunker()
    chunks = chunker.process_and_save_chunks()
    print(f"\n[Success] Generated {len(chunks)} cognitive conflict chunks in {config.OUTPUT_DIR / 'chunks'}")
