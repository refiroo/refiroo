from reconcile import *
from collections import Counter
p=ROOT/'_waves/COVERAGE.md'; text=p.read_text(); rows=table(text,r'^\| C\d'); by={x[0]:x for x in rows}
merges=json.loads((NOTES/'semantic-merges.json').read_text())
def link(h):return '['+h+'](../src/content/docs/'+h+'.md)'
def merge(keep,remove,append=True):
 a=by[keep];b=by[remove]
 if b not in rows:return
 if append and b[1].lower().rstrip('.') not in a[1].lower():a[1]+=' '+b[1]
 a[5]+='; '+b[5]+' (merged '+remove+')'
 a[3]=', '.join(dict.fromkeys((a[3]+', '+b[3]).split(', ')))
 if b[6]!=a[6]:a[6]+='; '+b[6]
 rows.remove(b);merges.append({'keep':keep,'removed':remove,'reason':'Same writing obligation; source and reader coverage retained.'})

# The older audit is evidence for the capability, never a second requirement
# that all its former absences must still be true today.
for keep,remove in [('C0086','C0096'),('C0189','C0097'),('C0224','C0229'),('C0226','C0230'),
 ('C0544','C0464'),('C0571','C0568'),('C0612','C0610'),('C0742','C0731'),
 ('C1041','C1038'),('C1125','C1074'),('C1075','C1184'),('C1056','C1185'),
 ('C1746','C1270'),('C1316','C1321'),('C1697','C1807'),('C1916','C1915'),
 ('C1917','C1897')]:
 # Only fold an audit into a row that actually concerns the same capability.
 if (keep,remove) in [('C1125','C1074'),('C1075','C1184'),('C1746','C1270'),('C1316','C1321'),('C1697','C1807')]:continue
 merge(keep,remove,False)

# Narrow rule statements and their fuller release statement are one obligation.
for keep,remove in [('C3921','C3929'),('C3931','C3941'),('C3931','C3942'),
 ('C3932','C3943'),('C3935','C3944'),('C3948','C3965'),('C3946','C3966'),
 ('C3947','C3967'),('C3957','C3968'),('C3959','C3969'),('C3955','C3971'),
 ('C3960','C3972'),('C3980','C3988'),('C3980','C3989'),('C3975','C3990'),
 ('C3991','C4008'),('C3992','C4009'),('C3998','C4011'),('C4004','C4012'),
 ('C4019','C4044'),('C4019','C4045'),('C4022','C4046'),('C4022','C4049'),
 ('C4028','C4048'),('C4037','C4051'),('C4059','C4065'),('C4052','C4066')]:merge(keep,remove)

