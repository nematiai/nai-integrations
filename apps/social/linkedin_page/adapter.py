"""LinkedIn company page adapter for social posting."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
ORG_URL = "https://api.linkedin.com/v2/organizationalEntityAcls"


class LinkedInPageAdapter(BaseSocialAdapter):
    """Post to LinkedIn company pages via UGC Posts API."""

    platform_name = "linkedin_page"
    max_content_length = 3000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure access_token and organization_urn are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        urn = self.credentials.get("organization_urn", "")
        if not urn:
            raise ConfigurationError("organization_urn is required")
        if not urn.startswith("urn:li:organization:"):
            raise ConfigurationError(
                "organization_urn must start with 'urn:li:organization:'"
            )

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
        """Build UGC post payload for organization."""
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
            "author": self.credentials["organization_urn"],
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
        """Create a UGC post on the LinkedIn company page."""
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
            raise APIError(
                f"LinkedIn Page API request failed: {exc}",
            ) from exc

        if resp.status_code >= 400:
            raise APIError(
                f"LinkedIn Page error: {resp.text[:200]}",
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
        """Verify token by checking org admin access."""
        try:
            resp = httpx.get(
                ORG_URL,
                headers=self._headers(),
                params={"q": "roleAssignee", "projection": "(elements)"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("LinkedIn Page health check failed")
            return False
