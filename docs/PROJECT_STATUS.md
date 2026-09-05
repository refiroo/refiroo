# Project status

## Current baseline

Model release `0.5.0` is the completed operational base of a generic reference-data engine. The
versioned JSON model is the source of truth for applications, global attribute types, object types and
bindings, relation types, allowed source/relation/target triples and UI views.

The starter model contains three configurable applications—RDM Master, RDM Systems and RDM
Translations—but the runtime contains no branches for those names or their object-type keys.

Base 0.5 is complete. The singleton database runtime-state row selects the authoritative installed
release, and source JSON remains bootstrap input only. Each request uses one immutable model and
metadata snapshot. Read-only release APIs now include key-based semantic diff and bounded runtime-data
compatibility analysis, while inline model validation returns stable JSON-path diagnostics without
persistence side effects. Mutation-gated, versioned drafts can be edited and compiled, then installed
atomically as inactive immutable releases without changing the active runtime selection.
Guarded activation reparses and compatibility-checks installed candidates transactionally, claims the
runtime state with both concurrency tokens, commits before refreshing the local registry and makes
readiness unhealthy if publication fails. Activation is available only in the supported single-worker
mutation topology.
Object collections use signed, filter-bound keyset cursors with repeatable state filters and built-in
sorting. Relation expansion and object audit history are cursor-paged and workspace-bound; an indexed
audit-subject projection connects object, attribute and relation events without querying JSON payloads
for identity.
The generic UI carries explicit workspace context in its shell and routes, restores URL-backed
collection search/state/sort/page-size controls, provides reusable row actions and retry states, and
shows independently paged relation expansion and audit history on object details.
The frontend has since had a structural pass, phases 0–4 of
`docs/FRONTEND_STRUCTURE_REFACTOR.md`, ahead of the Base 0.6 UI work. It changed no API contract,
model contract or architecture: `frontend/src` is organized into `app/`, `features/`, `ui/`,
`model/`, `routing/`, `lib/`, `types/` and `styles/`; cursor paging, search debouncing and API error
handling each have one implementation; and the frontend has lint and format tooling for the first
time, which the definition of done had always required. Phase 5 followed: every dialog now shares
one modal shell in `frontend/src/ui/Modal.tsx`, with Escape, focus restore, a focus trap and a
scroll lock applied consistently. Base 0.6 WP1 then moved those difficult overlay mechanics behind
the RDM-owned React Aria boundary, added exact Lucide and React Aria dependency locks, enforced the
feature-import boundary in ESLint, and established semantic selection, menu, notice, dialog, tab and
icon wrappers with documented plain-CSS tokens. The shell now distinguishes product, workspace,
application, view and object-type context, provides a skip link and labelled narrow-layout
navigation, and keeps native table semantics in a labelled scroll region. Phase 6 remains as
implementation work governed by accepted ADR-021.

The global Models workbench keeps installed releases readable when administration mutations are
disabled. When enabled, it supports JSON draft creation/import/editing, authoritative validation,
optimistic-conflict recovery, canonical compilation, semantic diff and compatibility review, browser
export, immutable installation and guarded activation without starter-model key branches.

## Source evidence incorporated

The supplied RDM application package declares 3 applications, 23 object types, 27 attribute types, 72
relation types and 55 allowed object-type relations. The accompanying API examples show:

- object-type metadata with features and attribute bindings;
- a custom-overview query that asks for numeric attribute and relation IDs;
- a relation-type catalogue declaring 201 entries, with 20 complete entries in the captured excerpt;
- forward/reverse relation names, orientation and typed relation features; and
- separate runtime retrieval for the Master and Translation applications.

The engine keeps the useful object–attribute–relation separation and configurable applications. It
intentionally replaces numeric integration IDs, unbounded `take: 0` queries and UI-coupled endpoint
configuration with stable keys, explicit schemas, cursor pagination and resource APIs.

## Implemented

- `model/rdm-starter.json`: schema-language 0.4 model with 22 attributes, 9 object types, 13 relation
  types, 16 allowed triples, three applications, collection views and typed detail compositions. Domain
  and Codelist objects can have optional System Value representations without joining the independent
  system containment hierarchy.
- Translation objects support translated name, description and value content, are contained by a
  Translation Group, and have exactly one required target chosen from every explicitly configured
  translatable Master object type. Active Target and Language combinations are unique.
- `backend/app/models/schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/services/model/compiler.py`, `model/diff.py` and `model/compatibility.py`:
  side-effect-free canonical compilation, stable JSON-path diagnostics, key-based structural diff and
  bounded runtime-data compatibility checks exposed through validation and release-diff APIs.
  Compatibility covers object and relation attribute constraints and relation-type-wide cardinality;
  diffs distinguish JSON null from omission and ignore ordering for set-like stable-key memberships.
