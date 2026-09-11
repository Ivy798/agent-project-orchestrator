from __future__ import annotations
import subprocess, sys, json, os
from pathlib import Path


def run(repo,*args,check=True):
    env=os.environ.copy()
    # Package is available in test environment through project path.
    cp=subprocess.run([sys.executable,'-m','agent_project_orchestrator.cli','--repo',str(repo),*args],text=True,capture_output=True,env=env)
    if check and cp.returncode!=0: raise AssertionError(cp.stderr+cp.stdout)
    return cp


def test_cli_bootstrap_and_task_commits(gitrepo:Path):
    assert run(gitrepo,'init','--name','Demo').returncode==0
    assert run(gitrepo,'task','create','TASK-001','--title','One','--required-checks','unit').returncode==0
    status=subprocess.run(['git','status','--porcelain'],cwd=gitrepo,text=True,capture_output=True,check=True).stdout
    assert status.strip()==''
    plan=json.loads(run(gitrepo,'plan').stdout)
    assert plan['runnable']==['TASK-001']


def test_cli_unknown_dependency_and_cycle_detection(gitrepo:Path):
    run(gitrepo,'init','--name','Demo')
    cp=run(gitrepo,'task','create','A','--title','A','--depends-on','X',check=False)
    assert cp.returncode!=0
    assert 'unknown dependency' in cp.stderr


def test_check_and_review_order_is_enforced(gitrepo:Path):
    run(gitrepo,'init','--name','Demo')
    run(gitrepo,'task','create','TASK-001','--title','One','--required-checks','unit')
    run(gitrepo,'worktree','create','TASK-001')
    cp=run(gitrepo,'check','record','TASK-001','unit','pass',check=False)
    assert cp.returncode!=0
    assert 'testing/review' in cp.stderr
    cp=run(gitrepo,'review','record','TASK-001','passed','--reviewer','r1',check=False)
    assert cp.returncode!=0
    assert 'review state' in cp.stderr
