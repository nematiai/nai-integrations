"""Tests for the Discord social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.discord.adapter import DiscordAdapter

VALID_CREDS = {
    "webhook_url": "https://discord.com/api/webhooks/123/abc-token",
}


def _mock_response(
    status_code: int = 200,
    json_data: dict = None,
    text: str = "",
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid webhook_url should not raise."""
    adapter = DiscordAdapter(VALID_CREDS)
    assert adapter.credentials == VALID_CREDS


def test_validate_credentials_missing_url() -> None:
    """Missing webhook_url should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="webhook_url is required"):
        DiscordAdapter({})


def test_validate_credentials_invalid_url() -> None:
    """Non-Discord URL should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="webhook_url must start"):
        DiscordAdapter({"webhook_url": "https://example.com/hook"})


# --- post ---


@patch("apps.social.discord.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sends content JSON and returns external_id."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "987654321"},
    )
    adapter = DiscordAdapter(VALID_CREDS)

    result = adapter.post("Hello Discord")

    mock_httpx.post.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc-token?wait=true",
        json={"content": "Hello Discord"},
        timeout=10,
    )
    assert result["external_id"] == "987654321"


@patch("apps.social.discord.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url includes embeds with image."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "111222333"},
    )
    adapter = DiscordAdapter(VALID_CREDS)

    result = adapter.post("Caption", media_url="https://example.com/img.png")

    call_kwargs = mock_httpx.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["content"] == "Caption"
    assert payload["embeds"] == [{"image": {"url": "https://example.com/img.png"}}]
    assert result["external_id"] == "111222333"


@patch("apps.social.discord.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Discord returning 400+ should raise APIError."""
    mock_httpx.post.return_value = _mock_response(
        400,
        text="Bad Request",
    )
    adapter = DiscordAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Discord error"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.discord.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET webhook returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"name": "my-hook"})
    adapter = DiscordAdapter(VALID_CREDS)

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc-token",
        timeout=5,
    )


@patch("apps.social.discord.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable webhook returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = DiscordAdapter(VALID_CREDS)

    assert adapter.health_check() is False
