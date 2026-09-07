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
WP6 removes the rejected per-object lifecycle persistence and public mutation surface while retaining
workspace drafts and immutable workspace revisions. Corrective WP7 restores the established generic
object, attribute, relation and translation CRUD over WP6 storage. Workspace draft/revision discovery,
validation, guarded atomic publication and publication retirement remain separate workspace operations.
Active reads resolve through the selected workspace revision; writes use the same CRUD contract against
an explicit workspace draft; published and historical revisions remain immutable.
Audit-subject projection remains cursor-paged and workspace-bound without querying JSON payloads for identity.
The generic UI carries explicit workspace context in its shell and routes, restores URL-backed
collection search/sort/page-size controls, provides reusable row actions and retry states, and
shows independently paged relation expansion and audit history on object details.
The global workspace catalogue is now authoritative: a singleton, concurrency-protected state selects
the active default; discovery is searchable and cursor-paged; unknown explicit keys fail; and retired
workspaces remain readable while rejecting object, attribute and relation mutations. The shell uses
catalogue labels and keeps stable keys in URLs instead of accepting free-text authority.
Schema 0.5 is now the only runnable model language. It provides an extra-forbidden typed table
contract, rejects unimplemented semantic view types, and drives model-aware typed filters, attribute
sorts and URL-stable cursor paging. Historical schema 0.4 releases remain inspectable, while fresh
bootstrap and the offline `python -m app.cli.model_schema_upgrade --model <path>` transition establish
the schema 0.5 runtime selection. The starter is content release 0.6.0; its former tree is represented
honestly as a table and its mapping view is deferred to schema 0.6.
Base 0.6 WP4 implemented authoritative per-object revisions, but that publication boundary has been
rejected before release. ADR-024 supersedes ADR-020: the workspace is the publication aggregate, and
objects, attributes, containment and relations are records inside mutable workspace drafts and
immutable workspace revisions. The historical WP4 schema is migration input only; its object
lifecycle tables, pointers and APIs are removed after successful corrective conversion.
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

- `model/rdm-starter.json`: schema-language 0.5/content-release 0.6.0 model with 22 attributes, 9 object
  types, 13 relation types, 16 allowed triples, three applications, collection views and typed detail compositions. Domain
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
- The Base 0.5/pre-WP6 `backend/app/routers` and `backend/app/services` implementation established
  generic object CRUD, search/cursors, concurrency checks, hierarchy maintenance and relation instance
  CRUD (create/read-one/update/delete) with optimistic concurrency, cardinality checks and
  model-declared typed relation attributes. WP6 removed these public mutation routes before their
  workspace-backed replacements existed; WP7 must recover their behavior selectively from Git history.
  Engine-maintained parent-containment relations remain read-only through the relation API. The
  established object-scoped attribute-value endpoints
  (`GET`/`POST`/`PATCH`/`DELETE` on `/objects/{type}/{id}/attributes/{attributeTypeKey}`) set, read,
  update and delete single stored values with the same validation, uniqueness and object-version
  concurrency as object writes. Standalone reads expose the current object version, and mutations
  atomically claim that version before writing; `backend/app/main.py` contains application assembly
  only.
- Git history retains workspace-scoped attribute uniqueness and transactional object deletion with
  dependency preview/cascade behavior. WP7 restores those generic semantics in the selected workspace
  draft, but must not restore the rejected WP4 lifecycle routes, tables or publication behavior.
- `backend/app/migrations`: versioned Alembic database migrations are the single source of schema truth;
  the initial migration provisions new databases and upgrades existing ones, and startup runs only
  `alembic upgrade head`. The environment-aware `app.cli.database_upgrade` command and startup
  boundary turn failures into actionable, credential-safe operator messages without tracebacks. The
  WP4 migration recovers only recognized empty SQLite DDL from an interrupted attempt and refuses
  unsafe cleanup. Startup regression coverage now exercises clean boot, restart, preceding-revision
  upgrade, interrupted-DDL recovery and maintenance-mode refusal against real temporary databases.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  workspace-explicit routes, view and panel component registries, URL-backed searchable/filterable/
  sortable cursor-paged collections, composable object details and cursor-paged audit history.
  Workspace lifecycle UI is not yet complete. Generic object, attribute, relation and translation
  controls must be restored and reused inside a selected workspace draft; failed collection and lookup
  reads remain retryable, while genuinely empty relationship/translation collections render as empty
  states and engine-maintained containment edges remain read-only.
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

