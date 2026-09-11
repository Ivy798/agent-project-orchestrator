from pathlib import Path
import subprocess

import pytest

from agent_project_orchestrator.controller import assert_controller_checkout
from agent_project_orchestrator.errors import GitStateError, ValidationError
from agent_project_orchestrator.project import bootstrap, create_task
from agent_project_orchestrator import gitops


def test_init_missing_identity_fails_before_writing(gitrepo: Path):
    subprocess.run(['git', 'config', '--unset', 'user.name'], cwd=gitrepo, check=False)
    subprocess.run(['git', 'config', '--unset', 'user.email'], cwd=gitrepo, check=False)
    before = subprocess.run(['git', 'status', '--porcelain'], cwd=gitrepo, text=True, capture_output=True, check=True).stdout
    assert before.strip() == ''

    with pytest.raises(GitStateError, match='Git identity is not configured'):
        bootstrap(gitrepo, 'Demo')

    after = subprocess.run(['git', 'status', '--porcelain'], cwd=gitrepo, text=True, capture_output=True, check=True).stdout
    assert after.strip() == ''
    assert not (gitrepo / 'AGENTS.md').exists()


def test_task_create_missing_identity_fails_before_writing(gitrepo: Path):
    bootstrap(gitrepo, 'Demo')
    subprocess.run(['git', 'config', '--unset', 'user.name'], cwd=gitrepo, check=False)
    subprocess.run(['git', 'config', '--unset', 'user.email'], cwd=gitrepo, check=False)

    with pytest.raises(GitStateError, match='Git identity is not configured'):
        create_task(gitrepo, 'TASK-001', 'One')

    assert not (gitrepo / 'docs/exec-plans/tasks/TASK-001.md').exists()
    assert gitops.is_clean(gitrepo)


def test_task_worktree_cannot_be_controller_writer(gitrepo: Path):
    bootstrap(gitrepo, 'Demo')
    create_task(gitrepo, 'TASK-001', 'One')
    wt = gitrepo.parent / 'wt-controller-only'
    gitops.run_git(gitrepo, ['worktree', 'add', '-b', 'feature/controller-only', str(wt), 'main'])

    with pytest.raises(ValidationError, match='controller-only'):
        assert_controller_checkout(wt)
