# NEMI — Auth Architecture & buildmyapp.us Roadmap

## Auth Design Decision

### The Problem
Storage services need a user identity. NEMI is backend-to-backend (no browser users).
Calling apps (NAI, IndoxHub) already authenticated their users.
NEMI needs to know: "which app is calling" + "for which user."

### Solution: Option A — Trusted AppClient + X-User-Id

```
User → NAI (authenticates user) → NEMI (trusts NAI, acts on user_id)
         ↑ session/JWT/OIDC           ↑ API key + X-User-Id header
```

- `X-API-Key` header → authenticates the calling app (AppClient)
- `X-User-Id` header → identifies target user (opaque ID from caller)
- NEMI trusts the calling AppClient fully
- NEMI never sees user passwords, sessions, or tokens

### Composite Key for Storage

NAI user_id=42 and IndoxHub user_id=42 could be different people.
Storage auth uses composite key:

```python
class Meta:
    unique_together = ("app_client", "external_user_id")
```

NEMI stores `external_user_id` as opaque string. Never imports Django User model.

### No OIDC in Phase 1

NEMI is not browser-facing in Phase 1. No OIDC needed.

---

## OAuth Flow for Storage Connections (Phase 1)

```
User clicks "Connect Google Drive" in NAI
  → NAI calls NEMI: GET /api/v1/storage/google/authorize
  → NEMI returns Google OAuth URL (redirect_uri = NAI's callback)
  → User logs into Google in browser
  → Google redirects back to NAI
  → NAI forwards auth code to NEMI: POST /api/v1/storage/google/callback
  → NEMI exchanges code for tokens, stores encrypted
  → NAI shows "Connected!" to user

NEMI never sees the browser. NAI handles the redirect.
```

---

## buildmyapp.us — Product Roadmap

### Phase 1 (now): Internal Use Only
- API key auth only
- Keys created via Django admin (Unfold)
- Users: NAI, IndoxHub, Vesper (your apps only)
- No public signup, no dashboard, no OIDC
- Domain: not needed yet (internal Docker network or private URL)
- REST API endpoints for social, storage, notify

### Phase 2: Developer Dashboard + MCP Server
- Public site at buildmyapp.us
- Developer sign up (email/password + OIDC options)
- Dashboard:
  - Create/manage API keys
  - Configure social platforms (bring your own API keys)
  - Configure storage connections
  - View post logs and analytics
  - Monitor health per adapter
  - **MCP server connection instructions + test playground**
- Session auth for dashboard, API key for programmatic access
- mkdocs documentation at docs.buildmyapp.us
- **MCP server wrapping all Phase 1 + Phase 2 adapters**
- **MCP Server Card at /.well-known/mcp for discovery**
- **MCP transport: Streamable HTTP (remote clients)**
- Hard platform adapters: LinkedIn, Twitter, Facebook, Instagram
- Scheduled posts via Celery Beat
- S3/MinIO storage adapter

### Phase 3: Self-Serve Platform
- Billing: Stripe integration
- Usage metering: per post, per notification, per storage call, **per MCP call**
- Plans: Free tier (limited) → Pro → Enterprise
- Rate limiting per plan tier
- Public API docs with interactive playground
- SDKs:
  - REST client: `pip install nemi-client`
  - **MCP connection: standard MCP client config (no custom SDK needed)**
- Extended platforms: YouTube, TikTok, Threads, Pinterest
- Google Calendar, Outlook Calendar
- Listmonk email marketing
- WebDAV/Nextcloud storage

### Phase 4: CRM + Analytics + Marketplace + Adapter Expansion
- Twenty CRM, EspoCRM integration
- Plausible/Umami/PostHog analytics
- List on RapidAPI or similar
- Third-party adapter plugins
- Community-contributed adapters
- Webhook marketplace (IFTTT-style triggers)
- **Activepieces reference-porting begins here** (see "Parked Decisions" section)

### Phase 5: A2A Protocol + Workflow Engine
- **A2A Agent Card at /.well-known/agent-card.json**
- **A2A server — accept delegated tasks from external AI agents**
- **NEMI becomes discoverable as an autonomous agent, not just a tool**
- Workflow engine ("when X → do Y")
- Webhook triggers and event-driven automation
- Forms: Formbricks, Heyform
- Payments: Stripe, Lago

