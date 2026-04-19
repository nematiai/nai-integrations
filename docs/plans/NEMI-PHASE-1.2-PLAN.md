# NEMI — Phase 1.2, 1.3, Phase 2 Execution Plan

**Project root:** `D:\NAI_Project\BACKENDS\nai-integrations`
**Active branch:** `production`
**Latest commit at time of plan:** `b45283c` (CLAUDE.md port fix)
**Session date:** 2026-04-17
**Phase 1.1 status:** COMPLETE (262 tests passing)

---

## Human Summary

### Where we are
Phase 1.1 closed. Zero regressions, 30 new integration tests across auth, social posting, 4 storage providers, and notify API. One real bug fixed along the way (`AnonymousUser` FK on notify channel create). 9 pieces of tech debt catalogued.

### What this plan covers
- **Phase 1.2** — production hardening: docs alignment, docker-compose prod, REQ-LOCK, healthchecks, rollback plan, known tech debt D1-D9
- **Phase 1.3** — live integration tests across all 24 services (20 social + 4 storage) — high level only; detailed plan written after 1.2 closes
- **Phase 2** — high-level scope: MCP exposure, notify redesign, AI proxy for Postiz, notify API compaction. Non-executable — for reference only.

### Execution model
Every Phase 1.2 task has:
1. **Pre-flight** — commands the agent runs to verify state before editing
2. **Steps** — explicit edits with FIND/REPLACE or file creation
3. **Verification** — commands whose output the agent reports back
4. **Hard rules** — what the agent must NOT do
5. **Acceptance** — pass/fail criteria before commit
6. **Rollback** — one-liner to back out the change

### Tech debt accrued in Phase 1.1 (D1-D9)

