"""
Box Integration App Configuration.
"""

from django.apps import AppConfig


class BoxIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nai_integrations.box"
    verbose_name = "Box Integration"
    label = "nai_box"
