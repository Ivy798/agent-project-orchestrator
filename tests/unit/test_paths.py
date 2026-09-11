from agent_project_orchestrator.paths import path_key, same_path

def test_windows_separator_and_case_normalization():
    assert same_path(r'C:\\Users\\Me\\Worktrees\\TASK-1', 'c:/users/me/worktrees/TASK-1', platform='windows')

def test_unc_windows_normalization():
    assert path_key(r'\\\\Server\\Share\\A', platform='windows') == path_key(r'\\\\server\\share\\a', platform='windows')
