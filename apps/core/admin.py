"""Django admin registration for core models."""

from django.contrib import admin, messages

from .auth.models import AppClient, _generate_api_key, _hash_key

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

    def save_model(self, request, obj, form, change) -> None:
        if not change:
            raw_key = _generate_api_key()
            obj.api_key_hash = _hash_key(raw_key)
            obj.api_key_prefix = raw_key[:8]
            super().save_model(request, obj, form, change)
            messages.success(
                request,
                f"API key for '{obj.name}': {raw_key}  — "
                "copy it now, it will not be shown again.",
            )
        else:
            super().save_model(request, obj, form, change)
