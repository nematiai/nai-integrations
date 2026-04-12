"""Google Drive Integration API Views."""

import logging
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from apps.storage.base.helpers import get_storage_context

from .schemas import (
    GoogleAuthorizeOut,
    GoogleDisconnectOut,
    GoogleDriveContentsOut,
    GoogleStatusOut,
)
from .services import GoogleDriveService

logger = logging.getLogger(__name__)
router = Router(tags=["Google Drive Integration"])


@router.get("/status/", response=GoogleStatusOut)
def check_google_connection(request: HttpRequest) -> GoogleStatusOut:
    app_client, user_id = get_storage_context(request)
    service = GoogleDriveService(app_client, user_id)

    if not service.is_connected():
        return GoogleStatusOut(connected=False, message="Not connected")

    if service.auth.needs_refresh():
        if not service.refresh_access_token():
            return GoogleStatusOut(connected=False, message="Token refresh failed")
        service._load_auth()

    return GoogleStatusOut(
        connected=True,
        email=service.auth.email,
        display_name=service.auth.display_name,
        account_id=service.auth.account_id,
        connected_at=service.auth.connected_at,
        expires_at=service.auth.expires_at,
        scopes=service.auth.scopes,
        message="Connected",
    )


@router.post("/authorize/", response=GoogleAuthorizeOut)
def initiate_google_oauth(request: HttpRequest) -> GoogleAuthorizeOut:
    app_client, user_id = get_storage_context(request)
    redirect_uri = getattr(settings, "GOOGLE_DRIVE_REDIRECT_URI", "")
    if not redirect_uri:
        raise HttpError(500, "GOOGLE_DRIVE_REDIRECT_URI not configured")

    service = GoogleDriveService(app_client, user_id)
    auth_url = service.get_authorization_url(redirect_uri)
    return GoogleAuthorizeOut(
        authorization_url=auth_url,
        message="Redirect user to this URL to connect Google Drive",
    )


@router.post("/callback/")
def google_callback(request: HttpRequest) -> Dict[str, Any]:
    """NAI forwards the OAuth code here."""
    app_client, user_id = get_storage_context(request)
    code = request.GET.get("code") or request.POST.get("code")
    if not code:
        raise HttpError(400, "Authorization code required")

    redirect_uri = getattr(settings, "GOOGLE_DRIVE_REDIRECT_URI", "")
    if not redirect_uri:
        raise HttpError(500, "GOOGLE_DRIVE_REDIRECT_URI not configured")

    try:
        service = GoogleDriveService(app_client, user_id)
        token_data = service.exchange_code_for_tokens(code, redirect_uri)
        service.save_tokens(token_data)
        service._load_auth()
        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)
        return {
            "success": True,
            "email": account_info.get("email", ""),
            "name": account_info.get("name", ""),
        }
    except Exception as e:
        logger.error("Google callback error: %s", e, exc_info=True)
        raise HttpError(500, f"Google connection failed: {str(e)}")


@router.delete("/disconnect/", response=GoogleDisconnectOut)
def disconnect_google(request: HttpRequest) -> GoogleDisconnectOut:
    app_client, user_id = get_storage_context(request)
    service = GoogleDriveService(app_client, user_id)
    if not service.is_connected():
        raise HttpError(404, "Google Drive not connected")
    success = service.disconnect()
    return GoogleDisconnectOut(
        connected=False,
        message="Disconnected" if success else "Failed",
        token_revoked=success,
    )


@router.get("/contents/", response=GoogleDriveContentsOut)
def list_google_contents(request: HttpRequest) -> GoogleDriveContentsOut:
    app_client, user_id = get_storage_context(request)
    service = GoogleDriveService(app_client, user_id)

    if not service.is_connected():
        raise HttpError(404, "Google Drive not connected")

    if service.auth.needs_refresh():
        if not service.refresh_access_token():
            raise HttpError(401, "Token expired, refresh failed")
        service._load_auth()

    try:
        drive_data = service.list_all_files(page_size=100)
        files = drive_data.get("files", [])
        file_items, folder_items = _split_drive_items(files)
        user_info = service.get_account_info()

        return GoogleDriveContentsOut(
            success=True,
            integration_status="Working",
            user_info={
                "email": user_info.get("email"),
                "name": user_info.get("name"),
            },
            drive_contents={
                "files": file_items,
                "folders": folder_items,
                "total_files": len(file_items),
                "total_folders": len(folder_items),
            },
            token_info={
                "expires_at": (
                    service.auth.expires_at.isoformat()
                    if service.auth.expires_at
                    else None
                ),
                "scopes": service.auth.scopes,
            },
            message=f"Found {len(files)} items",
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error("Error listing Google Drive: %s", e)
        raise HttpError(500, f"Failed: {str(e)}")


def _split_drive_items(files: list) -> tuple[list, list]:
    """Split Google Drive items into files and folders."""
    file_items, folder_items = [], []
    for item in files:
        data = {
            "id": item.get("id"),
            "name": item.get("name"),
            "mimeType": item.get("mimeType"),
            "size": item.get("size"),
            "createdTime": item.get("createdTime"),
            "modifiedTime": item.get("modifiedTime"),
            "webViewLink": item.get("webViewLink"),
        }
        if item.get("mimeType") == "application/vnd.google-apps.folder":
            folder_items.append(data)
        else:
            file_items.append(data)
    return file_items, folder_items
