---
name: test-suite
description: "Auto-generate and run tests for FastAPI backend. Finds untested code, generates pytest tests, runs them inside Docker, and reports coverage. Use when user says test suite, generate tests, auto test, test everything, write tests, or coverage check."
disable-model-invocation: true
---

# Test Suite — Generate & Verify Tests

Find untested code, generate tests, run them, prove the package works.

**RULE: Generate tests in `tests/` directory following existing test patterns.**
**RULE: ALL test commands run inside Docker: `docker exec nai-integrations-dev pytest`**
**RULE: Do NOT modify production code. Only create/modify test files.**

---

## Phase 1 — Discover What Exists

!`find app/ -name 'test_*.py' -o -name '*_test.py' | sort`
!`find tests/ -name 'test_*.py' 2>/dev/null | sort`
!`docker exec nai-integrations-dev pytest --collect-only -q 2>/dev/null | tail -5`

Build a map of what's tested and what's not.

---

## Phase 2 — Find Untested Code

If $ARGUMENTS provided, scope to those apps/modules only.
Otherwise, scan all of `app/`.

For each module, check:
- `app/api/` — are endpoints tested?
- `app/services/` — are service functions tested?
- `app/models/` — are model methods tested?
- `app/tasks/` — are Celery tasks tested?
- `app/utils/` — are utility functions tested?
- `app/core/` — are core functions tested?

Build a gap table:

| Module | Functions | Tested | Gap |
|--------|-----------|--------|-----|

---

## Phase 3 — Prioritize

Rank untested code by risk:

1. **CRITICAL** — Auth endpoints, payment logic, provider routing, API key management
2. **HIGH** — API endpoints with business logic, Celery tasks, external provider calls
3. **MEDIUM** — Service layer functions, model methods, utility functions
4. **LOW** — Middleware, config, management scripts

Generate tests starting from CRITICAL, working down.

---

## Phase 4 — Generate Tests

For each untested module, create test files following these patterns:

**API endpoint tests:**
```python
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
class TestEndpointName:
    async def test_authenticated_access(self, client: AsyncClient):
        """Test endpoint requires auth."""

    async def test_success_response(self, client: AsyncClient):
        """Test happy path returns expected schema."""

    async def test_invalid_input(self, client: AsyncClient):
        """Test validation errors return 422."""

    async def test_not_found(self, client: AsyncClient):
        """Test missing resource returns 404."""
```

**Service tests:**
```python
import pytest

@pytest.mark.asyncio
class TestServiceName:
    async def test_happy_path(self):
        """Test expected behavior."""

    async def test_edge_case(self):
        """Test boundary conditions."""

    async def test_error_handling(self):
        """Test failure scenarios."""
```

**Model tests:**
```python
import pytest

@pytest.mark.asyncio
class TestModelName:
    async def test_create(self):
        """Test model creation with valid data."""

    async def test_str_representation(self):
        """Test __str__ returns expected format."""

    async def test_constraints(self):
        """Test unique/validation constraints."""
```

**Celery task tests:**
```python
import pytest

@pytest.mark.asyncio
class TestTaskName:
    async def test_task_success(self):
        """Test task completes successfully."""

    async def test_task_retry_on_failure(self):
        """Test task retries on transient error."""

    async def test_task_timeout(self):
        """Test task respects time limit."""
```

Rules:
- Use `pytest.fixture` for shared setup
- Use `pytest.mark.asyncio` for async tests
- Use `unittest.mock.patch` for external APIs — never call real APIs
- Test file naming: `test_<module>.py`
- One test class per module/endpoint
- Each test method tests ONE behavior
- Use FastAPI TestClient or httpx AsyncClient for API tests

---

## Phase 5 — Run Tests

```bash
docker exec nai-integrations-dev pytest --tb=short -q
```

If specific tests:
```bash
docker exec nai-integrations-dev pytest tests/test_<module>.py --tb=short -v
```

If tests fail:
1. Read the traceback
2. Fix the TEST (not the production code)
3. Re-run until green
4. If test failure reveals a real bug → report it, do NOT fix production code

---

## Phase 6 — Coverage Check

```bash
docker exec nai-integrations-dev pytest --cov=app --cov-report=term-missing --tb=short -q 2>/dev/null | tail -30
```

If `pytest-cov` not available:
```bash
docker exec nai-integrations-dev pip show pytest-cov 2>/dev/null || echo "pytest-cov not installed — skip coverage"
```

---

## Phase 7 — Report

```
## Test Suite Report — nai-integrations

| # | Module | Tests Added | Status | Coverage |
|---|--------|-------------|--------|----------|

**Summary:**
- Tests before: N
- Tests added: X
- Tests total: N + X
- All passing: YES / NO
- Coverage: Y%

### Untested Critical Code (remaining gaps)
| Module | Risk | Reason |
|--------|------|--------|

### Test Failures (if any)
| Test | Error | Fix Applied |
|------|-------|-------------|

**Verdict:**
- **READY** — all tests pass, critical code covered
- **NOT READY** — N failures, M critical gaps remain
```

Write issues for any real bugs found to `docs/issues.md`.</content>
<parameter name="filePath">d:\NAI_Project\BACKENDS\nai-integrations\.claude\skills\test-suite\SKILL.md