# The cells below identify what is actually absent in the current pages.
states={
 'C0068':link('use/workspaces')+'; '+link('guide/use/open-an-application'),
 'C0093':'partly: '+link('administer/people-and-groups')+' — missing: the explicit limits on bulk person import and invitations beyond a password link',
 'C0192':link('administer/people-and-groups'),
 'C0322':'partly: '+link('use/change-sets')+' — missing: immediate attribute uniqueness versus deferred relationship-scope validation',
 'C0371':'partly: '+link('use/change-sets')+' — missing: immediate uniqueness prevents a direct exchange of two held values',
 'C0627':'not for readers: An old list of missing model pages, not a distinct product obligation; each named capability has its own model row.',
 'C0629':'not for readers: An old page-location audit; JSON, versions, migrations, workspaces and workbook onboarding have their own rows.',
 'C0927':link('model/workbook-onboarding')+'; partly: '+link('guide/model/start-a-draft-from-a-workbook')+' — missing: the complete workbook inference pattern catalogue',
 'C0995':'partly: '+link('use/inbox-and-approvals')+'; '+link('use/account')+' — missing: the dedicated notification-settings task, schedule edge cases and follow-choice retention',
 'C1041':link('use/publications')+'; partly: '+link('guide/use/browse-a-publication')+' — missing: a step-by-step withdrawal task',
 'C1074':'partly: '+link('use/records')+' — missing: ancestor-scoped uniqueness and the detailed bulk-action dialogs; field kinds, inline editing, atomic creation and history are covered',
 'C1184':'partly: '+link('guide/use/find-records')+' — missing: the lists-and-filters capability page',
 'C1270':link('model/managing-workspaces')+'; '+link('use/workspaces'),
 'C1316':link('guide/model/add-a-record-type-and-fields')+'; '+link('guide/model/add-a-relationship'),
 'C1697':link('model/model-mappings')+'; partly: '+link('guide/model/move-records-to-another-model')+' — missing: the detailed copy/move job-results screen',
 'C1844':link('model/releases')+'; partly: '+link('guide/model/install-and-activate-a-release')+' — missing: detailed migration result classes and the conversion/loss task',
 'C2253':link('use/records')+'; '+link('administer/roles-and-grants'),
 'C3360':'partly: '+link('model/the-model-editor')+' — missing: the individual consumer API editor forms and their options',
 'C3860':'partly: '+link('examples/the-starter-model')+' — missing: the starter consumer API showcase in examples/the-consumer-api',
 'C3924':'partly: '+link('model/releases')+' — missing: the recorded predecessor versus a labelled same-key fallback and the first-release baseline',
 'C3925':'partly: '+link('model/releases')+' — missing: the unsupported historical release comparison state while metadata and export remain available',
 'C3926':'partly: '+link('use/change-sets')+' — missing: unsaved-input protection and recovery when the new pinned model cannot refresh',
 'C3927':'partly: '+link('use/mapping-grids')+' — missing: choosing the target application and explaining an unavailable required parent',
 'C3928':'steward: '+link('use/records')+'; model-admin: '+link('model/releases')+'; operator: '+link('run/troubleshooting'),
 'C3930':'steward: partly: '+link('use/mapping-grids')+' — missing: retained relationship values versus an explicitly empty replacement; integrator: uncovered → integrate/writing-in-bulk',
 'C3931':'steward: partly: '+link('use/relation-matrices')+' — missing: five-record previews and target-end states being outgoing-only; model-admin: partly: '+link('use/relation-matrices')+' — missing: target-end state direction; integrator: uncovered → integrate/reading-records',
 'C3932':'partly: '+link('use/hierarchies')+' — missing: effective-reclassification restoration, preserved relationship IDs and the exclusions for deliberate clears/discarded changes',
 'C3933':'partly: '+link('use/hierarchies')+' — missing: model-defined sibling order and the same-type constraint for moving multiple records',
 'C3934':'steward: partly: '+link('guide/use/find-records')+' — missing: default name ordering and unsupported computed/timestamp sorts; model-admin: partly: '+link('model/the-model-editor')+' — missing: all non-JSON fields may sort despite the sortable flag; integrator: uncovered → integrate/reading-records',
 'C3937':'steward: partly: '+link('use/hierarchies')+' — missing: following the changed type and matching either type in review filters; integrator: uncovered → integrate/workspaces-contexts-and-models',
 'C3938':'partly: '+link('use/relation-matrices')+' — missing: returning from a stale edit to cell actions when its record is gone',
 'C3939':'steward: '+link('use/change-sets')+'; integrator: uncovered → integrate/changes-approvals-and-publication',
 'C3940':'partly: '+link('use/hierarchies')+' — missing: the lossless widening pairs and destination-rule failures becoming inputs',
 'C3973':'model-admin: partly: '+link('model/the-model-editor')+' — missing: the 500-operation bound and own-model impact boundary; integrator: uncovered → integrate/model-and-release-operations',
 'C3974':'partly: '+link('model/releases')+' — missing: the installed base/version behavior and editable next-version proposal after a duplicate installation',
 'C3975':link('model/the-model-editor'),
 'C3977':'partly: '+link('model/workbook-onboarding')+' — missing: owner-scoped replacement, superseded-file retention and stopping dependent dry runs on deletion',
 'C3978':'partly: '+link('model/workbook-onboarding')+' — missing: which changes restart a dry run and which preserve it',
 'C3981':'partly: '+link('model/workbook-onboarding')+' — missing: the full supported pattern catalogue and precise preservation of manual/undone decisions',
 'C3985':'partly: '+link('model/workbook-onboarding')+' — missing: letter-stable bindings and the three-same-heading-list merge rule',
 'C3994':link('model/model-mappings'),
 'C3995':link('model/model-mappings')+'; '+link('guide/model/move-records-to-another-model'),
 'C3996':link('model/model-mappings'),
 'C3997':'steward: partly: '+link('model/model-mappings')+' — missing: updating originals or recreating their IDs when moving copies back; integrator: uncovered → integrate/model-and-release-operations',
 'C3999':'partly: '+link('model/the-model-editor')+' — missing: the same-model fallback baseline and limiting operation impact to that model’s workspaces',
 'C4001':'operator: '+link('run/database')+'; '+link('run/troubleshooting')+'; integrator: uncovered → integrate/identifiers-paging-and-errors',
 'C4002':link('run/health-and-startup-checks'),
 'C4003':'operator: '+link('run/several-processes')+'; '+link('run/background-jobs')+'; integrator: uncovered → integrate/jobs',
 'C4004':'partly: '+link('guide/use/find-records')+' — missing: browser Find covers only drawn rows',
 'C4005':link('use/hierarchies')+'; '+link('guide/use/arrange-records-in-a-tree'),
 'C4006':link('use/hierarchies'),
 'C4013':'access-admin: '+link('administer/clients')+'; '+link('administer/roles-and-grants')+'; integrator: uncovered → integrate/consumer-apis',
 'C4014':'access-admin: '+link('administer/roles-and-grants')+'; integrator: uncovered → integrate/security-model-for-integrators',
 'C4015':link('use/change-sets')+'; '+link('administer/approval-policies'),
 'C4016':link('use/inbox-and-approvals')+'; '+link('administer/approval-policies'),
 'C4018':'steward: partly: '+link('use/account')+' — missing: password bounds/common-password refusal and slowdown; access-admin: partly: '+link('administer/sign-in')+' — missing: exact limits and slowdown thresholds',
 'C4019':'steward: partly: '+link('use/account')+' — missing: proof before adding a passkey and the local-password prerequisite; access-admin: partly: '+link('administer/sign-in')+' — missing: the registration proof requirement; operator: '+link('run/sign-in-and-mail-setup'),
 'C4020':link('administer/people-and-groups'),
 'C4021':link('administer/sign-in')+'; '+link('administer/people-and-groups'),
 'C4022':'partly: '+link('administer/sign-in')+' — missing: secret re-entry after changing endpoints; mail screen: uncovered → administer/mail',
 'C4023':'operator: '+link('run/sign-in-and-mail-setup')+'; access-admin: uncovered → administer/mail',
 'C4024':'steward: partly: '+link('use/inbox-and-approvals')+' — missing: immediate-mail eligibility since enabling and its 24-hour bound; operator: '+link('run/sign-in-and-mail-setup'),
 'C4025':link('use/inbox-and-approvals'),
 'C4026':'steward: partly: '+link('use/inbox-and-approvals')+' — missing: notices arriving while the subject is open and decision/cancellation handling; integrator: uncovered → integrate/changes-approvals-and-publication',
 'C4028':'model-admin: '+link('model/releases')+'; operator: '+link('run/model-releases-and-rollback'),
 'C4029':'model-admin: partly: '+link('model/releases')+' — missing: the in-place schema-raising screen and review; operator: '+link('run/upgrades'),
 'C4030':'steward: '+link('use/workspaces')+'; model-admin: partly: '+link('model/releases')+' — missing: reopening a workspace after raising its stored schema; operator: '+link('run/health-and-startup-checks'),
 'C4033':'evaluator: uncovered → about/compatibility-and-licence; operator: '+link('run/licence-and-source'),
 'C4034':link('run/install-with-compose')+'; '+link('run/https'),
 'C4035':link('run/https')+'; '+link('run/security-checklist'),
 'C4037':link('run/secrets-and-keys'),
 'C4038':'partly: '+link('administer/roles-and-grants')+'; '+link('guide/administer/grant-a-role')+'; '+link('guide/administer/manage-a-group')+' — missing: the explicit all-or-nothing boundary of bulk group removal',
 'C4040':link('use/history'),
 'C4052':'steward: partly: '+link('use/inbox-and-approvals')+' — missing: no 24-hour digest cutoff, all-notice counts and retained job outcome counts; integrator: uncovered → integrate/changes-approvals-and-publication',
 'C4053':'steward: partly: '+link('use/account')+' — missing: when the next digest time moves or stays unchanged; integrator: uncovered → integrate/changes-approvals-and-publication',
 'C4054':'steward: partly: '+link('use/home')+' — missing: retaining the follow choice while access or activity is lost; integrator: uncovered → integrate/changes-approvals-and-publication',
 'C4055':'partly: '+link('use/inbox-and-approvals')+' — missing: opening only an active readable publication and otherwise remaining in the inbox',
 'C4056':'partly: '+link('model/managing-workspaces')+' — missing: remembered-draft reuse, detachment and permission/compatibility fallback',
 'C4057':'partly: '+link('model/managing-workspaces')+' — missing: activation-failure recovery after installation succeeded and retrying each stage',
 'C4060':'steward: '+link('guide/use/find-records')+'; integrator: uncovered → integrate/reading-records',
 'C4061':link('model/the-model-editor')+'; '+link('guide/model/arrange-applications-and-views'),
 'C4062':'partly: '+link('model/the-model-editor')+' — missing: the exact zero-impact boundary and remaining-reference diagnostics after removal',
}
for ident,status in states.items():
 if by[ident] in rows:by[ident][6]=status

