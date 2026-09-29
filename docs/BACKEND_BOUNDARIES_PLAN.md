# Backend boundaries and one write path (Track E)

**Status:** delivered 2026-09-29, after 0.9 Q1 and before Q2 (planned after Q4; brought forward on
request, so Q2–Q4 build on this layout). **Follows:** [BACKEND_STRUCTURE_REFACTOR.md](BACKEND_STRUCTURE_REFACTOR.md)
(F-01 … F-14).

Three packages, E1–E3. None changes an API contract or the database schema: both generated OpenAPI
documents (default and `MODEL_ADMIN_MUTATIONS_ENABLED=true`) are byte-identical to the Q1 baseline,
and no Alembic revision was added. Behaviour notes lists the few places where the result of a
request differs.

## Why

Since the last structural refactor (665c530, 2026-09-05) `backend/app` grew from about 7,900 to
30,000 lines, almost all of it in `services/`, with two problems:

1. **No tiers.** Domain rules, UI read projections, response builders, flush-hook indexes and generic
   helpers sat side by side in `services/`. Eight services built API DTOs, four imported FastAPI, and
   the model registry imported the FastAPI `DbSession`. Seven modules formed an import cycle held
   together by function-level imports, and 22 imports took `_private` names from another module.
2. **Every write existed twice.** Live writes checked the rules against live tables; change-set
   writes checked the same rules again against the change set lookup; the mapping replacement had a
   live and a change-set twin of every step.

0.9 would have multiplied the second problem: B1 adds batch items live and in a change set, B3 has
the mapping PUT and `replaceRelationSet` share one service, and F1 requires every live write path to
take the workspace lock first.

## Layout

```
backend/app/
├── main.py, config.py, db.py          app factory, settings, engines and migrations (db.py: no FastAPI)
├── errors.py                          ApiError, the engine's error (no FastAPI)
├── common/                            helpers that know neither the model nor the API
│   ├── pagination.py, cursors.py      keyset paging, signed cursors
│   ├── encoding.py                    JSON form of stored data (was FastAPI's jsonable_encoder)
│   └── time.py, json_pointer.py
├── models/
│   ├── schema.py                      the model contract; EngineModel.allowed_relation, containment_relation_keys
│   ├── commands.py                    write inputs the engine accepts (object, relation, mapping, workspace)
│   └── database.py, search_index.py   persistence
├── engine/                            the domain: no FastAPI, no API schemas
│   ├── model/                         compile, validate, registry, releases, placements, metadata IDs
│   ├── records/
│   │   ├── rules.py                   every write rule, once
│   │   ├── refusals.py                where live and change sets word a refusal differently (E-D4)
│   │   ├── context.py                 LiveLookup, ChangeSetLookup, load_object
│   │   ├── writes.py                  LiveWrites, ChangeSetWrites: the only writer of record rows
│   │   ├── values.py                  one attribute value in its forms
│   │   └── objects.py, relations.py, attributes.py, deletion.py, audit.py, relation_set_versions.py
│   ├── change_sets/                   access, lifecycle, records, validation, pinning, publish
│   ├── operations/                    restructuring, type_changes, mapping_replacement
│   ├── reads/                         object_query, object_lookup, snapshot_reads, relation_queries,
│   │                                  change_lists, matrix_cells, mapping_projection
│   ├── indexes/                       snapshot_values, matrix_states (flush-hook maintained)
│   └── workspaces/                    catalogue, workspace_audit
├── management/                        the management API (/api/v1), used by the UI and integrations
│   ├── dependencies.py                DbSession, ActiveModelSnapshot, RequestModelSnapshot
│   ├── errors.py                      exception handlers
│   ├── routers/, schemas/             routes; response schemas by area
│   ├── presenters.py, paging.py       engine result → response; page parameters
│   └── projections/                   the API's composed reads: relation matrix, mapping grid,
│                                      parent candidates, model metadata
├── consumer/                          the consumer API; created by C2
└── migrations/, cli/
```

`management/projections/` is where a read builds a page of API schemas directly. The relation
matrix, mapping grid and parent candidates are views of the management API, not reads the consumer
tier would reuse, so they stay whole instead of duplicating every response class as an engine
dataclass.

### Tier rules

| Module | May import | Must not import |
| --- | --- | --- |
| `common` | `common`, `errors`, `config` | anything else in `app` |
| `models.schema` | `common` | anything else in `app` |
| `engine` | `common`, `models`, `errors`, `db`, `config` | `management`, `consumer`, `fastapi`, `starlette` |
| `management` | everything above | `consumer` |
| `consumer` | everything above `management` | `management` |

