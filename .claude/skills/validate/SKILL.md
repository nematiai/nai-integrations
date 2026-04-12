---
name: validate
description: "Post-implementation validation for nai-integrations FastAPI backend. Verifies plan completeness, route wiring, auth dependencies, async lifecycle, Celery tasks, code standards, and pydantic Settings usage. Use when user says validate, verify, recheck, or final check."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Validate — Post-Implementation Verification

**RULE: Do NOT fix anything. Report only.**
**RULE: Read every file — do not skim.**

---

## Phase 1 — Scope

```bash
git diff --name-only HEAD~3
git diff --cached --name-only
git status --short
```

Read most recent plan from `docs/plans/`. If $ARGUMENTS provided, scope to those.

---

## Phase 2 — Build & Lint

```bash
ruff check .
ruff format --check .
pytest tests/ -v 2>&1 | tail -50
```

FAIL: any ruff error, any failing test.

---

## Phase 3 — Plan Completeness

Read active plan. For each `[x]` phase: verify described work exists in code.
For each `[ ]` phase: FAIL (incomplete).
Phase mentions file that doesn't exist: FAIL.
Phase says "add route" but no route added: FAIL.
Phase says "add test" but no test created: FAIL.

---

## Phase 4 — Route & API Wiring

Read `main.py` for `app.include_router()` calls.
Read `app/api/routers/` for all `@router.get/post/put/delete` decorators.

For each new endpoint:
1. Router included in main app → FAIL if missing
2. Auth dependency present on protected routes → FAIL if missing
3. `response_model` specified → WARN if missing
4. Route parameters match handler signature → FAIL if mismatch

---

## Phase 5 — Auth & Security

FAIL:
- New endpoint without `Depends()` auth on protected data
- JWT secret hardcoded
- `allow_origins=["*"]` in production CORS
- Raw SQL with f-strings
- Provider API keys in logs or responses

---

## Phase 6 — Async & Resource Lifecycle

FAIL:
- `async def` with blocking calls (`time.sleep`, sync DB, `requests.*`)
- DB session without context manager
- `httpx.AsyncClient` without `async with`
- File handles without `with`
- `asyncio.create_task()` without stored reference

---

## Phase 7 — Celery Tasks

FAIL:
- Missing `bind=True`, `max_retries`, or explicit `queue`
- DB/API operations without try/except
- Not using `self.retry()` on transient failures

---

## Phase 8 — Environment & Config

FAIL:
- `os.getenv()` / `os.environ` in business logic (must use pydantic Settings)
- Hardcoded service URLs
- `debug=True` or `reload=True` in production config

---

## Phase 9 — Code Standards

Per CLAUDE.md: max 200 lines/file, 50 lines/function, 30 lines/endpoint.

FAIL:
- File over 200 lines
- Function over 50 lines
- Endpoint over 30 lines
- Business logic in route handlers
- Missing type hints on function signatures

WARN:
- Unused imports
- Magic strings not in constants
- Missing `response_model`

---

## Phase 10 — Docker & Deployment

Check `docker/` for changed compose files:
- Service references match actual Dockerfiles
- Env vars referenced in code exist in env templates
- Health check endpoint `/api/v1/health` responds
- Nginx configs reference correct upstream ports

---

## Phase 11 — Report

```
## Validation Report — [plan name]
Stack: FastAPI / PostgreSQL / MongoDB / Redis / Celery
Scope: N files changed

| # | Check | Result | Findings |
|---|-------|--------|----------|
| 1 | Build & lint | PASS/FAIL | |
| 2 | Plan completeness | PASS/FAIL | |
| 3 | Route & API wiring | PASS/FAIL | |
| 4 | Auth & security | PASS/FAIL | |
| 5 | Async & lifecycle | PASS/FAIL | |
| 6 | Celery tasks | PASS/FAIL | |
| 7 | Environment & config | PASS/FAIL | |
| 8 | Code standards | PASS/FAIL | |
| 9 | Docker & deploy | PASS/FAIL | |

**Verdict:** VALIDATED / NOT VALIDATED
```

Write findings to `docs/issues.md`.
