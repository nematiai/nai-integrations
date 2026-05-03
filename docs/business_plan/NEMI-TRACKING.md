# NEMI — Nemati Integration Hub

## Overview

NEMI is a standalone Django microservice that provides unified integrations (social media posting, cloud storage, notifications) for all Nemati ecosystem apps (NAI, IndoxHub, Vesper, etc.) via REST API + MCP.

**Repo:** Evolves from `github.com/NematiAI/nai-integrations`
**Current state:** Standalone Django service (Phase 1.0 cleanup complete). 20 social adapters, 4 storage adapters, Apprise notifications, API key auth. 209 unit tests passing. DEBUG=False with WhiteNoise. src/ pip-package tree eliminated.
**Target state:** Standalone deployed service with social + storage + notifications + multi-app API keys

---

## Key Decisions Made

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | Standalone service, NOT pip package | Other apps (IndoxHub, Vesper) need to call it via HTTP, not import it |
| 2 | Separate from NAI backend | Avoids coupling; NEMI down ≠ NAI down for core features |
| 3 | Users bring their own API keys | No central OAuth management burden; each app configures its own platform credentials |
| 4 | Apprise for notifications | 90+ channels already built; no need to rebuild messaging |
| 5 | No n8n / no Postiz UI | Build our own adapter pattern in Django; no extra Node.js services |
| 6 | MCP layer for AI agents | Expose same adapters to Claude/Cursor via MCP protocol (Phase 5) |
| 7 | No more pip publish | NEMI is a deployed service, not a library. Apps call REST API |
| 8 | API keys per app | NAI gets a key, IndoxHub gets a key; rate-limited, scoped |

---

## Architecture

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│   NAI    │  │ IndoxHub │  │  Vesper  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     ▼              ▼              ▼
┌─────────────────────────────────────────┐
│          NEMI (Django + Celery)          │
│          REST API + MCP Server          │
├──────────┬──────────────┬───────────────┤
│ Social   │ Storage      │ Notify        │
│ adapters │ adapters     │ (Apprise)     │
├──────────┴──────────────┴───────────────┤
│ Celery + Redis │ PostgreSQL             │
└────────────────┴────────────────────────┘
```

---

## Platform Feasibility Matrix

### Social Media (Post FROM accounts)

| Platform | Free? | Approval? | Stability | Dev Time | Phase |
|----------|-------|-----------|-----------|----------|-------|
| Telegram | Yes | None | Very stable | 1 hr | 1 |
| Reddit | Yes | Instant OAuth | Stable | 2 hrs | 1 |
| Discord | Yes | Create bot | Very stable | 1 hr | 1 |
| Bluesky | Yes | App password | Stable | 2 hrs | 1 |
| Mastodon | Yes | OAuth instant | Very stable | 2 hrs | 1 |
| LinkedIn | Yes | App review needed | Moderate | 1-2 days | 2 |
| X/Twitter | ~$5/mo+ | Dev account review | Chaotic | 1 day | 2 |
| Facebook | Yes | Meta App Review (weeks) | Moderate | 2 days | 2 |
| Instagram | Yes | Same as Facebook | Moderate | 2 days | 2 |
| YouTube | Yes | Google consent review | Moderate | 1-2 days | 3 |
| TikTok | Yes | Content API approval | Moderate | 1-2 days | 3 |
| Threads | Yes | Meta API (newer) | New/unproven | 1 day | 3 |
| Pinterest | Yes | App approval | Stable | 1 day | 3 |

### Cloud Storage (already exists in nai-integrations)

| Platform | Free? | Approval? | Stability | Status |
|----------|-------|-----------|-----------|--------|
| Google Drive | Yes | OAuth consent | Stable | ✅ EXISTS |
| Dropbox | Yes | OAuth instant | Very stable | ✅ EXISTS |
| OneDrive | Yes | Azure AD app | Stable | ✅ EXISTS |
| Box | Yes | OAuth | Stable | ✅ EXISTS |
| S3/MinIO | Yes | API key | Very stable | Phase 1 |

### Notifications

| Solution | Channels | Status |
|----------|----------|--------|
| Apprise | 90+ (Email, Slack, Discord, Telegram, SMS, Push, etc.) | ✅ USE AS-IS |

---

> **Note on phase numbering**
>
> This document uses **engineering-delivery phase numbers** — what
> is being built, week by week. These do NOT map 1:1 to the
> **product-maturity phase numbers** in NEMI-AUTH-AND-ROADMAP.md,
> which describe who can use the platform (internal → public →
> paid → marketplace). Both numbering systems are intentional and
> serve different planning needs. When phases are referenced
> elsewhere, always specify which axis: "TRACKING Phase 2"
> (engineering) vs "AUTH-AND-ROADMAP Phase 2" (product).

## Phase Plan

### Phase 1.0: Test Infrastructure Cleanup (COMPLETED Apr 17, 2026)

| Step | Commit | What |
|---|---|---|
| Step 1 | `454fe32` | Eliminated `src/` pip-package tree, re-pointed 209 test imports to `apps/` |
| Step 2 | `257b53e` | Added pytest markers (unit/integration_mocked/integration_live), test deps |
| Step 3 | `464a0ba` | Cleaned apps/notify/tests, added smoke tests |
| Step 4 | `c9b3804` | Created .env.test.example + .env.test.live.example, conditional env loading |
| Step 4.5 | `3d01123` | Gitignored .claude/settings.local.json |
| Step 5 | `40c081b` | Integration test scaffolding (mocked + live directories, shared fixtures) |
| Step 5.5 | (pending) | WhiteNoise + DEBUG=False |
| Swagger | `70237c7` | Moved docs URL to /api/v1/docs |

**Bugs found during demo (to fix in Phase 1.1):**
- `GET /api/v1/health` returns empty response body
- `GET /api/v1/storage/google/status` returns empty response body

**Tech debt tracked:**
- REQ-LOCK: pin all dependencies + add lockfile (Phase 1.2)
- CLAUDE.md port drift: says 8010, actual is 8012 (Phase 1.2)
- NEMI-TRACKING.md phase numbers misaligned with AUTH-AND-ROADMAP.md (deferred)
- D12  Discord fixture/adapter mismatch (webhook_url vs BOT_TOKEN) → Phase 1.3 blocker
- D13  DB_PASSWORD defaults to "nemi" in settings.py — tighten to require explicit value when DEBUG=False
- D14  LOGGING config has no redaction filter — add SensitiveDataFilter for token/password/secret/api_key
- D15  Dockerfile collectstatic uses SECRET_KEY=build-placeholder — rename to BUILD_ONLY_NOT_A_SECRET for clarity

### Phase 1: Core Engine + Easy Platforms (2 weeks)

**Goal:** Working NEMI service with 5 social adapters + existing storage + Apprise

- [x] Convert nai-integrations from pip package to standalone Django service
- [x] Add API key auth system (apps register, get key)
- [x] Create base adapter pattern for social posting
- [x] Implement Telegram adapter
- [x] Implement Reddit adapter
- [x] Implement Discord adapter
- [x] Implement Bluesky adapter
- [x] Implement Mastodon adapter
- [x] Integrate Apprise for notifications
- [x] Add health check per adapter
- [x] Celery tasks for async posting
- [x] Docker Compose for deployment
- [x] Basic tests per adapter
- [x] PostLog model (track all posts)

### Phase 2: Hard Platforms + Scheduling (3-4 weeks)

- [ ] LinkedIn adapter (after approval)
- [ ] X/Twitter adapter (after dev account)
- [ ] Facebook adapter (after Meta review)
- [ ] Instagram adapter (after Meta review)
- [ ] Scheduled posts (Celery Beat)
- [ ] Content calendar API
- [ ] Bulk schedule endpoint
- [ ] S3/MinIO storage adapter

### Phase 3: Extended Platforms (2 weeks)

- [ ] YouTube adapter
- [ ] TikTok adapter
- [ ] Threads adapter
- [ ] Pinterest adapter

### Phase 4: Intelligence (2 weeks)

- [ ] AI caption generation per platform
- [ ] Per-platform content adaptation (char limits, hashtags)
- [ ] Best time to post suggestions
- [ ] Post templates

### Phase 5: MCP + Workflows (2 weeks)

- [ ] MCP server layer exposing all tools
- [ ] Workflow engine: "when X happens → do Y"
- [ ] Webhook triggers from external apps

### Phase 6: Analytics + Team (later)

- [ ] Engagement metrics per post
- [ ] Cross-platform dashboard API
- [ ] Multi-user workspace
- [ ] Approval workflows

---

## API Design (Phase 1)

```
# Auth
POST   /api/v1/auth/register       → Register app, get API key
POST   /api/v1/auth/rotate-key     → Rotate API key

