from pathlib import Path
from datetime import datetime
import json
b=Path('guide');p=b/'_waves/C10.screens.json';spec=json.loads(p.read_text());by={s['name']:s for s in spec['screens']}
def go(path):return {'goto':path}
def click(name,role='button',**extra):return {'click':{'role':role,'name':name,'exact':True,**extra}}
def wait(text,timeout=15000):return {'waitFor':{'text':text,'exact':False},'timeout':timeout}
def heading(name):return {'waitFor':{'role':'heading','name':name,'exact':True}}
def nav(label):return [go('/settings/ai'),heading('AI'),click(label,'link')]
# The radio inputs deliberately have pointer-events:none; click their visible label.
for name in ['use-ask-filters','use-ask-partial']:
 s=by[name]
 for a in s['actions']:
  if a.get('click',{}).get('name')=='Ask':a['click']={'css':'.ask-switch label:has-text("Ask")'}
 s['actions']=[a for a in s['actions'] if a.get('wait')!=90000]
 for a in s['actions']:
  if 'waitFor' in a:a['timeout']=300000
by['use-history-explained']['actions'][0]=go('/settings/workspaces/graubuenden/activity')
s=by['admin-mail-messages'];s['actions']=[a for a in s['actions'] if a.get('waitFor',{}).get('text') not in ['Mail is not set up','No message is in this state.']];s['actions'].insert(1,heading('Mail'));s['expect']=['Messages','State','Refresh'];s['shows']='Mail Messages filtered to Waiting, whether rows exist or not. No dependency on the former unconfigured state or an empty outbox. No message is sent or stopped.'
# Navigate using the rendered settings link, rather than assume the server deep link reaches the page.
for name in ['admin-agent-access-enabled','integrate-agent-access-connect','admin-agent-new-client','admin-agent-register','admin-agent-calls']:
 s=by[name];s['actions']=nav('Agent access')+[heading('Agent access')]+s['actions'][1:]
 s['actions'].insert(4,wait('How to connect'))
 s['shows']+=' Enabled MCP is an external prerequisite: AgentAccessPage hides these controls when Agent access is off. The supplied log does not establish enabled MCP. Do not enable it; report the off/error screen if this prerequisite fails.'
s=by['notification-email-digest'];s['actions']=nav('Notification email')+[heading('Notification email'),{'waitFor':{'css':'.account-page, .account-muted, .inline-error'}}];s['expect']=['Notification email','Workspaces I follow'];s['shows']='Notification email settings, not a sent digest email. Read existing preferences and any no-email/unconfigured explanation. An account without an address has no digest controls. No email is enabled, preference changed or message sent. Navigate through the working Settings sidebar.'
# Accept the actual zero-proposal result; never ask/charge again to force a target.
s=by['use-mapping-proposal-result'];s['expect']=[x for x in s['expect'] if x!='Show proposed'];s['actions']=[a for a in s['actions'] if a.get('wait')!=180000]
for a in s['actions']:
 if a.get('waitFor',{}).get('text')=='Targets proposed':a['timeout']=300000
