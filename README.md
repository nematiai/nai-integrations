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
- **Django Admin Integration**: Built-in admin interfaces (supports django-unfold)

## Installation
```bash
# From GitHub (production)
pip install git+https://github.com/nematiai/nai-integrations.git@production

# From GitHub (latest)
pip install git+https://github.com/nematiai/nai-integrations.git

# With optional dependencies
pip install "nai-integrations[celery] @ git+https://github.com/nematiai/nai-integrations.git@production"
```

## Quick Start

### 1. Add to INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    # Django apps...
    'django.contrib.auth',
    'django.contrib.contenttypes',
    
    # NAI Integrations (add only what you need)
    'nai_integrations.box',
    'nai_integrations.dropbox',
    'nai_integrations.google',
    'nai_integrations.onedrive',
]
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Configure Environment Variables
```bash
# Token Encryption (REQUIRED)
# Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your-fernet-key-here

# Box
BOX_CLIENT_ID=your_client_id
BOX_CLIENT_SECRET=your_client_secret
BOX_REDIRECT_URI=https://yourapp.com/api/v1/integrations/box/callback

# Dropbox
DROPBOX_CLIENT_ID=your_client_id
DROPBOX_CLIENT_SECRET=your_client_secret
DROPBOX_REDIRECT_URI=https://yourapp.com/api/v1/integrations/dropbox/callback

# Google Drive
GOOGLE_OAUTH2_CLIENT_ID=your_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REDIRECT_URI=https://yourapp.com/api/v1/integrations/google/callback

# OneDrive
ONEDRIVE_CLIENT_ID=your_client_id
ONEDRIVE_CLIENT_SECRET=your_client_secret
ONEDRIVE_REDIRECT_URI=https://yourapp.com/api/v1/integrations/onedrive/callback
```

### 4. Configure Authentication Adapter

Create an adapter to bridge your auth system:
```python
# your_project/integrations_auth.py
from nai_integrations.contrib.auth import BaseAuthAdapter


class IntegrationsAuthAdapter(BaseAuthAdapter):
    """Adapter for your authentication system."""

    def get_user_from_request(self, request):
        # Session-based auth
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        
        # Or token-based auth
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            # Validate token and return user
            # ...
        
        return None

    def get_ninja_auth(self):
        # Return your django-ninja auth class
        from ninja.security import django_auth
        return django_auth
```

Register in settings:
```python
# settings.py
NAI_INTEGRATIONS = {
    'AUTH_ADAPTER': 'your_project.integrations_auth.IntegrationsAuthAdapter',
}
```

### 5. Register API Routes
```python
# urls.py or api.py
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

## API Endpoints

Each integration provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status/` | GET | Check connection status |
| `/authorize/` | POST | Get OAuth authorization URL |
| `/disconnect/` | DELETE | Revoke tokens and disconnect |
| `/contents/` | GET | List folder contents |
| `/callback` | GET | OAuth callback (internal) |

## Using Services Directly
```python
from nai_integrations.google.services import GoogleDriveService
from nai_integrations.box.services import BoxService
from nai_integrations.dropbox.services import DropboxService
from nai_integrations.onedrive.services import OneDriveService


def list_user_files(user):
    # Google Drive
    service = GoogleDriveService(user)
    if service.is_connected():
        files = service.list_all_files(page_size=100)
        for f in files.get('files', []):
            print(f"Google: {f['name']}")

    # Box
    service = BoxService(user)
    if service.is_connected():
        folder = service.list_folder(folder_id='0')
        for entry in folder.get('entries', []):
            print(f"Box: {entry['name']}")

    # Dropbox
    service = DropboxService(user)
    if service.is_connected():
        folder = service.list_folder(path='')
        for entry in folder.get('entries', []):
            print(f"Dropbox: {entry['name']}")

    # OneDrive
    service = OneDriveService(user)
    if service.is_connected():
        folder = service.list_folder(folder_id='root')
        for entry in folder.get('value', []):
            print(f"OneDrive: {entry['name']}")
```

## Celery Tasks (Optional)

Enable background token refresh:
```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'refresh-box-tokens': {
        'task': 'nai-integrations-refresh-box-tokens',
        'schedule': 3600,  # Every hour
    },
    'refresh-dropbox-tokens': {
        'task': 'nai-integrations-refresh-dropbox-tokens',
        'schedule': 3600,
    },
    'refresh-google-tokens': {
        'task': 'nai-integrations-refresh-google-tokens',
        'schedule': 3600,
    },
    'refresh-onedrive-tokens': {
        'task': 'nai-integrations-refresh-onedrive-tokens',
        'schedule': 3600,
    },
}
```

## Database Tables

Each provider creates a table:

- `nai_box_auth`
- `nai_dropbox_auth`
- `nai_google_auth`
- `nai_onedrive_auth`

## Requirements

- Python 3.10+
- Django 4.2+
- django-ninja 1.0+
- requests 2.28+
- cryptography 41.0+

## License

MIT License - see [LICENSE](LICENSE)
