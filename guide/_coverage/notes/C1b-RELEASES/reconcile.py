from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[3]
NOTES=Path(__file__).resolve().parent

def split(line):
 return [s.strip().replace('\\|','|') for s in re.split(r'(?<!\\)\|',line)[1:-1]]
def row(parts):
 return '| '+' | '.join(str(x).replace('|','\\|').replace('\n',' ') for x in parts)+' |'
def table(text,pattern):
 return [split(l) for l in text.splitlines() if re.match(pattern,l)]
def apply(version, additions, rules, resolutions, superseded=()):
 p=ROOT/'_waves/PROMISES.md';b=ROOT/'_waves/BEHAVIOUR-RULES.md';c=ROOT/'_waves/COVERAGE.md'
 pt=p.read_text();bt=b.read_text();ct=c.read_text()
 primary={x[0]:x for x in table(pt.split('## Unreconciled')[0],r'^\| (?:J|F|R|GL|US|AS)')}
 cov=table(ct,r'^\| C\d'); cid=max(int(x[0][1:]) for x in cov)
 added=[];ruleids=[]
 for ident,ability,reader,section,home,source in additions:
  assert ident not in primary,ident
  parts=[ident,ability,reader,source,''];primary[ident]=parts
  pt=pt.replace('## Superseded statements',row(parts)+'\n\n## Superseded statements',1)
  cid+=1;cov.append([f'C{cid:04}',ability,'capability',reader,section,f'PROMISES.md {ident}; {source}',f'uncovered → {home}']);added.append(ident)
 for ident,rule,cause,effect,ui,reader,code,source,section,home in rules:
  assert not re.search(r'^\| '+re.escape(ident)+r' \|',bt,re.M),ident
  bt=bt.replace('## Counts per area',row([ident,rule,cause,effect,ui,reader,code,source])+'\n\n## Counts per area',1)
  cid+=1;cov.append([f'C{cid:04}',rule,'rule',reader,section,f'BEHAVIOUR-RULES.md {ident}; {source}',f'uncovered → {home}']);ruleids.append(ident)
 notes=[];counts={'added_promises':len(added),'added_rules':len(ruleids),'merged':0,'superseded':0,'dropped':0}
 lines=[]
 for line in pt.splitlines():
  if not re.match(r'^\| (?:CL-|PL-)',line):lines.append(line);continue
  parts=split(line);ident=parts[0]
  if ident not in resolutions:lines.append(line);continue
  disposition,targets,reason=resolutions[ident];counts[disposition]+=1
  notes.append({'id':ident,'disposition':disposition,'targets':targets,'reason':reason,'source':parts[3]})
  # Preserve provenance on the semantic record, without copying obsolete prose.
  for target in targets:
   if target in primary:
    primary[target][3]+='; '+parts[3]+' ('+ident+')'
  oldcov=[x for x in cov if re.search(r'PROMISES\.md '+re.escape(ident)+r'(?:;|$| )',x[5])]
  for old in oldcov:
   if disposition=='merged':
    destinations=[x for x in cov if any(re.search(r'PROMISES\.md '+re.escape(t)+r'(?:;|$| )',x[5]) for t in targets)]
    assert destinations,(ident,targets)
    for dest in destinations:dest[5]+='; '+old[5]
    cov.remove(old)
   else:
    old[6]='not for readers: '+reason
    old[1]=('Superseded source: ' if disposition=='superseded' else 'Excluded source: ')+reason
 linestr='\n'.join(lines)+'\n'
 for ident,parts in primary.items():
  linestr=re.sub(r'^\| '+re.escape(ident)+r' \|.*$',lambda _:row(parts),linestr,flags=re.M)
 for text in superseded:
  linestr=linestr.replace('## Reconciliation accounting','- '+text+'\n\n## Reconciliation accounting',1)
 match=re.search(r'^Releases reconciled: (.*)$',linestr,re.M)
 done=(match[1]+', ' if match else '')+version
 if match:linestr=linestr[:match.start()]+f'Releases reconciled: {done}'+linestr[match.end():]
 else:linestr=linestr.replace('\n\n','\n\nReleases reconciled: '+done+'\n\n',1)
 # Keep ledger grouping and stable row IDs.
 order=['about','use','model','administer','run','integrate','examples','journeys']
 cov.sort(key=lambda x:(order.index(x[4]),int(x[0][1:])))
 header=ct[:ct.index('| ID |')]
 ct=header+'| ID | Item | Kind | Reader | Section | Source | Covered by |\n|---|---|---|---|---|---|---|\n'+'\n'.join(row(x) for x in cov)+'\n'
 # Counts are refreshed after every saved release.
 def status(x):
  s=x[6]
  if 'uncovered' in s:return 'uncovered'
  if 'partly:' in s:return 'partly'
  if s=='after 0.16':return 'after'
  if s.startswith('not for readers:'):return 'excluded'
  return 'covered'
 for section in order:
  nums=[sum(x[4]==section and status(x)==s for x in cov) for s in ['covered','partly','uncovered','after','excluded']]
  ct=re.sub(r'^- '+section+r': .*$',f'- {section}: '+ ' / '.join(map(str,nums[:4]))+f'; not for readers: {nums[4]}.',ct,flags=re.M)
 pending=sum('source-review' in x for x in linestr.splitlines() if x.startswith('|'))
 ct=re.sub(r'^Total: .*$',f'Total: {len(cov)} rows; {pending} release evidence leads retained. IDs are snapshot identities and are not product identifiers.',ct,flags=re.M)
 # Count each rule area, including additional release rules in L.
 allrules=table(bt,r'^\| [A-L]\d+ ')
 for area in 'ABCDEFGHIJKL':
  bt=re.sub(r'^\| '+area+r' \| \d+ \|$',row([area,sum(x[0].startswith(area) for x in allrules)]),bt,flags=re.M)
 bt=re.sub(r'^\| \*\*Total\*\* \|.*$',row(['**Total**',f'**{len(allrules)}**']),bt,flags=re.M)
 bt=bt.replace('## C1 corrections and source review',f'Release {version} reconciled: '+', '.join(ruleids or ['no additional standalone rules'])+'. Sources and decisions: `_coverage/notes/C1b-RELEASES/'+version+'-resolution.json`.\n\n## C1 corrections and source review',1)
 p.write_text(linestr);b.write_text(bt);c.write_text(ct)
 report={'release':version,'counts':counts,'added_promises':added,'added_rules':ruleids,'resolutions':notes}
 (NOTES/(version+'-resolution.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(version,counts)
