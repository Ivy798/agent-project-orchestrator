from pathlib import Path
import json
import subprocess

import pytest

from agent_project_orchestrator import github
from agent_project_orchestrator.errors import ValidationError


def cp(stdout='', stderr='', code=0):
    return subprocess.CompletedProcess(['gh'], code, stdout=stdout, stderr=stderr)


def test_snapshot_parses_live_pr_and_required_checks(monkeypatch, tmp_path: Path):
    def fake_run(repo, args, allowed_codes=None):
        if args[:2] == ['pr', 'view']:
            return cp(json.dumps({
                'number': 12,
                'url': 'https://github.com/o/r/pull/12',
                'headRefName': 'feature/task-1',
                'headRefOid': 'abc123',
                'baseRefName': 'main',
                'isDraft': False,
                'state': 'OPEN',
                'mergeable': 'MERGEABLE',
                'mergeStateStatus': 'CLEAN',
                'reviewDecision': 'APPROVED',
            }))
        if args[:2] == ['pr', 'checks']:
            return cp(json.dumps([
                {'bucket': 'pass', 'name': 'test', 'state': 'SUCCESS', 'workflow': 'CI', 'link': '', 'startedAt': '', 'completedAt': ''}
            ]))
        raise AssertionError(args)

    monkeypatch.setattr(github, '_run', fake_run)
    snap = github.snapshot(tmp_path, 'feature/task-1')
    assert snap['number'] == 12
    assert snap['head_sha'] == 'abc123'
    assert snap['required_checks']['all_pass'] is True


def test_required_checks_pending_is_not_ready(monkeypatch, tmp_path: Path):
    def fake_run(repo, args, allowed_codes=None):
        return cp(json.dumps([
            {'bucket': 'pending', 'name': 'test', 'state': 'PENDING', 'workflow': 'CI', 'link': '', 'startedAt': '', 'completedAt': ''}
        ]), code=8)

    monkeypatch.setattr(github, '_run', fake_run)
    result = github.required_checks(tmp_path, 1)
    assert result['pending'] is True
    assert result['all_pass'] is False


def test_required_checks_real_error_is_not_treated_as_empty(monkeypatch, tmp_path: Path):
    def fake_run(repo, args, allowed_codes=None):
        return cp('', 'authentication failed', 1)

    monkeypatch.setattr(github, '_run', fake_run)
    with pytest.raises(ValidationError, match='authentication failed'):
        github.required_checks(tmp_path, 1)


def test_assert_ready_requires_matching_head_and_checks(monkeypatch, tmp_path: Path):
    policy = {
        'github': {
            'enabled': True,
            'require_pr_for_ready': True,
            'require_required_checks': True,
            'require_github_review': True,
        }
    }
    task = {'commit': 'abc123', 'branch': 'feature/task-1', 'pr_number': 12}
    good = {
        'provider': 'github', 'number': 12, 'url': 'u', 'head_ref': 'feature/task-1',
        'head_sha': 'abc123', 'base_ref': 'main', 'is_draft': False, 'state': 'OPEN',
        'mergeable': 'MERGEABLE', 'merge_state_status': 'CLEAN', 'review_decision': 'APPROVED',
        'required_checks': {'has_required_checks': True, 'all_pass': True, 'pending': False, 'failing': [], 'checks': []},
    }
    monkeypatch.setattr(github, 'snapshot', lambda repo, ref: good)
    assert github.assert_ready(tmp_path, task, 'main', policy) == good

    bad = dict(good)
    bad['head_sha'] = 'other'
    monkeypatch.setattr(github, 'snapshot', lambda repo, ref: bad)
    with pytest.raises(ValidationError, match='head SHA'):
        github.assert_ready(tmp_path, task, 'main', policy)


def test_no_required_checks_is_a_valid_snapshot_but_not_a_passing_gate(monkeypatch, tmp_path: Path):
    def fake_run(repo, args, allowed_codes=None):
        return cp('', 'no checks reported on the branch', 1)

    monkeypatch.setattr(github, '_run', fake_run)
    result = github.required_checks(tmp_path, 1)
    assert result['has_required_checks'] is False
    assert result['all_pass'] is False
