---
name: perf-audit
description: "Performance audit for nai-integrations FastAPI backend. Checks N+1 queries, async anti-patterns, caching, Celery task efficiency, connection pooling, pagination, MongoDB indexing, and provider call optimization. Use when user says perf audit, performance, slow, optimize, or query optimization."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Perf Audit — Performance Review

**RULE: Do NOT fix anything. Report only.**

---

## Phase 1 — Scope

```bash
find app -name '*.py' | wc -l
find app -name '*.py' -exec wc -l {} + | sort -rn | head -20
```

---

## Phase 2 — Query Performance (N+1)

Scan `app/db/`, `app/services/`, `app/api/routers/` for:

FAIL:
- DB queries inside loops without bulk fetch
- `.get()` or `.filter()` in loops without eager loading
- Queryset evaluated multiple times
- Missing `joinedload` / `selectinload` on relationships

WARN:
- Missing `.limit()` on large queries
- Large result sets without `.yield_per()` / streaming

---

## Phase 3 — Async Anti-Patterns

FAIL:
- `time.sleep()` in `async def` (use `asyncio.sleep()`)
- Synchronous DB queries in `async def`
- `requests.get/post` in async context (use `httpx.AsyncClient`)
- Sequential `await` calls that could use `asyncio.gather()`

WARN:
- CPU-bound work in `async def` without `run_in_executor()`
- Sync `def` endpoint doing only I/O that could be async
- Missing `async with` on client sessions

---

## Phase 4 — Pagination

FAIL:
- List endpoints without pagination parameters
- Pagination without default limit / max limit cap
- Queries returning unbounded result sets

---

## Phase 5 — Caching

FAIL:
- Provider model catalog lookups repeated without Redis cache
- Expensive computations repeated without cache

WARN:
- No cache invalidation on writes
- Missing TTL on cached items
- Read-heavy endpoints without any caching

---

## Phase 6 — Celery Task Performance

FAIL:
- Sync HTTP calls without timeout
- Entire querysets loaded (use streaming / chunking)
- No `soft_time_limit` set

WARN:
- Missing `chunks()` for bulk operations
- Heavy tasks on default queue (should use dedicated queue)
- No retry backoff (exponential backoff recommended)

---

## Phase 7 — Connection Pooling

FAIL:
- New DB connection per request (should use pool)
- HTTP client created per-request (should use shared client)
- Redis connection not pooled

WARN:
- Pool size not configured for production
- Missing connection timeout settings

---

## Phase 8 — MongoDB Performance

FAIL:
- Collection queries without indexes on filtered fields
- Missing compound indexes for common query patterns
- Large documents fetched when only subset needed (missing projection)

WARN:
- No TTL index on ephemeral collections
- Missing aggregation pipeline for complex queries (using multiple queries instead)

---

## Phase 9 — Report

```
## Perf Audit — nai-integrations
| # | File:Line | Issue | Category | Severity |
|---|-----------|-------|----------|----------|

Top 3 impact fixes:
1. ...
2. ...
3. ...
```
