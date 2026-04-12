"""Health check utilities for NEMI."""

import logging
from typing import Any

from django.db import connection

logger = logging.getLogger(__name__)


def check_database() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        from django.conf import settings
        from redis import Redis

        r = Redis.from_url(settings.REDIS_URL)
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


def get_social_status() -> dict[str, Any]:
    """Return the list of registered social adapters."""
    try:
        from apps.social.registry import ADAPTERS

        platforms = sorted(ADAPTERS.keys())
        return {
            "status": "ok",
            "adapters_registered": len(platforms),
            "platforms": platforms,
        }
    except Exception as e:
        logger.error("Social health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


def get_storage_status() -> dict[str, Any]:
    """Return the list of configured storage providers."""
    providers = ["box", "dropbox", "google", "onedrive"]
    return {"status": "ok", "providers": providers}


def get_notify_status() -> dict[str, Any]:
    """Return notify subsystem status."""
    try:
        import apprise  # noqa: F401

        return {"status": "ok"}
    except Exception as e:
        logger.error("Notify health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


def get_health_status() -> dict[str, Any]:
    """Return overall health status with per-subsystem detail."""
    db = check_database()
    redis = check_redis()
    social = get_social_status()
    storage = get_storage_status()
    notify = get_notify_status()

    subsystems = [db, redis, social, storage, notify]
    overall = "ok" if all(s.get("status") == "ok" for s in subsystems) else "degraded"

    return {
        "status": overall,
        "database": db,
        "redis": redis,
        "social": social,
        "storage": storage,
        "notify": notify,
    }
