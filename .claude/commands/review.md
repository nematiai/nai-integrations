Do a full production code review on the files I specify.
Report every issue as: | Severity | File | Line | Issue | Fix |

Run first:
  ruff check [files]
Include ruff output at top of report.

Check in this order:

BLOCKING
- File over 200 lines?
- Function over 50 lines?
- Any hardcoded API key or secret (OPENAI_API_KEY, STRIPE_API_KEY, etc.)?

CRITICAL
- Async def missing try/except touching DB or external provider?
- Provider API key read via os.getenv() instead of pydantic Settings?
- Celery task missing bind=True or max_retries?
- DB session not closed after use?

HIGH
- Missing type hints on function signature?
- Silent except swallowing errors without logging?
- Response leaking internal provider error details to client?
- Missing auth dependency on protected route?

PERFORMANCE
- N+1 query pattern (loop with individual DB calls)?
- Synchronous blocking call inside async def?
- Missing Redis cache on repeated provider catalog lookups?

MEDIUM
- Magic strings for provider names not extracted to constants?
- Duplicate routing logic across provider handlers?
- Race condition on concurrent billing updates?

LOW
- Unused imports?
- Dead code or commented-out routes?

ARCHITECTURE
- Business logic inside router handler instead of service layer?
- MongoDB and PostgreSQL writes in same transaction without rollback plan?
- Celery task doing work that belongs in a service?

SECURITY
- Provider keys or user tokens in any log.info/log.debug call?
- Stripe webhook not verifying signature?
- CORS origins set to wildcard in non-local environment?
