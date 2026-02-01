"""
Dropbox Integration Schemas.
"""

from datetime import datetime
from typing import List, Optional

from ninja import Schema


class DropboxStatusOut(Schema):
    connected: bool
    email: Optional[str] = None
    display_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class DropboxAuthorizeOut(Schema):
    authorization_url: str
    message: str


class DropboxDisconnectOut(Schema):
    success: bool
    message: str


class DropboxFileInfo(Schema):
    name: str
    path: str
    type: str
    size: Optional[int] = None
    modified: Optional[datetime] = None
    id: Optional[str] = None


class DropboxContentsOut(Schema):
    path: str
    entries: List[DropboxFileInfo]
    has_more: bool
    cursor: Optional[str] = None
