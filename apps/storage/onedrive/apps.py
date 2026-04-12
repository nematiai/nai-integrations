"""OneDrive Integration App Configuration."""

from django.apps import AppConfig


class OneDriveStorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.storage.onedrive"
    verbose_name = "OneDrive Integration"
    label = "storage_onedrive"
