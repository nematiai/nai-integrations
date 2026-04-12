---
name: api-audit
description: "API contract and documentation audit for nai-integrations FastAPI backend. Checks endpoint consistency, response models, error handling, auth dependencies, rate limiting, CORS, and OpenAPI spec. Use when user says api audit, check endpoints, api review, schema check, or endpoint audit."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# API Audit — Endpoint & Contract Review

**RULE: Do NOT fix anything. Report only.**

---

## Phase 1 — Scope

Read `main.py` for all `app.include_router()` calls and prefixes.
Read `app/api/routers/` to inventory all endpoints.

---

## Phase 2 — Endpoint Inventory

List all endpoints with: method, path, auth dependency, response_model, status codes.

FAIL:
- Missing `response_model`
- Missing auth `Depends()` on protected routes
- Duplicate paths
- Inconsistent URL naming (mixed kebab/snake)

---

## Phase 3 — Request Schema Validation

Read Pydantic input schemas in `app/models/`.

FAIL:
- Input schema without `Field()` constraints (min_length, max_length, ge, le)
- `from_attributes=True` without explicit field list
- Missing type hints
- Required fields marked Optional without default

---

## Phase 4 — Response Schema Validation

FAIL:
- Sensitive fields exposed (password, hashed_password, secret_key, refresh_token, provider_api_key)
- Single status code response (missing error codes)
- Inconsistent error format across endpoints
- Missing pagination schema on list endpoints
- ORM models returned directly without response schema

---

## Phase 5 — HTTP Method Conventions

FAIL:
- GET that modifies data
- POST for updates (should be PUT/PATCH)
- Non-idempotent PUT
- DELETE without confirmation or soft-delete pattern

---

## Phase 6 — Rate Limiting & Throttling

FAIL:
- Auth endpoints without rate limiting
- File upload endpoints without size limit
- Public endpoints without throttling
- Provider proxy endpoints without per-user rate limit

---

## Phase 7 — Error Handling Consistency

FAIL:
- Raw exceptions returned to client
- Inconsistent error response format
- 500s exposing internal details / tracebacks
- Missing 404 handling on resource endpoints
- Provider errors leaked to client without sanitization

---

## Phase 8 — Report

```
## API Audit — nai-integrations
| # | Endpoint | Method | Issue | Severity |
|---|----------|--------|-------|----------|

Summary: Total endpoints N, auth X, response models Y, error handling Z
```
