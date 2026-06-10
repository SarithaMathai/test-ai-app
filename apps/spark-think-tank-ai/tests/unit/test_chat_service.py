"""Unit tests for ChatService — mocks the LLM client, no HTTP calls."""

from unittest.mock import MagicMock

import pytest
from ai_core.llm.base import ChatResponse
from spark_think_tank_ai.services.chat_service import PROMPT_TEMPLATES, ChatService


def _make_service(content="mock response", finish_reason="stop"):
    mock_llm = MagicMock()
    mock_llm.provider = "mock"
    mock_llm.model_name = "test-model"
    mock_llm.system.side_effect = lambda c: MagicMock(role="system", content=c)
    mock_llm.user.side_effect = lambda c: MagicMock(role="user", content=c)
    mock_llm.chat.return_value = ChatResponse(
        content=content,
        model="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        finish_reason=finish_reason,
    )
    return ChatService(mock_llm), mock_llm


# ── happy paths ───────────────────────────────────────────────────────────────


def test_execute_text_operation():
    service, _mock_llm = _make_service("This is a summary.")
    result = service.execute("summarise", "Some long text here")
    assert result["result"] == "This is a summary."
    assert result["model"] == "test-model"
    assert result["prompt_tokens"] == 10
    assert result["completion_tokens"] == 5


def test_execute_json_operation_parses_response():
    service, _ = _make_service('{"label": "positive", "confidence": 0.95}')
    result = service.execute("classify", "Great product!")
    assert isinstance(result["result"], dict)
    assert result["result"]["label"] == "positive"
    assert result["result"]["confidence"] == 0.95


def test_execute_json_falls_back_to_string_on_bad_json():
    service, _ = _make_service("not valid json at all")
    result = service.execute("classify", "text")
    assert isinstance(result["result"], str)  # graceful fallback


def test_execute_passes_payload_as_json_string():
    service, mock_llm = _make_service()
    service.execute("summarise", {"key": "value", "count": 42})
    call_args = mock_llm.chat.call_args[0][0]
    user_msg = call_args.messages[1]
    assert '"key"' in user_msg.content
    assert '"count"' in user_msg.content


def test_execute_passes_string_payload_directly():
    service, mock_llm = _make_service()
    service.execute("chat", "Hello!")
    call_args = mock_llm.chat.call_args[0][0]
    assert call_args.messages[1].content == "Hello!"


# ── model / temperature overrides ─────────────────────────────────────────────


def test_model_override_passed_to_request():
    service, mock_llm = _make_service()
    service.execute("chat", "hi", model="gpt-4o-mini")
    req = mock_llm.chat.call_args[0][0]
    assert req.model == "gpt-4o-mini"


def test_temperature_override():
    service, mock_llm = _make_service()
    service.execute("chat", "hi", temperature=0.9)
    req = mock_llm.chat.call_args[0][0]
    assert req.temperature == 0.9


# ── error cases ───────────────────────────────────────────────────────────────


def test_unknown_operation_raises_value_error():
    service, _ = _make_service()
    with pytest.raises(ValueError, match="Unknown operation"):
        service.execute("nonexistent-op", "payload")


# ── all templates are reachable ───────────────────────────────────────────────


@pytest.mark.parametrize("op", list(PROMPT_TEMPLATES.keys()))
def test_all_templates_execute_without_error(op):
    service, _ = _make_service(
        '{"ok": true}' if PROMPT_TEMPLATES[op]["response_format"] == "json" else "ok"
    )
    result = service.execute(op, "test payload")
    assert result["result"] is not None
