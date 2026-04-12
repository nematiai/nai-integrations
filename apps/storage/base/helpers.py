"""Request helpers for storage views."""

from django.http import HttpRequest
from ninja.errors import HttpError

from apps.core.auth.models import AppClient


def get_storage_context(request: HttpRequest) -> tuple[AppClient, str]:
    """
    Extract app_client and external_user_id from the request.

    Middleware already validated X-API-Key and attached request.app_client.
    This function reads X-User-Id header for the target user.

    Returns:
        (app_client, external_user_id)

    Raises:
        HttpError 401 if app_client missing
        HttpError 400 if X-User-Id header missing
        HttpError 403 if app_client lacks storage permission
    """
    app_client = getattr(request, "app_client", None)
    if not app_client:
        raise HttpError(401, "Authentication required")

    if not app_client.has_permission("storage"):
        raise HttpError(403, "Storage permission required")

    user_id = request.META.get("HTTP_X_USER_ID", "").strip()
    if not user_id:
        raise HttpError(400, "X-User-Id header required")

    return app_client, user_id
