"""
Shared per-slide timing for subtitles and animation steps.

Steps are grouped from *phrase units* (punctuation/space boundaries), never by
blind character offsets, so an English word or a Chinese phrase is not cut at a
step boundary. Each step window then shares its boundaries with the first
subtitle cue of that step.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from pipeline.cue_text import (
    MAX_CUE_EM,
    estimate_em,
    join_text,
    segment_cue,
    single_line,
    split_units,
    tokenize,
)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？!?；;])", str(text or ""))
    return [part.strip() for part in parts if part.strip()]


def _join_atoms(atoms: Sequence[str]) -> str:
    result = ""
    for atom in atoms:
        if atom.isspace():
            if result:
                result += " "
            continue
        result = join_text(result, atom) if result else atom
    return result.strip()


def _split_unit(unit: str) -> List[str]:
    """Split one over-long unit near its width midpoint, at atom boundaries."""
    atoms = [atom for atom in tokenize(unit) if not atom.isspace()]
    if len(atoms) < 2:
        return [unit]
    widths = [max(0.1, estimate_em(atom)) for atom in atoms]
    total = sum(widths)
    half = total / 2
    left: List[str] = []
    acc = 0.0
    for atom, width in zip(atoms, widths):
        if left and acc + width > half:
            break
        left.append(atom)
        acc += width
    if not left or len(left) == len(atoms):
        return [unit]
    right = atoms[len(left):]
    return [_join_atoms(left), _join_atoms(right)]


def _partition(units: Sequence[str], k: int) -> List[Sequence[str]]:
    """Partition ordered units into k contiguous groups with balanced width."""
    n = len(units)
    widths = [max(0.1, estimate_em(unit)) for unit in units]
    prefix = [0.0]
    for width in widths:
        prefix.append(prefix[-1] + width)
    total = prefix[-1]
    target = total / k if k else total

    infinity = float("inf")
    dp = [[infinity] * (k + 1) for _ in range(n + 1)]
    prev = [[-1] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    for group in range(1, k + 1):
        for end in range(group, n - (k - group) + 1):
            for begin in range(group - 1, end):
                if dp[begin][group - 1] == infinity:
                    continue
                cost = dp[begin][group - 1] + (prefix[end] - prefix[begin] - target) ** 2
                if cost < dp[end][group]:
                    dp[end][group] = cost
                    prev[end][group] = begin

    groups: List[Sequence[str]] = []
    end = n
    for group in range(k, 0, -1):
        begin = prev[end][group]
        if begin < 0:
            begin = max(0, end - 1)
        groups.append(units[begin:end])
        end = begin
    groups.reverse()
    return groups


def schedule_from_steps(
    step_narrations: Sequence[str],
    step_durations: Sequence[float],
) -> Dict[str, List[Dict[str, Any]]]:
    """Build exact windows from per-step narration audio durations."""
    windows: List[Dict[str, Any]] = []
    cues: List[Dict[str, Any]] = []
    cursor = 0.0

    for text, duration in zip(step_narrations, step_durations):
        duration = max(0.0, float(duration or 0.0))
        start, end = cursor, cursor + duration
        windows.append({"start": round(start, 3), "end": round(end, 3)})

        pieces = segment_cue(str(text or ""), MAX_CUE_EM)
        if pieces and duration > 0.05:
            weights = [max(0.5, estimate_em(piece)) for piece in pieces]
            total_weight = sum(weights) or 1.0
            piece_cursor = start
            for piece, weight in zip(pieces, weights):
                piece_end = min(end, piece_cursor + duration * weight / total_weight)
                cues.append(
                    {
                        "start": round(piece_cursor, 3),
                        "end": round(max(piece_end, piece_cursor + 0.25), 3),
                        "text": piece,
                    }
                )
                piece_cursor = piece_end
        cursor = end

    return {"windows": windows, "cues": cues}


def build_schedule(
    narration: str,
    steps: Sequence[Dict[str, Any]],
    audio_duration: float,
    pause: float = 0.0,
) -> Dict[str, List[Dict[str, Any]]]:
    step_count = max(1, len(steps or []))
    audio_duration = max(0.0, float(audio_duration or 0.0))
    text = single_line(narration)
    units = split_units(text)
    total_em = sum(max(0.1, estimate_em(unit)) for unit in units)

    windows: List[Dict[str, Any]] = []
    cues: List[Dict[str, Any]] = []

    if not units or total_em <= 0 or audio_duration <= 0.05:
        for idx in range(step_count):
            windows.append(
                {
                    "start": round(audio_duration * idx / step_count, 3),
                    "end": round(audio_duration * (idx + 1) / step_count, 3),
                }
            )
        return {"windows": windows, "cues": cues}

    # Make sure there are at least as many units as animation steps.
    while len(units) < step_count:
        largest = max(range(len(units)), key=lambda i: estimate_em(units[i]))
        pieces = _split_unit(units[largest])
        if len(pieces) < 2:
            break
        units[largest: largest + 1] = pieces

    if len(units) < step_count:
        # Degenerate narration: fall back to equal windows without step cues.
        for idx in range(step_count):
            windows.append(
                {
                    "start": round(audio_duration * idx / step_count, 3),
                    "end": round(audio_duration * (idx + 1) / step_count, 3),
                }
            )
        return {"windows": windows, "cues": cues}

    groups = _partition(units, step_count)
    widths = [max(0.1, estimate_em(unit)) for unit in units]
    prefix = [0.0]
    for width in widths:
        prefix.append(prefix[-1] + width)
    total = prefix[-1]

    cursor_index = 0
    for group in groups:
        group_text = _join_atoms(group)
        start = audio_duration * prefix[cursor_index] / total
        cursor_index += len(group)
        end = audio_duration * prefix[cursor_index] / total
        windows.append({"start": round(start, 3), "end": round(end, 3)})

        pieces = segment_cue(group_text, MAX_CUE_EM)
        if not pieces:
            continue
        weights = [max(0.5, estimate_em(piece)) for piece in pieces]
        weight_total = sum(weights) or 1.0
        cursor = start
        for piece, weight in zip(pieces, weights):
            duration = (end - start) * weight / weight_total
            cue_end = min(end, cursor + duration)
            cues.append(
                {
                    "start": round(cursor, 3),
                    "end": round(max(cue_end, cursor + 0.3), 3),
                    "text": piece,
                }
            )
            cursor = cue_end

    if cues and cues[-1]["end"] > audio_duration:
        cues[-1]["end"] = round(audio_duration, 3)
    return {"windows": windows, "cues": cues}
