"""Detect curated additives in raw ingredient strings."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import ADDITIVE_PATTERNS


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def detect_additives(ingredients_text: str | None, patterns: dict[str, list[str]] | None = None) -> dict[str, int]:
    """Return binary flags per additive column name."""
    if not ingredients_text:
        return {k: 0 for k in (patterns or ADDITIVE_PATTERNS)}
    pats = patterns or ADDITIVE_PATTERNS
    text = _norm(ingredients_text)
    out: dict[str, int] = {}
    for col, phrases in pats.items():
        found = False
        for ph in phrases:
            phn = ph.lower().strip()
            if phn.startswith("e") and len(phn) <= 5:
                if re.search(rf"(?:^|[^a-z0-9]){re.escape(phn.strip())}(?:$|[^a-z0-9])", text):
                    found = True
                    break
            elif phn in text:
                found = True
                break
        out[col] = int(found)
    return out
