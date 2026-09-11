import os

from agent_project_orchestrator.paths import path_key, same_path

def test_windows_separator_and_case_normalization():
    assert same_path(r'C:\\Users\\Me\\Worktrees\\TASK-1', 'c:/users/me/worktrees/TASK-1', platform='windows')

def test_unc_windows_normalization():
    assert path_key(r'\\\\Server\\Share\\A', platform='windows') == path_key(r'\\\\server\\share\\a', platform='windows')


def test_native_filesystem_identity_handles_windows_short_path_alias(monkeypatch):
    short = r'C:\Users\RUNNER~1\AppData\Local\Temp\apo-selftest\wt'
    long = 'C:/Users/runneradmin/AppData/Local/Temp/apo-selftest/wt'
    monkeypatch.setattr(os.path, 'samefile', lambda a, b: (a, b) == (short, long))
    assert same_path(short, long)
