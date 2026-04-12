---
name: redo
description: "Re-execute a previously completed task for nai-integrations. Reruns ruff, pytest, line checks, phase verification, or any prior action. Use when user says redo, run again, recheck, retry, rerun, or repeat that."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Redo — Re-Execute a Completed Task

**RULE: Execute the task fully — not a summary of what was done before.**
**RULE: Use the latest file state, not cached results.**

---

## Phase 1 — Identify What to Redo

| User says | Action |
|-----------|--------|
| `/redo tests` | `pytest tests/ -v` |
| `/redo lint` | `ruff check . && ruff format --check .` |
| `/redo lines` | Re-check changed files for 200/50 line limits |
| `/redo phase N` | Re-verify phase N from active plan |
| `/redo [filename]` | Re-audit that specific file |
| `/redo pre-commit` | Run full /pre-commit flow |
| `/redo validate` | Run full /validate flow |
| `/redo build` | `cd docker/local && docker-compose up -d --build` |
| `/redo last` | Repeat last substantive action |

If NO arguments, identify last action and offer to redo it.

---

## Phase 2 — Execute

### 2A — Tests
```bash
pytest tests/ -v
```
If scoped: `pytest [path] -v`

### 2B — Lint
```bash
ruff check .
ruff format --check .
```

### 2C — Line Check

```bash
git diff --cached --name-only 2>/dev/null || git diff --name-only HEAD~1
```

For each changed `.py` file: `wc -l [file]`
- Over 200 → FAIL, suggest split points
- 150–200 → WARN
- Under 150 → PASS

Check function length (over 50 lines → FAIL).

### 2D — Phase N

Read active plan from `docs/plans/`. Find Phase N.
Re-verify every task: files exist, routes registered, tests pass.

### 2E — Specific File

Read file. Run: `ruff check [file]`, line count, check error handling, auth deps, async safety.

### 2F — FastAPI-Specific Checks

- Endpoints have `Depends()` auth where needed
- `response_model` present
- Celery tasks have `bind=True`, `max_retries`, `queue`
- No `os.getenv()` — use pydantic Settings
- Service layer separation (no business logic in handlers)

---

## Phase 3 — Report

```
## Redo — [what was redone]

**Action:** [description]
**Scope:** [files/paths]
**Result:** PASS / FAIL / [N passed, M failed]

[Details]
```
