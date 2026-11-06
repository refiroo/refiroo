from html.parser import HTMLParser
from pathlib import Path
import sys,re
class Reader(HTMLParser):
 def __init__(self):
  super().__init__(); self.main=False; self.skip=0; self.text=[]; self.links=[]; self.images=[]; self.pre=False
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='main': self.main=True
  if t in ('script','style'): self.skip+=1
  if self.main:
   if t=='pre': self.pre=True
   if self.pre and 'ec-line' in a.get('class','').split(): self.text.append('\n')
   if t in ('p','li','pre','h1','h2','h3','h4','tr'): self.text.append('\n')
   if t=='td': self.text.append(' | ')
   if t=='a' and a.get('href','').startswith('/docs/'): self.links.append(a['href'])
   if t=='img': self.images.append((a.get('src'),a.get('alt')))
 def handle_endtag(self,t):
  if self.main and t in ('p','li','pre','h1','h2','h3','h4','tr'): self.text.append('\n')
  if t=='pre': self.pre=False
  if t=='main': self.main=False
  if t in ('script','style'): self.skip-=1
 def handle_data(self,d):
  if self.main and not self.skip: self.text.append(d if self.pre else re.sub(r'\s+',' ',d))
def read(url):
 path=url.split('#')[0].removeprefix('/docs/').lstrip('/')
 p=Path('guide/dist')/path/'index.html'
 r=Reader(); r.feed(p.read_text()); return r
if __name__=='__main__':
 for url in sys.argv[1:]:
  r=read(url); print('\nPAGE',url,'\n',re.sub(r'\n\s*\n','\n',''.join(r.text))); print('LINKS',*dict.fromkeys(r.links),sep='\n'); print('IMAGES',r.images)
