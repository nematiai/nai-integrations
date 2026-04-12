"""Whop adapter for creating forum posts via the REST API v1."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 200


class WhopAdapter(BaseSocialAdapter):
    """Create forum posts on Whop via the public REST API."""

    platform_name = "whop"
    max_content_length = 5000
    supports_media = True

    API_BASE = "https://api.whop.com/api/v1"

    def validate_credentials(self) -> None:
        """Ensure api_key and forum_id (experience_id) are present."""
        if not self.credentials.get("api_key"):
            raise ConfigurationError("api_key is required")
        if not self.credentials.get("forum_id"):
            raise ConfigurationError("forum_id is required")

    def _headers(self) -> dict:
        """Bearer auth + JSON content type for all API calls."""
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    def _extract_title(self, content: str) -> str:
        """Use the first line of content as post title."""
        first_line = content.split("\n", 1)[0].strip()
        if len(first_line) > MAX_TITLE_LENGTH:
            return first_line[: MAX_TITLE_LENGTH - 3] + "..."
        return first_line

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a forum post in the configured experience."""
        content = self.truncate_content(content)
        payload: Dict[str, Any] = {
            "experience_id": self.credentials["forum_id"],
            "title": self._extract_title(content),
            "content": content,
        }
        if media_url:
            payload["attachments"] = [{"url": media_url}]

        try:
            resp = httpx.post(
                f"{self.API_BASE}/forum_posts",
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"Whop API request failed: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise APIError(
                f"Whop error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        post_id = str(data.get("id", ""))
        return {
            "external_id": post_id,
            "url": data.get("url", ""),
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify API key by listing forum posts in the configured experience."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/forum_posts",
                headers=self._headers(),
                params={"experience_id": self.credentials["forum_id"]},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Whop health check failed")
            return False
