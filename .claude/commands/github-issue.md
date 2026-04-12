---
description: "Open, close, reopen, check, list GitHub issues — or start full fix workflow on an issue for nai-integrations"
allowed-tools: Bash, Read, Grep, Glob
---
# GitHub Issue Management — nai-integrations
**Repo:** `osllmai/backend_Indox_Router_Server`

## Usage
- `/github-issue NUMBER` — start full fix workflow on issue
- `/github-issue open "TITLE" "BODY" label1,label2`
- `/github-issue close NUMBER` · `/github-issue reopen NUMBER`
- `/github-issue check` · `/github-issue list`

---
## Start Working on Issue (`/github-issue NUMBER`)

### Phase 0 — Fetch Issue & Branch Setup
```bash
source .env && curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues/NUMBER"
```
1. Parse title, body, labels from response
2. Create branch: `git checkout -b fix/NUMBER-short-description`
3. Rename session: `/rename fix-NUMBER`

### Phase 1 — Read Context (NO code changes)
1. Read `CLAUDE.md` and `.claude/rules/workflow.md`
2. Read all files referenced in issue body
3. Read related files in `app/` that will need changes

### Phase 2 — Write Plan — STOP, wait for approval
Create `docs/plans/YYYY-MM-DD-issue-NUMBER.md`:
```
# Plan: Fix #NUMBER — ISSUE_TITLE
## Status: PLANNING
## Issue: https://github.com/osllmai/backend_Indox_Router_Server/issues/NUMBER
## Phases:
- [ ] Phase 1: [description + expected outcome]
- [ ] Phase 2: [description + expected outcome]
## Deliverables:
- Files to modify: [list] · Files to create: [list] · Tests: [list]
## Rollback:
- [how to revert if something goes wrong]
## Current Phase: Planning
## Last Updated: YYYY-MM-DD HH:MM
```
**STOP — Do NOT write code. Wait for user to say "approved" or "go".**

### Phase 3 — Execute (after approval, phase by phase)
For EACH phase in the plan:
1. Implement the phase (max 200 lines/file, 50 lines/function)
2. Run checks inside Docker:
```bash
docker exec nai-backend-dev ruff check .
docker exec nai-backend-dev ruff format --check .
docker exec nai-backend-dev pytest tests/ -v
```
3. Update plan: mark `[x]`, update Status + Last Updated
4. Write findings to `docs/issues.md`
5. **STOP — report to user before next phase**

Gates: `app/api/` → health check | `celery_app` → worker starts | DB model → migration exists | new key → pydantic Settings

### Phase 4 — Quality Gates
Run ALL — every one must pass: `/redo` `/review` `/validate` `/pre-commit`

### Phase 5 — Commit, Push & PR
1. Commit: `git commit -m "fix(#NUMBER): [description]"`
2. Push: `git push -u origin fix/NUMBER-short-description`
3. Create PR targeting `development`:
```bash
source .env && cat > /tmp/gh_pr.json << 'JSONEOF'
{
  "title": "fix(#NUMBER): description",
  "body": "Fixes #NUMBER\n\n## Changes\n- ...\n\n## Testing\n- ruff clean\n- pytest passing\n- 200 line limit respected",
  "head": "fix/NUMBER-short-description",
  "base": "development"
}
JSONEOF
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/pulls" \
  -d @/tmp/gh_pr.json)
rm -f /tmp/gh_pr.json
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY_OUT=$(echo "$RESPONSE" | sed '$d')
if [ "$HTTP_CODE" = "201" ]; then
  echo "PR CREATED"; echo "$BODY_OUT" | grep -E '"number"|"html_url"'
else
  echo "PR FAILED (HTTP $HTTP_CODE)"; echo "$BODY_OUT" | head -5
fi
```
**Do NOT close the issue. Ask user: "PR created. Close issue #NUMBER?"**

---
## Open an Issue
```bash
source .env && TITLE="TITLE" && \
EXISTING=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues?state=all&per_page=100" \
  | grep -c "\"title\": \"$TITLE\"") && \
if [ "$EXISTING" -gt 0 ]; then
  echo "SKIPPED — issue already exists: $TITLE"
else
  cat > /tmp/gh_issue.json << 'JSONEOF'
{"title":"TITLE","body":"BODY","labels":["LABEL1","LABEL2"]}
JSONEOF
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues" \
    -d @/tmp/gh_issue.json)
  rm -f /tmp/gh_issue.json
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY_OUT=$(echo "$RESPONSE" | sed '$d')
  if [ "$HTTP_CODE" = "201" ]; then
    echo "CREATED"; echo "$BODY_OUT" | grep -E '"number"|"html_url"|"title"'
  else
    echo "FAILED (HTTP $HTTP_CODE)"; echo "$BODY_OUT" | head -5
  fi
fi
```

## Close an Issue — **NEVER close without user approval.**
```bash
source .env && RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues/NUMBER" \
  -d '{"state":"closed"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY_OUT=$(echo "$RESPONSE" | sed '$d')
if [ "$HTTP_CODE" = "200" ]; then echo "CLOSED — issue #NUMBER"
else echo "FAILED (HTTP $HTTP_CODE)"; echo "$BODY_OUT" | head -5; fi
```

## Reopen an Issue
```bash
source .env && RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues/NUMBER" \
  -d '{"state":"open"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY_OUT=$(echo "$RESPONSE" | sed '$d')
if [ "$HTTP_CODE" = "200" ]; then echo "REOPENED — issue #NUMBER"
else echo "FAILED (HTTP $HTTP_CODE)"; echo "$BODY_OUT" | head -5; fi
```

## Check Recent Issues
```bash
source .env && curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues?state=all&per_page=5" \
  | grep -E '"number"|"title"|"state"'
```

## List Open Issues
```bash
source .env && curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues?state=open&per_page=50" \
  | grep -E '"number"|"title"|"labels"'
```

---
## Rules (NON-NEGOTIABLE)
- Do NOT skip phases — Do NOT write code before plan is approved
- Do NOT commit without user approval — Do NOT close issues without user saying "close it"
- ALL lint/test commands: `docker exec nai-backend-dev`
- Max 200 lines per file — Every finding opens a GitHub issue first

## Labels & Priority
Labels: `bug` `enhancement` `security` `performance` `tech-debt`
Priority prefix in title: `[P0]` `[P1]` `[P2]` `[P3]`
