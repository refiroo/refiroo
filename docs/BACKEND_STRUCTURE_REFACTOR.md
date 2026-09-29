# Backend structure refactor

> The layout below is superseded by [BACKEND_BOUNDARIES_PLAN.md](BACKEND_BOUNDARIES_PLAN.md)
> (2026-09-29): `services/` and `routers/` became `engine/`, `management/` and `common/`. The findings
> and their reasoning still hold.

Structural reorganization of `backend/app` following the review recorded as fourteen findings
(F-01 … F-14). Supersedes nothing in `docs/REFACTOR_CHANGES.md`, which describes the earlier v0.3.0
reorganization.

## Scope

No API contract, database schema, or architectural change. Both generated OpenAPI documents — the
default topology and the one with `MODEL_ADMIN_MUTATIONS_ENABLED=true` — are byte-identical to the
pre-refactor output. No Alembic revision was added.

One behavioral change, F-01, described below.

## Layout

```
backend/app/
├── main.py                      app factory, exception handlers, router wiring
├── config.py                    Settings object read from the environment  (F-10)
├── db.py                        lazy engine, get_session/DbSession, migrations  (F-02, F-09)
├── errors.py
├── common/                                                                  (F-06)
│   ├── time.py                  as_utc
│   └── json_pointer.py          pointer_segment, relation_path
├── models/
│   ├── api.py
│   ├── database.py
│   └── schema.py                shapes, key indexes, graph freezing only     (F-03)
├── routers/
│   ├── presenters.py            shared service-dataclass → DTO renderers     (F-06)
│   ├── model.py                 active model, capabilities, metadata         (F-08)
│   ├── model_releases.py        release catalog, detail, diff                (F-08)
│   ├── model_management.py
│   ├── objects.py               transport only                              (F-07)
│   ├── relations.py
│   └── attributes.py
└── services/
    ├── objects.py               + build_object_query, create/update records  (F-07)
    ├── relations.py
    ├── attributes.py            + validate_attribute_change/apply_…          (F-05)
    ├── deletion.py
    ├── audit.py
    ├── cursors.py
    ├── pagination.py            shared keyset paginator                      (F-04)
    └── model/                                                                (F-11)
        ├── bootstrap.py         moved out of db.py                           (F-09)
        ├── compiler.py          compile_model, parse_model                   (F-01)
        ├── diagnostics.py       ModelDiagnostic, ModelReferenceError
        ├── validation/          one module per rule family              (F-01, F-03)
        ├── compatibility.py
        ├── diff.py
        ├── drafts.py
        ├── loader.py
        ├── metadata.py          public-ID projections + per-release cache    (F-14)
        ├── registry.py
        ├── releases.py
        └── runtime.py           runtime-state access
```

## F-01 — model diagnostics no longer parse their own error messages

Before, cross-reference rules lived in `EngineModel.validate_references` and reported failures by
raising `ValueError` with a formatted sentence. Because a Pydantic validator error carries no
useful `loc`, `model_compiler._inferred_reference_path` reconstructed the diagnostic's JSON pointer
by running roughly twenty regular expressions over that sentence, and for several codes re-scanned
the raw source document to guess which element was meant.

Now each rule in `services/model/validation/` raises `ModelReferenceError(code, path, message)` at
the point of detection, where the offending keys are still in hand. The regex layer is deleted.

**This changes when references are checked.** `EngineModel.model_validate` now validates shape
only; it no longer guarantees that references resolve. Every path that turns a document into a
model goes through `compile_model` or `parse_model`, which do check — including the bootstrap
loader and `ModelRegistry`, so runtime code still only ever holds a reference-valid model.

Messages and codes are unchanged. Paths are unchanged in 42 of the 45 pinned cases; the three that
differ are cases where the old pointer was wrong:

| Case | Before | After |
| --- | --- | --- |
| Unknown `uniqueToAncestorTypeKey` | pointed at the first object-type relation in the document, not the one named in the message | points at the failing relation |
| A view with duplicate columns | `""` | `/applications/{app}/views/{view}/config/columns` |
| A view with an unknown `ancestor:` column | `""` | `/applications/{app}/views/{view}/config/columns` |

`tests/test_model_diagnostics.py` pins the code and path of all 45 cases, one per rule.

Reference validation still reports the first violation only, matching the single-diagnostic
contract the API has always exposed. Collecting every violation is a one-line change in
`validate_references`.

## Other findings

- **F-02** One session per request via `DbSession`. Handlers, the `ActiveModelSnapshot` dependency
  and the metadata projections now share it; nothing opens `SessionLocal()` inside a request path.
- **F-04** `services/pagination.py` replaces six hand-written keyset implementations.
  `paginate_statement` derives each key's comparison from that key's own direction, so mixed-
  direction keysets (drafts order `updatedAt` descending, `publicId` ascending) stay lexicographic.
  Ordering behavior is unchanged at every call site. The draft endpoint retains its historical
  cursor sort identity so cursors signed before this refactor remain usable.
- **F-05** `apply_attribute_values` owns the write sequence — merge, `atLeastOneOf`, uniqueness,
  save, scoped-relation revalidation — for both single-attribute endpoints. `update_object_record`
  shares its `validate_attribute_change` half while keeping the original order of validation
  relative to name/state/parent mutation.
- **F-07** `create_object_record` and `update_object_record` moved into `services/objects.py`;
  metadata response builders moved into `services/model/metadata.py`.
- **F-09** Bootstrap moved to `services/model/bootstrap.py`. The engine is built lazily, so
  `DATABASE_URL` no longer has to be set before the first `app.*` import.
- **F-10** `Settings` is validated once and cached; `create_app()` re-reads it, which is what lets
  a test construct a differently configured app in the same process. Engines and session factories
  are cached by database URL, so reloading settings cannot make migrations and request sessions use
  different databases. The per-process ephemeral cursor signing key is generated at import so
  reloading settings does not invalidate live cursors.
- **F-12** The unused partial re-export barrel in `models/__init__.py` is gone.
- **F-13** `backend/build/` (a stale copy of every module) and the empty `backend/alembic/` are
  removed. The existing `backend/rdm-engine.db` default is retained so the structural refactor does
  not relocate or hide local data.
- **F-14** Public-ID maps are cached per immutable release and cleared with `ModelRegistry.clear()`.

## Verification

- 225 backend tests pass (162 before; diagnostic, pagination, request-scope and defensive model-
  installation coverage added).
- `ruff check app/ tests/` clean.
- Frontend production build succeeds.
- Both OpenAPI documents byte-identical to the pre-refactor baseline.
- A real Uvicorn process serves health, capabilities, paginated metadata, runtime state and
  structured validation diagnostics.
