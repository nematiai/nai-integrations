"""Auth API endpoints: register app, rotate key."""

import logging

from ninja import Router

from .models import AppClient
from .schemas import (
    ErrorSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    RotateKeyResponseSchema,
)

logger = logging.getLogger(__name__)
router = Router(tags=["auth"])


@router.post(
    "/register",
    response={201: RegisterResponseSchema, 400: ErrorSchema},
    auth=None,
)
def register_app(request, payload: RegisterRequestSchema):
    """Register a new app client and return its API key."""
    if AppClient.objects.filter(name=payload.name).exists():
        return 400, {"detail": f"App '{payload.name}' already registered"}

    client, raw_key = AppClient.create_client(
        name=payload.name,
        permissions=payload.permissions,
        rate_limit=payload.rate_limit_per_minute,
    )
    logger.info("Registered new app client: %s", client.name)
    return 201, {
        "id": client.id,
        "name": client.name,
        "api_key": raw_key,
        "api_key_prefix": client.api_key_prefix,
        "permissions": client.permissions,
        "created_at": client.created_at,
    }


@router.post(
    "/rotate-key",
    response={200: RotateKeyResponseSchema, 401: ErrorSchema},
)
def rotate_key(request):
    """Rotate the API key for the authenticated app client."""
    if not getattr(request, "app_client", None):
        return 401, {"detail": "Authentication required"}

    client = request.app_client
    new_key = client.rotate_key()
    logger.info("Rotated API key for: %s", client.name)
    return {
        "api_key": new_key,
        "api_key_prefix": client.api_key_prefix,
        "message": "Key rotated. Store the new key — it cannot be retrieved.",
    }
