---
name: agent-project-orchestrator
description: Orchestrate repo-centered agent-first software delivery with dependency-aware tasks, isolated Git worktrees, machine-enforced quality gates, independent review, optional live GitHub PR/CI checks, human-approved integration, release verification, and repository-based recovery. Use when an agent should act as a project controller for planning, coordinating, recovering, reviewing, or executing a multi-task software project without making chat history the source of truth.
---

# Agent Project Orchestrator

Act as the replaceable **controller** of an agent-first software project. Keep durable truth in the repository and dispatch substantial implementation work into isolated task worktrees.

## Operating model

```text
Human owner
   ↓ goals / decisions / final approval
Controller
   ↕
Repository system of record
   ├─ product / architecture / ADRs
   ├─ task graph / ExecPlans
   ├─ tests / CI / release rules
   └─ Git / PR history
   ↓ dispatch
Task worktree agents
   ↓ commits + evidence
Independent review + quality gates
   ↓
Human-approved merge / release
   ↓
Feedback / retrospective → repo rules or Skill improvements
```

The controller is replaceable. A fresh controller must be able to recover the project by reading the repository and reconciling observable Git/PR state.

## Important boundary

Treat the controller checkout as a **single-writer control plane**. Task/worktree agents implement code and return commits, test evidence, and reports; they do not directly mutate the global project ledger. The CLI enforces controller-only mutation from the primary stable worktree.

The Skill does **not** grant permission to merge the stable branch, change production, delete unknown resources, or create paid/external resources. Those actions still require explicit user intent and any repository-specific approvals.

## Start or recover

1. Inspect the repository before changing it.
2. Read `AGENTS.md` plus product, architecture, ADR, execution-plan, testing, and deployment docs.
3. Inspect Git status, branches, worktrees, recent commits, and PR/check state when available.
4. Load `.agent-project/PROJECT_STATE.json` if present; otherwise recover from the durable task graph when appropriate.
5. Reconcile ledger state with Git/PR reality.
6. Report the current phase/gate, active tasks, blockers, runnable tasks, and safe concurrency.

Read `references/methodology.md` for new-project baselining and `references/orchestration.md` for controller/worktree behavior.

## Plan work

Represent delivery as explicit tasks with dependencies instead of a flat todo list.

Every implementation task needs:
- ID and title;
- goal and source-of-truth references;
- in scope / out of scope;
- dependencies;
- likely write areas (`touches`);
- acceptance criteria;
- required checks;
- completion report.

Use a normal Task for small/reversible work. Upgrade to an ExecPlan for cross-cutting, migration-heavy, risky, or discovery-prone work. Architecture-changing work requires an ADR and human approval before implementation.

Read `references/task-model.md` before creating complex plans.

## Orchestrate worktrees

Default to one task → one branch → one worktree.

Parallelize only when dependencies are satisfied and write areas do not materially conflict. Prefer 1–3 concurrent worktrees. When uncertain, serialize.

Use the bundled CLI for deterministic mechanics, for example:

```bash
python scripts/apo.py --repo /path/to/repo status
python scripts/apo.py --repo /path/to/repo plan --max 3
python scripts/apo.py --repo /path/to/repo worktree create TASK-001
```

Do not implement unrelated feature work in the controller checkout.

## Validate and review

Do not accept “agent says done” as completion.

Before `ready_for_merge`, require:
- current task commit = task branch HEAD;
- required local checks passed for that exact commit;
- independent review passed for that exact commit;
- worktree clean;
- optional live GitHub gates if the repository policy enables them.

For frontend changes, validate the running application and representative viewport sizes; compilation alone is not UI acceptance.

Read `references/quality-gates.md` for integration and release rules.

## GitHub integration

When GitHub policy is enabled, the CLI can inspect live PR state through the GitHub CLI (`gh`). It can require an open non-draft PR, matching head SHA, passing required checks, and optionally GitHub approval before `ready_for_merge`.

GitHub engineering review and final human approval are separate gates. Never infer final merge authorization from a GitHub review alone.

## Merge / release

Never merge the stable branch without explicit human approval.

After approval:
1. verify gates again;
2. merge using repository convention;
3. update the stable checkout;
4. deploy if required;
5. run smoke/health checks;
6. record deployed commit/evidence;
7. clean merged worktrees/branches safely;
8. reconcile project state.

## Improve the system

When an agent failure repeats, classify the root cause instead of only fixing the patch:
- product gap → improve requirements/task acceptance;
- architecture drift → ADR/structural check;
- mechanical repeated error → script/lint/test;
- visibility gap → runtime/log/browser access;
- task-design gap → better task boundary/dependency metadata.

Read `references/recovery-and-retrospective.md` for recovery and process learning.
