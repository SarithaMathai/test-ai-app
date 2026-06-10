"""Unit tests for ai_core.llm — base types, NoOpLLMClient, and factory."""

import pytest
from ai_core.config import load_settings
from ai_core.exceptions import ConfigError
from ai_core.llm.base import ChatMessage, ChatRequest, ChatResponse, LLMClient, NoOpLLMClient
from ai_core.llm.factory import build_llm_client

# ── ChatMessage / ChatRequest / ChatResponse ──────────────────────────────────


def test_chat_message_fields():
    m = ChatMessage(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"


def test_chat_request_defaults():
    req = ChatRequest(messages=[ChatMessage("user", "hi")])
    assert req.model == ""
    assert req.temperature is None
    assert req.response_format == "text"
    assert req.stream is False


def test_chat_response_total_tokens():
    resp = ChatResponse(content="ok", model="gpt-4o", prompt_tokens=10, completion_tokens=5)
    assert resp.total_tokens == 15


# ── NoOpLLMClient ─────────────────────────────────────────────────────────────


def test_noop_client_provider():
    client = NoOpLLMClient()
    assert client.provider == "none"
    assert client.model_name == "none"


def test_noop_client_chat_returns_empty():
    client = NoOpLLMClient()
    resp = client.chat(ChatRequest(messages=[ChatMessage("user", "test")]))
    assert resp.content == ""
    assert resp.finish_reason == "disabled"


def test_noop_client_is_llm_client():
    assert isinstance(NoOpLLMClient(), LLMClient)


# ── helper shortcuts ──────────────────────────────────────────────────────────


def test_system_helper():
    client = NoOpLLMClient()
    msg = client.system("You are helpful.")
    assert msg.role == "system"


def test_user_helper():
    client = NoOpLLMClient()
    msg = client.user("What is 2+2?")
    assert msg.role == "user"


# ── factory — provider="none" ─────────────────────────────────────────────────


def test_factory_none_provider(tmp_path):
    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"provider": "none"}}))
    settings = load_settings(config_path=cfg)
    client = build_llm_client(settings)
    assert isinstance(client, NoOpLLMClient)


def test_factory_unknown_provider_raises(tmp_path):
    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"provider": "unknown-provider"}}))
    settings = load_settings(config_path=cfg)
    with pytest.raises(ConfigError, match="Unknown LLM provider"):
        build_llm_client(settings)


def test_factory_openai_without_lib_raises(tmp_path, monkeypatch):
    import sys

    import yaml

    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"provider": "openai"}}))
    settings = load_settings(config_path=cfg)
    # Block ai_openai import
    monkeypatch.setitem(sys.modules, "ai_openai.client", None)
    with pytest.raises((ConfigError, ImportError)):
        build_llm_client(settings)
