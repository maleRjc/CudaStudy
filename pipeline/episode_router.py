"""
Map a curated episode onto the real PDF section.

Titles alone are noisy ("GPU", "CUDA" appear everywhere), so scoring uses
concept → section-title hints instead of bare token overlap. This also prevents
"GPU 线程索引" from being routed to a Multi-GPU chapter just because both
contain the word GPU.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

GENERIC_TOKENS = {
    "gpu",
    "gpus",
    "cuda",
    "programming",
    "program",
    "guide",
    "c++",
    "api",
    "system",
    "systems",
    "nvidia",
}

CONCEPT_HINTS = {
    "线程": ["thread", "programming model", "simt"],
    "索引": ["programming model", "thread", "simt"],
    "网格": ["programming model", "thread", "simt"],
    "物理地址": ["programming model", "memory"],
    "地址": ["programming model", "memory"],
    "thread": ["thread", "programming model", "simt"],
    "block": ["programming model", "thread"],
    "grid": ["programming model", "thread"],
    "index": ["programming model", "thread"],
    "warp": ["simt", "warp"],
    "simt": ["simt"],
    "分支": ["simt", "control flow"],
    "bank": ["tile", "shared memory"],
    "共享内存": ["tile", "shared memory"],
    "合并": ["memory", "coalescing", "global memory"],
    "访存": ["memory", "coalescing"],
    "显存": ["memory", "global memory"],
    "内存": ["memory", "programming model"],
    "寄存器": ["programming model", "memory"],
    "全局内存": ["memory", "global memory"],
    "多流": ["asynchronous", "stream"],
    "异步": ["asynchronous", "stream"],
    "重叠": ["asynchronous", "stream"],
    "统一内存": ["unified", "system memory"],
    "nvcc": ["nvcc", "compiler"],
    "编译": ["nvcc", "compiler"],
    "矩阵": ["tile", "matrix", "gemm"],
    "gemm": ["tile", "matrix"],
    "原子": ["atomic"],
    "同步": ["synchronization", "simt", "barrier"],
    "python": ["python"],
    "vector": ["intro to cuda"],
    "vector add": ["intro to cuda"],
    "第一个 cuda 程序": ["intro to cuda"],
    "多 gpu": ["multiple gpus"],
    "multiple gpu": ["multiple gpus"],
    "多卡": ["multiple gpus"],
}


def _score(section_title: str, episode_title: str) -> float:
    section = section_title.lower()
    episode = episode_title.lower()
    score = 0.0

    for concept, hints in CONCEPT_HINTS.items():
        if concept in episode:
            for hint in hints:
                if hint in section:
                    score += 12.0

    # Multi-GPU is explicit: do not let generic "GPU" steal other episodes.
    if any(term in episode for term in ("多 gpu", "多gpu", "multiple gpu", "多卡")):
        if "multiple gpus" in section:
            score += 40.0
        elif "multiple" in section:
            score += 12.0

    for token in re.findall(r"[a-z][a-z0-9+#.]{2,}", episode):
        if token in GENERIC_TOKENS:
            continue
        if token in section:
            score += 4.0

    return score


def resolve_episode_section(
    curriculum: List[Dict[str, Any]],
    episode: Dict[str, Any],
    episode_number: int,
) -> Optional[Dict[str, Any]]:
    if not curriculum:
        return None

    title = str(episode.get("title") or "")
    best = None
    best_score = -1.0
    for section in curriculum:
        score = _score(str(section.get("title", "")), title)
        # Mild preference for sections with enough material.
        score += min(section.get("page_count", 1), 30) * 0.02
        if score > best_score:
            best, best_score = section, score

    if best is None or best_score <= 1.0:
        best = max(curriculum, key=lambda s: s.get("page_count", 0))
        match_quality = "fallback"
    else:
        match_quality = "semantic"

    resolved = dict(best)
    resolved.update(
        {
            "sec_id": f"ep_{episode_number:02d}",
            "title": f"第{episode_number:02d}讲 · {title}",
            "level": 1,
            "index": episode_number,
            "episode_match": match_quality,
            "episode_source_section": best.get("title"),
        }
    )
    return resolved


def describe_match(section: Dict[str, Any]) -> str:
    return (
        f"{section.get('title')} ← {section.get('episode_source_section')} "
        f"(P{section.get('start_page')}-P{section.get('end_page')}, {section.get('episode_match')})"
    )
