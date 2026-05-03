# Phase 1.2 Secrets Audit

Branch: `production` (HEAD pre-audit: `819e41c`). Suite baseline: 266 tests.

## Findings

| ID  | Severity | File:Line | Issue | Fix |
|-----|----------|-----------|-------|-----|
| S1  | CRITICAL | `config/settings.py:18` | `SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")` — predictable fallback ships if env var missing. | Require explicit value when `DEBUG=False`; raise `ImproperlyConfigured`. |
| S2  | CRITICAL | `config/settings.py:19` | `DEBUG` defaults to **`true`**. A misconfigured production deploy that forgets the env var runs with debug pages exposed. | Default to `false` (fail-secure). |
| S3  | CRITICAL | `apps/social/base/models.py:75-88`, `apps/storage/base/models.py:71-84` | When `TOKEN_ENCRYPTION_KEY` is unset, `_encrypt` / `_encrypt_token` **silently return plaintext** — credentials persist unencrypted. | Raise `ImproperlyConfigured` on encrypt path when key is missing. (Decrypt path keeps lenient legacy fallback.) |
| S4  | HIGH     | `config/settings.py:94` | `DB_PASSWORD` defaults to `"nemi"` — known credential string. Acceptable for local docker-compose, dangerous if anyone leans on the default in prod. | Track as **D13**; tighten to require explicit value when `DEBUG=False` in a follow-up. |
| S5  | HIGH     | `config/settings.py:101-138` | `LOGGING` config has no redaction filter. Audit shows no current call-site logs token/credential values, but there is no defense if a future log statement does. | Track as **D14**; add a `SensitiveDataFilter` and unit tests. |
| S6  | MEDIUM   | `Dockerfile:18` | `SECRET_KEY=build-placeholder` is passed to `collectstatic`. It is build-only and never reaches CMD, but the literal could mislead readers. | Track as **D15**; rename to `BUILD_ONLY_NOT_A_SECRET` and document. |
| S7  | LOW      | `config/settings.py:20` | `ALLOWED_HOSTS` default is `localhost,127.0.0.1`. Safe — already restrictive. No `*` wildcard. | Verified clean; recommend documenting prod requirement in deploy guide. |

## Critical (fix in this task)

- **S1 + S2** combined commit: tighten `config/settings.py` so production cannot run with default `SECRET_KEY` and cannot accidentally enable `DEBUG`. Add tests under `tests/test_settings_security.py` that import `config.settings` with `DEBUG=False` and no `SECRET_KEY` to assert `ImproperlyConfigured` is raised; assert default `DEBUG=False` when env var unset.
- **S3** separate commit: change `_encrypt` / `_encrypt_token` in `apps/social/base/models.py` and `apps/storage/base/models.py` to raise `ImproperlyConfigured` when key missing. Update existing `tests/test_base.py::test_encrypt_without_key_returns_original` (which currently asserts the insecure behavior) to assert the raise; add equivalent test for the social model.

## High (open as tech debt)

- **D13 — DB_PASSWORD default `"nemi"` (S4):** local-only acceptable; harden when DEBUG=False is set.
- **D14 — LOGGING redaction filter (S5):** add `SensitiveDataFilter` matching `token|password|secret|api_key|client_secret|authorization` and scrubbing values; unit-test against representative log records.

## Medium / Low (open as tech debt)

- **D15 — Dockerfile build placeholder rename (S6):** cosmetic clarity.
- **S7 ALLOWED_HOSTS:** verified clean; no debt entry.

## Verified Clean

- **`.env` is gitignored** (`.gitignore` lines 36-43) and **not tracked** in git history (`git ls-files` confirms only `.env.example`, `.env.test.example`, `.env.test.live.example` are tracked).
- **No real-looking secrets in git history.** `git log --all -p` scan for `SECRET_KEY|TOKEN|PASSWORD` shows only test fixtures and documented placeholders.
- **API key auth (`apps/core/auth/middleware.py:46`):** reads `HTTP_X_API_KEY`, hashes via `AppClient` model, never logs the raw key.
- **Logger call sites (`apps/storage/*/services.py`, `apps/storage/*/tasks.py`):** all `logger.error("... token: %s", e)` patterns log the *exception object*, never the token value. 14 sites verified.
- **Decrypt path** in both `_decrypt` methods: catches `InvalidToken` and falls back to raw value (legacy-compat) and logs at `warning` — acceptable migration aid; no plaintext is *re-stored*.
- **Test settings (`config/test_settings.py:31-34`)** seeds a deterministic test Fernet key and `SECRET_KEY` via `os.environ.setdefault` before importing `config.settings` — keeps unit tests hermetic and unaffected by S1/S3 hardening.
- **`AUTH_PASSWORD_VALIDATORS`** present (default Django four-validator stack).
- **`STATICFILES_STORAGE`** uses `CompressedManifestStaticFilesStorage` (immutable hashed names) — no leak via predictable static URLs.

## Recommendations

1. **Deploy-time check command.** Add `python manage.py check --deploy` to CI for production builds. Catches `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS` defaults — none are currently set explicitly. (Tracked separately as future work; out of scope for #21.)
2. **Token rotation playbook.** `TOKEN_ENCRYPTION_KEY` rotation is undocumented. Decrypt fallback (`_decrypt` returns raw on `InvalidToken`) means a rotated key silently corrupts reads. Document a rotation procedure: dual-key window, re-encrypt migration, then retire old key.
3. **Pre-commit secret scanner.** `gitleaks` or `detect-secrets` in `pre-commit` catches accidental commits before they hit history. No new runtime dependency.
4. **Storage of OAuth client secrets at rest.** Currently injected via env vars and held in `settings`. Acceptable for single-tenant. If multi-tenant rolls out (per AUTH-AND-ROADMAP), move to `AppClient`-scoped encrypted storage.
5. **Sentry / error reporter scrubbing.** None configured today, but when added, ensure default scrubbers cover `*_token`, `*_password`, `*_secret`, `authorization` fields.

## Audit Method

- `git grep -nE "SECRET|TOKEN|PASSWORD|API_KEY|CLIENT_SECRET|PRIVATE_KEY|ENCRYPTION_KEY|FERNET"` — 60+ hits classified env-loaded / hardcoded / test-fixture / doc.
- `git log --all -p -G "SECRET_KEY|password|TOKEN" -- '*.py' '*.env*'` — no real values in history.
- `git ls-files | grep -E '^\.env'` — confirms only `.env*.example` tracked.
- `grep -rnE 'logger\.(info|debug|warning|error).*\b(token|password|secret|credential|api_key)\b' apps/ config/` — 14 hits, all log the exception not the secret.
- Manual review: `config/settings.py`, `config/test_settings.py`, `apps/social/base/models.py`, `apps/storage/base/models.py`, `Dockerfile`, `.gitignore`.
