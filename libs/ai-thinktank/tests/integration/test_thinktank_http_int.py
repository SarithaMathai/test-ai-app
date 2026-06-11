"""Integration test: verify ThinkTank-specific HTTP contract.

Tests that ThinkTank headers and payload shapes are correct end-to-end
(AuthenticatedHttpClient + ThinkTankClient together). No live network.

Marks: integration (mocked network via `responses`).
"""

from __future__ import annotations

import json

import pytest
import responses as resp_lib
import yaml
from ai_core.config import load_settings

pytestmark = pytest.mark.integration

_FAKE_BASE_URL = "https://thinktank.fake.target.com"
_FAKE_ENDPOINT = "/chat/completions"
_FAKE_URL = f"{_FAKE_BASE_URL}{_FAKE_ENDPOINT}"

_MOCK_RESPONSE = {
    "id": "chatcmpl-test",
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": "Hello from mock ThinkTank"},
        }
    ],
    "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
}


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_API_KEY", "test-integration-key-xyz")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "llm": {"provider": "thinktank", "model": "gpt-4o"},
                "thinktank": {
                    "base_url": _FAKE_BASE_URL,
                    "chat_endpoint": _FAKE_ENDPOINT,
                    "app_name": "my-test-ai-app",
                    "tenant_id": "plm-team",
                    "is_prod": True,
                },
            }
        )
    )
    return load_settings(config_path=cfg)


# ── ThinkTank-specific header contract ────────────────────────────────────────


@resp_lib.activate
def test_x_tgt_application_header_sent(settings):
    """x-tgt-application must be present — required by ThinkTank API."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings)
    client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))

    sent = resp_lib.calls[0].request.headers
    assert "x-tgt-application" in sent
    assert sent["x-tgt-application"] == "my-test-ai-app"


@resp_lib.activate
def test_tenant_id_header_sent(settings):
    """tenant-id must be forwarded when configured."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings)
    client.chat(ChatRequest(messages=[ChatMessage("user", "hi")]))

    sent = resp_lib.calls[0].request.headers
    assert sent.get("tenant-id") == "plm-team"


# ── ThinkTank payload contract ─────────────────────────────────────────────────


@resp_lib.activate
def test_payload_uses_max_tokens(settings):
    """ThinkTank client must send max_tokens (not max_new_tokens)."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings)
    client.chat(ChatRequest(messages=[ChatMessage("user", "2+2?")], max_tokens=256))

    body = json.loads(resp_lib.calls[0].request.body)
    assert body["max_tokens"] == 256
    assert "max_new_tokens" not in body


@resp_lib.activate
def test_payload_required_fields(settings):
    """ThinkTank request must include model, messages, stream, temperature."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings)
    client.chat(ChatRequest(messages=[ChatMessage("user", "hello")]))

    body = json.loads(resp_lib.calls[0].request.body)
    assert "model" in body
    assert isinstance(body["messages"], list)
    assert body["stream"] is False
    assert "temperature" in body
