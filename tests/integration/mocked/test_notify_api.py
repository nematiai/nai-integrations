"""Mocked integration tests for the Notify API (channels + send)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.notify.models import NotificationChannel, NotificationLog

pytestmark = pytest.mark.django_db


def _make_slack_channel(name: str = "slack-test") -> NotificationChannel:
    return NotificationChannel.objects.create(
        name=name,
        service_type="slack",
        config={"webhook_url": "https://hooks.slack.com/services/T1/B1/XYZ"},
        is_active=True,
        created_by=None,
    )


# ── Channel CRUD ─────────────────────────────────────────────


def test_create_channel_success(api_client, post_json):
    payload = {
        "name": "my-slack",
        "service_type": "slack",
        "config": {"webhook_url": "https://hooks.slack.com/services/T1/B1/XYZ"},
    }
    resp = post_json(api_client, "/api/v1/notify/channels/", payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "my-slack"
    assert body["service_type"] == "slack"
    assert NotificationChannel.objects.filter(name="my-slack").exists()


def test_create_channel_unknown_service_type(api_client, post_json):
    payload = {"name": "bad", "service_type": "not_a_real_service", "config": {}}
    resp = post_json(api_client, "/api/v1/notify/channels/", payload)
    assert resp.status_code == 400
    body = resp.json()
    assert "config" in body["detail"]
    assert "service_type" in body["detail"]["config"]
    assert "Unknown service type" in body["detail"]["config"]["service_type"]


def test_create_channel_missing_required_config(api_client, post_json):
    payload = {"name": "missing-url", "service_type": "slack", "config": {}}
    resp = post_json(api_client, "/api/v1/notify/channels/", payload)
    assert resp.status_code == 400
    body = resp.json()
    assert "webhook_url" in body["detail"]["config"]


def test_list_channels(api_client):
    _make_slack_channel("ch-a")
    _make_slack_channel("ch-b")
    resp = api_client.get("/api/v1/notify/channels/")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "ch-a" in names
    assert "ch-b" in names


def test_patch_channel_deactivate(api_client):
    ch = _make_slack_channel("to-disable")
    resp = api_client.patch(
        f"/api/v1/notify/channels/{ch.id}/",
        data=json.dumps({"is_active": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    ch.refresh_from_db()
    assert ch.is_active is False


def test_delete_channel(api_client):
    ch = _make_slack_channel("to-delete")
    resp = api_client.delete(f"/api/v1/notify/channels/{ch.id}/")
    assert resp.status_code == 204
    assert not NotificationChannel.objects.filter(id=ch.id).exists()


# ── Send ─────────────────────────────────────────────────────


def test_send_success(api_client, post_json):
    ch = _make_slack_channel("send-success")
    with patch("apps.notify.services.apprise.Apprise") as mock_cls:
        mock_obj = MagicMock()
        mock_obj.notify.return_value = True
        mock_cls.return_value = mock_obj

        payload = {"title": "Hello", "body": "World", "channel_ids": [ch.id]}
        resp = post_json(api_client, "/api/v1/notify/send/", payload)

    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "sent"

    log = NotificationLog.objects.get(channel=ch, title="Hello")
    assert log.status == "sent"
    assert log.sent_at is not None
    mock_obj.notify.assert_called_once_with(title="Hello", body="World")


def test_send_failure(api_client, post_json):
    ch = _make_slack_channel("send-failure")
    with patch("apps.notify.services.apprise.Apprise") as mock_cls:
        mock_obj = MagicMock()
        mock_obj.notify.return_value = False
        mock_cls.return_value = mock_obj

        payload = {"title": "Ping", "body": "Test", "channel_ids": [ch.id]}
        resp = post_json(api_client, "/api/v1/notify/send/", payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body[0]["status"] == "failed"

    log = NotificationLog.objects.get(channel=ch, title="Ping")
    assert log.status == "failed"
    assert "Apprise returned False" in (log.error_message or "")
