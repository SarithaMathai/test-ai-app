"""Integration tests for plm-tcin-mapper routes (mocked Mongo + LLM)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from plm_tcin_mapper.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.mark.integration
class TestHealthRoute:
    def test_health_returns_ok(self, client):
        with patch("plm_tcin_mapper.dependencies._cached_mongo") as mock_mongo_fn:
            mock_mongo = MagicMock()
            mock_mongo.ping = AsyncMock(return_value=True)
            mock_mongo_fn.return_value = mock_mongo

            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "llm_provider" in data


@pytest.mark.integration
class TestMappingsRoute:
    def test_list_mappings_returns_empty(self, client):
        with (
            patch("plm_tcin_mapper.dependencies._cached_mongo") as mock_mongo_fn,
            patch("plm_tcin_mapper.dependencies._cached_llm_client") as mock_llm_fn,
        ):
            mock_mongo = MagicMock()
            mock_db = MagicMock()
            mock_col = MagicMock()
            mock_col.count_documents = AsyncMock(return_value=0)
            mock_col.find.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
            mock_db.__getitem__ = MagicMock(return_value=mock_col)
            mock_mongo.get_db.return_value = mock_db
            mock_mongo_fn.return_value = mock_mongo
            mock_llm_fn.return_value = MagicMock()

            resp = client.get("/api/v1/mappings")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 0
            assert data["items"] == []
