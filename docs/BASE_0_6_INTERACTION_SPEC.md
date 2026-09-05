# Base 0.6 interaction specification

**Status:** WP0 reviewed and accepted

**Applies to:** Product 0.6 daily runtime-object operations

**Authority:** Accepted ADR-019 through ADR-023 and `BASE_0_6_IMPLEMENTATION_PLAN.md`

This specification freezes the user-visible behavior for the seven Base 0.6 acceptance journeys. It
does not define component implementations, persistence layouts or additional API contracts. The
canonical test data is exported by `frontend/src/test/base06AcceptanceFixtures.ts` and guarded by its
focused invariant test.

## Scope boundary

This specification covers workspace selection, schema 0.5 tables, stable logical objects, mutable
drafts, immutable revisions, activation, retirement and conflict recovery. It deliberately excludes
mapping-grid behavior and APIs, relation-set persistence, bulk operations, a hierarchy renderer and
model-workbench redesign. Application and object-type keys in the fixtures are representative data;
no renderer may branch on them.

## Base 0.5 walkthrough

| Journey | Base 0.5 result | Failure or unnecessary context switch |
| --- | --- | --- |
| J1 Workspace and application navigation | The workspace key is carried in list and detail URLs and survives an application switch. | The selector accepts arbitrary text, cannot distinguish unknown or retired workspaces and cannot show a catalogue label. Switching applications resets that application's view, search, state, sort and page-size context. |
| J2 Typed find, open and return | Search, free-text state, built-in sort and page size are URL-backed; in-session return from detail remembers one collection. | Configured attribute filters and sorts are ignored. State is unconstrained text. A detail URL does not retain its originating list route, so refresh or a new tab cannot reliably return to the same filters and sort. |
| J3 Create and activate root draft | Creation can submit name, parent, typed attributes and required relationships atomically. | Creation writes a current mutable object immediately. There is no populated root draft, separate activation review or immutable first revision. |
| J4 Revise active content | A core dialog updates name, state and parent; attribute panels update values separately. | There is no derived draft or activation. A complete edit requires leaving the core dialog and opening one dialog per attribute; partial writes become visible immediately. |
| J5 Branch from retired history | Audit events are cursor-paged. | Events are not immutable snapshots and expose neither a selectable source revision nor separate derivation and supersession edges. The journey cannot be completed. |
| J6 Retire and reactivate | An object can be deleted, with a second cascade confirmation when dependencies exist. | Deletion removes runtime content; free-text `state` is not lifecycle. There is no retirement without replacement, retired discovery or reactivation from history. |
| J7 Recover from conflicts | Core edit reloads a newer object version while preserving uncontrolled field input. Other failures appear as messages. | There is no complete-draft comparison, active-revision token or pinned-model conflict. Uniqueness errors are not guaranteed to identify and focus the affected field, and recovery is fragmented across edit surfaces. |

Base 0.5 behavior that remains valuable is URL-backed list state, bounded cursor paging, server-side
search, model-derived fields and relationships, atomic required relationships on initial creation,
structured errors and explicit destructive confirmation.

## Information architecture

The interface exposes seven contexts with distinct roles:

1. **Product** is the global shell and entry point. It owns global model administration, but the
   Models workbench is not redesigned in this release.
2. **Workspace** is the global runtime-data scope. Its stable key is stored in the URL; its label and
   active/retired status come from the catalogue. Changing it preserves the current application and
   view when that destination is valid, clears result cursors, and reapplies the same normalized
   filters and sort. A retired workspace is visibly read-only.
3. **Application** is a configured task area within a workspace. Application switching retains the
   selected workspace. Returning to an application restores that application's last view and list
   query during the session; a copied URL remains independently sufficient to restore list state.
4. **View** is a schema 0.5 typed table in Base 0.6. Its declaration controls visible columns,
   filters, sorts, default sort and page size. It does not change runtime-data authority.
5. **Logical object** is the stable identity across all revisions and drafts. Its overview separates
   the current active revision, mutable drafts and immutable history.
6. **Draft** is the only editable object-owned snapshot. The editor presents core fields, parent,
   typed attributes and required ownership relationships in one task. Saving a draft and activating
   it are distinct actions.
7. **Revision** is an immutable snapshot. Its page identifies lifecycle status and pinned model
   release and offers `Create draft from this revision`; it never offers edit controls.

The visible context trail is `Workspace / Application / View / Logical object`, extended by `Draft`
or `Revision` only when one is open. Labels are primary; stable keys are available as supporting
metadata where ambiguity matters. Runtime revision lifecycle is never labelled as model release state,
and the model workbench never appears to edit runtime objects.

