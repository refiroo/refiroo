# Base 0.6 implementation plan

**Status:** Planned  
**Target:** Product release 0.6.0  
**Scope:** Usable daily operations and the core relation-driven mapping workflow  
**Depends on:** Completed Base 0.5 operational and model-lifecycle foundation  
**Unlocks:** Translation, hierarchy, integration-scale bulk operations and later structured model
authoring

## Product outcome

Base 0.6 turns the technically complete Base 0.5 into a coherent daily-use product. A data steward can
select a known workspace, find and filter records, create or edit a complete object, understand
validation and concurrency failures, and manage mappings without navigating through low-level relation
screens. A model administrator can understand and operate the existing draft-to-activation lifecycle
through a clearer workbench.

The release combines a bounded usability foundation with one high-value specialist workflow. It must
not become either an unbounded visual redesign or a mapping screen built on interaction patterns known
to be incomplete.

## Release principles

1. Design and test complete user tasks, not isolated components.
2. Preserve the generic model boundary: no starter application, object-type or relation keys in
   runtime or UI branches.
3. Do not add a second object, relation or model lifecycle contract when the Base 0.5 contract can be
   composed safely.
4. A declared view type must have typed, validated semantics. The UI must not silently present a
   different semantic view under the requested view-type label.
5. Browser import/export and database drafts remain the model document boundary. Do not add arbitrary
   server-filesystem read/write operations.
6. Keep every collection bounded, every write concurrency-aware and every error machine-readable.
7. Product release numbers and model-language versions are separate. Increment `schemaVersion` only
   when the declarative model contract changes.

## Scope

### Included

- Task-based usability baseline and acceptance scenarios
- A deliberate visual and interaction foundation for the React UI
- Authoritative workspace catalogue and accessible workspace selection
- Typed table and mapping-grid view configuration
- Model-aware filtering and sorting needed for daily table and mapping work
- Unified create/edit object experience, including attributes and required relationships
- Controlled object-state interaction after its authority is decided
- Model-workbench usability improvements using the existing lifecycle APIs
- Cursor-paged mapping coverage, candidate lookup, create/remove/atomic replace and audit
- Browser-level workflow, accessibility and visual-regression coverage

### Deferred

- Bulk object mutation and bounded bulk mapping
- Translation matrix and dedicated hierarchy tree
- Asynchronous import/export jobs, change feeds and webhooks
- OIDC, authorization and multi-node model publication
- Executable runtime-data migration plans
- Full structured or graphical model designer
- Extension packaging or reusable model modules

Bulk mapping moves to the integration and bulk milestone unless usability evidence demonstrates that
the core mapping workflow cannot be used effectively without it.

## Decisions required before implementation

Record durable outcomes in `docs/DECISIONS.md` before implementing dependent work.

### D1 — Workspace authority and lifecycle

Define who provisions workspaces, their stable key and label, how a default is selected, whether
retired workspaces remain readable, and how unknown keys behave. The catalogue must be first-class
persistence and must not be inferred from object rows.

### D2 — Runtime object-state authority

Choose a typed source for allowed object states and their presentation. The UI must not retain an
unconstrained text field accidentally. If state becomes model-declared, define compatibility behavior
for existing stored values and validate references before consuming the configuration.

### D3 — Typed view contracts and compatibility

Replace the open `ViewDefinition.config` bag for implemented views with discriminated table and
mapping-grid definitions. Decide how older schema 0.4 releases are parsed and how declared but
unimplemented `form`, `dashboard` and `tree` views are represented without misleading users.

### D4 — Mapping replacement concurrency

Define one atomic service operation that changes the selected mapping only when the expected source or
relation version still matches. Deleting one relation and creating another in separate browser calls
is not an acceptable replacement contract.

### D5 — UI foundation ownership

Decide whether the project owns a small internal component system or adopts a focused accessible
primitive library. In either case, model configuration selects semantic components and never embeds
markup, pixels or backend routes.

## User journeys used as acceptance scenarios

Use realistic, non-trivial data in at least two object types and two relation configurations.

1. Select a non-default workspace, move between applications and return without losing context.
2. Find an object using a configured attribute filter and sort, open it and return to the same list
   state.