Every module imports at module level, never another module's `_private` name, and no two modules
import each other, directly or around a cycle. Inside `engine`, only `operations` imports
`operations`. Only `engine/records/writes.py` constructs a record, relation or attribute-value row,
live or in a change set, or names their tables in a Core insert, update or delete.
`tests/test_boundaries.py` (group `contract`) checks all of it from the imports and calls; its
allowlist is empty.

## The duplicates and their single version

| Rule or step | Before | After |
| --- | --- | --- |
| Application and object type identity | `objects.get_object_type` + `validate_application_object_type`; `change_sets._validate_object_identity` | `rules.object_identity` |
| Binding lookup | `relations.find_allowed_relation`; `change_sets._normalize_relation`; 11 inline scans of `objectTypeRelations` | `EngineModel.allowed_relation`, `rules.relation_binding` |
| Relation attributes | `relations.validate_relation_attributes`, called three ways | `rules.relation_attributes` |
| Attribute uniqueness | SQL in `attributes.check_attribute_uniqueness`; `change_sets._validate_change_set_attribute_uniqueness` | `rules.unique_values` over the lookup |
| Parent validity and cycles | `objects.validate_parent` + `_would_create_parent_cycle`; `change_sets._validate_candidate_parent` (also in validation) | `rules.parent` over the lookup |
| Cardinality and ancestor scope | `relations.validate_cardinality`, `validate_unique_to_ancestor`; `change_sets.validate_change_set_relation` | `rules.relation_cardinality`, `rules.relation_scope`, `rules.relation` |
| Required initial relations | `objects._require_initial_relations`; inline in `write_new_change_set_object` | `rules.required_initial_relations` |
| Containment keys | `parent_relation_keys` and inline `parentRelationTypeKeys` reads | `EngineModel.containment_relation_keys` |
| Row writes | 6 modules writing live rows, 3 writing change-set rows | `LiveWrites`, `ChangeSetWrites` |
| Mapping replacement | a live and a change-set function for each step (1,039 lines) | one flow over a lookup and a unit, two small side adapters (646 lines) |
| Version claims | `claim_object_version`, `claim_relation_version`, `_claim_change_set` | `LiveWrites.claim_object`, `claim_relation`, `ChangeSetWrites.claim` |
| Chunking | `_chunks` ×3 | one per lookup module |

What stays different between the contexts is **policy**, carried by the context rather than branches
in the rules: which claim a write takes, which checks a change set defers to whole-graph validation,
what each context records in the audit log, and the wording in `refusals.py`.

### Wording that still differs (E-D4)

`tests/test_rule_parity.py` provokes 31 rule violations live and in a change set, on the example
model and its renamed copy, and pins what each context answers. 15 answer alike. These differ, each
kept as it was and stated once in `refusals.py`:

| Violation | Live | Change set |
| --- | --- | --- |
| Unknown object type | 404 `unknown_object_type` "…not found" | 422 "…is not in the pinned model" |
| Unknown application | 404 `unknown_application` | 422 `object_type_not_in_application` |
| Type not in application | 422 `invalid_object_type_for_application` | 422 `object_type_not_in_application` |
| Unknown relation type | 404 `unknown_relation_type` | 422 |
| Parent that does not exist | 404 `object_not_found` | 422 `parent_wrong_scope` |
| Relation endpoint that does not exist | 404 `object_not_found` | 422 `relation_endpoint_missing` |
| ID already taken | "An object with ID '…' already exists" | "Object '…' already exists" |
| Duplicate unique value | "Attribute '<name>' must be unique", no details | "Attribute '<key>' must be unique in the change set", with the holder |
| Containment relation written directly | one message for create and delete | a message per operation |
| Required relation deleted | "…cannot be deleted independently" | "…cannot be deleted directly" |
| Two identical initial relations | 409 `cardinality_violation` | 422 `duplicate_initial_relation` |
| `atLeastOneOf` broken by an update | 422 `object_attribute_rule_violation` | accepted; whole-graph validation reports it and publish refuses it |
| Empty string in a unique attribute | not a value | a value |

Settling E-D4 means choosing one answer per row, as a contract change with its API.md entry.

## Behaviour notes

Single-rule refusals are unchanged (pinned by the parity test). These results can differ:

- **Precedence when one request breaks two rules.** The rules run in one order in both contexts now:
  parent required → parent exists → scope → parent type → cycle; binding → containment → cardinality
  → scope → attributes. Before, live checked a cycle before the parent type, and a change set checked
  relation attributes before containment and cardinality. A request that breaks two of these may
  now get the other error.
