"""Integration tests for POST /api/v1/social/post.

Covers payload validation, unknown platforms, missing accounts,
happy-path Telegram posting, upstream errors, and multi-platform dispatch.
All upstream HTTP is intercepted via respx (no real network traffic).
"""

import httpx

from apps.social.base.models import PostLog, SocialAccount

POST_URL = "/api/v1/social/post"
TG_SEND_URL = "https://api.telegram.org/botFAKETOKEN123/sendMessage"


def _make_telegram_account(app_client_obj, user_id="test-user-123"):
    """Create a SocialAccount with Fernet-encrypted telegram creds."""
    acct = SocialAccount(
        app_client=app_client_obj,
        external_user_id=user_id,
        platform="telegram",
        is_active=True,
    )
    acct.decrypted_credentials = {
        "bot_token": "FAKETOKEN123",
        "chat_id": "-100111222",
    }
    acct.save()
    return acct


def _tg_ok(message_id=42):
    return httpx.Response(
        200,
        json={
            "ok": True,
            "result": {"message_id": message_id, "chat": {"id": -100111222}},
        },
    )


def _tg_error(status=400):
    return httpx.Response(
        status,
        json={
            "ok": False,
            "error_code": status,
            "description": "Bad Request",
        },
    )


# --- TEST 1: payload validation ---


def test_missing_content_returns_422(api_client, post_json):
    resp = post_json(api_client, POST_URL, {"platforms": ["telegram"]})
    assert resp.status_code == 422


# --- TEST 2: unknown platform ---


def test_unknown_platform_creates_failed_log(app_client, api_client, post_json):
    resp = post_json(
        api_client,
        POST_URL,
        {"content": "hi", "platforms": ["not_a_platform"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["status"] == "failed"
    assert "Unknown platform" in (body[0]["error"] or "")
    log = PostLog.objects.get(platform="not_a_platform")
    assert log.status == "failed"


# --- TEST 3: no connected account ---


def test_no_account_marks_log_failed(app_client, api_client, post_json):
    resp = post_json(
        api_client,
        POST_URL,
        {"content": "hello", "platforms": ["telegram"]},
    )
    assert resp.status_code == 200
    log = PostLog.objects.get(platform="telegram")
    assert log.status == "failed"
    assert "No active telegram account" in (log.error or "")


# --- TEST 4: happy path ---


def test_telegram_success(
    app_client,
    api_client,
    post_json,
    mock_httpx,
):
    app, _ = app_client
    _make_telegram_account(app)
    mock_httpx.post(TG_SEND_URL).mock(return_value=_tg_ok(42))

    resp = post_json(
        api_client,
        POST_URL,
        {"content": "hello world", "platforms": ["telegram"]},
    )
    assert resp.status_code == 200
    log = PostLog.objects.get(platform="telegram")
    assert log.status == "success"
    assert log.external_id == "42"
    assert log.posted_at is not None


# --- TEST 5: upstream error ---


def test_telegram_upstream_error_marks_failed(
    app_client,
    api_client,
    post_json,
    mock_httpx,
):
    app, _ = app_client
    _make_telegram_account(app)
    mock_httpx.post(TG_SEND_URL).mock(return_value=_tg_error(400))

    resp = post_json(
        api_client,
        POST_URL,
        {"content": "bad", "platforms": ["telegram"]},
    )
    assert resp.status_code == 200
    log = PostLog.objects.get(platform="telegram")
    assert log.status == "failed"
    assert log.error


# --- TEST 6: multi-platform ---


def test_multi_platform_mixed_results(
    app_client,
    api_client,
    post_json,
    mock_httpx,
):
    app, _ = app_client
    _make_telegram_account(app)
    mock_httpx.post(TG_SEND_URL).mock(return_value=_tg_ok(99))

    resp = post_json(
        api_client,
        POST_URL,
        {"content": "ping", "platforms": ["telegram", "not_real"]},
    )
    assert resp.status_code == 200
    assert PostLog.objects.filter(
        platform="telegram",
        status="success",
    ).exists()
    assert PostLog.objects.filter(
        platform="not_real",
        status="failed",
    ).exists()
