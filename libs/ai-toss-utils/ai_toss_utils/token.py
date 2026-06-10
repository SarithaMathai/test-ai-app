"""OAuth token management for ThinkTank and Model Garden APIs.

Strategy (tried in order):
  1. Full OAuth flow via pyOauthTarget + tgt_certs (Target internal environments).
     Requires THINKTANK_OAUTH_CLIENT_ID and THINKTANK_OAUTH_CLIENT_SECRET to be set.
  2. Static API key fallback — returns "Bearer {THINKTANK_API_KEY}".
     Suitable for external / local development environments.

Secrets come from environment variables injected into settings.toss by
ai_core.config.load_settings. Never read them from YAML.

Usage:
    from ai_toss_utils.token import get_bearer_token
    token = get_bearer_token(settings)   # "Bearer eyJ..."
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from ai_core.exceptions import AuthenticationError

if TYPE_CHECKING:
    from ai_core.config import Settings

log = logging.getLogger(__name__)


def get_bearer_token(settings: Settings) -> str:
    """Return a valid Bearer token string for API authentication.

    Raises:
        AuthenticationError: if no authentication method is configured.
    """
    toss = settings.toss

    # Strategy 1: OAuth flow (Target internal environments)
    if toss.oauth_client_id and toss.oauth_client_secret:
        try:
            return _oauth_token(settings)
        except ImportError:
            log.warning(
                "pyOauthTarget / tgt_certs not available — "
                "falling back to API key auth. "
                "Install ai-toss-utils[target-auth] for full OAuth support."
            )

    # Strategy 2: static API key
    api_key = toss.api_key or os.environ.get("THINKTANK_API_KEY", "")
    if api_key:
        return f"Bearer {api_key}"

    raise AuthenticationError(
        "No authentication configured for ThinkTank. "
        "Set THINKTANK_API_KEY for simple auth, or set "
        "THINKTANK_OAUTH_CLIENT_ID + THINKTANK_OAUTH_CLIENT_SECRET for OAuth."
    )


def _oauth_token(settings: Settings) -> str:
    """Internal: obtain token via pyOauthTarget (Target-internal only).

    Raises ImportError when the Target-internal packages are not installed.
    """
    import tgt_certs  # type: ignore[import]
    from pyOauthTarget import pyOauthTarget  # type: ignore[import]

    toss = settings.toss
    # setup_env() configures REQUESTS_CA_BUNDLE; setup_requests() patches the
    # requests library with Target's CA bundle — both are required.
    tgt_certs.setup_env()
    tgt_certs.setup_requests()
    svc = pyOauthTarget(tgt_certs.where())

    token_env_var = toss.token_env_var or "THINKTANK_TOKEN"
    is_prod = bool(toss.is_prod)
    raw = svc.ClientGetToken(
        clientID=toss.oauth_client_id,
        clientSecret=toss.oauth_client_secret,
        NUID=toss.oauth_nuid_username,
        NUIDPassword=toss.oauth_nuid_password,
        tokenEnvVar=token_env_var,
        isProd=is_prod,
        expiryLeadTime=60,  # refresh 60 s before actual expiry
    )

    if raw and svc.CheckIfTokenIsExpired(raw):
        log.info("OAuth token expired — refreshing")
        os.environ.pop(token_env_var, None)
        raw = svc.ClientGetToken(
            clientID=toss.oauth_client_id,
            clientSecret=toss.oauth_client_secret,
            NUID=toss.oauth_nuid_username,
            NUIDPassword=toss.oauth_nuid_password,
            tokenEnvVar=token_env_var,
            isProd=is_prod,
            expiryLeadTime=60,
        )

    if not raw:
        raise AuthenticationError("OAuth token retrieval returned empty token.")

    return f"Bearer {raw}"
