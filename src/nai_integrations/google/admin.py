"""
Google Drive Integration Admin Configuration.
"""

from django.contrib import admin
from nai_integrations.base.admin import BaseCloudAuthAdmin
from .models import GoogleAuth


@admin.register(GoogleAuth)
class GoogleAuthAdmin(BaseCloudAuthAdmin):
    """Admin interface for Google authentications."""
    list_display = (
        "user_link",
        "email",
        "display_name",
        "google_user_id",
        "active_icon",
        "connected_at",
    )
