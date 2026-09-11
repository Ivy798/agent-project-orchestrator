# Task and ExecPlan Model

## Good task properties

A task should have one coherent outcome, a reviewable diff, explicit dependencies, limited likely write areas, testable acceptance criteria, and no unrelated cleanup.

## Task metadata

The task Markdown is durable. The operational ledger mirrors scheduling data:

```json
{
  "id": "TASK-012",
  "status": "planned",
  "depends_on": ["TASK-010"],
  "touches": ["apps/api/learning", "tests/learning"],
  "parallel_safe_with": [],
  "required_checks": ["unit", "api"],
  "checks": {},
  "review": {"status": "pending"}
}
```

## ExecPlan threshold

Use an ExecPlan when two or more apply:
- 3+ architectural modules;
- schema/data migration;
- multiple milestones;
- risky rollout/rollback;
- temporary compatibility layer;
- likely discoveries during implementation;
- coherent backend + frontend + infra change.

ExecPlans are living files with Progress, Decision Log, Surprises, Validation, Rollout/Rollback, and Outcome.

## Architecture changes

Do not smuggle a new architecture through a feature task. Propose an ADR, obtain human approval, update source-of-truth docs, then implement.
