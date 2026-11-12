# SCREENS-CAPTIONS report

Placed 16 canvas pictures in two guides. Compared the 405 existing screenshot references with available screen definitions and checked the PNGs where captions or definitions were uncertain. Corrected 40 captions and 21 image descriptions across 35 existing pages. No image was renamed or removed.

## Canvas pictures placed

### guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md

| Picture | Caption |
| --- | --- |
| `canvas-workbook-open.png` | Above: The Busbetrieb Nord workbook draft after Adjust. Workbook check shows 85 rows to load and 9 refused; the proposed cards have not created a workspace. |
| `canvas-workbook-connect.png` | Above: Haltestellen is related to Namen. The notice says no workbook column was found to fill the link; Undo is available. |
| `canvas-workbook-columns-as-rows.png` | Above: Perron A, Perron B and Perron C are selected. Read 3 columns as rows into asks which object type or attribute to fill. |
| `canvas-workbook-readings.png` | Above: The Perron A menu offers Fill blanks from the cell above, Rows holding only this column are headings…, Make an object type of its values and Leave out. |
| `canvas-workbook-navigation.png` | Above: Navigation shows the proposed Haltestellen lists group, entries Not in a group and a New group destination. |
| `canvas-workbook-refused.png` | Above: Namen has 9 refused rows because no record matches the reference. See the rows opens their details. |
| `canvas-workbook-create-dialog.png` | Above: Create workspace proposes Busbetrieb Nord canvas as the name and reports 85 rows to load and 9 refused rows that stay out. Creation has not been confirmed. |

### guide/src/content/docs/guide/model/edit-a-model-on-the-canvas.md

| Picture | Caption |
| --- | --- |
| `canvas-model-whole.png` | Above: Whole model is selected in Guide canvas draft. Network and Systems frame their object types; visible cards are marked Released, and Fit is at the lower right. |
| `canvas-model-add-menu.png` | Above: The header’s + menu offers Application…, Object type…, Attribute type…, Relation type… and Navigation group…. |
| `canvas-model-attribute.png` | Above: FSO number on Canton is a Whole number. Required is off and Unique is on; the inspector also offers Move to… and further operations. |
| `canvas-model-relation-rule.png` | Above: Canton contains District is selected. Its popover explains the parent and child types and offers Which records may be chosen and All operations. |
| `canvas-model-navigation.png` | Above: Network, Systems and Names each show collections Not in a group and a New group destination. |
| `canvas-model-views.png` | Above: Canton has a Geography tree in Network and no view in Names. Preview tables and record page and Edit layout are available. |
| `canvas-model-consumer.png` | Above: The Consumer APIs tab lists Stops API, version 1, marked Released, with a + control to add another contract. |
| `canvas-model-issues.png` | Above: The draft has one issue: a view refers to a field that does not exist. The link opens the affected Municipalities view in Network. |
| `canvas-model-history.png` | Above: History records one whole-model edit by Guide Admin and offers Undo for that step. |

## Each caption changed

### src/content/docs/administer/audit.md — admin-audit-person

- **Old:** Above: fictional Rita Approver's changes include a publication and the height correction it applied to Davos Platz in Graubünden.
- **New:** Above: Fictional Rita Approver’s changes are listed newest first, with Workspace, What and Period filters. The visible entries include record edits, a model draft change and a publication.

### src/content/docs/administer/clients.md — admin-client

- **Old:** Above: Stops reader (guide) has a Consumer API grant in Graubünden. The webhooks section shows a load error on this capture; it does not show that the client has no webhooks.
- **New:** Above: Stops reader (guide) has a Stops API grant in Graubünden. Webhooks it created says it created no webhook you administer.

### src/content/docs/administer/sign-in.md — admin-signin

- **Old:** Above: local accounts are on and no organisation provider is configured in the reference instance.
- **New:** Above: Local accounts is on. Guide identity provider is listed but Disabled in the reference instance.

### src/content/docs/administer/signing-keys.md — admin-signing-keys

