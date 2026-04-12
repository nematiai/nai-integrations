"""Celery tasks for async social media posting."""

import logging
from typing import Any, Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="nemi-social-post",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="social",
)
def post_to_platform(self, post_log_id: int) -> Dict[str, Any]:
    """Post a single PostLog entry to its target platform."""
    from apps.social.base.models import PostLog, SocialAccount
    from apps.social.registry import get_adapter

    try:
        log = PostLog.objects.select_related("app_client").get(id=post_log_id)
    except PostLog.DoesNotExist:
        logger.error("PostLog %s does not exist", post_log_id)
        return {"status": "failed", "error": "log_missing"}

    try:
        account = SocialAccount.objects.get(
            app_client=log.app_client,
            external_user_id=log.external_user_id,
            platform=log.platform,
            is_active=True,
        )
    except SocialAccount.DoesNotExist:
        log.status = "failed"
        log.error = f"No active {log.platform} account"
        log.save(update_fields=["status", "error"])
        return {"status": "failed", "error": log.error}

    try:
        adapter_class = get_adapter(log.platform)
        adapter = adapter_class(account.decrypted_credentials)
        result = adapter.post(log.content, log.media_url)
        log.status = "success"
        log.external_id = str(result.get("external_id", ""))
        log.posted_at = timezone.now()
        log.save(update_fields=["status", "external_id", "posted_at"])
        return {"status": "success", "external_id": log.external_id}
    except Exception as exc:
        log.status = "failed"
        log.error = str(exc)[:1000]
        log.save(update_fields=["status", "error"])
        logger.warning("Post %s failed: %s", post_log_id, exc)
        raise self.retry(exc=exc)