### URL and return-state rules

- Workspace key, application key, view key, typed filters, sort and page size are URL state.
- Opaque cursors may be URL state while a page is open but must be cleared whenever workspace,
  filter or sort semantics change.
- Opening an object or draft retains an encoded return location containing the originating list URL.
  Browser Back and the visible `Back to <view>` action return to that exact URL. The return location
  must be same-origin and application-owned; invalid values fall back to the object's matching view.
- Draft and revision URLs identify the stable logical object as context, even when no active revision
  exists. A retired object URL must not resolve through the active-detail endpoint.
- Changing workspace while an object, draft or revision is open returns to the equivalent application
  view in the new workspace rather than attempting to reuse an object ID from another scope.

## Low-fidelity interaction states

### Table collection

```text
[Workspace: Central Europe v]  RDM Master / Codelists                 [New codelist]
Search [________________]  Filters [2]  Sort [Name A-Z v]  [Clear]
Active filters: [Active = true x] [Code starts with AP x]

Name                    Code       Active        Actions
Timetable types       MOT       Yes           Open  More
...
Showing this page                                      Previous  Next
```

The heading names the view and workspace. Search remains separate from typed filters. A filter
control is generated only for a declared `filterField`, offers only operators valid for its type and
shows an explicit value editor. Applied filters remain visible, removable and URL-backed. Sort offers
only declared sort fields and directions. Null and unset are distinct choices. There is no free-text
revision-state field.

Row activation opens the logical object. Essential `Open` and lifecycle actions are keyboard visible;
no essential action exists only on hover. At desktop density, headers and cell values remain readable
without uppercase micro-labels. At narrow widths the table keeps its semantic table and scrolls in its
own labelled region; the name and actions columns remain identifiable and the page itself does not
gain horizontal scrolling.

Collection states are mutually exclusive:

- **Initial loading:** render the heading, controls and column headers disabled or inert, then a
  labelled loading row. Do not briefly show the empty state.
- **Refresh/paging:** retain current rows, mark the table busy and prevent duplicate page actions.
- **No data:** `No <objects> in this workspace yet`, with the create action when applicable.
- **No matches:** `No results match these filters`, with `Clear filters`; do not offer creation as if
  it would fix the query.
- **Error:** retain the URL query and applied-filter summary, replace stale rows with an error notice,
  and expose `Retry` plus a safe route away.
- **Retired workspace:** show a persistent read-only notice and suppress every runtime mutation action;
  reads, filters, history and navigation continue to work.

### Complete draft editor

```text
Edit draft: Timetable types                    Saved draft v3
Created from: revision 2  |  Model release: 0.6.0

Basics          Name [________________________]
Classification  Parent [Connections v]
Attributes      Code [MOT]  Active [x]  ...
Relationships   Required target [...]            (when model-declared)

[Discard draft]                         [Save draft] [Review and activate]
```

The editor does not mix draft save with activation. It loads the complete draft before enabling
fields and never renders an empty form while a snapshot is pending. All mutable object-owned fields
share one form and one validation summary. Optional unset values have an explicit unset control;
stored `false`, zero, null and empty JSON are not treated as absent. Read-only model fields are shown
as values, not disabled inputs.

`Save draft` is the ordinary primary action while fields are dirty. `Review and activate` first saves
when necessary, then opens an activation review showing the candidate, its source revision, the
currently active revision it is expected to supersede, and impact/validation results. Activation is a
second explicit action. Closing a dirty editor requests confirmation; busy mutations cannot be
dismissed. Successful save keeps the editor open and updates the visible draft version. Successful
activation opens the new immutable revision and returns focus to its heading.

### Logical object and history

```text
Timetable types                         Active revision 3
[Create draft from active] [Retire active revision]

Drafts (2)                 History
Draft v4                   Rev 3 ACTIVE
Draft v1                   Created from: Rev 2
                           Superseded on activation: Rev 2
                           [Open snapshot] [Create draft from this revision]

                           Rev 2 RETIRED
                           Created from: Rev 1
                           Superseded on activation: Rev 1
```

History is newest first and cursor-paged. Each entry always shows revision ID, lifecycle status,
activation time, pinned model release and the two lineage labels. A missing edge is displayed as
`None (initial revision)` or `None (no active revision)` rather than omitted. `Created from` uses
`derivedFromRevisionId`; `Superseded on activation` uses `supersedesRevisionId`. An earlier source and
a later superseded revision must be visibly different in J5.

