"""TikTok adapter for video posting via Content Posting API v2."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class TikTokAdapter(BaseSocialAdapter):
    """Publish videos to TikTok via the Content Posting API v2.

    Uses PULL_FROM_URL: TikTok fetches the video from a public URL.
    Posting is asynchronous — TikTok returns a publish_id and processes
    the upload through its own pipeline.
    """

    platform_name = "tiktok"
    max_content_length = 2200
    supports_media = True

    API_BASE = "https://open.tiktokapis.com/v2"

    def validate_credentials(self) -> None:
        """Ensure access_token is present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")

    def _headers(self) -> dict:
        """Bearer auth headers for TikTok Open API."""
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def _build_payload(self, content: str, media_url: str) -> dict:
        """Build the init upload payload (PULL_FROM_URL method)."""
        return {
            "post_info": {
                "title": content,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 0,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media_url,
            },
        }

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish a video to TikTok. media_url is required."""
        if not media_url:
            raise APIError("TikTok requires media_url for video posting")

        content = self.truncate_content(content)
        payload = self._build_payload(content, media_url)

        try:
            resp = httpx.post(
                f"{self.API_BASE}/post/publish/video/init/",
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"TikTok publish init failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"TikTok error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        publish_id = str(data.get("data", {}).get("publish_id", ""))
        return {
            "external_id": publish_id,
            "url": "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify token by fetching the authenticated user info."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/user/info/",
                params={"fields": "open_id,display_name"},
                headers={
                    "Authorization": f"Bearer {self.credentials['access_token']}",
                },
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("TikTok health check failed")
            return False
