"""YouTube adapter for video uploads via YouTube Data API v3."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
WATCH_URL = "https://www.youtube.com/watch?v="


class YouTubeAdapter(BaseSocialAdapter):
    """Upload videos to YouTube via the Data API v3."""

    platform_name = "youtube"
    max_content_length = 5000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure access_token and channel_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("channel_id"):
            raise ConfigurationError("channel_id is required")

    def _headers(self) -> dict:
        """Standard YouTube API headers with bearer token."""
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
        }

    def _build_metadata(self, content: str) -> dict:
        """First line becomes title; remainder becomes description."""
        lines = content.strip().split("\n", 1)
        title = (lines[0] or "Untitled")[:100]
        description = lines[1] if len(lines) > 1 else ""
        return {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        }

    def _download_video(self, media_url: str) -> bytes:
        """Download video bytes from a public URL."""
        try:
            resp = httpx.get(media_url, timeout=60, follow_redirects=True)
        except HTTPError as exc:
            raise APIError(f"Failed to download video: {exc}") from exc
        if resp.status_code >= 400:
            raise APIError(
                f"Video download failed: {resp.status_code}",
                status_code=resp.status_code,
            )
        return resp.content

    def _init_upload(self, metadata: dict) -> str:
        """Initiate a resumable upload and return the upload URL."""
        try:
            resp = httpx.post(
                UPLOAD_URL,
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                    "X-Upload-Content-Type": "video/*",
                },
                json=metadata,
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"YouTube upload init failed: {exc}") from exc
        if resp.status_code >= 400:
            raise APIError(
                f"YouTube error: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        upload_url = resp.headers.get("location") or resp.headers.get("Location")
        if not upload_url:
            raise APIError("YouTube did not return upload URL")
        return upload_url

    def _upload_bytes(self, upload_url: str, video_bytes: bytes) -> dict:
        """PUT video bytes to the resumable upload URL."""
        try:
            resp = httpx.put(
                upload_url,
                content=video_bytes,
                headers={"Content-Type": "video/*"},
                timeout=120,
            )
        except HTTPError as exc:
            raise APIError(f"YouTube upload failed: {exc}") from exc
        if resp.status_code >= 400:
            raise APIError(
                f"YouTube upload error: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return resp.json()

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a video to YouTube. media_url is required."""
        if not media_url:
            raise APIError("YouTube requires media_url for video upload")
        content = self.truncate_content(content)
        metadata = self._build_metadata(content)
        video_bytes = self._download_video(media_url)
        upload_url = self._init_upload(metadata)
        data = self._upload_bytes(upload_url, video_bytes)
        video_id = str(data.get("id", ""))
        return {
            "external_id": video_id,
            "url": f"{WATCH_URL}{video_id}" if video_id else "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify token by listing the user's channel."""
        try:
            resp = httpx.get(
                CHANNELS_URL,
                params={"part": "snippet", "mine": "true"},
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("YouTube health check failed")
            return False
