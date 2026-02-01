"""
Google Drive Integration App Configuration.
"""

from django.apps import AppConfig


class GoogleIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nai_integrations.google"
    verbose_name = "Google Drive Integration"
    label = "nai_google"
