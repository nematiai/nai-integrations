"""OneDrive Integration API Views."""

import logging
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from apps.storage.base.helpers import get_storage_context

from .schemas import (
    OneDriveAuthorizeOut,
    OneDriveContentsOut,
    OneDriveDisconnectOut,
    OneDriveFileInfo,
    OneDriveStatusOut,
)
from .services import OneDriveService

logger = logging.getLogger(__name__)
router = Router(tags=["OneDrive Integration"])


@router.get("/status/", response=OneDriveStatusOut)
def get_onedrive_status(request: HttpRequest) -> OneDriveStatusOut:
    app_client, user_id = get_storage_context(request)
    service = OneDriveService(app_client, user_id)
    return OneDriveStatusOut(**service.get_connection_status())


@router.post("/authorize/", response=OneDriveAuthorizeOut)
def authorize_onedrive(request: HttpRequest) -> OneDriveAuthorizeOut:
    app_client, user_id = get_storage_context(request)
    callback_url = getattr(settings, "ONEDRIVE_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "ONEDRIVE_REDIRECT_URI not configured")
    service = OneDriveService(app_client, user_id)
    auth_url = service.get_authorization_url(callback_url)
    return OneDriveAuthorizeOut(
        authorization_url=auth_url,
        message="Redirect user to this URL to connect OneDrive",
    )


@router.post("/callback/")
def onedrive_callback(request: HttpRequest) -> Dict[str, Any]:
    """NAI forwards the OAuth code here."""
    app_client, user_id = get_storage_context(request)
    code = request.GET.get("code") or request.POST.get("code")
    if not code:
        raise HttpError(400, "Authorization code required")

    callback_url = getattr(settings, "ONEDRIVE_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "ONEDRIVE_REDIRECT_URI not configured")

    try:
        service = OneDriveService(app_client, user_id)
        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()
        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)
        email = account_info.get("userPrincipalName", "") or account_info.get(
            "mail", ""
        )
        return {"success": True, "email": email}
    except Exception as e:
        logger.error("OneDrive callback error: %s", e, exc_info=True)
        raise HttpError(500, f"OneDrive connection failed: {str(e)}")


@router.delete("/disconnect/", response=OneDriveDisconnectOut)
def disconnect_onedrive(request: HttpRequest) -> OneDriveDisconnectOut:
    app_client, user_id = get_storage_context(request)
    service = OneDriveService(app_client, user_id)
    if not service.is_connected():
        raise HttpError(404, "OneDrive is not connected")
    success = service.disconnect()
    return OneDriveDisconnectOut(
        success=success,
        message="Disconnected" if success else "Failed",
    )


@router.get("/contents/", response=OneDriveContentsOut)
def get_onedrive_contents(request: HttpRequest) -> OneDriveContentsOut:
    app_client, user_id = get_storage_context(request)
    service = OneDriveService(app_client, user_id)
    folder_id = request.GET.get("folder_id", "root")
    limit = int(request.GET.get("limit", "100"))

    if not service.is_connected():
        raise HttpError(404, "OneDrive is not connected")

    try:
        folder_data = service.list_folder(folder_id, limit)
        entries = _parse_onedrive_entries(folder_data)
        return OneDriveContentsOut(
            path=f"/{folder_id}" if folder_id != "root" else "/",
            entries=entries,
            total_count=len(entries),
            next_url=folder_data.get("@odata.nextLink"),
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error("Failed to list OneDrive contents: %s", e, exc_info=True)
        raise HttpError(500, f"Failed: {str(e)}")


def _parse_onedrive_entries(folder_data: Dict[str, Any]) -> list[OneDriveFileInfo]:
    """Parse OneDrive API response into file info list."""
    entries = []
    for entry in folder_data.get("value", []):
        entry_type = "folder" if "folder" in entry else "file"
        modified = None
        if entry.get("lastModifiedDateTime"):
            try:
                modified = datetime.fromisoformat(
                    entry["lastModifiedDateTime"].replace("Z", "+00:00")
                )
            except Exception:
                pass
        entries.append(
            OneDriveFileInfo(
                name=entry.get("name", ""),
                path="/" + entry.get("name", ""),
                type=entry_type,
                size=entry.get("size"),
                modified=modified,
                id=entry.get("id", ""),
            )
        )
    return entries
