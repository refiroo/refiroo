from pathlib import Path
from datetime import datetime
import json
BASE=Path('guide/_coverage/notes/SCREENS-CAPTIONS')
def steer():
 p=Path('guide/_waves/steer/SCREENS-CAPTIONS.md')
 print(p.read_text() if p.exists() else 'No steering file.')
def replace(page,old,new,kind='caption'):
 p=Path('guide/src/content/docs')/page
 t=p.read_text()
 assert t.count(old)==1,(page,old,t.count(old))
 p.write_text(t.replace(old,new,1))
 log=BASE/'changes.json'; rows=json.loads(log.read_text()) if log.exists() else []
 rows.append(dict(page=page,kind=kind,old=old,new=new));log.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
def caption(index,new):
 r=json.loads((BASE/'audit.json').read_text())[index]
 old=r['caption']; assert old
 replace(r['page'].removeprefix('guide/src/content/docs/'),old,'*Above: '+new+'*')
def alt(index,new):
 r=json.loads((BASE/'audit.json').read_text())[index]
 replace(r['page'].removeprefix('guide/src/content/docs/'),'!['+r['alt']+']','!['+new+']','image description')
def done(text):
 with Path('guide/_waves/progress/SCREENS-CAPTIONS.md').open('a') as f:f.write(f'## {datetime.now().astimezone().isoformat(timespec="seconds")}\n\n{text} No steering file was present.\n\n')
