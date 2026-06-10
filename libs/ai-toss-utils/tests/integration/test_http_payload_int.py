"""Integration test: verify the exact HTTP payload and headers sent to ThinkTank.

Does NOT require real credentials — intercepts at the requests layer using
`responses`. Validates that our HTTP client sends the right payload structure
(matching the OBI reference implementation).

Marks: integration (HTTP contract test — no live network).
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
def settings_with_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_API_KEY", "test-integration-key-xyz")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "llm": {"provider": "thinktank", "model": "gpt-4o"},
                "toss": {
                    "base_url": _FAKE_BASE_URL,
                    "chat_endpoint": _FAKE_ENDPOINT,
                    "app_name": "my-test-ai-app",
                    "is_prod": True,
                },
            }
        )
    )
    return load_settings(config_path=cfg)


# ── header contract tests ──────────────────────────────────────────────────────


@resp_lib.activate
def test_authorization_header_sent(settings_with_api_key):
    """Every request must carry Authorization: Bearer <token>."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_toss_utils.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient.from_settings(settings_with_api_key)
    client.call_chat_completions(
        {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert len(resp_lib.calls) == 1
    sent_headers = resp_lib.calls[0].request.headers
    assert "Authorization" in sent_headers
    assert sent_headers["Authorization"].startswith("Bearer ")


@resp_lib.activate
def test_x_tgt_application_header_sent(settings_with_api_key):
    """x-tgt-application header must be present — required by ThinkTank API."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_toss_utils.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient.from_settings(settings_with_api_key)
    client.call_chat_completions({"model": "gpt-4o", "messages": []})

    sent_headers = resp_lib.calls[0].request.headers
    assert "x-tgt-application" in sent_headers
    assert sent_headers["x-tgt-application"] == "my-test-ai-app"


@resp_lib.activate
def test_content_type_header_sent(settings_with_api_key):
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_toss_utils.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient.from_settings(settings_with_api_key)
    client.call_chat_completions({"model": "gpt-4o", "messages": []})

    assert resp_lib.calls[0].request.headers["Content-Type"] == "application/json"


# ── payload contract tests ─────────────────────────────────────────────────────


@resp_lib.activate
def test_thinktank_payload_uses_max_tokens(settings_with_api_key):
    """ThinkTank client must send max_tokens (not max_new_tokens)."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings_with_api_key)
    client.chat(
        ChatRequest(
            messages=[ChatMessage("user", "What is 2+2?")],
            max_tokens=256,
        )
    )

    body = json.loads(resp_lib.calls[0].request.body)
    assert "max_tokens" in body, "payload must use max_tokens"
    assert body["max_tokens"] == 256
    assert "max_new_tokens" not in body, "max_new_tokens must NOT be in payload"


@resp_lib.activate
def test_thinktank_payload_has_required_fields(settings_with_api_key):
    """ThinkTank request must include model, messages, stream, temperature."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.llm.base import ChatMessage, ChatRequest
    from ai_thinktank.client import ThinkTankClient

    client = ThinkTankClient(settings_with_api_key)
    client.chat(ChatRequest(messages=[ChatMessage("user", "hello")]))

    body = json.loads(resp_lib.calls[0].request.body)
    assert "model" in body
    assert "messages" in body
    assert isinstance(body["messages"], list)
    assert body["stream"] is False
    assert "temperature" in body


@resp_lib.activate
def test_retry_on_server_error(settings_with_api_key):
    """Client retries 3 times on 500 then raises ProviderError."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)

    from ai_core.exceptions import ProviderError
    from ai_toss_utils.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient.from_settings(settings_with_api_key)
    with pytest.raises(ProviderError, match="HTTP 500"):
        client.call_chat_completions({"model": "gpt-4o", "messages": []})

    # tenacity retries 3 times total
    assert len(resp_lib.calls) == 3
