"""Box Integration API Views."""

import logging
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from apps.storage.base.helpers import get_storage_context

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


@router.get("/status/", response=BoxStatusOut)
def get_box_status(request: HttpRequest) -> BoxStatusOut:
    app_client, user_id = get_storage_context(request)
    service = BoxService(app_client, user_id)
    status = service.get_connection_status()
    return BoxStatusOut(**status)


@router.post("/authorize/", response=BoxAuthorizeOut)
def authorize_box(request: HttpRequest) -> BoxAuthorizeOut:
    app_client, user_id = get_storage_context(request)
    callback_url = getattr(settings, "BOX_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "BOX_REDIRECT_URI not configured")
    service = BoxService(app_client, user_id)
    auth_url = service.get_authorization_url(callback_url)
    return BoxAuthorizeOut(
        authorization_url=auth_url,
        message="Redirect user to this URL to connect Box",
    )


@router.post("/callback/")
def box_callback(request: HttpRequest) -> Dict[str, Any]:
    """NAI forwards the OAuth code here. No browser involved."""
    app_client, user_id = get_storage_context(request)
    code = request.GET.get("code") or request.POST.get("code")
    if not code:
        raise HttpError(400, "Authorization code required")

    callback_url = getattr(settings, "BOX_REDIRECT_URI", "")
    if not callback_url:
        raise HttpError(500, "BOX_REDIRECT_URI not configured")

    try:
        service = BoxService(app_client, user_id)
        token_data = service.exchange_code_for_tokens(code, callback_url)
        service.save_tokens(token_data)
        service._load_auth()
        account_info = service.get_account_info()
        service.save_tokens(token_data, account_info)
        return {"success": True, "email": account_info.get("login", "")}
    except Exception as e:
        logger.error("Box callback error: %s", e, exc_info=True)
        raise HttpError(500, f"Box connection failed: {str(e)}")


@router.delete("/disconnect/", response=BoxDisconnectOut)
def disconnect_box(request: HttpRequest) -> BoxDisconnectOut:
    app_client, user_id = get_storage_context(request)
    service = BoxService(app_client, user_id)
    if not service.is_connected():
        raise HttpError(400, "Box is not connected")
    success = service.disconnect()
    return BoxDisconnectOut(
        success=success,
        message="Box disconnected" if success else "Failed to disconnect",
    )


@router.get("/contents/", response=BoxContentsOut)
def get_box_contents(request: HttpRequest) -> BoxContentsOut:
    app_client, user_id = get_storage_context(request)
    service = BoxService(app_client, user_id)
    folder_id = request.GET.get("folder_id", "0")
    limit = int(request.GET.get("limit", "100"))
    offset = int(request.GET.get("offset", "0"))

    if not service.is_connected():
        raise HttpError(400, "Box is not connected")

    try:
        folder_data = service.list_folder(folder_id, limit, offset)
        entries = _parse_box_entries(folder_data)
        return BoxContentsOut(
            path=f"/{folder_id}" if folder_id != "0" else "/",
            entries=entries,
            total_count=folder_data.get("total_count", len(entries)),
            offset=folder_data.get("offset", offset),
            limit=folder_data.get("limit", limit),
        )
    except HttpError:
        raise
    except Exception as e:
        logger.error("Failed to list Box contents: %s", e, exc_info=True)
        raise HttpError(500, f"Failed to list Box contents: {str(e)}")


def _parse_box_entries(folder_data: Dict[str, Any]) -> list[BoxFileInfo]:
    """Parse Box API response into BoxFileInfo list."""
    entries = []
    for entry in folder_data.get("entries", []):
        path_parts = []
        path_coll = entry.get("path_collection", {})
        if "entries" in path_coll:
            path_parts = [p["name"] for p in path_coll["entries"]]
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

        entries.append(
            BoxFileInfo(
                name=entry.get("name", ""),
                path=path,
                type=entry.get("type", "file"),
                size=entry.get("size"),
                modified=modified,
                id=entry.get("id", ""),
            )
        )
    return entries
