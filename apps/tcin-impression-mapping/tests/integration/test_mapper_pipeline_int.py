"""Integration test: full TCIN mapper pipeline — real rapidfuzz, mocked LLM.

Tests the complete deterministic + LLM fallback pipeline end-to-end using
real rapidfuzz scoring but a mocked LLM (NoOpLLMClient for speed, mock LLM
for LLM-path tests). No external services required.

Marks: integration (full-pipeline test, no external services).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from ai_core.llm.base import ChatResponse, NoOpLLMClient
from tcin_impression_mapping.models.schemas import MappingRequest, MatchStrategy
from tcin_impression_mapping.services.mapper import MapperService

pytestmark = pytest.mark.integration


# ── fixtures ──────────────────────────────────────────────────────────────────


def _req(**kw) -> MappingRequest:
    defaults = {
        "pid": "P001",
        "tcin_id": "T001",
        "color_family": "Blue",
        "color_name": "Navy Blue",
        "size": "M",
        "candidates": ["NAVY", "DARK BLUE", "COBALT DREAM", "RED", "WHITE"],
    }
    defaults.update(kw)
    return MappingRequest(**defaults)


def _llm_mock(impression: str, confidence: float = 0.90) -> MagicMock:
    mock = MagicMock()
    mock.system.side_effect = lambda c: MagicMock(role="system", content=c)
    mock.user.side_effect = lambda c: MagicMock(role="user", content=c)
    mock.chat.return_value = ChatResponse(
        content=f'{{"impression_name":"{impression}","confidence":{confidence},"reasoning":"integration test"}}',
        model="mock",
        prompt_tokens=10,
        completion_tokens=5,
    )
    return mock


# ── deterministic path ────────────────────────────────────────────────────────


def test_navy_blue_maps_to_navy_deterministic():
    """'Navy Blue' should deterministically map to 'NAVY' with high confidence."""
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(_req(color_name="Navy Blue", candidates=["NAVY", "RED", "WHITE"]))
    assert result.strategy == MatchStrategy.DETERMINISTIC
    assert result.chosen_impression == "NAVY"
    assert result.confidence >= 0.85
    assert result.is_high_confidence


def test_red_maps_to_red():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(_req(color_name="Red", color_family="Red", candidates=["RED", "NAVY"]))
    assert result.chosen_impression == "RED"
    assert result.strategy == MatchStrategy.DETERMINISTIC


def test_synonym_ruby_matches_red_candidate():
    """'Ruby' is a synonym for red — should match 'RED' or 'RUBY GLOW'."""
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(
        _req(
            color_name="Ruby",
            color_family="Red",
            candidates=["RUBY GLOW", "MIDNIGHT", "COBALT"],
        )
    )
    assert result.strategy != MatchStrategy.NO_MATCH
    assert result.confidence >= 0.85


def test_exact_impression_name_match():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(
        _req(color_name="COBALT DREAM", color_family="Blue", candidates=["COBALT DREAM", "NAVY"])
    )
    assert result.chosen_impression == "COBALT DREAM"
    assert result.confidence == 1.0


# ── LLM-assisted path ─────────────────────────────────────────────────────────


def test_ambiguous_color_routes_to_llm_path():
    """A color with no deterministic containment match triggers the LLM path.

    "Azure" has no exact containment match in the candidates, so rapidfuzz
    will score it below 0.99 (artificially high auto_threshold), routing it
    to the LLM path.
    """
    mock_llm = _llm_mock("CERULEAN SKY", confidence=0.78)
    # Force everything ≥ 0.01 into the LLM path
    mapper = MapperService(mock_llm, auto_threshold=0.99, llm_threshold=0.01)
    result = mapper.map_one(
        _req(
            color_name="Azure",
            color_family="Blue",
            candidates=["CERULEAN SKY", "DEEP SEA", "FOREST GREEN"],
        )
    )
    # Azure → none of the candidates contain "azure" or are contained in "azure"
    # So score will be < 0.99 and LLM should be called
    assert mock_llm.chat.called, "LLM should be called for ambiguous color"
    if result.strategy == MatchStrategy.LLM:
        assert result.chosen_impression == "CERULEAN SKY"


def test_llm_hallucination_snaps_to_deterministic_best():
    """When LLM returns an impression not in candidates, we snap to deterministic."""
    mock_llm = _llm_mock("COMPLETELY MADE UP", confidence=0.95)
    mapper = MapperService(mock_llm, auto_threshold=0.99, llm_threshold=0.01)
    result = mapper.map_one(_req(color_name="Navy Blue", candidates=["NAVY", "DARK BLUE"]))
    # Result must be one of the real candidates
    assert result.chosen_impression in ["NAVY", "DARK BLUE", ""]


# ── no-match path ─────────────────────────────────────────────────────────────


def test_unknown_color_returns_no_match():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(
        _req(
            color_name="XYZZY_NOTACOLOR_9999",
            color_family="Unknown",
            candidates=["TOTALLY UNRELATED IMPRESSION", "SOMETHING ELSE ENTIRELY"],
        )
    )
    assert result.strategy == MatchStrategy.NO_MATCH
    assert result.needs_review


def test_empty_candidates_returns_no_match():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(_req(candidates=[]))
    assert result.strategy == MatchStrategy.NO_MATCH
    assert result.chosen_impression == ""


# ── batch pipeline ────────────────────────────────────────────────────────────


def test_batch_processes_all_requests():
    mapper = MapperService(NoOpLLMClient())
    requests = [
        _req(pid=f"P{i:03d}", color_name=name, candidates=candidates)
        for i, (name, candidates) in enumerate(
            [
                ("Navy Blue", ["NAVY", "RED"]),
                ("Red", ["RED", "WHITE"]),
                ("Midnight Black", ["MIDNIGHT", "IVORY"]),
                ("XYZZY_FAKE_9999", ["SOMETHING_ELSE"]),
            ]
        )
    ]
    batch = mapper.map_batch(requests)
    assert batch.total == 4
    assert batch.deterministic + batch.llm_assisted + batch.no_match == 4
    assert len(batch.results) == 4


def test_batch_counts_match_individual_results():
    mapper = MapperService(NoOpLLMClient())
    requests = [
        _req(pid="P001", color_name="Navy Blue", candidates=["NAVY", "RED"]),
        _req(pid="P002", color_name="Red", candidates=["RED", "WHITE"]),
        _req(pid="P003", color_name="ZZZ_FAKE", candidates=["NOTHING"]),
    ]
    batch = mapper.map_batch(requests)

    # Re-count from individual results to verify batch counters are accurate
    det_count = sum(1 for r in batch.results if r.strategy == MatchStrategy.DETERMINISTIC)
    llm_count = sum(1 for r in batch.results if r.strategy == MatchStrategy.LLM)
    nm_count = sum(1 for r in batch.results if r.strategy == MatchStrategy.NO_MATCH)

    assert batch.deterministic == det_count
    assert batch.llm_assisted == llm_count
    assert batch.no_match == nm_count


# ── live ThinkTank path (skipped unless creds set) ───────────────────────────


def test_live_thinktank_chat(thinktank_available):
    """Full pipeline with real ThinkTank API. Skipped if no credentials."""
    import tempfile
    from pathlib import Path

    import yaml
    from ai_core.config import load_settings
    from ai_core.llm.factory import build_llm_client

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config.yaml"
        cfg.write_text(yaml.dump({"llm": {"provider": "thinktank", "model": "gpt-4o-mini"}}))
        settings = load_settings(config_path=cfg)
        llm = build_llm_client(settings)

    mapper = MapperService(llm)
    result = mapper.map_one(
        _req(color_name="Navy Blue", candidates=["NAVY", "DARK BLUE", "COBALT"])
    )
    assert result.chosen_impression in ["NAVY", "DARK BLUE", "COBALT"]
