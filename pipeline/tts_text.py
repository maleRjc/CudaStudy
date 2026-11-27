"""
Make narration TTS-friendly.

CUDA syntax is not speakable: ``MyKernel<<<1000,128>>>`` was read as a chain of
"小于", and ``__syncthreads()`` as underscores. Replace code constructs with
spoken Chinese before synthesis; the code itself stays intact in the slide.
``blockIdx.x`` becomes "块索引变量的 x 分量" rather than a hybrid English term.
"""

from __future__ import annotations

import re

_LAUNCH_RE = re.compile(r"<<<\s*([^<>]*?)\s*>>>")

_REPLACEMENTS = [
    (r"__syncthreads\s*\(\s*\)", "同步屏障"),
    (r"__global__", "global 函数"),
    (r"__device__", "device 函数"),
    (r"__shared__", "shared 内存"),
    (r"__host__", "host 函数"),
    (r"cudaMemcpyPeer", "cuda 设备间拷贝"),
    (r"cudaMemcpyAsync", "cuda 异步拷贝"),
    (r"cudaMemcpy", "cuda 内存拷贝"),
    (r"cudaMallocManaged", "cuda 统一内存分配"),
    (r"cudaMalloc", "cuda 内存分配"),
    (r"cudaFree", "cuda 内存释放"),
    (r"cudaSetDevice", "cuda 设置设备"),
    (r"cudaGetDevice", "cuda 获取设备"),
    (r"cudaStreamCreate", "cuda 创建流"),
    (r"cudaStreamSynchronize", "cuda 流同步"),
    (r"cudaDeviceSynchronize", "cuda 设备同步"),
    (r"blockIdx", "块索引变量"),
    (r"threadIdx", "线程索引变量"),
    (r"blockDim", "块维度变量"),
    (r"gridDim", "网格维度变量"),
    (r"#\s*include", "包含头文件"),
    (r"#\s*define", "定义宏"),
    (r"->", "指向"),
    (r"&&", "并且"),
    (r"\|\|", "或者"),
    (r"!=", "不等于"),
    (r">=", "大于等于"),
    (r"<=", "小于等于"),
    (r"==", "等于"),
    (r"%", "百分号"),
]


def normalize_for_speech(text: str) -> str:
    """Convert code-ish narration into something a Chinese TTS can read."""
    result = str(text or "")

    # kernel<<<grid, block>>> -> kernel，启动配置为 grid 和 block，
    result = _LAUNCH_RE.sub(lambda match: f"，启动配置为 {match.group(1).replace(',', ' 和 ')}，", result)
    result = result.replace("<<<", "三尖括号").replace(">>>", "三尖括号")

    for pattern, replacement in _REPLACEMENTS:
        result = re.sub(pattern, replacement, result)

    # 块索引变量.x -> 块索引变量的 x 分量
    result = re.sub(r"(块索引变量|线程索引变量|块维度变量|网格维度变量)\.([xyz])", r"\1的 \2 分量", result)
    # strip leftover dunder decoration
    result = re.sub(r"__(\w+)__", r"\1", result)

    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r"，\s*，", "，", result)
    result = re.sub(r"！\s*！", "！", result)
    return result.strip()


if __name__ == "__main__":
    sample = "启动 MyKernel<<<1000,128>>>(p0)，并在 if (idx < N) 内调用 __syncthreads()。"
    print(normalize_for_speech(sample))