- **Old:** Above: the reference instance has a new Signing key and a previous key verifying until its displayed deadline. The identifiers distinguish keys; they are not values to copy into a system.
- **New:** Above: The reference instance has one key, marked Signing. Start a new key and Retire the current key now are available.

### src/content/docs/guide/administer/create-a-client.md — admin-client

- **Old:** Above: Stops reader (guide) can read the Stops API in Graubünden. The failed webhooks section below is a load error, not an empty-list confirmation.
- **New:** Above: Stops reader (guide) can read Stops API in Graubünden. Webhooks it created says it created no webhook you administer.

### src/content/docs/guide/administer/find-who-changed-something.md — admin-audit-person

- **Old:** Above: fictional Rita Approver's page shows her publication and the Davos Platz height change applied by it in Graubünden. These are related entries, not proof of two separate manual edits.
- **New:** Above: Fictional Rita Approver’s page lists her changes across the workspaces you can read. The visible entries include record edits, a model draft change and a publication; each entry identifies its workspace.

### src/content/docs/guide/administer/find-who-changed-something.md — admin-grants-person

- **Old:** Above: Guide Admin's security activity follows their roles and groups. A one-time password link creation appears as an event without revealing the link itself.
- **New:** Above: Guide Admin's Recent activity follows their roles and groups. The visible entries include group changes and a sign-in.

### src/content/docs/guide/administer/rotate-signing-keys.md — admin-signing-keys

- **Old:** Above: the reference instance shows a new Signing key and a previous key still verifying.
- **New:** Above: The reference instance has one current key, marked Signing.

### src/content/docs/guide/model/create-a-model-draft.md — model-workspace-edit-model

- **Old:** Above: Guide draft applies to Graubünden and offers Apply to this workspace….
- **New:** Above: The workspace draft applies to Graubünden and offers Apply to this workspace….

### src/content/docs/guide/model/install-and-activate-a-release.md — model-install-dialog

- **Old:** Above: Guide draft proposes release 1.0.1 for Graubünden, adding Step-free access and Inspected by. The captured dialog was cancelled: neither installation nor activation happened.
- **New:** Above: Guide draft proposes release 1.8.4 for Graubünden, adding Step-free access and Inspected by. The dialog shows compatible stored data and Stops API; installation has not been confirmed.

### src/content/docs/guide/model/install-and-activate-a-release.md — model-workspace-apply-dialog

- **Old:** Above: applying Guide draft to Graubünden leaves Default unchanged and names December 2026 timetable change as remaining on release 1.0.0. The dialog was cancelled.
- **New:** Above: The Apply to Graubünden review shows a consumer API change that needs version 2. Activation is refused until the contract version is raised; open change sets remain on release 1.8.1.

### src/content/docs/guide/model/install-and-activate-a-release.md — model-release-detail

- **Old:** Above: release 1.0.0 of the Graubünden model is immutable and already run by Graubünden.
- **New:** Above: Release 1.8.1 of the Graubünden model is immutable and run by Graubünden. Its open menu offers Export JSON.

### src/content/docs/guide/model/install-and-activate-a-release.md — model-release-activate-dialog

- **Old:** Above: the selected target is Default, which runs RDM Starter Model; Graubünden stays unchanged. The captured activation was cancelled.
- **New:** Above: an example workspace is selected for activation of release 1.8.1. Its data is compatible and it has no open change set; activation has not been confirmed.

### src/content/docs/guide/model/load-a-workbook-into-a-change-set.md — wbload-dialog

- **Old:** Above: the fictional operator workbook is about to install release 1.0.1, open a change set in Guide workbook test and load the rows. This is the destination chosen for this example.
- **New:** Above: The fictional operator workbook is ready to install release 1.8.3, open a change set in Guide workbook test and load the rows. This is the destination chosen for this example.

### src/content/docs/guide/model/review-an-assistants-workbook-design.md — model-assistant-workbook-proposal

