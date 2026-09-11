# Contributing

Thank you for helping improve Agent Project Orchestrator.

## Principles

This project values:
- machine-enforced guarantees over prose-only rules;
- reproducible failures over speculative fixes;
- small, reviewable changes;
- tests for every workflow invariant;
- backward-compatible evolution where practical;
- human approval for changes that weaken safety gates.

## Before opening a PR

1. Open or reference an issue for non-trivial behavior changes.
2. Explain the failure mode or user outcome being addressed.
3. Keep unrelated refactors out of the PR.
4. Add/update tests for changed behavior.
5. Run:

```bash
python -m pip install -e ".[test]"
pytest -q
python apo.py selftest
```

6. Update `CHANGELOG.md` for user-visible changes.
7. Update `SKILL.md` and relevant references when behavior/methodology changes.

## Architecture changes

Changes to the task state machine, controller safety model, GitHub gate semantics, durable task graph, or recovery behavior should include a short design rationale in the PR. Prefer explicit migration notes over silent behavior changes.

## Review standard

Reviewers should try to break the change, not merely confirm the happy path. Useful adversarial cases include:
- dirty/stale worktrees;
- fake or stale commit SHAs;
- branch HEAD changing after review;
- dependency cycles;
- missing Git identity;
- Windows/POSIX path differences;
- stale controller ledger revisions;
- missing/failed/pending GitHub checks.
