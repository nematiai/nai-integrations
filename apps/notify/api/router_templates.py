"""Template CRUD endpoints for NEMI notifications."""

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.core.base.rate_limit import rate_limit_user
from apps.notify.models import NotificationChannel, NotificationTemplate

from .router import _channel_to_list
from .schemas import (
    ErrorSchema,
    TemplateCreateSchema,
    TemplateDetailSchema,
    TemplateListSchema,
    TemplatePatchSchema,
    TemplatePreviewResponseSchema,
    TemplatePreviewSchema,
    TemplateUpdateSchema,
    ValidationErrorSchema,
)

router = Router(tags=["notifications"])


def _tpl_detail(t: NotificationTemplate) -> TemplateDetailSchema:
    return TemplateDetailSchema(
        id=t.id,
        name=t.name,
        template_type=t.template_type,
        title_template=t.title_template,
        body_template=t.body_template,
        channels=[_channel_to_list(c) for c in t.channels.all()],
        is_active=t.is_active,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("/templates/", response=list[TemplateListSchema])
@rate_limit_user
def list_templates(request):
    return [
        TemplateListSchema(
            id=t.id,
            name=t.name,
            template_type=t.template_type,
            is_active=t.is_active,
            created_at=t.created_at,
        )
        for t in NotificationTemplate.objects.all()
    ]


@router.post(
    "/templates/", response={201: TemplateDetailSchema, 400: ValidationErrorSchema}
)
@rate_limit_user
def create_template(request, payload: TemplateCreateSchema):
    t = NotificationTemplate.objects.create(
        name=payload.name,
        template_type=payload.template_type,
        title_template=payload.title_template,
        body_template=payload.body_template,
        is_active=payload.is_active,
    )
    if payload.channel_ids:
        t.channels.set(NotificationChannel.objects.filter(id__in=payload.channel_ids))
    return 201, _tpl_detail(t)


@router.get("/templates/{tid}/", response={200: TemplateDetailSchema, 404: ErrorSchema})
@rate_limit_user
def get_template(request, tid: int):
    return _tpl_detail(get_object_or_404(NotificationTemplate, id=tid))


@router.put("/templates/{tid}/", response={200: TemplateDetailSchema, 404: ErrorSchema})
@rate_limit_user
def update_template(request, tid: int, payload: TemplateUpdateSchema):
    t = get_object_or_404(NotificationTemplate, id=tid)
    t.name = payload.name
    t.template_type = payload.template_type
    t.title_template = payload.title_template
    t.body_template = payload.body_template
    t.is_active = payload.is_active
    t.save()
    t.channels.set(NotificationChannel.objects.filter(id__in=payload.channel_ids))
    return _tpl_detail(t)


@router.patch(
    "/templates/{tid}/", response={200: TemplateDetailSchema, 404: ErrorSchema}
)
@rate_limit_user
def patch_template(request, tid: int, payload: TemplatePatchSchema):
    t = get_object_or_404(NotificationTemplate, id=tid)
    if payload.name is not None:
        t.name = payload.name
    if payload.template_type is not None:
        t.template_type = payload.template_type
    if payload.title_template is not None:
        t.title_template = payload.title_template
    if payload.body_template is not None:
        t.body_template = payload.body_template
    if payload.is_active is not None:
        t.is_active = payload.is_active
    t.save()
    if payload.channel_ids is not None:
        t.channels.set(NotificationChannel.objects.filter(id__in=payload.channel_ids))
    return _tpl_detail(t)


@router.delete("/templates/{tid}/", response={204: None, 404: ErrorSchema})
@rate_limit_user
def delete_template(request, tid: int):
    get_object_or_404(NotificationTemplate, id=tid).delete()
    return 204, None


@router.post(
    "/templates/{tid}/preview/",
    response={200: TemplatePreviewResponseSchema, 400: ErrorSchema, 404: ErrorSchema},
)
@rate_limit_user
def preview_template(request, tid: int, payload: TemplatePreviewSchema):
    t = get_object_or_404(NotificationTemplate, id=tid)
    try:
        title, body = t.render(payload.context)
        return {"title": title, "body": body}
    except KeyError:
        return 400, {"detail": "Missing required context variable."}
