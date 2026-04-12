"""Tests for the Dribbble social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.dribbble.adapter import DribbbleAdapter

VALID_CREDS = {
    "access_token": "dribbble_test_token_123",
}


def _mock_response(
    status_code: int = 200,
    json_data: dict = None,
    text: str = "",
    content: bytes = b"img",
    headers: dict = None,
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.content = content
    resp.headers = headers or {}
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid access_token should not raise."""
    adapter = DribbbleAdapter(VALID_CREDS.copy())
    assert adapter.credentials["access_token"] == "dribbble_test_token_123"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        DribbbleAdapter({})


# --- post ---


def test_post_without_media_raises() -> None:
    """Posting without media_url should raise APIError."""
    adapter = DribbbleAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="Dribbble requires an image"):
        adapter.post("Just text")


@patch("apps.social.dribbble.adapter.httpx")
def test_post_with_media_success(mock_httpx: MagicMock) -> None:
    """Post with media downloads image, uploads shot, parses Location header."""
    download_resp = _mock_response(200, content=b"fake-image-bytes")
    shot_resp = _mock_response(
        202,
        headers={"Location": "https://api.dribbble.com/v2/shots/shot-789"},
    )
    mock_httpx.get.return_value = download_resp
    mock_httpx.post.return_value = shot_resp

    adapter = DribbbleAdapter(VALID_CREDS.copy())
    result = adapter.post(
        "My shot title\nFull description here",
        media_url="https://example.com/pic.png",
    )

    mock_httpx.get.assert_called_once_with(
        "https://example.com/pic.png",
        timeout=15,
        follow_redirects=True,
    )
    post_call = mock_httpx.post.call_args
    assert post_call.args[0] == "https://api.dribbble.com/v2/shots"
    assert post_call.kwargs["headers"] == {
        "Authorization": "Bearer dribbble_test_token_123"
    }
    assert post_call.kwargs["data"] == {
        "title": "My shot title",
        "description": "My shot title\nFull description here",
    }
    assert "image" in post_call.kwargs["files"]

    assert result["external_id"] == "shot-789"
    assert result["url"] == "https://api.dribbble.com/v2/shots/shot-789"
    assert result["raw"]["status_code"] == 202


@patch("apps.social.dribbble.adapter.httpx")
def test_post_title_truncation(mock_httpx: MagicMock) -> None:
    """Title longer than 150 chars should be truncated."""
    mock_httpx.get.return_value = _mock_response(200, content=b"img")
    mock_httpx.post.return_value = _mock_response(
        202,
        headers={"Location": "https://api.dribbble.com/v2/shots/shot-1"},
    )
    adapter = DribbbleAdapter(VALID_CREDS.copy())

    long_title = "A" * 200
    adapter.post(long_title, media_url="https://example.com/pic.png")

    data = mock_httpx.post.call_args.kwargs["data"]
    assert len(data["title"]) == 150
    assert data["title"].endswith("...")


@patch("apps.social.dribbble.adapter.httpx")
def test_post_image_download_failure(mock_httpx: MagicMock) -> None:
    """Image download failure should raise APIError."""
    mock_httpx.get.return_value = _mock_response(404, text="Not Found")
    adapter = DribbbleAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Failed to download image"):
        adapter.post("text", media_url="https://example.com/missing.png")


@patch("apps.social.dribbble.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Dribbble returning 401 should raise APIError."""
    mock_httpx.get.return_value = _mock_response(200, content=b"img")
    mock_httpx.post.return_value = _mock_response(401, text="Unauthorized")
    adapter = DribbbleAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Dribbble error"):
        adapter.post("text", media_url="https://example.com/pic.png")


# --- health_check ---


@patch("apps.social.dribbble.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /v2/user returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"id": 1, "name": "me"})
    adapter = DribbbleAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://api.dribbble.com/v2/user",
        headers={"Authorization": "Bearer dribbble_test_token_123"},
        timeout=5,
    )


@patch("apps.social.dribbble.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = DribbbleAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
