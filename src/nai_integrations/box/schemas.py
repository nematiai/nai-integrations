"""
Box Integration Schemas.
"""

from datetime import datetime
from typing import List, Optional

from ninja import Schema


class BoxStatusOut(Schema):
    connected: bool
    email: Optional[str] = None
    display_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None


class BoxAuthorizeOut(Schema):
    authorization_url: str
    message: str


class BoxDisconnectOut(Schema):
    success: bool
    message: str


class BoxFileInfo(Schema):
    name: str
    path: str
    type: str
    size: Optional[int] = None
    modified: Optional[datetime] = None
    id: Optional[str] = None


class BoxContentsOut(Schema):
    path: str
    entries: List[BoxFileInfo]
    total_count: int
    offset: int
    limit: int
