"""Integration test: Spark Think Tank AI — real FastAPI app, mocked LLM backend.

Tests the full request lifecycle through FastAPI routing → dependency injection
→ ChatService, without mocking the framework layers. The LLM provider itself is
replaced with NoOpLLMClient so no real API calls are made.

Marks: integration (full-stack test, no external services required).
"""

from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    """Settings with provider=none so NoOpLLMClient is used."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "llm": {"provider": "none", "model": "no-op"},
                "app": {"name": "spark-int-test"},
            }
        )
    )
    monkeypatch.setenv("APP_CONFIG_DIR", str(tmp_path))
    from ai_core.config import load_settings

    return load_settings(config_path=cfg)


@pytest.fixture()
def app_client(settings):
    """Full FastAPI app with real DI wired up (LLM is NoOpLLMClient)."""
    from spark_think_tank_ai.dependencies import get_app_settings, get_llm_client
    from spark_think_tank_ai.main import create_app

    application = create_app()
    application.dependency_overrides[get_app_settings] = lambda: settings
    application.dependency_overrides[get_llm_client] = lambda: __import__(
        "ai_core.llm.base", fromlist=["NoOpLLMClient"]
    ).NoOpLLMClient()
    with TestClient(application, raise_server_exceptions=True) as c:
        yield c


# ── health endpoint ────────────────────────────────────────────────────────────


def test_health_returns_200(app_client):
    r = app_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_health_returns_provider_and_model(app_client):
    r = app_client.get("/health")
    data = r.json()
    assert "provider" in data
    assert "model" in data


# ── chat endpoint ──────────────────────────────────────────────────────────────


def test_chat_summarise_returns_200(app_client):
    r = app_client.post(
        "/api/v1/chat",
        json={"operation": "summarise", "payload": "This is a long document about AI."},
    )
    assert r.status_code == 200
    data = r.json()
    assert "result" in data
    assert "model" in data
    assert "prompt_tokens" in data


def test_chat_classify_returns_json_field(app_client):
    r = app_client.post(
        "/api/v1/chat",
        json={"operation": "classify", "payload": "Some text to classify."},
    )
    assert r.status_code == 200


def test_chat_extract_operation(app_client):
    r = app_client.post(
        "/api/v1/chat",
        json={"operation": "extract", "payload": {"text": "Extract from this"}},
    )
    assert r.status_code == 200


def test_chat_unknown_operation_returns_400(app_client):
    r = app_client.post(
        "/api/v1/chat",
        json={"operation": "unknown_op_xyz", "payload": "something"},
    )
    assert r.status_code == 400
    assert "unknown_op_xyz" in r.json()["detail"].lower()


def test_chat_model_override_accepted(app_client):
    r = app_client.post(
        "/api/v1/chat",
        json={
            "operation": "chat",
            "payload": "Hello",
            "model": "gpt-4o-mini",
            "temperature": 0.5,
        },
    )
    assert r.status_code == 200


def test_chat_missing_payload_returns_422(app_client):
    r = app_client.post("/api/v1/chat", json={"operation": "chat"})
    assert r.status_code == 422


def test_chat_missing_operation_returns_422(app_client):
    r = app_client.post("/api/v1/chat", json={"payload": "Hello"})
    assert r.status_code == 422


def test_all_valid_operations_return_200(app_client):
    for op in ("summarise", "classify", "extract", "chat"):
        r = app_client.post(
            "/api/v1/chat",
            json={"operation": op, "payload": f"Test payload for {op}"},
        )
        assert r.status_code == 200, f"operation '{op}' returned {r.status_code}"
