from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import gitops
from . import github as github_ops
from .controller import assert_controller_checkout, load_task
from .dag import validate_dag
from .errors import APOError, ValidationError
from .planner import conservative_parallel_set, runnable
from .policy import load_policy, save_policy
from .project import bootstrap, create_task, recover_state_from_task_graph
from .reconcile import reconcile
from .state import load_state, now, save_state
from .transitions import transition


def csv(value):
    return [x.strip() for x in (value or '').split(',') if x.strip()]


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def cmd_init(a):
    state = bootstrap(Path(a.repo), a.name, a.stable_branch, a.phase, not a.no_commit)
    emit(
        {
            'ok': True,
            'project': state['project'],
            'stable_branch': state['stable_branch'],
            'revision': state['revision'],
            'note': (
                'Baseline planning files committed.'
                if not a.no_commit
                else 'Baseline files created but not committed; commit/merge them before worktree creation.'
            ),
        }
    )


def cmd_recover(a):
    state = recover_state_from_task_graph(Path(a.repo), a.name, a.phase)
    emit(
        {
            'ok': True,
            'tasks': list(state['tasks']),
            'revision': state['revision'],
            'note': 'Operational states reset to planned. Run reconcile and inspect Git/PR state before continuing.',
        }
    )


def cmd_task_create(a):
    task, path = create_task(
        Path(a.repo),
        a.id,
        a.title,
        csv(a.depends_on),
        csv(a.touches),
        csv(a.parallel_safe_with),
        csv(a.required_checks),
        not a.no_commit,
    )
    emit(
        {
            'ok': True,
            'task': task,
            'task_file': str(path),
            'note': (
                'Task plan committed.'
                if not a.no_commit
                else 'Task plan is uncommitted; commit/merge before worktree creation.'
            ),
        }
    )