| ID | Debt | Target |
|---|---|---|
| D1 | Disconnect endpoint: Box/Dropbox/OneDrive return 400, Google returns 404 | Task #13 |
| D2 | `/status/` auto-refresh: Google yes, Box/Dropbox/OneDrive no | Task #14 |
| D3 | OneDrive callback silently swallows `get_account_info` failures | Task #15 |
| D4 | Notify API: 18 endpoints, review for compaction | Phase 2 |
| D5 | No Django LOGGING config — tracebacks disappear under gunicorn | Task #17 |
| D6 | Notify models use Django User FK (violates composite key pattern) | Phase 2 notify redesign |
| D7 | GitHub remote case mismatch (`NematiAI` → `nematiai`) | Task #16 |
| D8 | `/contents/` endpoints untested (deferred from Phase 1.1 Task #5) | Phase 1.3 |
| D9 | Folder typo `docs/bussiness_plan/` → `docs/business_plan/` | Task #18 |

### Order of execution
Small/safe first (Tasks 8-9, 13-18), then prod-critical (Tasks 10-12), then optional hardening (19-22). Live tests (Phase 1.3) last.

### Full suite baseline
**262 tests passing** after Phase 1.1. Every Phase 1.2 task must keep this number intact or increase it. Any drop = stop and investigate.

---

## Execution Order

| # | Task | Size | Risk | Blocks |
|---|---|---|---|---|
| 8 | Align NEMI-TRACKING phase numbers with AUTH-AND-ROADMAP | S | Low | Doc coherence |
| 9 | Docker healthcheck directives in local compose | XS | Low | Task #10 |
| 10 | Production `docker-compose.prod.yml` | M | Medium | Any real deploy |
| 11 | REQ-LOCK — pin deps + lockfile | S | Low | Reproducible builds |
| 12 | Rollback plan doc for first prod deploy | S | Low | Prod deploy safety |
| 13 | Fix disconnect 400/404 inconsistency (D1) | S | Low | API contract |
| 14 | Standardize `/status/` auto-refresh (D2) | M | Medium | API contract |
| 15 | Fix OneDrive callback exception swallowing (D3) | XS | Low | Bug fix |
| 16 | Fix GitHub remote case (D7) | XS | None | Push perf |
| 17 | Add Django LOGGING config (D5) | S | Low | Prod debugging |
| 18 | Fix folder typo `bussiness_plan` → `business_plan` (D9) | S | Low | Doc quality |
| 19 | *(Optional)* Sentry integration | S | Low | Decide on arrival |
| 20 | *(Optional)* Rate limiting on public endpoints | M | Low | Decide on arrival |
| 21 | *(Optional)* Secrets handling audit | S | Low | Decide on arrival |
| 22 | *(Optional)* CI pipeline (lint + tests + docker build) | M | Low | Decide on arrival |

**Sizes:** XS <30min • S 30min–2h • M half day • L full day

---

# Phase 1.2 — Tasks

---

## Task #8 — Align NEMI-TRACKING phase numbers with AUTH-AND-ROADMAP

**Size:** S
**Rationale:** Three docs (TRACKING, AUTH-AND-ROADMAP, MASTER-DECISIONS if it exists) have drifted on phase numbering. AUTH-AND-ROADMAP is the source of truth (per stored memory). Align the others.

**Pre-flight — agent reports, does NOT edit yet:**

```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== All NEMI docs ===" && \
find . -iname "*nemi*" -type f 2>/dev/null | grep -v __pycache__ && \
echo "" && \
echo "=== All Phase headings in TRACKING ===" && \
grep -nE "^## |^### |Phase [0-9]" docs/bussiness_plan/NEMI-TRACKING.md | head -40 && \
echo "" && \
echo "=== All Phase headings in AUTH-AND-ROADMAP ===" && \
grep -nE "^## |^### |Phase [0-9]" docs/bussiness_plan/NEMI-AUTH-AND-ROADMAP.md | head -40 && \
echo "" && \
echo "=== Phase sections in MASTER-DECISIONS if exists ===" && \
grep -nE "^## |^### |Phase [0-9]" docs/bussiness_plan/NEMI-MASTER-DECISIONS.md 2>/dev/null | head -40
```

**STOP. Human reviews the diff of phase numbering before any edits.**

**Steps (after human approval of mapping):**
1. Human tells agent the exact phase-number mapping
2. Agent runs targeted FIND/REPLACE on each occurrence in TRACKING.md
3. Agent runs same for MASTER-DECISIONS.md if present
4. AUTH-AND-ROADMAP.md is NOT edited

**Verification:**
```bash
grep -n "Phase " docs/bussiness_plan/NEMI-TRACKING.md | head -20
grep -n "Phase " docs/bussiness_plan/NEMI-AUTH-AND-ROADMAP.md | head -20
diff <(grep "^### Phase" docs/bussiness_plan/NEMI-TRACKING.md) \
     <(grep "^### Phase" docs/bussiness_plan/NEMI-AUTH-AND-ROADMAP.md)
```

**Hard rules:**
- Do NOT rewrite sections. Only renumber.
- Do NOT edit AUTH-AND-ROADMAP.md.
- If any FIND string doesn't match exactly, STOP and report.
- If phase numbers in TRACKING.md reference work that doesn't exist in AUTH-AND-ROADMAP (or vice versa), STOP — the plan has a semantic mismatch, not just numeric.

**Acceptance:**
- Every `Phase X` heading in TRACKING.md matches a `Phase X` heading in AUTH-AND-ROADMAP.md.
- `diff` command shows no differences in phase-heading lines.

**Rollback:** `git checkout docs/bussiness_plan/NEMI-TRACKING.md`

---

## Task #9 — Docker healthcheck directives in local compose

**Size:** XS
**Rationale:** Local compose doesn't have healthcheck directives on the app container. Without them, `docker compose up` returns "started" even when gunicorn fails to boot. Healthchecks give `docker compose ps` accurate status.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== Current compose ===" && \
cat docker/local/docker-compose.yml && \
echo "" && \
echo "=== Existing healthcheck directives ===" && \
grep -n "healthcheck" docker/local/docker-compose.yml
```

**Steps:**

Add healthcheck to the `nemi-api` service. Agent inserts inside the `nemi-api:` block, before `ports:`:

```yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

Dockerfile must have `curl` installed. If not, agent adds `curl` to the apt install list.

**Verification:**
```bash
docker compose -f docker/local/docker-compose.yml down && \
docker compose -f docker/local/docker-compose.yml build nemi-api && \
docker compose -f docker/local/docker-compose.yml up -d && \
sleep 20 && \
docker compose -f docker/local/docker-compose.yml ps
# Expected: nemi-api-dev status column shows "Up (healthy)"
```

**Hard rules:**
- ONLY modify `docker/local/docker-compose.yml` and `Dockerfile` (if curl missing).
- Do NOT change port mappings, environment, or other services.
- If healthcheck fails (container goes "unhealthy"), STOP and report — we investigate before committing.

**Acceptance:**
- `docker compose ps` shows `nemi-api` as `Up (healthy)` within 45 seconds of `up -d`.
- Full test suite still passes (Docker changes don't affect host pytest, but run it anyway to confirm).

**Rollback:** `git checkout docker/local/docker-compose.yml Dockerfile`

---

## Task #10 — Production `docker-compose.prod.yml`

**Size:** M
**Rationale:** Currently no prod compose file exists (`docker/production/` folder doesn't exist). Every Phase 1.2+ deliverable depends on having a reproducible prod environment.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== Current docker/ tree ===" && \
ls -la docker/ && \
echo "" && \
echo "=== Local compose (basis for prod) ===" && \
cat docker/local/docker-compose.yml && \
echo "" && \
echo "=== Env file reference check ===" && \
grep -rn "env_file\|environment:" docker/local/ && \
echo "" && \
echo "=== Dockerfile (confirm prod-readiness) ===" && \
cat Dockerfile
```

**Steps:**
1. Create `docker/production/` directory
2. Create `docker/production/docker-compose.yml`

Prod compose differs from local in these ways:

| Setting | Local | Prod |
|---|---|---|
| Database | Internal postgres container | External managed DB (env DATABASE_URL) |
| Redis | Internal container | External (env REDIS_URL) |
| Port exposure | `8012:8000` for dev | Behind reverse proxy (e.g. nginx), container port only |
| `restart:` | `unless-stopped` | `always` |
| `env_file` | `../../.env` | `../../.env.prod` |
| `DEBUG` | from env (True in dev) | Forced False |
| Image tag | `local-nemi-api:latest` | Versioned tag (e.g. `nemi-api:v1.0.0`) |
| Resource limits | None | mem_limit + cpu_limit |
| Logs | Default | Structured JSON (to stdout) |

**Decisions needed from human before agent proceeds:**

1. Is DB + Redis external in prod, or colocated?
2. Is there a reverse proxy (nginx) in this compose or external?
3. Log driver — json-file with rotation, or ship to aggregator?
4. Image tagging strategy — git SHA, semver, or latest?

**Verification:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
docker compose -f docker/production/docker-compose.yml config && \
echo "--- config valid ---" && \
# Can't fully boot prod without .env.prod, but config validation proves schema is right
docker compose -f docker/production/docker-compose.yml config --services
```

**Hard rules:**
- Do NOT copy `.env` secrets into the compose file.
- DEBUG must be hardcoded `False` — not env-driven.
- If external DB/Redis URLs are TBD, use `${DATABASE_URL}` / `${REDIS_URL}` placeholders with no default.
- Compose must `config`-validate cleanly (no warnings).

**Acceptance:**
- `docker compose -f docker/production/docker-compose.yml config` exits 0 with no warnings.
- Documented list of env vars the prod compose requires (add to CLAUDE.md or separate `docker/production/README.md`).

**Rollback:** `rm -rf docker/production/`

---

## Task #11 — REQ-LOCK: pin deps + lockfile

**Size:** S
**Rationale:** Current `requirements/base.txt` likely uses ranges (`>=`, `~=`) or bare package names. Any rebuild may pull newer versions than were tested. Need exact pins for reproducibility.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== Current requirements/ ===" && \
ls requirements/ && \
echo "" && \
for f in requirements/*.txt; do
  echo "--- $f ---"
  cat "$f"
done && \
echo "" && \
echo "=== Installed versions in running container ===" && \
docker compose -f docker/local/docker-compose.yml exec nemi-api pip freeze 2>&1 | head -40
```

**Steps — choose tool based on what's already there:**

**Option A** — pip-tools (simple, widely used):
1. Create `requirements/base.in` with loose constraints (copy current `base.txt`)
2. Run `pip-compile requirements/base.in -o requirements/base.txt`
3. Commit both `.in` and locked `.txt`

**Option B** — uv (fast, modern):
1. Create `pyproject.toml` with deps (if not already present)
2. Run `uv pip compile pyproject.toml -o requirements.lock`
3. Commit `requirements.lock`

**Agent picks based on pre-flight findings. Human approves choice before execution.**

**Verification:**
```bash
# Every line in the generated lock file must include `==`
grep -vE "^#|^\s*$" requirements/base.txt | grep -vE "==" | head -5
# Expected: no output (every non-comment, non-blank line has ==)

# Rebuild Docker with new lockfile, confirm suite still passes
docker compose -f docker/local/docker-compose.yml build --no-cache nemi-api && \
docker compose -f docker/local/docker-compose.yml up -d && \
sleep 15 && \
pytest 2>&1 | tail -5
# Expected: 262 passed
```

**Hard rules:**
- Do NOT remove any currently-installed package. Pin-only, no deletions.
- Do NOT upgrade major versions silently — only lock what's currently installed.
- If pip-compile finds version conflicts, STOP and report — don't force resolve.

**Acceptance:**
- Every line in locked requirements has `==` pin (no ranges).
- Fresh docker build succeeds.
- Full suite: 262 passed.

**Rollback:** `git checkout requirements/`

---

## Task #12 — Rollback plan doc for first prod deploy

**Size:** S
**Rationale:** No prod deploy has ever happened. First deploy needs explicit rollback instructions so if it breaks, the on-call (likely you) knows exactly what to do.

**Pre-flight:** None. This is pure documentation.

**Steps:**

Create `docs/bussiness_plan/ROLLBACK-PROD.md` containing:

1. **Pre-deploy checklist** (all must be green before touching prod)
   - Current commit on `production` branch is tagged (e.g. `v1.0.0`)
   - All tests pass locally
   - Docker image built and pushed to registry with versioned tag
   - Database backup taken within last 1 hour
   - Staging environment matches prod config, tested by agent

2. **Deploy procedure** (happy path)
   - Pull new image on prod host
   - Stop old containers
   - Run migrations (`python manage.py migrate --noinput`)
   - Start new containers
   - Verify `/api/v1/health/` returns 200
   - Smoke-test: send a test notification via POST /send/
   - Tail logs for 5 minutes

3. **Rollback triggers** (any one = abort)
   - `/api/v1/health/` returns non-200 for > 60 seconds
   - Integration test suite run against staging fails
   - Error rate spikes > 5% in first 10 minutes
   - Any 500 errors in logs

4. **Rollback procedure**
   - Stop new containers
   - Pull previous image tag
   - Re-run migrations in reverse if schema changed (`python manage.py migrate <app> <previous_migration>`)
   - Start old containers
   - Verify health
   - Post-mortem template

5. **Contacts + escalation path**
   - Who to tell
   - Where to look for logs
   - Link to dashboards / monitoring (TBD)

**Verification:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
wc -l docs/bussiness_plan/ROLLBACK-PROD.md
# Expected: 80-150 lines, no more. If longer, it's a novel, not a runbook.
```

**Hard rules:**
- Keep under 150 lines. Runbooks that no one reads don't help.
- Include exact commands, not prose descriptions.
- Mark unknown items explicitly as `TBD` — don't guess.

**Acceptance:**
- Document is reviewed by human.
- Every `TBD` is tracked as a follow-up item.

**Rollback:** `rm docs/bussiness_plan/ROLLBACK-PROD.md`

---

## Task #13 — Fix disconnect 400/404 inconsistency (D1)

**Size:** S
**Rationale:** Google returns 404 "not connected"; Box/Dropbox/OneDrive return 400. Integration tests lock this in as current behavior. Standardize.

**Decision:** 404 is semantically correct. Fix Box/Dropbox/OneDrive to return 404.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
grep -n "is not connected" apps/storage/box/views.py \
                          apps/storage/dropbox/views.py \
                          apps/storage/onedrive/views.py
```

Expected 6 lines total (2 per file — one in `disconnect`, one in `contents`).

**Steps:**

For each of `box/views.py`, `dropbox/views.py`, `onedrive/views.py`:

FIND: `raise HttpError(400, "X is not connected")` (where X is Box/Dropbox/OneDrive)
REPLACE: `raise HttpError(404, "X is not connected")`

Apply in both places where the pattern appears in each file.

**Update corresponding tests:**

For each of `test_box_storage.py`, `test_dropbox_storage.py`, `test_onedrive_storage.py`:

FIND `assert resp.status_code == 400` in TEST 8 (disconnect-not-connected test)
REPLACE with `assert resp.status_code == 404`

Remove the "tracked as tech debt D1" comment from those tests.

**Verification:**
```bash
pytest tests/integration/mocked/test_box_storage.py \
       tests/integration/mocked/test_dropbox_storage.py \
       tests/integration/mocked/test_onedrive_storage.py \
       -v --tb=short
pytest 2>&1 | tail -5
# Expected: 262 passed (still)
```

**Hard rules:**
- Do NOT modify `google/views.py` — already 404.
- Do NOT change disconnect response body schema, only the status code.
- If Box/Dropbox/OneDrive have additional `HttpError(400, ...)` for different reasons, DO NOT change those — only the "is not connected" ones.

**Acceptance:**
- All 4 providers return 404 for disconnect-when-not-connected.
- All 3 updated test files pass.
- Full suite: 262 passed.

**Rollback:** `git revert <commit>`

---

## Task #14 — Standardize `/status/` auto-refresh (D2)

**Size:** M
**Rationale:** Google's `/status/` auto-refreshes expiring tokens. Box/Dropbox/OneDrive don't — they return `connected: true` even with expired tokens. Inconsistent UX.

**Decision needed from human before agent proceeds:**

Three options:
- **A** — Add auto-refresh to Box/Dropbox/OneDrive (match Google). More code.
- **B** — Remove auto-refresh from Google (match the others). Less code, but users hit refresh errors on first API call after token expires.
- **C** — Move auto-refresh to base `get_connection_status()` so all 4 get it for free.

**Recommended:** C. Base class already has `get_connection_status()` used by 3 of 4 providers. Google's view re-implements the logic inline. Refactoring to base unifies the pattern.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== Google inline refresh logic ===" && \
sed -n '25,50p' apps/storage/google/views.py && \
echo "" && \
echo "=== Base get_connection_status ===" && \
grep -B2 -A20 "def get_connection_status" apps/storage/base/services.py && \
echo "" && \
echo "=== Base class refresh method ===" && \
grep -B2 -A15 "def refresh_access_token\|def needs_refresh" apps/storage/base/services.py
```

**Steps (assuming Option C):**

1. In `apps/storage/base/services.py`, modify `get_connection_status()`:
   - Check `self.auth.needs_refresh()`
   - If true, call `self.refresh_access_token()`
   - If refresh fails, return `{"connected": False, "message": "Token refresh failed", ...}`
   - If refresh succeeds, reload `self.auth` and return normal status

2. In `apps/storage/google/views.py`, simplify `check_google_connection()` to delegate:
   - Replace inline refresh logic with `return GoogleStatusOut(**service.get_connection_status())`
   - Keep the extra Google-specific fields (scopes, expires_at) by extending `get_connection_status()` return shape

3. Update tests: each provider's status-token-expired test should now show `connected: true` after refresh (currently only Google does). Check mocks register `TOKEN_URL` for the refresh call.

**Verification:**
```bash
pytest tests/integration/mocked/test_*_storage.py -v --tb=short
pytest 2>&1 | tail -5
# Expected: 262 passed
```

**Hard rules:**
- Do NOT change the `StatusOut` schema shape for any provider — only the underlying behavior.
- If any provider's `refresh_access_token()` doesn't exist, STOP and report.
- If tests fail because refresh is called when not expected, STOP and investigate — don't loosen assertions.

**Acceptance:**
- All 4 provider `/status/` endpoints auto-refresh expiring tokens.
- All 4 provider status tests pass.
- Full suite: 262 passed.

**Rollback:** `git revert <commit>`

---

## Task #15 — Fix OneDrive callback exception swallowing (D3)

**Size:** XS
**Rationale:** OneDrive callback does this:
```python
try:
    account_info = service.get_account_info()
    service.save_tokens(token_data, account_info)
except Exception:
    account_info = {}
```

If `get_account_info()` fails, user sees "success" with empty email. That's a lie.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
sed -n '49,85p' apps/storage/onedrive/views.py
```

**Steps:**

In `apps/storage/onedrive/views.py`, the `onedrive_callback` function:

FIND:
```python
        try:
            account_info = service.get_account_info()
            service.save_tokens(token_data, account_info)
        except Exception:
            account_info = {}
        email = account_info.get("userPrincipalName", "") or account_info.get(
            "mail", ""
        )
        return {"success": True, "email": email}
```

REPLACE:
```python
        account_info = service.get_account_info()  # let exceptions propagate to outer try
        service.save_tokens(token_data, account_info)
        email = account_info.get("userPrincipalName", "") or account_info.get(
            "mail", ""
        )
        return {"success": True, "email": email}
```

This lets the outer `except Exception as e:` in the callback (which logs and raises HttpError 500) handle `get_account_info` failures properly.

**Add a test** in `test_onedrive_storage.py`:

```python
TEST 9 — POST /callback/ when get_account_info fails returns 500
    @onedrive_settings
    def inner():
        mock_requests.add(
            "POST", "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            json={"access_token": "x", "refresh_token": "y", "expires_in": 3600},
            status=200,
        )
        mock_requests.add(
            "GET", "https://graph.microsoft.com/v1.0/me",
            json={"error": "forbidden"},
            status=403,
        )
        resp = api_client.post("/api/v1/storage/onedrive/callback/?code=x")
        assert resp.status_code == 500
    inner()
```

**Verification:**
```bash
pytest tests/integration/mocked/test_onedrive_storage.py -v --tb=short
pytest 2>&1 | tail -5
# Expected: 263 passed (262 + 1 new test)
```

**Hard rules:**
- Do NOT remove the outer try/except in the callback — it handles real auth failures correctly.
- Do NOT change other storage callbacks.

**Acceptance:**
- New test passes.
- Full suite: 263 passed.

**Rollback:** `git revert <commit>`

---

## Task #16 — Fix GitHub remote case (D7)

**Size:** XS
**Rationale:** Remote points to `NematiAI/nai-integrations`. GitHub canonicalized to `nematiai/nai-integrations` (lowercase). Every push gets a redirect warning.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
git remote -v
```

Expected:
```
origin  https://github.com/NematiAI/nai-integrations.git (fetch)
origin  https://github.com/NematiAI/nai-integrations.git (push)
```

**Steps:**
```bash
git remote set-url origin https://github.com/nematiai/nai-integrations.git
git remote -v   # verify
git push origin production   # should push without redirect warning
```

**Verification:**
Push output must NOT contain the line:
```
remote: This repository moved. Please use the new location:
```

**Hard rules:**
- Do NOT change the remote to a different repo. Only canonicalize the case.
- Verify `git remote -v` shows the new URL before pushing.

**Acceptance:**
- Remote URL is lowercase.
- Next push has no redirect warning.

**Rollback:**
```bash
git remote set-url origin https://github.com/NematiAI/nai-integrations.git
```

---

## Task #17 — Add Django LOGGING config (D5)

**Size:** S
**Rationale:** Phase 1.1 had several 500 errors whose tracebacks were invisible because Django's default logging disappears under gunicorn. A proper LOGGING config ensures tracebacks land in container stdout and can be tailed with `docker compose logs`.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
grep -n "LOGGING" config/settings.py config/test_settings.py
```

**Steps:**

Add to `config/settings.py` (after DATABASES block, before INSTALLED_APPS):

```python
import sys

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",  # logs unhandled exceptions with traceback
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

**Verification:**
```bash
# Restart container, trigger a known 500 (create channel was fixed, but a bad payload still 400s)
docker compose -f docker/local/docker-compose.yml restart nemi-api && \
sleep 5 && \
curl -s -X POST http://localhost:8012/api/v1/notify/channels/ \
  -H "X-API-Key: <key>" -H "X-User-Id: test" \
  -H "Content-Type: application/json" \
  -d '{"invalid":"body"}' > /dev/null && \
docker compose -f docker/local/docker-compose.yml logs nemi-api --tail=20 2>&1 | grep -i "error\|warning"
# Expected: see structured log lines, not bare access log
```

Also run full test suite — LOGGING config affects every test run:
```bash
pytest 2>&1 | tail -5
# Expected: 262 or 263 passed (depending on whether Task #15 landed)
```

**Hard rules:**
- Do NOT add file-based log handlers. Containers should log to stdout only.
- Do NOT add third-party handlers (Sentry etc.) in this task — separate Task #19.
- Do NOT change test_settings.py — tests use pytest's built-in log capture.

**Acceptance:**
- Django errors surface in `docker compose logs` with formatted timestamp + level.
- `django.request` logger emits tracebacks for unhandled exceptions.
- Full suite still passes.

**Rollback:** `git checkout config/settings.py`

---

## Task #18 — Fix folder typo `bussiness_plan` → `business_plan` (D9)

**Size:** S
**Rationale:** The folder is misspelled. Every doc reference and import path that mentions it inherits the typo. Fix once now before more things reference it.

**Pre-flight:**
```bash
cd /d/NAI_Project/BACKENDS/nai-integrations && \
echo "=== Files in misspelled folder ===" && \
ls docs/bussiness_plan/ && \
echo "" && \
echo "=== All references to the typo anywhere in repo ===" && \
grep -rn "bussiness_plan" . --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.pytest_cache 2>/dev/null | head -20
```

**Steps:**
```bash
# Rename folder
git mv docs/bussiness_plan docs/business_plan

# Update any references in other files (based on pre-flight grep)
# Use sed or str_replace for each reference
```

**Verification:**
```bash
grep -rn "bussiness_plan" . --exclude-dir=.git --exclude-dir=__pycache__ 2>/dev/null
# Expected: no output

ls docs/business_plan/   # files should still be there
```

**Hard rules:**
- Use `git mv` (preserves history), not `mv` + `git add`/`rm`.
- Update EVERY reference in the codebase. `grep` output above must become empty.
- Do NOT edit file contents beyond the folder path.

**Acceptance:**
- No file/reference contains `bussiness_plan`.
- `docs/business_plan/` contains all the original files.
- Full suite: still passing.

**Rollback:**
```bash
git mv docs/business_plan docs/bussiness_plan
# (and revert any other file changes)
```

---

# Optional Phase 1.2 Items (Decide on Arrival)

Per user instruction: **don't decide upfront, decide when we get to each one.** Listed for awareness only.

## Task #19 — Sentry or equivalent error tracking

**Decide on arrival. Only execute if:**
- Prod deploy is imminent AND
- You have a Sentry account OR another error tracker chosen

Non-blocking for Phase 1.2 close.

## Task #20 — Rate limiting on public endpoints

**Decide on arrival. Only execute if:**
- You're exposing endpoints to non-trusted AppClients (currently all are trusted) OR
- Public-facing discovery (Phase 3 MCP exposure) is starting

Auth middleware already has per-client rate limit (60/min default). May not need more.

## Task #21 — Secrets handling audit

**Decide on arrival. Only execute if:**
- `.env.prod` is being created AND
- You want to audit what's currently in `.env` for prod-inappropriate values

Quick check: `grep -E "SECRET|KEY|PASSWORD|TOKEN" .env` and confirm each value is rotated from any test/dev default.

## Task #22 — CI pipeline

**Decide on arrival. Only execute if:**
- You want PR checks enforced on GitHub AND
- You're ready to commit to keeping CI green (broken main = blocker)

Minimal first pass: GitHub Actions running `ruff check` + `pytest` on every PR.

---

# Phase 1.3 — Live Integration Tests (High-Level Only)

**Size:** 1-2 weeks, dedicated effort.
**Prerequisite:** Phase 1.2 complete, prod compose working, at least a staging env.

**Scope — all 24 services:**

| Category | Services |
|---|---|
| Social (20) | bluesky, discord, dribbble, facebook, google_business, instagram, linkedin, linkedin_page, mastodon, mewe, pinterest, reddit, skool, slack, telegram, threads, tiktok, whop, x, youtube |
| Storage (4) | box, dropbox, google, onedrive |

**Infrastructure needs (before writing any test):**
1. Burner accounts on all 20 social platforms
2. Dedicated OAuth apps registered for all 4 storage providers
3. Credential vault (env-based is acceptable for now: `.env.test.live`)
4. Cleanup hooks — every test that posts must delete its post
5. Per-test rate-limit handling (pytest-retry + skip-on-rate-limit)
6. Opt-in via pytest marker (`integration_live`) already scaffolded in Phase 1.0

**Execution order within Phase 1.3:**
1. Storage first (4 services) — OAuth flows are reusable, less noisy
2. Webhook-based social (slack, discord, telegram) — easiest, no OAuth dance
3. OAuth-based social (reddit, bluesky, mastodon, x, linkedin, etc.)
4. Complex (tiktok, youtube — video upload)
5. Placeholders (skool, mewe) — confirm they still return the "not supported" error

**Detailed plan written after Phase 1.2 closes. Not writing prompts for live tests here.**

---

# Phase 2 — Scope (Reference Only, Not Executable)

## P2-A: Notify model redesign
Migrate notify models from Django User FK to `app_client + external_user_id` composite key pattern. Matches storage/social architecture. Addresses D6.

## P2-B: Notify API compaction
Review the 18 notify endpoints. Likely compact to ~6-8 (merge CRUD into fewer, RESTful endpoints). Addresses D4.

## P2-C: AI proxy for Postiz
Expose NAI's OpenAI connection as an internal service so Postiz (and other tools) use centralized credit management instead of calling OpenAI directly.

## P2-D: MCP exposure
Wrap existing REST adapters as MCP server tools. Distribution: AI IDEs (Claude Desktop, Cursor, Windsurf) can call NEMI directly.

## P2-E: `/contents/` endpoint testing
Addresses D8 (deferred from Phase 1.1 Task #5). Tests for list_folder, download_file, etc. across all 4 storage providers.

---

# How to Use This Plan

For each Phase 1.2 task (8-18, optional 19-22):

1. **Read the task section in full.**
2. **Copy the pre-flight block, send to agent.**
3. **Human reviews pre-flight output.** Agent must STOP after pre-flight.
4. **Copy the steps block + hard rules, send to agent.** Add any overrides.
5. **Agent executes, runs verification, reports back.**
6. **Human checks acceptance criteria.** If green, commit.
7. **Commit message convention:** `<type>(<scope>): <summary>` matching existing commit history.

**If a task reveals a new bug mid-flight:**
- Do NOT silently fix it in the same commit.
- Add to tech debt list.
- Fix in its own task.

**Every commit must pass:**
- Full suite: ≥ 262 (or current baseline, never lower)
- Ruff clean
- No untracked files except those being committed

---

**End of plan.**
