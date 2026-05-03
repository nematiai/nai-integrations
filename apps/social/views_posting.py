"""Social posting, logs, and platform discovery API endpoints."""

import logging
from typing import List

from django.http import HttpRequest
from ninja import Router

from apps.core.base.rate_limit import rate_limit_user
from apps.social.base.helpers import get_social_context
from apps.social.base.models import PostLog, SocialAccount
from apps.social.base.schemas import PlatformOut, PostIn, PostOut
from apps.social.registry import ADAPTERS
from apps.social.tasks import post_to_platform

logger = logging.getLogger(__name__)
router = Router(tags=["Social Posting"])


@router.post("/post", response=List[PostOut])
@rate_limit_user
def create_post(request: HttpRequest, payload: PostIn) -> List[PostOut]:
    """Queue a post to one or more platforms via Celery."""
    app_client, user_id = get_social_context(request)
    results: List[PostOut] = []

    for platform in payload.platforms:
        if platform not in ADAPTERS:
            log = PostLog.objects.create(
                app_client=app_client,
                external_user_id=user_id,
                platform=platform,
                content=payload.content,
                media_url=payload.media_url,
                status="failed",
                error=f"Unknown platform: {platform}",
            )
        else:
            log = PostLog.objects.create(
                app_client=app_client,
                external_user_id=user_id,
                platform=platform,
                content=payload.content,
                media_url=payload.media_url,
                status="pending",
            )
            post_to_platform.delay(log.id)

        results.append(
            PostOut(
                platform=log.platform,
                status=log.status,
                external_id=log.external_id or "",
                error=log.error,
                created_at=log.created_at,
            )
        )
    return results


@router.get("/platforms", response=List[PlatformOut])
@rate_limit_user
def list_platforms_endpoint(request: HttpRequest) -> List[PlatformOut]:
    """Return all registered adapter platforms and whether the user has them."""
    app_client, user_id = get_social_context(request)
    registered = set(
        SocialAccount.objects.filter(
            app_client=app_client,
            external_user_id=user_id,
            is_active=True,
        ).values_list("platform", flat=True)
    )
    return [
        PlatformOut(
            name=name,
            max_content_length=getattr(adapter_cls, "max_content_length", 0),
            supports_media=getattr(adapter_cls, "supports_media", False),
            registered=name in registered,
        )
        for name, adapter_cls in sorted(ADAPTERS.items())
    ]


@router.get("/logs", response=List[PostOut])
@rate_limit_user
def list_post_logs(request: HttpRequest) -> List[PostOut]:
    """Return post history for the authenticated user."""
    app_client, user_id = get_social_context(request)
    platform = request.GET.get("platform")
    status = request.GET.get("status")
    try:
        limit = max(1, min(int(request.GET.get("limit", "50")), 500))
        offset = max(0, int(request.GET.get("offset", "0")))
    except ValueError:
        limit, offset = 50, 0

    qs = PostLog.objects.filter(app_client=app_client, external_user_id=user_id)
    if platform:
        qs = qs.filter(platform=platform)
    if status:
        qs = qs.filter(status=status)

    logs = qs[offset : offset + limit]
    return [
        PostOut(
            platform=log.platform,
            status=log.status,
            external_id=log.external_id or "",
            error=log.error,
            created_at=log.created_at,
        )
        for log in logs
    ]
