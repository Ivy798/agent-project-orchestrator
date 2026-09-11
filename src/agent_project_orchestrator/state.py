from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .dag import assert_valid_dag
from .errors import ValidationError

STATE_REL = Path('.agent-project/PROJECT_STATE.json')
LOCK_REL = Path('.agent-project/PROJECT_STATE.lock')
LOCK_TIMEOUT_SECONDS = 5.0
STALE_LOCK_SECONDS = 60.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_path(repo: Path) -> Path:
    return repo / STATE_REL


def lock_path(repo: Path) -> Path:
    return repo / LOCK_REL


def load_state(repo: Path) -> dict:
    p = state_path(repo)
    if not p.exists():
        raise ValidationError(f'Missing project state: {p}')
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValidationError(f'Invalid project state JSON: {p}: {exc}') from exc
    validate_state(data)
    return data


def _disk_revision(p: Path) -> int | None:
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValidationError(f'Cannot safely update corrupted project state: {p}: {exc}') from exc
    rev = data.get('revision', 0)
    if not isinstance(rev, int) or rev < 0:
        raise ValidationError('project state revision must be a non-negative integer')
    return rev


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except (OSError, AttributeError):
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


@contextmanager
def _state_lock(repo: Path):
    """Cross-platform lock-file serialization for short controller writes.

    O_EXCL makes lock creation atomic on normal local filesystems. The lock is
    intentionally held only around revision comparison + atomic replacement.
    A lock older than STALE_LOCK_SECONDS is treated as left behind by a crashed
    writer and is removed once before retrying.
    """
    lp = lock_path(repo)
    lp.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(json.dumps({'pid': os.getpid(), 'created_at': now()}) + '\n')
                fh.flush()
                os.fsync(fh.fileno())
            break
        except FileExistsError:
            try:
                age = time.time() - lp.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > STALE_LOCK_SECONDS:
                try:
                    lp.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise ValidationError(
                    f'project state is locked by another controller process: {lp}'
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lp.unlink()
        except FileNotFoundError:
            pass


def save_state(repo: Path, data: dict) -> None:
    """Serialize, revision-check, and atomically replace the controller ledger."""
    validate_state(data)
    p = state_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)

    with _state_lock(repo):
        expected = data.get('revision', 0)
        current = _disk_revision(p)
        if current is None:
            if expected not in (0, None):
                raise ValidationError(
                    f'stale project state: expected revision {expected}, but ledger does not exist'
                )
            current = 0
        elif current != expected:
            raise ValidationError(
                f'stale project state: in-memory revision {expected}, on-disk revision {current}; reload before writing'
            )

        next_data = json.loads(json.dumps(data))
        next_data['revision'] = current + 1
        next_data['updated_at'] = now()
        validate_state(next_data)
        payload = json.dumps(next_data, ensure_ascii=False, indent=2) + '\n'

        fd, tmp_name = tempfile.mkstemp(
            prefix='PROJECT_STATE.', suffix='.tmp', dir=str(p.parent)
        )
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, p)
            _fsync_dir(p.parent)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)

        data.clear()
        data.update(next_data)


def validate_state(data: dict) -> None:
    if data.get('schema_version') != 1:
        raise ValidationError('Unsupported/missing schema_version')
    revision = data.get('revision', 0)
    if not isinstance(revision, int) or revision < 0:
        raise ValidationError('revision must be a non-negative integer')
    if not data.get('stable_branch'):
        raise ValidationError('stable_branch is required')
    tasks = data.get('tasks')
    if not isinstance(tasks, dict):
        raise ValidationError('tasks must be an object')
    assert_valid_dag(tasks)


def new_task(tid, title, depends_on=None, touches=None, parallel_safe_with=None, required_checks=None) -> dict:
    return {
        'id': tid,
        'title': title,
        'status': 'planned',
        'depends_on': depends_on or [],
        'touches': touches or [],
        'parallel_safe_with': parallel_safe_with or [],
        'required_checks': required_checks or [],
        'checks': {},
        'review': {'status': 'pending', 'reviewer': None, 'at': None, 'notes': None, 'commit': None},
        'approval': {'by': None, 'at': None, 'commit': None},
        'branch': None,
        'worktree': None,
        'commit': None,
        'pr_url': None,
        'pr_number': None,
        'remote': None,
        'deployment': {'status': 'not_required', 'evidence': None, 'at': None},
        'notes': [],
    }
