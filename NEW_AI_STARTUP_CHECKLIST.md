# NEW AI STARTUP CHECKLIST

Use this checklist at the start of every new Jarvis project session, before implementation work.

## Step 1 — Read Mandatory Project Documents

Read in this order:

1. `PROJECT_VISION.md`
2. `ROADMAP.md`
3. `PROJECT_STATUS.md`
4. `PHASE5_REVIEW.md`
5. `PHASE5_3_OPTIONS.md`

For Phase 5 work, continue with:

6. `PHASE5_DEVELOPER_AGENT.md`
7. `PHASE5_IMPLEMENTATION_PLAN.md`
8. The relevant phase-specific design and implementation plan.
9. Relevant source files and focused tests.

## Step 2 — Review Current State

Read `CURRENT_PROJECT_STATE.md`. Treat it as the current snapshot, not a permanent history. Check its last-verified date and note any assumptions or pending approvals.

## Step 3 — Review Continuity Log

Read `PROJECT_CONTINUITY_LOG.md` from the start through its last entry. The log is append-only. Distinguish reconstructed historical notes from contemporaneous records and check the last recommendation/open issues.

## Step 4 — Validate the Live Repository

Run non-destructive checks:

```powershell
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-list --left-right --count HEAD...origin/main
```

Record:

- current branch and commit;
- clean/dirty status, including all untracked files;
- whether the local branch is ahead of or behind its upstream;
- whether any worktree changes are unrelated user work.

Do not stage, overwrite, discard, reset, clean, commit, or push while checking state.

## Step 5 — Verify Test Status

Read the test source and latest test record. A recorded test count is historical until rerun. When appropriate and within the user’s request, run the focused or full safe local test suite and record the exact command, date, and result. Do not claim tests passed without running them.

Current baseline recorded in `CURRENT_PROJECT_STATE.md`: `python -m unittest discover -s tests -v` — 127 tests passed on 2026-10-30.

## Step 6 — Compare Repository and Continuity State

Compare the live branch, revision, status, remote relationship, test results, and project files with `CURRENT_PROJECT_STATE.md` and the last continuity-log entry.

- If they match, use the continuity recommendation as context.
- If they differ, determine why and report the difference; do not rewrite history to make them match.
- Update the current-state snapshot only when new facts have been verified.
- Append a dated continuity-log entry for significant completed work; never delete historical entries.

## Step 7 — Determine Unfinished Work

Confirm which work is implemented, planned, recommended, not started, blocked, or awaiting approval. In particular, Testing Awareness is a recommendation, not an implementation approval. Do not start it automatically.

## Step 8 — Ask Before Implementation

Before performing implementation work, ask the user exactly:

> Would you like me to continue from the last recommended milestone, or would you like to change direction?

Wait for the user’s direction. Approval must be specific to the work scope; implementation approval does not imply approval to run risky tests, commit, push, merge, or deploy.