def cmd_task_set_commit(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    if task.get('status') in {'ready_for_merge', 'approved', 'merged', 'deployed'}:
        raise ValidationError('cannot change task commit after ready_for_merge')
    sha = gitops.resolve_commit(repo, a.commit)
    if not sha:
        raise ValidationError('commit does not exist')
    if task.get('branch') and not gitops.commit_on_branch(repo, sha, task['branch']):
        raise ValidationError('commit is not on task branch')
    if task.get('branch') and gitops.branch_head(repo, task['branch']) != sha:
        raise ValidationError('set-commit must point to current task branch HEAD')
    if task.get('commit') != sha:
        task['checks'] = {}
        task['review'] = {'status': 'pending', 'reviewer': None, 'at': None, 'notes': None, 'commit': None}
        task['approval'] = {'by': None, 'at': None, 'commit': None}
        task['remote'] = None
    task['commit'] = sha
    save_state(repo, state)
    emit({'task': a.task, 'commit': sha, 'revision': state['revision']})


def cmd_validate(a):
    repo = gitops.repo_root(Path(a.repo))
    state = load_state(repo)
    errors = validate_dag(state['tasks'])
    out = {
        'ok': not errors,
        'dag_errors': errors,
        'controller_clean': gitops.is_clean(repo),
        'revision': state['revision'],
    }
    emit(out)
    if errors:
        raise SystemExit(2)


def cmd_plan(a):
    repo = gitops.repo_root(Path(a.repo))
    state = load_state(repo)
    chosen, conflicts = conservative_parallel_set(state['tasks'], a.max)
    emit(
        {
            'runnable': runnable(state['tasks']),
            'recommended_parallel_set': chosen,
            'conflicts': conflicts,
            'note': 'Default is conservative. Unknown/overlapping touch areas serialize unless explicitly marked safe.',
        }
    )


def cmd_worktree_create(a):
    repo, state = assert_controller_checkout(Path(a.repo), require_clean=True)
    task = state['tasks'].get(a.task)
    if not task:
        raise ValidationError(f'unknown task: {a.task}')
    if a.task not in runnable(state['tasks']):
        raise ValidationError('task is not runnable; validate dependencies/status first')
    branch = a.branch or f'feature/{a.task.lower()}'
    if gitops.branch_exists(repo, branch):
        raise ValidationError(f'branch already exists: {branch}')
    root = Path(a.worktrees_dir).resolve() if a.worktrees_dir else repo.parent / f'{repo.name}-worktrees'
    root.mkdir(parents=True, exist_ok=True)
    wt = root / a.task
    if wt.exists():
        raise ValidationError(f'worktree path already exists: {wt}')
    base = a.base or state['stable_branch']
    gitops.run_git(repo, ['worktree', 'add', '-b', branch, str(wt), base])
    task['branch'] = branch
    task['worktree'] = str(wt)
    task['status'] = 'developing'
    save_state(repo, state)
    emit({'ok': True, 'task': a.task, 'branch': branch, 'worktree': str(wt), 'base': base})


def cmd_check_record(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    if task.get('status') not in {'testing', 'review'}:
        raise ValidationError('checks may be recorded only during testing/review')
    if not task.get('commit'):
        raise ValidationError('set current task commit before recording checks')
    if gitops.branch_head(repo, task.get('branch', '')) != task['commit']:
        raise ValidationError('task branch HEAD changed; set current commit again before recording checks')
    if a.name not in task.get('required_checks', []):
        raise ValidationError(f'{a.name} is not in required_checks')
    task.setdefault('checks', {})[a.name] = {
        'result': a.result,
        'detail': a.detail,
        'at': now(),
        'commit': task['commit'],
    }
    save_state(repo, state)
    emit(task['checks'][a.name])


def cmd_review_record(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    if task.get('status') != 'review':
        raise ValidationError('independent review may be recorded only in review state')
    if not task.get('commit'):
        raise ValidationError('set current task commit before recording review')
    if a.status == 'passed' and not a.reviewer:
        raise ValidationError('passed review requires --reviewer')
    if gitops.branch_head(repo, task.get('branch', '')) != task['commit']:
        raise ValidationError('task branch HEAD changed; set current commit again before review')
    task['review'] = {
        'status': a.status,
        'reviewer': a.reviewer,
        'at': now(),
        'notes': a.notes,
        'commit': task['commit'],
    }
    save_state(repo, state)
    emit(task['review'])


def cmd_transition(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    transition(repo, state, task, a.to, a.by, a.deployment_evidence)
    save_state(repo, state)
    emit(
        {
            'task': a.task,
            'status': task['status'],
            'approval': task.get('approval'),
            'deployment': task.get('deployment'),
            'remote': task.get('remote'),
            'revision': state['revision'],
        }
    )


def cmd_status(a):
    repo = gitops.repo_root(Path(a.repo))
    state = load_state(repo)
    grouped = {}
    for tid, task in state['tasks'].items():
        grouped.setdefault(task['status'], []).append(tid)
    emit(
        {
            'project': state['project'],
            'phase': state.get('current_phase'),
            'gate': state.get('current_gate'),
            'revision': state.get('revision'),
            'policy': load_policy(repo),
            'tasks_by_status': grouped,
            'runnable': runnable(state['tasks']),
            'worktrees': gitops.worktrees(repo),
        }
    )


def cmd_reconcile(a):
    repo = Path(a.repo)
    if a.apply:
        assert_controller_checkout(repo, require_clean=False)
    findings = reconcile(repo, a.apply)
    emit(
        {
            'findings': findings,
            'applied': a.apply,
            'note': 'Dry-run is the default. Use --apply only after reviewing findings.',
        }
    )


def cmd_cleanup(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    if task['status'] not in {'merged', 'deployed', 'cancelled'}:
        raise ValidationError('cleanup allowed only for merged/deployed/cancelled tasks')
    wt = task.get('worktree')
    branch = task.get('branch')
    if wt and Path(wt).exists():
        if not gitops.is_clean(Path(wt)):
            raise ValidationError('refusing to remove dirty worktree')
        gitops.run_git(repo, ['worktree', 'remove', wt])
    if a.delete_branch and branch:
        cp = gitops.run_git(repo, ['branch', '-d', branch], check=False)
        if cp.returncode != 0:
            raise ValidationError(cp.stderr.strip() or 'branch cannot be safely deleted')
    task['worktree'] = None
    if a.delete_branch:
        task['branch'] = None
    save_state(repo, state)
    emit({'ok': True, 'task': a.task, 'revision': state['revision']})


def cmd_github_preflight(a):
    repo = gitops.repo_root(Path(a.repo))
    emit({'ok': True, **github_ops.preflight(repo)})


def cmd_github_configure(a):
    repo, state = assert_controller_checkout(Path(a.repo), require_clean=True)
    if not a.no_commit:
        gitops.assert_git_identity(repo)
    policy = load_policy(repo)
    cfg = policy.setdefault('github', {})
    if a.enabled is not None:
        cfg['enabled'] = a.enabled
    if a.require_pr is not None:
        cfg['require_pr_for_ready'] = a.require_pr
    if a.require_checks is not None:
        cfg['require_required_checks'] = a.require_checks
    if a.require_review is not None:
        cfg['require_github_review'] = a.require_review
    path = save_policy(repo, policy)
    if not a.no_commit:
        gitops.run_git(repo, ['add', str(path.relative_to(repo))])
        gitops.run_git(repo, ['commit', '-m', 'chore(apo): configure GitHub quality gate'])
    emit({'ok': True, 'policy': policy, 'committed': not a.no_commit})


def _pr_ref(task: dict):
    return task.get('pr_number') or task.get('branch')


def cmd_pr_create(a):
    repo, state, task = load_task(Path(a.repo), a.task, require_clean=True)
    branch = task.get('branch')
    if not branch:
        raise ValidationError('task has no branch/worktree')
    if not task.get('commit'):
        raise ValidationError('set current task commit before creating the PR')
    if gitops.branch_head(repo, branch) != task['commit']:
        raise ValidationError('task branch HEAD changed; set current commit again before creating PR')
    github_ops.preflight(repo)
    if a.push:
        github_ops.push_branch(repo, branch, a.remote)
    body = (
        Path(a.body_file).read_text(encoding='utf-8')
        if a.body_file
        else f"## Goal\n\n{task['title']}\n\n## Task\n\n{a.task}\n\n> Managed by agent-project-orchestrator. Final merge still requires explicit human approval.\n"
    )
    snap = github_ops.create_pr(
        repo,
        branch=branch,
        base=state['stable_branch'],
        title=a.title or f"{a.task}: {task['title']}",
        body=body,
        draft=a.draft,
    )
    task['remote'] = github_ops.snapshot(repo, snap['number'])
    task['pr_number'] = task['remote']['number']
    task['pr_url'] = task['remote']['url']
    save_state(repo, state)
    emit({'ok': True, 'task': a.task, 'remote': task['remote']})


def cmd_pr_status(a):
    repo = gitops.repo_root(Path(a.repo))
    state = load_state(repo)
    task = state.get('tasks', {}).get(a.task)
    if not task:
        raise ValidationError(f'unknown task: {a.task}')
    ref = _pr_ref(task)
    if not ref:
        raise ValidationError('task has no PR reference or branch')
    emit({'task': a.task, 'remote': github_ops.snapshot(repo, ref)})


def cmd_pr_sync(a):
    repo, state, task = load_task(Path(a.repo), a.task)
    ref = _pr_ref(task)
    if not ref:
        raise ValidationError('task has no PR reference or branch')
    task['remote'] = github_ops.snapshot(repo, ref)
    task['pr_number'] = task['remote']['number']
    task['pr_url'] = task['remote']['url']
    save_state(repo, state)
    emit({'ok': True, 'task': a.task, 'remote': task['remote'], 'revision': state['revision']})


def cmd_pr_checks(a):
    repo = gitops.repo_root(Path(a.repo))
    state = load_state(repo)
    task = state.get('tasks', {}).get(a.task)
    if not task:
        raise ValidationError(f'unknown task: {a.task}')
    ref = _pr_ref(task)
    if not ref:
        raise ValidationError('task has no PR reference or branch')
    emit({'task': a.task, 'required_checks': github_ops.required_checks(repo, ref)})


def cmd_selftest(a):
    with tempfile.TemporaryDirectory(prefix='apo-selftest-') as td:
        repo = Path(td) / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(['git', 'config', 'user.email', 'selftest@example.com'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'APO Selftest'], cwd=repo, check=True)
        (repo / 'seed').write_text('seed\n')
        subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'seed'], cwd=repo, check=True, capture_output=True, text=True)
        bootstrap(repo, 'Selftest')
        create_task(repo, 'TASK-001', 'Smoke', touches=['src'], required_checks=['unit'])
        state = load_state(repo)
        task = state['tasks']['TASK-001']
        wt = repo.parent / 'wt'
        gitops.run_git(repo, ['worktree', 'add', '-b', 'feature/task-001', str(wt), 'main'])
        (wt / 'x').write_text('x\n')
        gitops.run_git(wt, ['add', '.'])
        gitops.run_git(wt, ['commit', '-m', 'feat'])
        task['branch'] = 'feature/task-001'
        task['worktree'] = str(wt)
        task['status'] = 'developing'
        task['commit'] = gitops.head(wt)
        transition(repo, state, task, 'testing')
        task['checks']['unit'] = {'result': 'pass', 'commit': task['commit']}
        transition(repo, state, task, 'review')
        task['review'] = {'status': 'passed', 'reviewer': 'selftest', 'commit': task['commit']}
        transition(repo, state, task, 'ready_for_merge')
        transition(repo, state, task, 'approved', approver='selftest-human')
        gitops.run_git(repo, ['merge', '--no-ff', 'feature/task-001', '-m', 'merge'])
        transition(repo, state, task, 'merged')
        emit({'ok': True, 'selftest': 'passed', 'commit': task['commit']})


def parser():
    p = argparse.ArgumentParser(prog='apo')
    p.add_argument('--repo', default='.', help='Git repository path; place before subcommand')
    sp = p.add_subparsers(dest='cmd', required=True)

    q = sp.add_parser('init')
    q.add_argument('--name', required=True)
    q.add_argument('--stable-branch')
    q.add_argument('--phase', default='phase-1')
    q.add_argument('--no-commit', action='store_true')
    q.set_defaults(fn=cmd_init)

    q = sp.add_parser('recover')
    q.add_argument('--name', default='Recovered Project')
    q.add_argument('--phase', default='unknown')
    q.set_defaults(fn=cmd_recover)

    task = sp.add_parser('task')
    tsp = task.add_subparsers(dest='taskcmd', required=True)
    q = tsp.add_parser('create')
    q.add_argument('id')
    q.add_argument('--title', required=True)
    q.add_argument('--depends-on', default='')
    q.add_argument('--touches', default='')
    q.add_argument('--parallel-safe-with', default='')
    q.add_argument('--required-checks', default='')
    q.add_argument('--no-commit', action='store_true')
    q.set_defaults(fn=cmd_task_create)
    q = tsp.add_parser('set-commit')
    q.add_argument('task')
    q.add_argument('commit')
    q.set_defaults(fn=cmd_task_set_commit)

    q = sp.add_parser('validate')
    q.set_defaults(fn=cmd_validate)
    q = sp.add_parser('plan')
    q.add_argument('--max', type=int, default=3)
    q.set_defaults(fn=cmd_plan)

    wt = sp.add_parser('worktree')
    wtsp = wt.add_subparsers(dest='wtcmd', required=True)
    q = wtsp.add_parser('create')
    q.add_argument('task')
    q.add_argument('--base')
    q.add_argument('--branch')
    q.add_argument('--worktrees-dir')
    q.set_defaults(fn=cmd_worktree_create)

    chk = sp.add_parser('check')
    csp = chk.add_subparsers(dest='checkcmd', required=True)
    q = csp.add_parser('record')
    q.add_argument('task')
    q.add_argument('name')
    q.add_argument('result', choices=['pass', 'fail'])
    q.add_argument('--detail')
    q.set_defaults(fn=cmd_check_record)

    rv = sp.add_parser('review')
    rsp = rv.add_subparsers(dest='rvcmd', required=True)
    q = rsp.add_parser('record')
    q.add_argument('task')
    q.add_argument('status', choices=['pending', 'passed', 'failed'])
    q.add_argument('--reviewer')
    q.add_argument('--notes')
    q.set_defaults(fn=cmd_review_record)

    q = sp.add_parser('transition')
    q.add_argument('task')
    q.add_argument('to')
    q.add_argument('--by')
    q.add_argument('--deployment-evidence')
    q.set_defaults(fn=cmd_transition)

    q = sp.add_parser('status')
    q.set_defaults(fn=cmd_status)
    q = sp.add_parser('reconcile')
    q.add_argument('--apply', action='store_true')
    q.set_defaults(fn=cmd_reconcile)
    q = sp.add_parser('cleanup')
    q.add_argument('task')
    q.add_argument('--delete-branch', action='store_true')
    q.set_defaults(fn=cmd_cleanup)

    gh = sp.add_parser('github')
    ghsp = gh.add_subparsers(dest='ghcmd', required=True)
    q = ghsp.add_parser('preflight')
    q.set_defaults(fn=cmd_github_preflight)
    q = ghsp.add_parser('configure')
    q.add_argument('--enabled', action=argparse.BooleanOptionalAction, default=None)
    q.add_argument('--require-pr', action=argparse.BooleanOptionalAction, default=None)
    q.add_argument('--require-checks', action=argparse.BooleanOptionalAction, default=None)
    q.add_argument('--require-review', action=argparse.BooleanOptionalAction, default=None)
    q.add_argument('--no-commit', action='store_true')
    q.set_defaults(fn=cmd_github_configure)

    pr = sp.add_parser('pr')
    prsp = pr.add_subparsers(dest='prcmd', required=True)
    q = prsp.add_parser('create')
    q.add_argument('task')
    q.add_argument('--title')
    q.add_argument('--body-file')
    q.add_argument('--draft', action='store_true')
    q.add_argument('--push', action='store_true')
    q.add_argument('--remote', default='origin')
    q.set_defaults(fn=cmd_pr_create)
    q = prsp.add_parser('status')
    q.add_argument('task')
    q.set_defaults(fn=cmd_pr_status)
    q = prsp.add_parser('sync')
    q.add_argument('task')
    q.set_defaults(fn=cmd_pr_sync)
    q = prsp.add_parser('checks')
    q.add_argument('task')
    q.set_defaults(fn=cmd_pr_checks)

    q = sp.add_parser('selftest')
    q.set_defaults(fn=cmd_selftest)
    return p


def main():
    p = parser()
    a = p.parse_args()
    try:
        a.fn(a)
    except APOError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
