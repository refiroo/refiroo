"""Check every ledger target and source navigation against the isolated guide build."""
from pathlib import Path
from html.parser import HTMLParser
import importlib.util
import json
import re

NOTES = Path(__file__).resolve().parent
ROOT = NOTES.parents[2]
DOCS = ROOT / 'src/content/docs'
BUILD = ROOT / '_build/C11-FINAL'
spec = importlib.util.spec_from_file_location('coverage_audit', NOTES / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key == 'id')

pages = {str(p.relative_to(DOCS)).removesuffix('.md'): p for p in DOCS.rglob('*.md')}
side = '\n'.join(p.read_text() for p in (ROOT / 'sidebar').glob('*.mjs'))
listed = set(re.findall(r'["\']((?:about|use|examples|model|administer|run|integrate|journeys|guide)/[^"\']+)["\']', side))
assert not pages.keys() - listed - {'index', '404'}, 'page absent from sidebar'
links = {slug: {s.split('#')[0].rstrip('/') for s in re.findall(r'\]\(/docs/([^?)]+)', p.read_text())} for slug, p in pages.items()}
for guide in (s for s in pages if s.startswith('guide/')):
    concepts = {s for s in links[guide] if s in pages and not s.startswith(('guide/', 'journeys/'))}
    assert concepts, ('guide has no documentation link', guide)
    assert any(guide in links[s] for s in concepts), ('no reciprocal documentation link', guide)
ids = {}
for slug, page in pages.items():
    front = page.read_text().split('---', 2)[1]
    assert all(re.search(r'^' + key + r':\s*\S', front, re.M) for key in ('title', 'description', 'reader')), page
    html = BUILD / ('index.html' if slug == 'index' else '404.html' if slug == '404' else slug.removesuffix('/index') + '/index.html')
    assert html.is_file(), ('unbuilt page', slug)
    parser = Ids()
    parser.feed(html.read_text())
    ids[slug] = parser.ids
rows = audit.rows()
for row in rows:
    if row['status'] != 'covered':
        continue
    assert row['targets'], ('no target', row['id'])
    for target in row['targets']:
        assert target['exists'], (row['id'], target)
        if '#' in target['link']:
            anchor = target['link'].split('#', 1)[1]
            assert anchor in ids[target['slug']], ('missing coverage anchor', row['id'], target['link'])
result = dict(pages=len(pages), sidebar_pages=len(pages)-2,
              guides=sum(s.startswith('guide/') for s in pages),
              covered_rows=sum(r['status']=='covered' for r in rows),
              all_rows=len(rows), counts=audit.counts(rows),
              ignored_sidebar_placeholders=sorted(listed-pages.keys()))
(NOTES / 'structure-result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
