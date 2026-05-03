"""Phase 1.2 secrets audit — settings hardening regression tests."""

import importlib
import os
import sys
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured


def _reload_settings(env: dict) -> object:
    """Reload config.settings under a controlled env. Restores os.environ after.

    Patches dotenv.load_dotenv to a no-op so the working tree .env cannot
    leak SECRET_KEY/DEBUG defaults into the test.
    """
    backup = {k: os.environ.get(k) for k in env}
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    sys.modules.pop("config.settings", None)
    try:
        with patch("dotenv.load_dotenv", lambda *a, **kw: False):
            return importlib.import_module("config.settings")
    finally:
        for k, v in backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        sys.modules.pop("config.settings", None)


class TestSecretKeyHardening:
    def test_missing_secret_key_with_debug_false_raises(self):
        with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
            _reload_settings({"SECRET_KEY": None, "DEBUG": "false"})

    def test_missing_secret_key_with_debug_true_uses_dev_fallback(self):
        mod = _reload_settings({"SECRET_KEY": None, "DEBUG": "true"})
        assert mod.SECRET_KEY.startswith("django-insecure-")
        assert mod.DEBUG is True

    def test_explicit_secret_key_honored(self):
        mod = _reload_settings(
            {"SECRET_KEY": "explicit-prod-key-xyz", "DEBUG": "false"}
        )
        assert mod.SECRET_KEY == "explicit-prod-key-xyz"
        assert mod.DEBUG is False


class TestDebugDefault:
    def test_debug_defaults_to_false_when_unset(self):
        mod = _reload_settings(
            {"SECRET_KEY": "test-key", "DEBUG": None}
        )
        assert mod.DEBUG is False
