# NEMI (Nemati Integration Hub) — Project Context

## Product
- Name: NEMI — Nemati Integration Hub
- Domain: buildmyapp.us
- Model: Open source core + API key gated access
- License: BSL 1.1 (Business Source License) — free to use and self-host, cannot sell as competing hosted service without commercial license
- Repo: github.com/nematiai/nai-integrations
- Internal users: NAI, IndoxHub, Vesper (Nemati ecosystem)
- External users: Anyone via API key from buildmyapp.us

## Project
- Stack: Python 3.11, Django 4.2+, Django Ninja, PostgreSQL, Redis, Celery
- Entry point: manage.py / config.wsgi
- Celery app: config.celery
- Package root: /app (PYTHONPATH)
- Local URL: http://localhost:8012
- Production URL: https://buildmyapp.us
- Health check: GET /api/v1/health/
- Admin panel: Django Unfold at /admin/
- API docs: Django Ninja auto-docs at /api/docs

## Environments
- local:  docker/local/  → port 8012
- prod:   docker/production/  → port 8000
- env files: .env (local), .env.dev, .env.prod

## Architecture
- config/             → settings.py, urls.py, celery.py, wsgi.py
- apps/core/          → AppClient model, API key auth, exceptions, health
- apps/core/auth/     → models.py (AppClient), middleware.py (API key), views.py
- apps/core/base/     → exceptions.py, health.py
- apps/social/        → social media posting adapters
- apps/social/base/   → BaseSocialAdapter, SocialAccount, PostLog models
- apps/social/{platform}/ → 20 platforms: bluesky/, discord/, dribbble/, facebook/, google_business/, instagram/, linkedin/, linkedin_page/, mastodon/, mewe/, pinterest/, reddit/, skool/, slack/, telegram/, threads/, tiktok/, whop/, x/, youtube/
- apps/storage/       → cloud storage adapters (migrated from nai-integrations)
- apps/storage/base/  → BaseCloudAuth, BaseCloudService, schemas, admin
- apps/storage/{provider}/ → box/, dropbox/, google/, onedrive/
- apps/notify/        → Apprise notification wrapper
- apps/dashboard/     → web UI (Phase 2, not Phase 1)
- docker/             → local/, development/, production/ compose files
- tests/              → test files per app
- docs/               → NEMI-TRACKING.md, NEMI-PHASE1-SPEC.md
- static/             → static assets (Unfold admin)

## Code Standards
- Zero ruff warnings — always run before commit
- Max 50 lines per function, 200 lines per file — refactor if exceeded. exceptions you must ask like tests or md file or json.
- try/except on every async def or view that touches DB or external API
- Never expose API keys or tokens in logs or responses
- All env vars via django.conf.settings — no os.getenv() in business logic
- Type hints required on all function signatures
- Celery tasks: always use bind=True, max_retries, and explicit queue
- Token encryption: Fernet via TOKEN_ENCRYPTION_KEY setting
- All social adapters must extend BaseSocialAdapter
- All storage adapters must extend BaseCloudService
- Each adapter in its own folder with adapter.py + tests.py
-   Write a plan to docs/plans/2026-0x-0x-[task-name].md covering:
  - What we are building
  - Phases with clear deliverables
  - Files to create or modify per phase

## Auth
- External apps (NAI, IndoxHub, Vesper): API key via X-API-Key header
- Admin dashboard: Django session auth (User model)
- Both auth paths coexist — middleware routes by URL prefix
- /api/* → API key auth
- /admin/* → Django session auth

## Build (local)
```bash
cd docker/local && docker-compose up -d --build
```

## Test
```bash
pytest tests/ -v
```

## Lint
```bash
ruff check . && ruff format --check .
```

## Docker Services
```yaml
nemi-api:     # Django + Gunicorn, port 8012
nemi-worker:  # Celery worker
nemi-beat:    # Celery beat (scheduled tasks)
nemi-db:      # PostgreSQL 16
nemi-redis:   # Redis 7
```

---

## GitHub Issue Tracking (NON-NEGOTIABLE)

Every time ANY skill or manual review finds an error, warning, or issue:
1. **ALWAYS open a GitHub issue FIRST** — even if you plan to fix it in the same session
2. Write to docs/issues.md with the GitHub issue number
3. Fix the issue
4. Verify with /redo
5. **STOP — ask user to approve the fix**
6. Only close the GitHub issue after user says "approved" or "close it"

**NEVER skip opening a GitHub issue because "it was fixed in the same session."**
**NEVER close a GitHub issue without user approval.**

Traceability is mandatory. Every finding must be tracked on GitHub.

---

## API Endpoints (Phase 1)

### Auth
```
POST   /api/v1/auth/register       → Register app, get API key
POST   /api/v1/auth/rotate-key     → Rotate API key
```

### Social
```
POST   /api/v1/social/accounts              → Register platform credentials
POST   /api/v1/social/post                  → Post to platforms
GET    /api/v1/social/platforms              → List configured platforms
GET    /api/v1/social/logs                   → Post history
DELETE /api/v1/social/accounts/{platform}    → Remove platform
```

### Storage (migrated from nai-integrations)
```
GET    /api/v1/storage/{provider}/status     → Connection status
POST   /api/v1/storage/{provider}/authorize  → Get OAuth URL
DELETE /api/v1/storage/{provider}/disconnect → Revoke and disconnect
GET    /api/v1/storage/{provider}/contents   → List folder contents
```

### Notify
```
POST   /api/v1/notify/send                  → Send via Apprise
```

### Health
```
GET    /api/v1/health                        → Overall + per-adapter status
```

---

## Dependencies
```
django>=4.2
django-ninja>=1.0
django-unfold>=0.40
celery[redis]>=5.3
redis>=5.0
httpx>=0.27
apprise>=1.7
cryptography>=41.0
gunicorn>=22.0
psycopg2-binary>=2.9
python-dotenv>=1.0
requests>=2.28
ruff
pytest
pytest-django
```

---

## Migration from nai-integrations

This project evolves from github.com/NematiAI/nai-integrations (pip package).
Storage adapters (box, dropbox, google, onedrive) are moved as-is into apps/storage/.
Import paths change from `nai_integrations.*` to `apps.storage.*` and `apps.core.*`.
Storage code keeps `self.user` pattern — AppClient maps to storage connections at higher level.
contrib/auth.py is replaced by apps/core/auth/middleware.py (API key based).
No more pip publish. NEMI is a deployed service.

---

## Unfold Admin
- Install: django-unfold in requirements.txt
- Config: Add "unfold" to INSTALLED_APPS BEFORE "django.contrib.admin"
- All admin classes inherit from unfold.admin.ModelAdmin (with fallback)
- Pattern already exists in nai-integrations base/admin.py — reuse it