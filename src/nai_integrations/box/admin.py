"""
Box Integration Admin Configuration.
"""

from django.contrib import admin

from nai_integrations.base.admin import BaseCloudAuthAdmin

from .models import BoxAuth


@admin.register(BoxAuth)
class BoxAuthAdmin(BaseCloudAuthAdmin):
    """Admin interface for Box authentications."""

    pass
