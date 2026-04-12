"""Google Drive Integration App Configuration."""

from django.apps import AppConfig


class GoogleStorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.storage.google"
    verbose_name = "Google Drive Integration"
    label = "storage_google"