s['shows']+=' Fourth capture already completed: 0 proposed, 1 no likely target, 0 changed meanwhile. Keep the existing image; do NOT rerun this charged setup for the retake.'
s['after']=[click('Close')]
s=by['use-mapping-proposed'];s['actions']=[go('/apps/systems/change-sets?workspaceKey=graubuenden'),click('Open change set',**{'in':{'css':'.change-set-card:has-text("C10 AI mapping proposals")'}}),click('Codes to stops','tab'),{'click':{'css':'.theme-choice label:has-text("Proposed")'}}];s['expect']=['Codes to stops','Proposed'];s['shows']='Read the retained C10 AI mapping proposals change set and its Proposed filter. The previous job offered zero targets, so capture the honest empty Proposed grid, without confidence/reason rows. No new proposal request, mapping edit or publication. An absent named change set is reported, never recreated.'
# Recover the already created task; do not repeat file upload/task creation.
s=by['use-assistant-stopped'];s['actions']=[go('/settings/jobs'),{'click':{'css':'tr:has-text("Graubünden") a.job-name:has-text("Assistant: reading a workbook")'}},click('Open the load','link'),{'waitFor':{'css':'h2:has-text("You stopped the assistant"), h2:has-text("The assistant stopped")'},'timeout':300000}];s['expect']=['Nothing was installed or loaded','Tell the assistant how to go on','Send to the assistant','Discard this task'];s['shows']='Recover the existing workbook task started and asked to stop in the fourth capture: newest Graubünden Assistant: reading a workbook job, Open the load. Wait for its real stopped/failed state; no new task or Stop request. If other assistant jobs have since run, replace this lookup with the recorded task URL before execution. If it already has a proposal, report that state rather than start another task.'
s=by['use-assistant-proposal'];s['actions']=[{'waitFor':{'css':'button:has-text("Go on as it was"), button:has-text("Try again as it was")'},'timeout':300000},{'click':{'css':'button:has-text("Go on as it was"), button:has-text("Try again as it was")'}},wait('The assistant’s proposal',300000)];s['shows']='Resume/retry the same recovered task ONCE using the actual continuation action. This can incur provider turns. Wait up to five minutes for its checked proposal; do not create a duplicate. All six task captures must run together, in their now contiguous manifest order.'
# All provider/task result waits use real waits, not fixed sleeps plus a 15-second timeout.
for s in spec['screens']:
 if s['name'] in ['use-record-history-explained','model-account-facts','admin-ai-test-answered','run-ai-provider-calls','model-assistant-workbook-proposal','use-assistant-loaded','model-assistant-workbook-loaded','use-assistant-reload']:
  s['actions']=[a for a in s['actions'] if a.get('wait') not in [90000,300000]]
  for a in s['actions']:
   if 'waitFor' in a:a['timeout']=300000
s=by['use-history-explained'];s['actions']=[a for a in s['actions'] if a.get('wait')!=90000]
for a in s['actions']:
 if 'waitFor' in a:a['timeout']=300000
chain=['use-assistant-stopped','use-assistant-proposal','model-assistant-workbook-proposal','use-assistant-loaded','model-assistant-workbook-loaded','use-assistant-reload']
rest=[s for s in spec['screens'] if s['name'] not in chain];idx=next(i for i,s in enumerate(rest) if s['name']=='use-assistant-workbook')+1
spec['screens']=rest[:idx]+[by[n] for n in chain]+rest[idx:]
p.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
# Page captions describe existing evidence and distinguish a zero-result run.
d=b/'src/content/docs'
p=d/'guide/use/propose-targets.md';t=p.read_text().replace('5. Choose **Show proposed** to open','5. When at least one target was proposed, choose **Show proposed** to open').replace('![The proposal job result with counts, warnings and Show proposed]','![A finished proposal job with no proposed targets, one source left unmapped and Close]');t=t.replace('6. Review the whole change set','   If no target was proposed, **Show proposed** is absent. Choose **Close** and investigate\n   the unmapped sources manually.\n6. Review the whole change set');p.write_text(t)
p=d/'use/mapping-grids.md';t=p.read_text().replace('![A change-set mapping grid narrowed to Proposed with AI confidence and reasons]','![The Proposed filter in a change-set mapping grid; it is empty when no target was offered]');p.write_text(t)
p=d/'guide/use/continue-an-assistant-task.md';t=p.read_text().replace('![A task stopped by its requester, with the words box and continuation actions]','![A stopped assistant task with its reason, words box and continuation actions]');p.write_text(t)
p=d/'use/notifications-settings.md';t=p.read_text().replace('![Notification email delivery choices and the digest schedule options]','![Notification email settings with the saved choices or the reason email choices are unavailable]');t=t.replace('## When email does not arrive','There is no browser view of a sent digest. Read the message in the receiving mailbox;\nuse **Notification email** to check its saved delivery choices and schedule.\n\n## When email does not arrive');p.write_text(t)
with (b/'_waves/progress/C10-SCREENS.md').open('a') as f:f.write('\n## '+datetime.now().astimezone().isoformat(timespec='seconds')+' — failed recipe corrections\n\nApplied the latest capture feedback and reread steering: corrected Ask label hit targets, Activity path, Mail state assumptions and sidebar navigation; added 300000 ms provider/task waits. Reused the existing task via Jobs, made its six captures contiguous and preserved the zero-proposal mapping result; updated the three related Use captions plus notification settings. MCP-enabled controls remain conditional on deployment state, not renamed.\n')
