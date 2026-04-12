"""Instagram Business adapter for publishing via Graph API v21.0."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class InstagramAdapter(BaseSocialAdapter):
    """Publish to Instagram Business accounts via the Graph API.

    Uses the two-step container workflow: create media container, then publish.
    """

    platform_name = "instagram"
    max_content_length = 2200
    supports_media = True

    API_BASE = "https://graph.facebook.com/v21.0"

    def validate_credentials(self) -> None:
        """Ensure access_token and instagram_account_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("instagram_account_id"):
            raise ConfigurationError("instagram_account_id is required")

    def _params(self) -> dict:
        """Base query params with access token."""
        return {"access_token": self.credentials["access_token"]}

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create and publish an Instagram media container.

        Instagram requires a media_url — raises APIError without one.
        """
        if not media_url:
            raise APIError("Instagram requires media_url for posting")

        content = self.truncate_content(content)
        ig_id = self.credentials["instagram_account_id"]

        try:
            container_resp = httpx.post(
                f"{self.API_BASE}/{ig_id}/media",
                params=self._params(),
                json={"image_url": media_url, "caption": content},
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"Instagram container creation failed: {exc}") from exc

        if container_resp.status_code >= 400:
            raise APIError(
                f"Instagram container error: {container_resp.text[:200]}",
                status_code=container_resp.status_code,
            )

        creation_id = container_resp.json().get("id")
        if not creation_id:
            raise APIError("Instagram returned no container id")

        try:
            publish_resp = httpx.post(
                f"{self.API_BASE}/{ig_id}/media_publish",
                params=self._params(),
                json={"creation_id": creation_id},
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"Instagram publish failed: {exc}") from exc

        if publish_resp.status_code >= 400:
            raise APIError(
                f"Instagram publish error: {publish_resp.text[:200]}",
                status_code=publish_resp.status_code,
            )

        data = publish_resp.json()
        media_id = str(data.get("id", ""))
        return {
            "external_id": media_id,
            "url": f"https://www.instagram.com/p/{media_id}/" if media_id else "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify Instagram account access."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/{self.credentials['instagram_account_id']}",
                params={**self._params(), "fields": "id,username"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Instagram health check failed")
            return False
