"""Dropbox Integration Models."""

from django.db import models

from apps.storage.base.models import BaseCloudAuth


class DropboxAuth(BaseCloudAuth):
    """Model to store Dropbox OAuth tokens per app_client + user."""

    class Meta:
        db_table = "nemi_storage_dropbox_auth"
        verbose_name = "Dropbox Authentication"
        verbose_name_plural = "Dropbox Authentications"
        unique_together = [("app_client", "external_user_id")]
        indexes = [
            models.Index(
                fields=["app_client", "is_active"],
                name="stdbx_client_active_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="stdbx_expires_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Dropbox - {self.app_client.name}:{self.external_user_id} ({self.email})"
        )
