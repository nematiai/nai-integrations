"""Dropbox Integration App Configuration."""

from django.apps import AppConfig


class DropboxStorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.storage.dropbox"
    verbose_name = "Dropbox Integration"
    label = "storage_dropbox"
