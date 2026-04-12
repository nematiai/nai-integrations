```
╔══════════════════════════════════════════════════════════════════╗
║              SKILL USAGE WORKFLOW — nai-integrations                     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   PRIORITY GUIDE                                                 ║
║   ──────────────                                                 ║
║   P0 = every push       (mandatory)                              ║
║   P1 = every session     (recommended)                           ║
║   P2 = as needed         (during dev)                            ║
║   P3 = per deploy        (milestone gate)                        ║
║   P4 = monthly/quarterly (health check)                          ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   START SESSION                                                  ║
║   │                                                              ║
║   ▼                                                              ║
║   /resume ─────── P1 · every session start                       ║
║   │  Rebuilds context, finds next action                         ║
║   │  WHEN: returning after break, switching repos                ║
║   │                                                              ║
║   ▼                                                              ║
║   Write Plan ──── docs/plans/YYYY-MM-DD-task.md                  ║
║   │                                                              ║
║   ▼                                                              ║
║   ┌─────────────────────────────────┐                            ║
║   │   IMPLEMENT (code, test, run)   │                            ║
║   └──────────────┬──────────────────┘                            ║
║                  │                                               ║
║                  ▼                                               ║
║   /redo ─────── P1 · after every fix                             ║
║   │  Re-runs ruff, pytest, health check                          ║
║   │  WHEN: after fixing a bug, after each code change            ║
║   │                                                              ║
║   ▼                                                              ║
║   ┌──────────────────────────────────────────────────┐           ║
║   │            QUALITY GATES (use by need)            │           ║
║   │                                                    │           ║
║   │  /review ────── P2 · when you want a second eye    │           ║
║   │     WHEN: wrote 1-3 files, want quick review       │           ║
║   │     NOT: every commit                              │           ║
║   │                                                    │           ║
║   │  /validate ──── P2 · when plan is done             │           ║
║   │     WHEN: finished implementing a plan             │           ║
║   │     NOT: mid-implementation                        │           ║
║   │                                                    │           ║
║   │  /perf-audit ── P4 · per major feature             │           ║
║   │     WHEN: N+1 queries, async anti-patterns,        │           ║
║   │           MongoDB indexing, caching issues         │           ║
║   │     NOT: every commit                              │           ║
║   │                                                    │           ║
║   │  /api-audit ─── P4 · after adding endpoints        │           ║
║   │     WHEN: new/changed endpoints, schema updates    │           ║
║   │     NOT: every commit                              │           ║
║   │                                                    │           ║
║   └──────────────────────┬───────────────────────────┘           ║
║                          │                                       ║
║                          ▼                                       ║
║   /pre-commit ────── P0 · EVERY push (mandatory)                 ║
║   │  Secrets, auth, async safety, Celery, pydantic Settings      ║
║   │  WHEN: RIGHT BEFORE git push — no exceptions                 ║
║   │  THIS IS THE ONLY MANDATORY GATE                             ║
║   │                                                              ║
║   ├── APPROVED → git push                                        ║
║   └── BLOCKED → fix → /redo → /pre-commit again                 ║
║   │                                                              ║
║   ▼                                                              ║
║   /github-issue ── auto + manual issue tracking                  ║
║   │  Issues auto-opened when skills find errors                  ║
║   │  Dedup check prevents duplicates                             ║
║   │  Manual: /github-issue open|close|reopen|check               ║
║                          │                                       ║
║                          ▼                                       ║
║   ┌──────────────────────────────────────────────────┐           ║
║   │            RELEASE PIPELINE (milestone only)      │           ║
║   │                                                    │           ║
║   │  /dep-audit ────── P4 · monthly or before deploy   │           ║
║   │     WHEN: monthly health check, pre-release        │           ║
║   │                                                    │           ║
║   │  /full-app-audit ── P3 · quarterly or major release│           ║
║   │     WHEN: before v1.0, v2.0, major milestones      │           ║
║   │     NOT: every feature — too heavy                 │           ║
║   │                                                    │           ║
║   │  /release-check ── P3 · before production deploy   │           ║
║   │     WHEN: RIGHT BEFORE production deployment       │           ║
║   │                                                    │           ║
║   └──────────────────────┬───────────────────────────┘           ║
║                          ▼                                       ║
║                  DEPLOY TO PRODUCTION                            ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   QUICK REFERENCE                                                ║
║   ───────────────                                                ║
║                                                                  ║
║   MANDATORY FLOW (every session):                                ║
║     /resume → code → /redo → /review → /validate                 ║
║     → /pre-commit → push                                         ║
║     (or run /daily to chain all 5 automatically)                 ║
║                                                                  ║
║   BEFORE SHIP (every release):                                   ║
║     /release-check → push to store/deploy                        ║
║                                                                  ║
║   ON DEMAND:                                                     ║
║     /perf-audit · /api-audit · /dep-audit · /full-app-audit      ║
║                                                                  ║
║   ISSUES:                                                        ║
║     Auto-open when any skill finds errors                        ║
║     /github-issue check · close · reopen                         ║
║                                                                  ║
║   CHANGELOG:                                                     ║
║     Every change logged to docs/changelog.md automatically       ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   ALL SKILLS + COMMANDS (11)                                     ║
║   ───────────────────────────────────────────────                ║
║   /resume  P1  rebuild context, find next action                 ║
║   /redo    P1  re-run ruff, pytest, health check                 ║
║   /review  P2  quick targeted file review                        ║
║   /validate P2 verify plan vs implementation                     ║
║   /pre-commit P0 MANDATORY gate before git push                  ║
║   /perf-audit P4 async, query & MongoDB performance              ║
║   /api-audit  P4 endpoint & schema validation                    ║
║   /dep-audit  P4 requirements.txt health check                   ║
║   /full-app-audit P3 deep audit of entire backend                ║
║   /release-check  P3 production deployment readiness             ║
║   /github-issue  --  open/close/reopen/check GitHub issues       ║
║                                                                  ║
║   LINT: ruff check . && ruff format --check .                    ║
║   TEST: pytest tests/ -v                                         ║
║   BUILD: cd docker/local && docker-compose up -d --build         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   MANDATORY CHECKLIST                                            ║
║   ───────────────────                                            ║
║                                                                  ║
║   ┌──────────────────┬───────────────────┬────────────────────┐  ║
║   │ Skill            │ When              │ Required?          │  ║
║   ├──────────────────┼───────────────────┼────────────────────┤  ║
║   │ /resume          │ Every session     │ YES — mandatory    │  ║
║   │ /redo            │ Every code change │ YES — mandatory    │  ║
║   │ /review          │ Before push       │ YES — mandatory    │  ║
║   │ /pre-commit      │ Before push       │ YES — mandatory    │  ║
║   │ /validate        │ Plan complete     │ YES — mandatory    │  ║
║   │ /release-check   │ Before ship       │ YES — mandatory    │  ║
║   │ /perf-audit      │ When needed       │ No — on demand     │  ║
║   │ /api-audit       │ When needed       │ No — on demand     │  ║
║   │ /dep-audit       │ When needed       │ No — on demand     │  ║
║   │ /full-app-audit  │ When needed       │ No — on demand     │  ║
║   └──────────────────┴───────────────────┴────────────────────┘  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```
