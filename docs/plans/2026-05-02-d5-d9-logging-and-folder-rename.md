# Plan — Tasks #17 (D5) + #18 (D9)

**Created:** 2026-05-02
**Branch:** production
**Baseline at start:** HEAD `f623dd0`, full suite 263 passed

## What we are building

Two unrelated cleanup tasks, each shipped as its own commit. Test the full
suite after each task. No app-code changes — settings + docs only.

| Task | Title | Touches |
|------|-------|---------|
| #17 (D5) | Add Django LOGGING config | `config/settings.py` |
| #18 (D9) | Rename folder `business_plan` → `business_plan` | `docs/`, refs in `CLAUDE.md` etc. |

## Hard rules (apply to both tasks)

1. Run Task #17 fully before starting Task #18.
2. Full suite must report **263 passed** after each task. If not → STOP.
3. Use `git mv` for the folder rename (preserves history).
4. Do NOT touch app code. Do NOT modify `.gitignore`. Do NOT push.
5. Each task is its own commit — no squashing.

---

## Task #17 — Django LOGGING config (D5)

### Files
- `config/settings.py` — add `import sys`, add `LOGGING` dict.

### Decision (insertion point)
The user-supplied spec said "AFTER DATABASES block, BEFORE INSTALLED_APPS",
but in this file `INSTALLED_APPS` is on line 29 and `DATABASES` ends on line
97. Anchors contradict. Resolution: **place LOGGING after DATABASES** (line
97 → before "Auth password validators" on line 99) under a new
`# --- Logging ---` section. `import sys` goes next to `import os` at top.

### Phases
1. **Pre-flight:** confirm no existing `LOGGING`, no existing `import sys`.
2. **Edit:** add `import sys` next to `import os`; insert `LOGGING` block
   after the DATABASES `else` branch with a section header comment.
3. **Verify:**
   - Restart `nemi-api` container; confirm `(healthy)`.
   - Full suite must show `263 passed`.
   - Sample log line from `docker compose logs nemi-api` should match
     `[YYYY-MM-DD HH:MM:SS,ms] LEVEL name: message` format.
4. **Commit:** `feat(logging): add Django LOGGING config for stdout structured logs (D5)`

### Acceptance
- `git diff --stat` shows exactly 1 file changed (`config/settings.py`).
- Targeted: not applicable (no test added).
- Full suite: 263 passed.
- Log lines emitted in the configured `[asctime] LEVEL name: message` format.

### Rollback
`git revert <commit>` — single-file change, isolated.

---

## Task #18 — Folder rename `business_plan` → `business_plan` (D9)

### Files
- `docs/business_plan/` → `docs/business_plan/` (git mv, all 6 files inside)
- Any other file with the string `business_plan` (likely `CLAUDE.md`,
  possibly `README.md`, internal cross-links).

### Phases
1. **Pre-flight:** `grep -rn "business_plan"` across repo (excluding
   `.git`, caches). List every match.
2. **Rename folder:** `git mv docs/business_plan docs/business_plan`.
3. **Update references:** for each match outside the folder, replace
   `business_plan` → `business_plan` in-place.
4. **Verify references:** re-run grep — must be empty.
5. **Verify tests:** full suite must show `263 passed` (rename should not
   affect tests).
6. **Commit:** `chore(docs): rename business_plan → business_plan (D9)`

### Acceptance
- Post-edit grep returns no matches.
- `git status` shows renames detected for all 6 files inside the folder
  plus any reference-updated files.
- Full suite: 263 passed.

### Rollback
`git revert <commit>` — folder rename + ref edits all in one commit.

---

## Final report (after both tasks)
- Task #17 commit hash
- Task #18 commit hash
- `git log --oneline -5`
- Final pytest tail (must be 263)
- `git status` clean
