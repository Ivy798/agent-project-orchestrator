# Agent Project Orchestrator

**Repo-centered orchestration for agent-first software delivery.**

Agent Project Orchestrator (`apo`) is a reusable method + Codex Skill + lightweight Python CLI for running software projects with a replaceable controller and isolated Git worktree agents.

It is designed for a workflow where a human owns goals and final approvals, a controller agent owns planning/integration, and task agents implement independently in worktrees.

## Why this exists

Long-running agent projects fail when project memory lives only in chat, multiple agents edit the same checkout, or “quality gates” exist only as prose.

APO makes the repository the durable control plane:

```text
Human owner
     │
     ▼
Main controller  ←→  Repository truth
     │              PRD / Architecture / ADR
     │              Task DAG / ExecPlans / CI
     │
 ┌───┼───────────┐
 ▼   ▼           ▼
WT-A WT-B       WT-C
Agent Agent     Agent
 └──── commits / evidence ────┘
               │
               ▼
      machine quality gates
               │
      independent review
               │
               ▼
       human final approval
               │
               ▼
          merge / release
```

The controller can be replaced. The project should still be recoverable from the repo, Git state, PRs, and CI.

## Current maturity

**v1.2.0** is intended for serious human-supervised agent development workflows.

It provides:
- dependency-aware task planning and DAG validation;
- one-task/one-branch/one-worktree orchestration;
- controller-only global state mutation;
- atomic CAS-style operational ledger writes with revision checks;
- commit-bound test/review evidence;
- machine-enforced task state transitions;
- recovery/reconcile support;
- optional live GitHub PR and required-check gates via `gh`;
- Windows + Ubuntu CI for the public project;
- reusable project templates and methodology references.

It is **not** a 7×24 autonomous multi-controller scheduler and it does not auto-merge production branches.

## Important safety boundary

APO deliberately keeps the human at high-leverage approval points. Final integration still requires **explicit human approval**.

It does not treat any of the following as implicit permission:
- merge the stable branch;
- alter production infrastructure;
- delete unknown branches/services/resources;
- create paid/external resources;
- expose secrets;
- broaden project scope.

Task agents should return commits and evidence. The controller is the **single-writer** authority for the project ledger.

## Requirements

- Python 3.11+
- Git
- Optional: GitHub CLI (`gh`) for live PR/CI integration

## Use as a Codex Skill

Place this repository/folder under your Codex skills directory, commonly:

```text
~/.codex/skills/agent-project-orchestrator
```

Or install it from a GitHub repository using Codex's skill installer. For a repository where the Skill is at the repo root, use the repository with path `.`.

Then invoke it naturally, for example:

```text
Use $agent-project-orchestrator as the main controller for this project.
Recover repository state, identify runnable tasks, create only safe parallel
worktrees, enforce quality gates, and do not merge main without my approval.
```

The UI metadata lives in `agents/openai.yaml`.

## CLI quick start

No package installation is required inside this repository:

```bash
python apo.py --help
python apo.py selftest
# Skill-standard launcher: python scripts/apo.py --help
```

Optional editable install:

```bash
python -m pip install -e .
apo --help
```

### 1. Bootstrap an existing Git repository

Configure Git identity first because `apo init` creates a planning commit by default:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"

apo --repo . init --name "My Project"
```

`init` creates the project harness, including:
- `AGENTS.md`
- `docs/product/PROJECT_CHARTER.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/testing/TEST_STRATEGY.md`
- `docs/deployment/DEPLOYMENT.md`
- `docs/exec-plans/TASK_GRAPH.json`
- `docs/exec-plans/ORCHESTRATOR_POLICY.json`
- PR template

The runtime ledger is stored in `.agent-project/PROJECT_STATE.json` and is gitignored.

### 2. Create tasks

```bash
apo --repo . task create TASK-001 \
  --title "Project skeleton" \
  --touches apps/web,apps/api \
  --required-checks unit,build

apo --repo . task create TASK-002 \
  --title "Course schema" \
  --depends-on TASK-001 \
  --touches packages/schema \
  --required-checks unit