# Authoritative planned homes, as settled in OUTLINE. Avoid invented page names.
homes={
 'use/bulk-changes':'use/changing-many-records','use/copy-and-move':'model/model-mappings',
 'model/import-profiles':'model/workbook-onboarding','administer/workspaces':'model/managing-workspaces',
 'administer/sign-in-providers':'administer/sign-in','run/webhooks':'run/webhook-delivery',
 'run/install':'run/install-with-compose','run/security':'run/security-checklist',
 'integrate/relationships-and-mappings':'integrate/writing-in-bulk','integrate/records-and-values':'integrate/reading-records',
 'integrate/paging-and-queries':'integrate/identifiers-paging-and-errors',
 'integrate/consumer-events':'integrate/consumer-events-and-webhooks','integrate/webhooks':'integrate/consumer-events-and-webhooks',
 'integrate/consumer-crosswalks':'integrate/looking-up-and-resolving','integrate/consumer-lookup':'integrate/looking-up-and-resolving',
 'integrate/effective-dates':'integrate/business-dates','integrate/import-and-export':'integrate/files-imports-and-exports',
 'integrate/authentication':'integrate/signing-in-and-tokens',
}
for x in rows:
 for wrong,right in homes.items():x[6]=re.sub(r'(?<![\w/-])'+re.escape(wrong)+r'(?![\w/-])',right,x[6])

