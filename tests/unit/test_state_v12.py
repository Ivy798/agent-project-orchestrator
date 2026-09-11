from pathlib import Path

import pytest

from agent_project_orchestrator.errors import ValidationError
from agent_project_orchestrator.project import bootstrap
from agent_project_orchestrator.state import load_state, save_state, state_path


def test_state_revision_rejects_stale_writer(gitrepo: Path):
    bootstrap(gitrepo, 'Demo')
    first = load_state(gitrepo)
    stale = load_state(gitrepo)
    rev = first['revision']

    first['current_gate'] = 'one'
    save_state(gitrepo, first)
    assert first['revision'] == rev + 1

    stale['current_gate'] = 'two'
    with pytest.raises(ValidationError, match='stale project state'):
        save_state(gitrepo, stale)

    persisted = load_state(gitrepo)
    assert persisted['current_gate'] == 'one'


def test_atomic_save_leaves_no_temp_file(gitrepo: Path):
    bootstrap(gitrepo, 'Demo')
    state = load_state(gitrepo)
    state['current_gate'] = 'updated'
    save_state(gitrepo, state)
    tmp_files = list(state_path(gitrepo).parent.glob('PROJECT_STATE.*.tmp'))
    assert tmp_files == []


def test_concurrent_writers_do_not_lose_update(gitrepo: Path):
    import threading

    bootstrap(gitrepo, 'Demo')
    a = load_state(gitrepo)
    b = load_state(gitrepo)
    barrier = threading.Barrier(2)
    outcomes = []

    def writer(state, gate):
        state['current_gate'] = gate
        barrier.wait()
        try:
            save_state(gitrepo, state)
            outcomes.append(('ok', gate))
        except ValidationError as exc:
            outcomes.append(('error', str(exc)))

    t1 = threading.Thread(target=writer, args=(a, 'A'))
    t2 = threading.Thread(target=writer, args=(b, 'B'))
    t1.start(); t2.start(); t1.join(); t2.join()

    assert sum(1 for kind, _ in outcomes if kind == 'ok') == 1
    assert sum(1 for kind, _ in outcomes if kind == 'error') == 1
    assert load_state(gitrepo)['current_gate'] in {'A', 'B'}
