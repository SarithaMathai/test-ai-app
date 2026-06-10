"""Unit tests for MongoConfig, TossConfig, local.yaml merge, and secret injection."""

import yaml
from ai_core.config import load_settings

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


# ── TossConfig defaults ────────────────────────────────────────────────────────


def test_toss_defaults(tmp_path):
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.toss.base_url == "https://thinktank.prod.target.com"
    assert settings.toss.chat_endpoint == "/chat/completions"
    assert settings.toss.app_name == "my-test-ai-app"
    assert settings.toss.is_prod is True
    assert settings.toss.token_env_var == "THINKTANK_TOKEN"
    assert settings.toss.api_key == ""


# ── Secret injection from env vars ────────────────────────────────────────────


def test_toss_api_key_injected_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("THINKTANK_API_KEY", "sk-test-key-123")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.toss.api_key == "sk-test-key-123"


def test_toss_oauth_injected_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_ID", "client-abc")
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_SECRET", "secret-xyz")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.toss.oauth_client_id == "client-abc"
    assert settings.toss.oauth_client_secret == "secret-xyz"


def test_mongo_url_with_embedded_credentials(tmp_path):
    """Credentials embedded in the URL are passed through unchanged."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump({"mongo": {"url": "mongodb://user:pass@host:27017/mydb"}})
    )
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