When no active revision exists, the page remains a logical-object page headed `Retired`; it shows the
latest retired snapshot, drafts and history, with no edit or direct reactivation action. Reactivation
always starts with `Create draft from this revision` and ends with explicit activation.

History states distinguish loading, no revisions (never-activated root draft), partial-page loading,
retryable error and end of history. A failed older-page request retains already loaded entries.

### Retirement

```text
Retire active revision?
Timetable types / revision 3
This removes it from active collections. Identity and history remain.
[impact summary or loading/error state]

[Cancel]                                      [Retire revision]
```

The action is named `Retire active revision`, never Delete. The first request obtains current impact
without mutation. With no active dependants, confirmation submits the expected active revision ID.
With active owned dependants, the dialog lists grouped counts and examples and requires a separately
labelled `Retire with dependants` confirmation. Associations are described as retained history, not
deleted targets. A conflict leaves the dialog open and refreshes the displayed active identity and
impact before another confirmation. On success, focus returns to the logical-object heading and a
status message announces retirement.

### Conflict recovery

Every conflict notice identifies the failed action, states what was preserved and offers one safe
next step. Notices receive focus after submission; their summary links focus the relevant field or
comparison. Conflict recovery never silently retries a write.

| Conflict | Preserved state | Required presentation and recovery |
| --- | --- | --- |
| Draft version | All locally entered values and the server's latest complete draft | Show a field-level comparison. The user chooses the local or latest value for each changed field, adopts the latest draft version, then explicitly saves again. `Reload latest` requires confirmation because it discards local input. |
| Active revision | The saved draft and its pinned source lineage | Show the expected and now-active revisions. `Review current active` opens the immutable snapshot; returning preserves the draft. A new activation confirmation uses the fresh active revision identity. |
| Uniqueness | The complete draft and field values | Put the diagnostic in the summary and beside the implicated field/relationship. Link the conflicting logical object when the server identifies it. The user changes the candidate and explicitly saves or activates again. |
| Pinned model release | The complete persisted draft and any unsaved browser input | Show pinned and current model releases and state that automatic rebasing is unavailable. The draft remains readable and editable but activation stays disabled. Offer copy/export of entered values and navigation to create a separately validated draft; do not claim that retry can succeed unchanged. |

Generic validation uses the same summary-and-field-link pattern. Network failure retains the form and
offers retry. Authentication recovery is not specified because authentication is outside Base 0.6.

## Responsive, keyboard and focus contract

Two acceptance viewports are fixture data: a desktop viewport (`1280 x 800`) and a narrow viewport
(`390 x 844`). Layout changes may occur at content-driven breakpoints, but both must satisfy the same
information and action contract.

- Desktop keeps product/application navigation, workspace selection and page context visually
  distinct. Secondary navigation may occupy a sidebar, but the task heading and primary action belong
  to the main region.
- Narrow layout places product, workspace and application/view navigation before the main heading.
  Secondary navigation collapses behind a labelled control, not an icon alone. Dialogs become
  full-height sheets; their title and action bar remain reachable while content scrolls.
- Keyboard order follows visual/task order: skip link, product navigation, workspace, application/view
  navigation, page heading action, query controls, results, pagination, then secondary content.
  Programmatic focus never jumps merely because results refresh.
- Composite selectors follow the React Aria behavior exposed by RDM wrappers. Simple fields, buttons,
  links and tables use native semantics. Arrow-key behavior is confined to the composite that owns it;
  Tab moves to the next task control.
- Opening a modal focuses the first invalid field, otherwise its first task field, otherwise the
  dialog heading. Focus is trapped. Escape and outside interaction close only a clean, idle dialog;
  dirty content requires confirmation and a busy mutation cannot be dismissed.
- Closing returns focus to the exact invoking control. If that control no longer exists, focus moves
  to the nearest stable heading or result row. After collection return, focus moves to the originating
  row's `Open` control when it still exists; otherwise to the table heading.
- Notices use text plus semantic status, never color alone. Icon-only controls require explicit names;
  decorative icons are hidden. Visible focus indicators must not be clipped by table or dialog
  overflow.
- Dense tables use a readable body size and consistent row height. Users may choose comfortable or
  compact density only if both preserve the same fields, targets and keyboard order; density is not a
  substitute for responsive layout.

## Action hierarchy

- A page has at most one visually primary action: create on a collection, save in a dirty editor, or
  activate in the activation review.
