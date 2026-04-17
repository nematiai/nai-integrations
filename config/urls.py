"""NEMI URL configuration."""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.core.auth.views import router as auth_router
from apps.core.base.health import get_health_status

api = NinjaAPI(
    title="NEMI — Nemati Integration Hub",
    version="1.0.0",
    urls_namespace="api",
    docs_url="/v1/docs/",
)

# Auth endpoints
api.add_router("/v1/auth/", auth_router)

# Notification endpoints (channels, templates, logs, send)
from apps.notify.api.router import router as notify_channels_router  # noqa: E402
from apps.notify.api.router_actions import router as notify_actions_router  # noqa: E402
from apps.notify.api.router_templates import router as notify_templates_router  # noqa: E402

api.add_router("/v1/notify/", notify_channels_router)
api.add_router("/v1/notify/", notify_templates_router)
api.add_router("/v1/notify/", notify_actions_router)

# Storage endpoints
from apps.storage.box.views import router as box_router  # noqa: E402
from apps.storage.dropbox.views import router as dropbox_router  # noqa: E402
from apps.storage.google.views import router as google_router  # noqa: E402
from apps.storage.onedrive.views import router as onedrive_router  # noqa: E402

api.add_router("/v1/storage/box/", box_router)
api.add_router("/v1/storage/dropbox/", dropbox_router)
api.add_router("/v1/storage/google/", google_router)
api.add_router("/v1/storage/onedrive/", onedrive_router)


# Social endpoints (Step 6)
from apps.social.urls import router as social_router  # noqa: E402

api.add_router("/v1/social/", social_router)


@api.get("/v1/health/", tags=["health"], auth=None)
def health_check(request):
    return get_health_status()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
