from pathlib import Path
import json,re
from datetime import datetime
from zoneinfo import ZoneInfo
notes=Path('guide/_coverage/notes/SH1-GUIDE')
baseline=json.loads((notes/'baseline.json').read_text())
progress=Path('guide/_waves/progress/SH1-GUIDE.md');progress.parent.mkdir(parents=True,exist_ok=True)
map_groups={
 'Security':{'People':'People and access','Groups':'People and access','Roles':'People and access','Sign-in':'People and access','Signing keys':'People and access','Clients':'Connections','Agent access':'Connections'},
 'General':{'About':'This instance','Appearance':'You','Account':'You','Notification email':'You'},
 'Administration':{'AI':'This instance','Deployment':'This instance','Operations':'This instance'},
 'Integration':{'API reference':'Connections','Consumer APIs':'Connections','Webhooks':'Connections','Mail':'This instance'},
 'Data operations':{'Jobs':'This instance','Import profiles':'Workspaces and models','Copy and move':'Workspaces and models'}}
for f in baseline:
 p=Path(f);text=p.read_text();original=text
 steer=Path('guide/_waves/steer/SH1-GUIDE.md')
 if steer.exists() and steer.read_text().strip():
  print('STEERING REQUIRES REVIEW: '+steer.read_text());break
 for old,pages in map_groups.items():
  for page,new in pages.items():text=text.replace('Settings › '+old+' › '+page,'Settings › '+new+' › '+page)
 if f.endswith('administer/roles-and-grants.md'):text=text.replace('**Security › Roles**','**People and access › Roles**')
 if f.endswith('administer/deployment-pages.md'):text=text.replace('**General › About**','**This instance › About**').replace('**Administration › Deployment**','**This instance › Deployment**')
 # These sentences previously put identities from different new groups on one path.
 if f.endswith('administer/audit.md') or f.endswith('guide/administer/find-who-changed-something.md'):
  text=text.replace('**Settings › People and access › People** or **Clients**','**Settings › People and access › People** or **Settings › Connections › Clients**')
 if f.endswith('guide/administer/grant-a-role.md') or f.endswith('guide/administer/narrow-a-grant-to-record-types.md'):
  text=text.replace('**Settings › People and access › People**, **Groups** or **Clients**','**Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients**')
 if text==original:continue
 p.write_text(text)
 with progress.open('a') as log:
  log.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — `{f}`: Updated Settings paths to the task groups in `navigation.ts`; other content retained. No steering file or uncertainty for this page.\n')
 print(f)
