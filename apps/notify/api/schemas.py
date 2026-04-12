"""Pydantic schemas for NEMI notification API."""

from datetime import datetime
from typing import Any

from ninja import Schema


# --- Channel ---
class ChannelCreateSchema(Schema):
    name: str
    service_type: str
    config: dict[str, Any] = {}
    is_active: bool = True


class ChannelUpdateSchema(Schema):
    name: str
    service_type: str
    config: dict[str, Any] = {}
    is_active: bool = True


class ChannelPatchSchema(Schema):
    name: str | None = None
    service_type: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class ChannelListSchema(Schema):
    id: int
    name: str
    service_type: str
    service_label: str
    is_active: bool


class ChannelDetailSchema(Schema):
    id: int
    name: str
    service_type: str
    service_label: str
    config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Template ---
class TemplateCreateSchema(Schema):
    name: str
    template_type: str
    title_template: str
    body_template: str
    channel_ids: list[int] = []
    is_active: bool = True


class TemplateUpdateSchema(Schema):
    name: str
    template_type: str
    title_template: str
    body_template: str
    channel_ids: list[int] = []
    is_active: bool = True


class TemplatePatchSchema(Schema):
    name: str | None = None
    template_type: str | None = None
    title_template: str | None = None
    body_template: str | None = None
    channel_ids: list[int] | None = None
    is_active: bool | None = None


class TemplateListSchema(Schema):
    id: int
    name: str
    template_type: str
    is_active: bool
    created_at: datetime


class TemplateDetailSchema(Schema):
    id: int
    name: str
    template_type: str
    title_template: str
    body_template: str
    channels: list[ChannelListSchema]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TemplatePreviewSchema(Schema):
    context: dict[str, Any] = {}


class TemplatePreviewResponseSchema(Schema):
    title: str
    body: str


# --- Log ---
class LogListSchema(Schema):
    id: int
    channel_name: str | None
    template_name: str | None
    title: str
    status: str
    sent_at: datetime | None
    created_at: datetime


class LogDetailSchema(Schema):
    id: int
    channel: int | None
    channel_name: str | None
    template: int | None
    template_name: str | None
    title: str
    body: str
    status: str
    error_message: str
    context_data: dict[str, Any]
    sent_at: datetime | None
    created_at: datetime


# --- Actions ---
class TestChannelResponseSchema(Schema):
    success: bool
    message: str


class SendNotificationSchema(Schema):
    title: str
    body: str
    channel_ids: list[int] | None = None


class ErrorSchema(Schema):
    detail: str


class ValidationErrorSchema(Schema):
    detail: dict[str, Any]
