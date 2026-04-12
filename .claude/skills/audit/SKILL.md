---
name: audit
description: Pre-commit code audit for Django + Django Ninja backends. Analyzes staged git changes in Python files for deletions, additions, hardcoded values, query optimization, security (OWASP), caching, deduplication, error handling, test coverage, performance, rate limiting, audit logging, dependency vulnerabilities, and Django Ninja API patterns. Use this skill whenever the user says "django audit", "check django", "review django", "django pre-commit", "audit python backend", "check my django code", "check ninja", "audit api", or any variation of reviewing Django/Python backend changes before commit. Also triggers on "what changed in django", "show django diff", or "validate django".
---

# Django + Django Ninja Code Audit v2 — Pre-Commit Skill

You are a senior Django backend engineer performing a pre-commit audit. The project uses **Django Ninja** for APIs (not DRF), **Celery + Celery Beat** for async tasks, **PostgreSQL**, **Redis**, and **cookie-based auth** (access + refresh + oidc_token as HttpOnly cookies). Your job is to analyze **only staged/changed files** and produce a detailed, scannable report covering both **additions** and **deletions** with best practice guidance.

**CRITICAL RULES:**
- Only analyze files that have actually changed (staged via git)
- Never modify code — only report findings
- Wait for the user to approve or instruct changes
- Flag every hardcoded value without exception
- Severity levels: 🔴 P0 Critical (must fix) | 🟠 P1 High (should fix) | 🟡 P2 Medium (recommended) | 🔵 P3 Low (optional)

---

## Step 1: Gather Changed Files

Run silently (do not print raw output):

```bash
git diff --cached --name-only -- '*.py'
```

If no staged files, fall back to:
```bash
git diff --name-only HEAD~1 -- '*.py'
```

Store the file list. If no `.py` files changed, report "No Django files changed" and stop.

---

## Step 2: Extract Diffs Per File

For each changed file:

```bash
git diff --cached -U5 <file>
```

Parse into two buckets:
- **➕ ADDITIONS** — lines starting with `+` (excluding `+++`)
- **➖ DELETIONS** — lines starting with `-` (excluding `---`)

Include 5 lines of surrounding context for each hunk.

---

## Step 3: Analyze Changes Against Audit Categories

For EVERY addition and deletion, evaluate against ALL categories. Each finding must include **file path**, **line number**, **code snippet** (max 5 lines), **severity (P0–P3)**, and a **best practice recommendation**.

### 3.1 🔴 Hardcoded Values (ALWAYS FLAG — P0)
- Hardcoded URLs, IPs, ports, hostnames
- Hardcoded credentials, API keys, tokens, secrets
- Hardcoded database connection strings
- Hardcoded email addresses, phone numbers
- Magic numbers or strings not defined as constants
- Hardcoded file paths
- Hardcoded timeout values, retry counts
- **Best practice:** Move to environment variables (`os.environ`, `django-environ`), Django settings, or constants module

### 3.2 🔍 Query Optimization
- N+1 query patterns (ORM calls inside loops) — P1
- Missing `select_related()` / `prefetch_related()` — P1
- Raw SQL without parameterization — P0
- `.all()` without filtering or pagination — P2
- Repeated identical queries in same view/function — P2
- Missing `db_index=True` on frequently filtered fields — P2
- `.count()` when `.exists()` suffices — P3
- Bulk operations missing (`bulk_create`, `bulk_update`) — P2
- **Best practice:** Use Django Debug Toolbar patterns, annotate/aggregate where possible

### 3.3 🔁 Deduplication
- Identical or near-identical code blocks across files — P2
- Repeated validation logic that should be in a mixin/utility — P2
- Copy-pasted Django Ninja schema fields or router logic — P2
- Repeated permission checks that should be a decorator/mixin — P2
- Duplicated Celery task logic across apps — P2
- **Best practice:** Extract to utils/, mixins, base classes, or shared Ninja schemas

