from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def run(repo: Path, env: dict, *args: str, check: bool = True):
    cp = subprocess.run(
        [sys.executable, '-m', 'agent_project_orchestrator.cli', '--repo', str(repo), *args],
        text=True,
        capture_output=True,
        env=env,
    )
    if check and cp.returncode != 0:
        raise AssertionError(cp.stderr + cp.stdout)
    return cp


def make_fake_gh(tmp_path: Path, head_sha: str) -> dict:
    script = tmp_path / 'fakegh.py'
    script.write_text(
        '''import json, os, sys\n\nargs=sys.argv[1:]\nhead=os.environ["FAKE_GH_HEAD_SHA"]\nif args==["--version"]:\n    print("gh version 9.9.9-fake")\n    raise SystemExit(0)\nif args[:2]==["auth","status"]:\n    print("Logged in to github.com as fake-user", file=sys.stderr)\n    raise SystemExit(0)\nif args[:2]==["repo","view"]:\n    print(json.dumps({"nameWithOwner":"fake/project","url":"https://github.com/fake/project","defaultBranchRef":{"name":"main"}}))\n    raise SystemExit(0)\nif args[:2]==["pr","create"]:\n    print("https://github.com/fake/project/pull/7")\n    raise SystemExit(0)\nif args[:2]==["pr","view"]:\n    print(json.dumps({"number":7,"url":"https://github.com/fake/project/pull/7","headRefName":"feature/task-001","headRefOid":head,"baseRefName":"main","isDraft":False,"state":"OPEN","mergeable":"MERGEABLE","mergeStateStatus":"CLEAN","reviewDecision":""}))\n    raise SystemExit(0)\nif args[:2]==["pr","checks"]:\n    print(json.dumps([{"bucket":"pass","name":"CI / test","state":"SUCCESS","workflow":"CI","link":"","startedAt":"","completedAt":""}]))\n    raise SystemExit(0)\nprint("unhandled fake gh args: "+repr(args), file=sys.stderr)\nraise SystemExit(1)\n''',
        encoding='utf-8',
    )
    env = os.environ.copy()
    env['FAKE_GH_HEAD_SHA'] = head_sha
    if os.name == 'nt':
        wrapper = tmp_path / 'gh.cmd'
        wrapper.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding='utf-8')
    else:
        wrapper = tmp_path / 'gh'
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding='utf-8')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    env['PATH'] = str(tmp_path) + os.pathsep + env.get('PATH', '')
    return env


def test_cli_live_github_gate_with_fake_gh(gitrepo: Path, tmp_path: Path):
    env = os.environ.copy()
    run(gitrepo, env, 'init', '--name', 'Demo')
    run(gitrepo, env, 'task', 'create', 'TASK-001', '--title', 'One', '--required-checks', 'unit')

    # Configure remote policy before creating the implementation worktree so
    # the worktree starts from the current stable planning baseline.
    run(
        gitrepo,
        env,
        'github', 'configure', '--enabled', '--require-pr', '--require-checks', '--no-require-review'
    )
    wt_info = json.loads(run(gitrepo, env, 'worktree', 'create', 'TASK-001').stdout)
    wt = Path(wt_info['worktree'])
    (wt / 'feature.txt').write_text('x\n', encoding='utf-8')
    subprocess.run(['git', 'add', '.'], cwd=wt, check=True)
    subprocess.run(['git', 'commit', '-m', 'feat'], cwd=wt, check=True, capture_output=True, text=True)
    sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=wt, check=True, text=True, capture_output=True).stdout.strip()

    env = make_fake_gh(tmp_path, sha)
    run(gitrepo, env, 'task', 'set-commit', 'TASK-001', sha)
    run(gitrepo, env, 'transition', 'TASK-001', 'testing')
    run(gitrepo, env, 'check', 'record', 'TASK-001', 'unit', 'pass')
    run(gitrepo, env, 'transition', 'TASK-001', 'review')
    run(gitrepo, env, 'review', 'record', 'TASK-001', 'passed', '--reviewer', 'independent-agent')
    created = json.loads(run(gitrepo, env, 'pr', 'create', 'TASK-001').stdout)
    assert created['remote']['number'] == 7
    assert created['remote']['head_sha'] == sha

    ready = json.loads(run(gitrepo, env, 'transition', 'TASK-001', 'ready_for_merge').stdout)
    assert ready['status'] == 'ready_for_merge'
    assert ready['remote']['required_checks']['all_pass'] is True
