"""Abstract base model for cloud storage authentication."""

import logging
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseCloudAuth(models.Model):
    """
    Abstract base model for storing OAuth tokens for cloud storage providers.

    Uses app_client + external_user_id composite key instead of Django User.
    NEMI never imports AUTH_USER_MODEL — external_user_id is opaque.
    """

    app_client = models.ForeignKey(
        "core.AppClient",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_connections",
        help_text="The application that owns this connection",
    )
    external_user_id = models.CharField(
        max_length=255,
        help_text="Opaque user ID from the calling application",
    )
    _access_token = models.TextField(
        db_column="access_token",
        help_text="Encrypted access token",
    )
    _refresh_token = models.TextField(
        db_column="refresh_token",
        blank=True,
        null=True,
        help_text="Encrypted refresh token",
    )
    token_type = models.CharField(max_length=50, default="bearer")
    expires_at = models.DateTimeField(null=True, blank=True)
    account_id = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["app_client", "external_user_id"]),
            models.Index(fields=["expires_at"]),
        ]
        unique_together = [("app_client", "external_user_id")]

    def __str__(self) -> str:
        provider = self.__class__.__name__.replace("Auth", "")
        return f"{provider} - {self.app_client.name}:{self.external_user_id} ({self.email})"

    @staticmethod
    def _get_encryption_key() -> str | None:
        """Get the encryption key from settings."""
        key = getattr(settings, "TOKEN_ENCRYPTION_KEY", None)
        if not key:
            logger.warning("TOKEN_ENCRYPTION_KEY not set")
        return key

    @classmethod
    def _encrypt_token(cls, token: str) -> str:
        """Encrypt a token for storage. Raises if encryption key is missing."""
        if not token:
            return token
        key = cls._get_encryption_key()
        if not key:
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                "TOKEN_ENCRYPTION_KEY must be set; refusing to store tokens in plaintext"
            )
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(token.encode()).decode()

    @classmethod
    def _decrypt_token(cls, encrypted: str) -> str:
        """Decrypt a stored token."""
        if not encrypted:
            return encrypted
        key = cls._get_encryption_key()
        if not key:
            return encrypted
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            logger.warning("Token decryption failed — may be unencrypted legacy data")
            return encrypted
        except Exception as e:
            logger.error("Token decryption failed: %s", e)
            return encrypted

    @property
    def decrypted_access_token(self) -> str:
        return self._decrypt_token(self._access_token)

    @decrypted_access_token.setter
    def decrypted_access_token(self, value: str) -> None:
        self._access_token = self._encrypt_token(value)

    @property
    def decrypted_refresh_token(self) -> str | None:
        if self._refresh_token:
            return self._decrypt_token(self._refresh_token)
        return None

    @decrypted_refresh_token.setter
    def decrypted_refresh_token(self, value: str) -> None:
        if value:
            self._refresh_token = self._encrypt_token(value)
        else:
            self._refresh_token = None

    def is_token_expired(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at

    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        if not self.expires_at:
            return False
        buffer = timedelta(minutes=buffer_minutes)
        return timezone.now() >= (self.expires_at - buffer)

    def time_until_expiry(self) -> timedelta:
        if not self.expires_at:
            return timedelta(days=365)
        return self.expires_at - timezone.now()
