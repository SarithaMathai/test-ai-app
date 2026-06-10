from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from ai_core.exceptions import ConfigError


class AppConfig(BaseModel):
    name: str = "my-test-ai-app"
    env: str = "development"
    log_level: str = "INFO"


class LLMConfig(BaseModel):
    provider: str = "thinktank"
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 2048
    request_timeout: int = 60
    max_retries: int = 3


class OpenAIConfig(BaseModel):
    base_url: str = ""


class ElasticsearchConfig(BaseModel):
    url: str = "http://localhost:9200"
    username: str = ""
    verify_certs: bool = True
    request_timeout: int = 30
    max_retries: int = 3


class MongoConfig(BaseModel):
    """MongoDB connection settings.

    Use the full connection URL — embed credentials directly:
      mongodb://username:password@host:27017/database
      mongodb+srv://username:password@cluster.mongodb.net/database

    Override via env var:  MONGO__URL=mongodb://user:pass@host:27017/db
    """

    url: str = "mongodb://localhost:27017"
    database: str = "ai_app"


class TossConfig(BaseModel):
    """ThinkTank / Model Garden connection, OAuth, and API settings.

    Secrets (oauth_client_secret, oauth_nuid_password, api_key) are injected
    from env vars at runtime — they are never read from YAML.
    """

    base_url: str = "https://thinktank.prod.target.com"
    chat_endpoint: str = "/chat/completions"
    app_name: str = "my-test-ai-app"  # sent as x-tgt-application header
    tenant_id: str = ""
    token_env_var: str = "THINKTANK_TOKEN"
    is_prod: bool = True  # True for prod OAuth; False for stage/dev
    # Populated from env at startup — not settable via YAML
    api_key: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_nuid_username: str = ""
    oauth_nuid_password: str = ""


class SparkConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class TCINConfig(BaseModel):
    data_dir: str = "./data"
    batch_size: int = 500


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    llm: LLMConfig = LLMConfig()
    toss: TossConfig = TossConfig()
    openai: OpenAIConfig = OpenAIConfig()
    elasticsearch: ElasticsearchConfig = ElasticsearchConfig()
    mongo: MongoConfig = MongoConfig()
    spark: SparkConfig = SparkConfig()
    tcin: TCINConfig = TCINConfig()


def _coerce(value: str) -> Any:
    """Convert an env var string to the most likely Python type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _apply_env_overrides(data: dict[str, Any]) -> None:
    """Merge APP__SECTION__KEY=value env vars into data dict.

    Example: APP__LLM__MODEL=gpt-3.5-turbo  →  data["llm"]["model"] = "gpt-3.5-turbo"
    """
    for raw_key, raw_value in os.environ.items():
        if not raw_key.startswith("APP__"):
            continue
        parts = raw_key[5:].lower().split("__")
        node = data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = _coerce(raw_value)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file; return {} if it doesn't exist. Raise ConfigError on parse failure."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse {path}: {exc}") from exc


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base. Override wins on conflicts."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _inject_secrets(settings: Settings) -> None:
    """Pull secrets from env vars into config objects after YAML + env-override loading.

    These are never read from YAML. The convention is flat env var names so they
    integrate naturally with secret managers (AWS SSM, K8s secrets, .env files).
    """
    env = os.environ

    # Toss / ThinkTank OAuth
    settings.toss.api_key = env.get("THINKTANK_API_KEY", "")
    settings.toss.oauth_client_id = env.get("THINKTANK_OAUTH_CLIENT_ID", "")
    settings.toss.oauth_client_secret = env.get("THINKTANK_OAUTH_CLIENT_SECRET", "")
    settings.toss.oauth_nuid_username = env.get("THINKTANK_OAUTH_NUID_USERNAME", "")
    settings.toss.oauth_nuid_password = env.get("THINKTANK_OAUTH_NUID_PASSWORD", "")

    # OpenAI (no config object — accessed directly from env by the client)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings by merging base.yaml → local.yaml → env var overrides.

    Resolution order (highest wins):
        1. APP__SECTION__KEY=value env vars
        2. config/local.yaml  (local dev overrides, git-ignored)
        3. config/base.yaml   (repo defaults, checked in)
        4. Pydantic field defaults

    Raises ConfigError only when a YAML file exists but cannot be parsed.
    """
    if config_path is not None:
        # Explicit path provided (mostly for tests)
        data = _load_yaml(config_path)
    else:
        config_dir = Path(os.environ.get("APP_CONFIG_DIR", "config"))
        base = _load_yaml(config_dir / "base.yaml")
        local = _load_yaml(config_dir / "local.yaml")
        data = _deep_merge(base, local)

    _apply_env_overrides(data)
    settings = Settings(**data)
    _inject_secrets(settings)
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return load_settings()
