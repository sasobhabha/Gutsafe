"""
Aggregate microbiome-effect rubric from common food ingredient phrases (not only additives).

Matches each comma-separated segment against the longest keyword first (ingredient_lexicon.csv).
Short keywords (<=5 chars) use word boundaries to avoid false positives (e.g. 'salt' in 'basil').
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import TARGET_COLUMNS

LEXICON_CSV = _ROOT / "data" / "ingredient_lexicon.csv"

_rows_cache: list[dict] | None = None


def clear_lexicon_cache() -> None:
    """Call after tests if ingredient_lexicon.csv changes."""
    global _rows_cache
    _rows_cache = None


def _load_lexicon_rows() -> list[dict]:
    global _rows_cache
    if _rows_cache is not None:
        return _rows_cache
    df = pd.read_csv(LEXICON_CSV)
    rows = []
    for _, r in df.iterrows():
        kw = str(r["keyword"]).strip()
        if not kw:
            continue
        row = {"keyword": kw.lower()}
        for t in TARGET_COLUMNS:
            row[t] = float(r[t])
        rows.append(row)
    rows.sort(key=lambda x: -len(x["keyword"]))
    _rows_cache = rows
    return _rows_cache


def _split_segments(ingredients_text: str) -> list[str]:
    t = re.sub(r"\s+", " ", ingredients_text.lower().strip())
    if not t:
        return []
    parts: list[str] = []
    for p in t.split(","):
        p = p.strip()
        if p:
            parts.append(p)
    return parts


def _keyword_in_segment(keyword: str, segment: str) -> bool:
    """Segment is already lowercased."""
    k = keyword.lower().strip()
    seg = segment.lower()
    if len(k) <= 5:
        return re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", seg) is not None
    return k in seg


def aggregate_lexicon_effects(ingredients_text: str | None) -> tuple[dict[str, float], int, list[str]]:
    """
    Sum lexicon rows: one best (longest) keyword match per segment.
    Returns (effects dict, segment_count, matched_keywords for transparency).
    """
    out = {t: 0.0 for t in TARGET_COLUMNS}
    if not ingredients_text or not str(ingredients_text).strip():
        return out, 0, []

    segments = _split_segments(ingredients_text)
    rows = _load_lexicon_rows()
    matched: list[str] = []

    for seg in segments:
        hit: dict | None = None
        for row in rows:
            if _keyword_in_segment(row["keyword"], seg):
                hit = row
                break
        if hit:
            matched.append(hit["keyword"])
            for t in TARGET_COLUMNS:
                out[t] += float(hit[t])

    return out, len(segments), matched


def merge_additive_and_lexicon(
    additive_effects: dict[str, float],
    lexicon_effects: dict[str, float],
    segment_count: int,
) -> dict[str, float]:
    """Element-wise sum + ultra-processed proxy from ingredient-list length."""
    merged = {t: float(additive_effects.get(t, 0)) + float(lexicon_effects.get(t, 0)) for t in TARGET_COLUMNS}
    if segment_count > 6:
        merged["barrier_risk"] += min(0.14, 0.0035 * float(segment_count - 6))
    return merged
