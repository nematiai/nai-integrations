# Phase 1.2 Rate Limiting (#20)

Branch: `production` (HEAD pre-task: `edc4205`). Adds endpoint-level rate limiting on top of the existing per-AppClient quota in `apps/core/auth/middleware.py`.

## Library

`django-ratelimit==4.1.0` (jsocol). Pinned in `requirements/base.in` and re-locked into `base.txt`/`dev.txt`/`production.txt`. No other new dependencies — Django ≥ 4 ships a built-in Redis cache backend, and the project already pins `redis>=5.0`.

Sanity-checked against `django-smart-ratelimit` (newer, sliding window, async backends). Per the task constraint we stayed on `django-ratelimit`. If concurrency or sliding-window semantics become a need, a switch would be a one-shot change because both share the same `@decorator` shape.

## Endpoint Classification

| Class            | Count | Rate setting        | Key       | Examples |
|------------------|-------|---------------------|-----------|----------|
| public-anon POST |  2    | `RATE_LIMIT_ANON`   | IP        | `POST /v1/auth/register`, `GET /v1/notify/schemas/` (auth=None) |
| authenticated    | 25    | `RATE_LIMIT_USER`   | AppClient | All `/v1/social/*`, `/v1/storage/*` (status / authorize / disconnect / contents), `/v1/notify/channels/*`, `/v1/notify/templates/*`, `/v1/notify/logs/*`, `/v1/notify/send/`, `/v1/auth/rotate-key` |
| oauth-callback   |  4    | `RATE_LIMIT_OAUTH`  | IP        | `POST /v1/storage/{box,dropbox,google,onedrive}/callback/` |
| health (exempt)  |  1    | —                   | —         | `GET /v1/health/` |
| internal (exempt)|  1    | —                   | —         | `/api/v1/docs/`, `/openapi.json` |

Total endpoints touched by `#20`: **31** (across `apps/core/auth/views.py`, `apps/social/views_*.py`, `apps/storage/{box,dropbox,google,onedrive}/views.py`, `apps/notify/api/router*.py`).

## Defaults

```text
RATE_LIMIT_ANON  = 30/m   # protects /auth/register and the anon /notify/schemas
RATE_LIMIT_USER  = 120/m  # 2 rps sustained for authenticated apps
RATE_LIMIT_OAUTH = 10/m   # strict: callback endpoints are post-redirect, single-use
```

Reasoning:
- **`30/m` anon** — `/auth/register` is the only write surface that doesn't require an API key. 30/min per IP is generous for a real signup flow and instantly blocks naive bot loops.
- **`120/m` user** — Sized for normal NAI/IndoxHub/Vesper traffic patterns (a few requests per UI action, plus occasional bulk operations). Layered with the per-AppClient `rate_limit_per_minute` quota in `ApiKeyAuthMiddleware`, which can be tuned per customer.
- **`10/m` oauth** — Each OAuth callback corresponds to a single browser redirect; legitimate callers never need more than ~1/s in burst.

## Override in production

All three are read from environment variables. Set in `.env.prod` or your secrets manager:

```bash
RATE_LIMIT_ANON=60/m
RATE_LIMIT_USER=300/m
RATE_LIMIT_OAUTH=20/m
```

Format follows `django-ratelimit`: `N/s`, `N/m`, `N/h`, `N/d`. Values are read **at request time** (the helper passes a callable to `@ratelimit`), so setting changes via `override_settings` in tests or live config rollouts take effect without re-decorating views.

## 429 Response Contract

```json
{"error": "rate_limited", "retry_after": 60}
```

- HTTP status: `429`
- `Retry-After` header: matches `retry_after` (in seconds)
- Logged at `WARNING` with `scope`, `path`, `ip`. Implemented once in `apps/core/base/rate_limit.py::_build_429`; views never duplicate this shape.

## Cache Backend

`config/settings.py` configures Django's built-in Redis cache (`django.core.cache.backends.redis.RedisCache`) pointed at `REDIS_URL`. `RATELIMIT_USE_CACHE = "default"` makes `django-ratelimit` share that cache.

`config/test_settings.py` overrides to `LocMemCache` so tests are hermetic — no Redis needed in CI, and the autouse `_flush_cache` fixture in `tests/integration/mocked/test_rate_limits.py` resets state between cases.

## Internal Bypass (Nemati ↔ NEMI)

Today there is **no** dedicated bypass for internal docker-network or Nemati.ai service-to-service traffic. All internal traffic flows through the same `RATE_LIMIT_USER` bucket as external apps. This is acceptable because:

- Internal callers register their own `AppClient` with a generous `rate_limit_per_minute`.
- The django-ratelimit limit is applied per-AppClient (key = AppClient id), so two internal services with separate AppClients have separate buckets.

If a noisy internal job (e.g. bulk migration) trips the user bucket, options without code change:
1. Raise `RATE_LIMIT_USER` for the deploy.
2. Issue the internal caller a high-quota `AppClient`.

A formal bypass (e.g. allowlist by source IP CIDR or shared secret) is **future work** — log as a follow-up if it ever bites.

## Layered with the Existing Middleware

`apps/core/auth/middleware.py` already enforces per-AppClient `rate_limit_per_minute` using an in-process bucket (per worker). #20 layers a Redis-backed limit on top:

| Layer | Where               | Scope                           | Purpose |
|-------|---------------------|---------------------------------|---------|
| 1     | Middleware          | per AppClient, per worker       | Customer quota enforcement |
| 2     | `@rate_limit_*`     | per IP / per AppClient, cluster | Endpoint abuse protection |

The middleware limit is unchanged. Migrating it to Redis-backed (so it works across workers) is intentionally out of scope for #20 and tracked separately.

## Known Limitations

1. **Fixed window, not sliding** — `django-ratelimit` uses fixed time windows. A burst at the boundary of two windows can briefly exceed the nominal rate. Acceptable for abuse protection at these magnitudes.
2. **`Retry-After` is the window length, not the precise time-to-reset** — we report 60s for `*/m`, etc. `django-ratelimit` does not expose remaining-window seconds.
3. **Redis required in production** — LocMemCache is per-worker only; using it in prod silently degrades to no protection across workers. Compose already runs Redis; the `CACHES` setting is not configurable per-env.
4. **No shared rate budget across endpoints** — each endpoint has its own bucket. An attacker hitting many distinct endpoints under one AppClient can spend `RATE_LIMIT_USER` on each. The middleware (Layer 1) catches this.

## Files Touched

- `requirements/base.in`, `requirements/{base,dev,production}.txt` — pinned `django-ratelimit==4.1.0`.
- `config/settings.py` — `CACHES`, `RATELIMIT_USE_CACHE`, `RATE_LIMIT_*` env reads.
- `config/test_settings.py` — `LocMemCache` override + same `RATE_LIMIT_*` constants.
- `apps/core/base/rate_limit.py` — `rate_limit_anon`, `rate_limit_user`, `rate_limit_oauth` decorators + `_build_429` helper.
- 11 view files across `apps/core/auth/`, `apps/social/`, `apps/storage/`, `apps/notify/` — one decorator per endpoint.
- `.env.example`, `.env.test.example` — added `RATE_LIMIT_*` lines.
- `tests/integration/mocked/test_rate_limits.py` — 6 tests covering anon/user/oauth/health/shape/header.

## Verification

```text
pytest                                          → 277 passed (was 271)
pytest tests/integration/mocked/test_rate_limits.py -v  → 6 passed
```

No new dependency beyond `django-ratelimit`. No real `time.sleep` in tests. Health endpoint untouched and verified at 50 consecutive requests.
