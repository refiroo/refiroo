"""Bounded checks for this page; never execute deployment commands."""
from pathlib import Path
import base64
import re
import subprocess

root = Path(__file__).resolve().parents[4]
page = root / 'guide/src/content/docs/run/install-with-compose.md'
text = page.read_text()
blocks = re.findall(r'^ *```bash\n(.*?)\n *```', text, re.S | re.M)
for i, block in enumerate(blocks, 1):
    script = block.replace('v<version>', 'vTEST').replace('v<next>', 'vNEXT')
    result = subprocess.run(['bash', '-n'], input=script, text=True, capture_output=True)
    assert result.returncode == 0, f'block {i}: {result.stderr}'
print(f'PASS: bash syntax in {len(blocks)} blocks after replacing documented tag placeholders')

# Compare the prescribed token script to the wave exactly, ignoring Markdown indentation.
wave = (root / 'guide/_waves/C5d-DEPLOY.md').read_text()
expected = re.search(r'```bash\n(.*?)\n   ```', wave, re.S).group(1)
expected = '\n'.join(line[3:] if line.startswith('   ') else line for line in expected.splitlines())
actual = next(block for block in blocks if '#!/usr/bin/env bash' in block)
actual = '\n'.join(line[3:] if line.startswith('   ') else line for line in actual.splitlines())
assert actual == expected
print('PASS: GitHub App token script matches wave verbatim')

# Exercise only openssl generation, keeping all generated values in memory.
def openssl(n):
    return subprocess.check_output(['openssl', 'rand', '-base64', str(n)], text=True).strip()
password = openssl(24).translate(str.maketrans('', '', '/+=\n'))
sealing = openssl(32).translate(str.maketrans('+/', '-_'))
cursor = openssl(32)
assert password and re.fullmatch(r'[A-Za-z0-9]+', password)
assert len(base64.urlsafe_b64decode(sealing)) == 32
assert len(base64.b64decode(cursor)) == 32
assert len({password, sealing, cursor}) == 3
print('PASS: secret generation yields database-safe password and two 32-byte keys; values not logged')

links = re.findall(r'\]\((/docs/[^)]+)\)', text)
for link in links:
    slug = link.removeprefix('/docs/').split('#')[0].strip('/')
    assert any((root / 'guide/src/content/docs' / (slug + suffix)).is_file() for suffix in ('.md', '.mdx')), link
print(f'PASS: {len(links)} internal page links resolve to source files')
sidebar = (root / 'guide/sidebar/run.mjs').read_text()
assert '["run/install-with-compose", "Deploy to production with Docker"]' in sidebar
assert len(re.findall(r'^## [1-8]\. ', text, re.M)) == 8
print('PASS: eight ordered steps and sidebar label')

html = root / 'guide/_build/C5d-DEPLOY/run/install-with-compose/index.html'
if html.is_file():
    rendered = html.read_text()
    assert 'Deploy to production with Docker' in rendered
    for i in range(1, 9):
        assert f'id="{i}-' in rendered, f'missing step {i} heading'
    print('PASS: built deployment page has new title and all eight step headings')
