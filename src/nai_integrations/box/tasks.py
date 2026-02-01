"""
Celery tasks for Box OAuth token management.
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_refresh_task():
    """Get the Celery task for refreshing Box tokens."""
    try:
        from celery import shared_task
    except ImportError:
        return None

    @shared_task(
        name="nai-integrations-refresh-box-tokens",
        bind=True,
        max_retries=3,
        default_retry_delay=60,
    )
    def refresh_expiring_box_tokens(self) -> Dict[str, Any]:
        from .models import BoxAuth
        from .services import BoxService

        try:
            cutoff_time = timezone.now() + timedelta(hours=6)
            expiring_tokens = BoxAuth.objects.filter(
                expires_at__lte=cutoff_time,
                expires_at__gt=timezone.now(),
                _refresh_token__isnull=False,
                is_active=True,
            ).exclude(_refresh_token="").select_related("user")

            total_tokens = expiring_tokens.count()
            if total_tokens == 0:
                return {"success": True, "tokens_refreshed": 0}

            success_count = 0
            for box_auth in expiring_tokens:
                try:
                    service = BoxService(box_auth.user)
                    if service.refresh_access_token():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to refresh Box token: {e}")

            return {"success": True, "tokens_refreshed": success_count}
        except Exception as e:
            logger.error(f"Box token refresh task failed: {e}")
            raise self.retry(exc=e)

    return refresh_expiring_box_tokens


refresh_expiring_box_tokens = get_refresh_task()
