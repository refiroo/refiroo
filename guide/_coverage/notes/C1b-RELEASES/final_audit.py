from reconcile import *
from collections import Counter

cp=ROOT/'_waves/COVERAGE.md'
text=cp.read_text(); rows=table(text,r'^\| C\d'); by={x[0]:x for x in rows}
changes=[];merges=[]

def link(home):
 return '['+home+'](../src/content/docs/'+home+'.md)'

# These pairs express the same obligation, not merely adjacent controls or errors.
# Keep the fuller statement, the union of readers, and both source identities.
pairs=[('C1311','C1303'),('C2457','C2421'),('C0433','C0330'),
 ('C0548','C0478'),('C0482','C0484'),('C0482','C0468'),('C0469','C0557'),
 ('C0414','C0419'),('C0572','C0573'),('C0612','C0614'),('C1041','C1044')]

# Rule aliases added while reading successive releases. The later wording is
# retained in the rule record, but it is one writing obligation in the ledger.
aliases={'L29':'G10','L35':'D7','L38':'F5','L39':'G3','L40':'F12','L44':'H6','L47':'G8','L51':'H2'}
for old,new in aliases.items():
 a=next(x for x in rows if re.search(r'BEHAVIOUR-RULES.md '+new+r'(?:;|$)',x[5]))
 b=next(x for x in rows if re.search(r'BEHAVIOUR-RULES.md '+old+r'(?:;|$)',x[5]))
 pairs.append((a[0],b[0]))
for keep,remove in pairs:
 a=by[keep];b=by[remove]
 a[5]+='; '+b[5]+' (merged '+remove+')'
 a[3]=', '.join(dict.fromkeys((a[3]+', '+b[3]).split(', ')))
 if b[1].lower().rstrip('.') not in a[1].lower():a[1]+=' '+b[1]
 if b[6]!=a[6]:a[6]+='; '+b[6]
 rows.remove(b);merges.append({'keep':keep,'removed':remove,'reason':'Same reader obligation; fuller clauses and provenance retained.'})

