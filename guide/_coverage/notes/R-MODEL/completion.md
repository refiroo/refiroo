# R-MODEL completion

## Completion report

All 69 source headings have one ledger row, in source order: MODEL_AUTHORING 23,
APPLICATION_MODEL 30 (including its two consecutive Upsert keys headings), UI_MODEL 11,
EXAMPLE_MODEL 5. Rows include heading-only entries and explicit skips. No in-scope heading remains open.
Consumer-API definitions remain with their separate owner; no consumer page or consumer guide was edited.

Counts use the actionable fact units recorded above; cross-links and prose-only rearrangements count zero.

| Page under src/content/docs/ | Added | Corrected | Expanded |
| --- | ---: | ---: | ---: |
| model/workbook-proposals.md (new) | 46 | 0 | 0 |
| model/types-attributes-relations.md | 24 | 1 | 6 |
| model/applications-and-views.md | 26 | 0 | 4 |
| model/record-pages-and-tables.md | 14 | 2 | 4 |
| model/workbook-onboarding.md | 7 | 0 | 0 |
| guide/model/rename-or-re-key-an-element.md | 1 | 0 | 0 |
| guide/model/start-a-draft-from-a-workbook.md (cross-link) | 0 | 0 | 0 |
| **Total** | **118** | **3** | **14** |

sidebar/model.mjs adds workbook-proposals in the existing Drafts from a workbook group.
No new screenshots are needed: existing linked editor, evidence, range, layout and matrix screenshots
cover the relevant screens. This was a source/code reconciliation, not a new browser or visual check.

### Source differences resolved

- Editor and migrations are built; old future-tense descriptions were not propagated.
- Model activation is scoped to a workspace, not every workspace; draft comparison stays within its model.
- Workbook checks restart for loading-affecting changes, not every label/layout change.
- Requesting workbook proposals applies editable draft history steps, rather than returning unapplied suggestions.
- Workbook source upload accepts XLSX/CSV, while broader bulk imports also support JSON Lines.
- Current import profiles support combined keys, beyond the source's original single-unique-field description.
- Cross-file inference can use supported name matching as well as identifiers; absolute never-names wording is obsolete.
- Relationship-only table filters are supported despite an earlier contradictory paragraph in APPLICATION_MODEL.
- Current tree/matrix renderers exist; the only supported model language is 0.10, despite historical wider-window claims.
- Fallback detail pages derive children and relationships too, contrary to UI_MODEL's minimal-fields/hierarchy wording.
- JSON attributes may display in ordinary tables and attribute panels, unlike the old guide's blanket exclusion.
- Duplicate headings differ by stage: inference skips later table duplicates with warnings; mapping/loading can distinguish numbered headings.
- History supports saved-step inspection and undo/redo; no arbitrary historical-state viewing control was found.
- No visual field-editor variant selector was found; generic registry extension possibilities were not presented as a control.

### Something that looks wrong

frontend/src/features/model-editor/matrixView.ts actionOptions requires every required cell field to
be selected to offer Create. Backend matrix validation allows an omitted required field when it has
a default. This can hide Create for a declaration the engine accepts. Reported, not changed; the guide
explains the stricter visual form. No runtime reproduction or application test was performed.

### Validation

Final command in guide/: GUIDE_OUT=_build/R-MODEL npm run verify — PASS.
Its build produced 225 pages; terms and brand passed; all 58,070 local links and sources passed.
node --check guide/sidebar/model.mjs and scoped git diff --check also passed.
Earlier verify runs rejected the shared header's intentional application-home link; the shared checker
was updated concurrently outside this wave and the final check passed. No header/checker edit was made here.
Non-blocking build warning: /404 route priority collision. A prior build also warned about unsupported
Caddyfile syntax highlighting on another wave's page. No application suites or browser checks were run.

No steering file appeared. Only the permitted pages, sidebar, ledger, progress and working notes were
written manually. No commits or git state-changing commands were run. Final build log:
_coverage/notes/R-MODEL/verify.log.
