"""Box Integration App Configuration."""

from django.apps import AppConfig


class BoxStorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.storage.box"
    verbose_name = "Box Integration"
    label = "storage_box"
