from __future__ import annotations

import json
from pathlib import Path

from .errors import ValidationError

POLICY_REL = Path('docs/exec-plans/ORCHESTRATOR_POLICY.json')

DEFAULT_POLICY = {
    'schema_version': 1,
    'single_writer_control_plane': True,
    'github': {
        'enabled': False,
        'require_pr_for_ready': False,
        'require_required_checks': False,
        'require_github_review': False,
    },
}


def policy_path(repo: Path) -> Path:
    return repo / POLICY_REL


def load_policy(repo: Path) -> dict:
    p = policy_path(repo)
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_POLICY))
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValidationError(f'invalid orchestrator policy: {exc}') from exc
    if data.get('schema_version') != 1:
        raise ValidationError('unsupported orchestrator policy schema_version')
    gh = data.setdefault('github', {})
    for key, default in DEFAULT_POLICY['github'].items():
        gh.setdefault(key, default)
    data.setdefault('single_writer_control_plane', True)
    return data


def save_policy(repo: Path, data: dict) -> Path:
    if data.get('schema_version') != 1:
        raise ValidationError('unsupported orchestrator policy schema_version')
    p = policy_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return p
