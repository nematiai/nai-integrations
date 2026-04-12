"""Tests for the YouTube social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.youtube.adapter import YouTubeAdapter

VALID_CREDS = {
    "access_token": "ya29.test_token",
    "channel_id": "UC_test_channel",
}


def _mock_response(
    status_code: int = 200,
    json_data: dict = None,
    text: str = "",
    headers: dict = None,
    content: bytes = b"",
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = headers or {}
    resp.content = content
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid access_token + channel_id should not raise."""
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    assert adapter.credentials["channel_id"] == "UC_test_channel"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        YouTubeAdapter({"channel_id": "UC_x"})


def test_validate_credentials_missing_channel_id() -> None:
    """Missing channel_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="channel_id is required"):
        YouTubeAdapter({"access_token": "tok"})


# --- post ---


@patch("apps.social.youtube.adapter.httpx")
def test_post_video_success(mock_httpx: MagicMock) -> None:
    """Resumable upload: download video, init upload, PUT bytes."""
    mock_httpx.get.return_value = _mock_response(200, content=b"VIDEO_BYTES")
    mock_httpx.post.return_value = _mock_response(
        200,
        headers={"location": "https://upload.example/abc"},
    )
    mock_httpx.put.return_value = _mock_response(200, {"id": "vid123"})

    adapter = YouTubeAdapter(VALID_CREDS.copy())
    result = adapter.post(
        "My Title\nDescription text",
        media_url="https://example.com/v.mp4",
    )

    assert result["external_id"] == "vid123"
    assert result["url"] == "https://www.youtube.com/watch?v=vid123"
    mock_httpx.get.assert_called_once_with(
        "https://example.com/v.mp4",
        timeout=60,
        follow_redirects=True,
    )
    mock_httpx.put.assert_called_once_with(
        "https://upload.example/abc",
        content=b"VIDEO_BYTES",
        headers={"Content-Type": "video/*"},
        timeout=120,
    )


def test_post_requires_media_url() -> None:
    """Text-only post should raise APIError (YouTube needs video)."""
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="requires media_url"):
        adapter.post("hello")


@patch("apps.social.youtube.adapter.httpx")
def test_post_download_failure(mock_httpx: MagicMock) -> None:
    """Failed video download should raise APIError."""
    mock_httpx.get.return_value = _mock_response(404, text="Not Found")
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="Video download failed"):
        adapter.post("title", media_url="https://example.com/x.mp4")


@patch("apps.social.youtube.adapter.httpx")
def test_post_init_failure(mock_httpx: MagicMock) -> None:
    """Failed resumable init should raise APIError."""
    mock_httpx.get.return_value = _mock_response(200, content=b"BYTES")
    mock_httpx.post.return_value = _mock_response(401, text="Unauthorized")
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="YouTube error"):
        adapter.post("t", media_url="https://example.com/x.mp4")


@patch("apps.social.youtube.adapter.httpx")
def test_post_no_upload_url(mock_httpx: MagicMock) -> None:
    """Init upload without Location header should raise."""
    mock_httpx.get.return_value = _mock_response(200, content=b"BYTES")
    mock_httpx.post.return_value = _mock_response(200, headers={})
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="did not return upload URL"):
        adapter.post("t", media_url="https://example.com/x.mp4")


@patch("apps.social.youtube.adapter.httpx")
def test_post_upload_bytes_failure(mock_httpx: MagicMock) -> None:
    """PUT failure on the upload URL should raise APIError."""
    mock_httpx.get.return_value = _mock_response(200, content=b"BYTES")
    mock_httpx.post.return_value = _mock_response(
        200,
        headers={"location": "https://upload.example/abc"},
    )
    mock_httpx.put.return_value = _mock_response(500, text="Server Error")
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="upload error"):
        adapter.post("t", media_url="https://example.com/x.mp4")


@patch("apps.social.youtube.adapter.httpx")
def test_post_init_network_error(mock_httpx: MagicMock) -> None:
    """Network failure during init should raise APIError."""
    from httpx import HTTPError

    mock_httpx.get.return_value = _mock_response(200, content=b"BYTES")
    mock_httpx.post.side_effect = HTTPError("timeout")
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="upload init failed"):
        adapter.post("t", media_url="https://example.com/x.mp4")


# --- health_check ---


@patch("apps.social.youtube.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /channels?mine=true returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"items": []})
    adapter = YouTubeAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true"},
        headers={"Authorization": "Bearer ya29.test_token"},
        timeout=5,
    )


@patch("apps.social.youtube.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("network down")
    adapter = YouTubeAdapter(VALID_CREDS.copy())
    assert adapter.health_check() is False
