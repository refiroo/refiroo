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

## Current state — model 0.4

- Global reusable attribute types and object-type attribute bindings
- Forward/reverse typed relations, features and allowed object-type relation triples
- Immutable model releases installed into relational metadata tables
- Persisted, optimistic-concurrency model drafts and atomic immutable release installation
- Compatibility-gated release activation with runtime-state concurrency and lifecycle audit
- Side-effect-free model validation with stable diagnostics, key-based release diff and bounded
  runtime-data compatibility analysis
- Generic objects with application, workspace, object type, state, parent and path
- Separately stored typed attribute values—text, integer, decimal, boolean, date, datetime and JSON
- Typed object relations, automatic parent relations and hierarchy cycle protection
- Relation cardinality checks and audit events
- Cursor pagination with explicit limits and optimistic concurrency
- React application/view navigation, searchable hierarchy explorer and stable object routes
- Registry-driven collection views and composable object details with main/side panels
- Reusable attribute, child, relation, table and hierarchy panels
- Model-driven runtime CRUD for objects, individual typed attribute values and mutable relationships
- Accessible confirmations, structured mutation errors and optimistic-concurrency recovery
- Dependency-previewed object deletion with explicit transactional graph cascade
- Cross-application relationship lookup with server-side search and cursor pagination
- Optional Domain/Codelist-to-System Value representations that preserve the separate system hierarchy
- Translation CRUD with generic Domain, Codelist and Master Value targets, atomic required bindings,
  and active Language-scoped uniqueness
- Docker development environment and continuous-integration workflow

Mapping-grid and hierarchy-tree views are defined by the model but currently resolve to the generic
collection presentation. Base 0.5 first strengthens object management and introduces safe model
lifecycle foundations; dedicated interaction components follow.

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

Python 3.12 is the supported version (see `.python-version` and `backend/Dockerfile`); the package
declares `requires-python >= 3.12`.

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

The backend uses SQLite locally unless `DATABASE_URL` is set. The model defaults to
`model/rdm-starter.json`. Set `RDM_CURSOR_SIGNING_KEY` to a deployment-specific secret so opaque
pagination cursors remain verifiable across restarts. Without it, the process generates an ephemeral
key and cursors issued before a restart become invalid.

Model-administration mutations are not registered by default. Set
`MODEL_ADMIN_MUTATIONS_ENABLED=true` only in the supported single-process administration deployment
to enable draft CRUD, draft compilation, release installation and guarded activation. Set
`WEB_CONCURRENCY=1` explicitly when configuring a worker count; startup rejects mutation enablement
with multiple workers until cross-process release propagation exists. Installed-release reads, diff
and inline validation remain available without the flag.

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
| `docs/ROADMAP.md` | Sequenced product milestones and release gates |
| `docs/BASE_0_5_IMPLEMENTATION_PLAN.md` | Ordered Base 0.5 coding handoff and acceptance criteria |
| `AGENTS.md` | Authoritative instructions for coding agents |

Before changing the architecture, read `AGENTS.md` and the documents it links.

## Source-material boundary

The supplied vendor package and API examples were used to identify the generic object–attribute–
relation model, application packaging, hierarchy and UI configuration concepts. They are deliberately
not included in this repository. RDM Engine uses its own keys, schema, database, API and interface.

The source is not ready for public release until an open-source licence is selected; see
`docs/OPEN_SOURCE.md`.
