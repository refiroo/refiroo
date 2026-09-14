# Architecture findings

## Executive conclusion

Previous reviews checked WP6-WP8 against their accepted ADRs, but did not repeatedly test those ADRs
against the daily journey in `docs/PRODUCT.md`. This produced a locally consistent system that
contradicted the product's reference-data-maintenance purpose.

ADR-026 correctly made live reference data writable without a release ceremony. However, it changed the
data authority without updating compatibility analysis, draft baselines, historical model resolution,
publication retirement semantics or future work packages as one coherent migration.

The architecture needs five explicit authorities:

| Concern | Intended authority |
|---|---|
| Model/schema | Database-selected immutable `ModelRelease` |
| Current reference data | `RdmObject`, `AttributeValue`, `ObjectRelation` |
| Staged coordinated data changes | `WorkspaceDraft*` over an immutable base snapshot |
| Historical data | `WorkspaceRevision*`, interpreted with its pinned model release |
| Publication availability | Unresolved product decision |

Staged workspace data is still data. It must not be described as the application-model release path.

## P0 — model compatibility uses obsolete revision membership

Evidence:

- `backend/app/services/model/compatibility.py:26-35` defines `_is_in_active_workspace()` by joining
  `RdmObject` through `Workspace.active_revision_id` and `WorkspaceRevisionObject`.
- The predicate is reused for object/attribute counts (`:532-550`), uniqueness (`:607-621`), relation
  pairs (`:624-639`), relation attributes (`:645-701`) and required relations (`:705-726`).
- ADR-026 defines the live tables as authority in `docs/DECISIONS.md:566-577,623-629`.
- Compatibility fixtures populate both live rows and revision membership in
  `backend/tests/test_model_compatibility.py:113-162`, masking the discrepancy.

Impact:

- Live-only content can be ignored during model compatibility analysis.
- Clearing `active_revision_id` makes the workspace's live rows invisible to the predicate.
- An incompatible model release can pass analysis and activate over actual live data.

Required correction:

- Analyze authoritative live rows directly, with an explicit rule for catalogue-retired but readable
  workspaces.
- Cover live-only objects, attributes, containment, relations, cardinality and uniqueness.
- Add regressions after an ordinary live write and after revision-checkpoint/publication retirement.

## P0 — fresh current-live draft baselines do not exist

Evidence:

- ADR-026 requires a fresh live snapshot at draft creation in `docs/DECISIONS.md:600-619`.
- `backend/app/services/workspace_revisions.py:145-180` records only optional `source_revision_id`.
- `effective_draft_membership()` at `:57-111` has no live baseline for a root draft.
- `_revision_snapshot_maps()` at `:1058-1080` returns empty maps without a source revision and otherwise
  reads the selected historical revision.
- The plan still says root drafts start empty at `docs/BASE_0_6_IMPLEMENTATION_PLAN.md:125-127`.

Impact:

- A root draft in a populated workspace cannot edit or tombstone existing live records.
- A draft derived from the newest revision can be stale because later live writes do not update it.
- There is no truthful "start a coordinated change from what is live now" operation for WP9.

Decision required:

- Preferred: persist an immutable current-live base snapshot at draft creation, including object and
  relation versions needed for delta/conflict calculation.
- Alternative: define drafts as history branches only and add an explicit current-live
  checkpoint/branch operation.

## P0 — historical reads ignore the revision's pinned model

Evidence:

- `WorkspaceRevision.model_release_id` is stored at `backend/app/models/database.py:321-337`.
- Historical objects use the global active model at `backend/app/routers/objects.py:236-280,332-361`.
- Historical attributes do the same at `backend/app/routers/attributes.py:29-74`.
- Historical relation expansion passes the current model at `backend/app/routers/relations.py:69-93`.
- `docs/DECISIONS.md:504-508` promises pinned immutable model releases.

Impact:

- A new model activation can make old history fail with an unknown object type.
- Historical labels, types, filters and responses can be interpreted using the wrong model.
- The persisted model pin is not an effective runtime contract.

Required correction:

- Resolve and use the revision's `model_release_id` for every historical query and response.
- Test history created under model A after model B changes or removes a type.

## High — publication retirement no longer retires served data

Evidence:

- `backend/app/services/workspace_revisions.py:1512-1535` clears `active_revision_id`.
- Active reads use live rows directly at `backend/app/routers/objects.py:282-304,362-366`.
- `backend/tests/test_wp8_retirement.py:420-447` explicitly locks continued serving.
- `docs/DECISIONS.md:497-502` still says retirement controls whether a dataset is published.

Impact: the operation is revision-checkpoint retirement, not publication retirement. WP9 must not show
"publication retired" while consumers receive the same live dataset without a precise explanation.

Decision required:

- Keep live serving and rename/redefine the operation as checkpoint retirement; or
- Add a distinct publication-availability authority and specify reads/writes while unpublished.

## High — documents and future packages retain the rejected assumption

- `docs/BASE_0_6_IMPLEMENTATION_PLAN.md:32-33,452` still says revisions are authoritative.
- WP9 is selected-draft-only at `:359-373`, while `:441-445` says no draft is required.
- WP10 at `:375-391` omits the new live authority boundaries.
- `docs/ROADMAP.md:120-126,151-155,167-169,183-188` remains draft-first for mapping,
  translation, hierarchy and integration bulk work.
- `docs/APPLICATION_MODEL.md:93-101,155-168` retains draft-only lifecycle explanations.

`docs/REVIEW.md` already records authority prose, cursor, delete-contract and draft-required
contradictions. It must also record the three P0 implementation findings and the retirement decision.

## Why green suites did not reveal this

- Tests validated implementation against accepted ADRs instead of challenging daily product use.
- Compatibility fixtures created matching live and revision rows.
- Retirement tests turned an unresolved semantic change into passing regression behavior.
- Delta-merge tests do not prove a fresh draft base from already-diverged current live content.
- Historical-read tests do not cross a model-release activation boundary.

Future gates must ask: "What does a data owner do every day, and does this design allow it without an
unrelated release ceremony?" They must also re-test every dependent authority when that answer changes.