# Preserve the deferred AI inventory exactly, including older rows whose
# judgment was not yet spelled after 0.16. Digests/following stay in scope.
before={x[0]:x for x in table((NOTES/'COVERAGE.before.md').read_text(),r'^\| C\d')}
held=[]
for x in rows:
 old=before.get(x[0])
 if old and (old[6]=='after 0.16' or re.search(r'\bAI\b|assistant|\bMCP\b|agent access|Ask in words|Propose targets',old[1],re.I)) and not re.search(r'digest|follow|neither an AI|no AI',old[1],re.I):
  x[:]=old;held.append(x[0])

# Rewrite obsolete audit assertions as current obligations. Their original
# audit wording remains in COVERAGE.before.md and their source identities.
audit_items={
 'C0068':'Open a workspace or application address, handle a missing model element, find another suitable workspace and open a retired workspace.',
 'C0095':'Open notification settings and Appearance from the account area.',
 'C0204':'Choose theme, density, palette and pencil visibility, and use keyboard and phone navigation.',
 'C0348':'Use change-set actions, propose changes, withdraw a request and prepare or migrate to another model release.',
 'C0611':'Follow a workspace, receive publication notices excluding one’s own publication and stop following from notification settings.',
 'C0628':'Import and export records, edit a people workbook, use import profiles and follow or download jobs.',
 'C0927':'Build a model from a workbook using inference, source lists, column/value mappings, dry runs and loading into a change set.',
 'C0995':'Set notice email by kind to At once, Digest or Off; choose the digest schedule and follow or stop following workspaces.',
 'C1074':'Edit typed fields inline or in a dialog, create with parent and required relationships, review deletion impact and use bulk actions under the same rules.',
 'C1075':'Read validity periods in the browser, which has no business-date filter.',
 'C1137':'A matrix chooses the first suitable declared field, belongs to a model-declared application and leaves records in their own applications.',
 'C1183':'Set, change or delete relationships, edit their fields, recognise parent-managed locks, apply candidate rules and replace a many-valued set.',
 'C1184':'Understand lists, search, filters, scrolling, positions and related-record columns as a capability, alongside the find-records task.',
 'C1270':'Manage workspace defaults, retirement, reactivation, deletion, model changes and the deployment setting that disables mutations.',
 'C1316':'Create types and fields, choose placements and candidate criteria, and configure cardinality and required relationships within the visual editor’s limits.',
 'C1321':'Arrange application listings and navigation groups and create table layouts or relation matrices with the supported editor controls.',
 'C1605':'Fix model issues using the offered actions and compare full-source dry-run results.',
 'C1697':'Use the Copy and move catalogue, mapping editor, release-mismatch recovery and copy/move job results.',
 'C1746':'Browse models, their ordering and state marks, tabs, workspace assignments and disabled-mutation state with the appropriate permissions.',
 'C1844':'Install and activate releases, review compatibility results, compare history, copy technical IDs, export, retire, bring back or delete unused releases.',
 'C1914':'Edit consumer APIs in the model editor and use the JSON and export views where appropriate.',
 'C1916':'Use the model editor frame, keyboard model tree, phone tabs, draft facts, menus and relationship matrix.',
 'C1917':'After a concurrent edit, see the other administrator’s steps and choose Apply mine again or recover a local JSON edit.',
 'C2253':'Contributors propose a change through a change set; the interface follows their permitted actions.',
 'C3360':'Configure consumer API contracts with the model editor’s individual forms.',
 'C3860':'Understand the starter model as an optional example, including its consumer API showcase.',
 'C3861':'Use example application names only in the example section and clearly marked examples or captions.',
}
for ident,item in audit_items.items():
 if by[ident] in rows:by[ident][1]=item

