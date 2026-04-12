"""X (Twitter) adapter for social posting via API v2 + OAuth 1.0a."""

import logging
from typing import Any, Dict, Optional

import httpx
from authlib.integrations.httpx_client import OAuth1Auth
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("api_key", "api_secret", "access_token", "access_token_secret")


class XAdapter(BaseSocialAdapter):
    """Post tweets via Twitter API v2 with OAuth 1.0a user-context auth."""

    platform_name = "x"
    max_content_length = 280
    supports_media = True

    API_BASE = "https://api.twitter.com/2"
    UPLOAD_BASE = "https://upload.twitter.com/1.1"

    def validate_credentials(self) -> None:
        """Ensure all four OAuth 1.0a credentials are present."""
        for field in _REQUIRED_FIELDS:
            if not self.credentials.get(field):
                raise ConfigurationError(f"{field} is required")

    def _auth(self) -> OAuth1Auth:
        """Build OAuth 1.0a auth object for httpx requests."""
        return OAuth1Auth(
            client_id=self.credentials["api_key"],
            client_secret=self.credentials["api_secret"],
            token=self.credentials["access_token"],
            token_secret=self.credentials["access_token_secret"],
        )

    def _upload_media(self, media_url: str) -> str:
        """Download remote media and upload to Twitter. Returns media_id."""
        dl = httpx.get(media_url, timeout=15, follow_redirects=True)
        if dl.status_code >= 400:
            raise APIError(f"Failed to download media: HTTP {dl.status_code}")

        resp = httpx.post(
            f"{self.UPLOAD_BASE}/media/upload.json",
            auth=self._auth(),
            files={"media": ("upload", dl.content, "application/octet-stream")},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise APIError(
                f"X media upload failed: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return str(resp.json()["media_id_string"])

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a tweet via Twitter API v2."""
        content = self.truncate_content(content)
        payload: Dict[str, Any] = {"text": content}

        if media_url:
            media_id = self._upload_media(media_url)
            payload["media"] = {"media_ids": [media_id]}

        try:
            resp = httpx.post(
                f"{self.API_BASE}/tweets",
                auth=self._auth(),
                json=payload,
                timeout=10,
            )
        except HTTPError as exc:
            raise APIError(f"X API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"X error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json().get("data", {})
        tweet_id = data.get("id", "")
        return {
            "external_id": str(tweet_id),
            "url": f"https://x.com/i/status/{tweet_id}",
            "raw": resp.json(),
        }

    def health_check(self) -> bool:
        """Verify credentials via GET /2/users/me."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/users/me",
                auth=self._auth(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("X health check failed")
            return False
