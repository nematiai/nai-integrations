"""Django admin registration for core models."""

from django.contrib import admin

from .auth.models import AppClient

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


@admin.register(AppClient)
class AppClientAdmin(BaseModelAdmin):
    list_display = [
        "name",
        "api_key_prefix",
        "is_active",
        "rate_limit_per_minute",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "api_key_prefix"]
    readonly_fields = ["api_key_hash", "api_key_prefix", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        ("Permissions", {"fields": ("permissions", "rate_limit_per_minute")}),
        (
            "API Key",
            {
                "fields": ("api_key_prefix", "api_key_hash"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, _request) -> bool:
        return False
