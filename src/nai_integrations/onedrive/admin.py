"""
OneDrive Integration Admin Configuration.
"""

from django.contrib import admin
from nai_integrations.base.admin import BaseCloudAuthAdmin
from .models import OneDriveAuth


@admin.register(OneDriveAuth)
class OneDriveAuthAdmin(BaseCloudAuthAdmin):
    """Admin interface for OneDrive authentications."""
    pass
