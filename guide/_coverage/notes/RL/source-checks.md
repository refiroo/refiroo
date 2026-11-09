# RL source checks and completion

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/RL.md` first.
Top-level agent instructions do not govern this assignment. No earlier RL progress or steer
file existed; steer was checked before each page and the final verification unit.
Only the three assigned pages, RL screenshot requests, progress and these notes were edited.
Build products use the explicitly requested `_build/RL` destination. No git commands were used.

## Evidence by assignment statement

1. Confirmed in `frontend/src/model/defaults.ts` (`fallbackDetail`, `heldRelations`,
   `relationsPanelConfig`) and `backend/app/engine/model/authoring/layout.py` (`detail_page`,
   `relations_panel`). The generated parent column requires all target types to have the same
   single direct parent type; a self-type hierarchy is excluded. Parent-column initial sort
   applies only when exactly one related type is listed. Incoming panels require a reverse key.
   A contained panel listing several types takes the first type's plural title.
2. Confirmed in `layout.py:place_relation`, `kinds.py:disallow_relation` and `cascade.py`
   (`_drop_related_fields` and pruning relationship panels). Existing panels are retained if
   they already list the relationship in that direction. Removal prunes only unavailable
   relationships: another allowed pair at that end can keep a column/panel available.
   Existing page arrangements are not rebuilt to match the new rule.
3. Confirmed in `layout.ts:addPanelSpec`, `fieldGroupOperations`, `TypePreview.tsx` and
   `OperationDialog.tsx`. Related and contained titles follow the choice until edited;
   Fields starts with a blank title. Related records is absent if no held non-containment
   relationship exists. Contained records needs contained types listed in the application.
   Existing relationships are marked, not disabled. Apply and Not applied are exact labels.
4. Confirmed in `layout.ts:relatedFieldChoices`, `tableColumnsSpec`, `tableFiltersSpec`;
   `OperationDialog.tsx:CheckboxList`; `model/fields.ts:relatedText`, `attributeName` and
   `model/lookup.ts:relatedFieldLabel`. Related attributes and ancestor name/attributes are
   offered, non-JSON only. Their own column selections are independent of the names column.
   Sorting/filter restrictions agree with `docs/APPLICATION_MODEL.md`'s relation-column section.
5. Confirmed in `layout.ts:whereItSits`, `panelColumnsSpec`: ancestor names and Type for multiple
   listed types, under Where it sits. Ancestor attributes are table related-field choices,
   not panel-column choices.
6. Confirmed in `kinds.py:add_panel_kind` and `docs/API.md` draft operations. The operation
   accepts the stated fields and its inverse removes the panel; invalid relationship direction
   membership is unknownElement, invalid contained choices invalidValue, duplicate key keyTaken.
   API parameter names and codes are intentionally not included on these browser-reader pages.

No numbered statement is wholly unconfirmed. Qualifications to broad assignment wording are
listed above and reflected in the pages. `samples/` in the wave refers to `guide/samples/`:
read its README, SOURCES and model.json. Stop relationship names, System, Language, External code
and Language code are taken from this reference model. No private data or AI features were added.

Other sources: targeted RL delivered/plan section of `BASE_0_13_IMPLEMENTATION_PLAN.md`, the RL
Unreleased changelog entry, API's undeclared-page section, application-model panels and relation
columns, current functionality's preview/layout section and J33's layout and invalid-page variants.
The approved prototype is illustrative and was not used for facts or labels; delivered code wins.
No separate template file was found; existing guide/task and concept page kinds were retained.

## Coverage and remaining work

All six RL subject groups are covered by the assigned pages. This focused wave supplies no coverage
ledger rows of its own and does not authorize editing another wave's ledger. No unrelated coverage
rows were changed. Four capture requests are in `_waves/screens-wanted/RL.md`. Existing screenshots
are reused for unchanged layout, menu, sort and preview surfaces; no new screenshots were captured
or browser behavior exercised. Visual appearance remains unverified.

No unsupported old statement remains known on the three pages. The old advice to ask a specialist
for table related-field columns was replaced with the current Columns… procedure. No product defect
was established by this documentation-only source review.

## Validation

`GUIDE_OUT=_build/RL npm run verify` built 247 pages and passed terms and brand checks, then failed
link checking on 19 missing screenshot files: the four explicitly requested RL placeholders plus
15 other pages' screenshot requests. No page-link or anchor error was reported. Full log: verify.log.
Screenshots must be captured later; adding image files is outside the allowed edit list.
A final explicit `GUIDE_OUT=_build/RL npm run build` checks the final wording; result in build.log.
The existing Caddyfile syntax highlighting warning belongs to run/https.md, outside this wave.

Final explicit build passed: 247 pages in 2.91 seconds. Assigned-page front matter and screenshot-request coverage also checked successfully. No servers or background services were started.
