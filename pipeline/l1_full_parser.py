"""
Layer 1 (Full-Book Dynamic Parser).

Extracts the PDF outline (TOC), section hierarchy and exact page ranges, then
pulls verbatim text, paragraphs and *real* code blocks out of each section.

The code extractor is line-oriented and brace-aware on purpose: PDF text has no
blank lines between code lines, so the previous "split on \\n\\n" heuristic
returned zero snippets on the CUDA guide.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pypdf

# pypdf emits noisy fontTools warnings on CUDA-guide Type1 fonts; they do not
# affect extraction for this document.
logging.getLogger("pypdf").setLevel(logging.ERROR)

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

CODE_KEYWORDS = (
    "__global__",
    "__device__",
    "__shared__",
    "__host__",
    "__syncthreads",
    "cudaMalloc",
    "cudaMemcpy",
    "cudaFree",
    "cudaMemcpyAsync",
    "threadIdx",
    "blockIdx",
    "blockDim",
    "gridDim",
    "warpSize",
    "atomicAdd",
    "cudaStream",
    "cudaEvent",
    "dim3",
    "<<<",
    ">>>",
)

CALL_RE = re.compile(r"\b[a-zA-Z_]\w*\s*\([^;]*\)\s*;")
INCLUDE_RE = re.compile(r"^\s*#\s*(include|define|pragma)\b")
DECL_RE = re.compile(r"^\s*(int|float|double|unsigned|char|void|dim3|size_t|bool|auto|const)\b")
ASSIGN_RE = re.compile(r"^\s*[\w\[\]\.\->\s]+\s*=\s*[^=].*;\s*$")

HEADER_NOISE = re.compile(
    r"^(CUDA C\+\+ Programming Guide|PG-\d+-\d+_v[\d.]+\s*\|\s*\d+|Programming Guide\s*\|\s*\d+|\d{1,4})\s*$",
    re.IGNORECASE,
)
TOC_LINE = re.compile(r"^(chapter|section|figure|table|listing|appendix)\s+\d", re.IGNORECASE)
DOTTED_LEADER = re.compile(r"\.{4,}\s*\d+\s*$")


def _is_toc_fragment(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if TOC_LINE.match(stripped) and len(stripped) < 200:
        return True
    if DOTTED_LEADER.search(stripped):
        return True
    digits_and_dots = sum(ch.isdigit() or ch == "." for ch in stripped)
    return len(stripped) > 20 and digits_and_dots / len(stripped) > 0.22


def _is_prose(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith((";", "{", "}", "#")):
        return False
    words = len(re.findall(r"[A-Za-z]{2,}", stripped))
    if stripped.endswith((".", "。", ":", "：")) and "(" not in stripped:
        return True
    return words >= 10 and not CALL_RE.search(stripped) and "=" not in stripped


def _is_strong_code(line: str) -> bool:
    """Line shapes that are unambiguously code, not prose mentioning a keyword."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith((";", "{", "}")) and not stripped.endswith("."):
        return True
    if INCLUDE_RE.match(stripped):
        return True
    if "<<<" in stripped or stripped.startswith(("}", "};", ")", ");")):
        return True
    if ASSIGN_RE.match(stripped) or CALL_RE.search(stripped):
        return True
    if DECL_RE.match(stripped) and ("(" in stripped or "=" in stripped or ";" in stripped):
        return True
    if re.match(r"^\s*(for|while|if|else|switch|return|template|struct|class)\b", stripped):
        return True
    return False


def _looks_like_code(line: str) -> bool:
    stripped = line.strip()
    if not stripped or _is_prose(stripped):
        return False
    if _is_strong_code(stripped):
        return True
    if any(keyword in stripped for keyword in CODE_KEYWORDS):
        return True
    punctuation = sum(stripped.count(ch) for ch in "{}();=<>[]")
    return len(stripped) > 12 and punctuation / len(stripped) > 0.18


