"""Integration tests for Dropbox storage endpoints (mocked).

All external HTTP is intercepted via the ``responses`` library (mock_requests
fixture).  DropboxService uses ``requests``, not ``httpx``.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.storage.dropbox.models import DropboxAuth

TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
ACCOUNT_URL = "https://api.dropboxapi.com/2/users/get_current_account"
REVOKE_URL = "https://api.dropboxapi.com/2/auth/token/revoke"
REDIRECT_URI = "http://localhost:8012/storage/dropbox/callback"

dropbox_settings = override_settings(
    DROPBOX_CLIENT_ID="test-client-id",
    DROPBOX_CLIENT_SECRET="test-client-secret",
    DROPBOX_REDIRECT_URI=REDIRECT_URI,
)


def _make_dropbox_auth(app_client_obj, user_id="test-user-123", expires_in_hours=1):
    auth = DropboxAuth(
        app_client=app_client_obj,
        external_user_id=user_id,
        email="user@dropbox.example",
        display_name="Test User",
        account_id="dbx-user-001",
        scopes=[],
        expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        is_active=True,
    )
    auth.decrypted_access_token = "fake-dbx-access-token"
    auth.decrypted_refresh_token = "fake-dbx-refresh-token"
    auth.save()
    return auth


# --- TEST 1: status when not connected ---


@dropbox_settings
def test_status_not_connected(api_client):
    resp = api_client.get("/api/v1/storage/dropbox/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False


# --- TEST 2: status when connected, token fresh ---


@dropbox_settings
def test_status_connected_fresh_token(app_client, api_client):
    app, _ = app_client
    _make_dropbox_auth(app)
    resp = api_client.get("/api/v1/storage/dropbox/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["email"] == "user@dropbox.example"


# --- TEST 3a: status when token expired, refresh succeeds ---


@dropbox_settings
def test_status_token_refresh_succeeds(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_dropbox_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST", TOKEN_URL,
        json={
            "access_token": "new-dbx-access",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
        status=200,
    )

    resp = api_client.get("/api/v1/storage/dropbox/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["message"] == "Connected"


# --- TEST 3b: status when token expired, refresh fails ---


@dropbox_settings
def test_status_token_refresh_fails(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_dropbox_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST", TOKEN_URL,
        json={"error": "invalid_grant"},
        status=400,
    )

    resp = api_client.get("/api/v1/storage/dropbox/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["message"] == "Token refresh failed"


# --- TEST 4: authorize returns dropbox oauth URL ---


@dropbox_settings
def test_authorize_returns_oauth_url(api_client):
    resp = api_client.post("/api/v1/storage/dropbox/authorize/")
    assert resp.status_code == 200
    body = resp.json()
    assert "dropbox.com/oauth2/authorize" in body["authorization_url"]
    assert body["message"]


# --- TEST 5: callback with valid code creates DropboxAuth ---
# NOTE: Dropbox get_account_info uses POST (not GET) and
# returns nested name.display_name structure.


@dropbox_settings
def test_callback_valid_code_creates_auth(app_client, api_client, mock_requests):
    app, _ = app_client

    mock_requests.add(
        "POST", TOKEN_URL,
        json={
            "access_token": "real-dbx-access",
            "refresh_token": "real-dbx-refresh",
            "expires_in": 14400,
            "token_type": "bearer",
        },
        status=200,
    )
    mock_requests.add(
        "POST", ACCOUNT_URL,
        json={
            "account_id": "dbid:real-dbx-001",
            "email": "real@dropbox.example",
            "name": {"display_name": "Real Dropbox User"},
        },
        status=200,
    )

    resp = api_client.post(
        "/api/v1/storage/dropbox/callback/?code=valid-auth-code"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["email"] == "real@dropbox.example"
    assert DropboxAuth.objects.filter(
        app_client=app, email="real@dropbox.example",
    ).exists()


# --- TEST 6: callback missing code returns 400 ---


@dropbox_settings
def test_callback_missing_code_returns_400(api_client):
    resp = api_client.post("/api/v1/storage/dropbox/callback/")
    assert resp.status_code == 400


# --- TEST 7: disconnect when connected ---
# Dropbox revoke goes through _make_api_request, hitting
# https://api.dropboxapi.com/2/auth/token/revoke (POST)


@dropbox_settings
def test_disconnect_when_connected(app_client, api_client, mock_requests):
    app, _ = app_client
    _make_dropbox_auth(app)

    mock_requests.add("POST", REVOKE_URL, json={}, status=200)

    resp = api_client.delete("/api/v1/storage/dropbox/disconnect/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# --- TEST 8: disconnect when not connected returns 404 ---


@dropbox_settings
def test_disconnect_not_connected_returns_400(api_client):
    resp = api_client.delete("/api/v1/storage/dropbox/disconnect/")
    assert resp.status_code == 404
