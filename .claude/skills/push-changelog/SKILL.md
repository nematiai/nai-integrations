---
name: push-changelog
description: "Push a changelog entry to the nai-integrations backend API. Use when user says push changelog, publish changelog, send changelog, create changelog entry, or log a change to the server."
disable-model-invocation: true
allowed-tools: Bash, Read, Grep
---

# Push Changelog — Send Entry to Backend API

You push changelog entries to the nai-integrations backend via a secured POST endpoint.

**RULE: Never hardcode the API key. Always read from `.env` or `.env.local`.**
**RULE: Always confirm the entry details with the user before pushing.**
**RULE: Write content as a non-technical summary — describe what changed for end users, not how the code works. Avoid mentioning files, functions, classes, or implementation details. Focus on what the user can now do or what improved.**
**RULE: Always read `docs/changelog.md` first to build the entry from session work — do not rely on memory.**
**RULE: Always use today's date via `$(date +%Y-%m-%d)` — never hardcode a date.**
**RULE: Always check for duplicate titles before pushing — skip if already exists.**
**RULE: Always prefix the title with "nai-integrations — ".**
**RULE: Always set `app_name` to "nai-integrations".**
**RULE: Always read `app_version` from `pyproject.toml` (version field) — never guess.**

---

## Workflow

### Step 1 — Read session changes
```bash
cat docs/changelog.md
```
Use the latest entries to build the changelog content.

### Step 2 — Check for duplicates
```bash
source .env && curl -s \
  "https://api.nai-integrations.com/v1/changelogs/" \
  -H "Authorization: Bearer $CHANGELOG_API_KEY" \
  | python -c "
import sys, json
entries = json.load(sys.stdin)
for e in entries:
    print(f'  id={e[\"id\"]}  {e[\"date\"]}  {e[\"title\"]}')
"
```
If a title already exists, **SKIP** — do not push a duplicate.

### Step 3 — Confirm with user
Show the draft entry (title, category, content) and ask for approval before pushing.

### Step 4 — Push the entry
See **How to Push** below.

### Step 5 — Verify
Confirm the entry is live on production.

---

## Endpoint

```
POST /api/v1/changelogs/
Host: api.nai-integrations.com (production) or localhost:9050 (local)
Authorization: Bearer <CHANGELOG_API_KEY>
Content-Type: application/json
```

## Authentication

- Bearer token via `Authorization` header
- Key is stored as `CHANGELOG_API_KEY` in `.env` and `.env.local`
- Rate limited: 5 failed auth attempts = 5 minute IP lockout
- Timing-safe comparison (hmac.compare_digest)

To read the key:
```bash
source .env && echo "$CHANGELOG_API_KEY"
```

---

## Request Body (JSON)

```json
{
  "title": "string (required, max 255 chars)",
  "date": "YYYY-MM-DD (required — use $(date +%Y-%m-%d))",
  "category": "string (required, see valid values below)",
  "content": "string (required, markdown formatted, non-technical)",
  "is_published": true,
  "app_name": "nai-integrations",
  "app_version": "1.0.0",
  "platform": "all",
  "update_available": false,
  "download_url": null
}
```

### Valid Categories

| Value           | Description                     |
|-----------------|---------------------------------|
| `New Feature`   | Brand new functionality         |
| `Improvement`   | Enhancement to existing feature |
| `Bug Fix`       | Bug fix                         |
| `Security`      | Security patch or update        |
| `Announcement`  | General announcement            |

### Field Rules

- `title` — Required. Max 255 characters. Always prefix with "nai-integrations — ".
- `date` — Required. Always use today's date: `$(date +%Y-%m-%d)`.
- `category` — Required. Pick the best fit: `New Feature`, `Improvement`, `Bug Fix`, `Security`, or `Announcement`. Do not default everything to one category — match the nature of the change.
- `content` — Required. Non-technical, user-facing summary. Supports markdown.
- `is_published` — Always set to `true` to publish immediately.
- `app_name` — Always "nai-integrations".
- `app_version` — Semver string (e.g. `"1.0.0"`). Read from `pyproject.toml` version field.
- `platform` — `"all"`, `"web"`, or `"api"`. Default `"all"`.
- `update_available` — Boolean. Set `true` when a new version is released. Default `false`.
- `download_url` — Optional URL. Set `null` if not applicable.

### Valid Platforms