# Specific judgments from the full-text reading of the 82 existing non-AI homes.
# A gap is recorded only for the part absent, rather than repeating an old audit.
gaps={
 'C0083':'the proof required before adding a passkey',
 'C0084':'the 15–128-character limits and the refusal of common passwords',
 'C0088':'the sign-in-method and session-start facts shown on the account card',
 'C0095':'the Appearance page and its density, palette and pencil choices',
 'C0190':'the limited thirty-second recovery exception for a reused refresh token',
 'C0197':'using the API console as the signed-in person',
 'C0327':'why a record created and deleted in the same change set is omitted',
 'C0334':'why restoring starting values still leaves a changed record and a version check',
 'C0339':'recovery when changing the pinned release succeeded but refreshing the browser failed',
 'C0347':'the next-chunk refusal and already-committed chunks after a concurrent change',
 'C0351':'starting an empty root change set', 'C0352':'the additions-only review of an empty root change set',
 'C0358':'deleting missing workbook records only through a change set',
 'C0371':'the immediate unique-value check prevents directly swapping two held values',
 'C0376':'the workspace-write wait boundary during publication',
 'C0413':'whether a change set can be renamed after creation; the current page says it cannot',
 'C0417':'Saved unchanged and why publication still checks the saved version',
 'C0444':'Show parent links and the initially hidden containment rows',
 'C0452':'dropping changes containment rather than setting a manual sibling position',
 'C0453':'same-type and widening value conversions and restoration only from effective reclassifications',
 'C0462':'the exclusion of deliberate clears and discarded reclassifications from restoration',
 'C0481':'the ancestor-scoped uniqueness check after changing parent',
 'C0538':'Show parent links and why a move already appears as a Parent change',
 'C0547':'the subtree-size refusal and its reported limit',
 'C0558':'the 500-record bound and the preview digest checked at confirmation',
 'C0611':'Stop following in notification settings and notices excluding the publisher',
 'C0739':'publication notices now open the active publication rather than always leading nowhere',
 'C0743':'publication notices can now open the active publication',
 'C0745':'the limits of locale and language settings, separate from the digest time-zone choice',
 'C0767':'notices arriving while the subject is already open being marked read automatically',
 'C0957':'preserving retained relationship identities and their attribute values on replacement',
 'C0969':'the twenty-target preview bound and continuation for the remaining targets',
 'C0989':'fixed digest wording and its independence from AI settings and permissions',
 'C0994':'clients cannot follow workspaces or receive digests',
 'C0997':'the exclusion of names from digest mail',
 'C1014':'the complete eligibility rules when mail, addresses or the person are unavailable',
 'C1038':'a step-by-step withdrawal task; lineage labels are already explained',
 'C1049':'the read-only check on creation as well as update and removal',
 'C1052':'recovery when a field removal succeeded but refreshing its content failed',
 'C1054':'defaults fill required values on creation only',
 'C1056':'the skip-versus-atomic policy for selected-record deletion',
 'C1057':'empty text and null do not participate in attribute uniqueness',
 'C1071':'the selected-record bulk-delete dialog and its confirmation counts',
 'C1074':'the detailed bulk-value and bulk-relationship dialogs',
 'C1086':'replacing a many-valued relationship set in the selection dialog',
 'C1089':'the exact ancestor scope and conditional target-value test',
 'C1125':'the conditional ancestor-scoped uniqueness rule',
 'C1177':'how each of the four cardinalities constrains each end',
 'C1183':'bulk-relationship and set-replacement tasks',
 'C1184':'the capability page for lists and filters; the find-records guide supplies the task',
 'C1185':'the changing-many-records capability page and its dialogs',
 'C1189':'the twenty-target preview bound and paging the rest',
 'C1193':'candidate counts that distinguish eligible records from already-held relationships',
 'C1196':'the many-valued set-replacement dialog',
 'C1205':'the record picker keyboard commands, including Ctrl+Home and Ctrl+End',
 'C1257':'the conditional ancestor-scoped uniqueness rule',
 'C1258':'the conditional ancestor-scoped uniqueness rule',
 'C1264':'refusing duplicate directed relationships and repeated initial relationships',
 'C1741':'the migration conversion choices and loss-confirmation task',
 'C1756':'matching a missing named record under the chosen fixed parent',
 'C1802':'checking and accepting changes in the next version of a saved-profile workbook',
 'C1807':'updating the original records when moving mapped copies back',
 'C1811':'the split and merge choices for model-mapping operations',
 'C1817':'the complete same-workspace migration task, including loss confirmation',
 'C1822':'the supported workbook inference patterns and their limits',
 'C1899':'an empty navigation group is valid',
 'C1911':'the offered collision-free profile key and the Save with another key recovery',
 'C1914':'the individual consumer API form options beyond the six-tab overview',
 'C1928':'the complete list of model-language options unavailable in the visual editor',
 'C1936':'the dependent cleanup and removal of history entries after moving a branch',
 'C1940':'the relationship hint control and the information it opens',
 'C1957':'the dependent references and issues caused by removing the selected element',
 'C1958':'the dependent references and issues caused by removing the selected element',
 'C1959':'atomic model-operation requests through the API',
 'C1961':'the phone Start move control and available destinations',
 'C2260':'the individual consumer API editor forms',
 'C2284':'the collection-export dialog and its options',
 'C2301':'which individual action groups accept a narrowing',
 'C2401':'reset-link refusals and their rate limits',
 'C2602':'the About page Open release link',
 'C2604':'the activation timestamp distinct from installation time',
 'C2622':'the probe-address Copy controls in Operations',
 'C2624':'the individual Operations fields for workers and threads',
 'C2630':'the About page engine/API/model-version facts',
 'C2714':'the administrator webhook subscription creation and editing screens',
 'C2715':'the latest-subject-wins rule for duplicate queued notices',
 'C2734':'the administrator webhook CRUD screens; the old host-change suspension is superseded',
 'C3315':'the job summary retained after row results and files expire',
 'C3316':'the Jobs screen filters, results and cancellation confirmation',
 'C3851':'the Jobs screen filters, results and cancellation confirmation',
}

