from __future__ import annotations
import subprocess
from pathlib import Path
import pytest
from agent_project_orchestrator.project import bootstrap, create_task
from agent_project_orchestrator.state import load_state, save_state
from agent_project_orchestrator import gitops
from agent_project_orchestrator.dag import assert_valid_dag
from agent_project_orchestrator.errors import ValidationError, TransitionError
from agent_project_orchestrator.transitions import transition


def test_bootstrap_task_create_worktree_no_dirty_deadlock(gitrepo:Path):
    bootstrap(gitrepo,'Demo')
    assert gitops.is_clean(gitrepo)
    create_task(gitrepo,'TASK-001','First',touches=['apps/api'],required_checks=['unit'])
    assert gitops.is_clean(gitrepo)
    state=load_state(gitrepo)
    wt=gitrepo.parent/'wts'/'TASK-001'; wt.parent.mkdir()
    gitops.run_git(gitrepo,['worktree','add','-b','feature/task-001',str(wt),'main'])
    state['tasks']['TASK-001']['branch']='feature/task-001'; state['tasks']['TASK-001']['worktree']=str(wt); state['tasks']['TASK-001']['status']='developing'; save_state(gitrepo,state)
    assert wt.exists()


def test_fake_commit_rejected(gitrepo:Path):
    bootstrap(gitrepo,'Demo'); create_task(gitrepo,'TASK-001','First')
    assert not gitops.commit_exists(gitrepo,'deadbeef')


def test_ready_gate_and_merge_verification(gitrepo:Path):
    bootstrap(gitrepo,'Demo'); create_task(gitrepo,'TASK-001','First',required_checks=['unit'])
    state=load_state(gitrepo); t=state['tasks']['TASK-001']
    wt=gitrepo.parent/'wt'; gitops.run_git(gitrepo,['worktree','add','-b','feature/task-001',str(wt),'main'])
    (wt/'feature.txt').write_text('x\n')
    gitops.run_git(wt,['add','.']); gitops.run_git(wt,['commit','-m','feat'])
    commit=gitops.head(wt)
    t.update({'status':'developing','branch':'feature/task-001','worktree':str(wt),'commit':commit})
    transition(gitrepo,state,t,'testing')
    transition(gitrepo,state,t,'review')
    t['checks']['unit']={'result':'pass','commit':commit}
    t['review']={'status':'passed','reviewer':'independent','commit':commit}
    transition(gitrepo,state,t,'ready_for_merge')
    transition(gitrepo,state,t,'approved',approver='human-owner')
    with pytest.raises(ValidationError): transition(gitrepo,state,t,'merged')
    # Integrate using normal Git merge, then merged gate should succeed.
    gitops.run_git(gitrepo,['merge','--no-ff','feature/task-001','-m','merge task'])
    transition(gitrepo,state,t,'merged')
    assert t['status']=='merged'


def test_cycle_rejected_before_task_is_saved(gitrepo:Path):
    bootstrap(gitrepo,'Demo')
    create_task(gitrepo,'A','A')
    create_task(gitrepo,'B','B',depends_on=['A'])
    state=load_state(gitrepo)
    state['tasks']['A']['depends_on']=['B']
    with pytest.raises(Exception): assert_valid_dag(state['tasks'])


def test_ready_gate_rejects_stale_check_and_review(gitrepo:Path):
    bootstrap(gitrepo,'Demo'); create_task(gitrepo,'TASK-001','First',required_checks=['unit'])
    state=load_state(gitrepo); t=state['tasks']['TASK-001']
    wt=gitrepo.parent/'wt-stale'; gitops.run_git(gitrepo,['worktree','add','-b','feature/task-stale',str(wt),'main'])
    (wt/'a.txt').write_text('a\n'); gitops.run_git(wt,['add','.']); gitops.run_git(wt,['commit','-m','first'])
    old=gitops.head(wt)
    (wt/'b.txt').write_text('b\n'); gitops.run_git(wt,['add','.']); gitops.run_git(wt,['commit','-m','second'])
    current=gitops.head(wt)
    t.update({'status':'review','branch':'feature/task-stale','worktree':str(wt),'commit':current})
    t['checks']['unit']={'result':'pass','commit':old}
    t['review']={'status':'passed','reviewer':'independent','commit':old}
    with pytest.raises(ValidationError): transition(gitrepo,state,t,'ready_for_merge')


def test_ready_gate_rejects_branch_head_changed_after_recorded_commit(gitrepo:Path):
    bootstrap(gitrepo,'Demo'); create_task(gitrepo,'TASK-001','First',required_checks=['unit'])
    state=load_state(gitrepo); t=state['tasks']['TASK-001']
    wt=gitrepo.parent/'wt-head'; gitops.run_git(gitrepo,['worktree','add','-b','feature/task-head',str(wt),'main'])
    (wt/'a.txt').write_text('a\n'); gitops.run_git(wt,['add','.']); gitops.run_git(wt,['commit','-m','first'])
    old=gitops.head(wt)
    t.update({'status':'review','branch':'feature/task-head','worktree':str(wt),'commit':old})
    t['checks']['unit']={'result':'pass','commit':old}
    t['review']={'status':'passed','reviewer':'independent','commit':old}
    (wt/'later.txt').write_text('later\n'); gitops.run_git(wt,['add','.']); gitops.run_git(wt,['commit','-m','later'])
    with pytest.raises(ValidationError): transition(gitrepo,state,t,'ready_for_merge')
