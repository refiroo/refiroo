# Base 0.11 implementation plan

**Status:** Planning input, recorded 2026-10-15 after 0.10.0's release, from the conversation that
closed 0.10's R. Not a plan yet: the packages, their decisions and test cases are written in the
design pass (the first step below) and accepted by the user before any build. Everything here is
either the user's requirement (marked so), a conclusion reached with the user, or a finding with its
evidence; recommendations are marked as such and are not decisions.

**Target:** Product 0.11.0, [production hardening and staged model rollout](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout),
extended on 2026-10-15 by the user's two requirements below.

**Depends on:** 0.10.0 (released 2026-10-15, tag `v0.10.0`). 0.14 (another session's track:
the management API documented, the palettes, UP2's start page) blocks nothing here and is taken as
filler when the user asks.

## Why 0.11 next

Recommended to the user on 2026-10-15, not yet accepted as an order: 0.11 is the next release on the
roadmap, it had no plan, several of 0.10 R's findings belong to its scope (below), and its first
package is the one D152 placed in "the next build". 0.14 is filler work and is already being worked
on elsewhere.

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
ROADMAP now states the requirement in 0.11's scope and exit gate (commit `a0859ae`); the plan builds
on that wording, not on the older one.

**Not multi-tenancy.** Hosting stays one instance per organisation; per-workspace models are within
one organisation. The word "tenant" in DECISIONS and TODO conflicts with that rule and is corrected
in the design pass.

**What it touches (the engine assumes one active release today; to be checked in the design pass):**

- `model_runtime_state` is a singleton row naming the one active release; the registry resolves one
  snapshot per request. A request must resolve its workspace first, then that workspace's snapshot.
- `unique_attribute_values` and its triggers follow the active release only (J2a).
- The consumer APIs are those of the active release (Settings › Integration, the consumer tier, the
  event deriver, webhooks).
- Change sets already name a model release (ADR-028); publications pin theirs.
- Every read that spans workspaces: mapping coverage, the cross-type lookup (`GET /objects`), the
  feed, exports and imports naming other workspaces (0.9 J5).
- The job worker and dry runs resolve the active release (`dry_run_context`, `open_job_context`).
- The model editor's drafts: "New from a workbook" with a new model replaces the active model for
  every workspace until 0.11 (MODEL_AUTHORING).

**Decisions the design pass puts to the user, each with a recommendation:**

- What a workspace without a model of its own follows (presumably the instance's default release),
  and what happens to it when the default moves on (each workspace's own migration, or none).
- What reads spanning workspaces mean when their models differ (each item above), and whether
  relationships may ever cross workspaces of different models (the roadmap's groups entry notes data
  in different models cannot relate).
- Which schema-language versions may run side by side (DECISIONS: a bounded window, every pinned
  parser served concurrently).

### 2. Data moved between workspaces whose models differ

**Requirement (the user):** move (or copy) data between workspaces wherever their models are
compatible, even partly, with the mapping between them proposed by the engine and completed by hand;
"for this we should have literally everything which possibly can be needed". ROADMAP 0.11 holds it
in scope and exit gate (commit `a0859ae`). Its placement in 0.11, beside requirement 1 which it
needs, is Claude's inference: **the user is to confirm it, or move it to a release of its own.**

**Built from what exists (checked 2026-10-15):**

- 0.9 J5: another workspace's export loads as this workspace's own records, identity kept as
  counterparts and found again when the file is sent again.
- Import profiles and value maps (0.9 J2), edited step by step with undo by A5's mapping operations.
- A6/A7's inference: proposals with evidence and alternatives, matching by keys, names, values and
  stored records, drift reported; turned to a source model instead of a workbook, it proposes the
  model-to-model mapping.
- The dry run of every item (D67) and the load into a reviewed change set (A5b, A5c).
- The model compatibility analysis (`engine/model/compatibility.py`).

**New:** the mapping between two models (which type, attribute, relation and parent of the source's
model becomes what in the target's), proposed and completed as above, then the move through a dry
run and a change set; what cannot move is reported, never dropped silently.

**The inventory the design pass starts from** (the user asked for everything that can be needed;
first list, to be completed before any design):

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

## Findings from 0.10 R that belong to 0.11

- **Multi-process job worker:** the profile job held its file `FOR UPDATE` (R-F5), inference and
  the profile's statistics did not renew their lease (R-F6, R-F7), concurrent uploads did not
  supersede each other (R-F9). All fixed in R; 0.11's several processes and nodes need the whole
  worker (every job kind's long phases, leases, cancels) checked under real concurrency.
- **Statistics after bulk writes (R-F19):** a dry run's or a check's tens of thousands of fresh rows
  were joined before PostgreSQL's statistics saw them (95 s and 64 s of a 10,000-row check). Fixed
  for that path (outcomes inserted with their rows; `ANALYZE` before the summary); production-scale
  performance in 0.11 should look for the same pattern on every bulk path (imports at full volume,
  change-set captures, exports).
- **Job lookups (R-F14):** fixed in R with `job_parameter` and three partial indexes (migration
  `20261017_01`).
- **`NOT IN` subqueries** that may outgrow `work_mem` (TODO since 0.9 R): measure at full volume.

## First package: the test suite's time (D152)

**Decided in D152 (0.10 R):** the backend suite's time over its 5-minute ceiling is fixed in the next
build's first package, not in R. Measured at 0.10 R: the full suite 8 min 31 s (5,771 cases); the
`jobs` group alone near 6 minutes; J34 and J35 build a draft and profile W1 in every case.
**Approach recorded in TODO since A6a:** profile W1 once per configuration in a session fixture for
the cases that only read it, and split J34 so its cases spread over the workers.

**Why it matters beyond the ceiling (2026-10-15):** R's runs made the user's laptop unusable for
hours. The cause was mostly the machine's memory (swap full; about 40 Claude sessions' MCP server
processes), but R's suites, 49 browser runners and repeated gates multiplied it. Every later package
and R gets cheaper when the suite does.

## How release runs are done from now on (the user, 2026-10-15)

- Each heavy run (the full suite, the browser runners, a gate, a long measurement) is announced with
  its expected time and run only on the user's go-ahead, one at a time, never several test processes
  side by side because the machine has cores to spare.
- On a failure or a figure out of line: stop, report the cause and the options, ask before any
  rerun, diagnostic run or second measurement.
- Check the machine's load before a block; a failure under load is not evidence of a defect.
- Iterate on a new runner or helper with its smallest slice (one model, one walk), never the whole
  gate.
- Small verification runs (a handful of test files, one process) need no separate approval; the
  user does not want to approve every step.
- Clean up after every block: servers, scratch databases, the harness's PostgreSQL, output folders.

## Next

1. The design pass for 0.11 (as 0.10's A0): the decisions above with recommendations, the data-move
   inventory completed, the packages and their order (the test-time package first), journeys and
   test cases; accepted by the user before any build.
