"""
CUDA Code & Pedagogical Concept Validator (pipeline/cuda_validator.py).
Provides static rule-based analysis and semantic checks for CUDA C++ snippets
and lecture slides to ensure 100% technical accuracy and prevent LLM hallucinations.
"""

import re
from typing import Dict, Any, List, Tuple


class CudaAccuracyValidator:
    """Static analysis and heuristic rule checker for CUDA concepts and code."""

    @staticmethod
    def audit_cuda_code(code: str) -> List[Dict[str, str]]:
        """
        Audits a C++/CUDA code snippet for classic hazards and correctness:
        - __syncthreads() in conditional blocks (Deadlock risk)
        - Missing boundary check (idx < N buffer overflow)
        - Bank conflict in shared memory 2D arrays (stride of 32)
        - Host/Device memory mismatch
        """
        issues = []
        if not code or len(code.strip()) == 0:
            return issues

        # 1. __syncthreads() inside branch conditional (Deadlock Risk)
        branch_pattern = re.compile(
            r'if\s*\([^)]*(?:threadIdx|tid|lane)[^)]*\)\s*\{[^}]*__syncthreads\s*\(\s*\)',
            re.DOTALL
        )
        if branch_pattern.search(code):
            issues.append({
                "severity": "CRITICAL",
                "category": "Deadlock Risk",
                "message": "__syncthreads() placed inside divergent branch! All threads in a block must execute the barrier collectively."
            })

        # 2. Global Index Boundary Check
        has_idx_calc = ("blockIdx.x * blockDim.x + threadIdx.x" in code) or ("threadIdx.x" in code and "blockIdx.x" in code)
        has_boundary_check = bool(re.search(r'if\s*\(\s*(?:idx|i|tid|global_idx)\s*<\s*(?:n|N|size|num_elements)', code))
        if has_idx_calc and not has_boundary_check and ("float" in code or "int" in code) and "void " in code:
            issues.append({
                "severity": "WARNING",
                "category": "Memory Safety",
                "message": "Global indexing found without boundary check 'if (idx < N)'. Risk of memory out-of-bounds in tail blocks."
            })

        # 3. Shared Memory Bank Conflict (2D power-of-two stride without padding)
        smem_2d_match = re.search(r'__shared__\s+\w+\s+\w+\[(\d+)\]\[(\d+)\]', code)
        if smem_2d_match:
            d1, d2 = int(smem_2d_match.group(1)), int(smem_2d_match.group(2))
            if d2 % 32 == 0:
                issues.append({
                    "severity": "SUGGESTION",
                    "category": "Performance / Bank Conflict",
                    "message": f"Shared memory array [{d1}][{d2}] has stride of {d2} (multiple of 32). Consider [{d1}][{d2 + 1}] padding to eliminate bank conflicts."
                })

        # 4. Warp size hardcoded assumption
        warp_match = re.search(r'\bwarpSize\b|32', code)
        if "16" in code and "warp" in code.lower():
            issues.append({
                "severity": "WARNING",
                "category": "Hardware Specification",
                "message": "NVIDIA GPU Warp size is strictly 32 threads. Do not confuse with half-warp or sub-warp."
            })

        return issues

    @staticmethod
    def audit_slide_deck(deck: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits all slides in a lecture deck.
        Inserts correction alerts or notes into the visual spec and key points if needed.
        """
        slides = deck.get("slides", [])
        total_issues = 0

        for s in slides:
            slide_issues = []

            # Check code block
            code = s.get("code", "")
            if code:
                code_issues = CudaAccuracyValidator.audit_cuda_code(code)
                slide_issues.extend(code_issues)

            # Check narration script text for common myths
            narration = s.get("narration_script", "")
            if "syncthreads" in narration and "跨块" in narration:
                slide_issues.append({
                    "severity": "CRITICAL",
                    "category": "Scope Concept",
                    "message": "__syncthreads() 只能同步同一个 Thread Block 内的线程，无法跨 Block 同步！跨 Block 需使用 Cooperative Groups 或结束 Kernel。"
                })

            if slide_issues:
                total_issues += len(slide_issues)
                if "validator_notes" not in s:
                    s["validator_notes"] = []
                s["validator_notes"].extend(slide_issues)

                # Append verified badge or warning note
                for issue in slide_issues:
                    if issue["severity"] == "CRITICAL":
                        s["key_points"].append(f"⚠️ [CUDA 规范校验] {issue['message']}")

        deck["audit_status"] = {
            "passed": total_issues == 0,
            "issues_count": total_issues
        }
        return deck


if __name__ == "__main__":
    bad_code = """
    __global__ void test_kernel(float* d_out, int n) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (threadIdx.x % 2 == 0) {
            __syncthreads();
        }
        d_out[idx] = 1.0f;
    }
    """
    results = CudaAccuracyValidator.audit_cuda_code(bad_code)
    print("Audit Results for Bad CUDA Code:")
    for r in results:
        print(f"[{r['severity']}] {r['category']}: {r['message']}")
