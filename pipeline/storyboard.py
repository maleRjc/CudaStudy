"""
Storyboard planning for per-slide Manim animation (v2).

The plan is a JSON-able choreography description. The renderer in
``assets/storyboard_scene.py`` executes it deterministically, so no LLM-authored
Python is run.

Kinds:
  warp      - 32 threads in a warp, divergence / reconvergence
  banks     - 32 shared-memory banks, stride conflicts, padding fix
  coalesce  - coalesced vs strided global-memory transactions
  matrix    - tiled GEMM / shared-memory reuse
  grid      - generic grid / block / thread mapping
  boxes     - generic flow diagram with animated particles
  timeline  - async streams / overlap
  code      - code walkthrough with line highlighting
  compare   - side-by-side correct vs wrong
  bars      - benchmark-style bars
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

PLAN_SCHEMA_VERSION = "plan-v2"

KINDS = (
    "warp",
    "banks",
    "coalesce",
    "matrix",
    "grid",
    "boxes",
    "timeline",
    "code",
    "compare",
    "bars",
)

ANIMATED_SLIDE_TYPES = {
    "manim_physics_demo",
    "code_diff",
    "code_misconception",
    "memory_layout",
    "profiler_timeline",
    "benchmark_chart",
    "metaphor_sketch",
    "concept_breakdown",
    "math_architecture_resolution",
}

KIND_KEYWORDS = {
    "warp": ("warp", "simt", "divergen", "lockstep", "分支分化", "线程束"),
    "banks": ("bank", "shared memory", "smem", "padding", "共享内存"),
    "coalesce": ("coalesc", "合并访问", "合并访存", "总线事务", "跨步"),
    "matrix": ("gemm", "matrix", "matmul", "tiling", "分块", "矩阵乘"),
    "timeline": ("stream", "async", "overlap", "nsight", "异步", "流水线", "重叠"),
    "code": ("__global__", "kernel", "代码", "code"),
    "compare": ("反例", "误区", "对比", "correct", "wrong"),
    "bars": ("benchmark", "throughput", "gflops", "加速比", "吞吐"),
    "grid": ("thread", "block", "grid", "index", "索引", "线程"),
}


def choose_kind(title: str, body: str = "") -> str:
    """Pick a figure kind with title hits weighted much higher than body mentions."""
    title = (title or "").lower()
    body = (body or "").lower()
    best_kind, best_score = "boxes", 0.0
    for kind, keywords in KIND_KEYWORDS.items():
        title_hits = sum(1 for kw in keywords if kw in title)
        body_hits = sum(1 for kw in keywords if kw in body)
        score = title_hits * 10.0 + body_hits * 2.0
        if kind == "warp":
            # "warp" appears in many explanations; require more evidence to win.
            score *= 0.85
        if score > best_score:
            best_kind, best_score = kind, score
    return best_kind if best_score > 0 else "boxes"


def _clip(text: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rstrip()
    if " " in cut and re.search(r"[A-Za-z]", cut[-1:]) and not re.search(r"[\u4e00-\u9fff]", cut):
        cut = cut[: cut.rfind(" ")].rstrip()
    return cut + "…"


def _clean_list(values: Any, limit: int = 4, chars: int = 64) -> List[str]:
    out: List[str] = []
    if isinstance(values, (list, tuple)):
        for value in values:
            text = _clip(value, chars)
            if text and text not in out:
                out.append(text)
            if len(out) >= limit:
                break
    return out


def _as_int_list(value: Any, upper: int) -> List[int]:
    if not isinstance(value, (list, tuple)):
        return []
    out: List[int] = []
    for item in value:
        try:
            idx = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < upper and idx not in out:
            out.append(idx)
    return out


def _focusable_count(kind: str, figure: Dict[str, Any]) -> int:
    if kind in ("grid", "warp"):
        return int(figure.get("rows", 4)) * int(figure.get("cols", 8))
    if kind == "banks":
        return int(figure.get("banks", 32))
    if kind == "coalesce":
        return int(figure.get("threads", 8)) * 2
    if kind == "matrix":
        size = int(figure.get("size", 4))
        return size * size
    if kind == "bars":
        return len(figure.get("items") or [])
    if kind == "timeline":
        return len(figure.get("rows") or [])
    if kind == "boxes":
        return len(figure.get("nodes") or [])
    if kind == "code":
        return len(figure.get("lines") or [])
    return 2


def _default_focus(kind: str, step_index: int, count: int) -> List[int]:
    if count <= 0:
        return []
    if kind == "warp":
        evens = [i for i in range(count) if i % 2 == 0]
        odds = [i for i in range(count) if i % 2 == 1]
        return [list(range(count)), evens, odds, list(range(count))][min(step_index, 3)]
    if kind == "banks":
        stride = 2
        banks = [0, stride, stride * 2, stride * 3]
        return [[i for i in range(min(8, count))], [b % count for b in banks], [i for i in range(min(8, count))]][min(step_index, 2)]
    if kind == "coalesce":
        half = max(1, count // 2)
        return [list(range(half)), list(range(half, count)), list(range(min(4, count)))][min(step_index, 2)]
    if kind == "matrix":
        size = int(count ** 0.5) or 1
        return [list(range(count)), list(range(0, size * min(2, size))), list(range(count // 2))][min(step_index, 2)]
    if kind == "grid" and step_index == 0:
        return list(range(min(4, count)))
    if kind in ("bars", "timeline", "boxes", "code"):
        return [step_index % count]
    return [step_index % count]


def _figure_for_kind(kind: str, source: Dict[str, Any], slide: Dict[str, Any]) -> Dict[str, Any]:
    raw = source.get("figure") if isinstance(source.get("figure"), dict) else {}
    points = slide.get("key_points") or []
    code_badge = str((slide.get("visual_spec") or {}).get("code_badge") or "")

    if kind == "warp":
        return {"threads": 32, "rows": 4, "cols": 8, "title": _clip(raw.get("title", "Warp = 32 Threads"), 34)}

    if kind == "banks":
        return {
            "banks": 32,
            "stride": max(1, min(int(raw.get("stride", 2)), 8)),
            "threads": 8,
            "title": _clip(raw.get("title", "Shared Memory · 32 Banks"), 34),
        }

    if kind == "coalesce":
        return {"threads": 8, "segments": 4, "title": _clip(raw.get("title", "Global Memory Transaction"), 34)}

    if kind == "matrix":
        size = max(2, min(int(raw.get("size", 4)), 6))
        return {"size": size, "tile": max(1, min(int(raw.get("tile", 2)), size)), "title": _clip(raw.get("title", "Tiled GEMM"), 34)}

    if kind == "grid":
        rows = max(1, min(int(raw.get("rows") or 4), 8))
        cols = max(1, min(int(raw.get("cols") or 8), 12))
        labels = _clean_list(raw.get("labels"), limit=rows * cols, chars=12)
        labels += [f"{i}" for i in range(len(labels), rows * cols)]
        return {"rows": rows, "cols": cols, "labels": labels[: rows * cols]}

    if kind == "bars":
        items = raw.get("items")
        if not isinstance(items, list) or not items:
            items = []
            for idx, point in enumerate(points[:4]):
                match = re.search(r"(\d+(?:\.\d+)?)\s*(x|倍|%|GB/s|GFLOPS|ms)?", str(point))
                value = float(match.group(1)) if match else float(30 + idx * 20)
                items.append({"label": _clip(point, 18), "value": value, "unit": (match.group(2) or "") if match else ""})
        cleaned = []
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            try:
                value = float(item.get("value", 0))
            except (TypeError, ValueError):
                value = 0.0
            cleaned.append({"label": _clip(item.get("label", ""), 18), "value": max(0.0, value), "unit": _clip(item.get("unit", ""), 8)})
        return {"items": cleaned or [{"label": "baseline", "value": 1.0, "unit": "x"}]}

    if kind == "timeline":
        rows = raw.get("rows")
        if not isinstance(rows, list) or not rows:
            rows = [
                {"label": "Stream 0 · 串行", "segments": [{"start": 0, "end": 3, "label": "H2D"}, {"start": 3, "end": 7, "label": "Kernel"}, {"start": 7, "end": 9, "label": "D2H"}]},
                {"label": "Stream 1 · 异步", "segments": [{"start": 2, "end": 5, "label": "H2D"}, {"start": 5, "end": 8, "label": "Kernel"}]},
            ]
        cleaned_rows = []
        for row in rows[:4]:
            if not isinstance(row, dict):
                continue
            segments = []
            for seg in (row.get("segments") or [])[:5]:
                if not isinstance(seg, dict):
                    continue
                try:
                    start = float(seg.get("start", 0))
                    end = float(seg.get("end", start + 1))
                except (TypeError, ValueError):
                    continue
                segments.append({"start": start, "end": max(end, start + 0.2), "label": _clip(seg.get("label", ""), 12)})
            if segments:
                cleaned_rows.append({"label": _clip(row.get("label", ""), 18), "segments": segments})
        return {"rows": cleaned_rows or [{"label": "row", "segments": [{"start": 0, "end": 5, "label": "work"}]}]}

    if kind == "boxes":
        nodes = raw.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            nodes = [{"id": f"n{i}", "label": _clip(p, 14)} for i, p in enumerate(points[:4])]
        cleaned_nodes = []
        for idx, node in enumerate(nodes[:5]):
            if isinstance(node, dict):
                cleaned_nodes.append({"id": str(node.get("id") or f"n{idx}"), "label": _clip(node.get("label", f"步骤{idx + 1}"), 16)})
            else:
                cleaned_nodes.append({"id": f"n{idx}", "label": _clip(node, 16)})
        if len(cleaned_nodes) < 2:
            cleaned_nodes.append({"id": "n1", "label": "结论"})
        edges = raw.get("edges")
        cleaned_edges = []
        if isinstance(edges, list):
            for edge in edges[:5]:
                if isinstance(edge, (list, tuple)) and len(edge) >= 2:
                    cleaned_edges.append([str(edge[0]), str(edge[1]), _clip(edge[2] if len(edge) > 2 else "", 10)])
        if not cleaned_edges:
            cleaned_edges = [[cleaned_nodes[i]["id"], cleaned_nodes[i + 1]["id"], ""] for i in range(len(cleaned_nodes) - 1)]
        return {"nodes": cleaned_nodes, "edges": cleaned_edges}

    if kind == "code":
        lines = raw.get("lines")
        if not isinstance(lines, list) or not lines:
            lines = [line for line in code_badge.splitlines() if line.strip()] or [
                "int idx = blockIdx.x * blockDim.x + threadIdx.x;",
                "if (idx < N) { d_out[idx] = d_in[idx]; }",
            ]
        return {"lines": [_clip(line, 96) for line in lines[:10]], "language": _clip(raw.get("language", "CUDA C++"), 12)}

    # compare
    left = raw.get("left") if isinstance(raw.get("left"), dict) else {}
    right = raw.get("right") if isinstance(raw.get("right"), dict) else {}
    left_lines = _clean_list(left.get("lines"), limit=4, chars=90) or [code_badge.splitlines()[0] if code_badge else "朴素实现"]
    right_lines = _clean_list(right.get("lines"), limit=4, chars=90) or ["边界判断 + 全局索引"]
    return {
        "left": {"title": _clip(left.get("title", "反例 / 隐患"), 20), "lines": left_lines},
        "right": {"title": _clip(right.get("title", "规范实现"), 20), "lines": right_lines},
    }


def normalize_plan(plan: Any, slide: Dict[str, Any], topic: str = "", duration: float = 8.0) -> Dict[str, Any]:
    plan = plan if isinstance(plan, dict) else {}
    kind = str(plan.get("kind") or "").strip().lower()
    if kind not in KINDS:
        kind = "boxes"

    figure = _figure_for_kind(kind, plan, slide)
    focus_count = _focusable_count(kind, figure)

    raw_steps = plan.get("steps")
    steps: List[Dict[str, Any]] = []
    if isinstance(raw_steps, list):
        for idx, step in enumerate(raw_steps[:6]):
            if not isinstance(step, dict):
                continue
            heading = _clip(step.get("heading", ""), 32)
            bullets = _clean_list(step.get("bullets"), limit=2, chars=54)
            if not heading and not bullets:
                continue
            steps.append(
                {
                    "heading": heading or f"Step {idx + 1}",
                    "bullets": bullets,
                    "focus": _as_int_list(step.get("focus"), focus_count) or _default_focus(kind, idx, focus_count),
                    "caption": _clip(step.get("caption", ""), 40),
                    "narration": _clip(step.get("narration", ""), 260),
                }
            )

    if not steps:
        points = [str(p) for p in (slide.get("key_points") or []) if str(p).strip()]
        for idx, point in enumerate(points[:4] or [slide.get("title", topic)]):
            steps.append(
                {
                    "heading": _clip(point, 30),
                    "bullets": [],
                    "focus": _default_focus(kind, idx, focus_count),
                    "caption": "",
                    "narration": "",
                }
            )

    has_narration = any(str(step.get("narration") or "").strip() for step in steps)

    narration = str(slide.get("narration_script") or "")
    sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;])", narration) if 10 <= len(s.strip()) <= 70]
    if steps and not any(step.get("bullets") for step in steps) and sentences:
        for idx, step in enumerate(steps):
            if not step.get("bullets"):
                step["bullets"] = [_clip(sentences[idx % len(sentences)], 46)]

    # Specialised concepts have a canonical pedagogical arc; fill missing steps.
    arc = {
        "warp": ["32 线程锁步执行", "分支 A：偶数线程", "分支 B：奇数线程", "重新收敛"],
        "banks": ["无冲突：1:1 访问", "跨步：多线程命中同一 Bank", "Padding 错开 Bank"],
        "coalesce": ["连续访问：合并成 1 次事务", "跨步访问：事务分裂", "总线利用率"],
        "matrix": ["分块载入 Shared Memory", "复用数据完成乘法", "写回结果"],
    }.get(kind)
    if arc and not has_narration:
        for idx, heading in enumerate(arc):
            if len(steps) >= 4:
                break
            if all(step.get("heading") != heading for step in steps):
                steps.append({"heading": heading, "bullets": [], "focus": _default_focus(kind, idx, focus_count), "caption": "", "narration": ""})

    if not has_narration:
        for sentence in sentences:
            if len(steps) >= 4:
                break
            heading = _clip(sentence, 30)
            if heading and all(heading != step.get("heading") for step in steps):
                steps.append({"heading": heading, "bullets": [], "focus": _default_focus(kind, len(steps), focus_count), "caption": "", "narration": ""})

    if kind == "boxes" and len(figure.get("nodes") or []) <= 2 and len(steps) >= 3:
        nodes = [{"id": f"n{i}", "label": _clip(step["heading"], 14)} for i, step in enumerate(steps[:4])]
        figure["nodes"] = nodes
        figure["edges"] = [[nodes[i]["id"], nodes[i + 1]["id"], ""] for i in range(len(nodes) - 1)]

    title_text = _clip(plan.get("title") or slide.get("title") or topic, 42)
    subtitle_text = _clip(plan.get("subtitle") or topic, 42)
    if subtitle_text.lower() == title_text.lower():
        subtitle_text = _clip(f"{topic} · 第 {slide.get('slide_id', 1)} 页", 42)

    return {
        "schema": PLAN_SCHEMA_VERSION,
        "kind": kind,
        "slide_id": slide.get("slide_id", ""),
        "title": title_text,
        "subtitle": subtitle_text,
        "caption": _clip(plan.get("caption") or "", 56),
        "figure": figure,
        "steps": steps,
        "duration": round(max(3.0, float(duration or 3.0)), 3),
    }


def plan_for_slide(slide: Dict[str, Any], topic: str, duration: float) -> Dict[str, Any]:
    visual = slide.get("visual_spec") or {}
    title = str(slide.get("title") or "")
    body = " ".join(
        [
            " ".join(str(p) for p in (slide.get("key_points") or [])),
            str(visual.get("code_badge") or ""),
            str(((visual.get("scene_plan") or {}).get("kind")) or ""),
        ]
    )
    kind = choose_kind(title, body)
    if kind == "grid" and str(slide.get("slide_type")) in ("code_diff", "code_misconception"):
        kind = "compare"

    plan = {
        "kind": kind,
        "title": slide.get("title") or topic,
        "subtitle": topic,
        "caption": "",
        "steps": [
            {"heading": point, "bullets": [], "focus": _default_focus(kind, idx, 8)}
            for idx, point in enumerate([str(p) for p in (slide.get("key_points") or [])][:4])
        ],
        "figure": {},
    }
    plan = normalize_plan(plan, slide, topic=topic, duration=duration)

    canonical_heads = {
        "warp": ["32 个线程锁步执行", "分支 A：偶数线程执行", "分支 B：奇数线程执行", "重新收敛：时间翻倍"],
        "banks": ["无冲突：1:1 访问", "跨步：多线程命中同一 Bank", "Padding 错开 Bank"],
        "coalesce": ["连续访问：合并为一次事务", "跨步访问：事务分裂", "合并后的总线利用率"],
        "matrix": ["分块载入 Shared Memory", "复用数据完成乘法", "写回结果"],
    }.get(kind)
    if canonical_heads:
        for idx, heading in enumerate(canonical_heads):
            if idx < len(plan["steps"]):
                plan["steps"][idx]["heading"] = heading
    return plan


def slide_wants_animation(slide: Dict[str, Any]) -> bool:
    slide_type = str(slide.get("slide_type") or "").lower()
    visual = slide.get("visual_spec") or {}
    plan = visual.get("scene_plan")
    # A summary with a real storyboard should animate too; only fall back to a
    # static card when there is no usable scene plan.
    if slide_type == "summary_best_practice":
        if isinstance(plan, dict) and plan.get("kind") and plan.get("steps"):
            return str(plan.get("kind")).lower() not in ("none", "static")
        return False
    if isinstance(plan, dict) and plan.get("kind"):
        return str(plan.get("kind")).lower() not in ("none", "static")
    return slide_type in ANIMATED_SLIDE_TYPES


def plan_fingerprint(plan: Dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