- **Old:** Above: the reference workbook proposal adds types and relationships, adds Step-free access and Remark to Stop, and makes FSO number and System key optional. The expanded table shows these changes.
- **New:** Above: The reference workbook proposal adds Line, Platform, Tariff network and Tariff zone types and their relationships. It adds Barrier-free and Remark to Stop and makes Municipality’s FSO number optional; the expanded table shows these changes.

### src/content/docs/guide/model/undo-and-review-the-draft-history.md — model-history

- **Old:** Above: moving Stop code to the top level of Systems is marked Needs a migration, with 12 records, 36 values and 12 relationships holding the type. Undo is available.
- **New:** Above: Guide draft records adding Step-free access and allowing Inspected by as two saved steps. Each step offers Undo.

### src/content/docs/guide/use/approve-a-change-set.md — appr-submitted

- **Old:** Above: Guide Admin's Guide approval example waits in Graubünden. Its submitted version is 2; the proposed height correction is still separate from Live.
- **New:** Above: Guide approval example waits for approval in Graubünden. The banner offers Review and decide and Withdraw request; its one proposed change is still separate from Live.

### src/content/docs/guide/use/approve-a-change-set.md — appr-home-waiting

- **Old:** Above: fictional approver Rita Approver has Data owner access in Graubünden. Guide Admin's request appears below her workspace card.
- **New:** Above: Fictional approver Rita Approver has Data owner access in Graubünden. Guide Admin’s request appears under Waiting for your approval, above her workspace card.

### src/content/docs/guide/use/correct-a-record.md — stop-edit-record

- **Old:** Above: Edit object for Chur Wiesental shows Chur as the selected Parent, followed by Name, Designation, Stop number (UIC) and the other stop fields. The remaining fields and save control are further down the form.
- **New:** Above: Chur Wiesental’s edit form shows In Chur with Change, followed by required Name, Designation and Stop number (UIC). More fields is open, and Cancel and Save are visible at the foot.

### src/content/docs/guide/use/find-records.md — stop-details

- **Old:** Above: Chur Wiesental in Network has its fields under Stop details. Modes shows Train and Operator shows Rhätische Bahn. Its path places the stop under Chur.
- **New:** Above: Chur Wiesental is open beside the Stops list in Network. Stop details shows its fields, and Hierarchy places it under Chur; Expand to full page opens the full record.

### src/content/docs/guide/use/map-codes-between-systems.md — mapping-grid-map-dialog

- **Old:** Above: T-9999, the fictional special day pass, is deliberately unmapped. The dialog shows Not mapped and offers stop candidates and Create new stop. It was cancelled; the screenshot does not suggest that this pass needs a stop mapping.
- **New:** Above: The fictional code T-0412 is currently mapped to Chur Wiesental. Change mapping offers a stop search, Create new stop and Remove mapping; no replacement has been selected.

### src/content/docs/guide/use/prepare-and-publish-a-change-set.md — change-sets-list

- **Old:** Above: Network in the Graubünden workspace lists December 2026 timetable change. Open change set continues that work; Start from current live data begins a separate proposal.
- **New:** Above: Network in the Graubünden workspace lists December 2026 timetable change. Open change set continues that work; New change set starts a separate proposal.

### src/content/docs/guide/use/prepare-and-publish-a-change-set.md — change-set-open

- **Old:** Above: December 2026 timetable change is open over Stops in Network. The orange banner offers Review changes, Validate change set and Publish change set. The example proposal changes Valid to (exclusive) on several stops: the first date on which each stop is no longer valid.
- **New:** Above: December 2026 timetable change is open over Stops in Network. The orange banner shows 11 changes and offers Details, Review changes, Publish and a menu for further actions.

### src/content/docs/guide/use/relate-records.md — relationship-picker-mode

- **Old:** Above: Add relationship in Chur Wiesental's Modes panel offers Served by mode (outgoing) and candidate modes such as Boat and Bus. Nothing is selected; this dialog was cancelled.
- **New:** Above: Add Mode for Chur Wiesental names Served by mode and offers candidates such as Boat and Bus. Nothing is selected, so Add Mode is unavailable.

