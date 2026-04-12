"""Tests for the Telegram social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.telegram.adapter import TelegramAdapter

VALID_CREDS = {"bot_token": "123:ABC", "chat_id": "-1001234"}


def _mock_response(ok: bool, result: dict = None, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"ok": ok, "result": result or {}}
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid credentials should not raise."""
    with patch("apps.social.telegram.adapter.httpx"):
        adapter = TelegramAdapter(VALID_CREDS)
    assert adapter.credentials == VALID_CREDS


def test_validate_credentials_missing_token() -> None:
    """Missing bot_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="bot_token"):
        TelegramAdapter({"chat_id": "-1001234"})


def test_validate_credentials_missing_chat_id() -> None:
    """Missing chat_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="chat_id"):
        TelegramAdapter({"bot_token": "123:ABC"})


# --- post ---


@patch("apps.social.telegram.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post calls sendMessage and returns external_id."""
    mock_httpx.post.return_value = _mock_response(True, {"message_id": 42})
    adapter = TelegramAdapter(VALID_CREDS)

    result = adapter.post("Hello Telegram")

    mock_httpx.post.assert_called_with(
        "https://api.telegram.org/bot123:ABC/sendMessage",
        json={"chat_id": "-1001234", "text": "Hello Telegram"},
        timeout=10,
    )
    assert result["external_id"] == "42"


@patch("apps.social.telegram.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url calls sendPhoto."""
    mock_httpx.post.return_value = _mock_response(True, {"message_id": 99})
    adapter = TelegramAdapter(VALID_CREDS)

    result = adapter.post("Caption", media_url="https://example.com/pic.jpg")

    mock_httpx.post.assert_called_with(
        "https://api.telegram.org/bot123:ABC/sendPhoto",
        json={
            "chat_id": "-1001234",
            "photo": "https://example.com/pic.jpg",
            "caption": "Caption",
        },
        timeout=10,
    )
    assert result["external_id"] == "99"


@patch("apps.social.telegram.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Telegram returning ok=false should raise APIError."""
    mock_httpx.post.return_value = _mock_response(False, status_code=400)
    adapter = TelegramAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Telegram error"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.telegram.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """Healthy bot returns True."""
    mock_httpx.post.return_value = _mock_response(True, {"id": 1, "is_bot": True})
    adapter = TelegramAdapter(VALID_CREDS)

    assert adapter.health_check() is True


@patch("apps.social.telegram.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.post.side_effect = Exception("connection refused")
    adapter = TelegramAdapter(VALID_CREDS)

    assert adapter.health_check() is False
