from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import base64
import io
import json
from openpyxl import load_workbook

root=Path(__file__).resolve().parents[3]
built=root/'_build/C11-FIX'
class Page(HTMLParser):
    def __init__(self,path):
        super().__init__(); self.links=[]; self.ids=set(); self.downloads=[]; self.feed(path.read_text())
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        if tag=='a' and 'href' in a:
            self.links.append(a['href'])
            if 'download' in a: self.downloads.append((a['download'],a['href']))
        if tag=='img' and 'src' in a: self.links.append(a['src'])
pages=[
 'guide/use/correct-a-record',
 'guide/model/start-a-draft-from-a-workbook',
 'guide/model/propose-again-with-a-newer-workbook',
 'run/sign-in-and-mail-setup',
]
errors=[]; checked=0; downloads=[]
for slug in pages:
    page=Page(built/slug/'index.html')
    for link in page.links:
        u=urlsplit(link)
        if not u.path.startswith('/docs/') or u.scheme or u.netloc: continue
        if u.path.rstrip('/')=='/docs/api': continue
        dest=built/unquote(u.path.removeprefix('/docs/'))
        if dest.is_dir(): dest=dest/'index.html'
        checked+=1
        if not dest.is_file(): errors.append(f'{slug}: missing {link}'); continue
        if u.fragment and dest.suffix=='.html' and unquote(u.fragment) not in Page(dest).ids:
            errors.append(f'{slug}: missing anchor {link}')
    for name,url in page.downloads:
        assert url.startswith('data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,')
        content=base64.b64decode(url.split(',',1)[1], validate=True)
        source=root/('samples/'+name if not name.endswith('_next.xlsx') else '_coverage/notes/C10-SCREENS/'+name)
        assert content==source.read_bytes()
        wb=load_workbook(io.BytesIO(content))
        downloads.append({'page':slug,'file':name,'bytes':len(content),'matches_source':True,'sheets':wb.sheetnames})
assert len(downloads)==2
assert not errors, errors
print(json.dumps({'pages':len(pages),'static_links_and_images_checked':checked,'errors':errors,'downloads':downloads},indent=2))
