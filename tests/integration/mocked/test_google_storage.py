"""Integration tests for Google Drive storage endpoints (mocked).

All external HTTP is intercepted via the ``responses`` library (mock_requests
fixture).  GoogleDriveService uses ``requests``, not ``httpx``.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.storage.google.models import GoogleAuth

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
REDIRECT_URI = "http://localhost:8012/storage/google/callback"

google_settings = override_settings(
    GOOGLE_DRIVE_REDIRECT_URI=REDIRECT_URI,
    GOOGLE_OAUTH2_CLIENT_ID="test-client-id",
    GOOGLE_OAUTH2_CLIENT_SECRET="test-client-secret",
)


def _make_google_auth(app_client_obj, user_id="test-user-123", expires_in_hours=1):
    auth = GoogleAuth(
        app_client=app_client_obj,
        external_user_id=user_id,
        email="user@example.com",
        display_name="Test User",
        account_id="google-user-001",
        scopes=["drive.readonly", "userinfo.email"],
        expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        is_active=True,
    )
    auth.decrypted_access_token = "fake-access-token-abc"
    auth.decrypted_refresh_token = "fake-refresh-token-xyz"
    auth.save()
    return auth


# --- TEST 1: status when not connected ---


@google_settings
def test_status_not_connected(api_client):
    resp = api_client.get("/api/v1/storage/google/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["message"] == "Not connected"


# --- TEST 2: status when connected, token fresh ---


@google_settings
def test_status_connected_fresh_token(app_client, api_client):
    app, _ = app_client
    _make_google_auth(app)
    resp = api_client.get("/api/v1/storage/google/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["email"] == "user@example.com"


# --- TEST 3: status when token needs refresh, refresh succeeds ---


@google_settings
def test_status_token_refresh_succeeds(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_google_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST",
        TOKEN_URL,
        json={
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
        status=200,
    )

    resp = api_client.get("/api/v1/storage/google/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True


# --- TEST 4: authorize returns oauth URL ---


@google_settings
def test_authorize_returns_oauth_url(api_client):
    resp = api_client.post("/api/v1/storage/google/authorize/")
    assert resp.status_code == 200
    body = resp.json()
    assert "accounts.google.com" in body["authorization_url"]
    assert body["message"]


# --- TEST 5: callback with valid code creates GoogleAuth ---


@google_settings
def test_callback_valid_code_creates_auth(app_client, api_client, mock_requests):
    app, _ = app_client

    mock_requests.add(
        "POST",
        TOKEN_URL,
        json={
            "access_token": "real-access-token",
            "refresh_token": "real-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "drive.readonly",
        },
        status=200,
    )
    mock_requests.add(
        "GET",
        USERINFO_URL,
        json={
            "id": "google-user-real-001",
            "email": "real@example.com",
            "name": "Real User",
        },
        status=200,
    )

    resp = api_client.post("/api/v1/storage/google/callback/?code=valid-auth-code")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["email"] == "real@example.com"
    assert GoogleAuth.objects.filter(
        app_client=app,
        email="real@example.com",
    ).exists()


# --- TEST 6: callback missing code returns 400 ---


@google_settings
def test_callback_missing_code_returns_400(api_client):
    resp = api_client.post("/api/v1/storage/google/callback/")
    assert resp.status_code == 400


# --- TEST 7: disconnect when connected ---


@google_settings
def test_disconnect_when_connected(app_client, api_client, mock_requests):
    app, _ = app_client
    _make_google_auth(app)

    mock_requests.add("POST", REVOKE_URL, json={}, status=200)

    resp = api_client.delete("/api/v1/storage/google/disconnect/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False


# --- TEST 8: disconnect when not connected returns 404 ---


@google_settings
def test_disconnect_not_connected_returns_404(api_client):
    resp = api_client.delete("/api/v1/storage/google/disconnect/")
    assert resp.status_code == 404
