"""
Google Drive Integration Schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema


class GoogleStatusOut(Schema):
    connected: bool
    email: Optional[str] = None
    display_name: Optional[str] = None
    account_id: Optional[str] = None
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    message: Optional[str] = None


class GoogleAuthorizeOut(Schema):
    authorization_url: str
    message: str


class GoogleDisconnectOut(Schema):
    connected: bool
    user_id: Optional[int] = None
    message: str
    token_revoked: Optional[bool] = None


class GoogleFileInfo(Schema):
    id: str
    name: str
    mimeType: str
    size: Optional[str] = None
    createdTime: Optional[str] = None
    modifiedTime: Optional[str] = None
    webViewLink: Optional[str] = None


class GoogleDriveContentsOut(Schema):
    success: bool
    integration_status: str
    user_info: Dict[str, Any]
    drive_contents: Dict[str, Any]
    token_info: Dict[str, Any]
    message: str
