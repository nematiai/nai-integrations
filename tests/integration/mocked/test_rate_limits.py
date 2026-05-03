"""Endpoint-level rate-limit tests (#20).

Cache is flushed between tests so each case starts at zero.
No time.sleep — limits are tightened via override_settings and triggered
by hitting the same key (IP or AppClient id) in a tight loop.
"""

import json

import pytest
from django.core.cache import cache
from django.test import Client, override_settings


PUBLIC_REGISTER = "/api/v1/auth/register"
HEALTH = "/api/v1/health/"
BOX_CALLBACK = "/api/v1/storage/box/callback/"


@pytest.fixture(autouse=True)
def _flush_cache():
    cache.clear()
    yield
    cache.clear()


def _register_payload(name: str) -> dict:
    return {
        "name": name,
        "permissions": ["social"],
        "rate_limit_per_minute": 60,
    }


def _post_json(c: Client, url: str, body: dict, **extra):
    return c.post(
        url, data=json.dumps(body), content_type="application/json", **extra
    )


@override_settings(RATE_LIMIT_ANON="2/m")
def test_anon_endpoint_throttled_after_limit(db):
    c = Client()
    r1 = _post_json(c, PUBLIC_REGISTER, _register_payload("anon-rl-1"))
    r2 = _post_json(c, PUBLIC_REGISTER, _register_payload("anon-rl-2"))
    r3 = _post_json(c, PUBLIC_REGISTER, _register_payload("anon-rl-3"))
    assert r1.status_code in (201, 400)
    assert r2.status_code in (201, 400)
    assert r3.status_code == 429


@override_settings(RATE_LIMIT_USER="3/m", RATE_LIMIT_ANON="1/m")
def test_authenticated_endpoint_higher_limit(api_client, db):
    """Authenticated endpoints honor RATE_LIMIT_USER, not RATE_LIMIT_ANON."""
    url = "/api/v1/social/platforms"
    statuses = [api_client.get(url).status_code for _ in range(3)]
    assert all(s != 429 for s in statuses)
    assert api_client.get(url).status_code == 429


@override_settings(RATE_LIMIT_OAUTH="1/m")
def test_oauth_callback_strict_limit(api_client, db):
    api_client.post(BOX_CALLBACK + "?code=x")
    r2 = api_client.post(BOX_CALLBACK + "?code=x")
    assert r2.status_code == 429


def test_health_check_not_throttled(db):
    c = Client()
    statuses = [c.get(HEALTH).status_code for _ in range(50)]
    assert all(s == 200 for s in statuses)


@override_settings(RATE_LIMIT_ANON="1/m")
def test_429_response_shape(db):
    c = Client()
    _post_json(c, PUBLIC_REGISTER, _register_payload("shape-1"))
    r = _post_json(c, PUBLIC_REGISTER, _register_payload("shape-2"))
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limited"
    assert isinstance(body["retry_after"], int) and body["retry_after"] > 0


@override_settings(RATE_LIMIT_ANON="1/m")
def test_429_includes_retry_after_header(db):
    c = Client()
    _post_json(c, PUBLIC_REGISTER, _register_payload("hdr-1"))
    r = _post_json(c, PUBLIC_REGISTER, _register_payload("hdr-2"))
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "60"
