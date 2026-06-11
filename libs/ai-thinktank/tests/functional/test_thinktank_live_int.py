"""Functional test: live ThinkTank API call.

Calls the real ThinkTank/Model Garden API to verify end-to-end functionality.
Requires THINKTANK_API_KEY (or OAuth creds) to be set.
Skipped automatically if credentials are absent.

    THINKTANK_API_KEY=your-key make test-functional-live
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from ai_core.config import load_settings
from ai_core.llm.base import ChatMessage, ChatRequest

pytestmark = pytest.mark.functional


@pytest.fixture(scope="module")
def live_client(thinktank_available):
    """Build a real ThinkTankClient using credentials from env."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Path(tmpdir) / "config.yaml"
        cfg.write_text(yaml.dump({"llm": {"provider": "thinktank", "model": "gpt-4o-mini", "max_tokens": 64}}))
        settings = load_settings(config_path=cfg)

    from ai_thinktank.client import ThinkTankClient

    return ThinkTankClient(settings)


def test_live_chat_returns_content(live_client):
    """A simple prompt should return a non-empty response."""
    request = ChatRequest(
        messages=[
            ChatMessage("system", "You are a helpful assistant. Be very concise."),
            ChatMessage("user", "What is 2 + 2? Answer with just the number."),
        ],
        max_tokens=16,
    )
    response = live_client.chat(request)
    assert response.content.strip() != ""
    assert "4" in response.content


def test_live_chat_response_fields(live_client):
    """Response envelope must contain all expected fields."""
    request = ChatRequest(
        messages=[ChatMessage("user", "Say hello.")],
        max_tokens=16,
    )
    response = live_client.chat(request)
    assert response.model != ""
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.finish_reason in ("stop", "length")


def test_live_provider_and_model(live_client):
    assert live_client.provider == "thinktank"
    assert live_client.model_name != ""
