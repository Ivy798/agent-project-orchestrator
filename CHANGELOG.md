# Changelog

## 1.2.0

### Added
- live GitHub PR/required-check integration through `gh`;
- configurable machine-readable GitHub quality-gate policy;
- controller-only global ledger mutation enforcement;
- serialized atomic ledger writes with lock-file protection and revision conflict checks;
- Git identity preflight before planning commands that auto-commit;
- Ubuntu + Windows GitHub Actions CI;
- public repository README, CONTRIBUTING and SECURITY documentation;
- `agents/openai.yaml` UI metadata;
- minimal example project harness;
- adversarial tests for new v1.2 invariants.

### Changed
- `reconcile` is explicitly dry-run by default and requires `--apply` to mutate;
- public license changed from MIT to Apache-2.0 for clearer patent terms;
- CLI mutation commands consistently execute through the primary stable controller checkout;
- Windows GitHub CLI execution honors the PATH-resolved command and decodes CLI output as UTF-8;
- native path identity checks handle Windows 8.3 short-path aliases returned by hosted runners;
- GitHub Actions use the Node 24-compatible `actions/setup-python@v6` runtime;
- `ready_for_merge` can enforce live remote PR/CI state when enabled.

### Intentionally deferred
- multi-controller scheduler/database state;
- RBAC/GPG approval identity;
- autonomous merge/deploy;
- cross-machine worktree synchronization;
- full failure-taxonomy automation.

## 1.1.0

Engineering rewrite after independent review:
- real task state machine;
- DAG validation;
- commit-bound checks/review;
- worktree/branch/commit gates;
- recovery/reconcile;
- Windows path normalization tests;
- unified CLI and automated test suite.

## 1.0.0

Initial methodology and prototype tooling.
