# Installation and Use

## Codex Skill

Place the skill folder under the Codex skills directory supported by your environment, commonly:

```text
$CODEX_HOME/skills/agent-project-orchestrator
```

For a public GitHub repository whose Skill is at the repository root, Codex's skill installer can install the repository path `.`.

Restart/reload Codex if the surface requires it to discover newly installed skills.

## CLI

From the Skill/repository directory:

```bash
python apo.py --help
python apo.py selftest
```

Optional package install:

```bash
python -m pip install -e .
apo --help
```

## Example controller request

> Use $agent-project-orchestrator as the main controller for this repository. Recover project state, validate the task DAG, propose at most three safe worktrees, enforce configured GitHub/local quality gates, and never merge the stable branch without my explicit approval.
