"""Request/response schemas for auth endpoints."""

from datetime import datetime

from ninja import Schema


class RegisterRequestSchema(Schema):
    name: str
    permissions: list[str] = ["social", "storage", "notify"]
    rate_limit_per_minute: int = 60


class RegisterResponseSchema(Schema):
    id: int
    name: str
    api_key: str
    api_key_prefix: str
    permissions: list[str]
    created_at: datetime


class RotateKeyRequestSchema(Schema):
    pass


class RotateKeyResponseSchema(Schema):
    api_key: str
    api_key_prefix: str
    message: str


class AppClientSchema(Schema):
    id: int
    name: str
    api_key_prefix: str
    permissions: list[str]
    rate_limit_per_minute: int
    is_active: bool
    created_at: datetime


class ErrorSchema(Schema):
    detail: str
