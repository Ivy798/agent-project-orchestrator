from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]

def test_skill_frontmatter_minimal_and_valid():
    text=(ROOT/'SKILL.md').read_text(encoding='utf-8')
    m=re.match(r'^---\n(.*?)\n---\n',text,re.S)
    assert m
    keys=[]
    for line in m.group(1).splitlines():
        if ':' in line and not line.startswith((' ','\t')):
            keys.append(line.split(':',1)[0].strip())
    assert set(keys)=={'name','description'}
    assert 'name: agent-project-orchestrator' in m.group(1)

def test_no_nonstandard_manifest_dependency():
    assert not (ROOT/'manifest.json').exists()

def test_readme_license_and_tests_exist():
    assert (ROOT/'README.md').exists()
    assert (ROOT/'LICENSE').exists()
    assert (ROOT/'tests').is_dir()
