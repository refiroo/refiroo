# WP8 implementation and current-diff review

Reviewed 2026-09-08 against HEAD `60b99d3` plus the existing uncommitted WP8 implementation,
tests, audit migration and documentation. Existing unrelated changes are preserved; nothing is
staged or committed. This is implementation evidence, separate from the earlier documentation-only
reconciliation in `docs/REVIEW.md`.

Follow-up 2026-09-09 implemented the user-confirmed locked-hierarchy deletion contract and reran the
complete validation listed below.

## Confirmed defects corrected

| Severity | Finding and consequence | Correction and direct evidence |
| --- | --- | --- |
| P1 | Activation removed an old parent before updating its surviving child's parent pointer. A valid reparent-and-delete draft failed with FK enforcement. | Detach affected pointers transactionally before deletion, then restore the validated final graph after all new parents exist. API regression publishes to a newly created parent and verifies immutable old history. |
| P1 | Live cascade queued ORM deletes in a presumed depth order, which does not control batched SQL ordering under `RESTRICT`. Activation also relied on disabled SQLite FK cascades to remove attribute rows. | Detach the deletion set before the ORM flush and explicitly delete removed attributes. Tests exercise real SQLite foreign keys and check removed values. |
| P1 | Live and draft deletion silently unlinked non-parent associations without the documented confirmation; undirected required relationships incorrectly conferred ownership. | Both paths return `409 object_has_dependants` before any change. Only oriented required one-to-one/one-to-many bindings cascade to their targets. Four API cases cover live/draft and optional/directed versus required/undirected edges, retained endpoints, audit and versions. |
| P1 | Draft concurrency only compared cached ORM versions; two sessions could both save expected version 1 and silently overwrite each other. | Conditional database version claims protect draft edits/discard and activation. A two-session stale-instance regression reproduces the lost update and verifies the winning name/version survives. Activation claims before reading the merge population, obtaining SQLite's writer lock. |
| P2 | Live relation GET used an internal primary-key lookup with a public UUID, returning 404 for an existing relation and potentially accepting sequence IDs. | Use the canonical public-ID loader. API tests cover the created UUID, a missing UUID and rejection of the internal sequence ID. |
| P2 | Publication retirement mutated a catalogue-retired workspace. | Return `409 workspace_retired` and preserve publication/audit state. |
| P2 | Draft attribute deletion ignored `readOnly`; whole-graph validation rejected valid stored/defaulted read-only values. | Reuse the common deletion validator; graph validation allows stored read-only content while retaining type/constraint checks. Tests preserve value, record/draft versions and audit, and activate graphs containing read-only defaults. |
| P1 | Draft writes and whole-graph validation permitted non-root-creatable records without parents. | Validate required parents, application scope, permitted parent types and cycles for draft writes and again at publication. API regression covers create/update refusal and activation refusal for a previously persisted invalid candidate. |
| P1 | Activation checked new IDs only within its own workspace, so a collision in another workspace reached a database uniqueness failure. | Reject existing live/effective object IDs on draft creation and check authored object/relation IDs against the global live namespace during merge. A late cross-workspace collision now returns `409 version_conflict` / `id_collision`, preserving the draft and audit. |

The new regressions are in `backend/tests/test_wp8_review_regressions.py`. Two legacy assertions
in `test_api.py` and `test_cascade_delete.py` expected silent association removal despite the API
contract. They now assert the preview or provide explicit cascade confirmation. Parent-containment
edges alone still permit deleting a leaf without cascade. Numeric-query fixtures now create the
required containment parent, and the cycle diagnostic test first asserts API refusal before injecting
invalid persisted content to exercise the separate graph-validation boundary.

## Documentation comparison and remaining packages

