"""Tests for the Reddit social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.reddit.adapter import RedditAdapter

VALID_CREDS = {
    "client_id": "abc123",
    "client_secret": "secret456",
    "username": "testbot",
    "password": "pass789",
    "subreddit": "test",
}


def _mock_token_response() -> MagicMock:
    """Mock a successful Reddit OAuth2 token response."""
    resp = MagicMock()
    resp.json.return_value = {
        "access_token": "tok_abc",
        "token_type": "bearer",
    }
    return resp


def _mock_submit_response(
    name: str = "t3_abc",
    url: str = "https://reddit.com/r/test/comments/abc/",
    errors: list = None,
) -> MagicMock:
    """Mock a Reddit submit response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "json": {
            "errors": errors or [],
            "data": {"name": name, "url": url},
        },
    }
    return resp


def _mock_me_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid credentials should not raise."""
    adapter = RedditAdapter(VALID_CREDS)
    assert adapter.credentials == VALID_CREDS


def test_validate_credentials_missing_fields() -> None:
    """Each missing required field should raise ConfigurationError."""
    for field in ("client_id", "client_secret", "username", "password", "subreddit"):
        creds = {k: v for k, v in VALID_CREDS.items() if k != field}
        with pytest.raises(ConfigurationError, match=field):
            RedditAdapter(creds)


# --- _get_access_token ---


@patch("apps.social.reddit.adapter.httpx")
def test_get_access_token(mock_httpx: MagicMock) -> None:
    """Successful token request returns access_token string."""
    mock_httpx.post.return_value = _mock_token_response()
    adapter = RedditAdapter(VALID_CREDS)

    token = adapter._get_access_token()

    assert token == "tok_abc"
    call_kwargs = mock_httpx.post.call_args
    assert call_kwargs[0][0] == "https://www.reddit.com/api/v1/access_token"
    assert call_kwargs[1]["auth"] == ("abc123", "secret456")


@patch("apps.social.reddit.adapter.httpx")
def test_get_access_token_error(mock_httpx: MagicMock) -> None:
    """Token endpoint returning error should raise APIError."""
    resp = MagicMock()
    resp.json.return_value = {"error": "invalid_grant"}
    mock_httpx.post.return_value = resp
    adapter = RedditAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Reddit token error"):
        adapter._get_access_token()


# --- post ---


@patch("apps.social.reddit.adapter.httpx")
def test_post_text(mock_httpx: MagicMock) -> None:
    """Text post calls /api/submit with kind=self."""
    mock_httpx.post.side_effect = [
        _mock_token_response(),
        _mock_submit_response(),
    ]
    adapter = RedditAdapter(VALID_CREDS)

    result = adapter.post("My Title\nBody text here")

    submit_call = mock_httpx.post.call_args_list[1]
    assert submit_call[0][0] == "https://oauth.reddit.com/api/submit"
    assert submit_call[1]["data"]["kind"] == "self"
    assert submit_call[1]["data"]["sr"] == "test"
    assert submit_call[1]["data"]["title"] == "My Title"
    assert result["external_id"] == "t3_abc"


@patch("apps.social.reddit.adapter.httpx")
def test_post_with_link(mock_httpx: MagicMock) -> None:
    """Post with media_url submits a link post."""
    mock_httpx.post.side_effect = [
        _mock_token_response(),
        _mock_submit_response(),
    ]
    adapter = RedditAdapter(VALID_CREDS)

    result = adapter.post("Link Title", media_url="https://example.com/img.jpg")

    submit_call = mock_httpx.post.call_args_list[1]
    assert submit_call[1]["data"]["kind"] == "link"
    assert submit_call[1]["data"]["url"] == "https://example.com/img.jpg"
    assert result["url"] == "https://reddit.com/r/test/comments/abc/"


@patch("apps.social.reddit.adapter.httpx")
def test_post_api_error(mock_httpx: MagicMock) -> None:
    """Reddit returning errors in response should raise APIError."""
    mock_httpx.post.side_effect = [
        _mock_token_response(),
        _mock_submit_response(errors=[["SUBREDDIT_NOEXIST", "invalid", "test"]]),
    ]
    adapter = RedditAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Reddit submit error"):
        adapter.post("Will fail")


# --- health_check ---


@patch("apps.social.reddit.adapter.httpx")
def test_health_check_success(mock_httpx: MagicMock) -> None:
    """Successful /api/v1/me returns True."""
    mock_httpx.post.return_value = _mock_token_response()
    mock_httpx.get.return_value = _mock_me_response(200)
    adapter = RedditAdapter(VALID_CREDS)

    assert adapter.health_check() is True


@patch("apps.social.reddit.adapter.httpx")
def test_health_check_failure(mock_httpx: MagicMock) -> None:
    """Exception during health check returns False."""
    mock_httpx.post.side_effect = Exception("connection refused")
    adapter = RedditAdapter(VALID_CREDS)

    assert adapter.health_check() is False
