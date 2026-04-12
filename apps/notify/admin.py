"""Django admin registration for notification models."""

from django.contrib import admin

from .models import NotificationChannel, NotificationLog, NotificationTemplate
from .services import NotificationService

try:
    from unfold.admin import ModelAdmin as BaseModelAdmin
except ImportError:
    from django.contrib.admin import ModelAdmin as BaseModelAdmin


@admin.register(NotificationChannel)
class NotificationChannelAdmin(BaseModelAdmin):
    list_display = ["name", "service_type", "is_active", "created_at"]
    list_filter = ["service_type", "is_active"]
    search_fields = ["name"]
    ordering = ["-created_at"]
    readonly_fields = ["apprise_url", "created_at", "updated_at"]
    actions = ["test_channels", "activate_channels", "deactivate_channels"]

    fieldsets = (
        (None, {"fields": ("name", "service_type", "is_active")}),
        ("Configuration", {"fields": ("config",)}),
        (
            "System",
            {
                "fields": ("apprise_url", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change) -> None:
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Test selected channels")
    def test_channels(self, request, queryset) -> None:
        ok = fail = 0
        svc = NotificationService()
        for ch in queryset:
            success, _ = svc.test_channel(ch)
            if success:
                ok += 1
            else:
                fail += 1
        self.message_user(request, f"Tested: {ok} ok, {fail} failed")

    @admin.action(description="Activate selected channels")
    def activate_channels(self, request, queryset) -> None:
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected channels")
    def deactivate_channels(self, request, queryset) -> None:
        queryset.update(is_active=False)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(BaseModelAdmin):
    list_display = ["name", "template_type", "is_active", "created_at"]
    list_filter = ["template_type", "is_active"]
    search_fields = ["name", "title_template", "body_template"]
    filter_horizontal = ["channels"]
    fieldsets = (
        (None, {"fields": ("name", "template_type", "is_active")}),
        ("Content", {"fields": ("title_template", "body_template")}),
        ("Delivery", {"fields": ("channels",)}),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(BaseModelAdmin):
    list_display = ["title", "channel", "status", "sent_at", "created_at"]
    list_filter = ["status", "channel__service_type"]
    search_fields = ["title", "body"]
    ordering = ["-created_at"]
    readonly_fields = [
        "channel",
        "template",
        "title",
        "body",
        "status",
        "error_message",
        "context_data",
        "sent_at",
        "created_at",
    ]

    def has_add_permission(self, _request) -> bool:
        return False

    def has_change_permission(self, _request, _obj=None) -> bool:
        return False
