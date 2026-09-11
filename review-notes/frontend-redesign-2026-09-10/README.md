# Frontend redesign work packages

Status: proposed execution plan, saved at the user's request on 2026-09-10.
UI-01 and UI-02 were implemented on 2026-09-10; UI-03A and UI-03B completed on 2026-09-11.
See their completion records below. No commit was created.

## Outcome

A minimal, professional interface for everyday reference-data work: compact navigation,
a focused collection, a record inspector, contextual actions and deliberate inline edits.
Mobile gets an intentional single-screen flow. Configured applications and object types
share the same design; the example is not a hardcoded Master application.

The scope is too broad for one reliably verified session. Execute UI-01 through UI-07
sequentially, one package per session. Each leaves a usable application. If discovery
reveals that a package exceeds one bounded ownership unit, propose a smaller independent
slice before implementing it. Do not silently complete only part of its acceptance criteria.

UI-07 is deferred by the user. Its original recommended ordering was second, so accessibility and visual gates
constrain UI-02 through UI-06 as they land. It is numbered last only because it was added
after UI-01–UI-06 were written. Its baselines are deliberately refreshed in UI-06.

## Baseline and authority

Build on the current working tree, including untracked files, not just the last commit.
The pending WP9 A/B/C work adds workspace navigation and restored list position, direct
live authoring, conflict recovery, deletion impact confirmation, and optional draft
creation/editing/validation/activation/discard. These are existing behaviours to preserve.

- [Current status](../../docs/PROJECT_STATUS.md)
- [Current interaction specification](../../docs/BASE_0_6_INTERACTION_SPEC.md)
- [WP9 delivery slices and evidence links](../wp9-delivery-slices-2026-09-09.md)
- [Existing browser runners](../../frontend/e2e/README.md)
- [Generated visual concept](concept.png)

The concept is an illustrative visual direction, not a pixel-perfect specification.
It shows a desktop table and inspector plus a mobile record screen. Sample data,
spacing and simultaneous open controls are illustrative. In particular, show a sort
indicator only for the actual active sort, and keep inspector headings compact.

This proposal does not amend the accepted delivery roadmap or close WP9/WP10.
History and historical draft source selection remain WP9-D work. Do not implement
those journeys or show enabled placeholders as part of this redesign.

## Shared boundaries and completion rules

- Frontend only. No backend, API, declarative-model or persistence-contract changes.
  If an interaction requires them, explain the dependency and defer that interaction.
- Preserve live maintenance without draft ceremony, named draft context, model-driven
  types/requirements/read-only rules, and coherent multi-field forms.
- Preserve workspace/application/draft identity in navigation, relationships and lookups;
  preserve filtered list position, retry behaviour and successful loaded content.
- Preserve record and draft concurrency handling, unsaved input, explicit reconciliation,
  signed deletion impact confirmation, and reviewed-version activation.
- Never imply a bulk operation, undo, global search or cross-record transaction that the
  current application does not provide. No new specialist renderers or model workbench redesign.
- Retain all configured panels and their meaning, visibility, ordering and content.
  New presentation must not depend on starter application keys or English panel titles.
- Work directly with one implementation owner. Preserve unrelated changes and do not
  commit unless requested. Inspect the dirty tree before each package.
- Use existing UI wrappers, cursor hooks and view/panel registries. No new UI framework
  or speculative general-purpose layout builder is required.
- Each package includes desktop and mobile behaviour, keyboard/focus operation and
  meaningful regressions at the real interaction boundary. Mobile is not deferred to UI-06.
- After the final frontend change in each package, run `npm run format`, `npm run lint`,
  `npm run test`, and `npm run build` from `frontend/`, once each; run `git diff --check`.
  Do not rerun passing gates without relevant changes. Report warnings and limitations.
- Use the existing isolated real-backend browser harness for affected journeys, with
  at least two configured object types, desktop and 390px mobile. Do not mutate the
  configured development database. Mocked tests alone do not establish browser usability.
- Save a short completion record and representative screenshots in this directory's
  package-specific evidence folder. Update package status here; update current product
  documentation only for behaviour actually implemented in that package.

## UI-01 — Visual foundation and navigation

