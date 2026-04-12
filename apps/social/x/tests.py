"""Tests for the X (Twitter) social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.x.adapter import XAdapter

VALID_CREDS = {
    "api_key": "test-consumer-key",
    "api_secret": "test-consumer-secret",
    "access_token": "test-access-token",
    "access_token_secret": "test-access-secret",
}


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
    content: bytes = b"img",
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.content = content
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """All four OAuth 1.0a fields present should not raise."""
    adapter = XAdapter(VALID_CREDS.copy())
    assert adapter.credentials["api_key"] == "test-consumer-key"


def test_validate_missing_api_key() -> None:
    """Missing api_key should raise ConfigurationError."""
    creds = VALID_CREDS.copy()
    del creds["api_key"]
    with pytest.raises(ConfigurationError, match="api_key is required"):
        XAdapter(creds)


def test_validate_missing_api_secret() -> None:
    """Missing api_secret should raise ConfigurationError."""
    creds = VALID_CREDS.copy()
    del creds["api_secret"]
    with pytest.raises(ConfigurationError, match="api_secret is required"):
        XAdapter(creds)


def test_validate_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    creds = VALID_CREDS.copy()
    del creds["access_token"]
    with pytest.raises(ConfigurationError, match="access_token is required"):
        XAdapter(creds)


def test_validate_missing_access_token_secret() -> None:
    """Missing access_token_secret should raise ConfigurationError."""
    creds = VALID_CREDS.copy()
    del creds["access_token_secret"]
    with pytest.raises(ConfigurationError, match="access_token_secret is required"):
        XAdapter(creds)


# --- post ---


@patch("apps.social.x.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only tweet sends JSON and returns external_id + url."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"data": {"id": "1234567890", "text": "Hello X"}},
    )
    adapter = XAdapter(VALID_CREDS.copy())
    result = adapter.post("Hello X")

    mock_httpx.post.assert_called_once()
    call_args = mock_httpx.post.call_args
    assert call_args.args[0] == "https://api.twitter.com/2/tweets"
    assert call_args.kwargs["json"] == {"text": "Hello X"}
    assert result["external_id"] == "1234567890"
    assert "x.com/i/status/1234567890" in result["url"]


@patch("apps.social.x.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url uploads media first, then attaches media_ids."""
    download_resp = _mock_response(200, content=b"fake-image-bytes")
    upload_resp = _mock_response(200, {"media_id_string": "media-42"})
    tweet_resp = _mock_response(
        201,
        {"data": {"id": "9876", "text": "With pic"}},
    )

    mock_httpx.get.return_value = download_resp
    mock_httpx.post.side_effect = [upload_resp, tweet_resp]

    adapter = XAdapter(VALID_CREDS.copy())
    result = adapter.post("With pic", media_url="https://example.com/pic.png")

    upload_call = mock_httpx.post.call_args_list[0]
    assert "media/upload.json" in upload_call.args[0]

    tweet_call = mock_httpx.post.call_args_list[1]
    payload = tweet_call.kwargs["json"]
    assert payload["media"] == {"media_ids": ["media-42"]}
    assert result["external_id"] == "9876"


@patch("apps.social.x.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Twitter returning 403 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(403, text="Forbidden")
    adapter = XAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="X error"):
        adapter.post("fail")


@patch("apps.social.x.adapter.httpx")
def test_post_truncates_long_content(mock_httpx: MagicMock) -> None:
    """Content exceeding 280 chars should be truncated."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"data": {"id": "111", "text": "truncated"}},
    )
    adapter = XAdapter(VALID_CREDS.copy())
    long_text = "A" * 300
    adapter.post(long_text)

    sent_text = mock_httpx.post.call_args.kwargs["json"]["text"]
    assert len(sent_text) == 280
    assert sent_text.endswith("...")


# --- health_check ---


@patch("apps.social.x.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /2/users/me returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"data": {"id": "1"}})
    adapter = XAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once()
    assert "users/me" in mock_httpx.get.call_args.args[0]


@patch("apps.social.x.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = XAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
