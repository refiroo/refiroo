# RDM Engine

RDM Engine is an API-first, model-driven platform for reference data. Applications, object types,
global attribute types, relation types, allowed object-type relationships and UI views are described
by a versioned JSON model rather than hardcoded into the product.

The starter model contains three configured applications:

- RDM Master — domains, codelists and canonical values
- RDM Systems — external-system values, groups, master mappings and Domain/Codelist representations
- RDM Translations — languages, groups and translated values

They are starter definitions, not reserved engine modules. A model can replace them or add entirely
different applications.

## Current state — Base 0.6 released

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
  and an explicitly selected workspace draft is optional; no per-record lifecycle
- Live active data writes (ADR-026): the active workspace is live-writable for **data** —
  record writes no longer require a workspace draft (`workspaceDraftId` optional; omitted → direct live
  write, immediate and audited, no workspace revision). The model stays immutable on an active
  workspace; drafts remain the design playground; activation delta-merges over live content
- Complete browser journeys for live CRUD, optional drafts, newest-first immutable history, historical
  draft sources, truthful publication retirement and conflict reconciliation (WP9)
- Composed release validation with real-browser and backend evidence (WP10)
- Frontend redesign (UI-01–UI-06): compact navigation, focused collections, record inspector, inline
  field editing, resizable panels, display preferences and refined draft presentation
- Cross-application relationship lookup with server-side search and cursor pagination
- Optional Domain/Codelist-to-System Value representations that preserve the separate system hierarchy
- Translation CRUD with generic Domain, Codelist and Master Value targets, atomic required bindings,
  and active Language-scoped uniqueness
- A global model workbench for installed-release inspection and export, plus capability-gated JSON
  draft validation, comparison, installation and activation
- Docker development environment and continuous-integration workflow

Base 0.5 supplies the bounded query and model-lifecycle foundations. Base 0.6 delivers daily live
operations and optional coordinated design: a steward can maintain live records, fields, parents,
relationships and translations without a draft; use optional workspace drafts for coordinated changes
with delta-merge activation; browse newest-first immutable history; and retire publications truthfully.
Automated accessibility and visual-regression tooling (UI-07), the schema 0.6 mapping-grid contract,
and live/draft mapping coverage, version-bound target details and candidate search APIs (WP-4) are
delivered. Cascade deletion invalidates affected mapping tokens. The mapping renderer is currently
a placeholder; see the [mapping API contract](docs/API.md#product-07-mapping-api-wp-4-delivered-wp-5-planned). The full workflow and draft
model-version selection remain planned 0.7 work, with translation and hierarchy interactions in 0.8.
The [0.7 plan](docs/BASE_0_7_IMPLEMENTATION_PLAN.md) freezes WP1–WP3, splits mapping coverage/actions
into WP8A/WP8B and assigns integration acceptance to WP9, with conditional WP10 for confirmed gaps.

Start with the [product functionality guide](docs/product-functionality/README.md) for available/planned
functions, stories and realistic acceptance scenarios. The [delivery queue](docs/TODO.md) traces
remaining 0.7 work. Historical schema replacement with preview and explicit loss confirmation is a
planned 0.10 migration, not a current force action.

## Run with Docker

```bash
docker compose up --build
```

Open:

- UI: http://localhost:5173
- API documentation: http://localhost:8000/docs
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

Model-administration mutations are not registered by default. Set
`MODEL_ADMIN_MUTATIONS_ENABLED=true` only in the supported single-process administration deployment
to enable draft CRUD, draft compilation, release installation and guarded activation. Set
`WEB_CONCURRENCY=1` explicitly when configuring a worker count; startup rejects mutation enablement
with multiple workers until cross-process release propagation exists. Installed-release reads, diff
and inline validation remain available without the flag.

Workspace administration is registered by default until authentication exists. Set
`WORKSPACE_ADMIN_MUTATIONS_ENABLED=false` on an API exposed outside a trusted environment unless an
external access-control layer protects it. The flag removes workspace create/update/default-switch
routes; it is a deployment capability, not caller authorization. Workspace discovery remains
available, retired workspaces remain readable, and all runtime mutations in them are rejected.

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
| `model/rdm-starter.json` | Independent starter application model |
| `backend/app/models/schema.py` | Executable model contract and cross-reference validation |
| `backend/app/models/database.py` | Metadata, object, attribute, relation and audit persistence |
| `backend/app/routers` | Model and runtime API routes |
| `backend/app/services` | Generic object, attribute and relation behavior |
| `backend/app/migrations` | Versioned Alembic database migrations |
| `frontend/src/App.tsx` | Model-driven application and form renderer |
| `docs/PROJECT_STATUS.md` | Current implementation and next work |
| `docs/ROADMAP.md` | Sequenced product milestones and release criteria |
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
