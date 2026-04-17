"""Smoke tests for apps.notify — verifies package loads cleanly."""

import pytest


@pytest.mark.unit
def test_notify_app_importable():
    """apps.notify should import without errors."""
    import apps.notify  # noqa: F401


@pytest.mark.unit
def test_notify_app_config_valid():
    """apps.notify Django AppConfig should be registered."""
    from django.apps import apps as django_apps

    config = django_apps.get_app_config("notify")
    assert config.name == "apps.notify"
