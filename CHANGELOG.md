# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Base 0.8 S1: a Track S volume fixture and read baseline. `tests/volume_fixture.py` generates a model
  with its own keys and bulk-seeds 10,000 root records, 100,000 contained records (20,000 under one
  parent), a seven-level self-hierarchy, a record with 1,500 relations of one type and a parent with
  children of two types, then records revision 1 and derives a draft with scattered edits, tombstones
  and new records. `tests/volume_baseline.py` measures time, SQL statements and ORM rows per request
  in live, draft and history contexts; the full-volume figures and the budgets are recorded in the
  Base 0.8 plan. The new `volume` test group holds the budgets at two scales: live reads and writes
  meet them, while draft/history reads and draft writes are strict expected failures until S2.
- Base 0.8 S2: draft and history reads in SQL. Migration `20260925_01` adds
  `snapshot_attribute_values`, a typed index of revision, draft-base and draft object values (D1),
  backfilled from existing rows and kept current by an ORM flush hook, plus ordered page indexes on
  revision and draft-base objects. Object pages, single records, attributes, relation pages and draft
  write responses read one base-plus-overlay statement instead of the whole draft or revision; at full
  volume a draft page takes 3–6 ms (was about 3.1 s) and a history page 2–5 ms (was 1.1–2.6 s). Live,
  draft and history share one object query builder, held by a parity test across all four contexts.

- Base 0.8 S3: cursor and position paging on every collection endpoint (ADR-030). Pages add
  `prevCursor`, an `anchor` that reopens the page, and with `includeTotal=true` a `totalCount` and
  `startIndex`; requests add `from=end`, `position=N` and, on object, relation and mapping-coverage
  lists, `seek=<value>`. Selecting a page two ways is refused with `422 conflicting_page_parameters`.
  Existing cursors keep working.
- Base 0.8 S4: `topLevel=true` on object lists pages records without a parent in every context;
  relation lists gain `search` (the related record's name and searchable fields) and `sort` (`name`,
  and `createdAt` live) in live, draft and history. Migration `20260925_02` adds (owner, endpoint,
  relation ID) indexes on revision, draft-base and draft relations, so a draft or history relation page reads the
  record's own relations instead of the whole revision.
- Live object page indexes (migration `20260925_03`): (workspace, type, name, sequence) and
  (workspace, parent, type, name, sequence). Name-ordered live pages past the first, their totals and
  position reads now seek instead of scanning the type: 2–13 ms at full volume (a deep position read
  took about 500 ms).

