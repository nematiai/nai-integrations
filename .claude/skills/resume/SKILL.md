---
name: resume
description: "Resume a paused task by rebuilding nai-integrations project context. Reads active plan, git history, container status, issues, and CLAUDE.md. Use when user says resume, continue, where was I, pick up, or what's next."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Resume — Rebuild Context & Continue

**RULE: Do NOT start working on the task. Report status only.**
**RULE: Read every source — do not guess from filenames alone.**

---

## Phase 1 — Load Project Context

Read CLAUDE.md for: stack, architecture, conventions, build commands.

Stack: Python 3.11 / FastAPI / PostgreSQL 17 / MongoDB 6 / Redis 7 / Celery
Entry: main.py → app.core.celery_app
Lint: ruff check . && ruff format --check .
Test: pytest tests/ -v
Local: docker/local/ → port 9050

---

## Phase 2 — Container Status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "indox|mongo|redis|postgres|nginx"
```

Flag if any container is down or restarting.

---

## Phase 3 — Find Active Plan

```bash
ls -t docs/plans/*.md 2>/dev/null | head -5
```

Read most recent plan. Parse: task title, phases, completed `[x]` vs incomplete `[ ]`.

If $ARGUMENTS provided, use that to locate specific plan.
If no plan found: "No plan file found. Using git history only."

---

## Phase 4 — Recent Git Activity

```bash
git log --oneline -15
git diff --stat HEAD~5 2>/dev/null || git diff --stat
git status --short
```

Extract: last commits, uncommitted changes, untracked files.

---

## Phase 5 — Open Issues

```bash
cat docs/issues.md 2>/dev/null
```

Scan recently changed files for `TODO|FIXME|HACK|XXX`.

---

## Phase 6 — Report

```
## Resume — nai-integrations

**Stack:** Python 3.11 / FastAPI / PostgreSQL / MongoDB / Redis / Celery
**Plan:** [filename] — [task title]
**Containers:** [all up / X down]

### Progress
| Phase | Status | Detail |
|-------|--------|--------|

### Recent Activity
Last commits: ...
Uncommitted changes: N files

### Open Items
- [TODOs/issues found]

### Next Action
**[Phase N, Task name]**
[One sentence: what to do next]
Files to touch: `path/to/file1`, `path/to/file2`
```
