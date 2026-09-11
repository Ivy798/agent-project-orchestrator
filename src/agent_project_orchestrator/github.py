from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .errors import ValidationError


def _run(repo: Path, args: list[str], *, allowed_codes: set[int] | None = None) -> subprocess.CompletedProcess[str]:
    gh = shutil.which('gh')
    if not gh:
        raise ValidationError('GitHub CLI `gh` is required for GitHub integration but was not found in PATH')
    cp = subprocess.run(
        [gh, *args], cwd=str(repo), text=True, encoding='utf-8', capture_output=True
    )
    allowed = allowed_codes or {0}
    if cp.returncode not in allowed:
        msg = cp.stderr.strip() or cp.stdout.strip() or f"gh {' '.join(args)} failed"
        raise ValidationError(msg)
    return cp


def preflight(repo: Path) -> dict:
    version = _run(repo, ['--version']).stdout.splitlines()[0]
    auth = _run(repo, ['auth', 'status'], allowed_codes={0}).stderr.strip() or 'authenticated'
    view = _run(repo, ['repo', 'view', '--json', 'nameWithOwner,url,defaultBranchRef']).stdout
    data = json.loads(view)
    return {'gh_version': version, 'auth': auth, 'repository': data}


def repo_slug(repo: Path) -> str:
    cp = _run(repo, ['repo', 'view', '--json', 'nameWithOwner'])
    data = json.loads(cp.stdout)
    return data['nameWithOwner']


def push_branch(repo: Path, branch: str, remote: str = 'origin') -> None:
    cp = subprocess.run(['git', 'push', '-u', remote, branch], cwd=str(repo), text=True, capture_output=True)
    if cp.returncode != 0:
        raise ValidationError(cp.stderr.strip() or cp.stdout.strip() or f'failed to push {branch}')


def create_pr(repo: Path, *, branch: str, base: str, title: str, body: str, draft: bool = False) -> dict:
    args = ['pr', 'create', '--head', branch, '--base', base, '--title', title, '--body', body]
    if draft:
        args.append('--draft')
    cp = _run(repo, args)
    url = cp.stdout.strip().splitlines()[-1]
    return view_pr(repo, branch)


def view_pr(repo: Path, branch_or_number: str | int) -> dict:
    fields = 'number,url,headRefName,headRefOid,baseRefName,isDraft,state,mergeable,mergeStateStatus,reviewDecision'
    cp = _run(repo, ['pr', 'view', str(branch_or_number), '--json', fields])
    return json.loads(cp.stdout)


def required_checks(repo: Path, branch_or_number: str | int) -> dict:
    fields = 'bucket,name,state,workflow,link,startedAt,completedAt'
    cp = _run(repo, ['pr', 'checks', str(branch_or_number), '--required', '--json', fields], allowed_codes={0, 8, 1})
    raw = cp.stdout.strip()
    if cp.returncode == 1 and not raw:
        err = cp.stderr.strip()
        low = err.lower()
        if 'no checks reported' in low or 'no required checks' in low:
            checks = []
            return {
                'exit_code': cp.returncode,
                'checks': checks,
                'all_pass': False,
                'has_required_checks': False,
                'pending': False,
                'failing': [],
            }
        raise ValidationError(err or 'gh pr checks failed')
    try:
        checks = json.loads(raw) if raw else []
    except json.JSONDecodeError as exc:
        raise ValidationError(f'invalid JSON from gh pr checks: {exc}') from exc
    return {
        'exit_code': cp.returncode,
        'checks': checks,
        'all_pass': bool(checks) and all(c.get('bucket') == 'pass' for c in checks),
        'has_required_checks': bool(checks),
        'pending': any(c.get('bucket') == 'pending' for c in checks),
        'failing': [c.get('name') for c in checks if c.get('bucket') in {'fail', 'cancel'}],
    }


def snapshot(repo: Path, branch_or_number: str | int) -> dict:
    pr = view_pr(repo, branch_or_number)
    checks = required_checks(repo, pr['number'])
    return {
        'provider': 'github',
        'number': pr['number'],
        'url': pr['url'],
        'head_ref': pr['headRefName'],
        'head_sha': pr['headRefOid'],
        'base_ref': pr['baseRefName'],
        'is_draft': pr['isDraft'],
        'state': pr['state'],
        'mergeable': pr['mergeable'],
        'merge_state_status': pr['mergeStateStatus'],
        'review_decision': pr.get('reviewDecision') or '',
        'required_checks': checks,
    }


def assert_ready(repo: Path, task: dict, stable_branch: str, policy: dict) -> dict | None:
    cfg = policy.get('github', {})
    if not cfg.get('enabled'):
        return None
    if not cfg.get('require_pr_for_ready') and not cfg.get('require_required_checks') and not cfg.get('require_github_review'):
        return None

    ref = task.get('pr_number') or task.get('branch')
    if not ref:
        raise ValidationError('GitHub gate requires a PR, but task has no PR reference/branch')
    snap = snapshot(repo, ref)
    commit = task.get('commit')

    if cfg.get('require_pr_for_ready'):
        if snap['state'] != 'OPEN':
            raise ValidationError(f"GitHub PR must be OPEN; current state is {snap['state']}")
        if snap['is_draft']:
            raise ValidationError('GitHub PR is still draft')
        if snap['base_ref'] != stable_branch:
            raise ValidationError(f"GitHub PR base {snap['base_ref']} does not match stable branch {stable_branch}")
        if snap['head_sha'] != commit:
            raise ValidationError('GitHub PR head SHA does not match the current task commit')
        if snap['mergeable'] == 'CONFLICTING':
            raise ValidationError('GitHub reports the PR has merge conflicts')

    if cfg.get('require_required_checks'):
        check_state = snap['required_checks']
        if not check_state['has_required_checks']:
            raise ValidationError('GitHub policy requires required checks, but none are configured/reported')
        if not check_state['all_pass']:
            raise ValidationError('GitHub required checks are not all passing')

    if cfg.get('require_github_review') and snap['review_decision'] != 'APPROVED':
        raise ValidationError(f"GitHub reviewDecision must be APPROVED; current value is {snap['review_decision'] or '<empty>'}")

    return snap
