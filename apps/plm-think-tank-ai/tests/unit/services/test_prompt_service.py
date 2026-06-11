"""Unit tests for PromptService."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from ai_core.llm.base import ChatResponse
from plm_think_tank_ai.services.prompt_service import PromptService


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def service(mock_llm):
    return PromptService(mock_llm)


def _make_response(content: str, model: str = "gemini-1.5-pro") -> ChatResponse:
    return ChatResponse(
        content=content,
        model=model,
        prompt_tokens=10,
        completion_tokens=5,
        finish_reason="stop",
    )


@pytest.mark.unit
def test_spell_checker_returns_parsed_json(service, mock_llm):
    payload = [
        {"id": 1, "value": "propt is no spelllling"},
        {"id": 2, "value": "anottter tyyypooos"},
        {"id": 3, "value": "spelllling, ths is bad"},
    ]
    mock_response = json.dumps(
        [
            {"invalidText": "propt", "suggestions": ["prompt", "prop"], "foundIn": [1]},
            {"invalidText": "spelllling", "suggestions": ["spelling"], "foundIn": [1, 3]},
            {"invalidText": "anottter", "suggestions": ["another"], "foundIn": [2]},
            {"invalidText": "tyyypooos", "suggestions": ["typos"], "foundIn": [2]},
        ]
    )
    mock_llm.chat.return_value = _make_response(mock_response)
    mock_llm.system.side_effect = lambda c: type("M", (), {"role": "system", "content": c})()
    mock_llm.user.side_effect = lambda c: type("M", (), {"role": "user", "content": c})()

    result = service.execute("spell-checker", payload)

    assert result["result"] == [
        {"invalidText": "propt", "suggestions": ["prompt", "prop"], "foundIn": [1]},
        {"invalidText": "spelllling", "suggestions": ["spelling"], "foundIn": [1, 3]},
        {"invalidText": "anottter", "suggestions": ["another"], "foundIn": [2]},
        {"invalidText": "tyyypooos", "suggestions": ["typos"], "foundIn": [2]},
    ]
    assert result["model"] == "gemini-1.5-pro"
    mock_llm.chat.assert_called_once()


@pytest.mark.unit
def test_unit_test_operation_returns_text(service, mock_llm):
    mock_llm.chat.return_value = _make_response("hello world")
    mock_llm.system.side_effect = lambda c: type("M", (), {"role": "system", "content": c})()
    mock_llm.user.side_effect = lambda c: type("M", (), {"role": "user", "content": c})()

    result = service.execute("unit-test", "")

    assert result["result"] == "hello world"
    mock_llm.chat.assert_called_once()


@pytest.mark.unit
def test_unknown_operation_raises_value_error(service, mock_llm):
    with pytest.raises(ValueError, match="Unknown PLM operation 'does-not-exist'"):
        service.execute("does-not-exist", {})


@pytest.mark.unit
def test_invalid_json_response_returns_raw_string(service, mock_llm):
    """When the LLM returns non-JSON for a json operation, result is the raw string."""
    mock_llm.chat.return_value = _make_response("{invalid json}")
    mock_llm.system.side_effect = lambda c: type("M", (), {"role": "system", "content": c})()
    mock_llm.user.side_effect = lambda c: type("M", (), {"role": "user", "content": c})()

    result = service.execute("spell-checker", [])

    assert result["result"] == "{invalid json}"
