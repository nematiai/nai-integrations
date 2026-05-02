"""Dropbox Integration API Views."""

import logging
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from apps.storage.base.helpers import get_storage_context

from .schemas import (
    DropboxAuthorizeOut,
    DropboxContentsOut,
    DropboxDisconnectOut,
    DropboxFileInfo,
    DropboxStatusOut,
)
from .services import DropboxService

logger = logging.getLogger(__name__)
router = Router(tags=["Dropbox Integration"])


@router.get("/status/", response=DropboxStatusOut)
def get_dropbox_status(request: HttpRequest) -> DropboxStatusOut:
    app_client, user_id = get_storage_context(request)
    service = DropboxService(app_client, user_id)
    return DropboxStatusOut(**service.get_connection_status())


@router.post("/authorize/", response=DropboxAuthorizeOut)
def authorize_dropbox(request: HttpRequest) -> DropboxAuthorizeOut:
    app_client, user_id = get_storage_context(request)
    callback_url = getattr(settings, "DROPBOX_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "DROPBOX_REDIRECT_URI not configured")
    service = DropboxService(app_client, user_id)
    auth_url = service.get_authorization_url(callback_url)
    return DropboxAuthorizeOut(
        authorization_url=auth_url,
        message="Redirect user to this URL to connect Dropbox",
    )


@router.post("/callback/")
def dropbox_callback(request: HttpRequest) -> Dict[str, Any]:
    """NAI forwards the OAuth code here."""
    app_client, user_id = get_storage_context(request)
    code = request.GET.get("code") or request.POST.get("code")
    if not code:
        raise HttpError(400, "Authorization code required")

    callback_url = getattr(settings, "DROPBOX_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "DROPBOX_REDIRECT_URI not configured")

    try:
        service = DropboxService(app_client, user_id)
        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()
        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)
        return {"success": True, "email": account_info.get("email", "")}
    except Exception as e:
        logger.error("Dropbox callback error: %s", e, exc_info=True)
        raise HttpError(500, f"Dropbox connection failed: {str(e)}")


@router.delete("/disconnect/", response=DropboxDisconnectOut)
def disconnect_dropbox(request: HttpRequest) -> DropboxDisconnectOut:
    app_client, user_id = get_storage_context(request)
    service = DropboxService(app_client, user_id)
    if not service.is_connected():
        raise HttpError(404, "Dropbox is not connected")
    success = service.disconnect()
    return DropboxDisconnectOut(
        success=success,
        message="Dropbox disconnected" if success else "Failed",
    )


@router.get("/contents/", response=DropboxContentsOut)
def get_dropbox_contents(request: HttpRequest) -> DropboxContentsOut:
    app_client, user_id = get_storage_context(request)
    service = DropboxService(app_client, user_id)
    path = request.GET.get("path", "")

    if not service.is_connected():
        raise HttpError(404, "Dropbox is not connected")

    try:
        folder_data = service.list_folder(path)
        entries = [
            DropboxFileInfo(
                name=e.get("name", ""),
                path=e.get("path_display", ""),
                type="folder" if e.get(".tag") == "folder" else "file",
                size=e.get("size"),
                modified=e.get("client_modified") or e.get("server_modified"),
                id=e.get("id", ""),
            )
            for e in folder_data.get("entries", [])
        ]
        return DropboxContentsOut(
            path=path or "/",
            entries=entries,
            has_more=folder_data.get("has_more", False),
            cursor=folder_data.get("cursor"),
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error("Failed to list Dropbox contents: %s", e, exc_info=True)
        raise HttpError(500, f"Failed to list Dropbox contents: {str(e)}")
