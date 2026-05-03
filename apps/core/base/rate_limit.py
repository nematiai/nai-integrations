"""Rate-limit helpers for NEMI public endpoints.

Wraps django-ratelimit so view code stays a single decorator.
Returns a uniform JSON 429 response shape.

Layered with the per-AppClient quota in apps/core/auth/middleware.py:
this module enforces per-IP and per-app endpoint-level limits;
the middleware enforces the AppClient.rate_limit_per_minute quota.
Health and OpenAPI docs are not wrapped — they stay exempt.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


def _retry_after_seconds(rate: str) -> int:
    """Best-effort 'N/m'/'N/s'/'N/h' -> seconds. Defaults to 60."""
    if not rate or "/" not in rate:
        return 60
    unit = rate.rsplit("/", 1)[1].lower()
    return {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit, 60)


def _build_429(request: HttpRequest, rate: str, scope: str) -> JsonResponse:
    retry_after = _retry_after_seconds(rate)
    logger.warning(
        "Rate limit hit: scope=%s path=%s ip=%s",
        scope,
        request.path,
        request.META.get("REMOTE_ADDR", "?"),
    )
    return JsonResponse(
        {"error": "rate_limited", "retry_after": retry_after},
        status=429,
        headers={"Retry-After": str(retry_after)},
    )


def _app_client_key(group: str, request: HttpRequest) -> str:
    """Key by AppClient id when authenticated, else by IP."""
    client = getattr(request, "app_client", None)
    if client is not None:
        return f"app:{client.id}"
    return f"ip:{request.META.get('REMOTE_ADDR', '0.0.0.0')}"


def _make_decorator(setting_name: str, key, scope: str) -> Callable:
    """Build a decorator that reads the rate from settings at call time."""

    def decorator(view_func):
        rate_callable = lambda group, request: getattr(  # noqa: E731
            settings, setting_name
        )

        @ratelimit(key=key, rate=rate_callable, block=False)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if getattr(request, "limited", False):
                return _build_429(request, getattr(settings, setting_name), scope)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


rate_limit_anon = _make_decorator("RATE_LIMIT_ANON", "ip", "anon")
rate_limit_user = _make_decorator("RATE_LIMIT_USER", _app_client_key, "user")
rate_limit_oauth = _make_decorator("RATE_LIMIT_OAUTH", "ip", "oauth")