Status: complete — 2026-09-10. [Implementation and evidence](ui-01-evidence/README.md). Dependency: none.

**User outcome:** users immediately understand where they are, with more space for data.

**Scope**

- Replace the heavy global header with a compact, quiet shell: white content, neutral
  sidebar, charcoal text and restrained green accent; consistent type and spacing.
- Place workspace and application selectors above configured view navigation. Put
  model administration in a clearly separate secondary location. Keep version details
  accessible through an information disclosure rather than a permanent release chip.
- Show workspace/application location once, with an explicit Live or named Draft context.
- Browse hierarchy is the default navigation mode (2026-09-11 correction), with separate branch
  expand/collapse controls and browser-local choices per workspace/application across refreshes.
  It appears before Views; after the first visit, the selected mode is restored on refresh.
  Retain explorer search/paging while switching modes.
  Do not show the full explorer and full view list as competing permanent sections.
- Mobile navigation becomes an accessible drawer, with selected location visible when closed.
- Consolidate redundant headings, uppercase micro-labels, excessive rounded cards and shadows.
  Retain existing form/dialog functionality and model workbench readability.

**Likely source:** `frontend/src/styles/`, `app/AppShell.tsx`,
`features/workspaces/WorkspaceSelector.tsx`, `features/objects/Explorer.tsx`, `ui/`.

**Acceptance**

- Navigate two applications and two workspaces, in Live and an existing Draft; labels and
  write context remain correct. Hidden navigation does not reset query/page state.
- Every configured view and the hierarchy remain discoverable without horizontal menu scrolling.
- Drawer opens/closes by touch and keyboard; focus restores; main content has a useful heading.
- At 390px, the shell has no page-level horizontal overflow. At desktop widths, content
  gains usable room. Text, controls and focus indicators remain readable at 200% zoom.
- Exercise existing navigation browser regression and capture desktop/mobile screenshots.

## UI-02 — Focused collections and table controls

Status: complete — 2026-09-10. [Implementation and evidence](ui-02-evidence/README.md). Dependency: UI-01.
Executed at the user’s explicit request before UI-07; UI-07 remains not started.

**User outcome:** users find records without confronting a form full of filtering controls.

**Scope**

- One visible Add action, search field, Filter popover and Display menu.
- Filter popover exposes all currently configured typed filter operations. Applied filters
  become individually removable chips; removing a chip changes only that filter.
- Sort through supported column headings and an accessible menu alternative. Keep the
  existing single-sort contract and honest page-local counts.
- Display controls offer visibility of existing configured columns, comfortable/compact
  density and page size. Do not invent undeclared fields or saved server-side views.
- Sticky table headings where useful; clear row hover, focus and selection treatment.
- Mobile prioritises record identity and a few configured fields with an explicit way
  to inspect remaining columns; retain usable horizontal table scrolling where needed.

**Likely source:** `features/objects/CollectionView.tsx`, `ObjectToolbar.tsx`,
`ui/ObjectTable.tsx`, `ui/Pagination.tsx`, collection panel tables, styles.

**Acceptance**

- Text, numeric/date, false/zero, unset/null filters retain their existing distinctions.
- Search/filter/sort/page-size changes reset continuation correctly. Back navigation and
  reload retain URL-backed query state. Page-size and display settings have clear ownership.
- Failed pagination retains existing rows and retries the same request; empty and error
  states remain distinct. Loading does not misleadingly display an empty result.
- All configured columns remain reachable on mobile. Filter popover focus and dismissal work.
- Test the collection and at least one embedded collection with two object types.

## UI-03 — Record inspector and contextual actions

Status: UI-03A and UI-03B complete — 2026-09-11. Dependency: UI-02.
[UI-03A implementation and evidence](ui-03a-evidence/README.md) ·
[UI-03B implementation and evidence](ui-03b-evidence/README.md).

The user approved splitting UI-03 after discovery. UI-03A preserves collection origins through
reload/history and guards unsaved record edits during navigation. UI-03B delivers the inspector,
mobile/full-page transitions, contextual actions, selection/focus and collection refresh. Both slices
have passed their scoped acceptance checks; UI-07 remains deferred.

