from __future__ import annotations

import json
import shutil
from importlib import resources
from pathlib import Path

from . import gitops
from .dag import assert_valid_dag
from .errors import GitStateError, ValidationError
from .policy import DEFAULT_POLICY, POLICY_REL, save_policy
from .state import new_task, save_state, state_path

TASK_GRAPH_REL = Path('docs/exec-plans/TASK_GRAPH.json')


def _template(name: str):
    return resources.files('agent_project_orchestrator').joinpath('templates', name)


def ensure_gitignore(repo: Path):
    p = repo / '.gitignore'
    text = p.read_text(encoding='utf-8') if p.exists() else ''
    lines = text.splitlines()
    if '.agent-project/' not in lines:
        if text and not text.endswith('\n'):
            text += '\n'
        text += '.agent-project/\n'
        p.write_text(text, encoding='utf-8')


def _copy_if_missing(name: str, dst: Path):
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    with resources.as_file(_template(name)) as src:
        shutil.copy2(src, dst)


def _write_task_graph(repo: Path, state: dict):
    durable = {
        'schema_version': 1,
        'project': state.get('project'),
        'stable_branch': state.get('stable_branch'),
        'current_phase': state.get('current_phase'),
        'tasks': {
            tid: {
                k: t.get(k)
                for k in ['id', 'title', 'depends_on', 'touches', 'parallel_safe_with', 'required_checks']
            }
            for tid, t in state['tasks'].items()
        },
    }
    p = repo / TASK_GRAPH_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(durable, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return p


def bootstrap(repo: Path, name: str, stable_branch=None, phase='phase-1', commit=True):
    repo = gitops.repo_root(repo)
    primary = gitops.primary_worktree_path(repo)
    if primary and repo.resolve() != Path(primary).resolve():
        raise ValidationError('apo init is controller-only: run it from the primary worktree')
    if not gitops.is_clean(repo):
        raise GitStateError('apo init requires a clean repository')
    stable_branch = stable_branch or gitops.current_branch(repo)
    if not stable_branch or not gitops.branch_exists(repo, stable_branch):
        raise ValidationError(f'stable branch does not exist: {stable_branch!r}')
    if gitops.current_branch(repo) != stable_branch:
        raise ValidationError(f'apo init must run on stable branch {stable_branch}')
    if commit:
        # Preflight *before* writing any project files, so failure leaves the
        # caller's checkout untouched.
        gitops.assert_git_identity(repo)

    mapping = {
        'AGENTS.md': repo / 'AGENTS.md',
        'PROJECT_CHARTER.md': repo / 'docs/product/PROJECT_CHARTER.md',
        'ARCHITECTURE.md': repo / 'docs/architecture/ARCHITECTURE.md',
        'TEST_STRATEGY.md': repo / 'docs/testing/TEST_STRATEGY.md',
        'DEPLOYMENT.md': repo / 'docs/deployment/DEPLOYMENT.md',
        'PR_TEMPLATE.md': repo / '.github/pull_request_template.md',
    }
    for src, dst in mapping.items():
        _copy_if_missing(src, dst)
    for rel in ['docs/adr', 'docs/exec-plans/tasks', 'docs/exec-plans/execplans']:
        d = repo / rel
        d.mkdir(parents=True, exist_ok=True)
        keep = d / '.gitkeep'
        if not keep.exists():
            keep.write_text('', encoding='utf-8')

    ensure_gitignore(repo)
    state = {
        'schema_version': 1,
        'revision': 0,
        'project': name,
        'stable_branch': stable_branch,
        'current_phase': phase,
        'current_gate': 'baseline',
        'updated_at': None,
        'tasks': {},
    }
    save_state(repo, state)
    _write_task_graph(repo, state)
    policy_path = repo / POLICY_REL
    if not policy_path.exists():
        save_policy(repo, json.loads(json.dumps(DEFAULT_POLICY)))

    if commit:
        gitops.run_git(repo, ['add', 'AGENTS.md', 'docs', '.github', '.gitignore'])
        gitops.run_git(repo, ['commit', '-m', 'chore(apo): bootstrap agent project harness'])
    return state


def create_task(
    repo: Path,
    tid,
    title,
    depends_on=None,
    touches=None,
    parallel_safe_with=None,
    required_checks=None,
    commit=True,
):
    repo = gitops.repo_root(repo)
    primary = gitops.primary_worktree_path(repo)
    if primary and repo.resolve() != Path(primary).resolve():
        raise ValidationError('task planning is controller-only: run it from the primary worktree')
    if not gitops.is_clean(repo):
        raise GitStateError('task create requires a clean controller checkout')
    from .state import load_state

    state = load_state(repo)
    stable = state['stable_branch']
    if gitops.current_branch(repo) != stable:
        raise ValidationError(f'task planning must run on stable branch {stable}')
    if commit:
        gitops.assert_git_identity(repo)
    if tid in state['tasks']:
        raise ValidationError(f'task already exists: {tid}')

    t = new_task(tid, title, depends_on, touches, parallel_safe_with, required_checks)
    trial = {**state, 'tasks': {**state['tasks'], tid: t}}
    assert_valid_dag(trial['tasks'])

    task_file = repo / 'docs/exec-plans/tasks' / f'{tid}.md'
    task_file.parent.mkdir(parents=True, exist_ok=True)
    deps = '\n'.join(f'- {x}' for x in t['depends_on']) or '- None'
    touches_text = '\n'.join(f'- `{x}`' for x in t['touches']) or '- To be confirmed'
    checks = '\n'.join(f'- [ ] {x}' for x in t['required_checks']) or '- [ ] Define task-specific checks'
    task_file.write_text(
        f"""# {tid} — {title}\n\n## Goal\n\n## Source of truth\n\n## In scope\n\n## Out of scope\n\n## Dependencies\n{deps}\n\n## Likely code areas (`touches`)\n{touches_text}\n\n## Acceptance criteria\n- [ ]\n\n## Required checks\n{checks}\n\n## Completion report\n- result\n- branch/worktree\n- files changed\n- migrations/API/config\n- checks and exact results\n- runtime/preview evidence\n- risks/follow-ups\n- commit\n- PR URL if available\n- clean worktree confirmation\n""",
        encoding='utf-8',
    )
    state['tasks'][tid] = t
    save_state(repo, state)
    graph = _write_task_graph(repo, state)
    if commit:
        gitops.run_git(repo, ['add', str(task_file.relative_to(repo)), str(graph.relative_to(repo))])
        gitops.run_git(repo, ['commit', '-m', f'chore(plan): add {tid}'])
    return t, task_file


def recover_state_from_task_graph(repo: Path, name='Recovered Project', phase='unknown'):
    repo = gitops.repo_root(repo)
    primary = gitops.primary_worktree_path(repo)
    if primary and repo.resolve() != Path(primary).resolve():
        raise ValidationError('recovery is controller-only: run it from the primary worktree')
    if state_path(repo).exists():
        raise ValidationError('operational ledger already exists; recovery is for a missing ledger. Back it up/remove it intentionally before recover.')
    p = repo / TASK_GRAPH_REL
    if not p.exists():
        raise ValidationError(f'missing durable task graph: {p}')
    graph = json.loads(p.read_text(encoding='utf-8'))
    tasks = {}
    for tid, meta in graph.get('tasks', {}).items():
        tasks[tid] = new_task(
            tid,
            meta.get('title', tid),
            meta.get('depends_on', []),
            meta.get('touches', []),
            meta.get('parallel_safe_with', []),
            meta.get('required_checks', []),
        )
    stable = graph.get('stable_branch') or gitops.current_branch(repo) or 'main'
    state = {
        'schema_version': 1,
        'revision': 0,
        'project': graph.get('project') or name,
        'stable_branch': stable,
        'current_phase': graph.get('current_phase') or phase,
        'current_gate': 'recovered',
        'updated_at': None,
        'tasks': tasks,
    }
    save_state(repo, state)
    return state