- **`features.parent`.** The change-set path also treated a binding with an undocumented
  `features.parent` as a containment relation. Nothing declares it, so the rule uses
  `parentRelationTypeKeys` only.
- **Mapping replacement in a change set** checks the ancestor scope like the live path, instead of
  the full relation rule. The binding, containment and cross-cardinality checks it dropped are the
  ones the replacement already makes before.

## Delivered packages

- **E1 — tiers and moves.** The layout above; `models/api.py` split into `management/schemas/` and
  `models/commands.py`; response builders into presenters and projections; `DbSession` and the
  request model dependencies into `management/dependencies.py`; exception handlers into
  `management/errors.py`; `common/encoding.py` in place of `jsonable_encoder` in the engine, pinned
  against FastAPI's output by `tests/test_encoding.py`; the mapping version conflict raised by the
  engine as `MappingVersionConflict`, with the grid continuation added by the route.
- **E2 — one rule set.** The parity inventory first, then `rules.py`, `refusals.py`, `LiveLookup`
  and `EngineModel.allowed_relation`; live writes, change-set writes, whole-graph validation, type
  changes, restructuring and the mapping replacement call the same rules.
- **E3 — one write path.** `writes.py`; every record, relation and attribute-value row goes through
  it, including the publish merge (`LiveWrites.apply_publication`) and deletion
  (`remove_records`). `LiveWrites._begin` is the empty seam F1 fills. The mapping twins collapsed.
  `change_sets` became a package with public names for what type changes and restructuring use
  (`load_change_set`, `change_set_model`, `place_record`, `stored_attributes`,
  `advance_relation_sets`, `require_record_version`); the import cycles and function-level
  imports are gone.

Deviations from the plan: `change_sets` has `access.py` and `lifecycle.py` besides the four planned
modules (lifecycle and pinning needed a common base without a cycle);
`relation_set_versions.py` stayed in `engine/records/` beside the writes that advance it; the
exit "no inline scan of `objectTypeRelations`" applies to binding lookups, not to model validation
or selections by other criteria.

## Effect on later 0.9 packages

- **B1:** a batch item calls the operation its single-write route calls; the same-codes test stays
  as the guard. `models/commands.py` holds the item shapes.
- **B3:** the mapping replacement is one flow over both contexts; B3 extends it to a set.
- **F1:** the feed position goes into `LiveWrites._begin`; `test_boundaries` already refuses a live
  row written outside the unit, so the delivery note lists one path, not an audit of every route.
- **C2:** creates `app/consumer/`, already constrained to read through `engine`, never `management`.

## Composable domains check (ADR-032)

E touches the code of identity, attribute storage and audit, but not their contract or storage: no
door in COMPOSABLE_DOMAINS.md is affected.

## Decisions

| # | Question | Decision |
| --- | --- | --- |
| E-D1 | Name of the UI-facing tier | `management`, as the docs call the API at `/api/v1` |
| E-D2 | How the tiers are enforced | Own `ast` test in `contract`; no import-linter dependency |
| E-D3 | Engine errors | The engine keeps raising `ApiError` (status and code) |
| E-D4 | Wording that differs between live and change sets | Kept; listed above; each settled later as a contract change |
| E-D5 | Timing | Delivered after Q1 on request |

## Verification

- Every backend group once (`model`, `model_admin`, `startup`, `records`, `queries`, `workspaces`,
  `change_sets`, `mapping`, `matrix`, `contract`, `volume`), the explicit exception to the
  package-level test rule for a refactor that moves every module: 852 cases, 851 passed at first. The
  one failure, `test_w6_workspace_deletion::test_live_write_resolved_before_deletion_saves_nothing`,
  held a create by patching `resolve_workspace` on the workspace catalogue; E3 made the create
  import it at module level, so the hold now patches the object module's reference. The file then
  passed (8 cases); the race behaviour (`404 workspace_not_found`, no orphan row) is unchanged.
- New: `test_boundaries` (tiers, private names, function-level imports, cycles, the single row
  writer; empty allowlist), `test_rule_parity` (31 violations × two contexts × two models),
  `test_encoding` (the engine's JSON encoding against FastAPI's).
- Both OpenAPI documents byte-identical to the Q1 baseline; `ruff check app/ tests/` clean; every
  `from app… import` in `app/` and `tests/` resolves, and every module attribute a test patches exists.
- A real Uvicorn process on a copy of the development database serves health, capabilities, a paged
  lookup, workspaces and placements, and renders a refusal through the moved exception handler.
- Not run: the frontend suites and build (no frontend file changed, and the API contract is
  unchanged), browser runners and the accessibility and visual gates (no UI change).
