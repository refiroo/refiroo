# Base 0.17 implementation plan

**Status:** Planned 2026-10-31 at the user's request. The plan and the canvas mock-up were approved by the user
on 2026-10-31. Nothing is built yet, and the decision marked **Open** below is not settled.

**Target:** Product 0.17.0, [the plain path](ROADMAP.md#product-release-017--the-plain-path).

**Depends on:** 0.16 released, with WM1 (see [PP-D2](#decisions)). The findings, principles and the detail of
PL0–PL2 and PL3–PL6 stay in [PLAIN_PATH_PLAN.md](PLAIN_PATH_PLAN.md) and are not repeated here. PL3b's full
scope is in this plan.

## Why

refiroo can do almost everything a steward or model administrator needs, but the everyday journeys are long
and show every capability at once ([the review](PLAIN_PATH_PLAN.md#why)). Import is what a new person meets
first. Today a drag in the model editor only opens a form: a column's drop opens the Map dialog and a move opens
the Move dialog (`ModelEditor.tsx`, `drop`).

## Outcome

- **A workbook becomes a workspace in one go,** and a person shapes its model by dragging on one screen beside
  the live result, with or without AI: columns, sheets, hierarchies, a list dropped on a field for a
  relationship, filters and navigation groups, in a very easy way.
- **The everyday journeys are short:** a change set starts with a name and publishes with one main action, a
  form asks required fields first, each workspace has a page, and plain words replace identifiers.
- **No capability is removed;** today's full controls stay one step away, and every drop is available through
  the API.

"A few words and a workbook" stays the route to a model and an import (0.16). The canvas is where a person
corrects that result, and the way to import when no provider is configured.

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [PL0](PLAIN_PATH_PLAN.md#pl0-the-principles-as-reference-rules) | — | The principles as reference rules in UI acceptance |
| [PL1](PLAIN_PATH_PLAN.md#pl1-change-sets-in-two-clicks) | PL0 | Start with a name; Publish checks, then confirms in plain words |
| [PL2](PLAIN_PATH_PLAN.md#pl2-plain-add-and-edit) | PL0 | Parent as a sentence, required first, inline errors |
| [PL3](PLAIN_PATH_PLAN.md#pl3-the-workspace-page) | PL0, WM1 | A page for each workspace, with search across it. **Edit model:** WM1 (0.16) delivers it in the workspace ⋯ menu and as a button on the workspace's page in Settings › Workspaces; both stay, and this page adds a button running the same action (the user, 2026-10-31) |
| [PL3b](#pl3b-the-workbook-canvas) | PL0 | The workbook beside the live result; every drop applies at once |
| [PL4](PLAIN_PATH_PLAN.md#pl4-new-workspace-from-a-workbook) | PL3, PL3b | The file and a name, what refiroo found, Create workspace |
| [PL5](PLAIN_PATH_PLAN.md#pl5-plain-words-and-identifiers) | PL0 | One list of replacements; Settings index; Back to the workspace |
| [PL6](PLAIN_PATH_PLAN.md#pl6-collection-import-and-export-and-your-changes) | PL0 | Import file-first; Export for people; draft steps grouped |
| [R](#r-build-acceptance-and-release) | all | Full review since 0.16, the gates, the release |

**Order.** PL0, PL1, PL2, PL3, PL3b, PL4, PL5, PL6, R. PL1 and PL2 are the cheapest fixes on the most frequent
paths. PL3 gives PL4 its place, and PL3b is where PL4's Adjust leads. Each UI package shows its mock-up with its
plan for one approval and is then delivered whole.

## Decisions

| ID | Decision | State |
| --- | --- | --- |
| PP-D1 | **Where a new workspace's first load goes.** Straight into live data (recommended: the workspace is new, nobody relies on it, and a change set adds a review of everything) or into a change set first. A load into an existing workspace keeps going into a change set. Needed before PL4. | **Open, the user's** |
| PP-D2 | **WM1 stays in 0.16.** PL3 and PL4 rely on it. Delivered 2026-10-31, as planned in [the 0.16 plan](BASE_0_16_IMPLEMENTATION_PLAN.md#wm1-change-a-workspaces-model-from-the-workspace). | Planning default |
| PP-D3 | **The canvas is a view of the model draft,** opened by PL4 and by an assistant's result, on the existing draft, operations, undo and dry run. There is no second store and no second dialect. Today's editor is reachable from it and edits the same draft. Shared pieces are extracted from the editor, never copied. | Planning default |
| PP-D4 | **A drop applies at once, as one operation request and one undo step,** as `MapColumnDialog` already does with several operations in one request. No dialog opens; a small panel on the item takes changes. A drop the engine refuses changes nothing and says why in place. | Follows the user's request |
| PP-D5 | **Every drop is reachable without AI and through the API.** Whatever a gesture needs that the engine lacks is added to the engine and API first, generically. | AGENTS.md |
| PP-D6 | **Wide sheets become a profile reading,** not a task-only step: `unpivot` on a source (the columns, the field naming each row, the field taking the value), read by the import path. It works for any import and repeats from the saved profile. The assistant's former `unpivots` is gone and its SQL derived sheets are task design only, so neither serves a person or a saved profile. | Approved with this plan, 2026-10-31 |
| PP-D7 | **Rows grouped under a heading become a profile reading too:** `fillDown` for columns repeated by blanks, and a heading row read as the parent of the rows beneath it. Neither exists today. | Approved with this plan, 2026-10-31 |
| PP-D8 | **The join is found over every row.** A list dropped on a field compares the two columns in PostgreSQL over the whole set. The stored overlaps of the profile (first 1,000 distinct values, best five) stay a hint only. When two candidates tie, the panel asks; nothing is guessed silently. | Rule: checks cover the whole set |
| PP-D9 | **The canvas never waits for a check.** The existing dry-run job runs after each step and a newer run cancels the older; the count reads "Checking…" until it answers, and the person may keep dropping. | Planning default |
| PP-D10 | **Phone:** the canvas works by the ⋯ menu at 390px; dragging is a desktop and tablet fast path. | Planning default |

## PL3b: The workbook canvas

**Journey:** a person opens a workbook and sees its sheets on the left, the result in the middle with its sample
values, and the navigation on the right, already filled and marked Proposed by the inference or the assistant.
They drag until it reads as the business does, watching the count of rows that load or are refused, then
continue to the import.

sample rows. It computes its counts on those rows but is not connected to the engine.

### Gestures and what each one uses

Checked against the code on 2026-10-31.

| Drag | Result | The engine today | To add |
| --- | --- | --- | --- |
| A sheet onto empty space | A new list, its columns as fields | `addObjectType`, `addAttributeType`, `attachAttribute`, `addSource`, `mapColumn` in one request; `inference/list` answers with list rules | A table-shaped proposal for one sheet, answered at once |
| A column onto a list or field | A new or mapped field | Yes, `mapOperations` | The drop without the dialog |
| A column onto empty space | Its distinct values as a list, linked back | `convertAttributeToListType`, for a mapped attribute | The same for an unmapped column, as one request |
| A card's Connect handle or a sheet onto a field | A relationship, drawn as a dashed line | `allowRelation`, a `relation` binding by `mapColumn` | Whole-set join candidates (PP-D8) |
| A card's Connect handle onto another card | Parent and child, drawn as a solid line | `setContainment`; a `parent` binding or fixed `Source.parent` | Both in one request, with the parent column found as for a join |
| Several columns onto one field | Translations, flags or a wide sheet as rows | Translations by `relatedRecord`; flags by `relationFlags` | `unpivot` (PP-D6) |
| A column onto a list's filter box | A filter on the list | `setViewProperty` with `filterFields`, table views, for an attribute already there | The attribute added first, in one request |
| A list onto a group or New group | A navigation group | `addNavigationGroup`, `placeCollection`, `setNavigationGroup` | Nothing |
| A field back onto the workbook | The column left out | The inverse operations and `ignore` | Nothing |

**Actions on the sheet preview:** click the row that holds the headers (`headerRow`, with rebinding through
`setSource`, exists); mark a column as repeated by blanks, or a row as a heading (PP-D7). Side-by-side tables are
found already (`block`, `sources/layout.py`) and appear as separate tables.

**Placing and connecting (the user, 2026-10-31):** the board is a free surface. A card is placed anywhere by its
top bar, which never changes the model, so a card moved near another cannot link them by accident. Connecting is
its own gesture, the Connect handle, and every connection is a visible line with a × that removes it. Tidy
arranges the cards to use the board's width. Positions belong to the draft's canvas, are readable through the
API, and are not part of the model release.

**Also on the canvas**
- **Refusals:** the count covers every row; a click opens the rows by reason. A wrong value is corrected by
  dropping it on the right one (`setValueMap`).
- **Undo and redo:** the existing routes, shared by model and profile. A step a later step depends on cannot be
  undone alone; the toolbar then says what it depends on.
- **Field order and layout:** the preview's existing layout editing, not a second implementation.
- **Without dragging:** every gesture has a menu and keyboard path (MODEL_AUTHORING).
- **Suggest…:** where a provider is configured, an assistant's proposal lands as Proposed cards. With none, it
  is not shown.

### Engine and API work

1. The `unpivot`, `fillDown` and heading-row readings in the import profile, the reader, the dry run and the
   import, in PostgreSQL over the whole set; `docs/API.md` updated.
2. A route returning whole-set join candidates between two sources or columns.
3. A table-shaped proposal for one sheet, answered at once without the inference job.
4. The operation requests of the table above; a one-step route only where a client cannot compose them.
5. **An assistant's result must carry its profile.** The session can pass a dry run with the profile sent inline,
   and `tasks/agent.py` does not check that `draft.profile_json` was stored. Not proven in a run; PL3b tries it
   once, and if the profile can be missing, the task fails with a plain reason unless it is stored.

**Door check (ADR-032):** the new profile readings change only how rows are read. Identity, attribute storage,
history, bulk APIs, `match` and mapping coverage are not affected.

**Measure once:** a drop and its dry run at 200 and 2,000 records, reported with AI, job and overhead shown
apart where relevant. Known figures: an editor step at 2,000 records about 1.4 s; dry runs of 19,453 items about
7 s and 40,107 items 22.2 s; a large workspace's step about 3.5 minutes (`POSTGRESQL_BUDGETS.md`). The last is
why PP-D9 stands. Volume runs only if these basics give a reason.

**Tests:** journeys through the API on two model configurations (J51): a flat sheet shaped into a hierarchy with
its relationship, filter and group, then loaded; a wide sheet by `unpivot` and grouped rows by `fillDown`, each
repeated from the saved profile; a tied join asked rather than guessed; a caller without the groups refused by
code. Browser: a real sample workbook from drops to import, including undo, a refused row corrected and an
invalid draft; each gesture by keyboard; 390px; axe; no 5xx. Real-file smoke on the user's samples: a flat
hierarchy, a wide sheet with its header on row 2, and a workbook with side-by-side lists. **Before and after:**
an inventory diff on the user's model, since the profile reader changes.

**Documentation (the user, 2026-10-31: required, part of being finished):** the guide explains the canvas for
a person who has never seen it: a how-to in "Model your domain" ([0.13 plan](BASE_0_13_IMPLEMENTATION_PLAN.md#5-model-your-domain))
covering placing cards, making lists, connecting (hierarchy and relationship), filters and groups, reading
refused rows, wide sheets and grouped rows, repeating a load from the saved profile, and doing it all without
dragging and through the API, with screenshots. PL3b updates these pages in the same change, by the rule in the
[documentation plan](DOCUMENTATION_PLAN.md#timing). If the guide does not exist yet when PL3b is delivered, the
text goes in with PL3b as the seed in `MODEL_AUTHORING.md` and `PRODUCT.md`, and DOC writes it from there.

**Said plainly:** the canvas builds a new model, or a new version of a draft's. Reshaping records already in a
workspace stays with restructuring and WM1. Consumer APIs and security stay in their own pages.

## R: Build acceptance and release

Starts with the full review of every change since 0.16; the contract lock marked additive (the new profile
fields and routes); documentation (PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, API, MODEL_AUTHORING, journeys,
CHANGELOG); each heavy run announced, one at a time.

## Exit gate

- A real workbook is shaped on the canvas without a dialog and without AI, every row checked, and becomes a
  workspace in one confirmed step.
- A flat sheet becomes a hierarchy, a list dropped on a field becomes a relationship, a wide sheet becomes rows,
  and rows under headings get their parents; each repeats next month from the saved profile.
- With a provider, an assistant's result opens on the same canvas and can be corrected there.
- Every drag has a menu and keyboard path, and everything a drop does is available through the API.
- A change set publishes from one main action; a form asks required fields first; a workspace has its page and
  its search; identifiers are out of the common pages.
- No capability is removed.
- The user has judged the canvas on their own workbooks.
