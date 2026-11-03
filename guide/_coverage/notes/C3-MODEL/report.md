# C3-MODEL delivery report

## Pages

41 pages added and seven existing pages expanded or reorganised (48 written pages total). The section now contains 57 pages; all 57 are listed in its sidebar, with no duplicate, missing or unlisted entries. Existing useful pages were retained. Only permitted files were edited; no commits or state-changing git commands were used.

- `guide/src/content/docs/guide/model/add-a-relation-matrix.md`
- `guide/src/content/docs/guide/model/arrange-applications-and-views.md`
- `guide/src/content/docs/guide/model/change-a-workspaces-model.md`
- `guide/src/content/docs/guide/model/check-a-workbook-with-a-dry-run.md`
- `guide/src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`
- `guide/src/content/docs/guide/model/choose-what-moves.md`
- `guide/src/content/docs/guide/model/compare-releases.md`
- `guide/src/content/docs/guide/model/create-a-workspace.md`
- `guide/src/content/docs/guide/model/define-a-consumer-api.md`
- `guide/src/content/docs/guide/model/delete-a-draft.md`
- `guide/src/content/docs/guide/model/edit-a-draft-as-json.md`
- `guide/src/content/docs/guide/model/edit-a-mapping-row.md`
- `guide/src/content/docs/guide/model/edit-a-record-page.md`
- `guide/src/content/docs/guide/model/edit-a-workspaces-model.md`
- `guide/src/content/docs/guide/model/export-a-release.md`
- `guide/src/content/docs/guide/model/find-your-way-around-the-editor.md`
- `guide/src/content/docs/guide/model/group-collections-in-navigation.md`
- `guide/src/content/docs/guide/model/make-a-workspace-the-default.md`
- `guide/src/content/docs/guide/model/map-a-column.md`
- `guide/src/content/docs/guide/model/migrate-a-workspace.md`
- `guide/src/content/docs/guide/model/preview-a-type.md`
- `guide/src/content/docs/guide/model/propose-again-with-a-newer-workbook.md`
- `guide/src/content/docs/guide/model/raise-a-contract-version.md`
- `guide/src/content/docs/guide/model/raise-a-model-language-version.md`
- `guide/src/content/docs/guide/model/read-lists-in-a-sheet.md`
- `guide/src/content/docs/guide/model/remove-an-element.md`
- `guide/src/content/docs/guide/model/rename-or-re-key-an-element.md`
- `guide/src/content/docs/guide/model/retire-or-delete-a-release.md`
- `guide/src/content/docs/guide/model/retire-or-delete-a-workspace.md`
- `guide/src/content/docs/guide/model/reuse-and-change-attributes.md`
- `guide/src/content/docs/guide/model/see-a-consumer-apis-documents.md`
- `guide/src/content/docs/guide/model/split-merge-and-move-types.md`
- `guide/src/content/docs/guide/model/turn-an-attribute-into-a-list.md`
- `guide/src/content/docs/guide/model/undo-and-review-the-draft-history.md`
- `guide/src/content/docs/guide/model/work-on-a-draft-with-others.md`
- `guide/src/content/docs/model/applications-and-views.md`
- `guide/src/content/docs/model/consumer-apis.md`
- `guide/src/content/docs/model/json-view.md`
- `guide/src/content/docs/model/managing-workspaces.md`
- `guide/src/content/docs/model/migrations.md`
- `guide/src/content/docs/model/model-language-versions.md`
- `guide/src/content/docs/model/model-mappings.md`
- `guide/src/content/docs/model/models.md`
- `guide/src/content/docs/model/record-pages-and-tables.md`
- `guide/src/content/docs/model/releases.md`
- `guide/src/content/docs/model/the-model-editor.md`
- `guide/src/content/docs/model/types-attributes-relations.md`
- `guide/src/content/docs/model/workbook-onboarding.md`

## Coverage

