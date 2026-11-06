from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
import json
base=Path('guide/dist')
roots=['','run/overview','run/install-with-compose','run/production-checklist','journeys','journeys/look-after-data','journeys/change-with-approval','journeys/work-with-an-assistant','journeys/shape-a-model','journeys/integrate-a-system','journeys/manage-access','journeys/run-the-service','journeys/receive-notices']
class Links(HTMLParser):
 def __init__(self):super().__init__();self.main=False;self.links=[];self.images=[];self.ids=set()
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='main':self.main=True
  if 'id' in a:self.ids.add(a['id'])
  if self.main and t=='a':self.links.append(a.get('href',''))
  if self.main and t=='img':self.images.append(a.get('src',''))
 def handle_endtag(self,t):
  if t=='main':self.main=False
cache={}
def get(path):
 if path not in cache:
  r=Links();r.feed((base/path/'index.html').read_text());cache[path]=r
 return cache[path]
selected=set(roots)
for root in roots:
 for link in get(root).links:
  u=urlsplit(link)
  if u.scheme or u.netloc:continue
  p=u.path
  if p.startswith('/docs/') and not p.startswith('/docs/api'):selected.add(unquote(p.removeprefix('/docs/').strip('/')))
issues=[];checked=0;runtime=0;images=set()
for path in sorted(selected):
 r=get(path)
 for link in r.links:
  url=urlsplit(link)
  if url.scheme or url.netloc:continue
  if not url.path.startswith('/docs/') and url.path!='':continue
  if url.path.startswith('/docs/api'):runtime+=1;continue
  target=unquote(url.path.removeprefix('/docs/').strip('/')) if url.path else path
  p=base/target/'index.html'
  if not p.exists():issues.append({'page':path,'link':link,'reason':'missing page'});continue
  if url.fragment and unquote(url.fragment) not in get(target).ids:issues.append({'page':path,'link':link,'reason':'missing fragment'})
  checked+=1
 for src in r.images:
  images.add(src)
  p=base/src.removeprefix('/docs/').lstrip('/')
  if not p.exists():issues.append({'page':path,'image':src,'reason':'missing image'})
result={'selected_pages':len(selected),'static_links_checked':checked,'runtime_api_links_excluded':runtime,'unique_image_references':len(images),'issues':issues}
Path('guide/_coverage/notes/C11-READER/link-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