Hierarchy navigation retains its standalone full-record behavior. The subsequent sizing correction
uses that same full-width presentation for collection rows by default. Collection-origin records
retain Back to list; hierarchy records omit it. An unrelated collection must not remain in the middle.

**User outcome:** users inspect and act on records while keeping their place in the collection.

**Scope**

- Open a selected row in the full-width record view, matching hierarchy navigation. Reuse the
  same detail content and data context. Keep the originating collection hidden for state restoration.
- Provide Back to list for collection-origin records. Mobile opens a full record screen.
- Preserve direct record links and browser Back/Forward/reload. If a deep link has no
  originating collection, show a full detail page with a sensible collection return path.
- Use compact property sections; group secondary content only when existing model semantics
  support the grouping. Otherwise retain labelled configured sections in order. No panel loss.
- Add a record overflow menu for Edit all fields, Copy link and Delete record. Right-click
  on a record offers the same actions as a convenience. Destruction retains impact review.
- Keep creation and coherent edit forms available. Compact empty related sections without
  hiding their add action. Keep record activity distinct from workspace revision history.

**Likely source:** `app/App.tsx`, `app/useRouter.ts`, `routing/routes.ts`, `types/ui.ts`,
`features/objects/ObjectDetail.tsx`, `CurrentObjectContent.tsx`, panels, `ui/ActionMenu.tsx`.

**Acceptance**

- From a filtered later page, open a full-width record, close, reload and use Back/Forward; restore
  query/page and selection when applicable. Follow a cross-application related record and return.
- Live and draft records never read or write through the wrong context. Switching context
  cannot leave a stale inspector visible under a different workspace label.
- Saving updates visible record and collection content. Deletion closes the deleted record
  and refreshes the collection appropriately; stale impact previews still require fresh review.
- Dirty edits require deliberate save/discard before changing selection or closing.
- Menus work by visible trigger and keyboard, not only right-click or hover. Inspector
  focus is predictable; the nonmodal desktop inspector does not trap focus away from the table.
- Full-page and inspector paths expose all configured content for two structurally different types.

## UI-04 — Inline fields and clear save feedback

Status: implementation complete — 2026-09-11. [Combined UI-04–UI-06 evidence](ui-04-06-evidence/README.md).
Dependency: UI-03. Validation was intentionally consolidated and kept lightweight at the user's request.

**User outcome:** users correct one value in place and still edit several fields coherently.

**Scope**

- Click/tap or keyboard activation opens the existing appropriate typed editor within a
  property row. Hover/focus reveals a subtle affordance; mobile has a discoverable edit target.
- Begin with fields supported by current single-field mutations. Core fields, parent changes
  and required connections can continue through the coherent form when needed.
- Show Save/Cancel while editing; Enter saves appropriate single-line fields, Escape cancels,
  and multiline Enter inserts a newline. Do not autosave on blur or on checkbox activation.
- Show saving, saved and actionable error states next to the edit. Keep unsaved input on failure.
- Optional missing values offer Add value. Clearing an optional value is distinct from setting
  null, false or empty text. An appearing clear control is available on focus and touch too.
- Retain clear confirmation for persisted-value removal and record deletion; do not promise undo.
- Keep Edit all fields and its single coherent save. Do not turn ordinary editing into a chain
  of mandatory individual-field saves. Avoid table-cell editing in this package.

**Likely source:** `features/objects/panels/AttributesPanel.tsx`, `AttributeValueDialog.tsx`,
`ObjectFormDialog.tsx`, `ui/AttributeField.tsx`, `ui/attributeForm.ts`, shared notices/styles.

**Acceptance**

- Exercise supported text, multiline, number, date and boolean fields, including false/zero,
  missing/null and required/read-only cases. No lossy conversion or unexpected clearing.
- Live and draft saves use existing concurrency paths. Record/draft conflicts retain input
  and show current saved values for explicit reconciliation. Saved-but-refresh-failed remains
  reported as saved and blocks unsafe further writes until the existing recovery completes.
- Validation does not close the editor. Keyboard and touch can save/cancel/clear without hover.
- The full edit form still saves multiple changes together and supports parent/required connections.
- Browser tests cover inline edits and full-form edits for two types, plus a real conflict boundary.

