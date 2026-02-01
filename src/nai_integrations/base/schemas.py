"""
Common schemas for cloud storage integrations.
"""

from datetime import datetime
from typing import List, Optional

from ninja import Schema


class ConnectionStatusOut(Schema):
    """Schema for connection status response."""
    connected: bool
    email: Optional[str] = None
    display_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class AuthorizeOut(Schema):
    """Schema for authorization response."""
    authorization_url: str
    message: str


class DisconnectOut(Schema):
    """Schema for disconnect response."""
    success: bool
    message: str


class FileInfo(Schema):
    """Schema for file/folder information."""
    name: str
    path: str
    type: str  # 'file' or 'folder'
    size: Optional[int] = None
    modified: Optional[datetime] = None
    id: Optional[str] = None


class ContentsOut(Schema):
    """Schema for folder contents listing."""
    path: str
    entries: List[FileInfo]
    total_count: int
    has_more: bool = False
    cursor: Optional[str] = None
    next_url: Optional[str] = None
