"""Integration test: verify generic AuthenticatedHttpClient behaviour.

Does NOT require real credentials — intercepts at the requests layer using
`responses`. Tests that auth injection, retry, and error surfacing work
correctly for any caller. No live network, no provider-specific knowledge.

Marks: integration (HTTP contract test — mocked network).
"""

from __future__ import annotations

import pytest
import responses as resp_lib
import yaml
from ai_core.config import load_settings

pytestmark = pytest.mark.integration

_FAKE_BASE_URL = "https://api.fake.target.com"
_FAKE_ENDPOINT = "/v1/action"
_FAKE_URL = f"{_FAKE_BASE_URL}{_FAKE_ENDPOINT}"

_MOCK_RESPONSE = {"result": "ok"}


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_API_KEY", "test-key-xyz")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({}))
    return load_settings(config_path=cfg)


# ── auth ───────────────────────────────────────────────────────────────────────


@resp_lib.activate
def test_authorization_header_injected(settings):
    """Every request must carry Authorization: Bearer <token>."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient(settings, base_url=_FAKE_BASE_URL)
    client.post(_FAKE_ENDPOINT, {"key": "value"})

    assert len(resp_lib.calls) == 1
    sent = resp_lib.calls[0].request.headers
    assert "Authorization" in sent
    assert sent["Authorization"].startswith("Bearer ")


@resp_lib.activate
def test_content_type_json(settings):
    """Content-Type must always be application/json."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient(settings, base_url=_FAKE_BASE_URL)
    client.post(_FAKE_ENDPOINT, {})

    assert resp_lib.calls[0].request.headers["Content-Type"] == "application/json"


@resp_lib.activate
def test_caller_headers_forwarded(settings):
    """Static headers provided by caller must appear in every request."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json=_MOCK_RESPONSE, status=200)

    from ai_core.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient(
        settings,
        base_url=_FAKE_BASE_URL,
        headers={"x-custom-app": "my-service", "x-tenant": "t123"},
    )
    client.post(_FAKE_ENDPOINT, {})

    sent = resp_lib.calls[0].request.headers
    assert sent["x-custom-app"] == "my-service"
    assert sent["x-tenant"] == "t123"


# ── retry ─────────────────────────────────────────────────────────────────────


@resp_lib.activate
def test_retry_on_server_error(settings):
    """Client retries 3 times on 500 then raises ProviderError."""
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)
    resp_lib.add(resp_lib.POST, _FAKE_URL, json={"error": "server error"}, status=500)

    from ai_core.exceptions import ProviderError
    from ai_core.http import AuthenticatedHttpClient

    client = AuthenticatedHttpClient(settings, base_url=_FAKE_BASE_URL)
    with pytest.raises(ProviderError, match="HTTP 500"):
        client.post(_FAKE_ENDPOINT, {})

    assert len(resp_lib.calls) == 3
