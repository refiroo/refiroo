# Base 0.11 implementation plan

**Status:** Planned 2026-10-15, after 0.10.0, replacing the planning input of the same day (its
content is kept below: the user's requirements, the R findings and the rules for release runs).
**The workspace-model part comes first** (the user, 2026-10-15): every package about workspaces and
their models (a model of its own per workspace, moving a workspace to another release, data moved
between workspaces whose models differ) is grouped as [Part 1](#part-1--workspace-models) and
delivered before production hardening. D1 is the user's; **D2, D3 and D12 were accepted by the user
(2026-10-15)**; D4–D11, D13–D29 and the move inventory were accepted with the [P0 plan](#p0-plan-2026-10-15) (2026-10-15). Work
packages are specified below at package level; each package's detailed plan, test cases and
decisions are written and accepted when it starts, and it is delivered in the order of the
[delivery queue](#delivery-queue), each by the [delivery steps](#how-a-package-is-delivered).
**Delivered:** P0 (2026-10-15).

**Target:** Product 0.11.0, [production hardening and staged model rollout](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout),
with the two requirements the user added on 2026-10-15 (ROADMAP commit `a0859ae`).

**Depends on:** Product 0.10.0, released 2026-10-15 (tag `v0.10.0`), in particular:

- immutable model releases with their metadata stored per release (`model_object_types` and the
  other `model_*` tables are keyed by `model_release_id`), and the registry resolving any installed
  release by its ID (`resolve_pinned_release`), as change sets and publications already do;
- the compatibility analysis (`engine/model/compatibility.py`) and the guarded activation
  (`activate_model_release`, 0.8 W5);
- 0.9 J5's counterparts (`engine/records/counterparts.py`): another workspace's records loaded as
  this workspace's own, found again by `sourceId`;
- import profiles and value maps (0.9 J2), the dry run of every item (D67), the load into a
  reviewed change set (A5b, A5c), and A5's mapping operations with undo;
- A6/A7's inference: proposals with evidence and alternatives, matching by keys, names, values and
  stored records;
- type changes of existing records in change sets (ADR-034);
- the job worker with leases (0.9 B2) and the R fixes R-F5–R-F9, R-F14, R-F19.

0.14 (another session's track: the management API documented, the palettes, UP2's start page)
blocks nothing here and is taken as filler when the user asks.

## Product outcome

An organisation runs several workspaces on one instance, and each workspace runs a model of its own:
different models, not only different versions of one model. A workspace's model is installed,
activated and migrated without touching the others, and its data moves to another release through a
previewed, confirmed migration. Records move or are copied between workspaces whose models differ,
wherever the models are compatible, through a mapping the engine proposes and the administrator
completes. The engine then runs safely with several processes and nodes on one database, at full
volume, observed and backed up. Authentication and authorization follow in 0.12.

Exit gate: the [roadmap's 0.11 exit gate](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout) in full.

## The user's requirements (2026-10-15)

### 1. Each workspace runs a model of its own

**Requirement (the user, "it has to be covered by 0.11"):** different workspaces of one instance may
run **different models**, not only different versions of one model; each workspace's model is
installed, activated and migrated without touching the others. The user had asked for it for weeks
and had been told 0.11 covers it.

**How it got narrowed (found 2026-10-15):** MODEL_AUTHORING promised it ("until 0.11 gives each
workspace a model of its own"), but ROADMAP's 0.11 scope said only "workspace-scoped model-release
assignment", which reads as staged versions of one model, and an unscheduled entry ("workspace groups
as owners of a model history") put separate models *after* 0.11. DECISIONS (ADR-021's closing
paragraph), TODO and ROADMAP_COVERAGE describe it as "staged tenant or governance-domain rollout".
ROADMAP now states the requirement in 0.11's scope and exit gate (commit `a0859ae`); this plan builds
on that wording, not on the older one.

**Not multi-tenancy.** Hosting stays one instance per organisation; per-workspace models are within
one organisation. The word "tenant" in DECISIONS and TODO conflicts with that rule and is corrected
in P0 (D22).

### 2. Data moved between workspaces whose models differ

**Requirement (the user):** move (or copy) data between workspaces wherever their models are
compatible, even partly, with the mapping between them proposed by the engine and completed by hand;
"for this we should have literally everything which possibly can be needed". ROADMAP 0.11 holds it
in scope and exit gate (commit `a0859ae`). **Its placement in 0.11, beside requirement 1 which it
needs, was accepted by the user on 2026-10-15 (D3).**

## Principles and exclusions

1. **Generic.** No branch on an application, object-type, attribute or relation key. Every
   workspace-model journey runs on two differently shaped models side by side: `generated-a` and
   `generated-b` (`tests/journeys/configurations.py`), plus the example model with its keys renamed
   (0.10 D20). A move runs between two of them.
2. **One workspace, one snapshot.** A request resolves its workspace first, then that workspace's
   release; no request combines two snapshots (the roadmap's exit gate). A read spanning workspaces
   resolves each workspace's snapshot on its own (D7).
3. **API first.** Assigning, activating and migrating a workspace's model and every step of a move
   are API operations an integrator can send; the UI is one client.
4. **Same checks.** Activation per workspace uses the existing compatibility analysis on that
   workspace's data; a move uses the import's dry run, row outcomes and change set. No second
   validation path.
5. **Lifecycles unchanged.** Model draft → immutable release → activation, now into one workspace;
   data through a job into a reviewed change set by default.
6. **Set work in the database.** Migrations, dry runs and moves run as `INSERT … SELECT` and `MERGE`
   in PostgreSQL in background jobs; nothing moves records row by row through Python.
7. **Nothing dropped silently.** What a migration or a move cannot carry is reported per item before
   confirmation, and nothing is applied without it.
8. **Bounded and paged.** Assignment lists, migration previews, move reports and mapping proposals
   page under ADR-030; every limit is documented and returned in errors.

Excluded: multi-tenancy (one instance per organisation), workspace groups owning a model history
(ROADMAP, unscheduled; its door stays open, D5), migration-class operations in the editor (1.0, on
0.11's migration boundary), relationships between records of different workspaces (D8),
authentication and authorization (0.12).

## What already exists

Checked against the code at `e2cce78`:

- **One active release for the instance.** `model_runtime_state` is a singleton row
  (`ck_model_runtime_state_singleton`) naming the active release, and `model_releases.is_active` is
  set for one release (`activate_model_release` clears it everywhere). `resolve_model_snapshot`
  takes no workspace; it is called from about 25 modules (routers, jobs, dry runs, inference,
  profiling, the event dispatcher and subscriptions, exports, the CLI).
- **The commit guard** (`require_resolved_release`, 0.8 W5) checks at every commit that the release
  a write was validated under is still the active one, under a share lock on the singleton row;
  activation holds that row `FOR UPDATE`. Per workspace, the lock moves to the workspace's
  assignment.
- **Metadata per release.** Installing projects the model into `model_*` tables keyed by
  `model_release_id`, and releases are unique by `(release_key, release_version)`. Two models with
  different keys can already be installed side by side; only activation is single.
- **Pinned contexts.** Change sets and publications carry `model_release_id`, and
  `resolve_request_model` already resolves their pinned release. Live reads fall back to the active
  one.
- **Workspaces** have a key, a status, an active publication and a feed position; a default
  workspace is held in `workspace_runtime_state`, and requests without `workspaceKey` resolve it
  (`resolve_workspace`). `GET /model` and `GET /model/placements` already accept `workspaceKey`,
  but it only selects change-set or publication context today.
- **Instance-wide resources bound to the active release:** import profiles (instance-wide, D65,
  `checked_release_id`), model drafts and their base release, source files, unique attribute values
  (`unique_attribute_values`, whose trigger follows `model_runtime_state`), matrix cell states, the
  consumer APIs (definitions read from the active release; subscriptions, events and checkpoints are
  per workspace).
- **Counterparts (0.9 J5):** a file holding another workspace's record IDs loads, with
  `otherWorkspaceIds: "counterparts"`, as this workspace's own records keyed by `sourceId`; without it
  the import refuses with `RECORD_IDS_OF_ANOTHER_WORKSPACE`.
- **Gates:** model administration under `MODEL_ADMIN_MUTATIONS_ENABLED`, which requires
  `WEB_CONCURRENCY=1`; installation runs under an in-process lock.

## Design documents

| Document | Holds | State |
| --- | --- | --- |
| This plan | Outcome, tracks, packages, sequence, decisions, delivery records, acceptance | Planned 2026-10-15 |
| [DECISIONS.md](DECISIONS.md) | ADR-042 (each workspace runs its own model release), written in P0; ADR-021's closing paragraph superseded | Written in P0 |
| [API.md](API.md) | P0 writes the designs: workspace model assignment and activation, migration preview and confirm, the model-to-model mapping and the move; each package moves its part to "delivered" | Written in P0 |
| [MODEL_AUTHORING.md](MODEL_AUTHORING.md) | "New from a workbook" and install-and-activate into a chosen workspace | Amended in P0 |
| [USER_JOURNEYS.md](product-functionality/USER_JOURNEYS.md), [API_JOURNEYS.md](testing/API_JOURNEYS.md) | J36–J38 and their API inventory | Extended in P0 |
| [OPERATIONS.md](OPERATIONS.md) | Several processes and nodes, metrics, backup and restore | Track N and O |
| [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md) | The doors the move and the compatibility commitment touch | Checked in P0 and L2 |

## Scope inventory

| # | Roadmap 0.11 item | Package |
| --- | --- | --- |
| 1 | Each workspace runs a model of its own | M1–M6 |
| 2 | Executable workspace-scoped data migration plans | V1 |
| 3 | Historical-draft model replacement for one workspace (GAP-02) | V2 |
| 4 | Moving a draft (change set) onto a release its content does not fit (ADR-028) | V3 |
| 5 | Mixed-schema conversion rules and a bounded supported schema-version window | V4 |
| 6 | Data moved between workspaces whose models differ | X1–X5 |
| — | The backend suite's time (D152, 0.10 R) | S1 |
| 7 | Snapshot propagation across processes; the job worker on several nodes | N1, N2 |
| 8 | Database constraints as a second line, decided on evidence; the concurrency exit gate | N3 |
| 9 | Production-scale PostgreSQL: full-volume fixture, pool sizing, bulk-path statistics | Q1 |
| 10 | Model-derived indexes, unique checks on non-text values | Q2 |
| 11 | Precomputed sort keys (0.8 D26) | Q3 |
| 12 | Metrics, structured logging, health and readiness | O1 |
| 13 | Backup and restore rehearsal; the Operations page (U7) | O2 |
| 14 | Touch drag in the tree lens (0.8 D35) | U1 |
| 15 | Licensing, contribution and security policies; the compatibility commitment; supported schema versions published | L1, L2 |

## Tracks overview

### Part 1 — Workspace models

All workspace-model work, delivered first and in this order.

**Track M — each workspace a model of its own.** M1 gives every workspace its own release assignment
and makes every request resolve its workspace before its snapshot. M2 installs and activates a model
into one workspace, with the compatibility check, unique values, matrix states and subscriptions
scoped to it. M3 binds what is instance-wide today (import profiles, drafts, source files, jobs, the
consumer APIs) to a workspace's model. M4 defines reads spanning workspaces whose models differ. M5
is the UI: the shell follows the workspace's model, and Settings › Model manages each workspace's
model. M6 is the checkpoint: two workspaces on two different models, composed in the browser.

**Track V — a workspace moved to another release.** The migration boundary the roadmap places in
0.11. V1 is the executable migration plan for one workspace: preview of conversions and loss,
confirmation bound to the reviewed versions, atomic switch of data and assignment. V2 (GAP-02) and
V3 (ADR-028) reuse it for a change set started from a publication and for a change set moved onto a
release it does not fit. V4 fixes the schema-language window and the conversion rules that let
different schema versions run side by side.

**Track X — data moved between workspaces whose models differ.** X1 is the model-to-model mapping,
proposed by the inference and completed with A5's mapping operations. X2 selects what moves and dry
runs every item. X3 moves or copies it into a reviewed change set, with identity, relationships,
hierarchy, values and history carried or reported. X4 is the move editor. X5 is the checkpoint.

### Part 2 — Production hardening

**S1 — the backend suite's time** (D152). **Track N — several processes and nodes:** snapshot
propagation (now per workspace), the job worker under real concurrency, the invariants at full
volume. **Track Q — PostgreSQL at full volume:** the fixture, pool sizing, bulk-path statistics,
model-derived indexes, sort keys. **Track O — operability:** metrics, logs, health and readiness,
backup and restore, the Operations page. **U1 — touch drag.**

### Part 3 — First public release

**Track L:** licensing, contribution and security policies (L1), the compatibility commitment with
the supported schema versions and their dates (L2). **R:** build acceptance and release.

### Why the workspace models come first

The user asked for it (2026-10-15). It also fits the design:

- **Every later track depends on the resolution model.** Snapshot propagation across processes (N1),
  model-derived indexes (Q2), the unique-value trigger and the backup rehearsal ("without mixed-model
  requests") all change shape when the active release is per workspace. Built after M1, each is
  built once; built before, each is built for a singleton and rebuilt.
- **It carries the most design risk.** About 25 modules resolve "the" active release. Finding what
  that costs early leaves room to cut elsewhere (D13), never here.
- **The move needs it.** Track X has nothing to move between until two workspaces can run two
  models.

What it costs: the backend suite stays slow for longer (D2), and Track N's multi-process work waits,
so M1–M5 are built and tested with one web process, as today.

## How a package is delivered

As in 0.10: each package is one vertical slice, delivered on the instruction **"deliver
`<package>`"**, in the order of the [delivery queue](#delivery-queue).

1. **Read** the package entry, the design sections it cites, the ADRs it names and `AGENTS.md`.
2. **Plan** under the package (`##### <package> plan (date)`): what is built, checked against the
   code at the current commit; the decisions it raises (D23 onward) with a recommendation, each in
   plain words (what, why, cost); the journey test cases. The user accepts the decisions and the
   test cases before coding.
3. **Mock up first for a new surface.** A package that adds or reshapes a screen (M5, X4, O2, U1)
   shows a sample in the browser first and builds on the shape the user approves; it is complete
   when the user approves its screenshots.
4. **Build** the slice: migration when the package names one, service, route, OpenAPI lock
   re-baseline (checked by diffing the document), frontend where the scope says so.
5. **Test** the journeys the plan lists, written first and seen failing, plus unit tests for the new
   code's purpose. Run the package's groups and the changed boundary per
   [EXECUTION_GUIDE §2](testing/EXECUTION_GUIDE.md#2-changed-boundary--selected-checks) only. Test
   work stays a quarter of the package or less; no full suite before R.
6. **Record** under the package: **Delivered YYYY-MM-DD.**, what was built, where it differs from the
   design, and **Checks:** the groups run with their counts, and what was not run and why. Name what
   the user still cannot do and which package delivers it.
7. **Update** CHANGELOG (Unreleased), PROJECT_STATUS and TODO. Commit only when asked.

A package starts when every package it **needs** is delivered. A defect, a revised decision or a new
need found during a package that changes something the next package builds on becomes a named
amendment package (M1a, …); otherwise it goes into TODO.

### How heavy runs are done (the user, 2026-10-15)

- Each heavy run (the full suite, the browser runners, a gate, a long measurement) is announced with
  its expected scope and run only on the user's go-ahead, one at a time, never several test
  processes side by side because the machine has cores to spare.
- On a failure or a figure out of line: stop, report the cause and the options, ask before any
  rerun, diagnostic run or second measurement.
- Check the machine's load before a block; a failure under load is not evidence of a defect.
- Iterate on a new runner or helper with its smallest slice (one model, one walk), never the whole
  gate.
- Small verification runs (a handful of test files, one process) need no separate approval.
- Clean up after every block: servers, scratch databases, the harness's PostgreSQL, output folders.

These apply to every package and to R, and especially to Track Q's full-volume measurements.

### Test groups and runners added in 0.11

| Group or runner | Introduced by | Covers |
| --- | --- | --- |
| `workspace_models` marker | M1 | Assignment, resolution per workspace, activation per workspace, the commit guard per workspace |
| `migration` marker | V1 | Migration previews, confirmations, conversions, the schema window |
| `move` marker | X1 | The model-to-model mapping, dry runs, moves and their reports |
| `test:browser:workspace-m5` | M5 | The shell and Settings › Model with two workspaces on two models |
| `test:browser:workspace-x4` | X4 | The move editor |
| `test:browser:touch-u1` | U1 | Touch drag on phone emulation |

Existing groups carry on: `model`, `jobs`, `startup` (every migration), `contract` (every route
change) and `volume` (every budget).

## Delivery queue

| # | Package | Needs | Scope in one line |
| --- | --- | --- | --- |
| 0 | — | 0.10.0 released | **Met 2026-10-15**, tag `v0.10.0` |
| 1 | [P0](#p0-design-pass) | — | **Delivered 2026-10-15.** Decisions D4–D11 and D13–D29 settled; ADR-042; API design; the move inventory completed; journeys J36–J38; mock-ups of M5 and X4 |
| | **Part 1 — workspace models** | | |
| 2 | [M1](#m1-a-release-assignment-per-workspace) | P0 | **Delivered 2026-10-15** (M2 folded in). Every workspace names its release; every request resolves its workspace, then its snapshot; the commit guard per workspace |
| 3 | [M2](#m2-installing-and-activating-into-one-workspace) | — | **Folded into M1 (D32).** Activation into one workspace with its own compatibility check; unique values, matrix states and subscriptions scoped to it; a new workspace created on a model |
| 4 | [M3](#m3-instance-wide-resources-bound-to-a-workspaces-model) | M2 | Import profiles, drafts, source files, jobs and dry runs, consumer APIs and events resolved through the workspace's model |
| 5 | [M4](#m4-reads-spanning-workspaces) | M3 | Cross-type lookup, feed, mapping coverage, exports and counterpart imports when models differ |
| 6 | [M5](#m5-the-ui-follows-the-workspaces-model) | M4 | The shell follows the workspace's model; Settings › Model per workspace; "New from a workbook" into a chosen workspace |
| 7 | [M6](#m6-workspace-models-checkpoint) | M5 | Two workspaces on two models composed in the browser; the roadmap's first workspace-model exit item; tagged 0.11.0-alpha.1 (D12) |
| 8 | [V1](#v1-a-workspaces-data-migrated-to-another-release) | M2 | Migration plan for one workspace: preview, conversions, loss, confirm bound to versions, atomic switch |
| 9 | [V2](#v2-a-change-set-from-a-publication-moved-to-another-release) | V1 | GAP-02: a change set started from a publication moved to a named installed release |
| 10 | [V3](#v3-a-change-set-moved-onto-a-release-it-does-not-fit) | V1 | ADR-028: a change set moved onto a release its content does not fit, previewed and confirmed |
| 11 | [V4](#v4-the-schema-language-window) | V1, M6 | The bounded window of schema versions run side by side; explicit conversion rules |
| 12 | [X1](#x1-the-mapping-between-two-models) | M4, P0 inventory | The model-to-model mapping: proposed, completed with mapping operations, saved and reused |
| 13 | [X2](#x2-selection-and-the-dry-run-of-a-move) | X1 | What moves; the dry run of every item; what cannot move, with reasons |
| 14 | [X3](#x3-the-move) | X2 | Copy or move into a reviewed change set: identity, relationships, hierarchy, values, history |
| 15 | [X4](#x4-the-move-editor) | X3, M5 | The move editor: the two models, the mapping, the proposals, the dry-run figures and the report |
| 16 | [X5](#x5-move-checkpoint) | X4 | The roadmap's move exit item at full volume, measured once |
| | **Part 2 — production hardening** | | |
| 17 | [S1](#s1-the-backend-suites-time) | — | The backend suite back under its 5-minute ceiling (D152); a filler during Part 1, delivered before X2 at the latest (D2) |
| 18 | [N1](#n1-snapshots-across-processes) | M2 | Assignment changes propagated across processes; model administration with `WEB_CONCURRENCY` above 1 |
| 19 | [N2](#n2-the-job-worker-on-several-nodes) | N1 | Every job kind's leases, cancels and supersession under real concurrency |
| 20 | [N3](#n3-concurrency-invariants-at-full-volume) | N2, Q1 | Several processes and nodes on one database at full volume; constraints as a second line, on evidence |
| 21 | [Q1](#q1-full-volume-fixture-pool-and-bulk-paths) | — | The fixture at full scale; pool sizing; the bulk-path statistics pattern; `NOT IN` subqueries |
| 22 | [Q2](#q2-model-derived-indexes) | M2, Q1 | Indexes derived from each workspace's model; unique checks on non-text values |
| — | _cut line (D13)_ | | _If R is out of reach, 0.11.0 releases here and Q3 and U1 move to 0.11.x_ |
| 23 | [Q3](#q3-precomputed-sort-keys) | Q2 | Attribute and ancestor sorts over very large parents within the list budget |
| 24 | [O1](#o1-metrics-logs-health-and-readiness) | N1 | Metrics, structured logging, health and readiness |
| 25 | [O2](#o2-backup-restore-and-the-operations-page) | O1, M6 | Backup and restore rehearsed with workspaces on different models; Settings › Operations (U7) |
| 26 | [U1](#u1-touch-drag-in-the-tree-lens) | — | Long-press drag in the tree lens on phones (0.8 D35) |
| | **Part 3 — first public release** | | |
| 27 | [L1](#l1-licensing-and-policies) | — | Licensing checklist, contribution and security policies |
| 28 | [L2](#l2-the-compatibility-commitment) | V4 | The compatibility commitment, the supported schema versions and their dates, the doors kept open |
| 29 | [R](#r-build-acceptance-and-release) | all above the cut | Build acceptance and release |

## Sequence and dependencies

```text
Design:         P0
Part 1
 Own model:     P0 ─ M1 ─ M2 ─ M3 ─ M4 ─ M5 ─ M6
 Releases:               M2 ─ V1 ─┬─ V2
                                  ├─ V3
                          M6 ─────┴─ V4
 Moves:                       M4 ─ X1 ─ X2 ─ X3 ─ X4 ─ X5      (X4 also needs M5)
Part 2
 Suite:         S1                                (filler in Part 1; before X2, D2)
 Nodes:                  M2 ─ N1 ─ N2 ─ N3        (N3 also needs Q1)
 Volume:        Q1 ─ Q2 (needs M2) ── cut line (D13) ── Q3
 Operations:    N1 ─ O1 ─ O2 (needs M6)
 Touch:         U1 (independent; filler)
Part 3:         L1 (independent; filler) · V4 ─ L2
Release:        everything above the cut line → R
```

Part 1 runs in the order shown. V1 may start after M2, but is queued after M6 so the workspace
models are accepted together first. Q1, U1 and L1 need nothing from Part 1 and may be taken as
fillers while a Part 1 package waits for screenshot approval, as A3 was in 0.10.

## P0: Design pass

**Scope:**

- Settle D4–D11 and D13–D22 with the user, workspace-model decisions first. Record ADR-042 (each workspace runs
  its own model release) and mark ADR-021's closing paragraph superseded; correct "tenant" (D22).
- **Complete the move inventory** (below) with the user: every case a move can meet, each with how
  it is handled or reported. Nothing in Track X is designed before the user accepts it.
- Check every call of `resolve_model_snapshot` and every reader of `model_runtime_state` and
  `is_active` against D4–D11, and list which package changes it. This list is M1–M4's scope.
- Write the API design in API.md's style: workspace model assignment and activation, the migration
  preview and confirmation, the model-to-model mapping, the move's dry run and the move.
- Add journeys J36–J38 to USER_JOURNEYS and their routes, codes and settings to API_JOURNEYS.
- **Mock up** Settings › Model per workspace and the shell switching between two workspaces on two
  models (M5), and the move editor (X4), as claude.ai artifacts on the Atlas tokens, light and dark,
  1440px and 390px, in an invented neutral domain. The user approves them before M5 and X4 build.

**Journeys** (wording final in USER_JOURNEYS):

- **J36 Run a workspace on a model of its own.** Variants: create a workspace on a model other
  workspaces do not run; activate a new release of one workspace's model, the others unchanged; a
  workspace on a different model of the same application keys; "New from a workbook" into a new
  workspace; a write refused when its workspace's release changed meanwhile; reads in each
  workspace see only their model; a cross-workspace read with different models.
- **J37 Move a workspace to another release.** Variants: preview with conversions and loss;
  confirm; cancel; a stale review refused; a failed execution changes nothing; a change set from a
  publication moved (V2); a change set moved onto a release it does not fit (V3); a model of the
  previous schema version activated beside one of the current version (V4).
- **J38 Move data between workspaces whose models differ.** Variants: the mapping proposed and
  completed; copy a whole workspace; move a subtree; a relationship whose other end stays behind; a
  unique value already held in the target; a second move found again; what could not move
  reported; the change set reviewed and published.

**The move inventory** (first list from the planning input; P0 completes it):

- Identity: a moved record's identity in the target, found again on a second move (J5's
  counterparts), moving back, and a record moved twice from two sources.
- Move or copy, and what the source keeps (deleted in a change set like `missing: delete`, or kept).
- Selection: a whole workspace, chosen types, a subtree, a filtered set, a selection (K1).
- Relationships whose other end stays behind, comes along, or exists in the target already;
  relation attributes; required relationships and ownership.
- Hierarchy: parents in the target, containment that differs between the models, a parent created
  by name (`missing: create`).
- Values: conversion between attribute types (the attribute registry), value maps, unique values
  already held in the target, required values the source lacks, list values (lookups) created or
  matched.
- Translations and effective periods (0.9 C16) where both models have them.
- History and provenance: the target's audit entries naming the move and its source; the source's
  history untouched; publications.
- The target's validation and refusals, row by row as an import's (J3).
- Volume: whole-set work in PostgreSQL, a background job, a dry run of every item, measured once.
- Consumer APIs and events of the target workspace: what its subscribers receive.
- Who may move data (0.12 authorization; until then the capability gates).

**Exit:** decisions recorded; ADR-042 written; the move inventory accepted; API design written;
journeys added; the M5 and X4 mock-ups approved; package scopes confirmed or amended.

**Checks:** documentation and throwaway mock-ups; `pytest tests/test_api_journeys.py`; no product
code.

##### P0 plan (2026-10-15)

**Planned 2026-10-15; accepted by the user the same day ("okay"): every decision as recommended and
the move inventory as listed.**
Checked against the code at `e2cce78`:

- **Resolution.** `resolve_model_snapshot(session)` (`engine/model/registry.py`) reads the singleton
  `model_runtime_state` and binds the session to that release for the commit guard. It is called in
  17 modules, and through the `ActiveModelSnapshot` and `RequestModelSnapshot` dependencies in 7
  routers. Change sets and publications already resolve their pinned release by ID
  (`resolve_pinned_release`); the registry already caches one parsed model per release.
- **The singleton is read directly**, outside the resolver, in 12 places (the list below), and once
  in PostgreSQL: the unique-values triggers (`20261007_07`) read
  `model_runtime_state.active_model_release_id` to know which attributes are unique, and refill
  `unique_attribute_values` for the whole instance when it changes.
- **`model_releases.is_active`** is written by activation, bootstrap and the schema-upgrade CLI and
  read only by bootstrap, for a database older than `model_runtime_state` (0.6). Nothing serves it:
  `GET /model-releases` computes `active` from the runtime state.
- **Activation's compatibility analysis** (`analyze_compatibility`) counts stored records of every
  active workspace; contract checks and subscription suspension are instance-wide; matrix states
  resync for every workspace (`matrix_states.sync_all`).
- **Publishing** refuses a change set pinned to a release other than the active one
  (`CHANGE_SET_MODEL_RELEASE_CONFLICT`); creating one captures its base under a share lock on the
  singleton. Per workspace, both compare with the workspace's release instead.
- **Startup** resolves the active release once; if it cannot be parsed the registry is marked
  unhealthy and the whole instance answers `503 MODEL_REGISTRY_UNAVAILABLE`.
- **Schema versions (D11).** The compiler accepts 0.5–0.10 and compiles every one into the same
  `EngineModel`; documents of 0.8 and earlier go through `LegacyEngineModel`, a subclass that only
  reads the old consumer API shape. One parser serves every version already, so running them side by
  side costs nothing extra.
- **Counterparts (0.9 J5)** are computed, not stored: a record's counterpart in workspace `B` is the
  name-based UUID of `B/{id}`. Nothing records where a record came from. A second move from the same
  source finds its earlier result by recomputing the ID; moving a record back does not find the
  original, since the counterpart of the counterpart is a third ID (D23).
- **Consumer APIs.** Every read route takes `workspace` and resolves the workspace, then the active
  release; the API index and the OpenAPI per definition take no workspace.
- **Import profiles** are instance-wide with `checked_release_id`; source files carry an optional
  workspace; drafts name a base release and compile against the active release when they have none.

**The call sites** (M1–M4's scope; each package changes the ones it is listed with):

| Where | What it reads | Package |
| --- | --- | --- |
| `engine/model/registry.py`: `resolve_model_snapshot`, `require_resolved_release`, `resolve_request_model`, `ModelRegistry.resolve_active`/`refresh_active` | The singleton; the commit guard's share lock | M1 |
| `management/dependencies.py` (`ActiveModelSnapshot`, `RequestModelSnapshot`) and the routers using them: `model`, `objects`, `relations`, `attributes`, `change_sets`, `model_releases`, `model_management` | The active snapshot per request | M1 |
| `management/routers/model.py` `GET /model-runtime-state`; `model_releases.py` (`active` filter and field) | The singleton | M1 (read), M2 (the route's new shape) |
| `engine/change_sets/lifecycle.py` (base capture), `engine/change_sets/publish.py` (`CHANGE_SET_MODEL_RELEASE_CONFLICT`) | The singleton | M1 |
| `engine/records/feed.py` `take_positions` (the release each write records) | The singleton | M1 |
| `management/reference/__init__.py` | `resolve_active` | M1 |
| `app/main.py` startup and readiness | `resolve_active`, `ready` | M1 (D29) |
| `engine/model/bootstrap.py`, `cli/model_schema_upgrade.py`, `model_releases.is_active` | The singleton and the flag | M1 (D24) |
| `engine/model/releases.py` `activate_model_release`, `engine/model/compatibility.py`, `routers/model_management.py` | Lock, check and switch of the singleton | M2 |
| Migration `20261007_07`'s triggers (`unique_attribute_values`) | The singleton, in SQL | M2 |
| `engine/indexes/matrix_states.py` (live owner's shapes, `sync_all`) | The singleton | M2 |
| `engine/events/subscriptions.py` (`suspend_left_behind`, create and change) | The active model | M2 (suspension), M3 (the rest) |
| `engine/model/authoring/released.py` (a draft without a base) | The singleton | M3 |
| `engine/imports/profiles.py`, `engine/sources/store.py`, `profiling.py`, `profile_check.py`, `dry_run.py`, `inference/run.py` | The active snapshot | M3 |
| `engine/jobs/batches.py` `open_batch_context`, `engine/jobs/background.py` `open_job_context` | The active snapshot (jobs already record `model_release_id`) | M3 |
| `consumer/router.py` (eight routes), `engine/events/dispatcher.py`, `engine/events/worker.py` | The active snapshot | M3 |
| `engine/jobs/exports.py`, `management/projections/mapping.py`, `relation_matrix.py`, `routers/queries.py`, `engine/operations/mapping_replacement.py` | `resolve_request_model` (spanning reads in M4) | M1 (resolution), M4 (spanning meaning) |

**What P0 produces**, in this order, each with its approval point:

1. **Decisions.** The user accepts or changes D4–D11, D13–D22 and the new D23–D29 below; they are
   recorded here and package scopes amended where a decision changes them.
2. **The move inventory** below, accepted by the user. It is Track X's scope.
3. **ADR-042** and the superseded paragraph of ADR-021; "tenant" replaced (D22).
4. **The API design** in API.md under "Designed for 0.11": workspace model assignment and
   activation, the migration preview and confirmation, the model-to-model mapping, the move's dry run
   and the move, at contract level (routes, bodies, codes, paging, limits).
5. **Journeys** J36–J38 in USER_JOURNEYS and their planned routes, codes and settings in
   API_JOURNEYS; MODEL_AUTHORING amended for D15.
6. **Mock-ups** of M5 (Settings › Model per workspace, the shell switching between two workspaces
   on two models, a workspace created on a model) and X4 (the move editor), as claude.ai artifacts
   on the Atlas tokens, light and dark, 1440px and 390px, in an invented neutral domain. The user
   approves them.
7. **The P0 record.**

**Decisions.** D4–D11 and D13–D22 are the plan's, restated where the check changed them; D23–D29
are new from the check.

| # | Question | Recommendation |
| --- | --- | --- |
| D4 | What a workspace without "its own" model follows | **As planned, made simpler.** Every workspace names its release; nothing follows a default. The check shows `model_runtime_state` would then only hold "the release a new workspace starts on". Recommended: drop it; a workspace created without a release starts on the default workspace's release (`workspace_runtime_state` already names that workspace). One concept fewer, and the unique-values trigger and commit guard move to the workspace row anyway |
| D5 | What "a model" is | As planned: the line of releases sharing one `release.key`; releases stay instance-wide and immutable |
| D6 | Routes naming no workspace | As planned: the default workspace's model; `workspaceKey` selects another; any installed release readable by ID |
| D7 | Reads spanning workspaces | As planned: each workspace with its own snapshot; every item names its workspace and release; a filter or sort naming an element some workspace's model lacks is refused, naming those workspaces. Counterpart imports between different models go through the move |
| D8 | Relationships across workspaces | As planned: none |
| D9 | Import profiles | As planned: bound to a model (release key), checked against the target workspace's release when used |
| D10 | Consumer APIs | **As planned, with the two routes that lack it:** definitions, events and webhooks per workspace; the API index and the OpenAPI per definition gain the `workspace` parameter the read routes already have, the default workspace when absent |
| D11 | Schema versions side by side | **As planned, confirmed:** 0.5–0.10, the versions the compiler accepts today; they compile into one internal model (checked above). V4 writes the conversion rules and the refusal outside the window; L2 publishes the dates |
| D13 | Cut line | As planned: Q3 and U1 may move to 0.11.x; never Part 1 |
| D14 | Gates | As planned: assignment and activation under `MODEL_ADMIN_MUTATIONS_ENABLED`; migrations and moves also under `INTEGRATION_JOBS_ENABLED` |
| D15 | "New from a workbook" with a new model | As planned: installed and activated into a workspace chosen or created in the same step |
| D16 | Identity of a moved record | **As planned for the first and later moves; moving back by D23.** A moved record's ID is its counterpart in the target, so the next move from the same source finds it again |
| D17 | Move or copy | As planned: copy by default; move is the copy plus the source's deletion in a change set of the source workspace, reviewed on its own |
| D18 | Where the mapping lives | As planned: a saved resource beside import profiles, source a workspace's model, edited with A5's mapping operations, undo and history |
| D19 | The job of a move | As planned: one job kind with the import's phases and row outcomes |
| D20 | A move in the target's feed and events | As planned: nothing until the change set is published |
| D21 | Where the mock-ups live | As planned: claude.ai artifacts |
| D22 | "Tenant" | As planned: replaced by "workspace" and "model" in DECISIONS (ADR-021) and TODO; ROADMAP_COVERAGE no longer uses the word (checked) |
| D23 | Moving a record back | **New.** Counterparts are computed, so moving a record back would create a third record instead of finding the original. Recommended: a move records each moved record's origin (source workspace and record ID) in a table of its own, written in the same statement as the copy; a move finds an earlier result by its counterpart ID and the original by that origin. Cost: one table and its index in X3; the computed ID stays as it is, so J5's imports are unchanged |
| D24 | `model_releases.is_active` | **New.** Dropped in M1's migration: written in three places, read only by a 0.6-era bootstrap path, served nowhere. `GET /model-releases`' `active` filter and field become "assigned to at least one workspace", plus the list of workspaces |
| D25 | What a draft compiles against | **New.** A draft without a base release compiles against the default workspace's release today's way; with a base, against the base, and its compatibility check runs on every workspace that runs the base's model, reported per workspace, so the editor shows which workspaces an activation would touch |
| D26 | Open change sets when their workspace changes release | **New.** As today's rule, per workspace: a change set pinned to a release its workspace no longer runs cannot publish (`CHANGE_SET_MODEL_RELEASE_CONFLICT`, now naming the workspace) and is moved (V3) or discarded; activation lists them in its result |
| D27 | A consumer API key in two models | **New.** Allowed: subscriptions and checkpoints are per workspace already, so the same key may mean different contracts in two workspaces; the index and OpenAPI name the workspace and release they describe |
| D28 | Unique values per workspace | **New.** Uniqueness stays per workspace (the constraint is keyed by workspace already); the triggers read each written record's workspace release instead of the singleton, and activation refills only the target workspace's rows |
| D29 | A workspace whose release cannot be loaded at startup | **New.** Today one unparseable release stops the whole instance. Recommended: only that workspace answers `503 MODEL_REGISTRY_UNAVAILABLE` (naming it); the others serve; readiness reports it (O1). Follows "without touching the others" |

**The move inventory** (completed from the planning input; every case with how it is handled and
the package that does it; nothing in Track X is designed before the user accepts it):

| # | Case | Handled | Package |
| --- | --- | --- | --- |
| I1 | First move of a record | A new record in the target whose ID is the counterpart of the source ID; its origin recorded (D23) | X3 |
| I2 | Second move from the same source | Found by its counterpart ID and updated in the change set, not duplicated; the dry run says "update" | X2, X3 |
| I3 | Moving back to the source workspace | Found through its origin and updated; the dry run says "update original" | X3 |
| I4 | One target record from two sources | Two records (two counterparts); merging them is the user's, reported as possible duplicates when a unique or name match says so | X2 |
| I5 | Copy (default) | The source untouched | X3 |
| I6 | Move | The copy, plus a separate change set in the source workspace deleting the moved records, opened for review; deleting refused rows never | X3 |
| I7 | Selection | A whole workspace, chosen types, a subtree (a record and its contained records), a filtered set, a selection (K1); the selection is stored with the move | X2 |
| I8 | Type not mapped | Its records not moved, reported with the count and "map the type" | X2 |
| I9 | Type mapped to a type of other attributes | Mapped attributes carried; unmapped ones reported per attribute with counts | X1, X2 |
| I10 | Attribute of another value type | Converted through the attribute registry where a conversion exists (number to text, text to number when it parses, date formats); otherwise reported per value | X2 |
| I11 | Value map | The mapping holds value maps as an import profile does (0.9 J2), used before conversion | X1 |
| I12 | Unique value already held in the target | The item refused with the holder's ID, as an import row; "update that record instead" offered as a mapping choice (match by the unique attribute) | X2 |
| I13 | Required value the source lacks | Refused per record unless the mapping sets a default | X1, X2 |
| I14 | List values (lookups) | Matched in the target by key, code or name as an import does; missing ones created when the mapping says so, otherwise refused | X1, X2 |
| I15 | Relationship whose other end moves too | Carried, between the two moved records | X3 |
| I16 | Other end stays behind but exists in the target (moved before, or matched) | Carried to that record | X2, X3 |
| I17 | Other end stays behind and is not in the target | The relationship dropped and reported; the record still moves unless the relation is required | X2 |
| I18 | Relation type not mapped or not allowed in the target | Reported per relation type with counts | X1, X2 |
| I19 | Relation attributes | Carried as attributes are (I9–I13) | X3 |
| I20 | Required relationship or ownership the target demands | Refused per record when unmet, as the target's validation refuses an import row | X2 |
| I21 | Parent in the target | The parent moved along, found (I16), or named by the mapping (`missing: create` for a parent by name) | X1, X2 |
| I22 | Containment that differs between the models | The mapping names the target's parent relation; a contained record whose parent type is unmapped is reported | X1, X2 |
| I23 | Translations (types under a language list) | Moved as any related types; nothing special, since translations are modelled, not built in | X3 |
| I24 | Effective periods (0.9 C16) | Carried when both types declare one; dropped and reported when only the source does; required when only the target does (I13) | X2, X3 |
| I25 | History | The target's audit entries name the move, its source workspace and its job; the source's history and publications untouched; source history is not copied | X3 |
| I26 | Publications | The source's not copied; the target's change set publishes as any other | X3 |
| I27 | The target's validation | Row by row, as an import (J3): every refusal with its code and pointer, in the dry run of every item (D67) | X2 |
| I28 | Volume | Set statements in PostgreSQL in a background job; the dry run of every item; measured once at full volume in X5 | X2, X5 |
| I29 | The target's consumers | Nothing until the change set publishes; then the ordinary events of the target's consumer APIs (D20) | X3 |
| I30 | The source changes during the move | The move reads the source at one point (a publication or the live state at its start, recorded); a later change is the next move's | X3 |
| I31 | The mapping changes after a dry run | The load refuses a dry run of an older mapping version, as an import refuses an older profile | X3 |
| I32 | The target's model changes meanwhile | The change set is pinned to the target's release; publishing after a change is D26's rule | X3 |
| I33 | Who may move | Until 0.12, the gates (D14); 0.12's authorization adds the source's read right and the target's write right | X3 |
| I34 | Same model on both sides | The mapping proposed as identity; the move is the same machinery | X1 |

**Composable domains (ADR-032):** P0 changes only documents. D23 touches identity (an origin beside
the computed counterpart ID): the retired-ID redirect door stays open, as an origin is a lookup
beside the ID, not a change of it.

##### P0 record (2026-10-15)

**Delivered 2026-10-15.** The user approved the M5 and X4 mock-ups the same day ("screenshots
approved"), without changes; their shapes are the ones M5 and X4 build on.

- **Decisions:** D4–D11 and D13–D29 accepted as recommended, with the move inventory I1–I34
  ("okay", 2026-10-15); recorded in the decisions table. Package scopes amended: M1 (D4's removal of
  `model_runtime_state`, D24, D29, the call sites), M2 (the routes replacing the runtime state and
  activation, D26, D28), M3 (D10's two consumer routes, D25, D27), X3 (D23's origins), Track X
  scoped by the inventory.
- **ADR-042**, each workspace runs its own model release; ADR-021's closing paragraph marked
  superseded; "tenant" replaced in ADR-021 and TODO (D22).
- **API design:** [API.md § Workspace models](API.md#workspace-models-product-011): a
  workspace's model and its activation, resolution and the commit guard per workspace, what follows
  the workspace's model, spanning reads, the migration preview and confirmation, model mappings and
  moves, with their codes. **Where it goes beyond the plan:** `GET /model-runtime-state` and
  `POST /model-releases/{id}/activation` are removed by M2 rather than kept beside the new routes
  (pre-1.0, one way to do one thing); an assignment has a version of its own, claimed by activation;
  a migration's confirmation binds the workspace's feed position; the move's preview distinguishes
  `update` (found by counterpart) from `updateOriginal` (found by origin).
- **Journeys:** J36 (8 variants), J37 (8), J38 (8) in USER_JOURNEYS under a new "Workspace models"
  group; their planned routes and codes in API_JOURNEYS; MODEL_AUTHORING amended for D15 and D25.
- **Mock-ups:** [workspace models and move editor canvas](https://claude.ai/artifact/EiSQmSGwdGjCf2y21Cv4L9), seven boards in an invented
  library and archive domain: the shell switching between workspaces on two models and two releases
  (clickable: the workspace menu marks another model or release, a notice says what changed, a
  collection the other model lacks opens the "not in this workspace's model" page); Settings › Model
  per workspace with installed releases by model and the activation dialog (compatibility for that
  workspace only, change sets left behind, a migration offered when the release does not fit);
  Settings › Workspaces with a workspace created on a model and "New from a workbook" activating
  into a new or chosen workspace (D15); the 390px shell with the workspace sheet and Settings › Model;
  the move editor (source and target models, the mapping with Proposed steps edited in place, the
  reason and alternatives of a step, the dry-run figures recomputed after each step, undo and redo,
  copy or move); what cannot move by reason with every item, the start dialog for copy and move,
  and the refusal when the mapping changed after the dry run; the 390px move editor as tabs. Each
  board has a dark tweak. Built on the Atlas tokens, without the account's design system. Private
  until shared.

**Checks:** `pytest tests/test_api_journeys.py` (below). Links checked for the anchors added. **Not
done:** the mock-ups were not opened in a browser at 1440px and 390px in light and dark before they
were shown, since no browser tool was used in this session; the user then looked at them and
approved them.

## Part 1 — Workspace models

### Track M: each workspace a model of its own

#### M1: A release assignment per workspace

**Design:** ADR-042, D4–D6, D24, D29; [API.md § Workspace models](API.md#workspace-models-product-011). **Needs:** P0.

**Scope:**

- Migration: `workspaces.model_release_id` (not null) and its assignment version, filled from
  `model_runtime_state` for every existing workspace; `model_runtime_state` and
  `model_releases.is_active` dropped (D4, D24); a new workspace starts on the default workspace's
  release. Bootstrap and the schema-upgrade CLI assign the workspace instead.
- Every call site P0 lists for M1 ([the call sites](#p0-plan-2026-10-15)); a workspace whose release
  cannot be loaded at startup is unavailable alone (D29).
- `resolve_model_snapshot(session, workspace)` at every call site in P0's list: the request
  resolves its workspace (default as today), then that workspace's release through the registry,
  which already resolves releases by ID. The registry's cache holds one snapshot per release.
- The commit guard per workspace: a write checks its workspace's assignment under a share lock on
  that workspace's row; `MODEL_RELEASE_CHANGED` names the workspace.
- `GET /model` and the metadata routes resolve the named workspace's model (D6); `X-Model-Release-Id`
  and the ETag follow it. A read of any installed release's model by ID stays available.
- No UI and no change in behaviour while every workspace names the same release.

**Tests:** two workspaces on two releases of one model and on two different models (`generated-a`,
`generated-b`): reads and writes in each resolve their own; a write refused after its workspace's
release changed, while a write in the other workspace commits; the migration from 0.10.0 assigning
every workspace the active release.

**Groups:** `workspace_models` (new), `model`, `records`, `contract`, `startup`.

**Exit:** no request resolves "the" active release; the 0.10 behaviour unchanged with one model.

##### M1 plan (2026-10-15)

**Planned 2026-10-15; accepted by the user the same day: D30, D31, D33, D34 and the test cases.
D32 rejected** ("we don't develop just to bridge M1 to M2 then remove the development"): **M2 is
folded into M1** instead, so the 0.10 routes are replaced, not bridged; the cases below include
M2's. Checked against the code at `71b15ea`.

**What the check found beyond P0's list:**

- **The workspace row cannot carry the guard's lock.** Live writes take the workspace row
  `FOR NO KEY UPDATE` (`LiveWrites._begin`, then `take_positions` updates it), publishing takes it
  `FOR NO KEY UPDATE` and withdrawal `FOR UPDATE`, change-set writes `FOR KEY SHARE`. A guard's
  `FOR SHARE` on that row conflicts with `NO KEY UPDATE`: every change-set write would queue behind
  the workspace's live writes and its publication, which today run beside each other (PG-D5). D30.
- **A fresh database's default workspace exists before any release.** The baseline migration
  creates it and `workspace_runtime_state`; bootstrap installs the release later. A not-null
  `workspaces.model_release_id` has nothing to hold at that point. D30.
- **M1's tests need two models side by side through the API**, and only M2 would let a client put a
  workspace on another model. D31.
- **Once two models can run side by side, M2's and M3's readers act on the wrong model.** The
  unique-values triggers would check model B's records against model A's unique attributes; matrix
  states would keep A's shapes for B's live data; activation would count B's records in A's
  compatibility check and suspend B's subscriptions by A's definitions; the consumer routes, the
  event dispatcher and the jobs would read A for B's data. D32, D33.
- `analyze_compatibility` already has the hook a workspace filter needs (`_is_in_active_workspace`,
  `literal(True)` today, used at every count).
- Live writes on an existing record (update, delete, attribute value, relation) resolve the model
  before they know the record; per workspace they read the record's workspace first (one indexed
  read of `objects.workspace_key`), then its model. Not a decision; listed so it is not missed.

**Decisions** (D30 onward; each with what, why and cost):

| # | Question | Recommendation |
| --- | --- | --- |
| D30 | Where a workspace's assignment lives | **A table of its own, `workspace_models`** (`workspace_key` primary key and foreign key to `workspaces`, cascading on delete; `model_release_id`, restricted; `version`; `updated_at`), not columns on `workspaces`. Why: the commit guard's share lock and activation's update lock then sit on a row nothing else locks, so today's lock behaviour holds per workspace exactly as it holds for the singleton; a workspace without a row is only possible between the baseline migration and bootstrap, which fills it. Cost: one join when a request resolves its model. The API is unchanged: workspace responses still carry `model`, and its `version` is this row's |
| D31 | Creating a workspace on a named release | **Moved from M2 into M1:** `POST /workspaces` takes the optional `modelReleaseId` (any installed release of a supported schema; `404 MODEL_RELEASE_NOT_FOUND`, `422 UNSUPPORTED_SCHEMA_VERSION`). Why: M1's tests must build two workspaces on two models through the public API; without it only a hand-made database state could, which the test rules forbid. Cost: one optional field. A new workspace is empty, so it needs no compatibility check. M2 keeps activation into an existing workspace |
| D32 | What the 0.10 activation route does until M2 removes it | **Rejected by the user (2026-10-15):** no code is built only to bridge two packages. M2 is folded into M1: `POST /workspaces/{workspaceKey}/model/activation` and `GET /workspace-models` replace `POST /model-releases/{id}/activation` and `GET /model-runtime-state` in M1, with activation into one workspace (its own compatibility check, contract check, subscription suspension and matrix states) and the change sets it leaves behind (D26). The browser's Settings › Model calls the new routes for the default workspace, which is what it manages today; M5 adds the choice of workspace |
| D33 | M2's and M3's readers that already know their workspace | **Changed in M1 to use it**, since D31 makes two models possible: the unique-values triggers read each written record's workspace release, and the refill trigger moves to `workspace_models`, refilling only that workspace's rows (D28, done here); matrix states keep the workspace's live shapes; the feed records the workspace's release; the consumer read routes, the event dispatcher and worker, subscription create and change, and jobs and batches resolve their workspace's model; activation's check and suspension per D32. **Left to M3**, resolving the default workspace's model as their meaning is today: import profiles (D9), drafts without a base (D25), source profiling, checks, dry runs and inference started without a workspace, the consumer index and OpenAPI (D10, D27) and the API reference page. Why: each changed reader would otherwise act on the wrong model's rules; the ones left are those whose meaning M3 decides. Cost: M1 grows by these readers, M2 shrinks by D28 |
| D34 | A workspace whose release cannot be loaded (D29), in detail | **Only that workspace answers `503 MODEL_REGISTRY_UNAVAILABLE`** with `details.workspaceKey`, `releaseId` and, for an unsupported schema, `schemaVersion` (the log keeps 0.10's upgrade instructions). `/health` answers 503 only when the database is unreachable or no workspace can be served, so one workspace on one model behaves as in 0.10. The job worker, listener, event deriver and dispatcher start when at least one workspace can be served; a job or subscription of an unavailable workspace fails with that code instead of running. Why: "without touching the others" (D29). Cost: the registry keeps a set of unloadable releases instead of one flag; readiness listing them is O1's |

**What is built:**

1. **Migration `20261018_01_workspace_models`:** the table (D30), one row per existing workspace
   from `model_runtime_state` (version 1); `model_runtime_state` and its trigger dropped,
   `model_releases.is_active` and its index dropped (D24); the unique-values functions rewritten to
   read the record's workspace release, the refill trigger on `workspace_models` (D33). Downgrade
   restores the singleton from the default workspace's row. `ChangeSetBase.model_runtime_version`
   keeps its column and now holds the assignment version.
2. **Bootstrap and the schema-upgrade CLI:** bootstrap gives every workspace without a row the
   bootstrap release; the 0.6-era `is_active` path goes; the CLI's transition assigns every
   workspace running the selected 0.4 release.
3. **Registry:** `resolve_model_snapshot(session, workspace_key)` resolves the workspace (default
   when `None`), then its release through the per-release cache; `session.info` records each
   workspace's resolved release, and `require_resolved_release` rechecks each under a share lock on
   its `workspace_models` row; `MODEL_RELEASE_CHANGED` gains `details.workspaceKey` and
   `currentReleaseId` (replacing `activeReleaseId`). Startup loads every assigned release (D34).
   `resolve_active`, `refresh_active` and `runtime.py` go.
4. **Every call site** of P0's M1 list, and D33's: routers through `ActiveModelSnapshot` /
   `RequestModelSnapshot` (now resolving `workspaceKey`; an unknown one is
   `404 WORKSPACE_NOT_FOUND`), the change-set base capture and publish check against the
   workspace's release (`CHANGE_SET_MODEL_RELEASE_CONFLICT` with `details.workspaceKey`), the feed,
   the reference page, system state (the default workspace's), startup.
5. **API:** workspace responses gain `model`; `GET /workspaces/{workspaceKey}/model`;
   `POST /workspaces` `modelReleaseId` (D31); `GET /model` and the metadata routes add the
   `RDM-Workspace` header beside `X-Model-Release-Id` and the `ETag`; `GET /model-releases` replaces
   `active` with `assigned` (filter and field) and adds `workspaces` (D24). From M2:
   `POST /workspaces/{workspaceKey}/model/activation` (`releaseId`, `expectedVersion`,
   `expectedReleaseId`) activates into that workspace alone: its compatibility check counts that
   workspace's data, the contract check compares with its release, subscription suspension and the
   matrix-state resync cover it only; the answer adds `changeSetsLeftBehind` (D26); the audit entry
   names the workspace and `GET /model-releases/{id}/activations` items gain `workspaceKey`.
   `GET /workspace-models` pages the assignments (`releaseKey`, `releaseId`). `GET
   /model-runtime-state` and `POST /model-releases/{id}/activation` are removed. OpenAPI lock
   re-baselined by diffing.
6. **Frontend, no visible change:** the release type's `active` becomes `assigned` (four reads in
   Settings › Model and the create-draft dialog); `Workspace` gains `model`; Settings › Model, the
   install dialog and the load dialog read the default workspace's model and activate into it
   through the new routes (M5 adds the choice of workspace).
7. **Docs:** API.md (the M1 part moved to delivered), ARCHITECTURE (resolution and the lock),
   OPERATIONS (D34's health), USER_JOURNEYS J36 evidence, CHANGELOG, PROJECT_STATUS, TODO.

**Journey test cases** (J36, `workspace_models` marker; each runs in both directions,
`generated-a` beside `generated-b` and the reverse; names structures only):

1. **J36.1 A new workspace on another model.** Given configuration X running in the default
   workspace and Y's model installed. When a workspace is created with Y's release. Then its
   `model` names Y's release, version 1; the default workspace's still names X's;
   `GET /workspaces/{key}/model` answers the same; `GET /model-releases?assigned=true` lists both,
   each with its workspace. A workspace created without `modelReleaseId` runs X's release; an
   unknown release is `404 MODEL_RELEASE_NOT_FOUND`.
2. **J36.3/J36.6 Each workspace reads and writes by its own model.** Given the two workspaces of
   case 1. When `GET /model?workspaceKey=` is read for each, and an `R` is created, read and found
   in each. Then each answers its own model with its `X-Model-Release-Id` and `RDM-Workspace`; each
   record carries its model's keys; X's `R` type key is refused in Y's workspace with its unknown-type
   code. `GET /model` without `workspaceKey` answers the default workspace's model; an unknown
   `workspaceKey` is `404 WORKSPACE_NOT_FOUND`.
3. **Unique values follow the workspace's model.** Given the two workspaces. When two `R`s with
   one `R.u` value are created in Y's workspace. Then the second is refused with the unique-value
   code; the same value is accepted once in X's workspace.
4. **J36.5 A write when its workspace's release changed meanwhile.** Given X's release X1 in the
   default workspace, X2 installed, and a workspace on Y. When actor A's live write in the default
   workspace is resolved under X1 and waits, X2 is activated into the default workspace, and a live
   write in Y's workspace runs meanwhile. Then A is refused `409 MODEL_RELEASE_CHANGED` naming the workspace, X1 and X2,
   nothing of A is saved; the write in Y's workspace commits; Y's workspace still runs Y.
5. **J36.2 Activation into one workspace leaves the others alone.** Given two workspaces on X1,
   the second holding records of a type X2 drops and a subscription X2 cannot serve, and a
   workspace on Y. When X2 is activated into the first. Then it is not refused for the second's
   records; the first runs X2 at version 2, the second X1 and Y's workspace Y, each at its version;
   only the first's subscriptions are suspended; activating X2 into the second is
   `409 MODEL_MIGRATION_REQUIRED` counting its records only; a stale `expectedVersion` is
   `409 ACTIVATION_CONFLICT` with `details.workspaceKey`; `GET /workspace-models?releaseKey=` lists
   the assignments of X.
6. **A change set publishes under its workspace's release.** Given the two workspaces. When a
   change set is created, edited and published in Y's workspace. Then it is pinned to Y's release
   and publishes; a change set of the default workspace pinned to X1 is listed in the activation's
   `changeSetsLeftBehind` when X2 is activated there, and its publish is refused
   `409 CHANGE_SET_MODEL_RELEASE_CONFLICT` with `details.workspaceKey`.
7. **J36.8 One workspace's release cannot be loaded** (the state arrives from outside the API: an
   older database whose release this version cannot read). Given a workspace on such a release.
   When the engine starts. Then that workspace's reads answer `503 MODEL_REGISTRY_UNAVAILABLE`
   naming it; the default workspace serves; `/health` is 200.

**Startup and migration** (the `startup` group, older-style module): upgrade of a 0.10.0 database
holding two workspaces (every workspace assigned the active release, unique values kept, the
singleton and the flag gone), clean bootstrap, restart, an interrupted migration resumed, the
lifespan against a real temporary database, and a smoke start on a copy of the development
database. **Unit:** the registry's resolution with one unloadable release among several.

**Groups:** `workspace_models` (new), `model`, `records`, `matrix`, `events`, `contract`,
`startup`; the frontend's
Settings › Model and create-draft tests, format, lint and build. No full suite (R).

**Composable domains (ADR-032):** no door is affected; unique values stay keyed by workspace, and
identity and attribute storage are unchanged.

##### M1 record (2026-10-15)

**Delivered 2026-10-15** (commit `a55d634`, and the test fixes after the group run). Built as
planned, M2 included:

- **Migration `20261018_01`:** `workspace_models` (D30), one row per workspace from the singleton at
  version 1; `model_runtime_state`, its trigger and `model_releases.is_active` dropped; the
  unique-values triggers read the record's workspace release and the refill trigger is on
  `workspace_models`, per workspace (D28). The downgrade restores the singleton from the default
  workspace (a workspace on another model then has no representation; values another model made
  unique lose their rows).
- **Registry:** `resolve_model_snapshot(session, workspace_key)` (the default workspace for `None`),
  `resolve_record_snapshot` and `resolve_relation_snapshot` for writes naming a record; the commit
  guard per resolved workspace; unloadable releases per release (`start`, `withdraw`, D34);
  `engine/model/runtime.py` removed; `engine/model/workspace_models.py` (assignment reads, a new
  workspace's assignment).
- **Activation into one workspace** (`releases.activate_model_release`), its route, `GET
  /workspaces/{key}/model`, `GET /workspace-models`, `modelReleaseId` on `POST /workspaces`; the two
  0.10 routes removed; compatibility scoped by workspace (`analyze_compatibility(…, workspace_keys)`).
- **D33's readers:** unique values, matrix states, the feed, consumer reads, the event dispatcher,
  subscriptions, jobs, batches and the source jobs resolve their workspace's model. Import profiles,
  drafts, the consumer index and OpenAPI and the reference page resolve the default workspace's,
  for M3.
- **Frontend:** the release type's `assigned` and `workspaces`, `Workspace.model`,
  `api.workspaceModel`, `api.defaultWorkspaceModel`, `api.activateWorkspaceModel`. Settings › Model,
  the install dialog and the create-draft dialog work on the default workspace; the change-set
  dialog and the workspace data context compare with the workspace's own release; Load into a change
  set activates into the workspace it loads into. No visible change with one model.
- **Docs:** API.md (the delivered contract and § Workspace models), ARCHITECTURE, OPERATIONS,
  CURRENT_FUNCTIONALITY, USER_JOURNEYS J36, API_JOURNEYS, EXECUTION_GUIDE (the `workspace_models`
  group), CHANGELOG, PROJECT_STATUS, TODO.

**Where it differs from the plan:** `RDM-Workspace` is set on `GET /model` only, not on the metadata
routes (they answer no model headers today). Creating a workspace on a release is gated by workspace
administration, not model administration (it changes no existing workspace's model). The audit
aggregate of an activation is `workspace_model`; the activation history still reads 0.10's
`model_runtime_state` entries, without a workspace.

**Older tests changed because M1 made them wrong** (no case's intent changed): the harness's
`world.activate` (into a named workspace) and a new `world.activate_everywhere` (what one activation
did before 0.11, used by J34, which loads into workspaces of its own); J08, J12.6 (one schema-upgrade
entry per workspace now), J21's route list and the runtime-state reads of eleven journey files; the
older modules `test_model_lifecycle`, `test_w5_activation_write_race` and `test_pg3_concurrency`
(activation into the workspace the race writes in; the lock patterns on `workspace_models`),
`test_model_schema_upgrade`, `test_startup` (`HEAD`), `test_foreign_keys`, `test_matrix_states`,
`test_wp81a_context`, `test_wp81b_current_live_bases`, the unique-values unit test, the volume
fixture (its workspace's assignment row, inserted before its values) and baseline; twelve browser
runners' API calls (syntax-checked only); Vitest fixtures.

**Checks so far:**

- J36 (`test_j36_workspace_models.py`): 7 cases × 2 directions written first and seen failing (14
  failed: routes and fields absent), then 14 passed (28.8 s).
- `test_startup`: the new upgrade case (a 0.10.0 database with two workspaces and unique values, an
  interrupted run rolled back and refused naming the table, two starts, assignments at version 1,
  unique rows kept, singleton and flag gone, a downgrade) with the two neighbouring migration cases:
  3 passed. **Smoke start** on a copy of the development database (`rdm`, at `20261016_01`, 2
  workspaces, 2,380 records): migrated to `20261018_01`, both workspaces on the release that was
  active at version 1, `/health` and `/system` 200, unique-value rows 15 before and after; the copy
  dropped and the development server stopped again.
- Journeys J07, J08, J12, J18, J20, J21, J25, J27, J31, J33, J34 in one parallel run (4 min 31 s,
  load 6, **over the ceiling and not announced first**): 3 failures, both caused by the change (J12.6
  counting one entry per workspace; J34 loading into workspaces activation no longer moves), fixed,
  then J12.6 (2 passed) and J34 alone (112 passed, 5 min 3 s, **also not announced first**).
- `contract` group: 38 passed; `test_boundaries::test_tiers_hold` fails, at `71b15ea` too (TODO).
  OpenAPI lock re-baselined after diffing the default document against `71b15ea`: two routes added,
  one removed, the schemas named in the lock's comment changed, nothing else.
- Ruff on `app/` and `tests/`: clean. Frontend: `tsc`, `npm run lint` (0 errors, the 7 listed
  warnings), `npm run format`, `npm run build` passed; Vitest on the 13 changed files, 130 passed.

- **The groups the execution guide selects** (`workspace_models`, `model`, `model_admin`, `records`,
  `matrix`, `workspaces`, `change_sets`, `mapping`, `feed`, `consumer`, `jobs`, `startup`, which
  include `test_pg3_concurrency` and `test_w5_activation_write_race`), on the user's go-ahead, load
  3.6: 5,435 passed and 34 failed in 6 min 52 s. All 34 were older tests M1 made wrong: compatibility
  calls without their workspaces (18), the race helper without its workspace (1), the removed
  `active` filter (1), the startup log call read by argument position (5), activations into the
  default workspace followed by work in another (J30, the SC15 acceptance: 7), and incompatible data
  in another workspace expected to block the default's activation (2). Fixed, the second of the last
  rewritten with the user's approval: a retired workspace keeps its release and an activation into it
  is refused `WORKSPACE_RETIRED` (ADR-042 replaces "retired data blocks activation"). Rerun: the 8
  files, 99 passed (37 s); the other importers of the changed J30 helper, 60 passed (1 min 22 s); the
  serial part of the groups, 3 passed (9 s).

**Not run:** the full suites, `queries`, `authoring` and `volume` (no change there), the browser
runners (no visible change), all at R. **What the
user cannot do yet:** choose a workspace in Settings › Model or the shell (M5), import profiles and
drafts per workspace model (M3), spanning reads across models (M4).

#### M2: Installing and activating into one workspace

**Folded into M1 (the user, 2026-10-15, D32).** Its scope below is delivered with M1.

**Design:** D4, D5, D14, D26, D28. **Needs:** M1.

**Scope:**

- Activation targets one workspace: the compatibility analysis runs on that workspace's data only;
  the workspace's assignment row is locked instead of the singleton; the audit event names the
  workspace. Installing stays instance-wide (releases are immutable and shared).
- What activation touches is scoped to the workspace: `unique_attribute_values` and its trigger
  follow each workspace's release; matrix cell states rebuild for that workspace; consumer
  subscriptions suspended by a contract change are that workspace's only.
- A workspace is created on a named release (default per D4); deleting an unused workspace (0.8 W6)
  is unchanged.
- `GET /workspace-models` and `POST /workspaces/{key}/model/activation` replace
  `GET /model-runtime-state` and `POST /model-releases/{id}/activation`; activation lists the
  workspace's change sets left behind on the old release (D26).

**Tests:** activation into one workspace with the other's data incompatible with the new release
(allowed: only the target's data is checked); unique values held in one workspace under one model
and the same values in another; a contract change suspending only the target workspace's
subscriptions; a new workspace on a model no other workspace runs.

**Groups:** `workspace_models`, `model`, `matrix`, `events`, `startup`, `contract`.

**Exit:** two workspaces of one instance run two different models, each activated without touching
the other.

#### M3: Instance-wide resources bound to a workspace's model

**Design:** D9, D10, D15, D25, D27. **Needs:** M2.

**Scope:**

- Import profiles: bound to a model (its release key) instead of "the active release" (D65 amended,
  D9); checked against the target workspace's release when used; a profile naming another model's
  types refused at its pointer.
- Jobs and dry runs (`dry_run_context`, `open_job_context`) resolve the job's workspace; profiling
  and inference against a draft are unchanged (the draft's own model).
- Drafts: a draft's base release names its model; installing and activating from the editor asks
  for the target workspace(s); "New from a workbook" with a new model activates into a chosen or new
  workspace, never into all (D15; MODEL_AUTHORING amended).
- Consumer APIs: definitions come from the requested workspace's release; the API index, the
  OpenAPI per definition (both gaining `workspace`), the event deriver, the dispatcher and webhooks
  resolve per workspace (D10, D27).
- Draft compile reports compatibility for each workspace running the base's model (D25).

**Tests:** an import into each of two workspaces with a profile per model; a profile of one model
used on the other's workspace refused; a consumer API served from two workspaces with two
contracts; an event derived under each workspace's model; "New from a workbook" into a new
workspace leaving the existing workspaces' model as it was.

**Groups:** `workspace_models`, `jobs`, `authoring`, `consumer`, `events`, `contract`.

**Exit:** nothing instance-wide assumes one model.

#### M4: Reads spanning workspaces

**Design:** D7, D8. **Needs:** M3.

**Scope:** each read that spans workspaces is defined when their models differ (D7): the cross-type
lookup (`GET /objects`), the change feed, mapping coverage, exports, imports naming another
workspace's records (0.9 J5's counterparts between different models: refused with a pointer to the
move, or allowed where the profile maps them, per D7). Relationships stay within one workspace (D8).

**Tests:** each read over two workspaces on two models, with the per-workspace model named in every
item; a filter naming a type only one model has.

**Groups:** `workspace_models`, `queries`, `feed`, `jobs`, `contract`.

**Exit:** no read combines two snapshots; each spanning read's meaning documented in API.md.

#### M5: The UI follows the workspace's model

**Design:** the M5 mock-up approved in P0. **Needs:** M4.

**Scope:**

- The shell reloads the model, applications and navigation when the workspace changes, from
  `GET /model?workspaceKey=…`; bookmarks to a collection the other model lacks show a plain "not in
  this workspace's model" page.
- Settings › Model shows each workspace with its model and release; activation chooses the
  workspace; the workspace administration screen creates a workspace on a model.
- The editor opened on a workspace's model; install and activate into the workspaces chosen.

**Tests:** browser (`test:browser:workspace-m5`): two workspaces on two models, switching between
them, Settings › Model, activation into one, keyboard alone, 1440px and 390px.

**Groups:** frontend unit tests, `test:browser:workspace-m5`, the accessibility check on the new
screens.

**Exit:** screenshots approved.

#### M6: Workspace models checkpoint

**Needs:** M5.

**Scope:** J36 composed in the browser over the real backend on `generated-a` and `generated-b` in
two workspaces; the roadmap's exit item "two workspaces of one instance run two different models side
by side, each installed, activated and migrated on its own, with no request combining their
snapshots" (its "migrated" part completed by V1). Released as 0.11.0-alpha.1 when it passes, tagged
`v0.11.0-alpha.1` on the user's instruction (D12).

**Exit:** the checkpoint passes, or each failure is explained and tracked.

### Track V: a workspace moved to another release

#### V1: A workspace's data migrated to another release

**Design:** the roadmap's "executable workspace-scoped data migration plans"; ADR-034. **Needs:**
M2.

**Scope:** for one workspace and a target installed release (of its model or another): a preview of
every conversion and every potential loss, item by item, from the compatibility analysis; the
conversions executed in PostgreSQL in a background job (type changes as ADR-034's, value
conversions through the attribute registry); confirmation bound to the reviewed workspace, release
and data versions; the data and the assignment switched atomically. Cancel, a stale review and a
failed execution change nothing. Immutable history is preserved; other workspaces are untouched.

**Tests:** J37's preview, confirm, cancel, stale and failure variants on two models; a migration
whose loss the user confirmed; at volume once.

**Groups:** `migration` (new), `workspace_models`, `jobs`, `change_sets`, `startup`.

**Exit:** the roadmap's exit item on confirmed historical migration.

#### V2: A change set from a publication moved to another release

**Design:** GAP-02, the roadmap item. **Needs:** V1.

**Scope:** a change set started from a publication, targeted at a named installed release (normally
the historical pin), with V1's preview of incompatibilities and loss, confirmation bound to the
exact reviewed versions, and atomic model and data application for that workspace only.

**Groups:** `migration`, `change_sets`.

#### V3: A change set moved onto a release it does not fit

**Design:** ADR-028, the roadmap item. **Needs:** V1.

**Scope:** V1's machinery against the change set's own candidate graph and current live base:
conversions and loss of change-set content previewed; applied only on confirmation of the exact
change set and release versions; never forced, never deleting change-set content to make it fit. A
change set left on a replaced release is moved or thrown away explicitly.

**Groups:** `migration`, `change_sets`.

**Exit:** the roadmap's two exit items on moving a draft.

#### V4: The schema-language window

**Design:** D11. **Needs:** V1, M6.

**Scope:** the schema-language versions workspaces may run side by side (D11), every pinned parser
served concurrently; the conversion rules between them written down; a release outside the window
refused at installation with its version and the window. The list and the dates are published by
L2.

**Groups:** `model`, `migration`, `startup`.

### Track X: data moved between workspaces whose models differ

The packages below are scoped by the move inventory accepted in P0 (I1–I34, in the
[P0 plan](#p0-plan-2026-10-15)); each case names its package.

#### X1: The mapping between two models

**Design:** D16, D18. **Needs:** M4 and P0's inventory.

**Scope:** a saved mapping from a source workspace's model to a target workspace's model: which type,
attribute, relation and parent of the source becomes what in the target. Proposed by A6/A7's
inference turned to a source model (keys, names, values, stored records, with evidence and
alternatives), placed in the mapping as editable steps marked Proposed, and completed or corrected
with A5's mapping operations, with undo. Saved and reused for the next move between the same
models; drift between the models reported.

**Groups:** `move` (new), `authoring`, `contract`.

#### X2: Selection and the dry run of a move

**Needs:** X1.

**Scope:** what moves: a whole workspace, chosen types, a subtree, a filtered set, a selection (K1).
The dry run of every item (D67) as a background job in PostgreSQL: each item's outcome in the
target with its reasons, as an import's row outcomes (J3): what cannot move (no mapping, value not
convertible, unique value held, required value missing, parent missing, relationship's other end
left behind) with what to do about it.

**Groups:** `move`, `jobs`, `volume`.

#### X3: The move

**Design:** D16, D17, D23; the move inventory I1–I34. **Needs:** X2.

**Scope:** the move into a reviewed change set of the target workspace: identity as counterparts
(found again on a second move, D16), each moved record's origin stored in a table of its own so a
record moved back finds its original (D23); copy by default, move as a copy plus the source's deletion in
a change set of the source workspace (D17); relationships, hierarchy, values, lookups, translations
and effective periods as the inventory decides; the target's audit naming the move and its source;
the target's subscribers receiving events on publication as for any change set.

**Groups:** `move`, `jobs`, `change_sets`, `events`.

#### X4: The move editor

**Design:** the X4 mock-up approved in P0. **Needs:** X3, M5.

**Scope:** source and target models side by side, the mapping with its proposals as editable steps,
the selection, the dry-run figures after every step, the report of what cannot move, and the start
of the move into a change set opened for review.

**Tests:** browser (`test:browser:workspace-x4`): J38 on `generated-a` → `generated-b`, keyboard alone,
1440px and 390px.

**Exit:** screenshots approved; one smoke on a real sample including a dialog on an invalid mapping.

#### X5: Move checkpoint

**Needs:** X4.

**Scope:** the roadmap's exit item "records of one workspace move into a workspace of a different,
partly compatible model through a proposed and hand-completed model-to-model mapping, dry run and
reviewed change set, with what could not move reported", composed in the browser; the move at full
volume, measured once, announced as a heavy run.

## Part 2 — Production hardening

#### S1: The backend suite's time

**Design:** D152 (0.10 R), D2. **Needs:** —. **When:** a filler while a Part 1 package waits for
screenshot approval, delivered before X2 at the latest (D2).

**Scope:** the backend suite under its 5-minute ceiling. Measured at 0.10 R: 8 min 31 s (5,771
cases); the `jobs` group alone near 6 minutes; J34 and J35 build a draft and profile W1 in every
case. Approach recorded in TODO since A6a: profile W1 once per configuration in a session fixture for
the cases that only read it, and split J34 so its cases spread over the workers. Why it matters
beyond the ceiling: R's runs made the user's laptop unusable for hours; every later package and R
gets cheaper when the suite does.

**Exit:** the suite measured once under the ceiling on the user's go-ahead.

#### N1: Snapshots across processes

**Needs:** M2.

**Scope:** an assignment change in one process is seen by every other before it serves the
workspace again (the assignment's version read at resolution, or `LISTEN/NOTIFY`, decided in its
plan); the in-process installation lock replaced by a database lock; `MODEL_ADMIN_MUTATIONS_ENABLED`
no longer requires `WEB_CONCURRENCY=1`.

**Groups:** `workspace_models`, `model`, `startup`.

#### N2: The job worker on several nodes

**Needs:** N1.

**Scope:** every job kind's long phases renew their lease, cancel and supersede under real
concurrency with several worker processes. R found the profile job holding its file `FOR UPDATE`
(R-F5), inference and the profile's statistics not renewing their lease (R-F6, R-F7) and concurrent
uploads not superseding each other (R-F9); all fixed in R, and the whole worker is now checked the
same way.

**Groups:** `jobs`.

#### N3: Concurrency invariants at full volume

**Needs:** N2, Q1.

**Scope:** the roadmap's first exit item: concurrency and uniqueness invariants with several
processes and nodes on one database, in production-like tests at full volume. Database constraints
as a second line behind the per-workspace write lock, only where the evidence shows a write path
that bypasses the write unit.

#### Q1: Full-volume fixture, pool and bulk paths

**Scope:** the volume fixture at full scale; connection pool sizing; every bulk path (imports at full
volume, change-set captures, exports, migrations, moves) checked for the R-F19 pattern (fresh rows
joined before PostgreSQL's statistics see them); the two `NOT IN` subqueries in TODO since 0.9 R
measured at full volume; matrix-state cost per commit (TODO) measured once. Each measurement once,
announced, with cause and options reported before any fix.

#### Q2: Model-derived indexes

**Needs:** M2, Q1.

**Scope:** indexes derived from each workspace's model, including unique checks on non-text values
(the value indexes cover `text_value` only). Composable domains: whether a later derived value can
be indexed and sorted is decided here (the derived-values door).

#### Q3: Precomputed sort keys

**Needs:** Q2. Below the cut line.

**Scope:** attribute and ancestor sorts over very large parents within the list budget (0.8 D26).

#### O1: Metrics, logs, health and readiness

**Needs:** N1.

**Scope:** metrics, structured logging, health and readiness endpoints, documented in OPERATIONS;
readiness reports each workspace's model resolved.

#### O2: Backup, restore and the Operations page

**Needs:** O1, M6.

**Scope:** backup and restore rehearsed with `pg_dump` on an instance whose workspaces run different
models, without mixed-model requests; Settings › Operations (U7, approved 2026-10-05). Historical
change sets are not direct dataset restore operations (exit gate).

**Exit:** screenshots approved; the rehearsal recorded in OPERATIONS.

#### U1: Touch drag in the tree lens

Below the cut line.

**Scope:** long-press drag that does not conflict with scrolling or with opening a record, confirmed
in the same move dialog as with a mouse (0.8 D35), tested on iOS Safari and Android Chrome
emulation.

## Part 3 — First public release

#### L1: Licensing and policies

**Scope:** the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md); contribution
and security policies.

#### L2: The compatibility commitment

**Needs:** V4.

**Scope:** the compatibility commitment for the public contracts; the supported schema versions and
their migration and removal dates published; the [composable domains doors](COMPOSABLE_DOMAINS.md#doors-to-keep-open)
checked against it (a retired-ID redirect, a value source, derived read-only values and a new value
type each addable without a breaking change).

## R: Build acceptance and release

- A full review of every change since 0.10.0 first, as every R.
- J36–J38 composed in the browser over the real backend on two models, keyboard alone, 1440px and
  390px, with the accessibility and visual gates.
- The roadmap 0.11 exit gate, item by item.
- Migrations: clean bootstrap, upgrade from 0.10.0 (every workspace assigned the active release).
- Full suites per AGENTS.md; documents and versions; tag on the user's instruction.
- Every heavy run as an announced block (above).

**Exit:** all gates pass, or each failure is explained and tracked; Base 0.11.0 is ready to release.

## Composable domains check (ADR-032)

- **Identity:** moves reuse J5's counterparts (`sourceId`); a retired-ID redirect stays addable.
  Checked in X3.
- **Attribute storage:** unchanged; model-derived indexes (Q2) decide the derived-values door.
- **Audit and history:** a move's audit entries name their source; history stays immutable; V1
  preserves it. No door closed.
- **Bulk APIs:** migrations and moves are jobs with item outcomes, as 0.9's bulk writes.
- **The consumer API `match` declaration:** unchanged; definitions resolve per workspace (M3).
- **Mapping coverage:** defined across workspaces with different models in M4.
- **The compatibility commitment** (L2) covers the contracts the doors extend.

## Invariant notes

- **The versioned JSON model is the declarative source.** Still: one per workspace, each an
  immutable release. Releases stay instance-wide and immutable; only their assignment is per
  workspace.
- **Not multi-tenancy.** One instance per organisation; workspaces of one organisation run
  different models.
- **Optimistic concurrency.** An assignment change is versioned; a write validated under a release
  its workspace no longer runs is refused, never applied.
- **Stable public IDs.** Record IDs stay unique across the instance; a moved record gets its own ID
  in the target (its counterpart) and its origin is recorded beside it (D23).
- **Workspace groups** (unscheduled) remain possible: release identities stay instance-wide in 0.11,
  and nothing here prevents a group owning a model history later.
- **D152's order** (the suite first) conflicts with the user's request that 0.11 start with the
  workspace models. The user's request is the later one; D2 (accepted 2026-10-15) makes S1 a filler
  during Part 1, before X2 at the latest.

## Decisions

D1 is the user's; D2, D3 and D12 were accepted by the user on 2026-10-15; the others were accepted
as recommended with the [P0 plan](#p0-plan-2026-10-15) on 2026-10-15, where D4, D10, D11, D16 and
D22 are restated after the code check and D23–D29 are added.

| # | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| D1 | Order of the parts | **The user's (2026-10-15):** the workspace-model topic grouped and first (Part 1) | All |
| D2 | Where the suite's time (S1) goes, since D152 placed it first | **Accepted 2026-10-15:** as a filler while a Part 1 package waits for screenshot approval, at the latest before X2, whose packages run the slow `jobs` group. Cost: M1–M5 run their targeted groups on today's slow `jobs` group where they touch it | S1 |
| D3 | The data move in 0.11 | **Accepted 2026-10-15:** in 0.11, beside the per-workspace models it needs, as Track X | X1–X5 |
| D4 | What a workspace without "its own" model follows | **Recommended:** none. Every workspace names its release explicitly; the instance's default release is only the one a new workspace starts on, and moving the default never moves an existing workspace. Any "follow the default" would activate into workspaces that did not ask, against "without touching the others" | M1, M2 |
| D5 | What "a model" is | **Recommended:** the line of releases with one `release.key`; different keys are different models; releases stay instance-wide and immutable. Keeps workspace groups possible later | M1 |
| D6 | Routes that name no workspace (`GET /model`, the metadata routes) | **Recommended:** the default workspace's model, as data routes already resolve the default workspace; `workspaceKey` selects another. Any installed release's model also readable by release ID | M1 |
| D7 | Reads spanning workspaces whose models differ | **Recommended:** each workspace resolved with its own snapshot; every item names its workspace and release; a filter or sort naming a model element is refused unless every workspace read holds it, with the workspaces that lack it named. Counterpart imports between different models go through the move (X), not J5 | M4 |
| D8 | Relationships between records of different workspaces | **Recommended:** none, as today (imports refuse another workspace's IDs unless they load as counterparts). Data in different models meets only through a move | M4, X3 |
| D9 | Import profiles | **Recommended:** bound to a model (release key), checked against the target workspace's release when used; D65's "instance-wide, the active release" amended | M3 |
| D10 | Consumer APIs | **Recommended:** per workspace: definitions, the API index, the OpenAPI per definition, events and webhooks resolve the workspace's release; a consumer API key may mean different contracts in two models | M3 |
| D11 | Which schema-language versions run side by side | **Recommended:** the versions the compiler accepts today, if P0 confirms they compile to one internal model (then serving them side by side costs nothing extra); the published window and removal dates in L2. Otherwise the current and previous version, as ADR-021 foresaw | V4, L2 |
| D12 | An interim release after M6 | **Accepted 2026-10-15:** 0.11.0-alpha.1 when M6 passes, as 0.10.0-alpha.1 after T1; the tag on the user's instruction | M6 |
| D13 | Cut line | **Recommended:** Q3 and U1 may move to 0.11.x. Never Part 1 (the user's requirements) | R |
| D14 | Gates | **Recommended:** assignment and activation under `MODEL_ADMIN_MUTATIONS_ENABLED`; migrations and moves also under `INTEGRATION_JOBS_ENABLED`; authorization in 0.12 | M2, V1, X3 |
| D15 | "New from a workbook" with a new model | **Recommended:** installed and activated into a workspace the user chooses or creates in the same step; never into every workspace | M3, M5 |
| D16 | Identity of a moved record | **Recommended:** J5's counterparts: a new record in the target with `sourceId`, found again on the next move from the same source; moving back finds the original through the same link | X3 |
| D17 | Move or copy | **Recommended:** copy by default; move is the copy plus the source records' deletion in a change set of the source workspace, reviewed on its own; never a silent deletion | X3 |
| D18 | Where the model-to-model mapping lives | **Recommended:** a saved resource beside import profiles, with the source a workspace instead of a file, edited by A5's mapping operations with undo and history, reused for the next move | X1 |
| D19 | The job of a move | **Recommended:** one job kind with the import's phases (dry run of every item, then the load into a change set); the same row outcomes and paging | X2, X3 |
| D20 | Who sees a move in the target's feed and events | **Recommended:** as any change set: nothing until published, then the ordinary events | X3 |
| D21 | Where the mock-ups live | **Recommended:** claude.ai artifacts, as 0.10's | P0 |
| D22 | "Tenant" in DECISIONS, TODO and ROADMAP_COVERAGE | **Recommended:** replaced by "workspace" and "model"; ADR-021's closing paragraph marked superseded by ADR-042 | P0 |
| D23 | Moving a record back | **Accepted (P0):** a move stores each moved record's origin in a table of its own; a record moved back finds its original | X3 |
| D24 | `model_releases.is_active` | **Accepted (P0):** dropped; `GET /model-releases` gains `assigned` and `workspaces` | M1 |
| D25 | What a draft compiles against | **Accepted (P0):** its base, with compatibility reported for each workspace running the base's model | M3 |
| D26 | Change sets left on a replaced release | **Accepted (P0):** cannot publish until moved (V3) or discarded; activation lists them | M2 |
| D27 | A consumer API key in two models | **Accepted (P0):** allowed; index and OpenAPI name their workspace and release | M3 |
| D28 | Unique values per workspace | **Accepted (P0):** triggers read each record's workspace release; activation refills that workspace only | M2 |
| D29 | A workspace whose release cannot be loaded | **Accepted (P0):** that workspace alone answers `503`; the others serve | M1 |

## Findings from 0.10 R that belong to 0.11

- **Multi-process job worker** (R-F5, R-F6, R-F7, R-F9): N2.
- **Statistics after bulk writes** (R-F19): a dry run's or check's fresh rows were joined before
  PostgreSQL's statistics saw them (95 s and 64 s of a 10,000-row check), fixed for that path; Q1
  looks for the same pattern on every bulk path, and V1 and X2 avoid it by design.
- **Job lookups** (R-F14): fixed in R (`job_parameter`, three partial indexes, migration
  `20261017_01`).
- **`NOT IN` subqueries** that may outgrow `work_mem` (TODO since 0.9 R): Q1.
- **One visual-gate flake** whose cause was not found (TODO): looked at in R's gates only if it
  recurs.

## Risks

- **Scope.** Two user requirements on top of the roadmap's production work. Part 1 first and the cut
  line (D13) keep the requirements in reach; Part 2's measurements are once each.
- **The resolution change touches about 25 modules.** P0 lists every call site before M1; M1 is the
  only package that changes resolution, and it changes nothing while one release is assigned.
- **The move is open-ended** ("everything which possibly can be needed"). P0's inventory, accepted
  by the user, is the scope; a new case found later is an amendment package, not silent growth.
- **Multi-process work comes late.** M1's resolution is designed so N1 only adds propagation, not a
  second redesign.
- **The laptop.** Full-volume measurements and runners run as announced blocks, one at a time.

## Next

1. **P0, the design pass**, on the instruction "deliver P0": D4–D11 and D13–D22
   settled (D2, D3 and D12 accepted 2026-10-15), the move inventory completed, ADR-042, the API design, J36–J38, the M5 and X4 mock-ups.
