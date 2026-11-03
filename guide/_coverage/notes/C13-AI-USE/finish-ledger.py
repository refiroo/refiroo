from pathlib import Path
import re
b=Path(__file__).resolve().parents[3]
p=b/'_waves/reconcile/C13-AI-USE.md'
if '## Remaining heading dispositions' in p.read_text():
 p.write_text(p.read_text().split('## Remaining heading dispositions')[0])
with p.open('a') as f:
 f.write('''
## Remaining heading dispositions

Each row below is saved before advancing to the next heading. Current reader behavior was
checked against the named screen/engine files above. Package test logs, real-workbook results,
implementation-only history and unrelated non-AI packages were not read in full or treated as
current validation. Where an entry says handoff it identifies another reader, not completed work
in that other section. Earlier tables contain the detailed reconciliations for the main headings.

| Source heading | Outcome and destination | Disagreement or limit |
| --- | --- | --- |
''')
plan=Path('docs/BASE_0_16_IMPLEMENTATION_PLAN.md').read_text().splitlines()
existing=p.read_text()
for line_no,line in enumerate(plan,1):
 if not re.match(r'^#{2,4} ',line):continue
 title=re.sub(r'^#+ ','',line)
 # Existing detailed heading rows use a short heading without the dated suffix.
 short=re.sub(r' \(.*','',title)
 if f'BASE_0_16_IMPLEMENTATION_PLAN — {short} |' in existing:continue
 if line_no>=2238:
  result='Historical assistant design: superseded by AP8/AP10. Current task documented in `use/loading-with-the-assistant`.'
  limit='Heading disposition only; historical step/tool formats are not instructions for current users.'
 elif title.startswith(('WM1','Decisions (recommended','The Apply dialog','Tests (cases','Delivery')):
  result='Non-AI model-editor work; Model section owns it. No steward AI page added for this heading.'
  limit='Heading/scope checked; detailed implementation and tests excluded.'
 elif title.startswith('AO3'):
  result='Non-AI notifications: existing `use/notifications-settings` and its guides remain the home.'
  limit='J57 confirms fixed wording and no provider; no AI instructions added.'
 elif title.startswith(('Tests','Door check','R:', 'R record','AI usage','Exit gate')):
  result='Delivery, architectural review or release evidence; not product instructions. Usage concepts covered in `use/ai-and-your-data`.'
  limit='Only relevant excerpts read; historical timings, test logs and costs are not current checks or price promises.'
 elif title.startswith(('AG1','AG2','AG3')):
  result='Steward sign-in/session effects in `use/ai-and-your-data` and `use/account`; prepared-work limits and marks in `use/history`.'
  limit='Heading excerpts, F30, J51–J53, current Agent access contract and origin/sign-in screens checked. Tool schemas and security-administration controls are other-reader handoffs.'
 elif title.startswith('AO1'):
  result='Model-administrator account: handoff to `model/ai-model-changes`, model releases and its explanation guide; shared disclosure in `use/ai-and-your-data`.'
  limit='Current model-change summary facts/citation behavior checked through J55 and shared AiAccount; not a steward task.'
 elif title.startswith('AP1 record'):
  result='Provider access, sending and retained calls in `use/ai-and-your-data`.'
  limit='Implementation excerpt and current context/call usage checked; setup remains in Run and no old inference naming helper is documented.'
 elif title.startswith(('Why','Outcome','Packages','Decisions','Where each')):
  result='Scope reconciled with current releases: built-in session and separate provider, human review, generic records/model; new steward pages cover these.'
  limit='Older no-provider-means-no-assistant and plan-step statements are superseded. Packages table explicitly makes old assistant sections historical.'
 elif title.startswith('Track'):
  result='Track grouping/decision table; applicable user facts are covered in the detailed feature reconciliations above.'
  limit='Later decisions and current code override early job, tool, language and retention wording.'
 else:
  raise SystemExit('Missing heading disposition: '+title)
 with p.open('a') as f:
  f.write(f'| BASE_0_16_IMPLEMENTATION_PLAN:{line_no} — {title} | {result} | {limit} |\n');f.flush()
