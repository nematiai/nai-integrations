"""MeWe adapter — placeholder until the developer API exits private preview.

MeWe exposes a developer portal at developer.mewe.com but the HTTP endpoint
schema, base URL, and auth flow are gated behind a manual approval process
and not publicly documented. This adapter reserves the registry slot so
credentials can be stored and swapped in once MeWe publishes its API spec.
"""

import logging
from typing import Any, Dict, Optional

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

UNAVAILABLE_MSG = (
    "MeWe platform API is not publicly available — "
    "developer access is gated and endpoint docs are not published. "
    "Contact MeWe for API access."
)


class MeWeAdapter(BaseSocialAdapter):
    """Placeholder adapter for MeWe."""

    platform_name = "mewe"
    max_content_length = 5000
    supports_media = True

    def validate_credentials(self) -> None:
        """Require access_token so credentials can be persisted for later use."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Posting is not supported until MeWe publishes its write API."""
        logger.warning("MeWe post attempted but platform API is unavailable")
        raise APIError(UNAVAILABLE_MSG)

    def health_check(self) -> bool:
        """Always unhealthy — no endpoint to probe."""
        raise APIError(UNAVAILABLE_MSG)
