"""Tests for the Bluesky social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.bluesky.adapter import BlueskyAdapter
from apps.social.bluesky.conftest import (
    VALID_CREDS,
    mock_blob_response,
    mock_error_response,
    mock_media_download,
    mock_record_response,
    mock_session_response,
)


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid credentials should not raise."""
    adapter = BlueskyAdapter(VALID_CREDS)
    assert adapter.credentials == VALID_CREDS


def test_validate_credentials_missing_fields() -> None:
    """Each missing required field should raise ConfigurationError."""
    for field in ("handle", "app_password"):
        creds = {k: v for k, v in VALID_CREDS.items() if k != field}
        with pytest.raises(ConfigurationError, match=field):
            BlueskyAdapter(creds)


# --- _create_session ---


@patch("apps.social.bluesky.adapter.httpx")
def test_create_session(mock_httpx: MagicMock) -> None:
    """Successful createSession returns accessJwt and did."""
    mock_httpx.post.return_value = mock_session_response()
    adapter = BlueskyAdapter(VALID_CREDS)

    session = adapter._create_session()

    assert session["accessJwt"] == "jwt_abc"
    assert session["did"] == "did:plc:test123"
    call_args = mock_httpx.post.call_args
    assert "createSession" in call_args[0][0]


@patch("apps.social.bluesky.adapter.httpx")
def test_create_session_error(mock_httpx: MagicMock) -> None:
    """Auth failure should raise APIError."""
    mock_httpx.post.return_value = mock_error_response(
        401,
        "AuthenticationRequired",
        "Invalid identifier or password",
    )
    adapter = BlueskyAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Bluesky auth failed"):
        adapter._create_session()


# --- post ---


@patch("apps.social.bluesky.adapter.httpx")
def test_post_text(mock_httpx: MagicMock) -> None:
    """Text post calls createRecord with correct payload."""
    mock_httpx.post.side_effect = [
        mock_session_response(),
        mock_record_response(),
    ]
    adapter = BlueskyAdapter(VALID_CREDS)

    result = adapter.post("Hello Bluesky!")

    assert result["external_id"].startswith("at://")
    assert "bsky.app/profile/did:plc:test123/post/3k4abc" in result["url"]
    create_call = mock_httpx.post.call_args_list[1]
    body = create_call[1]["json"]
    assert body["collection"] == "app.bsky.feed.post"
    assert body["record"]["text"] == "Hello Bluesky!"


@patch("apps.social.bluesky.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media uploads blob then creates record with embed."""
    mock_httpx.get.return_value = mock_media_download()
    mock_httpx.post.side_effect = [
        mock_session_response(),
        mock_blob_response(),
        mock_record_response(),
    ]
    adapter = BlueskyAdapter(VALID_CREDS)

    result = adapter.post("With image", media_url="https://example.com/img.jpg")

    assert result["external_id"].startswith("at://")
    blob_call = mock_httpx.post.call_args_list[1]
    assert "uploadBlob" in blob_call[0][0]
    record_call = mock_httpx.post.call_args_list[2]
    embed = record_call[1]["json"]["record"]["embed"]
    assert embed["$type"] == "app.bsky.embed.images"


@patch("apps.social.bluesky.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """createRecord returning error should raise APIError."""
    mock_httpx.post.side_effect = [
        mock_session_response(),
        mock_error_response(400, "InvalidRequest", "Bad record"),
    ]
    adapter = BlueskyAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Bluesky post failed"):
        adapter.post("Will fail")


@patch("apps.social.bluesky.adapter.httpx")
def test_post_media_download_failure(mock_httpx: MagicMock) -> None:
    """Failed media download should raise APIError."""
    mock_httpx.get.return_value = mock_media_download(status_code=404)
    mock_httpx.post.return_value = mock_session_response()
    adapter = BlueskyAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Failed to download media"):
        adapter.post("Bad media", media_url="https://example.com/gone.jpg")


@patch("apps.social.bluesky.adapter.httpx")
def test_post_blob_upload_failure(mock_httpx: MagicMock) -> None:
    """Failed blob upload should raise APIError."""
    mock_httpx.get.return_value = mock_media_download()
    mock_httpx.post.side_effect = [
        mock_session_response(),
        mock_error_response(400, "BlobTooLarge", "over 1MB"),
    ]
    adapter = BlueskyAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Bluesky blob upload failed"):
        adapter.post("Too big", media_url="https://example.com/huge.jpg")


# --- health_check ---


@patch("apps.social.bluesky.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """Successful createSession means healthy."""
    mock_httpx.post.return_value = mock_session_response()
    adapter = BlueskyAdapter(VALID_CREDS)

    assert adapter.health_check() is True


@patch("apps.social.bluesky.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Exception during health check returns False."""
    mock_httpx.post.side_effect = Exception("connection refused")
    adapter = BlueskyAdapter(VALID_CREDS)

    assert adapter.health_check() is False
