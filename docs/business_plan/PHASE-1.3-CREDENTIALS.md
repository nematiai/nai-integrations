# Phase 1.3 — Live Integration Test Credentials

Source: `apps/social/registry.py`, `apps/social/*/adapter.py`, `apps/storage/*/services.py`, `config/settings.py`. UNKNOWN = not evident from code, needs human input.

## Summary
- Total services: **24** (20 social + 4 storage) — matches handoff.
- Have credentials: **0 real values; template exists for 6/20 social + 4/4 storage** (see "Existing Test Fixtures" below).
- Need credentials: **22** functional adapters.
- Blocked / placeholder: **2** (skool, mewe — no public write API).

Storage providers source `*_CLIENT_ID / *_CLIENT_SECRET / *_REDIRECT_URI` from `config/settings.py` env. Social adapters take per-account credentials at runtime from `SocialAccount` rows (no env vars) — only the OAuth app client IDs/secrets that gate user authorization need provisioning, and several social platforms (Telegram bot, Discord/Slack webhooks, Bluesky app password, X user keys, Mastodon user token) skip OAuth entirely and use credentials the end-user produces directly.

## Social Platforms

| # | Service | Auth | Required credential fields | Scopes / restrictions | Sandbox | Status | Notes |
|---|---------|------|----------------------------|-----------------------|---------|--------|-------|
| 1 | telegram | Bot token | `bot_token`, `chat_id` | UNKNOWN (Bot API) | Yes (test bot) | NEED | Anyone can create bot via @BotFather. |
| 2 | discord | Webhook | `webhook_url` (must start `https://discord.com/api/webhooks/`) | UNKNOWN | Yes (test server) | NEED | No app review; webhook from server settings. |
| 3 | slack | Webhook | `webhook_url` (`https://hooks.slack.com/`) | UNKNOWN | Yes (test workspace) | NEED | Incoming Webhooks app required. |
| 4 | reddit | OAuth2 password grant | `client_id`, `client_secret`, `username`, `password`, `subreddit` | UNKNOWN (`submit` implied) | Yes (test sub) | NEED | Script-app type at reddit.com/prefs/apps. |
| 5 | bluesky | App password | `handle`, `app_password` | n/a (AT Protocol) | Yes | NEED | App password from bsky.app settings. |
| 6 | mastodon | OAuth2 token | `instance_url`, `access_token` | UNKNOWN (write:statuses implied) | Yes (any instance) | NEED | Self-issued via app registration. |
| 7 | x (Twitter) | OAuth 1.0a | `api_key`, `api_secret`, `access_token`, `access_token_secret` | UNKNOWN (`tweet.write` + media upload) | Limited (paid Basic+) | **BLOCKED** | Free tier write-restricted; needs paid X API. |
| 8 | linkedin | OAuth2 bearer | `access_token`, `person_urn` | UNKNOWN (`w_member_social`) | No | **BLOCKED** | App review for `w_member_social` scope. |
| 9 | linkedin_page | OAuth2 bearer | `access_token`, `organization_urn` | UNKNOWN (`w_organization_social`) | No | **BLOCKED** | Requires LinkedIn company page admin + scope review. |
| 10 | pinterest | OAuth2 bearer | `access_token`, `board_id` | UNKNOWN (`pins:write`, `boards:read`) | Yes (Trial Access) | NEED | Standard Access requires app review. |
| 11 | facebook | Graph API token | `access_token`, `page_id` | UNKNOWN (`pages_manage_posts`, `pages_read_engagement`) | Yes (dev mode) | **BLOCKED** | Live mode needs Meta App Review + Business Verification. |
| 12 | instagram | Graph API token | `access_token`, `instagram_account_id` | UNKNOWN (`instagram_content_publish` + FB scopes) | Yes (dev mode) | **BLOCKED** | Requires Instagram Business account linked to FB Page + App Review. |
| 13 | threads | Graph API token | `access_token`, `threads_user_id` | UNKNOWN (`threads_basic`, `threads_content_publish`) | Yes (dev mode) | NEED | Threads API GA but tied to Meta app. |
| 14 | youtube | OAuth2 bearer | `access_token`, `channel_id` | UNKNOWN (`youtube.upload`) | Yes (test project) | NEED | Quota: 1600 units/upload; default quota 10k/day. |
| 15 | tiktok | OAuth2 bearer | `access_token` | UNKNOWN (`video.publish`) | Yes (sandbox) | **BLOCKED** | Content Posting API requires audit for production. |
| 16 | google_business | OAuth2 bearer | `access_token`, `account_id`, `location_id` | UNKNOWN (`business.manage`) | No | **BLOCKED** | Requires verified GBP location (real business). |
| 17 | dribbble | OAuth2 bearer | `access_token` | UNKNOWN (`upload`, `public`) | UNKNOWN | NEED | Dribbble API v2 — registered apps only. |
| 18 | skool | API key (stub) | `api_key`, `community_id` | n/a (no public write API) | No | **PLACEHOLDER** | Adapter raises `APIError("not publicly available")`. |
| 19 | whop | API key | `api_key`, `forum_id` | UNKNOWN | UNKNOWN | NEED | Bearer auth at api.whop.com/api/v1. |
| 20 | mewe | OAuth2 (stub) | `access_token` | n/a (no public API) | No | **PLACEHOLDER** | Adapter raises `APIError("not publicly available")`. |

