import pytest
import yaml
from ai_core.config import get_settings, load_settings
from ai_core.exceptions import ConfigError

# ── defaults ──────────────────────────────────────────────────────────────────


def test_settings_defaults_without_yaml(tmp_path):
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.app.name == "my-test-ai-app"
    assert settings.app.env == "development"
    assert settings.llm.provider == "thinktank"
    assert settings.llm.max_tokens == 2048
    assert settings.spark.port == 8000
    assert settings.tcin.batch_size == 500


# ── yaml loading ──────────────────────────────────────────────────────────────


def test_load_values_from_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "app": {"env": "production", "log_level": "WARNING"},
                "llm": {"model": "gpt-3.5-turbo", "temperature": 0.7},
                "spark": {"port": 9000},
            }
        )
    )
    settings = load_settings(config_path=cfg)
    assert settings.app.env == "production"
    assert settings.app.log_level == "WARNING"
    assert settings.llm.model == "gpt-3.5-turbo"
    assert settings.llm.temperature == 0.7
    assert settings.spark.port == 9000


def test_yaml_partial_override_keeps_defaults(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"app": {"env": "staging"}}))
    settings = load_settings(config_path=cfg)
    assert settings.app.env == "staging"
    assert settings.app.log_level == "INFO"  # default preserved
    assert settings.llm.provider == "thinktank"  # default preserved


def test_invalid_yaml_raises_config_error(tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("key: [unclosed bracket")
    with pytest.raises(ConfigError, match="Failed to parse"):
        load_settings(config_path=cfg)


# ── env var overrides ──────────────────────────────────────────────────────────


def test_env_override_string(monkeypatch, tmp_path):
    monkeypatch.setenv("APP__LLM__MODEL", "gpt-3.5-turbo")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.llm.model == "gpt-3.5-turbo"


def test_env_override_int(monkeypatch, tmp_path):
    monkeypatch.setenv("APP__SPARK__PORT", "9999")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.spark.port == 9999


def test_env_override_bool_true(monkeypatch, tmp_path):
    monkeypatch.setenv("APP__ELASTICSEARCH__VERIFY_CERTS", "false")
    settings = load_settings(config_path=tmp_path / "missing.yaml")
    assert settings.elasticsearch.verify_certs is False


def test_env_override_wins_over_yaml(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"model": "from-yaml"}}))
    monkeypatch.setenv("APP__LLM__MODEL", "from-env")
    settings = load_settings(config_path=cfg)
    assert settings.llm.model == "from-env"


# ── singleton ─────────────────────────────────────────────────────────────────


def test_get_settings_returns_same_instance():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
