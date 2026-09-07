# Base 0.6 interaction specification

**Status:** Accepted corrective WP5 baseline

**Authority:** ADR-024 and `BASE_0_6_IMPLEMENTATION_PLAN.md`

This freezes user-visible workspace publication behavior for later WP6 persistence and WP7 APIs/UI;
it does not authorize either implementation. The canonical data is
`frontend/src/test/base06AcceptanceFixtures.ts`. No object has a draft, active, retired or published
state: those terms apply only to a workspace draft or workspace revision.

## Scope and read-only rules

The retained WP0 behavior is workspace catalogue selection, schema 0.5 typed tables, URL-backed
query state, responsive layout, keyboard operation, focus restoration and action hierarchy. This
baseline replaces lifecycle journeys J3-J7 with workspace-draft/revision journeys, and excludes
mapping-grid UI, model-workbench redesign, persistence and API implementation.

The visible trail is `Workspace / Application / View`, extended by `Workspace draft` or `Workspace
revision` when one is open. Workspace labels are primary and stable keys remain URL state. An active
catalogue workspace may have an active content revision or no published content; a retired catalogue
workspace is always read-only. Catalogue retirement and publication retirement are different actions.

Published and historical workspace revisions are immutable. Until the workspace-draft editor exists,
all published object content remains read-only: collection rows offer `Open` only, and object detail
offers no create, edit, activate, retire, draft or revision actions. The rejected WP4 backend must not
be surfaced as a client capability. Opening an object preserves an encoded same-origin return list URL.
Workspace, filter or sort changes clear cursors. A cursor is never reused after the active revision,
draft or model release that bound it changes.

## Workspace draft editor

```text
Workspace: Central Europe / Draft: September terminology / Saved v7
Based on: revision 4                 Model release: 0.6.0

Objects          Relations           Validation
Timetable types  MOT              contains / translates

[Discard draft]                         [Save draft] [Review and activate]
```

A root draft starts empty. A derived draft has an explicit source workspace revision and is edited as
one coherent graph: object fields and typed attributes, containment parent/typed edge, required
relationships and independent relations. The UI never presents a per-object publication action.
Record edits use record versions for useful editor feedback; saving also advances the aggregate draft
version. Dirty/busy guards and notices follow the retained WP0 accessibility rules.

Validation is non-publishing and covers the complete effective graph. Activation review shows the
source revision, currently active revision expected to be superseded, model release, validation and
impact. It requires `expectedDraftVersion` and nullable `expectedActiveRevisionId`. Success publishes
all candidate objects, attributes, containment edges and relations atomically, opens the new immutable
workspace revision and restores focus to its heading.

## Workspace history and publication retirement

```text
Central Europe                              Published revision 5
[Create workspace draft] [Retire publication]

History
Revision 5  PUBLISHED    Created from: revision 3
                        Superseded on activation: revision 4
                        [Open snapshot] [Create draft from this revision]
```

History is newest first and cursor-paged. Each revision displays immutable ID, publication state,
time, pinned model release and both lineage edges. `Created from` is `derivedFromRevisionId`; it can
differ from `Superseded on activation`, `supersedesRevisionId`. Failed older-page loading keeps loaded
history and retries the exact cursor.

`Retire publication` is only a workspace-level action. Its confirmation names the workspace revision,
explains that the current dataset will no longer be published, and requires the expected active
workspace revision ID. It never lists, marks or retires individual objects. Success clears the active
workspace content-revision pointer while retaining workspace identity, immutable history and stable
object/relation identities. A later root or history-derived workspace draft is the only way to publish
content again.

## Conflict recovery

Every conflict states the failed action, what remains preserved and the safe next step; it never
silently retries.

| Conflict | Preserved state | Recovery |
| --- | --- | --- |
| Record version | Local record fields and latest draft context | Compare/adopt the current record, then explicitly save. |
| Workspace draft version | Complete local graph edits | Reload or reconcile the latest draft, then explicitly save or activate. |
| Active workspace revision | Saved draft and source lineage | Review current workspace revision; activation requires a fresh expected revision. |
| Uniqueness/graph validation | Complete draft | Focus the implicated record/edge and validate or activate again. |
| Pinned model release | Persisted draft and browser input | Show pinned/current releases; automatic rebase is unavailable. |

## Journey acceptance criteria

1. **J1 — Workspace and application context.** Select a catalogue workspace by label, retain its
   stable key and table state across applications, and show retired catalogue workspaces as read-only.
2. **J2 — Typed find, open and return.** Apply declared typed filters/sort, open an object, and return
   to the exact URL state without a broadened request.
3. **J3 — Root workspace draft.** Create an empty root draft, add objects of two types with typed
   attributes, containment and a required relation, validate the graph, then activate it once.
4. **J4 — Coherent graph edit.** Derive from the active workspace revision, change an object, its
   containment parent and an independent relation, and verify active reads stay unchanged until one
   activation publishes the full graph.
5. **J5 — History branch lineage.** Derive from an earlier workspace revision while a later revision
   is active; after activation, show distinct source and superseded revision IDs.
6. **J6 — Publication retirement and restoration.** Retire the active workspace publication without
   deleting records or history, then derive a workspace draft from history and publish it again.
7. **J7 — Recover without losing input.** Independently exercise record-version, draft-version,
   active-revision, uniqueness and pinned-model conflicts; no partial graph becomes published.

Fixtures cover desktop (`1280 x 800`) and narrow (`390 x 844`) states. Existing semantic table,
modal, keyboard, focus, busy, retry and responsive rules remain in force. A page has one primary
action; an unavailable mutation is hidden with an adjacent explanation, never represented by an
object-level lifecycle control.
