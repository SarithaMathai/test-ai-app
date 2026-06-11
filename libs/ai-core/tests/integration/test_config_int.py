"""Integration test: load the real config/base.yaml and validate all sections.

Does NOT require external services — reads only the checked-in YAML file.
Marks: integration (config-layer contract test — no live network).
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture()
def real_config_dir(monkeypatch):
    """Point APP_CONFIG_DIR at the workspace config/ directory."""
    workspace_root = Path(__file__).parents[4]  # …/my-test-ai-app
    config_dir = workspace_root / "config"
    if not (config_dir / "base.yaml").exists():
        pytest.skip("config/base.yaml not found — run from workspace root")
    monkeypatch.setenv("APP_CONFIG_DIR", str(config_dir))
    return config_dir


def test_real_base_yaml_loads(real_config_dir):
    """All Settings fields resolve without error from the real base.yaml."""
    from ai_core.config import load_settings

    settings = load_settings()
    assert settings.app.name != ""
    assert settings.llm.provider in ("thinktank", "openai", "none")


def test_thinktank_base_url_is_https(real_config_dir):
    from ai_core.config import load_settings

    settings = load_settings()
    assert settings.thinktank.base_url.startswith("https://")


def test_thinktank_chat_endpoint_present(real_config_dir):
    from ai_core.config import load_settings

    settings = load_settings()
    assert settings.thinktank.chat_endpoint.startswith("/")


def test_thinktank_app_name_set(real_config_dir):
    from ai_core.config import load_settings

    settings = load_settings()
    assert settings.thinktank.app_name != ""


def test_all_sections_have_expected_keys(real_config_dir):
    from ai_core.config import load_settings

    s = load_settings()
    # Spot-check each section has its primary field
    assert s.llm.model != ""
    assert s.elasticsearch.url != ""
    assert s.mongo.url != ""
    assert s.spark.port > 0
    assert s.tcin.batch_size > 0
