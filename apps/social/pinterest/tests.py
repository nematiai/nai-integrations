"""Tests for the Pinterest social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.pinterest.adapter import PinterestAdapter

VALID_CREDS = {
    "access_token": "pina_test_token_123",
    "board_id": "board-456",
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
    """Valid access_token + board_id should not raise."""
    adapter = PinterestAdapter(VALID_CREDS.copy())
    assert adapter.credentials["board_id"] == "board-456"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        PinterestAdapter({"board_id": "board-456"})


def test_validate_credentials_missing_board_id() -> None:
    """Missing board_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="board_id is required"):
        PinterestAdapter({"access_token": "tok"})


# --- post ---


@patch("apps.social.pinterest.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url creates a pin with image_url media_source."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "pin-789"},
    )
    adapter = PinterestAdapter(VALID_CREDS.copy())

    result = adapter.post(
        "My pin title\nSome description", media_url="https://example.com/pic.jpg"
    )

    mock_httpx.post.assert_called_once_with(
        "https://api.pinterest.com/v5/pins",
        headers={"Authorization": "Bearer pina_test_token_123"},
        json={
            "board_id": "board-456",
            "title": "My pin title",
            "description": "My pin title\nSome description",
            "media_source": {
                "source_type": "image_url",
                "url": "https://example.com/pic.jpg",
            },
        },
        timeout=10,
    )
    assert result["external_id"] == "pin-789"
    assert result["url"] == "https://www.pinterest.com/pin/pin-789/"


@patch("apps.social.pinterest.adapter.httpx")
def test_post_without_media(mock_httpx: MagicMock) -> None:
    """Post without media_url creates a pin with no media_source."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "pin-100"},
    )
    adapter = PinterestAdapter(VALID_CREDS.copy())

    result = adapter.post("Text only pin")

    call_kwargs = mock_httpx.post.call_args.kwargs
    assert "media_source" not in call_kwargs["json"]
    assert result["external_id"] == "pin-100"


@patch("apps.social.pinterest.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Pinterest returning 403 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(403, text="Forbidden")
    adapter = PinterestAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Pinterest error"):
        adapter.post("fail")


@patch("apps.social.pinterest.adapter.httpx")
def test_post_title_truncation(mock_httpx: MagicMock) -> None:
    """Title longer than 100 chars should be truncated."""
    mock_httpx.post.return_value = _mock_response(200, {"id": "pin-200"})
    adapter = PinterestAdapter(VALID_CREDS.copy())

    long_title = "A" * 120
    adapter.post(long_title)

    call_kwargs = mock_httpx.post.call_args.kwargs
    title = call_kwargs["json"]["title"]
    assert len(title) == 100
    assert title.endswith("...")


# --- health_check ---


@patch("apps.social.pinterest.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET user_account returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"username": "testuser"})
    adapter = PinterestAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://api.pinterest.com/v5/user_account",
        headers={"Authorization": "Bearer pina_test_token_123"},
        timeout=5,
    )


@patch("apps.social.pinterest.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = PinterestAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
