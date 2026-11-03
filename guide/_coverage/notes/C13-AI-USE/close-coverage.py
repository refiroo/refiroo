from pathlib import Path
from collections import Counter
b=Path(__file__).resolve().parents[3]
p=b/'_waves/coverage/use.md'
excluded={
'C0091':'security-administrator registration, blocking and restoration screen; steward sign-in and ending a session are covered in use/account and use/ai-and-your-data',
'C0119':'audit channel is an integration contract with no browser control or Changes-page mark; record origin is covered in use/history',
'C0141':'token scopes and client kinds are an authentication implementation and integration contract, not a steward control',
'C0143':'internal task-client lifecycle; its early cleanup-at-load wording is superseded by the session-end rules documented in use/loading-with-the-assistant',
'C0161':'removal of superseded implementation paths; current saved-layout and session behavior is documented instead',
'C0253':'future 0.17 gesture design, not delivered 0.16 behavior',
'C0255':'superseded plan-step ownership design; the current assistant rereads the editable model draft',
'C0256':'test design and acceptance process, not product instructions',
'C0261':'superseded in-process planning-tool loop; current Claude Code task described in use/loading-with-the-assistant',
'C0262':'superseded provider-based assistant design; the current built-in assistant uses Claude Code independently of the provider',
'C0267':'test fake and release-validation procedure, not product behavior',
'C0271':'future 0.17 canvas design, not a delivered screen',
'C0292':'request-level send policy is an integration contract; these browser screens have no send-level selector',
'C0591':'facts-only assistant tool contract for integrators; browser history account is documented in use/history',
'C0599':'security-administrator tool-call log and database storage design; not a steward screen',
'C0674':'superseded three-file proposal; current browser takes one XLSX or CSV file as documented in use/loading-with-the-assistant',
'C0675':'superseded profile-tool assistant transport; current session receives the whole workbook, documented in use/ai-and-your-data',
'C0682':'superseded one-provider planning architecture; current session and provider are independent',
'C0703':'superseded five-kind plan representation; current task proposals and review documented without internal step names',
'C0714':'future 0.17 profile unpivot design, not delivered by this wave',
'C0716':'administration screen inventory; steward actions are documented at their task surfaces',
'C0802':'superseded task-plan batch-construction implementation, not a browser action',
'C0823':'model-administrator and integrator summary-route contract; not a steward task',
'C1066':'security-administrator Calls screen, not a steward task',
'C1099':'operator startup migration of settings and a runtime dependency, not a steward task; operator settings live in run/ai',
'C1104':'MCP tool annotations and response formatting contract for integrators, not a browser control',
'C1106':'schema-design decision about a field-proposal feature not delivered in 0.16',
'C1230':'model-query and relationship-candidate configuration contract, not an AI task-specific steward control',
'C1279':'model-activation summary fact representation for model administrators and integrators, not a steward task',
'C1280':'tool refusal wire format for integrators, not browser-facing text',
'C1281':'generated MCP tool naming contract for integrators, not a steward control',
'C1283':'MCP resource URI and paging contract for integrators, not a browser control',
}
groups={
'use/ai-and-your-data': 'C0112 C0114 C0115 C0126 C0142 C0160 C0169 C0227 C0243 C0282 C0289 C0397 C0826 C1117',
'use/history': 'C0223 C0106 C0109 C0117 C0146 C0155 C0158 C0247 C0259 C0269 C0275 C0319 C0346 C0391 C0393 C0396 C0514 C0562 C0567 C0570 C0580 C0581 C0582 C0583 C0584 C0586 C0592 C0596 C0597 C0603 C0606 C0607 C0608 C0609 C0666 C0752 C0762 C0788 C0824 C0829 C0901 C0940',
'use/ask-in-words': 'C0222 C0301 C0302 C0305 C0306 C0308 C0311 C0312 C0313 C0314 C0315 C0317 C0320 C0390 C0756 C0790 C0797 C0804 C0981 C1234',
'use/mapping-grids': 'C0310 C0958 C0959 C0960 C0962 C0963 C0964 C0965 C0966 C0971 C0972 C0979 C0985 C0987',
'use/loading-with-the-assistant': 'C0104 C0105 C0107 C0113 C0116 C0120 C0128 C0145 C0153 C0157 C0163 C0164 C0166 C0167 C0168 C0170 C0188 C0238 C0295 C0303 C0304 C0309 C0316 C0318 C0332 C0518 C0569 C0622 C0623 C0624 C0640 C0719 C0753 C0758 C0876 C0895 C0928 C0929 C0930 C0931 C0932 C0933 C0934 C0935 C0936 C0937 C0938 C0939 C0941 C0942 C0943 C0944 C0945 C0946 C0947 C0948 C0949 C0950 C0952 C0953 C0954 C0955 C0956',
}
lookup={id:page for page,ids in groups.items() for id in ids.split()}
lines=p.read_text().splitlines(); count=Counter(); dispositions=[]
for i,line in enumerate(lines):
 if not line.startswith('| C') or 'after 0.16' not in line: continue
 parts=line.split(' | '); id=parts[0].strip('| ')
 if id in excluded:
  result='not for readers: '+excluded[id]+'.';count['not for readers']+=1
 elif id in lookup:
  page=lookup[id];result=f'[{page}](../../src/content/docs/{page}.md)';count['covered']+=1
 else: raise SystemExit('Unclassified '+id)
 parts[-2]=result;lines[i]=' | '.join(parts);dispositions.append(f'| {id} | {result} |')
# Preserve historical C11 counts; add a current statement separately.
lines.insert(4,f'C13-AI-USE: reconciled 185 deferred rows: {count["covered"]} covered; {count["not for readers"]} not for readers (superseded, future, internal or another reader); 0 deferred rows remain. C11 counts above are historical.')
p.write_text('\n'.join(lines)+'\n')
(b/'_coverage/notes/C13-AI-USE/row-dispositions.md').write_text('# Deferred-row dispositions\n\n| Row | Final disposition |\n| --- | --- |\n'+'\n'.join(dispositions)+'\n')
print(dict(count))
