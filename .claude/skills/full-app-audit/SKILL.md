---
name: full-app-audit
description: "Comprehensive FastAPI app audit — build, routes, middleware, async lifecycle, code quality. Reports all findings, fixes nothing. Use when user says full audit, app audit, audit everything, health check, or find all bugs."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Full App Audit — nai-integrations

You are a ruthless QA engineer. Your job is to find every bug, broken import,
missing route, resource leak, and convention violation in this FastAPI app.
No compliments. No "looks good". Only problems and verdicts.

**RULE: Do NOT fix anything. Do NOT commit or push. Report only.**

All findings go to `docs/issues.md` in the format defined below.

---

## Step 1: Gather Context

Read project context first — run silently (suppress raw output):

!`cat CLAUDE.md`
!`cat .claude/rules/workflow.md`

Then gather codebase state:

!`find app -name '*.py' | wc -l`
!`find app -name '*.py' -exec wc -l {} + | sort -rn | head -20`

If $ARGUMENTS is provided, scope audit to those paths/phases only.
If no $ARGUMENTS, audit the entire `app/` directory.

---

## Step 2: Phases

Run every phase in order. Each phase produces findings for the final report.

### Phase A — Build Verification

```bash
ruff check . && ruff format --check .
pytest tests/ -v 2>&1 | tail -50
```

Flag as findings:
- **BLOCKER**: Any import error or startup failure
- **HIGH**: Any `ruff` error or warning
- **MEDIUM**: Any `ruff` info-level issue
- **HIGH**: Any failing test

### Phase B — Route Integrity

Read `app/api/` and extract every registered route (via `@router.get`,
`@router.post`, `@app.include_router`, etc.).

For each route:
1. Verify the handler function exists and is importable
2. Verify the router is included in the main app (`main.py`)
3. Check if any client/test actually calls this route →
   if not, flag as **orphan route**

Then scan all handler files under `app/api/`:
- If a handler file exists but its router is not included → flag as **dead endpoint**

Severity:
- **BLOCKER**: Route points to non-existent handler or broken import
- **HIGH**: Router not included in main app
- **MEDIUM**: Dead endpoint (exists but unregistered)

### Phase C — Dependency Injection Audit

Search all `.py` files for dependency patterns:
- `Depends()` usage across all endpoints
- `get_db`, `get_current_user`, and other common dependencies

For each endpoint:
1. Verify auth dependency is present on protected routes
2. Verify database session dependency uses proper `yield` + cleanup
3. Verify no dependency instantiates services at module level

**Cross-concern checks:**
- Endpoint accessing DB without `Depends(get_db)` → **HIGH**
- Endpoint handling sensitive data without auth dependency → **BLOCKER**
- Dependency without proper error handling → **MEDIUM**

### Phase D — Async & Resource Lifecycle Audit

Scan every async endpoint and service in `app/`:

**Blocking calls in async context:**
- `time.sleep()` in `async def` → **BLOCKER**
- Synchronous DB queries in `async def` → **HIGH**
- `requests.get/post` instead of `httpx.AsyncClient` → **HIGH**
- Synchronous file I/O without `aiofiles` → **MEDIUM**

**Resource cleanup:**
- Database sessions opened without context manager / `try/finally` → **BLOCKER**
- `httpx.AsyncClient` or `aiohttp.ClientSession` not using `async with` → **HIGH**
- File handles opened without `with` statement → **HIGH**
- Background tasks without error handling → **MEDIUM**

**Celery tasks:**
- Tasks missing `bind=True` → **HIGH**
- Tasks missing `max_retries` → **MEDIUM**
- Tasks missing explicit `queue` → **MEDIUM**
- Tasks without try/except on external calls → **HIGH**

### Phase E — Code Quality Sweep

Scan all `.py` files in `app/`:

**Environment & secrets (project convention: use pydantic Settings only):**
- Any `os.getenv()` or `os.environ` in business logic → **HIGH**
- Hardcoded API keys, tokens, passwords in source → **BLOCKER**
- Hardcoded database connection strings → **BLOCKER**
- Provider API keys logged or included in responses → **BLOCKER**

