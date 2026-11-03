from pathlib import Path
from collections import Counter
import re
from finish_unit import root,steering,finish
steering()
p=root/'_waves/coverage/integrate.md'
notes=root/'_coverage/notes/C6-INTEGRATE'
pages={str(f.relative_to(root/'src/content/docs')).removesuffix('.md'):f.read_text() for base in ['integrate','guide/integrate'] for f in (root/'src/content/docs'/base).glob('*.md')}
defer={'C3429','C3530','C3545','C3548','C3749','C3760','C3779','C3473','C3475','C3479','C3612','C3613','C3617','C3691'}
special={
'C2940':['guide/integrate/load-then-follow-changes'],
'C2941':['integrate/api-reference'],'C2942':['integrate/api-reference'],
'C2966':['integrate/business-dates','model/types-attributes-relations'],
'C3009':['integrate/looking-up-and-resolving'],'C3010':['integrate/reading-business-objects'],
'C3012':['integrate/consumer-events-and-webhooks'],'C3014':['integrate/reading-business-objects'],
'C3015':['integrate/looking-up-and-resolving'],'C3019':['integrate/reading-business-objects'],
'C3021':['integrate/looking-up-and-resolving'],'C3024':['integrate/consumer-events-and-webhooks'],
'C3025':['integrate/reading-business-objects'],'C3027':['integrate/looking-up-and-resolving'],
'C3028':['integrate/looking-up-and-resolving'],'C3029':['integrate/reading-business-objects'],
'C3030':['integrate/reading-business-objects'],'C3031':['integrate/reading-business-objects'],
'C3032':['integrate/reading-business-objects'],'C3041':['integrate/discovering-the-model'],
'C3053':['use/account','integrate/security-model-for-integrators'],
'C3056':['integrate/consumer-events-and-webhooks','integrate/security-model-for-integrators','integrate/signing-in-and-tokens'],
'C3057':['integrate/security-model-for-integrators','run/configure'],
'C3122':['model/managing-workspaces','integrate/consumer-events-and-webhooks'],
'C3131':['integrate/api-reference'],'C3135':['integrate/writing-in-bulk'],
'C3137':['integrate/model-and-release-operations','guide/integrate/move-records-between-models'],
'C3162':['integrate/writing-in-bulk'],'C3169':['integrate/files-imports-and-exports','use/importing-and-exporting'],
'C3174':['integrate/files-imports-and-exports','use/importing-and-exporting'],
'C3208':['integrate/following-changes','integrate/model-and-release-operations'],
'C3236':['integrate/consumer-apis'],'C3237':['integrate/workspaces-contexts-and-models'],
'C3242':['integrate/discovering-the-model'],'C3244':['integrate/versions-and-conflicts'],
'C3246':['integrate/consumer-events-and-webhooks'],'C3247':['integrate/identifiers-paging-and-errors','guide/integrate/read-a-collection-completely-and-resume'],
'C3300':['integrate/writing-in-bulk'],
'C3319':['integrate/consumer-apis'],'C3321':['integrate/consumer-apis'],
'C3353':['integrate/reading-records','integrate/versions-and-conflicts'],
'C3354':['integrate/api-reference'],'C3358':['integrate/discovering-the-model'],
'C3359':['integrate/discovering-the-model'],'C3360':['model/consumer-apis','integrate/consumer-apis'],'C3445':['model/model-language-versions','integrate/model-and-release-operations'],
'C3448':['integrate/security-model-for-integrators','integrate/changes-approvals-and-publication'],
'C3449':['integrate/changes-approvals-and-publication'],
'C3518':['integrate/security-model-for-integrators'],'C3519':['integrate/changes-approvals-and-publication'],
'C3520':['integrate/discovering-the-model','integrate/workspaces-contexts-and-models'],
'C3521':['integrate/identifiers-paging-and-errors'],'C3522':['integrate/identifiers-paging-and-errors'],
'C3523':['integrate/changes-approvals-and-publication'],'C3524':['integrate/workspaces-contexts-and-models'],
'C3525':['integrate/reading-records'],'C3526':['integrate/discovering-the-model'],
'C3527':['integrate/workspaces-contexts-and-models'],'C3528':['integrate/workspaces-contexts-and-models'],
'C3553':['integrate/security-model-for-integrators'],'C3556':['integrate/versions-and-conflicts'],
'C3557':['integrate/versions-and-conflicts'],'C3558':['integrate/versions-and-conflicts'],
'C3629':['guide/integrate/read-a-collection-completely-and-resume'],'C3633':['guide/integrate/submit-a-bulk-change'],
'C3661':['integrate/writing-in-bulk'],'C3665':['integrate/writing-in-bulk'],
'C3670':['integrate/reading-records'],'C3671':['integrate/writing-in-bulk'],
'C3678':['integrate/writing-in-bulk'],'C3685':['integrate/writing-in-bulk'],
'C3822':['integrate/files-imports-and-exports','use/importing-and-exporting','use/jobs'],
'C3823':['integrate/files-imports-and-exports','use/importing-and-exporting'],
'C3827':['integrate/files-imports-and-exports'],'C3830':['integrate/files-imports-and-exports'],
'C3831':['integrate/files-imports-and-exports'],'C3833':['integrate/jobs','integrate/model-and-release-operations'],
'C3834':['integrate/files-imports-and-exports'],'C3851':['integrate/jobs','use/jobs'],
'C3856':['integrate/files-imports-and-exports'],'C3857':['integrate/files-imports-and-exports'],
'C3923':['integrate/reading-records'],'C3954':['integrate/reading-business-objects','integrate/consumer-events-and-webhooks'],
'C4000':['integrate/workspaces-contexts-and-models'],
}
def link(slug):return f'[{slug}](../../src/content/docs/{slug}.md)'
audit=[];out=[];stats=Counter();unresolved=[]
for line in p.read_text().splitlines():
 if not line.startswith('| C'):out.append(line);continue
 fields=line.split('|');id=fields[1].strip();item=fields[2].strip();kind=fields[3].strip();old=fields[-2].strip()
 if old=='after 0.16' or id in defer:
  value='after 0.16';stats['deferred AI']+=1
 elif old.startswith('not for readers:'):
  value=old;stats['not for readers']+=1
 else:
  targets=special.get(id)
  code=re.search(r'with ([A-Z][A-Z_0-9]+)',item) if kind=='message/error' else None
  if code:
   hits=[slug for slug,body in pages.items() if re.search(r'\b'+code[1]+r'\b',body)]
   preferred=re.findall(r'(?:guide/)?integrate/[a-z-]+',old)
   targets=[next((x for x in preferred if x in hits),hits[0] if hits else '')]
   source=re.search(r'; (backend/[^ ;]+)',fields[6])
   if source:
    source_path=root.parent/source[1]
    found=source_path.exists() and code[1] in source_path.read_text()
    audit.append(f'| {id} | `{code[1]}` | `{source[1]}` | {"present" if found else "requires source reconciliation"} | {targets[0]} |')
  if not targets:
   targets=re.findall(r'(?:guide/)?integrate/[a-z-]+',old)
   if not targets and 'about/how-it-works' in old:targets=['about/how-it-works']
   targets=list(dict.fromkeys(targets))
  if not targets or not all(targets):unresolved.append((id,item,old));value=old
  else:
   for slug in targets:
    assert (root/'src/content/docs'/f'{slug}.md').exists(),(id,slug)
   value='; '.join(link(x) for x in targets)
   if id=='C3449':value+=' — own-work collection filters the caller’s created open sets; workspace change sets remain shared.'
   if id in {'C2941','C2942','C3131'}:value+=' — current code serves documentation at /docs and the reference at /docs/api.'
   if id=='C3057':value+='; AI-specific settings remain after 0.16.'
   stats['covered']+=1
 fields[-2]=' '+value+' ';out.append('|'.join(fields))
