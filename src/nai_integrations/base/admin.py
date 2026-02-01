"""
Base admin classes for cloud storage integrations.
"""

import logging

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

logger = logging.getLogger(__name__)

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


class BaseCloudAuthAdmin(BaseModelAdmin):
    """Base admin class for cloud storage authentication models."""

    list_display = (
        "user_link",
        "email",
        "display_name",
        "active_icon",
        "connected_at",
        "updated_at",
    )
    list_filter = ("is_active", "connected_at")
    search_fields = ("user__username", "user__email", "email", "account_id")
    readonly_fields = ("connected_at", "updated_at", "account_id")

    fieldsets = (
        ("User Information", {"fields": ("user", "email", "display_name", "account_id")}),
        (
            "Token Information",
            {"fields": ("token_type", "expires_at", "scopes"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("is_active", "connected_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request):
        return False

    def user_link(self, obj):
        if hasattr(obj, "user") and obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "N/A"

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def active_icon(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981; font-size: 16px;">✓</span>'
            )
        return format_html('<span style="color: #ef4444; font-size: 16px;">✗</span>')

    active_icon.short_description = "Active"
    active_icon.admin_order_field = "is_active"