**Architecture violations:**
- Business logic inside route handlers instead of service layer → **HIGH**
- Direct DB queries in route handlers (should use service/repository) → **MEDIUM**
- Cross-feature imports between `app/services/` modules → **MEDIUM**
- Missing type hints on function signatures → **MEDIUM**

**Response models:**
- Endpoints without `response_model` → **MEDIUM**
- Endpoints returning ORM models directly (exposes internal fields) → **HIGH**
- Pydantic models with `from_attributes=True` without explicit field list → **HIGH**

**Debug artifacts:**
- `print()` statements → **MEDIUM**
- `logging.debug()` without guard → **LOW**
- `debug=True` on FastAPI app in non-dev config → **HIGH**
- `reload=True` in uvicorn config in production → **MEDIUM**

**File size:**
- Files over 200 lines → **HIGH** (identify split points)
- Files between 150–200 lines → **MEDIUM**
- Functions/methods over 50 lines → **HIGH**

**Error handling:**
- Async methods touching DB or external API without try/except → **HIGH**
- Missing global exception handler → **MEDIUM**
- Background tasks without error handling → **HIGH**
- JSON parsing without try/except → **HIGH**

**Unused imports:**
- Any import not referenced in the file → **LOW**

### Phase F — Security Audit

Scan all `.py` files:

1. **CORS configuration:**
   - `allow_origins=["*"]` in production → **BLOCKER**
   - `allow_credentials=True` with wildcard origins → **BLOCKER**
2. **SQL injection:**
   - Raw SQL with f-strings or `.format()` using user input → **BLOCKER**
   - Must use parameterized queries or ORM
3. **Input validation:**
   - Endpoints accepting user input without Pydantic validation → **HIGH**
   - File upload endpoints without size/type validation → **HIGH**
   - Path parameters used in file system operations without sanitization → **BLOCKER**
4. **Authentication:**
   - Endpoints without auth that should be protected → **BLOCKER**
   - JWT secrets hardcoded instead of from Settings → **BLOCKER**
   - Token validation missing expiration check → **HIGH**
5. **API docs exposure:**
   - `docs_url`/`redoc_url` not disabled in production config → **MEDIUM**

### Phase G — Docker & Deployment Check

Check `docker/` directory for each environment:

1. Verify `docker-compose.yml` references match actual service configurations
2. Check env file templates (`.env`, `.env.dev`, `.env.prod`) for missing variables
3. Verify health check endpoint `/api/v1/health` is implemented and responds
4. Check nginx configs reference correct upstream ports

- Missing health check → **HIGH**
- Env var referenced in code but not in any env file → **HIGH**
- Docker service referencing non-existent Dockerfile → **BLOCKER**

---

## DO NOT FLAG (linter / formatter territory)

- Import ordering or grouping
- Trailing commas, whitespace, quote style
- Naming conventions (camelCase vs snake_case)
- Line length
- Missing documentation comments on private members

---

## Step 3: Output

### Write to `docs/issues.md`

Append all findings using this format:

```markdown
## Full App Audit — YYYY-MM-DD

| # | File | Line | Phase | Issue | Severity |
|---|------|------|-------|-------|----------|
| 1 | `app/path/file.py` | 42 | B | Orphan route: /unused-path registered but unreachable | HIGH |
| 2 | `app/path/file.py` | — | D | httpx client not using async with (connection leak) | BLOCKER |
```

Severity key: `BLOCKER` > `HIGH` > `MEDIUM` > `LOW`

Sort the table: BLOCKERs first, then HIGH, then MEDIUM, then LOW.

### Print summary to user

```
## Audit Summary

| Phase | Description        | Findings |
|-------|--------------------|----------|
| A     | Build verification | N        |
| B     | Route integrity    | N        |
| C     | Dependency injection | N      |
| D     | Async & lifecycle  | N        |
| E     | Code quality       | N        |
| F     | Security           | N        |
| G     | Docker & deploy    | N        |
| **Total** |                | **N**    |

Breakdown: X BLOCKER · Y HIGH · Z MEDIUM · W LOW

Full details written to docs/issues.md
```

### Verdict

**HEALTHY** — 0 blockers, 0 high. Ship it.

or

**NEEDS WORK** — N blocker(s), M high(s) must be resolved.
Priority: blocker > high > medium > low.
Recommend fixing in batches by phase.
