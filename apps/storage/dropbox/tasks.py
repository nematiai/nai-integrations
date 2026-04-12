"""Celery tasks for Dropbox OAuth token management."""

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

    @shared_task(
        name="nemi-refresh-dropbox-tokens",
        bind=True,
        max_retries=3,
        default_retry_delay=60,
    )
    def refresh_expiring_dropbox_tokens(self) -> Dict[str, Any]:
        from .models import DropboxAuth
        from .services import DropboxService

        try:
            cutoff = timezone.now() + timedelta(hours=6)
            expiring = (
                DropboxAuth.objects.filter(
                    expires_at__lte=cutoff,
                    expires_at__gt=timezone.now(),
                    _refresh_token__isnull=False,
                    is_active=True,
                )
                .exclude(_refresh_token="")
                .select_related("app_client")
            )

            success_count = 0
            for auth in expiring:
                try:
                    svc = DropboxService(auth.app_client, auth.external_user_id)
                    if svc.refresh_access_token():
                        success_count += 1
                except Exception as e:
                    logger.error("Failed to refresh Dropbox token: %s", e)

            return {"success": True, "tokens_refreshed": success_count}
        except Exception as e:
            logger.error("Dropbox token refresh task failed: %s", e)
            raise self.retry(exc=e)

    return refresh_expiring_dropbox_tokens


refresh_expiring_dropbox_tokens = get_refresh_task()
