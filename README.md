# RDM Engine

RDM Engine is an API-first, model-driven platform for reference data. Applications, object types,
global attribute types, relation types, allowed object-type relationships and UI views are described
by a versioned JSON model rather than hardcoded into the product.

The engine is model-independent. Every application gets the same feature set: any view type (table,
mapping grid, relation matrix, tree), any relation pattern and the same live, change-set and
publication behaviour. The engine never branches on an application, object-type or relation key.

The bundled example model (`model/rdm-starter.json`) shows these capabilities with one
reference-data use case, split into three applications:

- RDM Master — domains, codelists and canonical values
- RDM Systems — external-system values, groups, master mappings and Domain/Codelist representations
- RDM Translations — languages, groups and translated values

They are examples, not engine modules and not a template to follow. A model can rename, reshape or
replace them, or add applications for entirely different domains. The views each example application
declares differ only because the example declares them that way; see
[docs/EXAMPLE_MODEL.md](docs/EXAMPLE_MODEL.md).

This project is delivered by LLM coding agents, Claude Code and ChatGPT Codex, under human
supervision.

## Current state — Base 0.8 released

- Global reusable attribute types and object-type attribute bindings
- Forward/reverse typed relations, features and allowed object-type relation triples
- Immutable model releases installed into relational metadata tables
- Persisted, optimistic-concurrency model drafts and atomic immutable release installation
- Compatibility-gated release activation with runtime-state concurrency and lifecycle audit
- Side-effect-free model validation with stable diagnostics, key-based release diff and bounded
  runtime-data compatibility analysis
- Stable workspace, object and relation identities with workspace-level publication boundary
- Separately stored typed attribute values—text, integer, decimal, boolean, date, datetime and JSON
- Typed object relations, automatic parent relations and hierarchy cycle protection
- Relation cardinality checks and audit events
- Cursor pagination with explicit limits and optimistic concurrency
- React application/view navigation, searchable hierarchy explorer and stable object routes
- Catalogue-backed workspace selection with a concurrency-protected default, searchable bounded
  discovery, URL-stable keys and read-only retired scopes
- Registry-driven collection views and composable object details with main/side panels
- Reusable attribute, child, relation, table and hierarchy panels
- Accessible confirmations, structured mutation errors and optimistic-concurrency recovery
- Generic object, attribute, relation and translation CRUD as one contract; normal writes are live
  and an explicitly selected change set is optional; no per-record lifecycle
- Live active data writes (ADR-026): the active workspace is live-writable for **data** —
  record writes no longer require a change set (`changeSetId` optional; omitted → direct live
  write, immediate and audited, no publication). The model stays immutable on an active
  workspace; change sets remain the design playground; publishing delta-merges over live content
- Complete browser journeys for live CRUD, optional change sets, newest-first immutable history, historical
  change set sources, truthful publication withdrawal and conflict reconciliation (WP9)
- Composed release validation with real-browser and backend evidence (WP10)
- Frontend redesign (UI-01–UI-06): compact navigation, focused collections, record inspector, inline
  field editing, resizable panels, display preferences and refined change set presentation
- Cross-application relationship lookup with server-side search and cursor pagination
- Optional Domain/Codelist-to-System Value representations that preserve the separate system hierarchy
- Translation CRUD with generic Domain, Codelist and Master Value targets, atomic required bindings,
  and active Language-scoped uniqueness
- A global model workbench for installed-release inspection and export, plus capability-gated JSON
  draft validation, comparison, installation and activation
- Schema 0.6 `mappingGrid` views: live and change set mapping coverage, candidate search, version-bound
  target details and atomic mapping replacement with relation-set concurrency (ADR-022)
- One contextual application browser with table and mapping lenses, direct-parent scope, typed facets
  and mapping coverage filters (ADR-029)
- Change sets on a chosen model release, so one draft can prepare a new release while live data
  stays on the active one (ADR-028)
- Release technical details and earlier-release → selected-release semantic comparison
- Dark mode, automated accessibility (axe) and visual-regression gates
- Collections at any size (ADR-030): cursor and position paging, continuous scrolling in both
  directions, totals and jumps by page, value, start or end, indexed search, and a sidebar tree that
  loads by parent, in live, change sets and publications
- One name per concept (workspace, live, change set, publication) and a Workspaces screen to create,
  rename, retire, reactivate, delete and choose the default workspace (ADR-031)
- Schema 0.7 `relationMatrix` views: rows against the records of an ancestor type, with cell states
  across the whole list and create, edit, link and unlink from a cell (ADR-033)
- Schema 0.7 `tree` views: a lazily loaded hierarchy lens with add child, rename, availability and move
  by dialog or by drag and drop, including to the top level
