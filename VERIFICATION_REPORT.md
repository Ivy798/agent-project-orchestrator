# Verification Report — v1.2.0

**Environment used for this report:** Linux sandbox, Python 3.x available in the execution environment, local Git. Network access for package downloads/GitHub was unavailable during final local verification.

## 1. Automated test suite

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
40 passed in 20.12s
```

Coverage includes the previous v1.1 regression set plus v1.2 tests for:
- stale revision rejection;
- atomic ledger writes;
- concurrent controller write conflict handling;
- Git identity preflight with clean failure;
- controller-only state mutation;
- GitHub PR snapshot parsing;
- required-check pass/pending/error/no-check behavior;
- GitHub head-SHA/check/review gate rules;
- CLI-level GitHub flow using a deterministic fake `gh` executable;
- public repository structure/version consistency;
- Skill/README boundary consistency;
- public/runtime template synchronization;
- recovery refusing to overwrite an existing ledger.

## 2. Built-in selftest

Command:

```bash
PYTHONPATH=src python apo.py selftest
```

Result:

```json
{
  "ok": true,
  "selftest": "passed"
}
```

The selftest exercises a real temporary Git repository through planning, worktree creation, task commit, testing, review, ready-for-merge, explicit approval, Git merge, and merged-state verification.

## 3. Wheel build and hygiene

Because the sandbox could not reach PyPI to install the `build` package, local verification used the installed setuptools backend through:

```bash
python -m pip wheel --no-build-isolation --no-deps -w dist .
```

Result:

```text
agent_project_orchestrator-1.2.0-py3-none-any.whl
package hygiene: PASS
```

The wheel contained no leaked `build/`, `.egg-info/`, `__pycache__/`, or `.pytest_cache/` paths.

The public GitHub CI uses `python -m build --wheel` and repeats the wheel-content check in a networked hosted runner.

## 4. Clean virtual-environment install

A new Python virtual environment was created and the locally built wheel installed with no network and no dependencies.

Then:

```bash
apo --help
apo selftest
```

both succeeded, and the installed-package selftest returned `passed`.

## 5. GitHub integration verification boundary

The local environment did not contain an authenticated GitHub CLI and had no network access. Therefore v1.2 **does not claim that a real GitHub PR was created during this local verification**.

What was verified locally:
- exact `gh pr view` JSON fields expected by the adapter;
- `gh pr checks --required` result handling, including exit code 8 for pending checks;
- CLI `pr create` / remote snapshot / live ready gate using a deterministic fake `gh` executable;
- commit/PR-head equality enforcement;
- required-check enforcement;
- optional review-decision enforcement.

What must happen after public push:
- GitHub Actions runs on `ubuntu-latest` and `windows-latest`;
- authenticated `apo github preflight` against the real repository;
- one real dogfood PR through `apo pr create`, CI, `ready_for_merge`, human approval and merge.

## 6. Windows verification boundary

Windows path semantics are covered by unit tests and the repository now contains a real `windows-latest` CI matrix entry. This Linux session did not execute a native Windows runner.

The first public GitHub CI run is therefore an explicit final verification gate for Windows behavior.

## 7. Known intentional limitations

v1.2 does not implement:
- multi-controller shared database scheduling;
- RBAC/GPG identity for approvers;
- automatic stable-branch merge;
- automatic production deployment;
- remote worktree replication;
- event-sourced ledger replay;
- structured telemetry backend;
- automatic failure-taxonomy classification.

These are deferred until real project usage justifies them.

## 8. Publication preflight on Windows — 2026-09-11

The public-release preflight was repeated on native Windows with Python 3.12.14:

```text
pytest: 40 passed in 67.72s
selftest: passed
wheel package hygiene: PASS (30 entries)
```

The first Windows run exposed a command-resolution defect in the fake-`gh` integration test: the adapter verified the PATH-resolved command but launched a bare `gh`, which could select a different executable. The adapter now launches the resolved command and decodes GitHub CLI output as UTF-8. The targeted regression and full suite passed after the fix.

GitHub-hosted Ubuntu and Windows CI remain required gates before creating the release tag.

## 9. Release judgment

The local release candidate passed all tests available in this environment and is suitable for:
1. public GitHub publication;
2. GitHub-hosted Ubuntu/Windows CI verification;
3. human-supervised dogfooding on Agent Learning Platform.

It should not be described as a fully autonomous 7×24 enterprise orchestrator.
