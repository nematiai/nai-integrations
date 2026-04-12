"""LinkedIn personal profile adapter for social posting."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


class LinkedInAdapter(BaseSocialAdapter):
    """Post to LinkedIn personal profiles via UGC Posts API."""

    platform_name = "linkedin"
    max_content_length = 3000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure access_token and person_urn are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        urn = self.credentials.get("person_urn", "")
        if not urn:
            raise ConfigurationError("person_urn is required")
        if not urn.startswith("urn:li:person:"):
            raise ConfigurationError("person_urn must start with 'urn:li:person:'")

    def _headers(self) -> dict:
        """Standard LinkedIn API headers."""
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _build_payload(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> dict:
        """Build UGC post payload."""
        share: Dict[str, Any] = {
            "shareCommentary": {"text": content},
            "shareMediaCategory": "NONE",
        }
        if media_url:
            share["shareMediaCategory"] = "ARTICLE"
            share["media"] = [
                {"status": "READY", "originalUrl": media_url},
            ]
        return {
            "author": self.credentials["person_urn"],
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share,
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
            },
        }

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a UGC post on the user's LinkedIn profile."""
        content = self.truncate_content(content)
        payload = self._build_payload(content, media_url)

        try:
            resp = httpx.post(
                UGC_URL,
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
        except HTTPError as exc:
            raise APIError(f"LinkedIn API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise APIError(
                f"LinkedIn error: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        post_id = str(data.get("id", ""))
        return {
            "external_id": post_id,
            "url": f"https://www.linkedin.com/feed/update/{post_id}",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify token by calling LinkedIn userinfo endpoint."""
        try:
            resp = httpx.get(
                USERINFO_URL,
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("LinkedIn health check failed")
            return False
