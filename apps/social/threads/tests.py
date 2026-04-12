"""Tests for the Threads social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.threads.adapter import ThreadsAdapter

VALID_CREDS = {
    "access_token": "THtest_token_789",
    "threads_user_id": "user_321",
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
    """Valid access_token + threads_user_id should not raise."""
    adapter = ThreadsAdapter(VALID_CREDS.copy())
    assert adapter.credentials["threads_user_id"] == "user_321"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        ThreadsAdapter({"threads_user_id": "user_321"})


def test_validate_credentials_missing_user_id() -> None:
    """Missing threads_user_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="threads_user_id is required"):
        ThreadsAdapter({"access_token": "tok"})


# --- post ---


@patch("apps.social.threads.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sets media_type=TEXT."""
    container_resp = _mock_response(200, {"id": "container_111"})
    publish_resp = _mock_response(200, {"id": "thread_222"})
    mock_httpx.post.side_effect = [container_resp, publish_resp]

    adapter = ThreadsAdapter(VALID_CREDS.copy())
    result = adapter.post("Hello Threads")

    assert mock_httpx.post.call_count == 2
    mock_httpx.post.assert_any_call(
        "https://graph.threads.net/v1.0/user_321/threads",
        params={"access_token": "THtest_token_789"},
        json={"text": "Hello Threads", "media_type": "TEXT"},
        timeout=15,
    )
    mock_httpx.post.assert_any_call(
        "https://graph.threads.net/v1.0/user_321/threads_publish",
        params={"access_token": "THtest_token_789"},
        json={"creation_id": "container_111"},
        timeout=15,
    )
    assert result["external_id"] == "thread_222"
    assert result["url"] == ""


@patch("apps.social.threads.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media sets media_type=IMAGE and image_url."""
    container_resp = _mock_response(200, {"id": "container_333"})
    publish_resp = _mock_response(200, {"id": "thread_444"})
    mock_httpx.post.side_effect = [container_resp, publish_resp]

    adapter = ThreadsAdapter(VALID_CREDS.copy())
    result = adapter.post("Image post", media_url="https://example.com/pic.jpg")

    first_call = mock_httpx.post.call_args_list[0]
    payload = first_call.kwargs["json"]
    assert payload["media_type"] == "IMAGE"
    assert payload["image_url"] == "https://example.com/pic.jpg"
    assert result["external_id"] == "thread_444"


@patch("apps.social.threads.adapter.httpx")
def test_post_container_error(mock_httpx: MagicMock) -> None:
    """Container creation failure should raise APIError."""
    mock_httpx.post.return_value = _mock_response(400, text="Bad request")
    adapter = ThreadsAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Threads container error"):
        adapter.post("fail")


@patch("apps.social.threads.adapter.httpx")
def test_post_publish_error(mock_httpx: MagicMock) -> None:
    """Publish step failure should raise APIError."""
    container_resp = _mock_response(200, {"id": "container_555"})
    publish_resp = _mock_response(400, text="Publish failed")
    mock_httpx.post.side_effect = [container_resp, publish_resp]

    adapter = ThreadsAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Threads publish error"):
        adapter.post("fail")


@patch("apps.social.threads.adapter.httpx")
def test_post_no_container_id(mock_httpx: MagicMock) -> None:
    """Container response with no id should raise APIError."""
    mock_httpx.post.return_value = _mock_response(200, {})
    adapter = ThreadsAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="no container id"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.threads.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET threads_publishing_limit returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"data": []})
    adapter = ThreadsAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://graph.threads.net/v1.0/user_321/threads_publishing_limit",
        params={"access_token": "THtest_token_789"},
        timeout=5,
    )


@patch("apps.social.threads.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = ThreadsAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
