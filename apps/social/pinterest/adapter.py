"""Pinterest adapter for creating pins via API v5."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 100


class PinterestAdapter(BaseSocialAdapter):
    """Create pins on Pinterest boards via the v5 REST API."""

    platform_name = "pinterest"
    max_content_length = 500
    supports_media = True

    API_BASE = "https://api.pinterest.com/v5"

    def validate_credentials(self) -> None:
        """Ensure access_token and board_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("board_id"):
            raise ConfigurationError("board_id is required")

    def _headers(self) -> dict:
        """Authorization header for all API calls."""
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    def _extract_title(self, content: str) -> str:
        """Use the first line of content as title (max 100 chars)."""
        first_line = content.split("\n", 1)[0].strip()
        if len(first_line) > MAX_TITLE_LENGTH:
            return first_line[: MAX_TITLE_LENGTH - 3] + "..."
        return first_line

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a pin on the configured board."""
        content = self.truncate_content(content)
        payload: Dict[str, Any] = {
            "board_id": self.credentials["board_id"],
            "title": self._extract_title(content),
            "description": content,
        }

        if media_url:
            payload["media_source"] = {
                "source_type": "image_url",
                "url": media_url,
            }

        try:
            resp = httpx.post(
                f"{self.API_BASE}/pins",
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
        except HTTPError as exc:
            raise APIError(f"Pinterest API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"Pinterest error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        pin_id = str(data.get("id", ""))
        return {
            "external_id": pin_id,
            "url": f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify access token via user_account endpoint."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/user_account",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Pinterest health check failed")
            return False
