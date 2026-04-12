"""Mastodon adapter for social posting."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class MastodonAdapter(BaseSocialAdapter):
    """Post statuses to Mastodon instances via REST API."""

    platform_name = "mastodon"
    max_content_length = 500
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure instance_url and access_token are present."""
        url = self.credentials.get("instance_url", "")
        if not url:
            raise ConfigurationError("instance_url is required")
        if not url.startswith("https://"):
            raise ConfigurationError("instance_url must start with https://")
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        # Normalise: strip trailing slash
        self.credentials["instance_url"] = url.rstrip("/")

    def _headers(self) -> dict:
        """Authorization header for all API calls."""
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    def _upload_media(self, media_url: str) -> str:
        """Download remote media and upload to Mastodon. Returns media id."""
        dl = httpx.get(media_url, timeout=15, follow_redirects=True)
        if dl.status_code >= 400:
            raise APIError(f"Failed to download media: HTTP {dl.status_code}")

        base = self.credentials["instance_url"]
        resp = httpx.post(
            f"{base}/api/v2/media",
            headers=self._headers(),
            files={"file": ("upload", dl.content, "application/octet-stream")},
            timeout=30,
        )
        if resp.status_code not in (200, 202):
            raise APIError(
                f"Mastodon media upload failed: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return str(resp.json()["id"])

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new status on the configured Mastodon instance."""
        content = self.truncate_content(content)
        payload: Dict[str, Any] = {"status": content}

        if media_url:
            payload["media_ids"] = [self._upload_media(media_url)]

        try:
            base = self.credentials["instance_url"]
            resp = httpx.post(
                f"{base}/api/v1/statuses",
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
        except HTTPError as exc:
            raise APIError(f"Mastodon API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"Mastodon error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        return {
            "external_id": str(data.get("id", "")),
            "url": data.get("url", ""),
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify credentials against the instance."""
        try:
            base = self.credentials["instance_url"]
            resp = httpx.get(
                f"{base}/api/v1/accounts/verify_credentials",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Mastodon health check failed")
            return False