3. Create a contained object with typed attributes and a required non-parent relation in one flow.
4. Edit an existing object's core fields, parent and attributes without visiting separate edit modes.
5. Recover from an object-version conflict without losing local input.
6. Find unmapped source values, select a target, remove a mapping and safely replace a mapping.
7. Create a permitted target from the mapping task and select it without object-specific form logic.
8. Inspect a model draft, resolve diagnostics, compare it with its base or the active release, install
   it and understand that activation is separate.

## Work packages

### WP0 — Establish the usability baseline and interaction specification

Primary files:

- `docs/UI_MODEL.md`
- focused usability notes or fixtures under `docs/`
- frontend test fixtures

Tasks:

1. Walk the eight acceptance journeys against Base 0.5 and record task failures, unnecessary context
   switches, unclear terminology and accessibility problems.
2. Define the information architecture for product, application, view, workspace and object context.
3. Produce low-fidelity states for collection, complete object editing, mapping and model lifecycle.
4. Define a readable typography scale, density targets, action hierarchy and responsive behavior.
5. Agree D1 through D5 before their dependent implementation begins.

Exit: the new interaction model is reviewable independently of color and styling, and the release has
observable task-based acceptance criteria.

### WP1 — Build the UI foundation and application shell

Primary files:

- `frontend/src/App.tsx`
- `frontend/src/styles.css`, split into focused modules if useful
- new reusable primitives under `frontend/src/components/ui/`
- shell and accessibility tests

Tasks:

1. Implement tokens for typography, spacing, color, borders, focus and density; replace very small
   uppercase metadata and decorative pills where they do not communicate useful state.
2. Introduce consistent buttons, fields, menus, notices, loading/empty states, dialogs and drawers.
3. Use an intentional icon set with accessible names rather than unrelated text glyphs.
4. Simplify navigation so application, view, workspace and contextual exploration have distinct roles.
5. Add focus containment/restoration, Escape behavior and dirty-form protection to modal surfaces.
6. Make narrow layouts support the acceptance journeys rather than only stacking the desktop shell.

Exit: the shell, one collection and one object page use the new system; keyboard and narrow-layout
tests pass; no starter key determines presentation.

### WP2 — Add workspace discovery and typed collection semantics

Primary files:

- `backend/app/models/database.py`
- new Alembic revision
- `backend/app/models/api.py`
- new focused workspace router/service
- `backend/app/models/schema.py`
- object query service/router
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- workspace selector, collection and toolbar components
- `model/rdm-starter.json` only after contracts are final

Tasks:

1. Implement D1 with bounded workspace list/detail APIs and stable public keys.
2. Replace the raw workspace text input with an accessible searchable selector while preserving the
   selected key in every relevant URL.
3. Implement D2 or explicitly retain and document a deliberate built-in state contract.
4. Introduce discriminated table configuration with columns, permitted filters, permitted sorts,
   default sort and page size.
5. Add typed server-side filters and sorts for configured built-in or declared attribute fields. Keep
   cursor fingerprints bound to all effective query semantics.
6. Migrate the starter content to honest view declarations. Do not label a generic collection as a
   dedicated tree or dashboard.

Exit: unknown and retired workspaces behave deterministically; configured collection defaults work;
attribute filters and sorts are bounded and typed; older installed releases follow the documented
compatibility path.

### WP3 — Deliver coherent object management

Primary files:

- object and attribute API models/services only where atomic composition is required
- `frontend/src/components/ObjectFormDialog.tsx` or its replacement
- object collection, table, detail, attribute and relation components
- focused backend and frontend tests

Tasks:

1. Provide one create/edit experience for name, controlled state, parent, editable attributes and
   required relationships.
2. Preserve typed unset, null and falsy values and all existing required/read-only semantics.
3. Map structured API failures to fields plus a page-level summary.
4. Preserve dirty input on validation and version conflicts; explain the server-side changes that
   require review where the response provides enough data.
5. Improve table scanning, row activation, action menus and column overflow without hiding essential
   information behind hover-only interactions.
6. Retain dependency preview and separate cascade authorization for deletion.

Exit: journeys 2 through 5 can be completed without switching between a core-fields editor and
per-attribute edit actions; optimistic concurrency and deletion guarantees remain intact.

### WP4 — Improve the existing model workbench

Primary files:

- `frontend/src/components/model/`
- route and API adapter helpers
- model-workbench frontend tests

Tasks:

