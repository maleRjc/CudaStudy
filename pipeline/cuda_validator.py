"""
CUDA technical accuracy validator.

Audits the code that actually reaches the screen (``visual_spec.code_badge``,
``scene_plan.figure.lines`` and explicit bad/good code blocks), not a legacy
``code`` field that the deck schema never contained.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

BRANCH_SYNC = re.compile(
    r"if\s*\([^)]*(?:threadIdx|tid|lane)[^)]*\)\s*\{[^}]*__syncthreads\s*\(\s*\)",
    re.DOTALL,
)
BOUNDARY = re.compile(r"if\s*\(\s*(?:idx|i|tid|global_idx)\s*<\s*(?:n|N|size|num_elements)", re.IGNORECASE)
SHARED_2D = re.compile(r"__shared__\s+\w+\s+\w+\s*\[\s*(\d+)\s*\]\s*\[\s*(\d+)\s*\]")


class CudaAccuracyValidator:
    @staticmethod
    def audit_cuda_code(code: str) -> List[Dict[str, str]]:
        issues: List[Dict[str, str]] = []
        if not code or len(code.strip()) < 8:
            return issues

        if BRANCH_SYNC.search(code):
            issues.append(
                {
                    "severity": "CRITICAL",
                    "category": "死锁风险",
                    "message": "__syncthreads() 位于分支内：未进入分支的线程不会到达屏障，Block 将永久挂起。",
                }
            )

        has_index = ("blockIdx" in code and "threadIdx" in code) or "blockIdx.x * blockDim.x + threadIdx.x" in code
        has_boundary = bool(BOUNDARY.search(code))
        if has_index and not has_boundary and re.search(r"\b(d_out|out|dst|output)\s*\[", code):
            issues.append(
                {
                    "severity": "WARNING",
                    "category": "越界风险",
                    "message": "存在全局索引写入但没有 if (idx < N) 边界保护，尾块可能越界。",
                }
            )

        match = SHARED_2D.search(code)
        if match:
            stride = int(match.group(2))
            if stride % 32 == 0:
                issues.append(
                    {
                        "severity": "SUGGESTION",
                        "category": "Bank 冲突",
                        "message": f"共享内存列宽 {stride} 是 32 的倍数，存在 Bank 冲突；可填充为 [{stride}][{stride + 1}]。",
                    }
                )

        if re.search(r"\bwarpSize\b\s*=\s*16|\bhalf\s*warp\b", code):
            issues.append(
                {
                    "severity": "WARNING",
                    "category": "硬件规格",
                    "message": "NVIDIA Warp 固定为 32 线程，不要把半 Warp 概念误当作硬件规格。",
                }
            )
        return issues

    # ------------------------------------------------------------------
    @staticmethod
    def _iter_code(deck: Dict[str, Any]):
        for slide in deck.get("slides") or []:
            if not isinstance(slide, dict):
                continue
            visual = slide.get("visual_spec") or {}
            if not isinstance(visual, dict):
                continue
            candidates = []
            for key in ("code_badge", "bad_code", "good_code"):
                value = visual.get(key)
                if isinstance(value, str):
                    candidates.append(value)
                elif isinstance(value, (list, tuple)):
                    candidates.append("\n".join(str(v) for v in value))

            plan = visual.get("scene_plan") or {}
            figure = plan.get("figure") if isinstance(plan, dict) else None
            if isinstance(figure, dict):
                lines = figure.get("lines")
                if isinstance(lines, list):
                    candidates.append("\n".join(str(line) for line in lines))

            for code in candidates:
                if code and len(code.strip()) >= 8:
                    yield slide, code

    @staticmethod
    def audit_slide_deck(deck: Dict[str, Any]) -> Dict[str, Any]:
        total = 0
        for slide, code in CudaAccuracyValidator._iter_code(deck):
            issues = CudaAccuracyValidator.audit_cuda_code(code)
            if not issues:
                continue
            total += len(issues)
            notes = slide.setdefault("validator_notes", [])
            for issue in issues:
                if issue not in notes:
                    notes.append(issue)
                if issue["severity"] == "CRITICAL":
                    points = slide.setdefault("key_points", [])
                    marker = f"⚠️ 校验：{issue['message']}"
                    if marker not in points and len(points) < 7:
                        points.append(marker)

        deck["audit_status"] = {"passed": total == 0, "issues_count": total}
        if total:
            print(f"[!] CUDA 校验命中 {total} 条规则（已注入页面提示）")
        else:
            print("[+] CUDA 校验：未命中已知危险模式")
        return deck