### Phase 6: Multi-Agent Orchestration + Team
- **Agent SDK integration examples (Claude Agent SDK, OpenAI Agents SDK, LangGraph)**
- **Multi-agent orchestration via A2A**
- Multi-user workspace
- Approval workflows
- AI content generation per platform
- Communication: Chatwoot, Matrix
- Project management: Plane, Leantime

---

## Three Access Layers (Phase 2+)

| Layer | Who | Method | Protects |
|---|---|---|---|
| Dashboard auth | Human developers in browser | Session / OIDC | /dashboard/*, /admin/* |
| REST API auth | Developer's apps (machines) | X-API-Key header | /api/v1/* |
| MCP auth | AI agents (Claude Desktop, Cursor, etc.) | API key in MCP config | MCP tool calls |

Developer signs up → gets session → creates API key in dashboard → uses API key in their code OR in MCP client config.

### MCP Client Configuration Example (Phase 2+)

```json
{
  "mcpServers": {
    "nemi": {
      "url": "https://buildmyapp.us/mcp",
      "headers": {
        "X-API-Key": "nemi_sk_...",
        "X-User-Id": "user_42"
      }
    }
  }
}
```

Any MCP-compatible client (Claude Desktop, Cursor, Windsurf, custom agents) connects with this config. No custom SDK required.

---

## Pricing Model (Phase 3+)

| Plan | Social posts/mo | Notifications/mo | Storage ops/mo | MCP calls/mo | Price |
|---|---|---|---|---|---|
| Free | 100 | 500 | 100 | 500 | $0 |
| Pro | 5,000 | 10,000 | 5,000 | 25,000 | $29/mo |
| Business | 50,000 | 100,000 | 50,000 | 250,000 | $99/mo |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited | Custom |

---

## Protocol Architecture

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

---

## License

BSL 1.1 (Business Source License)
- Free to self-host and use
- Cannot resell as competing hosted service
- Commercial license available for resellers
- MCP server and A2A agent included in BSL — same terms

---

## Parked Decisions

Decisions deferred to later phases. Do NOT start work on these before their phase gate opens.

### Activepieces Reference-Porting (Parked → Phase 4)

**Source:** github.com/activepieces/activepieces (MIT, Community Edition, `packages/pieces/community/*`)

**Decision:** Reference-port TypeScript pieces to Python adapters inside `nai-integrations`, agent-driven, customer-demand-driven. NOT a fork, NOT a sidecar deploy, NOT a wholesale import.

**Approach (Option D — strategic reference-port):**
- Agent reads Activepieces TypeScript piece + vendor docs → produces spec
- Agent generates Python adapter matching the canonical `nai-integrations` pattern
- Agent writes mocked unit tests + integration test skeleton
- Human reviews against canonical pattern before merge
- Attribution: include Activepieces MIT copyright notice in each ported adapter file

**Rejected alternatives:**
- Option B (sidecar deploy of Activepieces as a service) — adds Node.js runtime, violates decoupled-services principle, wrong tool for the job
- Option C (fork their monorepo, strip to pieces only) — inherits V8 sandbox + shared package complexity, fork maintenance burden

**Prerequisites before first port (hard gates):**
1. Phase 1 blockers closed — NEMI integration tests + production docker-compose
2. Phase 2 complete — AI proxy in NAI serving Postiz
3. Phase 3 complete — MCP exposure of existing adapters
4. Canonical adapter pattern documented in `nai-integrations`
5. Golden reference adapter identified (cleanest existing adapter, becomes the template)
6. Customer demand signal — real paying customer asks for a specific piece

**What is explicitly NOT allowed until Phase 4 opens:**
- No parallel branch porting
- No speculative adapter scaffolds
- No agent prompts for piece porting
- Research-only activity permitted (priority list, vendor notes) — no code

**Revisit trigger:** Phase 3 MCP exposure marked complete AND at least one paying customer requests a specific Activepieces-covered integration not already in `nai-integrations`.