# Social
POST   /api/v1/social/post         → Post to platforms
POST   /api/v1/social/schedule     → Schedule future post
GET    /api/v1/social/platforms     → List configured platforms
GET    /api/v1/social/logs          → Post history

# Storage (migrated from nai-integrations)
GET    /api/v1/storage/{provider}/status
POST   /api/v1/storage/{provider}/authorize
DELETE /api/v1/storage/{provider}/disconnect
GET    /api/v1/storage/{provider}/contents
POST   /api/v1/storage/{provider}/upload

# Notify
POST   /api/v1/notify/send         → Send via Apprise

# Health
GET    /api/v1/health              → Overall health
GET    /api/v1/health/{adapter}    → Per-adapter health
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 4.2+ / Django Ninja |
| Task Queue | Celery + Redis |
| Database | PostgreSQL |
| Notifications | Apprise (pip install apprise) |
| Token Encryption | Fernet (already in nai-integrations) |
| Auth | API key per app (X-API-Key header) |
| Deployment | Docker Compose on Hetzner |
| MCP | Phase 5 — FastAPI or Django endpoint |

---

## Migration from nai-integrations

| What | From (pip package) | To (NEMI service) |
|------|-------------------|-------------------|
| Storage adapters | Django apps (box, dropbox, google, onedrive) | Same code, moved into NEMI |
| Auth | BaseAuthAdapter (per-project) | API key middleware |
| Routes | django-ninja routers (imported by host app) | Self-contained API |
| Token storage | Per-app DB tables | Central NEMI PostgreSQL |
| Distribution | `pip install git+...` | Docker service on Hetzner |
| Users | nai-integrations assumes Django User model | NEMI has AppClient model (API key holder) |

---

## Open Questions

1. ~~Should existing nai-integrations pip package be deprecated or maintained alongside NEMI?~~ **RESOLVED (Apr 17, 2026):** pip package eliminated. `src/` tree deleted. NEMI is a standalone service only. Commit `454fe32`.
2. Domain: `nemi.nemati.io` or `integrations.nemati.io`?
3. Should NEMI share Redis/PostgreSQL with other Nemati apps or have dedicated instances?
