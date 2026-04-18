"""Channel CRUD endpoints for NEMI notification API."""

import logging

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.notify.models import NotificationChannel
from apps.notify.schemas import SERVICE_SCHEMAS
from apps.notify.services import NotificationService

from .schemas import (
    ChannelCreateSchema,
    ChannelDetailSchema,
    ChannelListSchema,
    ChannelPatchSchema,
    ChannelUpdateSchema,
    ErrorSchema,
    TestChannelResponseSchema,
    ValidationErrorSchema,
)

logger = logging.getLogger(__name__)
router = Router(tags=["notifications"])


def _channel_to_list(ch: NotificationChannel) -> ChannelListSchema:
    return ChannelListSchema(
        id=ch.id,
        name=ch.name,
        service_type=ch.service_type,
        service_label=ch.get_service_type_display(),
        is_active=ch.is_active,
    )


def _channel_to_detail(ch: NotificationChannel) -> ChannelDetailSchema:
    return ChannelDetailSchema(
        id=ch.id,
        name=ch.name,
        service_type=ch.service_type,
        service_label=ch.get_service_type_display(),
        config=ch.config,
        is_active=ch.is_active,
        created_at=ch.created_at,
        updated_at=ch.updated_at,
    )


def _validate_config(service_type: str, config: dict) -> dict | None:
    schema = SERVICE_SCHEMAS.get(service_type)
    if not schema:
        return {"service_type": f"Unknown service type: {service_type}"}
    errors = {}
    for field in schema["fields"]:
        if field.get("required") and not config.get(field["name"]):
            errors[field["name"]] = f"{field['label']} is required"
    return errors if errors else None


@router.get("/channels/", response=list[ChannelListSchema])
def list_channels(request):
    return [_channel_to_list(c) for c in NotificationChannel.objects.all()]


@router.post(
    "/channels/", response={201: ChannelDetailSchema, 400: ValidationErrorSchema}
)
def create_channel(request, payload: ChannelCreateSchema):
    errors = _validate_config(payload.service_type, payload.config)
    if errors:
        return 400, {"detail": {"config": errors}}
    ch = NotificationChannel.objects.create(
        created_by=None,
        name=payload.name,
        service_type=payload.service_type,
        config=payload.config,
        is_active=payload.is_active,
    )
    return 201, _channel_to_detail(ch)


@router.get("/channels/{cid}/", response={200: ChannelDetailSchema, 404: ErrorSchema})
def get_channel(request, cid: int):
    return _channel_to_detail(get_object_or_404(NotificationChannel, id=cid))


@router.put(
    "/channels/{cid}/",
    response={200: ChannelDetailSchema, 400: ValidationErrorSchema, 404: ErrorSchema},
)
def update_channel(request, cid: int, payload: ChannelUpdateSchema):
    ch = get_object_or_404(NotificationChannel, id=cid)
    errors = _validate_config(payload.service_type, payload.config)
    if errors:
        return 400, {"detail": {"config": errors}}
    ch.name = payload.name
    ch.service_type = payload.service_type
    ch.config = payload.config
    ch.is_active = payload.is_active
    ch.save()
    return _channel_to_detail(ch)


@router.patch(
    "/channels/{cid}/",
    response={200: ChannelDetailSchema, 400: ValidationErrorSchema, 404: ErrorSchema},
)
def patch_channel(request, cid: int, payload: ChannelPatchSchema):
    ch = get_object_or_404(NotificationChannel, id=cid)
    if payload.name is not None:
        ch.name = payload.name
    if payload.service_type is not None:
        ch.service_type = payload.service_type
    if payload.config is not None:
        ch.config = payload.config
    if payload.is_active is not None:
        ch.is_active = payload.is_active
    errors = _validate_config(ch.service_type, ch.config)
    if errors:
        return 400, {"detail": {"config": errors}}
    ch.save()
    return _channel_to_detail(ch)


@router.delete("/channels/{cid}/", response={204: None, 404: ErrorSchema})
def delete_channel(request, cid: int):
    get_object_or_404(NotificationChannel, id=cid).delete()
    return 204, None


@router.post(
    "/channels/{cid}/test/",
    response={200: TestChannelResponseSchema, 404: ErrorSchema},
)
def test_channel(request, cid: int):
    ch = get_object_or_404(NotificationChannel, id=cid)
    success, message = NotificationService().test_channel(ch)
    return {"success": success, "message": message}
