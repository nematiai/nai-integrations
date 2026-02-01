# NAI Integrations

A Django package providing unified OAuth 2.0 integrations for cloud storage providers: **Box**, **Dropbox**, **Google Drive**, and **OneDrive**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2+](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Unified API**: Consistent interface across all providers
- **Encrypted Token Storage**: Fernet encryption for tokens at rest
- **Automatic Token Refresh**: Proactive refresh before expiration
- **Celery Tasks**: Background token refresh (optional)
- **Pluggable Authentication**: Adapter pattern for custom auth systems
- **Django Admin Integration**: Built-in admin interfaces

## Installation

```bash
pip install git+https://github.com/NematiAI/nai-integrations.git
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    'nai_integrations.box',
    'nai_integrations.dropbox',
    'nai_integrations.google',
    'nai_integrations.onedrive',
]
```

### 2. Configure Environment

```bash
TOKEN_ENCRYPTION_KEY=your-32-byte-fernet-key

BOX_CLIENT_ID=...
BOX_CLIENT_SECRET=...
BOX_REDIRECT_URI=https://yourapp.com/api/v1/box/callback

DROPBOX_CLIENT_ID=...
DROPBOX_CLIENT_SECRET=...
DROPBOX_REDIRECT_URI=https://yourapp.com/api/v1/dropbox/callback

GOOGLE_OAUTH2_CLIENT_ID=...
GOOGLE_OAUTH2_CLIENT_SECRET=...
GOOGLE_DRIVE_REDIRECT_URI=https://yourapp.com/api/v1/google/callback

ONEDRIVE_CLIENT_ID=...
ONEDRIVE_CLIENT_SECRET=...
ONEDRIVE_REDIRECT_URI=https://yourapp.com/api/v1/onedrive/callback
```

### 3. Configure Auth Adapter

```python
# your_project/integrations_auth.py
from nai_integrations.contrib.auth import BaseAuthAdapter

class IntegrationsAuthAdapter(BaseAuthAdapter):
    def get_user_from_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        return None

    def get_ninja_auth(self):
        from ninja.security import django_auth
        return django_auth
```

```python
# settings.py
NAI_INTEGRATIONS = {
    'AUTH_ADAPTER': 'your_project.integrations_auth.IntegrationsAuthAdapter',
}
```

### 4. Register Routes

```python
from ninja import NinjaAPI
from nai_integrations.box.views import router as box_router
from nai_integrations.dropbox.views import router as dropbox_router
from nai_integrations.google.views import router as google_router
from nai_integrations.onedrive.views import router as onedrive_router

api = NinjaAPI()
api.add_router("/integrations/box/", box_router)
api.add_router("/integrations/dropbox/", dropbox_router)
api.add_router("/integrations/google/", google_router)
api.add_router("/integrations/onedrive/", onedrive_router)
```

## Using Services Directly

```python
from nai_integrations.google.services import GoogleDriveService

service = GoogleDriveService(user)
if service.is_connected():
    files = service.list_all_files(page_size=100)
    for file in files.get('files', []):
        print(file['name'])
```

## License

MIT License - see LICENSE
