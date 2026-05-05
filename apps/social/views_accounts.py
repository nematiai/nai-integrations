"""Social account management API endpoints."""

import logging
from typing import List

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from apps.core.base.exceptions import ConfigurationError
from apps.social.base.helpers import get_social_context
from apps.social.base.models import SocialAccount
from apps.social.base.schemas import (
    AccountOut,
    HealthOut,
    RegisterAccountIn,
)
from apps.social.registry import ADAPTERS, get_adapter

logger = logging.getLogger(__name__)
router = Router(tags=["Social Accounts"])


def _instantiate_adapter(platform: str, credentials: dict):
    """Validate platform + credentials by constructing the adapter."""
    if platform not in ADAPTERS:
        raise HttpError(400, f"Unknown platform: {platform}")
    try:
        return get_adapter(platform)(credentials)
    except ConfigurationError as exc:
        raise HttpError(400, f"Invalid credentials: {exc.message}") from exc
    except Exception as exc:
        logger.warning("Adapter init failed for %s: %s", platform, exc)
        raise HttpError(400, f"Invalid credentials: {exc}") from exc


def _run_health_check(account: SocialAccount, adapter) -> bool:
    """Run health_check if available and persist result on the account."""
    if not hasattr(adapter, "health_check"):
        return False
    try:
        healthy = bool(adapter.health_check())
    except Exception as exc:
        logger.warning("Health check raised for %s: %s", account.platform, exc)
        healthy = False
    account.health_status = "healthy" if healthy else "unhealthy"
    account.last_health_check = timezone.now()
    account.save(update_fields=["health_status", "last_health_check", "updated_at"])
    return healthy


@router.post("/accounts", response={201: AccountOut})
def register_account(request: HttpRequest, payload: RegisterAccountIn):
    """Register a social media account after validating credentials."""
    app_client, user_id = get_social_context(request)
    adapter = _instantiate_adapter(payload.platform, payload.credentials)

    account, _ = SocialAccount.objects.get_or_create(
        app_client=app_client,
        external_user_id=user_id,
        platform=payload.platform,
        defaults={"_credentials": ""},
    )
    account.decrypted_credentials = payload.credentials
    account.is_active = True
    account.save()
    _run_health_check(account, adapter)

    return 201, AccountOut(
        platform=account.platform,
        is_active=account.is_active,
        health_status=account.health_status,
        last_health_check=account.last_health_check,
        created_at=account.created_at,
    )


@router.get("/accounts", response=List[AccountOut])
def list_accounts(request: HttpRequest) -> List[AccountOut]:
    """List registered social accounts (credentials never returned)."""
    app_client, user_id = get_social_context(request)
    accounts = SocialAccount.objects.filter(
        app_client=app_client,
        external_user_id=user_id,
        is_active=True,
    ).order_by("platform")
    return [
        AccountOut(
            platform=a.platform,
            is_active=a.is_active,
            health_status=a.health_status,
            last_health_check=a.last_health_check,
            created_at=a.created_at,
        )
        for a in accounts
    ]


@router.delete("/accounts/{platform}")
def delete_account(request: HttpRequest, platform: str) -> dict:
    """Soft-delete a social account (set is_active=False)."""
    app_client, user_id = get_social_context(request)
    try:
        account = SocialAccount.objects.get(
            app_client=app_client,
            external_user_id=user_id,
            platform=platform,
        )
    except SocialAccount.DoesNotExist:
        raise HttpError(404, f"No {platform} account registered")

    account.is_active = False
    account.save(update_fields=["is_active", "updated_at"])
    return {"success": True}


@router.post("/accounts/{platform}/health", response=HealthOut)
def check_account_health(request: HttpRequest, platform: str) -> HealthOut:
    """Run a live health check against the registered account."""
    app_client, user_id = get_social_context(request)
    try:
        account = SocialAccount.objects.get(
            app_client=app_client,
            external_user_id=user_id,
            platform=platform,
            is_active=True,
        )
    except SocialAccount.DoesNotExist:
        raise HttpError(404, f"No active {platform} account")

    adapter = _instantiate_adapter(platform, account.decrypted_credentials)
    healthy = _run_health_check(account, adapter)
    return HealthOut(platform=platform, healthy=healthy)