```

Task creation validates dependency cycles and commits the durable task graph by default.

### 3. Plan safe parallel work

```bash
apo --repo . validate
apo --repo . plan --max 3
```

Unknown write areas or overlapping `touches` are serialized unless explicitly marked safe.

### 4. Create a task worktree

```bash
apo --repo . worktree create TASK-001
```

Task agents work in the task worktree. They should **not** mutate the controller ledger directly.

### 5. Bind evidence to the actual task commit

After the task agent commits its work:

```bash
apo --repo . task set-commit TASK-001 <sha>
apo --repo . transition TASK-001 testing
apo --repo . check record TASK-001 unit pass --detail "42 passed"
apo --repo . check record TASK-001 build pass
apo --repo . transition TASK-001 review
apo --repo . review record TASK-001 passed --reviewer "independent-agent"
apo --repo . transition TASK-001 ready_for_merge
```

If the branch HEAD changes after checks/review, APO invalidates the gate until the new commit is explicitly set and revalidated.

## GitHub PR / CI integration

GitHub integration is optional and uses the official `gh` CLI.

Preflight:

```bash
apo --repo . github preflight
```

Enable live PR + required-check gates:

```bash
apo --repo . github configure \
  --enabled \
  --require-pr \
  --require-checks \
  --no-require-review
```

Create a PR after setting the task commit:

```bash
apo --repo . pr create TASK-001 --push
```

Inspect/sync:

```bash
apo --repo . pr status TASK-001
apo --repo . pr checks TASK-001
apo --repo . pr sync TASK-001
```

When GitHub gating is enabled, `ready_for_merge` performs a **live** PR lookup. Depending on policy, it can require:
- open, non-draft PR;
- PR head SHA matching the current task commit;
- base matching the stable branch;
- passing GitHub required checks;
- optional GitHub `APPROVED` review decision.

GitHub review is not final owner approval. Final merge authorization remains a separate explicit human gate:

```bash
apo --repo . transition TASK-001 approved --by "project-owner"
```

APO does not provide an automatic stable-branch merge command by design.

## Controller-only state writes

`.agent-project/PROJECT_STATE.json` is an operational ledger. Global state mutation is restricted to the primary stable worktree.

The ledger uses:
- a short cross-platform exclusive lock file for controller writes;
- monotonically increasing `revision`;
- compare-before-save stale-writer detection;
- write-to-temp + `fsync` + `os.replace` atomic replacement.

If two controller processes race on the same local project, writes are serialized and a stale revision is rejected instead of silently overwriting newer state.

## Reconcile and recovery

Dry-run is the default:

```bash
apo --repo . reconcile
```

Apply only after reviewing findings:

```bash
apo --repo . reconcile --apply
```

If runtime state is lost, recover a planned baseline from the durable task graph:

```bash
apo --repo . recover
```

Then reconcile with Git/PR reality before continuing.

## Project methodology

The Skill includes references for:
- `references/methodology.md`
- `references/orchestration.md`
- `references/task-model.md`
- `references/quality-gates.md`
- `references/recovery-and-retrospective.md`

The core delivery loop is:

```text
Intent → Baseline → Harness → Task DAG → Worktrees →
Implementation → Independent Review → Human Approval →
Release → Operate → Retrospective
```

## Development and verification

Run locally:

```bash
python -m pip install -e ".[test]"
pytest -q
python apo.py selftest
```

The public repository CI runs the suite on Ubuntu and Windows.

See `VERIFICATION_REPORT.md` for the exact verification performed for this release.

## Public project files

- `CONTRIBUTING.md` — contribution workflow
- `SECURITY.md` — security reporting and trust boundaries
- `CHANGELOG.md` — release history
- `INDEPENDENT_REVIEW_RESPONSE.md` — review-driven improvement notes
- `examples/minimal-project/` — small illustrative project harness

## Limitations

v1.2.0 intentionally does not implement:
- multi-controller concurrent scheduling;
- SQLite/WAL/event-sourced controller state;
- RBAC or cryptographic approver identity;
- automatic production merge/deploy;
- cross-machine worktree synchronization;
- autonomous scope/architecture approval.

Those features should be added only when real project use demonstrates the need.

## License

Apache License 2.0. See `LICENSE`.
