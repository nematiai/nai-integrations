"""
Scheduled notification tasks for Celery Beat.

- Health check: Every 6 hours
- Cleanup old logs: Daily at 3:10 AM
- Retry failed: Every hour at :30
"""

import logging
from datetime import timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="notifications.channel_health_check")
def channel_health_check() -> str:
    """Test all active channels and report failures. Schedule: every 6h."""
    from .models import NotificationChannel
    from .services import NotificationService

    failed_channels: list[dict] = []
    checked = 0
    channels = NotificationChannel.objects.filter(is_active=True)
    service = NotificationService()

    for channel in channels:
        checked += 1
        success, message = service.test_channel(channel)
        if not success:
            failed_channels.append({"name": channel.name, "error": message})
            logger.warning(
                "Channel health check failed: %s — %s", channel.name, message
            )

    if failed_channels:
        working = (
            NotificationChannel.objects.filter(is_active=True)
            .exclude(name__in=[c["name"] for c in failed_channels])
            .first()
        )
        if working:
            body = "\n".join(
                f"- {c['name']}: {c['error'][:80]}" for c in failed_channels[:10]
            )
            service.send(
                title=f"{len(failed_channels)} channel(s) failed health check",
                body=body,
                channels=[working],
            )

    return f"Checked {checked} channels, {len(failed_channels)} failed"


@shared_task(name="notifications.cleanup_old_logs")
def cleanup_old_logs(days: int = 30) -> str:
    """Clean up old notification logs. Schedule: daily 3:10 AM."""
    from django.utils import timezone

    from .models import NotificationLog

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = NotificationLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleaned up %d notification logs older than %d days", deleted, days)
    return f"Deleted {deleted} logs"


@shared_task(name="notifications.retry_failed_notifications")
def retry_failed_notifications(hours: int = 24) -> str:
    """Retry failed notifications from the last N hours. Schedule: hourly :30."""
    from django.utils import timezone

    from .models import NotificationLog
    from .services import NotificationService

    cutoff = timezone.now() - timedelta(hours=hours)
    failed_logs = NotificationLog.objects.filter(
        status="failed",
        created_at__gte=cutoff,
    ).select_related("channel")

    retried = 0
    succeeded = 0
    service = NotificationService()

    for log in failed_logs:
        if not log.channel or not log.channel.is_active:
            continue
        retried += 1
        new_logs = service.send(title=log.title, body=log.body, channels=[log.channel])
        if new_logs and new_logs[0].status == "sent":
            succeeded += 1
            log.status = "sent"
            log.error_message = f"Retry succeeded at {timezone.now()}"
            log.save()

    logger.info("Retried %d failed notifications, %d succeeded", retried, succeeded)
    return f"Retried {retried}, succeeded {succeeded}"
