# GitHub Publication Guide

Recommended repository name:

`agent-project-orchestrator`

Recommended description:

> Repo-centered orchestration Skill and CLI for agent-first software delivery with isolated Git worktrees, dependency-aware planning, machine quality gates, live GitHub PR/CI checks, independent review, and human-approved integration.

Recommended topics:

`codex`, `agents`, `agentic-development`, `git-worktree`, `software-engineering`, `multi-agent`, `developer-tools`, `project-management`

## First publication

From the project directory:

```bash
git init -b main
git add .
git commit -m "feat: release agent-project-orchestrator v1.2.0"
```

Then create a public GitHub repository using the GitHub UI or your authenticated GitHub CLI, add it as `origin`, and push `main`.

Before creating the `v1.2.0` tag, confirm the GitHub Actions CI run is green on both Ubuntu and Windows.

Then:

```bash
git tag v1.2.0
git push origin v1.2.0
```

The included release workflow builds a wheel, reruns tests/selftest, and creates a GitHub Release for the tag.

## Repository settings worth enabling

For `main`, prefer:
- require a pull request before merging;
- require the `CI` checks;
- require conversation resolution if you use review discussions;
- disallow force pushes;
- disallow branch deletion.

Keep final merge approval as a human/project-owner decision even when automated and GitHub checks pass.

## Codex installation from the public repository

The Skill lives at repository root. Ask Codex's skill installer to install the repository path `.` into the skills directory, then restart/reload Codex if required by the surface.

Example natural-language request:

> Use $skill-installer to install `agent-project-orchestrator` from my public GitHub repository, using the repository root (`.`) as the skill path.

## After publication

Use real project failures to drive future versions. Do not add enterprise-grade mechanisms merely to increase feature count.
