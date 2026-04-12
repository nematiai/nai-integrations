"""Tests for the Mastodon social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.mastodon.adapter import MastodonAdapter

VALID_CREDS = {
    "instance_url": "https://mastodon.social",
    "access_token": "test-token-123",
}


def _mock_response(
    status_code: int = 200,
    json_data: dict = None,
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
    """Valid instance_url + access_token should not raise."""
    adapter = MastodonAdapter(VALID_CREDS.copy())
    assert adapter.credentials["instance_url"] == "https://mastodon.social"


def test_validate_credentials_missing_instance_url() -> None:
    """Missing instance_url should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="instance_url is required"):
        MastodonAdapter({"access_token": "tok"})


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        MastodonAdapter({"instance_url": "https://mastodon.social"})


def test_validate_instance_url_format() -> None:
    """Non-https instance_url should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="must start with https://"):
        MastodonAdapter({"instance_url": "http://mastodon.social", "access_token": "t"})


def test_validate_strips_trailing_slash() -> None:
    """Trailing slash on instance_url should be stripped."""
    creds = {"instance_url": "https://mastodon.social/", "access_token": "t"}
    adapter = MastodonAdapter(creds)
    assert adapter.credentials["instance_url"] == "https://mastodon.social"


# --- post ---


@patch("apps.social.mastodon.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sends status JSON and returns external_id + url."""
    mock_httpx.post.return_value = _mock_response(
        200,
        {"id": "1234", "url": "https://mastodon.social/@user/1234"},
    )
    adapter = MastodonAdapter(VALID_CREDS.copy())

    result = adapter.post("Hello Mastodon")

    mock_httpx.post.assert_called_once_with(
        "https://mastodon.social/api/v1/statuses",
        headers={"Authorization": "Bearer test-token-123"},
        json={"status": "Hello Mastodon"},
        timeout=10,
    )
    assert result["external_id"] == "1234"
    assert result["url"] == "https://mastodon.social/@user/1234"


@patch("apps.social.mastodon.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url uploads media first, then attaches media_ids."""
    download_resp = _mock_response(200, content=b"fake-image-bytes")
    upload_resp = _mock_response(202, {"id": "media-99"})
    status_resp = _mock_response(
        200,
        {"id": "5678", "url": "https://mastodon.social/@user/5678"},
    )

    mock_httpx.get.return_value = download_resp
    mock_httpx.post.side_effect = [upload_resp, status_resp]

    adapter = MastodonAdapter(VALID_CREDS.copy())
    result = adapter.post("With image", media_url="https://example.com/pic.png")

    # First call: media upload
    upload_call = mock_httpx.post.call_args_list[0]
    assert upload_call.args[0] == "https://mastodon.social/api/v2/media"

    # Second call: status with media_ids
    status_call = mock_httpx.post.call_args_list[1]
    payload = status_call.kwargs["json"]
    assert payload["status"] == "With image"
    assert payload["media_ids"] == ["media-99"]
    assert result["external_id"] == "5678"


@patch("apps.social.mastodon.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Mastodon returning 422 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(422, text="Unprocessable")
    adapter = MastodonAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Mastodon error"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.mastodon.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET verify_credentials returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"id": "1", "username": "me"})
    adapter = MastodonAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://mastodon.social/api/v1/accounts/verify_credentials",
        headers={"Authorization": "Bearer test-token-123"},
        timeout=5,
    )


@patch("apps.social.mastodon.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable instance returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = MastodonAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
