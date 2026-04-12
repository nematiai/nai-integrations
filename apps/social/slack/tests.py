"""Tests for the Slack social adapter."""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.slack.adapter import SlackAdapter

VALID_CREDS = {
    "webhook_url": "https://hooks.slack.com/services/T00/B00/xxxx",
}


def _mock_response(status_code: int = 200, text: str = "ok") -> MagicMock:
    """Build a mock httpx.Response for Slack (plain text body)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid webhook_url should not raise."""
    adapter = SlackAdapter(VALID_CREDS)
    assert adapter.credentials == VALID_CREDS


def test_validate_credentials_missing_url() -> None:
    """Missing webhook_url should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="webhook_url is required"):
        SlackAdapter({})


def test_validate_credentials_invalid_url() -> None:
    """Non-Slack URL should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="webhook_url must start"):
        SlackAdapter({"webhook_url": "https://example.com/hook"})


# --- post ---


@patch("apps.social.slack.adapter.httpx")
def test_post_text_only(mock_httpx: MagicMock) -> None:
    """Text-only post sends {text: ...} and parses 'ok' response."""
    mock_httpx.post.return_value = _mock_response(200, "ok")
    adapter = SlackAdapter(VALID_CREDS)

    result = adapter.post("Hello Slack")

    mock_httpx.post.assert_called_once_with(
        "https://hooks.slack.com/services/T00/B00/xxxx",
        json={"text": "Hello Slack"},
        timeout=10,
    )
    assert result["external_id"] == ""
    assert result["raw"]["body"] == "ok"


@patch("apps.social.slack.adapter.httpx")
def test_post_with_media(mock_httpx: MagicMock) -> None:
    """Post with media_url includes Block Kit image block."""
    mock_httpx.post.return_value = _mock_response(200, "ok")
    adapter = SlackAdapter(VALID_CREDS)

    result = adapter.post("Caption", media_url="https://example.com/img.png")

    call_kwargs = mock_httpx.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["text"] == "Caption"
    assert len(payload["blocks"]) == 2
    assert payload["blocks"][1]["type"] == "image"
    assert payload["blocks"][1]["image_url"] == "https://example.com/img.png"
    assert result["raw"]["body"] == "ok"


@patch("apps.social.slack.adapter.httpx")
def test_post_error_response(mock_httpx: MagicMock) -> None:
    """Slack returning non-ok text should raise APIError."""
    mock_httpx.post.return_value = _mock_response(200, "invalid_payload")
    adapter = SlackAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Slack error"):
        adapter.post("fail")


@patch("apps.social.slack.adapter.httpx")
def test_post_http_error(mock_httpx: MagicMock) -> None:
    """Slack returning 403 should raise APIError."""
    mock_httpx.post.return_value = _mock_response(403, "action_prohibited")
    adapter = SlackAdapter(VALID_CREDS)

    with pytest.raises(APIError, match="Slack error"):
        adapter.post("fail")


# --- health_check ---


def test_health_check_success() -> None:
    """Valid webhook URL format returns True."""
    adapter = SlackAdapter(VALID_CREDS)
    assert adapter.health_check() is True


def test_health_check_failure() -> None:
    """Invalid webhook URL format returns False."""
    adapter = SlackAdapter.__new__(SlackAdapter)
    adapter.credentials = {"webhook_url": "https://bad.url/x"}
    assert adapter.health_check() is False
