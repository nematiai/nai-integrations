"""OneDrive Integration Models."""

from django.db import models

from apps.storage.base.models import BaseCloudAuth


class OneDriveAuth(BaseCloudAuth):
    """Model to store OneDrive OAuth tokens per app_client + user."""

    class Meta:
        db_table = "nemi_storage_onedrive_auth"
        verbose_name = "OneDrive Authentication"
        verbose_name_plural = "OneDrive Authentications"
        unique_together = [("app_client", "external_user_id")]
        indexes = [
            models.Index(
                fields=["app_client", "is_active"],
                name="stod_client_active_idx",
            ),
            models.Index(fields=["expires_at"], name="stod_expires_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"OneDrive - {self.app_client.name}:{self.external_user_id} ({self.email})"
        )
