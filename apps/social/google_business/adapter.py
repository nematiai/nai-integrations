"""Google Business Profile adapter for creating local posts via v4 API."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class GoogleBusinessAdapter(BaseSocialAdapter):
    """Post local updates to a Google Business Profile location."""

    platform_name = "google_business"
    max_content_length = 1500
    supports_media = True

    API_BASE = "https://mybusiness.googleapis.com/v4"

    def validate_credentials(self) -> None:
        """Ensure access_token, account_id, and location_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("account_id"):
            raise ConfigurationError("account_id is required")
        if not self.credentials.get("location_id"):
            raise ConfigurationError("location_id is required")

    def _headers(self) -> dict:
        """Standard API headers with bearer token."""
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    def _location_path(self) -> str:
        """Build the fully-qualified location path used in endpoints."""
        return (
            f"accounts/{self.credentials['account_id']}"
            f"/locations/{self.credentials['location_id']}"
        )

    def _build_body(self, content: str, media_url: Optional[str]) -> dict:
        """Build the localPosts request body."""
        body: dict = {
            "languageCode": "en",
            "summary": content,
            "topicType": "STANDARD",
        }
        if media_url:
            body["media"] = [
                {"mediaFormat": "PHOTO", "sourceUrl": media_url},
            ]
        return body

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a local post on the configured Business Profile location."""
        content = self.truncate_content(content)
        url = f"{self.API_BASE}/{self._location_path()}/localPosts"
        body = self._build_body(content, media_url)

        try:
            resp = httpx.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(
                f"Google Business API request failed: {exc}",
            ) from exc

        if resp.status_code >= 400:
            raise APIError(
                f"Google Business error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        name = str(data.get("name", ""))
        return {
            "external_id": name,
            "url": "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify location access via GET /accounts/.../locations/...."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/{self._location_path()}",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Google Business health check failed")
            return False
