from agent_project_orchestrator.dag import validate_dag, topological_order

def t(deps): return {'depends_on':deps}

def test_valid_order():
    tasks={'A':t([]),'B':t(['A']),'C':t(['B'])}
    assert validate_dag(tasks)==[]
    assert topological_order(tasks)==['A','B','C']

def test_self_dependency():
    assert 'self-dependency' in validate_dag({'A':t(['A'])})[0]

def test_unknown_dependency():
    assert 'unknown dependency' in validate_dag({'A':t(['X'])})[0]

def test_cycle_detection():
    errs=validate_dag({'A':t(['B']),'B':t(['A'])})
    assert any('cycle' in e for e in errs)
