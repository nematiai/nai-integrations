"""Dropbox Integration Admin Configuration."""

from django.contrib import admin

from apps.storage.base.admin import BaseCloudAuthAdmin

from .models import DropboxAuth


@admin.register(DropboxAuth)
class DropboxAuthAdmin(BaseCloudAuthAdmin):
    """Admin interface for Dropbox authentications."""