covered_ids=set('C0046 C0047 C0048 C0054 C0059 C0060 C0065 C0068 C0069 C0070 C0073 C0077 C0081 C0085 C0086 C0087 C0090 C0096 C0097 C0098 C0099 C0103 C0189 C0193 C0194 C0195 C0196 C0216 C0217 C0218 C0219 C0220 C0221 C0224 C0225 C0226 C0229 C0230 C0232 C0233 C0236 C0321 C0324 C0325 C0326 C0328 C0329 C0330 C0331 C0333 C0335 C0336 C0337 C0340 C0341 C0342 C0343 C0344 C0345 C0349 C0350 C0353 C0354 C0355 C0356 C0357 C0359 C0360 C0361 C0362 C0363 C0364 C0365 C0366 C0367 C0368 C0369 C0370 C0372 C0373 C0374 C0375 C0414 C0415 C0416 C0418 C0420 C0421 C0423 C0424 C0425 C0426 C0427 C0428 C0429 C0430 C0431 C0432 C0434 C0445 C0446 C0447 C0448 C0449 C0450 C0451 C0454 C0455 C0456 C0457 C0458 C0459 C0460 C0461 C0464 C0465 C0466 C0467 C0469 C0470 C0471 C0472 C0473 C0474 C0475 C0476 C0477 C0479 C0480 C0482 C0483 C0485 C0486 C0536 C0537 C0539 C0540 C0541 C0544 C0545 C0546 C0548 C0552 C0553 C0554 C0555 C0556 C0559 C0561 C0563 C0564 C0565 C0566 C0568 C0571 C0572 C0574 C0575 C0576 C0577 C0578 C0579 C0585 C0604 C0605 C0610 C0612 C0613 C0615 C0616 C0617 C0618 C0619 C0734 C0735 C0736 C0737 C0738 C0740 C0741 C0742 C0744 C0746 C0766 C0768 C0769 C0770 C0771 C0772 C0773 C0774 C0775 C0776 C0777 C0778 C0779 C0780 C0781 C0782 C0783 C0784 C0967 C0968 C0986 C1006 C1039 C1040 C1041 C1042 C1043 C1045 C1075 C1179 C1192 C1746 C1755 C1798 C1813 C1897 C1898 C1908 C1909 C1916 C1917 C1918 C1964 C1981 C2439 C2455 C2463 C2599 C2603 C2610 C2612 C2613 C2615 C2616 C2618 C2619 C2621 C2623 C2628 C2629 C2707 C2708 C2709 C2711 C2713 C2717 C2718 C2730 C2732 C2735 C2736 C3024 C3211 C3218 C3301 C3305 C3894'.split())
excluded={
 'C0038':'A test matrix, not a separate reader capability; role and consumer-grant behavior remains in F27 and F5.',
 'C0228':'An old page-length audit rather than product behavior.',
 'C0231':'An old section-existence audit rather than product behavior; current sections have their own rows.',
 'C1799':'Reusable model modules are planned, not delivered.',
 'C1804':'The old model catalogue/card layout was replaced by the model page and tabs in 0.12 A3a.',
 'C2262':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2263':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2265':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2295':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2313':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2453':'Internal security test evidence; reader-visible permissions have their own records.',
 'C2626':'A document heading, not a product behavior.',
}

redirect={
 'C0092':'use/account','C0100':'use/account','C0101':'use/account',
 'C0191':'run/sign-in-and-mail-setup','C0192':'administer/people-and-groups',
 'C0194':'administer/sign-in','C0220':'use/account','C0221':'use/account',
 'C0216':'use/records','C0217':'use/records','C0218':'model/models',
 'C0344':'use/history','C0345':'use/history','C0356':'use/home','C0357':'use/home',
 'C0434':'use/history','C0463':'guide/use/find-records','C0538':'use/change-sets',
 'C0546':'use/change-sets','C0604':'use/inbox-and-approvals','C0605':'use/workspaces',
 'C0734':'model/managing-workspaces','C0735':'use/home','C0746':'administer/approval-policies',
 'C0781':'use/applications','C0782':'use/home','C0784':'model/managing-workspaces',
 'C0961':'administer/sign-in','C0986':'use/applications','C1006':'use/inbox-and-approvals',
 'C1048':'model/model-mappings','C1075':'use/records','C1179':'use/mapping-grids',
 'C1192':'use/mapping-grids','C1798':'run/model-releases-and-rollback',
 'C1807':'model/model-mappings','C1909':'model/model-mappings','C1981':'use/hierarchies',
 'C2264':'guide/model/add-a-record-type-and-fields','C2406':'administer/roles-and-grants',
 'C2439':'administer/sign-in','C2455':'model/managing-workspaces','C2463':'administer/approval-policies',
 'C2599':'run/upgrades','C2603':'run/configure','C2610':'run/sign-in-and-mail-setup',
 'C2612':'run/health-and-startup-checks','C2613':'run/webhook-delivery',
 'C2615':'run/background-jobs','C2616':'run/sign-in-and-mail-setup','C2618':'run/background-jobs',
 'C2619':'run/licence-and-source','C2621':'run/health-and-startup-checks','C2623':'run/backup-and-restore',
 'C2628':'run/secrets-and-keys','C2707':'run/webhook-delivery','C2708':'run/monitoring',
 'C2715':'run/several-processes','C2717':'run/developer-instance','C2718':'run/sign-in-and-mail-setup',
 'C2730':'run/command-line','C2732':'run/several-processes','C2735':'run/sign-in-and-mail-setup',
 'C3024':'run/webhook-delivery','C3301':'run/background-jobs','C3305':'run/background-jobs',
}

