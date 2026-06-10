import pytest
from ai_core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the get_settings LRU cache before and after every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
