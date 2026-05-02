# NEMI — Master Decision Log
All decisions made during the architecture planning conversation.
---
## 1. What is NEMI?
| Question | Answer |
|---|---|
| What | Nemati Integration Hub — unified integration service for all Nemati apps |
| Domain | buildmyapp.us |
| License | BSL 1.1 (Business Source License) |
| Model | Open source core + API key gated access |
| Repo | github.com/NematiAI/nai-integrations (evolving from pip package) |
---
## 2. Core Architecture Decisions
| # | Decision | Why |
|---|---|---|
| 1 | Standalone Django service, NOT pip package | Other apps call via HTTP, not import |
| 2 | Separate from NAI backend | Decoupled — NEMI down ≠ NAI down |
| 3 | Users bring their own API keys per platform | No central OAuth burden |
| 4 | Apprise for notifications (90+ channels) | Already built, don't rebuild |
| 5 | Moved notification_system from NAI to NEMI | Already has models, tasks, management commands |
| 6 | No n8n, no Postiz | Build own adapter pattern in Django, no Node.js |
| 7 | MCP layer in Phase 2 | Thin wrapper over REST adapters — free distribution via AI IDEs (Claude Desktop, Cursor, Windsurf) |
| 8 | No more pip publish | NEMI is deployed service, not library |
| 9 | API keys per app | NAI gets key, IndoxHub gets key, rate-limited |
| 10 | Django Unfold admin | Already in nai-integrations, carry over |
| 11 | Social adapters mimic Postiz pattern | Adapter per platform, build ourselves |
| 12 | mkdocs documentation | Build at end of Phase 1, not leave for later |
| 13 | MCP in Phase 2, not Phase 5 | Thin wrapper over REST endpoints, every MCP-compatible client becomes a distribution channel |
| 14 | A2A protocol in Phase 5 | NEMI is a tool provider first, autonomous agent second. A2A needed only when NEMI acts independently |
| 15 | Model-agnostic agent support | Don't lock to one Agent SDK — expose via MCP so any SDK (Claude, OpenAI, LangGraph, ADK) can call NEMI |
| 16 | No Agent SDK dependency in NEMI core | NEMI serves MCP tools, consuming apps choose their own agent framework |
---
## 3. Auth Architecture
| Question | Answer |
|---|---|
| Auth model | Option A — Trusted AppClient + X-User-Id header |
| How it works | X-API-Key authenticates calling app, X-User-Id identifies target user |
| Trust model | NEMI trusts calling app fully |
| Storage user identity | Composite key: (app_client, external_user_id) |
| BaseCloudAuth change | Refactor from `user = OneToOneField(User)` to `app_client + external_user_id` |
| OIDC needed? | No for Phase 1. Yes for Phase 2 (buildmyapp.us developer dashboard) |
| Phase 1 auth | API key only, keys created via Django admin |
| Phase 2 auth | Add signup + dashboard + OIDC for external developers |
---
## 4. What We Investigated
### MCP (Model Context Protocol)
| Question | Answer |
|---|---|
| What is it | Open standard for AI agents to connect to tools (agent-to-tool communication) |
| Current status (2026) | v2.1 spec, production-ready, adopted by OpenAI, Google, Microsoft, 150+ orgs |
| Governance | Linux Foundation (Agentic AI Foundation), co-founded by Anthropic, Block, OpenAI |
| Transport | Streamable HTTP (remote), STDIO (local) |
| Key 2026 features | Server Cards (.well-known discovery), stateless horizontal scaling, enterprise auth |
| Use for NEMI? | Yes — Phase 2. Wrap REST adapters as MCP tools |
| Why Phase 2 | Marginal cost is 2-3 days per adapter category on top of REST. Immediate distribution via AI IDEs |
### A2A (Agent2Agent Protocol)
| Question | Answer |
|---|---|
| What is it | Open standard for AI agent-to-agent communication (complements MCP) |
| Current status (2026) | v1.0 spec, 150+ organizations, production deployments across industries |
| Governance | Linux Foundation, originally by Google |
| Key concepts | Agent Cards (discovery), Tasks (work units), Messages (communication) |
| Relationship to MCP | MCP = agent-to-tool, A2A = agent-to-agent. Complementary, not competing |
| Use for NEMI? | Yes — Phase 5. When NEMI has workflow engine and acts as autonomous agent |
| Why Phase 5 | NEMI is a tool provider now, not an autonomous agent. A2A solves a problem we don't have yet |
### Agent SDKs / Frameworks (2026 landscape)
| Framework | Lock-in | Production Readiness | Best For |
|---|---|---|---|
| LangGraph | None | Highest | Stateful workflows, graph-based orchestration |
| OpenAI Agents SDK | OpenAI only | High | Fast prototyping on OpenAI models |
| Claude Agent SDK | Claude only | High | Safety-critical, tool-use chains, computer use |
| CrewAI | None | Medium | Multi-agent teams, role-based |
| Google ADK | Gemini-first | Early | A2A protocol, multimodal, hierarchical agents |
| **NEMI decision** | **None** | **N/A** | **NEMI exposes MCP tools — consuming apps choose their own SDK** |
### n8n
| Question | Answer |
|---|---|
| What is it | Open source workflow automation (like Zapier/Make) |
| Free? | Community edition is free, self-hosted |
| Use it? | No — adds Node.js dependency, we build our own in Django |
### Postiz
| Question | Answer |
|---|---|
| What is it | Open source social media scheduler |
| License | AGPL-3.0 |
| Use it? | No — has UI we don't want, Node.js stack |
| What we take | Mimic their adapter pattern, build in Django |
### Ayrshare / Outstand / PostEverywhere
| Question | Answer |
|---|---|
| What are they | Paid unified social media posting APIs |
| Use them? | No — we build our own to avoid monthly cost |
| Why not | $30+/mo, adds dependency on third party |
### Apprise
| Question | Answer |
|---|---|
| What is it | Python library for 90+ notification channels |
| Use it? | Yes — `pip install apprise==1.9.7` |
| Already in NAI? | Yes — full notification_system Django app exists |
| Moved to NEMI? | Yes — apps/notify/ |
---
## 5. Social Media Platform Feasibility
### Phase 1 — No approval needed, free
| Platform | Cost | Approval | Dev Time | Credentials |
|---|---|---|---|---|
| Telegram | Free | None | 1 hr | bot_token, chat_id |
| Reddit | Free | Instant OAuth | 2 hrs | client_id, client_secret, username, password, subreddit |
| Discord | Free | Create bot | 1 hr | webhook_url |
| Bluesky | Free | App password | 2 hrs | handle, app_password |
| Mastodon | Free | OAuth instant | 2 hrs | instance_url, access_token |
### Phase 2 — Needs approval, may cost
| Platform | Cost | Approval | Dev Time |
|---|---|---|---|
| LinkedIn | Free | App review needed | 1-2 days |
| X/Twitter | ~$5/mo+ (pay-per-use) | Dev account review | 1 day |
| Facebook | Free | Meta App Review (weeks) | 2 days |
| Instagram | Free | Same as Facebook | 2 days |
### Phase 3 — Extended
| Platform | Cost | Approval | Dev Time |
|---|---|---|---|
| YouTube | Free | Google consent review | 1-2 days |
| TikTok | Free | Content API approval | 1-2 days |
| Threads | Free | Meta API | 1 day |
| Pinterest | Free | App approval | 1 day |
---
## 6. Storage Platform Feasibility
### Existing (migrated from nai-integrations)
| Platform | Status |
|---|---|
| Google Drive | ✅ EXISTS |
| Dropbox | ✅ EXISTS |
| OneDrive | ✅ EXISTS |
| Box | ✅ EXISTS |
### Future storage adapters
| Platform | Difficulty | Notes |
|---|---|---|
| S3/MinIO | Easy | One adapter covers Backblaze B2, Wasabi, DO Spaces, Cloudflare R2 |
| WebDAV | Easy | Covers Nextcloud, ownCloud |
| FTP/SFTP | Easy | Legacy but widely used |
| Azure Blob | Medium | Reuse OneDrive Azure OAuth |
| Google Cloud Storage | Medium | Reuse Google OAuth |
---
## 7. Notification System
| Question | Answer |
|---|---|
| Solution | Apprise (pip install apprise==1.9.7) |
| Existing code | Moved from NAI apps/notification_system/ → NEMI apps/notify/ |
| Dependencies removed | WebsiteSetting, Newsletter, Subscriber, UserNotificationPreference |
| Imports fixed | apps.notification_system.* → apps.notify.* |
| Email handling | Apprise handles email (mailto://) — no separate email app needed |
---
## 8. Future Integration Categories
| Category | Examples | Phase |
|---|---|---|
| Social posting | Telegram, Reddit, Discord, Twitter, LinkedIn, etc. | 1-3 |
| Cloud storage | Google Drive, Dropbox, OneDrive, Box, S3, WebDAV | 1-3 |
| Notifications | 90+ via Apprise | 1 (done) |
| MCP server | Expose all adapters as MCP tools for AI agents | 2 |
| Calendar | Google Calendar, Outlook Calendar, Cal.com | 3+ |
| Email marketing | Listmonk, Mautic, BillionMail | 3+ |
| CRM | Twenty CRM, EspoCRM | 4+ |
| Analytics | Plausible, Umami, PostHog | 4+ |
| A2A agent | Agent Card discovery, autonomous workflows | 5 |
| Forms | Formbricks, Heyform | 5+ |
| Payments | Stripe, Lago | 5+ |
| Communication | Chatwoot, Matrix | 6+ |
| AI proxy | OpenAI, Anthropic (already in NAI) | 6+ |
| Agent SDK orchestration | Multi-agent via Claude/OpenAI/LangGraph SDKs | 6+ |
| Project mgmt | Plane, Leantime | 6+ |
---
## 9. Phase Plan
### Phase 1: Core + Easy Platforms (now)
| Step | Task | Status |
|---|---|---|
| 1 | Scaffold Django project | ✅ DONE |
| 2 | Build core/auth (AppClient + API key) | ✅ DONE |
| - | Fix notify app (move from NAI, fix imports) | ✅ DONE |
| 3 | Move storage code + refactor BaseCloudAuth | ⬜ IN PROGRESS |
| 4 | Build social base + models | ⬜ |
| 5 | Build 5 social adapters (TG, Reddit, Discord, BS, Mastodon) | ⬜ |
| 6 | Build social API endpoints | ⬜ |
| 7 | Build notify API endpoints | ⬜ |
| 8 | Health check endpoint | ⬜ |
| 9 | Docker Compose | ⬜ |
| 10 | Tests + mkdocs documentation | ⬜ |
### Phase 2: Hard Platforms + Scheduling + MCP
- LinkedIn, Twitter, Facebook, Instagram adapters
- Scheduled posts (Celery Beat)
- S3/MinIO storage adapter
- **MCP server wrapping all Phase 1 + Phase 2 adapters**
- **MCP Server Card at .well-known for discovery**
- Developer dashboard at buildmyapp.us
### Phase 3: Extended Platforms + Calendar
- YouTube, TikTok, Threads, Pinterest
- Google Calendar, Outlook Calendar
- Listmonk email marketing
- WebDAV/Nextcloud storage
### Phase 4: CRM + Analytics
- Twenty CRM integration
- Plausible/Umami analytics
- Stripe/Lago billing
### Phase 5: A2A + Workflows
- **A2A Agent Card — NEMI discoverable by external agents**
- **A2A server — accept delegated tasks from other agents**
- Workflow engine ("when X → do Y")
- Webhook triggers
### Phase 6: Team + Advanced + Agent Orchestration
- Multi-user workspace
- Approval workflows
- AI content generation per platform
- **Agent SDK integration examples (Claude, OpenAI, LangGraph)**
- **Multi-agent orchestration via A2A**
---
## 10. buildmyapp.us Product Roadmap
| Phase | What | Auth |
|---|---|---|
| Phase 1 | Internal use only (NAI, IndoxHub, Vesper) | API key via admin |
| Phase 2 | Developer dashboard, public signup, MCP server registry | Session/OIDC + API key |
| Phase 3 | Self-serve platform, billing | Stripe, usage metering |
| Phase 4 | Marketplace | Third-party plugins |
### Pricing Model (Phase 3+)
| Plan | Social posts/mo | Notifications/mo | Storage ops/mo | MCP calls/mo | Price |
|---|---|---|---|---|---|
| Free | 100 | 500 | 100 | 500 | $0 |
| Pro | 5,000 | 10,000 | 5,000 | 25,000 | $29/mo |
| Business | 50,000 | 100,000 | 50,000 | 250,000 | $99/mo |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited | Custom |
---
## 11. Tech Stack
| Component | Technology |
|---|---|
| Framework | Django 4.2+ / Django Ninja |
| Admin | Django Unfold |
| Task queue | Celery + Redis |
| Database | PostgreSQL |
| Notifications | Apprise 1.9.7 |
| HTTP client | httpx |
| Token encryption | Fernet (cryptography) |
| Auth | API key (X-API-Key header) |
| MCP server | Python MCP SDK (@modelcontextprotocol/python-sdk) |
| Protocol | MCP v2.1 (Streamable HTTP transport) |
| Deployment | Docker Compose on Hetzner |
| Documentation | mkdocs-material |
| Linting | ruff |
| Testing | pytest + pytest-django |
---
## 12. Code Standards
- Max 50 lines per function, 200 lines per file
- Zero ruff warnings
- Type hints on all function signatures
- try/except on external API calls
- Never expose tokens in logs
- Celery tasks: bind=True, max_retries, explicit queue
- All env vars via Django settings, no os.getenv() in business logic
- Each adapter in its own folder with adapter.py + tests.py
- GitHub issue for every finding — never skip
---
## 13. Protocol Architecture
### How NEMI serves different clients
```
┌─────────────────────────────────────────────────┐
│                 NEMI (Django)                    │
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│  │  Social    │  │  Storage  │  │  Notify     │ │
│  │  Adapters  │  │  Adapters │  │  (Apprise)  │ │
│  └─────┬─────┘  └─────┬─────┘  └──────┬──────┘ │
│        │              │               │         │
│  ┌─────┴──────────────┴───────────────┴──────┐  │
│  │          Unified Adapter Layer             │  │
│  └─────┬──────────────┬───────────────┬──────┘  │
│        │              │               │         │
│  ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴──────┐  │
│  │ REST API  │  │ MCP Server│  │ A2A Server │  │
│  │ (Phase 1) │  │ (Phase 2) │  │ (Phase 5)  │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬──────┘  │
└────────┼──────────────┼───────────────┼─────────┘
         │              │               │
    ┌────┴────┐   ┌─────┴──────┐  ┌────┴─────────┐
    │ NAI     │   │Claude Desktop│ │External     │
    │ IndoxHub│   │Cursor       │ │AI Agents    │
    │ Vesper  │   │Any MCP client│ │(via A2A)   │
    └─────────┘   └────────────┘  └──────────────┘
```
### Protocol comparison (why we use both)
| | MCP | A2A |
|---|---|---|
| Purpose | Agent calls NEMI as a tool | Agent collaborates with NEMI as a peer |
| Direction | Client → NEMI | Agent ↔ NEMI Agent |
| Discovery | Server Card (.well-known) | Agent Card (.well-known/agent-card.json) |
| NEMI role | Tool provider | Autonomous agent |
| When needed | Phase 2 (immediate value) | Phase 5 (when NEMI has workflows) |
| Example | "Post this to Telegram via NEMI" | "NEMI, negotiate with content agent, then publish" |
---
## 14. Files Produced
| File | Purpose |
|---|---|
| NEMI-PROJECT-CONTEXT.md | Agent follows for standards |
| NEMI-PHASE1-SPEC.md | 10-step execution plan |
| NEMI-TRACKING.md | Discussion decisions (original) |
| NEMI-AUTH-AND-ROADMAP.md | Auth architecture + buildmyapp.us roadmap |
| NEMI-MASTER-DECISIONS.md | This file — complete decision log |