# Phase 1.2 Security Layer (#20 — superseded)

Replaces the standalone `django-ratelimit` integration (#20 commits `376e28e` + `ff71c02`, both reverted) with `nai-security[all]==1.10.0` — a Django security app maintained at `github.com/nematiai/nai-security` (MIT, version 1.10.0 on PyPI).

## What this gives us

`nai-security` ships:

- **Admin-managed rate limiting** — `RateLimitRule` model + `RateLimitLoggingMiddleware`. Rules live in the database (path pattern + method + rate), editable in the admin without redeploys. Built on `django-ratelimit==4.1.0`.
- **IP / country / email / user-agent blocking** — `BlockedIP`, `BlockedCountry`, `AllowedCountry`, `BlockedDomain`, `BlockedEmail`, `BlockedUserAgent`, plus a single `SecurityMiddleware` that enforces them all.
- **Whitelisting** — `WhitelistedIP` and `WhitelistedUser` (granular: `all` / `ip_block` / `geo_block` / `rate_limit`).
- **Login history + auto-blocking** — `LoginHistory`, `SecurityLog`, plus `services.auto_blocker` to ban IPs after N failed logins; `services.sync_services` for periodic list refresh.
- **django-axes integration** — `DynamicAxesHandler` reads `SecuritySettings.max_login_attempts` so admin can tune lockouts at runtime.
- **GeoIP support** — opt-in via `GEOIP_PATH`. Package degrades gracefully if mmdb missing (country features no-op, no crash).

## Why we replaced #20

`#20` (django-ratelimit decorators per endpoint) had three drawbacks vs. `nai-security`:

1. Limits hard-coded at decoration time → required redeploys to tune.
2. No IP / country / email / UA blocking surface.
3. No login-history or auto-block primitives.

Layered with NEMI's existing `apps/core/auth/middleware.py` per-AppClient quota, the new stack covers four concerns (per-AppClient, per-IP, per-endpoint, per-country/IP-blocklist) without us having to maintain any of them ourselves.

## Wire-up

`config/settings.py`:

```python
INSTALLED_APPS = [
    "unfold", "django.contrib.admin", ...,
    "axes", "import_export", "nai_security",   # ← new
    "apps.core", ..., "apps.notify",
]

MIDDLEWARE = [
    ..., "django.contrib.auth.middleware.AuthenticationMiddleware",
    "nai_security.middleware.SecurityMiddleware",          # ← new
    "nai_security.middleware.RateLimitLoggingMiddleware",  # ← new
    "django.contrib.messages.middleware.MessageMiddleware",
    ..., "apps.core.auth.middleware.ApiKeyAuthMiddleware",
]

AXES_HANDLER = "nai_security.handlers.axes_integration.DynamicAxesHandler"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
GEOIP_PATH = os.environ.get("GEOIP_PATH",
    str(BASE_DIR / "geoip" / "GeoLite2-Country.mmdb"))
NAI_SECURITY_EXEMPT_PATHS = [
    "/api/v1/health/", "/health/", "/ready/", "/favicon.ico",
]
```

Order rule: `nai_security.SecurityMiddleware` MUST follow `AuthenticationMiddleware` (it raises `ImproperlyConfigured` on misorder). `ApiKeyAuthMiddleware` is intentionally last — IP/country block runs before API-key validation, so blocked IPs get `403` before we even check their key.

## Migrations

Five migrations apply on first `manage.py migrate`:

```
nai_security/0001_initial
nai_security/0002_securitysettings_max_login_attempts
nai_security/0003_whitelisteduser
nai_security/0004_securitysettings_axes_attempt_expiry_enabled_and_more
nai_security/0005_alter_whitelisteduser_exemption_type
```

`0001` and `0003` declare `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`. NEMI keeps `django.contrib.auth` in `INSTALLED_APPS` for the admin panel, so `AUTH_USER_MODEL` resolves to `auth.User` and migrations apply cleanly.

Caveat: `LoginHistory` + `WhitelistedUser` only carry rows for **admin-panel users**, since NEMI's API surface uses `AppClient` auth (composite key), not Django sessions. Those tables stay near-empty in production unless the admin login flow gets used.

## GeoIP database

- Default path: `<repo>/geoip/GeoLite2-Country.mmdb` (the `geoip/` dir is gitignored).
- Download command: `python manage.py download_geoip` — pulls from `github.com/P3TERX/GeoLite.mmdb/releases/latest` (third-party mirror; ~6 MB).
- **MaxMind license** is not included. If your deployment requires direct MaxMind sourcing, override `GEOIP_PATH` and download via your own license-tracked process before container start.
- Missing mmdb is non-fatal: `utils.get_country_from_ip()` returns empty string and logs a warning; country-block features no-op.

## Rate limiting under nai-security

Limits are stored as `RateLimitRule` rows (`name`, `path_pattern`, `rate`, `method`, `is_active`). Examples in admin:

| name | path_pattern | rate | method |
|---|---|---|---|
| auth-register | `/api/v1/auth/register*` | `30/m` | `POST` |
| storage-callback | `/api/v1/storage/*/callback/` | `10/m` | `POST` |
| social-post | `/api/v1/social/post*` | `60/m` | `POST` |

The `RateLimitLoggingMiddleware` matches incoming paths against active rules and counts via Django cache. Adding a rule does not require a redeploy.

## Known caveats

1. **`axes.W002` warning** — Django check warns that `axes.middleware.AxesMiddleware` is not in `MIDDLEWARE`. Benign for NEMI: NEMI uses API-key auth (`ApiKeyAuthMiddleware`), not Django session login, so the AxesMiddleware lockout-enforcement signals do not apply. Adding it would silence the warning at the cost of one more middleware on every request.
2. **`RuntimeWarning` in `NaiSecurityConfig.ready()`** — package queries `SecuritySettings` at app startup. Visible during `pytest --collect-only`. Upstream issue; non-blocking.
3. **Editable install in current dev env** — locally, `pip install nai-security[all]==1.10.0` resolves to an editable install at `D:\NAI_Project\LIBRARIES\nai-security`. The lock files still pin the PyPI artifact, so CI/Docker builds pull the canonical 1.10.0 wheel. Verify with `pip show nai-security` if local behavior diverges.

## Verification

```text
pytest                                              → 275 passed (was 271)
pytest tests/integration/mocked/test_nai_security.py -v  → 4 passed
manage.py showmigrations nai_security               → 5 migrations recognized
```

Tests added: `tests/integration/mocked/test_nai_security.py` —
`test_security_middleware_loaded`, `test_health_endpoint_exempt_from_security`,
`test_blocked_ip_returns_403`, `test_rate_limit_rule_admin_creatable`.
The package's own 158-test suite covers internal correctness; we
intentionally do not duplicate it here.

## Files Touched

- `requirements/base.in` + `requirements/{base,dev,production}.txt` — pinned `nai-security[all]==1.10.0`.
- `config/settings.py` — INSTALLED_APPS, MIDDLEWARE, axes handler, auth backends, `GEOIP_PATH`, `NAI_SECURITY_EXEMPT_PATHS`.
- `.env.example`, `.env.test.example` — `GEOIP_PATH` placeholder.
- `.gitignore` — `geoip/`, `_audit_*/`.
- `tests/integration/mocked/test_nai_security.py` — 4 integration smoke tests.
- This doc replaces `PHASE-1.2-RATE-LIMITS.md` (deleted by the #20 revert).

## Commits

- `880e4ff` — `Revert "docs(security): rate limiting setup guide (#20)"`
- `ee99106` — `Revert "feat(security): rate limiting on public endpoints (#20)"`
- `70c457b` — `feat(security): integrate nai-security[all]==1.10.0`
- `7987e7d` — `feat(security): nai-security migrations + GeoIP setup`
- `211c705` — `test(security): nai-security integration tests`
- _(this commit)_ — `docs(security): replace #20 plan with nai-security integration`