819 rows reviewed by topic and reconciled: 763 ordinary rows linked to reader coverage, 18 pre-existing non-reader exclusions retained, 38 AI/deferred rows preserved verbatim under COMPLETE-COMMON. No ordinary row remains partly covered or uncovered. Schema-member rows link to their browser meaning and the specialist document-view limits; they do not claim an individual browser form for every member. Out-of-section record, account and approval fragments link to existing Use pages. The exact per-row decisions, former text and source leads are in coverage-decisions.json.

All preserved AI/deferred IDs: C1650, C1680, C1698, C1699, C1718, C1744, C1760, C1781, C1782, C1783, C1784, C1789, C1794, C1806, C1808, C1834, C1839, C1847, C1848, C1853, C1854, C1855, C1871, C1872, C1874, C1875, C1889, C1892, C1895, C1943, C1950, C1953, C2140, C2167, C2168, C2179, C2180, C2181.

Among these, the following retain the original partly/uncovered wording because their AI content is deferred and the instructions say to leave their rows as they are: C1650, C1698, C1699, C1781, C1782, C1789, C1871, C1872, C1874, C1950, C2168.

## Screenshots

Seven captures requested in `guide/_waves/screens-wanted/C3-MODEL.md`, with page, state and required visible content for each:

- `model-workbook-map-column.png`: Map to form, source and destination with mapping and matching choices.
- `model-workbook-value-map.png`: source-text to loaded-value replacements and remove/confirmation controls.
- `model-workbook-list-range.png`: selected detected list, shaded header/range, Under/Cells/Note/Loads and list actions.
- `model-migration-review.png`: finished preview, destination, unchanged-data notice, missing-element choices, four outcomes and item rows.
- `model-migration-loss-confirm.png`: removed items, explicit acceptance and exact destination/action before execution.
- `model-migration-stale.png`: intervening-change refusal, nothing migrated, Close and Preview again.
- `model-language-raise-review.png`: historical-language preview, rewritten contracts, every affected workspace and unchanged data, before confirmation.

Reused existing screenshots. Visually inspected model-consumer-tab-fields.png, model-view-matrix-dialog.png and model-workspace-apply-dialog.png against their corresponding descriptions. The remaining existing captures were selected by their existing page context, inventory and source labels, not a fresh visual pass.

## Checks

`GUIDE_OUT=_build/C3-MODEL npm run verify` in guide:

- Build passed after the final content edit: 182 built pages, 2.37 seconds.
- Terms and branding passed: 181 content pages at that snapshot.
- Link check failed: 40 findings, of which eight references are this wave's seven deliberately requested missing screenshots, and 32 are elsewhere in concurrent sections. No broken page link originates in Model. Counts are a snapshot of parallel writing, not a frozen whole-site result.
- The output is isolated at guide/_build/C3-MODEL. Logs are under this notes directory.
- Read-only sidebar inspection: 57 entries, no missing pages, unlisted pages or duplicates.
- `git diff --check` for the permitted paths reported no whitespace problems. Most guide content is untracked in this workspace; this check is supplemented by the actual site build and link check rather than treated as a complete content audit.

No application tests, servers, database changes or screenshot capture jobs were run. Browser tasks are documented from current source and product journeys; they are not newly exercised runtime evidence.

## Uncertainty and product findings

- The seven requested states still need real reference-data captures; historical-language and migration examples need isolated fixtures. No fabricated image or data change was used to satisfy link checking.
- No new live browser validation was performed. Permissions and failure labels were checked in source, including useEditModel, the model workbench, migration page, workspace repair and consumer editor.
- A source-visible UI inconsistency: ConsumerApis.tsx shows “Key fixed: released” for a released consumer API. Its Change key menu is nevertheless available, operations.ts warns that the old access point stops working, and authoring/consumer.py permits a distinct unused replacement key. Documentation describes the offered action and warns about the changed access point; the badge inconsistency was not repaired because code is outside this wave.
- Existing product prose has older wording in places (for example the model card layout); current frontend tabs and controls take precedence in these pages.
