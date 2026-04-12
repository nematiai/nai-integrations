"""Tests for the TikTok social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.tiktok.adapter import TikTokAdapter

VALID_CREDS = {"access_token": "tt.test_token"}


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
    """Valid access_token should not raise."""
    adapter = TikTokAdapter(VALID_CREDS.copy())
    assert adapter.credentials["access_token"] == "tt.test_token"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        TikTokAdapter({})


# --- post ---


@patch("apps.social.tiktok.adapter.httpx")
def test_post_video_success(mock_httpx: MagicMock) -> None:
    """PULL_FROM_URL init should return publish_id."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"data": {"publish_id": "pub_abc123"}},
    )

    adapter = TikTokAdapter(VALID_CREDS.copy())
    result = adapter.post(
        "My TikTok caption",
        media_url="https://example.com/video.mp4",
    )

    assert result["external_id"] == "pub_abc123"
    assert result["url"] == ""
    assert result["raw"] == {"data": {"publish_id": "pub_abc123"}}

    call = mock_httpx.post.call_args
    assert call.args[0] == ("https://open.tiktokapis.com/v2/post/publish/video/init/")
    payload = call.kwargs["json"]
    assert payload["post_info"]["title"] == "My TikTok caption"
    assert payload["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
    assert payload["source_info"]["source"] == "PULL_FROM_URL"
    assert payload["source_info"]["video_url"] == "https://example.com/video.mp4"
    assert call.kwargs["headers"]["Authorization"] == "Bearer tt.test_token"


def test_post_requires_media_url() -> None:
    """Text-only post should raise APIError (TikTok needs video)."""
    adapter = TikTokAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="requires media_url"):
        adapter.post("hello")


@patch("apps.social.tiktok.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """API 4xx response should raise APIError with status code."""
    mock_httpx.post.return_value = _mock_response(401, text="Unauthorized")
    adapter = TikTokAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="TikTok error"):
        adapter.post("t", media_url="https://example.com/v.mp4")


@patch("apps.social.tiktok.adapter.httpx")
def test_post_network_error(mock_httpx: MagicMock) -> None:
    """Network failure during init should raise APIError."""
    from httpx import HTTPError

    mock_httpx.post.side_effect = HTTPError("connection refused")
    adapter = TikTokAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="publish init failed"):
        adapter.post("t", media_url="https://example.com/v.mp4")


@patch("apps.social.tiktok.adapter.httpx")
def test_post_truncates_long_caption(mock_httpx: MagicMock) -> None:
    """Captions longer than 2200 chars should be truncated."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"data": {"publish_id": "pub_x"}},
    )
    adapter = TikTokAdapter(VALID_CREDS.copy())
    long_caption = "a" * 3000
    adapter.post(long_caption, media_url="https://example.com/v.mp4")

    sent_title = mock_httpx.post.call_args.kwargs["json"]["post_info"]["title"]
    assert len(sent_title) == 2200
    assert sent_title.endswith("...")


# --- health_check ---


@patch("apps.social.tiktok.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /user/info/ returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"data": {"user": {}}})
    adapter = TikTokAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://open.tiktokapis.com/v2/user/info/",
        params={"fields": "open_id,display_name"},
        headers={"Authorization": "Bearer tt.test_token"},
        timeout=5,
    )


@patch("apps.social.tiktok.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("network down")
    adapter = TikTokAdapter(VALID_CREDS.copy())
    assert adapter.health_check() is False