### src/content/docs/guide/use/relate-records.md — relationship-delete-confirm

- **Old:** Above: deleting Chur Wiesental's Served by mode connection would leave both the stop and Train. The confirmation was cancelled, so the connection remains.
- **New:** Above: Chur Wiesental’s Modes panel is empty after the Train connection was removed. The removal notice offers Undo; the connection was restored after this picture.

### src/content/docs/journeys/shape-a-model.md — model-account-facts

- **Old:** Above: the Apply dialog for a change to the Graubünden reference model. The account cites the facts below it.
- **New:** Above: The activation review compares RDM Starter Model with Graubünden’s current model. The account cites the facts below it; activation needs a migration.

### src/content/docs/model/releases.md — model-releases

- **Old:** Above: the Graubünden model has one installed release, 1.0.0, used by Graubünden.
- **New:** Above: The Graubünden model lists its installed releases, newest first. Graubünden runs 1.8.1; Guide workbook test runs 1.8.3.

### src/content/docs/model/releases.md — model-drafts

- **Old:** Above: Guide draft and another draft both start from the Graubünden model's release 1.0.0.
- **New:** Above: The drafts list shows each base release and how many releases it is behind. Guide draft starts from 1.8.1.

### src/content/docs/model/releases.md — model-workspace-model

- **Old:** Above: Graubünden runs Public transport stops of Graubünden 1.0.0 and offers Edit model.
- **New:** Above: Graubünden runs Public transport stops of Graubünden 1.8.1 and offers Edit model.

### src/content/docs/model/the-model-editor.md — model-type-preview

- **Old:** Above: Stop's draft layout is shown over a live Graubünden record. Step-free access is still a draft addition, with no live value.
- **New:** Above: Stop’s draft layout is shown over the live Graubünden record 38 Extern Mountain Tour, Berg. The preview’s record controls are disabled; it writes nothing.

### src/content/docs/model/workbook-onboarding.md — wbload-dialog

- **Old:** Above: the fictional operator workbook is ready to load into Guide workbook test. The draft changes the model, so the dialog proposes release 1.0.1 and offers Install, activate and load.
- **New:** Above: The fictional operator workbook is ready to load into Guide workbook test. The draft changes the model, so the dialog proposes release 1.8.3 and offers Install, activate and load.

### src/content/docs/run/configure.md — run-deployment

- **Old:** Above: Deployment in the reference instance used for this guide. Its values describe that installation; its older container paths differ from the current image paths listed below.
- **New:** Above: Deployment shows the reference instance’s capability switches, limits, database revision and runtime settings. These values describe this installation; secrets are masked.

### src/content/docs/use/change-sets.md — change-set-open

- **Old:** Above: December 2026 timetable change is open over the Stops list. The orange banner identifies the proposed data and offers Review changes, Validate change set and Publish change set.
- **New:** Above: December 2026 timetable change is open over the Stops list. The orange banner identifies the proposed data and offers Details, Review changes, Publish and a menu for further actions.

### src/content/docs/use/home.md — use-home

- **Old:** Above: Guide Admin can browse two workspaces. Graubünden has an open change set; Default has none.
- **New:** Above: Guide Admin’s Home shows 21 available workspaces, ten open change sets and a request waiting for approval. Your change sets lists work to continue; Your workspaces starts below it.

### src/content/docs/use/inbox-and-approvals.md — use-inbox-panel

- **Old:** Above: Guide Admin has eight unread Batch finished notices from jobs they started.
- **New:** Above: Guide Admin’s inbox includes unread workbook, mapping-proposal, move and batch notices. Mark all read is at the top.

### src/content/docs/use/inbox-and-approvals.md — use-notifications-page

