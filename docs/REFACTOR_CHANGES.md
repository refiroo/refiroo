# Refactor changes — v0.3.0 structural reorganization

## Summary

Reorganized the backend and frontend into a standard layered folder structure aligned with
FastAPI and React conventions. Applied four correctness fixes. No API contracts, database schemas,
model definitions, or external behavior changed. All 10 existing tests pass, linting is clean,
and the frontend production build succeeds.

## Backend structure: before and after

### Before (flat modules)

```
backend/app/
├── __init__.py
├── api_models.py         ← Pydantic request/response models
├── attribute_values.py   ← Attribute validation + typed persistence
├── config.py             ← Environment config
├── database.py           ← SQLAlchemy ORM models + engine + session + install_model
├── main.py               ← 605 lines: app, lifespan, CORS, all routes, all business logic
├── model_loader.py       ← JSON model loading + caching
└── model_schema.py       ← Engine model Pydantic schema + validation
```

### After (layered packages)

```
backend/app/
├── __init__.py
├── main.py               ← 44 lines: app, lifespan, CORS, router includes
├── config.py             ← Environment config (added CORS_ORIGINS)
├── db.py                 ← Engine, SessionLocal, create_database, install_model
├── models/
│   ├── __init__.py       ← Re-exports for convenience
│   ├── api.py            ← Pydantic request/response models (from api_models.py)
│   ├── database.py       ← SQLAlchemy ORM models + Base (from database.py)
│   └── schema.py         ← Engine model schema + validation (from model_schema.py)
├── routers/
│   ├── __init__.py
│   ├── model.py          ← Model metadata endpoints (GET /model, /applications, etc.)
│   ├── objects.py        ← Object CRUD endpoints (list, create, get, update, delete)
│   └── relations.py      ← Relation endpoints (create, get with expansion)
└── services/
    ├── __init__.py
    ├── attributes.py     ← Attribute validation, normalization, persistence (from attribute_values.py)
    ├── model_loader.py   ← Model JSON loading + LRU cache (from model_loader.py)
    ├── objects.py        ← Object business logic (parent validation, cycle detection, path, responses)
    └── relations.py      ← Relation business logic (allowed relation, cardinality, response building)
```

### Deleted files

| Old file | Replaced by |
|----------|-------------|
| `api_models.py` | `models/api.py` |
| `attribute_values.py` | `services/attributes.py` |
| `database.py` | `models/database.py` + `db.py` |
| `model_loader.py` | `services/model_loader.py` |
| `model_schema.py` | `models/schema.py` |

## Frontend structure: before and after

### Before (flat)

```
frontend/src/
├── main.tsx
├── App.tsx
├── api.ts
├── model.ts
├── types.ts
├── CollectionView.tsx
├── Explorer.tsx
├── ObjectDetail.tsx
├── ObjectFormDialog.tsx
└── ObjectTable.tsx
```

### After (organized)

```
frontend/src/
├── main.tsx              ← Unchanged
├── App.tsx               ← Updated imports only
├── types.ts              ← Unchanged
├── api/
│   └── client.ts         ← API client (from api.ts)
├── components/
│   ├── CollectionView.tsx
│   ├── Explorer.tsx
│   ├── ObjectDetail.tsx
│   ├── ObjectFormDialog.tsx
│   └── ObjectTable.tsx
└── utils/
    └── model.ts          ← Route parsing, field helpers (from model.ts)
```

### Deleted files

| Old file | Replaced by |
|----------|-------------|
| `api.ts` | `api/client.ts` |
| `model.ts` | `utils/model.ts` |
| `CollectionView.tsx` | `components/CollectionView.tsx` |
| `Explorer.tsx` | `components/Explorer.tsx` |
| `ObjectDetail.tsx` | `components/ObjectDetail.tsx` |
| `ObjectFormDialog.tsx` | `components/ObjectFormDialog.tsx` |
| `ObjectTable.tsx` | `components/ObjectTable.tsx` |

## Correctness fixes included

### 1. SQL wildcard escaping in search (was: injection risk)

**File:** `routers/objects.py` (list_objects)

The `search` parameter was interpolated raw into `ilike(f"%{search}%")`. Characters `%` and `_`
in user input acted as SQL wildcards. Now escaped before interpolation:

```python
escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
# Uses ilike(f"%{escaped}%", escape="\\")
```

### 2. Missing audit event on object deletion

**File:** `routers/objects.py` (delete_object)

`delete_object` was the only mutation endpoint that did not write an `AuditEvent`. Now creates
a `"deleted"` audit event before removing the object, completing the audit trail invariant.

### 3. O(1) model lookups via dictionary indexes

**File:** `models/schema.py` (EngineModel)

The `attribute_type()`, `object_type()`, and `relation_type()` methods previously did linear
scans over the full list on every call. The `validate_references` model validator now builds
`dict[str, T]` indexes (`_attribute_types_by_key`, `_object_types_by_key`,
`_relation_types_by_key`) during validation, and the lookup methods use `.get()`.

### 4. Configurable CORS origins

**File:** `config.py`, `main.py`

CORS `allow_origins` was hardcoded to `["http://localhost:5173"]`. Now reads from the
`CORS_ORIGINS` environment variable (comma-separated), defaulting to `http://localhost:5173`.

## Test impact

- All 10 existing tests pass unchanged (test_api imports `app` from `app.main`, which still works)
- `test_model.py` imports updated: `app.model_loader` → `app.services.model_loader`,
  `app.model_schema` → `app.models.schema`
- Ruff linting passes with zero errors
- Frontend TypeScript compilation and Vite production build succeed

## What did NOT change

- All API endpoints, status codes, request/response schemas — identical
- Database schema — no table or column changes
- `model/rdm-starter.json` — untouched
- `frontend/src/types.ts` — untouched
- `frontend/src/main.tsx` — untouched
- `frontend/src/styles.css` — untouched
- No new dependencies added
- No behavioral changes to any endpoint
