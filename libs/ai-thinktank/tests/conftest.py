import os

import pytest
from ai_core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def thinktank_available():
    """Skip the test if no ThinkTank credentials are configured.

    Checks for THINKTANK_API_KEY or THINKTANK_OAUTH_CLIENT_ID.
    Add this fixture to any integration test that needs a live ThinkTank connection.
    """
    if not os.getenv("THINKTANK_API_KEY") and not os.getenv("THINKTANK_OAUTH_CLIENT_ID"):
        pytest.skip("ThinkTank credentials not configured — set THINKTANK_API_KEY to run live tests")