- **Old:** Above: the reference account's notices are job results. One has been read; the others are highlighted.
- **New:** Above: The reference account’s notices include workbook results, mapping proposals, migrations, batches and moves. Unread notices are highlighted; read notices have a plain background.

### src/content/docs/use/inbox-and-approvals.md — appr-submitted

- **Old:** Above: Guide Admin submitted Guide approval example in Graubünden. Version 2 proposes a height correction to Davos Platz; this earlier view keeps the submission comment in the banner. In the current frame, read the comment in the review’s **Decision** panel.
- **New:** Above: Guide approval example waits for approval in Graubünden. The banner offers Review and decide and Withdraw request; open the review to read the submission details.

### src/content/docs/use/inbox-and-approvals.md — appr-sent-back

- **Old:** Above: Rita asks Guide Admin to name the source of the new height. Review changes, Validate change set and Submit for publication are available again; the correction has not reached Live.
- **New:** Above: Rita asks Guide Admin to name the source of the new height. Review changes and Submit for publication are available again; the correction has not reached Live.

### src/content/docs/use/records.md — stop-details

- **Old:** Above: Chur Wiesental is a Stop in the Network application of the Graubünden workspace. Stop details holds its number, abbreviation and other fields; Modes and Operator show connected records. This earlier view shows the ID and version directly in the heading; open **Details** in the current header to see them.
- **New:** Above: Chur Wiesental is open beside the Stops list in Network. Stop details holds its number, abbreviation and other fields, and Hierarchy shows its parent. Details and Expand to full page are in the record header.

### src/content/docs/use/workspaces.md — use-home

- **Old:** Above: Graubünden is marked Default. The workspace named Default runs a different model.
- **New:** Above: Guide Admin’s Home shows work waiting for approval and open change sets above the workspace cards. Graubünden is among the available workspaces.

## Image descriptions corrected

| Page | Picture | Old | New |
| --- | --- | --- | --- |
| src/content/docs/administer/clients.md | admin-clients | Clients catalogue with one active client and no selection | Clients catalogue with two active clients and Active and Deactivated filters |
| src/content/docs/administer/sign-in.md | admin-signin | Sign-in catalogue with Local accounts on and no providers | Sign-in catalogue with Local accounts on and a disabled provider |
| src/content/docs/administer/signing-keys.md | admin-signing-keys | Signing keys with a current Signing key and a replaced key still verifying | Signing keys with one current Signing key and rotation and retirement actions |
| src/content/docs/administer/webhooks.md | admin-webhook-deliveries | Retrying webhook delivery with its attempts and receiver response | Dropped webhook delivery with two attempts and a 503 receiver response |
| src/content/docs/guide/administer/rotate-signing-keys.md | admin-signing-keys | Signing keys list with current and replaced key states | Signing keys list with one current key marked Signing |
| src/content/docs/guide/model/add-a-record-type-and-fields.md | model-type-required-edit | Required setting opened in place with Save and Cancel | Required setting opened in place as a Yes or No choice |
| src/content/docs/guide/model/edit-a-workspaces-model.md | model-workspace-edit-model | Workspace overview with Edit model | Workspace model draft with Applies to Graubünden and Apply to this workspace |
| src/content/docs/guide/model/make-a-workspace-the-default.md | use-workspace-default | Workspace management showing the Default mark | The workspace named Default open on RDM Master with an empty Domains collection |
| src/content/docs/guide/model/undo-and-review-the-draft-history.md | model-history | History showing an applied move, its Needs a migration mark and affected data counts | History showing two saved model changes and their Undo actions |
| src/content/docs/guide/use/approve-a-change-set.md | appr-submitted | Submitted change set showing Waiting for approval, version, comment and Withdraw request | Submitted change set awaiting approval with review and withdrawal controls |
| src/content/docs/guide/use/change-how-refiroo-looks.md | use-appearance-themes | Appearance showing its two colour themes separately from light or dark mode | Appearance showing five themes separately from light or dark mode |
| src/content/docs/guide/use/correct-a-record.md | stop-edit-field | One numeric field open for correction with Cancel and Save | One numeric field open for correction in place with Enter to save and Escape to cancel |
| src/content/docs/guide/use/correct-a-record.md | stop-edit-record | The record editing form showing Parent, Name and other fields | Record editing dialog with its parent, required fields, expanded More fields and Save |
| src/content/docs/guide/use/fill-in-a-relation-matrix.md | matrix-cell-editor | An existing cell record open for editing with a content field and Active checkbox | An existing cell record in a centred dialog with Translated name and an Active switch |
| src/content/docs/guide/use/find-records.md | stop-details | A record page with its fields, hierarchy path and relationship sections | A record opened beside its collection with its fields and hierarchy path |
| src/content/docs/guide/use/map-codes-between-systems.md | mapping-grid-map-dialog | A mapping dialog for an unmapped row with target radio choices and a creation action | Change mapping dialog for a mapped code with its current stop and candidate choices |
| src/content/docs/guide/use/relate-records.md | relationship-picker-mode | The Connect an object dialog with a relationship choice and candidate search | The Add Mode dialog with the relationship name, candidate search and Add Mode action |
| src/content/docs/guide/use/relate-records.md | relationship-delete-confirm | The Delete relationship confirmation explaining that both records remain | An empty Modes panel after a relationship removal with Undo in the notice |
| src/content/docs/use/appearance-and-devices.md | use-appearance-themes | Appearance settings with Normal and Website purple themes, light or dark mode, density and edit hints | Appearance settings with five themes, light or dark mode, density and edit hints |
| src/content/docs/use/inbox-and-approvals.md | appr-submitted | Submitted change set with Waiting for approval, its comment and review and withdrawal controls | Submitted change set awaiting approval with review and withdrawal controls |
| src/content/docs/use/records.md | stop-details | A record page with a heading, hierarchy path, fields and relationship tables | A record opened beside its collection with a heading, fields and hierarchy path |

