## Quality Gates

nai-integrations-specific checks after changes:
- Any change to app/api/ → verify /api/v1/health still passes
- Any change to app/core/celery_app → verify worker starts cleanly
- Any DB model change → check alembic migration exists
- Any new provider key → verify it is sourced from pydantic Settings only
- Run: ruff check . && pytest tests/ -v after significant changes
- Write findings to docs/issues.md (never print)

Issues format (docs/issues.md only — never print):
`- [ ] description — file:line — priority: high/med/low`

Session hygiene:
- /rename [task-slug] at session start
- /compact at 50% context
- /clear when switching to a new task

## File Size Limits (NON-NEGOTIABLE)
- **Hard limit: 200 lines per file** — no file may exceed 200 lines, no exceptions
- **Soft limit: 150 lines per file** — refactor when a file reaches 150 lines
- When a file hits 150 lines: plan a split before adding more code
- When a file hits 200 lines: STOP — refactor immediately before continuing
- Check with: `wc -l` on any file you create or modify
- This applies to ALL files: widgets, pages, providers, services, models, configs

## GitHub Issues — Auto + Manual

### Automated (after any skill finds issues)
When ANY skill (/pre-commit, /validate, /review, /perf-audit, /api-audit, /full-app-audit, /release-check, /redo) finds errors, warnings, or issues:

**NO EXCEPTIONS — even if you plan to fix the issue in the same session, you MUST open it on GitHub FIRST.**
The flow is: find → open on GitHub → fix → verify with /redo → ask user to approve → close on GitHub.
Never skip opening because "it was fixed in the same session." Traceability is mandatory.
1. Write to docs/issues.md as usual
2. **Check for duplicates first**, then open if new:

**IMPORTANT:** Always write JSON to a temp file — inline `-d "{...}"` breaks on special characters.

```bash
source .env && TITLE="[PRIORITY] TITLE" && \
EXISTING=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues?state=all&per_page=100" \
  | grep -c "\"title\": \"$TITLE\"") && \
if [ "$EXISTING" -gt 0 ]; then
  echo "SKIPPED — issue already exists: $TITLE"
else
  cat > /tmp/gh_issue.json << 'JSONEOF'
{
  "title": "[PRIORITY] TITLE",
  "body": "BODY\n\nFound by: /SKILL_NAME\nFile: FILE:LINE",
  "labels": ["LABEL"]
}
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
    echo "CREATED"; echo "$BODY_OUT" | grep -E '"number"|"html_url"'
  else
    echo "FAILED (HTTP $HTTP_CODE) — RETRY or report to user"
    echo "$BODY_OUT" | head -5
  fi
fi
```
3. **Verify**: "CREATED" = new issue opened, "SKIPPED" = duplicate found, "FAILED" = retry once then report
4. Add the GitHub issue number to docs/issues.md next to the item: `- [ ] desc — file:line — #42`

### Issue Closure Workflow (MANDATORY)
After fixing an issue that has a GitHub issue number:
1. Apply the fix
2. Run `/redo` to verify the fix passes (ruff, pytest, health check)
3. **STOP — ask user to verify and approve the fix**
4. Only after user says "approved" or "close it":
```bash
source .env && RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/osllmai/backend_Indox_Router_Server/issues/NUMBER" \
  -d '{"state":"closed"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "CLOSED — issue #NUMBER closed on GitHub"
else
  echo "FAILED — issue NOT closed, report to user"
fi
```
5. Verify output says "CLOSED" — if "FAILED", retry once then report
6. Update docs/issues.md: `- [x] desc — file:line — #42 (closed)`

**NEVER close a GitHub issue without user approval.**

### Manual
Run `/github-issue open|close|reopen|check` anytime for manual control.

### Labels by skill
| Skill | Default label |
|-------|--------------|
| /pre-commit | `bug` or `security` |
| /validate | `bug` |
| /review | `enhancement` or `bug` |
| /perf-audit | `performance` |
| /api-audit | `bug` or `enhancement` |
| /dep-audit | `tech-debt` |
| /full-app-audit | `tech-debt` |
| /release-check | `bug` |

## Changelog — Track Every Change

Every time you modify, create, or delete a file, log it to `docs/changelog.md`.

### Format
```markdown
## YYYY-MM-DD

| Time | Action | Files | Details | Skill |
|------|--------|-------|---------|-------|
| HH:MM | created/modified/deleted | file1.dart, file2.dart | Brief description of what changed | /redo, /review, manual, etc. |
```

### Rules
- One table per day (append rows, don't create new table if same day)
- Log EVERY file change — no exceptions
- Include which skill or manual action triggered the change
- If a file is created: action = "created"
- If a file is modified: action = "modified"
- If a file is deleted: action = "deleted"
- If multiple files changed in one action, list them comma-separated
- Create `docs/changelog.md` if it doesn't exist
- Never delete or overwrite previous entries

### Example
```markdown
## 2026-03-19

| Time | Action | Files | Details | Skill |
|------|--------|-------|---------|-------|
| 14:30 | modified | lib/features/auth/pages/login_page.dart | Fixed validation on email field | manual |
| 14:45 | created | lib/features/auth/widgets/phone_input.dart | New phone auth widget | manual |
| 15:00 | modified | lib/core/config/router.dart | Added /phone-auth route | manual |
| 15:10 | modified | docs/issues.md | Added issue #12 for missing error state | /review |
```
