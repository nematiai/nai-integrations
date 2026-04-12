"""Celery tasks for async notification sending."""

import logging

from celery import shared_task

from .models import NotificationChannel, NotificationTemplate
from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(
    self,
    title: str,
    body: str,
    channel_ids: list[int] | None = None,
) -> None:
    """Async task for sending notifications."""
    try:
        channels = None
        if channel_ids:
            channels = NotificationChannel.objects.filter(
                id__in=channel_ids, is_active=True
            )
        service = NotificationService()
        service.send(title=title, body=body, channels=channels)
    except Exception as exc:
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_template_notification_task(
    self,
    template_id: int,
    context: dict,
    channel_ids: list[int] | None = None,
) -> None:
    """Async task for sending template-based notifications."""
    try:
        template = NotificationTemplate.objects.get(id=template_id)
        channels = None
        if channel_ids:
            channels = NotificationChannel.objects.filter(
                id__in=channel_ids, is_active=True
            )
        service = NotificationService()
        service.send_from_template(
            template=template, context=context, channels=channels
        )
    except Exception as exc:
        self.retry(exc=exc)


@shared_task
def test_channel_task(channel_id: int) -> dict:
    """Async task for testing a notification channel."""
    try:
        channel = NotificationChannel.objects.get(id=channel_id)
        service = NotificationService()
        success, message = service.test_channel(channel)
        return {"success": success, "message": message}
    except NotificationChannel.DoesNotExist:
        return {"success": False, "message": "Channel not found"}
    except Exception as e:
        return {"success": False, "message": str(e)}
