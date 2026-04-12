"""Tests for the MeWe social adapter (placeholder)."""

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.mewe.adapter import MeWeAdapter

VALID_CREDS = {
    "access_token": "mewe_test_token",
}


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid access_token should not raise."""
    adapter = MeWeAdapter(VALID_CREDS.copy())
    assert adapter.credentials["access_token"] == "mewe_test_token"


def test_validate_credentials_missing_access_token() -> None:
    """Missing access_token should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        MeWeAdapter({})


def test_validate_credentials_empty_access_token() -> None:
    """Empty access_token string should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="access_token is required"):
        MeWeAdapter({"access_token": ""})


# --- post ---


def test_post_raises_unavailable() -> None:
    """post() should raise APIError — platform API unavailable."""
    adapter = MeWeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="MeWe platform API is not publicly available"):
        adapter.post("hello")


def test_post_with_media_also_raises() -> None:
    """post() with media should also raise (platform not supported)."""
    adapter = MeWeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="MeWe platform API is not publicly available"):
        adapter.post("hello", media_url="https://example.com/img.png")


# --- health_check ---


def test_health_check_raises_unavailable() -> None:
    """health_check() should raise APIError — no endpoint to probe."""
    adapter = MeWeAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="MeWe platform API is not publicly available"):
        adapter.health_check()


# --- class metadata ---


def test_platform_metadata() -> None:
    """Class-level metadata should match the platform contract."""
    assert MeWeAdapter.platform_name == "mewe"
    assert MeWeAdapter.max_content_length == 5000
    assert MeWeAdapter.supports_media is True
