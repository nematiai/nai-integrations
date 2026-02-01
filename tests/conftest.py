"""
Pytest configuration for nai-integrations tests.
"""

import os
import sys

import django
from django.conf import settings

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def pytest_configure():
    """Configure Django settings for tests."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY='test-secret-key-not-for-production',
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'nai_integrations.box',
                'nai_integrations.dropbox',
                'nai_integrations.google',
                'nai_integrations.onedrive',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
            USE_TZ=True,
            TIME_ZONE='UTC',
            TOKEN_ENCRYPTION_KEY='VGVzdEVuY3J5cHRpb25LZXkxMjM0NTY3ODkwMTI=',
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                }
            },
            NAI_INTEGRATIONS={
                'AUTH_ADAPTER': None,
            },
        )
        django.setup()