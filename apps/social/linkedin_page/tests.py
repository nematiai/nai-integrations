"""Tests for the LinkedIn company page adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.linkedin_page.adapter import LinkedInPageAdapter

VALID_CREDS = {
    "access_token": "test-token-456",
    "organization_urn": "urn:li:organization:98765",
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
    """Valid access_token + organization_urn should not raise."""
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())
    assert adapter.credentials["organization_urn"] == "urn:li:organization:98765"


def test_validate_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        LinkedInPageAdapter({"organization_urn": "urn:li:organization:1"})


def test_validate_missing_organization_urn() -> None:
    """Missing organization_urn should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="organization_urn is required"):
        LinkedInPageAdapter({"access_token": "tok"})


def test_validate_invalid_organization_urn_format() -> None:
    """Non-URN organization_urn should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="must start with"):
        LinkedInPageAdapter(
            {"access_token": "tok", "organization_urn": "bad-urn"},
        )


# --- post ---


@patch("apps.social.linkedin_page.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post uses organization_urn as author."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"id": "urn:li:ugcPost:org100"},
    )
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    result = adapter.post("Company update")

    payload = mock_httpx.post.call_args.kwargs["json"]
    assert payload["author"] == "urn:li:organization:98765"
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert share["shareCommentary"]["text"] == "Company update"
    assert share["shareMediaCategory"] == "NONE"
    assert result["external_id"] == "urn:li:ugcPost:org100"


@patch("apps.social.linkedin_page.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url sets ARTICLE category."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"id": "urn:li:ugcPost:org200"},
    )
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    result = adapter.post(
        "Check this out",
        media_url="https://example.com/blog",
    )

    payload = mock_httpx.post.call_args.kwargs["json"]
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert share["shareMediaCategory"] == "ARTICLE"
    assert share["media"][0]["originalUrl"] == "https://example.com/blog"
    assert result["external_id"] == "urn:li:ugcPost:org200"


@patch("apps.social.linkedin_page.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """LinkedIn returning 403 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(403, text="Forbidden")
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    with pytest.raises(APIError, match="LinkedIn Page error"):
        adapter.post("fail")


@patch("apps.social.linkedin_page.adapter.httpx")
def test_post_truncates_long_content(mock_httpx: MagicMock) -> None:
    """Content exceeding 3000 chars is truncated."""
    mock_httpx.post.return_value = _mock_response(
        201,
        {"id": "urn:li:ugcPost:1"},
    )
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    adapter.post("b" * 4000)

    payload = mock_httpx.post.call_args.kwargs["json"]
    share = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
    assert len(share["shareCommentary"]["text"]) == 3000


# --- health_check ---


@patch("apps.social.linkedin_page.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """GET organizationalEntityAcls returning 200 means healthy."""
    mock_httpx.get.return_value = _mock_response(200, {"elements": []})
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is True
    mock_httpx.get.assert_called_once_with(
        "https://api.linkedin.com/v2/organizationalEntityAcls",
        headers={
            "Authorization": "Bearer test-token-456",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        params={"q": "roleAssignee", "projection": "(elements)"},
        timeout=5,
    )


@patch("apps.social.linkedin_page.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Network error returns False."""
    mock_httpx.get.side_effect = Exception("timeout")
    adapter = LinkedInPageAdapter(VALID_CREDS.copy())

    assert adapter.health_check() is False
