from __future__ import annotations
from collections import defaultdict, deque
from .errors import ValidationError


def validate_dag(tasks: dict) -> list[str]:
    ids = set(tasks)
    errors: list[str] = []
    for tid, task in tasks.items():
        deps = task.get("depends_on", [])
        if tid in deps:
            errors.append(f"{tid}: self-dependency")
        for dep in deps:
            if dep not in ids:
                errors.append(f"{tid}: unknown dependency {dep}")
    if errors:
        return errors

    indeg = {tid: 0 for tid in ids}
    graph = defaultdict(list)
    for tid, task in tasks.items():
        for dep in task.get("depends_on", []):
            graph[dep].append(tid)
            indeg[tid] += 1
    q = deque(sorted([k for k,v in indeg.items() if v == 0]))
    seen = []
    while q:
        n=q.popleft(); seen.append(n)
        for nxt in sorted(graph[n]):
            indeg[nxt]-=1
            if indeg[nxt]==0: q.append(nxt)
    if len(seen) != len(ids):
        cyc = sorted([k for k,v in indeg.items() if v>0])
        errors.append("dependency cycle detected involving: " + ", ".join(cyc))
    return errors


def assert_valid_dag(tasks: dict) -> None:
    errors = validate_dag(tasks)
    if errors:
        raise ValidationError("; ".join(errors))


def topological_order(tasks: dict) -> list[str]:
    assert_valid_dag(tasks)
    indeg = {tid: 0 for tid in tasks}
    graph = defaultdict(list)
    for tid, task in tasks.items():
        for dep in task.get("depends_on", []):
            graph[dep].append(tid); indeg[tid]+=1
    q=deque(sorted([k for k,v in indeg.items() if v==0])); out=[]
    while q:
        n=q.popleft(); out.append(n)
        for nxt in sorted(graph[n]):
            indeg[nxt]-=1
            if indeg[nxt]==0:q.append(nxt)
    return out