| Value | Description |
|-------|-------------|
| `all` | All platforms (default) |
| `web` | Web interface only |
| `api` | API only |

---

## Response

### 201 Created
```json
{
  "id": 42,
  "title": "nai-integrations — New LLM provider support",
  "category": "New Feature",
  "content": "Added support for Claude and GPT-4...",
  "is_published": true
}
```

### 400 Bad Request
```json
{
  "message": "Invalid category. Must be one of: New Feature, Improvement, Bug Fix, Security, Announcement"
}
```

### 401 Unauthorized
Returned when API key is missing, invalid, or IP is locked out.

### 500 Internal Server Error
```json
{
  "message": "Failed to create changelog"
}
```

---

## How to Push

### Write JSON to temp file, then push with curl

```bash
# Step 1: Get today's date and version
TODAY=$(date +%Y-%m-%d)
VERSION=$(grep '^version =' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Step 2: Write the entry to a temp file
cat > /tmp/changelog_entry.json << JSONEOF
{
  "title": "nai-integrations — Your title here",
  "date": "$TODAY",
  "category": "New Feature",
  "content": "Non-technical summary of what changed for end users.",
  "is_published": true,
  "app_name": "nai-integrations",
  "app_version": "$VERSION",
  "platform": "all",
  "update_available": false,
  "download_url": null
}
JSONEOF

# Step 3: Check for duplicate
source .env && EXISTING=$(curl -s \
  "https://api.nai-integrations.com/api/v1/changelogs/" \
  -H "Authorization: Bearer $CHANGELOG_API_KEY" \
  | python -c "
import sys, json
title = 'nai-integrations — Your title here'
entries = json.load(sys.stdin)
print(sum(1 for e in entries if e['title'] == title))
")

if [ "$EXISTING" -gt 0 ]; then
  echo "SKIPPED — duplicate title already exists"
  rm -f /tmp/changelog_entry.json
else
  # Step 4: Push it
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://api.nai-integrations.com/api/v1/changelogs/" \
    -H "Authorization: Bearer $CHANGELOG_API_KEY" \
    -H "Content-Type: application/json" \
    -d @/tmp/changelog_entry.json)

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | sed '$d')

  if [ "$HTTP_CODE" = "201" ]; then
    echo "CREATED — changelog pushed successfully"
    echo "$BODY" | grep -E '"id"|"title"'
  else
    echo "FAILED (HTTP $HTTP_CODE)"
    echo "$BODY" | head -5
  fi

  rm -f /tmp/changelog_entry.json
fi
```

---

## Verify — Confirm Entry is Live

After pushing, ALWAYS verify the entry is visible on production:

```bash
source .env && curl -s \
  "https://api.nai-integrations.com/api/v1/changelogs/" \
  -H "Authorization: Bearer $CHANGELOG_API_KEY" \
  | python -c "
import sys, json
entries = json.load(sys.stdin)
for e in entries:
    print(f'  id={e[\"id\"]}  published={e[\"is_published\"]}  {e[\"date\"]}  {e[\"title\"]}')
"
```

---

## Local Testing (Docker)

```bash
source .env.local && curl -s -X POST \
  "http://localhost:9050/api/v1/changelogs/" \
  -H "Authorization: Bearer $CHANGELOG_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Test\",\"date\":\"$(date +%Y-%m-%d)\",\"category\":\"New Feature\",\"content\":\"Test entry\",\"is_published\":true,\"app_name\":\"nai-integrations\"}"
```

---

## Env Var Setup

The key must be in BOTH files for local + production:

**`.env`** — used by scripts/agents:
```
CHANGELOG_API_KEY=<your-key>
```

**`.env.local`** — used by Docker:
```
######################################################################
# CHANGELOG INGEST
######################################################################
CHANGELOG_API_KEY=<your-key>
```

**Production** — set via CI/CD secrets or server env.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | Key missing or wrong | Check `CHANGELOG_API_KEY` in env |
| 401 after repeated attempts | IP locked out (5 fails) | Wait 5 minutes or clear Redis key `changelog_auth_fail:<ip>` |
| 400 Invalid category | Typo in category value | Use exact values from the table above |
| 500 Internal Server Error | DB error | Check Docker logs: `docker logs nai-integrations-dev` |
| Connection refused on localhost | Container not running | Rebuild and restart Docker containers |</content>
<parameter name="filePath">d:\NAI_Project\BACKENDS\nai-integrations\.claude\skills\push-changelog\SKILL.md
