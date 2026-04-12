---
name: review
description: "Quick production code review on specific files for nai-integrations FastAPI backend. Checks auth dependencies, async safety, Celery patterns, response models, security, query performance, and code standards. Use when user says review, check this file, look at this, or code review."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Review — Targeted File Code Review

**RULE: Do NOT fix anything. Report only.**
**RULE: Read every file fully — do not skim.**

---

## Phase 1 — Identify Targets

If $ARGUMENTS provided, use those files.
Otherwise: `git diff --name-only HEAD~1`

---

## Phase 2 — Static Analysis

```bash
ruff check [files]
```

---

## Phase 3 — Auth & Response Model Compliance

FAIL:
- Endpoint missing `Depends()` auth on protected data
- Endpoint returning ORM model without `response_model`
- `response_model` exposing sensitive fields (password, hashed_password, secret_key, refresh_token)
- Pydantic model with `from_attributes=True` without explicit field list
- Input schema missing `Field()` validators on user-facing fields

---

## Phase 4 — Async & Resource Safety

FAIL:
- Blocking calls in `async def` (`time.sleep`, sync DB, `requests.*`)
- DB session without context manager
- `httpx.AsyncClient` / `aiohttp.ClientSession` without `async with`
- File handles without `with`

WARN:
- `await` in loop when `asyncio.gather()` would parallelize
- CPU-bound work in `async def` without `run_in_executor()`

---

## Phase 5 — Celery Task Patterns

FAIL:
- Missing `bind=True`, `max_retries`, or explicit `queue`
- DB/API ops without try/except
- Not using `self.retry()` on transient failures
- Task importing FastAPI request context

---

## Phase 6 — Query Performance

FAIL:
- N+1 query pattern (DB queries inside loops)
- List endpoints without pagination

WARN:
- Missing eager loading (joinedload/selectinload)
- Heavy computation without caching

---

## Phase 7 — Security

FAIL:
- Raw SQL with f-strings
- Hardcoded secrets
- `eval`/`exec` with user input
- Provider keys in logs or responses
- `os.getenv()` in business logic

---

## Phase 8 — Code Standards

Per CLAUDE.md: max 200 lines/file, 50 lines/function, 30 lines/endpoint.

FAIL:
- File over 200 lines
- Function over 50 lines
- Endpoint over 30 lines
- Business logic in route handlers

WARN:
- Unused imports
- Magic strings
- Missing type hints

---

## Phase 9 — Report

```
## Review — [file name(s)]
| # | File:Line | Issue | Severity |
|---|-----------|-------|----------|

**Verdict:** CLEAN / N issue(s) found
```
