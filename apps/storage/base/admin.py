"""Base admin classes for cloud storage integrations."""

import logging

from django.utils.html import format_html

logger = logging.getLogger(__name__)

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


class BaseCloudAuthAdmin(BaseModelAdmin):
    """Base admin class for cloud storage authentication models."""

    list_display = (
        "client_name",
        "external_user_id",
        "email",
        "display_name",
        "active_icon",
        "connected_at",
        "updated_at",
    )
    list_filter = ("is_active", "app_client", "connected_at")
    search_fields = (
        "app_client__name",
        "external_user_id",
        "email",
        "account_id",
    )
    readonly_fields = ("connected_at", "updated_at", "account_id")

    fieldsets = (
        (
            "Connection",
            {"fields": ("app_client", "external_user_id")},
        ),
        (
            "Account Info",
            {"fields": ("email", "display_name", "account_id")},
        ),
        (
            "Token Info",
            {
                "fields": ("token_type", "expires_at", "scopes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Status",
            {"fields": ("is_active", "connected_at", "updated_at")},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("app_client")

    def has_add_permission(self, request):
        return False

    def client_name(self, obj) -> str:
        return obj.app_client.name if obj.app_client else "N/A"

    client_name.short_description = "App Client"
    client_name.admin_order_field = "app_client__name"

    def active_icon(self, obj) -> str:
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981; font-size: 16px;">&#10003;</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-size: 16px;">&#10007;</span>'
        )

    active_icon.short_description = "Active"
    active_icon.admin_order_field = "is_active"
