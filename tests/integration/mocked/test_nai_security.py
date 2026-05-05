"""nai-security integration smoke tests.

Verifies wire-up only. The package's own suite (158 tests) covers
internal correctness; here we just confirm:
- middleware is loaded in the right order
- /api/v1/health/ is exempt
- a BlockedIP row blocks a non-exempt request with 403
- RateLimitRule rows are creatable (admin model surface works)
"""

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client


@pytest.fixture(autouse=True)
def _clear_security_cache():
    cache.clear()
    yield
    cache.clear()


def test_security_middleware_loaded():
    assert (
        "nai_security.middleware.SecurityMiddleware" in settings.MIDDLEWARE
    ), "nai_security.SecurityMiddleware must be in MIDDLEWARE"
    auth_idx = settings.MIDDLEWARE.index(
        "django.contrib.auth.middleware.AuthenticationMiddleware"
    )
    sec_idx = settings.MIDDLEWARE.index(
        "nai_security.middleware.SecurityMiddleware"
    )
    assert sec_idx > auth_idx, "SecurityMiddleware must come after AuthenticationMiddleware"


def test_health_endpoint_exempt_from_security(db):
    """Health endpoint stays reachable even from an IP that would be blocked."""
    from nai_security.models import BlockedIP

    BlockedIP.objects.create(ip_address="10.0.0.99", is_active=True, reason="test")
    c = Client()
    resp = c.get("/api/v1/health/", REMOTE_ADDR="10.0.0.99")
    assert resp.status_code == 200


def test_blocked_ip_returns_403(db):
    """A non-exempt API path returns 403 when REMOTE_ADDR is blocked."""
    from nai_security.models import BlockedIP

    BlockedIP.objects.create(ip_address="10.0.0.42", is_active=True, reason="test")
    c = Client()
    resp = c.get("/api/v1/social/platforms", REMOTE_ADDR="10.0.0.42")
    assert resp.status_code == 403


def test_rate_limit_rule_admin_creatable(db):
    """RateLimitRule rows persist via ORM (admin surface uses the same path)."""
    from nai_security.models import RateLimitRule

    rule = RateLimitRule.objects.create(
        name="auth-register-anon",
        path_pattern="/api/v1/auth/register",
        rate="30/m",
        method="POST",
        is_active=True,
    )
    assert rule.pk is not None
    assert RateLimitRule.objects.filter(name="auth-register-anon").exists()
