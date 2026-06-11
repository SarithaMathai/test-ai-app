"""Unit tests for MongoConfig, ThinkTankConfig, local.yaml merge, and secret injection."""

import ai_core.config as config_module
import pytest
import yaml
from ai_core.config import load_settings

pytestmark = pytest.mark.unit

# ── MongoConfig defaults ───────────────────────────────────────────────────────


def test_mongo_defaults(tmp_path):
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.mongo.url == "mongodb://localhost:27017"
    assert settings.mongo.database == "ai_app"


def test_mongo_from_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "mongo": {"url": "mongodb://mongo-host:27017", "database": "mydb"},
            }
        )
    )
    settings = load_settings(config_path=cfg)
    assert settings.mongo.url == "mongodb://mongo-host:27017"
    assert settings.mongo.database == "mydb"


def test_mongo_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("APP__MONGO__URL", "mongodb://prod:27017")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.mongo.url == "mongodb://prod:27017"


# ── ThinkTankConfig defaults ──────────────────────────────────────────────────


def test_thinktank_defaults(tmp_path):
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.thinktank.base_url == "https://thinktank.prod.target.com"
    assert settings.thinktank.chat_endpoint == "/chat/completions"
    assert settings.thinktank.app_name == "my-test-ai-app"
    assert settings.thinktank.is_prod is True
    assert settings.thinktank.token_env_var == "THINKTANK_TOKEN"
    assert settings.thinktank.api_key == ""


# ── Secret injection from env vars ────────────────────────────────────────────


def test_thinktank_api_key_injected_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("THINKTANK_API_KEY", "sk-test-key-123")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.thinktank.api_key == "sk-test-key-123"


def test_thinktank_oauth_injected_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_ID", "client-abc")
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_SECRET", "secret-xyz")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.thinktank.oauth_client_id == "client-abc"
    assert settings.thinktank.oauth_client_secret == "secret-xyz"


def test_thinktank_api_key_injected_from_tap_secret_file(monkeypatch, tmp_path):
    tap_secret_dir = tmp_path / "tap-secret"
    tap_secret_dir.mkdir()
    (tap_secret_dir / "THINKTANK_API_KEY").write_text("tap-secret-key\n")
    monkeypatch.setattr(config_module, "_SECRET_DIRS", (tap_secret_dir,))
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.thinktank.api_key == "tap-secret-key"


def test_env_secret_wins_over_tap_secret_file(monkeypatch, tmp_path):
    tap_secret_dir = tmp_path / "tap-secret"
    tap_secret_dir.mkdir()
    (tap_secret_dir / "THINKTANK_API_KEY").write_text("tap-secret-key\n")
    monkeypatch.setattr(config_module, "_SECRET_DIRS", (tap_secret_dir,))
    monkeypatch.setenv("THINKTANK_API_KEY", "env-secret-key")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.thinktank.api_key == "env-secret-key"


def test_mongo_url_with_embedded_credentials(tmp_path):
    """Credentials embedded in the URL are passed through unchanged."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"mongo": {"url": "mongodb://user:pass@host:27017/mydb"}}))
    settings = load_settings(config_path=cfg)
    assert "user:pass@" in settings.mongo.url


# ── local.yaml merge (via APP_CONFIG_DIR) ────────────────────────────────────


def test_local_yaml_overrides_base(tmp_path, monkeypatch):
    (tmp_path / "base.yaml").write_text(
        yaml.dump(
            {
                "llm": {"provider": "thinktank", "model": "gpt-4o"},
            }
        )
    )
    (tmp_path / "local.yaml").write_text(
        yaml.dump(
            {
                "llm": {"model": "gpt-3.5-turbo"},  # override only model
            }
        )
    )
    monkeypatch.setenv("APP_CONFIG_DIR", str(tmp_path))
    settings = load_settings()
    assert settings.llm.provider == "thinktank"  # kept from base
    assert settings.llm.model == "gpt-3.5-turbo"  # overridden by local


def test_missing_local_yaml_is_fine(tmp_path, monkeypatch):
    (tmp_path / "base.yaml").write_text(yaml.dump({"llm": {"provider": "none"}}))
    # no local.yaml — should not raise
    monkeypatch.setenv("APP_CONFIG_DIR", str(tmp_path))
    settings = load_settings()
    assert settings.llm.provider == "none"
