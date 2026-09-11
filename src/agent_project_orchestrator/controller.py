from __future__ import annotations

from pathlib import Path

from . import gitops
from .errors import ValidationError
from .state import load_state


def primary_worktree(repo: Path) -> Path:
    items = gitops.worktrees(repo)
    if not items:
        raise ValidationError('no Git worktree found')
    return Path(items[0]['worktree']).resolve()


def assert_controller_checkout(
    repo: Path, state: dict | None = None, *, require_clean: bool = False
) -> tuple[Path, dict]:
    """Enforce the single-writer control-plane rule.

    Mutating APO commands must run against the primary worktree, checked out on
    the stable branch. Worktree agents return commits/reports; they do not write
    the global operational ledger directly.
    """
    root = gitops.repo_root(repo)
    if root.resolve() != primary_worktree(root):
        raise ValidationError(
            'state mutation is controller-only: use the primary worktree, not a task worktree'
        )
    loaded = state or load_state(root)
    stable = loaded.get('stable_branch')
    if gitops.current_branch(root) != stable:
        raise ValidationError(f'controller must be on stable branch {stable}')
    if require_clean:
        gitops.assert_controller_clean(root)
    return root, loaded


def load_task(
    repo: Path, task_id: str, *, require_clean: bool = False
) -> tuple[Path, dict, dict]:
    root, state = assert_controller_checkout(repo, require_clean=require_clean)
    task = state.get('tasks', {}).get(task_id)
    if not task:
        raise ValidationError(f'unknown task: {task_id}')
    return root, state, task
