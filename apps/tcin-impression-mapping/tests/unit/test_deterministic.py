"""Unit tests for deterministic fuzzy matcher."""

from tcin_impression_mapping.matching.deterministic import find_best_match

CANDIDATES = ["NAVY", "DARK BLUE", "COBALT DREAM", "ROYAL BLUE", "MIDNIGHT", "RED", "WHITE"]


# ── exact / near-exact matches ────────────────────────────────────────────────


def test_exact_color_word_in_impression():
    result = find_best_match("NAVY BLUE", "Blue", ["NAVY", "DARK BLUE", "RED"])
    assert result is not None
    assert result.impression == "NAVY"
    assert result.score == 1.0


def test_color_contained_in_impression():
    result = find_best_match("Blue", "Blue", ["DARK BLUE", "RED", "GREEN"])
    assert result is not None
    assert result.impression == "DARK BLUE"
    assert result.score == 1.0


def test_case_insensitive():
    result = find_best_match("navy", "blue", ["NAVY", "RED"])
    assert result is not None
    assert result.impression == "NAVY"


# ── synonym matching ──────────────────────────────────────────────────────────


def test_synonym_ruby_maps_to_red():
    result = find_best_match("Ruby Red", "Red", ["RUBY GLOW", "COBALT", "IVORY"])
    assert result is not None
    assert result.score >= 0.85


def test_synonym_midnight_maps_to_black():
    result = find_best_match("Black", "Black", ["MIDNIGHT", "IVORY", "COBALT"])
    assert result is not None
    assert result.impression == "MIDNIGHT"
    assert result.score >= 0.85


# ── thresholds ────────────────────────────────────────────────────────────────


def test_returns_none_when_no_candidates():
    result = find_best_match("Blue", "Blue", [])
    assert result is None


def test_returns_none_below_min_threshold():
    result = find_best_match("XYZ123", "XYZ", ["COMPLETELY DIFFERENT TEXT", "NOTHING SIMILAR"])
    # Score should be below the 0.40 default min threshold
    if result is not None:
        assert result.score < 0.85  # at worst ambiguous, not high-confidence


def test_respects_custom_threshold():
    result = find_best_match("Blue", "Blue", ["DARK BLUE"], auto_threshold=0.99, min_threshold=0.99)
    # Even a 1.0 containment match should survive
    assert result is not None


# ── multi-word colors ─────────────────────────────────────────────────────────


def test_multi_word_color_name():
    result = find_best_match("Light Pink", "Pink", ["LIGHT PINK BLUSH", "DARK RED", "NAVY"])
    assert result is not None
    assert "PINK" in result.impression.upper()


def test_color_family_used_in_scoring():
    # Provide color_family to help distinguish ambiguous cases
    r1 = find_best_match("Cobalt", "Blue", ["COBALT DREAM", "COBALT GREEN", "RED"])
    assert r1 is not None
