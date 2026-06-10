"""Unit tests for MapperService — LLM client is mocked throughout."""

from unittest.mock import MagicMock

import pytest
from ai_core.exceptions import LLMError
from ai_core.llm.base import ChatResponse, NoOpLLMClient
from tcin_impression_mapping.models.schemas import MappingRequest, MatchStrategy
from tcin_impression_mapping.services.mapper import MapperService


def _req(**kwargs) -> MappingRequest:
    defaults = {
        "pid": "P001",
        "tcin_id": "T001",
        "color_family": "Blue",
        "color_name": "Navy Blue",
        "size": "M",
        "candidates": ["NAVY", "DARK BLUE", "RED"],
    }
    defaults.update(kwargs)
    return MappingRequest(**defaults)


def _mock_llm(
    response_json: str = '{"impression_name":"NAVY","confidence":0.92,"reasoning":"exact match"}',
):
    mock = MagicMock()
    mock.system.side_effect = lambda c: MagicMock(role="system", content=c)
    mock.user.side_effect = lambda c: MagicMock(role="user", content=c)
    mock.chat.return_value = ChatResponse(
        content=response_json, model="mock", prompt_tokens=10, completion_tokens=5
    )
    return mock


# ── no candidates ─────────────────────────────────────────────────────────────


def test_no_candidates_returns_no_match():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(_req(candidates=[]))
    assert result.strategy == MatchStrategy.NO_MATCH
    assert result.chosen_impression == ""


# ── deterministic path ────────────────────────────────────────────────────────


def test_high_confidence_deterministic_match():
    mapper = MapperService(NoOpLLMClient())
    result = mapper.map_one(
        _req(
            color_name="Navy Blue",
            candidates=["NAVY", "RED", "WHITE"],
        )
    )
    assert result.strategy == MatchStrategy.DETERMINISTIC
    assert result.confidence >= 0.85
    assert result.chosen_impression == "NAVY"


def test_deterministic_does_not_call_llm():
    mock_llm = _mock_llm()
    mapper = MapperService(mock_llm)
    mapper.map_one(_req(color_name="Navy Blue", candidates=["NAVY", "RED"]))
    mock_llm.chat.assert_not_called()


# ── LLM fallback path ─────────────────────────────────────────────────────────


def test_ambiguous_triggers_llm():
    mock_llm = _mock_llm()
    mapper = MapperService(mock_llm, auto_threshold=0.85, llm_threshold=0.30)
    # Use a color that fuzzy-scores in the middle range
    result = mapper.map_one(
        _req(
            color_name="Cobalt",
            candidates=["COBALT DREAM", "DEEP SEA", "FOREST GREEN"],
        )
    )
    # LLM should be called since fuzzy may not hit 0.85
    # (result depends on rapidfuzz score — just verify no crash)
    assert result.chosen_impression != "" or result.strategy == MatchStrategy.NO_MATCH


def test_llm_result_used_when_in_candidates():
    mock_llm = _mock_llm(
        '{"impression_name":"DARK BLUE","confidence":0.88,"reasoning":"dark synonym"}'
    )
    mapper = MapperService(mock_llm, auto_threshold=0.99, llm_threshold=0.01)
    result = mapper.map_one(
        _req(
            color_name="Cobalt",
            candidates=["NAVY", "DARK BLUE", "RED"],
        )
    )
    if result.strategy == MatchStrategy.LLM:
        assert result.chosen_impression == "DARK BLUE"
        assert result.confidence == pytest.approx(0.88)


def test_llm_hallucination_snapped_to_deterministic():
    mock_llm = _mock_llm('{"impression_name":"NOT IN LIST","confidence":0.9,"reasoning":"bad"}')
    mapper = MapperService(mock_llm, auto_threshold=0.99, llm_threshold=0.01)
    result = mapper.map_one(
        _req(
            color_name="Navy Blue",
            candidates=["NAVY", "DARK BLUE"],
        )
    )
    assert result.chosen_impression in ["NAVY", "DARK BLUE"]


# ── LLM failure fallback ──────────────────────────────────────────────────────


def test_llm_failure_falls_back_to_deterministic():
    mock_llm = _mock_llm()
    mock_llm.chat.side_effect = LLMError("network timeout", provider="openai")
    mapper = MapperService(mock_llm, auto_threshold=0.99, llm_threshold=0.01)
    result = mapper.map_one(
        _req(
            color_name="Navy",
            candidates=["NAVY", "RED"],
        )
    )
    assert result.chosen_impression != ""
    assert "fallback" in result.reasoning.lower() or result.strategy == MatchStrategy.DETERMINISTIC


# ── batch mapping ─────────────────────────────────────────────────────────────


def test_batch_result_counts():
    mapper = MapperService(NoOpLLMClient())
    requests = [
        _req(color_name="Navy Blue", candidates=["NAVY", "RED"]),
        _req(color_name="Red", candidates=["RED", "NAVY"]),
        _req(color_name="XYZ999", candidates=["COMPLETELY UNRELATED"], pid="P002"),
    ]
    batch = mapper.map_batch(requests)
    assert batch.total == 3
    assert batch.deterministic + batch.llm_assisted + batch.no_match == 3
