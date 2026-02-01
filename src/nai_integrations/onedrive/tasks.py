"""
Celery tasks for OneDrive OAuth token management.
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_refresh_task():
    try:
        from celery import shared_task
    except ImportError:
        return None

    @shared_task(name="nai-integrations-refresh-onedrive-tokens", bind=True, max_retries=3)
    def refresh_expiring_onedrive_tokens(self) -> Dict[str, Any]:
        from .models import OneDriveAuth
        from .services import OneDriveService

        try:
            cutoff_time = timezone.now() + timedelta(hours=6)
            expiring_tokens = OneDriveAuth.objects.filter(
                expires_at__lte=cutoff_time,
                expires_at__gt=timezone.now(),
                _refresh_token__isnull=False,
                is_active=True,
            ).exclude(_refresh_token="").select_related("user")

            success_count = 0
            for onedrive_auth in expiring_tokens:
                try:
                    service = OneDriveService(onedrive_auth.user)
                    if service.refresh_access_token():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to refresh OneDrive token: {e}")

            return {"success": True, "tokens_refreshed": success_count}
        except Exception as e:
            logger.error(f"OneDrive token refresh task failed: {e}")
            raise self.retry(exc=e)

    return refresh_expiring_onedrive_tokens


refresh_expiring_onedrive_tokens = get_refresh_task()
