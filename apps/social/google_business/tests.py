"""Tests for the Google Business Profile social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.google_business.adapter import GoogleBusinessAdapter

VALID_CREDS = {
    "access_token": "ya29.test_token",
    "account_id": "111222333",
    "location_id": "444555666",
}

EXPECTED_POST_URL = (
    "https://mybusiness.googleapis.com/v4"
    "/accounts/111222333/locations/444555666/localPosts"
)
EXPECTED_LOCATION_URL = (
    "https://mybusiness.googleapis.com/v4/accounts/111222333/locations/444555666"
)
POST_NAME = "accounts/111222333/locations/444555666/localPosts/987"


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
    """Valid access_token + account_id + location_id should not raise."""
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())
    assert adapter.credentials["location_id"] == "444555666"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        GoogleBusinessAdapter(
            {"account_id": "111", "location_id": "222"},
        )


def test_validate_credentials_missing_account_id() -> None:
    """Missing account_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="account_id is required"):
        GoogleBusinessAdapter(
            {"access_token": "tok", "location_id": "222"},
        )


def test_validate_credentials_missing_location_id() -> None:
    """Missing location_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="location_id is required"):
        GoogleBusinessAdapter(
            {"access_token": "tok", "account_id": "111"},
        )


# --- post ---


@patch("apps.social.google_business.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sends STANDARD localPost with no media."""
    mock_httpx.post.return_value = _mock_response(200, {"name": POST_NAME})
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    result = adapter.post("Hello world")

    mock_httpx.post.assert_called_once_with(
        EXPECTED_POST_URL,
        headers={
            "Authorization": "Bearer ya29.test_token",
            "Content-Type": "application/json",
        },
        json={
            "languageCode": "en",
            "summary": "Hello world",
            "topicType": "STANDARD",
        },
        timeout=15,
    )
    assert result["external_id"] == POST_NAME
    assert result["url"] == ""
    assert result["raw"] == {"name": POST_NAME}


@patch("apps.social.google_business.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url includes PHOTO media entry."""
    mock_httpx.post.return_value = _mock_response(200, {"name": POST_NAME})
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    result = adapter.post(
        "Check this",
        media_url="https://example.com/pic.jpg",
    )

    mock_httpx.post.assert_called_once_with(
        EXPECTED_POST_URL,
        headers={
            "Authorization": "Bearer ya29.test_token",
            "Content-Type": "application/json",
        },
        json={
            "languageCode": "en",
            "summary": "Check this",
            "topicType": "STANDARD",
            "media": [
                {
                    "mediaFormat": "PHOTO",
                    "sourceUrl": "https://example.com/pic.jpg",
                },
            ],
        },
        timeout=15,
    )
    assert result["external_id"] == POST_NAME


@patch("apps.social.google_business.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Google Business returning 400 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(400, text="Bad Request")
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Google Business error"):
        adapter.post("fail")


@patch("apps.social.google_business.adapter.httpx")
def test_post_network_error(mock_httpx: MagicMock) -> None:
    """Network failure should raise APIError."""
    from httpx import HTTPError

    mock_httpx.post.side_effect = HTTPError("timeout")
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="Google Business API request failed"):
        adapter.post("fail")


# --- health_check ---


@patch("apps.social.google_business.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET /accounts/.../locations/... returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"name": "locations/444555666"})
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        EXPECTED_LOCATION_URL,
        headers={
            "Authorization": "Bearer ya29.test_token",
            "Content-Type": "application/json",
        },
        timeout=5,
    )


@patch("apps.social.google_business.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Unreachable API returns False."""
    mock_httpx.get.side_effect = Exception("connection refused")
    adapter = GoogleBusinessAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
