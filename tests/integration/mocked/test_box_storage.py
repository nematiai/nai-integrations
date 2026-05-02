"""Integration tests for Box storage endpoints (mocked).

All external HTTP is intercepted via the ``responses`` library (mock_requests
fixture).  BoxService uses ``requests``, not ``httpx``.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.storage.box.models import BoxAuth

TOKEN_URL = "https://api.box.com/oauth2/token"
USERINFO_URL = "https://api.box.com/2.0/users/me"
REVOKE_URL = "https://api.box.com/oauth2/revoke"
REDIRECT_URI = "http://localhost:8012/storage/box/callback"

box_settings = override_settings(
    BOX_CLIENT_ID="test-client-id",
    BOX_CLIENT_SECRET="test-client-secret",
    BOX_REDIRECT_URI=REDIRECT_URI,
)


def _make_box_auth(app_client_obj, user_id="test-user-123", expires_in_hours=1):
    auth = BoxAuth(
        app_client=app_client_obj,
        external_user_id=user_id,
        email="user@box.example",
        display_name="Test User",
        account_id="box-user-001",
        scopes=[],
        expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        is_active=True,
    )
    auth.decrypted_access_token = "fake-box-access-token"
    auth.decrypted_refresh_token = "fake-box-refresh-token"
    auth.save()
    return auth


# --- TEST 1: status when not connected ---


@box_settings
def test_status_not_connected(api_client):
    resp = api_client.get("/api/v1/storage/box/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False


# --- TEST 2: status when connected, token fresh ---


@box_settings
def test_status_connected_fresh_token(app_client, api_client):
    app, _ = app_client
    _make_box_auth(app)
    resp = api_client.get("/api/v1/storage/box/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["email"] == "user@box.example"


# --- TEST 3a: status when token expired, refresh succeeds ---


@box_settings
def test_status_token_refresh_succeeds(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_box_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST",
        TOKEN_URL,
        json={
            "access_token": "new-box-access",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
        status=200,
    )

    resp = api_client.get("/api/v1/storage/box/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["message"] == "Connected"


# --- TEST 3b: status when token expired, refresh fails ---


@box_settings
def test_status_token_refresh_fails(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_box_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST",
        TOKEN_URL,
        json={"error": "invalid_grant"},
        status=400,
    )

    resp = api_client.get("/api/v1/storage/box/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["message"] == "Token refresh failed"


# --- TEST 4: authorize returns box oauth URL ---


@box_settings
def test_authorize_returns_oauth_url(api_client):
    resp = api_client.post("/api/v1/storage/box/authorize/")
    assert resp.status_code == 200
    body = resp.json()
    assert "account.box.com/api/oauth2/authorize" in body["authorization_url"]
    assert body["message"]


# --- TEST 5: callback with valid code creates BoxAuth ---


@box_settings
def test_callback_valid_code_creates_auth(app_client, api_client, mock_requests):
    app, _ = app_client

    mock_requests.add(
        "POST",
        TOKEN_URL,
        json={
            "access_token": "real-box-access",
            "refresh_token": "real-box-refresh",
            "expires_in": 3600,
            "token_type": "bearer",
        },
        status=200,
    )
    mock_requests.add(
        "GET",
        USERINFO_URL,
        json={
            "id": "box-user-real-001",
            "login": "real@box.example",
            "name": "Real Box User",
        },
        status=200,
    )

    resp = api_client.post("/api/v1/storage/box/callback/?code=valid-auth-code")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["email"] == "real@box.example"
    assert BoxAuth.objects.filter(
        app_client=app,
        email="real@box.example",
    ).exists()


# --- TEST 6: callback missing code returns 400 ---


@box_settings
def test_callback_missing_code_returns_400(api_client):
    resp = api_client.post("/api/v1/storage/box/callback/")
    assert resp.status_code == 400


# --- TEST 7: disconnect when connected ---


@box_settings
def test_disconnect_when_connected(app_client, api_client, mock_requests):
    app, _ = app_client
    _make_box_auth(app)

    mock_requests.add("POST", REVOKE_URL, json={}, status=200)

    resp = api_client.delete("/api/v1/storage/box/disconnect/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# --- TEST 8: disconnect when not connected returns 404 ---


@box_settings
def test_disconnect_not_connected_returns_400(api_client):
    resp = api_client.delete("/api/v1/storage/box/disconnect/")
    assert resp.status_code == 404
