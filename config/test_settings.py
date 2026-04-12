"""Test-only Django settings — in-memory sqlite, no external services."""

import os

os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY", "VGVzdEVuY3J5cHRpb25LZXkxMjM0NTY3ODkwMTI="
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from config.settings import *  # noqa: E402, F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TOKEN_ENCRYPTION_KEY = "VGVzdEVuY3J5cHRpb25LZXkxMjM0NTY3ODkwMTI="
REDIS_URL = "redis://localhost:6379/0"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_URL = "memory://"
