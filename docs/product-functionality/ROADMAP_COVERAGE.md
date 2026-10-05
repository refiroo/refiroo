# Roadmap coverage from the user's perspective

This document translates the delivery roadmap into user outcomes. It does not treat a planned endpoint,
component or decision as delivered functionality. Release numbers are a delivery sequence, not calendar
commitments. The technical scope and exit gates are in the [delivery roadmap](../ROADMAP.md); what is
available today is in the [functionality catalogue](CURRENT_FUNCTIONALITY.md).

## Release overview

| Release | User outcome | Stories primarily covered | State |
| --- | --- | --- | --- |
| Base 0.5 | Stable bounded APIs and the application-model release lifecycle | US-I01–I02, US-P01–P04 | Delivered |
| 0.6 | Model-driven daily browser use and optional change sets | US-D01–D14, US-W01–W08, US-L01–L02, US-P06, US-U01 | Delivered 2026-09-11 |
| 0.7 | Review mapping coverage and replace one mapping atomically | US-M01–M04, US-W09 | Delivered 2026-09-25 |
| 0.8 | Work with translation coverage and deep hierarchies at any size | US-L03–L04, US-H01–H03 | Delivered 2026-09-29 |
| 0.9.0-alpha.1 | PostgreSQL runtime with real concurrency | — (no user-visible change) | In progress |
| 0.9 | Exchange and synchronise data at integration scale | US-I03–I09 | In progress: queries, `asOf`, bulk object jobs and consumer API definitions delivered |
| 0.10 | Turn spreadsheets into applications; edit models in one structured editor | US-P05 (additive), US-P09–P10 | Roadmap |
| 0.11 | Operate reliably with multiple writers and nodes, and staged models | US-O03–O04, US-O06, US-P07 | Roadmap |
| 0.12 | Authenticate every caller and authorise every operation | US-S01, US-O05 | Roadmap |
| 1.0 | Change released structure through the editor; reuse proven definitions | US-P05 (migrations), US-P08 | Roadmap |

## Delivered: 0.6 — Daily operations

**Acceptance:** SC-01–SC-06 and SC-08, with real-browser evidence for two configured record types at
desktop and narrow widths.

A steward finds, creates, corrects, connects, translates and deletes records in the browser, live by
default, with typed fields, relationships, parent changes, two-stage deletion and conflict recovery that
keeps the entered values. A change set is an explicit alternative: started from current live data or a
publication, validated, published as a delta over live data, or discarded. Workspace history lists
publications newest first, and withdrawing a publication keeps its history.

The simplicity rule holds for every later release: **a normal data edit is live by default; choosing a
change set is an explicit alternative, not a prerequisite.**

## Delivered: 0.7 — Core mapping and contextual collections

**Acceptance:** SC-07 (US-M01–M04) and SC-15 (US-W09), composed browser and API journeys.

One application browser groups a record type's views as lenses of its collection. A mapping grid shows
mapped, unmapped and ambiguous source values with counts and target previews, searches candidates on the
server and replaces one mapping atomically, live or in a change set, without a delete-then-create gap and
without overwriting a concurrent change. A change set can be prepared against a newer model release
while live data keeps the active one (ADR-028).

## Delivered: 0.8 — Relation matrix and hierarchy editor

**Acceptance:** SC-09 (US-L03–L04, US-H01–H02) and SC-17 (US-H03).

Collections of any size scroll continuously, with totals and jumps, in live data, change sets and
publications. A relation matrix shows translation and mapping coverage across a whole list and edits from
a cell. A tree lens browses and edits deep hierarchies lazily, with moves by menu or drag and drop, and in
a change set reshapes them (type changes, inserted and removed levels) with a preview. A review screen
lists everything a change set changes before publishing, and a Workspaces screen administers workspaces.

