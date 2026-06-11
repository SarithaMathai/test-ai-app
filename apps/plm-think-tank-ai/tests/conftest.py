"""Shared test fixtures for plm-think-tank-ai."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from ai_core.config import get_settings
from plm_think_tank_ai.services.prompt_service import PromptService

# Safe test defaults — never leak real secrets.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("THINKTANK_API_KEY", "")
os.environ.setdefault("THINKTANK_OAUTH_CLIENT_ID", "")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_prompt_service() -> MagicMock:
    return MagicMock(spec=PromptService)
