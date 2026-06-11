"""Size normalization and similarity scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_BASE_SIZE_MAP: dict[str, str] = {
    "x small": "xs", "xsmall": "xs", "xs": "xs", "extra small": "xs",
    "x-small": "xs", "xtra small": "xs",
    "small": "s", "sm": "s", "s": "s",
    "medium": "m", "med": "m", "m": "m",
    "large": "l", "lg": "l", "l": "l",
    "x large": "xl", "xlarge": "xl", "xl": "xl", "extra large": "xl",
    "x-large": "xl",
    "xx large": "2xl", "xxlarge": "2xl", "2xl": "2xl", "2x large": "2xl",
    "2x": "2xl", "xxl": "2xl",
    "xxx large": "3xl", "3xl": "3xl", "3x large": "3xl", "3x": "3xl",
    "4xl": "4xl", "4x large": "4xl", "4x": "4xl",
    "5xl": "5xl", "5x large": "5xl", "5x": "5xl",
    "one size fits most": "os", "one size fits all": "os", "one size": "os",
    "os": "os", "osfm": "os",
    "0": "0", "2": "2", "4": "4", "6": "6", "8": "8", "10": "10",
    "12": "12", "14": "14", "16": "16", "18": "18", "20": "20",
}

_MODIFIER_PATTERNS: dict[str, str] = {
    r"\b(husky|hsky)\b": "husky",
    r"\b(tall|tll)\b": "tall",
    r"\b(petite|pttie|pt)\b": "petite",
    r"\b(plus|plus\s*size)\b": "plus",
    r"\b(slim|slim\s*fit)\b": "slim",
    r"\b(regular|reg)\b": "regular",
}

_SIZE_ORDER = ["xs", "s", "m", "l", "xl", "2xl", "3xl", "4xl", "5xl"]


@dataclass(frozen=True)
class NormalizedSize:
    base: str
    modifier: str
    raw: str

    @property
    def key(self) -> str:
        return f"{self.base}:{self.modifier}" if self.modifier else self.base

    def __str__(self) -> str:
        return self.key


@lru_cache(maxsize=2048)
def normalize_size(raw: str) -> NormalizedSize:
    if not raw or not isinstance(raw, str):
        return NormalizedSize(base="", modifier="", raw=raw or "")

    text = raw.strip().lower()
    text = re.sub(r"\s+", " ", text)

    modifier = ""
    for pattern, mod_name in _MODIFIER_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            modifier = mod_name
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            break

    base = _BASE_SIZE_MAP.get(text, "")
    if not base:
        text_clean = text.rstrip("s").strip()
        base = _BASE_SIZE_MAP.get(text_clean, text)

    return NormalizedSize(base=base, modifier=modifier, raw=raw)


def size_similarity(tcin_size: str, var_size: str) -> float:
    if not tcin_size and not var_size:
        return 1.0
    if not tcin_size or not var_size:
        return 0.5

    ns_t = normalize_size(tcin_size)
    ns_v = normalize_size(var_size)

    if not ns_t.base or not ns_v.base:
        from rapidfuzz import fuzz as _fuzz
        score = _fuzz.token_set_ratio(tcin_size.lower(), var_size.lower()) / 100.0
        return round(score * 0.80, 3)

    if ns_t.base == ns_v.base and ns_t.modifier == ns_v.modifier:
        return 1.0
    if ns_t.base == ns_v.base:
        return 0.85

    if ns_t.base in _SIZE_ORDER and ns_v.base in _SIZE_ORDER:
        diff = abs(_SIZE_ORDER.index(ns_t.base) - _SIZE_ORDER.index(ns_v.base))
        if diff == 1:
            return 0.75
        if diff == 2:
            return 0.50

    return 0.0


def best_size_match(tcin_size: str, var_sizes: list[str]) -> tuple[str, float]:
    if not var_sizes:
        return "", 0.0
    best_sz, best_sc = "", 0.0
    for vs in var_sizes:
        sc = size_similarity(tcin_size, vs)
        if sc > best_sc:
            best_sz, best_sc = vs, sc
    return best_sz, best_sc
