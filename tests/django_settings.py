SECRET_KEY = "test-only"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "nai_integrations.box",
    "nai_integrations.dropbox",
    "nai_integrations.google",
    "nai_integrations.onedrive",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
