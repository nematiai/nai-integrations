"""Tests for the LinkedIn personal profile adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.linkedin.adapter import LinkedInAdapter

VALID_CREDS = {
    "access_token": "test-token-123",
    "person_urn": "urn:li:person:ABC123",
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
    """Valid access_token + person_urn should not raise."""
    adapter = LinkedInAdapter(VALID_CREDS.copy())
    assert adapter.credentials["person_urn"] == "urn:li:person:ABC123"


def test_validate_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        LinkedInAdapter({"person_urn": "urn:li:person:ABC123"})


def test_validate_missing_person_urn() -> None:
    """Missing person_urn should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="person_urn is required"):
        LinkedInAdapter({"access_token": "tok"})


def test_validate_invalid_person_urn_format() -> None:
    """Non-URN person_urn should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="must start with"):
        LinkedInAdapter({"access_token": "tok", "person_urn": "bad-urn"})


# --- post ---


@patch("apps.social.linkedin.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sends UGC payload and returns external_id + url."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"id": "urn:li:ugcPost:123456"},
    )
    adapter = LinkedInAdapter(VALID_CREDS.copy())

    result = adapter.post("Hello LinkedIn")

    call_kwargs = mock_httpx.post.call_args.kwargs
    payload = call_kwargs["json"]
    assert payload["author"] == "urn:li:person:ABC123"
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert share["shareCommentary"]["text"] == "Hello LinkedIn"
    assert share["shareMediaCategory"] == "NONE"
    assert result["external_id"] == "urn:li:ugcPost:123456"
    assert "linkedin.com/feed/update" in result["url"]


@patch("apps.social.linkedin.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url sets ARTICLE category with media array."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"id": "urn:li:ugcPost:789"},
    )
    adapter = LinkedInAdapter(VALID_CREDS.copy())

    result = adapter.post("With link", media_url="https://example.com/img.jpg")

    payload = mock_httpx.post.call_args.kwargs["json"]
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert share["shareMediaCategory"] == "ARTICLE"
    assert share["media"][0]["originalUrl"] == "https://example.com/img.jpg"
    assert result["external_id"] == "urn:li:ugcPost:789"


@patch("apps.social.linkedin.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """LinkedIn returning 422 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(422, text="Unprocessable")
    adapter = LinkedInAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="LinkedIn error"):
        adapter.post("fail")


@patch("apps.social.linkedin.adapter.httpx")
def test_post_truncates_long_content(mock_httpx: MagicMock) -> None:
    """Content exceeding 3000 chars is truncated."""
    mock_httpx.post.return_value = _mock_response(201, {"id": "urn:li:ugcPost:1"})
    adapter = LinkedInAdapter(VALID_CREDS.copy())
    long_text = "a" * 4000

    adapter.post(long_text)

    payload = mock_httpx.post.call_args.kwargs["json"]
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert len(share["shareCommentary"]["text"]) == 3000


# --- health_check ---


@patch("apps.social.linkedin.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET userinfo returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"sub": "abc"})
    adapter = LinkedInAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization": "Bearer test-token-123",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=5,
    )


@patch("apps.social.linkedin.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Network error returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = LinkedInAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
