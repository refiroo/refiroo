# Base 0.6 interaction specification

**Status:** Accepted product baseline updated from GAP-01–GAP-08, 2026-09-08; implementation and
composed-browser validation remain WP8.1/WP9/WP10 work.

**Authority:** ADR-026/027, `PRODUCT.md`, product stories/scenarios and `BASE_0_6_IMPLEMENTATION_PLAN.md`.
Existing `frontend/src/test/base06AcceptanceFixtures.ts` must be extended to this behavior during
implementation; it is not proof that these revised journeys already work.

> Historical note: this document records the released Base 0.6 interaction contract. ADR-029 and
> Base 0.7 WP-14 supersede its separate Browse hierarchy / Views navigation modes with one
> model-driven application browser; the record-origin rules below remain applicable.
> The Base 0.7 presentation pass further supersedes the navigation presentation below: applications
> are header tabs rather than a vertical list, versions replace the Information disclosure, record
> branches start collapsed, and typed filters share one Filter popover. See
> [UI model — Base 0.7 presentation](UI_MODEL.md#base-07-presentation).

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

WP9-A stores the live collection cursor trail in repeatable `cursor` URL parameters.
Returning from details, including related records in another application, restores
the originating collection query and page. Changing workspace or collection controls
starts from the first page. A failed page read retains loaded rows from the same query;
Retry repeats that request. Failed initial reads do not display a misleading empty state.

UI-03A retains each record's originating collection in its browser-history entry, including the
query, cursor trail and workspace/draft/revision context. Record reload and Back/Forward restore
that entry's origin, including after following a related record in another application. Origins
are checked against the model and selected data context; invalid origins fall back to the record's
matching collection. Copied record URLs contain no origin and open the full detail page.

Record, individual-value and relationship editors require confirmation before router navigation
discards unsaved input. Cancelling Back/Forward retains the editor and restores its URL; reload/tab
close use the browser's native unsaved-input prompt. In-flight editor/deletion requests refuse router
navigation until completion. Successful saves release their guard before opening the saved record;
failed saves keep entered values protected. Form input is not persisted. Browser-native unload
prompts remain subject to browser support and user interaction.

## Record presentation

Collection rows open the same full-width record presentation used by Browse hierarchy, at desktop
and mobile widths. The originating collection remains mounted but hidden, retaining its query,
page and temporary display choices. Back to list restores it and returns focus to the selected row
when present. Reload and browser Back/Forward preserve the full-width presentation and origin.

Browse hierarchy retains its standalone record-navigation behavior: selecting a hierarchy node
opens the configured full record view and does not retain an unrelated table in the middle. Further
hierarchy selections remain standalone. A copied record link likewise opens the full record view.
Records opened through Browse hierarchy omit Back to list, including after reload and related-record
navigation. Collection-based navigation retains it; direct links retain their fallback collection
return. Explicit application/ancestor breadcrumbs remain available.

Inspector and full-page views share the same detail renderer, data context and configured panels.
The supporting side region appears first in stacked inspector/mobile layouts, keeping record
properties readily available; wide full pages keep the main and side regions side by side. Ordering
within each region is retained. Empty sections use compact spacing and keep their add controls.
Live record activity remains separate from workspace revision history.

Record actions offers Edit all fields, Copy link and Delete record. Collection and embedded-table
rows expose the same actions through a visible menu, right-click or Shift+F10. Row edit/delete opens
the selected record's existing coherent form or signed-impact confirmation. Read-only records offer
Copy link only. Copy preserves workspace/draft/revision identity and reports clipboard refusal with
a manual-copy recovery action.

Saves refresh the visible record and collection without losing continuation or previously loaded
rows on refresh failure. Changing collection controls retains the selected inspector while updating
its return query. Deletion closes the deleted record and refreshes the collection; if its later page
is now empty, paging returns to a preceding page while retaining the query.

## Navigation presentation

UI-01 places workspace and application selection above the configured views in a compact neutral
sidebar. Browse hierarchy appears first, followed by Views. On the first visit hierarchy is selected;
after a choice, browser local storage restores the selected mode on reload from the first render.
The preference applies across applications and workspaces and does not change the current route. Each branch
has a separate keyboard-accessible expand/collapse button that does not select the record. Branches
start expanded; explicit collapsed choices persist in browser local storage per workspace/application
using stable record IDs, shared across Live, Draft and history contexts. Expanding a parent restores
its descendants' own choices. Invalid or unavailable storage falls back to usable session state.
These preferences belong to this browser, not a server-synced account. Hiding either navigation or
the mobile drawer preserves explorer search and continuation. Application choices and views use
vertical lists. Model administration has a separate secondary entry; model and schema versions are
available through Information. The main content shows workspace/application and Live, named Draft,
or historical context, followed by the page heading.

At widths up to 760px, Browse application opens a modal navigation drawer. Escape, Close and outside
interaction dismiss it and restore focus. The selected location remains visible in the main content
when closed. Navigation preserves the existing workspace, draft/revision and collection route rules.

## Collection presentation

UI-02 keeps search visible and places configured typed filters behind Filter. Applied filters are
individually removable; removing one preserves the others and search. Sortable configured headings
and the Sort menu share one active sort, indicated only on its actual column. Display controls expose
only configured columns, retain a record identity column, and offer comfortable/compact rows.

In the collection-only view, search, filters, sort, page size and continuation remain URL-backed;
with a selected inspector they belong to its browser-history collection origin. Changing a query
control starts at page one; column visibility and density do not change the query or page. Embedded
collection page size belongs to that mounted panel. Display choices are temporary and reset on leaving
the collection/reloading; local persistence belongs to UI-05. Embedded panels expose search and display,
without inventing filter/sort configuration absent from their model contract.

At mobile widths the table prioritises record identity and two other visible configured columns.
Show all columns exposes the remainder with horizontal table scrolling; Display also allows choosing
columns. Tables retain sticky headings within bounded scrolling, keyboard record links and focus
highlighting. Counts describe only the loaded page; loading, an empty result and failed reads remain
distinct. UI-03B adds single-record selection for the inspector without introducing bulk selection.

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

WP9-B exposes Add on live collections and child/dependent panels, plus Edit object and Delete object
on details. Catalogue retirement removes these write controls. The edit form preserves entered values
on failure and displays current saved content after a version conflict; only deliberately edited fields
are submitted when the user saves again. Individual field and relationship forms retain their input
and display current values on conflicts as well.

The first Delete confirmation requests ordinary deletion. When dependencies exist, the API returns
an impact without deleting anything; the dialog lists owned records and affected relationships for
explicit confirmation using the returned signed token. A stale preview leaves the displayed impact
and retry message visible. Retry refreshes the root version; the user requests and reviews a fresh
impact before confirming again. It never automatically resubmits a cascade.

## Optional workspace data draft

WP9-C implements Live/Drafts navigation. Draft collection and detail URLs carry
`workspaceDraftId`; switching applications, opening related records, returning to a collection and
reloading retain it. Live remains a separate, directly editable context. Draft creation explicitly
copies current live data, including post-publication edits and workspaces without a publication.
The source label names that capture, independently of the publication activation will supersede.

The same record, field, parent, relationship, translation and signed-delete controls operate inside
the selected draft. Its resource supplies the aggregate version, including when individual record
reads omit it. Record and aggregate conflicts preserve entered fields and require an explicit retry.
A successful save followed by a failed version refresh is reported as saved; further writes wait for
an explicit version refresh. Draft record details do not present live audit history as draft history.

Validate draft checks the effective graph. Activation is enabled only for that checked draft version
and asks for confirmation of the workspace publication; activation rechecks the final merged graph.
Conflict feedback identifies affected records and preserves the draft. Discard has a separate
confirmation and leaves live content unchanged. Historical source selection remains slice D.

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

Product 0.11 adds the accepted historical model replacement path: preview incompatibilities and
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

### Unconfigured record details

When an object type has no explicit detail configuration, its generic fallback derives child
collections from declared containment relationships and displays its incoming/outgoing relationships.
Properties and hierarchy use the side region, matching configured record layouts. This covers
System groups and Translation groups without domain-specific renderer branches or model changes.