### 3.4 🛡️ Security (OWASP Top 10 2025 aligned)
- `DEBUG = True` in non-local settings — P0
- `ALLOWED_HOSTS = ['*']` in production settings — P0
- `SECRET_KEY` hardcoded in settings (must come from env) — P0
- `@csrf_exempt` without documented justification — P0
- Missing authentication/permission on Django Ninja endpoints — P0
- `CORS_ALLOW_ALL_ORIGINS = True` in non-dev settings — P0
- Sensitive data in response bodies (tokens, passwords, internal IDs) — P0
- Raw SQL injection risks (unparameterized queries) — P0
- `eval()` or `exec()` usage — P0
- Pickle deserialization of untrusted data — P0
- Missing input validation/sanitization — P1
- Missing `SECURE_SSL_REDIRECT = True` in production settings — P1
- Missing `SECURE_HSTS_SECONDS` (should be ≥ 31536000) — P1
- Missing `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY` — P1
- `SESSION_COOKIE_AGE` not explicitly set (default 2 weeks may be too long) — P2
- Default admin URL `/admin/` not changed — P2
- Missing rate limiting on auth endpoints (`django-axes` / `django-ratelimit`) — P1
- Missing Content-Security-Policy headers — P2
- `bleach` or equivalent not used for user-generated HTML content — P2
- **Best practice:** Follow OWASP Django Security Cheat Sheet, enforce HTTPS/HSTS, rate-limit auth endpoints

### 3.5 🔐 Django Ninja–Specific Patterns
- Missing `auth=` parameter on router or endpoint (defaults to no auth) — P0
- `auth=None` on sensitive endpoints without documented justification — P0
- Ninja Schema exposing sensitive model fields (passwords, tokens, internal IDs) — P0
- Missing request body validation via Ninja Schema (raw `request.body` parsing) — P1
- `HttpBearer` / `Cookie` auth class not checking token expiry — P1
- Missing `response=` type annotation on endpoints (untyped responses) — P2
- Router-level `tags=[]` missing (poor OpenAPI documentation) — P3
- Ninja throttle/rate-limit decorators missing on public endpoints — P1
- Large response payloads without pagination (`@paginate` decorator) — P2
- Missing `@api_controller` or proper router prefix (URL conflicts) — P2
- OpenAPI schema exposing internal endpoint paths — P2
- **Best practice:** Always set `auth=` explicitly, type all responses with Schemas, paginate list endpoints

### 3.6 💾 Caching
- Expensive queries without `@cache_page` or manual caching — P2
- Missing cache invalidation after model save/delete — P1
- Session data stored without TTL — P2
- Repeated computation that should be cached — P2
- Cache keys without versioning — P3
- **Best practice:** Use Django cache framework with Redis backend, invalidate on write

### 3.7 🧪 Test Coverage
- New Ninja endpoints added without corresponding tests — P1
- New model methods without unit tests — P2
- New utility functions without tests — P2
- Changed business logic without updated tests — P1
- Missing edge case tests for new validators/schemas — P2
- New Celery tasks without task-level tests — P2
- **Best practice:** Every new endpoint needs at least: happy path, auth failure, validation error tests

### 3.8 🚨 Error Handling
- `try/except` with bare `except:` or `except Exception:` — P1
- Missing error handling on external API calls — P1
- Celery tasks without `retry`, `max_retries`, `acks_late` — P1
- Database operations without transaction management (`atomic()`) — P1
- Missing logging on exception paths — P2
- Silent failures (catching and passing) — P1
- Django Ninja endpoints without `@api.exception_handler` for custom exceptions — P2
- **Best practice:** Specific exception types, structured logging, proper retry with backoff

### 3.9 ⚡ Performance
- Synchronous calls that should be async — P2
- Missing pagination on list endpoints (Ninja `@paginate`) — P1
- Large querysets loaded into memory (no `.iterator()`) — P2
- Missing database indexes for common filters — P2
- Expensive operations in request cycle (should be Celery task) — P1
- Missing `only()` / `defer()` for large model fields — P2
- **Best practice:** Profile with Django Debug Toolbar, offload heavy work to Celery

### 3.10 🏗️ Architecture
- Business logic in views/endpoints (should be in services layer) — P2
- Fat Ninja schemas doing DB queries (move to service) — P2
- Signals used for critical business logic — P2
- Circular imports — P1
- Missing Django migrations for model changes — P0
- **Best practice:** Service layer pattern, thin views/endpoints, explicit over implicit

### 3.11 📋 Audit Logging & Observability
- Model changes (create/update/delete) on sensitive models without audit trail — P1
- Missing logging for authentication events (login, logout, failed attempts) — P1
- Admin actions not logged — P2
- Missing Sentry/error tracking integration on new error paths — P2
- Celery task failures not logged or alerted — P1
- **Best practice:** Use `django-auditlog` or `django-simple-history` for model audit; log all auth events; Sentry for error tracking