## UI-05 — Selective resizing and remembered display preferences

Status: implementation complete — 2026-09-11. [Combined UI-04–UI-06 evidence](ui-04-06-evidence/README.md).
Dependency: UI-04. Validation was intentionally consolidated and kept lightweight at the user's request.

**User outcome:** users adapt useful working space without managing a complicated dashboard.

**Scope**

- Resize the navigation rail, desktop inspector and useful text-heavy table columns.
  Keep action/icon columns fixed; enforce sensible minimum/maximum widths.
- Provide visible draggable dividers with arrow-key resizing and double-click/Enter reset.
  Rail and inspector preset buttons were removed at the user's request. Include the properties
  divider in the default full record page. Disable split-pane resizing in the mobile single-screen layout.
- Remember display preferences locally with keys scoped to the relevant view/layout.
  Store no records or draft input. Existing saved values must tolerate removed/changed columns,
  a narrower viewport, blocked storage and corrupted preferences.
- Finalise persistence of UI-02 column visibility/density preferences. Use sensible defaults
  and retain at least a discoverable record identity column.

**Likely source:** shell/inspector layout, `ui/ObjectTable.tsx`, Display controls, styles,
and a small shared preference helper if needed by these real consumers.

**Acceptance**

- Resize using pointer, keyboard and presets; reload and reset successfully for two views.
- Narrow the viewport after saving wide settings: the page remains usable, without stranded
  off-screen controls or a zero-width table. Mobile editing remains usable with the keyboard open.
- Missing/invalid/unavailable local storage falls back gracefully. Layout changes do not
  alter query, page, workspace, draft context or unsaved input.

## UI-06 — Draft presentation and composed visual acceptance

Status: implementation complete — 2026-09-11. [Combined UI-04–UI-06 evidence](ui-04-06-evidence/README.md).
Dependency: UI-05. UI-07 remains deferred; full visual and accessibility automation is therefore outside this evidence.

**User outcome:** the complete redesigned journey feels consistent, including coordinated changes
and failure recovery, rather than only the happy-path record screen.

**Scope**

- Refine the draft list and persistent named-draft strip. Keep validation/review/activation
  together with understandable state, and discard in its separate secondary menu.
- Preserve source labels, reviewed-version gating, confirmation and truthful live/draft save
  feedback. Keep Live independently accessible and visually unambiguous.
- Give errors, loading, empty sections, confirmation dialogs and activity consistent treatment.
  Make known activity events readable while retaining details and a truthful unknown-event fallback.
- Review the composed desktop/mobile UI and correct concrete cross-package inconsistencies.
  Do not add new backend capabilities, historical flows or unrelated model-admin functionality.

**Likely source:** `features/workspaces/WorkspaceDrafts.tsx`, `WorkspaceDataContext.tsx`,
record activity/notice presentation, shared styles, `frontend/e2e/` and focused regressions.

**Acceptance**

- Run the existing navigation, live authoring and draft browser journeys against isolated real
  data, updating interaction selectors without weakening their behavioural assertions.
- Prove direct live maintenance; optional draft creation/edit/validate/activate/discard;
  retained unrelated live edits; record/aggregate conflict feedback; signed deletion review;
  failed-page retry; and saved-but-refresh-failed recovery through the redesigned controls.
- Capture collection, inspector, full record, inline edit, filter/menu, draft, deletion and
  error states at desktop, narrow desktop/tablet and 390px mobile sizes, with two object types.
- Review keyboard-only navigation, focus restore, zoom, contrast, touch target sizes,
  no hover-only functionality, and drag alternatives. Record manual checks separately from
  automated results. No blanket accessibility-conformance claim from a test score.
- Confirm model administration remains reachable and readable after shared styling changes.
- Report remaining WP9-D/WP10 gaps explicitly; this frontend package does not close backend,
  migration, packaging or historical acceptance requirements.

## UI-07 — Automated accessibility and visual-regression gates

Status: deferred by the user. Dependency: UI-01.

**Why this package exists.** It is not a redesign slice. This plan and WP10 both require browser
accessibility and visual-regression evidence, and no work package was ever scoped to build the tooling
that produces it. The assignment was stranded by numbering drift:

