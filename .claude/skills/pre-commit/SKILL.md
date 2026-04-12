---
name: pre-commit
description: "Pre-push code quality and security gate for nai-integrations FastAPI backend. Checks secrets, auth dependencies, async safety, Celery tasks, CORS, response models, resource cleanup, code standards. Use when user says pre-commit, pre-push, audit changes, check my code, or gate check."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Pre-Commit Audit — nai-integrations

**RULE: Do NOT fix anything. Report only.**
**RULE: Execute every phase in order. Do NOT skip phases.**

---

## Phase 1 — Gather Scope

```bash
git diff --cached --name-only
git diff --cached --stat
git diff --cached
git diff --cached --word-diff=porcelain | awk '/^+/{print "+ "$0} /^-/{print "- "$0}' | head -20
```

If $ARGUMENTS provided, scope to those files only.
If no staged files, fall back to `git diff --name-only HEAD~1`.

---

## Phase 2 — Lint & Format

```bash
ruff check .
ruff format --check .
```

FAIL: any ruff error. WARN: any ruff info-level issue.

---

## Phase 3 — Secrets & Credential Leaks

BLOCKER — scan staged diff for:
- API keys: `AKIA[0-9A-Z]{16}`, `sk-[a-zA-Z0-9]{20,}`, `ghp_[a-zA-Z0-9]{36}`
- `password\s*=\s*["'][^"']+["']`
- Database connection strings: `postgres://`, `mongodb://`, `redis://`
- Private keys: `-----BEGIN.*PRIVATE KEY-----`
- JWT tokens: `eyJ[a-zA-Z0-9_-]{10,}\.eyJ`
- High-entropy strings assigned to key/secret/token/password/credential vars
- `.env` files staged, `google-services.json` staged
- Provider API keys logged via `print()`, `logging.info()`, or in responses

---

## Phase 4 — Auth & Security

BLOCKER:
- Endpoints without `Depends()` auth on protected routes
- `allow_origins=["*"]` in CORSMiddleware in non-local config
- `allow_credentials=True` with wildcard origins
- Raw SQL with f-strings or `.format()` with user input
- `eval()`, `exec()`, `__import__()` with user input
- JWT secret hardcoded instead of from pydantic Settings
- Token validation missing expiration check

FAIL:
- Missing rate limiting on auth endpoints
- `docs_url`/`redoc_url` not disabled in production config
- File paths from user input without sanitization
- Jinja2 `Template(user_input).render()` — SSTI risk

---

## Phase 5 — Async & Resource Safety

BLOCKER:
- `time.sleep()` in `async def`
- Synchronous DB queries in `async def`
- DB session without context manager / `try/finally`

FAIL:
- `requests.get/post` instead of `httpx.AsyncClient` in async context
- `httpx.AsyncClient` / `aiohttp.ClientSession` not using `async with`
- File handles opened without `with` statement
- `asyncio.create_task()` without storing reference
- Missing `async with` on client sessions

WARN:
- `await` inside loop when `asyncio.gather()` would parallelize
- CPU-bound work in `async def` without `run_in_executor()`

---

## Phase 6 — Celery Tasks

FAIL:
- Task missing `bind=True`
- Task missing `max_retries`
- Task missing explicit `queue`
- Task doing DB/API ops without try/except
- Task not using `self.retry()` on transient failures
- Task importing FastAPI request context

---

## Phase 7 — Response Models & Data Exposure

FAIL:
- Endpoint returning ORM model directly without `response_model`
- `response_model` including sensitive fields (password, hashed_password, secret_key, refresh_token)
- Pydantic model with `from_attributes=True` without explicit field list
- Raw exception details/tracebacks returned to client

WARN:
- Missing `response_model` on any endpoint
- Input schema missing `Field()` constraints

---

## Phase 8 — Environment & Config

FAIL:
- `os.getenv()` or `os.environ` in business logic (must use pydantic Settings)
- Hardcoded API base URLs or service endpoints
- `debug=True` on FastAPI app in non-dev config
- `reload=True` in uvicorn config in production code

---

## Phase 9 — Code Standards

Per CLAUDE.md: max 200 lines per file, max 50 lines per function.

FAIL:
- File over 200 lines
- Function over 50 lines
- Endpoint handler over 30 lines
- Business logic in route handler (should be in service layer)
- Router file over 200 lines without splitting

WARN:
- File 150–200 lines approaching limit
- Magic strings/numbers not in constants
- TODO/FIXME without issue number
- Commented-out code blocks (>3 lines)
- Unused imports

---

## Phase 10 — Report

```
## Pre-Commit Audit — nai-integrations

| File | Lines | Hard Fails | Warnings | Verdict |
|------|-------|-----------|----------|---------|

### Hard Fails
File:Line — Rule — Evidence — Fix

### Warnings
File:Line | Rule | Description

**Verdict:** APPROVED / BLOCKED (N hard fails)
Priority: security > resource leak > celery > config > standards
```
