"""Google Drive Integration Models."""

from django.db import models

from apps.storage.base.models import BaseCloudAuth


class GoogleAuth(BaseCloudAuth):
    """Model to store Google OAuth tokens per app_client + user."""

    google_user_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "nemi_storage_google_auth"
        verbose_name = "Google Authentication"
        verbose_name_plural = "Google Authentications"
        unique_together = [("app_client", "external_user_id")]
        indexes = [
            models.Index(
                fields=["app_client", "is_active"],
                name="stggl_client_active_idx",
            ),
            models.Index(fields=["expires_at"], name="stggl_expires_idx"),
            models.Index(fields=["email"], name="stggl_email_idx"),
        ]

    def __str__(self) -> str:
        return f"Google - {self.app_client.name}:{self.external_user_id} ({self.email})"
