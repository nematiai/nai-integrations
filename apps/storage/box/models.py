"""Box Integration Models."""

from django.db import models

from apps.storage.base.models import BaseCloudAuth


class BoxAuth(BaseCloudAuth):
    """Model to store Box OAuth tokens per app_client + user."""

    class Meta:
        db_table = "nemi_storage_box_auth"
        verbose_name = "Box Authentication"
        verbose_name_plural = "Box Authentications"
        unique_together = [("app_client", "external_user_id")]
        indexes = [
            models.Index(
                fields=["app_client", "is_active"],
                name="stbox_client_active_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="stbox_expires_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Box - {self.app_client.name}:{self.external_user_id} ({self.email})"