class FullBookPdfParser:
    """Parses any technical PDF document based on its internal Outline / TOC."""

    def __init__(self, pdf_path: Optional[Path] = None):
        self.pdf_path = Path(pdf_path or config.DEFAULT_PDF_PATH)
        self.output_dir = config.OUTPUT_DIR / "curriculum"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Curriculum
    # ------------------------------------------------------------------
    def extract_full_curriculum(self, min_level: int = 0, max_level: int = 1) -> List[Dict[str, Any]]:
        if not self.pdf_path.exists():
            print(f"[!] PDF not found: {self.pdf_path}")
            return []

        cache_file = self.output_dir / f"{self.pdf_path.stem}_curriculum_L{min_level}_{max_level}.json"
        stat = self.pdf_path.stat()
        cache_meta = {
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "schema": config.SCHEMA_VERSION,
            "levels": [min_level, max_level],
        }
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and cached.get("meta") == cache_meta and cached.get("sections"):
                    return cached["sections"]
            except (OSError, json.JSONDecodeError):
                pass

        print(f"[*] Parsing complete Table of Contents for {self.pdf_path.name}...")
        reader = pypdf.PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)

        raw_items: List[Dict[str, Any]] = []

        def recurse_outline(outline, level=0):
            for item in outline:
                if isinstance(item, list):
                    recurse_outline(item, level + 1)
                else:
                    try:
                        page_number = reader.get_destination_page_number(item) + 1
                        raw_items.append({"level": level, "title": item.title.strip(), "page": page_number})
                    except Exception:
                        continue

        if reader.outline:
            recurse_outline(reader.outline, level=0)

        if not raw_items:
            print("[Warning] No internal PDF outline found. Generating synthetic chapter slices...")
            chunk_size = 15
            for idx, p_start in enumerate(range(1, total_pages + 1, chunk_size), 1):
                raw_items.append(
                    {
                        "level": 0,
                        "title": f"Chapter {idx}: Pages {p_start}-{min(p_start + chunk_size - 1, total_pages)}",
                        "page": p_start,
                    }
                )

        filtered = [item for item in raw_items if min_level <= item["level"] <= max_level]
        sections: List[Dict[str, Any]] = []

        for idx, item in enumerate(filtered):
            start_page = item["page"]
            if idx + 1 < len(filtered):
                next_page = max(start_page, filtered[idx + 1]["page"])
                end_page = max(start_page, next_page - 1)
            else:
                end_page = min(start_page + 15, total_pages)

            raw_title = item["title"]
            clean_slug = re.sub(r"[^\w\s-]", "", raw_title).strip().lower()
            clean_slug = re.sub(r"[-\s]+", "_", clean_slug)[:50].strip("_") or f"part_{idx + 1}"

            sections.append(
                {
                    "sec_id": f"sec_{idx + 1:03d}_{clean_slug}",
                    "index": idx + 1,
                    "level": item["level"],
                    "title": raw_title,
                    "start_page": start_page,
                    "end_page": min(end_page, total_pages),
                    "page_count": min(end_page, total_pages) - start_page + 1,
                }
            )

        try:
            cache_file.write_text(
                json.dumps({"meta": cache_meta, "sections": sections}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

        print(f"[+] Successfully extracted {len(sections)} curriculum sections from PDF.")
        return sections

    # ------------------------------------------------------------------
    # Section content
    # ------------------------------------------------------------------
    def extract_section_text_and_code(self, section: Dict[str, Any]) -> Dict[str, Any]:
        start_page = section["start_page"] - 1
        end_page = section["end_page"]

        reader = pypdf.PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)
        start_page = max(0, min(start_page, total_pages - 1))
        end_page = max(start_page + 1, min(end_page, total_pages))

        pages_text: List[str] = []
        for page_idx in range(start_page, end_page):
            raw_text = reader.pages[page_idx].extract_text() or ""
            text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", raw_text)
            pages_text.append(f"--- Page {page_idx + 1} ---\n{text}")

        full_text = "\n".join(pages_text)
        lines = full_text.splitlines()
        cleaned_lines = [line for line in lines if not HEADER_NOISE.match(line.strip())]
        body_text = "\n".join(cleaned_lines)

        code_blocks = self._extract_code_blocks(body_text, max_blocks=8, max_lines=22)
        paragraphs = self._extract_paragraphs(body_text, max_items=40)

        return {
            "sec_id": section["sec_id"],
            "title": section["title"],
            "start_page": section["start_page"],
            "end_page": section["end_page"],
            "page_count": section["page_count"],
            "full_text": body_text,
            "text_length": len(body_text),
            "code_snippets": code_blocks,
            "code_snippet": code_blocks[0] if code_blocks else "",
            "paragraphs": paragraphs,
        }

    # ------------------------------------------------------------------
    def _extract_code_blocks(self, text: str, max_blocks: int = 8, max_lines: int = 22) -> List[str]:
        lines = text.splitlines()
        blocks: List[List[str]] = []
        current: List[str] = []
        brace_depth = 0

        def flush():
            nonlocal current, brace_depth
            if len(current) >= 2:
                blocks.append(current[:max_lines])
            current = []
            brace_depth = 0

        for raw in lines:
            line = raw.rstrip()
            stripped = line.strip()
            if stripped.startswith("--- Page"):
                flush()
                continue
            if not stripped:
                continue

            strong = _is_strong_code(line)
            code_like = strong or (brace_depth > 0) or _looks_like_code(line)

            if not current:
                if not strong:
                    continue
                current.append(line)
                brace_depth = max(0, brace_depth + line.count("{") - line.count("}"))
                continue

            if _is_prose(stripped) and brace_depth == 0:
                flush()
                continue

            if not code_like:
                flush()
                continue

            current.append(line)
            brace_depth = max(0, brace_depth + line.count("{") - line.count("}"))
            if brace_depth == 0 and strong and len(current) >= 2 and stripped.endswith("}"):
                flush()

        flush()

        cleaned: List[str] = []
        seen_heads = set()
        scored = []
        for block in blocks:
            code_lines = [line for line in block if line.strip()]
            if len(code_lines) < 2:
                continue
            # Drop leading continuation fragments (", float* out", "{", ...).
            while code_lines and re.match(r"^\s*[,;{}\])]", code_lines[0]):
                code_lines.pop(0)
            if len(code_lines) < 2:
                continue
            strong_count = sum(1 for line in code_lines if _is_strong_code(line))
            prose_count = sum(1 for line in code_lines if _is_prose(line))
            if strong_count < 2 or prose_count > max(1, len(code_lines) // 3):
                continue

            code = "\n".join(code_lines).strip()
            code = re.sub(r"\n{2,}", "\n", code)
            code = re.sub(r"(?<=[A-Za-z])\ufffd+(?=[A-Za-z])", "'", code)
            code = code.replace("\ufffd", "")
            if len(code) < 20:
                continue
            if not any(keyword in code for keyword in CODE_KEYWORDS) and code.count(";") < 2:
                continue
            head = code[:60]
            if head in seen_heads:
                continue
            seen_heads.add(head)
            keyword_hits = sum(1 for keyword in CODE_KEYWORDS if keyword in code)
            scored.append((keyword_hits * 100 + strong_count * 10 + len(code_lines), code))

        scored.sort(key=lambda item: item[0], reverse=True)
        for _, code in scored:
            cleaned.append(code)
            if len(cleaned) >= max_blocks:
                break
        return cleaned

    def _extract_paragraphs(self, text: str, max_items: int = 40) -> List[str]:
        """PDFs usually lack blank lines; rebuild paragraphs from sentence flow."""
        sentences: List[str] = []
        buffer = []
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("--- Page"):
                if buffer:
                    sentences.append(" ".join(buffer))
                    buffer = []
                continue
            if _is_toc_fragment(stripped) or HEADER_NOISE.match(stripped) or re.match(
                r"^(CUDA Programming Guide, Release|Figure \d+:|Table \d+:|Listing \d+:|Copyright\b|DOI\b)",
                stripped,
            ):
                if buffer:
                    sentences.append(" ".join(buffer))
                    buffer = []
                continue
            if _looks_like_code(stripped):
                if buffer:
                    sentences.append(" ".join(buffer))
                    buffer = []
                continue
            buffer.append(stripped)
            if stripped.endswith((".", "。", "!", "?", ":", "；", ";")):
                sentences.append(" ".join(buffer))
                buffer = []
        if buffer:
            sentences.append(" ".join(buffer))

        paragraphs = []
        for sentence in sentences:
            sentence = re.sub(r"\s+", " ", sentence).strip()
            sentence = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", sentence).strip()
            if len(sentence) < 40:
                continue
            if _is_toc_fragment(sentence):
                continue
            paragraphs.append(sentence)
            if len(paragraphs) >= max_items:
                break
        return paragraphs


if __name__ == "__main__":
    parser = FullBookPdfParser()
    curriculum = parser.extract_full_curriculum(min_level=1, max_level=1)
    print(f"Sections: {len(curriculum)}")
    for section in curriculum[:5]:
        print(f"[{section['index']}] {section['title']} (P{section['start_page']}-P{section['end_page']})")
    if curriculum:
        sample = parser.extract_section_text_and_code(curriculum[1])
        print(f"\n{sample['title']}: {sample['text_length']} chars, {len(sample['code_snippets'])} code blocks")
        if sample["code_snippets"]:
            print(sample["code_snippets"][0][:400])
