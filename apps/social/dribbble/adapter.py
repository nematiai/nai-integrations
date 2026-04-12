"""Dribbble adapter for creating shots via API v2."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 150


class DribbbleAdapter(BaseSocialAdapter):
    """Create shots on Dribbble via the v2 REST API."""

    platform_name = "dribbble"
    max_content_length = 10000
    supports_media = True

    API_BASE = "https://api.dribbble.com/v2"

    def validate_credentials(self) -> None:
        """Ensure access_token is present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")

    def _headers(self) -> dict:
        """Authorization header for all API calls."""
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    def _extract_title(self, content: str) -> str:
        """Use the first line of content as title (max 150 chars)."""
        first_line = content.split("\n", 1)[0].strip()
        if len(first_line) > MAX_TITLE_LENGTH:
            return first_line[: MAX_TITLE_LENGTH - 3] + "..."
        return first_line

    def _download_image(self, media_url: str) -> bytes:
        """Download remote image bytes for upload."""
        dl = httpx.get(media_url, timeout=15, follow_redirects=True)
        if dl.status_code >= 400:
            raise APIError(f"Failed to download image: HTTP {dl.status_code}")
        return dl.content

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a shot on Dribbble. An image is required."""
        if not media_url:
            raise APIError("Dribbble requires an image")

        content = self.truncate_content(content)
        image_bytes = self._download_image(media_url)

        data = {
            "title": self._extract_title(content),
            "description": content,
        }
        files = {"image": ("upload", image_bytes, "application/octet-stream")}

        try:
            resp = httpx.post(
                f"{self.API_BASE}/shots",
                headers=self._headers(),
                data=data,
                files=files,
                timeout=30,
            )
        except HTTPError as exc:
            raise APIError(f"Dribbble API request failed: {exc}") from exc

        if resp.status_code not in (200, 201, 202):
            raise APIError(
                f"Dribbble error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        location = resp.headers.get("Location", "")
        shot_id = location.rstrip("/").rsplit("/", 1)[-1] if location else ""
        return {
            "external_id": shot_id,
            "url": location,
            "raw": {"location": location, "status_code": resp.status_code},
        }

    def health_check(self) -> bool:
        """Verify access token via /v2/user endpoint."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/user",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Dribbble health check failed")
            return False
