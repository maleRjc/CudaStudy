"""
Layer 2: Deep pedagogical deck generation, now driven by DeepSeek.

Contract produced by this layer (one object per section):

{
  "sec_id": "...", "topic": "...", "source": "deepseek",
  "slides": [
    {
      "slide_id": 1,
      "title": "...",
      "slide_type": "title_overview | concept_breakdown | code_diff | manim_physics_demo | ...",
      "key_points": ["...", "...", "..."],
      "narration_script": "180~320 字逐字讲稿",
      "visual_spec": {
        "layout": "...",
        "code_badge": "仅在原文中真实出现的代码行",
        "scene_plan": {kind, title, subtitle, figure, steps:[{heading, bullets, focus}]}
      }
    }
  ]
}

Every slide gets its own ``scene_plan`` so the Manim layer can render a
*different* animation per slide instead of repeating one scene for the chapter.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline.cuda_validator import CudaAccuracyValidator
from pipeline.deepseek_client import DeepSeekClient, DeepSeekError, DeepSeekUnavailable
from pipeline.storyboard import choose_kind, normalize_plan

SLIDE_TYPES = (
    "title_overview",
    "concept_breakdown",
    "code_diff",
    "code_misconception",
    "manim_physics_demo",
    "memory_layout",
    "profiler_timeline",
    "benchmark_chart",
    "metaphor_sketch",
    "math_architecture_resolution",
    "summary_best_practice",
)

SYSTEM_PROMPT = """你是一位世界级的高性能计算教授 + 教学视频分镜导演。
你会严格依据用户提供的 PDF 原文（段落与真实代码）制作 PPT 教学讲稿，并为每一页设计一个可直接渲染的 Manim 分镜计划。
铁律：
1. 只使用输入原文中的事实；原文没有的实测数字、Profiler 截图、加速比一律不得编造。
2. 每页 narration_script 必须是 180~320 字的中文逐字口播讲稿，能直接朗读，不要 Markdown。
3. code_badge 必须逐字来自输入中的代码块；没有代码的页面必须留空字符串。
4. 每页 scene_plan 必须不同：kind 从 grid/bars/timeline/boxes/code/compare 中选择最贴合该页语义的一种；figure 数据必须具体（来自原文的标签/步骤），不要空泛。
5. 只输出合法 JSON 对象，不要任何解释文字。"""


def _clean_text(value: Any, limit: int = 400) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _norm_code(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def _clean_points(values: Any, limit: int = 5, chars: int = 46) -> List[str]:
    points: List[str] = []
    if isinstance(values, (list, tuple)):
        for value in values:
            text = _clean_text(value, chars)
            if text and text not in points:
                points.append(text)
            if len(points) >= limit:
                break
    return points


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


class DeckGenerationError(RuntimeError):
    """Raised when a deck cannot be generated (missing key / API failure)."""


class DeckOutputError(DeckGenerationError):
    """Raised when the model output violates the deck contract (retryable)."""


class DeepPedagogicalDeckGenerator:
    """Builds a section deck with DeepSeek. No offline content fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.api_key()
        self.output_dir = config.OUTPUT_DIR / "deep_decks"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.last_mode = "deepseek"
        self.last_error = ""

    # ------------------------------------------------------------------
    def generate_deck_from_section(
        self,
        section_data: Dict[str, Any],
        force: bool = False,
        max_slides: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a deck with DeepSeek.

        There is deliberately **no offline fallback**: without a working API key
        the pipeline stops with DeckGenerationError instead of producing a
        template/grounded lecture that looks like real content.
        """
        sec_id = section_data["sec_id"]
        deck_file = self.output_dir / f"{sec_id}.json"
        fingerprint = self._fingerprint(section_data)

        if not force and deck_file.exists():
            try:
                cached = json.loads(deck_file.read_text(encoding="utf-8"))
                deck_cached = cached.get("deck", {})
                if (
                    cached.get("fingerprint") == fingerprint
                    and deck_cached.get("slides")
                    and deck_cached.get("source") == "deepseek"
                ):
                    print(f"[~] Deck cache hit: {sec_id} ({len(deck_cached['slides'])} slides)")
                    self.last_mode = "deepseek"
                    return deck_cached
            except (OSError, json.JSONDecodeError):
                pass

        if not config.has_api_key():
            raise DeckGenerationError(
                "未配置 DEEPSEEK_API_KEY：本版本已移除无 Key 兜底模式。"
                "请在项目根目录 .env 中填写 DEEPSEEK_API_KEY，或在 GUI 的 Key 输入框中填入后重试。"
            )

        feedback = ""
        deck = None
        compact = True
        for attempt in (1, 2):
            try:
                deck = self._llm_deck(
                    section_data,
                    max_slides=max_slides,
                    feedback=feedback,
                    compact=compact,
                )
            except DeepSeekError as exc:
                if attempt == 1 and exc.kind in ("invalid_json", "truncated", "empty"):
                    feedback = "上一次输出在 JSON 中途被截断。请压缩输出：只写 4 页、每页 3 个 steps、每步旁白 40~70 字。"
                    compact = True
                    print(f"[!] Deck JSON truncated, retrying compact: {str(exc)[:160]}")
                    continue
                self.last_error = f"{exc.kind}: {exc}"
                raise DeckGenerationError(
                    f"DeepSeek 生成失败（{exc.kind}）：{exc}\n"
                    "请检查 Key、网络、余额与 DEEPSEEK_BASE_URL 后重试（不会退回离线模板）。"
                ) from exc

            salvaged = bool(deck.pop("__salvaged__", False))
            if salvaged and attempt == 1:
                feedback = "上一次输出在 JSON 中途被截断。请压缩输出：只写 4 页、每页 3 个 steps、每步旁白 40~70 字。"
                compact = True
                print("[!] Deck output was salvaged from a truncated JSON; retrying compact.")
                continue

            try:
                deck = self._validate_and_repair(deck, section_data, max_slides=max_slides)
                break
            except DeckOutputError as exc:
                if attempt == 2:
                    raise
                feedback = str(exc)[:800]
                compact = True
                print(f"[!] Deck rejected, retrying compact: {feedback[:160]}")

        self.last_mode = "deepseek"
        print(f"[+] DeepSeek deck OK: {sec_id} ({len(deck.get('slides', []))} slides)")
        deck["source"] = "deepseek"
        deck = CudaAccuracyValidator.audit_slide_deck(deck)

        try:
            deck_file.write_text(
                json.dumps({"fingerprint": fingerprint, "deck": deck}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"[!] Could not cache deck: {exc}")

        print(f"[+] Deck ready: {len(deck['slides'])} slides for '{deck.get('topic')}' (source=deepseek)")
        return deck

    # ------------------------------------------------------------------
    def _fingerprint(self, section_data: Dict[str, Any]) -> str:
        payload = "|".join(
            [
                config.SCHEMA_VERSION,
                section_data.get("sec_id", ""),
                str(len(section_data.get("full_text", ""))),
                _norm_code(section_data.get("full_text", ""))[:6000],
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------
    def _llm_deck(
        self,
        section_data: Dict[str, Any],
        max_slides: Optional[int] = None,
        feedback: str = "",
        compact: bool = False,
    ) -> Dict[str, Any]:
        client = DeepSeekClient(api_key=self.api_key)
        if not client.available:
            raise DeepSeekUnavailable("no api key")

        code_blocks = section_data.get("code_snippets") or []
        code_text = "\n\n".join(f"```cpp\n{block[:1200]}\n```" for block in code_blocks[:4]) or "（本节未提取到代码）"
        paragraphs = section_data.get("paragraphs") or []
        if not paragraphs:
            paragraphs = [p for p in re.split(r"\n{2,}", section_data.get("full_text", "")) if len(p.strip()) > 40][:12]
        corpus = "\n".join(f"[{i + 1}] {p[:520]}" for i, p in enumerate(paragraphs[:18]))

        slide_cap = max_slides or config.MAX_SLIDES_PER_SECTION
        slide_max = min(4, slide_cap)
        step_min, step_max = (3, 3) if compact else (3, 4)
        narr_min, narr_max = (40, 70) if compact else (45, 90)
        prompt = f"""请为下面这一节技术文档制作教学 PPT 讲稿。

【章节】{section_data.get('title')}
【页码】P{section_data.get('start_page')}-P{section_data.get('end_page')}（共 {section_data.get('page_count')} 页）

【原文段落（按页顺序，已清洗）】
{corpus}

【原文中真实提取到的代码块】
{code_text}

【输出要求】
- slides 数量 4~{slide_max}，按“全景 → 核心概念 → 代码/机制 → 易错点 → 架构推演 → 总结”的教学节奏组织；如果原文内容不足以支撑某一类，就跳过而不是编造。
- 标题必须是中文概括（≤ 24 字），不要把英文原文片段直接当标题。
- 每页 key_points 3~5 条，每条 ≤ 40 字，必须是陈述句。
- 【禁止重复】不同 slide 不得复述同一组事实、同一段代码流程或同一句结论；相邻 step 必须推进新信息，禁止同义改写凑字数；总结页只做 3~5 条精炼提炼，不得整段复述前文。若原文有多个高度相似的示例，合并成一页对比讲清，不要逐页重复。
- 【讲清概念】每页按“是什么 → 为什么/怎么发生 → 原文例子 → 边界或性能影响”展开；至少包含一个来自原文的具体事实、代码行或数字，禁止空泛套话。动画的 steps 要按机制推进（例如 Warp 先锁步、再分支、再收敛），而不是只换标题。
- 每页的朗读内容由各 step 的 narration 顺序拼接而成；页面级 narration_script 可填同样的拼接结果或留空。
- 每页 visual_spec.scene_plan 必须是不同分镜，steps {step_min}~{step_max} 个：
  heading 是中文概念句（≤ 18 字），bullets 0~2 条（解释因果），focus 是整数数组（指向 figure 中要高亮的元素下标）。
  **每个 step 必须包含 narration 字段（{narr_min}~{narr_max} 字）**：只讲这一步对应的内容，按顺序拼接后应基本等于整页 narration_script。
  当 kind=code 时，focus 必须是代码行下标（0 表示 figure.lines 的第一行），并且该 step 的 narration 必须只讲这一行/这几行代码，不得提前讲后面的行。
  每个 step 的 heading/bullets/narration 顺序必须一致。
  focus 必须随步骤推进：grid 分块高亮（不要把全部单元塞给每一步），boxes 按数据流逐节点，compare 左右切换，timeline 逐行。
- 优先使用概念专用图形（这决定动画是否“讲清楚”）：
  * warp：Warp / SIMT / 分支分化 / 线程束
  * banks：Shared Memory / Bank 冲突 / Padding
  * coalesce：合并访存 / 跨步 / 总线事务
  * matrix：分块矩阵 / GEMM / tile
  * timeline：多流 / 异步 / 重叠
  * code：逐行代码讲解（仅当原文确实提供了代码时使用；没有代码不要用）
  * grid：线程层级 / 全局索引
  * compare：反例 vs 规范
  * bars：有真实数字的性能对比
  * boxes：流程 / 架构数据流
- figure 结构按 kind 提供：
    grid:    {{"rows": int, "cols": int, "labels": [str]}}
    warp:    {{"threads": 32}}
    banks:   {{"stride": int}}
    coalesce:{{"threads": 8}}
    matrix:  {{"size": int, "tile": int}}
    bars:    {{"items": [{{"label": str, "value": number, "unit": str}}]}}  ← 只允许原文有明确数字时使用
    timeline:{{"rows": [{{"label": str, "segments": [{{"start": number, "end": number, "label": str}}]}}]}}
    boxes:   {{"nodes": [{{"id": str, "label": str}}], "edges": [[id, id, label]]}}
    code:    {{"lines": [str], "language": "CUDA C++"}}
    compare: {{"left": {{"title": str, "lines": [str]}}, "right": {{"title": str, "lines": [str]}}}}

【输出 JSON 结构】
{{
  "sec_id": "{section_data['sec_id']}",
  "topic": "{section_data.get('title')}",
  "slides": [
    {{
      "slide_id": 1,
      "title": "本页标题（≤ 24 字）",
      "slide_type": "title_overview | concept_breakdown | code_diff | manim_physics_demo | memory_layout | profiler_timeline | benchmark_chart | metaphor_sketch | math_architecture_resolution | summary_best_practice",
      "key_points": ["...", "...", "..."],
      "narration_script": "180~320 字逐字讲稿",
      "visual_spec": {{
        "layout": "collision_animation",
        "code_badge": "",
        "scene_plan": {{
          "kind": "boxes",
          "title": "本页标题",
          "subtitle": "{section_data.get('title')}",
          "figure": {{"nodes": [{{"id": "a", "label": "CPU"}}], "edges": []}},
          "steps": [{{"heading": "...", "bullets": ["..."], "focus": [0], "narration": "本步骤专属旁白 {narr_min}~{narr_max} 字"}}]
        }}
      }}
    }}
  ]
}}"""

        if feedback:
            prompt += (
                "\n\n【上一次输出未通过校验，必须修正后重新输出】\n"
                f"{feedback}\n"
                "请重写整份 JSON，删除所有重复的句子/步骤/结论，并确保每页只讲一个新概念。"
            )

        return client.chat_json(SYSTEM_PROMPT, prompt, temperature=0.35, max_tokens=config.DEEPSEEK_MAX_TOKENS)

    # ------------------------------------------------------------------
    # Validation / repair
    # ------------------------------------------------------------------
    @staticmethod
    def _repair_code_focus(plan: Dict[str, Any]) -> None:
        """Point each code step at the line its narration actually mentions."""
        lines = (plan.get("figure") or {}).get("lines") or []
        if not lines:
            return

        def line_score(index: int, text: str) -> int:
            identifiers = set(re.findall(r"[A-Za-z_]\w{2,}", lines[index]))
            return sum(1 for identifier in identifiers if identifier in text)

        for step in plan.get("steps") or []:
            text = " ".join(
                [str(step.get("heading", ""))]
                + [str(b) for b in (step.get("bullets") or [])]
                + [str(step.get("narration", ""))]
            )
            current = [i for i in (step.get("focus") or []) if 0 <= i < len(lines)]
            current_score = max((line_score(i, text) for i in current), default=0)
            best_index, best_score = -1, 0
            for index in range(len(lines)):
                score = line_score(index, text)
                if score > best_score:
                    best_index, best_score = index, score
            if best_index >= 0 and best_score > current_score:
                step["focus"] = [best_index]

    @staticmethod
    def _check_repetition(slides: List[Dict[str, Any]]) -> None:
        """Remove exact duplicate sentences, reject remaining repetition."""
        seen = set()
        removed = 0
        for slide in slides:
            plan = (slide.get("visual_spec") or {}).get("scene_plan") or {}
            step_texts = []
            for step in plan.get("steps") or []:
                original = str(step.get("narration") or "").strip()
                kept = []
                for sentence in re.split(r"(?<=[。！？；;])", original):
                    normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", sentence).lower()
                    if len(normalized) >= 14:
                        if normalized in seen:
                            removed += 1
                            continue
                        seen.add(normalized)
                    kept.append(sentence)
                shortened = "".join(kept).strip()
                if original and len(shortened) >= 20:
                    step["narration"] = shortened
                step_texts.append(str(step.get("narration") or "").strip())
            if step_texts:
                slide["narration_script"] = " ".join(step_texts)
        if removed:
            print(f"[!] Removed {removed} duplicate sentence(s) from narration.")

        entries = []
        for slide in slides:
            plan = (slide.get("visual_spec") or {}).get("scene_plan") or {}
            for step in plan.get("steps") or []:
                for sentence in re.split(r"(?<=[。！？；;])", str(step.get("narration") or "")):
                    normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", sentence).lower()
                    if len(normalized) >= 14:
                        entries.append((normalized, sentence.strip(), slide.get("title", ""), step.get("heading", "")))

        exact = []
        for index, (normalized, sentence, title, heading) in enumerate(entries):
            for other, _, other_title, _ in entries[:index]:
                if normalized == other:
                    exact.append(f"「{sentence[:24]}」出现在 {title} / {heading}")
                    break
        if exact:
            raise DeckOutputError(
                "检测到跨页/跨步骤的完全重复句子：\n- "
                + "\n- ".join(dict.fromkeys(exact))
                + "\n请重写讲稿：每页只讲一个新概念，总结页只做精炼，不得复述前文。"
            )

        # Reusing the same code block / key points across separate slides is the
        # main source of "same workflow explained again" duplicates.
        code_sets = []
        point_sets = []
        for slide in slides:
            visual = slide.get("visual_spec") or {}
            plan = visual.get("scene_plan") or {}
            lines = (plan.get("figure") or {}).get("lines") or [
                line for line in str(visual.get("code_badge") or "").splitlines() if line.strip()
            ]
            normalized_lines = {re.sub(r"\s+", "", str(line)) for line in lines if str(line).strip()}
            normalized_points = {
                re.sub(r"[^\w\u4e00-\u9fff]", "", str(point)).lower()
                for point in (slide.get("key_points") or [])
                if str(point).strip()
            }
            code_sets.append((slide.get("slide_id"), slide.get("title", ""), normalized_lines))
            point_sets.append((slide.get("slide_id"), slide.get("title", ""), normalized_points))

        reused = []
        for i in range(len(code_sets)):
            for j in range(i + 1, len(code_sets)):
                left, right = code_sets[i][2], code_sets[j][2]
                if len(left) >= 3 and len(right) >= 3:
                    union = left | right
                    overlap = left & right
                    if union and len(overlap) >= 3 and len(overlap) / len(union) >= 0.6:
                        reused.append(
                            f"第 {code_sets[i][0]} 页「{code_sets[i][1]}」与第 {code_sets[j][0]} 页「{code_sets[j][1]}」"
                            f"复用了 {len(overlap)} 行相同代码"
                        )
        if reused:
            raise DeckOutputError(
                "检测到跨页复用同一段代码/流程：\n- "
                + "\n- ".join(dict.fromkeys(reused))
                + "\n请把不同页改成不同机制或不同阶段的讲解，不要重复同一段代码流程。"
            )

        near = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                left, right = entries[i][0], entries[j][0]
                if abs(len(left) - len(right)) > max(len(left), len(right)) * 0.25:
                    continue
                ratio = difflib.SequenceMatcher(None, left, right).ratio()
                if ratio >= 0.90:
                    near.append(
                        f"「{entries[i][1][:22]}」≈「{entries[j][1][:22]}」"
                        f"（{entries[i][2]} / {entries[j][2]}）"
                    )
        if len(near) >= 2:
            raise DeckOutputError(
                "检测到多处近重复讲解：\n- "
                + "\n- ".join(dict.fromkeys(near[:4]))
                + "\n请合并相似步骤、删除同义改写，确保每个 step 都推进新信息。"
            )

    @staticmethod
    def _improve_focus(plan: Dict[str, Any]) -> None:
        """Keep highlight moving when the model gives every step the same target."""
        steps = plan.get("steps") or []
        if len(steps) < 2:
            return
        kind = plan.get("kind")
        figure = plan.get("figure") or {}
        if kind == "grid":
            count = int(figure.get("rows", 4)) * int(figure.get("cols", 8))
        elif kind == "boxes":
            count = len(figure.get("nodes") or [])
        elif kind == "timeline":
            count = len(figure.get("rows") or [])
        elif kind == "compare":
            count = 2
        else:
            return
        if count < 2:
            return

        focuses = [tuple(sorted(set(step.get("focus") or []))) for step in steps]
        if kind == "grid":
            too_broad = all(len(focus) >= max(2, count * 0.6) for focus in focuses)
            if len(set(focuses)) < len(focuses) or too_broad:
                chunk = max(1, (count + len(steps) - 1) // len(steps))
                for index, step in enumerate(steps):
                    step["focus"] = list(range(index * chunk, min((index + 1) * chunk, count)))
                return
        if len(set(focuses)) < len(focuses):
            for index, step in enumerate(steps):
                step["focus"] = [index % count]

    def _validate_and_repair(
        self,
        deck: Dict[str, Any],
        section_data: Dict[str, Any],
        max_slides: Optional[int] = None,
    ) -> Dict[str, Any]:
        topic = _clean_text(deck.get("topic") or section_data.get("title") or "CUDA 专题", 80)
        raw_slides = deck.get("slides") if isinstance(deck.get("slides"), list) else []
        cap = max_slides or config.MAX_SLIDES_PER_SECTION

        source_code = _norm_code("\n".join(section_data.get("code_snippets") or []))

        slides: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_slides[:cap], start=1):
            if not isinstance(raw, dict):
                continue
            slide_type = str(raw.get("slide_type") or "").strip()
            if slide_type not in SLIDE_TYPES:
                slide_type = "concept_breakdown"

            title = _clean_text(raw.get("title"), 44)
            if not title:
                raise DeckOutputError(f"DeepSeek 输出不完整：第 {idx} 页缺少标题。")

            points = _clean_points(raw.get("key_points"), limit=5, chars=46)
            if len(points) < 2:
                raise DeckOutputError(
                    f"DeepSeek 输出不完整：第 {idx} 页 key_points 少于 2 条（{title}）。"
                )

            # Page-level narration is optional; the spoken script is assembled
            # from step narrations below.
            narration = _clean_text(raw.get("narration_script"), 700)

            visual = raw.get("visual_spec") if isinstance(raw.get("visual_spec"), dict) else {}
            code_badge = str(visual.get("code_badge") or "").strip()
            if code_badge and source_code and _norm_code(code_badge) not in source_code:
                # Never show hallucinated code.
                print(f"[!] Dropped code_badge not found in source (slide {idx})")
                code_badge = ""
            if code_badge:
                code_badge = "\n".join(line for line in code_badge.splitlines() if line.strip())[:600]

            slide = {
                "slide_id": idx,
                "title": title,
                "slide_type": slide_type,
                "key_points": points,
                "narration_script": narration,
                "visual_spec": {
                    "layout": _clean_text(visual.get("layout") or "header_and_bullets", 40),
                    "code_badge": code_badge,
                },
            }

            raw_plan = visual.get("scene_plan") if isinstance(visual.get("scene_plan"), dict) else {}
            if slide_type == "title_overview":
                # Title pages are always an agenda/roadmap figure.
                raw_plan = {**raw_plan, "kind": "boxes"}
            plan = normalize_plan(raw_plan, slide, topic=topic, duration=8.0)

            expected_kind = choose_kind(slide.get("title", ""), " ".join(points))
            if (
                slide_type not in ("title_overview", "summary_best_practice")
                and expected_kind in ("warp", "banks", "coalesce", "matrix")
                and plan["kind"] != expected_kind
            ):
                # The model may default to a generic figure; upgrade it to the
                # concept-specific visual when the slide is clearly about one.
                plan = normalize_plan({**plan, "kind": expected_kind}, slide, topic=topic, duration=8.0)

            # A code walkthrough is only valid when the PDF actually has code.
            raw_code_lines = (raw_plan.get("figure") or {}).get("lines") if isinstance(raw_plan, dict) else None
            if plan["kind"] == "code" and not (section_data.get("code_snippets") or code_badge or raw_code_lines):
                fallback_kind = "grid" if expected_kind in ("grid", "timeline", "compare") else "boxes"
                print(f"[!] No real code in source; downgrading slide {idx} from code to {fallback_kind}")
                plan = normalize_plan({**plan, "kind": fallback_kind, "figure": {}}, slide, topic=topic, duration=8.0)

            step_texts: List[str] = []
            for step in plan.get("steps") or []:
                text = _clean_text(step.get("narration"), 300)
                if len(text) < 20:
                    raise DeckOutputError(
                        f"DeepSeek 输出不完整：第 {idx} 页步骤「{step.get('heading', '')}」缺少 narration。"
                        "每个 step 必须提供本步骤旁白，用于和代码高亮精确同步。"
                    )
                step["narration"] = text
                step_texts.append(text)

            if plan["kind"] == "code":
                self._repair_code_focus(plan)
            self._improve_focus(plan)

            # The spoken script is exactly the concatenation of step narrations.
            slide["narration_script"] = " ".join(step_texts)
            slide["visual_spec"]["scene_plan"] = plan
            slides.append(slide)

        if len(slides) < 3:
            raise DeckOutputError(f"deck for {section_data.get('sec_id')} produced too few slides ({len(slides)})")

        self._check_repetition(slides)

        deck = {
            "sec_id": section_data["sec_id"],
            "chunk_id": section_data["sec_id"],
            "concept_id": section_data["sec_id"],
            "topic": topic,
            "page_range": f"P{section_data.get('start_page')}-P{section_data.get('end_page')}",
            "page_count": section_data.get("page_count"),
            "slides": slides,
        }
        return deck