def gap_for(x,home):
 ident,item=x[0],x[1];s=item.lower()
 if ident in gaps:return gaps[ident]
 if any(phrase in s for phrase in ['500 operations','500 model','at most 500 records']):return 'the operation-size bound and its refusal'
 if home.startswith('guide/') and not any(t in s for t in ['composite','next version','migration','consumer api']):return None
 if ident in covered_ids:return None
 if home=='use/account':
  if 'password' in s and any(t in s for t in ['common','15','128','slow']):return 'password limits and refusal/recovery behavior'
  if any(t in s for t in ['appearance','density','palette','pencil']):return 'the Appearance controls and their choices'
 if home=='use/change-sets':
  if 'empty' in s and ('root' in s or 'bootstrap' in s):return 'starting and reviewing an empty root change set'
  if any(t in s for t in ['saved unchanged','starting values','created and then deleted']):return 'how unchanged saves and create-then-delete appear in review'
  if 'migration' in s or 'migrate' in s:return 'the migration choices, locking and confirmation task'
  if 'unique' in s and ('defer' in s or 'hold' in s):return 'the immediate attribute-uniqueness check, separate from deferred relationship scope validation'
 if home=='use/hierarchies':
  if any(t in s for t in ['restor','offered back','widening','effective reclassification']):return 'which effective reclassifications can restore values, and which clears cannot'
  if '500' in s or 'digest' in s:return 'the 500-record bound and confirmation against the preview digest'
  if 'manual' in s or 'child order' in s:return 'containment changes versus the model-defined sibling order'
 if home in ['use/records','use/relationships']:
  if any(t in s for t in ['bulk','selected-record','many records']):return 'the bulk-action options, preview and refusal handling'
  if any(t in s for t in ['scoped unique','scoped uniqueness','uniquetoancestor','uniquewhen']):return 'the exact ancestor scope and conditional uniqueness test'
  if any(t in s for t in ['many-valued','many-to-many set','replace the set','set replacement']):return 'the many-valued replacement dialog and conflict recovery'
  if 'unique' in s and ('empty' in s or 'null' in s):return 'empty text and null being excluded from attribute uniqueness'
  if 'default' in s and 'create' in s:return 'defaults applying on creation only'
 if home in ['use/mapping-grids','use/relationships'] and any(t in s for t in ['20','twenty','continuation']):return 'the target-preview bound and reading the remaining targets'
 if home=='use/relation-matrices':
  if 'five' in s or '5 ' in s or 'preview' in s:return 'the five-record cell preview alongside the complete count'
  if 'incoming' in s:return 'why incoming reads have no target-end inactive or uniqueness-conflict states'
 if home in ['use/inbox-and-approvals','use/home']:
  if '50' in s:return 'counting all eligible notices while listing only the fifty newest'
  if any(t in s for t in ['twenty-four','24-hour','24 hour','nextat','cutoff']):return 'digest eligibility without a twenty-four-hour cutoff and when the next run resets'
  if any(t in s for t in ['no names','without record','privacy']):return 'the names omitted from digest email'
  if 'lost access' in s or 'loses access' in s:return 'the follow choice surviving lost access while delivery stops'
  if 'already open' in s:return 'automatically reading a notice whose subject is already open'
 if home.startswith('model/'):
  if 'composite' in s:return 'binding, filling and resolving every component of a composite import key'
  if 'next version' in s and ('workbook' in s or 'profile' in s):return 'checking the next file, accepting renames and ignoring new columns'
  if 'consumer' in s and any(t in s for t in ['field','operation','form','tab']):return 'the individual consumer API form options and allowed operations'
  if 'migration' in s or 'migrate' in s:return 'the migration conversion, loss and confirmation choices'
  if any(t in s for t in ['repeated headings','same headers','key column','column merging','pattern']):return 'the precise workbook inference and key-merging rules'
 if home=='administer/roles-and-grants':
  if any(t in s for t in ['mail','smtp']):return 'the administrator mail-configuration screen and its refusal states'
  if 'consumer' in s and ('editor' in s or 'form' in s):return 'the individual consumer API editor forms'
 if home.startswith('run/'):
  if 'import' in s and any(t in s for t in ['profile','column','mapping','workbook']):return 'the import-profile options and row/refusal reports beyond the operational job lifecycle'
  if 'webhook' in s and any(t in s for t in ['create/read','subscription:','subscriptions:','crud']):return 'the subscription-management task and its controls'
 # Exact labels matter for screen inventories. A missing literal is a concrete
 # writing gap, not proof of a product defect. Exclude source filenames and code.
 page=(ROOT/'src/content/docs'/Path(home+'.md')).read_text().lower()
 labels=re.findall(r'"([^"\n]{4,100})"',item)
 absent=[q for q in labels if q.lower() not in page and not re.search(r'[<>]|\.tsx|\.py|^N |^<|^\d|^https?://',q)]
 if absent:return 'the screen wording/options '+', '.join('“'+q+'”' for q in absent[:3])
 # Source-level descriptions with explicit technical contracts cannot be proved
 # by a browser explanation and belong in the integration writing brief.
 if re.search(r'\b(GET|POST|PUT|PATCH|DELETE)\b|expectedVersion|setVersion|RELATION_[A-Z_]+|JSON pointer',item):return 'the API sequence, preconditions and refusal recovery for this behavior'
 return None

