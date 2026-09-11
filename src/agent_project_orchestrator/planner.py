from __future__ import annotations
from .dag import assert_valid_dag, topological_order

INTEGRATED={'merged','deployed'}


def runnable(tasks:dict)->list[str]:
    assert_valid_dag(tasks)
    out=[]
    for tid in topological_order(tasks):
        t=tasks[tid]
        if t.get('status') != 'planned':
            continue
        if all(tasks[d].get('status') in INTEGRATED for d in t.get('depends_on',[])):
            out.append(tid)
    return out


def _segments(path:str)->list[str]:
    return [p.casefold() for p in path.replace('\\','/').strip('/').split('/') if p]


def paths_overlap(a:str,b:str)->bool:
    aa=_segments(a); bb=_segments(b)
    n=min(len(aa),len(bb))
    return bool(n) and aa[:n]==bb[:n]


def task_conflict(a:dict,b:dict)->list[tuple[str,str]]:
    if b['id'] in a.get('parallel_safe_with',[]) or a['id'] in b.get('parallel_safe_with',[]):
        return []
    at=a.get('touches',[]); bt=b.get('touches',[])
    if not at or not bt:
        return [('<unknown>','<unknown>')]
    pairs=[]
    for x in at:
        for y in bt:
            if paths_overlap(x,y): pairs.append((x,y))
    return pairs


def conservative_parallel_set(tasks:dict,max_count:int=3)->tuple[list[str],list[dict]]:
    ids=runnable(tasks); chosen=[]; conflicts=[]
    for tid in ids:
        if len(chosen)>=max(1,max_count): break
        t=tasks[tid]; ok=True
        for cid in chosen:
            c=task_conflict(tasks[cid],t)
            if c:
                conflicts.append({'a':cid,'b':tid,'overlap':c}); ok=False; break
        if ok: chosen.append(tid)
    return chosen,conflicts
