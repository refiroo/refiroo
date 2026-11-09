# D-MODEL: "Model your data" documented in full

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/DEPTH-COMMON.md`, in that order. Reader: model administrators, who design and change a workspace's model in the model editor; they work in the browser and never open JSON.

Your scope: the entries of section `model` in `_coverage/inventory/*.json` (those still in `_coverage/inventory/uncovered.md`
first), then every page of the section and its guides, each held against the depth questions of `DEPTH-COMMON.md`.

The model editor gained many controls on 2026-11-07 (package ED: `CHANGELOG.md` entry "Added (the model editor sets everything a model holds, 0.13 ED)", `docs/BASE_0_13_IMPLEMENTATION_PLAN.md` section ED): a type's, an attribute type's, a relation type's and an application's Settings; Hidden and Help text on a type's attributes; what an allowed relationship carries; Header and breadcrumbs… on a record page; Sort menu and page size…; a panel's Settings…; Add a view… with tree views and mapping grids; consumer API contract version and preferred types; deleting a model mapping. Document each from the code in `frontend/src/features/model-editor/` (`elementSettings.tsx`, `SettingsTable.tsx`, `viewKinds.ts`, `operations.ts`, `layout.ts`, `ConsumerApis.tsx`). Every model feature in `_coverage/inventory/model-feature.json` is described by the editor control that sets it, never by its JSON path; a feature only the JSON view can set is documented as such and listed in the report.

## Files you may edit

- `src/content/docs/model/**`
- `src/content/docs/guide/model/**`
- `sidebar/model.mjs`
- `_waves/coverage/model.md`
- `_coverage/exclusions.md` (only lines for section `model`)
- `_waves/screens-wanted/D-MODEL.md`
- `_coverage/notes/D-MODEL/**` (working notes)

## Report

As `DEPTH-COMMON.md` says.
