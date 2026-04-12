"""Skool adapter — placeholder until a public posting API is available.

Skool does not currently expose a public create-post endpoint. The third-party
docs.skoolapi.com project only covers read/session management. This adapter
holds the registry slot so credentials can be stored and validated, and will
be fleshed out once Skool ships a write API.
"""

import logging
from typing import Any, Dict, Optional

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

UNAVAILABLE_MSG = (
    "Skool platform API is not publicly available — "
    "no create-post endpoint has been published. "
    "Contact Skool for API access."
)


class SkoolAdapter(BaseSocialAdapter):
    """Placeholder adapter for Skool communities."""

    platform_name = "skool"
    max_content_length = 5000
    supports_media = True

    def validate_credentials(self) -> None:
        """Require api_key and community_id even though posting is stubbed.

        Stored credentials stay useful for when the adapter becomes functional.
        """
        if not self.credentials.get("api_key"):
            raise ConfigurationError("api_key is required")
        if not self.credentials.get("community_id"):
            raise ConfigurationError("community_id is required")

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Posting is not supported until Skool ships a public write API."""
        logger.warning("Skool post attempted but platform API is unavailable")
        raise APIError(UNAVAILABLE_MSG)

    def health_check(self) -> bool:
        """Always unhealthy — no endpoint to probe."""
        raise APIError(UNAVAILABLE_MSG)