- Navigation and non-mutating inspection are links or secondary actions. Row menus may group
  contextual actions, but `Open` remains directly available.
- Destructive actions use explicit text and a destructive style only at the point of consequence.
  Draft discard and active retirement are separate concepts and confirmations.
- Disabled actions explain their prerequisite in adjacent text or a discoverable description. A
  missing capability or retired workspace hides mutation entry points and leaves a persistent reason;
  it is not presented as a transient validation failure.

## Journey acceptance criteria

The fixture export names the exact seed identities, routes, typed values, conflict categories and
already-fixed error codes. The following criteria are the independently observable minimum.

### J1 — Workspace and application context

1. Starting in the default workspace, the user selects the fixture's non-default active workspace by
   label from catalogue-backed search; no raw-key entry is available.
2. The URL contains its stable key and the page context shows its label.
3. Moving to another application keeps that workspace. Returning restores the first application's
   prior view, filters and sort.
4. Reloading the copied URL restores the same context. Selecting the retired fixture workspace shows
   read-only state and no mutation actions. An unknown explicit key renders `workspace_not_found` and
   never falls back to default.

### J2 — Typed find, open and return

1. The user applies case-insensitive `startsWith` on a configured text attribute and equality on a
   configured boolean attribute, then selects a declared descending sort.
2. The request and URL contain typed filter lexemes and sort; the matching Codelist appears.
3. Opening it shows the same workspace/application/object context.
4. Browser Back and `Back to Codelists` restore the exact search, filters, sort and page size without
   a broadened intermediate request. A changed filter clears the old cursor.

### J3 — Populated root draft and first activation

1. New Translation opens one complete initial-draft form with its Translation Group parent, typed
   attributes and required translated target.
2. Submission with the fixture values creates a stable logical identity and populated root draft but
   no active revision. The draft shows `Created from: None`.
3. Activation review shows no current active revision and requires null expected-active identity.
4. Successful activation creates immutable revision 1, removes the draft from mutable lists and makes
   the object appear in active discovery. Parent and required relationship are visible in the same
   published snapshot.

### J4 — Revise all object-owned content coherently

1. From the active Codelist revision, `Create draft from active` makes a complete derived draft.
2. In one editor the user changes name, parent and typed attributes, then saves once.
3. Active collection/detail remains unchanged before activation.
4. Activation review names both the source and expected active revision. Success creates one immutable
   revision, retires the former active revision and atomically publishes every edited field and
   containment projection.

### J5 — Branch from earlier retired history

1. History exposes an earlier retired Codelist revision and its immutable snapshot.
2. Creating a draft from it labels that revision as `Created from` and does not change current active
   content.
3. When activated, the new revision continues to show the earlier revision as its derivation source
   and the revision active at activation as `Superseded on activation`.
4. The two labels contain the distinct fixture IDs and remain visible at both viewports.

### J6 — Retire without replacement and reactivate through a draft

1. Retirement preview names the active Translation revision and its impact. Cancel changes nothing.
2. Confirming with its expected active revision removes it from active discovery without deleting the
   logical identity, revision, lineage or independent associations.
3. Retired discovery finds it; active detail does not pretend it is current editable content.
4. The user creates a draft from the retired revision and activates it. The object returns to active
   discovery with a new immutable revision; the retired source remains history.

### J7 — Preserve work through conflicts

1. Each fixture conflict is exercised independently: draft-version, active-revision, uniqueness and
   pinned-model-release conflict. Fixtures name an error code only where an existing or accepted
   contract already fixes one.
2. In every case, the entered name, parent, attributes and required relationships remain present after
   the response and the server publishes no partial candidate.
3. Draft-version recovery shows local/latest comparison and requires an explicit second save;
   active-revision recovery requires a new activation review; uniqueness focuses its field; pinned
   model conflict disables activation and truthfully states that automatic rebase is unavailable.
4. Keyboard focus lands on the conflict summary and can reach the affected field or revision without
   traversing unrelated navigation.

## Fixture and downstream-test contract

`frontend/src/test/base06AcceptanceFixtures.ts` is a behavior fixture, not a provisional API type. It
contains deterministic UUIDs, workspaces, model context, two representative object workflows,
revision/draft lineage, table state, conflict cases and step-level expectations for J1-J7. Later work
packages may adapt this data to finalized API response types, but must preserve its scenario IDs and
observable outcomes so component, browser, accessibility and visual suites refer to the same journeys.

WP1 may begin only after this baseline is accepted. Acceptance does not authorize mapping, schema 0.6,
relation-set persistence or a model-workbench redesign.
