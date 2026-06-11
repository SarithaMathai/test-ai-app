"""ai-thinktank — ThinkTank / Model Garden connectivity.

This package is the single dependency needed to connect an app to ThinkTank:
  - ThinkTankClient: LLMClient implementation (chat completions)
  - get_bearer_token: OAuth / API-key Bearer token helper
  - AuthenticatedHttpClient: low-level authenticated HTTP client

Target-internal auth packages (tgt-certs, pyOauthTarget) are used when
THINKTANK_OAUTH_CLIENT_ID + THINKTANK_OAUTH_CLIENT_SECRET are set; otherwise
falls back to THINKTANK_API_KEY as a static Bearer token.
"""

from ai_core.http import AuthenticatedHttpClient
from ai_core.token import get_bearer_token

from ai_thinktank.client import ThinkTankClient

__all__ = ["AuthenticatedHttpClient", "ThinkTankClient", "get_bearer_token"]
