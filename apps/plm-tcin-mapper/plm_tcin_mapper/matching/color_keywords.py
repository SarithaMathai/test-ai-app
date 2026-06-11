"""Color keyword dictionary — maps color words to canonical base colors.

BASE_COLOR_MAP is the static source of truth.
get_merged_keyword_map() merges in human-approved alias overrides from
config/alias_overrides.yaml at runtime without modifying this file.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

BASE_COLOR_MAP: dict[str, list[str]] = {
    "red": [
        "red", "reds", "ruby", "crimson", "scarlet", "cherry", "coral",
        "maroon", "burgundy", "wine", "brick", "rust", "tomato", "garnet",
        "raspberry", "cardinal", "vermillion", "cranberry", "pomegranate",
        "flame", "poppy", "romantic", "cayenne", "geranium", "terracotta",
        "zinfandel", "tawny", "wowzer", "stoplight", "chianti", "claret",
        "sangria", "hibiscus", "stiletto", "valentina", "tomatoes",
    ],
    "blue": [
        "blue", "blues", "navy", "navys", "cobalt", "azure", "cerulean",
        "indigo", "sapphire", "denim", "sky", "aqua", "periwinkle", "ocean",
        "marine", "royal", "powder", "cornflower", "peacock", "mudstone",
        "cashmere", "steel", "chambray", "teal", "cadet", "malibu",
        "regatta", "twilight", "capri", "poseidon", "delphinium", "turquoise",
        "cyan", "tiffany", "arctic", "stormy",
    ],
    "green": [
        "green", "greens", "olive", "olives", "forest", "sage", "mint",
        "emerald", "lime", "hunter", "pine", "moss", "jade", "seafoam",
        "army", "fern", "cedar", "basil", "ivy", "botanical", "jungle",
        "kelp", "terrarium", "pineneedle", "teal", "avocado", "eucalyptus",
        "matcha", "succulent", "cactus", "spruce", "artichoke", "seaweed",
        "fir", "juniper", "algae", "arugula", "malachite", "verdigris",
        "turquoise", "aquamarine", "celadon", "viridian",
    ],
    "yellow": [
        "yellow", "yellows", "gold", "golden", "canary", "lemon", "mustard",
        "amber", "honey", "saffron", "maize", "butter", "straw", "citrine",
        "sunflower", "daisy", "brass", "corn", "goldenrod", "sunshine",
        "banana", "pineapple", "harvest", "solar", "citrus", "beeswax",
        "flaxen", "buttercup", "daffodil",
    ],
    "orange": [
        "orange", "oranges", "tangerine", "peach", "apricot", "pumpkin",
        "papaya", "mango", "melon", "mandarin", "persimmon", "carrot",
        "fiesta", "sienna", "copper", "cantaloupe", "cider", "pumpkinspice",
        "sunrise", "sunset", "emberglow", "sherbet", "sorbet",
    ],
    "pink": [
        "pink", "pinks", "blush", "rose", "fuchsia", "magenta", "flamingo",
        "bubblegum", "mauve", "ballet", "carnation", "punch", "candy",
        "azalea", "clay", "melon", "cherry", "berry", "blossoms", "petal",
        "hot", "rosette", "peony", "quartz", "watermelon", "flamingos",
        "rouge", "rosé", "blossom", "cameo", "strawberry", "lychee",
        "guava", "taffy",
    ],
    "purple": [
        "purple", "purples", "violet", "violets", "lavender", "lilac",
        "plum", "grape", "eggplant", "amethyst", "orchid", "iris", "mulberry",
        "wisteria", "pansy", "powdered", "heather", "berry", "echevaria",
        "lavendula", "thistle", "byzantium", "viola", "hyacinth", "aster",
        "passion", "boysenberry",
    ],
    "brown": [
        "brown", "browns", "tan", "tans", "caramel", "chocolate", "mocha",
        "coffee", "walnut", "chestnut", "hazel", "taupe", "khaki", "sand",
        "wheat", "toffee", "cinnamon", "umber", "mahogany", "espresso",
        "cognac", "bourbon", "pecan", "tuscan", "camel", "bronze", "sienna",
        "honey", "roasted", "dapper", "teak", "hickory", "maple", "acorn",
        "nutmeg", "latte", "praline", "cocoa", "fudge", "tobacco", "saddle",
        "ginger", "timber", "suede", "biscotti", "cedar", "woodsy", "bark",
        "rustic",
    ],
    "gray": [
        "gray", "grays", "grey", "greys", "silver", "charcoal", "slate",
        "ash", "smoke", "pewter", "gunmetal", "dove", "mist", "storm",
        "heather", "hematite", "nickel", "cement", "chrome", "tin",
        "graphite", "granite", "mercury", "titanium", "flint", "pebble",
        "iron", "fossil", "zinc", "alloy",
    ],
    "black": [
        "black", "onyx", "ebony", "jet", "obsidian", "ink", "coal",
        "raven", "shadow", "licorice", "matte", "midnight", "noir",
        "blackout", "caviar", "panther", "phantom", "eclipse",
    ],
    "white": [
        "white", "whites", "ivory", "cream", "pearl", "vanilla", "snow",
        "linen", "chalk", "bone", "blanc", "birch", "alabaster", "porcelain",
        "milk", "eggshell", "marshmallow", "rice", "cloud", "magnolia",
        "creme", "frost", "flax", "popcorn", "coconut", "lace",
    ],
    "beige": [
        "beige", "beiges", "nude", "oatmeal", "almond", "bisque", "latte",
        "biscuit", "putty", "flax", "natural", "stucco", "curds",
        "champagne", "linen", "sand", "parchment", "sesame", "raffia",
        "burlap", "driftwood", "stone", "pebble", "warm", "wheat", "ecru",
        "buff",
    ],
    "multi": [
        "multi", "multicolor", "multicolored", "colorful", "rainbow",
        "print", "pattern", "floral", "graphic", "novelty", "iridescent",
        "assorted", "tiedye", "stripe", "gingham", "plaid", "combo",
        "mixed", "americana", "tropical", "tie-dye", "ombre", "variegated",
        "allover", "aop", "ditsy", "checkered", "animal",
    ],
    "clear": ["clear", "transparent", "translucent", "crystal"],
    "metallic": [
        "metallic", "glitter", "shimmer", "sparkle", "foil", "holographic",
        "iridescent", "chrome", "polished",
    ],
}

COLOR_MODIFIERS: frozenset[str] = frozenset([
    "light", "dark", "deep", "pale", "bright", "vivid", "muted",
    "heathered", "washed", "wash", "finish", "denim", "dusty",
    "classic", "brushed", "polished", "aged", "antique", "neon",
])

_STOP_WORDS: frozenset[str] = frozenset([
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to",
    "for", "with", "de", "du", "le", "la", "its",
    "tpx", "tcx", "tpg", "ncs", "ral", "cmyk", "rgb", "hex",
])

_PRIORITY_ORDER = [
    "black", "white", "red", "blue", "green", "yellow",
    "orange", "pink", "purple", "brown", "gray", "beige",
    "multi", "clear", "metallic",
]

KEYWORD_TO_BASE: dict[str, str] = {}
for _base in _PRIORITY_ORDER:
    for _word in BASE_COLOR_MAP.get(_base, []):
        if _word not in KEYWORD_TO_BASE:
            KEYWORD_TO_BASE[_word] = _base


def _default_override_path() -> Path:
    config_dir = os.environ.get("APP_CONFIG_DIR", "config")
    return Path(config_dir) / "alias_overrides.yaml"


def get_merged_keyword_map(
    override_path: Path | None = None,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return (color_map, keyword_to_base) merged with any approved alias overrides."""
    if override_path is None:
        override_path = _default_override_path()

    merged_map: dict[str, list[str]] = {base: list(words) for base, words in BASE_COLOR_MAP.items()}

    if override_path.exists():
        try:
            with open(override_path, encoding="utf-8") as f:
                overrides: dict = yaml.safe_load(f) or {}
            for base_color, aliases in overrides.items():
                base_lower = base_color.lower()
                if base_lower in merged_map and isinstance(aliases, list):
                    existing = set(merged_map[base_lower])
                    for alias in aliases:
                        alias_clean = str(alias).lower().strip()
                        if alias_clean and alias_clean not in existing:
                            merged_map[base_lower].append(alias_clean)
                            existing.add(alias_clean)
        except Exception:
            pass

    merged_keyword_to_base: dict[str, str] = {}
    for base in _PRIORITY_ORDER:
        for word in merged_map.get(base, []):
            if word not in merged_keyword_to_base:
                merged_keyword_to_base[word] = base
    for base, words in merged_map.items():
        if base not in merged_keyword_to_base:
            for word in words:
                if word not in merged_keyword_to_base:
                    merged_keyword_to_base[word] = base

    return merged_map, merged_keyword_to_base


def tokenize(text: str) -> list[str]:
    """Tokenize a color/impression name into meaningful lowercase words."""
    import re as _re

    raw = _re.split(r"[\s_\-/,&()\+:;\.\"\']+", text.lower())
    sub: list[str] = []
    for chunk in raw:
        parts = _re.sub(r"([a-z])(\d)", r"\1 \2", chunk)
        parts = _re.sub(r"(\d)([a-z])", r"\1 \2", parts)
        sub.extend(parts.split())

    tokens = []
    for tok in sub:
        tok = tok.strip(".#\"'")
        if not tok:
            continue
        if _re.fullmatch(r"[\d\.]+", tok):
            continue
        if _re.fullmatch(r"\d+(?:\.\d+)?(?:ml|oz|g|kg|l|lb|lbs|cm|mm|in|ft)", tok):
            continue
        if len(tok) > 3 and _re.search(r"\d", tok):
            continue
        if len(tok) <= 1 or tok in _STOP_WORDS:
            continue
        tokens.append(tok)
    return tokens


def canonical_colors(tokens: list[str]) -> set[str]:
    return {KEYWORD_TO_BASE[t] for t in tokens if t in KEYWORD_TO_BASE}
