"""
Dropbox Integration Models.
"""

from django.db import models
from nai_integrations.base.models import BaseCloudAuth


class DropboxAuth(BaseCloudAuth):
    """Model to store Dropbox OAuth tokens for users."""

    class Meta:
        db_table = "nai_dropbox_auth"
        verbose_name = "Dropbox Authentication"
        verbose_name_plural = "Dropbox Authentications"
        indexes = [
            models.Index(fields=["user", "is_active"], name="nai_dbx_user_active_idx"),
            models.Index(fields=["expires_at"], name="nai_dbx_expires_idx"),
        ]

    def __str__(self):
        return f"Dropbox - {self.user.username} ({self.email})"
