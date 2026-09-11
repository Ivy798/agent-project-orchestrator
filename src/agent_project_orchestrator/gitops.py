from __future__ import annotations
import subprocess
from pathlib import Path
from .errors import GitStateError
from .paths import same_path


def run_git(repo: Path, args: list[str], check: bool=True) -> subprocess.CompletedProcess[str]:
    cp=subprocess.run(["git",*args], cwd=str(repo), text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise GitStateError(cp.stderr.strip() or cp.stdout.strip() or f"git {' '.join(args)} failed")
    return cp


def repo_root(repo: Path) -> Path:
    return Path(run_git(repo,["rev-parse","--show-toplevel"]).stdout.strip()).resolve()


def is_clean(repo: Path) -> bool:
    return not run_git(repo,["status","--porcelain"]).stdout.strip()


def branch_exists(repo: Path, branch: str) -> bool:
    return run_git(repo,["show-ref","--verify","--quiet",f"refs/heads/{branch}"],check=False).returncode==0


def resolve_commit(repo: Path, value: str) -> str:
    cp=run_git(repo,["rev-parse",f"{value}^{{commit}}"],check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""


def commit_exists(repo: Path, commit: str) -> bool:
    return bool(resolve_commit(repo,commit))


def branch_head(repo: Path, branch: str) -> str:
    if not branch_exists(repo,branch): return ""
    return resolve_commit(repo,branch)


def commit_on_branch(repo: Path, commit: str, branch: str) -> bool:
    sha=resolve_commit(repo,commit)
    if not sha or not branch_exists(repo, branch): return False
    return run_git(repo,["merge-base","--is-ancestor",sha,branch],check=False).returncode==0


def commit_on_stable(repo: Path, commit: str, stable: str) -> bool:
    return commit_on_branch(repo, commit, stable)


def current_branch(repo: Path) -> str:
    return run_git(repo,["branch","--show-current"]).stdout.strip()


def head(repo: Path) -> str:
    return resolve_commit(repo,"HEAD")


def worktrees(repo: Path) -> list[dict]:
    raw=run_git(repo,["worktree","list","--porcelain"]).stdout
    out=[]; cur={}
    for line in raw.splitlines()+[""]:
        if not line.strip():
            if cur: out.append(cur); cur={}
            continue
        k,_,v=line.partition(" "); cur[k]=v
    for x in out:
        b=x.get("branch","")
        if b.startswith("refs/heads/"): x["branch"]=b[len("refs/heads/"):]
    return out


def worktree_for_branch(repo: Path, branch: str) -> str|None:
    for wt in worktrees(repo):
        if wt.get("branch")==branch:return wt.get("worktree")
    return None


def worktree_clean(repo: Path, wt_path: str) -> bool:
    p=Path(wt_path)
    if not p.exists(): return False
    return is_clean(p)


def assert_controller_clean(repo: Path) -> None:
    if not is_clean(repo):
        raise GitStateError("Controller checkout is dirty. Commit/merge planning changes or intentionally stash them before creating an implementation worktree.")


def git_identity(repo: Path) -> dict:
    name = run_git(repo,["config","--get","user.name"],check=False).stdout.strip()
    email = run_git(repo,["config","--get","user.email"],check=False).stdout.strip()
    return {"name": name, "email": email, "configured": bool(name and email)}


def assert_git_identity(repo: Path) -> None:
    ident = git_identity(repo)
    if not ident["configured"]:
        raise GitStateError(
            "Git identity is not configured. Set user.name and user.email before a command that creates commits; no files were changed."
        )


def primary_worktree_path(repo: Path) -> str | None:
    items = worktrees(repo)
    return items[0].get("worktree") if items else None