1. Keep the Base 0.5 draft, validation, compilation, diff, installation and activation APIs unchanged
   unless a demonstrated usability requirement needs an additive contract.
2. Add structured navigation across applications, object types, attributes, relations and views.
3. Group and filter diagnostics and make JSON Pointer navigation reliable.
4. Show base, active and candidate identities consistently and provide focused comparison views.
5. Add draft duplication, unsaved-change protection and clear draft provenance.
6. Present Draft → Validated → Installed → Active as separate states without implying that a draft
   concurrency version is immutable release history.

Exit: journey 8 is understandable without API knowledge; invalid local JSON and optimistic conflicts
never discard user input; mutation controls remain capability-gated.

### WP5 — Implement the core mapping workspace

Primary files:

- `backend/app/models/schema.py`
- `backend/app/models/api.py`
- focused mapping query/mutation service and router
- relation/audit services where shared behavior belongs
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- new mapping view component registered by semantic view type
- starter and synthetic model fixtures

Tasks:

1. Define and validate typed `mappingGrid` configuration: source type, target type, allowed relation,
   direction, displayed fields and permitted actions.
2. Return a cursor-paged source page with selected targets through one batched query; do not issue one
   relation request per row.
3. Support mapped, unmapped and ambiguous filtering. Never silently choose one edge from an ambiguous
   many-mapping state.
4. Reuse workspace-bounded, server-side candidate lookup.
5. Implement mapping create, remove and D4 atomic replace with explicit optimistic concurrency.
6. Reuse the generic object form for permitted create-target behavior.
7. Record and expose audit events for every mapping transition.
8. Prove the contract and renderer with the starter mapping and a second synthetic relation whose
   labels, endpoint types and direction differ.

Exit: journeys 6 and 7 are bounded, recoverable and key-agnostic; concurrent replacement never loses
the previously valid mapping; there is no client-side N+1 expansion.

### WP6 — Validate usability, accessibility and the release

Primary files:

- browser-level test configuration and scenarios
- frontend component and visual-regression tests
- backend contract/concurrency tests
- `README.md`, `CHANGELOG.md` and relevant `docs/`

Tasks:

1. Add browser-level tests for the eight acceptance journeys.
2. Add automated accessibility checks and explicit keyboard coverage for navigation, tables, forms,
   dialogs, lookups and mapping.
3. Add stable visual-regression coverage for the shell, collection, object editor, mapping view and
   model workbench.
4. Re-run the usability walkthrough with representative users or proxies and classify remaining gaps
   by task severity rather than visual preference.
5. Validate on the supported Python 3.12 environment as well as the normal frontend toolchain.
6. Update API, application-model, UI-model, architecture, project-status and roadmap documentation.

Exit: all release journeys pass; serious usability and accessibility findings are resolved or
explicitly deferred; the full repository definition of done passes.

## Release exit gate

- Normal workspace selection is catalogue-backed and remains explicit in URLs and API requests.
- Table and mapping-grid configurations are typed, validated and rendered according to their declared
  semantics.
- A steward can create and edit a complete object in one coherent flow without losing typed values or
  concurrency protection.
- Configured daily-use filters and sorts work server-side with stable bounded cursors.
- Mapping coverage, candidate search and single-row create/remove/replace avoid N+1 requests and
  preserve a valid mapping on conflict.
- The model workbench retains the Base 0.5 safety boundary while making lifecycle state and diagnostics
  understandable.
- Core workflows meet keyboard and automated accessibility expectations and have browser-level and
  visual-regression coverage.
- Backend tests, Ruff, frontend tests, frontend production build, migrations, documentation and
  `git diff --check` pass on the supported toolchain.

## Required validation

Run from the repository root:

```bash
backend/.venv/bin/python -m ruff check backend
backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

Also run the new browser, accessibility and visual-regression suites, verify a schema 0.4 upgrade with
existing workspaces and runtime data, and verify the packaged wheel contains every new Alembic
revision. The release validation environment must include Python 3.12.

## Coding-agent handoff

Implement work packages in order and keep each package independently reviewable. WP0 is a real gate:
do not begin a broad stylesheet rewrite or mapping backend before the task flows and D1 through D5 are
resolved. Inspect `git status` before every package, preserve unrelated changes, update OpenAPI locks
with public contract changes and create a dedicated checkpoint only after the package definition of
done passes.
