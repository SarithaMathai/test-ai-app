"""Unit tests for ai_thinktank.ThinkTankClient."""

from unittest.mock import MagicMock, patch

import pytest
from ai_core.config import load_settings
from ai_core.exceptions import LLMError
from ai_core.llm.base import ChatMessage, ChatRequest

pytestmark = pytest.mark.unit


def _settings(tmp_path, extra=None):
    import yaml

    data = {"llm": {"provider": "thinktank", "model": "llama-3-70b", "max_retries": 2}}
    if extra:
        data.update(extra)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump(data))
    return load_settings(config_path=cfg)


def _make_client(settings):
    mock_http = MagicMock()
    with patch("ai_core.http.AuthenticatedHttpClient", return_value=mock_http):
        from ai_thinktank.client import ThinkTankClient

        client = ThinkTankClient(settings)
    return client, mock_http


# ── provider / model_name ─────────────────────────────────────────────────────


def test_provider(tmp_path):
    settings = _settings(tmp_path)
    client, _ = _make_client(settings)
    assert client.provider == "thinktank"


def test_model_name(tmp_path):
    settings = _settings(tmp_path)
    client, _ = _make_client(settings)
    assert client.model_name == "llama-3-70b"


# ── chat() happy path ─────────────────────────────────────────────────────────


def test_chat_returns_response(tmp_path):
    settings = _settings(tmp_path)
    client, mock_http = _make_client(settings)

    mock_http.post.return_value = {
        "model": "llama-3-70b",
        "choices": [{"finish_reason": "stop", "message": {"content": "4"}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 3},
    }

    resp = client.chat(
        ChatRequest(
            messages=[
                ChatMessage("system", "You are helpful."),
                ChatMessage("user", "What is 2+2?"),
            ]
        )
    )

    assert resp.content == "4"
    assert resp.finish_reason == "stop"
    assert resp.prompt_tokens == 20
    assert resp.completion_tokens == 3
    assert resp.total_tokens == 23


def test_chat_uses_max_tokens(tmp_path):
    """Verify the payload uses max_tokens (standard OpenAI-compatible field)."""
    settings = _settings(tmp_path)
    client, mock_http = _make_client(settings)
    mock_http.post.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
        "usage": {},
    }

    client.chat(ChatRequest(messages=[ChatMessage("user", "hi")], max_tokens=512))

    call_payload = mock_http.post.call_args[0][1]
    assert "max_tokens" in call_payload
    assert call_payload["max_tokens"] == 512
    assert "max_new_tokens" not in call_payload


def test_chat_request_model_overrides_config(tmp_path):
    settings = _settings(tmp_path)
    client, mock_http = _make_client(settings)
    mock_http.post.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
        "usage": {},
    }

    client.chat(ChatRequest(messages=[ChatMessage("user", "hi")], model="gpt-4o"))

    payload = mock_http.post.call_args[0][1]
    assert payload["model"] == "gpt-4o"


# ── error handling ────────────────────────────────────────────────────────────


def test_empty_choices_raises_llm_error(tmp_path):
    settings = _settings(tmp_path)
    client, mock_http = _make_client(settings)
    mock_http.post.return_value = {"choices": [], "usage": {}}

    with pytest.raises(LLMError, match="empty choices"):
        client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))


def test_http_failure_raises_llm_error(tmp_path):
    settings = _settings(tmp_path)
    client, mock_http = _make_client(settings)
    mock_http.post.side_effect = RuntimeError("connection refused")

    with pytest.raises(LLMError, match="ThinkTank API call failed"):
        client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))
