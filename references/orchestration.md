# Orchestration

## Single-writer control plane

The controller is the only writer to global operational state. Task/worktree agents return commits, checks, review evidence and findings; the controller records transitions from the primary stable worktree.

The CLI enforces this boundary for mutating commands.

## Controller startup/recovery

1. Read repo rules and current execution plan.
2. Run `apo status`.
3. Run `apo reconcile` in dry-run mode.
4. Inspect real Git worktrees/branches/commits.
5. If GitHub integration is enabled, inspect live PR/check state with `apo pr status` / `apo pr checks`.
6. Run `apo validate`.
7. Run `apo plan`.
8. Report phase/gate, active tasks, blockers, runnable tasks, safe concurrency, and any approval needed.

A controller conversation is disposable. Repository state, Git and PR/CI are the recovery sources.

## Parallelism

A task is runnable only when all dependencies are integrated (`merged` or `deployed`) and the DAG is valid.

The planner is deliberately conservative about `touches` overlap. Explicit `parallel_safe_with` can permit a known-safe overlap, but it is not a substitute for controller judgment.

Prefer 1–3 active implementation worktrees unless the task graph clearly supports more.

Parallel development does not imply parallel merge. Integrate foundational contracts before dependent consumers and rerun tests after rebasing/updating dependent worktrees.

## Worktree lifecycle

```text
planned
→ developing
→ testing
→ review
→ ready_for_merge
→ approved
→ merged
→ deployed (when applicable)
```

Use the same worktree to fix review findings for the same task.

## Operational ledger

`.agent-project/PROJECT_STATE.json` is runtime state, not durable product truth.

Writes use:
- short exclusive lock-file serialization;
- revision comparison;
- atomic replacement.

If the runtime ledger is lost, recover a planned baseline from `TASK_GRAPH.json`, then reconcile observable Git/PR state.
