"""Shared fixtures for integration tests (mocked + live).

These fixtures mirror the pattern in apps/social/conftest.py but are
promoted to a shared location so both mocked and live integration
tests can use them consistently.
"""

import json
import os

import pytest
from django.test import Client

from apps.core.auth.models import AppClient


@pytest.fixture
def app_client(db):
    """Create an AppClient with all Phase 1 permissions; return (app, raw_key).

    Permissions match Phase 1 scope: social posting, storage, notify.
    """
    name = os.environ.get("NEMI_TEST_APP_NAME", "integration-test-app")
    app, raw_key = AppClient.create_client(
        name=name,
        permissions=["social", "storage", "notify"],
        rate_limit=10000,
    )
    return app, raw_key


@pytest.fixture
def api_client(app_client):
    """Django test client pre-configured with X-API-Key and X-User-Id headers."""
    _, raw_key = app_client
    user_id = os.environ.get("NEMI_TEST_USER_ID", "test-user-123")
    c = Client()
    c.defaults["HTTP_X_API_KEY"] = raw_key
    c.defaults["HTTP_X_USER_ID"] = user_id
    return c


@pytest.fixture
def post_json():
    """Helper: POST a dict as JSON body."""

    def _post(c: Client, url: str, body: dict):
        return c.post(
            url,
            data=json.dumps(body),
            content_type="application/json",
        )

    return _post
