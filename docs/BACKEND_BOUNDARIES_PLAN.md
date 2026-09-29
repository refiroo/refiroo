# Backend boundaries and one write path (Track E)

**Status:** proposed 2026-09-29, not yet in the 0.9 delivery queue. **Runs:** after Q4, before B1.
**Follows:** [BACKEND_STRUCTURE_REFACTOR.md](BACKEND_STRUCTURE_REFACTOR.md) (F-01 … F-14).

Three packages, E1–E3. None of them changes an API contract or the database schema: both generated
OpenAPI documents stay byte-identical to the Q4 baseline, and no Alembic revision is added.

## Why now

Since the last structural refactor (665c530, 2026-09-05) `backend/app` grew from about 7,900 to
30,000 lines, almost all of it in `services/`. Two problems grew with it:

1. **No tiers.** `services/` holds domain rules, UI read projections, response builders, flush-hook
   indexes and generic helpers side by side. Eight services build `models/api.py` DTOs, three import
   FastAPI (`jsonable_encoder` only), and `services/model/registry.py` imports the FastAPI
   `DbSession` dependency from `db.py`. Seven modules form an import cycle (attributes, objects,
   relations, workspaces, snapshot_reads, matrix_cells, matrix_states) held together by
   function-level imports, and 22 imports take `_private` names from another module, most of them
   `type_changes` and `restructuring` borrowing from `change_sets`.
2. **Every write exists twice.** Live writes check the rules against live tables (`objects.py`,
   `relations.py`, `attributes.py`, `deletion.py`); change-set writes check the same rules again
   against `ChangeSetLookup` (`change_sets.py`); `mapping.py` carries a live and a change-set twin of
   each replacement step. Six modules write live rows.

0.9 multiplies the second problem. B1 adds batch items "live and in a change set" tested against
their single-write routes; B3 has the mapping PUT and `replaceRelationSet` share one service; F1
requires that **every live write path takes the workspace lock first**, audited path by path, with
one feed entry per change. Built on today's code, each of those lands in every write path twice.
After E, each lands once.

## Target layout

```
backend/app/
├── main.py, config.py, errors.py      app factory and settings (unchanged)
├── db.py                              engines, sessions, migrations; no FastAPI import
├── common/                            helpers: know nothing about the model or the API
│   ├── time.py, json_pointer.py, chunks.py
│   ├── pagination.py, cursors.py      ← services/
├── models/
│   ├── schema.py                      the model contract (unchanged)
│   ├── database.py, search_index.py   persistence (unchanged)
├── engine/                            the domain; no FastAPI, no API schemas
│   ├── model/                         ← services/model/ (compiler, validation, registry, releases, placements, …)
│   ├── records/                       rules and writes for objects, relations, attribute values
│   │   ├── context.py                 RecordContext: LiveContext, ChangeSetContext (← change_set_lookups)
│   │   ├── rules.py                   every write-time rule, once, over a RecordContext
│   │   ├── writes.py                  WriteUnit: claim, lock seam, rows, audit, set versions, index notes
│   │   ├── attributes.py, objects.py, relations.py, deletion.py
│   │   └── audit.py
│   ├── workspaces/                    workspaces, workspace_audit, relation_set_versions
│   ├── change_sets/                   ← change_sets.py: records.py, validation.py, pinning.py, publish.py
│   ├── operations/                    multi-record operations: restructuring, type_changes, mapping_replacement
│   ├── reads/                         object_query, object_lookup (Q1), snapshot_reads, relation_queries,
│   │                                  change_lists, parent_candidates, relation_matrix, matrix_cells, mapping reads
│   └── indexes/                       flush-hook maintained: snapshot_values, matrix_states
├── management/                        the management API (/api/v1), used by the UI and integrations
│   ├── dependencies.py                DbSession, ActiveModelSnapshot (← db.py, routers)
│   ├── routers/                       ← routers/
│   ├── schemas/                       ← models/api.py, split by area
│   ├── presenters.py, paging.py       every engine result → DTO
├── consumer/                          the consumer API (/api/consumer/…); created by C2, empty until then
├── migrations/, cli/                  unchanged
```

"Internal API" in earlier discussion is the management API: the UI has no API of its own, and the
docs already name the two tiers management and consumer (CONSUMER_API.md).

### Tier rules

| Module | May import | Must not import |
| --- | --- | --- |
| `common` | `common`, `errors` | anything else in `app` |
| `models.schema` | `common` | anything else in `app` |
| `engine` | `common`, `models`, `errors`, `db`, `config` | `management`, `consumer`, `fastapi`, `starlette` |
| `management` | everything above | `consumer` |
| `consumer` | everything above `management` | `management` |

