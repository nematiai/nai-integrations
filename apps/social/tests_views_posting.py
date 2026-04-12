"""Tests for social posting, logs, platforms, and health endpoints."""

from unittest.mock import patch

from django.test import Client

from apps.social.base.models import PostLog, SocialAccount


@patch("apps.social.views_posting.post_to_platform")
def test_post_dispatches_celery(mock_task, api, client_and_key, post_json):
    """POST /post creates PostLogs and dispatches Celery task."""
    app_client, _ = client_and_key
    SocialAccount.objects.create(
        app_client=app_client,
        external_user_id="user-123",
        platform="telegram",
        _credentials="",
    )

    resp = post_json(
        api,
        "/api/v1/social/post",
        {"content": "hi", "platforms": ["telegram"]},
    )

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["status"] == "pending"
    assert mock_task.delay.call_count == 1
    assert PostLog.objects.filter(platform="telegram", status="pending").exists()


@patch("apps.social.views_posting.post_to_platform")
def test_post_invalid_platform_marked_failed(mock_task, api, post_json):
    """Unknown platform creates a failed PostLog without dispatching."""
    resp = post_json(
        api,
        "/api/v1/social/post",
        {"content": "hi", "platforms": ["myspace"]},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert items[0]["status"] == "failed"
    assert "Unknown platform" in (items[0]["error"] or "")
    mock_task.delay.assert_not_called()


def test_list_platforms(api, client_and_key):
    """GET /platforms returns all adapters with registered flag."""
    app_client, _ = client_and_key
    SocialAccount.objects.create(
        app_client=app_client,
        external_user_id="user-123",
        platform="telegram",
        _credentials="",
    )

    resp = api.get("/api/v1/social/platforms")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 20
    names = {p["name"]: p for p in data}
    assert names["telegram"]["registered"] is True
    assert names["discord"]["registered"] is False


def test_list_post_logs(api, client_and_key):
    """GET /logs returns post history filtered by platform."""
    app_client, _ = client_and_key
    PostLog.objects.create(
        app_client=app_client,
        external_user_id="user-123",
        platform="telegram",
        content="a",
        status="success",
    )
    PostLog.objects.create(
        app_client=app_client,
        external_user_id="user-123",
        platform="discord",
        content="b",
        status="failed",
        error="boom",
    )

    resp = api.get("/api/v1/social/logs?platform=telegram")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["platform"] == "telegram"
    assert items[0]["status"] == "success"


def test_health_endpoint_includes_social(db):
    """GET /api/v1/health/ reports social adapters + storage + notify."""
    c = Client()
    resp = c.get("/api/v1/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert "social" in data
    assert "platforms" in data["social"]
    assert data["social"]["adapters_registered"] >= 20
    assert "storage" in data
    assert "notify" in data
