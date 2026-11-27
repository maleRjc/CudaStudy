"""
Layer 4B: static slide cards (title / summary pages).

Cards are rendered at exactly the content area size (1280x632) so the composer
can append the 88px subtitle band without ever covering content. Long Chinese
bullets are wrapped and auto-shrunk instead of running off the card.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

import config

COLOR_BG = (13, 17, 23)
COLOR_CARD = (22, 27, 34)
COLOR_BORDER = (48, 54, 61)
COLOR_ACCENT = (118, 185, 0)
COLOR_BLUE = (88, 166, 255)
COLOR_TEXT = (240, 246, 252)
COLOR_MUTED = (139, 148, 158)
COLOR_CODE_BG = (9, 13, 19)
COLOR_CODE_TEXT = (126, 231, 135)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "msyh.ttc",
    "simhei.ttf",
    "DejaVuSans.ttf",
    "arial.ttf",
]
MONO_CANDIDATES = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "consola.ttf",
    "DejaVuSansMono.ttf",
]


def _font_path(bold: bool = False, mono: bool = False) -> Optional[str]:
    candidates = MONO_CANDIDATES if mono else FONT_CANDIDATES
    if bold and not mono:
        candidates = [r"C:\Windows\Fonts\msyhbd.ttc"] + candidates
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    path = _font_path(bold=bold, mono=mono)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    tokens = re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]|[^\s\u4e00-\u9fff]+|\s+", text)
    lines: List[str] = []
    current = ""
    for token in tokens:
        trial = current + token
        if draw.textlength(trial.strip(), font=font) <= max_width or not current.strip():
            current = trial
        else:
            lines.append(current.strip())
            current = token.lstrip()
    if current.strip():
        lines.append(current.strip())
    return lines


def clamp_lines(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font,
    max_lines: int,
    max_width: int,
) -> List[str]:
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    last = kept[-1]
    while last and draw.textlength(last + "…", font=font) > max_width:
        last = last[:-1]
    kept[-1] = last.rstrip() + "…"
    return kept


class SlideVideoRenderer:
    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "slide_images"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.ffmpeg_bin = config.ffmpeg_binary()

    # ------------------------------------------------------------------
    def render_slide_image(
        self,
        slide: Dict[str, Any],
        topic: str,
        width: int = config.CONTENT_WIDTH,
        height: int = config.CONTENT_HEIGHT,
    ) -> Path:
        img = Image.new("RGB", (width, height), COLOR_BG)
        draw = ImageDraw.Draw(img)

        margin = 28
        draw.rounded_rectangle(
            [margin, 10, width - margin, height - 10],
            radius=16,
            fill=COLOR_CARD,
            outline=COLOR_BORDER,
            width=2,
        )

        slide_id = slide.get("slide_id", 1)
        badge_text = f"  Slide {slide_id} · {slide.get('slide_type', 'concept')}  "
        badge_font = get_font(16, bold=True)
        badge_w = int(draw.textlength(badge_text, font=badge_font)) + 12
        draw.rounded_rectangle(
            [margin + 30, 28, margin + 30 + badge_w, 58],
            radius=10,
            fill=(28, 45, 15),
            outline=COLOR_ACCENT,
            width=1,
        )
        draw.text((margin + 36, 33), badge_text, fill=COLOR_ACCENT, font=badge_font)

        title_font = get_font(34, bold=True)
        max_text_width = width - 2 * margin - 70
        title_lines = wrap_text(draw, slide.get("title", f"Slide {slide_id}"), title_font, max_text_width)
        title_lines = clamp_lines(draw, title_lines, title_font, 2, max_text_width)
        y = 72
        for line in title_lines:
            draw.text((margin + 36, y), line, fill=COLOR_BLUE, font=title_font)
            y += 42

        sub_font = get_font(17)
        subtitle = f"《CUDA C++ Programming Guide》专题：{topic}"
        sub_lines = clamp_lines(draw, wrap_text(draw, subtitle, sub_font, max_text_width), sub_font, 1, max_text_width)
        if sub_lines:
            draw.text((margin + 38, y + 2), sub_lines[0], fill=COLOR_MUTED, font=sub_font)
            y += 30

        y += 8
        draw.line([margin + 30, y, width - margin - 30, y], fill=COLOR_BORDER, width=1)
        y += 22

        visual = slide.get("visual_spec") or {}
        code = str(visual.get("code_badge") or "").strip()
        body_bottom = height - 34

        if code:
            code_font = get_font(16, mono=True)
            code_lines: List[str] = []
            for raw in code.splitlines()[:5]:
                code_lines.extend(wrap_text(draw, raw, code_font, max_text_width - 30)[:2])
            code_lines = clamp_lines(draw, code_lines, code_font, 6, max_text_width - 30)
            block_h = 24 + len(code_lines) * 24
            draw.rounded_rectangle(
                [margin + 30, y, width - margin - 30, y + block_h],
                radius=10,
                fill=COLOR_CODE_BG,
                outline=COLOR_BORDER,
                width=1,
            )
            for idx, line in enumerate(code_lines):
                draw.text((margin + 46, y + 12 + idx * 24), line, fill=COLOR_CODE_TEXT, font=code_font)
            y += block_h + 20

        points = [str(p) for p in (slide.get("key_points") or []) if str(p).strip()][:6]
        for size in (23, 21, 19, 18):
            bullet_font = get_font(size)
            line_h = size + 12
            wrapped: List[tuple] = []
            for point in points:
                wrapped.append((point, wrap_text(draw, point, bullet_font, max_text_width - 40)))
            total_h = sum(len(lines) * line_h + 10 for _, lines in wrapped)
            if y + total_h <= body_bottom or size == 18:
                break

        for _, lines in wrapped:
            lines = clamp_lines(draw, lines, bullet_font, 3, max_text_width - 40)
            draw.ellipse([margin + 36, y + 8, margin + 46, y + 18], fill=COLOR_ACCENT)
            for line in lines:
                if y + line_h > body_bottom:
                    break
                draw.text((margin + 58, y), line, fill=COLOR_TEXT, font=bullet_font)
                y += line_h
            y += 10

        digest = hashlib.sha256(f"{topic}|{slide_id}|{slide.get('title')}".encode("utf-8")).hexdigest()[:10]
        img_path = self.output_dir / f"card_{digest}.png"
        img.save(img_path)
        return img_path

    # ------------------------------------------------------------------
    def create_slide_video_clip(
        self,
        slide_img_path: Path,
        audio_path: Path,
        output_clip_path: Path,
        duration: float,
    ) -> Optional[Path]:
        """Image + narration -> a 1280x632/30fps raw clip (composer adds the band)."""
        duration = max(1.0, float(duration))
        creationflags = 0
        startupinfo = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        audio_ok = bool(audio_path and Path(audio_path).exists())
        cmd = [str(self.ffmpeg_bin), "-y", "-loop", "1", "-framerate", str(config.VIDEO_FPS), "-i", str(slide_img_path)]
        if audio_ok:
            cmd += ["-i", str(audio_path), "-map", "0:v", "-map", "1:a", "-af", "apad"]
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a"]

        cmd += [
            "-t", f"{duration:.3f}",
            "-vf", f"scale={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:force_original_aspect_ratio=decrease,"
                   f"pad={config.CONTENT_WIDTH}:{config.CONTENT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                   f"tpad=stop_mode=clone:stop_duration=3600,fps={config.VIDEO_FPS}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "160k",
            str(output_clip_path),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        if proc.returncode == 0 and output_clip_path.exists() and output_clip_path.stat().st_size > 2000:
            return output_clip_path
        print(f"[!] Slide clip failed: {(proc.stderr or '')[-300:]}")
        return None
