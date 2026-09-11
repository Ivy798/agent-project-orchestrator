import pytest
from agent_project_orchestrator.transitions import transition
from agent_project_orchestrator.errors import TransitionError, ValidationError

def task(status='planned'):
    return {'id':'T','status':status,'required_checks':[],'checks':{},'review':{'status':'pending'},'approval':{},'deployment':{}}

def state(): return {'stable_branch':'main'}

def test_illegal_planned_to_merged(tmp_path):
    with pytest.raises(TransitionError): transition(tmp_path,state(),task(),'merged')

def test_approval_requires_human(tmp_path):
    with pytest.raises(ValidationError): transition(tmp_path,state(),task('ready_for_merge'),'approved')

def test_cancelled_dependency_is_not_integrated(tmp_path):
    st={'stable_branch':'main','tasks':{'A':{'status':'cancelled'}}}
    t={'id':'B','status':'planned','depends_on':['A'],'branch':None}
    with pytest.raises(ValidationError): transition(tmp_path,st,t,'developing')
