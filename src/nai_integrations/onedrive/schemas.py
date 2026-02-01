"""
OneDrive Integration Schemas.
"""

from datetime import datetime
from typing import List, Optional

from ninja import Schema


class OneDriveStatusOut(Schema):
    connected: bool
    email: Optional[str] = None
    display_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class OneDriveAuthorizeOut(Schema):
    authorization_url: str
    message: str


class OneDriveDisconnectOut(Schema):
    success: bool
    message: str


class OneDriveFileInfo(Schema):
    name: str
    path: str
    type: str
    size: Optional[int] = None
    modified: Optional[datetime] = None
    id: Optional[str] = None


class OneDriveContentsOut(Schema):
    path: str
    entries: List[OneDriveFileInfo]
    total_count: int
    next_url: Optional[str] = None
