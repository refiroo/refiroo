# The plain path: implementation plan

**Proposed 2026-10-28. Approved by the user 2026-10-31 as product release 0.17, straight after 0.16, with
the workbook canvas (PL3b) in it.** From a UX review of the running application at the user's request:
refiroo can do almost everything a steward or model administrator needs, but the everyday journeys feel
like a spaceship, with every capability visible at once and long paths between them. This plan keeps
every capability and adds a friendly common path, with the expert depth one step away. The review page
(findings with screenshots, the principles and the clickable mock-ups) is the visual reference for
these packages; each UI package still shows its own mock-up with its plan for one approval.

## Why

Walked on the developer instance on 2026-10-28 (sign in, Home, find and correct, add records, a change
set from start to publish, mapping, history, a workbook into a new workspace up to its confirmations,
Settings), ranked by what each costs a person in a common journey:

1. **A workbook never becomes a workspace in one go.** Eight decisions before the workbook is read
   (the new workspace not among them), then two finishes that each do half: Load picks only an existing
   workspace and activates the draft's model there (`LoadDialog.tsx`), Install creates a workspace and
   loads nothing. A profile-key clash with another model's profile blocks the load.
2. **Publishing needs a step nobody tells you about.** Publish stays disabled until a manual Validate
   passes, explained only by a tooltip (`ChangeSets.tsx`); the engine validates again at publish (J05).
   Starting asks Model release holders for a release from every model; the confirmation speaks of
   "authored changes" and "an invalid merged graph" on a danger button.
3. **No page is the workspace, and no search spans it.** A Home card lands on the first collection; the
   explorer's search covers one application's tree; the workspace's own actions live in Settings.
4. **Add forms ask what the page knows and hide what is required.** From a parent's page the parent
   picker still shows; required fields are unmarked and found by the browser's bubble.
