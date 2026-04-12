---
description: "Run all 5 mandatory skills in sequence"
allowed-tools: Read, Grep, Glob, Bash
---

# /daily — Mandatory Pipeline

Run all 5 mandatory skills in order. Stop immediately if any skill fails.

## Step 1: /resume
Rebuild context — read CLAUDE.md, rules, active plan, recent git history, open issues.

## Step 2: /redo
Re-run verification — analyze, tests, lint, check for banned patterns.
If FAIL → stop, write to docs/issues.md, auto-open GitHub issue, report to user.

## Step 3: /review
Self-review all changed files since last commit.
If issues found → stop, write to docs/issues.md, auto-open GitHub issue, report to user.

## Step 4: /validate
Verify active plan matches implementation.
If gaps found → stop, write to docs/issues.md, auto-open GitHub issue, report to user.

## Step 5: /pre-commit
Final gate — secrets, tokens, architecture, code standards.
If BLOCKED → stop, write to docs/issues.md, auto-open GitHub issue, report to user.
If APPROVED → report "READY TO PUSH" to user.

## Pipeline Result
```
ALL PASS → ✅ READY TO PUSH
ANY FAIL → ❌ BLOCKED at step N — fix and run /daily again
```

**Do NOT push automatically.** Always wait for user to push manually.
