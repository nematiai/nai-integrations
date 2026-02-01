"""
Google Drive Integration API Views.
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

from .schemas import GoogleAuthorizeOut, GoogleDisconnectOut, GoogleDriveContentsOut, GoogleStatusOut
from .services import GoogleDriveService

logger = logging.getLogger(__name__)
router = Router(tags=["Google Drive Integration"])
User = get_user_model()


@router.get("/status/", response=GoogleStatusOut, summary="Check Google Drive connection status")
def check_google_drive_connection(request: HttpRequest):
    user = require_auth(request)
    service = GoogleDriveService(user)

    if not service.is_connected():
        return GoogleStatusOut(connected=False, message="Google Drive not connected")

    if service.auth.needs_refresh():
        if not service.refresh_access_token():
            return GoogleStatusOut(connected=False, message="Token expired and refresh failed")
        service._load_auth()

    return GoogleStatusOut(
        connected=True,
        email=service.auth.email,
        display_name=service.auth.display_name,
        account_id=service.auth.account_id,
        connected_at=service.auth.connected_at,
        expires_at=service.auth.expires_at,
        scopes=service.auth.scopes,
        message="Google Drive connected successfully",
    )


@router.post("/authorize/", response=GoogleAuthorizeOut, summary="Initiate Google OAuth flow")
def initiate_google_oauth(request: HttpRequest):
    user = require_auth(request)
    redirect_uri = os.getenv("GOOGLE_DRIVE_REDIRECT_URI")
    if not redirect_uri:
        raise HttpError(500, "Google OAuth redirect URI not configured")

    state = secrets.token_urlsafe(32)
    request.session["google_auth_user_id"] = user.id
    request.session["google_auth_state"] = state
    request.session.save()

    service = GoogleDriveService(user)
    auth_url = service.get_authorization_url(redirect_uri, state)

    return GoogleAuthorizeOut(
        authorization_url=auth_url,
        message="Please visit the authorization URL to connect your Google Drive account.",
    )


@router.delete("/disconnect/", response=GoogleDisconnectOut, summary="Disconnect Google Drive")
def disconnect_google_drive(request: HttpRequest):
    user = require_auth(request)
    service = GoogleDriveService(user)

    if not service.is_connected():
        raise HttpError(404, "Google Drive not connected")

    success = service.disconnect()
    return GoogleDisconnectOut(
        connected=False,
        user_id=user.id,
        message="Google Drive disconnected successfully" if success else "Disconnect failed",
        token_revoked=success,
    )


@router.get("/drive/contents/", response=GoogleDriveContentsOut, summary="List Google Drive contents")
def list_google_drive_contents(request: HttpRequest):
    user = require_auth(request)
    service = GoogleDriveService(user)

    if not service.is_connected():
        raise HttpError(404, "Google Drive not connected. Please connect first.")

    if service.auth.needs_refresh():
        if not service.refresh_access_token():
            raise HttpError(401, "Token expired and refresh failed. Please reconnect.")
        service._load_auth()

    try:
        drive_data = service.list_all_files(page_size=100)
        files = drive_data.get("files", [])

        file_items = []
        folder_items = []
        for item in files:
            item_data = {
                "id": item.get("id"),
                "name": item.get("name"),
                "mimeType": item.get("mimeType"),
                "size": item.get("size"),
                "createdTime": item.get("createdTime"),
                "modifiedTime": item.get("modifiedTime"),
                "webViewLink": item.get("webViewLink"),
            }
            if item.get("mimeType") == "application/vnd.google-apps.folder":
                folder_items.append(item_data)
            else:
                file_items.append(item_data)

        user_info = service.get_account_info()

        return GoogleDriveContentsOut(
            success=True,
            integration_status="Google Drive integration is working properly",
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
                "expires_at": service.auth.expires_at.isoformat() if service.auth.expires_at else None,
                "scopes": service.auth.scopes,
            },
            message=f"Successfully accessed Google Drive. Found {len(files)} items.",
        )
    except Exception as e:
        logger.error(f"Error listing Google Drive contents: {e}")
        raise HttpError(500, f"Failed to list Google Drive contents: {str(e)}")


@router.get("/callback", include_in_schema=False, summary="OAuth callback endpoint")
def google_callback(request: HttpRequest):
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    if error:
        return render(request, "google/callback_error.html", {"error": error})

    expected_state = request.session.get("google_auth_state")
    if not state or not expected_state or state != expected_state:
        return render(request, "google/callback_error.html", {"error": "Invalid state parameter"})

    user_id = request.session.get("google_auth_user_id")
    if not user_id:
        return render(request, "google/callback_error.html", {"error": "User session not found"})

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return render(request, "google/callback_error.html", {"error": "User not found"})

    for key in ["google_auth_user_id", "google_auth_state"]:
        if key in request.session:
            del request.session[key]
    request.session.save()

    redirect_uri = os.getenv("GOOGLE_DRIVE_REDIRECT_URI")
    if not redirect_uri:
        return render(request, "google/callback_error.html", {"error": "Server configuration error"})

    try:
        service = GoogleDriveService(user)
        token_data = service.exchange_code_for_tokens(code, redirect_uri)
        service.save_tokens(token_data)
        service._load_auth()

        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)

        email = account_info.get("email", "")
        name = account_info.get("name", "")

        return render(request, "google/callback_success.html", {"email": email, "name": name})
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        return render(request, "google/callback_error.html", {"error": str(e)})
