# Instructions for coding agents

## Read first

Before changing code or the model, read in this order:

1. `docs/PROJECT_STATUS.md`
2. `docs/PRODUCT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/APPLICATION_MODEL.md`
5. `docs/SOURCE_MODEL_ANALYSIS.md`
6. `docs/DECISIONS.md`
7. The relevant backend or frontend source files

Do not infer the product from one screen or object type. This is a generic model-driven engine. RDM
Master, Systems and Translations are starter applications, not hardcoded modules.

## Product invariants

- The versioned JSON model is the declarative source for applications, object types, global attribute
  types, relation types, allowed object-type relationships and views.
- Runtime code must remain unaware of domain-specific keys such as `master-value` or `system-value`.
- Attribute types are globally reusable; object types attach them through explicit bindings.
- Relation types define forward/reverse semantics separately from permitted source/target combinations.
- Parent containment is both an object hierarchy and a typed relation, maintained atomically.
- UI renderers may implement generic view types but must not branch on application or object-type keys.
- Every model reference is validated at startup and should fail with a precise path and reason.
- Public APIs never use an undocumented result cap. Collections use cursor pagination.
- Bulk and integration APIs are first-class features, not wrappers around UI calls.
- Public IDs and model keys are stable. Never expose database sequence IDs as domain identifiers.
- Attribute values retain their declared types. Do not reduce booleans, numbers or dates to strings.
- Updates use optimistic concurrency. Never silently overwrite a newer version.
- Model releases are immutable snapshots; schema-language and content-release versions are separate.
- Keep vendor-specific source exports and internal numeric identifiers outside this repository.

## Working method

For each feature:

1. State the user-visible behavior in a small plan.
2. Extend the application model only when behavior must be configurable.
3. Add model validation before relying on new configuration.
4. Update metadata persistence if the model contract changes.
5. Implement backend behavior and tests.
6. Implement the generic UI component and exercise it with at least two object types.
7. Update documentation and add an architecture decision when the tradeoff is durable.
8. Run backend tests, linting and the frontend production build.

Avoid speculative abstractions. Add a generalization after two real RDM cases demonstrate it. Keep API
errors explicit and machine-readable.

## Code conventions

### Backend

- Python 3.14, FastAPI, Pydantic 2 and SQLAlchemy 2.
- Type public functions.
- Keep Pydantic API models separate from SQLAlchemy persistence models.
- Keep model parsing and validation independent of the database.
- Attribute conversion belongs in `services/attributes.py`, not route handlers.
- Every attribute write goes through `services/attributes.apply_attribute_values` or its
  `validate_attribute_change` half, so no path can persist values while skipping a check.
- Routers translate requests and responses. Orchestration lives in `services/`; a handler that
  reads the model to decide what to write belongs in a service.
- Handlers take the request-scoped `DbSession` dependency. Do not open `SessionLocal()` inside a
  request path; one request reads from one session.
- Collections page through `services/pagination.py`. Declare sort keys, do not hand-write a keyset
  predicate, and make the last key unique within the filtered set.
- Model shape lives in `models/schema.py`; cross-reference rules live in
  `services/model/validation/`. A rule raises `ModelReferenceError` with the JSON pointer of the
  failing node — never reconstruct a path from a message.
- Obtain an `EngineModel` through `services/model/compiler.parse_model` or `compile_model`.
  `EngineModel.model_validate` checks shape only and does not guarantee references resolve.
- Database migrations will use Alembic before the first deployed schema change.
- Prefer focused service modules over adding more logic to `main.py`.

### Frontend

- React, TypeScript and Vite. See `docs/FRONTEND_STRUCTURE_REFACTOR.md` for the module layout and
  the reasoning behind it.
- Import within `src/` through the `@/` alias, never with relative paths that climb directories.
- Keep model contracts in `src/types/`, which `src/types/index.ts` re-exports as one barrel. Split
  by area: `model.ts` for the declarative model, `runtime.ts` for stored objects and relations,
  `modelAdmin.ts` for drafts and releases, and `ui.ts` for state the browser owns such as
  `RouteState` — that is not a model contract and does not belong beside one.
- Generic renderers receive model definitions as input.
- Do not embed object-specific columns, labels or forms in components.
- Resolve a declared view or panel type through its registry in `features/objects/views/` or
  `features/objects/panels/`, and render the result as an element. Calling it as a function puts
  its hooks in the caller's hook list.
- `model/` holds reads over the model and stays free of JSX; presentation belongs in `ui/`.
- Page a collection with `lib/hooks/useCursorPages` for backward movement or `useCursorFeed` for
  append-on-demand. Do not hand-write a cursor stack.
- Recognise an API failure with `isApiError` from `api/errors`, never by reading `code` off a cast,
  and render one with `errorMessage` so users never see an `Error:` prefix.
- Build a dialog with `ui/Modal`, which owns the backdrop, the generated `aria-labelledby`,
  Escape, focus restore, the focus trap and the scroll lock. Do not hand-roll a `.dialog-backdrop`.
- Preserve keyboard operation and semantic HTML.
- Run `npm run lint` and `npm run format` before finishing. `react-hooks/set-state-in-effect` is
  configured as a warning for the reason recorded in `eslint.config.js`; do not add sites to it.

## Definition of done

A change is complete when tests pass, linting passes, the frontend builds, new configuration is
validated, documentation matches the implementation, and no branch was added for a starter
application or object-type key.

Concretely: `pytest` and `ruff check app/ tests/` in `backend/`, and `npm run lint`, `npm run test`
and `npm run build` in `frontend/`. The frontend lint step must report zero errors; warnings are
listed in `eslint.config.js` with their justification.
