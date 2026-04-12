"""Discord Webhook adapter for social posting."""

import logging
from typing import Any, Dict, Optional

from httpx import HTTPError
import httpx

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

WEBHOOK_PREFIX = "https://discord.com/api/webhooks/"


class DiscordAdapter(BaseSocialAdapter):
    """Post messages to Discord channels via Webhook API."""

    platform_name = "discord"
    max_content_length = 2000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure webhook_url exists and points to Discord."""
        url = self.credentials.get("webhook_url", "")
        if not url:
            raise ConfigurationError("webhook_url is required")
        if not url.startswith(WEBHOOK_PREFIX):
            raise ConfigurationError(
                "webhook_url must start with https://discord.com/api/webhooks/"
            )

    def _webhook_url(self, wait: bool = False) -> str:
        """Return the webhook URL, optionally with ?wait=true."""
        url = self.credentials["webhook_url"]
        if wait:
            return f"{url}?wait=true"
        return url

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the configured webhook."""
        content = self.truncate_content(content)
        payload: Dict[str, Any] = {"content": content}
        if media_url:
            payload["embeds"] = [{"image": {"url": media_url}}]
        try:
            resp = httpx.post(
                self._webhook_url(wait=True),
                json=payload,
                timeout=10,
            )
            return self._parse_response(resp)
        except HTTPError as exc:
            raise APIError(f"Discord API request failed: {exc}") from exc

    def _parse_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Parse Discord webhook response (?wait=true returns JSON)."""
        if resp.status_code == 204:
            return {"external_id": "", "url": "", "raw": {"status": 204}}
        if resp.status_code >= 400:
            detail = resp.text[:200]
            raise APIError(
                f"Discord error: {detail}",
                status_code=resp.status_code,
            )
        data = resp.json()
        msg_id = str(data.get("id", ""))
        return {"external_id": msg_id, "url": "", "raw": data}

    def health_check(self) -> bool:
        """GET the webhook URL — returns webhook info if valid."""
        try:
            resp = httpx.get(self.credentials["webhook_url"], timeout=5)
            return resp.status_code == 200
        except Exception:
            logger.exception("Discord health check failed")
            return False
