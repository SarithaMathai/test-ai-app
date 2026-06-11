"""Unit tests for ai_core.token."""

from unittest.mock import MagicMock, patch

import pytest
from ai_core.config import load_settings
from ai_core.exceptions import AuthenticationError
from ai_core.token import get_bearer_token

pytestmark = pytest.mark.unit


def _settings(tmp_path, extra=None):
    import yaml

    data = {}
    if extra:
        data.update(extra)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump(data))
    return load_settings(config_path=cfg)


# ── API key fallback ──────────────────────────────────────────────────────────


def test_returns_bearer_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_API_KEY", "my-api-key")
    settings = _settings(tmp_path)
    token = get_bearer_token(settings)
    assert token == "Bearer my-api-key"


def test_api_key_set_in_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_API_KEY", "key-from-env")
    settings = _settings(tmp_path)
    assert get_bearer_token(settings) == "Bearer key-from-env"


# ── no auth configured ────────────────────────────────────────────────────────


def test_raises_when_no_auth_configured(tmp_path):
    settings = _settings(tmp_path)  # no API key, no OAuth creds
    with pytest.raises(AuthenticationError, match="No authentication configured"):
        get_bearer_token(settings)


# ── OAuth flow — pyOauthTarget not available ───────────────────────────────────


def test_falls_back_to_api_key_when_oauth_pkg_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("THINKTANK_API_KEY", "fallback-key")
    settings = _settings(tmp_path)

    # Simulate pyOauthTarget not being installed
    import sys

    monkeypatch.setitem(sys.modules, "tgt_certs", None)
    monkeypatch.setitem(sys.modules, "pyOauthTarget", None)

    token = get_bearer_token(settings)
    assert token == "Bearer fallback-key"


# ── OAuth flow — happy path ───────────────────────────────────────────────────


def test_oauth_happy_path(tmp_path, monkeypatch):
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("THINKTANK_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("THINKTANK_OAUTH_NUID_USERNAME", "user")
    monkeypatch.setenv("THINKTANK_OAUTH_NUID_PASSWORD", "pass")
    settings = _settings(tmp_path)

    mock_tgt_certs = MagicMock()
    mock_tgt_certs.where.return_value = "/certs"
    mock_oauth_svc = MagicMock()
    mock_oauth_svc.ClientGetToken.return_value = "raw-token-xyz"
    mock_oauth_svc.CheckIfTokenIsExpired.return_value = False
    mock_pyoauth = MagicMock()
    mock_pyoauth.pyOauthTarget.return_value = mock_oauth_svc

    with patch.dict("sys.modules", {"tgt_certs": mock_tgt_certs, "pyOauthTarget": mock_pyoauth}):
        from importlib import reload

        import ai_core.token

        reload(ai_core.token)
        token = ai_core.token.get_bearer_token(settings)

    assert token == "Bearer raw-token-xyz"