- Change set review: every added, changed and removed record and relationship with before and after
- Hierarchy restructuring in a change set (ADR-034): a move that changes a record's type, change type,
  insert or remove a level, with a preview; records keep their IDs, and what a new type has no place
  for is kept in history and offered back
- Docker development environment and continuous-integration workflow

Base 0.5 supplies the bounded query and model-lifecycle foundations. Base 0.6 delivers daily live
operations and optional coordinated design. Base 0.7 adds core mapping: a steward resolves unmapped,
differently mapped and ambiguous rows in a configured mapping lens, live or in a change set, with conflicts
reported rather than overwritten; and prepares a schema change in a change set pinned to a candidate release
while live work continues. See the [mapping API contract](docs/API.md#product-07-mapping-api-wp-4-and-wp-5-delivered)
and the [0.7 plan](docs/BASE_0_7_IMPLEMENTATION_PLAN.md). Base 0.8 makes every collection work at any
size and adds the relation matrix (translation and mapping coverage), the hierarchy editor and
hierarchy restructuring; see the [0.8 plan](docs/BASE_0_8_IMPLEMENTATION_PLAN.md). Integration-grade
APIs follow in 0.9.

Start with the [product functionality guide](docs/product-functionality/README.md) for available/planned
functions, stories and realistic acceptance scenarios. The [delivery queue](docs/TODO.md) traces
the 0.9 work. Historical schema replacement with preview and explicit loss confirmation is a
planned 0.11 migration, not a current force action.

## Run with Docker

```bash
docker compose up --build
```

Open:

- UI: http://localhost:5173
- API reference: http://localhost:8000/docs (Scalar, works offline; see [API.md](docs/API.md#api-reference-page-base-09-v1))
- Model: http://localhost:8000/api/v1/model

## Run without Docker

Backend:

Python 3.14 is the supported version (see `.python-version` and `backend/Dockerfile`); the package
declares `requires-python >= 3.14`. Python 3.12 compatibility is not maintained.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run the frontend test suite with `npm test`.

The backend uses `backend/rdm-engine.db` through SQLite locally unless `DATABASE_URL` is set. The
model defaults to `model/rdm-starter.json`. Set `RDM_CURSOR_SIGNING_KEY` to a deployment-specific
secret so opaque pagination cursors remain verifiable across restarts. Without it, the process
generates an ephemeral key and cursors issued before a restart become invalid.

The API reference at `/docs` loads its Scalar script from the copy bundled with the engine, so it works
without internet access. Set `RDM_API_REFERENCE_SCRIPT=cdn` to load the same pinned version from a
CDN instead.

Model-administration mutations are not registered by default. Set
`MODEL_ADMIN_MUTATIONS_ENABLED=true` only in the supported single-process administration deployment
to enable draft CRUD, draft compilation, release installation and guarded activation. Set
`WEB_CONCURRENCY=1` explicitly when configuring a worker count; startup rejects mutation enablement
with multiple workers until cross-process release propagation exists. Installed-release reads, diff
and inline validation remain available without the flag.

Workspace administration is registered by default until authentication exists. Set
`WORKSPACE_ADMIN_MUTATIONS_ENABLED=false` on an API exposed outside a trusted environment unless an
external access-control layer protects it. The flag removes workspace create, rename, retire, delete and
default-switch routes; it is a deployment capability, not caller authorization. Workspace discovery
and the change-set workflow (create, edit, validate, publish, discard, and publication withdrawal)
remain available, retired workspaces remain readable, and all runtime mutations in them are rejected.
With the flag on, the browser's **Workspaces** screen (header, beside **Models**) lists, creates,
renames, retires, deletes and sets the default workspace; with it off, the screen is read only and names the
setting.

Bulk writes run as jobs (`POST /api/v1/batches`, read back through `/api/v1/jobs`). Job creation is
registered by default; `INTEGRATION_JOBS_ENABLED=false` removes it while job reads remain. The limits
are settings reported by `GET /api/v1/capabilities`: `BATCH_MAX_ITEMS` (1000), `BATCH_MAX_BYTES`
(5 MB), `ATOMIC_JOB_MAX_ITEMS` (10000) and `JOB_RETENTION_DAYS` (7). A batch is one transaction, so on
SQLite it holds the database's writer lock while it runs (about 3 s for 1,000 live upserts, 6 s in a
change set); `SQLITE_LOCK_WAIT_SECONDS` (60) is how long other writes wait for it before failing.

A batch sent with `run: background` (up to `BACKGROUND_JOB_MAX_ITEMS`, 1,000,000 items, in a body of
at most `BATCH_BACKGROUND_MAX_BYTES`, 50 MB) is queued and answered with `202`. A worker thread in
the API process runs it in chunks of `JOB_CHUNK_ITEMS` (500), each committing its changes, outcomes
and progress together; `POST /api/v1/jobs/{jobId}/cancel` stops it at the next chunk. The worker runs
only with `INTEGRATION_JOBS_ENABLED` on and a healthy model, and expires finished jobs past their
retention every hour.

