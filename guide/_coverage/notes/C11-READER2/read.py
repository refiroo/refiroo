from html.parser import HTMLParser
from pathlib import Path
import sys
class Reader(HTMLParser):
 def __init__(self): super().__init__(); self.active=False; self.hide=0
 def handle_starttag(self,t,a):
  if t=='main': self.active=True
  if self.active and t in ('script','style'): self.hide+=1
  if self.active and t=='a':
   href=dict(a).get('href','')
   if href: print(' [LINK '+href+'] ',end='')
  if self.active and t in ('p','li','h1','h2','h3','pre','tr'): print()
 def handle_endtag(self,t):
  if t=='main': self.active=False
  if self.active and t in ('script','style'): self.hide-=1
 def handle_data(self,d):
  if self.active and not self.hide: print(d,end='')
for arg in sys.argv[1:]:
 print('\nPAGE',arg); p=Path('guide/dist')/arg.strip('/')
 if p.is_dir(): p=p/'index.html'
 Reader().feed(p.read_text())
