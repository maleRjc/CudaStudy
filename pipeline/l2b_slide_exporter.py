"""
Layer 2B: PPT Slide Document Exporter (Markdown & HTML Presentation).
Generates beautiful, standalone slide presentations (.md and .html)
from the technical PPT deck structure extracted from the PDF documentation.
"""

import html
import json
from pathlib import Path
from typing import Dict, Any, List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def export_deck_to_markdown_ppt(deck: Dict[str, Any], output_path: Path) -> Path:
    """Exports structured deck into standard Marp / Presentation Markdown format."""
    slides = deck.get("slides", [])
    topic = deck.get("topic", "CUDA Technical Lecture")

    lines = [
        "---",
        "marp: true",
        "theme: gaia",
        "_class: lead",
        "paginate: true",
        "backgroundColor: #0D1117",
        "color: #FFFFFF",
        "style: |",
        "  section { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; }",
        "  h1 { color: #76B900; }",
        "  h2 { color: #58A6FF; }",
        "  code { background-color: #161B22; color: #7EE787; padding: 2px 6px; border-radius: 4px; }",
        "  blockquote { background: #161B22; border-left: 6px solid #76B900; padding: 10px 16px; margin: 15px 0; }",
        "---",
        "",
        f"# {topic}",
        "### 《CUDA C++ Programming Guide》权威深度精讲",
        "",
        "> 基于认知冲突驱动 · PPT图文精讲 + 3Blue1Brown风格Manim动态微架构推演",
        "",
        "---",
        ""
    ]

    for idx, slide in enumerate(slides, 1):
        s_title = slide.get("title", f"Slide {idx}")
        s_type = slide.get("slide_type", "concept")
        key_points = slide.get("key_points", [])
        narration = slide.get("narration_script", "")
        visual = slide.get("visual_spec", {})
        code_badge = visual.get("code_badge", "")

        lines.append(f"## Slide {idx}：{s_title}")
        lines.append(f"*类型：`{s_type}`*")
        lines.append("")

        if code_badge:
            lines.append("```cuda")
            lines.append(code_badge)
            lines.append("```")
            lines.append("")

        if key_points:
            lines.append("### 📌 核心知识点与板书：")
            for pt in key_points:
                lines.append(f"- **{pt}**")
            lines.append("")

        if narration:
            lines.append("### 🎙️ 讲师详细逐字口播讲稿：")
            lines.append(f"> {narration}")
            lines.append("")

        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[+] PPT Markdown Presentation generated: {output_path.name}")
    return output_path


def export_deck_to_html_presentation(deck: Dict[str, Any], output_path: Path) -> Path:
    """Exports deck into a standalone, interactive HTML presentation viewer."""
    slides = deck.get("slides", [])
    topic = deck.get("topic", "CUDA Technical Lecture")

    slides_html = []
    for idx, slide in enumerate(slides, 1):
        s_title = slide.get("title", f"Slide {idx}")
        s_type = slide.get("slide_type", "concept")
        key_points = slide.get("key_points", [])
        narration = slide.get("narration_script", "")
        visual = slide.get("visual_spec", {})
        code_badge = visual.get("code_badge", "")

        bullets_html = "".join([f"<li><strong>{html.escape(str(pt))}</strong></li>" for pt in key_points])
        code_html = f"<div class='code-block'><code>{html.escape(str(code_badge))}</code></div>" if code_badge else ""

        slides_html.append(f"""
        <div class="slide" id="slide-{idx}">
            <div class="slide-header">
                <span class="slide-badge">Slide {idx} / {len(slides)} · {html.escape(str(s_type))}</span>
                <h2>{html.escape(str(s_title))}</h2>
            </div>
            {code_html}
            <div class="slide-body">
                <div class="bullets-section">
                    <h3>📌 核心概念板书</h3>
                    <ul>{bullets_html}</ul>
                </div>
                <div class="narration-section">
                    <h3>🎙️ 讲师详细口播讲稿</h3>
                    <p>{html.escape(str(narration))}</p>
                </div>
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(str(topic))} - PPT讲解文档</title>
    <style>
        body {{
            margin: 0;
            background-color: #0D1117;
            color: #E6EDF3;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 30px 20px;
        }}
        .deck-container {{
            max-width: 960px;
            width: 100%;
        }}
        .deck-title {{
            text-align: center;
            border-bottom: 2px solid #30363D;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .deck-title h1 {{
            color: #76B900;
            margin: 0 0 10px 0;
        }}
        .slide {{
            background: #161B22;
            border: 1px solid #30363D;
            border-radius: 12px;
            padding: 24px 30px;
            margin-bottom: 28px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .slide-badge {{
            display: inline-block;
            background: rgba(118, 185, 0, 0.15);
            color: #76B900;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        h2 {{
            color: #58A6FF;
            margin: 4px 0 16px 0;
        }}
        h3 {{
            color: #8B949E;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .code-block {{
            background: #090D13;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 12px 16px;
            font-family: Consolas, Monaco, monospace;
            color: #7EE787;
            margin-bottom: 18px;
        }}
        .slide-body {{
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 20px;
        }}
        ul {{
            margin: 0;
            padding-left: 20px;
            color: #C9D1D9;
            line-height: 1.6;
        }}
        .narration-section {{
            background: #1F242C;
            border-left: 4px solid #76B900;
            border-radius: 4px 8px 8px 4px;
            padding: 12px 18px;
        }}
        .narration-section p {{
            margin: 0;
            color: #E6EDF3;
            line-height: 1.7;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="deck-container">
        <div class="deck-title">
            <h1>{html.escape(str(topic))}</h1>
            <p style="color: #8B949E; margin: 0;">《CUDA C++ Programming Guide》自动提取 PPT 讲解文档</p>
        </div>
        {"".join(slides_html)}
    </div>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[+] PPT HTML Presentation generated: {output_path.name}")
    return output_path
