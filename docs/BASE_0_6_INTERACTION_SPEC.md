# Base 0.6 interaction specification

**Status:** Accepted product baseline updated from GAP-01–GAP-08, 2026-09-08; implementation and
composed-browser validation remain WP8.1/WP9/WP10 work.

**Authority:** ADR-026/027, `PRODUCT.md`, product stories/scenarios and `BASE_0_6_IMPLEMENTATION_PLAN.md`.
Existing `frontend/src/test/base06AcceptanceFixtures.ts` must be extended to this behavior during
implementation; it is not proof that these revised journeys already work.

## Context and write rules

The trail is `Workspace / Application / View`, with **Live**, a named **Draft**, or a selected
**Historical revision** when applicable. Workspace labels are primary and stable keys stay in routes.
Carry the selected context into details, panels, lookups, related records and history, then restore the
originating same-origin list address and its search, filters, sorting and page position.

| Context | Record actions | Concurrency and meaning |
| --- | --- | --- |
| Live, catalogue active | Add, edit and delete as permitted by the model | Existing-record version; immediate validated save and audit; no draft/revision required |
| Selected data draft | Same generic record controls | Record plus aggregate draft version; changes remain staged |
| Historical revision | Inspect only, start a new draft from history | Pinned supported model; snapshot never edited |
| Catalogue retired | Read only | No data or lifecycle mutation |

Model-defined availability is a field value, not an individual record publication state. Workspace
publication retirement removes the current-publication designation but does not make live data
unavailable or read-only. Data drafts and model-definition drafts are visibly separate.

Collections use typed configured filters and bounded paging. Context/filter/sort changes discard their
continuation. Live cursors are not frozen snapshots and currently survive publication; draft/history
cursors identify their selected context. Do not claim invalidation from a token component that is not
actually encoded.

## Everyday record maintenance

Open a live record, edit the required fields in one coherent form and save once. Root creation starts
from a collection; child or dependent creation starts in its useful context. Preselect known parent or
target and collect the remaining required fields/connections in the same flow. Generic initial
relationships are part of record creation; do not expose low-level repair steps after an invalid save.

Do not require creating, naming, validating or activating a draft for routine maintenance. Preserve
optional individual-field actions, distinguish missing from false/zero/null and retain model-defined
read-only/required constraints. Containment changes through the Parent control, not an editable
engine-maintained relation. Ordinary relation identity is fixed; specialist atomic mapping follows 0.7.

Deletion presents the actual impact on owned dependants and affected links. Cancel changes nothing;
cascade needs explicit confirmation. Independent associated records survive. A successful empty panel
looks empty, while a failed panel explains the failure and retries without resetting successful data.

## Optional workspace data draft

```text
Workspace: Retail Reference / Live
[Add record]                         [Prepare coordinated changes]

Create data draft
Source: Current live data | Selected historical revision
Name: September delivery changes
[Cancel]                                      [Create draft]
```

Current-live creation copies the actual live graph and versions, including edits after publication
and a workspace with no publication. It does not publish a checkpoint just to begin. Historical
creation labels the chosen source revision and pinned model. Empty-root creation is development/
bootstrap support; an empty workspace naturally yields an empty current-live copy.

```text
Workspace: Retail Reference / Draft: September delivery changes / Saved v7
Started from: Live data captured at <time>       Model release: <release>
Historical source: <revision, when applicable>

Records       Relationships       Validation
[Discard draft]                         [Validate] [Review and activate]
```

Reuse record controls, with the draft version carried through each save. Do not add a second “save
all” layer unless a defined unsaved aggregate edit actually needs it. Validation checks the complete
candidate without publication. Activation review shows source, expected current publication, model,
authored changes and validation result. It applies authored changes over current live data, preserving
unrelated live edits; failures preserve draft and live content. No row has an activation button.

## History and publication designation

History is **newest first**, cursor-paged, and displays time, model release, immutable revision identity
and separate “Started from” and “Superseded on activation” references. A live-base capture identity must
not be replaced by a misleading old-publication label. Loaded history survives a failed older-page
request; retry uses the exact continuation.

“Start a draft from this revision” never says “Restore live data.” Newer untouched live records survive
later activation. Opening a historical record uses its supported pinned definition and read-only
controls. Unsupported historical schema versions receive a clear explanation; current definitions
must not be substituted silently.

“Retire publication” confirmation names the selected current revision and says: remove its current-
publication designation; live records and historical snapshots remain available. It is a workspace
operation with the expected revision claim. It does not mark individual records retired. Catalogue
retirement is a separate administrative read-only operation.

## Conflict and failure recovery

| Failure | Preserved state | Next action |
| --- | --- | --- |
| Live or draft record version | Entered fields and persisted data | Review current record, reconcile and explicitly retry |
| Aggregate draft version | Local input and persisted draft | Reload/reconcile current draft version before save or activation |
| Current publication changed | Draft, source and live data | Review current publication and make a fresh activation claim |
| Field/relationship/whole-graph validation | Input, draft and live data | Focus the affected field/record, correct it and check again |
| Historical/current model mismatch | Draft, history and live selection | Show both definitions and migration requirement; cancel/back is available |
| Failed page or panel | Successful loaded content and query context | Retry the failed request without broadening it |

Product 0.10 adds the accepted historical model replacement path: preview incompatibilities and
potential data loss for a named workspace and installed target definition (normally the historical
pin), explicitly confirm the reviewed migration or cancel. Confirmation is bound to
current model/data/draft versions and an executable transformation. It does not waive valid target
data or supported schema parsing. Only the selected workspace assignment changes; other workspaces
are unaffected. Base 0.6 must not present an enabled override button for this future capability.

## Acceptance journeys

Use SC-01–SC-06, SC-08 and the current-foundation portions of SC-12–SC-14 from
[product acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md). They replace the former
seven draft-only journey definitions as the complete release gate. Preserve these legacy labels for
fixture migration and traceability:

| Legacy label | Revised behavior / product scenario |
| --- | --- |
| J1 context | SC-01: non-default context through the whole task |
| J2 find/open/return | SC-01: typed query and exact list return |
| J3 create | SC-02/SC-03: normal live authoring; SC-05: optional copied draft |
| J4 coordinated edit | SC-06: draft changes staged, unrelated live work preserved |
| J5 source lineage | SC-08: historical source distinct from supersession, no direct restore |
| J6 retirement | SC-08: designation removal distinct from catalogue retirement and availability |
| J7 recovery | SC-02/SC-04/SC-06: preserved input, atomic refusal and retry |

Exercise at least two record types and ownership/containment configurations. Retain desktop
`1280 × 800` and narrow `390 × 844` fixture targets, then report actual real-browser viewport sizes.
Use semantic controls, visible focus, keyboard operation, meaningful labels, modal focus restoration,
dirty/busy guards and one clear primary action for the task. Record accessibility and visual evidence
actually executed; neither a mock fixture nor a route returning 200 proves the full flow.