## Checks

- `GUIDE_OUT=_build/SCREENS-CAPTIONS npm run build` in `guide/`: passed, 259 pages.
- `GUIDE_OUT=_build/SCREENS-CAPTIONS npm run verify` in `guide/`: passed. This includes build, terms, brand, sidebar, inventory, coverage and local links. Coverage: 1,112 covered, 14 excluded, zero uncovered. Links: 77,212 checked across 259 built pages.
- The first verification found a delivery identifier in a screenshot workspace name copied into a caption. Rephrased it as “an example workspace”; the final verification passes.
- All 405 original screenshot references remain. The 16 added references match the canvas assignment. All referenced screenshot files exist.
- No live application changes or browser journeys were run; this was a documentation and existing-image review.

## Uncertainties and discrepancies

No additional screenshots are needed for this assignment. No application defect was established by this review. The definitions are not always an exact description of the PNG; captions use the visible image:

- `canvas-workbook-refused`: the PNG shows nine refused rows, their reason and See the rows; no unmatched-value list or correction action is visible.
- `canvas-model-relation-rule`: the selected line is containment, with candidate and operation controls; it does not show the ordinary relationship cardinality controls named in the definition.
- `canvas-model-consumer`: the PNG shows the contract list, rather than an opened contract panel.
- Several release versions, audit entries, Home counts and dialog layouts differ from the definitions. The corrected captions use the PNGs.
- The publication PNGs still show Publication 1 and Publication 2, including Withdrawn on the older row in the approval example; those captions were retained.

43 existing screenshot names have no `shows` definition in `guide/_waves/*.screens.json`. For those with specific captions, the PNGs were checked directly; no new definition files were created because they are outside the assignment. Names:

