from __future__ import annotations

from . import gitops
from .errors import TransitionError, ValidationError
from .github import assert_ready as assert_github_ready
from .policy import load_policy
from .state import now

ALLOWED = {
    'planned': {'developing', 'blocked', 'cancelled'},
    'developing': {'testing', 'blocked', 'cancelled'},
    'testing': {'developing', 'review', 'blocked'},
    'review': {'developing', 'ready_for_merge', 'blocked'},
    'ready_for_merge': {'developing', 'approved', 'blocked'},
    'approved': {'merged'},
    'merged': {'deployed'},
    'deployed': set(),
    'blocked': {'planned', 'developing', 'cancelled'},
    'cancelled': set(),
}
INTEGRATED = {'merged', 'deployed'}


def _all_checks_current_and_pass(task: dict) -> tuple[bool, list[str]]:
    bad = []
    commit = task.get('commit')
    for name in task.get('required_checks', []):
        rec = task.get('checks', {}).get(name, {})
        if rec.get('result') != 'pass' or rec.get('commit') != commit:
            bad.append(name)
    return not bad, bad


def _assert_worktree_current(repo, task):
    branch = task.get('branch')
    commit = task.get('commit')
    ledger = task.get('worktree')
    if not branch or not gitops.branch_exists(repo, branch):
        raise ValidationError('task requires an existing branch')
    observed = gitops.worktree_for_branch(repo, branch)
    if not observed:
        raise ValidationError('task requires an active worktree for its branch')
    if ledger and not gitops.same_path(ledger, observed):
        raise ValidationError('ledger worktree path does not match Git worktree path')
    if not gitops.worktree_clean(repo, observed):
        raise ValidationError('task worktree must be clean')
    if commit:
        if not gitops.commit_exists(repo, commit):
            raise ValidationError('recorded task commit does not exist')
        if gitops.branch_head(repo, branch) != gitops.resolve_commit(repo, commit):
            raise ValidationError('recorded task commit is not current task branch HEAD')


def validate_gate(repo, state, task, target, approver=None, deployment_evidence=None):
    remote_snapshot = None
    if target == 'developing':
        for dep in task.get('depends_on', []):
            if state['tasks'][dep].get('status') not in INTEGRATED:
                raise ValidationError(f'dependency {dep} is not integrated')
        branch = task.get('branch')
        if not branch or not gitops.worktree_for_branch(repo, branch):
            raise ValidationError('developing requires a task branch/worktree; use worktree create')
    elif target in {'testing', 'review'}:
        _assert_worktree_current(repo, task)
    elif target == 'ready_for_merge':
        _assert_worktree_current(repo, task)
        if not task.get('commit'):
            raise ValidationError('ready_for_merge requires a recorded task commit')
        ok, bad = _all_checks_current_and_pass(task)
        if not ok:
            raise ValidationError('required checks missing/stale/failing: ' + ', '.join(bad))
        review = task.get('review', {})
        if review.get('status') != 'passed' or review.get('commit') != task.get('commit'):
            raise ValidationError('independent review must be passed for the current task commit')
        # Optional live GitHub gate. This reads the current PR/check state rather
        # than trusting a stale ledger snapshot.
        remote_snapshot = assert_github_ready(
            repo, task, state.get('stable_branch', 'main'), load_policy(repo)
        )
    elif target == 'approved':
        if not approver:
            raise ValidationError('approved transition requires --by HUMAN')
        _assert_worktree_current(repo, task)
    elif target == 'merged':
        commit = task.get('commit')
        stable = state.get('stable_branch', 'main')
        _assert_worktree_current(repo, task)
        if task.get('approval', {}).get('commit') != commit:
            raise ValidationError('human approval is not anchored to the current task commit')
        if not commit or not gitops.commit_on_stable(repo, commit, stable):
            raise ValidationError(f'recorded task commit is not integrated into stable branch {stable}')
    elif target == 'deployed':
        if not deployment_evidence:
            raise ValidationError('deployed transition requires deployment evidence')
    return remote_snapshot


def transition(repo, state, task, target, approver=None, deployment_evidence=None):
    current = task.get('status')
    if target not in ALLOWED.get(current, set()):
        raise TransitionError(f'illegal transition: {current} -> {target}')
    remote_snapshot = validate_gate(repo, state, task, target, approver, deployment_evidence)
    task['status'] = target
    if remote_snapshot is not None:
        task['remote'] = remote_snapshot
        task['pr_url'] = remote_snapshot.get('url')
        task['pr_number'] = remote_snapshot.get('number')
    if target == 'approved':
        task['approval'] = {'by': approver, 'at': now(), 'commit': task.get('commit')}
    if target == 'deployed':
        task['deployment'] = {
            'status': 'deployed',
            'evidence': deployment_evidence,
            'at': now(),
            'commit': task.get('commit'),
        }
    return task
