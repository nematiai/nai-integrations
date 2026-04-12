"""Tests for social account management endpoints."""

from unittest.mock import patch

from apps.core.base.exceptions import ConfigurationError
from apps.social.base.models import SocialAccount


@patch("apps.social.views_accounts.get_adapter")
def test_register_account_success(mock_get_adapter, api, client_and_key, post_json):
    """Valid credentials → 201 and SocialAccount row."""
    mock_get_adapter.return_value.return_value.health_check.return_value = True

    resp = post_json(
        api,
        "/api/v1/social/accounts",
        {"platform": "telegram", "credentials": {"bot_token": "x", "chat_id": "y"}},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "telegram"
    assert data["health_status"] == "healthy"
    assert "credentials" not in data
    app_client, _ = client_and_key
    assert SocialAccount.objects.filter(
        app_client=app_client, platform="telegram"
    ).exists()


def test_register_account_invalid_platform(api, post_json):
    """Unknown platform → 400."""
    resp = post_json(
        api,
        "/api/v1/social/accounts",
        {"platform": "myspace", "credentials": {}},
    )
    assert resp.status_code == 400
    assert "Unknown platform" in resp.json()["detail"]


@patch("apps.social.views_accounts.get_adapter")
def test_register_account_invalid_credentials(mock_get_adapter, api, post_json):
    """Adapter raises ConfigurationError → 400."""
    mock_get_adapter.return_value.side_effect = ConfigurationError("bot_token required")

    resp = post_json(
        api,
        "/api/v1/social/accounts",
        {"platform": "telegram", "credentials": {}},
    )
    assert resp.status_code == 400
    assert "bot_token" in resp.json()["detail"]


@patch("apps.social.views_accounts.get_adapter")
def test_list_accounts_no_credentials_leak(
    mock_get_adapter, api, client_and_key, post_json
):
    """List returns active accounts without credentials."""
    mock_get_adapter.return_value.return_value.health_check.return_value = True
    post_json(
        api,
        "/api/v1/social/accounts",
        {"platform": "telegram", "credentials": {"bot_token": "x", "chat_id": "y"}},
    )

    resp = api.get("/api/v1/social/accounts")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["platform"] == "telegram"
    assert "credentials" not in items[0]
    assert "_credentials" not in items[0]


def test_delete_account(api, client_and_key):
    """DELETE sets is_active=False."""
    app_client, _ = client_and_key
    acc = SocialAccount.objects.create(
        app_client=app_client,
        external_user_id="user-123",
        platform="telegram",
        _credentials="",
    )

    resp = api.delete("/api/v1/social/accounts/telegram")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    acc.refresh_from_db()
    assert acc.is_active is False


def test_delete_account_missing(api):
    """DELETE on unknown platform → 404."""
    resp = api.delete("/api/v1/social/accounts/telegram")
    assert resp.status_code == 404
