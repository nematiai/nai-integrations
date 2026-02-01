"""
OneDrive Integration Models.
"""

from django.db import models
from nai_integrations.base.models import BaseCloudAuth


class OneDriveAuth(BaseCloudAuth):
    """Model to store OneDrive OAuth tokens for users."""

    class Meta:
        db_table = "nai_onedrive_auth"
        verbose_name = "OneDrive Authentication"
        verbose_name_plural = "OneDrive Authentications"
        indexes = [
            models.Index(fields=["user", "is_active"], name="nai_od_user_active_idx"),
            models.Index(fields=["expires_at"], name="nai_od_expires_idx"),
        ]

    def __str__(self):
        return f"OneDrive - {self.user.username} ({self.email})"
