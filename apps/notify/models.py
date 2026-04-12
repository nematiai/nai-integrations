"""Notification models for NEMI."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .schemas import SERVICE_SCHEMAS, build_apprise_url


class NotificationChannel(models.Model):
    """
    Single table storing all notification service configurations.
    Each channel stores an Apprise-compatible URL built from user config.
    """

    SERVICE_TYPES = [(key, schema["label"]) for key, schema in SERVICE_SCHEMAS.items()]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Friendly name, e.g., 'Marketing Slack', 'Admin Telegram'",
    )
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    config = models.JSONField(
        default=dict,
        help_text="Service-specific configuration (tokens, webhooks, etc.)",
    )
    apprise_url = models.TextField(
        blank=True,
        editable=False,
        help_text="Auto-generated Apprise URL from config",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_channels",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notify"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["service_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_service_type_display()})"

    def clean(self) -> None:
        """Validate config against service schema."""
        schema = SERVICE_SCHEMAS.get(self.service_type)
        if not schema:
            raise ValidationError(
                {"service_type": f"Unknown service: {self.service_type}"}
            )
        errors = {}
        for field in schema["fields"]:
            field_name = field["name"]
            value = self.config.get(field_name)
            if field.get("required") and not value:
                errors[field_name] = f"{field['label']} is required"
        if errors:
            msgs = [f"{k}: {v}" for k, v in errors.items()]
            raise ValidationError({"config": ", ".join(msgs)})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        self.apprise_url = self.build_apprise_url()
        super().save(*args, **kwargs)

    def build_apprise_url(self) -> str:
        """Build Apprise URL from config using service schema."""
        return build_apprise_url(self.service_type, self.config)


class NotificationTemplate(models.Model):
    """Reusable notification message templates."""

    TEMPLATE_TYPES = [
        ("alert", "Alert"),
        ("digest", "Digest"),
        ("health", "Health Check"),
        ("custom", "Custom"),
    ]

    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    title_template = models.CharField(
        max_length=250,
        help_text="Supports variables: {app_name}, {count}, etc.",
    )
    body_template = models.TextField(
        help_text="Supports variables: {app_name}, {count}, etc.",
    )
    channels = models.ManyToManyField(
        NotificationChannel,
        blank=True,
        related_name="templates",
        help_text="Channels to send this notification to",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notify"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_template_type_display()})"

    def render(self, context: dict) -> tuple[str, str]:
        """Render title and body with context variables."""
        title = self.title_template.format(**context)
        body = self.body_template.format(**context)
        return title, body


class NotificationLog(models.Model):
    """Audit log for all sent notifications."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs",
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    source_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Notification source (e.g. social, storage, health)",
    )
    source_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="ID of the source object",
    )
    title = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    context_data = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "notify"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["channel", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self) -> str:
        ch = self.channel.name if self.channel else "N/A"
        return f"{self.title} -> {ch}"
