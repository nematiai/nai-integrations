"""Bluesky AT Protocol adapter for social posting."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

API_BASE = "https://bsky.social/xrpc"
REQUIRED_FIELDS = ("handle", "app_password")


class BlueskyAdapter(BaseSocialAdapter):
    """Post to Bluesky via AT Protocol using app password auth."""

    platform_name = "bluesky"
    max_content_length = 300
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure handle and app_password are present."""
        for field in REQUIRED_FIELDS:
            if not self.credentials.get(field):
                raise ConfigurationError(f"{field} is required")

    def _create_session(self) -> Dict[str, str]:
        """Authenticate via createSession, return accessJwt and did."""
        resp = httpx.post(
            f"{API_BASE}/com.atproto.server.createSession",
            json={
                "identifier": self.credentials["handle"],
                "password": self.credentials["app_password"],
            },
            timeout=10,
        )
        data = resp.json()
        if resp.status_code != 200 or "accessJwt" not in data:
            error = data.get("message", data.get("error", "unknown"))
            raise APIError(f"Bluesky auth failed: {error}")
        return {"accessJwt": data["accessJwt"], "did": data["did"]}

    def _auth_headers(self, token: str) -> Dict[str, str]:
        """Build Authorization header dict."""
        return {"Authorization": f"Bearer {token}"}

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a post on Bluesky."""
        content = self.truncate_content(content)
        try:
            session = self._create_session()
            return self._create_record(session, content, media_url)
        except HTTPError as exc:
            raise APIError(f"Bluesky API request failed: {exc}") from exc

    def _build_record(
        self,
        content: str,
        embed: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Build the app.bsky.feed.post record dict."""
        record: Dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": content,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        if embed:
            record["embed"] = embed
        return record

    def _create_record(
        self,
        session: Dict[str, str],
        content: str,
        media_url: Optional[str],
    ) -> Dict[str, Any]:
        """POST createRecord and return standard result dict."""
        token, did = session["accessJwt"], session["did"]
        embed = self._upload_media(token, media_url) if media_url else None
        record = self._build_record(content, embed)
        resp = httpx.post(
            f"{API_BASE}/com.atproto.repo.createRecord",
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            headers=self._auth_headers(token),
            timeout=10,
        )
        return self._parse_response(resp, did)

    def _parse_response(
        self,
        resp: httpx.Response,
        did: str,
    ) -> Dict[str, Any]:
        """Parse createRecord response into standard format."""
        data = resp.json()
        if resp.status_code != 200:
            error = data.get("message", data.get("error", "unknown"))
            raise APIError(
                f"Bluesky post failed: {error}",
                status_code=resp.status_code,
            )
        uri = data.get("uri", "")
        post_id = uri.rsplit("/", 1)[-1] if uri else ""
        url = f"https://bsky.app/profile/{did}/post/{post_id}" if post_id else ""
        return {"external_id": uri, "url": url, "raw": data}

    def _upload_media(
        self,
        token: str,
        media_url: str,
    ) -> Dict[str, Any]:
        """Download media from URL, upload as blob, return embed."""
        media_resp = httpx.get(media_url, timeout=30)
        if media_resp.status_code != 200:
            raise APIError(
                f"Failed to download media: {media_resp.status_code}",
            )
        content_type = media_resp.headers.get(
            "content-type",
            "image/jpeg",
        )
        blob_resp = httpx.post(
            f"{API_BASE}/com.atproto.repo.uploadBlob",
            content=media_resp.content,
            headers={
                **self._auth_headers(token),
                "Content-Type": content_type,
            },
            timeout=30,
        )
        blob_data = blob_resp.json()
        if blob_resp.status_code != 200 or "blob" not in blob_data:
            error = blob_data.get("message", "upload failed")
            raise APIError(f"Bluesky blob upload failed: {error}")
        return {
            "$type": "app.bsky.embed.images",
            "images": [{"alt": "", "image": blob_data["blob"]}],
        }

    def health_check(self) -> bool:
        """Verify credentials by creating a session."""
        try:
            self._create_session()
            return True
        except Exception:
            logger.exception("Bluesky health check failed")
            return False
