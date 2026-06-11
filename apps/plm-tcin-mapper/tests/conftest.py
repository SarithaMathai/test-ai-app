"""Shared test fixtures for plm-tcin-mapper tests."""

from unittest.mock import MagicMock

import pytest
from ai_core.config import Settings
from ai_core.llm.base import LLMClient, NoOpLLMClient


@pytest.fixture
def mock_settings() -> Settings:
    return Settings()


@pytest.fixture
def noop_llm() -> LLMClient:
    return NoOpLLMClient()


@pytest.fixture
def mock_mongo():
    mongo = MagicMock()
    mongo.get_sync_db.return_value = MagicMock()
    mongo.get_db.return_value = MagicMock()
    mongo.ping.return_value = True
    return mongo
