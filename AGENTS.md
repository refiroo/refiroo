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

### Error handling and regression fixes

- A stack trace is diagnostic data, not an operator-facing error message. Handle expected operational
  failures at the relevant boundary and report what failed, why it failed, the resulting service
  state, the safe recovery action and the information needed when escalating it. Do not require a
  user or operator to interpret a Python, JavaScript, SQL or framework traceback.
- Do not silently discard the underlying cause. Preserve it for controlled debug diagnostics or a
  correlation identifier, while keeping normal logs and API responses concise, safe and actionable.
- Fixing a defect includes a regression test that reproduces the observed failure mode and verifies
  the human-facing error behavior. Also test the adjacent real execution boundary that allowed the
  defect through; unit coverage of the corrected function alone is insufficient.
- When a migration or startup path changes, test clean bootstrap, upgrade from the preceding revision,
  restart, and recovery or actionable refusal after an interrupted migration. Exercise the FastAPI
  lifespan against a real temporary database and perform a final smoke start against the configured
  development database or an isolated copy of it.
- Validation reports must state what was actually exercised and any remaining limitations. Never use
  a broad claim such as “the application works” based only on passing unit or fixture-level tests.

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

For startup or migration changes, completion additionally requires the startup and interrupted-
migration checks in the error-handling section above; a green unit suite alone is not sufficient.

Concretely: `pytest` and `ruff check app/ tests/` in `backend/`, and `npm run lint`, `npm run test`
and `npm run build` in `frontend/`. The frontend lint step must report zero errors; warnings are
listed in `eslint.config.js` with their justification.

## Agent orchestration

The primary agent owns scope, coordination, final integration and the final answer.

For implementation work packages:

1. Delegate targeted code-path discovery to the `explorer` agent.
2. Use the `architect` agent only when requirements or architectural boundaries
   remain genuinely ambiguous.
3. Delegate implementation to one `implementer` agent.
4. After implementation, delegate focused verification to the `test_runner` agent.
5. For substantial or cross-module work, delegate final review to the `reviewer` agent.
6. The primary agent resolves review findings and performs final verification.

Use configured subagents automatically without requiring the user to request them
in every prompt.

### Model allocation

- Use Luna for targeted searches, code-path mapping, mechanical checks and test execution.
- Use Terra for normal implementation, debugging and code review.
- Reserve Sol for orchestration, difficult architecture decisions, conflicting
  requirements and complex failures that Terra could not resolve.
- Do not let subagents inherit Sol merely because the primary agent uses Sol.
- Start with low or medium reasoning and increase it only when the task demonstrates
  that deeper reasoning is needed.

### Proportional use

Do not run the full agent sequence for every change.

- Small localized change: one Terra implementer, then focused verification.
- Normal work package: Luna explorer, Terra implementer, Luna test runner.
- Large cross-module work package: parallel read-only exploration where useful,
  then one Terra implementer, test runner and Terra reviewer.
- Architectural decision: Sol architect before implementation.
- Failed implementation: return the concrete failure to the same agent first;
  escalate to Sol only when the failure requires architectural reasoning.

Do not spawn multiple agents to independently analyse the same code.

### Editing and concurrency

Read-only agents may run in parallel when examining independent areas.

Only one agent may write to a given module at a time. Prefer one implementation
owner for the complete work package when backend and frontend changes are coupled.

Do not run implementation and review concurrently. Review the completed diff.

Subagents must preserve unrelated working-tree changes and must not commit,
revert or rewrite another agent's work.

### Context discipline

Give each subagent only:

- the active work-package specification;
- relevant acceptance criteria;
- relevant architecture constraints;
- the files or modules it is expected to inspect.

Subagents should use targeted search rather than reading the whole repository.
They must return concise findings with file and symbol references, without raw
logs or a complete narration of their work.

The primary agent should reuse subagent findings and must not repeat the same
repository-wide exploration unless the evidence is incomplete.

### Work-package completion

The objective is a completed, verified work package, not merely an implementation
plan.

When a work package is too large to implement safely as one ownership unit, stop
after discovery and propose explicit independently deliverable slices. Do not
silently divide one work package into overlapping implementation tasks.