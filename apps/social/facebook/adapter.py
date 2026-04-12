"""Facebook Pages adapter for posting via Graph API v21.0."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class FacebookAdapter(BaseSocialAdapter):
    """Post to Facebook Pages via the Graph API."""

    platform_name = "facebook"
    max_content_length = 63206
    supports_media = True

    API_BASE = "https://graph.facebook.com/v21.0"

    def validate_credentials(self) -> None:
        """Ensure access_token and page_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("page_id"):
            raise ConfigurationError("page_id is required")

    def _params(self) -> dict:
        """Base query params with access token."""
        return {"access_token": self.credentials["access_token"]}

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post to a Facebook Page feed, optionally with a photo."""
        content = self.truncate_content(content)
        page_id = self.credentials["page_id"]

        try:
            if media_url:
                resp = httpx.post(
                    f"{self.API_BASE}/{page_id}/photos",
                    params={**self._params(), "url": media_url, "caption": content},
                    timeout=15,
                )
            else:
                resp = httpx.post(
                    f"{self.API_BASE}/{page_id}/feed",
                    params=self._params(),
                    json={"message": content},
                    timeout=15,
                )
        except HTTPError as exc:
            raise APIError(f"Facebook API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"Facebook error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        post_id = str(data.get("id", ""))
        return {
            "external_id": post_id,
            "url": f"https://www.facebook.com/{post_id}" if post_id else "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify page access via Graph API."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/{self.credentials['page_id']}",
                params={**self._params(), "fields": "id,name"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Facebook health check failed")
            return False
