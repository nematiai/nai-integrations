"""Test-only Django settings — in-memory sqlite, no external services.

Env file loading (controlled by NEMI_TEST_ENV):
    (unset)   -> pure unit tests, no .env loading
    mocked    -> loads .env.test  (for integration_mocked tests)
    live      -> loads .env.test.live  (for integration_live tests)

Real vendor credentials MUST NEVER be loaded for unit tests.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Conditional env file loading ---
_test_env = os.environ.get("NEMI_TEST_ENV", "").lower()

if _test_env == "mocked":
    load_dotenv(BASE_DIR / ".env.test", override=False)
elif _test_env == "live":
    load_dotenv(BASE_DIR / ".env.test.live", override=False)
# else: pure unit tests — no env file loaded

# --- Defaults for unit tests (used when no .env.test* is loaded) ---
os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from config.settings import *  # noqa: E402, F401, F403

# --- Test-specific overrides ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TOKEN_ENCRYPTION_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
REDIS_URL = "redis://localhost:6379/0"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = "memory://"
DEBUG = False
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rate-limit-tests",
    }
}
RATELIMIT_USE_CACHE = "default"
RATE_LIMIT_ANON = "30/m"
RATE_LIMIT_USER = "120/m"
RATE_LIMIT_OAUTH = "10/m"
