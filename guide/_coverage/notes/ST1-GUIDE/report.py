from pathlib import Path
import json,re,difflib
notes=Path('guide/_coverage/notes/ST1-GUIDE')
old=json.loads((notes/'baseline.json').read_text())
progress=Path('guide/_waves/progress/ST1-GUIDE.md').read_text()
changed=set(re.findall(r'`(guide/src/content/docs/[^`]+)`: (?!Checked the page)',progress))
changed={p for p in changed if old[p]!=Path(p).read_text()}
r=['# ST1-GUIDE report','',f'All {len(old)} assigned pages checked: {len(changed)} edited, {len(old)-len(changed)} unchanged. No commits or git state changes. Screenshot files and their Markdown references were preserved.','',
'## Validation','',
'`GUIDE_OUT=_build/ST1-GUIDE npm run build` in `guide/` passed (257 pages, first run 4.83 seconds). A final rebuild after the last wording correction is recorded in `build.log`. The build reports a `/404` route-priority warning and completes successfully. No browser runtime or image-by-image visual acceptance was performed.','',
'## Differences, uncertainties and possible problems','',
'- Import profiles has no **Load more profiles** or **Show more** button. `ImportProfilesPage.tsx` supplies `onEnd` to `EntityList.tsx`, whose intersection observer loads more on scroll. The page now says to scroll.',
'- The brief and changelog generalise log footers as “n of m”. `LogFoot` only shows a total when supplied. AI Calls, Agent access, Jobs, Signing keys and Changes pass no total and show “n calls”, “n jobs”, “n changes”, etc. In particular a person’s Changes does not show “n of m changes”. No promise of a total was added.',
'- The brief and changelog generalise logs as time first with totals above. Jobs still starts with **Job** or **Job or group**, with **Created**/**Finished** or **Latest** later. Signing keys starts with **Key ID**. Agent client and registration tables start with the name. Their prose was not changed to claim otherwise.',
'- `ModelReleaseDetail.tsx` heads the comparison **Changes in this release** and the readiness check **Workspaces running** followed by the model key. **Release history** and **Activation check** remain explanatory text, not those section headings. Affected prose was corrected.',
'- Older pages still name **Settings › Data operations › Jobs** or **Import profiles**. `navigation.ts` places Jobs under **This instance** and Import profiles under **Workspaces and models**. These group names predate ST1; the brief says no route changed and requests only ST1 corrections. They need a separate navigation correction.',
'- Some existing screenshot alt text describes the old layout (“no person selected”, profile deletion “buttons”). The assignment forbids changing screenshot references, so their full Markdown was preserved.',
'- Another wave changed `use/workspaces.md` from “sheet” to “dialog” during this run. This wave made no edit to that page, reports it as no change and preserved the other edit.',
'- No runtime defect was established. The broad log-layout claims above differ from the delivered code. Screenshot recapture and browser verification remain outstanding.','',
'## Per-page changes','',
'Paths are relative to `guide/src/content/docs/`. Old and new blocks retain the affected paragraph or step when a sentence spans lines; unchanged surrounding words provide context.','']
for p,s in old.items():
 rel=p.split('src/content/docs/')[1];r+=['### '+rel,'']
 if p not in changed:r+=['No change.',''];continue
 now=Path(p).read_text()
 assert re.findall(r'!\[[^\]]*\]\([^)]*\)',s)==re.findall(r'!\[[^\]]*\]\([^)]*\)',now),p
 assert re.findall(r'^#{1,6} .*',s,re.M)==re.findall(r'^#{1,6} .*',now,re.M),p
 a=s.split('\n\n');b=now.split('\n\n')
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b).get_opcodes():
  if tag!='equal':r+=['Old:','',*['> '+v for v in '\n\n'.join(a[i:j]).splitlines()],'','New:','',*['> '+v for v in '\n\n'.join(b[k:l]).splitlines()],'']
exact=set('jobs-list.png run-jobs.png job-results-and-file.png notification-email-digest.png use-notification-email-digest-settings.png use-account.png use-account-sessions.png use-account-permissions.png use-import-profile-delete-actions.png use-import-profile-delete-confirm.png use-import-file-delete-confirm.png import-profile-next-version.png run-deployment.png run-operations.png run-ai-settings.png run-ai-provider-calls.png integrate-agent-access-connect.png use-workspaces-manage.png use-workspaces-detail.png use-workspace-default.png model-releases.png model-drafts.png model-structure.png model-workspace-model.png model-workspace-other-model.png model-list.png model-overview.png model-workspaces-list.png model-release-compare.png model-release-detail.png release-technical-details.png workspace-retire-dialog.png release-retire-dialog.png workspaces-new-dialog.png workspace-cannot-open.png'.split())
screens={}
for p in old:
 for alt,name in re.findall(r'!\[([^\]]*)\]\(/docs/screens/([^)]*)\)',Path(p).read_text()):
  if name.startswith('admin-') or name in exact:
   item=screens.setdefault(name,{'alt':alt,'pages':[]});item['pages'].append(p.split('src/content/docs/')[1])
r+=['## Outdated Settings screenshots and recapture candidates','',
'No screenshot was changed, renamed or rereferenced. Each row lists its filename, screen/state and every assigned page referencing it. Keep the state and controls named in the existing alt text visible, using the current Settings layout.','',
'Visually inspected and confirmed outdated: `admin-people.png` (split list and empty selection), `admin-client.png` (split list and header actions), `admin-ai-test-answered.png` (settings/test/calls together), `use-import-file-delete-confirm.png` (old split-page background and deletion buttons).','',
'The remaining entries are recapture candidates identified from their documented Settings surface and the changed source; each has not been visually inspected. A dialog can remain correct while its background shows the old page. AI test results and Calls now need separate tab captures; retain filenames until the screenshot owner decides how to replace them.','',
'| Screenshot | Screen/state to retain | Referencing pages |','| --- | --- | --- |']
for name,item in sorted(screens.items()):r.append('| `'+name+'` | '+item['alt'].replace('|','\\|')+' | '+'; '.join('`'+p+'`' for p in item['pages'])+' |')
r+=['','Global account/workspace menus, record screens and workbook editor dialogs are not listed just because they show the surrounding application frame; changes there belong to other waves.','']
(notes/'report.md').write_text('\n'.join(r))
print(len(changed),'edited;',len(old)-len(changed),'unchanged;',len(screens),'Settings screenshot filenames. Report written.')
