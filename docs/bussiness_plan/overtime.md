Here's the full picture of what NEMI can integrate over time — organized by category:

| Category | Service | Open Source | GitHub | What NEMI adapter does |
|---|---|---|---|---|
| **Social (Phase 1-3)** | | | | |
| | Telegram, Reddit, Discord, Bluesky, Mastodon | N/A | N/A | Post from accounts |
| | Twitter/X, LinkedIn, Facebook, Instagram | N/A | N/A | Post from accounts |
| | YouTube, TikTok, Threads, Pinterest | N/A | N/A | Post from accounts |
| **Storage (EXISTS)** | | | | |
| | Google Drive, Dropbox, OneDrive, Box | N/A | N/A | File sync/upload |
| | S3/MinIO | ✅ MinIO | github.com/minio/minio | Object storage |
| **Notifications (EXISTS)** | | | | |
| | 90+ channels via Apprise | ✅ | github.com/caronc/apprise | Send notifications |
| **Calendar & Scheduling** | | | | |
| | Google Calendar | N/A | Google API | Create/read events, reminders |
| | Outlook Calendar | N/A | Microsoft Graph API | Same |
| | Cal.com | ✅ | github.com/calcom/cal.com | Scheduling links, booking |
| **Email Marketing** | | | | |
| | Listmonk | ✅ | github.com/knadh/listmonk | Newsletter, campaigns, subscribers |
| | Mautic | ✅ | github.com/mautic/mautic | Marketing automation |
| | BillionMail | ✅ | github.com/Billionmail/BillionMail | Self-hosted mail server |
| **CRM** | | | | |
| | Twenty CRM | ✅ | github.com/twentyhq/twenty | Contacts, deals, pipeline |
| | EspoCRM | ✅ | github.com/espocrm/espocrm | Lightweight CRM |
| **Project Management** | | | | |
| | Plane | ✅ | github.com/makeplane/plane | Issues, sprints, roadmaps |
| | Leantime | ✅ | github.com/Leantime/leantime | Project management |
| **Analytics** | | | | |
| | Plausible | ✅ | github.com/plausible/analytics | Website analytics |
| | Umami | ✅ | github.com/umami-software/umami | Website analytics |
| | PostHog | ✅ | github.com/PostHog/posthog | Product analytics |
| **Forms & Surveys** | | | | |
| | Formbricks | ✅ | github.com/formbricks/formbricks | Surveys, feedback |
| | Heyform | ✅ | github.com/heyform/heyform | Form builder |
| **Payments** | | | | |
| | Stripe | N/A | Stripe API | Billing, subscriptions |
| | Lago | ✅ | github.com/getlago/lago | Usage-based billing |
| **AI/LLM** | | | | |
| | OpenAI, Anthropic, etc. | N/A | APIs | AI proxy (you already have this in NAI) |
| **Communication** | | | | |
| | Matrix/Element | ✅ | github.com/element-hq/element-web | Team chat |
| | Chatwoot | ✅ | github.com/chatwoot/chatwoot | Customer support chat |

**What this means for NEMI:** Each of these becomes a potential adapter category. The same pattern you're building now (base adapter → platform adapter → API endpoint) works for all of them.

**Phased integration roadmap:**

| Phase | Adapters |
|---|---|
| **Phase 1 (now)** | Social (5) + Storage (4) + Notify (Apprise) |
| **Phase 2** | Social (4 more) + Scheduling |
| **Phase 3** | Calendar (Google, Outlook) + Email marketing (Listmonk) |
| **Phase 4** | CRM (Twenty) + Analytics (Plausible/Umami) |
| **Phase 5** | Payments (Stripe/Lago) + Forms (Formbricks) |
| **Phase 6** | AI proxy + Communication (Chatwoot) |

**But don't plan beyond Phase 1 right now.** The adapter pattern handles all of these the same way. Build the pattern right in Phase 1, everything else is just adding new adapters.

Save this as reference and move on to building. Want me to add this to the roadmap doc?