Both specialist lenses are generic: any application may declare them, and the generic record and
relationship flows remain an alternative (see [Capability preservation](#capability-preservation-across-releases)).

## In progress: 0.9 — Integration-grade APIs

**Why here:** extend validated single-record semantics to reliable larger exchanges.
**Acceptance:** SC-10–SC-11, stories US-I03–I09. SC-11 passes through the management API (Q4) and the consumer API (C16).

The interim release 0.9.0-alpha.1 moves the engine to PostgreSQL first: workspaces write in parallel,
and two writers racing in one workspace never break a rule. Users see no change.

### User outcome

External systems exchange and synchronize large reference datasets through stable, resumable contracts
rather than loops over user-interface operations or undocumented unlimited responses.

### Functions

Delivered:

- model-aware query across types, by ancestor and by a related record (F20);
- model-declared effective periods and `asOf` reads (F21);
- bulk create, update, upsert and delete as jobs, inline or in the background, with per-item outcomes,
  idempotency, progress, cancellation and resumption (F22);
- consumer API definitions in the model, with a breaking-change check at activation (F23); and
- the built-in API reference page (F24).

Remaining:

- bulk relationship and mapping items;
- an ordered change feed;
- the consumer APIs themselves: lookup by code across systems, lists, batch resolve, crosswalks,
  `asOf`, change events and webhooks; and
- asynchronous CSV/Excel import and export with a validation preview and an import screen (SC-10).

### Validation guardrails

- Every result is bounded or resumable.
- Partial failure and lifecycle state are machine-readable.
- Bulk behavior is a first-class service, not client-side repetition of one-item calls.
- Current type, relationship, workspace and concurrency rules still apply.

## Product 0.10 — Model authoring and spreadsheet onboarding

**Why before production controls:** reference data arrives in spreadsheets, and today each upload needs
hand-written model JSON and a bespoke import script. The editor's operations in 0.10 are limited to
additive changes and to structure that is not yet released, so they need no data migration.
**Acceptance:** SC-12 through the editor, stories US-P05 (additive and draft-only), US-P09 and US-P10,
and the exit gate in [MODEL_AUTHORING.md](../MODEL_AUTHORING.md).

### User outcome

A model administrator uploads a workbook, gets a proposed model and import mapping, renames, remaps and
reorganizes both while seeing the effect on the real rows, installs the model through the normal release
checks and reviews the data in a change set before publishing. The next version of the workbook loads
through the saved mapping and shows only its differences.

### Planned functions

- workbook upload and profiling (XLSX, CSV, several sheets);
- inference over common spreadsheet shapes, always as proposals with evidence;
- one editor for the model and the mapping: source, mapping and model panes, relationship matrix and a
  live preview rendered by the generic renderers;
- every edit a validated operation with history and undo; drag and drop with keyboard equivalents;
- generated default views and detail panels, edited in the preview;
- saved import profiles, executed by the 0.9 import job into a change set by default.

## Product 0.11 — Production hardening and staged model rollout

**Why it matters:** with 0.12, this is the gate for authenticated shared production use, not optional
polish. Earlier milestones are pre-production capabilities. **Acceptance:** SC-13, stories US-O03–O04,
US-O06 and US-P07, with measured operating and recovery targets agreed before validation.

### User outcome

Teams operate safely with multiple writers and nodes, while workspaces move between immutable models
through controlled migrations.

### Planned functions

- production-scale PostgreSQL performance evidence (PostgreSQL itself and single-node concurrent
  writers arrive in 0.9.0-alpha.1);
- database constraints as a second line behind the per-workspace write lock, where evidence calls for it;
- metrics and structured logs;
- rehearsed backup, restore and rollback;
- multi-node propagation of an activated immutable model;
- executable data-migration plans;
- model replacement for a change set started from a publication, with a preview of incompatibilities and potential data loss,
  explicit confirmation of the reviewed plan or cancel, and atomic workspace model/data application;
- workspace-specific model assignment and atomic staged switching; and
- an explicit supported window for schema-language versions.

Workspace model assignment is not merely a pin. The product must resolve the workspace before its
model, migrate its data, keep every permitted schema executable and prevent one request from combining
different model snapshots.

## Product 0.12 — Security, authentication and authorization

**Why it matters:** the security release, after everything else works; with 0.11 it gates shared
production use. **Acceptance:** stories US-S01 and US-O05, the identity part of SC-13.

### User outcome

Every person and system is authenticated, every operation is authorized in the same scope on every
path, and changes are attributed to a proven identity.

### Planned functions

- engine-provided OAuth 2.0 with JWT access tokens for the backend, frontend and consumer APIs; no API
  keys and no credential in a URL;
- application/record-type/operation authorization and per-definition consumer API access;
- HMAC-signed webhooks with rotatable keys;
- UI administration of OAuth clients and webhook subscriptions; and
- authenticated audit identity.

## Product 1.0 — Self-service model authoring and extensions

**Why after production controls:** changing released structure needs protected changes and safe migration.
**Acceptance:** SC-12 through structured controls, stories US-P05 (migration operations) and US-P08; demonstrate reuse with
two real configuration consumers before defining extension abstractions.

### User outcome

An authorized model administrator changes released applications with the 0.10 editor, including
changes that need a data migration, and reuses proven definitions.

### Planned functions

- the 0.10 editor's migration-class operations (key renames, splits, merges, cardinality changes on
  released structure), each with an impact preview;
- dependency visualization only where it improves comprehension;
- protected publish, activation and rollback on the 0.11 migration boundary; and
- reusable extension packages after two real reuse cases establish the abstraction.

The structured designer must not make a node-and-edge canvas the mandatory route for simple editing.
Installed releases stay immutable and unsafe changes remain blocked until an explicit migration
succeeds.

## Deliberately excluded product directions

The roadmap does not turn RDM Engine into:

- a general-purpose data catalogue, business glossary or lineage scanner;
- an enterprise governance suite unrelated to reference-data workflows;
- a product with starter-application-specific runtime branches;
- an unbounded synchronous data export service;
- a system where deployment capability flags are treated as user permissions; or
- a lifecycle where every individual record has to be drafted, activated or retired.

Source: [delivery roadmap](../ROADMAP.md), [current queue](../TODO.md) and
[ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-drafts-are-the-design-path).

## Capability preservation across releases

| Delivery adds | Existing user function it must preserve | Review question |
| --- | --- | --- |
| Optional change sets | Direct daily maintenance | Can I still correct a live label with one save? |
| Mapping grid | Ordinary relationship and target-record editing | Can I use the generic flow, and does it preserve mapping safety? |
| Relation matrix and tree | Generic related-record creation (translations among them) and parent editing | Can I complete the task without adopting the specialist view? |
| Bulk/import | Validation, scope and conflict protection | Do the same rules apply to every submitted item? |
| Identity and permissions | Permitted ordinary maintenance | Do authorized users still have a direct route to their task? |
| Structured designer | Inspectable, reproducible definitions and safe release controls | Can I understand and recover the active definition without opaque tooling? |

Approval workflow, duplication shortcuts and localized interface/model labels remain discovery topics.
No unscheduled candidate is implied to be part of 1.0. Use the decision table in the planning handoff
before adding release scope.