- `backend/app/services/model/drafts.py`, `model/releases.py` and the model-management router:
  persisted draft CRUD with optimistic concurrency, side-effect-free draft compilation and atomic,
  idempotent immutable installation serialized across drafts in the supported single-process
  topology. Complete model JSON is excluded from lifecycle audit payloads, and all write routes are
  absent unless model administration mutations are enabled.
- Guarded release activation with runtime-data compatibility diagnostics, dual-token optimistic
  concurrency, old/new release audit identities and hashes, post-commit registry refresh, unhealthy
  readiness on publication failure and startup rejection of configured multi-worker mutation mode.
- `backend/app/models/database.py` and `backend/app/db.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations and audit events.
- `backend/app/services/attributes.py`: attribute validation, defaults and typed persistence conversion.
- `backend/app/routers` and `backend/app/services`: metadata discovery, generic object CRUD,
  search/cursors, concurrency checks, hierarchy maintenance, relation instance CRUD
  (create/read-one/update/delete) with optimistic concurrency, cardinality checks and model-declared,
  typed relation attributes — engine-maintained
  parent-containment relations are read-only through the relations API; object-scoped attribute-value
  endpoints
  (`GET`/`POST`/`PATCH`/`DELETE` on `/objects/{type}/{id}/attributes/{attributeTypeKey}`) set, read,
  update and delete single stored values with the same validation, uniqueness and object-version
  concurrency as object writes. Standalone reads expose the current object version, and mutations
  atomically claim that version before writing; `backend/app/main.py` contains application assembly
  only.
- Workspace-scoped attribute uniqueness for `features.unique` (`409 duplicate_attribute_value`) and
  transactional object deletion with a structured dependency preview and explicit cascade option.
  Cascade recursively deletes containment descendants, unlinks independent associations, and follows
  directed required single-valued PK→FK bindings to dependent objects.
- `backend/app/migrations`: versioned Alembic database migrations are the single source of schema truth;
  the initial migration provisions new databases and upgrades existing ones, and startup runs only
  `alembic upgrade head`.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  workspace-explicit routes, view and panel component registries, URL-backed searchable/filterable/
  sortable cursor-paged collections, composable object details and
  full runtime CRUD for objects, individual typed attribute values and mutable relationships. Relation
  creation derives valid endpoint types and direction from the loaded model, uses cross-application
  server-side lookup, and keeps engine-managed containment edges read-only.
  Generic collection rows support open/edit/delete, failed collection and lookup requests remain
  retryable errors, and object details expose cursor-paged audit history. Required non-parent bindings
  are selected in the generated object form and created atomically with
  the new object and its containment relation.
- The global model workbench provides release inspection and structured model summaries in read-only
  deployments, and capability-gated JSON draft, validation, diff, installation and activation flows in
  the supported model-administration topology.
- Tests cover model validation and a Domain → Codelist containment flow including the generated typed
  relation, search/cursor behavior, update concurrency and deletion behavior. Composition tests mutate
  panel order, visibility, fields and relation-table configuration without renderer changes. Frontend
  unit tests (Vitest + Testing Library) exercise the model helpers and generic renderers with two
  object types. Frontend adapter and helper tests also cover typed field conversion, structured API
  errors, cross-application lookup queries and incoming/outgoing relationship derivation.

## Important design decisions

- Global attribute definitions and object-type bindings are separate.
- Relation definitions and permitted object-type triples are separate.
- Containment stores both an indexed parent ID and a semantic typed relation, updated atomically.
- Attribute values use typed columns rather than a single string or opaque JSON value.
- Model releases are immutable; a changed definition requires a new release key/version.
- Vendor exports and their numeric IDs are source research, not distributable runtime dependencies.

See `docs/DECISIONS.md` for the durable decisions and `AGENTS.md` for coding invariants.

## Known gaps

- The Base 0.5 workspace selector accepts a raw workspace key because no authoritative workspace
  catalogue exists yet. Base 0.6 plans bounded workspace discovery and a catalogue-backed selector;
  ADR-019 now fixes its authority, administration, default selection and unknown/retired behavior.
- Object management is functionally complete but fragmented: the main edit dialog changes core fields
  and parent while stored attributes are managed through separate detail-panel actions. Runtime object
  state and state filtering still use unconstrained text in Base 0.5. ADR-020 now defines the Base 0.6
  replacement: stable logical objects, immutable active/retired revisions, editable derived drafts,
  atomic activation, direct retirement without replacement, retired discovery and visible
  derivation/supersession lineage.
- Configured `mappingGrid`, `tree`, `form` and `dashboard` views still resolve through the registry to
  the generic collection renderer. Their `config` remains an open property bag, so declared semantic
  views are not yet guaranteed to have distinct validated behavior. ADR-021 defines the Base 0.6
  replacement: a strict schema 0.5 table contract, rejection of unimplemented view types and no
  schema 0.4 runtime adapter. `mappingGrid` moves to schema 0.6/product 0.7. The registry now lives in
  `frontend/src/features/objects/views/registry.ts`, where that decision is implemented rather than
  inside the collection screen.
- Model-declared `filterable` and `sortable` attribute features are not implemented in object queries;
  collection controls cover search, free-text state and built-in sorts only.
- The UI has component-level regression coverage but no browser-level workflow, automated
  accessibility or visual-regression release gate. WP1 now provides the documented RDM token and
  semantic-wrapper foundation, but broader adoption and real-browser proof remain release work rather
  than a claim that component primitives alone complete accessibility.
- Dialog keyboard behavior is now consistent through the shared `ui/Modal` shell, but it has only
  been exercised in jsdom. Nothing has driven a real browser or a screen reader; Base 0.6 WP6 owns
  that gate.
- The model lifecycle is complete, but its workbench remains a plain JSON-centred interface. Its
  broader usability redesign is deferred beyond Base 0.6 so runtime-object revisions stay bounded.
- Relations support full instance CRUD (create/read-one/update/delete with optimistic concurrency);
  bulk relation endpoints remain.
- Attribute uniqueness is enforced at the service layer; a database-level unique constraint/index
  remains before multi-writer PostgreSQL deployment.
- Ancestor-scoped relationship uniqueness is enforced transactionally by the service layer; database
  hardening remains for multi-writer PostgreSQL deployment.
- Integration-grade filtering, sorting, bulk upsert, imports/exports, change feeds and webhooks remain.
- OIDC, permissions and PostgreSQL performance/index work remain.
- The starter model is representative, not a one-to-one migration of every supplied source type.

## Next vertical slice

Product release 0.6 now has its bounded versioned-daily-operations interaction baseline in
`docs/BASE_0_6_INTERACTION_SPEC.md` and reusable J1-J7 data in
`frontend/src/test/base06AcceptanceFixtures.ts`. That baseline has been independently reviewed and is
the accepted interaction contract for the following work packages. Mapping remains the next
specialist release, after workspace selection, typed tables and authoritative runtime-object
revisions are proven.

Base 0.5 delivered:

1. **Done (WP1):** Make the database-selected installed release the single authoritative runtime
   model snapshot.
2. **Done (WP2):** Add validation, canonical compilation, semantic diff and runtime-data compatibility
   analysis.
3. **Done (WP3):** Add versioned drafts and immutable installation.
4. **Done (WP4):** Add guarded, compatibility-checked activation.
5. **Done (WP5):** Add signed built-in sorting, cursor-paged relation expansion and cursor-paged object
   audit history.
6. **Done (WP6):** Make workspace and URL-backed collection state explicit in the generic object UI,
   including sort, state and page-size controls and the history panel.
7. **Done (WP7):** Add the lightweight JSON model workbench, with model mutations disabled by default.
8. **Done (WP8):** Promote the starter content release to 0.5, complete release integration,
   operational documentation, migration/package verification and the locked OpenAPI error contract.

See `docs/BASE_0_5_IMPLEMENTATION_PLAN.md` for the completed historical work packages,
`docs/BASE_0_6_IMPLEMENTATION_PLAN.md` for the next implementation-ready handoff, `docs/TODO.md` for
the active delivery queue and `docs/ROADMAP.md` for the release exit gate and later milestones.

All Base 0.5 work packages and exit gates are complete. D1 through D5 are accepted. The Base 0.6 WP0
interaction baseline and WP1 UI foundation are complete. WP2 workspace authority is next, followed by
schema 0.5 typed tables, authoritative object revisions, lifecycle UI and release gates. Core mapping
is product 0.7 and bulk mapping remains in the later integration milestone.

## Coding-agent handoff

Open the repository root, then start a new coding chat with:

> Read `AGENTS.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/UI_MODEL.md`,
> `docs/BASE_0_6_IMPLEMENTATION_PLAN.md` and `docs/BASE_0_6_INTERACTION_SPEC.md`. Review the WP0
> accepted WP0 interaction baseline and its frontend acceptance fixtures, then execute Base 0.6 WP1
> only. Do not pull deferred mapping or model-workbench redesign into Base 0.6.
> Preserve all product invariants and report the current worktree status before editing.

Make a Git checkpoint before the first new slice. Run
`backend/.venv/bin/python -m ruff check backend`,
`backend/.venv/bin/python -m pytest backend/tests -q`, `npm --prefix frontend run lint`,
`npm --prefix frontend test`, `npm --prefix frontend run build` and `git diff --check` before
considering it complete. The frontend lint step is new; it must report zero errors. Base 0.6
release validation must also include its browser, accessibility and visual-regression suites and must
run on the supported Python 3.12 toolchain; the local review environment used on 2026-09-05 was Python
3.14.7 and is not sufficient as the only release environment.
