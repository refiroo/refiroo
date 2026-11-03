from reconcile import *
reports=[json.loads(p.read_text()) for p in NOTES.glob('*-resolution.json')]
pp=[]
for l in (NOTES/'0.17-leads.txt').read_text().splitlines():
 if not l.startswith('|'):continue
 r=split(l);pp.append({'id':r[0],'disposition':'merged' if r[0]=='PL-PP-D2' else 'dropped','targets':['J36.12'] if r[0]=='PL-PP-D2' else [],'reason':'WM1 delivered in 0.16; no new 0.17 feature.' if r[0]=='PL-PP-D2' else '0.17 is explicitly unbuilt, not current product behavior.','source':r[3]})
report={'release':'0.13–0.15 and 0.17 status','counts':{'added_promises':0,'added_rules':0,'merged':1,'superseded':0,'dropped':8},'added_promises':[],'added_rules':[],'resolutions':pp}
(NOTES/'unreleased-plans-resolution.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(report)
p=ROOT/'_waves/COVERAGE.md';text=p.read_text();rows=table(text,r'^\| C\d');removed=[];excluded=[]
for report in reports:
 for res in report['resolutions']:
  found=[x for x in rows if 'PROMISES.md unreconciled '+res['id']+';' in x[5]]
  for old in found:
   if res['disposition']=='merged':
    dests=[x for x in rows if any(re.search(r'PROMISES\.md '+re.escape(t)+r'(?:;|$| )',x[5]) for t in res['targets'])]
    assert dests,(old[0],res)
    for dest in dests:dest[5]+='; '+res['source']+' ('+res['id']+')'
    rows.remove(old);removed.append({'removed':old[0],'into':[d[0] for d in dests],'lead':res['id']})
   else:
    old[1]=('Superseded source: ' if res['disposition']=='superseded' else 'Excluded source: ')+res['reason'];old[6]='not for readers: '+res['reason'];excluded.append(old[0])
p.write_text(text[:text.index('| ID |')]+'| ID | Item | Kind | Reader | Section | Source | Covered by |\n|---|---|---|---|---|---|---|\n'+'\n'.join(row(x) for x in rows)+'\n')
(NOTES/'ledger-release-merges.json').write_text(json.dumps({'merged':removed,'excluded':excluded},indent=2)+'\n')
print('Release evidence merged',len(removed),'excluded',len(excluded),'rows',len(rows))
