from reconcile import *
from collections import Counter
pp=ROOT/'_waves/PROMISES.md';bp=ROOT/'_waves/BEHAVIOUR-RULES.md'
pt=pp.read_text();bt=bp.read_text()
primary=table(pt.split('## Superseded statements')[0],r'^\| (?:J|F|R|GL|US|AS)')
corrections={
 'J05.5':('Discard a change set in the browser; rename an open change set through the API against its version','steward, integrator','backend/app/management/routers/change_sets.py patch_change_set; frontend/src/features/workspaces/ChangeSets.tsx'),
 'J19.5':('Read workspace activity: change sets, publications, default switch, who and when','access-admin','CL 0.12 A3b (delivered, not planned)'),
 'J39.2':('Sessions renew while working. A reused refresh token ends the session except for the limited thirty-second successor-recovery case in R128','steward','backend/app/engine/identity/sessions.py REFRESH_REUSE_GRACE and refresh'),
 'F22.h':('People workbooks follow table columns/order/labels, with advanced choices, relationship sheets, hidden IDs/versions and non-imported summaries. Blank attributes and owned-record cells do not clear stored values; a blank replacing relationship-set cell clears that set when valid','steward','R085; PL 0.9 J4'),
 'F23.d':('Webhook subscriptions can be created, read, listed, edited, paused, resumed and deleted. HTTPS may use any host; HTTP is loopback-only. Model, contract, workspace, filter and expired-event changes can suspend delivery; the host allowlist is removed','operator','R075–R077; CL 0.9 C-D104 and subsequent delivery changes'),
 'R093':('A model operation request applies up to 500 operations atomically as one recorded step at the draft version, stores inverses and diagnostics and allows intermediate invalid drafts. Impact counts cover live data and open change sets only in workspaces running that draft’s model (R115)','model-admin, integrator','PL 0.11 M1; R115 (narrows the former cross-model wording)'),
}
for x in primary:
 if x[0] in corrections:
  ability,reader,source=corrections[x[0]];x[1]=ability;x[2]=reader;x[3]+='; '+source
prefix=pt[:pt.index('| id |')]
prefix=re.sub(r'^Releases reconciled: .*$', 'Releases reconciled: 0.3, 0.5, 0.6, 0.7, 0.8, 0.9 (including alpha.1), 0.10 (including alpha.1), 0.11 (including alpha.1), 0.12 and 0.16. Status checked: 0.13–0.15 and 0.17 (no additional released section).',prefix,flags=re.M)
prefix=re.sub(r'\*\*Audit status: provisional\.\*\*.*?\n\n','Release reconciliation completed for the ordinary product record. All 1,246 retained release leads have a disposition: 904 merged into semantic records, 28 superseded, 131 dropped, and 183 AI/agent leads retained unchanged for the later wave. The per-release resolution files preserve the source, destination and reason for every disposition. This is a documentation inventory, not runtime acceptance.\n\n',prefix,flags=re.S)
prefix=re.sub(r'^Current records: .*$',f'Primary records: {len(primary)} ({sum(x[4]!="ai-later" for x in primary)} current ordinary records and {sum(x[4]=="ai-later" for x in primary)} deferred AI/agent records). Release statements: R001–R164; C1b added R055–R164 (110). Deferred mechanical AI/agent evidence: 183 leads, outside these primary counts.',prefix,flags=re.M)
tail=pt[pt.index('## Superseded statements'):]
start=tail.index('## Reconciliation accounting');end=tail.index('## Unreconciled release evidence')
tail=tail[:start]+'''## Reconciliation accounting

C1's earlier extraction accounting is preserved in `_coverage/notes/C1b-RELEASES/PROMISES.before.md`. C1b reconciled the 1,246 retained release leads: 904 merged, 28 superseded, 131 dropped as internal/tooling/test evidence or unbuilt work, and 183 AI/agent leads held for the later wave. Added 110 primary statements and 37 rule entries; eight of those rules were subsequently merged into existing rules. COVERAGE has its own semantic row merges, recorded separately; these are not additional release-lead dispositions.

The original plan extractor collapsed identically numbered decisions from different releases into combined sources. C1b used each lead’s actual statement and the release-scoped decision to resolve that provenance; a shared D-number is not evidence of identical behavior. Resolution JSON files retain the earlier source strings for traceability.

## Reading scope and limits

C1b used the saved C1 notes, plan packets and record extracts as instructed, then reviewed the release record in release-sized units: 0.7, 0.8, 0.9, 0.10, 0.11, 0.12 and 0.16, including their alpha records and delivered-package decisions. The earlier 0.3, 0.5 and 0.6 record was checked for remaining leads. The 0.13 restart/stopped status and the unbuilt 0.14, 0.15 and 0.17 plans add no current release promises; the delivered workspace-model work cited by 0.17 belongs to 0.16. There is no separate 0.3/0.4 implementation plan in the plan family.

This review reuses the earlier reading record and extracts; it is not a claim to have reread every line of every historical plan or every source file. Direct checks covered the release amendments and disputed current statements. Existing code citations remain inherited evidence unless a working note names a fresh check. The final pass checked password bounds, the refresh reuse interval and the change-set rename API/browser distinction. No runtime or browser acceptance tests were run for this documentation-only wave.

The 82 existing non-AI page homes referenced by generic partly judgments were read in full. COVERAGE now distinguishes covered text from named missing clauses; it does not infer coverage from a filename. AI/agent rows remain unchanged, including their older judgments, for the explicitly deferred writing wave. No guide pages or screenshots are added by C1b.

''' +tail[end:]
tail=tail.replace('## Unreconciled release evidence (not current promises)','## Deferred AI/agent release evidence (not a current writing brief)',1)
tail=re.sub(r'These original leads are retained.*?\n\n\| id \|','These 183 original AI/agent leads are held unchanged under COMPLETE-COMMON. Their extraction may contain historical or duplicate wording. Reconcile them in the later AI wave before writing from them; ordinary digests and following have already been reconciled above.\n\n| id |',tail,count=1,flags=re.S)
pp.write_text(prefix+'| id | ability | reader | source | flag |\n|---|---|---|---|---|\n'+'\n'.join(row(x) for x in primary)+'\n\n'+tail)

