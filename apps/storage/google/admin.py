"""Google Drive Integration Admin Configuration."""

from django.contrib import admin

from apps.storage.base.admin import BaseCloudAuthAdmin

from .models import GoogleAuth


@admin.register(GoogleAuth)
class GoogleAuthAdmin(BaseCloudAuthAdmin):
    """Admin interface for Google authentications."""

    list_display = (
        "client_name",
        "external_user_id",
        "email",
        "display_name",
        "google_user_id",
        "active_icon",
        "connected_at",
    )
