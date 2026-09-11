# AGENTS.md

## Mission

{{MISSION}}

## Read first

- `docs/product/`
- `docs/architecture/`
- `docs/adr/`
- `docs/exec-plans/`
- `docs/testing/`
- `docs/deployment/`

## Controller / worktree boundary

- The primary stable checkout is the controller control plane.
- Task/worktree agents implement code and return commits/evidence.
- Task/worktree agents do not mutate `.agent-project/PROJECT_STATE.json` directly.

## Non-negotiables

- Stable branch is not the feature-development workspace.
- One implementation task → one branch → one worktree by default.
- Do not merge without explicit human approval.
- Do not silently change product/architecture baselines.
- Run and report required checks for the exact task commit.
- Use an independent review perspective for non-trivial changes.
- Keep secrets out of commits, logs, task files and PR bodies.
- If GitHub gates are enabled, do not claim ready-for-merge until the live PR/check gate passes.

## Required task completion report

- task ID/result
- branch/worktree
- files changed
- migrations/API/config changes
- checks and exact results
- runtime/preview evidence
- independent review result
- risks/follow-ups
- commit
- PR URL if available
- clean worktree confirmation
