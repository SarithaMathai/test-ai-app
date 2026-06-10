"""Integration-style tests for FastAPI routes using TestClient.

The LLM client is replaced with a NoOpLLMClient so no real provider is called.
"""

from unittest.mock import MagicMock, patch

import pytest
from ai_core.llm.base import ChatResponse, NoOpLLMClient
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Return a TestClient with the LLM client mocked to a controllable stub."""
    mock_llm = MagicMock(spec=NoOpLLMClient)
    mock_llm.provider = "mock"
    mock_llm.model_name = "mock-model"
    mock_llm.system.side_effect = lambda c: MagicMock(role="system", content=c)
    mock_llm.user.side_effect = lambda c: MagicMock(role="user", content=c)
    mock_llm.chat.return_value = ChatResponse(
        content="mocked response",
        model="mock-model",
        prompt_tokens=8,
        completion_tokens=4,
        finish_reason="stop",
    )

    from spark_think_tank_ai import dependencies

    with patch.object(dependencies, "_cached_llm_client", return_value=mock_llm):
        from spark_think_tank_ai.main import create_app

        app = create_app()
        with TestClient(app) as c:
            yield c, mock_llm


# ── /health ───────────────────────────────────────────────────────────────────


def test_health_returns_ok(client):
    tc, _ = client
    resp = tc.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["provider"] == "mock"
    assert data["model"] == "mock-model"


# ── POST /api/v1/chat ─────────────────────────────────────────────────────────


def test_chat_success(client):
    tc, _ = client
    resp = tc.post("/api/v1/chat", json={"operation": "summarise", "payload": "long text"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["operation"] == "summarise"
    assert data["result"] == "mocked response"
    assert data["prompt_tokens"] == 8
    assert data["completion_tokens"] == 4


def test_chat_unknown_operation_returns_400(client):
    tc, _ = client
    resp = tc.post("/api/v1/chat", json={"operation": "no-such-op", "payload": "x"})
    assert resp.status_code == 400


def test_chat_with_model_override(client):
    tc, mock_llm = client
    tc.post(
        "/api/v1/chat",
        json={
            "operation": "chat",
            "payload": "hello",
            "model": "gpt-4o-mini",
            "temperature": 0.5,
        },
    )
    req = mock_llm.chat.call_args[0][0]
    assert req.model == "gpt-4o-mini"
    assert req.temperature == 0.5


def test_chat_missing_payload_returns_422(client):
    tc, _ = client
    resp = tc.post("/api/v1/chat", json={"operation": "summarise"})
    assert resp.status_code == 422
