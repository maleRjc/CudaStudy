"""
Single-line subtitle text preparation with phrase-aware boundaries.

Two rules:
1. Never split inside a Latin word / code identifier.
2. Prefer sentence punctuation, then comma/colon, then spaces; only fall back to
   a CJK character boundary when a clause is still too wide.

The 1280px frame with a 20px burned font gives roughly 28em of usable width;
CJK = 1em, Latin = 0.55em.
"""

from __future__ import annotations

import re
from typing import List

MAX_CUE_EM = 28.0
MAX_UNIT_EM = 12.0

_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_@#\.\+\-/%<>=!&\|\(\)\[\]]+"
    r"|[\u4e00-\u9fff]"
    r"|[\u3000-\u303f\uff00-\uffef]"
    r"|\s+"
    r"|\S",
    re.UNICODE,
)

_PUNCT = "，,。.、；;：:！!？?）)】」』》"
_SENTENCE_END = ("。", "！", "？", "；", "!", "?", ";", ".")


def _ends_sentence(text: str) -> bool:
    return bool(text) and text.rstrip().endswith(_SENTENCE_END)


def estimate_em(text: str) -> float:
    width = 0.0
    for ch in str(text or ""):
        if ch.isspace():
            width += 0.30
        elif "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" or "\uff00" <= ch <= "\uffef":
            width += 1.0
        elif ch.isascii():
            width += 0.55
        else:
            width += 0.8
    return round(width, 2)


def single_line(text: str) -> str:
    return re.sub(r"\s*\n\s*", " ", str(text or "")).strip()


def join_text(left: str, right: str) -> str:
    """Join two units, inserting a space only between Latin word boundaries."""
    if not left:
        return right
    if not right:
        return left
    if left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum():
        return left + " " + right
    return left + right


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


def _split_to_width(text: str, max_em: float) -> List[str]:
    units: List[str] = []
    current = ""
    for token in tokenize(text):
        if token.isspace():
            if current:
                current += " "
            continue
        if not current and token in _PUNCT and units:
            units[-1] = units[-1].rstrip() + token
            continue
        candidate = join_text(current, token) if current else token
        if current and estimate_em(candidate) > max_em:
            units.append(current.strip())
            current = token
        else:
            current = candidate
    if current.strip():
        units.append(current.strip())
    return units


def split_units(text: str, max_unit_em: float = MAX_CUE_EM) -> List[str]:
    """Split narration into phrase-sized units that can be regrouped safely."""
    text = single_line(text)
    if not text:
        return []

    units: List[str] = []
    # Strong sentence boundaries keep their punctuation. A period only ends a
    # sentence when followed by whitespace + capital (so blockIdx.x stays whole).
    for sentence in re.split(r"(?<=[。！？!?；;])|(?<=\.)(?=\s+[A-Z])", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        # Weak clause boundaries: comma / colon / enumeration comma.
        for clause in re.split(r"(?<=[，,、：:])", sentence):
            clause = clause.strip()
            if clause:
                units.extend(_split_to_width(clause, max_unit_em))
    return [unit for unit in units if unit.strip()]


def _hard_split_keep_words(text: str, max_em: float) -> List[str]:
    """Last resort: split an over-wide Latin token only if it alone cannot fit."""
    pieces: List[str] = []
    current = ""
    for token in tokenize(text):
        if token.isspace():
            if current:
                current += " "
            continue
        if estimate_em(current + token) > max_em and current:
            pieces.append(current.strip())
            current = token
        else:
            current = token if not current else join_text(current, token)
    if current.strip():
        pieces.append(current.strip())
    return pieces


def segment_cue(text: str, max_em: float = MAX_CUE_EM) -> List[str]:
    """Regroup phrase units into single-line cues, never breaking a unit."""
    text = single_line(text)
    if not text:
        return []

    units = split_units(text, max_unit_em=max_em)
    cues: List[str] = []
    current = ""

    for unit in units:
        if estimate_em(unit) > max_em:
            if current:
                cues.append(current.strip())
                current = ""
            cues.extend(_hard_split_keep_words(unit, max_em))
            continue

        # Never merge across a sentence boundary.
        if current and _ends_sentence(current):
            cues.append(current.strip())
            current = unit
            continue

        candidate = join_text(current, unit) if current else unit
        if current and estimate_em(candidate) > max_em:
            cues.append(current.strip())
            current = unit
        else:
            current = candidate

    if current.strip():
        cues.append(current.strip())

    merged: List[str] = []
    for cue in cues:
        cue = cue.strip()
        if not cue:
            continue
        if merged and estimate_em(cue) < 4.0:
            if estimate_em(join_text(merged[-1], cue)) <= max_em + 2.0:
                merged[-1] = join_text(merged[-1], cue)
                continue
        merged.append(cue)
    return merged
