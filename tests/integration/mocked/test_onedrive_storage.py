"""Integration tests for OneDrive storage endpoints (mocked).

All external HTTP is intercepted via the ``responses`` library (mock_requests
fixture).  OneDriveService uses ``requests``, not ``httpx``.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from apps.storage.onedrive.models import OneDriveAuth

TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
ACCOUNT_URL = "https://graph.microsoft.com/v1.0/me"
REDIRECT_URI = "http://localhost:8012/storage/onedrive/callback"

onedrive_settings = override_settings(
    ONEDRIVE_CLIENT_ID="test-client-id",
    ONEDRIVE_CLIENT_SECRET="test-client-secret",
    ONEDRIVE_REDIRECT_URI=REDIRECT_URI,
)


def _make_onedrive_auth(app_client_obj, user_id="test-user-123", expires_in_hours=1):
    auth = OneDriveAuth(
        app_client=app_client_obj,
        external_user_id=user_id,
        email="user@onedrive.example",
        display_name="Test User",
        account_id="ms-user-001",
        scopes=[],
        expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        is_active=True,
    )
    auth.decrypted_access_token = "fake-ms-access-token"
    auth.decrypted_refresh_token = "fake-ms-refresh-token"
    auth.save()
    return auth


# --- TEST 1: status when not connected ---


@onedrive_settings
def test_status_not_connected(api_client):
    resp = api_client.get("/api/v1/storage/onedrive/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False


# --- TEST 2: status when connected, token fresh ---


@onedrive_settings
def test_status_connected_fresh_token(app_client, api_client):
    app, _ = app_client
    _make_onedrive_auth(app)
    resp = api_client.get("/api/v1/storage/onedrive/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["email"] == "user@onedrive.example"


# --- TEST 3a: status when token expired, refresh succeeds ---


@onedrive_settings
def test_status_token_refresh_succeeds(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_onedrive_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST", TOKEN_URL,
        json={
            "access_token": "new-ms-access",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
        status=200,
    )

    resp = api_client.get("/api/v1/storage/onedrive/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["message"] == "Connected"


# --- TEST 3b: status when token expired, refresh fails ---


@onedrive_settings
def test_status_token_refresh_fails(app_client, api_client, mock_requests):
    app, _ = app_client
    auth = _make_onedrive_auth(app, expires_in_hours=0)
    auth.expires_at = timezone.now() - timedelta(minutes=1)
    auth.save()

    mock_requests.add(
        "POST", TOKEN_URL,
        json={"error": "invalid_grant"},
        status=400,
    )

    resp = api_client.get("/api/v1/storage/onedrive/status/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["message"] == "Token refresh failed"


# --- TEST 4: authorize returns Microsoft oauth URL ---


@onedrive_settings
def test_authorize_returns_oauth_url(api_client):
    resp = api_client.post("/api/v1/storage/onedrive/authorize/")
    assert resp.status_code == 200
    body = resp.json()
    assert "login.microsoftonline.com" in body["authorization_url"]
    assert body["message"]


# --- TEST 5: callback with valid code creates OneDriveAuth ---
# NOTE: OneDrive get_account_info uses GET (not POST like Dropbox) and
# returns flat response with userPrincipalName / mail fields.


@onedrive_settings
def test_callback_valid_code_creates_auth(app_client, api_client, mock_requests):
    app, _ = app_client

    mock_requests.add(
        "POST", TOKEN_URL,
        json={
            "access_token": "real-ms-access",
            "refresh_token": "real-ms-refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
        status=200,
    )
    mock_requests.add(
        "GET", ACCOUNT_URL,
        json={
            "id": "ms-real-001",
            "userPrincipalName": "real@onedrive.example",
            "displayName": "Real OneDrive User",
        },
        status=200,
    )

    resp = api_client.post(
        "/api/v1/storage/onedrive/callback/?code=valid-auth-code"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["email"] == "real@onedrive.example"
    assert OneDriveAuth.objects.filter(
        app_client=app, email="real@onedrive.example",
    ).exists()


# --- TEST 6: callback missing code returns 400 ---


@onedrive_settings
def test_callback_missing_code_returns_400(api_client):
    resp = api_client.post("/api/v1/storage/onedrive/callback/")
    assert resp.status_code == 400


# --- TEST 7: disconnect when connected (no revoke URL) ---
# Microsoft Graph has no public token revoke endpoint.
# disconnect() just sets is_active=False. No upstream HTTP mock needed.


@onedrive_settings
def test_disconnect_when_connected(app_client, api_client):
    app, _ = app_client
    _make_onedrive_auth(app)

    resp = api_client.delete("/api/v1/storage/onedrive/disconnect/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# --- TEST 8: disconnect when not connected returns 404 ---


@onedrive_settings
def test_disconnect_not_connected_returns_400(api_client):
    resp = api_client.delete("/api/v1/storage/onedrive/disconnect/")
    assert resp.status_code == 404


# --- TEST 9: callback when get_account_info fails returns 500 ---


@onedrive_settings
def test_callback_account_info_failure_returns_500(api_client, mock_requests):
    mock_requests.add(
        "POST", TOKEN_URL,
        json={"access_token": "x", "refresh_token": "y", "expires_in": 3600},
        status=200,
    )
    mock_requests.add(
        "GET", ACCOUNT_URL,
        json={"error": "forbidden"},
        status=403,
    )
    resp = api_client.post("/api/v1/storage/onedrive/callback/?code=x")
    assert resp.status_code == 500
