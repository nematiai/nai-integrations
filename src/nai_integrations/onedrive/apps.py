"""
OneDrive Integration App Configuration.
"""

from django.apps import AppConfig


class OneDriveIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nai_integrations.onedrive"
    verbose_name = "OneDrive Integration"
    label = "nai_onedrive"