- WP7 backend corrective work is complete: generic CRUD is draft-scoped, draft/revision query and
  history contexts are cursor-bound, and no nested draft-object/relation API exists. WP8 owns workspace
  lifecycle orchestration, WP9 reuses generic CRUD UI in draft context, and WP10 owns integration/release
  validation.
- Schema 0.5 intentionally omits `mappingGrid`, `tree`, `form` and `dashboard`; those declarations are
  rejected rather than routed to the table renderer. `mappingGrid` moves to schema 0.6/product 0.7.
- Typed table filtering and sorting cover the bounded daily-use grammar. Integration-scale query
  expressions, relation-expanded filtering and multi-sort remain deferred.
- The UI has component-level regression coverage but no browser-level workflow, automated
  accessibility or visual-regression release checks. WP1 now provides the documented RDM token and
  semantic-wrapper foundation, but broader adoption and real-browser proof remain release work rather
  than a claim that component primitives alone complete accessibility.
- Dialog keyboard behavior is now consistent through the shared `ui/Modal` shell, but it has only
  been exercised in jsdom. Nothing has driven a real browser or a screen reader; Base 0.6 WP10 owns
  those checks.
- The model lifecycle is complete, but its workbench remains a plain JSON-centred interface. Its
  broader usability redesign is deferred beyond Base 0.6 so the corrective workspace lifecycle stays bounded.
- The established relation CRUD implementation supports create/read-one/update/delete with optimistic
  concurrency, but WP6 removed its public routes. WP7 must restore that behavior over workspace-backed
  storage; bulk relation endpoints remain later work.
- Attribute uniqueness is enforced at the service layer; a database-level unique constraint/index
  remains before multi-writer PostgreSQL deployment.
- Ancestor-scoped relationship uniqueness is enforced transactionally by the service layer; database
  hardening remains for multi-writer PostgreSQL deployment.
- Integration-grade filtering, sorting, bulk upsert, imports/exports, change feeds and webhooks remain.
- OIDC, permissions and PostgreSQL performance/index work remain.
- The starter model is representative, not a one-to-one migration of every supplied source type.

## Next vertical slice

Product release 0.6 retains the workspace-navigation, typed-table, responsive, keyboard, focus and
action-hierarchy findings from `docs/BASE_0_6_INTERACTION_SPEC.md`. The immediate next slice is WP7:
recover and re-enable generic object, attribute, relation and translation CRUD against WP6 workspace
storage. WP8 then completes workspace lifecycle orchestration, WP9 restores/reuses the generic CRUD UI
inside draft context, and WP10 performs real integration and release validation. Mapping remains the
next specialist release after Base 0.6 is proven.

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
the active delivery queue and `docs/ROADMAP.md` for the release criteria and later milestones.

All Base 0.5 work packages and acceptance criteria are complete. Base 0.6 WP1 UI foundation, WP2
workspace authority, WP3 typed tables, WP5 workspace contract and WP6 workspace persistence remain
complete. The delivered WP4 object-revision design is rejected and must not be extended. WP7 is the
current recovery slice; WP8-WP10 complete workspace lifecycle, generic CRUD UI integration and release
checks. Core mapping is product 0.7 and bulk mapping remains in the later integration milestone.

## Coding-agent handoff

Open the repository root, then start a new coding chat with:

> Read `AGENTS.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/UI_MODEL.md`,
> `docs/BASE_0_6_IMPLEMENTATION_PLAN.md` and `docs/BASE_0_6_INTERACTION_SPEC.md`. Review the
> completed WP1-WP3, retained WP5 contract and WP6 workspace persistence. Execute WP7 as a recovery
> slice: use `a3ead41^` to locate deleted backend CRUD and use `41aa7e7^` only as a source for
> individual generic frontend controls because that tree also contains rejected lifecycle UI. Recover
> object/attribute/relation/translation behavior selectively, exclude object lifecycle, and resolve it
> against workspace drafts/revisions without
> introducing nested draft CRUD resources. Then proceed to WP8-WP10 in order. Preserve all product
> invariants and report the current worktree status before editing.

Make a Git checkpoint before the first new slice. Run
`backend/.venv/bin/python -m ruff check backend`,
`backend/.venv/bin/python -m pytest backend/tests -q`, `npm --prefix frontend run lint`,
`npm --prefix frontend test`, `npm --prefix frontend run build` and `git diff --check` before
considering it complete. The frontend lint step is new; it must report zero errors. Base 0.6
release validation must also include its browser, accessibility and visual-regression suites and must
run on the supported Python 3.14 toolchain.
