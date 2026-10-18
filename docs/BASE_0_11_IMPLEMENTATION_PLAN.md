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
**Delivered:** P0, M1 with M2 (2026-10-15), M3, M4, M5, M6 and M6a (2026-10-16), released as
0.11.0-alpha.1 (2026-10-17, tag `v0.11.0-alpha.1`); V1, V2, V3, V4, X1, X2, S1 and X3 (2026-10-18).

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
| 4 | [M3](#m3-instance-wide-resources-bound-to-a-workspaces-model) | M2 | **Delivered 2026-10-16.** Import profiles, drafts, source files, jobs and dry runs, consumer APIs and events resolved through the workspace's model |
| 5 | [M4](#m4-reads-spanning-workspaces) | M3 | **Delivered 2026-10-16.** The cross-type lookup over several workspaces asked for; counterparts refused across models; the feed, coverage and exports stay within one workspace |
| 6 | [M5](#m5-the-ui-follows-the-workspaces-model) | M4 | **Delivered 2026-10-16.** The shell follows the workspace's model; Settings › Model per workspace; "New from a workbook" into a chosen workspace |
| 7 | [M6](#m6-workspace-models-checkpoint) | M5 | **Delivered 2026-10-16, released as 0.11.0-alpha.1 (2026-10-17).** Two workspaces on two models composed in the browser; the roadmap's first workspace-model exit item; tagged 0.11.0-alpha.1 (D12) |
| 7a | [M6a](#m6a-a-write-names-the-release-it-was-built-on) | M5 | **Delivered 2026-10-16.** Added 2026-10-16 in M6: a write names the release it was built on; refused when the workspace runs another; M6's case 4 |
| 8 | [V1](#v1-a-workspaces-data-migrated-to-another-release) | M2 | **Delivered 2026-10-18.** Migration plan for one workspace: preview, conversions, loss, confirm bound to versions, atomic switch |
| 9 | [V2](#v2-a-change-set-from-a-publication-moved-to-another-release) | V1 | **Delivered 2026-10-18.** GAP-02: a change set on an older release published by migrating its workspace to that release |
| 10 | [V3](#v3-a-change-set-moved-onto-a-release-it-does-not-fit) | V1 | **Delivered 2026-10-18.** ADR-028: a change set moved onto the release its workspace runs when its content does not fit, previewed and confirmed |
| 11 | [V4](#v4-the-schema-language-window) | V1, M6 | **Delivered 2026-10-18.** The window 0.5–0.10 declared once, its conversion rules written, installation outside it refused like activation, two startup refusals fixed |
| 12 | [X1](#x1-the-mapping-between-two-models) | M4, P0 inventory | **Delivered 2026-10-18.** The model-to-model mapping: proposed, completed with mapping operations, saved and reused |
| 13 | [X2](#x2-selection-and-the-dry-run-of-a-move) | X1 | **Delivered 2026-10-18.** What moves; the dry run of every item; what cannot move, with reasons |
| 14 | [X3](#x3-the-move) | X2 | **Delivered 2026-10-18.** Copy or move into a reviewed change set: the dry run confirmed or executed, origins and the move back, the source's deletion published after the copy |
| 15 | [X4](#x4-the-move-editor) | X3, M5 | The move editor: the two models, the mapping, the proposals, the dry-run figures and the report |
| 16 | [X5](#x5-move-checkpoint) | X4 | The roadmap's move exit item at full volume, measured once |
| | **Part 2 — production hardening** | | |
| 17 | [S1](#s1-the-backend-suites-time) | — | **Delivered 2026-10-18.** Journey cases spread over the workers; the full suite with `-n 6` under a revised 11-minute ceiling (D126) |
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

##### M3 plan (2026-10-15)

**Planned 2026-10-15; D35–D40 and the test cases accepted by the user the same day ("yes").**
Checked against the code at `6cd6404`.

**Already done by M1 (D33), not rebuilt:** jobs and batches (`open_job_context`,
`open_batch_context`), source profiling, profile checks, dry runs and inference started in a
workspace, consumer reads, the event dispatcher, subscriptions, and the event deriver (it reads the
release each feed entry recorded).

**What is left, found in the code:**

- `engine/imports/profiles.py`: create, read, list, update and delete resolve the default
  workspace's model; nothing records which model a profile belongs to. `draft_profile.
  save_at_installation` overwrites a profile of the same key whatever model it was written for.
- `routers/model_management.py`: the draft's outline, a draft's consumer API, compile and install
  read the default workspace's model. Install runs a compatibility analysis and throws the result
  away (installing is instance-wide; it goes).
- `routers/model_releases.py` `…/diff`: compatibility against the default workspace's data only.
- `engine/model/authoring/released.py`: a draft-only operation's impact counts records, values and
  relationships in **every** workspace and change set, whatever model they run; a draft without a
  base is compared with the default workspace's release, so a new model's draft reads as the default
  model with everything removed.
- `consumer/router.py`: the index and the OpenAPI document read the default workspace's model and
  take no `workspace`; `management/reference` lists the default workspace's consumer APIs.

**Decisions** (D35 onward; each with what, why and cost):

| # | Question | Recommendation |
| --- | --- | --- |
| D35 | Where a profile's model (D9's `modelKey`) is kept | **Read from the release it was last saved against** (`checked_release_id`'s `release_key`), no new column. Why: every save already records that release, and M3 makes every save run against a release of the profile's own model, so the two cannot drift; no migration means no startup and upgrade checks. Cost: the list's `modelKey` filter joins `model_releases` |
| D36 | A draft's profile installed under a key another model's profile holds | **Refused before anything is installed:** `409 IMPORT_PROFILE_MODEL_MISMATCH` naming the profile, its `modelKey` and the draft's. Why: today the installation silently rewrites that profile and the other model's imports start failing (principle 7). Cost: the administrator renames the draft's profile key first |
| D37 | What a draft is compared with | **One rule for compile, the outline, a draft's consumer API and released-element impact:** its base release; without a base, the newest installed release of its own `release.key`; with none, nothing (a new model: every element new, no consumer contract to raise, no data impact). Impact counts only workspaces running that model (any of its releases) and their change sets. `compatibility` (top level) stays what activating into the **default workspace** would do, as the UI uses it until M5; `compatibility.workspaces` (D25) adds one entry per workspace running the draft's model, against that workspace's own release and data. The release diff gets the same `workspaces`. Why: D25 said "without a base, the default workspace's release", which turns a new model's draft into "everything removed" and counts another model's records as its impact. Cost: one compatibility analysis per workspace of the model at compile (set statements each; workspaces are few) |
| D38 | Choosing the target workspace in the editor (M3's "installing and activating from the editor asks for the target workspace(s)") | **Moved to M5**, whose approved mock-up holds that dialog and New from a workbook's choice. M3 delivers the API side of D15: install, then `POST /workspaces` with `modelReleaseId` or activation into one workspace, already enough for an integrator. The browser keeps installing and activating into the default workspace until M5. Why: no screen is built twice or without its approved shape. Cost: J36.4 is API-only in M3 |
| D39 | The API reference page | **Takes `?workspace=`** and lists that workspace's consumer APIs, linking each OpenAPI with the same `workspace`; the default workspace without it. Why: it is the last reader of "the" model. Cost: one parameter |
| D40 | A profile read in a workspace running another model | **Read, not refused:** `valid: false` with one problem `IMPORT_PROFILE_MODEL_MISMATCH` at `""`; the list takes `modelKey` and `workspaceKey`. Saving (create, update) runs against `workspaceKey`'s release and refuses another model's profile with `422 IMPORT_PROFILE_MODEL_MISMATCH`; so do an import naming it and a file uploaded to it in such a workspace. Why: a list must still show every profile; only using one is wrong. Cost: none beyond the code |

**What is built:**

1. **Import profiles:** `modelKey` on every profile response (D35); `workspaceKey` on create and
   update (body) and on the read and list (query), the default workspace without it; the list's
   `modelKey` filter; the mismatch refusal on save, import and upload, the problem on read (D40);
   D36's check in `save_at_installation`, before installing.
2. **Drafts:** `released.base_release` and `impact` by D37; compile, the outline and a draft's
   consumer API compared by D37; `compatibility.workspaces` on compile and on the release diff;
   install's discarded analysis removed.
3. **Consumer:** the index and OpenAPI take `workspace`, answer `RDM-Workspace` and
   `X-Model-Release-Id` as the read routes do, and their ETag follows that release; the index's
   OpenAPI links carry the `workspace` asked for (D27); the reference page by D39.
4. **Frontend:** the profile and compile types gain the new fields; no visible change (D38).
5. **Docs:** API.md § What follows the workspace's model moved to delivered (and the drafts
   paragraph), MODEL_AUTHORING (D37, D38), CONSUMER_API (the two routes), USER_JOURNEYS J36.4
   evidence, API_JOURNEYS, CHANGELOG, PROJECT_STATUS, TODO. OpenAPI lock re-baselined by diffing.

**Journey test cases** (`workspace_models` marker; each runs X beside Y and the reverse, names
structures only):

1. **J36.4 A new model from a workbook into a new workspace.** Given X in the default workspace.
   When a draft started empty with a workbook has its new-model proposals applied, is compiled,
   installed, and a workspace is created on that release. Then compile's `compatibility.workspaces`
   is empty and its `changes` list every element as added; the default workspace still runs X at
   its version; the profile saved at installation has the new model's `modelKey` and loads the
   workbook into the new workspace; used in the default workspace it is refused
   `422 IMPORT_PROFILE_MODEL_MISMATCH`.
2. **A profile per model.** Given workspaces on X and Y. When a profile is saved in each and an
   import runs in each with its own. Then both load; X's profile named in Y's workspace (import, file
   upload, update) is refused `422 IMPORT_PROFILE_MODEL_MISMATCH` with `details.modelKey` and
   `workspaceModelKey`; read with `workspaceKey` of Y it is `valid: false` with that problem;
   `GET /import-profiles?modelKey=` lists only that model's.
3. **D36.** Given X's profile `P`. When a draft of Y's model carrying a profile with `P`'s key is
   installed. Then `409 IMPORT_PROFILE_MODEL_MISMATCH`, no release installed, `P` unchanged.
4. **D25/D37 compatibility per workspace.** Given two workspaces on X1, one holding `R` records, and
   a workspace on Y. When a draft based on X1 that removes `R` is compiled, and X1 is diffed with the
   release it installs. Then `compatibility.workspaces` lists the two X workspaces, the one with
   records needing a migration with its counts, the other compatible, and not Y's; a draft-only
   removal of `R` reports an impact counting only the X workspaces' records.
5. **D10/D27 consumer APIs per workspace.** Given the two workspaces. When the index and each
   definition's OpenAPI are read with `workspace` of each. Then each lists its own model's
   definitions and contract versions, names the workspace (`RDM-Workspace`) and release
   (`X-Model-Release-Id`), and its OpenAPI links carry the workspace; another workspace's definition
   is `404` with its not-found code; an `R` created in each workspace is derived as an event under
   that workspace's definition (passes since M1; kept as the variant's evidence).

**Unit:** D37's "compared with" choice (base, newest of the key, none). **Groups:**
`workspace_models`, `jobs`, `authoring`, `consumer`, `events`, `contract`, with the frontend's
profile and compile tests, format, lint and build. No migration, so no startup checks.

**Composable domains (ADR-032):** no door is affected; profiles stay keyed as today and the mapping
coverage is untouched.

##### M3 record (2026-10-16)

**Delivered 2026-10-16.** Built as planned, through the API:

- **Import profiles** (`engine/imports/profiles.py`): `modelKey` read from the release a profile was
  saved against (D35); create and update against `workspaceKey`'s release, the read and the list
  under it, the list's `modelKey` filter; `IMPORT_PROFILE_MODEL_MISMATCH` as a problem on a read and
  a refusal on save, on `POST /imports` with `profileKey` and on `POST /source-files` with
  `owner.profileKey` (D40); `draft_profile.require_installable` refuses an installation over another
  model's profile before installing (D36).
- **Drafts:** `released.base_release` by D37 (base, the newest installed release of the draft's
  `release.key`, none), `base_model`, and `impact` scoped to the workspaces running the draft's model
  and their change sets; compile's `changes`, `againstReleaseId` and `consumerContracts`, the
  outline's and a draft consumer API's contracts compared by D37;
  `engine/model/draft_compatibility.py` (`assess`, `by_workspace`) gives compile and the release diff
  `compatibility.workspaces` (`CandidateCompatibilityResponse`, `WorkspaceCompatibilityResponse`);
  install's discarded compatibility analysis removed.
- **Consumer:** the index and OpenAPI document take `workspace` and answer `RDM-Workspace` and
  `X-Model-Release-Id`, their ETag following that workspace's release; the index's links carry the
  workspace; the `/docs` page takes `?workspace=` (D39).
- **Frontend:** the `ImportProfile`, compilation and diff types; no visible change (D38).
- **Docs:** API.md (§ What follows the workspace's model, delivered; the profile section),
  CONSUMER_API, MODEL_AUTHORING, CURRENT_FUNCTIONALITY, USER_JOURNEYS (J36.4 delivered, evidence),
  API_JOURNEYS, EXECUTION_GUIDE (`workspace_models` 24 cases), CHANGELOG, PROJECT_STATUS, TODO.

**Where it differs from the plan:** `compatibility.workspaces` leaves out retired workspaces, which
no activation reaches (`WORKSPACE_RETIRED`); found by the case's first run on the seed's retired
workspace. The release diff's top-level `compatibility` and `consumerContracts` stay against the
default workspace, as the plan's top-level rule says; only compile's `consumerContracts` follow D37.
The consumer read routes still answer no `X-Model-Release-Id` (only the index and OpenAPI do). The
D36 refusal names `draftModelKey` beside `profileKey` and `modelKey`.

**Older tests changed because M3 made them wrong** (approved by the user 2026-10-16): J08
`test_data_the_candidate_does_not_fit_blocks_activation` (the top level counts the default
workspace's records, each active workspace of the model its own in `compatibility.workspaces`, the
retired one not listed; before, the top level summed three workspaces, which activation no longer
checks since M1); `test_model_lifecycle`'s diff case (the new `workspaces` list); five Vitest
fixtures (the new fields).

**Checks:**

- `test_j36_workspace_resources.py`: 5 cases × 2 directions written first and seen failing (10
  failed: fields, parameters and refusals absent), then 10 passed (18 s). Unit:
  `tests/unit/engine/model/authoring/test_released.py` (D37's choice), 1 passed.
- `contract` with J36: 79 passed; `contract` again after the docs: 75 passed. Both times
  `test_boundaries::test_tiers_hold` failed with the import cycle recorded in M1 (TODO), none of it
  M3's. OpenAPI lock re-baselined after diffing the default document against `6cd6404`: profile
  `modelKey` and `workspaceKey`, the list's `modelKey` filter, `CandidateCompatibilityResponse` and
  `WorkspaceCompatibilityResponse` replacing `ModelCompatibilityResponse` in the diff, descriptions;
  nothing else.
- The groups the guide selects (`jobs`, `authoring`, `consumer`, `feed`, `model_admin`), on the
  user's go-ahead, load 5: 4,400 passed and 3 failed in 5 min 36 s, over the 2-minute ceiling as
  announced. The 3 were the older tests above; fixed, then the J08 cases (2 passed),
  `test_model_lifecycle` as a module (27 passed; the case alone fails on a fresh database for a
  reason older than M3, TODO) and the groups' serial part (1 passed).
- Ruff on `app/` and `tests/`: clean. Frontend: `tsc`, Vitest on the 5 changed files (28 passed),
  `npm run format`, `npm run lint` (0 errors, the 7 listed warnings), `npm run build`.

**Not run:** the full suites, `startup` (no migration), `volume`, `queries`, the browser runners (no
visible change), all at R. **What the user cannot do yet:** choose the workspace in the browser:
Settings › Model, the editor's install dialog and New from a workbook still install and activate
into the default workspace (M5, D38); reads spanning workspaces whose models differ (M4).

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

##### M4 plan (2026-10-16)

**Planned 2026-10-16; D41–D45 and the test cases accepted by the user the same day ("okay, you
can go ahead with the cross-workspace read"), after D41's questions: separate calls per workspace
already work; the spanning read adds one ordered, paged list and finding a record by ID alone; the
repeated `workspaceKey` is an array in the OpenAPI document; its cost is measured once (below).** Checked
against the code at `5921015`.

**What the code does today (found, not assumed):**

- **No read of records spans workspaces.** `GET /objects` (the cross-type lookup) without
  `workspaceKey` reads the **default workspace** (`resolve_workspace(None)`), as D6 and ADR-042 say
  for every route that names no workspace. P0's API design (API.md § Reads spanning workspaces)
  says instead that `GET /objects` *without* `workspaceKey` spans every workspace. The two accepted
  texts disagree, and following API.md would change today's answer for every client that leaves
  `workspaceKey` out (D41).
- **The feed** is per workspace by its path (`/workspaces/{key}/feed`), and each entry already
  carries `modelReleaseId` (M1). **Mapping coverage** reads one workspace (`workspaceKey`, one
  snapshot). **An export** names one workspace. None of the three spans anything (D45).
- **Lists that do span workspaces** are management lists: jobs, consumer subscriptions, source
  files, import profiles, workspace models. Their filters match keys stored on the row (`kind`,
  `state`, `consumerApi`, `profileKey`), none read through a model, and their items name their
  workspace (jobs also `modelReleaseId`).
- **Counterparts** (`otherWorkspaceIds: "counterparts"`, 0.9 J5) translate another workspace's
  record ID into this workspace's counterpart whatever model that workspace runs: in an inline batch
  (`_Items.translate_ids`, `engine/jobs/batches.py`) and in a file's binding
  (`_counterpart_matches`, `engine/imports/binding.py`). A record of a model with other types
  then reaches this workspace's rules as if it were its own: its type is unknown here or, worse, a
  type with the same key means something else.

**Decisions** (D41 onward; each with what, why and cost):

| # | Question | Recommendation |
| --- | --- | --- |
| D41 | How a read spanning workspaces is asked for | **Only when asked: `GET /objects` takes `workspaceKey` repeatable.** None reads the default workspace and one reads that workspace, both as today (D6). Two or more read those workspaces' live records together. A spanning read is live only: `changeSetId` or `publicationId` belong to one workspace and with two workspaces are `422 WORKSPACE_CONTEXT_MISMATCH`. Why: keeps D6 and ADR-042, keeps every current client's answer, and still gives the integrator's journey (a record found by ID or name without knowing its workspace). API.md's "without `workspaceKey`" is corrected. Cost: the lookup builds over a set of workspaces, each item's attributes are formatted under its own workspace's model, the cursor binds the sorted workspace list. Not chosen: spanning when `workspaceKey` is left out (changes today's answers), `workspaceKey=*` (finding every workspace is one `GET /workspaces`; workspaces are few) |
| D42 | What a spanning read refuses (D7's detail) | **A model element named that some read workspace's model lacks:** `objectTypeKey` or `applicationKey` is `422 MODEL_ELEMENT_NOT_IN_EVERY_MODEL` with `details.element` (`{"kind": "objectType" or "application", "key"}`) and `details.workspaces` (the keys lacking it); no read model holding it stays `404 UNKNOWN_OBJECT_TYPE` (or `UNKNOWN_APPLICATION`) as today. The built-in filters (`id`, `name`, `parentObjectId`, timestamps) and `search` read no model and are always allowed. `sort=objectType` orders by each record's type name in its own workspace's model. Why: D7, and a type key that exists in only one model would silently narrow the read to that workspace. Cost: one check per element over the resolved models |
| D43 | Where an item names its release | **`modelReleaseId` on every item of the cross-type lookup**, in every context (live single, live spanning, change set, publication), so the route has one item shape; the per-type list and record reads are unchanged (one workspace, one release, already in `X-Model-Release-Id` on `GET /model`). Why: D7's "every item names its workspace and release"; items already carry `workspaceKey`. Cost: one field on the lookup's items |
| D44 | Counterparts between workspaces whose models differ (D7) | **Refused per item:** an ID held by a record of a workspace running another model (another `release.key`, D5) is not translated; its item or file row is rejected `COUNTERPARTS_ACROSS_MODELS` with `details.workspaceKey`, `modelKey` (that workspace's) and `workspaceModelKey` (this one's), and the job's notice for that workspace says the rows cannot load and points to moving data between models (Track X). The same model at another release keeps working as today. Why: per item, as every other row refusal, so the rest of the file still loads and nothing is dropped silently (principle 7); an import's rows are read after it is submitted, so a request-level refusal would come too late anyway. Cost: one check in each of the two translation paths. Without counterparts (`refuse`) nothing changes: `RECORD_IDS_OF_ANOTHER_WORKSPACE` as today |
| D45 | The feed, mapping coverage, exports and the spanning management lists | **No spanning variant; documented.** Each of the feed, coverage and an export reads one workspace under its own release; a feed entry's `modelReleaseId` already shows where the workspace's model changed. Coverage across workspaces has nothing to count, as no relationship crosses workspaces (D8); a multi-workspace export has no journey (data goes between models by a move, Track X). The management lists' filters match stored keys, so `consumerApi` lists the subscriptions of that key in every workspace whatever contract it means there (D27). Why: no journey needs more, and the exit ("no read combines two snapshots") already holds for them. Cost: API.md paragraphs only. Composable domains: the mapping-coverage door is unaffected |

A spanned workspace whose release cannot be loaded makes the whole read `503
MODEL_REGISTRY_UNAVAILABLE` naming it (D29), never a page silently without its records.

**What is built:**

1. **Lookup** (`engine/reads/object_lookup.py`, `routers/objects.py`): `workspaceKey` repeatable;
   one snapshot per workspace; the element check (D42); the statement over the workspace set with
   types narrowed per model; `objectType` sorted by each workspace's names; items formatted per
   workspace with `modelReleaseId` (D43); the cursor binding the workspaces.
2. **Counterparts** (D44): both translation paths skip an ID of another model's workspace and
   reject its item or row; the notice reworded for it.
3. **Docs:** API.md (§ Reads spanning workspaces delivered and corrected by D41; the cross-type
   lookup; counterparts), USER_JOURNEYS J36.7, API_JOURNEYS, CURRENT_FUNCTIONALITY, CHANGELOG,
   PROJECT_STATUS, TODO. OpenAPI lock re-baselined by diffing.

No migration, no frontend change (the UI always names its workspace).

**Journey test cases** (`workspace_models` marker; X beside Y and the reverse, structures only):

1. **J36.7 A lookup over two workspaces on two models.** Given the default workspace on X and a
   workspace on Y, each with records. When `GET /objects` names both workspaces. Then it pages every
   record of both once, ordered by name across them; each item names its `workspaceKey` and the
   `modelReleaseId` of that workspace's release, with its attributes as its own model names them;
   `filter.id.eq` finds a Y record without its workspace being known; `sort=objectType` answers.
2. **An element one model lacks.** When the spanning lookup names a type only X has, then `422
   MODEL_ELEMENT_NOT_IN_EVERY_MODEL` with `details.workspaces` = [Y's workspace]; the same type
   with X's workspace alone answers; a type neither has is `404 UNKNOWN_OBJECT_TYPE`; a
   `changeSetId` with two workspaces is `422 WORKSPACE_CONTEXT_MISMATCH`.
3. **Without a workspace, as before.** `GET /objects` without `workspaceKey` lists only the default
   workspace's records, each with its `modelReleaseId`.
4. **Counterparts across models.** When Y's records' IDs are sent to X's workspace with
   `otherWorkspaceIds: "counterparts"`, through `POST /batches` and through an import of Y's export,
   then each such item or row is rejected `COUNTERPARTS_ACROSS_MODELS` naming Y's workspace and both
   model keys, the import's notice says they cannot load, and nothing of Y's is created in X's
   workspace; rows without IDs in the same file load.

**Unit:** none planned; the element check is a set difference, covered by case 2. **Groups:**
`workspace_models`, `queries` (the lookup), `jobs` (counterparts in imports), `contract`. No
migration, so no startup checks; no browser runner (no visible change).

**Composable domains (ADR-032):** identity unchanged (counterparts keep their derivation, only
their use across models is refused); mapping coverage unaffected (D45).

##### M4 record (2026-10-16)

**Delivered 2026-10-16.** Built as planned, through the API:

- **The spanning lookup** (`engine/reads/object_lookup.py` `build_spanning_lookup_query`,
  `routers/objects.py`): `workspaceKey` repeatable; two or more resolve each workspace's snapshot and
  read their live records in one statement (`workspace_key IN …`, the types of every model), the
  cursor binding `workspaceKeys`; D42's check (`MODEL_ELEMENT_NOT_IN_EVERY_MODEL`, the element's own
  404 when no model holds it); `sort=objectType` through a per-workspace label
  (`ObjectColumns.object_type_label` in `object_query.py`); items built per workspace's model.
  Every lookup item is `LookupObject` with `modelReleaseId` (D43).
- **Counterparts across models** (D44): `records/counterparts.held_elsewhere` names each other
  workspace's model; a batch item naming such a record is refused
  `refusals.counterparts_across_models` (`engine/jobs/batches.py`), the import's binding gives it no
  counterpart (`imports/binding.py`), and the job's notice is `COUNTERPARTS_ACROSS_MODELS`
  (`jobs/store.py`).
- **Docs:** API.md (the cross-type lookup, `otherWorkspaceIds`, notices, counterparts, § Reads
  spanning workspaces delivered and corrected by D41), USER_JOURNEYS J36.7, API_JOURNEYS,
  CURRENT_FUNCTIONALITY, EXECUTION_GUIDE (`workspace_models` 32 cases), CHANGELOG.

**Where it differs from the plan:** the test cases name an application one model lacks instead of a
shared one (the two generated models share no application key; the refusal is D42's). A spanning
read hands the shared builder the first workspace's model and types, as the lookup filters, searches
and sorts only built-in fields; the type label covers the others.

**Older test changed because M4 made it wrong:** `test_cross_type_lookup::
test_an_item_has_the_per_type_list_shape` compares a lookup item with the per-type list's item; it
now requires `modelReleaseId` on each lookup item and compares the rest (D43).

**Checks:**

- `test_j36_spanning_reads.py`: 4 cases × 2 directions written first and seen failing (8 failed: a
  repeated `workspaceKey` read only the last workspace, no `modelReleaseId`, the counterpart
  translated), then 8 passed.
- `workspace_models`, `queries`, `records`, `change_sets`, `contract` in parallel: 918 passed and 3
  failed in 4 min 8 s, over the 2-minute ceiling at load 5.9. The 3: the older test above (fixed, 2
  passed) and `test_boundaries::test_tiers_hold`, the import cycle recorded in M1 (TODO), none of it
  M4's. Their serial part: 2 passed.
- `--journey J27.14 --journey J11 --journey J36` (counterparts, bulk changes, J36): 90 passed in
  73 s.
- OpenAPI lock re-baselined after diffing the default document against `5921015`: `LookupObject`,
  the lookup's items, `workspaceKey` as an array, the route's description; nothing else.
  `test_api_journeys`, `test_openapi_contract`, `test_error_codes`: 16 passed. Ruff on `app/` and
  `tests/`: clean.

- `jobs` (selected by `engine/jobs/*` and `engine/imports/*`), on the user's go-ahead: 531 passed in
  4 min 20 s, over the 2-minute ceiling as announced; its serial part 1 passed.
- **D41's cost, measured once** on the user's go-ahead (load 7.6; the volume fixture at full scale,
  seeded in 306 s since no seed was stored; `vol-workspace` and `default` on the volume model,
  257,758 records; 20-row pages; median of five after a warm-up): a first page 6.0 ms over one
  workspace, 6.7 ms over two; a name search with its total 12.6 ms and 13.3 ms; over two, sorted by
  type 74.9 ms (the per-workspace label is evaluated for every record) and every record counted
  26.8 ms. Spanning costs about what one workspace holding both workspaces' records costs.

**Not run:** the full suites, `startup` (no migration), `volume` and the read budgets (the
measurement above stands for the new reads), the browser runners (no visible change), all at R.
**What the user cannot do yet:** choose the workspace in the browser, and the lookup over several
workspaces has no screen (M5); data goes between workspaces whose models differ only through the
move (Track X, X1–X3); the counterpart refusal points to it before it exists.

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

##### M5 plan (2026-10-16)

**Planned 2026-10-16; D46–D55 and the test cases accepted by the user the same day ("yes it is good you can go ahead").** Checked
against the code at `c387e97` and the approved mock-up (boards Main, SettingsModel, NewWorkspace,
PhoneShell).

**What the code does today (found, not assumed):**

- **One model for the whole browser tab.** `useRouter` loads `GET /model` without a workspace once
  at start (the default workspace's model) and parses every route with it; `reloadModel` reloads the
  same. Switching workspace (`App.changeWorkspace`) keeps that model, so a workspace on another model
  shows the default workspace's applications and navigation over its own records.
- **A route naming an application the model lacks** is silently replaced by the default route
  (`useRouter`'s `active`), the reason recorded there being a release that retired an application.
- **The workspace switcher** is `WorkspaceSelector`, a search combo box in the rail on a desktop
  (restored there in U3 at the user's request) and opened from the band on a phone (0.10 N1). Its
  options name the label and key only. Workspace responses carry `model` (`releaseKey`,
  `releaseVersion`, …) but no release name.
- **Settings › Model** (`ModelWorkbench`) is the U3 catalogue (releases and drafts) beside the
  selected item; without a selection it shows "the active release", now the default workspace's.
  A release's **Activate…** (`ModelReleaseDetail`) and the editor's **Install and activate**
  (`InstallDialog`) both activate into the default workspace (`api.defaultWorkspaceModel`). The
  activation check reads `GET /model-releases/{id}/diff`, whose top-level `compatibility` is the
  default workspace's (M3); `compatibility.workspaces` covers only workspaces already on the
  candidate's model, so nothing checks a release of **another** model against a chosen workspace.
- **Settings › Workspaces** (`WorkspaceAdmin`, W4/U3 catalogue and detail) creates a workspace with
  key and label only; the API's `modelReleaseId` (M1) is not offered.
- **Settings pages** use the tab's one model: the job page and job toasts name types with it,
  whatever workspace the job ran in. The editor previews live data of the workspace the user came
  from, whatever model that workspace runs.

**Decisions** (D46 onward; each with what, why and cost):

| # | Question | Recommendation |
| --- | --- | --- |
| D46 | Where the workspace switcher sits | **Where it is: the rail on a desktop, the band on a phone,** with the mock-up's content added: under the field the current workspace's model name and release; each option's line "model name · release"; an **Other model** or **Other release** mark on options that differ from the current workspace's. Why: the mock-up put the switcher in the band, but the rail is where you asked for it in U3, and U-D14 allows one switcher only. Cost: none beyond the content |
| D47 | Telling the user the model changed on a switch | **A toast,** not the mock-up's inline notice: "South branch runs Library catalogue 2.0.0, another release of the model North branch runs (2.1.0)" or "…a different model…". Why: on 2026-10-15 you reported a page notice that stayed on every page until a reload; it became a toast then. Cost: none |
| D48 | A route naming an application, collection or record type the workspace's model lacks | **The mock-up's page "‹name› is not in this workspace's model",** in place of today's silent jump to the default route, for every cause (another model, or a release that removed it). It names the workspace's model and release, lists the workspaces whose model has it, and offers "Open ‹start› in ‹workspace›" and, after a switch, "Back to ‹previous workspace›". An unknown workspace key in the address gets the same kind of page ("No workspace ‹key›"), and a workspace whose release cannot be loaded (D29) a page naming it, with the switcher still working. Why: a silent jump hides that the bookmark points elsewhere; one rule for every cause. Cost: listing the holders reads each distinct release's model once (few releases), only when the page shows |
| D49 | Which model Settings and job pages use | **Settings reads the model of the workspace you came from** (its top bar keeps the same tabs, as U-D14 requires); **a job's page and its toasts read the job's own workspace's model**. The browser keeps one model per workspace, loaded when first needed and reloaded after an activation into that workspace. Why: a job of another workspace otherwise names its types with the wrong model (or by key). Cost: a model cache keyed by workspace in the router |
| D50 | The shape of Settings › Model | **Without a selection, the mock-up's overview:** "Workspaces and their models" (workspace, model, release with "‹newer› installed", schema, since, **Activate a release…**), then **Installed releases** grouped by model, each release "Run by ‹workspaces›" or "Run by no workspace", then the drafts. **With a release or draft selected,** today's catalogue and detail, the catalogue grouped by model and each release marked "Run by …" instead of the single **Active** pill. Why: there is no one active release any more; the overview is the approved shape, and the detail (diff, history, raw JSON, the draft editor's entry) stays as it is. Cost: the overview is a new section; the catalogue changes its grouping |
| D51 | One activation dialog, two ways in | **The mock-up's dialog, opened from a workspace row** (the workspace fixed, a release chosen) **or from a release's Activate…** (the release fixed, a workspace chosen in a field added at the top). It shows the check for that workspace only, the open change sets that would be left on the old release (read before confirming from the workspace's open change sets pinned to its release, since the activation's own list arrives only after it), "Not changed: ‹other workspaces›", and, when the data does not fit, "A migration is needed" with **no button** until V1 builds the migration preview. The release detail's activation check lists `compatibility.workspaces` (each workspace of the model: compatible or needing a migration). Why: one dialog component (U-D14), and the release detail keeps its way in that the 0.10 runners and SC15 use. Cost: a workspace field on the dialog when opened from a release |
| D52 | Checking a release against a chosen workspace (any model) | **`GET /model-releases/{id}/diff` takes `workspaceKey`:** the top-level `compatibility` and `consumerContracts` then describe activating into that workspace, against its own release and data; the default workspace without it, as today (D6); an unknown key `404 WORKSPACE_NOT_FOUND`. Why: D51's dialog must check a release of another model against the chosen workspace, which nothing serves today (`compatibility.workspaces` lists only workspaces on the candidate's model). Cost: one query parameter on a read route; OpenAPI lock re-baselined; two journey cases |
| D53 | The model's name in the switcher and tables | **`releaseName` on a workspace's `model`** (every workspace response, `GET /workspaces/{key}/model`, `GET /workspace-models`): the release's `name`. Why: the mock-up names models ("Library catalogue 2.1.0"); without it each workspace needs one release read. Cost: one field read from the joined release; OpenAPI lock re-baselined |
| D54 | Settings › Workspaces | **Its current layout kept** (W4/U3 catalogue and detail); each entry's subtitle and the detail name the model and release; **New workspace** gains the mock-up's **Model** choice: "The default workspace's model" (named) or "Another installed release" (a list of every installed release of a supported schema, each with the workspaces running it). The mock-up's table is not built. Why: the table would replace an approved layout for one column. Cost: none beyond the dialog field |
| D55 | The editor's workspace and its Install and activate | **The editor previews the live data of a workspace running the draft's model:** the one you came from if it does, else the first active one running it (key order), else none (a new model: the preview's collections are empty, said so). **Install and activate** gains the mock-up's **Activate into**: an existing workspace (a list, the editor's workspace first; others marked Other model when they run another) or a new workspace (name and key, offered where workspace administration is allowed). Activation into an existing workspace refused for its data keeps today's "Installed, not active" outcome with the reason. Why: D15, and a preview of one model over another model's records shows nothing true. Cost: the dialog's choice; install, then activate or `POST /workspaces` with `modelReleaseId` |

**What is built:**

1. **Backend** (D52, D53): the diff's `workspaceKey`; `releaseName` on the workspace's model. No
   migration.
2. **Router and shell:** the address's workspace resolved first, then that workspace's model (cached
   per workspace, D49); switching workspace swaps the model, applications and navigation with the
   page; the D47 toast; the D48 pages; the D46 switcher content.
3. **Settings › Model:** the D50 overview and catalogue, the D51 dialog from both ways in, the
   release detail's per-workspace check.
4. **Settings › Workspaces:** the model in entries and detail; New workspace on a model (D54).
5. **Editor:** its workspace by D55; Install and activate into an existing or new workspace.
6. **Docs:** USER_JOURNEYS J36 (browser evidence), API.md (D52, D53), CURRENT_FUNCTIONALITY,
   MODEL_AUTHORING (D55), UI_ACCEPTANCE (state-inventory rows), EXECUTION_GUIDE (the runner),
   CHANGELOG, PROJECT_STATUS, TODO.

**Journey test cases.** API (`workspace_models` marker, X beside Y and the reverse):

1. **D52.** Given the default workspace on X with records and a workspace on Y with records. When
   Y's release is diffed against X's with `workspaceKey` of X's workspace, then `compatibility`
   counts that workspace's records as needing a migration; with `workspaceKey` of Y's workspace,
   compatible; without it, the default workspace's as before; an unknown key `404
   WORKSPACE_NOT_FOUND`.
2. **D53.** `GET /workspaces`, `GET /workspaces/{key}`, `GET /workspaces/{key}/model` and
   `GET /workspace-models` name each workspace's `releaseName`, the name of the release it runs.

Browser (`test:browser:workspace-m5`, new; the starter model in the default workspace and
`generated-b` installed and run by a second workspace, records in each, set up through the API):

3. **Switch.** The switcher shows the current workspace's model and release; the other workspace is
   marked Other model; choosing it changes the top bar's applications and the navigation to its
   model's, a toast says so, and its records show; switching back restores the first model.
4. **Not in this model.** The address of a collection of the first model opened with the second
   workspace shows "… is not in this workspace's model" naming the workspace holding it; "Open …"
   opens the second model's start; an unknown workspace key shows its page.
5. **Activate into one workspace.** A second release of `generated-b` installed through the API;
   Settings › Model lists both workspaces with their models; **Activate a release…** on the second
   workspace's row, the new release chosen: compatible, "Not changed: ‹default›"; after activating,
   that row shows the new release and the default's row is unchanged; the first model's release
   chosen instead for a workspace with records shows "A migration is needed" and no Activate.
6. **A workspace on a model.** Settings › Workspaces › New workspace on "Another installed release"
   (`generated-b`'s); it opens on that model.
7. **New from a workbook into a new workspace.** A workbook draft installed with **Activate into a
   new workspace**; the new workspace runs the new model and the default's model is unchanged.
8. **Keyboard and phone.** Cases 3 and 5 by keyboard alone; at 390px the band's workspace choice and
   Settings › Model's rows; light and dark screenshots of the switcher, the D48 page, the overview,
   the dialog and the new-workspace dialog for approval.

**Unit (Vitest):** the router resolving a route against its workspace's model (an application the
model lacks gives the D48 state, not the default route); the switcher's marks. **Older tests made
wrong by M5** are changed and listed in the record (expected: `App.test`, `ModelWorkbench.test`,
`InstallDialog.test`, `WorkspaceSelector.test`, and the API calls of runners that use the single
Active pill or the release detail's Activate, syntax-checked only).

**Groups:** `workspace_models`, `contract` (the two API changes); Vitest on the changed files;
format, lint, build; `test:browser:workspace-m5`; the accessibility check on the new surfaces. No
migration, so no startup checks. **UI reference:** the U3 settings pages (SettingsLayout,
CatalogueLayout) and the 0.10 N1 band; state-inventory rows added for the overview, the dialog and
the D48 page.

**Composable domains (ADR-032):** no door is affected (no identity, storage, audit, bulk API, `match`
or coverage change).

**What the user still cannot do after M5:** preview and run a migration when a release does not fit
(V1; the dialog says a migration is needed), move change sets left behind (V3), move data between
models (Track X).

##### M5 record (2026-10-16)

**Delivered 2026-10-16.** The user approved the screenshots the same day ("yes"). Built as
planned:

- **API** (D52, D53): `GET /model-releases/{id}/diff` takes `workspaceKey` (`routers/model_releases.py`,
  resolved with `resolve_model_snapshot`); `releaseName` on `WorkspaceModelResponse`, so on every
  workspace response, its model route, `GET /workspace-models` and an activation's answer.
- **Router and shell** (D46–D49): `model/workspaceModels.ts` holds each workspace's model for the tab
  (`workspaceModel`, `useWorkspaceModel`, `forgetWorkspaceModel`); `useRouter` resolves the address's
  workspace, then its model, and swaps model and page together on a switch (`openWorkspace` for a
  workspace's own start); `routes.missingElement` and the router's `problem` drive
  `features/workspaces/NotInModel.tsx` (D48: an element the model lacks, an unknown or unavailable
  workspace), replacing the silent jump to the start; the switch's toast (`App.modelChangeText`);
  `WorkspaceSelector` names each model and release and marks Other model / Other release through
  `ui/Selection`'s new `mark` (a `StatusPill`); a job's page and toasts use the job's workspace's model.
- **Settings › Model** (D50, D51): `ModelWorkbench`'s overview (Workspaces and their models, Installed
  releases by model with Run by, Drafts) and the catalogue grouped by model;
  `model-admin/ActivateDialog.tsx`, one dialog from a workspace's row or a release's page (checked with
  D52's diff, change sets left behind read from the workspace's open change sets, Not changed, the
  first five reasons and no Activate when the data does not fit); `ModelReleaseDetail` shows Run by
  and checks each workspace of its model (`compatibility.workspaces`).
- **Settings › Workspaces** (D54): the model in each entry and the detail;
  `workspaces/NewWorkspaceFields.tsx` (name, key, the Model choice) extracted from the create dialog
  and shared with the editor.
- **Editor** (D55): the editor's workspace by D55 (`useEditorWorkspace`); `TypePreview` reads under the
  chosen workspace's own model and not from another model's workspace; `InstallDialog`'s Activate
  into (an existing workspace, or a new one created with `modelReleaseId`); `LoadDialog` compares with
  the release its chosen workspace runs (it read the default workspace's). `api.defaultWorkspaceModel`
  removed.
- **Docs:** API.md, USER_JOURNEYS J36, API_JOURNEYS, CURRENT_FUNCTIONALITY (F02, F15),
  MODEL_AUTHORING (D55), UI_ACCEPTANCE (M5-1 to M5-5), EXECUTION_GUIDE (`workspace_models` 36 cases,
  the runner, R's runner list), CHANGELOG, PROJECT_STATUS, TODO.

**Where it differs from the plan:** case 7 installs an API-made draft of a new model from the editor
rather than a workbook draft: the dialog and its Activate into are the same whatever made the draft,
and A5–A7's runners cover the workbook path. A shared select now shows only its option's label once
chosen (`components.css`; a description or mark stays in the list), and the dialog layout check
skips visually hidden controls (react-aria's form select), both found by the runner. The install
dialog names its fields Workspace name and Workspace key beside the release's Name. In the
activation dialog the reasons the data does not fit are a list of the first five (the release's page
lists every one), found when inspecting the screenshot, where they ran together as one paragraph.

**Older tests changed because M5 made them wrong:** `App.test` (the D48 page in place of the silent
fallback; the model cache reset per case), `useRouter.test` (a switch now waits for the other
workspace's model), `ModelReleaseDetail.test` (Run by, the per-workspace check, Activate in a
workspace…), `ModelWorkbench.test` (the overview in place of "the active release beside the
catalogue"), `InstallDialog.test`, `LoadDialog.test`, `JobPage.test` (the job's workspace model),
`WorkspaceSelector.test` (the description names the model), the fixtures' `releaseName`; runners
syntax-checked only: the install button's name in a4a, a4b, a4c, t1 and `designer-surfaces`; `wp12`
(activation through the dialog); `u3-settings`, `accessibility-gate`, `visual-regression-gate` (the
overview's table in place of the catalogue).

**Checks:**

- `test_j36_workspace_ui_reads.py` (D52, D53): 2 cases × 2 directions written first and seen
  failing (4 failed: parameter and field absent), then 4 passed (6 s).
- `contract` and `workspace_models` in one run: 111 passed and 1 failed in 1 min 45 s (load 4.3);
  the failure is `test_boundaries::test_tiers_hold`, the import cycle recorded in M1 (TODO). OpenAPI
  lock re-baselined after diffing the default document against `c387e97`: `releaseName` on
  `WorkspaceModelResponse` and `WorkspaceAssignmentResponse`, the diff's `workspaceKey`; nothing else.
  Ruff on `app/` and `tests/`: clean.
- Frontend: `tsc` clean; Vitest on the changed areas (`app`, `model-admin`, `model-editor`,
  `workspaces`, `jobs`, `settings`, `ui`, `routing`, `model`, `api`): 574 passed in 56 files, the new
  unit cases being the router's per-workspace model and D48 problem (2) and the switcher's marks
  (1); `npm run format`, `npm run lint` (0 errors, the 7 listed warnings), `npm run build`.
- `test:browser:workspace-m5` (new): cases 3–8 passed (17 s), with the starter model and generated-b
  in two workspaces: keyboard alone for the switch and the activation; 390px for the band's choice
  and Settings › Model without sideways scroll; axe with no violations on the second workspace's
  shell, the D48 page, the overview, the activation dialog in both states and the new-workspace
  dialog; the activation and new-workspace dialogs measured. Screenshots light and dark of the
  switcher, the D48 page, the overview, the activation dialog (fits and does not fit), the new
  workspace dialog, the install into a new workspace and the phone switcher and Settings › Model,
  inspected and approved by the user.

**Not run:** the full suites, `startup` (no migration), `model_admin` beyond `contract`, the older
runners changed above (syntax only) and the accessibility and visual gates, all at R, where Settings ›
Model's visual baselines change as intended (TODO). **What the user cannot do yet:** migrate a
workspace's data to a release it does not fit (V1; the dialog says it is not available yet), move
change sets left behind (V3), move data between models (Track X); the lookup over several workspaces
has no screen (no package plans one).

#### M6: Workspace models checkpoint

**Needs:** M5.

**Scope:** J36 composed in the browser over the real backend on `generated-a` and `generated-b` in
two workspaces; the roadmap's exit item "two workspaces of one instance run two different models side
by side, each installed, activated and migrated on its own, with no request combining their
snapshots" (its "migrated" part completed by V1). Released as 0.11.0-alpha.1 when it passes, tagged
`v0.11.0-alpha.1` on the user's instruction (D12).

**Exit:** the checkpoint passes, or each failure is explained and tracked.

##### M6 plan (2026-10-16)

**Planned 2026-10-16; D56–D62 and the test cases accepted by the user the same day ("yes").** Checked
against the code at `52cce04`, in the shape of 0.10's [T1](BASE_0_10_IMPLEMENTATION_PLAN.md#t1-designer-checkpoint).

**What each package proved on its own (found, not assumed):**

- **The API side** is J36.1–J36.8 in `test_j36_workspace_models` (7 cases), `_resources` (5),
  `_spanning_reads` (4) and `_ui_reads` (2), each generated A beside B and B beside A.
- **The browser side** is `test:browser:workspace-m5`: the **starter model** in the default workspace
  beside generated-b. It walks the switch, the D48 page, one activation, a workspace created on a
  release and the editor's install into a new workspace. It never writes a record, opens a change set
  or publishes in the second workspace, never runs generated-a, and never meets the commit guard
  (J36.5) in the browser. Nothing walks J36 from install to published data in two workspaces.
- **Deferred by M5:** the accessibility and visual gates for its surfaces (switcher marks, the D48
  page, Settings › Model's overview, the activation dialog, the new-workspace dialog's Model choice,
  the install dialog's Activate into), and Settings › Model's baselines, which change as intended
  (TODO "At R").
- **Open in TODO touching Track M:** M5's two small findings (the rail marks the first collection as
  current on the D48 page; a switch reads the rail's collections twice), marked "worth a look with
  M6"; `test_boundaries::test_tiers_hold` failing on the import cycle `sources.draft_profile` ↔
  `sources.dry_run` (the `contract` group fails on it); `test_model_lifecycle::…assesses_active_runtime_data`
  passing only after its module's earlier tests.
- **What the alpha touches:** one migration since `v0.10.0`, `20261018_01_workspace_models`, whose
  upgrade and interrupted run `test_startup::test_upgrade_to_workspace_models_…` covers from the
  head's baseline (not from a database the 0.10.0 code built). Version strings `0.10.0` in
  `backend/pyproject.toml`, `ENGINE_VERSION` and `frontend/package.json`. The starter model is
  unchanged, so no content release.

**What is built:**

1. **A composed browser journey**, `e2e/workspace-m6-checkpoint.mjs` (`test:browser:workspace-m6`),
   J36 from install to published data in two workspaces on generated-a and generated-b beside the
   starter's default workspace, naming no key (D56, cases below).
2. **M5's surfaces in the gates** (D57); the changed baselines re-recorded after you review them.
3. **The fixes** D58 and D59, each with its regression test.
4. **The backend groups together** (D60) and the alpha's migration check (D61).
5. **The interim release** 0.11.0-alpha.1 (D12, D61): CHANGELOG section, version strings,
   PROJECT_STATUS, TODO; the commit and the tag `v0.11.0-alpha.1` on your instruction.

No behaviour changes are planned beyond D58. A defect found is fixed in M6 with its regression test
when it is local; one that changes what V1 or X1 build on becomes an amendment (M6a) before the
release, with your agreement (D62).

**Decisions** (D56 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D56 | What the composed journey walks, and how | **One runner: the default workspace stays on the starter; generated-a and generated-b each go into a new workspace; the walk done once by keyboard alone and once by clicking, as T1's D60.** What: drafts of A and B are made through the API (no screen turns a JSON model into a draft; M5 did the same), then everything else is on screen: each draft installed from the editor into a new workspace (Activate into › a new workspace); in each workspace a root record and a child under it created on the record screen, a value edited, a change set opened, a record changed in it and published; the switcher moving between three workspaces on three models, each showing only its own applications and records; a second release of A (one attribute added) activated into A's workspace from Settings › Model while a change set is open there, which the dialog lists as left behind, the new field shown in A's record form and B's and the default's unchanged. A's workspace by keyboard alone and B's by clicking, then the second release by the other way round, so every step is taken both ways. Throughout, the runner fails on a console error, an `Error:` text, or a 4xx/5xx response other than the expected refusal (T1's lesson: earlier runners passed while the console showed a wrong read), and checks that every model read the page makes answers the release of the one workspace it names (`X-Model-Release-Id`): the browser half of "no request combining their snapshots". Why: it is the roadmap's exit item composed end to end, which no package walked. Cost: one runner, about 2–3 minutes |
| D56a | J36.5 in the browser | **Inside the same runner: a second tab has A's record open for editing when the second release is activated into A; its Save is refused with a readable message (`MODEL_RELEASE_CHANGED`), the record unchanged after a reload, and a Save in B's workspace at the same time commits.** Why: the commit guard per workspace has never been seen by a user; the message must be readable. Cost: a second page in the runner |
| D57 | M5's surfaces into the gates | **Into the accessibility gate light and dark, into the visual gate light, dark for the switcher and the overview,** through one helper `e2e/helpers/workspace-surfaces.mjs` visited by both gates, as `designer-surfaces` is: the switcher open with its marks, the D48 page, the unknown-workspace page, Settings › Model's overview, the activation dialog (fits; a migration is needed), the new-workspace dialog with Model, the install dialog's Activate into a new workspace, Settings › Workspaces' detail naming the model (about 9 surfaces, 18 accessibility scenarios, 11 baselines). Settings › Model's existing baselines are re-recorded only after you have seen the differences. Why: the alpha should not carry unchecked surfaces into V and X, as T1 decided for 0.10. Cost: the two gates run once each (about 3 minutes each, announced) |
| D58 | M5's two small findings | **Fixed in M6:** on the D48 page the rail marks no collection as current; a switch reads the rail's collections once, after the model arrives. Each with a Vitest regression seen failing first. Why: TODO marked them for M6, and the composed walk's request check (D56) would flag the double read as noise. Cost: small, in `useRouter`/the rail |
| D59 | The two failing or order-bound backend tests | **Fixed before the alpha.** The cycle: `runs_dry_run` and `NO_DRY_RUN` move from `draft_profile` to `dry_run`, which `draft_profile` already imports, so the deferred import goes and `test_tiers_hold` passes. The order-bound test: it installs its own candidate after the bootstrap release, so it compares two releases alone as it does after its module's earlier tests. Why: D60 runs `contract` and `model_admin`, and an alpha should not be accepted over a known red test. Cost: one function moved; one test's setup |
| D60 | Which backend checks | **`workspace_models`, `model`, `model_admin`, `contract` and `startup` in one run, parallel and serial parts; no full suite** (R). Within the 2-minute ceiling or reported with its time; announced if it looks longer (M5's `contract` + `workspace_models` took 1 min 45 s) |
| D61 | The alpha's migration check | **As T1's D63: the `startup` group, then once by hand: the tagged 0.10.0 code in a scratch worktree builds a scratch database with records, an open change set and a draft; the head upgrades it; the default workspace keeps its release, the change set and draft survive, a second workspace is created on another model, and the server restarts cleanly; a smoke start on a copy of the development database.** Worktree and scratch databases removed after. Versions written `0.11.0-alpha.1` in the three files. Why: `20261018_01` has been upgraded only from the head's own baseline, not from a database 0.10.0 built. Cost: one manual block |
| D62 | When M6 passes, and what a failure does | **M6 passes when the composed runner, the gates and the backend groups pass and you approve the screenshots and baseline differences; then the release steps run, commit and tag on your instruction.** A local defect is fixed in M6 with its regression test; one that changes what V1 or X1 build on becomes M6a with your agreement. A runner flake seen once is rerun once and recorded in TODO; seen twice it is a defect |

**Journey test cases** (browser, `test:browser:workspace-m6`; generated-a and generated-b beside the
starter, naming no key; types and applications read from each model):

1. **J36.1 + J36.4 + J36.6, two new workspaces from the editor.** Given drafts of A and B. When each
   is installed from the editor into a new workspace (A by keyboard alone, B by clicking), then each
   opens on its own model's applications, the default workspace still runs the starter, and an
   address of A's application opened in B's workspace shows the D48 page.
2. **J36.3, work in each workspace.** When a root record and a child under it are created on the
   record screen in A's workspace and in B's, a value edited, and a change set opened, a record
   changed and published in each, then each workspace's collections, record pages and publication
   list show only its own records, under its own model's labels, and the switcher moves between the
   three with the applications following.
3. **J36.2, a new release of one workspace's model.** Given a change set open in A's workspace. When
   a second release of A (one attribute added) is activated into A's workspace from its row in
   Settings › Model (by clicking; the keyboard walk on the other half), then the dialog lists the
   change set as left behind and names B's and the default workspace as not changed; A's record form
   shows the new field; B's and the default's do not.
4. **J36.5, a write when the release changed meanwhile** (D56a). *Moved to [M6a](#m6a-a-write-names-the-release-it-was-built-on)
   by the user (2026-10-16): the browser does not name the release its form came from, so a stale
   tab's save is checked against the new release and commits; the refusal needs M6a.* Given A's record open for editing
   in a second tab before case 3's activation. When it is saved after the activation, then the save
   is refused with a readable message, nothing saved; a save in B's workspace at the same moment
   commits.
5. **No combined snapshot, no error.** Across the walk, every model read answers the release of the
   workspace it names; no console error, no `Error:` text, no 4xx/5xx beyond case 4's refusal.
6. **390px.** In B's workspace at 390px: switch from the band, create a record, open the Settings ›
   Model overview; no sideways scroll on any screen of the walk.

These should pass on the first run if M1–M5 are right, since M6 changes no behaviour outside D58;
they cannot be seen failing first, which the record will say. D58's and D59's regressions are seen
failing before their fixes.

**Groups:** `workspace_models`, `model`, `model_admin`, `contract`, `startup`;
`test:browser:workspace-m6`; `test:a11y` and `test:visual` extended (D57), each announced; Vitest on
the files D58 changes; `npm run format`, `lint`, `build`. **Not run:** the full suites and the other
browser runners (R).

**Composable domains (ADR-032):** no contract changes; no door is affected.

##### M6 record (2026-10-16)

**Delivered 2026-10-16 and released as 0.11.0-alpha.1 (D12) on 2026-10-17:** the user approved the
baselines by asking for the commit (`07cd453`) and asked for the release ("you can do it"). Version
strings `0.11.0-alpha.1` in `backend/pyproject.toml`, `ENGINE_VERSION` and `frontend/package.json`
(with its lock); the OpenAPI lock re-baselined for `info.version` alone (with 0.10.0 the document
hashes to the previous lock exactly); the CHANGELOG section; the tag `v0.11.0-alpha.1`. Built as planned (D56–D62), with M6a added by the user for
case 4. Found and fixed on the way:

- **The header's product name followed the workspace's model** (from M5): every model declares its
  own `product.name`, so the top bar changed on a switch. The user: it stands for the instance's name
  and logo. It now reads the default workspace's model (`app/instanceProduct.ts`); regression in
  `App.test`, seen failing.
- **On a phone, tapping a workspace in the band's switcher did nothing** (since 0.10 N1; M5's runner
  only opened the list): the band's popover closed on the option's press, since the list is a React
  Aria popover of its own. `ui/ControlPopover` treats a press in a popover layered over the page as
  inside; regression in `ControlPopover.test`, seen failing; found by the runner's 390px case.
- **D58** (M5's TODO): the D48 page marks no rail entry current (`AppShell`'s `nothingCurrent`); a
  switch no longer reloads the old workspace's rail before the new one mounts. Two `App.test` cases,
  seen failing.
- **D59:** `runs_dry_run` and `NO_DRY_RUN` moved into `sources/dry_run.py`, so `test_tiers_hold`
  passes; the lifecycle diff test installs its candidate after the app's bootstrap, so it passes alone.
- **Settings › Model reworked at the user's request in several rounds** (columns, a catalogue of
  every release, a page per model, a card concept), each rejected in use. It is left laid out as
  Settings › Workspaces (models in the list, the default workspace's first; the selected model's card
  with Running in and Change model…, releases with the workspaces running each, drafts with how far
  behind), and the user judged it still not good: the redesign is recorded for 0.14 (TODO, with what
  was tried and asked for). "Activate a release…" is now "Change model…", its dialog grouped by model
  with the workspace's own first and nothing preselected in another model; rows and cards open on a
  click anywhere (`ui/OpenableRow`); `formatServerDate` for dates without a time.
- The runners' shared keyboard-or-click helper and error watch moved from `authoring-t1-designer.mjs`
  into `e2e/helpers/person.mjs` (one copy); its `tabTo` finds its target again each step, since a
  combo box's list hides the page and a dialog re-renders its buttons.

**Where it differs from the plan:** case 4 is M6a's (the user's choice). D57's surfaces gained the
model card, the second workspace's shell (the open switcher is in the visual gate only: an open
React Aria list hides the page, so page-level landmark rules do not apply) and Settings ›
Workspaces' detail; 20 accessibility scenarios, 13 visual baselines.

**Checks:**

- `test:browser:workspace-m6` (new): 6 cases passed (about 25 s), generated-a by keyboard alone and
  generated-b by clicking beside the starter; 37 model reads each answering its workspace's release;
  no console error, `Error:` text or unexpected 4xx/5xx; 390px without sideways scroll. The cases
  passed once the defects above were fixed; before, case 4 (no refusal; M6a) and case 6 (the phone
  switch) failed. `test:browser:workspace-m5`: 6 cases passed after its steps moved to the model card.
- Backend `workspace_models`, `model`, `model_admin`, `contract`, `startup` in one parallel run:
  4,061 passed and 2 failed in 2 min 19 s, over the 2-minute ceiling (load normal); the failures were
  M6a's header missing from API_JOURNEYS and the OpenAPI lock, both fixed (the lock re-baselined after
  diffing the default document against `52cce04`: the header on 100 operations, nothing else), their
  files then 14 passed; the serial part selects none. `ruff check app/ tests/`: clean.
- Frontend: `tsc`; Vitest on the changed areas 372 passed in 45 files; `npm run format`, `npm run
  lint` (0 errors, the 7 listed warnings), `npm run build`.
- `test:a11y`: a first run stopped in 0.10's spreadsheet surfaces (the dry run's figure not shown)
  while the machine's load averaged about 17, before the new section; rerun once (D62): 193 checks,
  no violations, 4 min 25 s. Recorded in TODO as seen once.
- `test:visual`: 156 checks; 52 baselines differ, all explained by committed or approved changes
  (`6cd6404`'s one top bar on Settings and the editor, M5's model line under the switcher, its install
  dialog, Settings › Workspaces and a release's page, M6's Settings › Model) and 13 are new. The
  update run's other 90 rewrites were restored. Approved by the user with the commit.
- **Migration (D61)**, by hand: the `v0.10.0` code in a scratch worktree built a scratch database
  with a record, an open change set and a draft; the head upgraded it to `20261018_01` and kept all
  three, the default workspace on its release; a second workspace was created on another installed
  model; a restart was clean. Worktree and database removed. Smoke: the development database is at
  `20261018_01`, served by the user's development server on the head code throughout the package.

**Not run:** the full suites and the other browser runners (R); `u3-settings` and
`authoring-t1-designer` were changed (the back label; the helper moved) and syntax-checked only.
**What the user cannot do yet:** migrate a workspace's data to a release it does not fit (V1),
move change sets left behind (V3), move data between models (Track X); Settings › Model's redesign
(0.14).

#### M6a: A write names the release it was built on

**Added by the user 2026-10-16** during M6, when case 4 (D56a) was found unable to pass. **Needs:**
M5. Delivered before M6's release steps; M6's case 4 runs on it.

**Why:** `MODEL_RELEASE_CHANGED` guards one request against an activation that commits while it runs
(`registry.py`'s commit guard). Nothing guards a client that read the model, waited, and writes after
the activation: the browser sends no release, so a tab opened before the activation saves under the
new release with a form built from the old one. Today that is harmless when the field is in both
releases and a validation refusal when it is not; either way the user is never told the model changed.

##### M6a plan (2026-10-16)

**Planned 2026-10-16; D63–D67 and the test cases accepted by the user the same day ("Accept").** Checked against
the code at `52cce04`:

- Every live request resolves its workspace's release once, in `registry.resolve_model_snapshot`
  (it records it for the commit guard); a change set's or publication's request resolves its pinned
  release through `resolve_pinned_release`. Responses name the release in `X-Model-Release-Id`
  (`GET /model`, the metadata reads).
- The browser keeps one model per workspace (`model/workspaceModels.ts`, M5) without its release
  ID; writes go through `api` in `api/client.ts` and, in a change set, `createChangeSetClient`.
  Nothing in `frontend/src` sends or reads a release ID on a data write.
- `ui/Toast` takes actions (buttons), so the Reload needs no new component.

**Decisions** (D63 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D63 | How a client names the release it built a request on | **An optional request header `X-Expected-Model-Release-Id: <release ID>`**, the request twin of the `X-Model-Release-Id` response header a client already reads. Without it nothing changes, so no integration breaks. Why a header and not a body field: it applies to every route the same way, as `Idempotency-Key` does, and needs no change to any request body. Cost: the header documented once in API.md and declared on the routes that take it (OpenAPI lock re-baselined) |
| D64 | What the server does with it | **Checked where the request resolves its release, before anything is read or written: when the release it resolves (the workspace's own for live data, the change set's or publication's pinned release in one) is not the one named, `409 MODEL_RELEASE_CHANGED`**, the same code a client already handles for the race, with `details` `{workspaceKey, expectedReleaseId, currentReleaseId}` and `changeSetId` in a change set, and a message saying nothing was saved and to reload. Any method: a read naming a release that is no longer current is refused the same way, which an integration may want; the browser sends it on writes only (D65). A request naming a release but resolving none (a route over no workspace) ignores it. Cost: one check in the two resolution functions, fed by a request dependency |
| D65 | What the browser sends | **Every write over a workspace's data sends the release the page's model came from:** record, relation and value writes, moves and deletes, live and in a change set, batches, imports and bulk changes. The tab keeps each workspace's release ID with its model (read from `X-Model-Release-Id` with it) and a change set's pinned release with the change set. Reads, Settings and model administration send nothing (activation already carries `expectedReleaseId`). Why: the form a user saves was built from that release; that is the claim to check. Cost: the client's write helpers take the context's release; their Vitest |
| D66 | What the user sees when it is refused | **The refusal in place, as any refusal is (input kept), and a toast: "‹Workspace› now runs ‹model› ‹version›. Nothing was saved." with Reload,** which reloads that workspace's model and the page. Why: the form's own message says what failed; the toast offers the one safe recovery once, wherever the save was made from. Cost: one handler where writes fail (`errorMessage` stays the renderer) |
| D67 | Where it is tested | **A journey variant J36.9, "a write built on a release the workspace no longer runs"**, through the API on two configurations (cases 1–4 below), M6's browser case 4, and Vitest for the client sending the header on writes and not on reads, and for the toast. The race variant J36.5 is unchanged |

**Journey test cases** (`tests/journeys/test_j36_expected_release.py`, `workspace_models`; X beside Y,
both directions, naming no key):

1. **J36.9 live.** Given an R read under X1 in the default workspace, X2 activated into it since.
   When the R is updated naming X1, then `409 MODEL_RELEASE_CHANGED` with the workspace, X1 and X2,
   and the R unchanged; when updated naming X2, it saves.
2. **J36.9 in a change set.** Given a change set pinned to X1 and moved to X2 since. When a record is
   changed in it naming X1, then refused the same way with the change set named, nothing saved in it.
3. **J36.9, the other workspace.** Given the same activation. When a record in Y's workspace is
   created naming Y's release, it commits; naming X2 there, it is refused (another workspace's release).
4. **Without the header.** The same stale write without the header saves under X2, as today: the
   header is optional and nothing else changed.

Browser (M6's runner, case 4): a tab opened before the activation saves; the field shows the refusal,
the toast offers Reload, the record is unchanged on the server; after Reload the save succeeds; a save
in B's workspace at the same moment commits.

**Groups:** `workspace_models`, `contract` (the header on the routes; the lock re-baselined after
diffing); Vitest on `api`, `app` and the record forms the client change touches; `npm run format`,
`lint`, `build`. **Composable domains (ADR-032):** no door is affected (no identity, storage, audit,
bulk-shape or `match` change; the bulk APIs gain the same optional header).

##### M6a record (2026-10-16)

**Delivered 2026-10-16.** Built as planned (D63–D67): `engine/model/expected_release.py` keeps the
named release on the request's session (`management/dependencies.expect_model_release`, on every
management router) and checks it where a request's own context is fixed: `LiveWrites` (the
workspace's current release, under its lock), `ChangeSetWrites` (the pinned release), the batch and
import context (`jobs/batches.open_batch_context`) and a read's request snapshot. The browser keeps
the release a model was served from (`EngineModel.releaseId`, from `X-Model-Release-Id`), its data
provider names the page's context's release (`api/expectedRelease.ts`), the client sends it on record,
relation, value, batch, import and type-change writes only, and the shell's toast offers Reload.
**Where it differs:** the API had to expose `X-Model-Release-Id` to browsers on other origins (CORS
`expose_headers`), found when M6's runner saw the stale save succeed: without it the browser never
had a release to name. The header's parameter is named apart from routes' `release_id`.

**Checks:** `test_j36_expected_release.py`, 4 cases × 2 configurations written first: 6 failed (no
refusal), the 2 "without the header" cases passed as they must; then 8 passed. Vitest: `client.test`
(the header on writes only, the refusal reported, the release kept), `App.test` (the toast's text).
M6's case 4 in the browser. The backend groups and contract as in M6's record.

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

##### V1 plan (2026-10-17)

**Planned 2026-10-17; D68–D78 and the test cases accepted by the user the same day (D70 in V1,
after its explanation: "ok, go ahead").** Checked against the
code at `0b08e9c`:

- **The compatibility analysis counts, it does not list.** `analyze_compatibility`
  (`engine/model/compatibility.py`) compares the workspace's release with a candidate and returns 19
  kinds of diagnostic, each a count at a model pointer, scoped to one workspace (M1). Nothing names
  the records behind a count, and it checks only what the candidate changes. It never checks data
  that a migration would have changed, such as a value converted to another type.
- **Activation** (`engine/model/releases.activate_model_release`) refuses any diagnostic with
  `409 MODEL_MIGRATION_REQUIRED`. Otherwise it switches the assignment under its row lock, then
  syncs matrix states, suspends left-behind subscriptions, lists left-behind change sets and writes
  one `activated` audit event. A migration's switch is the same tail.
- **Type changes** (ADR-034, `engine/operations/type_changes.py`) run in change sets only (D38),
  with derived attribute sources (same attribute type, display, unique-and-required) and
  `WIDENINGS = {text→longText, integer→decimal}`. Nothing converts values between other types.
- **Jobs** have a preview stage that waits for confirmation (`jobs/preview.py`, `awaiting_confirmation`,
  `POST /jobs/{id}/confirm`, rows in `job_items` paged by `GET /jobs/{id}/rows`). The kinds are a
  check constraint (`ck_job_kind`), so a new kind needs a migration.
- **The feed is the audit log with positions** (`engine/records/feed.py` `take_positions`): a record
  changed without an audit entry is a change no consumer sees.
- **The UI:** M5's activation dialog says "A migration is needed" with no button, waiting for V1
  (D51). M5's record names V1 as what delivers the migration to users. No mock-up of the preview
  exists: P0's canvas shows only the offer in the dialog.

**What is built:** `POST /workspaces/{key}/model/migrations` starts a `migration` job. The preview
stage applies the migration in a transaction, checks the result against the target release in full,
records every item as a row, and rolls back. `POST /jobs/{id}/confirm` reapplies it under the
workspace's assignment lock and switches the assignment in the same transaction. In the UI, the
activation dialog's "A migration is needed" opens the preview.

**Decisions** (D68 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D68 | What a migration does with each kind of difference | **Three outcomes, fixed per diagnostic.** *Conversion:* a value whose attribute (or relation attribute) changes value type is converted (D69). *Loss* (removed, listed, applied only with `acceptLoss`): records of a type or application the target lacks, with what they contain (unless D70 maps them); values of a removed attribute type or binding; relationships of a removed pair; relation attribute values removed. *Refused* (the migration cannot confirm until the data is fixed): a newly required attribute or relationship missing, `atLeastOneOf`, an effective period, uniqueness (attribute or scoped), bounds, cardinality, a parent now required, a parent relation whose meaning changed. Why: a migration may drop what the target has no place for once you have seen the list, but it never makes up a value or a relationship. Cost: one rule table in the engine |
| D69 | Which value conversions exist | **Done in SQL:** text↔longText; integer→decimal; decimal→integer when the value is whole; any number, boolean or date to text in the API's own format; text to integer, decimal, boolean, date or dateTime when it parses as an import cell does; date→dateTime at midnight UTC; dateTime→date only when the time is midnight UTC; json↔text when it parses. A value that does not convert is a loss item (the value removed), or refused when the target binding is required. Why: these are the lossless or checkable conversions; ADR-034's two widenings stay as they are for type changes. Cost: one SQL conversion per pair, unit-tested pair by pair |
| D70 | Types the target lacks: delete only, or map | **The request may map types:** `typeMappings: [{ fromObjectTypeKey, toObjectTypeKey, attributes: [{ attributeTypeKey, from }] }]`. Mapped records keep their ID and history (reclassified). Attribute sources follow ADR-034's derived rules unless named, so a renamed type or attribute is carried instead of lost. A mapped record must still have a valid place (its parent's type may contain the new type, or it may stand at the top); otherwise it is refused, with no cascade into descendants in V1. A type the target keeps maps to itself, and `attributes` there carries a renamed attribute. Why: a release that renames a type would otherwise delete every record of it. Cost: the largest part of V1; X1's saved mapping can later be named instead of an inline one |
| D71 | Live data, although ADR-034 restricts type changes to change sets | **The migration writes live data in one transaction, bound to the confirmed preview.** ADR-034's D38 gains one exception: in a migration, the confirmed preview stands in for the change set's review. Why: the plan's scope and API design (accepted in P0) switch data and assignment together, and a change set cannot hold a model switch. Cost: an amendment note in ADR-034 |
| D72 | Is the preview a sample or every item | **Amended 2026-10-18** (the user, after the 100,000-record run: "finish it"): the migrated data is checked against the rules new or changed in the target and those over what the migration changed, every record each covers; an unchanged rule over untouched data is not checked again. **Every item**, as D67's dry run: one row per affected record (or relationship) and difference, with the before value and, for a conversion, the after value. Refusals come from checking the migrated data in full against the target release. The analysis gains a listing form with the same predicates, which writes IDs into job rows instead of counting them, run against an empty model so every target rule is checked. Why: "nothing dropped silently" and checks over the whole set. Cost: the listing form of the 19 predicates; rows can number hundreds of thousands, paged under ADR-030 |
| D73 | What consumers and history see | **Every changed record gets its audit entry, written as a set statement at the target release:** `updated` for converted or removed values, `reclassified` with the full before state for a mapped type, `deleted` for a lost record, and `deleted` for a lost relationship. One `migrated` event on the workspace's model names the job, both releases and the counts. Why: the feed is the audit log, so consumers see the changes, and record history keeps what was removed. Cost: positions for every entry in one `take_positions` call |
| D74 | What the confirmation binds | **As designed in P0:** `expectedVersion` (the assignment) and `expectedFeedPosition` (the workspace's live feed), read by the preview and returned in its summary. Either moved → `409 MIGRATION_REVIEW_STALE`. A preview with refusals → `409 MIGRATION_HAS_REFUSALS` (new), and loss without `acceptLoss: true` → `422 MIGRATION_LOSS_NOT_ACCEPTED`. On confirm the engine recomputes the plan in the write transaction and refuses when it differs from the preview's digest, as ADR-034 does. Why: what is applied is exactly what was reviewed. Cost: one new code |
| D75 | Gates and the other workspaces | **`MODEL_ADMIN_MUTATIONS_ENABLED` and `INTEGRATION_JOBS_ENABLED` (D14).** Writes in other workspaces are never held up, except while unique values are refilled (activation's R-F2 lock). Change sets left behind and subscriptions are handled as by activation (D26). Publications stay pinned to the old release, unchanged. Why: the same tail as activation, so no second rule. Cost: none beyond reuse |
| D76 | The UI | **In V1, on a mock-up you approve first** (delivery step 3). "Preview migration…" in the activation dialog opens one screen with the counts by kind and the rows by tab (conversion, loss, refused), each paged, plus Accept loss and Confirm, and Cancel. Why: M5 promised this to V1, and without it the dialog stays a dead end. Cost: a mock-up round, a browser runner `test:browser:workspace-v1`, and gate scenarios |
| D77 | The test configurations | **A target release derived from each configuration in the test,** naming no key: pick a type with records and remove or rename it, change an attribute's value type, add a required attribute. Run X beside Y in both directions, as in M6a. Why: journeys test the engine on two models. Cost: one helper in `tests/journeys/` |
| D78 | Volume | **Measured once, announced:** a workspace of 100,000 records migrating one value-type change and one removed type, preview and confirm. Run in the volume group with `budget`, never by default. Why: set statements must stay set statements. Cost: one budget test |

**Journey test cases** (`tests/journeys/test_j37_workspace_migration.py`, `migration` and
`workspace_models`; X beside Y, both directions, naming no key; X2 derived from X per D77):

1. **J37.1 Preview.** Given workspace W on X1 with records, and X2 that changes a text attribute to
   integer (some values parse, one does not), removes a binding with values and removes a type with
   records. When a migration to X2 is started, then the job waits for confirmation. Its summary
   counts conversions, losses and no refusals. Its rows list each item with the record, the before
   and after values. W's records, release and feed position are unchanged.
2. **J37.2 Confirm with loss.** Given that preview, a confirmation without `acceptLoss` gets
   `422 MIGRATION_LOSS_NOT_ACCEPTED`. With it, W runs X2, converted values read as integers, the
   removed values and records are gone, W's feed has an entry for each changed record, and record
   history shows what was removed. The workspace on Y is unchanged (release, records, feed).
3. **J37.2 with a type mapping.** Given X2 renames a type, a preview without `typeMappings` lists its
   records as loss. With the mapping, the preview lists them as reclassified. After confirming they
   keep their IDs under the new type with their values.
4. **J37.3 Cancel.** Cancelling the waiting preview changes nothing. A confirmation afterwards gets
   `409 JOB_NOT_AWAITING_CONFIRMATION`.
5. **J37.4 Stale.** A record written in W after the preview, or an activation into W, makes the
   confirmation `409 MIGRATION_REVIEW_STALE`, with nothing changed. A write in the Y workspace does
   not make it stale.
6. **Refusals.** Given X2 adds a required attribute W's records lack, the preview's rows are refused
   with the records named, and confirming gets `409 MIGRATION_HAS_REFUSALS`. After the values are
   filled, a new preview confirms.
7. **J37.5 A failed execution.** The confirmation fails at its last statement (injected at the
   execution boundary, since no client can make a confirmed migration fail; stated in the test). The
   job is `failed` with an actionable error, and W's records, release and feed are unchanged.

Unit tests: the conversion pairs of D69 (property-based over values), the rule table of D68.

**Groups:** `migration` (new marker, registered), `workspace_models`, `jobs`, `change_sets`,
`startup` (the `ck_job_kind` migration: bootstrap, upgrade from `20261017_01`, interrupted),
`contract` (the route, the lock re-baselined after diffing); Vitest for the screen; the new runner on
two models at 1440px and 390px with keyboard; the budget once (D78), announced.

**Composable domains (ADR-032):** identity is unaffected (a mapped record keeps its ID). Audit and
history: every change is recorded with its before state, so no door closes. Bulk APIs: the migration
is a job with item outcomes, as 0.9's.

##### V1 record (in progress, 2026-10-17)

**Delivered 2026-10-18.** API, screen, gates and the budget done; the stored baselines are for the
user to look at (below). The budget (D78), measured once after the narrowed check: a workspace of
100,000 records (10,000 groups, the node hierarchy, the matrix's records) to a release turning every
rank into a decimal and dropping the node type: **preview 65.6 s, execution 110.8 s**, 257,504
values converted, 254 items removed, nothing refused; the workspace on the target afterwards.

**Closed in V1 too (2026-10-18, the user: "close everything which is V1 now"):** the scoped
uniqueness count, shared with activation, rewritten to climb from the rule's targets to the first
ancestor of the scope's type instead of walking every record to its root: a check of every rule of
the target over the 100,000-record workspace takes **5.8 s** (it ran over 9 minutes); measured in
`test_migration_budget`, rerun once (preview 64.6 s, execution 116.9 s). A migration's long steps
renew the worker's lease between their statements from a session of their own and stop when another
worker holds the job (unit-tested). Checks: `test_model_compatibility` and the migration unit
module (36, then the lease case: 19 unit), J37, J24, the groups `migration or workspace_models or
model_admin or model or contract` (3,932 passed, 1 min 47 s), Ruff.

**2026-10-18, the screen and the budget.** The user's "go ahead" taken as approval of the mock-up and
of D78's run.

- **Screen (D76):** `features/model-admin/MigrationPage.tsx` at `/settings/model/migrations/{jobId}`
  in Settings › Model, on the approved board: what the release no longer has with a choice per
  missing type and field (each choice cancels the waiting preview and starts another with the type
  mappings), the four outcome buttons with counts, the items of one outcome in `DataTable` with
  `useCursorWindow`, refusals in words ("Empty, and required in ‹version›"), the bar (Accept the
  loss, Cancel, Migrate), the previewing, refused, cancelled, failed and done states and the stale
  alert dialog. The activation dialog's **Preview the migration…** where model administration and
  background jobs run (it says why not otherwise). Types, routes, client calls; `jobText` names the
  newer job kinds. UI_ACCEPTANCE row V1-1; `test:browser:workspace-v1`; V1's two surfaces added to
  the gates' `workspace-surfaces.mjs` (`migration-preview`, dark too; `migration-stale-dialog`).
- **Found on the way and fixed:** the migration did not check the consumer contract as activation
  does (D75): a target changing what a consumer API's consumers read without a new contract version
  is now refused at the start, `409 CONSUMER_CONTRACT_VERSION_REQUIRED` (unit-tested). At full size
  the update of the migrated records ran for minutes: it tested each record against a set inside an
  `OR`, which PostgreSQL ran as a subplan per row once the set outgrew `work_mem`; the records the
  migration changes are now marked once in its table and the update joins on the mark, and the
  migration's tables are analysed after they are filled (R-F19's lesson). Measured after the fix at
  10,000 and 20,000 records: the update 1.1 s and 1.9 s, every statement in step with the size. The
  first full-size attempt also ran two workers on one job (the test called the worker beside the
  application's thread): a step longer than the lease lets another worker take the job over, which
  matters with several workers (N2, TODO).

**The final check narrowed (2026-10-18, D72 amended).** The 100,000-record run stopped in the check
of the migrated data: the scoped-uniqueness rule's walk of every record's ancestors took 0.6 s at
20,000 records and over 9 minutes at 100,000. Asked whether V1 was still open, the user said to
finish it; the check now covers the rules new or changed in the target and the rules over what the
migration changed (`migrations.Touched`, `relaxed(target, current, touched)`), every record each
covers; an unchanged rule over untouched data was checked when that data was written. Unit-tested
(`test_only_rules_that_changed_or_cover_what_the_migration_touched_are_checked`). The gates' V1
baselines (`migration-preview-light`, `-dark`, `migration-stale-dialog-light`) and the intended
change of `activate-migration-needed-dialog-light` (Preview the migration… shown, 3.14%) were stored
on the same instruction, for the user to look at afterwards. The accessibility gate passed (every
surface, 0 unexpected violations, 4 min 41 s); the visual gate's only other differences are four
screens V1 does not touch at 0.50–0.54%, two of them flipping between runs (TODO's flake). The
gates' V1 setup runs after the other surfaces, so their catalogues show the models they always did.

**Checks (2026-10-18):** `test:browser:workspace-v1` 5 cases passed on generated-a and generated-b
(keyboard for the preview, the acceptance and the confirmation; axe on the page and the stale dialog;
390px), screenshots inspected light and dark: they follow the board; fixed on the way, the bar under
the table's sticky header, a lone option stretched to its card's height, the done page's preview
text, the Migrate button not wrapping at 390px, the alert dialog's second Close. Vitest:
`MigrationPage.test` (4), `ActivateDialog.test` (2), `routes.test`, model-admin, routing and jobs
folders: 107 passed. `npm run format`, `lint` (0 errors; the 7 warnings are elsewhere), `build`.
Backend after the fixes: J37 and the unit module 31 passed (the contract case added: 17 unit cases),
`test_openapi_contract`, `test_api_journeys`, `test_boundaries` 17 passed, Ruff. The budget at
10,000 records: preview 4.2 s, execution 10–19 s (one run under load), 26,116 conversions; at 20,000:
preview 9–11 s, execution 18–20 s. **Not run yet (each needs a go-ahead):** the full-size budget
(100,000 records) and the accessibility and visual gates with V1's surfaces, where one baseline
changes as intended (`activate-migration-needed-dialog` now shows Preview the migration…).

- **Mock-up (D76):** two boards added to the [P0 canvas](https://claude.ai/artifact/EiSQmSGwdGjCf2y21Cv4L9),
  row "V1": the migration preview at 1440px (what the target no longer has with a choice for each
  missing type and field, the four outcome tabs with their rows paged, accept the loss, confirm,
  and the previewing, refused, stale, cancelled and done states as a tweak) and at 390px; the
  activation dialog's "Preview the migration…" opens it. Awaiting approval.
- **Built (API):** `engine/model/migrations.py` (plan, preview, confirmation, execution, the
  switch); `POST /workspaces/{key}/model/migrations` (registered with model administration and
  background jobs); a job's `migration` summary, `POST /jobs/{id}/confirm`'s optional body, `GET
  /jobs/{id}/rows` for a migration's items; the compatibility analysis's `listing` hook (its counting
  checks select the records they count, D72); `releases.switch_workspace_release`, activation's tail
  shared with the migration; migration `20261019_01` (`migration` job kind, `rdm_convert_value`,
  `ix_job_items_outcome`). `WIDENINGS` moved to `records/values.py` so both readers share it.
- **Where it differs from the design:** the job's summary is `migration`, not `preview` (an
  import's preview is a typed summary of other fields); four codes added: `MIGRATION_HAS_REFUSALS`
  (D74), `INVALID_MIGRATION_MAPPING` (D70), `MIGRATION_TARGET_IS_CURRENT`, `MIGRATION_FAILED`; a
  `reclassified` outcome beside the three designed; relationship types are not mapped (a renamed
  relation type loses its relationships, as listed in the preview); a mapped record whose parent
  can no longer hold it is refused, without the cascade into descendants (D70); the refusals of a
  preview pass through the process to survive its savepoint's rollback, bounded by what must be fixed
  (ARCHITECTURE).
- **Found on the way and fixed:** a migration's preview and execution first cleared the job's lease
  before the worker checked it, so the worker rolled back and ran the step again forever; the lease
  is now checked first.

**Checks so far:** `test_j37_workspace_migration.py`, 7 cases × 2 configurations, written first and
all failing (14, `404` at the route); then 14 passed. Unit `test_migrations.py`: 16 passed (the
conversion table against the import's reading of every text sample, every value to text and back,
the other pairs; the plan's rules and the mapping's pointers; the relaxed target; an executed
migration leaving the matrix cell states true). `test_startup`: the new upgrade case (an
interrupted run rolled back naming the function, two starts, the route answering, a downgrade) and
the M1 case, 2 passed. Groups `migration or workspace_models or model_admin or model or contract`
(3,928 passed, 1 min 40 s; `test_every_error_code_is_listed` failed until API_JOURNEYS listed the
new codes), `change_sets` (474 passed, 2 min 32 s, over the ceiling, TODO), the job journeys and
modules on the confirm and worker paths (J04, J11, J24, J27, J35, `unit/engine/jobs`, cascade
delete, batch statements: 242 passed, J35's 8 failures failing at `0b08e9c` too, TODO), the serial
part (1 passed). OpenAPI lock re-baselined after diffing the default document against `0b08e9c`
(three job routes, `JobResponse`, five new schemas). Smoke start on a copy of the development
database (3 workspaces, 2,380 records): upgraded to `20261019_01`, `/health` and `/system` 200,
every workspace on its release, unique-value rows 15 before and after; the copy dropped.
`test_startup`'s profile-check case fails at `0b08e9c` too (TODO). **Not run yet:** the browser
runner, the gates and Vitest (no screen yet), the budget (D78).

**What the user cannot do yet:** migrate from Settings (the activation dialog still says a migration
is needed; the screen is V1's remaining part); move a change set left on the old release (V3).

#### V2: A change set from a publication moved to another release

**Design:** GAP-02, the roadmap item. **Needs:** V1.

**Scope:** a change set started from a publication, targeted at a named installed release (normally
the historical pin), with V1's preview of incompatibilities and loss, confirmation bound to the
exact reviewed versions, and atomic model and data application for that workspace only.

**Groups:** `migration`, `change_sets`.

##### V2 plan (2026-10-18)

**Planned 2026-10-18; D79–D86 and the test cases accepted by the user the same day ("ok").** Checked against
the code at `989994c`:

- **A change set started from a publication is pinned to that publication's release**
  (`change_sets/lifecycle.create_change_set`), so once the workspace has moved on, the pin is a
  release the workspace no longer runs. Publishing then refuses it,
  `409 CHANGE_SET_MODEL_RELEASE_CONFLICT` (`change_sets/publish.publish_change_set`). The change set
  bar disables Publish and says to change the change set's version "if the content fits" (ADR-028's
  pin change, `pinning.set_change_set_model_release`, which refuses content that does not fit), or
  to discard it. Nothing offers the other direction.
- **V1's migration** (`engine/model/migrations.py`) already moves a workspace's live data to any
  installed release: a preview applied inside a savepoint and rolled back, rows per item, a
  confirmation bound to the assignment version and the feed position, the execution and the switch
  in one transaction. Its job row has a `change_set_id` column (no foreign key, so a publication
  deleting the change set leaves the job intact), unused by migrations.
- **`publish_change_set` commits by itself**, after the merge over live, the whole-graph check,
  the delta, the feed entries and the change set's deletion. A publication inside a migration's
  transaction needs the same steps without the commit.
- **Consumer contracts:** a migration is refused at its start when the target changes what a
  consumer API's consumers read without a higher contract version (V1, D75). Going back to an older
  release lowers a contract version whenever the newer one raised it
  (`CONSUMER_CONTRACT_VERSION_DECREASED`).

**The conflict between the documents (stated before planning, as CLAUDE.md asks).** The P0 API
design lists `POST /change-sets/{changeSetId}/model-migrations` for V2 and V3 and says it "does the
same for one change set's content". The GAP-02 decision (your words in PLANNING_HANDOFF: publishing
"gives a warning … and asks for confirmation of overriding the active scheme with potential data
loss, or cancel the publishing"), the roadmap item ("model replacement targeting one workspace … the
historical pin … atomic model/data application"), ARCHITECTURE ("It migrates current live data toward
that target") and ACCEPTANCE_SCENARIOS SC-13 all say the opposite direction: the **workspace** moves
to the change set's release, and the change set's content stays as it is. Moving the change set's
content is V3. This plan follows GAP-02 (D79) and keeps the P0 route for V3 (D80).

**What is built:** a change set whose pin differs from its workspace's release is published by
migrating the workspace to the pin first, in one confirmed job. `POST /workspaces/{key}/model/migrations`
takes an optional `changeSetId` (with `expectedChangeSetVersion`); the target is then the change
set's release. The preview runs V1's preview and, inside the same rolled-back savepoint, the
change set's merge over the migrated live data, listing what would stop the publication as refused
items. The execution migrates, switches the assignment and publishes the change set in one
transaction. In the UI, the change set bar's notice offers the migration (D85).

**Decisions** (D79 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D79 | What V2 moves | **The workspace's live data to the change set's release, then the change set is published, in one transaction.** The change set's content is not touched. Why: this is GAP-02 as you accepted it, the roadmap item and ARCHITECTURE; publishing in the same transaction is what makes it "confirm or cancel the publishing": a migration that succeeded but whose publication then failed would leave the workspace on the old release without the change set live. Cost: the publication's steps split from its commit (one function both paths call) |
| D80 | The route | **`changeSetId` and `expectedChangeSetVersion` added to V1's `POST /workspaces/{key}/model/migrations`;** `targetReleaseId` becomes optional when a change set is named and, if sent, must be the change set's release (`422 MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`, new). `POST /change-sets/{id}/model-migrations` stays V3's, which moves the change set's content. Why: the route that migrates a workspace stays the one that migrates a workspace; the route under a change set moves the change set. The P0 design put both under one route with one description that fits V3 only. Cost: a P0 API line rewritten; one new code |
| D81 | Which change sets | **Any open change set whose release its workspace no longer runs,** whether started from a publication, from live data under an earlier release, or left behind by an activation. A change set on the workspace's own release is refused with V1's `422 MIGRATION_TARGET_IS_CURRENT` (publish it as usual); a change set of another workspace `404 CHANGE_SET_NOT_FOUND` for this workspace. Why: the mechanism does not depend on how the change set started (generic capability first); the publication case is the common one. Cost: none |
| D82 | What would stop the publication, in the preview | **Refused items, beside V1's:** each record or relationship the change set changed that live data also changed since its base (`CHANGE_SET_CONFLICT`, the publication's `VERSION_CONFLICT` per item) and each rule the merged graph breaks under the target (the whole-graph diagnostics, by code and record). With any, the confirmation is `409 MIGRATION_HAS_REFUSALS`, as in V1. Why: the confirmation must not fail on something the preview could have shown. Cost: the merge's conflicts and diagnostics written as job rows; the merge stays the recorded whole-graph exception (Python), as publishing is today |
| D83 | What the confirmation binds | **V1's `expectedVersion` and `expectedFeedPosition`, plus the change set's version and the workspace's active publication,** read by the preview and returned in its summary (`changeSetId`, `changeSetVersion`, `activePublicationId`). A change set edited, or a publication made, since the preview is `409 MIGRATION_REVIEW_STALE` with the reviewed and current change set version in `details`. Why: what is applied is exactly what was reviewed, and one code says "preview again" for every kind of staleness. Cost: none beyond the fields |
| D84 | Consumer contracts on the way back | **Unchanged: refused at the start** (`409 CONSUMER_CONTRACT_VERSION_REQUIRED`, naming each consumer API), with no flag to accept it. The way out exists today: install a release of the historical model with the contract versions raised, move the change set onto it (ADR-028's pin change: the content fits, as nothing else differs), and migrate to that one. Why: a consumer contract is a promise to integrators that the engine never lowers silently (C-D17); ARCHITECTURE says loss confirmation never waives target-model validity. Cost: none; the refusal's message names the recovery |
| D85 | The UI | **On a mock-up you approve first** (delivery step 3). The change set bar's notice "This change set uses a different model version" gains **Move the workspace to this release…** where model administration and background jobs run (otherwise it says why not). It opens V1's migration page for the new job, which shows one more line ("Then publishes ‹change set›"), lists the publication's refusals with the others, and its done state links the new publication. Why: GAP-02 asks for the warning and confirmation at publishing; one migration page, not a second one. Cost: a board on the P0 canvas, the page's change-set line and refusals, a case in `test:browser:workspace-v1`, the gates' migration surfaces rechecked |
| D86 | Volume | **No budget of its own.** V1's budget measured the migration at 100,000 records; V2 adds the publication's merge, which publishing already runs at that size. Why: nothing new to measure. Cost: none |

**Journey test cases** (`tests/journeys/test_j37_workspace_migration.py`, J37.6, `migration`,
`workspace_models`, `change_sets`; X beside Y, both directions, naming no key; X2 derived from X by
V1's helper). Given in each: workspace W on X1 with records, publication P1; W migrated to X2 (V1)
and written under X2 (a value of the attribute X2 retyped, a value of an attribute only X2 binds);
change set C started from P1 (pinned to X1) with one record changed; publishing C refused
`409 CHANGE_SET_MODEL_RELEASE_CONFLICT`.

1. **J37.6 Preview.** A migration of W naming C waits for confirmation; its summary names C, its
   version and X1 as the target, and counts conversions (X2's values back to X1's type) and losses
   (the attribute X1 lacks). W's release, records and feed and C's version are unchanged.
2. **J37.6 Confirm.** Without `acceptLoss`, `422 MIGRATION_LOSS_NOT_ACCEPTED`. With it, W runs X1,
   C is gone and the next publication (on X1) is the active one, C's change is live, the converted
   values read in X1's type, the lost values are gone, and the feed holds the migration's entries
   followed by the publication's. The workspace on Y is unchanged.
3. **J37.6 Stale.** C edited after the preview: the confirmation is `409 MIGRATION_REVIEW_STALE`,
   nothing changed, and a new preview confirms.
4. **J37.6 Publication refused in the preview.** A record C changed is also changed live after C
   was started: the preview's refused rows name it (`CHANGE_SET_CONFLICT`) and the confirmation is
   `409 MIGRATION_HAS_REFUSALS`, nothing changed.
5. **J37.6 Start refusals.** A target other than C's release, `422
   MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`; a change set on W's own release, `422
   MIGRATION_TARGET_IS_CURRENT`; C named for the Y workspace, `404 CHANGE_SET_NOT_FOUND`.
6. **J37.6 A failed publication.** The execution fails at the publication's last step (injected at
   the execution boundary, as J37.5, stated in the test): the job is `failed` with
   `MIGRATION_FAILED`, W is on X2 with its records and feed unchanged, C still open at its version.

Unit tests: the publication's steps without the commit leave the same state as a publication (one
case over a published change set), the merge's conflicts and diagnostics turned into rows.

**Groups:** `migration`, `workspace_models`, `change_sets` (the publication's split touches its
path; its 2 min 32 s over the ceiling is TODO's), `contract` (the route's new fields and code, the
lock re-baselined after diffing); no migration of the database (the job's kind and `change_set_id`
exist); Vitest for the bar and the page; `test:browser:workspace-v1`'s new case on two models at
1440px and 390px with keyboard.

**Composable domains (ADR-032):** identity is unaffected (records keep their IDs); audit and
history: every migrated and published change has its entry, as in V1 and publishing; bulk APIs: the
same job with item outcomes. No door closes.

##### V2 record (2026-10-18)

**Delivered 2026-10-18.** The API, then the screen on the board (the user, 2026-10-18: "yes please go
ahead", taken as the board's approval and the `change_sets` group's go-ahead).

- **Screen (D85):** the change set bar's notice "This change set uses a different model version"
  offers **Move ‹workspace› to ‹release› and publish…** in `Notice`'s actions slot where model
  administration and background jobs run, and says why not otherwise (`ChangeSetActions`'
  `canMigrate`, `onMigrationStarted`, wired in `App`); it starts the migration naming the change set
  with its version and the assignment's, and opens V1's page. `MigrationPage` reads the change set
  from the job's parameters: the title adds "and publish ‹change set›", a line says it then publishes
  it as the next publication in the same step, a new preview (a choice, Preview again) names the
  change set's current version, the refusals read `CHANGE_SET_CONFLICT` in words and say to fix them
  in the change set or the workspace, the button is **Migrate and publish**, the stale dialog names the
  change set, and the done notice says the change set is live and names the publication's number.
  UI_ACCEPTANCE row V2-1; `test:browser:workspace-v1` case 6.
- **Where it differs from the board:** the offer sits in the notice's action slot (to the right at
  1440px) rather than under its text, as every `Notice` places its actions; the done state names the
  publication without a link (a publications page needs an application, which Settings' page does
  not have).

- **Built (API):** `POST /workspaces/{key}/model/migrations` takes `changeSetId` and
  `expectedChangeSetVersion`, `targetReleaseId` then optional (D80); the start refuses a change set
  of another workspace (`404 CHANGE_SET_NOT_FOUND`), one changed since its version (`409
  CHANGE_SET_VERSION_CONFLICT`), a target other than its release (`422
  MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`, new) and one on the workspace's own release (`422
  MIGRATION_TARGET_IS_CURRENT`). The preview merges the change set over the migrated data in V1's
  savepoint (`change_sets/publish.publication_findings`: the merge collects its conflicts instead of
  refusing) and writes what would stop the publication as refused rows (`migrations.
  publication_refusal_items`: `CHANGE_SET_CONFLICT`, the merge's other codes and the graph's, a
  relationship's row naming `relationId` and its ends). The summary adds `changeSetId`,
  `changeSetVersion`, `activePublicationId` and, executed, `publicationId`. Confirmation and
  execution check the change set's version and the active publication (`MIGRATION_REVIEW_STALE`
  with both versions); the execution claims the change set after the workspace row, migrates,
  switches and publishes through `publish.apply_publication` (`publish_change_set` is now that plus
  its commit) in one transaction. No database migration (the job's kind and `change_set_id`
  existed).
- **Where it differs from the design:** the plan's unit case "the publication's steps without the
  commit leave the same state as a publication" is held instead by the publish journeys J05, J06,
  J17 and J18, which run through the split (48 passed); the unit test covers the findings turned
  into items. In J37.6's stale case the change set's edit after the preview is made on a record the
  first migration did not touch: the record first chosen had been changed live by that migration,
  so the preview rightly refused it as `CHANGE_SET_CONFLICT` (the case as approved is unchanged).
  The consumer-contract refusal of D84 did not arise on the way back in either configuration.
- **Mock-up (D85):** a board added to the [P0 canvas](https://claude.ai/artifact/EiSQmSGwdGjCf2y21Cv4L9),
  row "V1, V2": the change set bar's notice with **Move ‹workspace› to ‹release› and publish…** (and
  the reason when model administration or jobs are off), and the migration page with its
  "Then publishes ‹change set›" line, the publication's refusals, the bar ("Migrate and publish")
  and the done state linking the publication; the 390px page is V1's phone board. Approved
  2026-10-18.

**Checks (2026-10-18), the screen:** `test:browser:workspace-v1` 6 cases passed (case 6 on
generated-a and generated-b: the bar's offer and Migrate and publish by keyboard, axe on the bar and
the page, the workspace on the change set's release and its rename live afterwards); the first run
stopped at the acceptance because the runner had written nothing the way back removes, fixed in the
runner by writing the X2-only value as the journey does. Screenshots inspected light and dark
(`v2-bar`, `v2-preview`, `v2-done`): they follow the board. Vitest: `ChangeSets.test` (2 new),
`MigrationPage.test` (2 new); the model-admin, workspaces and app folders 156 passed. `npm run
format`, `lint` (0 errors; the 7 warnings are elsewhere), `build`. The `change_sets` group: 474
passed, 2 min 21 s (over the 2-minute ceiling as in V1, TODO). **Not run:** the accessibility and
visual gates (build acceptance); V2 adds no surface to them, and the bar's notice shows only for a
change set on another release, which no gate scenario has.

**Checks (2026-10-18), the API:** J37.6 written first, 12 failing at the route (`changeSetId` not
accepted), then 12 passed. Groups `migration or workspace_models or contract`: 146 passed, 43 s
(`test_every_error_code_is_listed` and the lock failed until API_JOURNEYS listed the code and the
lock was re-baselined after diffing the document against `989994c`: only `MigrationSummary`'s four
fields). The publish journeys J05, J06, J17, J18: 48 passed, 54 s. Unit `tests/unit/engine/change_sets`
and `test_migrations.py`: 23 passed. The serial part: 2 passed. Ruff.

**What the user cannot do yet:** move a change set's content onto the release its workspace runs
when the content does not fit (V3); the bar offers changing the version only when it fits.

#### V3: A change set moved onto a release it does not fit

**Design:** ADR-028, the roadmap item. **Needs:** V1.

**Scope:** V1's machinery against the change set's own candidate graph and current live base:
conversions and loss of change-set content previewed; applied only on confirmation of the exact
change set and release versions; never forced, never deleting change-set content to make it fit. A
change set left on a replaced release is moved or thrown away explicitly.

**Groups:** `migration`, `change_sets`.

**Exit:** the roadmap's two exit items on moving a draft.

##### V3 plan (2026-10-18)

**Planned 2026-10-18; D87–D96 as recommended, the test cases and the mock-up accepted by the user the same day ("ok, please build the v3").**
Checked against the code at `68b7700`:

- **A change set holds a base and its own rows.** Its base is a publication's rows
  (`derived_from_publication_id`) or a private capture of live data (`change_set_bases`, copied by
  `snapshot_values.copy_live`); its own rows (`change_set_objects`, `change_set_relations`) are
  what it authored, with tombstones (`is_deleted`). Values are JSON in both, read under the change
  set's release; the typed index (`snapshot_attribute_values`) follows them.
- **Today's pin change** (`pinning.set_change_set_model_release`, `PATCH
  /change-sets/{id}/model-release`) moves a change set only when its whole effective graph already
  fits (`require_change_set_compatible`): a retyped value, a parent relation whose meaning changed
  or a broken rule is `409 CHANGE_SET_CONTENT_INCOMPATIBLE`. It changes no row and keeps the base.
  It is not gated by model administration or jobs.
- **Publishing checks versions against the base.** `_merge_change_set_over_live` refuses a record
  or relationship the change set changed whose live version differs from its base's
  (`VERSION_MISMATCH`, shown as `CHANGE_SET_CONFLICT`), and a touched mapping set whose edges
  differ (`MAPPING_SET_CHANGED`). **V1's migration raises the version of every live record it
  converts**, so a change set left on the old release, even once its pin is moved, would conflict
  on every record it edited that the migration touched: its old base also still holds the old
  release's values.
- **V1's machinery** (`engine/model/migrations.py`): the plan from two models
  (`plan_migration`, type mappings), the conversions in SQL (`rdm_convert_value`), the
  outcomes and rows, the preview in a rolled-back savepoint, confirmation bound to versions, the
  `migration` job kind with its `change_set_id` column (V2). Its fill and apply statements read and
  write the live tables only.
- **The UI:** the change set bar's notice "This change set uses a different model version" offers
  V2's Move ‹workspace› to ‹release› and publish…, and says the change set's version can be changed
  "if the content fits"; the Change model version dialog shows `CHANGE_SET_CONTENT_INCOMPATIBLE`'s
  diagnostics with no way forward.

**The documents, read together (stated before planning, as CLAUDE.md asks).** ADR-028 and API.md
say the review "reports … any potential loss of content authored in the change set" and also that
"a move never deletes change-set content to make a target fit". Read literally the second forbids
the first. This plan reads them as V1's D68 does (D90): content the target has no place for is
listed as loss and removed only when you accept it; a rule the content breaks is refused and never
resolved by removing anything. P0's API line also names `targetReleaseId` freely; D87 narrows it to
the workspace's release in V3, with the reason and the cost of the general case.

**What is built:** `POST /change-sets/{changeSetId}/model-migrations` starts a `migration` job that
moves one change set onto the release its workspace runs. The preview converts the change set's own
rows with V1's plan, replaces its base with a capture of current live data (which already runs the
target), checks the result against the target in full, lists every item as a row, and rolls back.
The confirmation applies it, moves the pin and records it on the change set, in one transaction. Live
data, the workspace's release, its feed and publications are never touched. In the UI, the change set
bar's notice offers **Move this change set to ‹release›…**, which opens V1's migration page for the
job.

**Decisions** (D87 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D87 | Which release a change set moves onto | **The release its workspace runs, only.** That is the case D26 and ADR-028 name ("a change set still on the replaced release is either thrown away or explicitly moved onto the new version"), and the only one after which the change set can publish. Another target is `422 MIGRATION_TARGET_NOT_WORKSPACE_RELEASE` (new); a change set whose content already fits any release keeps using today's pin change. Why: on the workspace's release the new base is live data itself (D88), so publishing afterwards compares like with like. On a release nobody runs yet, the base would have to be a converted copy, and V2's migration later raises the version of every record it converts, so that change set would conflict on exactly the records it was prepared for. Cost of the general case if you want it now: a converted private base and a content comparison in V2's merge, roughly doubling V3; otherwise it waits in TODO |
| D88 | What moves | **The change set's own rows are converted by V1's plan, and its base becomes a capture of current live data.** Values convert by D69's pairs, records of a mapped type are reclassified (D70's `typeMappings`), and what the target has no place for is loss (D90). The old base is dropped (a private one is deleted; a publication stays as it is, and the change set no longer names it). Why: the old base holds the old release's values, so it cannot be read under the target; live data already runs the target and is what publishing merges over. Records the change set did not touch then read as they are live now (for a change set started from a publication: no longer as in that publication). Cost: the conversions written for the change-set tables (JSON rows) beside V1's live-table ones; `copy_live` reused as starting a change set does |
| D89 | When a change the change set made conflicts with live data | **By content, not version:** a record or relationship the change set changed or deleted is refused as `CHANGE_SET_CONFLICT` when its live state differs from its old base state converted by the same plan; a touched mapping set when its live edges differ from its old base's edges carried by the plan. Why: the workspace's own migration raised versions without changing anything the change set did not expect; a version check would refuse every such record, while a live edit made since the base is still caught. Cost: one comparison statement over the change set's rows (a record changed live and changed back no longer counts as a conflict, which today's publish counts) |
| D90 | What "never deletes change-set content to make it fit" means | **V1's three outcomes, unchanged.** *Loss*, listed and removed only with `acceptLoss`: a value of an attribute or binding the target lacks or that does not convert; a record the change set created of a type the target lacks, with what it contains; an edit or deletion of a record live data no longer has; a relationship of a pair the target lacks. *Refused*: every rule the converted graph breaks under the target (required values, uniqueness, bounds, cardinality, a parent the target does not allow) and every conflict of D89, fixed by you in the change set or live, then previewed again. Why: loss is what the target cannot hold, which you see and accept; nothing is ever removed to satisfy a rule. Cost: none beyond V1's rule table. Alternative: refuse all loss too, so you remove such content yourself in the change set first (editing under the old release keeps working, ADR-028) |
| D91 | The route and the job | **As P0 designed it:** `POST /change-sets/{changeSetId}/model-migrations` with `expectedChangeSetVersion`, optional `targetReleaseId` (the workspace's release when left out) and `typeMappings`, answering `202` with a `migration` job naming the change set (`parameters.moves: "changeSet"`). Confirmed by `POST /jobs/{id}/confirm`, rows by `GET /jobs/{id}/rows`, cancel as for any job. Refused before a job exists: `404 CHANGE_SET_NOT_FOUND`, `409 CHANGE_SET_VERSION_CONFLICT`, `409 WORKSPACE_RETIRED`, `422 MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`, `422 MIGRATION_TARGET_IS_CURRENT` (already on it: nothing to move), `422 UNSUPPORTED_SCHEMA_VERSION`, `422 INVALID_MIGRATION_MAPPING`. Why: one job kind and one page for every migration; the job's kind exists, so no database migration. Cost: one new code |
| D92 | What the confirmation binds | **The change set's version, the workspace's assignment version and its feed position,** read by the preview and returned in its summary (`changeSetId`, `changeSetVersion`, `expectedVersion`, `feedPosition`). A change set edited, a live write or an activation in the workspace since the preview is `409 MIGRATION_REVIEW_STALE`. The confirmation body is V1's (`expectedVersion`, `expectedFeedPosition`, `acceptLoss`). Why: the new base is live data, so a live write changes what was reviewed. Cost: in a busy workspace a preview goes stale quickly; the page's Preview again is one click |
| D93 | Gates | **`INTEGRATION_JOBS_ENABLED` only.** The move changes no model and no assignment, so it is not model administration, as today's pin change is not. Why: a change set's owner can move it wherever jobs run. Cost: none |
| D94 | What history and consumers see | **Nothing in the feed** (an unpublished change set is invisible to consumers, D20). One `model-release-changed` event on the change set, as the pin change writes, adding the job's ID and its counts, and the change set's version raised once. Publishing it later writes the ordinary entries. Why: the move is an edit of one change set. Cost: none |
| D95 | The UI | **On a mock-up you approve first** (delivery step 3). The change set bar's notice gains **Move this change set to ‹workspace's release›…** beside V2's offer where background jobs run (otherwise it says why not), and its text says the version can be changed even when the content does not fit. It opens V1's migration page for the job: the title "Move ‹change set› to ‹release›", a line saying live data and the workspace's release stay as they are, the same choices for missing types and fields, outcome tabs and rows, refusals including `CHANGE_SET_CONFLICT` in words, **Accept the loss**, **Move change set**, and a done state with Open the change set. Why: one page for every migration. Cost: a board on the P0 canvas, the page's change-set mode, a case in `test:browser:workspace-v1` on two models at 1440px and 390px by keyboard |
| D96 | Volume | **No budget of its own.** The base capture is starting a change set (measured in 0.9), the conversions run over the change set's own rows with V1's statements, and the whole-graph check is publishing's (the recorded exception). Why: nothing new to measure. Cost: none |

**Journey test cases** (`tests/journeys/test_j37_7_change_set_moved.py`, J37.7, `migration`,
`change_sets`, `workspace_models`; X beside Y, both directions, naming no key; X2 derived from X by
V1's helper). Given in each: workspace W on X1 with records; change set C started from live data
under X1, with a record edited (a value of the attribute X2 retypes, one that converts) and a record
created with a value of the binding X2 removes; W then migrated to X2 (V1); publishing C refused
`409 CHANGE_SET_MODEL_RELEASE_CONFLICT`.

1. **J37.7 Preview.** A move of C waits for confirmation; its summary names C, its version, X1 and
   X2; its rows list the conversion and the loss in C's content. C's rows, version and release,
   and W's records, release and feed are unchanged.
2. **J37.7 Confirm.** Without `acceptLoss`, `422 MIGRATION_LOSS_NOT_ACCEPTED`. With it, C is on X2
   at the next version: the converted value reads in X2's type, the lost value is gone, a record C
   did not touch reads as it is live. W's feed has no new entry. Publishing C then succeeds and its
   edit is live, although the migration had raised that record's version (D89). Y is unchanged.
3. **J37.7 A type mapping.** X2 renames a type C created a record of: without `typeMappings` the
   record is loss; with the mapping it is reclassified, and after confirming keeps its ID under the
   new type with its values.
4. **J37.7 A conflict.** A record C edited is also edited live after the migration: the preview
   refuses it (`CHANGE_SET_CONFLICT`), the confirmation is `409 MIGRATION_HAS_REFUSALS`, nothing
   changed.
5. **J37.7 A rule refused.** X2 adds a required attribute the record C created lacks: the preview
   refuses it with the record named. After the value is filled in C (still on X1), a new preview
   confirms.
6. **J37.7 Stale and cancel.** C edited after the preview, or a live write in W: the confirmation is
   `409 MIGRATION_REVIEW_STALE`, nothing changed. A cancelled preview changes nothing.
7. **J37.7 Start refusals.** A target other than W's release, `422
   MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`; a change set already on W's release, `422
   MIGRATION_TARGET_IS_CURRENT`; a stale `expectedChangeSetVersion`, `409
   CHANGE_SET_VERSION_CONFLICT`.
8. **J37.7 A failed execution.** The execution fails at its last statement (injected at the
   execution boundary, as J37.5, stated in the test): the job is `failed` with `MIGRATION_FAILED`;
   C's rows, base, version and release are unchanged.

Unit tests: D89's comparison (a value converted by the plan only is no conflict; a live edit, a live
deletion and a changed mapping set are), the change-set rows' conversion over D69's pairs.

**Groups:** `migration`, `change_sets` (over its ceiling, TODO's), `workspace_models`, `contract`
(the route and the new code, the lock re-baselined after diffing); the job journeys on the confirm
path; no database migration; Vitest for the bar and the page; `test:browser:workspace-v1`'s new case.

**Composable domains (ADR-032):** identity is unaffected (records keep their IDs, a mapped one too);
audit and history: the change set's own event records the move, publication records the rest; bulk
APIs: the same job with item outcomes. No door closes.

##### V3 record (2026-10-18)

**Delivered 2026-10-18**, the API and the screen on the approved board (the user, 2026-10-18: "ok,
please build the v3", taken as acceptance of D87–D96 as recommended, the test cases, the board and
the groups the plan names).

- **Built (API):** `engine/model/change_set_migrations.py`: the submission (`POST
  /change-sets/{changeSetId}/model-migrations`, `ChangeSetMigrationRequest`, registered with
  background jobs in `change_sets.migration_router`), the preview, the execution and the change set's
  `model-release-changed` event; the worker hands a `migration` job with `parameters.moves:
  "changeSet"` to it (`migrations.moves_change_set`). From V1's module, made public for it:
  `load_plan` (the plan's tables, now with `migration_value_types` among them), `insert_rows`,
  `installed_release`, `record_summary`, `COUNTS`, `require_reviewed`, whose release check reads the
  target for a move. `snapshot_values.reindex_change_set` rebuilds a change set's typed index from
  its rows' JSON in two set statements, as the flush hook would. No database migration (the job kind
  and its `change_set_id` existed). One new code, `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`.
- **Built (screen, D95):** the change set bar's notice offers **Move this change set to
  ‹release›…** (primary) beside V2's offer (now secondary) where background jobs run, and says why
  either is missing (`ChangeSetActions`' `canMove`, `App`). `MigrationPage` reads `moves` from the
  job: the title "Move ‹change set› to ‹release›", the description naming the change set's release
  and saying live data, the workspace's release and its publications stay as they are, the change
  set's release as the current model for what the target no longer has, the columns "In the change
  set" and "After the move", the refusals `MAPPING_SET_CHANGED` and `MISSING_REQUIRED_ATTRIBUTES` in
  words, the acceptance "removed from ‹change set›. Nothing live is removed", **Move change set**,
  the stale dialog naming the change set, and the done notice with **Open the change set**, which
  opens its review in the application last used there (`SettingsArea`, `ModelWorkbench`). The
  shell's model is not reloaded after a move: the workspace's release did not change. UI_ACCEPTANCE
  row V3-1.
- **Where it differs from the design:** the record the change set created without a value the
  target requires is refused by the change set's own validation, `MISSING_REQUIRED_ATTRIBUTES`, not
  V1's `REQUIRED_ATTRIBUTE_MISSING`; the approved case says only that the record is named, and its
  test names the code it gets. A relationship set conflicts when its edge IDs differ (an edge added
  or removed live); a changed attribute of an edge counts only for edges the change set changed,
  through the relationship's own comparison. A deletion the change set made of something live data
  no longer holds is dropped from it. The change set's relationship-set versions follow the target's
  type keys and are dropped with a pair the target lacks. The execution holds the workspace row in
  share mode and the change set row, not the assignment row: it writes nothing a live write holds,
  and an activation committing meanwhile only leaves the change set behind again. The bar's offer
  names the release as the bar already labels it (key and version), cut short with "…" when long;
  the board showed the version alone.
- **Found on the way and fixed:** the index statement's type check answered `NULL` for a date held
  as a number, so the value was not indexed as JSON (the unit test against the flush hook found it);
  the runner first matched the page's description instead of the done notice.

**Checks (2026-10-18):** J37.7 written first, 16 failing at the route (`404`), then 16 passed on
generated-a and generated-b. Unit `tests/unit/engine/model/test_change_set_migrations.py` (2): the
index statement against `value_rows` over every value type's samples and mismatches; a moved change
set conflicting exactly on a live edit, a live deletion and a relationship set changed live, not on
a record the migration only converted nor one changed live and back, then executed with its index
and the stored matrix states (`matrix_states.verify`) true. J37, J37.6, J37.7, V1's and V3's unit
modules and `test_boundaries`: 67 passed, 43 s. Groups `contract`: 76 passed (the lock re-baselined
after diffing the default document against `68b7700`: the route, `ChangeSetMigrationRequest`,
`MigrationTypeMapping` and `MigrationAttributeSource` added, nothing removed;
`test_every_error_code_is_listed` failed until API_JOURNEYS listed the code). Groups `migration or
workspace_models or change_sets or queries` (`queries` selected by `snapshot_values.py`): 716 passed,
3 min 12 s, over the 2-minute ceiling as `change_sets` alone is (TODO's); the serial part 2 passed;
J24 and `unit/engine/jobs` 103 passed. Ruff. Frontend: `ChangeSets.test` (2 new, V2's "why not"
case replaced since its text changed), `MigrationPage.test` (2 new); the model-admin, workspaces,
app and routing folders 212 passed; `npm run format`, `lint` (0 errors; the 7 warnings are
elsewhere), `build`. `test:browser:workspace-v1` 7 cases passed, case 7 on generated-a and
generated-b (the bar's offer, the acceptance and Move change set by keyboard, axe on the bar and the
page, 390px without sideways scroll, the change set opened again). Screenshots inspected light and
dark (`v3-bar`, `v3-preview`, `v3-phone`, `v3-done`): they follow the board; the phone shot shows
the sticky bar over the page's middle as V1's approved phone shot does (a full-page capture of a
sticky bar). **Not run:** the accessibility and visual gates (build acceptance; V3 adds no gate
scenario, its surfaces show only for a change set left behind, as V2's); no budget (D96).

**What the user cannot do yet:** move a change set onto a release its workspace does not run when
its content does not fit (D87; TODO, not scheduled); run models of older schema versions side by
side (V4); move data between workspaces whose models differ (Track X).

#### V4: The schema-language window

**Design:** D11. **Needs:** V1, M6.

**Scope:** the schema-language versions workspaces may run side by side (D11), every pinned parser
served concurrently; the conversion rules between them written down; a release outside the window
refused at installation with its version and the window. The list and the dates are published by
L2.

**Groups:** `model`, `migration`, `startup`.

##### V4 plan (2026-10-18)

**Planned 2026-10-18; D97–D103 as recommended and the test cases accepted by the user the same day ("okay").**
Checked against the code at `68b7700` with V3's uncommitted changes in the working tree:

- **One parser already reads every version in the window.** `compiler.SCHEMA_VERSIONS` is
  `0.5`–`0.10`; `compile_model` refuses any other version with the diagnostic
  `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`, naming the window in its message. Documents of
  0.5–0.8 are read by `LegacyEngineModel`, which only keeps the 0.8 shape of `consumerApis`. The
  window is written three times: `SCHEMA_VERSIONS`, the `Literal` on `EngineModel.schemaVersion`
  and `LEGACY_SCHEMA_VERSIONS`.
- **A feature newer than the document is refused at its path** by `validation/fields.require_schema`
  (0.6 `mappingGrid`; 0.7 `relationMatrix`, `tree`, panel sorting; 0.8 `consumerApis`,
  `effectivePeriod`; 0.9 relation columns, `many-to-one`, `candidates`; 0.10 `navigation`).
- **Running side by side already works per request** (ADR-042, D11): the registry caches one
  snapshot per release; each workspace, change set and publication reads under its own release; a
  release this process cannot serve makes only its workspaces answer `503 MODEL_REGISTRY_UNAVAILABLE`
  (D29). Activation, workspace creation and the migration start answer `422
  UNSUPPORTED_SCHEMA_VERSION` with `details.schemaVersion` and `supportedSchemaVersions`.
- **Data conversions do not depend on the schema version.** Activation's compatibility analysis,
  V1–V3's migration plan (`rdm_convert_value`, D69) and the consumer contract check compare the two
  releases' declarations; nothing reads `schemaVersion`.
- **Installation is the exception:** `POST /model-drafts/{id}/install` answers a document outside
  the window with `422 INVALID_MODEL` and the diagnostic in `details`, not the structured
  `UNSUPPORTED_SCHEMA_VERSION` every other path returns. Validation and draft compile report
  `valid: false` with the diagnostic, as they should. `setRelease` refuses a version outside the
  window.
- **Two startup defects.** (a) `RDM_MODEL_PATH` naming a document outside the window stops the
  process with a `ModelValidationError` traceback, where schema 0.8 `consumerApis` has a named
  refusal (J12.7). (b) A workspace on a release outside the window is logged with the advice to run
  `model_schema_upgrade`, which only handles a schema 0.4 release and refuses anything else; a
  release of a schema newer than the window (a database used by a later engine) gets advice that
  cannot work.
- **The rules are written, but scattered** over APPLICATION_MODEL's per-version sections and
  "Versioning", ADR-021, ADR-042 and API.md; nothing states the rules for mixed operation in one
  place.
- **The test configurations** (`generated-a`, `generated-b`, the starter) are schema 0.9; nothing
  journey-tests a 0.10 release beside a 0.9 one.

**What is built:** the window declared once; the conversion rules written in one section of
APPLICATION_MODEL; installation's refusal made the same structured `422 UNSUPPORTED_SCHEMA_VERSION`
as activation's; the two startup defects fixed; J37.8 walked on two models. No UI and no database
migration, so no mock-up.

**Decisions** (D97 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D97 | The window in 0.11 | **0.5–0.10, unchanged (D11), declared once in `SCHEMA_VERSIONS`;** a unit test holds the `Literal`, the legacy set and every `require_schema` minimum to it. 0.11 opens no schema 0.11: no 0.11 package declares anything new in the model. Why: every version compiles into the same internal model, so keeping them costs nothing; a second copy of the list is how a version gets accepted by one check and refused by another. Cost: one unit test |
| D98 | Installation outside the window | **`422 UNSUPPORTED_SCHEMA_VERSION` with `details.schemaVersion`, `supportedSchemaVersions` and `operation: "install"`,** as activation, workspace creation and the migration start already answer; nothing is installed. Validation and draft compile keep `valid: false` with the diagnostic at `/schemaVersion`. A 0.8 document declaring `consumerApis` stays `INVALID_MODEL` (its version is in the window; a feature is refused). Why: an integrator reads one code with the window in `details` wherever a version is outside it. Cost: install's documented answer changes from `INVALID_MODEL` for this case; the OpenAPI lock re-baselined after diffing |
| D99 | The conversion rules | **Five rules, in one APPLICATION_MODEL section "Schema versions and the window"** that replaces "Versioning" and links the per-version sections. *Reading:* one parser; each version a strict superset of the one before, except that `consumerApis` changed shape at 0.9 (0.5–0.8 read as stored); a stored release keeps its content hash. *Writing:* any version in the window; raising a draft's version changes nothing else; lowering it is refused at the path of every feature newer than the target; 0.5–0.8 cannot declare `consumerApis` (C-D134). *Side by side:* every workspace, change set and publication reads under its own release; no request combines two. *Between releases of different versions:* activation, migration (V1–V3) and the consumer contract compare declarations only; the schema version itself never causes a conversion, a loss or a refusal. *Outside the window:* refused at installation, activation, workspace creation and migration; a stored release outside it makes only its workspaces unavailable. Why: this is what the code does, written where a model author looks. Cost: documentation; the rules are the ones J37.8 checks |
| D100 | How a version leaves the window | **No version leaves it in 0.11; the procedure and the dates are L2's.** A workspace already on a release outside the window stays as today: unavailable on its own, and no activation can replace its release, since its data cannot be compared (the roadmap's exit gate forbids forcing it). Why: nothing in 0.11 needs a version dropped, and how much notice, and what happens to publications pinned to it, belong with the compatibility commitment. Cost: that state is recovered only by running an engine that reads the version |
| D101 | Startup | **(a) A model file outside the window refuses to start with a message naming `RDM_MODEL_PATH`, the file, its version and the window,** as J12.7's refusal does. **(b) A workspace on a release outside the window is logged with the recovery that fits:** schema 0.4, the `model_schema_upgrade` command (as today); a version newer than the window, "this database was used by a later RDM Engine: start that version" (D100). Why: AGENTS' error-handling rule, a traceback is not an operator message; the current advice fails for every case but 0.4. Cost: two messages, two startup checks |
| D102 | A value type added by a later schema (the value-types door) | **A rule, no code:** until a new type's pairs are written in `rdm_convert_value`, a value converting to or from it is loss (VALUE_NOT_CONVERTIBLE), which the function already does for an unknown pair. Why: a new type stays additive and nothing is dropped silently. Cost: the door is open, but adding a type's conversions means a database migration replacing the function, not only a registry entry in `values.py`; COMPOSABLE_DOMAINS says so in one line |
| D103 | Which versions the journeys walk | **The newest two, 0.9 and 0.10, in both directions,** each test configuration raised to 0.10 by a test helper that sets the version and adds a navigation group. Versions 0.5–0.8 keep their older tests (`test_model_lifecycle`, `test_consumer_api_model`, J25, J12.7). Why: lowering a configuration to 0.5 would mean removing what it is made of; mixed operation does not depend on which two versions run. Cost: older versions side by side are covered by the shared parser, not by a journey |

**Journey test cases** (`tests/journeys/test_j37_8_schema_window.py`, J37.8, `migration`,
`workspace_models`, `model`; X beside Y, both directions, naming no key; X′ and Y′ are X and Y raised
to 0.10 with a navigation group):

1. **J37.8 Side by side.** W1 on X (0.9), W2 on Y′ (0.10). Each `GET /model` answers its own schema
   version, W2's with its navigation; a create, a read, a consumer API read and a published change
   set succeed in each under its own release (`X-Model-Release-Id`).
2. **J37.8 Raising the version is no migration.** Activating X′ into W1 needs no migration, its
   consumer contract is compatible and every record keeps its version; activating X back likewise.
3. **J37.8 A migration across versions converts by declarations.** X′ also retypes an attribute and
   removes a binding; migrating W1 from X to it previews exactly that conversion and that loss, no
   item naming a schema version; confirmed, W1 runs it.
4. **J37.8 A draft on an older version.** A draft based on X refuses a navigation group at its path
   naming 0.10; after `setRelease` raises it to 0.10 the group is added and the draft installs;
   lowered to 0.9 with the group declared, draft compile is `valid: false` at the navigation path.
5. **J37.8 Installation outside the window.** A draft naming schema 0.4, and one naming the version
   after the newest: install is `422 UNSUPPORTED_SCHEMA_VERSION` with `schemaVersion` and
   `supportedSchemaVersions` equal to `GET /system`'s `schemaLanguages`; the releases are unchanged;
   validation is `valid: false` at `/schemaVersion`; `setRelease` to that version is refused.
6. **J37.8 A workspace on a release outside the window** (written to the database as a later engine
   would leave it, which the test says): after a restart only that workspace answers `503
   MODEL_REGISTRY_UNAVAILABLE` with its schema version and the window, the other serves; the log
   names the workspace and the later-engine recovery, not the 0.4 command; an activation into it is
   `422 UNSUPPORTED_SCHEMA_VERSION` and changes nothing.
7. **J37.8 A model file outside the window** at startup: the service refuses to start with a message
   naming `RDM_MODEL_PATH`, the file, its version and the window.

Unit test: the window declared once (D97).

**Groups:** `model`, `migration`, `startup` (D101), `workspace_models`, `contract` (install's answer,
the lock re-baselined after diffing); no database migration, no frontend change.

**Composable domains (ADR-032):** attribute storage and the value-types door: D102 (open, at the
cost of a migration per new type's conversions); identity, audit, bulk APIs, `match` and mapping
coverage are unaffected.

##### V4 record (2026-10-18)

**Delivered 2026-10-18.** Built as planned (D97–D103), with no database migration, no route added
and no frontend change.

- **The window declared once (D97):** `compiler.SCHEMA_VERSIONS` stays the only list; a unit test
  holds `EngineModel.schemaVersion`'s `Literal`, `LEGACY_SCHEMA_VERSIONS` and every `require_schema`
  minimum to it. `compiler.after_window` says whether a version is newer than the window.
- **Installation (D98):** `POST /model-drafts/{id}/installation` answers a draft outside the window
  with `422 UNSUPPORTED_SCHEMA_VERSION` (`draftId`, `schemaVersion`, `supportedSchemaVersions`,
  `operation: "install"`). The route has no description, so the OpenAPI document did not change
  (the lock passes unchanged); the UI shows the server's message as for any refusal.
- **Startup (D101):** `loader.load_model` refuses a model file outside the window with a message
  naming `RDM_MODEL_PATH`, the file, its schema and the window, before any parsing; the lifespan
  logs a workspace on a release newer than the window with "a later RDM Engine" as the recovery
  instead of the 0.4 command, and every such log ends "Until this is resolved, …" (it said "Until
  the transition succeeds" for every case).
- **The rules (D99, D100, D102):** APPLICATION_MODEL's "Versioning" became "Schema versions and the
  window": the table of what each version adds, the five conversion rules and the line that no
  version leaves the window in 0.11 (L2). API.md (installation's refusal, the window's link),
  OPERATIONS (startup checks), COMPOSABLE_DOMAINS (D102's line), USER_JOURNEYS J37.8,
  API_JOURNEYS, CURRENT_FUNCTIONALITY and CHANGELOG follow it.

Where it differs from the plan: case 6 is two tests, as the log is read through the service
harness (J12's `serve`) and the 503 and the activation through the application on the world's
database; case 5 runs for 0.4 and for the version after the newest, each on both models.

**Checks (2026-10-18):** J37.8 written first (`tests/journeys/test_j37_8_schema_window.py`, 9
tests, 18 cases on generated-a and generated-b, the startup cases on generated-a and the example
model): before the change the installation, model-file and log cases failed (the log case first on
a wrong seed in the test, fixed; on the old code its message held the 0.4 command the test
refuses), and the side-by-side, raising, cross-version migration, draft and later-engine cases
passed, as the plan expected of behaviour that already held. After the change all 18 pass. Unit:
`tests/unit/engine/model/test_compiler.py` (6). Groups `model`, `model_admin`, `startup`,
`contract`, `workspace_models` and `migration`, parallel part: 4,147 passed, 1 failed, in 2 min 36
s, over the package ceiling, because `model` selects far more than the plan assumed; the failure,
`test_startup.py::test_upgrade_to_the_profile_check_kind_keeps_jobs_and_an_interrupted_run_recovers`
(a profile-check job failed in a chunk under parallel load), passed when run alone and touches no
V4 code, so it is recorded in TODO as a flake. Their serial part selects no case. After the final
formatting: J37.8, the compiler unit tests and J12 (70 passed). `ruff check app/ tests/` clean.
Not run: the full suite, Vitest, the browser runners and the gates (no frontend change; build
acceptance R).

**What the user still cannot do:** retire a schema version from the window or read the dates of
the supported versions (L2); move data between workspaces whose models differ (Track X).

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

##### X1 plan (2026-10-18)

**Planned 2026-10-18; D104–D113 as recommended and the test cases accepted by the user the same day ("ok, can you please implement the above?").**
Checked against the code at `7691c4f` with V4's uncommitted changes in the working tree:

- **A5's operations are a draft's.** The mapping kinds (`engine/model/authoring/mapping.py`) edit a
  draft's import profile through `Document`, whose log gives every kind an exact inverse
  (`restoreElements`, ADR-041). Their history, undo, redo, `VERSION_CONFLICT` and dependants
  (`authoring/history.py`) are written for `ModelDraft` and `model_draft_operations`: the lock,
  the version, the compile after each step and the profile's warnings are a draft's.
- **A6/A7's inference reads a file.** The job (`sources/inference/run.py`, kind `inference`)
  profiles a source file's staged cells, finds table patterns and builds operations that create
  model elements and bind columns. What carries over is the frame, not the matching: proposals
  stored per run in `model_draft_proposals` and replaced by the next; applied through
  `history.apply_steps` as steps of origin `proposal`, each with a snapshot so a later run tells the
  engine's steps from the administrator's (D92: `open`, `applied`, `held`, `rejected`); stored
  records compared in set statements (`StoredRecords`, `_identifiers`). Matching one model's
  elements to another's is new.
- **Nothing stores a mapping between two models.** V1's `typeMappings` (D70) map types and
  attributes within one migration request and are not saved; import profiles map a file's columns.
- **Value conversion is one function.** `rdm_convert_value` (V1, D69) converts every pair it knows
  and answers `NULL` otherwise; some pairs never convert (a boolean to a date, JSON to a number).
- **The test models fit the move.** `generated-a` and `generated-b` hold the same structures under
  entirely different keys (`ledger` and `x_ledger_7`), with the same element names, and differ in
  shape: in B a dependant stands under a container type A lacks. So the true mapping is known by
  structure, a parent differs between the models (I22), and the names alone would propose most
  of it, which is why case 2 also takes the names away.
- **Gates.** Import profiles are written under `INTEGRATION_JOBS_ENABLED`; A6's inference also
  under `MODEL_ADMIN_MUTATIONS_ENABLED`, since it edits a draft.

**What is built:** the `model_mappings` resource of API.md's design: created between two models,
changed only by operations with history, undo and redo, proposed by an inference job turned to two
workspaces, its drift and coverage reported on every read. A database migration (three tables and
the job kind), a service under `engine/moves/`, a router, the OpenAPI lock re-baselined. No UI (X4)
and nothing moves (X2, X3), so no mock-up.

**Decisions** (D104 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D104 | What a mapping is checked against | **Two releases it names, `sourceReleaseId` and `targetReleaseId`,** taken from two workspaces when it is created (or given as release IDs), and moved by an operation `setReleases`, which is undoable like any other. Its identity stays the two model keys (D18): one key, and a list filtered by the two models. Why: an operation is checked against a model; a mapping bound to "whatever the workspace runs today" would change meaning when a workspace activates a release, without any step in its history. As an import profile has `checked_release_id` and a draft its base. Cost: a mapping edited against older releases is re-pointed by hand; D110 shows what that breaks |
| D105 | Where the history lives | **One history component for drafts and mappings:** `authoring/history.py`'s steps, undo, redo, dependants and conflict entries taken out of `ModelDraft` behind a small owner interface (lock, version, write, check after a step), drafts and mappings both using it; a table `model_mapping_operations` with the columns of `model_draft_operations`. Why: one component, no copies; undo across dependants (D8) and origin `proposal` (D92) behave the same in both. Cost: A2's history refactored in this package, so the `authoring` group runs (as the plan already lists) |
| D106 | The mapping's shape | **API.md's design, completed:** `types` by source type, each one target type (several source types may name one target; one source type never two, a split by condition is not in 0.11), with `attributes` (target or `ignore`, an optional `valueMap`), `match` (how a target record not found by counterpart or origin is matched: `{attributeTypeKey}` of a unique target attribute, `{field: "name"}`, or none: I12), `parent` (`{from: "source"}` the source parent's mapped record, or `{objectTypeKey, value}` a fixed one, each with `missing: create|refuse`: I21, I22), `relations` (source relation and direction to target relation and direction, with relation attributes: I18, I19), `defaults` (a target attribute's value when the source has none: I13), and `valueMaps` (I11). The record name always carries; effective periods carry when both types declare one (I24), with nothing to map. Why: what X2's dry run needs to decide every item, nothing more. Cost: lookups (I14) are relations to list types here, so a list value not in the target is `missing: create|refuse` on that relation, not a separate construct |
| D107 | The operations | **`mapType`, `unmapType`, `mapAttribute` (a target, or `ignore: true`), `unmapAttribute`, `mapRelation`, `unmapRelation`, `setParent`, `setMatch`, `setValueMap` (create, replace or remove one map), `setMissing`, `setDefault`, `setReleases`,** each with its inverse from `Document`'s log as A5's kinds. Each is checked against the two releases: the elements exist; the target type binds the attribute; the target allows the relation between the mapped types; a parent's relation contains the target type. A value-type pair `rdm_convert_value` never converts is refused (`valueTypesNotConvertible`); a pair that converts some values (text to date) is accepted and its values are counted in X2. Refusals are `422 INVALID_OPERATION` with the pointer, as a draft's. Why: API.md's first cut with the two missing inverses (`unmapRelation`) and the release step D104 needs. Cost: a Python table of which pairs never convert, held to the SQL function by a unit test |
| D108 | The inference | **A job of kind `mappingInference`** (`POST /model-mappings/{key}/inference` with `sourceWorkspaceKey` and `targetWorkspaceKey` running the mapping's two releases), proposing per source type one proposal (`mapType` with its attributes, parent and match) and per relation one (`mapRelation`), each with its evidence and up to three alternatives, scored from: same key or same key once case and separators are folded; same name; attribute overlap (names and convertible value types); a parent already proposed; **stored records**: the share of the source type's unique values and names found among a target type's records, one statement per source type over `attribute_values` and `objects` in the two workspaces. Proposals replace the mapping's earlier ones; statuses `open`, `applied`, `held`, `rejected` read from the history as D92. Applying writes each as a step of origin `proposal` (the "Proposed" mark X4 shows) through the one history (D105). Why: the A6 frame the user knows, the matching new; stored records in set statements (principle 6). Cost: the stored-records statement is the slow part at full volume, measured in X5 |
| D109 | The same model on both sides (I34) | **Allowed and proposed as identity:** every element mapped to the element of the same key, evidence `sameModel`; the two releases may differ, so a key the target release lacks is proposed by name or not at all. Why: a move between two workspaces of one model is the same machinery. Cost: none beyond the matching rule |
| D110 | Drift and coverage | **Computed on every read, never stored:** `problems` lists each entry naming an element the mapping's releases lack or no longer allow (`ELEMENT_NOT_IN_RELEASE`, `BINDING_NOT_ALLOWED`, `VALUE_TYPES_NOT_CONVERTIBLE`), with its pointer; with `sourceWorkspaceKey` and `targetWorkspaceKey` on the read, the same against the releases those workspaces run, so a mapping is checked before a move without being re-pointed. `coverage` lists the source types, attributes and relations not mapped and the target's required attributes and relations nothing fills (I9, I13, I18). Why: the release a workspace runs changes without the mapping's knowledge; reporting is cheap (model metadata only). Cost: record counts per unmapped element are X2's dry run, not X1's |
| D111 | Gates and limits | **Reads always; writes, operations and the inference under `INTEGRATION_JOBS_ENABLED`,** as import profiles. Operations per request `MODEL_OPERATION_MAX_ITEMS` (500), as a draft's. The list and the proposals page under ADR-030. Why: a mapping is integration configuration, not a model; the move itself is under both gates (D14). Cost: none |
| D112 | Deleting a mapping | **`DELETE /model-mappings/{key}` with `expectedVersion`;** its operations and proposals go with it. A move job (X2, X3) keeps the definition it ran with, as an import job keeps its profile. Why: a job's record must not depend on a resource that may change. Cost: none here |
| D113 | Where the code lives | **`engine/moves/`** (`mappings.py` the resource, `mapping_kinds.py` the operations, `mapping_inference.py` the job), `management/routers/model_mappings.py`, and the `move` marker for `engine/moves/` and J38 in `tests/conftest.py` and EXECUTION_GUIDE. Why: X2 and X3 add the dry run and the move beside it. Cost: none |

**Journey test cases** (`tests/journeys/test_j38_1_model_mapping.py`, J38.1, `move`; W1 on X, W2 on
Y with X and Y generated-a and generated-b, both directions, naming no key; X4's browser walk is
X4's):

1. **J38.1 Created between two workspaces.** `POST /model-mappings` naming W1 and W2: `201` with
   both model keys and releases, version 1, no types, `coverage` listing every source type; a
   second mapping of the same key `409`; one naming a retired or unknown workspace refused; the
   list filtered by the two model keys finds it.
2. **J38.1 Proposed with evidence.** Records of R in W1 and W2 sharing unique values; the inference
   job completes; every structure type of X is proposed to the same structure of Y, attributes by
   structure, D's parent naming Y's container (I22), the relations to their structures. With the
   names of Y's types replaced by a test helper (a release of Y with other names), R is still
   proposed to R from the stored records, its evidence saying so, with alternatives.
3. **J38.1 Proposals applied as steps marked Proposed.** Applying them adds one step per proposal
   of origin `proposal`; the mapping's version rises; a new inference reads them `applied`; the
   mapping then covers every type and `coverage` lists only what Y has and X lacks.
4. **J38.1 Corrected by hand.** `mapAttribute` to another attribute, `setDefault` for a required
   attribute of Y nothing fills (I13), `setMatch` by Y's unique attribute (I12), a value map
   (I11), a relation unmapped: each applied; refused at its pointer: an attribute Y's type does not
   bind, a value-type pair that never converts, a relation Y does not allow between the mapped
   types. A new inference keeps the hand-corrected proposal `held`.
5. **J38.1 Undone and redone.** The hand step undone restores the mapping exactly, redo applies it
   again; a proposal step undone reads `rejected` on the next inference; an operation at a stale
   version is `409 VERSION_CONFLICT` with the newer entries; undoing a step a later one depends on
   is `409 OPERATION_HAS_DEPENDANTS`.
6. **J38.1 Drift reported and re-pointed.** W2 activates a release of Y without an attribute the
   mapping names: the read with W2 lists the entry in `problems` at its pointer, the read without
   it does not; `setReleases` to the new release puts it in `problems` of every read;
   `unmapAttribute` clears it; deleting the mapping at its version leaves `404
   MODEL_MAPPING_NOT_FOUND`.
7. **J38.1 The same model on both sides (I34).** W1 and a W3 on X: the inference proposes identity
   for every element with evidence `sameModel`.

Unit tests: each kind's inverse restores the mapping exactly; the pairs that never convert held to
`rdm_convert_value`; the inference's scoring on two small hand-built models.

**Groups:** `move` (new), `authoring` (D105's refactor), `jobs` (the job kind), `startup` (the
migration), `contract` (the routes; the lock re-baselined after diffing). No frontend change.

**Composable domains (ADR-032):** mapping coverage gains the two-model case (D110); identity, audit
and bulk APIs are X3's; the value-types door keeps D102's rule, a pair not yet written in
`rdm_convert_value` is refused in a mapping until it is.

**What the user still cannot do after X1:** choose what moves and read its dry run (X2), move or
copy records (X3), edit the mapping in the browser (X4).

##### X1 record (2026-10-18)

**Delivered 2026-10-18.** Built as planned (D104–D113): migration `20261020_01`, the engine
package `engine/moves/`, the router `management/routers/model_mappings.py`, the OpenAPI lock
re-baselined after diffing; no frontend change.

- **The resource (D104, D106, D111, D112):** `model_mappings` keyed, named by its two models, its
  definition holding the two release IDs, `types` and `valueMaps`; created from two workspaces or two
  releases; listed by models, read, deleted at its version with its history and proposals. Reads
  are always registered; writes, operations and the inference with `INTEGRATION_JOBS_ENABLED`.
- **The history (D105):** `authoring/history.py` now works over an `Owner` (lock, apply, write
  back, store entries); drafts (`DRAFTS`, the default, so every draft call site is unchanged) and
  mappings (`MAPPINGS`) use the same steps, undo, redo, dependants and conflicts. A draft's
  answers are unchanged (J33 and J34 pass).
- **The operations (D107):** the twelve kinds in `mapping_kinds.py`, each refused at its
  parameter (`unknownElement`, `bindingNotAllowed`, `valueTypesNotConvertible`, `modelMismatch`,
  `inUse`, `invalidValue`); `values.conversion` classifies each pair of value types as
  `rdm_convert_value` does (`always`, `partial`, `never`).
- **The inference (D108, D109):** `mapping_inference.py`, a job of kind `mappingInference` run by
  the worker; proposals per type (`mapType`, `mapAttribute`, `setParent`, and `setMatch` when the
  workspaces share records) and per relationship (`mapRelation` with relation attributes), each with
  evidence and up to three alternatives; one model on both sides proposed as identity.
- **Problems and coverage (D110):** `mapping_check.py`, on every read and every step's answer.

Where it differs from the plan:

- **Stored records in one statement for every pair of types,** not one per source type (D108):
  fewer statements, the same answer.
- **Key evidence is the share of the keys' words** (`keyTokens`), of which "the same key once case
  and separators are folded" is the whole share; `sameKey` stays for one key in two models.
- **A proposal's status is read from the mapping, not from a snapshot:** a proposal keeps one ID
  per mapping from one inference to the next, and reads `applied` while its entry is as it made it,
  `held` when the mapping decides it otherwise, `rejected` when a step that applied it was undone
  (D92's statuses without A6's per-element ownership, which a mapping entry does not need).
- **Added beyond the design:** `POST …/inference/application` (as a draft's), the codes
  `MODEL_MAPPING_EXISTS` and `INVALID_MODEL_MAPPING`, the problem `ATTRIBUTE_FILLED_TWICE` (two
  source attributes onto one target attribute are accepted, so that two can swap in one step, and
  reported), the coverage's `parents`, and an index of a mapping's jobs (`ix_jobs_mapping`, as
  R-F14's).
- **Each side named by a workspace or a release,** `sourceWorkspaceKey` and `targetWorkspaceKey`
  on reads checking against the releases those workspaces run.

**Checks (2026-10-18):** J38.1 written first (`tests/journeys/test_j38_1_model_mapping.py`, 7
tests, 14 cases on generated-a and generated-b), all failing with `404` before the routes existed;
after the change all 14 pass. Unit: `tests/unit/engine/moves/` (6: every kind's inverse and its
inverse's inverse, four scoring rules, the match from shared records) and
`tests/unit/engine/records/test_values.py` (the conversion classes held to `rdm_convert_value`).
Groups `move`, `startup` and `jobs` with `-n auto`: 699 passed, 35 failed, in 4 min 55 s, over the
package ceiling (TODO). The failures were the harness's `HEAD` revision and the reviewed foreign-key
rules, which a new migration changes, fixed with a new startup case for `20261020_01` (an
interrupted run refused naming the table, two starts creating and reading a mapping, a downgrade);
the 32 rerun with `--lf` passed, and the serial part (1) passed. D105's draft side: J33, J34 and the
`authoring` and `sources` unit tests, 3,536 passed in 4 min 57 s, over the ceiling (TODO). The
`authoring` group as a whole was not run: it selects 3,522 cases, most of them unrelated to the
history. `contract`: the lock, the paging inventory (41 collections) and API_JOURNEYS' routes,
parameters and codes updated; 76 passed. A first run of the three groups without `-n auto` ran
serially and was stopped after 10 minutes (the harness's PostgreSQL stopped with it). **Smoke
start** on a copy of the development database (3 workspaces, 2,380 records), taken back to
`20261019_01`: the start upgraded it to `20261020_01`, `/health` and `/system` 200, unique-value
rows 15 before and after, and a mapping between two of its workspaces created, inferred (61
proposals) and applied with no problems; the copy dropped. `ruff check app/ tests/` clean.
**Not run:** the full suite, Vitest, the browser runners and the gates (no frontend change; build
acceptance R). `MODEL_MAPPING_MODEL_MISMATCH` and `INVALID_MODEL_MAPPING` are not reached by a test.

**Found:** the development server (`uvicorn --reload` on the shared checkout) applied the migration
while it was still being written, so the development database `rdm` is at `20261020_01` without
`ix_jobs_mapping` (TODO, with its recovery); it holds no mapping.

**What the user still cannot do:** choose what moves and read the dry run of every item (X2), copy
or move records into a change set (X3), edit the mapping in the browser (X4).

#### X2: Selection and the dry run of a move

**Needs:** X1.

**Scope:** what moves: a whole workspace, chosen types, a subtree, a filtered set, a selection (K1).
The dry run of every item (D67) as a background job in PostgreSQL: each item's outcome in the
target with its reasons, as an import's row outcomes (J3): what cannot move (no mapping, value not
convertible, unique value held, required value missing, parent missing, relationship's other end
left behind) with what to do about it.

**Groups:** `move`, `jobs`, `volume`.

##### X2 plan (2026-10-18)

**Planned 2026-10-18; D114–D123 as recommended and the test cases accepted by the user the same day ("yes its fine"), X2 taken before S1 (D2 revised, below).**
Checked against the code at `6680834`:

- **An import's phases exist and are reusable.** An import binds its file in PostgreSQL into batch
  items (`imports/binding.py`: temporary tables, matches resolved in set statements, items ordered
  records by depth, then relationships, D72), stores them as `job_inputs` with its refused rows as
  its first outcomes, and previews every item through the batch path (`jobs/batches.run_items`,
  `previewing=True`) in a transaction it rolls back. A `dryRun` previews the whole file (D67) and
  completes with its summary; no sample cap applies to it. Row outcomes read by source and row
  (`job_items.source_index`, `row_number`) through `GET /jobs/{id}/rows`.
- **The batch path gives the target's rules for free.** Each create or update item is decided by
  the single write's rules over a batch lookup that sees the items before it (`rules.py`,
  `batch_lookup.py`), so a refusal carries the import's code and pointer (I27):
  `MISSING_REQUIRED_ATTRIBUTES`, `DUPLICATE_ATTRIBUTE_VALUE` with the holder,
  `MISSING_REQUIRED_RELATIONS`, `INVALID_PARENT_TYPE`, `PARENT_REQUIRED`.
- **Reading the source is a set source already.** `reads/context_sets.record_source` and
  `relation_source` read live data or a publication alike, each record with its values as one JSON
  object; exports select their scope from them by types, `where` criteria (`QueryCriterion`) and
  `parentObjectId`.
- **Conversion is one SQL function.** `rdm_convert_value` (V1) converts a value between two value
  types or answers `NULL`; V1 runs it over `attribute_values` in set statements.
- **Counterpart IDs are computed in Python.** `counterpart()` is a version-5 UUID (SHA-1), and
  PostgreSQL has no SHA-1 of its own, so J5's binding derives them in Python
  (`import_counterparts`). `pgcrypto`, which has one, ships with the PostgreSQL contrib modules
  (present in the Homebrew build), and `db.REQUIRED_EXTENSIONS` already creates and checks
  `pg_trgm` and `btree_gin` at startup with an actionable refusal.
- **X1's check is reusable.** `mapping_check.py` computes problems and coverage of a definition
  against two releases, and against the releases two workspaces run.
- **No origin table yet.** I3's `updateOriginal` needs D23's origins, which X3 writes; X2's dry run
  can say `create` or `update` (found by counterpart or by the mapping's `match`), not
  `updateOriginal`.

**What is built:** `POST /moves`, a background job of kind `move` that binds the selection through
the mapping into batch items in PostgreSQL and previews every item against the target workspace,
rolled back, then completes with its summary; its rows read through `GET /jobs/{id}/rows`. A
migration (the job kind, `pgcrypto` and the function `rdm_counterpart`), a service under
`engine/moves/`, a router, the OpenAPI lock re-baselined. Nothing is written to either workspace
(X3 loads), no UI (X4), so no mock-up.

**Decisions** (D114 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D114 | The job and its stages in X2 | **A job of kind `move` with the import's phases, `stage: "preview"` only:** it binds, previews every item (D67) and completes with its summary, as a `dryRun` does. X3 adds the confirmation that loads the preview into a change set (the job then waits for it, as an import's preview), so `stage` accepts `preview` alone until then and no route answers "not yet". Why: D19's one job kind; a dry run without a load is a complete answer, and X4's figures after every step are this job. Cost: X3 changes the job's final state from `completed` to waiting for confirmation, a contract change inside 0.11 |
| D115 | How the target's validation runs | **Through the batch path, as an import's preview:** the binding writes create and update items naming the target's types, parents and relationships, and `run_items` decides each against the target's live data, every item `independent`, and rolls back. Why: I27 asks for the import's refusals with their codes and pointers, and the rules exist once (`rules.py`); V1's whole-graph check would give compatibility counts, not rows an integrator can act on. Cost: each item is decided in Python over a batch lookup, as every import dry run is; the binding (selection, mapping, conversion, matching, ordering) stays in set statements, and the full-volume figure is X5's |
| D116 | The selection | **`selection` with `types` (each `{objectTypeKey, where}`, the exports' scope and criteria, refused `INVALID_QUERY` at the pointer), `parentObjectId` (that record and every record under it, I7), `objectIds` (up to 10,000, documented, as an atomic batch's items), combined: a record moves when every given part selects it; an empty selection is the whole workspace.** Selected records only: a parent or a related record not selected is found in the target or reported (D118), never pulled in. Stored on the job with the mapping's definition at its version (D112). Why: I7's five forms, exports' filter language rather than a second one. Cost: API.md's `types: [key]` and top-level `where` become the exports' per-type shape |
| D117 | Which source state is read | **`sourceAt`: `live` (read in the binding's one transaction, its feed position recorded on the job) or a publication ID of the source workspace** (`publication_context`). Why: I30 asks for one point; both are a `record_source` context already. Cost: none beyond a refusal for another workspace's publication (`PUBLICATION_NOT_FOUND`) |
| D118 | What each record becomes | **In the order:** found by its counterpart in the target → `update` (I2); else found by the mapping's `match` (a unique attribute's value or the name, one record) → `update` with `matchedBy`; else `create` with the counterpart as its ID (I1). Its type is the mapped type; attributes through the value map, then `rdm_convert_value`, then `defaults` for a value the source lacks (I11, I10, I13); effective periods as I24. **Its parent:** the moved parent's counterpart, a target record found by counterpart or match, or the mapping's fixed parent; `missing: create` adds a create item for a fixed parent by name; otherwise not moved. **Its relationships:** to a moved record, carried; to a record found in the target, carried (I16); otherwise dropped (I17), and a required one's loss is the target's `MISSING_REQUIRED_RELATIONS` (I20). A list record named by a relationship (I14) is matched by key or name, and with `missing: create` created. Why: the inventory's cases in one fixed order; `updateOriginal` is X3's (D23). Cost: a `match` finding several target records is not decided by guessing: the record is `refused` with `MATCH_AMBIGUOUS` and the candidates |
| D119 | What cannot move, and the rows | **One row per selected record and per relationship it holds, every item listed (J38.7):** `outcome` `create`, `update`, `refused` (the target's rule, its code, pointer and details as an import row) or `notMoved` (the mapping's reason, before any rule: `TYPE_NOT_MAPPED`, `PARENT_TYPE_NOT_MAPPED`, `PARENT_NOT_FOUND`, `RELATION_NOT_MAPPED`, `RELATION_TARGET_LEFT_BEHIND`, `RECORD_NOT_MOVED` for a record whose parent did not move); a moved record's row also lists what it leaves behind (`ATTRIBUTE_NOT_MAPPED`, `VALUE_NOT_CONVERTIBLE` at the attribute's pointer with the value, `EFFECTIVE_PERIOD_DROPPED`) and `possibleDuplicates` (a target record of the same type and name, I4). Each row names `sourceId`, `sourceType`, `targetId`, `targetType` and what to do (`action`: `mapType`, `mapAttribute`, `setDefault`, `setMatch`, `setParent`, `select`). `GET /jobs/{id}/rows` filters by `outcome`, `reason` and `sourceType`, paged (ADR-030). Why: the user reads what cannot move by reason and acts on it in the mapping (X4's report). Cost: a value that does not convert leaves the record moving without it (as V1's loss), so only a required one refuses it |
| D120 | Counterpart IDs in PostgreSQL | **`pgcrypto` added to `REQUIRED_EXTENSIONS` and an SQL function `rdm_counterpart(workspace, id)`** returning the same UUID as `counterpart()`, held to it by a unit test. Why: every selected record's target ID is a set statement (principle 6, and the PostgreSQL-only rule), not a stream through Python. Cost: one more contrib extension at startup, created by the existing check or refused with its instruction; J5's binding keeps its Python path (not changed here) |
| D121 | Refusals at the start | **Checked before a job exists:** `422 MOVE_SAME_WORKSPACE`; `404 MODEL_MAPPING_NOT_FOUND`; `409 MOVE_MAPPING_CHANGED` (`expectedVersion` stale); `422 MODEL_MAPPING_MODEL_MISMATCH`; `409 WORKSPACE_RETIRED` (either side); and **`422 MOVE_MAPPING_HAS_PROBLEMS`** with the problems when the mapping, checked against the releases the two workspaces run (D110), has any. Releases other than the mapping's own are allowed when nothing is wrong, and the job records all four. A target whose release changes during the dry run fails it `MODEL_RELEASE_CHANGED`, as any job. Gates: both, as D14 and D111 settled. Why: a dry run of a broken mapping would report the mapping's fault on every row. Cost: one new code |
| D122 | The summary | **Counts by source type and outcome; by reason with counts; relationships carried and dropped by relation type and reason; attributes not carried per type and attribute with counts (I9); possible duplicates; `coverage: complete` (D67)**; with the mapping key, version and the four releases. Why: X4's figures, read from one job. Cost: none |
| D123 | Where the code lives and the volume check | **`engine/moves/selection.py` (the selection to a set), `move_binding.py` (the mapping to items), `move_job.py` (submit, preview, summary); `management/routers/moves.py`; migration `20261021_01`.** The `volume` group gains one case: a move's binding costs the same number of statements for 50 and 500 records (as `test_batch_statements`); the full-volume measurement stays X5's. Why: D113's home; I28's "set statements" made checkable without a heavy run. Cost: none |

**Journey test cases** (`tests/journeys/test_j38_2_move_dry_run.py`, J38.2, J38.4, J38.5, J38.7,
`move`; W1 on X, W2 on Y with X and Y generated-a and generated-b, both directions, naming no key;
the mapping proposed and applied as in J38.1):

1. **J38.2 A whole workspace.** Given W1 with records of every structure and the applied mapping.
   When `POST /moves` with an empty selection, then `202`, and once run the job completes with one
   row per W1 record and relationship; every record of a mapped type is `create` with its
   counterpart as `targetId` and its mapped type; the counts by type equal W1's. W2's records, feed
   position and change sets are unchanged.
2. **J38.2 Selections.** Types with a `where`, a subtree (the record and everything under it), and
   `objectIds` each select exactly those records; `sourceAt` a publication of W1 omits a record
   created after it; the job's parameters hold the selection and the mapping's version.
3. **J38.7 What cannot move.** A type unmapped: its records `notMoved` `TYPE_NOT_MAPPED` with the
   count, the records under them `RECORD_NOT_MOVED`; an attribute unmapped: listed per attribute
   with its count, the records still `create`; a value that does not convert: `VALUE_NOT_CONVERTIBLE`
   at its pointer on a moving record; a required attribute of Y nothing fills: `refused`
   `MISSING_REQUIRED_ATTRIBUTES`, and after `setDefault` the same records `create`.
4. **J38.4 A relationship whose other end stays behind.** Selecting one type: a relationship to a
   record not in W2 is `notMoved` `RELATION_TARGET_LEFT_BEHIND` while its record is `create`; with
   the other end in W2 (found by the mapping's `match`), it is carried; a required relationship
   whose other end stays behind refuses its record `MISSING_REQUIRED_RELATIONS`.
5. **J38.5 A unique value already held.** W2 holds a record with a W1 record's unique value: that
   row is `refused` `DUPLICATE_ATTRIBUTE_VALUE` naming the holder; after `setMatch` by that
   attribute it is `update` of the holder with `matchedBy`; a W2 record of the same name only
   is listed in `possibleDuplicates` of a `create`.
6. **J38.2 The parent in the target (I21, I22).** The dependant whose parent type differs between
   the models: moved with its parent, it stands under the parent's counterpart; its parent not
   selected and not in W2, it is `notMoved` `PARENT_NOT_FOUND`; with a fixed parent and
   `missing: create`, a create item for that parent comes first and the dependant stands under it.
7. **Refusals.** Source and target one workspace `422 MOVE_SAME_WORKSPACE`; a mapping of other
   models `422 MODEL_MAPPING_MODEL_MISMATCH`; an unknown key `404 MODEL_MAPPING_NOT_FOUND`; a stale
   version `409 MOVE_MAPPING_CHANGED`; a retired target `409 WORKSPACE_RETIRED`; W2 on a release
   without an attribute the mapping names `422 MOVE_MAPPING_HAS_PROBLEMS` with the problem's
   pointer; an unknown type in the selection `422 INVALID_QUERY` at its pointer. No job is created
   by any of them.

Unit tests: `rdm_counterpart` held to `counterpart()`; the order of D118 on a hand-built pair of
records (counterpart, match, create). Volume: D123's statement count.

**Groups:** `move`, `jobs` (the job kind), `startup` (the migration and the extension), `volume`
(D123), `contract` (the route; the lock re-baselined after diffing). No frontend change.

**Composable domains (ADR-032):** identity: the counterpart ID is computed in PostgreSQL, the same
value as today, so the retired-ID door is unchanged; bulk APIs: a move's dry run is a job with an
import's rows; mapping coverage gains per-record counts (D122).

**What the user still cannot do after X2:** load the dry run into a change set, move rather than
copy, or move a record back to its original (X3); edit the mapping and read the dry run in the
browser (X4).

##### X2 record (2026-10-18)

**Delivered 2026-10-18.** Built as planned (D114–D123): migration `20261021_01` (`pgcrypto`,
`rdm_counterpart`, the job kind `move`), `engine/moves/selection.py`, `move_binding.py` and
`move_job.py`, the router `management/routers/moves.py`, a move's rows at `GET /jobs/{jobId}/rows`
and its `move` summary on the job; the OpenAPI lock re-baselined after diffing the document against
`6680834` (only the `Move*` schemas, `JobResponse.move` and its kind, the rows route's filters and
answer, the jobs list's kind filter); no frontend change.

Where it differs from the plan:

- **A read-only target attribute is not written** and is listed as `ATTRIBUTE_READ_ONLY` on the row:
  the target's rule refuses a value for it, so a type binding one would have had every record
  refused. Found by J38.2's whole-workspace case.
- **A relationship the target requires into a record it creates rides on that record's create**
  (D118 named the target's `MISSING_REQUIRED_RELATIONS`): it is carried there when its other end
  moves or is found, so only one left behind refuses the record, as I20 says. The relationship's
  row takes its record's outcome (`rides`).
- **Relationships are `ensureRelation` items**, so one already in the target is found again rather
  than duplicated.
- **`missing: refuse` on a relationship** does not move the selected record
  (`RELATION_TARGET_LEFT_BEHIND` on the record), as `setMissing` documents; `missing: create`
  creates the other end under its counterpart ID with its mapped values.
- **Refusals beyond D121:** a retired source as well as target (`WORKSPACE_RETIRED`), `404
  PUBLICATION_NOT_FOUND` for another workspace's publication, `404 OBJECT_NOT_FOUND` for a subtree
  or selected record the source lacks, each at `details.path`. A source whose release changed since
  the move was sent fails the job with `MODEL_RELEASE_CHANGED`.
- **The startup message for missing extensions** now names three (`pg_trgm, btree_gin and
  pgcrypto`) and says search indexes and moves need them. J12.4's approved case was edited for
  D120 only: its list of extensions to install gained `pgcrypto`; what it checks is unchanged.
- **The volume check** is `tests/test_move_statements.py` (groups `volume` and `move`): 124
  statements for 50 and for 500 selected records, each with a relationship left behind.

**Checks (2026-10-18):** J38.2 written first (`tests/journeys/test_j38_2_move_dry_run.py`, 7 tests,
14 cases on generated-a and generated-b), all failing with `404` (no route) or `422` (no `move` job
kind) before the change; after it all 14 pass. Unit: `tests/unit/engine/moves/test_move_binding.py`
(4: carried, ignored and read-only attributes; a period carried, dropped and named; the target's
required relationships; D118's order on the seed: counterpart, then match, then create) and
`tests/unit/engine/records/test_counterparts.py` (`rdm_counterpart` held to `counterpart` over 200
generated pairs); 7 passed. Groups `move`, `jobs` and `startup` with `-n auto`: 755 passed and 2
failed, J12.4 on both configurations (the extension list, above), which then passed; the serial part
(1) passed; 5 min 8 s, over the package ceiling (TODO). `startup` gained a case for `20261021_01`
(an interrupted run refused naming `rdm_counterpart`, two starts answering a move, the function's
value, `pgcrypto`, a downgrade). `contract`: the lock, API_JOURNEYS' route line, parameters
(`outcome`, `reason`) and code (`MOVE_MAPPING_HAS_PROBLEMS`); 76 passed. `volume`: only
`test_move_statements.py` (2 passed); the group's full-size budgets were not run (nothing they
measure changed). **Smoke start** on a copy of the development database (3 workspaces, 2,380
records) taken back to `20261020_01`: the start upgraded it to `20261021_01`, `/health` and
`/system` 200; a mapping from the default workspace (2,129 records) to another workspace was created,
inferred and applied without problems, and a whole-workspace dry run completed with 4,562 rows: 4,554
`create` and 8 `refused` with `RELATION_CANDIDATE_REFUSED`, relationships the source holds although
its own model's candidate rule no longer admits them (the record's category does not contain
"reserved"); records and unique-value rows (15) unchanged; the copy dropped. `ruff check` on the
changed files clean. **Not run:** the full suite, Vitest, the browser runners and the gates (no
frontend change; build acceptance R).

**Found:** the development server (`uvicorn --reload`) applied `20261021_01` to `rdm` as soon as the
file was saved; it was written in one go, so `rdm` holds the complete revision (`pgcrypto`, the
function, the kind). X1's missing `ix_jobs_mapping` on `rdm` remains (TODO).

**What the user still cannot do:** load the dry run into a change set, move rather than copy, or move
a record back to its original (X3); edit the mapping and read the dry run in the browser (X4).

#### X3: The move

**Design:** D16, D17, D23; the move inventory I1–I34. **Needs:** X2.

**Scope:** the move into a reviewed change set of the target workspace: identity as counterparts
(found again on a second move, D16), each moved record's origin stored in a table of its own so a
record moved back finds its original (D23); copy by default, move as a copy plus the source's deletion in
a change set of the source workspace (D17); relationships, hierarchy, values, lookups, translations
and effective periods as the inventory decides; the target's audit naming the move and its source;
the target's subscribers receiving events on publication as for any change set.

**Groups:** `move`, `jobs`, `change_sets`, `events`.

##### X3 plan (2026-10-18)

**Planned 2026-10-18; D128–D137 as recommended and the test cases (with the edit of X2's J38.2 state assertions, D128) accepted by the user the same day ("All good, you can go ahead").**
Checked against the code at `cc33d56`:

- **X2's job ends `completed`.** `move_job.preview` runs every input through `run_items`
  (`previewing=True`), rolls back, records the rows and completes; `MoveRequest` accepts `mode:
  copy` and `stage: preview` only. The inputs stay in `job_inputs` after the preview, each holding
  its batch item, so a load can run exactly what was previewed.
- **An import's confirmation is the pattern.** `jobs/store.await_confirmation` and `confirm_job`
  hold a previewed job in `awaiting_confirmation` and queue it again; `POST /jobs/{id}/confirm`
  dispatches by kind (a migration has its own confirmation, `confirm_migration`). A preview past
  its retention is `410 JOB_EXPIRED`.
- **A job's writes already name it.** `run_items` writes under `audit_cause(session, "job", id)`,
  so every change-set entry a load writes carries `cause: {kind: job, id}`; publishing writes the
  live entries with the publication as cause. A record's history (`object_history`) reads every
  entry naming the record, change-set entries included.
- **Deleting with its own relationships exists.** `records/deletion.delete_records` with
  `Deletion(own_links=True)` (0.10 A5c, D104) deletes a record with its own relationships and
  refuses one that others depend on (a child, a record a required relation ties to it) with
  `OBJECT_HAS_DEPENDANTS`; items deleted deepest first are decided in one run, live or in a change
  set (`ChangeSetScope`).
- **Nothing records where a record came from** (P0's check); X2's binding finds a target record
  by counterpart (`rdm_counterpart`) or the mapping's `match` only.
- **Change sets are independent.** Publishing one checks nothing about another; a change set
  created without a source is an overlay on live data, pinned to its workspace's release.

**What is built:** the confirmation that loads a move's preview into a new change set of the target
workspace, `stage: execute` for the same without waiting, `mode: move` with its deletion change set
in the source workspace, the origins table and the move back, and the origin on a record's history.
A migration (`20261022_01`, the table `record_origins`), `engine/moves/move_load.py`, the binding's
origin step, the worker's load step, the OpenAPI lock re-baselined. No UI (X4), so no mock-up.

**Decisions** (D128 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D128 | The job's stages | **`stage: preview` now waits in `awaiting_confirmation`** after the dry run, as an import's preview, and `POST /jobs/{id}/confirm` loads it; **`stage: execute`** binds and loads at once, with no wait. Why: D114 planned it; an integrator who has read a dry run before needs one call, as with imports. Cost: X2's approved J38.2 cases assert `completed` after a preview; they change to `awaiting_confirmation` (an edit of approved cases, which this acceptance covers), and a preview nobody confirms expires after the job retention, as an import's |
| D129 | What a confirmation loads | **The preview's stored items, as reviewed:** the source as it was read at the preview (I30), decided again against the target at the load, policy `independent`; the load's outcomes replace the preview's rows, as an import's execution does. Why: what the user reviewed is what loads; a source change after the preview is the next move's (I30). Cost: a source change between preview and confirmation is not carried; the summary names both feed positions so a client can see that the source moved on |
| D130 | Where it loads | **A new change set of the target workspace**, pinned to the target's release, named `Move from <source workspace> (<job ID>)`, opened for review; never live data, never an existing change set. Why: D20 (nothing reaches the target until it is published) and a preview whose target is live data needs nothing else; loading into an existing change set would need the binding to read change-set content. Cost: a move combined with other edits is two change sets; renaming uses the existing `PATCH /change-sets/{id}` |
| D131 | Refusals at the confirmation | **Checked before anything is written, the job left waiting:** `409 MOVE_MAPPING_CHANGED` (the mapping's version moved since the preview, I31); `409 MODEL_RELEASE_CHANGED` (either workspace runs another release than the preview's, I32); `409 WORKSPACE_RETIRED`; **`422 MOVE_NOTHING_TO_MOVE`** (new: no row is `create`, `update` or `updateOriginal`); plus the existing `409 JOB_NOT_AWAITING_CONFIRMATION` and `410 JOB_EXPIRED`. A confirmation needs both gates, as the submission (D14, I33). Why: an empty change set is noise, and the others are the inventory's. Cost: one new code |
| D132 | The origins table (D23) | **`record_origins`: the record ID (key), its workspace, the origin workspace and record ID, the job and when**, one row per record a move **creates**, written by one `INSERT … SELECT` in the transaction of the chunk that creates the records. A record found by counterpart or `match` gets none (it has its own identity). Rows stay when the change set is discarded: they speak about an ID only that one source can produce, and every lookup joins a record that exists. Why: D23 accepted; one table, no change to the computed IDs, so J5's imports are unchanged. Cost: one table and an index on the origin record |
| D133 | Moving back (I3) | **The binding looks for an origin first:** a selected record, a parent or a relationship's other end whose chain of origins (followed in one recursive query, at most `MAX_LEVELS`) reaches a record of the target workspace of the mapped type is that record: `updateOriginal` with `foundBy: origin`. When the original was deleted (a move deleted it) and its ID is free, it is **created again under its original ID** (`create`, `foundBy: origin`) and gets no origin row. Then counterpart, `match`, create, as D118. Rows of moving records name their `origin` when they have one. Why: "a record moved back finds its original" (J38.6), along chains of moves too. Cost: one recursive statement per move, whatever its size |
| D134 | `mode: move` (D17, I6) | **After the load, one new change set of the source workspace** (`Move to <target workspace> (<job ID>)`) deletes every selected record whose row was loaded (applied `create`, `update` or `updateOriginal`) and whose version in the source is still the one read, deepest first, each with its own relationships (`own_links`). Kept in the source, with the reason on the row's `source` (`{outcome: deleted / kept, reasons}`): a record changed since it was read (`SOURCE_CHANGED`), one that a record staying depends on (`OBJECT_HAS_DEPENDANTS`, such as a child whose type is not mapped). A refused or not-moved row is never deleted. A move from a publication compares with live data the same way. Why: I6 as accepted, through the deletion path A5c uses, so nothing that stays is deleted with it. Cost: none beyond the change set |
| D135 | Publishing the deletion before the copy | **Guarded:** publishing a move's source change set while its target change set is not published is `409 MOVE_COPY_NOT_PUBLISHED` (naming the target change set); once the copy is published it publishes as any change set; with the copy discarded, the deletion can only be discarded. Why: principle 7, nothing dropped silently: without it, publishing the deletion and discarding the copy loses the records. Cost: one check when a change set publishes (a job naming it as its source change set) and one code; D17's "reviewed on its own" stays true for everything else |
| D136 | History, publications and events (I25, I26, I29) | **The load's entries carry the move's job as cause (as any job), and a cause that is a move gains `origin` (`workspaceKey`, `objectId`) on `GET /objects/{id}/history`**; the job's rows carry `origin` too. The source's history and publications are not copied. The target's consumers see nothing until its change set publishes, then its ordinary events (D20); the source's deletion change set likewise. Why: the inventory's cases with the existing audit and events. Cost: the history entry's `cause` gains one optional field |
| D137 | Where the code lives and the volume check | **`engine/moves/move_load.py` (confirmation, load, origins, the source's deletion), the origin step in `move_binding.py`, the worker's load step, migration `20261022_01`.** D123's statement count gains the origin step and stays the same for 50 and 500 records; the load itself is the batch path, as an import's execution, and its full-volume figure is X5's. Translations (I23), effective periods (I24), lookups (I14) and relation attributes (I19) load as X2's binding built them: nothing special. Why: D113's home. Cost: none |

**Journey test cases** (`tests/journeys/test_j38_3_move.py`, J38.2, J38.3, J38.6, J38.8, `move`;
W1 on X, W2 on Y with X and Y generated-a and generated-b, both directions, naming no key; the
mapping proposed and applied as in J38.1):

1. **J38.2 and J38.8 A copy confirmed and published.** Given a whole-workspace preview waiting in
   `awaiting_confirmation`. When it is confirmed, the job completes naming a new change set of W2
   that holds every `create` and `update` row's record under its target ID; W2's live records, feed
   and consumer events are unchanged, and W1 is untouched. When the change set is published, the
   records are live in W2 and W2's consumer API has an event for each; a moved record's history
   names the move's job as cause with its `origin` in W1.
2. **J38.6 A second move found again.** After case 1 and a value changed in W1, the same move's
   rows are `update` with `foundBy: counterpart`; once confirmed and published, W2 holds as many
   records as before, with the changed value.
3. **J38.6 Moving back.** After case 1, a move from W2 to W1 through the reverse mapping: the
   records that came from W1 are `updateOriginal` of their originals (`targetId` the original ID,
   `origin` named); a record created in W2 itself is `create`. After a `mode: move` (case 4) whose
   deletion is published, moving those records back creates them again under their original IDs.
4. **J38.3 Move a subtree.** `mode: move` with `parentObjectId`, confirmed: W2's change set holds
   the copy, and a new change set of W1 deletes the loaded records; a record under the subtree whose
   type is unmapped keeps its parent in W1 (`kept`, `OBJECT_HAS_DEPENDANTS`); a record changed in
   W1 after the preview is copied as previewed and kept (`SOURCE_CHANGED`). Publishing W1's change
   set first is `409 MOVE_COPY_NOT_PUBLISHED`; after W2's is published it publishes, and the deleted
   records are gone from W1.
5. **J38.2 `stage: execute`.** A move sent with `stage: execute` completes without waiting, with its
   change set and the same rows a confirmed preview would have.
6. **Refusals at the confirmation.** The mapping changed after the preview `409
   MOVE_MAPPING_CHANGED`; W2 activated on another release `409 MODEL_RELEASE_CHANGED`; a preview
   with nothing to create or update `422 MOVE_NOTHING_TO_MOVE`. Each leaves the job waiting and
   creates no change set.

Unit tests: the origin chain (two moves A → B → C, then back to A, finds A's record; a deleted
original found for re-creation only while its ID is free). Volume: D137's statement count.

**Groups:** `move`, `jobs`, `change_sets` (the publish guard), `events` (case 1's events),
`startup` (the migration), `contract` (the route changes; the lock re-baselined after diffing),
`volume` (D137). No frontend change.

**Composable domains (ADR-032):** identity: an origin is a lookup beside the computed ID, never a
change of it, so the retired-ID redirect door stays open; audit/history: a history entry's cause
gains the origin; bulk APIs: the load is a job with an import's rows.

**What the user still cannot do after X3:** edit the mapping, read the dry run and start the move in
the browser (X4); the figure for a move at full volume (X5).

##### X3 record (2026-10-18)

**Delivered 2026-10-18.** Built as planned (D128–D137): migration `20261022_01` (the table
`record_origins`, a change set's `waits_for_change_set_id`), `engine/moves/move_load.py` (the
confirmation, the load, origins, the source's deletion), `engine/moves/origins.py` (a history's
origin), the binding's origin step in `move_binding.py`, the worker's load step, the confirmation
dispatched by `POST /jobs/{jobId}/confirm`, the publish guard in `change_sets/publish.py`, and
`run_items`' `own_links` for the source's deletion; the OpenAPI lock re-baselined after diffing the
document against `cc33d56` (only the `Move*` summary and row fields, `RecordOrigin` on a row and a
history entry's cause, the rows' `updateOriginal` filter and the confirmation's description); no
frontend change.

Where it differs from the plan:

- **The load's change sets are opened over current live data**, as the change sets the UI opens
  (`source: currentLive`): the base is copied in the job's transaction under share locks on the
  workspace and its release assignment (`lifecycle.open_job_change_set`). The plan's check said a
  change set without a source is an overlay on live data; it reads from an empty base, so the
  load's updates were refused (`REFERENCE_NOT_FOUND`) until this was found by J38.3's case.
- **No source change set is opened when nothing would be deleted** (every loaded record kept); the
  summary's `sourceChangeSetId` is then null.
- **`record_origins` is indexed by its workspace**, not by the origin record: a deleted workspace
  deletes its rows (`delete_workspace`), and no read goes from an original to its copies.
- **A history's origin is named on every entry a move caused**, the later moves updating the record
  included (D136 named the move's job).
- **The gates.** A move job is created only through `POST /moves`, registered with both gates; its
  confirmation is on the jobs route, registered with `INTEGRATION_JOBS_ENABLED`, as a migration's
  is, so switching model administration off after a dry run does not stop its confirmation. No
  route refuses by gate today (a gated group is not registered), so a refusal would need a new code;
  left as built (D131 said both).
- **Also changed:** the rows' `outcome` filter accepts `updateOriginal`; `stop_job` leaves an item
  that has a row as it is, since a move loads its items beside the rows its mapping decided (a load
  stopped mid-way would otherwise write a second row); X2's statement-count test asserted
  `completed` after a dry run and now asserts `awaiting_confirmation` (D128, as J38.2's cases).
- **The test cases as written:** case 1's events come from the target's model with its consumer API
  telling every change of the ledger type (the generated configurations declare no events); case
  3's second half (re-created under the original ID) ends case 4's test, which deletes the original
  first; case 4's record kept for a dependant is a ledger whose entry type is unmapped, in a first
  move of its own.

**Checks (2026-10-18):** J38.2, J38.3, J38.6, J38.8 written first
(`tests/journeys/test_j38_3_move.py`, 6 tests, 12 cases on generated-a and generated-b), all failing
before the change (the dry run still `completed`); after it all 12 pass. Unit:
`tests/unit/engine/moves/test_move_binding.py` gained the origin chain (two moves, then back; a
deleted original re-created while its ID is free; under the counterpart once it is taken), 5
passed. Groups `move`, `jobs` and `startup` with `-n auto`: 771 passed and 1 failed (the
statement-count test's state, above), which then passed; the serial part (1) passed; 2 min 59 s,
inside the 3-minute ceiling (D127) at a load of 3. `startup` gained a case for `20261022_01` (an
interrupted run refused naming `record_origins`, two starts answering a confirmation, the column,
a downgrade). `change_sets`, `events` and `contract` (outside those three): 536 passed in 2 min 30
s, the serial part (2) passed. After the rows filter changed: `test_openapi_contract.py` and
`test_api_journeys.py`, 14 passed. The record history and workspace deletion journeys (J1, J7, J19),
52 passed. `volume`: only `test_move_statements.py` (2 passed; the binding's origin step is one
statement, the counts for 50 and 500 records equal); its full-size budgets were not run. After the
final formatting: the move tests again, 33 passed. **Smoke start** on a copy of the development
database (3 workspaces on one model, 2,380 records) at `20261021_01`: the start upgraded it to
`20261022_01`, `/health` and `/system` 200. A mapping from the default workspace (2,129 records) to
an empty one, inferred and applied: the whole-workspace dry run waited with 4,554 `create` and 8
`refused` (`RELATION_CANDIDATE_REFUSED`, as in X2) in 9.8 s; confirmed, it loaded into a change set
in 10.9 s, which published in 11.4 s. The reverse mapping's dry run found all 2,129 records as
`updateOriginal` by origin (2.7 s). A second `mode: move` of 20 records: 20 `update` by
counterpart; the source change set deleted 3 and kept 17 (records with dependants that stay); its
publication was refused `MOVE_COPY_NOT_PUBLISHED` until the copy was published, then succeeded.
The copy dropped, the server stopped, the scratch files removed. `ruff check` on the changed files
clean; `ruff format` on the new and previously formatted files only (the others differed from the
formatter before this package). **Not run:** the full suite, Vitest, the browser runners and the
gates (no frontend change; build acceptance R).

**Found:** in the smoke run, the 20-record `mode: move` took 13.3 s from its confirmation to its end
in the running service, seconds after the 2,129-record publication; driven step by step on the same
copy it is 0.9 s of work, so the rest was waiting, most likely behind that publication's background
work; not traced further (TODO, for X5's full-volume measurement).

**What the user still cannot do:** edit the mapping, read the dry run and start a move in the
browser (X4); the figure for a move at full volume (X5).

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

##### S1 plan (2026-10-18)

**Planned 2026-10-18; D124 and D125 accepted by the user the same day ("You can go ahead with s1"), with the go-ahead for D125's measurement.**
Checked against the code at `a73d667`:

- **The suite holds 5,952 cases in 201 modules** (5,771 at 0.10 R). The largest journey module is
  J34 with 112 cases (48 at A6a), each building a draft, profiling a workbook and running its jobs.
- **Every module runs on one worker.** `pyproject.toml` sets `--dist loadfile` (H2, 2026-10-01), so
  a module's cases run one after another on a single worker whatever their number. The run cannot
  finish before its slowest module, and J34 alone took about 2 min 15 s at 48 cases.
- **Journey cases share nothing with their neighbours.** The `world` fixture is per case: a clone of
  the configuration's seed and an application started on it (`journeys/scenario.py`). No fixture
  under `tests/journeys/` or `tests/unit/` is module, class or package scoped. 19 of the older
  modules have module-scoped fixtures, and they share the worker's session database, so they keep a
  worker to themselves.
- **Shared state between workers is safe except for one file.** Seed builds take a PostgreSQL
  advisory lock (`seeds.ensure`). `scenario.model_path` writes the configuration's model file in
  the temp directory in place, so a worker starting the same configuration at the same time could
  read it half-written. Today that needs two modules on one configuration to start together; once
  cases spread out, all workers start on one configuration at once.

**What is built:** journey cases are spread over the workers one at a time; every other module stays
together on one worker (as built: a scheduler in `tests/conftest.py`, below). The model file is written to
a temporary file and moved into place. EXECUTION_GUIDE §1 and TEST_HARNESS_PLAN (H2) say how the
run distributes. No product code changes; no migration; no journey changes.

**Decisions** (D124 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D124 | How the slow journey modules get their time back | **Spread journey cases one at a time over the workers; keep every other module on one worker.** TODO's "split J34 so its cases spread over the workers" done for every journey module at once, with no test file edited, and J35 or a future large module never needs it again. Why only journey tests: the `world` fixture already gives each case its own database, while the older modules share a worker's session database and module fixtures. Cost: a module-scoped fixture added to a journey module later would run once per worker that takes its cases; EXECUTION_GUIDE says so |
| D125 | How the result is measured | **Once, after the change: the full suite in parallel, then its serial part, on your go-ahead, with the time of each module kept in the scratchpad (expected 5–9 minutes).** No baseline run: 0.10 R's 8 min 31 s is the before figure (5,771 cases). Under 5 minutes meets the exit. Over it, I stop and report which modules hold the time and the options, chiefly TODO's other approach (W1 profiled once per configuration as a seed the cases clone), and run nothing more without your go-ahead. Why: the spread may be enough on its own, and the seed is the larger change |
| D126 | The ceiling, after both measurements (added 2026-10-18) | **Accepted 2026-10-18:** keep D124's spread; the full suite with `-n 6` (10 min 15 s, load 11–19 after start-up) rather than `-n auto` (8 min 49 s, load near 145); its ceiling 11 minutes, recorded as revised. Why: summed test time is about 6 minutes over 10 cores even uncontended, so only less work meets 5 minutes. Cost: about 1.5 minutes more per full run |
| D127 | The package ceiling (added 2026-10-18) | **Decided within the approved S1:** 3 minutes, as D126 for the full suite: `move or jobs or startup` holds 1,542 s of test work (2 min 36 s); the W1 seed not built |

**Test cases:** none new. S1 adds no journey; the harness change is checked by the measurement and
by J34, J35 and one older module with module fixtures run in parallel, which must pass as before.

**Composable domains (ADR-032):** no door affected; test harness only.

##### S1 record (2026-10-18)

**Delivered 2026-10-18.** D126 accepted by the user ("okay"): the exit is revised, not met.

**Built:** `tests/conftest.py` supplies the run's scheduler (`pytest_xdist_make_scheduler`): xdist's
file scheduler with `layout.worker_scope` as its unit, a journey case alone and any other test with
its module. Not `--dist loadgroup` as planned: xdist renames every grouped test's ID in parallel runs
only (`…@group`), so testmon's records would differ between parallel and serial runs; the scheduler
leaves IDs as they are. `scenario.model_path` writes the model file to a temporary name and moves it
into place. Unit test `test_a_journey_test_goes_to_a_worker_alone_and_any_other_with_its_module`;
EXECUTION_GUIDE §1 and TEST_HARNESS_PLAN H2 describe the distribution.

**Checks:** `tests/unit/harness/test_layout.py` 6 passed. J34, J35 and `test_batch_statements` with
`-n auto`: 136 cases in 1 min 10 s (J34 alone took 5 min 3 s in M1); J35's 8 known failures (TODO,
since V1). Ruff check clean on the changed files.

**D125's measurement (load 6.7 at the start, 94–145 during the run):** `pytest -n auto -q` 5,939
passed and 11 failed in **8 min 49 s**; the serial part 3 passed in 11 s. **The exit is not met.** The
cause: the test time added up is 5,018 s (83.6 min), 8.4 min over 10 workers, so the workers stay
busy to the end and the run is bound by the total work, no longer by one module. Journey tests hold
3,141 s, the rest 1,877 s; the largest modules are J34 617 s, `test_mapping_replacement` 159 s,
`test_startup` 150 s, J30 delivery 127 s, J27 import 121 s, J12 107 s, J29 104 s,
`test_change_set_position_reads` 102 s. The failures fail alone and at `a73d667` too, so not S1's:
J35's 8 (TODO), and two new to TODO (`test_unique_values::test_the_rows_follow_the_active_release`,
`test_j27_export::test_a_cancelled_failed_or_expired_export_serves_no_file`). Per D125 nothing more
was run; the options went to the user.

**A second measurement, six workers, on the user's go-ahead (load 4.5 at the start, sampled every
30 s):** `pytest -n 6 -q` 5,938 passed and 12 failed in **10 min 15 s**. The load peaked at 58 in
the first minute, while the workers started, and stayed between 11 and 19 after it. The test time
added up was 3,568 s against 10 workers' 5,018 s: each test ran about 30% faster with fewer
workers competing for the cores. The twelfth failure is TODO's known
`test_startup::test_upgrade_to_the_profile_check_kind_keeps_jobs_and_an_interrupted_run_recovers`
(seen in V1 and V4, passes alone). Even uncontended, 3,568 s over 10 cores is about 6 minutes, so no
worker count meets the 5-minute ceiling; only less work does.

**D126 (accepted 2026-10-18):** the journey spread stays; the full suite runs with `-n 6`, so the
machine stays usable during R; its ceiling becomes 11 minutes (TEST_HARNESS_PLAN, EXECUTION_GUIDE
§1 and §3, AGENTS.md). Package runs keep `-n auto` and their 2-minute ceiling. Cost: about a minute
and a half more per full run than ten workers. W1 profiled once as a seed was not built: J34 is 617 s
of 5,018 s, about 30 s of a run.

**What the user still cannot do:** nothing changes for the user of the engine.

**After delivery, at the user's request to leave no open items (2026-10-18):** the three failing
areas were test drift from M1's activation into one workspace, not defects: J35 activated into the
default workspace and loaded into its own (now `activate_everywhere`, as M1 changed J34); the J27
export changed the default workspace's release while exporting another (now its own); the unique
rows' test counted the retired workspace's row, which rightly stays (now per workspace). TODO's
`test_startup` flake was a real race in the harness's use of the worker: `run_until_idle` beside the
service's thread, both claiming under one lease owner, ran one chunk twice; `JobWorker.run_once` now
holds a lock, with a unit test seen failing without it. `test_startup` is spread like journey tests
(`layout.OWN_DATABASES`). **Checks:** J35 10 passed; the J27 case and `test_unique_values` passed;
the new worker test passed and failed without the lock; `move or jobs or startup` 758 passed in
2 min 36 s, then 2 min 44 s with `test_startup` spread (started at load 19), its serial part 1
passed. That selection was over the 2-minute package ceiling: 1,542 s of work, 37% of it J34.

**D127 (2026-10-18, within the approved S1 at the user's instruction to complete it):** the package
ceiling becomes 3 minutes (AGENTS.md, TEST_HARNESS_PLAN, EXECUTION_GUIDE §1), on D126's reasoning:
the 2 minutes were set at about 1,000 tests and a package on the job paths now holds about 1,500 s
of test work; the measured 2 min 36 s fits. W1 profiled once as a seed was not built. S1 has no open
items; `.gitignore` also ignores the database folders when they are links to `.nosync` folders.

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
| D2 | Where the suite's time (S1) goes, since D152 placed it first | **Accepted 2026-10-15:** as a filler while a Part 1 package waits for screenshot approval, at the latest before X2, whose packages run the slow `jobs` group. Cost: M1–M5 run their targeted groups on today's slow `jobs` group where they touch it. **Revised 2026-10-18:** X2 went first on the user's go-ahead with its plan; S1 follows X2 | S1 |
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