- [Frontend structure refactor](../../docs/FRONTEND_STRUCTURE_REFACTOR.md) states that "Base 0.6 WP6
  adds the browser, accessibility and visual-regression gates that would close that gap." WP4 was then
  rejected and WP6 was redefined into backend persistence — "Replace object-lifecycle persistence with
  workspace revisions" — so the promise lost its owner.
- WP1 owned `frontend/package.json` but its exit criterion stops at "keyboard and narrow-layout tests
  pass", and its accessibility item only requires *preserving* accessible names, not measuring them.
- ADR-023 declares that "browser keyboard and automated accessibility tests remain release gates"
  and names no owner.
- WP9 built the Playwright harness and explicitly disclaimed accessibility and visual coverage.
- Every later document re-assigns the *evidence* to WP10, while WP10's own header names
  "accessibility/visual checks" as a primary area in the same paragraph that promises "No new feature
  scope hides in this gate." Its requirement to "run" those checks presupposes a suite with no creator,
  so it is unexecutable there regardless of effort.

The tooling must be built in the frontend package that owns the frontend, before any gate can run it.

**User outcome:** people using assistive technology or a different viewport get the same functioning
application, and visual regressions are caught by a gate instead of by review.

**Scope**

- Add `@axe-core/playwright` and assert on the composed pages inside the four existing real-backend
  runners. Do not build a second browser harness; reuse the isolated Vite/FastAPI/SQLite setup the
  WP9 runners already provide.
- Fail on serious and critical violations; record moderate and minor as a count without failing the
  run, so the gate stays actionable rather than noisy.
- Add visual comparison. The repository only *captures* today: it depends on bare `playwright`, not
  `@playwright/test`, so `toHaveScreenshot` is unavailable, and the `page.screenshot()` calls in
  `e2e/*.mjs` write images that nothing ever diffs. Choose one approach and document it
  (`@playwright/test` with committed snapshots, or `pixelmatch` over the existing captures).
- Cover the desktop shell, narrow desktop and 390px mobile, both configured object types, and the
  error, empty, refusal and conflict states the runners already reach.
- Keep the gate honest about what it proves: report automated results separately from manual checks,
  and never derive a conformance claim from a test score. This is UI-06's rule; enforce it here.
- Keep runs deterministic and bounded: fixed viewport, locale and timezone; no network fonts or images
  inside snapshots; write nothing to the configured development database.
- Wire both gates into the per-package completion commands so UI-02 onward run them as they land.

**Likely source:** `frontend/package.json`, `frontend/e2e/*.mjs`, a shared helper in `frontend/e2e/`,
committed snapshot baselines, `frontend/e2e/README.md`.

**Acceptance**

- The four existing browser runners and `npm run lint`/`test`/`build` still pass unchanged; the new
  gates run from the same commands and report into the same evidence file.
- An accessibility run over the shell, collection, inspector, full record, dialog, draft and history
  screens reports zero serious or critical violations, with any moderate/minor findings listed.
- The gates can fail. Reintroducing a known defect — a control without an accessible name, or a
  colour-only status — fails the accessibility gate, and a deliberate style change fails the visual
  gate. A gate that cannot fail is not evidence.
- Two consecutive runs on the same commit produce no snapshot diff.
- Baselines are refreshed deliberately in UI-06, recorded, and never silently overwritten.
- The package records the exact browser build, viewport list and commands used, and states plainly
  that no manual assistive-technology session was performed unless one actually was.
- Ownership is reported explicitly: this package supplies the capability; running it as a release gate
  against the composed product remains WP10.

## Prompt for each execution session

> Implement UI-01 from `review-notes/frontend-redesign-2026-09-10/README.md`.
> Read its dependencies and shared completion rules, inspect the pending working tree,
> and preserve the existing WP9 work. Complete only that package, including its
> frontend gates and named browser checks. Save evidence and update its status.
> Do not change backend/contracts or commit. Report what was exercised and any gaps.

Replace UI-01 with the next package number after its predecessor is complete. UI-07 is the one
exception to that ordering rule: run it second, directly after UI-01, then continue UI-02 onward.