pattern=r'partly: \[([^\]]+)\]\(\.\./src/content/docs/([^\)]+)\) — [^;]*(?=;|$)'
for x in rows:
 old=x[6]
 if old=='after 0.16':continue
 if x[0] in excluded:x[6]='not for readers: '+excluded[x[0]]
 else:
  def replace(m):
   home=redirect.get(x[0],m[2].split('.md')[0])
   if not (ROOT/'src/content/docs'/Path(home+'.md')).is_file():raise ValueError((x[0],home))
   gap=gap_for(x,home)
   return ('partly: '+link(home)+' — missing: '+gap) if gap else link(home)
  x[6]=re.sub(pattern,replace,old)
 if x[6]!=old:changes.append({'id':x[0],'before':old,'after':x[6]})

# Correct historical statements rather than treating superseded wording as a gap.
corrections={
 'C0190':'Sessions renew while working. Refresh-token reuse ends the session except for the limited thirty-second recovery case (R128).',
 'C0322':'Change sets enforce attribute uniqueness immediately; ancestor-scoped relationship breaches may be staged but are refused by validation or publication.',
 'C0371':'Unique attribute values are checked immediately, including in change sets; a direct swap of two held values is refused.',
 'C0739':'Approval and job notices identify their subject. Publication notices open the active publication when it remains available; removed subjects cannot be opened.',
 'C0743':'Failed job notices go to the requester. A publication notice opens the active publication when it is still available.',
 'C1764':'The current accepted model schema language is 0.10; older installed documents require the supported raising workflow.',
 'C2406':'Roles are action groups. There are nine general predefined roles plus the Agent role; custom roles can be created or copied.',
 'C2734':'Webhook subscriptions can be created, read, listed, edited, paused, resumed and deleted. HTTPS may use any host; HTTP is loopback-only. Model, contract, workspace, filter and expired-event changes can suspend delivery; the former host allowlist is removed.',
 'C3857':'People workbooks follow table columns/order/labels, with advanced choices, relationship sheets, hidden IDs/versions and non-imported summaries. Blank attributes do not clear stored values; a blank replacing relationship-set cell clears that set when valid.',
}
for ident,item in corrections.items():
 by[ident][1]=item
 by[ident][5]+='; C1b current-release correction (R085, R128, R140 or release amendment as applicable)'

# Fix invented aliases in the added rows to the settled outline paths.
homes={'model/model-editor':'model/the-model-editor','run/jobs':'run/background-jobs','use/notifications':'use/inbox-and-approvals','use/import-and-export':'use/importing-and-exporting'}
for x in rows:
 for wrong,right in homes.items():x[6]=re.sub(r'(?<![\w/-])'+re.escape(wrong)+r'(?![\w/-])',right,x[6])

cp.write_text(text[:text.index('| ID |')]+'| ID | Item | Kind | Reader | Section | Source | Covered by |\n|---|---|---|---|---|---|---|\n'+'\n'.join(row(x) for x in rows)+'\n')
(NOTES/'coverage-page-judgments.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(NOTES/'semantic-merges.json').write_text(json.dumps(merges,indent=2)+'\n')
print('Saved',len(rows),'rows;',len(merges),'semantic merges;',len(changes),'page judgments updated.')
