"""Integration tests for PLM Think Tank AI routes.

Tests the full HTTP request/response cycle with multiple components wired together
(router, DI, service, schema validation). External LLM dependency is mocked via
dependency_overrides — no real network calls, no credentials needed.

Run with:  uv run pytest -m integration
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from ai_core.llm.base import ChatResponse
from fastapi.testclient import TestClient
from plm_think_tank_ai.dependencies import get_llm_client, get_prompt_service
from plm_think_tank_ai.main import create_app
from plm_think_tank_ai.services.prompt_service import PromptService

pytestmark = pytest.mark.integration


def _mock_llm(content: str = "hello world", model: str = "gemini-1.5-pro") -> MagicMock:
    llm = MagicMock()
    llm.provider = "thinktank"
    llm.model_name = model
    llm.chat.return_value = ChatResponse(
        content=content,
        model=model,
        prompt_tokens=10,
        completion_tokens=5,
        finish_reason="stop",
    )
    llm.system.side_effect = lambda c: type("M", (), {"role": "system", "content": c})()
    llm.user.side_effect = lambda c: type("M", (), {"role": "user", "content": c})()
    return llm


@pytest.fixture
def client():
    app = create_app()
    mock_llm = _mock_llm()
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_prompt_service] = lambda: PromptService(mock_llm)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_json_llm():
    """Client whose mock LLM returns a JSON spell-check result."""
    app = create_app()
    spell_result = json.dumps([{"invalidText": "propt", "suggestions": ["prompt"], "foundIn": [1]}])
    mock_llm = _mock_llm(content=spell_result)
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_prompt_service] = lambda: PromptService(mock_llm)
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] == "thinktank"


# ── Prompt endpoint ───────────────────────────────────────────────────────────


def test_unit_test_operation_returns_success(client):
    response = client.post("/api/v1/prompt", json={"operation": "unit-test", "payload": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["operation"] == "unit-test"
    assert data["result"] == "hello world"


def test_spell_checker_returns_parsed_json(client_with_json_llm):
    payload = [{"id": 1, "value": "propt"}]
    response = client_with_json_llm.post("/api/v1/prompt", json={"operation": "spell-checker", "payload": payload})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["result"], list)
    assert data["result"][0]["invalidText"] == "propt"


def test_unknown_operation_returns_400(client):
    response = client.post("/api/v1/prompt", json={"operation": "does-not-exist", "payload": {}})
    assert response.status_code == 400


def test_missing_operation_field_returns_422(client):
    response = client.post("/api/v1/prompt", json={"payload": "test"})
    assert response.status_code == 422


def test_missing_payload_field_returns_422(client):
    response = client.post("/api/v1/prompt", json={"operation": "spell-checker"})
    assert response.status_code == 422
