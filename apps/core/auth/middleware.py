"""API key authentication middleware for NEMI."""

import logging
import time
from collections import defaultdict

from django.http import JsonResponse

from .models import AppClient

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter (per worker process)
_rate_buckets: dict[int, list[float]] = defaultdict(list)

API_KEY_HEADER = "HTTP_X_API_KEY"
API_PREFIX = "/api/"
EXEMPT_PATHS = (
    "/admin/",
    "/api/v1/health/",
    "/api/v1/auth/register",
    "/api/docs",
    "/api/openapi.json",
)


class ApiKeyAuthMiddleware:
    """
    Middleware that authenticates /api/* requests via X-API-Key header.
    Attaches request.app_client on success.
    Non-API paths (admin, static) pass through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.app_client = None

        if not request.path.startswith(API_PREFIX):
            return self.get_response(request)

        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        raw_key = request.META.get(API_KEY_HEADER, "")
        if not raw_key:
            return JsonResponse({"detail": "X-API-Key header required"}, status=401)

        client = AppClient.authenticate(raw_key)
        if client is None:
            logger.warning("Invalid API key attempt: %s...", raw_key[:8])
            return JsonResponse({"detail": "Invalid or inactive API key"}, status=401)

        if _is_rate_limited(client):
            return JsonResponse({"detail": "Rate limit exceeded"}, status=429)

        request.app_client = client
        return self.get_response(request)


def _is_rate_limited(client: AppClient) -> bool:
    """Check if client has exceeded their per-minute rate limit."""
    now = time.time()
    window = 60.0
    bucket = _rate_buckets[client.id]

    # Prune old entries
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= client.rate_limit_per_minute:
        return True
    bucket.append(now)
    return False
