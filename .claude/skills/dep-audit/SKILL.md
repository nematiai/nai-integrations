---
name: dep-audit
description: "Dependency health audit for nai-integrations. Checks requirements.txt for outdated, unused, vulnerable, or conflicting packages. Verifies provider SDK compatibility and FastAPI ecosystem coherence. Use when user says dep audit, dependency check, requirements health, outdated packages, or package audit."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Dep Audit — Dependency Health Check

**RULE: Do NOT modify requirements files. Report only.**

---

## Phase 1 — Read Requirements

```bash
cat requirements.txt
```

Also check for extras:
```bash
cat requirements-dev.txt 2>/dev/null
cat pyproject.toml 2>/dev/null | head -60
```

---

## Phase 2 — Outdated Check

```bash
pip list --outdated --format=columns 2>/dev/null | head -40
```

---

## Phase 3 — Unused Dependencies

For each package in requirements.txt, search for imports in `app/`.
FAIL if zero imports found. Skip implicit deps (e.g., psycopg2 used by SQLAlchemy).

---

## Phase 4 — Version Constraints

FAIL:
- No version pin (bare package name)
- `>=` without upper bound
- Git dependency without commit hash

WARN:
- Pinned to exact version (may miss security patches)
- Very old version when newer major exists

---

## Phase 5 — Duplicate Functionality

WARN:
- Multiple HTTP clients (requests + httpx + aiohttp) — verify each has distinct purpose
- Multiple auth libraries
- Multiple serialization approaches

---

## Phase 6 — Security & Risk

```bash
pip audit 2>/dev/null || echo "pip-audit not installed"
```

FAIL: known CVEs, archived packages.
WARN: no recent commits, single maintainer.

---

## Phase 7 — Provider SDK Compatibility

Check AI provider SDKs are compatible with each other:
- openai, anthropic, mistralai, google-genai, dashscope, boto3
- Verify no conflicting transitive dependencies (e.g., pydantic version conflicts)

---

## Phase 8 — Report

```
## Dep Audit — requirements.txt
| # | Package | Version | Status | Issue | Severity |
|---|---------|---------|--------|-------|----------|

Summary: Total N, Outdated X, Unused Y, At risk Z
```