**Restart behaviour.** A graceful stop finishes the running chunk and releases the worker's lease,
so the next start resumes the job at once. After a crash or kill, the chunk in progress rolls back,
and the job resumes at its first item without an outcome once its lease (`JOB_LEASE_SECONDS`, 120)
expires: no item is applied twice or skipped. On SQLite a running background job holds the writer
lock chunk after chunk, so other writes wait until the job ends and fail after
`SQLITE_LOCK_WAIT_SECONDS`; run large background jobs when nothing else writes, until the engine
runs on PostgreSQL.

### Model releases and rollback

`RDM_MODEL_PATH` (or `model/rdm-starter.json` by default) is bootstrap input, not the active-model
setting. Startup validates and installs missing bootstrap content, but an existing database keeps the
release selected in `model_runtime_state`. Every request resolves that database-selected immutable
release; changing the file alone does not activate it.

If an existing database still selects a schema 0.4 release, startup keeps the API in an unhealthy
state instead of emitting an exception traceback. The startup log names the selected and supported
schemas and prints the exact offline transition command for the configured model path. Stop every
process using that database, run the displayed command in the same configured environment, and then
restart the API; `/health` returns HTTP `503` until the transition succeeds.

The administration lifecycle is deliberately staged: save editable JSON as a versioned draft,
validate/compile it without persistence side effects, install it as an immutable inactive release,
then activate it with the current runtime version and active-release ID. Activation is refused when
stored runtime data is incompatible.

Before upgrading, stop writers and back up the database with the database engine's consistent backup
procedure. Run Alembic migrations before starting the new application. To roll back model content,
activate a previously installed compatible release through the Models workbench or activation API;
do not edit installed JSON or point `RDM_MODEL_PATH` at an older file. Application/schema rollback is
a separate operational change: restore the matching pre-upgrade database backup before running older
code because Alembic downgrades and automatic runtime-data transformations are not a supported
production rollback path. See `docs/API.md` for the activation contract and `docs/ARCHITECTURE.md` for
the detailed runbook.

Run database migrations through the environment-aware operator command:

```bash
cd backend
.venv/bin/python -m app.cli.database_upgrade
```

If a migration cannot complete safely, startup does not emit a framework traceback or continue as if
the schema were usable. The process enters maintenance mode, `/health` returns HTTP `503`, and the log
reports the database without credentials, current and target revisions, the failure reason, safe
backup/retry instructions, and what to include in an escalation. The WP4 migration automatically
recovers empty SQLite tables or columns left by an interrupted pre-backfill attempt; it refuses to
delete partial lifecycle data or an unfamiliar schema.

## Repository guide

| Path | Purpose |
| --- | --- |
| `model/rdm-starter.json` | Example model: three applications showing the engine's capabilities ([explained](docs/EXAMPLE_MODEL.md)) |
| `backend/app/models/schema.py` | Executable model contract and cross-reference validation |
| `backend/app/models/database.py` | Metadata, object, attribute, relation and audit persistence |
| `backend/app/routers` | Model and runtime API routes |
| `backend/app/services` | Generic object, attribute and relation behavior |
| `backend/app/migrations` | Versioned Alembic database migrations |
| `frontend/src/App.tsx` | Model-driven application and form renderer |
| `docs/PROJECT_STATUS.md` | Current implementation and next work |
| `docs/ROADMAP.md` | Sequenced product milestones and release criteria |
| `docs/MODEL_AUTHORING.md` | 0.10 design: one editor for the model and the import mapping, spreadsheet onboarding |
| `docs/COMPOSABLE_DOMAINS.md` | Unscheduled direction: MDM-lite and catalogues modelled from generic capabilities |
| `docs/TODO.md` | Prioritized active delivery queue |
| `docs/BASE_0_5_IMPLEMENTATION_PLAN.md` | Ordered Base 0.5 coding handoff and acceptance criteria |
| `docs/BASE_0_6_IMPLEMENTATION_PLAN.md` | Ordered Base 0.6 decisions, work packages and acceptance criteria |
| `docs/UI_MODEL.md` | UI semantics, interaction priorities and usability direction |
| `AGENTS.md` | Authoritative instructions for coding agents |

Before changing the architecture, read `AGENTS.md` and the documents it links.

## Source-material boundary

The supplied vendor package and API examples were used to identify the generic object–attribute–
relation model, application packaging, hierarchy and UI configuration concepts. They are deliberately
not included in this repository. RDM Engine uses its own keys, schema, database, API and interface.

The source is not ready for public release until an open-source licence is selected; see
`docs/OPEN_SOURCE.md`.
