"""
OneDrive Integration API Views.
"""

import logging
import os
import secrets
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError

from nai_integrations.contrib.auth import require_auth

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
User = get_user_model()


@router.get("/status/", response=OneDriveStatusOut, summary="Check OneDrive connection status")
def get_onedrive_status(request: HttpRequest):
    user = require_auth(request)
    service = OneDriveService(user)
    status = service.get_connection_status()
    return OneDriveStatusOut(**status)


@router.post("/authorize/", response=OneDriveAuthorizeOut, summary="Initiate OneDrive OAuth")
def authorize_onedrive(request: HttpRequest):
    user = require_auth(request)
    state_token = secrets.token_urlsafe(32)
    cache_key = f"nai_onedrive_state:{state_token}"
    cache.set(cache_key, user.id, timeout=300)

    callback_url = os.getenv("ONEDRIVE_REDIRECT_URI")
    if not callback_url:
        raise HttpError(500, "OneDrive redirect URI not configured")

    service = OneDriveService(user)
    auth_url = service.get_authorization_url(callback_url, state=state_token)

    return OneDriveAuthorizeOut(
        authorization_url=auth_url,
        message="Please visit the authorization URL to connect your OneDrive account",
    )


@router.delete("/disconnect/", response=OneDriveDisconnectOut, summary="Disconnect OneDrive")
def disconnect_onedrive(request: HttpRequest):
    user = require_auth(request)
    service = OneDriveService(user)
    if not service.is_connected():
        raise HttpError(400, "OneDrive is not connected")
    success = service.disconnect()
    return OneDriveDisconnectOut(
        success=success,
        message="OneDrive account disconnected successfully" if success else "Failed to disconnect",
    )


@router.get("/contents/", response=OneDriveContentsOut, summary="List OneDrive folder contents")
def get_onedrive_contents(request: HttpRequest):
    user = require_auth(request)
    service = OneDriveService(user)
    folder_id = request.GET.get("folder_id", "root")
    limit = int(request.GET.get("limit", "100"))

    if not service.is_connected():
        raise HttpError(400, "OneDrive is not connected. Please authorize first.")

    try:
        folder_data = service.list_folder(folder_id, limit)
        entries = []
        for entry in folder_data.get("value", []):
            entry_type = "folder" if "folder" in entry else "file"
            path = "/" + entry.get("name", "")
            modified = None
            if entry.get("lastModifiedDateTime"):
                try:
                    modified = datetime.fromisoformat(entry["lastModifiedDateTime"].replace("Z", "+00:00"))
                except Exception:
                    pass

            file_info = OneDriveFileInfo(
                name=entry.get("name", ""),
                path=path,
                type=entry_type,
                size=entry.get("size"),
                modified=modified,
                id=entry.get("id", ""),
            )
            entries.append(file_info)

        return OneDriveContentsOut(
            path=f"/{folder_id}" if folder_id != "root" else "/",
            entries=entries,
            total_count=len(entries),
            next_url=folder_data.get("@odata.nextLink"),
        )
    except Exception as e:
        logger.error(f"Failed to list OneDrive contents: {e}", exc_info=True)
        raise HttpError(500, f"Failed to list OneDrive contents: {str(e)}")


@router.get("/callback", include_in_schema=False, summary="OAuth callback endpoint")
def onedrive_callback(request: HttpRequest):
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    error_description = request.GET.get("error_description", "")

    if error:
        return render(request, "onedrive/callback_error.html", {"error": error, "error_description": error_description})

    if not code or not state:
        return render(request, "onedrive/callback_error.html", {"error": "Missing authorization code or state"})

    cache_key = f"nai_onedrive_state:{state}"
    user_id = cache.get(cache_key)
    if not user_id:
        return render(request, "onedrive/callback_error.html", {"error": "Invalid or expired session"})

    cache.delete(cache_key)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return render(request, "onedrive/callback_error.html", {"error": "User not found"})

    callback_url = os.getenv("ONEDRIVE_REDIRECT_URI")
    if not callback_url:
        return render(request, "onedrive/callback_error.html", {"error": "Server configuration error"})

    try:
        service = OneDriveService(user)
        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()

        try:
            account_info = service.get_account_info()
            service.save_tokens(token_data, account_info)
        except Exception:
            account_info = {}

        email = account_info.get("userPrincipalName", "") or account_info.get("mail", "") or "Unknown"
        return render(request, "onedrive/callback_success.html", {"onedrive_email": email})

    except Exception as e:
        logger.error(f"OneDrive callback error: {e}", exc_info=True)
        return render(request, "onedrive/callback_error.html", {"error": str(e)})
