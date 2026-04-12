"""Tests for the Facebook social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.facebook.adapter import FacebookAdapter

VALID_CREDS = {
    "access_token": "EAAtest_token_123",
    "page_id": "123456789",
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
    """Valid access_token + page_id should not raise."""
    adapter = FacebookAdapter(VALID_CREDS.copy())
    assert adapter.credentials["page_id"] == "123456789"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        FacebookAdapter({"page_id": "123456789"})


def test_validate_credentials_missing_page_id() -> None:
    """Missing page_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="page_id is required"):
        FacebookAdapter({"access_token": "tok"})


# --- post ---


@patch("apps.social.facebook.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post goes to /{page_id}/feed."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "123456789_987654321"},
    )
    adapter = FacebookAdapter(VALID_CREDS.copy())

    result = adapter.post("Hello Facebook")

    mock_httpx.post.assert_called_once_with(
        "https://graph.facebook.com/v21.0/123456789/feed",
        params={"access_token": "EAAtest_token_123"},
        json={"message": "Hello Facebook"},
        timeout=15,
    )
    assert result["external_id"] == "123456789_987654321"
    assert result["url"] == "https://www.facebook.com/123456789_987654321"


@patch("apps.social.facebook.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url goes to /{page_id}/photos."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "photo_456"},
    )
    adapter = FacebookAdapter(VALID_CREDS.copy())

    result = adapter.post("Check this out", media_url="https://example.com/pic.jpg")

    mock_httpx.post.assert_called_once_with(
        "https://graph.facebook.com/v21.0/123456789/photos",
        params={
            "access_token": "EAAtest_token_123",
            "url": "https://example.com/pic.jpg",
            "caption": "Check this out",
        },
        timeout=15,
    )
    assert result["external_id"] == "photo_456"


@patch("apps.social.facebook.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Facebook returning 400 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(400, text="Bad Request")
    adapter = FacebookAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Facebook error"):
        adapter.post("fail")


@patch("apps.social.facebook.adapter.httpx")
def test_post_network_error(mock_httpx: MagicMock) -> None:
    """Network failure should raise APIError."""
    from httpx import HTTPError

    mock_httpx.post.side_effect = HTTPError("timeout")
    adapter = FacebookAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Facebook API request failed"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.facebook.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /{page_id} returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"id": "123", "name": "Page"})
    adapter = FacebookAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://graph.facebook.com/v21.0/123456789",
        params={"access_token": "EAAtest_token_123", "fields": "id,name"},
        timeout=5,
    )


@patch("apps.social.facebook.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = FacebookAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
