"""
Dropbox Integration App Configuration.
"""

from django.apps import AppConfig


class DropboxIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nai_integrations.dropbox"
    verbose_name = "Dropbox Integration"
    label = "nai_dropbox"
