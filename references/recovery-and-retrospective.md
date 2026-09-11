# Recovery and Retrospective

## Recovery

A new controller should be able to recover without old chat history:
- read repo docs/task files;
- inspect Git branches/worktrees/commits;
- inspect PR/CI via authorized interface;
- run `apo reconcile` (dry-run by default) and `apo validate`;
- identify the stable integrated boundary and unresolved tasks.

If `.agent-project/PROJECT_STATE.json` is missing, `apo recover` rebuilds a **planned baseline** from the durable `docs/exec-plans/TASK_GRAPH.json`. It intentionally refuses to overwrite an existing operational ledger.

After recovery, reconcile observable Git/PR state before continuing.

## Ledger failures

The ledger is protected by a short exclusive lock, revision checks and atomic replacement. A stale controller process should fail rather than overwrite newer state.

If a crashed process leaves a stale lock, the writer may remove it after the configured stale-lock interval. Do not manually delete a fresh lock simply to bypass another active controller.

## Failure taxonomy

- Product gap → improve PRD/task acceptance.
- Architecture gap → ADR/structural test.
- Mechanical repeated error → script/lint/CI.
- Visibility gap → better runtime/browser/log access.
- Task-design gap → better Task/DAG/ExecPlan design.

## Retrospective rule

If a class of error repeats, modify the harness so it becomes harder to repeat. Prefer a machine check over an additional paragraph when the condition is mechanically verifiable.

Future automation of this taxonomy should be driven by repeated real-project failures rather than speculative rules.
