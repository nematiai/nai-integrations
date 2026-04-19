# NEMI — Production Docker Compose

Production stack for NEMI. 5 services on an isolated internal network plus a shared reverse-proxy network (`nai_public`).

## Required env vars (`.env.prod` in repo root)

Create `.env.prod` before deploying. Never commit it.

```
# Django
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=buildmyapp.us,...

# Database
POSTGRES_DB=nemi
POSTGRES_USER=nemi
POSTGRES_PASSWORD=...
DATABASE_URL=postgres://nemi:...@nemi-db:5432/nemi

# Redis / Celery
REDIS_URL=redis://nemi-redis:6379/0
CELERY_BROKER_URL=redis://nemi-redis:6379/0

# Token encryption (Fernet)
TOKEN_ENCRYPTION_KEY=...

# Storage OAuth
BOX_CLIENT_ID=...
BOX_CLIENT_SECRET=...
BOX_REDIRECT_URI=...
DROPBOX_CLIENT_ID=...
DROPBOX_CLIENT_SECRET=...
DROPBOX_REDIRECT_URI=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...
ONEDRIVE_CLIENT_ID=...
ONEDRIVE_CLIENT_SECRET=...
ONEDRIVE_REDIRECT_URI=...

# Image tag
GIT_SHA=...
```

## Network prerequisite

`nai_public` must exist before the first `up`:

```
docker network create nai_public
```

`nemi_internal` is declared `internal: true` so `nemi-db` and `nemi-redis` have no outbound internet. Only `nemi-api` joins `nai_public` for reverse-proxy reachability.

## Deploy

```
export GIT_SHA=$(git rev-parse --short HEAD)
docker compose -f docker/production/docker-compose.yml build
docker compose -f docker/production/docker-compose.yml up -d
docker compose -f docker/production/docker-compose.yml ps
```

## Services

| Service | Role | Memory | CPU |
|---|---|---|---|
| nemi-api | Django + Gunicorn (`:8000` internal) | 512M | 0.5 |
| nemi-worker | Celery worker | 512M | 0.5 |
| nemi-beat | Celery beat scheduler | 256M | 0.25 |
| nemi-db | PostgreSQL 16.4 | 1G | 1.0 |
| nemi-redis | Redis 7.2 | 256M | 0.25 |

Ports are not exposed on the host — connect via the reverse proxy on `nai_public`.

## Backup

Postgres backups (pg_dump → R2) are handled separately — see Task #12 rollback plan.
