"""Threads adapter for publishing via Threads API v1.0."""

import logging
from typing import Any, Dict, Optional

import httpx
from httpx import HTTPError

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)


class ThreadsAdapter(BaseSocialAdapter):
    """Publish to Threads via the Threads API.

    Uses the two-step container workflow: create thread container, then publish.
    """

    platform_name = "threads"
    max_content_length = 500
    supports_media = True

    API_BASE = "https://graph.threads.net/v1.0"

    def validate_credentials(self) -> None:
        """Ensure access_token and threads_user_id are present."""
        if not self.credentials.get("access_token"):
            raise ConfigurationError("access_token is required")
        if not self.credentials.get("threads_user_id"):
            raise ConfigurationError("threads_user_id is required")

    def _params(self) -> dict:
        """Base query params with access token."""
        return {"access_token": self.credentials["access_token"]}

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create and publish a Threads post."""
        content = self.truncate_content(content)
        user_id = self.credentials["threads_user_id"]

        container_payload: Dict[str, str] = {"text": content}
        if media_url:
            container_payload["media_type"] = "IMAGE"
            container_payload["image_url"] = media_url
        else:
            container_payload["media_type"] = "TEXT"

        try:
            container_resp = httpx.post(
                f"{self.API_BASE}/{user_id}/threads",
                params=self._params(),
                json=container_payload,
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"Threads container creation failed: {exc}") from exc

        if container_resp.status_code >= 400:
            raise APIError(
                f"Threads container error: {container_resp.text[:200]}",
                status_code=container_resp.status_code,
            )

        creation_id = container_resp.json().get("id")
        if not creation_id:
            raise APIError("Threads returned no container id")

        try:
            publish_resp = httpx.post(
                f"{self.API_BASE}/{user_id}/threads_publish",
                params=self._params(),
                json={"creation_id": creation_id},
                timeout=15,
            )
        except HTTPError as exc:
            raise APIError(f"Threads publish failed: {exc}") from exc

        if publish_resp.status_code >= 400:
            raise APIError(
                f"Threads publish error: {publish_resp.text[:200]}",
                status_code=publish_resp.status_code,
            )

        data = publish_resp.json()
        thread_id = str(data.get("id", ""))
        return {
            "external_id": thread_id,
            "url": "",
            "raw": data,
        }

    def health_check(self) -> bool:
        """Check Threads publishing limit to verify access."""
        try:
            resp = httpx.get(
                f"{self.API_BASE}/{self.credentials['threads_user_id']}/threads_publishing_limit",
                params=self._params(),
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Threads health check failed")
            return False