assert not unresolved,unresolved
assert sum(stats.values())==719,stats
p.write_text('\n'.join(out)+'\n')
(notes/'error-source-audit.md').write_text('# Current error-code source audit\n\nThis index confirms code presence and the page explaining recovery. It is not runtime execution evidence. Deferred AI errors are left to the later wave.\n\n| ID | Code | Cited code source | Source check | Recovery page |\n| --- | --- | --- | --- | --- |\n'+'\n'.join(audit)+'\n')
(notes/'coverage-summary.md').write_text('# Coverage closure\n\n'+str(dict(stats))+'\n\nAll 719 original IDs retained. Current rows now link to actual pages. AI-only proposal, assistant and MCP errors were deferred after inspecting their emitters. Ordinary following, digests and composite import keys remain current.\n\nSource discrepancies: older inventories put the reference at /docs; current reference router serves /docs/api. Export feed checkpoints are job metadata, not file contents. Consumer totals are null without a total request. Own-change-set collections filter creator; workspace change sets remain shared. The compatibility commitment promises parallel consumer contract versions, but current consumer routing first checks the workspace’s active version, including before a publication read.\n')
finish(['_waves/coverage/integrate.md'],'Closed all current coverage rows with actual page links; retained every original ID and deferred only AI work. Counts: '+str(dict(stats))+'. Reassigned misplaced errors/screens to their actual reader pages; source discrepancies recorded under working notes.')
print(dict(stats));print('Error source rows',len(audit))
