"""Unfold admin for social media models."""

import logging

from django.contrib import admin
from django.utils.html import format_html

from apps.social.base.models import PostLog, SocialAccount

logger = logging.getLogger(__name__)

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


@admin.register(SocialAccount)
class SocialAccountAdmin(BaseModelAdmin):
    """Admin for social media account connections."""

    list_display = (
        "client_name",
        "external_user_id",
        "platform",
        "active_icon",
        "health_status",
        "last_health_check",
    )
    list_filter = ("platform", "is_active", "health_status", "app_client")
    search_fields = (
        "app_client__name",
        "external_user_id",
        "platform",
    )
    readonly_fields = ("created_at", "updated_at", "last_health_check")

    fieldsets = (
        (
            "Connection",
            {"fields": ("app_client", "external_user_id", "platform")},
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "health_status",
                    "last_health_check",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize with select_related."""
        return super().get_queryset(request).select_related("app_client")

    def has_add_permission(self, request):
        """Accounts are created via API only."""
        return False

    def client_name(self, obj) -> str:
        """Display the app client name."""
        return obj.app_client.name if obj.app_client else "N/A"

    client_name.short_description = "App Client"
    client_name.admin_order_field = "app_client__name"

    def active_icon(self, obj) -> str:
        """Display a colored icon for active status."""
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981;">&#10003;</span>',
            )
        return format_html(
            '<span style="color: #ef4444;">&#10007;</span>',
        )

    active_icon.short_description = "Active"
    active_icon.admin_order_field = "is_active"


@admin.register(PostLog)
class PostLogAdmin(BaseModelAdmin):
    """Admin for social post logs — read-only."""

    list_display = (
        "client_name",
        "external_user_id",
        "platform",
        "status",
        "created_at",
    )
    list_filter = ("platform", "status")
    readonly_fields = (
        "app_client",
        "external_user_id",
        "platform",
        "content",
        "media_url",
        "status",
        "error",
        "external_id",
        "posted_at",
        "created_at",
    )

    def get_queryset(self, request):
        """Optimize with select_related."""
        return super().get_queryset(request).select_related("app_client")

    def has_add_permission(self, request):
        """Logs are created by the system only."""
        return False

    def has_change_permission(self, request, obj=None):
        """Logs are immutable."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Logs cannot be deleted from admin."""
        return False

    def client_name(self, obj) -> str:
        """Display the app client name."""
        return obj.app_client.name if obj.app_client else "N/A"

    client_name.short_description = "App Client"
    client_name.admin_order_field = "app_client__name"
