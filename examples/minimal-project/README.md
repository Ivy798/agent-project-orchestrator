# Minimal APO Project Example

This directory illustrates the **shape** of a repo after APO bootstrap and planning. It is documentation, not a runnable nested Git repository.

```text
AGENTS.md
docs/
  product/PROJECT_CHARTER.md
  architecture/ARCHITECTURE.md
  exec-plans/
    ORCHESTRATOR_POLICY.json
    TASK_GRAPH.json
    tasks/TASK-001.md
  testing/TEST_STRATEGY.md
  deployment/DEPLOYMENT.md
```

The real `.agent-project/PROJECT_STATE.json` is intentionally not included because it is runtime state and should be gitignored.
