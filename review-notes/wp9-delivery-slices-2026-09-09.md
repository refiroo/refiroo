# WP9 discovery and proposed delivery slices

Baseline: `main`, `b38aadc` (WP8.1-C). WP8.1-A/B/C are committed. Existing
untracked `review-notes/` content is preserved. No runtime files changed and no
commit requested. This proposal does not amend the approved delivery plan.

Authority: [WP9](../docs/BASE_0_6_IMPLEMENTATION_PLAN.md#wp9--complete-generic-browser-tasks-in-live-draft-and-history-contexts),
[ADR-027](../docs/DECISIONS.md#adr-027--consolidate-live-data-draft-sources-and-reviewed-historical-migration),
[acceptance scenarios](../docs/product-functionality/ACCEPTANCE_SCENARIOS.md),
[interaction specification](../docs/BASE_0_6_INTERACTION_SPEC.md), and
[API contract](../docs/API.md).

## Why slice before implementation

AGENTS.md requires stopping after discovery and proposing independently deliverable
slices when a package is too large to implement safely as one ownership unit.
WP9 spans route state, context propagation, restored CRUD, new workspace lifecycle
screens, pinned historical model resolution, and real-browser acceptance. These
can be delivered sequentially with observable outcomes and separate regression gates.

Observed execution-path gaps:

- `frontend/src/features/objects/ObjectDetail.tsx` calls `api.object` without
  workspace context on initial load and retry, and forces every panel read-only.
- `frontend/src/api/client.ts` has no context argument for single-object reads,
  and lacks workspace draft/revision lifecycle adapters. Most mutation adapters
  lack draft concurrency context; deletion carries some draft options already.
- `frontend/src/types/ui.ts` routes select a workspace but no data draft/revision.
  `app/useRouter.ts` loads the current model rather than a selected historical definition.
- `features/objects/CollectionView.tsx` owns paging inside the mounted collection;
  `App.tsx` unmounts it for details. Collection errors also hide previously loaded rows.
- Existing `ObjectFormDialog` and panel forms provide reusable generic controls,
  but their existence does not prove reachable complete authoring journeys.
- No repository browser/e2e harness was found by filename search. Browser tooling
  and isolated-backend setup must be established for the first slice's evidence.

## Sequential delivery units

Each unit has one implementation owner and receives focused regression coverage,
final frontend format/lint/test/build, and diff validation. Run both stack gates
if backend code or public contracts change. Prove the named journey against a real
backend with isolated data; mocked component results alone do not close it.

### A — Reliable live workspace navigation (recommended first) COMPLETED

Outcome: open a record in a non-default workspace, follow related/parent records,
retry failed reads, and return to the same filtered page with the workspace label
and successful content preserved.

Scope: live read adapters, routing/collection restoration, shell context and detail
panel/lookup reads. Preserve canonical API resources and existing cursor helpers.
Do not add speculative draft infrastructure in this slice.

Exit: SC-01 with two configured types, two workspaces, a later page and numeric/date
filters; panel empty/error/retry cases; initial detail and retry both demonstrably
use the selected workspace. Add adjacent adapter and app navigation regressions.

### B — Complete direct live authoring COMPLETED

Outcome: reachable generic Add/Edit/Delete, individual field controls, ordinary
relationships and translations, without creating a draft or publication.

Scope: reuse and complete coherent forms for core fields, typed attributes, parent
and required initial connections; wire signed deletion-impact preview/confirmation;
preserve input on validation and version conflicts and show current content for
explicit reconciliation. Derive read-only behavior from catalogue retirement.

Exit: SC-02/SC-03 and the live portion of SC-04, with two types and two
ownership/containment cases, zero/false values, atomic required connections,
stale deletion preview refusal, cancellation, keyboard/focus and narrow layout.

### C — Optional current-live drafts and publication COMPLETED

Outcome: explicitly create a draft from current live data, edit it through the
same generic controls, validate and activate reviewed changes, or discard it.
Ordinary live editing remains independently available.

Scope: Live/Drafts context routes, lifecycle adapters/types/UI, shared CRUD context
and aggregate version handling, draft source labels and activation conflict feedback.
Get current aggregate version from the draft resource; do not assume draft record
reads always supply it. Preserve entered fields on record and aggregate conflicts.

Exit: SC-05/SC-06 and draft SC-04. Include no-publication live bases, post-publication
edits, unrelated live changes surviving activation, touched-record conflicts and
invalid merged graph publishing nothing. Reuse slice B controls, not nested CRUD.

### D — Immutable history and historical draft sources

Outcome: browse newest-first revision history, inspect with its pinned supported
definition, start an explicitly labelled draft from history, and retire a current
publication with truthful confirmation that live data remains available.

Scope: History routes/model resolution, historical read context in shared panels,
source-versus-superseded labels, retryable history paging, immutable controls and
historical/current model mismatch explanations that preserve drafts and input.

Exit: SC-08, including old/new model typing, catalogue retirement versus publication
retirement, loaded history retained on paging failure, and refusal of unsupported
historical schemas without interpreting them under the current model.

## Boundaries and evidence

The units are sequential and independently reviewable; later units extend the
earlier working journeys. Completing A is not completing WP9. WP9 closes only
after SC-01–SC-06 and SC-08 meet the package's browser/real-backend exit criteria.
Track exact E1/E2/E3 evidence gaps separately. WP10 still owns composed release,
accessibility/visual, migration/lifespan, wheel and public-contract acceptance.

No specialist views, workspace administration redesign, schema migration/override,
global-model replacement from history, or model-workbench redesign is included.

Initial discovery used source and contract inspection only. The user subsequently
authorized slice A; it is implemented and verified on 2026-09-10. See
[completion evidence](wp9-a-evidence-2026-09-10/README.md). Slice B is implemented on 2026-09-10; see its
[completion evidence](wp9-b-evidence-2026-09-10/README.md). Slice C is implemented and verified on
2026-09-10; see its [completion evidence](wp9-c-evidence-2026-09-10/README.md). Slice D remains open.
