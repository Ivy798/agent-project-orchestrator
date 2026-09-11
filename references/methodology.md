# Agent-Orchestrated Project Delivery Method

## Ten-stage lifecycle

1. Intent — user/business outcome and constraints.
2. Baseline — PRD, UX, architecture, data/security/deployment assumptions.
3. Project Harness — repo docs, AGENTS, tests, CI, runtime tooling.
4. Planning — Epic → dependency-aware Tasks; Task vs ExecPlan.
5. Orchestration — controller chooses runnable tasks/worktrees.
6. Execution — agents implement/test/commit in isolated worktrees.
7. Integration — PR, CI, independent review, controller review, human approval.
8. Release — merge, deploy, smoke, rollback/restore readiness.
9. Operate — logs/bugs/user feedback become backlog.
10. Learn — retrospective upgrades docs, ADRs, tests, scripts or Skill.

## Repository as durable memory

A controller conversation is disposable. Store durable project context in:

```text
AGENTS.md
docs/product/
docs/architecture/
docs/adr/
docs/exec-plans/
docs/testing/
docs/deployment/
Git commits / branches / PRs / CI
```

`.agent-project/PROJECT_STATE.json` is an operational cache for scheduling. It is controller-owned, gitignored, revisioned, and reconcilable from durable/observable state.

## Planning vs feature code on stable branch

Planning artifacts are control-plane changes. The default CLI may make a small local planning commit containing generated baseline/task docs before worktree creation. This is intentionally different from feature development on the stable checkout.

If repository governance forbids local planning commits on the stable branch, use `--no-commit`, create a planning branch/PR, merge it, then create implementation worktrees from the integrated baseline.

## Human approval gates

Require explicit human input for:
- material product scope changes;
- architecture baseline changes;
- destructive/external-cost actions;
- merge to stable branch;
- production release where repository policy requires it.

Remote GitHub review/CI strengthens the engineering gate but does not replace final owner approval.
