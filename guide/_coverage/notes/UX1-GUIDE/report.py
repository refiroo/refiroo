from pathlib import Path
from datetime import datetime
import difflib,json,re
root=Path('guide/src/content/docs')
old=json.loads(Path('guide/_coverage/notes/UX1-GUIDE/originals.json').read_text())
steer=Path('guide/_waves/steer/UX1-GUIDE.md').read_text()
changed={p:(s,Path(p).read_text()) for p,s in old.items() if Path(p).read_text()!=s}
screen_re=r'!\[[^\]]*\]\((/docs/screens/[^)]+)\)'
for p,(before,after) in changed.items():
    assert re.findall(screen_re,before)==re.findall(screen_re,after),p
out=['# UX1-GUIDE completion report','',f'Written {datetime.now().astimezone().isoformat(timespec="seconds")}.','',f'{len(changed)} existing pages updated; {len(old)-len(changed)} allowed pages unchanged. No new page, sidebar entry, screenshot file or screenshot reference was added or renamed. The pre-existing content was saved before editing; the per-page report below compares that snapshot with the delivered text.','',
'## Added sections','',
'- `use/appearance-and-devices.md`: theme frame arrangements and reduced-motion behavior.','- `use/home.md`: Find a record, plus the revised placement of waiting work.','- `use/workspaces.md`: The workspace’s page, including shelf, search, application lists and activity.','- `use/records.md`: beside-list opening, in-place controls, switches, Undo and form disclosures.','- `model/the-model-editor.md`: short-operation popovers and side sheets.','- `administer/mail.md`: E-mail template, with Write and preview the layout and Add a logo and send a test.','- The existing mail setup guide and operator runbook link to that section. A separate template page would need `guide/sidebar/administer.mjs`, outside the allowed files. The wave’s explicit fallback to the nearest existing page was used.','',
'## Checks','',
'- `GUIDE_OUT=_build/UX1-GUIDE npm run build` in `guide/`: passed, 257 built pages.','- `GUIDE_OUT=_build/UX1-GUIDE npm run check` in `guide/`: passed terms, brand and sidebar checks.','- `GUIDE_OUT=_build/UX1-GUIDE npm run check:links` in `guide/`: passed.','- Screenshot references in all edited pages match their original references, in the original order.','- Application code was read, not changed. No application test suite or live browser task was run. Screenshot pixels and e-mail rendering in a real mail client were not verified. No server or background service was started.','',
'## Steering applied','',
'- Read the 04:37 steering before subsequent units. Re-read `ObjectDeleteDialog.tsx` immediately before revising each deletion page: the delivered guide describes one read of the impact and one confirmation, including failed reads and a changed impact.','- Home’s Waiting for your approval and Your change sets are described above workspace cards.','- File dropping is mentioned on pages that already describe the shared file chooser.','- The list-header pin is described on the list page and linked to the workspace shelf.','',
'## Code and changelog differences','',
'- `frontend/src/features/objects/ObjectFormDialog.tsx` still submits a whole-record edit with **Save changes**. It was retained in `guide/use/correct-a-record.md`, despite the general Save wording in the wave/changelog. The title is the record’s name.','- `frontend/src/features/workspaces/WorkspacePage.tsx` renders **Find a record** above the shelf, rather than beneath it as the UX1 changelog says. The guide does not prescribe the changelog’s order. Shelf counts come from live counts of the source record type, including when the tile is a matrix or another view; they are not filtered-view or cell counts.','- `frontend/src/features/security/PeoplePage.tsx` asks when switching Keeps local sign-in off, even if local sign-in is currently enabled. It saves immediately when switching it on. The guide follows that behavior rather than limiting the confirmation to a case where a password route is removed.','- `frontend/src/features/workspaces/Publications.tsx` still uses **Change set name** and **Create change set** for starting from a publication. Those labels were retained on the publication page; the live-data form instead uses Name and Start change set.','- `frontend/src/features/objects/RelationMatrixCellDialog.tsx` still offers **Create ‹type›** to enter creation, then submits with **Add ‹type›**. Only the obsolete form-submission instruction was corrected.','- Model operations keep **Apply** for short multi-selection popovers, including a new field group and navigation-group entry selection. They are not uniformly Save or Add; `surfaceOf` and `submitLabel` in `frontend/src/features/model-editor/operations.ts` determine the label.','',
'## Uncertainties and things that looked wrong','',
'- `guide/model/add-a-relation-matrix.md` already described a dedicated Add a relation matrix entry. The inspected model-editor operation catalogue exposes addition through **Add a view…**, selecting the matrix kind; The dedicated entry was absent from the inspected catalogue. The guide now names Add a view and the exact relation-matrix kind, as well as the corrected submission labels.','- Name/attribute Undo handlers in `InlineAttributeEditor.tsx` and the Yes/No handler in `EditableField.tsx` swallow a failed Undo request. A concurrent change can therefore prevent Undo without a failure notice. Documentation does not promise that Undo can overwrite a newer save.','- Template changes are not written to the security audit, as the MT1 changelog also records. The Mail section says this. Real mail-client rendering remains unverified.','- The pages were checked against local code. No claim of live application or release acceptance is made.','',
'## Screenshots showing affected, older controls','',
'The following existing files need recapture or review against the changed controls and layout. Their references and files were left untouched. This list is based on the documented captures and changed execution paths, not a pixel inspection. Other screenshots may also show an older frame.','',
'| Existing filenames | What the replacement must show |','| --- | --- |',
'| `use-appearance-themes.png` | Five themes with Current selected; Light or dark as a separate choice. |',
'| `use-home.png`, `home.png`, `use-home-continue.png`, `appr-home-waiting.png` | Home search, waiting approvals and own change sets above workspace cards. |',
'| `stop-details.png`, `stop-relationships.png`, `stop-edit-field.png`, `save-conflict.png`, `relationships-stop.png` | Current record layout and in-place editor, Yes/No switch, small-panel menu, save or refusal state. |',
'| `new-record-required-connections.png`, `stop-edit-record.png`, `stop-add-translation.png`, `matrix-missing-name-add.png` | Side sheet, correct title/action, supplied parent with Change, required-first fields and More fields. |',
'| `relationship-picker-mode.png`, `relationship-picker-operator.png` | Related-type lookup label, relationship wording, Add/Set/Change controls in a sheet. |',
'| `relationship-delete-confirm.png` | The old confirmation no longer exists: capture the remaining records and the removal notice with Undo instead. Keep the existing filename when refreshing it. |',
'| `record-delete-impact.png` | One confirmation after the impact read, dependant names/counts and Delete N records. No initial delete followed by Confirm deletion. |',
'| `mapping-grid-map-dialog.png` | Save, Cancel and Remove mapping inside the form, with the current source and chosen target. |',
'| `change-sets-list.png`, `change-set-open.png`, `change-set-publish-confirm.png` | New change set; Review changes and Publish; Validate now under the menu; the new plain publication summary confirmation. |',
'| `use-history-changes.png` | A grouped model-draft line, collapsed and expandable, with the step count. |',
'| `admin-role-new.png`, `admin-client-new.png`, `admin-group-new.png`, `admin-webhook-new.png`, `admin-webhook-workspace-events.png`, `admin-signin-provider-new.png`, `workspaces-new-dialog.png` | New-thing sheet and the corresponding Add button. |',
'| `admin-agent-new-client.png`, `admin-agent-register.png` | Add agent client, and New assistant with Add assistant. |',
'| `admin-client-rotate.png`, `admin-client-inactive-rotate.png`, `admin-webhook-rotate.png` | Rotation sheet with Rotate secret or Rotate key and the overlap choices. |',
'| `admin-grant-dialog.png`, `admin-grant-consumer-api.png`, `admin-grant-narrowed.png` | Add grant or Add N grants, with the intended roles, scope and restrictions. |',
'| `admin-client.png`, `admin-group-members.png`, `use-workspaces-detail.png`, `use-account.png` | Name/description edited where it stands and the saved change’s Undo notice, rather than Rename forms. |',
'| `model-hierarchy-dialog.png`, `model-field-dialog.png`, `model-relation-dialog.png`, `model-add-tree-view.png`, `model-add-mapping-grid.png`, `model-add-relationships-table-layout.png`, `model-view-matrix-dialog.png`, `model-add-panel-relationship.png`, `model-consumer-add-dialog.png`, `model-consumer-relationship-field-picker.png`, `model-consumer-add-field.png`, `model-consumer-add-filter.png`, `model-type-split-dialog.png`, `model-attribute-list-type-dialog.png` | Current sheet placement and the operation’s Add/Save action. |',
'| `model-type-rename-dialog.png`, `model-type-change-key-dialog.png`, `model-type-merge-dialog.png`, `model-layout-sort-dialog.png`, `model-table-columns-related-fields.png`, `model-table-menu-size.png`, `model-panel-columns-where-it-sits.png`, `model-group-add-entries-dialog.png` | Short operation beneath its triggering control; Save or Apply as appropriate. |',
'| `model-header-breadcrumbs.png`, `model-panel-settings.png` | Save for the longer settings sheet. |',
'| `use-wb-dialog.png`, `model-draft-new-dialog.png`, `use-assistant-workbook.png` | Current side-sheet file field, including its drop affordance and the original task controls. |','',
'### Additional captures needed','',
'No new image reference was inserted. Capture these states from the reference instance when screenshots are refreshed:','',
'- Workspace page: an empty shelf with Add a list, then a shelf containing a list and another view; tile menu with Move earlier, Move later and Take off your shelf; search, Applications, Needs you and What changed visible.','- Studio and Instrument, light and dark: application navigation, search, lists and the Live/change-set/publication context in their actual locations. Include a phone frame.','- Home: search results from two browseable workspaces, grouped by workspace; current waiting-work order.','- Record inspector: the list still visible and Expand to full page available.','- Record edit: one Yes/No switch and a saved-value Undo notice; separately a removal Undo notice.','- New change set: name-only form and expanded Options.','- Import: chosen file and automatically selected fitting profile, with Options folded and expanded.','- E-mail template: Markdown with the allowed placeholders, uploaded logo, Light paper/Dark paper/Plain text preview choices, Save and Send a test to me. Include an invalid placeholder warning and the saved-template test notice.','',
'## Per-page sentence changes','',
'Each changed passage below quotes the exact old and delivered text. An addition has no old passage; a removal has no new passage. Unchanged pages are explicitly listed afterwards. The guide’s existing screenshot captions were generally retained because they describe the captured state; outdated interfaces are listed above.','']
for path,(before,after) in changed.items():
    name=str(Path(path).relative_to(root))
    out += [f'### {name}','']
    a=before.split('\n\n'); b=after.split('\n\n')
    for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if tag=='equal':continue
        if i<j:
            out += ['Old:','', '```markdown','\n\n'.join(a[i:j]),'```','']
        else:out += ['Old: none (added passage).','']
        if k<l:
            out += ['New:','', '```markdown','\n\n'.join(b[k:l]),'```','']
        else:out += ['New: removed.','']
out += ['## Pages with no change','']
for path in old:
    if path not in changed:out.append(f'- `{Path(path).relative_to(root)}` — no change.')
Path('guide/_coverage/notes/UX1-GUIDE/report.md').write_text('\n'.join(out)+'\n')
print(f'Report saved: {len(changed)} changed, {len(old)-len(changed)} unchanged; screenshot references unchanged.')
