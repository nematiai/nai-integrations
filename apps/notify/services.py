"""Apprise wrapper service for sending notifications."""

import logging
from typing import Optional

import apprise
from django.utils import timezone

from .models import NotificationChannel, NotificationLog, NotificationTemplate

logger = logging.getLogger(__name__)


class NotificationService:
    """Service layer for sending notifications via Apprise."""

    def send(
        self,
        title: str,
        body: str,
        channels: Optional[list[NotificationChannel]] = None,
        template: Optional[NotificationTemplate] = None,
        context: Optional[dict] = None,
    ) -> list[NotificationLog]:
        """Send notification to specified channels or all active channels."""
        if channels is None:
            channels = NotificationChannel.objects.filter(is_active=True)

        logs = []
        for channel in channels:
            log = self._send_to_channel(
                channel=channel,
                title=title,
                body=body,
                template=template,
                context=context or {},
            )
            logs.append(log)
        return logs

    def send_from_template(
        self,
        template: NotificationTemplate,
        context: dict,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> list[NotificationLog]:
        """Send notification using a template."""
        title, body = template.render(context)
        if channels is None:
            channels = template.channels.filter(is_active=True)
        return self.send(
            title=title,
            body=body,
            channels=channels,
            template=template,
            context=context,
        )

    def _send_to_channel(
        self,
        channel: NotificationChannel,
        title: str,
        body: str,
        template: Optional[NotificationTemplate] = None,
        context: Optional[dict] = None,
    ) -> NotificationLog:
        """Send notification to a single channel."""
        log = NotificationLog.objects.create(
            channel=channel,
            template=template,
            title=title,
            body=body,
            status="pending",
            context_data=context or {},
        )
        try:
            apobj = apprise.Apprise()
            apobj.add(channel.apprise_url)
            result = apobj.notify(title=title, body=body)
            if result:
                log.status = "sent"
                log.sent_at = timezone.now()
            else:
                log.status = "failed"
                log.error_message = "Apprise returned False"
        except Exception as e:
            logger.exception("Failed to send notification to %s", channel.name)
            log.status = "failed"
            log.error_message = str(e)
        log.save()
        return log

    def test_channel(self, channel: NotificationChannel) -> tuple[bool, str]:
        """Test a notification channel. Returns (success, message)."""
        try:
            apobj = apprise.Apprise()
            apobj.add(channel.apprise_url)
            result = apobj.notify(
                title="Test Notification",
                body="This is a test from NEMI",
            )
            if result:
                return True, "Notification sent successfully"
            return False, "Apprise returned failure"
        except Exception as e:
            logger.exception("Test failed for %s", channel.name)
            return False, str(e)


def send_notification(
    title: str,
    body: str,
    channels: Optional[list[NotificationChannel]] = None,
) -> list[NotificationLog]:
    """Convenience function for sending notifications."""
    service = NotificationService()
    return service.send(title=title, body=body, channels=channels)


def send_template_notification(
    template_type: str,
    context: dict,
) -> list[NotificationLog]:
    """Send notification using template type."""
    template = NotificationTemplate.objects.filter(
        template_type=template_type,
        is_active=True,
    ).first()
    if not template:
        logger.warning("No active template for type: %s", template_type)
        return []
    service = NotificationService()
    return service.send_from_template(template=template, context=context)
