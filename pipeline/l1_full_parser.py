"""
Layer 1 (Full-Book Dynamic Parser):
Extracts the complete Table of Contents (TOC), section hierarchy, page ranges,
and verbatim text/code snippets from ANY technical PDF document.
No hardcoded chapter limits - dynamically builds a full course curriculum tree.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pypdf

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


class FullBookPdfParser:
    """Parses any technical PDF document based on its internal Outline / TOC."""

    def __init__(self, pdf_path: Optional[Path] = None):
        self.pdf_path = Path(pdf_path or config.DEFAULT_PDF_PATH)
        self.output_dir = config.OUTPUT_DIR / "curriculum"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_full_curriculum(self, min_level: int = 0, max_level: int = 1) -> List[Dict[str, Any]]:
        """
        Parses all outline entries from the PDF.
        Calculates exact start and end page for every section.
        Extracts verbatim text and creates clean curriculum nodes.
        """
        if not self.pdf_path.exists():
            print(f"[!] PDF not found: {self.pdf_path}")
            return []

        curriculum_cache_file = self.output_dir / f"{self.pdf_path.stem}_curriculum.json"
        if curriculum_cache_file.exists():
            try:
                with open(curriculum_cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached and len(cached) > 0:
                        return cached
            except Exception:
                pass

        print(f"[*] Parsing complete Table of Contents for {self.pdf_path.name}...")
        reader = pypdf.PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)

        # 1. Flatten outline with level info
        raw_items = []

        def recurse_outline(outline, level=0):
            for item in outline:
                if isinstance(item, list):
                    recurse_outline(item, level + 1)
                else:
                    try:
                        p_num = reader.get_destination_page_number(item) + 1
                        raw_items.append({
                            "level": level,
                            "title": item.title.strip(),
                            "page": p_num
                        })
                    except Exception:
                        pass

        if reader.outline:
            recurse_outline(reader.outline, level=0)

        if not raw_items:
            print("[Warning] No internal PDF outline found. Generating synthetic chapter slices...")
            # Fallback for PDFs without bookmarks: split by 15-page chunks
            chunk_size = 15
            for idx, p_start in enumerate(range(1, total_pages + 1, chunk_size), 1):
                p_end = min(p_start + chunk_size - 1, total_pages)
                raw_items.append({
                    "level": 0,
                    "title": f"Chapter {idx}: Pages {p_start}-{p_end}",
                    "page": p_start
                })

        # 2. Filter by level and compute section page ranges
        filtered = [item for item in raw_items if min_level <= item["level"] <= max_level]
        sections = []

        for i, item in enumerate(filtered):
            p_start = item["page"]
            # Section ends where the next section starts, or at end of book
            if i + 1 < len(filtered):
                next_page = filtered[i + 1]["page"]
                p_end = max(p_start, next_page - 1)
            else:
                p_end = min(p_start + 15, total_pages)

            # Clean slug id
            raw_title = item["title"]
            clean_slug = re.sub(r"[^\w\s-]", "", raw_title).strip().lower()
            clean_slug = re.sub(r"[-\s]+", "_", clean_slug)[:50]
            sec_id = f"sec_{i+1:03d}_{clean_slug}"

            sections.append({
                "sec_id": sec_id,
                "index": i + 1,
                "level": item["level"],
                "title": raw_title,
                "start_page": p_start,
                "end_page": p_end,
                "page_count": p_end - p_start + 1
            })

        # Save manifest
        with open(curriculum_cache_file, "w", encoding="utf-8") as f:
            json.dump(sections, f, ensure_ascii=False, indent=2)

        print(f"[+] Successfully extracted {len(sections)} curriculum sections from PDF.")
        return sections

    def extract_section_text_and_code(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts complete text and isolates code blocks from a specific section's page range."""
        start_p = section["start_page"] - 1
        end_p = section["end_page"]

        reader = pypdf.PdfReader(str(self.pdf_path))
        total_pages = len(reader.pages)
        start_p = max(0, min(start_p, total_pages - 1))
        end_p = max(start_p + 1, min(end_p, total_pages))

        pages_text = []
        for p_idx in range(start_p, end_p):
            t = reader.pages[p_idx].extract_text() or ""
            pages_text.append(f"--- Page {p_idx + 1} ---\n" + t)

        full_text = "\n".join(pages_text)

        # Extract code lines heuristic (lines with C++/CUDA keywords or indentation)
        code_snippets = []
        for block in re.split(r"\n\s*\n", full_text):
            if any(k in block for k in ["__global__", "__device__", "__shared__", "cudaMalloc", "cudaMemcpy", "threadIdx", "blockIdx", "void ", "int ", "float ", "for (", "if ("]):
                clean_b = block.strip()
                if len(clean_b) > 20 and len(clean_b) < 1500:
                    code_snippets.append(clean_b)

        return {
            "sec_id": section["sec_id"],
            "title": section["title"],
            "start_page": section["start_page"],
            "end_page": section["end_page"],
            "page_count": section["page_count"],
            "full_text": full_text,
            "text_length": len(full_text),
            "code_snippets": code_snippets[:5]  # Top representative code snippets
        }


if __name__ == "__main__":
    parser = FullBookPdfParser()
    curriculum = parser.extract_full_curriculum(min_level=1, max_level=1)
    print(f"\nTop 10 Sections in Book:")
    for s in curriculum[:10]:
        print(f"[{s['index']}] {s['title']} (P{s['start_page']}-P{s['end_page']}, {s['page_count']} pages)")

    sample_sec = parser.extract_section_text_and_code(curriculum[0])
    print(f"\nSection Sample: {sample_sec['title']}")
    print(f"Extracted Text Length: {sample_sec['text_length']} chars")
    print(f"Code snippets detected: {len(sample_sec['code_snippets'])}")
