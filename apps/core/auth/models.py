"""AppClient model — API key holder for NEMI consumers."""

import hashlib
import secrets

from django.db import models


def _generate_api_key() -> str:
    """Generate a 48-char hex API key."""
    return secrets.token_hex(24)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of an API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


class AppClient(models.Model):
    """
    Represents an external application consuming NEMI APIs.
    Each client authenticates via X-API-Key header.
    """

    PERMISSION_CHOICES = [
        ("social", "Social Posting"),
        ("storage", "Cloud Storage"),
        ("notify", "Notifications"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='App name, e.g. "nai-backend", "indoxhub"',
    )
    api_key_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        help_text="SHA-256 hash of the API key",
    )
    api_key_prefix = models.CharField(
        max_length=8,
        editable=False,
        help_text="First 8 chars for identification",
    )
    permissions = models.JSONField(
        default=list,
        blank=True,
        help_text='List of scopes: ["social", "storage", "notify"]',
    )
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "nemi_app_client"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["api_key_prefix"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.api_key_prefix}...)"

    @classmethod
    def create_client(
        cls,
        name: str,
        permissions: list[str] | None = None,
        rate_limit: int = 60,
    ) -> tuple["AppClient", str]:
        """
        Create a new AppClient and return (client, raw_api_key).
        The raw key is only available at creation time.
        """
        raw_key = _generate_api_key()
        client = cls.objects.create(
            name=name,
            api_key_hash=_hash_key(raw_key),
            api_key_prefix=raw_key[:8],
            permissions=permissions or ["social", "storage", "notify"],
            rate_limit_per_minute=rate_limit,
        )
        return client, raw_key

    def rotate_key(self) -> str:
        """Generate a new API key. Returns the raw key (show once)."""
        raw_key = _generate_api_key()
        self.api_key_hash = _hash_key(raw_key)
        self.api_key_prefix = raw_key[:8]
        self.save(update_fields=["api_key_hash", "api_key_prefix", "updated_at"])
        return raw_key

    @classmethod
    def authenticate(cls, raw_key: str) -> "AppClient | None":
        """Look up active client by key prefix + hash verification."""
        if not raw_key or len(raw_key) < 8:
            return None
        prefix = raw_key[:8]
        key_hash = _hash_key(raw_key)
        try:
            return cls.objects.get(
                api_key_prefix=prefix,
                api_key_hash=key_hash,
                is_active=True,
            )
        except cls.DoesNotExist:
            return None

    def has_permission(self, scope: str) -> bool:
        """Check if client has a specific permission scope."""
        return scope in self.permissions
