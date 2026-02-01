# NAI Integrations

A Django package providing unified OAuth 2.0 integrations for cloud storage providers: **Box**, **Dropbox**, **Google Drive**, and **OneDrive**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2+](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Unified API**: Consistent interface across all providers
- **Encrypted Token Storage**: Fernet encryption for access/refresh tokens at rest
- **Automatic Token Refresh**: Proactive refresh before expiration
- **Celery Tasks**: Background token refresh (optional)
- **Pluggable Authentication**: Adapter pattern for custom auth systems
- **Django Admin Integration**: Built-in admin interfaces (supports django-unfold)
- **Rate Limiting**: Built-in rate limiting for Google Drive endpoints
- **CSRF Protection**: State parameter validation on OAuth callbacks

## Architecture
```
nai_integrations/
├── base/                    # Abstract base classes
│   ├── models.py           # BaseCloudAuth - encrypted token storage
│   ├── services.py         # BaseCloudService - OAuth flow, API requests
│   ├── schemas.py          # Common Pydantic schemas
│   ├── admin.py            # BaseCloudAuthAdmin
│   └── exceptions.py       # Custom exceptions
├── contrib/
│   └── auth.py             # Pluggable authentication adapter
├── box/                    # Box integration
├── dropbox/                # Dropbox integration
├── google/                 # Google Drive integration
└── onedrive/               # OneDrive integration
```

## Installation
```bash
pip install nai-integrations
```

With optional dependencies:
```bash
# Celery support for background token refresh
pip install nai-integrations[celery]

# Django Unfold admin theme
pip install nai-integrations[unfold]

# Development dependencies
pip install nai-integrations[dev]
```

From GitHub (latest):
```bash
pip install git+https://github.com/NematiAI/nai-integrations.git
```

## Quick Start

### 1. Add to INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    # ...
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
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your-32-byte-fernet-key

# Box
BOX_CLIENT_ID=your_client_id
BOX_CLIENT_SECRET=your_client_secret
BOX_REDIRECT_URI=https://yourapp.com/api/v1/box/callback

# Dropbox
DROPBOX_CLIENT_ID=your_client_id
DROPBOX_CLIENT_SECRET=your_client_secret
DROPBOX_REDIRECT_URI=https://yourapp.com/api/v1/dropbox/callback

# Google Drive
GOOGLE_OAUTH2_CLIENT_ID=your_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REDIRECT_URI=https://yourapp.com/api/v1/google/callback

# OneDrive
ONEDRIVE_CLIENT_ID=your_client_id
ONEDRIVE_CLIENT_SECRET=your_client_secret
ONEDRIVE_REDIRECT_URI=https://yourapp.com/api/v1/onedrive/callback
```

### 4. Configure Authentication Adapter

Create an adapter that bridges your authentication system:
```python
# your_project/integrations_auth.py
from nai_integrations.contrib.auth import BaseAuthAdapter
from your_app.auth import YourNinjaAuth  # Your existing ninja auth


class IntegrationsAuthAdapter(BaseAuthAdapter):
    """Adapter to connect nai-integrations with your auth system."""

    def get_user_from_request(self, request):
        """
        Extract authenticated user from request.
        Called by require_auth() in views.
        """
        # Option 1: Session-based auth
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user

        # Option 2: Token-based auth (example with your token model)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                from your_app.models import AuthToken
                auth_token = AuthToken.objects.select_related('user').get(token=token)
                if not auth_token.is_expired():
                    return auth_token.user
            except AuthToken.DoesNotExist:
                pass

        return None

    def get_ninja_auth(self):
        """
        Return your django-ninja authentication class.
        Used when registering routes with auth.
        """
        return YourNinjaAuth()
```

Register in settings:
```python
# settings.py
NAI_INTEGRATIONS = {
    'AUTH_ADAPTER': 'your_project.integrations_auth.IntegrationsAuthAdapter',
}
```

### 5. Register Routes
```python
# urls.py or api.py
from ninja import NinjaAPI
from nai_integrations.box.views import router as box_router
from nai_integrations.dropbox.views import router as dropbox_router
from nai_integrations.google.views import router as google_router
from nai_integrations.google.callbacks import router as google_callbacks_router
from nai_integrations.onedrive.views import router as onedrive_router

api = NinjaAPI()

# Register integration routers
api.add_router("/integrations/box/", box_router)
api.add_router("/integrations/dropbox/", dropbox_router)
api.add_router("/integrations/google/", google_router)
api.add_router("/integrations/google/", google_callbacks_router)  # OAuth callbacks
api.add_router("/integrations/onedrive/", onedrive_router)
```

## API Endpoints

Each integration exposes the same endpoint pattern:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status/` | GET | Check connection status |
| `/authorize/` | POST | Get OAuth authorization URL |
| `/disconnect/` | DELETE | Revoke tokens and disconnect |
| `/contents/` | GET | List folder contents |
| `/callback` | GET | OAuth callback (internal) |

### Example: Connect Google Drive
```python
import requests

# 1. Get authorization URL
response = requests.post(
    'https://yourapp.com/api/integrations/google/authorize/',
    headers={'Authorization': 'Bearer your-token'}
)
auth_url = response.json()['authorization_url']
# Redirect user to auth_url

# 2. After OAuth callback, check status
response = requests.get(
    'https://yourapp.com/api/integrations/google/status/',
    headers={'Authorization': 'Bearer your-token'}
)
print(response.json())
# {'connected': True, 'email': 'user@gmail.com', ...}

# 3. List files
response = requests.get(
    'https://yourapp.com/api/integrations/google/drive/contents/',
    headers={'Authorization': 'Bearer your-token'}
)
```

## Using Services Directly

For backend operations without HTTP requests:
```python
from nai_integrations.google.services import GoogleDriveService
from nai_integrations.box.services import BoxService
from nai_integrations.dropbox.services import DropboxService
from nai_integrations.onedrive.services import OneDriveService


def sync_user_files(user):
    """Example: Sync files from all connected providers."""
    
    # Google Drive
    google_service = GoogleDriveService(user)
    if google_service.is_connected():
        files = google_service.list_all_files(page_size=100)
        for file in files.get('files', []):
            print(f"Google: {file['name']}")

    # Box
    box_service = BoxService(user)
    if box_service.is_connected():
        folder = box_service.list_folder(folder_id='0', limit=100)
        for entry in folder.get('entries', []):
            print(f"Box: {entry['name']}")

    # Dropbox
    dropbox_service = DropboxService(user)
    if dropbox_service.is_connected():
        folder = dropbox_service.list_folder(path='')
        for entry in folder.get('entries', []):
            print(f"Dropbox: {entry['name']}")

    # OneDrive
    onedrive_service = OneDriveService(user)
    if onedrive_service.is_connected():
        folder = onedrive_service.list_folder(folder_id='root', limit=100)
        for entry in folder.get('value', []):
            print(f"OneDrive: {entry['name']}")
```

### Service Methods

All services inherit from `BaseCloudService` and provide:
```python
# Connection
service.is_connected() -> bool
service.get_connection_status() -> dict
service.disconnect() -> bool

# OAuth
service.get_authorization_url(redirect_uri, state) -> str
service.exchange_code_for_tokens(code, redirect_uri) -> dict
service.refresh_access_token() -> bool
service.save_tokens(token_data, account_info) -> None

# API Operations
service.get_account_info() -> dict
service.list_folder(folder_id, **kwargs) -> dict

# Provider-specific methods vary (upload, download, create_folder, etc.)
```

## Token Encryption

Tokens are encrypted at rest using Fernet symmetric encryption:
```python
from nai_integrations.base.models import BaseCloudAuth

# Encryption is automatic via property setters
auth.decrypted_access_token = "raw_token"   # Encrypts and stores
token = auth.decrypted_access_token          # Decrypts and returns

# The underlying fields store encrypted data
auth._access_token   # Encrypted blob
auth._refresh_token  # Encrypted blob
```

Generate an encryption key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
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

Tasks automatically refresh tokens expiring within 6 hours.

## Custom Exceptions
```python
from nai_integrations.base.exceptions import (
    IntegrationError,      # Base exception
    AuthenticationError,   # Auth failures
    TokenRefreshError,     # Token refresh failures
    APIError,              # Provider API errors (includes status_code)
    ConfigurationError,    # Missing config
    RateLimitError,        # Rate limit exceeded
)

try:
    service.list_folder('invalid-id')
except APIError as e:
    print(f"API Error: {e.message}, Status: {e.status_code}")
except TokenRefreshError:
    print("Token expired, user needs to reconnect")
```

## Database Schema

Each provider creates a table inheriting from `BaseCloudAuth`:
```
nai_box_auth
nai_dropbox_auth
nai_google_auth
nai_onedrive_auth
```

Fields:
- `user` (FK) - OneToOne to User
- `_access_token` (encrypted)
- `_refresh_token` (encrypted)
- `token_type`
- `expires_at`
- `account_id`
- `email`
- `display_name`
- `scopes` (JSON)
- `connected_at`
- `updated_at`
- `is_active`

## Extending

### Add a New Provider
```python
# my_provider/models.py
from nai_integrations.base.models import BaseCloudAuth

class MyProviderAuth(BaseCloudAuth):
    class Meta:
        db_table = 'nai_myprovider_auth'


# my_provider/services.py
from nai_integrations.base.services import BaseCloudService
from .models import MyProviderAuth

class MyProviderService(BaseCloudService):
    PROVIDER_NAME = "MyProvider"
    API_BASE_URL = "https://api.myprovider.com/v1"
    AUTH_URL = "https://myprovider.com/oauth/authorize"
    TOKEN_URL = "https://myprovider.com/oauth/token"

    def _load_auth(self):
        try:
            self.auth = MyProviderAuth.objects.get(user=self.user, is_active=True)
        except MyProviderAuth.DoesNotExist:
            self.auth = None

    def _get_auth_model(self):
        return MyProviderAuth

    def _get_credentials(self):
        client_id = os.getenv('MYPROVIDER_CLIENT_ID')
        client_secret = os.getenv('MYPROVIDER_CLIENT_SECRET')
        if not client_id or not client_secret:
            raise ConfigurationError("MyProvider credentials not configured")
        return client_id, client_secret

    # Implement abstract methods...
    def get_authorization_url(self, redirect_uri, state=None):
        ...

    def exchange_code_for_tokens(self, code, redirect_uri):
        ...

    def refresh_access_token(self):
        ...

    def get_account_info(self):
        ...

    def list_folder(self, folder_id=None, **kwargs):
        ...
```

## Testing
```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src/nai_integrations --cov-report=html
```

## Requirements

- Python 3.10+
- Django 4.2+
- django-ninja 1.0+
- requests 2.28+
- cryptography 41.0+

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Support

- Issues: https://github.com/NematiAI/nai-integrations/issues
- Documentation: https://github.com/NematiAI/nai-integrations#readme