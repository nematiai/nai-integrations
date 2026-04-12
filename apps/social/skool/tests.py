"""Tests for the Skool social adapter (placeholder)."""

import pytest

from apps.core.base.exceptions import APIError, ConfigurationError
from apps.social.skool.adapter import SkoolAdapter

VALID_CREDS = {
    "api_key": "skool_test_key",
    "community_id": "comm_123",
}


# --- validate_credentials ---


def test_validate_credentials_valid() -> None:
    """Valid api_key and community_id should not raise."""
    adapter = SkoolAdapter(VALID_CREDS.copy())
    assert adapter.credentials["api_key"] == "skool_test_key"
    assert adapter.credentials["community_id"] == "comm_123"


def test_validate_credentials_missing_api_key() -> None:
    """Missing api_key should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="api_key is required"):
        SkoolAdapter({"community_id": "comm_123"})


def test_validate_credentials_missing_community_id() -> None:
    """Missing community_id should raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="community_id is required"):
        SkoolAdapter({"api_key": "skool_test_key"})


# --- post ---


def test_post_raises_unavailable() -> None:
    """post() should raise APIError because no public API exists."""
    adapter = SkoolAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="Skool platform API is not publicly available"):
        adapter.post("hello")


def test_post_with_media_also_raises() -> None:
    """post() with media should also raise (platform not supported)."""
    adapter = SkoolAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="Skool platform API is not publicly available"):
        adapter.post("hello", media_url="https://example.com/img.png")


# --- health_check ---


def test_health_check_raises_unavailable() -> None:
    """health_check() should raise APIError — no endpoint to probe."""
    adapter = SkoolAdapter(VALID_CREDS.copy())
    with pytest.raises(APIError, match="Skool platform API is not publicly available"):
        adapter.health_check()


# --- class metadata ---


def test_platform_metadata() -> None:
    """Class-level metadata should match the platform contract."""
    assert SkoolAdapter.platform_name == "skool"
    assert SkoolAdapter.max_content_length == 5000
    assert SkoolAdapter.supports_media is True