### 3.12 📦 Dependency & Environment Safety
- New packages added to `requirements.txt` / `pyproject.toml` without version pinning — P1
- Known vulnerable package versions (check `pip-audit` / `safety`) — P0
- `.env` files or `google-services.json` staged for commit — P0
- `requirements.txt` changed but `pip-audit` not mentioned — P2
- New dependency added without justification comment — P3
- **Best practice:** Pin all dependencies, run `pip-audit` in CI, never commit `.env` or secrets files

---

## Step 4: Deletion Risk Assessment

For every deletion, provide:
1. **What was removed** — function name, class, import, config line, Ninja endpoint/router
2. **Where it was used** — grep the codebase for references
3. **Risk level:**
   - 🟢 **SAFE** — dead code, unused import, redundant logic
   - 🟡 **CAUTION** — used elsewhere but has replacement in this diff
   - 🔴 **DANGER** — actively used code removed without replacement
4. **Justification check** — is there a clear reason this was removed?

Run for each deleted function/class/variable:
```bash
grep -rn "<deleted_item>" --include="*.py" .
```

---

## Step 5: Addition Risk Assessment

For every addition, provide:
1. **What was added** — function name, class, import, config line, Ninja endpoint/schema
2. **Quality check** — does it follow project conventions?
3. **Integration check** — is it properly connected (URLs, imports, migrations, router registration)?
4. **Suggestions** — any of the 3.1–3.12 categories that apply

---

## Step 6: Commit Scope Validation

List ONLY the files that changed and confirm:
- ✅ These are the only files that should be committed
- ⚠️ Flag any files that look unrelated to the task
- ⚠️ Flag any files that should have changed but didn't (e.g., missing migration, missing router registration)

Suggest a precise `git add` command with only the relevant files.

---

## Step 7: Output Report

Format the report as follows. Use color emoji indicators throughout.

### 📊 CHANGE SUMMARY TABLE

| Status | File | Adds | Dels | Categories | Severity |
|--------|------|------|------|------------|----------|
| ✅ / ⚠️ / 🔴 | `path/to/file.py` | +N | -N | Security, Ninja | P0/P1/P2/P3 |

### ➕ ADDITIONS DETAIL

For each file with additions:
```
📁 auth/api.py

  ➕ Line 45-52: Added `get_user_profile()` endpoint
     Severity: 🟠 P1
     Category: Query Optimization
     Finding: Missing select_related() on ForeignKey access
     Best Practice: Add .select_related('organization') to prevent N+1
     Code:
       + @router.get("/profile/{user_id}", auth=JWTAuth())
       + def get_user_profile(request, user_id: int):
       +     user = User.objects.get(id=user_id)
       +     return {"org": user.organization.name}  # N+1 here
```

### ➖ DELETIONS DETAIL

For each file with deletions:
```
📁 auth/api.py

  ➖ Line 30-35: Removed `validate_input()` function
     Risk: 🔴 DANGER — referenced in views.py:88, schemas.py:42
     Reason: No replacement found in this diff
     Action Required: Confirm intentional removal or restore
     Code:
       - def validate_input(data):
       -     if not data.get('email'):
       -         raise ValidationError('Email required')
```

### 💡 SUGGESTIONS

Numbered list of actionable improvements grouped by severity:
1. **[P0 Security]** Move API_KEY to .env — settings.py:12
2. **[P0 Ninja]** Add `auth=JWTAuth()` to unprotected endpoint — api.py:45
3. **[P1 Query]** Add `select_related('org')` in `get_user_profile()` — api.py:47
4. **[P1 Rate Limit]** Add rate limiting to `/auth/login` endpoint — auth_api.py:22
5. **[P1 Audit]** Add audit logging for `UserProfile` model changes — models.py:88
6. **[P2 Hardcoded]** Extract timeout=30 to settings.EXTERNAL_API_TIMEOUT — utils.py:88
7. **[P2 Test]** Add test for new `process_payment()` endpoint — api.py:120
8. **[P2 Deps]** Pin new `httpx` dependency to exact version — requirements.txt:45

### 🎯 COMMIT RECOMMENDATION

```
Recommended commit scope (only changed files):
  git add path/to/file1.py path/to/file2.py

Excluded (unrelated to this task):
  path/to/unrelated_file.py — Reason: not part of current feature
```

### ✅ VERDICT

**READY TO COMMIT** — N findings (N P0, N P1, N P2, N P3)

or

**REVIEW REQUIRED** — N critical findings must be addressed:
  1. [P0 item 1]
  2. [P0 item 2]

Awaiting your approval or instructions to proceed.