# The released changelog contains several generations of the assistant. Preserve that distinction.
lines=Path('CHANGELOG.md').read_text().splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('## [0.16.0]'))
end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('## ')),len(lines))
for index in range(start,end):
 line=lines[index]
 if not line.startswith(('## ','### ')): continue
 title=re.sub(r'^#+ ','',line)
 low=title.lower()
 if 'release review' in low:
  result='Permission boundaries, isolated session, stale checks and task offers reconciled with current task code.'
 elif any(t in low for t in ['notification','job\'s page','removal in the model','hint beside','opening a record','relation matrix','model editor','changing a workspace\'s model']):
  result='Non-AI capability or another reader; existing pages retain their home. No new AI behavior inferred.'
 elif any(t in low for t in ['reading turns','naming helper']):
  result='Historical/removed design. No reading-turn or inference AI naming instructions added.'
 elif 'ap6a' in low:
  result='Entry point and requester visibility retained in `use/loading-with-the-assistant`; old provider-loop and /plan behavior superseded.'
 elif 'ap6,' in low:
  result='Current session/proposal and journey bar covered in assistant documentation and guides. Earlier step/unpivot and automatic-activation paragraphs are superseded.'
 elif 'agent access' in low:
  result='Steward session and prepared-work behavior in account, AI disclosure and history; protocols/security administration handed to their readers.'
 elif any(t in low for t in ['model change, ao1']):
  result='Model-administrator summary handoff; shared privacy/citation explanation retained for stewards.'
 elif any(t in low for t in ['period','ao2']):
  result='`use/history` and `guide/use/explain-a-period-in-history`: periods, live counts, sources, failure and cache.'
 elif 'asking a list' in low:
  result='`use/ask-in-words` and its guide; ordinary replacement filters, partial acceptance, short lists and failures.'
 elif any(t in low for t in ['ap2','targets']):
  result='Mapping documentation and `guide/use/propose-targets`: eligible sources/candidates, marks, review and job outcomes.'
 elif 'who did' in low:
  result='History provenance, distinct requester/editor/publisher; call/retention explanation in AI and your data.'
 elif 'import and export' in low:
  result='Workspace menu entry verified in task guide and importing/exporting page.'
 elif 'several columns' in low:
  result='Combination keys and empty/ambiguous-key limits in `use/loading-with-the-assistant`.'
 elif any(t in low for t in ['one path','assistant','ai import']):
  result='Assistant documentation and three task guides; current session code supersedes older provider-plan wording.'
 elif any(t in low for t in ['ap1','ai proposal provider']):
  result='Provider, sending and access in `use/ai-and-your-data`; startup/runtime details handed to Run. Removed inference helper not revived.'
 elif 'language in the api' in low:
  result='OpenAPI/model contract and session log implementation: no new steward controls.'
 elif '[0.16.0]' in low:
  result='Released scope reconciled across new Ask, mapping, assistant and history pages; no planned feature documented.'
 else:
  raise SystemExit('Missing changelog disposition: '+title)
 with p.open('a') as f:
  f.write(f'| CHANGELOG:{index+1} — {title} | {result} | Release history checked against current code; no historical test result claimed as this wave validation. |\n');f.flush()
for title,description in [
 ('USER_JOURNEYS — J55 An account of a model change','Model-administrator task; cross-link to model/ai-model-changes and explanation guide. Shared facts/citations and data disclosure checked, no steward activation walkthrough duplicated.'),
 ('USER_JOURNEYS — J57 Notification digests and following a workspace','Not AI. Existing notification pages and guides remain authoritative for stewards; no provider requirement added.'),
 ('OUTLINE — section 8','New Ask/assistant pages and named guides, mapping/history additions and other-reader links follow the settled structure.'),
 ('BEHAVIOUR-RULES — F7 and related permission/activation rules','No live session writes, no approval/publication/activation by an assistant; real refusal/recovery actions documented. Targeted rows read, not the full historic audit.'),
 ('samples/README and SOURCES','Reference transport world and dated sample attribution checked. No private examples or unverified real-world claims added.'),
]:
 with p.open('a') as f:f.write(f'| {title} | {description} | Scope-specific source read; no live request. |\n');f.flush()
