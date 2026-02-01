"""
Box Integration API Views.
"""

import logging
import os
import secrets
from datetime import datetime

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError

from nai_integrations.contrib.auth import require_auth

from .schemas import (
    BoxAuthorizeOut,
    BoxContentsOut,
    BoxDisconnectOut,
    BoxFileInfo,
    BoxStatusOut,
)
from .services import BoxService

logger = logging.getLogger(__name__)
router = Router(tags=["Box Integration"])
User = get_user_model()


@router.get("/status/", response=BoxStatusOut, summary="Check Box connection status")
def get_box_status(request: HttpRequest):
    user = require_auth(request)
    service = BoxService(user)
    status = service.get_connection_status()
    return BoxStatusOut(**status)


@router.post(
    "/authorize/", response=BoxAuthorizeOut, summary="Initiate Box OAuth authorization"
)
def authorize_box(request: HttpRequest):
    user = require_auth(request)
    callback_url = os.getenv(
        "BOX_REDIRECT_URI",
        f"{request.build_absolute_uri('/').rstrip('/')}/api/v1/box/callback",
    )
    state = secrets.token_urlsafe(32)
    request.session["box_auth_user_id"] = user.id
    request.session["box_auth_state"] = state
    request.session.save()
    service = BoxService(user)
    auth_url = service.get_authorization_url(callback_url, state)
    return BoxAuthorizeOut(
        authorization_url=auth_url,
        message="Please visit the authorization URL to connect your Box account",
    )


@router.delete(
    "/disconnect/", response=BoxDisconnectOut, summary="Disconnect Box account"
)
def disconnect_box(request: HttpRequest):
    user = require_auth(request)
    service = BoxService(user)
    if not service.is_connected():
        raise HttpError(400, "Box is not connected")
    success = service.disconnect()
    return BoxDisconnectOut(
        success=success,
        message="Box account disconnected successfully"
        if success
        else "Failed to disconnect Box",
    )


@router.get("/contents/", response=BoxContentsOut, summary="List Box folder contents")
def get_box_contents(request: HttpRequest):
    user = require_auth(request)
    service = BoxService(user)
    folder_id = request.GET.get("folder_id", "0")
    limit = int(request.GET.get("limit", "100"))
    offset = int(request.GET.get("offset", "0"))

    if not service.is_connected():
        raise HttpError(400, "Box is not connected. Please authorize first.")

    try:
        folder_data = service.list_folder(folder_id, limit, offset)
        entries = []
        for entry in folder_data.get("entries", []):
            path_parts = []
            if "path_collection" in entry and "entries" in entry["path_collection"]:
                path_parts = [p["name"] for p in entry["path_collection"]["entries"]]
            path_parts.append(entry.get("name", ""))
            path = "/" + "/".join(path_parts)

            modified = None
            if entry.get("modified_at"):
                try:
                    modified = datetime.fromisoformat(
                        entry["modified_at"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            file_info = BoxFileInfo(
                name=entry.get("name", ""),
                path=path,
                type=entry.get("type", "file"),
                size=entry.get("size"),
                modified=modified,
                id=entry.get("id", ""),
            )
            entries.append(file_info)

        return BoxContentsOut(
            path=f"/{folder_id}" if folder_id != "0" else "/",
            entries=entries,
            total_count=folder_data.get("total_count", len(entries)),
            offset=folder_data.get("offset", offset),
            limit=folder_data.get("limit", limit),
        )
    except Exception as e:
        logger.error(f"Failed to list Box contents: {e}", exc_info=True)
        raise HttpError(500, f"Failed to list Box contents: {str(e)}")


@router.get("/callback", include_in_schema=False, summary="OAuth callback endpoint")
def box_callback(request: HttpRequest):
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")
    error_description = request.GET.get("error_description", "")

    if error:
        logger.warning(f"Box OAuth error: {error} - {error_description}")
        return render(
            request,
            "box/callback_error.html",
            {
                "error": error_description or error,
                "description": "We couldn't connect your Box account.",
            },
        )

    if not code:
        return render(
            request,
            "box/callback_error.html",
            {
                "error": "No authorization code provided",
                "description": "Please try the authorization process again.",
            },
        )

    expected_state = request.session.get("box_auth_state")
    if not state or not expected_state or state != expected_state:
        return render(
            request,
            "box/callback_error.html",
            {
                "error": "Invalid state parameter",
                "description": "Please try connecting your Box account again.",
            },
        )

    try:
        user_id = request.session.get("box_auth_user_id")
        if not user_id:
            return render(
                request,
                "box/callback_error.html",
                {"error": "User not authenticated", "description": "Please log in and try again."},
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return render(
                request,
                "box/callback_error.html",
                {"error": "User not found", "description": "Please try again."},
            )

        service = BoxService(user)
        callback_url = os.getenv(
            "BOX_REDIRECT_URI",
            f"{request.build_absolute_uri('/').rstrip('/')}/api/v1/box/callback",
        )

        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()

        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)

        for key in ["box_auth_user_id", "box_auth_state"]:
            if key in request.session:
                del request.session[key]
        request.session.save()

        email = account_info.get("login", "")
        display_name = account_info.get("name", "")

        logger.info(f"Box OAuth successful for user {user.username}: {email}")
        return render(
            request, "box/callback_success.html", {"email": email, "name": display_name}
        )

    except Exception as e:
        logger.error(f"Box OAuth callback error: {e}", exc_info=True)
        return render(
            request,
            "box/callback_error.html",
            {"error": str(e), "description": "An unexpected error occurred."},
        )
