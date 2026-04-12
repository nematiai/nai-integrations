"""Tests for the Instagram social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.instagram.adapter import InstagramAdapter

VALID_CREDS = {
    "access_token": "EAAtest_ig_token",
    "instagram_account_id": "17841400000",
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
    """Valid access_token + instagram_account_id should not raise."""
    adapter = InstagramAdapter(VALID_CREDS.copy())
    assert adapter.credentials["instagram_account_id"] == "17841400000"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        InstagramAdapter({"instagram_account_id": "17841400000"})


def test_validate_credentials_missing_account_id() -> None:
    """Missing instagram_account_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="instagram_account_id is required"):
        InstagramAdapter({"access_token": "tok"})


# --- post ---


def test_post_without_media_raises() -> None:
    """Instagram requires media — posting without should raise APIError."""
    adapter = InstagramAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="requires media_url"):
        adapter.post("No image")


@patch("apps.social.instagram.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Two-step publish: create container then publish."""
    container_resp = _mock_response(200, {"id": "container_123"})
    publish_resp = _mock_response(200, {"id": "media_456"})
    mock_httpx.post.side_effect = [container_resp, publish_resp]

    adapter = InstagramAdapter(VALID_CREDS.copy())
    result = adapter.post("My caption", media_url="https://example.com/pic.jpg")

    assert mock_httpx.post.call_count == 2
    # First call: create container
    mock_httpx.post.assert_any_call(
        "https://graph.facebook.com/v21.0/17841400000/media",
        params={"access_token": "EAAtest_ig_token"},
        json={"image_url": "https://example.com/pic.jpg", "caption": "My caption"},
        timeout=15,
    )
    # Second call: publish
    mock_httpx.post.assert_any_call(
        "https://graph.facebook.com/v21.0/17841400000/media_publish",
        params={"access_token": "EAAtest_ig_token"},
        json={"creation_id": "container_123"},
        timeout=15,
    )
    assert result["external_id"] == "media_456"
    assert result["url"] == "https://www.instagram.com/p/media_456/"


@patch("apps.social.instagram.adapter.httpx")
def test_post_container_error(mock_httpx: MagicMock) -> None:
    """Container creation failure should raise APIError."""
    mock_httpx.post.return_value = _mock_response(400, text="Invalid image")
    adapter = InstagramAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Instagram container error"):
        adapter.post("fail", media_url="https://example.com/bad.jpg")


@patch("apps.social.instagram.adapter.httpx")
def test_post_publish_error(mock_httpx: MagicMock) -> None:
    """Publish step failure should raise APIError."""
    container_resp = _mock_response(200, {"id": "container_123"})
    publish_resp = _mock_response(400, text="Publish failed")
    mock_httpx.post.side_effect = [container_resp, publish_resp]

    adapter = InstagramAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Instagram publish error"):
        adapter.post("fail", media_url="https://example.com/pic.jpg")


@patch("apps.social.instagram.adapter.httpx")
def test_post_no_container_id(mock_httpx: MagicMock) -> None:
    """Container response with no id should raise APIError."""
    mock_httpx.post.return_value = _mock_response(200, {})
    adapter = InstagramAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="no container id"):
        adapter.post("fail", media_url="https://example.com/pic.jpg")


# --- health_check ---


@patch("apps.social.instagram.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /{ig_id} returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(
        200,
        {"id": "17841400000", "username": "testuser"},
    )
    adapter = InstagramAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://graph.facebook.com/v21.0/17841400000",
        params={"access_token": "EAAtest_ig_token", "fields": "id,username"},
        timeout=5,
    )


@patch("apps.social.instagram.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = InstagramAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
