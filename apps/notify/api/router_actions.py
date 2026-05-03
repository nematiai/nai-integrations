"""Log listing, send, and schema endpoints for NEMI notifications."""

import logging

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.core.base.rate_limit import rate_limit_anon, rate_limit_user
from apps.notify.models import NotificationChannel, NotificationLog
from apps.notify.schemas import get_all_schemas
from apps.notify.services import NotificationService

from .schemas import (
    ErrorSchema,
    LogDetailSchema,
    LogListSchema,
    SendNotificationSchema,
)

logger = logging.getLogger(__name__)
router = Router(tags=["notifications"])


# --- Helpers ---
def _log_to_list(log: NotificationLog) -> LogListSchema:
    return LogListSchema(
        id=log.id,
        channel_name=log.channel.name if log.channel else None,
        template_name=log.template.name if log.template else None,
        title=log.title,
        status=log.status,
        sent_at=log.sent_at,
        created_at=log.created_at,
    )


def _log_to_detail(log: NotificationLog) -> LogDetailSchema:
    return LogDetailSchema(
        id=log.id,
        channel=log.channel_id,
        channel_name=log.channel.name if log.channel else None,
        template=log.template_id,
        template_name=log.template.name if log.template else None,
        title=log.title,
        body=log.body,
        status=log.status,
        error_message=log.error_message,
        context_data=log.context_data,
        sent_at=log.sent_at,
        created_at=log.created_at,
    )


# --- Logs ---
@router.get("/logs/", response=list[LogListSchema])
@rate_limit_user
def list_logs(request, status: str | None = None, channel_id: int | None = None):
    qs = NotificationLog.objects.select_related("channel", "template")
    if status:
        qs = qs.filter(status=status)
    if channel_id:
        qs = qs.filter(channel_id=channel_id)
    return [_log_to_list(log) for log in qs]


@router.get("/logs/{log_id}/", response={200: LogDetailSchema, 404: ErrorSchema})
@rate_limit_user
def get_log(request, log_id: int):
    log = get_object_or_404(
        NotificationLog.objects.select_related("channel", "template"),
        id=log_id,
    )
    return _log_to_detail(log)


# --- Schema & Send ---
@router.get("/schemas/", response=dict, auth=None)
@rate_limit_anon
def get_service_schemas(request):
    """Return all service schemas for frontend form generation."""
    return get_all_schemas()


@router.post("/send/", response={201: list[LogListSchema], 400: ErrorSchema})
@rate_limit_user
def send_notification(request, payload: SendNotificationSchema):
    """Send an ad-hoc notification to channels."""
    channels = None
    if payload.channel_ids:
        channels = NotificationChannel.objects.filter(
            id__in=payload.channel_ids, is_active=True
        )
    service = NotificationService()
    logs = service.send(title=payload.title, body=payload.body, channels=channels)
    return 201, [_log_to_list(log) for log in logs]
