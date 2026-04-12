"""Shared fixtures for social app tests."""

import json

import pytest
from django.test import Client

from apps.core.auth.models import AppClient


@pytest.fixture
def client_and_key(db):
    """Create an AppClient with social permission; return (client, raw_key)."""
    app, raw_key = AppClient.create_client(
        name="test-app", permissions=["social"], rate_limit=1000
    )
    return app, raw_key


@pytest.fixture
def api(client_and_key):
    """Django test client with X-API-Key and X-User-Id pre-set."""
    _, raw_key = client_and_key
    c = Client()
    c.defaults["HTTP_X_API_KEY"] = raw_key
    c.defaults["HTTP_X_USER_ID"] = "user-123"
    return c


@pytest.fixture
def post_json():
    """Helper: POST a dict as JSON."""

    def _post(c: Client, url: str, body: dict):
        return c.post(url, data=json.dumps(body), content_type="application/json")

    return _post
