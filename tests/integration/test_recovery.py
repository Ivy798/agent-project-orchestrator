from pathlib import Path
from agent_project_orchestrator.project import bootstrap, create_task, recover_state_from_task_graph
from agent_project_orchestrator.state import load_state, state_path
from agent_project_orchestrator import gitops


def test_recover_operational_ledger_from_durable_task_graph(gitrepo:Path):
    bootstrap(gitrepo,'Demo')
    create_task(gitrepo,'A','A',touches=['apps/api'])
    create_task(gitrepo,'B','B',depends_on=['A'],touches=['apps/web'])
    state_path(gitrepo).unlink()
    recovered=recover_state_from_task_graph(gitrepo,name='Demo')
    assert set(recovered['tasks'])=={'A','B'}
    assert recovered['tasks']['B']['depends_on']==['A']
    assert recovered['tasks']['A']['status']=='planned'


def test_recover_refuses_to_overwrite_existing_operational_ledger(gitrepo: Path):
    from agent_project_orchestrator.errors import ValidationError
    import pytest

    bootstrap(gitrepo, 'Demo')
    with pytest.raises(ValidationError, match='operational ledger already exists'):
        recover_state_from_task_graph(gitrepo, name='Demo')