Plus two rules for every module: no `from x import _name` across modules, and no function-level import
of an `app` module. Inside `engine`, `reads` never imports `records.writes`, and nothing imports
`operations`.

`tests/test_boundaries.py` (group `contract`) checks these rules by reading imports with `ast`, so
no dependency is added. E1 lands it with an allowlist of today's violations, each entry naming the
package that removes it; E3's exit is an empty allowlist.

## Where each file goes

| Now | After E |
| --- | --- |
| `services/model/**` | `engine/model/**` |
| `services/attributes.py` | `engine/records/attributes.py` (conversion) + `rules.py` (checks) |
| `services/objects.py` query half (filters, sorts, `build_object_query`) | `engine/reads/object_query.py` |
| `services/objects.py` write half | `engine/records/objects.py`; `build_object_responses` → `management/presenters.py` |
| `services/relations.py` | `engine/records/relations.py`; `build_relation_response` → presenters |
| `services/deletion.py`, `audit.py` | `engine/records/` |
| `services/change_set_lookups.py` | `engine/records/context.py` as `ChangeSetContext` |
| `services/change_sets.py` | `engine/change_sets/{records,validation,pinning,publish}.py` |
| `services/workspaces.py`, `workspace_audit.py`, `relation_set_versions.py` | `engine/workspaces/`; response builders → presenters |
| `services/restructuring.py`, `type_changes.py` | `engine/operations/` |
| `services/mapping.py` | reads → `engine/reads/mapping.py`; replacement → `engine/operations/mapping_replacement.py` |
| `services/mapping_projection.py`, `snapshot_reads.py`, `change_lists.py`, `parent_candidates.py`, `relation_queries.py`, `relation_matrix.py`, `matrix_cells.py`, Q's new modules | `engine/reads/` |
| `services/snapshot_values.py`, `matrix_states.py` | `engine/indexes/` |
| `services/pagination.py`, `cursors.py` | `common/` |
| `routers/**`, `models/api.py` | `management/routers/**`, `management/schemas/*.py` |
| `DbSession` in `db.py` | `management/dependencies.py` |

## The duplicates and their single version

| Rule or step | Live today | Change set today | After E |
| --- | --- | --- | --- |
| Application and object type identity | `objects.get_object_type`, `validate_application_object_type` | `change_sets._validate_object_identity` (also borrowed by restructuring, type changes) | `rules.object_identity` |
| Allowed relation lookup | `relations.find_allowed_relation` | inline `next(…objectTypeRelations…)`; 11 such scans across 10 modules | `EngineModel.allowed_relation(...)` and `rules.require_allowed_relation` |
| Attribute normalization | `attributes.validate_attribute_change` | `change_sets._normalize_object_attributes` | one, in `rules` |
| Attribute uniqueness | SQL in `attributes.py` | `_validate_change_set_attribute_uniqueness` over `unique_value_holder` | `rules`, over `RecordContext.unique_value_holder` |
| Parent validity and cycles | `objects.validate_parent`, `_would_create_parent_cycle` | `change_sets._validate_candidate_parent` | `rules.parent`, over `RecordContext` ancestors |
| Containment edge kept with the parent | `objects.replace_parent_relation` | `_sync_change_set_parent_relation`, `sync_containment_edge` | `WriteUnit` |
| Cardinality and ancestor-scope uniqueness | `relations.validate_cardinality`, `validate_unique_to_ancestor` | `validate_change_set_relation` | `rules.relation`, over `RecordContext.relations` |
| Required initial relations | `objects._require_initial_relations` | in `write_new_change_set_object` | `rules` |
| Object, relation, attribute writes | `create_object_record`, `update_object_record`, `set_live_attribute_value`, `*_live_relation`, `delete_object_record` | `put/update/delete_change_set_object`, `*_change_set_relation`, `patch/delete_change_set_attribute` | one operation per entity through a `WriteUnit` for the context |
| Mapping replacement | `_replace_live_mapping`, `_execute_live_*`, `_live_edges`, `_check_live_cross_cardinality` | the `_change_set` twin of each | one replacement over `RecordContext` and `WriteUnit`; B3 extends it to sets |
| Small helpers | `_chunks` ×3, `_edge_other_id` ×2, `_object_types` ×2, `_change_set` ×2 | | `common.chunks` and one owner each |

What stays different on purpose is **policy**, carried by the context, not by branches in the rules:

- which claim a write takes (the record's version live, the change set's version in a change set);
- which rules a change set defers to validation (`_diagnostics`: containment cycles, identity
  collisions and the rest of the change-set-wide checks);
- what the write records (a live audit event, later with a feed position; a change-set row);
- which index the flush hook keeps (live values and matrix states, or `snapshot_attribute_values`).

