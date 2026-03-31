"""
services/keyword_normalizer.py
===============================
Smart keyword normalization:
  1. Alias map   — regex replacements for abbreviations / typos
  2. Brand inject — bare model numbers get brand prefix
  3. Popular model list — used by instant-search suggestions
"""
import re
from typing import List, Optional

# ════════════════════════════════════════════════════════════════════
# ALIAS MAP  — pattern → canonical name
# Order matters: more specific patterns first
# ════════════════════════════════════════════════════════════════════
_ALIAS_MAP = [
    # ── iPhone ───────────────────────────────────────────────────
    (r"\bip\s*(\d{2})\s*prm\b",    r"iphone \1 pro max"),
    (r"\biphone\s*(\d{2})\s*pm\b", r"iphone \1 pro max"),
    (r"\biphone\s*(\d{2})\s*prm\b",r"iphone \1 pro max"),
    (r"\b(\d{2})\s*prm\b",         r"iphone \1 pro max"),
    (r"\bip\s*(\d{2})\s*pro\b",    r"iphone \1 pro"),
    (r"\bip\s*(\d{2})\b",          r"iphone \1"),
    (r"\bip(\d{2})\b",             r"iphone \1"),
    # ── Samsung ──────────────────────────────────────────────────
    (r"\bss\s*s(\d{2})\s*ultra\b", r"samsung galaxy s\1 ultra"),
    (r"\bss\s*s(\d{2})\b",         r"samsung galaxy s\1"),
    (r"\bsamsung\s*s(\d{2})\s*ultra\b", r"samsung galaxy s\1 ultra"),
    (r"\bsamsung\s*s(\d{2})\b",    r"samsung galaxy s\1"),
    (r"\bgalaxy\s*s(\d{2})\b",     r"samsung galaxy s\1"),
    (r"\bs(\d{2})\s*ultra\b",      r"samsung galaxy s\1 ultra"),
    # ── Xiaomi / Redmi ───────────────────────────────────────────
    (r"\bxm\s*(\d{2})\b",          r"xiaomi \1"),
    (r"\bmi\s*(\d{2})\b",          r"xiaomi \1"),
    (r"\bredmi\s*nt\s*(\d+)\b",    r"redmi note \1"),
    # ── Common typos ─────────────────────────────────────────────
    (r"\bpro\s*m\b",               "pro max"),
    (r"\bpromax\b",                "pro max"),
]

# Compile once at import time
_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _ALIAS_MAP]


# ════════════════════════════════════════════════════════════════════
# POPULAR MODELS — seed for instant-search suggestions
# ════════════════════════════════════════════════════════════════════
POPULAR_MODELS: List[str] = [
    # iPhone
    "iphone 14", "iphone 14 pro", "iphone 14 pro max",
    "iphone 15", "iphone 15 plus", "iphone 15 pro", "iphone 15 pro max",
    "iphone 16", "iphone 16 plus", "iphone 16 pro", "iphone 16 pro max",
    # Samsung
    "samsung galaxy s23", "samsung galaxy s23 ultra",
    "samsung galaxy s24", "samsung galaxy s24 plus", "samsung galaxy s24 ultra",
    "samsung galaxy s25", "samsung galaxy s25 plus", "samsung galaxy s25 ultra",
    "samsung galaxy a55", "samsung galaxy a35", "samsung galaxy a15",
    # Xiaomi / Redmi
    "xiaomi 14", "xiaomi 14 ultra", "xiaomi 13",
    "redmi note 13", "redmi note 13 pro", "redmi note 12",
    "poco x6 pro", "poco f6",
    # OPPO / Vivo / Realme
    "oppo reno 11", "oppo reno 12", "oppo find x7",
    "vivo v29", "vivo v30",
    "realme 12 pro", "realme gt 6",
    # Google / Others
    "pixel 8", "pixel 8 pro", "pixel 9",
    "nokia g42", "asus zenfone 10",
]


# ════════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════════

def normalize_keyword(keyword: str) -> str:
    """
    Normalize a search keyword:
      1. Lowercase & strip
      2. Apply alias/typo replacements
      3. Collapse whitespace
    Returns the canonical form used for DB lookups.
    """
    if not keyword:
        return keyword

    kw = keyword.strip().lower()
    kw = re.sub(r"\s+", " ", kw)

    for pattern, replacement in _COMPILED:
        kw = pattern.sub(replacement, kw)

    return re.sub(r"\s+", " ", kw).strip()


def get_instant_suggestions(prefix: str, db_results: Optional[List[dict]] = None,
                             limit: int = 8) -> List[dict]:
    """
    Build instant-search suggestion list.
    Priority: exact DB trending > popular model prefix > popular model contains.

    Args:
        prefix:     Raw user input (e.g. "ipho")
        db_results: Rows from keyword_log (pre-fetched by caller)
        limit:      Max suggestions to return
    """
    if not prefix or len(prefix.strip()) < 2:
        return []

    norm = normalize_keyword(prefix)
    seen: set = set()
    suggestions: List[dict] = []

    def _add(text: str, kind: str):
        if text not in seen and len(suggestions) < limit:
            seen.add(text)
            suggestions.append({"text": text, "type": kind})

    # 1. DB keyword_log — real user searches (most relevant)
    for row in (db_results or []):
        kw = row.get("keyword", "")
        if norm in kw or kw.startswith(norm):
            _add(kw, "trending")

    # 2. Popular models — exact prefix match
    for model in POPULAR_MODELS:
        if model.startswith(norm):
            _add(model, "popular")

    # 3. Popular models — contains match
    for model in POPULAR_MODELS:
        if norm in model:
            _add(model, "popular")

    return suggestions