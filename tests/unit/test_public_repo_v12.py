from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_public_repo_files_exist():
    for rel in [
        'README.md', 'LICENSE', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md',
        'agents/openai.yaml', '.github/workflows/ci.yml', '.github/workflows/release.yml',
        'examples/minimal-project/README.md', 'MANIFEST.in', 'scripts/apo.py'
    ]:
        assert (ROOT / rel).exists(), rel


def test_version_is_consistent():
    init = (ROOT / 'src/agent_project_orchestrator/__init__.py').read_text(encoding='utf-8')
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert '__version__ = "1.2.0"' in init
    assert 'version = "1.2.0"' in pyproject
    assert 'v1.2.0' in readme


def test_openai_yaml_has_expected_interface_and_skill_prompt():
    text = (ROOT / 'agents/openai.yaml').read_text(encoding='utf-8')
    assert 'display_name:' in text
    assert 'short_description:' in text
    assert '$agent-project-orchestrator' in text


def test_skill_and_readme_share_controller_boundary():
    skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8').lower()
    readme = (ROOT / 'README.md').read_text(encoding='utf-8').lower()
    for phrase in ['single-writer', 'explicit human approval']:
        assert phrase in skill
        assert phrase in readme


def test_public_and_runtime_templates_are_identical():
    public_dir = ROOT / 'assets/templates'
    runtime_dir = ROOT / 'src/agent_project_orchestrator/templates'
    assert {p.name for p in public_dir.glob('*.md')} == {p.name for p in runtime_dir.glob('*.md')}
    for src in runtime_dir.glob('*.md'):
        assert (public_dir / src.name).read_bytes() == src.read_bytes(), src.name
