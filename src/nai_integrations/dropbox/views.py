"""
Dropbox Integration API Views.
"""

import logging
import os
import secrets

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError

from nai_integrations.contrib.auth import require_auth

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
User = get_user_model()


@router.get("/status/", response=DropboxStatusOut, summary="Check Dropbox connection status")
def get_dropbox_status(request: HttpRequest):
    user = require_auth(request)
    service = DropboxService(user)
    status = service.get_connection_status()
    return DropboxStatusOut(**status)


@router.post("/authorize/", response=DropboxAuthorizeOut, summary="Initiate Dropbox OAuth")
def authorize_dropbox(request: HttpRequest):
    user = require_auth(request)
    callback_url = os.getenv(
        "DROPBOX_REDIRECT_URI",
        f"{request.build_absolute_uri('/').rstrip('/')}/api/v1/dropbox/callback",
    )
    state = secrets.token_urlsafe(32)
    request.session["dropbox_auth_user_id"] = user.id
    request.session["dropbox_auth_state"] = state
    request.session.save()
    service = DropboxService(user)
    auth_url = service.get_authorization_url(callback_url, state)
    return DropboxAuthorizeOut(
        authorization_url=auth_url,
        message="Please visit the authorization URL to connect your Dropbox account",
    )


@router.delete("/disconnect/", response=DropboxDisconnectOut, summary="Disconnect Dropbox")
def disconnect_dropbox(request: HttpRequest):
    user = require_auth(request)
    service = DropboxService(user)
    if not service.is_connected():
        raise HttpError(400, "Dropbox is not connected")
    success = service.disconnect()
    return DropboxDisconnectOut(
        success=success,
        message="Dropbox account disconnected successfully" if success else "Failed to disconnect",
    )


@router.get("/contents/", response=DropboxContentsOut, summary="List Dropbox folder contents")
def get_dropbox_contents(request: HttpRequest):
    user = require_auth(request)
    service = DropboxService(user)
    path = request.GET.get("path", "")

    if not service.is_connected():
        raise HttpError(400, "Dropbox is not connected. Please authorize first.")

    try:
        folder_data = service.list_folder(path)
        entries = []
        for entry in folder_data.get("entries", []):
            file_info = DropboxFileInfo(
                name=entry.get("name", ""),
                path=entry.get("path_display", ""),
                type="folder" if entry.get(".tag") == "folder" else "file",
                size=entry.get("size"),
                modified=entry.get("client_modified") or entry.get("server_modified"),
                id=entry.get("id", ""),
            )
            entries.append(file_info)

        return DropboxContentsOut(
            path=path or "/",
            entries=entries,
            has_more=folder_data.get("has_more", False),
            cursor=folder_data.get("cursor"),
        )
    except Exception as e:
        logger.error(f"Failed to list Dropbox contents: {e}", exc_info=True)
        raise HttpError(500, f"Failed to list Dropbox contents: {str(e)}")


@router.get("/callback", include_in_schema=False, summary="OAuth callback endpoint")
def dropbox_callback(request: HttpRequest):
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    error_description = request.GET.get("error_description", "")

    if error:
        return render(request, "dropbox/callback_error.html", {"error": error_description or error})

    if not code:
        return render(request, "dropbox/callback_error.html", {"error": "No authorization code"})

    expected_state = request.session.get("dropbox_auth_state")
    if not state or not expected_state or state != expected_state:
        return render(request, "dropbox/callback_error.html", {"error": "Invalid state parameter"})

    try:
        user_id = request.session.get("dropbox_auth_user_id")
        if not user_id:
            return render(request, "dropbox/callback_error.html", {"error": "User session not found"})

        user = User.objects.get(id=user_id)
        service = DropboxService(user)
        callback_url = os.getenv(
            "DROPBOX_REDIRECT_URI",
            f"{request.build_absolute_uri('/').rstrip('/')}/api/v1/dropbox/callback",
        )

        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()

        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)

        for key in ["dropbox_auth_user_id", "dropbox_auth_state"]:
            if key in request.session:
                del request.session[key]
        request.session.save()

        email = account_info.get("email", "")
        return render(request, "dropbox/callback_success.html", {"email": email})

    except Exception as e:
        logger.error(f"Dropbox OAuth callback error: {e}", exc_info=True)
        return render(request, "dropbox/callback_error.html", {"error": str(e)})