- `list-phone` — src/content/docs/about/accessibility.md
- `jobs-list` — src/content/docs/administer/jobs-and-limits.md
- `model-table-columns-related-fields` — src/content/docs/guide/model/choose-table-columns-filters-and-sort.md
- `model-layout-sort-dialog` — src/content/docs/guide/model/choose-table-columns-filters-and-sort.md
- `model-consumer-add-dialog` — src/content/docs/guide/model/define-a-consumer-api.md
- `model-consumer-add-field` — src/content/docs/guide/model/define-a-consumer-api.md
- `model-consumer-add-filter` — src/content/docs/guide/model/define-a-consumer-api.md
- `model-more-actions` — src/content/docs/guide/model/delete-a-draft.md
- `model-json-syntax-error` — src/content/docs/guide/model/edit-a-draft-as-json.md
- `model-json-workbench-actions` — src/content/docs/guide/model/edit-a-draft-as-json.md
- `model-add-panel-relationship` — src/content/docs/guide/model/edit-a-record-page.md
- `model-panel-columns-where-it-sits` — src/content/docs/guide/model/edit-a-record-page.md
- `model-layout-panel-menu` — src/content/docs/guide/model/edit-a-record-page.md
- `model-application-groups` — src/content/docs/guide/model/group-collections-in-navigation.md
- `model-group-add-entries-dialog` — src/content/docs/guide/model/group-collections-in-navigation.md
- `model-navigation-group-panel` — src/content/docs/guide/model/group-collections-in-navigation.md
- `model-group-menu` — src/content/docs/guide/model/group-collections-in-navigation.md
- `model-type-remove-confirm` — src/content/docs/guide/model/remove-an-element.md
- `model-type-rename-dialog` — src/content/docs/guide/model/rename-or-re-key-an-element.md
- `model-type-change-key-dialog` — src/content/docs/guide/model/rename-or-re-key-an-element.md
- `model-attribute-attach-existing` — src/content/docs/guide/model/reuse-and-change-attributes.md
- `model-attribute-menu` — src/content/docs/guide/model/reuse-and-change-attributes.md
- `model-consumer-tab-schema` — src/content/docs/guide/model/see-a-consumer-apis-documents.md
- `model-consumer-tab-example` — src/content/docs/guide/model/see-a-consumer-apis-documents.md
- `model-type-split-dialog` — src/content/docs/guide/model/split-merge-and-move-types.md
- `model-type-merge-dialog` — src/content/docs/guide/model/split-merge-and-move-types.md
- `model-type-move-to-dialog` — src/content/docs/guide/model/split-merge-and-move-types.md
- `model-attribute-list-type-dialog` — src/content/docs/guide/model/turn-an-attribute-into-a-list.md
- `model-history-undo-dependants` — src/content/docs/guide/model/undo-and-review-the-draft-history.md
- `model-conflict-editor` — src/content/docs/guide/model/work-on-a-draft-with-others.md
- `model-json-newer-version` — src/content/docs/guide/model/work-on-a-draft-with-others.md
- `record-delete-impact` — src/content/docs/guide/use/delete-a-record.md
- `model-application-panel` — src/content/docs/model/applications-and-views.md
- `model-matrix-view-dialog` — src/content/docs/model/applications-and-views.md
- `model-consumer-tab-fields` — src/content/docs/model/consumer-apis.md
- `model-consumer-tab-filters` — src/content/docs/model/consumer-apis.md
- `model-consumer-tab-types` — src/content/docs/model/consumer-apis.md
- `model-stop-page-relationship-panels` — src/content/docs/model/record-pages-and-tables.md
- `model-matrix-pair` — src/content/docs/model/types-attributes-relations.md
- `app-navigation-matrix-entry` — src/content/docs/use/applications.md
- `settings-notifications` — src/content/docs/use/inbox-and-approvals.md
- `list-filter-pills` — src/content/docs/use/lists-and-filters.md
- `workspace-actions-menu` — src/content/docs/use/workspaces.md

## Working record

Progress: `guide/_waves/progress/SCREENS-CAPTIONS.md`. Initial reference inventory: `audit.json`. Exact edit log: `changes.json`. Canvas placement list: `canvas-placements.json`. Build and final verification output: `build.log` and `verify.log`. No steering file was present at any unit boundary.
