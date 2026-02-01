"""
Google Drive Integration Models.
"""

from django.db import models
from nai_integrations.base.models import BaseCloudAuth


class GoogleAuth(BaseCloudAuth):
    """Model to store Google OAuth tokens for users."""

    google_user_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "nai_google_auth"
        verbose_name = "Google Authentication"
        verbose_name_plural = "Google Authentications"
        indexes = [
            models.Index(fields=["user", "is_active"], name="nai_google_user_active_idx"),
            models.Index(fields=["expires_at"], name="nai_google_expires_idx"),
            models.Index(fields=["email"], name="nai_google_email_idx"),
        ]

    def __str__(self):
        return f"Google - {self.user.username} ({self.email})"