# Merge duplicate rule records, preserving their identity as aliases and retaining
# additional effect/UI/source information in the fuller rule.
rules=table(bt,r'^\| [A-L]\d+ ');by={x[0]:x for x in rules}
aliases={'L29':'G10','L35':'D7','L38':'F5','L39':'G3','L40':'F12','L44':'H6','L47':'G8','L51':'H2'}
for old,new in aliases.items():
 a=by[new];b=by[old]
 a[7]+='; '+b[7]+' (merged '+old+')'
 for col in [2,3,4]:
  if b[col] and b[col] not in a[col]:a[col]+=('; ' if a[col] else '')+b[col]
 a[5]+=', '+b[5]
 bt=re.sub(r'^\| '+old+r' \|.*\n','',bt,flags=re.M)
 bt=re.sub(r'^\| '+new+r' \|.*$',lambda _:row(a),bt,flags=re.M)
for ident in ['C7']:
 a=by[ident];a[1]='`many-to-one` is not allowed together with `required`. The current schema language is 0.10; the feature first appeared in schema 0.9.'
 bt=re.sub(r'^\| '+ident+r' \|.*$',lambda _:row(a),bt,flags=re.M)
bt=re.sub(r'\|\n\s*\n(?=\|)', '|\n',bt)
actual=table(bt,r'^\| [A-L]\d+ ')
for area in 'ABCDEFGHIJKL':bt=re.sub(r'^\| '+area+r' \| \d+ \|$',row([area,sum(x[0].startswith(area) for x in actual)]),bt,flags=re.M)
bt=re.sub(r'^\| \*\*Total\*\* \|.*$',row(['**Total**',f'**{len(actual)}**']),bt,flags=re.M)
bt=bt.replace('Release 0.13/0.14/0.15/0.17 status checked (no additional released product section) reconciled: no additional standalone rules. Sources and decisions: `_coverage/notes/C1b-RELEASES/0.13/0.14/0.15/0.17 status checked (no additional released product section)-resolution.json`.','Status-only plans 0.13–0.15 and 0.17: no additional standalone rules. See `../_coverage/notes/C1b-RELEASES/unreleased-plans-resolution.json`.')
bt=bt.replace('Full prose mining of the remaining releases/plans is still open, as PROMISES.md records; do not treat 120 rules as proof that every released rule has been found.','C1b completed the ordinary release-lead reconciliation using the saved extracts and targeted source review described in PROMISES.md. The inventory now has 149 distinct rules; that count is not a claim of exhaustive code mining.')
bt=bt.replace('### Earlier inventory\'s reading record (inherited, not repeated in C1)','### Earlier inventory\'s reading record (historical; supplemented by C1 and C1b above)')
bt=bt.replace('## C1 corrections and source review','C1b rule aliases: '+', '.join(old+' → '+new for old,new in aliases.items())+'. These are merged identities, not additional current rules. C1b added 37 rule rows before these eight merges.\n\n## C1 corrections and source review',1)
bp.write_text(bt)
print('Primary records',len(primary),'ordinary',sum(x[4]!='ai-later' for x in primary),'rules',len(actual))
