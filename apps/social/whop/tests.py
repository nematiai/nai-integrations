"""Tests for the Whop social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.whop.adapter import WhopAdapter

VALID_CREDS = {
    "api_key": "whop_test_key_abc",
    "forum_id": "exp_test_123",
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
    """Valid api_key and forum_id should not raise."""
    adapter = WhopAdapter(VALID_CREDS.copy())
    assert adapter.credentials["api_key"] == "whop_test_key_abc"
    assert adapter.credentials["forum_id"] == "exp_test_123"


def test_validate_credentials_missing_api_key() -> None:
    """Missing api_key should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="api_key is required"):
        WhopAdapter({"forum_id": "exp_test_123"})


def test_validate_credentials_missing_forum_id() -> None:
    """Missing forum_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="forum_id is required"):
        WhopAdapter({"api_key": "whop_test_key_abc"})


# --- post ---


@patch("apps.social.whop.adapter.httpx")
def test_post_text_success(mock_httpx: MagicMock) -> None:
    """Text-only post should hit /forum_posts and return parsed id/url."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {
            "id": "post_42",
            "url": "https://whop.com/exp_test_123/post_42",
        },
    )
    adapter = WhopAdapter(VALID_CREDS.copy())

    result = adapter.post("Weekly Update\nFull body here")

    call = mock_httpx.post.call_args
    assert call.args[0] == "https://api.whop.com/api/v1/forum_posts"
    assert call.kwargs["headers"] == {
        "Authorization": "Bearer whop_test_key_abc",
        "Content-Type": "application/json",
    }
    assert call.kwargs["json"] == {
        "experience_id": "exp_test_123",
        "title": "Weekly Update",
        "content": "Weekly Update\nFull body here",
    }
    assert result["external_id"] == "post_42"
    assert result["url"] == "https://whop.com/exp_test_123/post_42"
    assert result["raw"]["id"] == "post_42"


@patch("apps.social.whop.adapter.httpx")
def test_post_with_media_attaches_url(mock_httpx: MagicMock) -> None:
    """media_url should be added to payload as an attachment."""
    mock_httpx.post.return_value = _mock_response(201, {"id": "post_1"})
    adapter = WhopAdapter(VALID_CREDS.copy())

    adapter.post("Check this out", media_url="https://example.com/img.png")

    payload = mock_httpx.post.call_args.kwargs["json"]
    assert payload["attachments"] == [{"url": "https://example.com/img.png"}]


@patch("apps.social.whop.adapter.httpx")
def test_post_title_truncation(mock_httpx: MagicMock) -> None:
    """A first line longer than MAX_TITLE_LENGTH should be truncated."""
    mock_httpx.post.return_value = _mock_response(201, {"id": "post_1"})
    adapter = WhopAdapter(VALID_CREDS.copy())

    long_first_line = "T" * 250
    adapter.post(long_first_line)

    payload = mock_httpx.post.call_args.kwargs["json"]
    assert len(payload["title"]) == 200
    assert payload["title"].endswith("...")


@patch("apps.social.whop.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Whop returning 401 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(401, text="Unauthorized")
    adapter = WhopAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Whop error"):
        adapter.post("text")


# --- health_check ---


@patch("apps.social.whop.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /forum_posts returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"data": []})
    adapter = WhopAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://api.whop.com/api/v1/forum_posts",
        headers={
            "Authorization": "Bearer whop_test_key_abc",
            "Content-Type": "application/json",
        },
        params={"experience_id": "exp_test_123"},
        timeout=5,
    )


@patch("apps.social.whop.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = WhopAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