**Resolved P1: changed deletion impact after preview (SC-04).** The preview now returns an opaque
signed token over the workspace/draft and model context plus every affected object and relationship
identity, version and containment pointer. `cascade=true` requires that token. Confirmation locks or
claims the applicable mutation boundary, rebuilds the hierarchy and rejects a mismatch with `409
deletion_preview_changed` and the message `The object was modified by another session. Please retry.`
The rejected request persists no deletion or audit event. Direct tests cover an added descendant in
both live and draft contexts, a changed child record, missing/tampered tokens, unchanged confirmation
and retained data. Missing-token rejection is deterministic even for a stale root. Draft deletion
also validates the object type in the route, and its token is bound to that type.

Live deletion conditionally claims active workspace status in the same transaction, so concurrent
catalogue retirement cannot pass between the status decision and deletion. It refuses malformed
containment or relationship edges that cross workspace boundaries. The frontend API adapter carries
the token and the draft ID/version when applicable. There is no reachable object-deletion browser
control in the current WP8 UI; WP9 must display the existing backend message through the generic error
renderer when it connects that control. This correction is distinct from WP8.1-A/B/C below.

ADR-026/027, `PRODUCT.md`, `ARCHITECTURE.md`, `APPLICATION_MODEL.md` and `API.md` establish live
maintenance with optional drafts. Historical WP8 draft-only wording is explicitly labelled as
superseded in the implementation plan; it must not be restored as current behavior.

The following substantial gaps were confirmed in current code and are already assigned explicit,
independently deliverable slices in `docs/BASE_0_6_IMPLEMENTATION_PLAN.md`. This bounded WP8 defect
fix does not mark those slices complete:

- **WP8.1-A:** compatibility still filters through publication membership instead of all live rows;
  historical response/query paths still use current model metadata; explicit context mismatches need
  consistent enforcement. Deliver the live population and pinned supported-model read boundary with
  model-switch API evidence together.
- **WP8.1-B:** draft creation still starts empty or derives from a publication. It does not capture
  immutable current-live data including post-publication edits. Deliver the explicit source contract,
  internal base persistence and upgrade preservation as the documented schema/API slice.
- **WP8.1-C:** revision discovery remains oldest first. Deliver newest-first bounded paging and the
  complete publication-retirement/live-mutability acceptance scenarios as the documented slice.

These packages remain prerequisites for dependent WP9 acceptance. The repository requires proposing
separate deliverable slices when the complete package exceeds one safe ownership unit; the existing
A/B/C plan already supplies those boundaries. No WP9 UI or product-0.10 migration work was added here.

## Validation

- Baseline before corrections: **312 backend tests passed**, 52 dependency warnings.
- Final backend suite: **336 passed**, 124 dependency warnings; no skips. Includes OpenAPI inventory
  and digest checks. Ruff passed.
- New audit migration tests exercise upgrade from **20260907_03** to **20260908_01**, preserve audit
  events and their object subjects, restart successfully, and simulate interrupted Alembic batch-copy
  DDL. The latter preserves both tables and reports actionable maintenance-mode refusal with health
  503, revision identities, backup/recovery instructions and no normal traceback.
- Existing lifespan/migration tests exercise clean bootstrap and earlier upgrade/recovery paths.
- An SQLite online backup of the configured development database was started and restarted in
  isolation: health and model endpoints returned **200** on both starts. The configured database was
  opened read-only for backup and was not upgraded or modified.
- Python 3.14 wheel built with `pip wheel . --no-deps --no-build-isolation`, installed into a temporary
  target, and booted against a new temporary database. The packaged WP8 migration was present; health
  and model reads returned **200** using the installed package outside the checkout.
- Frontend: **92 tests passed**, production build passed, lint **0 errors / 13 warnings**, formatter
  made no changes. The API adapter now carries the signed preview token; no browser workflow was added.
- `git diff --check` passed.

Warnings are the existing Starlette/httpx, SQLite datetime-adapter and frontend hook warnings.
No real-browser/accessibility/visual journey or PostgreSQL concurrency/upgrade test was run. SQLite
constraint tests and database-conditional draft claims are not evidence of complete multi-writer
PostgreSQL graph isolation. WP8.1–WP10 and documented production-hardening gates remain open.
