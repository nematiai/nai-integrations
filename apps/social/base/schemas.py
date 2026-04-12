"""Ninja schemas for social media endpoints."""

from datetime import datetime
from typing import List, Optional

from ninja import Schema


class RegisterAccountIn(Schema):
    """Schema for registering a social media account."""

    platform: str
    credentials: dict


class AccountOut(Schema):
    """Schema for social account response."""

    platform: str
    is_active: bool
    health_status: str
    last_health_check: Optional[datetime] = None
    created_at: datetime


class PostIn(Schema):
    """Schema for creating a social media post."""

    content: str
    platforms: List[str]
    media_url: Optional[str] = None


class PostOut(Schema):
    """Schema for post result response."""

    platform: str
    status: str
    external_id: str = ""
    error: Optional[str] = None
    created_at: datetime


class PlatformOut(Schema):
    """Schema for available platform info."""

    name: str
    max_content_length: int
    supports_media: bool
    registered: bool


class HealthOut(Schema):
    """Schema for platform health check response."""

    platform: str
    healthy: bool
