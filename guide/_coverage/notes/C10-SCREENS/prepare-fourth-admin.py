from pathlib import Path
import json
from datetime import datetime
ROOT=Path('guide'); SPEC=ROOT/'_waves/C10.screens.json'
spec=json.loads(SPEC.read_text())
def click(name,role='button',**kw):return {'click':{'role':role,'name':name,'exact':True,**kw}}
def wait(text):return {'waitFor':{'text':text,'exact':False}}
def goto(path):return {'goto':path}
def fill(label,value):return {'fill':{'label':label,'exact':True},'value':value}
def add(name,shows,actions,expect,after=None,**kw):
 if any(s['name']==name for s in spec['screens']):return
 spec['screens'].append(dict(name=name,shows=shows,actions=actions,expect=expect,**({'after':after} if after else {}),**kw))
def save(unit,detail):
 SPEC.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
 with (ROOT/'_waves/progress/C10-SCREENS.md').open('a') as f:f.write('\n## '+datetime.now().astimezone().isoformat(timespec='seconds')+' — '+unit+'\n\n'+detail+'\n')
add('admin-ai-settings','AI settings with assistant and provider on, send level and retention. No setting changes and no expanded call content.',[goto('/settings/ai'),wait('What is switched on')],['What is switched on','Assistant','Provider','What may be sent','Content kept','What the AI provider is asked'],height=1500)
add('run-ai-settings','The same enabled AI configuration for operators; no provider call.',[goto('/settings/ai'),wait('What is switched on')],['What is switched on','Assistant','Provider','What may be sent','Content kept'],height=1500)
add('admin-agent-access-enabled','Agent access connection and catalogues, if MCP is enabled. AI being on does not imply MCP is on; do not enable it to obtain this screen.',[goto('/settings/agent-access'),wait('How to connect')],['How to connect','Address','Limit','Agent clients','Assistants people sign in with'],height=1400)
add('integrate-agent-access-connect','MCP connection address and Claude Code command; read only, requires MCP enabled.',[goto('/settings/agent-access'),wait('How to connect')],['How to connect','Address','Limit','Agent clients'],height=1100)
add('admin-agent-new-client','Unsaved New agent client dialog; never create a client or show its secret.',[goto('/settings/agent-access'),click('New agent client'),{'waitFor':{'role':'dialog','name':'New agent client','exact':True}}],['New agent client','Name','Create and show its secret'],[click('Cancel')])
add('admin-agent-register','Unsaved assistant registration with a loopback return address. No assistant or access is registered.',[goto('/settings/agent-access'),click('Register an assistant'),fill('Name','Guide screenshot assistant'),fill('Return addresses','http://localhost:8480/assistant-return')],['Register an assistant','Return addresses','One per line.','Register'],[fill('Name',''),fill('Return addresses',''),click('Cancel')])
# Existing recipes must follow the newly enabled deployment, rather than expect the former off state.
for s in spec['screens']:
 if s['name']=='admin-webhook-new':
  s.update(shows='Enabled New webhook dialog, unsaved. The localhost URL names this reference instance; no receiver is asserted and no subscription is created.',height=1400,actions=[goto('/settings/webhooks'),click('New webhook'),{'waitFor':{'role':'dialog','name':'New webhook','exact':True}},fill('Name','Guide stop events'),fill('URL','http://localhost:8480/guide-webhook-receiver'),{'select':{'label':'Workspace','exact':True},'value':'Graubünden (graubuenden)'}],expect=['New webhook','Consumer API','Workspace','All events','Filters','Delivery','Create webhook'],after=[fill('Name',''),fill('URL',''),click('Cancel')])
# Only page image captions change: actual enabled-state images must still be reviewed externally.
for rel in ['administer/webhooks.md','guide/administer/create-a-webhook.md']:
 p=ROOT/'src/content/docs'/rel;t=p.read_text();t=t.replace('![Webhooks switched off in this deployment, with Open Deployment available]','![The New webhook dialog with its source, event and delivery choices]');p.write_text(t)
with (ROOT/'_waves/C10.data-changes.md').open('a') as f:f.write('''
## Fourth-round preparation: enabled settings (not executed)

Fourth-round steering says assistant/provider, mail and webhook subscriptions are now enabled. Added AI settings reads and Agent access connection/unsaved client and registration dialogs. MCP availability is a separate unverified prerequisite; no switch, client, registration or access grant is saved. Registration fields are cleared before cancellation. No secrets are created or photographed.

`admin-webhook-new` now opens and cancels the enabled dialog. Its unsaved URL is `http://localhost:8480/guide-webhook-receiver`, belonging to the reference origin; it is **not an established receiver** and is never saved or contacted. URL and DNS rules were read in `backend/app/engine/events/webhook_urls.py` and `webhook_client.py`: HTTP is limited to literal loopback hosts; non-loopback hostnames resolving to loopback, link-local, multicast and unspecified addresses are refused. No receiver is declared in the reference setup, and no server is started. Delivery capture remains deferred. Rotation and paused-state captures also require a saved subscription; creating one would change integration/security settings and expose a one-time signing key, so these recipes do not manufacture one.
''')
save('enabled administration recipes','Applied fourth-round steering: appended six AI/Agent access recipes and corrected the existing New webhook recipe and its two captions. Source labels/routes were checked; MCP and a saved webhook fixture remain unverified. No instance action ran.')
