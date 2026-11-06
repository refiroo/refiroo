from pathlib import Path
import json,re
b=Path('guide');spec=json.loads((b/'_waves/C10.screens.json').read_text());screens=spec['screens'];names=[s['name'] for s in screens]
assert len(names)==len(set(names)), 'duplicate names'
allowed={'goto','click','rightClick','hover','drag','check','fill','focusedFill','select','upload','press','waitFor','scrollTo','scrollEnd','wait'}
for s in screens:
 assert s.get('shows') and isinstance(s.get('expect'),list),s['name']
 for a in s.get('actions',[])+s.get('after',[]):
  assert len(set(a)&allowed)==1,(s['name'],a)
  if 'goto' in a:assert a['goto'].startswith('/') and not a['goto'].startswith('//')
  if 'upload' in a:assert Path(a['value']).is_file(),a['value']
missing={}
for p in sorted((b/'src/content/docs').rglob('*')):
 if p.suffix not in ('.md','.mdx'):continue
 for n in re.findall(r'/docs/screens/([^\s)"<>]+)',p.read_text()):
  if not (b/'public/screens'/n).exists():missing.setdefault(n,[]).append(str(p.relative_to(b/'src/content/docs')))
reasons={
 'admin-agent-block.png':'No saved fictional reference assistant is identified. Registration/access changes are prohibited; do not block a real assistant or invent its affected-session count.',
 'admin-ai-test-failed.png':'No controlled failure exists. Do not alter provider/security configuration or deliberately cause an outage for a picture.',
 'model-account-provider-failure.png':'No naturally failed account request exists. Do not invent the provider result or create an outage.',
 'model-assistant-partial-move.png':'Needs another model-change task and the first release already activated. Only one workbook task is requested; release activation is prohibited.',
 'model-assistant-whole-type-move.png':'Needs an additional whole-type model-change task/accepted model. The single task is used for workbook loading; no pre-existing accepted move is identified.',
 'use-assistant-words.png':'Needs a separate words-only task. The one allowed task uses a workbook; a file-backed proposal cannot honestly illustrate this state.',
 'use-history-assistant.png':'Needs an existing published AI-authored change and distinct publisher. No such fixture is identified; publication is prohibited for screenshots.'
}
rows=[]
for image,pages in missing.items():
 planned=image[:-4] in names
 assert planned or image in reasons,('unaccounted missing image',image)
 rows.append({'image':image,'pages':pages,'status':'recipe' if planned else 'deferred','reason':None if planned else reasons[image]})
(b/'_coverage/notes/C10-SCREENS/fourth-round-inventory-final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
summary=f'{len(screens)} recipes; {len(rows)} missing images: {sum(r["status"]=="recipe" for r in rows)} planned, {sum(r["status"]=="deferred" for r in rows)} deferred.'
print(summary)
report=['# Fourth-round capture handoff','',summary,'','No reference-instance request or screenshot capture ran in this preparation turn. Existing files in public/screens were inventoried, not newly visually reviewed. Provider outcomes, timing, actual data changes and image framing await external capture.','', '## Missing page images','', '| Image | Page(s) | Coverage |','| --- | --- | --- |']
for r in rows:report.append('| `'+r['image']+'` | '+', '.join('`'+p+'`' for p in r['pages'])+' | '+('Recipe ready; inspect the real result.' if r['status']=='recipe' else r['reason'])+' |')
report += ['','## External execution order','','Run only the missing-image batch below; running the entire manifest repeats older setup and charged requests. The runner uses manifest order, not the order supplied to --only. Dependent entries use identical width, height and identity and must be in the same invocation.','', '```sh', 'node guide/tools/screens.mjs --file C10.screens.json --only '+','.join(r['image'][:-4] for r in rows if r['status']=='recipe' and r['image']!='admin-ai-calls.png'), 'node guide/tools/screens.mjs --file C10.screens.json --only admin-ai-calls','```','', 'The Calls retake follows the task so it can include assistant turns. Allow roughly 20 minutes for the complete batch because provider recipes have explicit waits (the runner has no waitFor timeout option). These commands are a handoff, not commands executed here. Do not retry charged operations blindly. On a failed prerequisite, inspect the actual task/result and retain its identifiers before editing recipes.','', '## Deferred requests with no current page reference','','C10-LATER is outside the allowed edit list. Its owner should remove notification-email-digest only after the new read-only recipe succeeds and its actual state is accepted. The requested on/mixed/digest/next-time/followed-workspace state is not created: account email and saved preferences remain prerequisites. The stale contributor row is already absent from the current C10-LATER file.','', 'Webhooks are enabled but reference/README.md explicitly says the switch does not subscribe a receiver. URL rules allow HTTP only on literal loopback hosts; no valid established local receiver or saved subscription is identified. Do not start a receiver, create security/integration settings or expose a new signing key. New webhook is covered by the corrected existing recipe; deliveries, rotate and paused/resume remain deferred pending an existing receiver/subscription (and a suspended fixture for Resume). Do not remove those C10-LATER rows.','', 'Other C10-LATER fixtures (migration staleness/old-language recovery, unavailable workspace, held jobs, invalid import, provider-person link, local group members, authenticators, sign-in provider and local-sign-in-off) remain unchanged. AI/mail/webhook switches do not supply them.','', 'Requested companion details without distinct filenames (phone mapping Why?, idle history disclosure, claimed external-assistant history) have no separate recipe: phone result depends on the actual generated proposals; the latter published-history fixture is absent. These details remain unverified, not fabricated.','', '## Changes and limits','','New recipes, planned persistence and cancellation are recorded in C10.data-changes.md. Restored notification-email-digest on use/notifications-settings.md; changed the stopped-task caption to the honest person-stopped state. Earlier resumed work already corrected enabled webhook and activation-account captions. No C10-LATER file was edited. No product defect is established by this source-only preparation.','']
(b/'_coverage/notes/C10-SCREENS/fourth-round-report.md').write_text('\n'.join(report))
