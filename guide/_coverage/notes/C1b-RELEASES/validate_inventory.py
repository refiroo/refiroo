from reconcile import *
from collections import Counter

cp=ROOT/'_waves/COVERAGE.md';ct=cp.read_text();rows=table(ct,r'^\| C\d');by={x[0]:x for x in rows}
before={x[0]:x for x in table((NOTES/'COVERAGE.before.md').read_text(),r'^\| C\d')}
def link(h):return '['+h+'](../src/content/docs/'+h+'.md)'

# Bulk deletion policy and the whole bulk-action capability are distinct scopes.
# Undo the overly broad audit alias from the first semantic pass.
by['C1056'][5]=by['C1056'][5].split('; NOT-YET-COVERED.md:13')[0]
by['C1056'][6]='partly: '+link('use/records')+' — missing: the skip-versus-atomic policy for selected-record deletion'
restored=before['C1185'][:]
restored[1]='Change selected or all matching records: selection, value and relationship actions, deletion, previews and refusals.'
restored[6]='uncovered → use/changing-many-records'
if restored[0] not in by:rows.append(restored);by[restored[0]]=restored
merges=json.loads((NOTES/'semantic-merges.json').read_text());merges=[x for x in merges if x['removed']!='C1185']
(NOTES/'semantic-merges.json').write_text(json.dumps(merges,indent=2)+'\n')

# Security behavior remains a product obligation even when its original source
# was expressed as a sweep case; do not discard the refusal with the test.
for ident,item,reader,status in [
 ('C2263','Unknown or malformed API routes return structured client errors.','integrator','uncovered → integrate/identifiers-paging-and-errors'),
 ('C2265','Expired, altered, unsigned or wrong-audience tokens cannot authorise an operation.','access-admin, integrator','access-admin: partly: '+link('administer/sign-in')+' — missing: invalid-token refusal; integrator: uncovered → integrate/signing-in-and-tokens'),
 ('C2295','Every write route enforces the caller’s narrowed grants.','access-admin',link('administer/roles-and-grants')),
 ('C2313','Unauthenticated requests are refused; a forbidden operation identifies its required action and workspace.','access-admin, integrator','access-admin: '+link('administer/roles-and-grants')+'; integrator: uncovered → integrate/security-model-for-integrators')]:
 by[ident][1]=item;by[ident][3]=reader;by[ident][6]=status
by['C0413'][1]='Discard a change set in the browser; rename an open change set through the API against its version.'
by['C0413'][3]='steward, integrator'
by['C0413'][6]='steward: '+link('use/change-sets')+'; integrator: uncovered → integrate/changes-approvals-and-publication'
by['C1074'][6]='partly: '+link('use/records')+' — missing: ancestor-scoped uniqueness and the detailed bulk-action dialogs; field kinds, inline editing, atomic creation and history are covered'

pt=(ROOT/'_waves/PROMISES.md').read_text();bt=(ROOT/'_waves/BEHAVIOUR-RULES.md').read_text()
primary=table(pt.split('## Superseded statements')[0],r'^\| (?:J|F|R|GL|US|AS)')
rules=table(bt,r'^\| [A-L]\d+ ')
evidence=table(pt.split('## Deferred AI/agent release evidence')[1],r'^\| (?:PL-|CL-)')
assert len(evidence)==183
assert all('0.16' in x[3] for x in evidence)
for records,width in [(primary,5),(rules,8),(rows,7)]:
 assert all(len(x)==width for x in records)
 assert len({x[0] for x in records})==len(records)
assert not re.search('provisional',pt+ct,re.I)
outline=(ROOT/'_waves/OUTLINE.md').read_text()
homes=set(re.findall(r'\| ((?:about|use|model|administer|run|integrate|examples|guide)/[\w/-]+)',outline))
for x in rows:
 assert x[6]
 if x[6]=='after 0.16':assert x==before[x[0]]
 for h in re.findall(r'uncovered → ([\w/-]+)',x[6]):
  assert h in homes or (ROOT/'src/content/docs'/Path(h+'.md')).is_file(),(x[0],h)
 for h in re.findall(r'\]\(\.\./src/content/docs/([^\)]+)\)',x[6]):
  assert (ROOT/'src/content/docs'/h.split('#')[0]).is_file(),(x[0],h)
 if 'complete the specific behavior' in x[6]:
  assert re.search(r'\bAI\b|assistant|\bMCP\b|agent|ai-later',x[1],re.I),x[0]

def status(x):
 s=x[6]
 if s=='after 0.16':return 'after'
 if s.startswith('not for readers:'):return 'excluded'
 if 'uncovered' in s:return 'uncovered'
 if 'partly:' in s:return 'partly'
 return 'covered'
order=['about','use','model','administer','run','integrate','examples','journeys']
counts={s:Counter(status(x) for x in rows if x[4]==s) for s in order}
header=ct[:ct.index('| ID |')]
for s,c in counts.items():header=re.sub(r'^- '+s+r': .*$', '- '+s+': '+' / '.join(str(c[k]) for k in ['covered','partly','uncovered','after'])+f'; not for readers: {c["excluded"]}.',header,flags=re.M)
header=re.sub(r'^Total: .*$',f'Total: {len(rows)} rows; 183 deferred AI/agent release-evidence leads retained. Stable IDs are not renumbered after merging.',header,flags=re.M)
rows.sort(key=lambda x:(order.index(x[4]),int(x[0][1:])))
cp.write_text(header+'| ID | Item | Kind | Reader | Section | Source | Covered by |\n|---|---|---|---|---|---|---|\n'+'\n'.join(row(x) for x in rows)+'\n')
reports=[json.loads(f.read_text()) for f in NOTES.glob('*-resolution.json')]
total=Counter()
for report in reports:total.update(report['counts'])
assert total['merged']+total['superseded']+total['dropped']+len(evidence)==1246
summary={'coverage_rows':len(rows),'primary_records':len(primary),'ordinary_primary_records':sum(x[4]!='ai-later' for x in primary),'ai_primary_records':sum(x[4]=='ai-later' for x in primary),'rules':len(rules),'deferred_release_leads':len(evidence),'release_counts':total,'semantic_merges':len(merges),'sections':counts,'coverage_totals':Counter(status(x) for x in rows),'validation':'Inventory structure, unique stable IDs, planned homes, existing page links, unchanged after-0.16 rows and reconciliation arithmetic passed.'}
(NOTES/'final-counts.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
