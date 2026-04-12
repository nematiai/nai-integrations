"""Telegram Bot API adapter for social posting."""

import logging
from typing import Any, Dict, Optional

from httpx import HTTPError
import httpx

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.base.adapter import BaseSocialAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org/bot{token}"


class TelegramAdapter(BaseSocialAdapter):
    """Post messages to Telegram channels/groups via Bot API."""

    platform_name = "telegram"
    max_content_length = 4096
    supports_media = True

    def validate_credentials(self) -> None:
        """Ensure bot_token and chat_id are present."""
        if not self.credentials.get("bot_token"):
            raise ConfigurationError("bot_token is required")
        if not self.credentials.get("chat_id"):
            raise ConfigurationError("chat_id is required")

    def _api_url(self, method: str) -> str:
        """Build Telegram Bot API URL for the given method."""
        base = BASE_URL.format(token=self.credentials["bot_token"])
        return f"{base}/{method}"

    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message or photo to the configured chat."""
        content = self.truncate_content(content)
        chat_id = self.credentials["chat_id"]
        try:
            if media_url:
                return self._send_photo(chat_id, content, media_url)
            return self._send_message(chat_id, content)
        except HTTPError as exc:
            raise APIError(f"Telegram API request failed: {exc}") from exc

    def _send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a text message via sendMessage."""
        resp = httpx.post(
            self._api_url("sendMessage"),
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return self._parse_response(resp)

    def _send_photo(
        self,
        chat_id: str,
        caption: str,
        photo_url: str,
    ) -> Dict[str, Any]:
        """Send a photo with caption via sendPhoto."""
        resp = httpx.post(
            self._api_url("sendPhoto"),
            json={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
            },
            timeout=10,
        )
        return self._parse_response(resp)

    def _parse_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Parse Telegram API response into standard format."""
        data = resp.json()
        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise APIError(f"Telegram error: {desc}", status_code=resp.status_code)
        result = data.get("result", {})
        msg_id = str(result.get("message_id", ""))
        return {"external_id": msg_id, "url": "", "raw": data}

    def health_check(self) -> bool:
        """Verify bot token by calling getMe."""
        try:
            resp = httpx.post(self._api_url("getMe"), timeout=5)
            data = resp.json()
            return bool(data.get("ok"))
        except Exception:
            logger.exception("Telegram health check failed")
            return False
