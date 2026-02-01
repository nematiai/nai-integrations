"""
Box Integration Models.
"""

from django.db import models
from nai_integrations.base.models import BaseCloudAuth


class BoxAuth(BaseCloudAuth):
    """Model to store Box OAuth tokens for users."""

    class Meta:
        db_table = "nai_box_auth"
        verbose_name = "Box Authentication"
        verbose_name_plural = "Box Authentications"
        indexes = [
            models.Index(fields=["user", "is_active"], name="nai_box_user_active_idx"),
            models.Index(fields=["expires_at"], name="nai_box_expires_idx"),
        ]

    def __str__(self):
        return f"Box - {self.user.username} ({self.email})"
