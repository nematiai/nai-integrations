"""Slack Incoming Webhook adapter for social posting."""

import logging
from typing import Any, Dict, Optional

from httpx import HTTPError
import httpx

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

WEBHOOK_PREFIX = "https://hooks.slack.com/"


class SlackAdapter(BaseSocialAdapter):
    """Post messages to Slack channels via Incoming Webhooks."""

    platform_name = "slack"
    max_content_length = 40000
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure webhook_url exists and points to Slack."""
        url = self.credentials.get("webhook_url", "")
        if not url:
            raise ConfigurationError("webhook_url is required")
        if not url.startswith(WEBHOOK_PREFIX):
            raise ConfigurationError(
                "webhook_url must start with https://hooks.slack.com/"
            )

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the configured Slack webhook."""
        content = self.truncate_content(content)
        payload = self._build_payload(content, media_url)
        try:
            resp = httpx.post(
                self.credentials["webhook_url"],
                json=payload,
                timeout=10,
            )
            return self._parse_response(resp)
        except HTTPError as exc:
            raise APIError(f"Slack API request failed: {exc}") from exc

    def _build_payload(
        self,
        content: str,
        media_url: Optional[str],
    ) -> Dict[str, Any]:
        """Build Slack webhook payload with optional Block Kit image."""
        if not media_url:
            return {"text": content}
        blocks: list[Dict[str, Any]] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": content}},
            {"type": "image", "image_url": media_url, "alt_text": "image"},
        ]
        return {"text": content, "blocks": blocks}

    def _parse_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Parse Slack webhook response (plain text 'ok' on success)."""
        body = resp.text.strip()
        if resp.status_code != 200 or body != "ok":
            raise APIError(
                f"Slack error: {body}",
                status_code=resp.status_code,
            )
        return {"external_id": "", "url": "", "raw": {"status": 200, "body": body}}

    def health_check(self) -> bool:
        """Validate webhook URL format (no GET endpoint for webhooks)."""
        try:
            url = self.credentials.get("webhook_url", "")
            return url.startswith(WEBHOOK_PREFIX)
        except Exception:
            logger.exception("Slack health check failed")
            return False
