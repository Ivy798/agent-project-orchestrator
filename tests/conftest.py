from __future__ import annotations
import subprocess
from pathlib import Path
import pytest

@pytest.fixture
def gitrepo(tmp_path:Path)->Path:
    repo=tmp_path/'repo'; repo.mkdir()
    subprocess.run(['git','init','-b','main'],cwd=repo,check=True,capture_output=True,text=True)
    subprocess.run(['git','config','user.email','test@example.com'],cwd=repo,check=True)
    subprocess.run(['git','config','user.name','Test User'],cwd=repo,check=True)
    (repo/'seed.txt').write_text('seed\n')
    subprocess.run(['git','add','.'],cwd=repo,check=True)
    subprocess.run(['git','commit','-m','seed'],cwd=repo,check=True,capture_output=True,text=True)
    return repo
