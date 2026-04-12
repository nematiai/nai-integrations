"""Reddit API adapter for social posting via OAuth2 script app."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
REQUIRED_FIELDS = ("client_id", "client_secret", "username", "password", "subreddit")


class RedditAdapter(BaseSocialAdapter):
    """Post to Reddit subreddits via OAuth2 script-app credentials."""

    platform_name = "reddit"
    max_content_length = 40000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure all five required credential fields are present."""
        for field in REQUIRED_FIELDS:
            if not self.credentials.get(field):
                raise ConfigurationError(f"{field} is required")

    def _user_agent(self) -> str:
        username = self.credentials["username"]
        return f"NEMI/1.0 (by /u/{username})"

    def _get_access_token(self) -> str:
        """Obtain a bearer token via Reddit OAuth2 password grant."""
        resp = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "username": self.credentials["username"],
                "password": self.credentials["password"],
            },
            auth=(self.credentials["client_id"], self.credentials["client_secret"]),
            headers={"User-Agent": self._user_agent()},
            timeout=10,
        )
        data = resp.json()
        token = data.get("access_token")
        if not token:
            error = data.get("error", "unknown")
            raise APIError(f"Reddit token error: {error}")
        return token

    def _extract_title(self, content: str) -> str:
        """Use first line of content as title, max 300 chars."""
        first_line = content.split("\n", 1)[0].strip()
        return first_line[:300] if first_line else "Post via NEMI"

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a text or link post to the configured subreddit."""
        content = self.truncate_content(content)
        try:
            token = self._get_access_token()
            return self._submit(token, content, media_url)
        except HTTPError as exc:
            raise APIError(f"Reddit API request failed: {exc}") from exc

    def _submit(
        self,
        token: str,
        content: str,
        media_url: Optional[str],
    ) -> Dict[str, Any]:
        """POST to /api/submit and parse the response."""
        title = self._extract_title(content)
        payload: Dict[str, str] = {
            "sr": self.credentials["subreddit"],
            "title": title,
            "resubmit": "true",
        }
        if media_url:
            payload.update(kind="link", url=media_url)
        else:
            payload.update(kind="self", text=content)

        resp = httpx.post(
            f"{API_BASE}/api/submit",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self._user_agent(),
            },
            timeout=10,
        )
        return self._parse_response(resp)

    def _parse_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Parse Reddit submit response into standard format."""
        data = resp.json()
        inner = data.get("json", {})
        errors = inner.get("errors", [])
        if errors:
            raise APIError(
                f"Reddit submit error: {errors}",
                status_code=resp.status_code,
            )
        result = inner.get("data", {})
        return {
            "external_id": result.get("name", ""),
            "url": result.get("url", ""),
            "raw": data,
        }

    def health_check(self) -> bool:
        """Verify credentials by calling /api/v1/me."""
        try:
            token = self._get_access_token()
            resp = httpx.get(
                f"{API_BASE}/api/v1/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self._user_agent(),
                },
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Reddit health check failed")
            return False
