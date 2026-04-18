"""Integration tests for ApiKeyAuthMiddleware.

Covers:
    - Missing X-API-Key → 401
    - Invalid key → 401
    - Inactive AppClient → 401
    - Valid key → passes middleware
    - Exempt paths → bypass auth
    - Rate limiting → 429
"""

import pytest
from django.test import Client

from apps.core.auth.middleware import _rate_buckets
from apps.core.auth.models import AppClient

PROTECTED_URL = "/api/v1/social/platforms/"


@pytest.fixture(autouse=True)
def _reset_rate_buckets():
    """Prevent module-level bucket leakage between tests."""
    _rate_buckets.clear()
    yield
    _rate_buckets.clear()


@pytest.fixture
def extra_app(db):
    """Secondary AppClient used by tests that need a custom rate_limit."""
    app, raw_key = AppClient.create_client(
        name="auth-test-extra",
        permissions=["social"],
        rate_limit=2,
    )
    return app, raw_key


# ---------- Rejection cases ----------


def test_missing_api_key_returns_401(db):
    resp = Client().get(PROTECTED_URL)
    assert resp.status_code == 401
    assert "X-API-Key header required" in resp.json()["detail"]


def test_invalid_api_key_returns_401(db):
    c = Client()
    c.defaults["HTTP_X_API_KEY"] = "invalid_garbage_key_xyz"
    resp = c.get(PROTECTED_URL)
    assert resp.status_code == 401
    assert "Invalid or inactive API key" in resp.json()["detail"]


def test_inactive_app_client_returns_401(db):
    app, raw_key = AppClient.create_client(
        name="auth-test-disabled",
        permissions=["social"],
    )
    app.is_active = False
    app.save(update_fields=["is_active"])

    c = Client()
    c.defaults["HTTP_X_API_KEY"] = raw_key
    resp = c.get(PROTECTED_URL)
    assert resp.status_code == 401
    assert "Invalid or inactive API key" in resp.json()["detail"]


# ---------- Acceptance cases ----------


def test_valid_api_key_passes_middleware(api_client):
    """Valid key should not be blocked by middleware (anything != 401 is fine)."""
    resp = api_client.get(PROTECTED_URL)
    assert resp.status_code != 401


# ---------- Exempt paths ----------


def test_health_endpoint_bypasses_auth(db):
    resp = Client().get("/api/v1/health/")
    assert resp.status_code == 200


def test_docs_endpoint_bypasses_auth(db):
    resp = Client().get("/api/v1/docs")
    assert resp.status_code != 401


# ---------- Rate limiting ----------


def test_rate_limit_exceeded_returns_429(extra_app):
    """Client with rate_limit=2 hits 429 on third request within the window."""
    _, raw_key = extra_app
    c = Client()
    c.defaults["HTTP_X_API_KEY"] = raw_key

    r1 = c.get(PROTECTED_URL)
    r2 = c.get(PROTECTED_URL)
    r3 = c.get(PROTECTED_URL)

    assert r1.status_code != 429
    assert r2.status_code != 429
    assert r3.status_code == 429
    assert "Rate limit exceeded" in r3.json()["detail"]
