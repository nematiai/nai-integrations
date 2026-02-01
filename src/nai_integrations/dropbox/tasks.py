"""
Celery tasks for Dropbox OAuth token management.
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_refresh_task():
    """Get the Celery task for refreshing Dropbox tokens."""
    try:
        from celery import shared_task
    except ImportError:
        return None

    @shared_task(
        name="nai-integrations-refresh-dropbox-tokens",
        bind=True,
        max_retries=3,
        default_retry_delay=60,
    )
    def refresh_expiring_dropbox_tokens(self) -> Dict[str, Any]:
        from .models import DropboxAuth
        from .services import DropboxService

        try:
            cutoff_time = timezone.now() + timedelta(hours=6)
            expiring_tokens = DropboxAuth.objects.filter(
                expires_at__lte=cutoff_time,
                expires_at__gt=timezone.now(),
                _refresh_token__isnull=False,
                is_active=True,
            ).exclude(_refresh_token="").select_related("user")

            total_tokens = expiring_tokens.count()
            if total_tokens == 0:
                return {"success": True, "tokens_refreshed": 0}

            success_count = 0
            for dropbox_auth in expiring_tokens:
                try:
                    service = DropboxService(dropbox_auth.user)
                    if service.refresh_access_token():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to refresh Dropbox token: {e}")

            return {"success": True, "tokens_refreshed": success_count}
        except Exception as e:
            logger.error(f"Dropbox token refresh task failed: {e}")
            raise self.retry(exc=e)

    return refresh_expiring_dropbox_tokens


refresh_expiring_dropbox_tokens = get_refresh_task()
