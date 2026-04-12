"""Models for social media accounts and post logs."""

import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """
    Stores social media account credentials per app_client + user + platform.

    Credentials are Fernet-encrypted JSON in the database.
    """

    HEALTH_CHOICES = [
        ("unknown", "Unknown"),
        ("healthy", "Healthy"),
        ("unhealthy", "Unhealthy"),
    ]

    app_client = models.ForeignKey(
        "core.AppClient",
        on_delete=models.CASCADE,
        related_name="social_accounts",
        help_text="The application that owns this account",
    )
    external_user_id = models.CharField(
        max_length=255,
        help_text="Opaque user ID from the calling application",
    )
    platform = models.CharField(
        max_length=50,
        help_text="Platform name (telegram, discord, etc.)",
    )
    _credentials = models.TextField(
        db_column="credentials",
        help_text="Fernet-encrypted JSON credentials",
    )
    is_active = models.BooleanField(default=True)
    health_status = models.CharField(
        max_length=10,
        choices=HEALTH_CHOICES,
        default="unknown",
    )
    last_health_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "social"
        db_table = "nemi_social_account"
        unique_together = [("app_client", "external_user_id", "platform")]
        indexes = [
            models.Index(
                fields=["app_client", "external_user_id", "platform"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.platform} - {self.app_client.name}:{self.external_user_id}"

    @staticmethod
    def _get_encryption_key() -> str | None:
        """Get the Fernet encryption key from settings."""
        key = getattr(settings, "TOKEN_ENCRYPTION_KEY", None)
        if not key:
            logger.warning("TOKEN_ENCRYPTION_KEY not set")
        return key

    @classmethod
    def _encrypt(cls, plaintext: str) -> str:
        """Encrypt a string for storage."""
        if not plaintext:
            return plaintext
        key = cls._get_encryption_key()
        if not key:
            return plaintext
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error("Credential encryption failed: %s", e)
            return plaintext

    @classmethod
    def _decrypt(cls, encrypted: str) -> str:
        """Decrypt a stored string."""
        if not encrypted:
            return encrypted
        key = cls._get_encryption_key()
        if not key:
            return encrypted
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            logger.warning("Decryption failed — may be unencrypted data")
            return encrypted
        except Exception as e:
            logger.error("Credential decryption failed: %s", e)
            return encrypted

    @property
    def decrypted_credentials(self) -> dict:
        """Decrypt credentials and return as dict."""
        raw = self._decrypt(self._credentials)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    @decrypted_credentials.setter
    def decrypted_credentials(self, value: dict) -> None:
        """Encrypt a dict and store as credentials."""
        self._credentials = self._encrypt(json.dumps(value))


class PostLog(models.Model):
    """Immutable log of social media post attempts."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    app_client = models.ForeignKey(
        "core.AppClient",
        on_delete=models.CASCADE,
        related_name="social_post_logs",
    )
    external_user_id = models.CharField(max_length=255)
    platform = models.CharField(max_length=50)
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )
    error = models.TextField(blank=True, null=True)
    external_id = models.CharField(max_length=255, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "social"
        db_table = "nemi_post_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["app_client", "external_user_id", "platform"],
            ),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform} [{self.status}] {self.created_at}"