- Base 0.8 S5: continuous-scroll lists (ADR-030). `useCursorWindow` keeps at most five pages,
  prefetches one page ahead of either edge and evicts the page furthest from the viewport;
  `ui/ScrollWindow` keeps rows still as pages arrive above them, shows quiet start and end markers
  and a loading marker only while the user waits, and offers a proportional scrollbar sized from the
  total (a click or a drag's release sends one position request), a page field, start and end
  buttons, Ctrl+Home/Ctrl+End and, on the collection lens, **Go to** a value. Arrow keys move
  through rows across page boundaries. Adopted by the collection lens, record panels (which gain a
  sort, by name by default), relation panels (which gain search and sort), the mapping lens, the
  mapping candidates and the object picker, now a search field over a listbox.
  `tests/volume_seed.py` seeds the volume fixture for the new `test:browser:s5` runner.
- Base 0.8 S6: the sidebar record tree reads by parent. Each root (`rootCreatable`) type of the
  application pages its top-level records (`topLevel=true`) in its own bounded, scrolling group;
  expanding a record pages each child type separately with `parentObjectId`, headed by the type and
  its count, and collapsing releases the branch. **Load more objects** and the global per-type load
  are gone, and with them the record with an unloaded parent drawn at the top level. The tree is a
  `role="tree"` with one tab stop, `aria-setsize` and `aria-posinset` from totals and arrow keys that
  load across a window's edge. Search lists matching records of every type with their ancestor path.
  `ui/ScrollWindow` reads only its own rows, so windows nest, and gains a `group` role for rows owned
  by an enclosing widget. New runner `test:browser:s6`.
- Base 0.8 S7: composed Track S acceptance. New runner `test:browser:s7` walks one collection-lens
  journey per context (scroll, scrollbar click, seek, end, page number, copied URL) over the volume
  fixture and the starter model, checks each landing against the same context's API read, and opens a
  record deep in the tree; it passes at full volume (`S7_VOLUME_SCALE=1`). The accessibility and
  visual gates gain a `scrolling-list-tree` scenario in light and dark, and every visual baseline was
  refreshed after review. `volume_baseline.py` adds a whole-type name search and a deep record read.
- Base 0.8 S8: indexed search (D25). Migration `20260926_03` adds SQLite FTS5 trigram indexes over
  live and snapshot text values, kept equal to the values by triggers on every write. A search of
  three or more characters looks up values only for the records the index names, and still decides
  with the same case-insensitive "contains" match, so results are unchanged in every context. A
  whole-type name search with its total at 100,000 records takes 37 ms live, 73 ms in a draft and
  40 ms in history (was 0.7–0.9 s). Names stay on the (type, name) index; one- and two-character
  searches, and phrases in more than 10,000 values, read each record as before.
- Base 0.8 W6: delete an unused workspace to correct a mistyped key (ADR-019 amendment, D27).
  `DELETE /workspaces/{key}?expectedVersion=N` removes a workspace that is not the default, was never
  published and has no objects or change sets, active or retired; the key can be created again. It
  refuses with `workspace_is_default`, `workspace_has_publications`, `workspace_not_empty` (with
  counts) or `version_conflict`, changing nothing, and is gated by `WORKSPACE_ADMIN_MUTATIONS_ENABLED`.
  Single-workspace responses add `deletable` and `deleteBlockedBy` (OpenAPI lock re-baselined). The
  Workspaces screen offers **Delete…** with a confirmation naming the key, or says why it cannot.

### Changed

- Base 0.8 W4: a global **Workspaces** screen beside **Models**, in the same list-and-detail layout,
  lists every workspace including retired ones and creates, renames, retires, reactivates and sets
  the default with their version claims; a conflict shows the current state and is never retried.
  It appears in the header, and as **Manage workspaces** in the workspace selector, only when
  `workspaceAdmin.manageWorkspaces` is true. The selector is a read-only label while one workspace
  exists. Models and Workspaces show the deployment capabilities read only, naming the setting of a
  disabled group, which `GET /capabilities` now reports in each group's new `setting` field
  (OpenAPI lock re-baselined). The narrow navigation drawer is titled for its screen. New browser
  runner `test:browser:w4`; the a11y and visual gates gain `workspaces-admin` light and dark, and
  every shell baseline was refreshed for the header entry and the single-workspace label.
- Base 0.8 W3: `WORKSPACE_ADMIN_MUTATIONS_ENABLED` gates only workspace create, rename, retire and
  set default (ADR-031). Change-set create, update, delete, model-release change, validation and
  publish, and publication withdrawal, are always registered and still refused in a retired
  workspace. Their OpenAPI tag is `change-sets`.
- Base 0.8 W2: data drafts are **change sets** and workspace revisions are **publications** in every
  layer (ADR-031), with no aliases. Breaking API changes:
  - Routes: `/workspaces/{key}/drafts` → `/workspaces/{key}/change-sets`,
    `/workspace-drafts/{id}` → `/change-sets/{id}`, `/workspace-drafts/{id}/activation` →
    `/change-sets/{id}/publication`, `/workspaces/{key}/drafts/{id}/model-release` →
    `/change-sets/{id}/model-release`, `/workspaces/{key}/revisions` → `/workspaces/{key}/publications`,
    `/workspace-revisions/{id}` → `/publications/{id}`, and `POST /workspaces/{key}/retirement` with
    `expectedActiveRevisionId` → `POST /publications/{id}/withdrawal` with no body (the path ID is the
    claim). Lists stay under their workspace; single items are flat by global ID.
  - Fields and parameters: `workspaceDraftId` → `changeSetId`, `workspaceRevisionId` →
    `publicationId`, `expectedWorkspaceDraftVersion` and `expectedDraftVersion` →
    `expectedChangeSetVersion`, `workspaceDraftVersion` → `changeSetVersion`,
    `expectedActiveRevisionId` → `expectedActivePublicationId`, `derivedFromRevisionId` →
    `derivedFromPublicationId`, `supersedesRevisionId` → `supersedesPublicationId`, `revisionNumber`
    → `publicationNumber`, `activatedAt` → `publishedAt`, `retiredAt` → `withdrawnAt`, source
    `"revision"` → `"publication"` and publication status `retired` → `withdrawn`. A publication also
    returns `modelReleaseKey` and `modelReleaseVersion`.
  - Error codes: `workspace_draft_*` → `change_set_*` (`change_set_not_found`,
    `change_set_version_conflict`, `change_set_model_release_conflict`, `change_set_required`,
    `change_set_snapshot_retry`, `change_set_snapshot_unsupported`), `draft_content_incompatible` →
    `change_set_content_incompatible`, `workspace_revision_not_found` → `publication_not_found` and
    `workspace_active_revision_conflict` → `workspace_active_publication_conflict`.

  Migration `20260926_04` rebuilds the draft and revision tables as `change_set*` and `publication*`
  with their columns, indexes and constraints, renames `workspaces.active_revision_id` and
  `relation_set_versions.workspace_draft_id`, records snapshot value owners as `publication`, `base`
  and `change_set`, and rewrites stored audit names (`change-set`, `change-set-object`,
  `publication`/`published`, `publication-withdrawn`) and payload keys. It resumes an interrupted run
  on SQLite and refuses another dialect with a recovery instruction. The browser says "Change set ·
  name", "Publish change set", "Publication N" with its model release and date, and "Withdraw
  publication"; its URLs are `/apps/{app}/change-sets` and `/apps/{app}/publications` with
  `changeSetId` and `publicationId`. The OpenAPI lock is re-baselined, the `drafts` test marker is
  `change_sets`, and the WP9 runners are `test:browser:change-sets` and `test:browser:publications`.
- Base 0.8 W1: documentation adopts the ADR-031 terms. The glossary defines workspace, live, change
  set, publication ("Publication N" and its per-workspace number), model draft, model release, and the
  verbs publish, install, activate, withdraw and retire, with a diagram of one workspace's live data,
  change sets and publications and a note on the old names the code keeps until W2. Milestones A and B
  are renamed **Translation editor** and **Hierarchy editor** in the roadmap, TODO, the 0.8 plan and the
  functionality catalogue. The stale "non-default workspace detail gap" notes in PRODUCT, the product
  guide, user journeys, user stories and the functionality catalogue are corrected: 0.6 WP9 repaired
  the context handoff, and the WP9 navigation runner opens detail, children, relationships and
  history in a non-default workspace.
- Base 0.8 S8: a draft list's total counts its base, less the rows the draft replaces, plus its own
  rows, instead of the union (a total at full volume in 19–31 ms, was 45–56 ms); a first or
  position page that reaches the end of its list returns its total without a count.
- Base 0.8 S4R1: relation lists sort and search the related record through the object query
  builder, as object lists do. `sort` takes `name` (now the default in every context), any
  `sortable` attribute of the related type, `ancestor:<type>`, and live only the related record's
  `createdAt`/`updatedAt`; relation creation order is no longer a sort. Attribute and ancestor sorts
  need the listed relations to reach one object type (`422 invalid_sort` otherwise), and
  `relationTypeKey` repeats to list several relation types. Search covers the related types'
  searchable fields instead of every searchable attribute type. Draft and history object and
  relation pages return each record's `path` (it was empty, so ancestor columns were blank), and a
  relation page for a record the context does not hold answers `404` as it does live. Migration
  `20260926_01` rebuilds the draft and history relation endpoint indexes to cover the relation type
  and the other end. Relation cursors issued before the change are refused with `422 invalid_cursor`.
- Base 0.8 S4R2: schema 0.7. The engine accepts `schemaVersion: "0.7"` beside 0.5 and 0.6 in
  validation, the registry, releases, `model_schema_upgrade` and the startup message. Relations
  panels may declare `sortFields` and `defaultSort` (D21), validated against what the relation list
  accepts: `name`, a sortable attribute of the one related type, or an ancestor it can sit under;
  a 0.5 or 0.6 model declaring them is refused at the field's path, and absent fields stay out of the
  canonical document so earlier releases keep their hash. The starter model moves to schema 0.7,
  content release 0.8.0: its system panels sort by system, value code and name, its translation
  panels by language, translated name and name, and `translated-name` becomes sortable.
- Base 0.8 S4R3: one sort element for table-shaped lists (`ui/TableSort`), and one rule: every data
  column sorts. Column headers sort: a quiet sort icon on hover and focus (drawn in the header's
  padding, so columns never widen), an accent up or down arrow on the sorted column, activation toggling
  the direction, `aria-sort`, an accessible name stating the order and a polite announcement. Every
  list with sort fields shows the same icon-only **Sort** menu in its toolbar (radio items per field
  plus the direction, with a tooltip), which also reaches columns collapsed at 390px or hidden through
  Display and fields a view or panel declares without a column. The collection lens, record panels and
  relation panels use it. Removed: the lens toolbar's **Sort** popover and the relation panel's inline
  **Sort** select with its fixed name and creation-time options. `ui/ActionMenu` gains radio sections,
  a trigger icon and a tooltip.
- Sorting no longer depends on the attribute type's `sortable` flag: object and relation lists sort by
  any non-JSON attribute, and a relation list over several related types sorts by an attribute with
  records whose type lacks it last. `objectType` sorts by the type's model name and, on relation
  lists, `relationship` by the label each row shows, both then by name. The only data columns that do
  not sort are the computed path, JSON attributes and, outside live data, the unrecorded timestamps.
  Model validation follows: view and relations-panel sort fields accept any non-JSON attribute plus
  `objectType` and (panels) `relationship`, and a relations panel may declare `defaultSort` alone.
  The OpenAPI lock is re-baselined for the two `sort` descriptions.
- Collection URLs hold one `anchor` cursor for the page at the top of the list instead of a
  `cursor` trail, written as the user scrolls without adding history entries. Older links with
  `cursor` parameters open at the start. Previous/Next page buttons and **Load more** in panels,
  relation lists and pickers are removed.
- Page responses carry the new navigation fields beside `items` and `nextCursor`, so a client that
  compared a whole page body must allow them. Live relation pages build their related records in one
  batch instead of two statements per row.
- Draft and history `search` matches the record name and `searchable` fields, as live search does,
  instead of every attribute's text. Draft and history cursors issued before the upgrade are refused
  with `422 invalid_cursor`; restart from the first page.

- Base 0.8 S4R4: object lists without `sort` order by name in live, draft and history (live used
  creation order, drafts and history record ID), so the object picker and Explorer search results
  list by name and an unsorted list accepts `seek` by name. Mapping coverage and candidates list by
  name, and coverage `seek` takes a source name instead of an ID. Cursors issued for the former
  default orders are refused with `422 invalid_cursor`; reload from the first page.
- Base 0.8 S4R5: every page lists `items` first, then its navigation fields. `totalCount` and
  `startIndex` are omitted unless `includeTotal=true` instead of returned as `null`, and OpenAPI
  documents them as optional integers. Clients that tested them for `null` should test for absence.
- Base 0.8 S4R6: a draft position read resolves in its base's index and corrects for the draft's
  own rows, instead of skipping every earlier row through the base-plus-overlay union. Three quarters
  into a whole 100,000-record type it takes 60 ms (was 175 ms; about 40 ms of it is the total count), and
  its cost no longer grows with the position.

### Fixed

- Base 0.8 W6 review: on the Workspaces screen, creating a workspace after deleting one no longer
  leaves the "was deleted" notice above the new workspace.
- Base 0.8 W6: a live write that resolved its workspace before the workspace was retired, or deleted,
  could still commit into it. It now rereads the workspace inside its transaction and returns
  `409 workspace_retired` or `404 workspace_not_found`, saving nothing.
- Base 0.8 W5: a live write validated under one model release could commit after another release
  was activated, storing data the new release does not allow. The write now rereads the active
  release inside its transaction and returns `409 model_release_changed`, saving nothing; activation
  reserves the database writer before its compatibility check, and returns
  `409 model_activation_retry` if live writes keep it busy. Holds in one process and across
  instances sharing a SQLite database.
- Base 0.8 S8 review: the trigram search index is SQLite-only. Migration `20260926_03` changes
  nothing on another dialect (it stopped a PostgreSQL upgrade), and a search there reads each
  record's values as before S8 instead of naming the missing index table.
- Base 0.8 S2b: a draft write no longer loads the whole draft. Object, attribute, relation and
  mapping writes check only the records and relations they touch: the parent and its ancestors, the
  relations at each end, the draft-wide holders of a unique value through the typed value index, and
  for a deletion the subtree it removes. Renaming one record in a 100,000-record draft takes 7.5 ms
  (was 4.9 s). Migration `20260926_02` adds a value lookup index on `snapshot_attribute_values`. A
  unique attribute without a value no longer conflicts with records that lack it.
- A draft or history single-record read returned an empty `path`, so the record page showed no
  ancestors and the sidebar tree could not open the record's branch in those contexts. It now returns
  the ancestor path, as live reads and draft and history pages do.
- In the dark theme, a list footer's page field and **Go to** field kept the browser's light field
  colours and failed contrast; they now use the shared text-input treatment.
- Paging a list sorted by a boolean field past its first page returned a server error; keyset cursor
  positions are now bound as typed values. Keyset pages also seek to the cursor through the first sort
  key's index instead of scanning every earlier row.

## [0.7.0] - 2026-09-25

### Added

- Base 0.7 WP-9: composed acceptance for SC-07 and SC-15. `test:browser:sc07` resolves unmapped,
  differently mapped and 25-target ambiguous rows (candidates beyond page one, bounded previews with
  continuation), survives a racing generic relation write with the attempted choice kept, proves an
  independent binding with a typed relation attribute is untouched, and refuses draft activation when
  live changed the draft's mapping set. `test:browser:sc15` prepares one draft on an installed candidate
  release while another stays on the active one, refuses incompatible and unavailable releases without
  touching live data, history or another workspace, then publishes the prepared draft after the
  candidate is activated and discards the other. `test_build07_wp9_acceptance.py` adds corrupt and
  unsupported releases at the HTTP boundary. The browser harness accepts a model variant
  (`transformModel`).

- Base 0.7 WP-13C: `docs/testing/UI_ACCEPTANCE.md` names the existing reference pattern for each kind
  of UI element and inventories the states of every 0.7 surface with its evidence. The new browser
  runner `test:browser:wp13c` checks mapping and draft states against a real backend: outages with
  Retry, empty and no-match results, conflict review, the inverse mapping in a draft, a draft on a
  non-active model release, keyboard focus and phone width. UI changes now report functional,
  accessibility and visual evidence separately. Found and scoped WP-10F and WP-10G.

- Base 0.7 WP-13B: `docs/testing/EXECUTION_GUIDE.md` maps each changed production boundary to its
  focused checks and shared-boundary expansion, lists the WP-9 comprehensive command set and records
  measured before/after costs. Backend tests carry contract-group markers (`pytest -m mapping`, …) from
  one manifest in `conftest.py`; an unclassified test module or unknown marker fails collection.
  Vitest runs pure `.test.ts` files in a `unit` project without jsdom and components in `dom`. The
  gate-helper check (now in CI) refuses an unlisted browser runner, and the browser harness prints
  its setup phase timings.

- Base 0.7 WP-13A: `docs/testing/COVERAGE_MAP.md` links product invariants and capability contracts
  to their test evidence, boundary and cost tier, ranks risk and records audit status, residual risk
  and consolidation decisions. New regression evidence: mapping replacement refuses foreign-workspace
  drafts, unknown workspaces, a revision context and retired workspaces without changing data; draft
  relation update/delete advance both draft anchors' set versions only; runtime sources contain no
  starter-model key literal; live `date` values keep their type through write, boundary filters and
  sort; the mapping conflict retry sends the user's attempted target. Two confirmed defects are
  reproduced and fixed as WP-10C and WP-10D, and a third as WP-10E (see Fixed). One relation-set test duplicating stronger evidence was removed.

- Base 0.7 WP-12: `GET /api/v1/model-releases/{releaseId}/activations` reads a release's recorded
  activations (oldest first, with the release each replaced). Models release details move the
  Release ID and content hash into an explained, copyable **Technical details** disclosure; release
  history compares an earlier baseline (Before) with the selected release (After), including the
  active release, defaulting to the recorded predecessor, otherwise the labelled preceding installed
  release of the same key, with an explicit **Compare with** selector and truthful first-release,
  identical-content and unsupported-baseline states. Activation readiness is shown separately and
  always checks the current active release against the candidate.

- Dark mode: a complete dark token set that follows the system preference by default, with an
  explicit System / Light / Dark choice saved per browser and applied before first paint.
- Settings control at the bottom of the navigation rail with the appearance choice and an
  Account placeholder (local single-user session, disabled Sign in) for the planned multi-user
  authentication.
- Dark accessibility scenarios (core pages and the settings menu) and four dark visual baselines.

- Build 0.7 WP-7 browser draft version selection (ADR-028 frontend). Draft creation offers an
  optional model-release selector when multiple releases are installed; default is the active release.
  Draft list cards and detail header show each draft's model release key and version. An informational
  banner explains the state when a draft's version differs from the active release, and activation is
  disabled with a tooltip. A "Change model version" action in secondary draft actions loads available
  releases, attempts the pin change via the WP-6 PATCH endpoint, shows incompatibility diagnostics
  on failure and reloads the model context on success. Dirty-input protection via the existing
  `allowNavigation()` guard before applying version changes. Model-context refresh after pin change
  reloads the draft, pinned model and active release state; external pin change detection via
  `useEffect` + `useRef` in `LoadedDraft`. `WorkspaceDraft` type extended with `modelReleaseKey` and
  `modelReleaseVersion`. 169 frontend tests (5 new), zero lint errors, production build passes.

- Build 0.7 WP-5 atomic mapping replacement API: `PUT /api/v1/workspaces/{workspaceKey}/mappings`
  atomically creates, replaces or removes a mapping for one source in a configured relation binding.
  Supports live and draft contexts with optimistic concurrency via `expectedMappingVersion` and
  `expectedWorkspaceDraftVersion`. Direction-aware cross-cardinality enforcement (one-to-one always,
  one-to-many outgoing only). Retained relation identity when resolving ambiguous→mapped. Typed
  attribute semantics: omitted preserves retained edge values, explicit replaces, `{}` clears. Null
  target with non-empty attributes rejected. Idempotent no-ops with valid tokens produce no version
  increment or audit event. Stale tokens return `409 mapping_version_conflict` with bounded preview.
  Single-direction set version increments avoid double counting. Containment and required-ownership
  bindings rejected. Mapping-transition audit events with old/new targets and relation identities.
  After acceptance follow-up: 73 replacement/activation integration tests; 486 backend tests pass
  on SQLite.

- Build 0.7 mapping list API: `GET /api/v1/workspaces/{workspaceKey}/mappings` returns cursor-paged
  live/draft edges with optional binding, direction and name filters, directional set tokens, stored
  typed relation attributes and optional view-specific projections. Omitting direction returns both
  orientations of each edge; this supplements source-grouped coverage for integration reads.

- Build 0.7 WP-4 mapping query APIs: workspace-scoped coverage, candidate search and version-bound
  target details resolve the selected `mappingGrid` view under the live or draft-pinned model.
  SQL pagination and batched reads return typed projections, mapped/unmapped/ambiguous states,
  exact counts and at most 20 target summaries with explicit continuation. Cursors bind workspace,
  context, model release, view, direction and query configuration.

- Schema 0.6 `mappingGrid` view contract (Build 0.7 WP-2). The model language now accepts
  `schemaVersion: "0.6"` alongside `"0.5"`. `MappingGridViewDefinition` joins `TableViewDefinition`
  in a Pydantic discriminated union on `ViewDefinition.type`. Backend validation checks relation
  binding existence, rejects containment (`parentOf`) and required-ownership bindings, validates
  source/target columns against attached attributes, and verifies candidate search fields are
  searchable target-type attributes. The starter model advances to schema 0.6 / content release 0.7.0
  with two mapping grid views: `system-to-master-mapping` (outgoing) in RDM Systems and
  `master-to-system-mapping` (incoming) in RDM Master. Frontend `ViewDefinition` is a TypeScript
  discriminated union with type-safe narrowing; its initial placeholder was subsequently replaced by
  the WP-8/WP-14 contextual lens. 11 new backend tests cover parse, activation, backward compatibility
  and all validation rejection paths.

- Relation-set version persistence and generic participation (Build 0.7 WP-3). Every generic relation
  write (create, update, delete) now atomically maintains exact-binding set versions in both the
  outgoing and incoming directions. The `relation_set_versions` table tracks the optimistic version
  of each (workspace, optional draft, relation type, from/to object-type pair, anchor object,
  direction) combination. Rows are created lazily on first touch with version 1; untouched sets have
  implicit version 0. Draft-scoped and live-scoped versions are independent. Draft deletion cascades
  set-version rows; draft activation merges draft mutation counts into live set versions. A partial
  unique index protects live-context uniqueness where `workspace_draft_id IS NULL`. 9 focused tests
  cover all mutation paths, independent bindings, draft/live isolation, cascade and activation merge.
  All 379 backend tests pass.

- UI-07 automated accessibility and visual-regression gates (WP-1). `npm run test:a11y` runs
  axe-core WCAG 2.1 AA checks on 9 core page types across two object types; `npm run test:visual`
  compares viewport screenshots against committed baselines using pixelmatch. ~16 color-contrast
  violations fixed, definition-list structure corrected, sidebar landmark added. Two known violations
  allowlisted with tracked references. Light-theme baselines committed; dark baselines followed with
  dark mode.

### Changed

- Backend tests that need a private database copy a once-migrated template instead of running every
  Alembic migration per test; startup and migration tests still migrate for real. The sampled backend
  selection runs in 22.7 s instead of 46.8 s with the same cases. A pagination test that failed when run
  alone now owns its database.

- Models page aligned with the rest of the UI: the release/draft catalogue is now sidebar
  navigation, and the main column uses the shared context bar, page header and surfaces.

- Base 0.7 UX pass over the generic frontend, with routes, data contexts and API contracts unchanged:
  applications as header tabs with model icons; a segmented Live / Drafts / History control;
  collection list plus a collapsed-by-default record tree that opens toward the active record;
  one Filter popover with an applied count; lens tabs, scope banner and page count beside
  pagination; whole-row open; a record header with one breadcrumb line and a visible Edit record
  action; readable record activity without identifiers or concurrency tokens; a compact draft bar;
  and a rewritten design-token stylesheet with a 12–14px minimum text scale.
- Mapping lenses: segmented coverage filter, row-click to map, a searchable radio list of
  candidates, **Save and next**, and an explicit **Remove mapping** action. Selecting nothing no
  longer turns the primary button into a clear operation.

- Build 0.7 WP-14 composes model-defined table and mapping views as lenses of one contextual
  collection. One application browser now presents virtual collection groups alongside runtime
  hierarchy records, replacing the separate Browse hierarchy / Views modes. Direct-parent scope,
  typed field facets and mapping coverage state are visible and URL-backed. Mapping coverage applies
  parent/state filters before cursor pagination in live, draft and immutable-revision contexts, and
  cursor fingerprints bind both values. This remains generic over configured applications, object
  types, relations and renderers; Master, Systems and Translations remain starter examples.

- The WP-8A/WP-8B review retained atomic mapping actions while removing duplicate configured name
  columns and requiring explicit review before retrying after a mapping-version conflict. Historical
  mapping reads now use revision projections and expose no mutation controls. Focused package evidence
  covers both configured mapping directions, direct-parent scope, visible mapping-state filtering,
  live replacement, narrow layout and the composed page's accessibility.

- Extended the planned 0.7 design and delivery documentation after plan review: WP-1–WP-3 remain
  frozen; later packages specify bounded view-based mapping reads, stable retained relation identities,
  typed attributes, direction-aware constraints and atomic whole-candidate draft compatibility.
  Mapping UI is split into WP-8A coverage and WP-8B actions; WP-9 expands integration/a11y/visual
  evidence, with conditional WP-10 for confirmed foundation gaps.

### Fixed

- Base 0.7 WP-10K: records and relations read in a draft or from history no longer show the current
  time as their created and updated times. These are not recorded there, so the API returns `null`
  (the fields are now nullable), filtering or sorting by them is refused with an explanation instead
  of matching nothing, and collection views neither offer nor send them outside live data.
- Base 0.7 WP-10H: the mapping dialog no longer offers **Remove mapping** for a required
  relationship, which the server refuses; it asks for a replacement instead.
- Base 0.7 WP-10I: starting a draft on an incompatible model release lists the records that do not
  fit, as a version change already did, and draft error messages no longer run two sentences together.
- Base 0.7 WP-10J: missing-required and read-only field errors name the fields (“Required fields are
  missing: External ID”) instead of printing a list of keys; the keys are in `details.attributeTypeKeys`.
- Test reliability: the WP-12 and WP-13C browser runners waited too little for clipboard feedback
  and focus restore; a current-live base test read another test's draft from the shared database. The
  Models page visual baselines now show the WP-12 layout.
- Base 0.7 WP-10E: a live `dateTime` write keeps its instant. Values are stored in UTC and every
  context returns them with an explicit offset; decimals read back in one form without trailing
  zeros (live reads were padded to `12.5000000000`), so draft uniqueness compares equal decimals as
  equal. All server timestamps (`createdAt`, `updatedAt`, `occurredAt`, …) now carry an offset on
  SQLite too, and the browser no longer appends one to zone-less times.
- Base 0.7 WP-10F: **Create new …** in a mapping lens asks which application the new target
  belongs to, listing every application that contains its type and defaulting to the lens's own.
  Parent choices are limited to types in that application, and a notice explains when it has none.
  The starter can now create a target in both mapping directions.
- Base 0.7 WP-10G: the mapping dialog's search box keeps its height at phone width, and the draft
  model-mismatch and historical-revision notices name releases by key and version instead of UUID.
- Base 0.7 WP-10C: `date`, `dateTime` and `decimal` values can be written in a workspace draft
  (create, update and the field endpoint returned 500) and are published to live on activation,
  including values captured from live. Draft and revision lists filter and sort these fields and
  integers by their declared type: numbers no longer sort as text (`10` before `5`), date-times sort
  by instant, and a zone-less `dateTime` filter value is read as UTC.
- Base 0.7 WP-10D: renaming or moving a contained record inherited by a draft no longer adds a
  second containment relation with a new ID. An unchanged parent keeps its relation; a move replaces
  it with exactly one. Such drafts now activate instead of refusing with `duplicate_edge` or
  `relation_cardinality_violation`.

- WP1-001: the navigation resize separator is inside the navigation landmark, so its accessibility
  exception is removed. Collection and settings popovers render inside a landmark (or the open
  dialog), and zone-less server timestamps are read as UTC.

- Build 0.7 WP-5 review: enforce ancestor-scoped constraints against the final replacement graph,
  and reject missing required ancestors in generic draft relation writes as in live writes. Reject
  required-ownership replacement irrespective of relation orientation. Explicit empty application/view
  keys fail validation instead of selecting unconfigured reads. Twelve HTTP regressions cover these
  boundaries, preserved tokens and valid replacements within one ancestor scope.

- Build 0.7 WP-10B: draft activation now refuses new, removed or updated live relations in exact
  mutable binding sets the draft touched, including previously unmapped sets. It compares the
  immutable source/live edge identities and versions before applying any rows. Refusals preserve
  the draft, live data and revision designation and include bounded mapping-set diagnostics with
  recovery instructions. Unrelated live mapping work and existing containment/ownership merge
  behavior remain covered. WP-5 acceptance adds independent-binding isolation, required-ownership
  and clearing refusals, and overlapping generic create/update/delete versus mapping saves.

- Build 0.7 WP-10A, found in WP-4 review: confirmed live/draft object cascades now advance both
  directional relation-set versions for removed edges. Stale mapping target continuations return
  `409 mapping_version_conflict` with refresh guidance; previews and rejected deletes leave versions
  unchanged. Regression coverage exercises both directions and contexts.

- Build 0.7 WP-1/WP-2 review fixes: scope accessibility exceptions to known targets and node counts,
  fail visual comparisons on missing baselines outside explicit update mode, reject `mappingGrid`
  under schema 0.5, and allow the documented offline schema 0.4 recovery to select a compatible
  schema 0.5 or 0.6 candidate. The CLI reports expected refusals without a traceback, and the draft
  context regression now checks the current named-draft and version presentation. Visual capture
  waits for loaded panels, and the model-workbench baseline now covers the loaded release detail.

## [0.6.0] - 2026-09-11

### Changed

- Implemented WP8.1-A model authority boundaries. Compatibility now examines all authoritative live
  objects, attributes and relations, including catalogue-retired workspaces. Draft and historical
  reads resolve their pinned supported model before filters, typed responses and relation expansion;
  missing, corrupt or unsupported pins and workspace-context mismatches return structured errors.

- WP8.1-B captures an immutable current-live draft base including post-publication edits, model and
  record versions, with live data that has no prior publication. Historical source remains separate.

- WP8.1-C delivers newest-first revision history with deterministic cursor retry. Designation
  retirement preserves live access and history; catalogue retirement rejects writes.

- Reviewed the uncommitted WP8 implementation against the live/draft API contracts. Corrected
  activation and cascade deletion ordering, association confirmation and ownership checks, atomic
  draft version claims, public relation UUID reads, retired-workspace publication guards, and
  read-only attribute handling, draft containment validation and cross-workspace ID collisions.
  Added request-boundary and audit-migration regression coverage. Cascade confirmation now requires
  the signed token from the exact displayed preview and rejects any intervening hierarchy change with
  no deletion or audit side effects. Missing tokens are rejected before stale-version checks, draft
  deletion verifies the route object type, live deletion serializes against workspace retirement and
  inconsistent cross-workspace graph edges are refused. The frontend adapter carries both live and
  draft confirmation context.

- Reconciled technical documentation and delivery planning with the accepted product stories and
  GAP-01–GAP-08 answers. ADR-027 consolidates live data, optional copied drafts, immutable history,
  truthful publication retirement and newest-first history. Corrected API documentation against
  current payloads and cursor behavior.

- Implemented ADR-026 live active data writes: the active workspace is live-writable for **data**.
  `workspaceDraftId` is optional on record writes — present stages into the design draft; absent
  writes directly to the live active object store (record `expectedVersion` claim + audit, no
  workspace revision). Active reads resolve the live projection; activation is a delta-merge of the
  draft onto current live content with per-record version conflict detection (`version_mismatch` /
  `id_collision` / `duplicate_edge`), merged-graph validation and a merged revision snapshot that
  preserves live-only records. Restored `services/objects.py` CRUD functions, `services/relations.py`
  helpers and `services/deletion.py` as the live write path basis; added the workspace-audit seam and
  a corrective migration widening the audit `aggregate_id` column to host live object/relation ids.
  Amends ADR-024/ADR-025 write-context clauses for data content.

- Corrective Base 0.6 WP6 persistence: workspace drafts and immutable workspace revisions own the
  staged/historical graph; ADR-026 subsequently restores live-row current-data authority. The migration
  converts only unambiguous Base 0.5/rejected-WP4 workspace graphs,
  preserves public object and relation UUIDs, and removes per-object lifecycle persistence.

- The backend now requires Python 3.14. The local version pin, package metadata, Ruff target, CI
  runtime, container base image and development documentation all use 3.14; Python 3.12
  compatibility is no longer maintained.

- Frontend structure refactor, phases 0–4 of `docs/FRONTEND_STRUCTURE_REFACTOR.md`. No API
  contract, model contract or architectural change. `frontend/src` is reorganized into `app/`,
  `features/`, `ui/`, `model/`, `routing/`, `lib/`, `types/` and `styles/`, with every internal
  import going through an `@/` alias. `types.ts` and `utils/model.ts` are split by concern behind a
  barrel, the four overloaded components are split into 28 modules, and `styles.css` becomes four
  layers whose built output is byte-identical.

- The generic view and panel registries are rendered as elements rather than called as functions.
  Nothing was broken, but a panel component gaining state would have made `ObjectDetail`'s hook
  order depend on which panels a model declares as visible. The panel registry is keyed by the
  `PanelDefinition` discriminant, removing its per-entry casts, and both registries now live in
  their own modules.

- Client error handling is consolidated in `api/errors`. `isApiError` replaces five untyped casts
  used to detect optimistic-concurrency conflicts, and `errorMessage` replaces 36 inline
  expressions. Seven messages that reached the UI as `Error: …` now read like every other message.

- Cursor paging and search debouncing are consolidated into `useCursorPages`, `useCursorFeed` and
  `useDebouncedValue`, replacing two incompatible paging implementations across seven components.

- Every dialog shares one modal shell, `ui/Modal`. Five dialogs previously rebuilt the same backdrop
  and disagreed about its behavior. `ObjectFormDialog`, `AttributeValueDialog` and
  `RelationFormDialog` now close on Escape and return focus to whatever opened them; Tab is trapped
  inside an open dialog; the page no longer scrolls behind one; and two dialogs that carried
  hardcoded `aria-labelledby` ids now generate them, so opening two cannot produce duplicate ids.

- Frontend redesign (UI-01–UI-06). Compact neutral sidebar with workspace/application/view
  navigation; Browse hierarchy default with browser-local expand/collapse persistence; accessible
  mobile navigation drawer. Focused collections with search, typed filter popover, sort, display
  controls, sticky headings, comfortable/compact density and mobile-aware column prioritisation.
  Full-width record inspector with collection-origin preservation through reload/Back/Forward,
  contextual action menus, dirty-edit navigation guards and cross-application related-record return.
  Inline typed field editing with explicit save/cancel, null/removal distinction, saved/error
  feedback and retained coherent multi-field forms. Pointer and keyboard resizable navigation rail,
  inspector and table columns with browser-local display preferences. Refined draft catalogue,
  named-draft strip, consistent error/loading/empty/confirmation treatment and composed
  desktop/mobile visual review. UI-07 (automated accessibility and visual-regression gates) is
  deferred to 0.7.

### Added

- WP9 complete generic browser tasks in live, draft and history contexts. Slice A implements live
  workspace navigation with cursor-position restoration and retry/content preservation. Slice B
  implements direct live Add/Edit/Delete with typed fields, ordinary relationships and translations,
  conflict reconciliation and signed deletion confirmation. Slice C implements optional current-live
  drafts, shared draft authoring, validation, activation and discard with aggregate concurrency and
  conflict feedback. Slice D implements newest-first immutable history, pinned-model reads, historical
  draft sources and truthful publication retirement. SC-01–SC-06 and SC-08 have isolated real-backend
  browser evidence with two configured object types at desktop and 390px mobile widths.

- WP10 composed release validation: product scenarios exercised against a real browser and backend,
  including live CRUD without a draft, optional staging, current-live draft bases, concurrency and
  delta merge, whole-graph atomic failure, live-only compatibility and pinned historical typing.
  Keyboard/focus/narrow-layout journeys, migration/lifespan, packaging and public-contract checks.
  Automated accessibility and visual-regression tooling (UI-07) is deferred; manual keyboard and
  focus checks are recorded.

- Base 0.6 WP7 corrective CRUD restoration: the established generic object, attribute, relation and
  translation CRUD contract is restored over WP6 workspace storage. Originally draft-scoped, it was
  extended by ADR-026 to direct live writes plus optional drafts. No per-record lifecycle or nested
  public CRUD resources are introduced, and the
  original CRUD, attribute, cascade and translation suites are restored and enabled.

- Base 0.6 WP8 workspace lifecycle orchestration. Root and
  history-derived workspace drafts, whole-graph validation, atomic activation that writes one immutable
  workspace revision of the merged live graph and applies authored changes in one transaction after the
  ADR-026 correction,
  cursor-paged immutable revision history, and publication retirement under an expected active-revision
  claim. Draft/revision/validation/activation/retirement events use dedicated workspace aggregates with
  bounded identity payloads, kept separate from record-level `object-draft` and `relation` audit
  events. Objects, typed attributes, containment and relations remain ordinary records through the
  canonical generic CRUD routers; no per-object lifecycle or nested workspace-draft CRUD resources
  exist.

- Database migration failures now produce a credential-safe operator message with the current and
  target revisions, recovery command, backup requirement and escalation details. Startup enters
  maintenance mode without a traceback, and the WP4 migration safely retries recognized empty SQLite
  DDL left by an interrupted attempt. Real-database startup, restart and interruption regression tests
  cover the failure that previously left the development application unable to boot.

- Base 0.6 authoritative runtime-object revisions. Stable logical objects now own model-pinned,
  optimistic drafts and immutable active/retired snapshots with separate derivation and supersession
  lineage. Root and historical drafts, explicit activation, cursor-paged history, retired discovery,
  direct retirement and ownership-cascade retirement are public API contracts. Activation publishes
  core fields, typed attributes, containment and required relationships atomically; independent
  associations and published identity survive retirement. The Alembic transition preserves object
  UUIDs, migrates known active/draft/retired rows and rejects unknown legacy states with counts.
  Post-implementation hardening conditionally claims the final draft version during activation,
  prevents compatibility adapters from drifting the lifecycle projection and rejects corrupt
  cross-workspace retirement graphs.
  This pre-release design was subsequently rejected as the wrong publication boundary. ADR-024 and
  corrective WP5 froze workspace-level journeys, fixtures and API design; WP6 supplied the corrected
  persistence, WP7 restored generic CRUD and WP8 completed workspace orchestration, with WP9-WP10
  delivering the UI and release validation. These object-lifecycle APIs are not a compatibility
  commitment.

- Frontend lint and format tooling: ESLint 10 with `typescript-eslint` and
  `eslint-plugin-react-hooks`, and Prettier. `AGENTS.md` listed "linting passes" in the definition
  of done, but the frontend had no linter. Dependencies are pinned instead of `"latest"`, build
  tooling moves to `devDependencies`, and the Dockerfile uses `npm ci`; TypeScript is pinned to 6.x
  because `typescript-eslint` cannot yet parse with the TypeScript 7 native compiler.

- An application-level smoke test covering the extracted router: model-driven shell rendering, deep
  collection URLs, fallback when a URL names a retired application, and returning from an object to
  the collection and workspace it was opened from.

### Fixed

- A detail panel naming an object type that a later release retired now reports it instead of
  crashing the detail screen through a non-null assertion.
- Modals restore focus to their opener even when a form field uses `autoFocus`; cursor feeds ignore
  late load-more responses after their query changes or reloads; and cancelling a failed relationship
  deletion clears its action-specific error without blocking relation paging.

## [0.5.0] - 2026-09-05

### Added

- A global model workbench with always-readable installed releases and capability-gated JSON draft
  creation/import/editing, validation diagnostics, canonical compilation, semantic comparison,
  browser export, immutable installation and guarded activation. Optimistic conflicts preserve local
  input, and mutation controls remain absent by default.

- Base 0.5 generic object-management UI. Workspace context is explicit in the app shell and URLs;
  collection search, repeatable state filters, built-in sorting and page size survive browser
  navigation; generic rows expose existing edit/delete semantics; failed collections, panels and
  lookups are retryable; and object details show bounded, incrementally loaded audit history.

- Base 0.5 object and relation query foundations. Object collections now support repeatable state
  filters and stable built-in sorting through signed, filter-bound keyset cursors. Relation expansion
  is a bounded workspace-checked page, and object history uses an indexed audit-subject projection to
  include object, attribute and connected-relation events without exposing internal sequences or full
  before/after payloads.

- Base 0.5 guarded model activation. Compatible installed releases can be selected with both expected
  runtime version and active-release tokens; incompatible runtime data and stale selections return
  structured conflicts. Activation commits before refreshing the process registry, records old/new
  release IDs and hashes, marks health unhealthy on refresh failure, and rejects mutation enablement
  when `WEB_CONCURRENCY` configures multiple workers.

- Base 0.5 persisted model drafts and immutable installation. Mutation-gated draft APIs support
  optimistic version claims, side-effect-free compilation and atomic content-addressed installation;
  lifecycle audit events retain hashes and identities without copying complete model JSON. The
  capabilities endpoint reports the effective read, draft, installation and activation surface.

- Base 0.5 model compilation and comparison: inline validation returns stable diagnostic codes and
  JSON Pointer paths; installed releases can be compared by semantic, key-based paths; and bounded
  runtime-data checks classify candidates as compatible or migration-required without persisting or
  activating content.

- Base 0.5 model runtime authority: a singleton, versioned database row selects the active immutable
  release; source JSON is bootstrap input only. Requests resolve one cached model/release snapshot,
  `GET /api/v1/model` exposes its hash and release UUID in response headers, and cursor-paged release
  catalogue/detail APIs expose installed snapshots without enabling mutations.

- Complete model-driven Translation CRUD. Translations contain optional translated name, description
  and value fields (with at least one required), belong to a Translation Group, and atomically bind to
  exactly one configured target object. Domain, Codelist and Master Value targets are enabled in the
  starter model; future target types require only another JSON allowed pair. Duplicate active
  target/Language translations are rejected, inactive historical records may coexist, required
  bindings cannot be unlinked, and owner cascade deletes the Translation.

- Optional, model-driven Domain/Codelist-to-System Value representation relationships. Domain and
  Codelist details expose outgoing representations, while System Value details expose their incoming
  reference structures. These associations do not alter system containment and cascade deletion only
  unlinks them. System Value relation tables show the containing System through a generic ancestor
  column and can omit their constant relationship-label column.

- Optional transactional cascade deletion for runtime objects. A non-cascade delete with dependencies
  now returns a structured, non-mutating impact report; the UI renders the affected child objects,
  PK/FK dependents and relationships before allowing explicit cascade confirmation. Cascades delete
  containment descendants, unlink independent relationships and follow directed, required
  single-valued bindings from owner to dependent.

- Model-driven runtime CRUD in the React UI: object create/edit/delete, individual attribute-value
  add/edit/remove, and direction-aware relationship create/edit/delete. Relationship choices come from
  configured panels and allowed object-type triples; candidate lookup is server-side and can cross
  application boundaries within a workspace. Engine-maintained containment edges remain visible but
  immutable.
- A structured frontend `ApiError`, shared typed field renderer, paged object lookup and accessible
  destructive confirmation dialog. Optimistic-concurrency, dependency, uniqueness and cardinality
  failures remain recoverable in their active UI context.

- Standalone object-scoped CRUD for attribute values:
  `GET`/`POST`/`PATCH`/`DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`.
  A single stored value can now be read, set, updated or removed without rewriting the whole object.
  Mutations require the object's `expectedVersion`, return the full object response, and enforce the
  same validation, read-only/required and workspace-uniqueness rules as object writes. Deleting a value
  on a required or read-only attribute is rejected (`422 cannot_delete_required_attribute` /
  `read_only_attributes`).
- Read-one, update and delete for relation instances:
  `GET`/`PATCH`/`DELETE /api/v1/relations/{relationId}`. `PATCH` replaces relation `attributes`
  (relation identity is immutable) and, like `DELETE`, claims an atomic `expectedVersion`
  (`409 version_conflict` on a stale claim). Engine-maintained parent-containment and hierarchy
  relations — those named in the target object type's `behavior.parentRelationTypeKeys` — are rejected
  for direct create/update/delete with `422 immutable_relation`; they stay atomic through object parent
  operations.
- Workspace-scoped attribute uniqueness for attribute types that declare `features.unique`. Create and
  update now reject a colliding value with `409 duplicate_attribute_value`. Uniqueness is enforced per
  attribute type within a workspace, and declaring `unique` on a `json` value type is rejected at model
  load.
- Frontend unit-test setup (Vitest + Testing Library) covering the model helpers and the generic
  renderers with two object types, run locally and in CI via `npm test`.

### Changed

- The bundled starter content release is now `0.5.0`; its model-language `schemaVersion` remains
  `0.4` because Base 0.5 did not change the declarative schema contract. Existing databases retain
  their database-selected active release until an administrator deliberately activates another
  installed release.
- Release operations now have documented backup and rollback boundaries: back up before migrations,
  use activation for compatible model-content rollback, and restore the matching database backup for
  application/schema rollback rather than editing immutable releases or relying on Alembic downgrade.

- Hardened the Base 0.5 WP2/WP3 lifecycle foundation after review: compatibility checks now include
  numeric relation attributes and enforce cardinality across every allowed pair sharing a relation
  type; compiler diagnostics retain stable paths for top-level validation failures; semantic diffs
  preserve real JSON `null` values and ignore ordering in set-like key collections; and concurrent
  installations are serialized in the supported single-process administration topology.

- Metadata collection endpoints now use opaque cursor pagination with a documented page-size limit.
- Attribute-value response items now include their stable public UUID `id`.
- Relation `fromObjectId`/`toObjectId` and object `parentObjectId` are now validated as UUID v4,
  returning `422 request_validation_error` for non-UUID values.
- Alembic migrations are now the single source of schema truth: the initial migration provisions a new
  database and upgrades an existing one, and startup no longer runs `create_all`.
- Object ancestor paths are resolved in level order (one query per depth level) instead of one query per
  object, removing the N+1 traversal on collections.
- Developer tooling: `.python-version` pins Python 3.12, and generated `*.egg-info`/`*.tsbuildinfo`
  artifacts are removed from version control.

### Fixed

- Model release snapshots are recursively immutable, metadata and release cursors are signed and
  filter-bound, model ETags use valid quoted entity-tag syntax, and release timestamps are normalized
  to UTC even when SQLite returns naive datetimes.
- Relation create and update now reject attributes not declared by the matched allowed pair and
  validate declared values through their global attribute types before persistence.
- Duplicate many-to-many edges supplied through atomic object `initialRelations` now return
  `409 duplicate_relation` and roll back the new object instead of escaping as an internal error.
- The initial Alembic revision now owns a frozen schema snapshot rather than importing live ORM
  metadata, keeping fresh-database upgrades reproducible as later revisions are added.
- Object creation preserves `false` for optional boolean attributes without a configured default
  instead of treating that value as absent.
- Object and standalone attribute-value writes now share an atomic expected-version claim, preventing
  concurrent requests from accepting the same object version and silently overwriting one another.
- Standalone attribute-value `GET` responses now include `objectVersion`, allowing clients to obtain
  the concurrency token required by `POST`, `PATCH` and `DELETE` without fetching the full object.
- Objects that have a parent can now be deleted. Deleting such an object removes its parent containment
  relation atomically, while objects with child objects or non-parent relations (mappings, translations)
  still return `409 object_has_dependents`.
- Partial updates no longer let a required attribute be cleared. Providing a required attribute as
  `null` or empty in a `PATCH` returns `422 missing_required_attributes`; omitting it remains allowed.
- `validation.minimum`/`maximum` on a non-numeric attribute type no longer causes a server error. These
  bounds now apply only to `integer`/`decimal`; non-numeric, non-finite, inverted or misplaced bounds
  are rejected at model load.
- The object form's parent picker now pages through all candidate parents instead of truncating at the
  first page, so a parent beyond the first page is no longer silently lost when editing.

## [0.3.0] - 2026-09-02

Baseline executable vertical slice of the generic reference-data engine: the versioned JSON model
(schema 0.3) as the source of truth for applications, object types, global attribute types, relation
types, allowed object-type triples and UI views, with a FastAPI backend, immutable model releases,
typed attribute storage, cursor-paginated APIs and a generic React UI.