def status(x):
 s=x[6]
 if s=='after 0.16':return 'after'
 if s.startswith('not for readers:'):return 'excluded'
 if 'uncovered' in s:return 'uncovered'
 if 'partly:' in s:return 'partly'
 return 'covered'
order=['about','use','model','administer','run','integrate','examples','journeys']
counts={s:Counter(status(x) for x in rows if x[4]==s) for s in order}
header='''# C1 coverage ledger

Snapshot: 2026-11-03. C1b release reconciliation and existing-page review completed. Counts describe this writing ledger, not release acceptance or proof that the product has no other behavior.

Each row is a writing obligation, ordered by section. Sources retain the original record identities; merged IDs are recorded in the surviving Source cell and `_coverage/notes/C1b-RELEASES/semantic-merges.json`. A journey appears once under `journeys`; its variants remain capability/rule obligations. Several readers may share an item. Counts use the least complete reader judgment: uncovered before partly before covered. `not for readers` preserves excluded or superseded evidence without making it a writing task.

Covered judgments cite current page text. Partly judgments identify a specific missing clause, task or screen wording; they no longer mean merely that a page was not read. Existing non-AI pages referenced by those judgments were read in full. Coverage is a documentation judgment, not runtime verification. The `after 0.16` AI/agent inventory is retained unchanged; digests and following are current work. A few older AI rows retain their original generic judgment under that explicit deferral.

Inputs: PROMISES.md, BEHAVIOUR-RULES.md, OUTLINE.md, NOT-YET-COVERED.md, MODEL-EDITOR-INVENTORY.md, UI-INVENTORY-SETTINGS.md, UI-INVENTORY-DATA.md, ../_coverage/restored/INVENTORY.md and docs/product-functionality/USER_JOURNEYS.md. Old page-existence audits were reconciled against current pages, not repeated as product facts. Planned homes follow OUTLINE.md. Detailed release resolutions and page judgments are saved under `_coverage/notes/C1b-RELEASES/`.

Counts (covered / partly / uncovered / after 0.16; not for readers separately):

'''
for s,c in counts.items():header+='- '+s+': '+' / '.join(str(c[k]) for k in ['covered','partly','uncovered','after'])+f'; not for readers: {c["excluded"]}.\n'
header+=f'\nTotal: {len(rows)} rows; 183 deferred AI/agent release-evidence leads retained. Stable IDs are not renumbered after merging.\n\n'
rows.sort(key=lambda x:(order.index(x[4]),int(x[0][1:])))
p.write_text(header+'| ID | Item | Kind | Reader | Section | Source | Covered by |\n|---|---|---|---|---|---|---|\n'+'\n'.join(row(x) for x in rows)+'\n')
(NOTES/'semantic-merges.json').write_text(json.dumps(merges,indent=2)+'\n')
(NOTES/'final-counts.json').write_text(json.dumps({'rows':len(rows),'sections':counts,'semantic_merges':len(merges),'ai_rows_preserved':held},indent=2)+'\n')
print('Saved',len(rows),'rows;',len(merges),'semantic merges. Counts:',dict(counts))
