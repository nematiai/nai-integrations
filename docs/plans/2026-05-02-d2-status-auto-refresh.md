# Plan — Task #14 (D2): /status auto-refresh standardization

**Created:** 2026-05-02
**Branch:** production
**Baseline at start:** HEAD `bf93e84`, full suite 263 passed
**Decision (locked):** Option C — refactor base `get_connection_status()` to handle auto-refresh.

## What we are building

Today only Google's `/status/` auto-refreshes expired tokens; Box/Dropbox/OneDrive
report `connected=True` for expired-but-active rows without trying to refresh.
This is incorrect behavior: a stale token will fail on the very next API call.

Move the refresh logic into `BaseCloudService.get_connection_status()` so all
4 providers behave identically. Then collapse the inline logic in Google's view.

## Open design forks (need user approval)

### Fork 1 — base response shape

`get_connection_status()` returns 5 keys today. Google's view returns 8 (adds
`expires_at`, `scopes`, `message`). Three options:

- **(A) Extend base to return all 8 keys** for all providers. Schema-out classes
  for Box/Dropbox/OneDrive currently don't declare those fields, so this either
  (i) needs schema updates per provider, or (ii) forces a breaking change to the
  API surface for downstream callers (NAI/Vesper/IndoxHub).
- **(B) Keep base at 5 keys; add `message` only.** Each provider's view passes
  the dict through its `*StatusOut` schema, which silently drops keys the schema
  doesn't declare. Lowest blast radius, but `expires_at` and `scopes` stay
  Google-only — partial standardization.
- **(C) Add `message` to base, leave `expires_at`/`scopes` schema-by-schema.**
  Box/Dropbox/OneDrive schemas already have `expires_at` and `scopes` fields
  declared (verify in pre-edit step) — if so, populate them from the base call
  too. This achieves full surface parity without breaking anything.

**Recommendation: (C)** — verify the 3 schemas first; if they declare those
fields, populate them. Otherwise fall back to (B) and tackle schema parity in
a separate task.

### Fork 2 — behavior on refresh failure

Match Google's existing pattern: return `connected=False, message="Token
refresh failed"` (does NOT mark `is_active=False`; that would force re-auth).
**Recommendation: yes, mirror Google.**

### Fork 3 — Google view simplification

After base handles refresh, the 8 inline lines in `apps/storage/google/views.py:30-36`
become redundant. Should we:
- **(a) Collapse Google's view to the same one-liner the others use.** Keeps
  surface identical but loses the `message` field for Google's "Connected" path
  unless base supplies it.
- **(b) Leave Google's view alone for now.** Smaller diff, slight code
  duplication, no behavioral change.

**Recommendation: (a)** — base supplies `message`, Google view collapses cleanly.

### Fork 4 — existing test semantics

Three existing tests (`test_status_expired_token_still_connected` in box,
dropbox, onedrive) currently assert that an expired-but-active token reports
`connected=True` with no upstream HTTP. **D2 calls these out as wrong** — that's
the whole reason this task exists. After the fix, the test must change. Two
sub-options:

- **(i) Reframe to "expired token auto-refreshes successfully → still
  connected=True".** Mock the provider's refresh endpoint with a success
  response. Same final assertion, different mechanism. Test count stays at 263.
- **(ii) Replace with two tests:** "refresh succeeds → connected=True" AND
  "refresh fails → connected=False with message". Test count goes to 263 + 3 = 266.

**Recommendation: (ii)** — proper coverage of both branches.

## Files to touch

| File | Change | Source |
|------|--------|--------|
| `apps/storage/base/services.py` | `get_connection_status()` adds refresh + `message` key | base |
| `apps/storage/google/views.py` | collapse inline refresh logic (Fork 3a) | Google |
| `apps/storage/box/views.py` | no change (already uses base) — verify | Box |
| `apps/storage/dropbox/views.py` | no change (already uses base) — verify | Dropbox |
| `apps/storage/onedrive/views.py` | no change (already uses base) — verify | OneDrive |
| `apps/storage/{box,dropbox,onedrive}/schemas.py` | possible: confirm/declare `expires_at`, `scopes`, `message` (Fork 1c) | per-provider |
| `tests/integration/mocked/test_box_storage.py` | rewrite TEST 3 + add refresh-fail test (Fork 4ii) | Box |
| `tests/integration/mocked/test_dropbox_storage.py` | same | Dropbox |
| `tests/integration/mocked/test_onedrive_storage.py` | same | OneDrive |
| `tests/integration/mocked/test_google_storage.py` | check existing tests still pass after Google view collapse | Google |

## Phases

1. **Pre-edit confirmations** — read the 4 `*StatusOut` schemas, verify
   `expires_at`/`scopes` field availability. Determine if Fork 1 lands as (C) or
   falls back to (B).
2. **Base refactor** — modify `get_connection_status()` in
   `apps/storage/base/services.py`: add inline `if self.auth.needs_refresh(): if
   not self.refresh_access_token(): return {"connected": False, "message":
   "Token refresh failed", ...}; self._load_auth()`. Add `message` key
   ("Connected" / "Not connected" / "Token refresh failed") to all return
   shapes. Always include `expires_at` and `scopes` keys (None when not
   connected).
3. **Google view collapse** — replace the inline logic with
   `return GoogleStatusOut(**service.get_connection_status())`.
4. **Test rewrites** — for Box/Dropbox/OneDrive, replace TEST 3 with two new
   tests (success + failure paths). Mock each provider's refresh-token endpoint
   per its actual URL (Box: `https://api.box.com/oauth2/token`; Dropbox:
   `https://api.dropboxapi.com/oauth2/token`; OneDrive:
   `https://login.microsoftonline.com/common/oauth2/v2.0/token`).
5. **Verify** — full suite must show **266 passed** (263 baseline − 3 deleted
   tests + 6 new tests = 266). Run targeted tests first.
6. **Commit** — single commit:
   `fix(storage): standardize /status auto-refresh across providers (D2)`

## Acceptance

- Full suite: 266 passed
- All 4 providers' `/status/` endpoints behave identically: connected with
  fresh token → 200 + `connected=True`; connected with expired token + refresh
  succeeds → 200 + `connected=True`; refresh fails → 200 + `connected=False` +
  `message="Token refresh failed"`.
- ruff check (clean for files I touch)

## Hard rules

1. No change to API status code (always 200 from `/status/`).
2. No change to `*StatusOut` schemas unless Fork 1 lands as (C).
3. Refresh failure must NOT flip `is_active=False`.
4. Do NOT push (per user policy).
5. If suite count differs from 266 → STOP, report.

## Rollback

`git revert <commit>` — single-commit refactor.
