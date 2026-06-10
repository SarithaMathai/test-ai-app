"""Unit tests for ai_openai.OpenAIClient.

All tests mock the openai SDK so no real API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest
from ai_core.config import load_settings
from ai_core.exceptions import LLMError
from ai_core.llm.base import ChatMessage, ChatRequest


def _settings(tmp_path, provider="openai"):
    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"provider": provider, "max_retries": 2}}))
    return load_settings(config_path=cfg)


# ── construction ──────────────────────────────────────────────────────────────


def test_raises_without_api_key(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        from ai_openai.client import OpenAIClient

        OpenAIClient(settings)


def test_raises_without_openai_package(tmp_path, monkeypatch):
    import sys

    settings = _settings(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ImportError, match="openai package"):
        from importlib import reload

        import ai_openai.client

        reload(ai_openai.client)
        ai_openai.client.OpenAIClient(settings)


# ── provider / model_name ─────────────────────────────────────────────────────


def test_provider_and_model_name(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = _settings(tmp_path)
    mock_openai = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai}):
        mock_openai.OpenAI.return_value = MagicMock()
        from importlib import reload

        import ai_openai.client

        reload(ai_openai.client)
        client = ai_openai.client.OpenAIClient(settings)
        assert client.provider == "openai"
        assert client.model_name == settings.llm.model


# ── chat() ────────────────────────────────────────────────────────────────────


def test_chat_returns_response(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = _settings(tmp_path)

    fake_choice = MagicMock()
    fake_choice.message.content = "Hello, world!"
    fake_choice.finish_reason = "stop"
    fake_resp = MagicMock()
    fake_resp.choices = [fake_choice]
    fake_resp.model = "gpt-4o"
    fake_resp.usage.prompt_tokens = 10
    fake_resp.usage.completion_tokens = 5

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value.chat.completions.create.return_value = fake_resp

    with patch.dict("sys.modules", {"openai": mock_openai}):
        from importlib import reload

        import ai_openai.client

        reload(ai_openai.client)
        client = ai_openai.client.OpenAIClient(settings)
        resp = client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))

    assert resp.content == "Hello, world!"
    assert resp.prompt_tokens == 10
    assert resp.completion_tokens == 5
    assert resp.total_tokens == 15


def test_chat_raises_llm_error_after_retries(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = _settings(tmp_path)  # max_retries=2

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError(
        "network fail"
    )

    with patch.dict("sys.modules", {"openai": mock_openai}):
        from importlib import reload

        import ai_openai.client

        reload(ai_openai.client)
        client = ai_openai.client.OpenAIClient(settings)
        with patch("time.sleep"), pytest.raises(LLMError, match="attempt"):
            client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))
