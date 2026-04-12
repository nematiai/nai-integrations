---
name: release-check
description: "Production deployment readiness check for nai-integrations. Verifies Docker builds, health check, migrations, security settings, debug artifacts, env config, Celery health, nginx, and deployment checklist. Use when user says release check, ready to deploy, production ready, deploy check, or ship it."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Release Check — Production Deployment Readiness

**RULE: Do NOT fix anything. Report only.**

---

## Phase 1 — Docker Build

Verify containers build and run for production:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "indox|mongo|redis|postgres|nginx"
```

Check `docker/production/docker-compose.yml` for service definitions.

---

## Phase 2 — Health Check

```bash
curl -f http://localhost:9050/api/v1/health 2>/dev/null || echo "Health check failed"
```

---

## Phase 3 — Lint & Tests

```bash
ruff check .
ruff format --check .
pytest tests/ -v 2>&1 | tail -50
```

---

## Phase 4 — Debug Artifacts

BLOCKER: scan `app/` for:
- `print()` statements (not in logging)
- `debug=True` on FastAPI app
- `reload=True` in uvicorn config
- `breakpoint()`, `import pdb`
- `logging.debug()` calls with sensitive data

---

## Phase 5 — Security Settings

Read production config. Check:
- CORS origins NOT wildcard
- JWT secrets from environment (pydantic Settings)
- No hardcoded API keys
- `docs_url` and `redoc_url` disabled (or auth-protected)
- HTTPS enforcement
- Rate limiting enabled

---

## Phase 6 — Environment Configuration

Check `.env.prod` template (do NOT read actual .env files — denied):
- All required vars documented
- No sensitive defaults
- Database URLs use production hosts
- Redis URL configured
- Celery broker URL configured
- All provider API key vars listed

---

## Phase 7 — Celery & Background Tasks

Verify:
- All tasks have `bind=True`, `max_retries`, explicit `queue`
- Error handling on all tasks
- Beat schedule configured (if applicable)
- Worker concurrency settings in production compose

---

## Phase 8 — Nginx Configuration

Read `nginx/` configs:
- Production upstream points to correct backend port
- SSL/TLS configured
- CORS headers correct for production origins
- Max upload size appropriate
- Static file serving configured

---

## Phase 9 — MongoDB & PostgreSQL

Check:
- Migration scripts exist for any schema changes
- MongoDB indexes defined for production queries
- Connection pooling configured for production load
- Backup configuration documented

---

## Phase 10 — Final Checks

BLOCKER:
- Hardcoded `localhost` URLs in production code
- Test credentials in code
- `.env` files in git
- GitHub Actions workflows pass

---

## Phase 11 — GitHub Issue Gate
Check all open issues before shipping:
```bash
source .env && curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues?state=open&per_page=100" \
  | grep -E '"number"|"title"|"labels"'
```

**Evaluate open issues:**
- Any `[P0]` or `[P1]` in title → **BLOCKED — cannot ship with critical issues open**
- Any `[P2]` or `[P3]` in title → **WARNING — list them, ask user if OK to proceed**
- No open issues → CLEAR

**Close fixed issues (requires user approval):**
For each issue the user approves to close:
```bash
source .env && RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues/NUMBER" \
  -d '{"state":"closed"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "CLOSED — issue #NUMBER"
else
  echo "FAILED — issue #NUMBER NOT closed, report to user"
fi
```
Verify each says "CLOSED". Update docs/issues.md: `- [x] desc — #NUMBER (closed for release)`

**NEVER close issues without user approval.**

---

## Phase 12 — Report

```
## Release Check — nai-integrations
| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | Docker build | PASS/FAIL | |
| 2 | Health check | PASS/FAIL | |
| 3 | Lint & tests | PASS/FAIL | |
| 4 | Debug artifacts | PASS/FAIL | |
| 5 | Security settings | PASS/FAIL | |
| 6 | Env config | PASS/FAIL | |
| 7 | Celery tasks | PASS/FAIL | |
| 8 | Nginx config | PASS/FAIL | |
| 9 | Database | PASS/FAIL | |
| 10 | Final checks | PASS/FAIL | |

**Verdict:** READY TO DEPLOY / NOT READY
```