## Storage Providers

| # | Service | Auth | Env vars | Default scopes | Sandbox | Status | Notes |
|---|---------|------|----------|----------------|---------|--------|-------|
| 1 | box | OAuth2 | `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, `BOX_REDIRECT_URI` | UNKNOWN (no `DEFAULT_SCOPES` in code — uses app config defaults) | Yes (dev token) | NEED | Custom App in Box Developer Console. |
| 2 | dropbox | OAuth2 | `DROPBOX_CLIENT_ID`, `DROPBOX_CLIENT_SECRET`, `DROPBOX_REDIRECT_URI` | UNKNOWN (no `DEFAULT_SCOPES` in code) | Yes (dev) | NEED | Scoped App at dropbox.com/developers. |
| 3 | google (Drive) | OAuth2 | `GOOGLE_OAUTH2_CLIENT_ID`, `GOOGLE_OAUTH2_CLIENT_SECRET`, `GOOGLE_DRIVE_REDIRECT_URI` | `drive.readonly`, `drive.file`, `userinfo.email`, `userinfo.profile` | Yes (test users) | **BLOCKED** | `drive.file` is non-sensitive; broader scopes need Google verification + CASA security review for production. |
| 4 | onedrive | OAuth2 | `ONEDRIVE_CLIENT_ID`, `ONEDRIVE_CLIENT_SECRET`, `ONEDRIVE_REDIRECT_URI` | `offline_access Files.Read Files.Read.All User.Read` | Yes (personal Microsoft acct) | NEED | Azure AD app registration; multi-tenant for external users. |
| 0 | **(global prereq)** | Fernet key | `TOKEN_ENCRYPTION_KEY` | n/a | n/a | **HARD PREREQ** | `config/settings.py:174`. Encrypts ALL persisted credentials (social `SocialAccount` + storage `*Auth` rows). If unset, every live test fails at decrypt before the adapter is even called. |

## Blockers

Items below need a paid tier, app review, business-account chain, or production verification before live tests can run.

- **x (Twitter):** Free API tier blocks tweet creation; need paid Basic ($200/mo) at minimum. Mitigation: temporarily test against paid dev account or skip live posting in CI.
- **linkedin / linkedin_page:** `w_member_social` and `w_organization_social` scopes require LinkedIn Marketing Developer Platform / Community Management API access (manual approval, weeks). Mitigation: file applications now, gate Phase 1.3 on tokens received.
- **facebook / instagram / threads:** Meta App Review + Business Verification chain. Instagram additionally requires a Business/Creator IG account linked to a FB Page. Mitigation: run in Meta dev mode against test users — sufficient for integration tests but not "live posts to public timeline."
- **tiktok:** Content Posting API requires app audit; sandbox accepts test users only with private posts. Mitigation: keep tests in sandbox, mark prod live test as deferred.
- **google_business:** Requires a verified physical business location. Mitigation: NEMI/Nemati office location if available, else mark deferred.
- **google (Drive):** `drive.readonly` is sensitive scope — needs Google OAuth verification + annual CASA assessment for >100 users. Mitigation: stay in test-user mode (cap 100) for Phase 1.3.

## Cleanup Hooks Required

For each functional adapter, Phase 1.3 must implement a teardown step:

- telegram, discord, slack — delete test message via `deleteMessage` / webhook DELETE (UNKNOWN if all webhooks support delete; may require manual purge of test channel).
- reddit — delete submission via `/api/del?id={fullname}`.
- bluesky — `com.atproto.repo.deleteRecord`.
- mastodon — `DELETE /api/v1/statuses/{id}`.
- x — `DELETE /2/tweets/:id`.
- linkedin / linkedin_page — `DELETE /v2/ugcPosts/{urn}`.
- pinterest — `DELETE /v5/pins/{pin_id}`.
- facebook / instagram / threads — `DELETE /{post_id}` via Graph API.
- youtube — `DELETE /youtube/v3/videos?id=...` (otherwise quota-eats one upload per run).
- tiktok — UNKNOWN: Content Posting API has no documented programmatic delete; sandbox auto-cleans, prod requires manual.
- google_business — `DELETE /v4/{localPost name}`.
- dribbble — `DELETE /v2/shots/{id}`.
- whop — UNKNOWN delete endpoint for forum_posts; may need manual cleanup.
- skool, mewe — no posts created, nothing to clean.
- box / dropbox / google / onedrive — Phase 1.3 storage tests should upload to a dedicated `nemi-test/` prefix and call provider delete on teardown; also revoke OAuth token via existing `/disconnect` endpoint.

Token revocation (all OAuth services) on suite end: call existing `apps/storage/*/services.py` revoke flow for storage; for social, drop the `SocialAccount` row (revocation against the platform is provider-specific and not currently implemented in adapters).

## Existing Test Fixtures

A live-test credential template already exists in the repo — the doc's "have credentials: 0" applies to populated values, not to scaffolding.

- **Template:** `.env.test.live.example` (3271 B, repo root). Copy to `.env.test.live` (gitignored) and fill with sandbox creds.
- **Loader:** `config/test_settings.py` reads it automatically when `NEMI_TEST_ENV=live`.
- **Coverage today:** 6 social platforms (telegram, reddit, discord, bluesky, mastodon, +1) + all 4 storage providers. Includes `TOKEN_ENCRYPTION_KEY` and `NEMI_TEST_APP_NAME` / `NEMI_TEST_USER_ID` fixtures.
- **Gap:** 14 social platforms (slack, x, linkedin, linkedin_page, pinterest, facebook, instagram, threads, youtube, tiktok, google_business, dribbble, skool, whop, mewe — actually 15, depending on the +1 already covered) have **no entries**. Phase 1.3 must extend the template before it can run end-to-end across the full registry.
- CI: same variable names should be injected from GitHub Actions secrets / Vault — code is source-agnostic.

## Open Questions

1. Which Phase 1.3 services do we actually intend to live-test vs. mock? (Blocked items above are candidates to defer.)
2. Do we have an existing X paid API tier, Meta verified business, or Google Cloud project under buildmyapp.us? Status of each unknown from repo.
3. Where do we store production OAuth client IDs/secrets — Vault, GitHub Actions secrets, `.env.prod`? Settings.py only reads env vars; provisioning path not documented.
4. Confirm scopes per adapter against the platform docs — adapter source uses bearer tokens but does not record the OAuth scopes that were requested when those tokens were issued. All "scopes" cells above are inferred from endpoint usage and marked UNKNOWN where not explicit.
5. For skool and mewe placeholders: keep registry slot in Phase 1.3 tests (validate-only), or skip entirely?
6. Cleanup ownership: do we want a generic `cleanup()` method on `BaseSocialAdapter` before Phase 1.3 starts, or per-test inline deletes?
7. **D12: discord adapter expects `webhook_url`, but `.env.test.live.example` defines `DISCORD_BOT_TOKEN` + `DISCORD_TEST_CHANNEL_ID`. Adapter or fixture is wrong. Resolve before Phase 1.3 starts.**
