from __future__ import annotations
from pathlib import Path
from .state import load_state, save_state
from . import gitops
from .paths import same_path


def reconcile(repo:Path,apply=False)->list[dict]:
    repo=gitops.repo_root(repo); state=load_state(repo); findings=[]; changed=False
    for tid,t in state['tasks'].items():
        b=t.get('branch'); ledger=t.get('worktree')
        if not b: continue
        if not gitops.branch_exists(repo,b):
            findings.append({'task':tid,'type':'missing_branch','branch':b}); continue
        observed=gitops.worktree_for_branch(repo,b)
        if observed and ledger and not same_path(observed,ledger):
            findings.append({'task':tid,'type':'worktree_path_mismatch','ledger':ledger,'observed':observed})
            if apply: t['worktree']=observed; changed=True
        elif observed and not ledger:
            findings.append({'task':tid,'type':'ledger_missing_worktree','observed':observed})
            if apply: t['worktree']=observed; changed=True
        elif not observed and t.get('status') in {'developing','testing','review','ready_for_merge'}:
            findings.append({'task':tid,'type':'active_task_without_worktree','branch':b})
    if changed: save_state(repo,state)
    return findings
