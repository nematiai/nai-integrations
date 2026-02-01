"""
Abstract base model for cloud storage authentication.
"""

import logging
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseCloudAuth(models.Model):
    """
    Abstract base model for storing OAuth tokens for cloud storage providers.
    
    All provider-specific models should inherit from this class.
    Provides encrypted token storage and common functionality.
    """
    
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        help_text="User who connected this cloud storage"
    )
    _access_token = models.TextField(
        db_column='access_token',
        help_text="Encrypted access token"
    )
    _refresh_token = models.TextField(
        db_column='refresh_token',
        blank=True,
        null=True,
        help_text="Encrypted refresh token for automatic renewal"
    )
    token_type = models.CharField(
        max_length=50,
        default="bearer",
        help_text="Token type (usually bearer)"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    account_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Provider account ID"
    )
    email = models.EmailField(
        blank=True,
        help_text="Email associated with the account"
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Display name from provider"
    )
    scopes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of granted OAuth scopes"
    )
    connected_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the account was first connected"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time the tokens were updated"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the connection is active"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        provider = self.__class__.__name__.replace("Auth", "")
        return f"{provider} - {self.user.username} ({self.email})"

    # =========================================================================
    # Token Encryption/Decryption
    # =========================================================================

    @staticmethod
    def _get_encryption_key():
        """Get the encryption key from settings."""
        key = getattr(settings, 'TOKEN_ENCRYPTION_KEY', None)
        if not key:
            logger.warning("TOKEN_ENCRYPTION_KEY not set, tokens will be stored unencrypted")
        return key

    @classmethod
    def _encrypt_token(cls, token: str) -> str:
        """Encrypt a token for storage."""
        if not token:
            return token
            
        key = cls._get_encryption_key()
        if not key:
            return token
            
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.encrypt(token.encode()).decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            return token

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
            # Token might not be encrypted (legacy data)
            logger.warning("Token decryption failed - may be unencrypted legacy data")
            return encrypted
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            return encrypted

    # =========================================================================
    # Property-based access for encrypted tokens
    # =========================================================================

    @property
    def decrypted_access_token(self) -> str:
        """Get decrypted access token."""
        return self._decrypt_token(self._access_token)

    @decrypted_access_token.setter
    def decrypted_access_token(self, value: str):
        """Set encrypted access token."""
        self._access_token = self._encrypt_token(value)

    @property
    def decrypted_refresh_token(self) -> str:
        """Get decrypted refresh token."""
        if self._refresh_token:
            return self._decrypt_token(self._refresh_token)
        return None

    @decrypted_refresh_token.setter
    def decrypted_refresh_token(self, value: str):
        """Set encrypted refresh token."""
        if value:
            self._refresh_token = self._encrypt_token(value)
        else:
            self._refresh_token = None

    # =========================================================================
    # Token Status Methods
    # =========================================================================

    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at

    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        """
        Check if token needs refresh.
        
        Args:
            buffer_minutes: Refresh if token expires within this many minutes
            
        Returns:
            True if token should be refreshed
        """
        if not self.expires_at:
            return False
        buffer = timedelta(minutes=buffer_minutes)
        return timezone.now() >= (self.expires_at - buffer)

    def time_until_expiry(self) -> timedelta:
        """Get time remaining until token expires."""
        if not self.expires_at:
            return timedelta(days=365)  # Return large value if no expiry
        return self.expires_at - timezone.now()