5. **Identifiers lead the common pages** (record UUID and version, the change-set band's model key),
   against the Disclosure pattern in [UI acceptance](testing/UI_ACCEPTANCE.md#1-reference-patterns).
6. **A collection's Import and Export open on expert choices** (every profile, three switches; Export on
   Technical).
7. **Your changes is flooded** by one line per model-draft step.
8. **The top bar** cuts off a sixth application at 1440px and shows a workspace's tabs inside Settings.

Changing a workspace's model from the workspace is [WM1](BASE_0_16_IMPLEMENTATION_PLAN.md#wm1-change-a-workspaces-model-from-the-workspace)
and is not repeated here.

## Principles

1. **One obvious next step.** One primary action per page, named for the outcome; the rest secondary or in ⋯.
2. **Start where the thing is.** Actions on a workspace, record or collection live on its page; Settings is
   for the instance.
3. **Ask only what can't be guessed.** Defaults stated as a sentence with Change.
4. **Required first, the rest behind More.** Marked required fields; "More fields (n)" for the optional ones.
5. **No hidden prerequisites.** The main action does a required step itself, or the page says the next step
   in words; never a disabled button explained by a tooltip.
6. **Plain words, identifiers in Details.**
7. **Finish where you started**, with one sentence saying what happened.
8. **Depth one step away.** Every plain surface links to today's full control; no capability is removed.

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [PL0](#pl0-the-principles-as-reference-rules) | — | The principles as reference rules in UI acceptance, with a plain-path checklist for each UI package |
| [PL1](#pl1-change-sets-in-two-clicks) | — | Start with a name; Publish checks, then confirms in plain words; Validate and the rest in ⋯ |
| [PL2](#pl2-plain-add-and-edit) | — | The parent as a sentence, required first, optional under More fields, inline errors; the record header without the raw ID |
| WM1 | 0.12 | Delivered in 0.16: in the workspace ⋯ menu and as a button on the workspace's page in Settings › Workspaces (the user, 2026-10-31). PL3's page reuses the action |
| [PL3](#pl3-the-workspace-page) | PL0, WM1 | A page for each workspace: search across it, what waits, recent changes, its own actions; Home cards open it |
| [PL3b](BASE_0_17_IMPLEMENTATION_PLAN.md#pl3b-the-workbook-canvas) | PL0 | The workbook beside the live result: drag sheets and columns into lists, fields, relationships, hierarchies, filters and groups; each drop applies at once |
| [PL4](#pl4-new-workspace-from-a-workbook) | WM1, PL3, PL3b | The file and a name, what refiroo found, Create workspace |
| [PL5](#pl5-plain-words-and-identifiers) | PL0 | One list of replacements applied on the common path; Settings index; Back to the workspace |
| [PL6](#pl6-collection-import-and-export-and-your-changes) | PL0 | Import file-first with profile chosen and options folded; Export for people; draft steps grouped |

**Order (recommended).** PL0, PL1, PL2, then WM1 as planned, PL3, PL3b, PL4, PL5, PL6. PL1 and PL2 are the
cheapest fixes on the most frequent paths; PL3 adds WM1's action to its page and gives PL4 its place; PL3b is where PL4's Adjust leads.

**Decision needed (asked with this plan):** a workbook's new workspace loads straight into live data
(recommended) or into a change set first. A workbook loaded into an existing workspace keeps going into
a change set.

## PL0: The principles as reference rules

**Scope.** [UI acceptance](testing/UI_ACCEPTANCE.md) §1 gains a "Plain path" row: the eight rules and their
reference surfaces (the mapping dialog as the model dialog, the collection page for one primary). The
package report names, for a changed surface, its one primary, where its depth is, and that no step is
explained by a tooltip alone. **Tests:** documentation only; links checked.

## PL1: Change sets in two clicks

**Journey:** a designer starts a change set by naming it, makes changes, chooses Publish, reads what goes
live and confirms; if the check finds a problem, nothing is published and the page lists what to fix with
links to the records.

**Scope.**
- New change set: the name; start point and model version under **Options** (the release list for Model
  release holders only, defaulting to the workspace's own).
- The bar: **Review changes**, **Publish** (primary), ⋯ (Validate now, Change model version, Rename,
  Discard). The band: name, change count, who and when; version and model under Details.
- **Publish** runs the existing validation, then confirms with counts and what happens on a conflict, in
  the primary style; a failed check lists its records above the page.

**API:** none; the engine validates at publish already (J05). **Tests:** unit (`ChangeSets.test`):
publish checks first, the problem list, the release list hidden without Model release; the change-set
browser runner on two configurations, with and without a problem, keyboard, 390px.

## PL2: Plain add and edit

**Journey:** from a record's page a steward adds a record under it, filling the marked required fields;
the optional ones wait under More fields; a missing value is said under its field.

**Scope.**
- `ObjectFormDialog` opened from a parent: "In ‹parent› · Change" replaces the parent picker (behind Change).
- Required fields first and marked from the model's bindings; optional ones under **More fields (n)**,
  open state remembered per type in this browser; inline required and type errors, never the native bubble.
- The eyebrow names the collection. The record header shows name, type and path; ID and version move into
  a Details disclosure; Copy link stays in ⋯.

**Tests:** unit for parent-fixed, field order, More fields and inline errors; the record-actions runner on
two object types of two configurations, keyboard, 390px, axe on the dialog.

## PL3: The workspace page

**Journey:** a person opens a workspace from Home, finds a record by typing part of its name without
knowing its application, opens it, and returns; the workspace's own actions are on the same page.

**Scope.**
- A workspace overview in the shared frame: a search over every type (the cross-type lookup, results
  grouped by type with their path, Enter opens), the applications, the person's waiting change sets, the
  five latest changes there.
- Actions: **Import a workbook…** (PL4), **Edit model** (WM1), ⋯ opening today's Settings › Workspaces pages
  (Rename, Access, Approval, Copy or move, Retire); each hidden without its permission.
- Home: one primary (Continue, or New workspace from a workbook for administrators); cards open the
  overview; roles in one line. The same search from the top bar (one `SearchField`). Tabs that don't fit go
  into a More menu.

**API:** existing routes (`GET /objects` cross-type lookup, `/me/change-sets`, changes by workspace). Its
search over every type's name was not checked beyond API.md; if missing, adding it is this package's, with
a J01.4 journey test on two configurations. **Tests:** browser: Home → overview → search → record → back on
two configurations, keyboard through results, 390px, axe, no 5xx or server error line.

## PL3b: The workbook canvas

Added 2026-10-31 at the user's request. Its scope, gestures and engine work are in the
[0.17 plan](BASE_0_17_IMPLEMENTATION_PLAN.md#pl3b-the-workbook-canvas).

## PL4: New workspace from a workbook

**Journey:** an administrator drops a workbook and names the workspace, reads what refiroo found (lists,
rows that load, rows that don't and why, every row checked), and creates the workspace in one confirmed
step, landing on its page with what didn't load.

**Scope.**
- Started from Home, Settings › Workspaces and the workspace page. Draft, release key, version and profile
  key are derived; **More ways to start** keeps today's dialog.
- **Adjust** opens the workbook canvas (PL3b); its main finish for a draft not made for a workspace is
  **Create workspace…**; **Load into an existing workspace…** moves to ⋯ and names whose model it replaces.
- **Create workspace** installs the draft, creates the workspace on the release and loads the workbook
  (live or change set: the decision above).
- A draft's import-profile key is made unique when the draft is created; a clash never reaches the person.

**API:** one route for the whole step (a workspace created from a draft with its workbook loaded, answering
the workspace and the load job), so integrators get it too. **Door check (ADR-032):** the import path,
identity and history are reused unchanged; no door affected. **Tests:** journeys (J36.4, J34.8 variants)
on two configurations: a workbook becomes a workspace with its records; a profile-key clash doesn't refuse;
refused rows are reported and the rest load; other workspaces unchanged; a caller without the groups is
refused by code. Browser: the real sample workbook end to end, including an invalid draft's dialogs;
keyboard; 390px; no 5xx.

## PL5: Plain words and identifiers

**Scope.** One list of replacements kept in this section when the package starts (for example "declared
views", "Create in context", "authored changes", "merged graph", "Current object", a draft's "Version 99"),
applied in the UI copy; application keys out of picker paths; workspace keys in lists under Details.
Settings opens on a short index of its pages by task; inside Settings the top bar offers Back to the
workspace instead of its tabs. **Tests:** copy assertions updated where they change; changed surfaces'
screenshots inspected; visual baselines updated only for those surfaces.

## PL6: Collection import and export, and Your changes

**Scope.** Import: the file first; a profile chosen when one matches the file and the workspace's model;
other models' invalid profiles hidden; the three loading switches under Options with today's defaults.
Export from a collection opens on For people. Your changes and Home's latest show consecutive steps on one
model draft as one expandable line with their count. **API:** unchanged (grouping presents the existing
feed). **Tests:** unit for the profile choice, the hidden profiles and the grouping; the import runner with
a people workbook on two configurations; 390px.

## Said plainly: what stays expert

Mapping a workbook column by column, consumer API definitions, restructuring across types, copy and move
between models, the release catalogue, people and sign-in stay as they are, reachable from the plain
surfaces.