API schemas that look the same (`ObjectPathPart` and `RelationMatrixPathPart`, `RelationChangeState`
and `change_lists.RelationState`, `ModelChangeResponse` and `diff.SemanticChange`) stay: merging them
renames OpenAPI components. The engine dataclass and its API schema are the intended pair.

## Packages

#### E1: Tiers and moves

**Needs:** Q4. **Scope:** the layout above as moves only: packages created, files moved and split along
the lines in the table, `models/api.py` split into `management/schemas/`, response builders moved into
presenters, `DbSession` moved out of `db.py`, `jsonable_encoder` in services replaced by the engine's
own encoding, `_chunks` and the other copied helpers moved to one owner. `test_boundaries.py` with its
allowlist. AGENTS.md code conventions, the execution guide's path-to-group table and the ARCHITECTURE
paths updated to the new layout.

**Tests:** both OpenAPI documents byte-identical; `test_boundaries`; `ruff`; a real Uvicorn smoke start.
No behavior change, so the moved modules run under their existing groups.

**Groups:** `contract`, `startup`, then each group once for the modules it covers. Moves change every
path, so E1 runs the groups the execution guide selects for all moved boundaries; name them in the
delivery note rather than running the full suite.

**Exit:** every module in its tier; the allowlist lists only what E2 and E3 remove.

#### E2: One rule set

**Needs:** E1. **Scope:** first a **parity inventory**: a test that, per rule, provokes the same
violation live and in a change set on two models and pins the code, status and details each context
returns today. Then `RecordContext` with `LiveContext` beside the existing change-set lookup,
`EngineModel.allowed_relation`, and `engine/records/rules.py` holding each rule once. Live and
change-set writes call the same rules; the inventory must pass unchanged.

The inventory will show where the contexts already differ. Codes found raised by one context only,
such as `duplicate_relation` and `relation_wrong_scope` (live) and `object_type_not_in_application`
(change set), stay as they are in E2 and go to decision E-D4, not silently aligned.

**Tests:** the parity inventory; the existing `records`, `change_sets`, `mapping` groups for the changed
paths; `volume` for the change-set write budget (S2b lookups) and the live write budget.

**Groups:** `records`, `change_sets`, `mapping`, `volume`, `contract`.

**Exit:** no rule implemented twice; no inline scan of `objectTypeRelations` outside `models/schema.py`.

#### E3: One write path

**Needs:** E2. **Scope:** `WriteUnit`, one per context, owning the claim, an empty **lock seam** (F1
fills it), row writes, audit, relation set versions and the index notes (`matrix_states.note_*`,
`snapshot_values`). Objects, relations, attributes, deletion and mapping replacement go through it in
both contexts; the mapping twins collapse into one replacement. `change_sets.py` becomes its package,
with a public API that `type_changes` and `restructuring` use instead of private names. Publish writes
live rows through the unit's batch form. The import cycle and every function-level import go.

**Tests:** existing write tests in both contexts; `matrix_states.verify` on each collapsed mapping path;
publish of 10,000 records against the 0.8 C5 budget (D46); `test_boundaries` with an empty allowlist.

**Groups:** `records`, `change_sets`, `mapping`, `matrix`, `workspaces`, `volume`, `contract`.

**Exit:** one place in the code writes live rows; one writes change-set rows; the allowlist is empty.

## Effect on later 0.9 packages

- **B1:** a batch item calls the same operation as its single-write route, so "same codes as the single
  write" holds by construction; the test stays as the guard.
- **B3:** the mapping replacement is already one service over both contexts; B3 extends it to a set.
- **F1:** "every live write path takes the lock first, audited path by path" becomes the lock in the
  live `WriteUnit` plus a boundary rule that nothing else writes live rows. The delivery note lists
  one path.
- **C2:** creates `app/consumer/`, already constrained to read through `engine` and never `management`.

## Composable domains check (ADR-032)

E touches the code of identity, attribute storage and audit, but not their contract or storage: no door
in COMPOSABLE_DOMAINS.md is affected.

## Decisions

| # | Question | Proposal |
| --- | --- | --- |
| E-D1 | Name of the UI-facing tier | `management`, as the docs already call the API at `/api/v1` |
| E-D2 | How the tiers are enforced | Own `ast` test in `contract`; no import-linter dependency |
| E-D3 | Engine errors | The engine keeps raising `ApiError` (status and code). Separating domain errors from HTTP is a larger change with no current need |
| E-D4 | Codes that differ between live and change set today | Kept in E2; each difference decided afterwards, as a contract change with its own API.md entry |
| E-D5 | Timing | After Q4, before B1, as queue rows 6a–6c |
