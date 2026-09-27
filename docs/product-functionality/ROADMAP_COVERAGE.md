# Roadmap coverage from the user's perspective

This document translates the delivery roadmap into user outcomes. It does not treat a planned endpoint,
component or decision as delivered functionality. Release numbers retain the existing delivery sequence;
they are not calendar commitments. GAP-01–GAP-08 answers are accepted in ADR-027; unscheduled future details remain planning inputs.
The technical roadmap needs the reconciliations in [planning handoff](PLANNING_HANDOFF.md).

## Release overview

| Release      | User outcome                                                                | Stories primarily covered                  | Current state                                  |
| ------------ | --------------------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------- |
| Base 0.5     | Establish stable bounded APIs and the application-model release lifecycle   | US-I01-I02, US-P01-P04                     | Completed foundation                           |
| Product 0.6  | Complete model-driven daily browser use and optional workspace design       | US-D01–D14, US-W01–W08, US-L01–L02, US-P06, US-U01 | Current-live change set API available; browser gaps remain for WP9/WP10 |
| Product 0.7  | Review mapping coverage and replace one mapping atomically                  | US-M01–M04, US-W09                         | Roadmap                                        |
| Product 0.8  | Work efficiently with translation coverage and deep hierarchies             | US-L03–L04, US-H01–H02   | Roadmap                                        |
| Product 0.9  | Exchange and synchronize data at integration scale                          | US-I03–I09                                 | Roadmap                                        |
| Product 0.10 | Operate securely and reliably with multiple writers/nodes and staged models | US-S01, US-O03–O06, US-P07                     | Roadmap                                        |
| Product 1.0  | Author models through structured, reference-aware tools                     | US-P05, US-P08                             | Roadmap                                        |

## Product 0.6 — Finish daily operations

**Why first:** users need to complete ordinary maintenance before specialist screens add value.
**Acceptance:** SC-01–SC-06, SC-08 and the existing-workbench portion of SC-12; keyboard and recovery
checks apply throughout. Current-live change set creation (US-W08) is available through the API; its browser
source-selection journey remains a WP9/WP10 gap.

### What is already present

- catalogue-backed workspace selection;
- strict typed tables with server-side search, filtering, sorting and cursor pages;
- model-driven browser navigation and record inspection, with edit actions temporarily not wired into
  the detail journey;
- accessible interface foundations;
- API support for live and change-set-context record, typed-field, relation and translation maintenance;
- API support for change sets, whole-graph validation, conflict-aware activation, immutable history
  and publication withdrawal; and
- direct live maintenance while a change set is open, with activation that applies its changes over
  current live data and preserves unrelated work.

WP8.1-B captures the fresh live starting view required by ADR-026/027. The complete browser design
journey, including source choice, remains WP9 work.

### What WP9 must make usable in the browser

- Add/Edit/Delete for live records without requiring a change set.
- Optional switching into a selected workspace change set for coordinated changes.
- Typed field add/edit/remove actions.
- Ordinary relationship and translation actions.
- Parent/containment editing through the record rather than the engine-managed relationship.
- Two-stage deletion with impact preview.
- Workspace-level Change sets, History, validation, publishing and publication-withdrawal destinations.
- Newest-first workspace history, confirmed by the user in GAP-05 and implemented through WP8.1-C.
- Empty relationship and translation collections as successful empty states.
- Conflict recovery that preserves entered values and distinguishes record, change set, activation and model
  conflicts.

The important simplicity rule is: **a normal data edit is live by default; choosing a change set is
an explicit alternative, not a prerequisite.**

### What WP10 must prove

- real frontend-to-backend journeys across at least two record types;
- keyboard operation, focus behavior and narrow-screen use in a real browser;
- automated accessibility and visual-regression checks;
- live edits, staged invisibility, atomic activation and no-partial-publication failure paths;
- clean bootstrap, database upgrades, restart and interrupted-migration recovery;
- packaged installation on Python 3.14; and
- no skipped relevant record, typed-field, relation or translation suites.

### Explicitly outside 0.6

- a dedicated mapping grid or mapping replacement API;
- a translation coverage matrix or specialist tree view;
- bulk operations, imports, exports, change feeds or webhooks;
- authenticated permissions;
- model-workbench information-architecture redesign;
- a structured model designer;
- physical deletion of immutable history; and
- any individual record change set, publication, publishing or retirement lifecycle.

## Product 0.7 — Core mapping and contextual collections

**Why next:** mapping is a central RDM task that generic relationship editing does not make simple.
**Depends on:** usable live record/relationship maintenance, optional change set context and two proven
relationship configurations. **Acceptance:** SC-07, stories US-M01–M04; and SC-15, story US-W09 for
change set model-version selection (ADR-028).

### User outcome

A steward selects an unscoped or direct-parent collection from one application browser, changes its
semantic lens, and can see coverage and safely create, clear, replace or resolve one mapping without
managing low-level relationship records.

### Planned functions

- model-defined table and mapping renderers grouped as lenses of their source collection;
- one browser for virtual collection entries and bounded containment records;
- bounded rows showing mapped, unmapped and ambiguous states;
- server-side target search;
- one atomic replacement operation for zero or one chosen target;
- one concurrency version for the complete mapping set, including currently empty or ambiguous sets;
- conflict responses with bounded current-target context;
- creation of a missing target through normal workspace record creation where configuration permits;
- change set model-version selection, delivered in WP-6/WP-7 with WP-11 refusal/UI hardening, so one change set
  prepares under a candidate release while live data and other change sets keep the release in use
  (US-W09, ADR-028; composed acceptance remains WP-9); and
- mapping-transition audit in addition to underlying relationship history.

### Validation guardrails

- No request per displayed row.
- No delete-then-create gap.
- A relationship binding cannot accidentally replace another binding that shares a relationship type.
- Generic relationship operations cannot bypass mapping concurrency.
- Parent/containment and required ownership relationships are not presented as independently mutable
  mappings.

## Product 0.8 — Translation and hierarchy editors

**Why here:** generic translation and parent editing already have a defined foundation; specialist
views reduce repetitive navigation. These are separately gated outcomes and neither depends on using
the other. **Acceptance:** SC-09, stories US-L03–L04 and US-H01–H02.

### Translation outcome

A localization steward works by target and language, sees missing coverage and updates translations
without manually navigating the containment structure.

Planned functions:

- model-defined target/language matrix;
- bounded coverage query rather than a request per cell;
- distinction between missing, current and historical-only translations;
- in-context translation creation/editing; and
- uniqueness validation for the complete relevant graph.

### Hierarchy outcome

A steward browses and maintains large, deep, model-defined hierarchies through lazy loading.

Planned functions:

- strict typed tree configuration;
- bounded root and child loading with path context;
- contextual child creation;
- safe rename, availability and parent changes;
- cycle validation and atomic parent/path relationship updates; and
- keyboard, focus, loading and error behavior for mixed-type and recursive hierarchies.

### Live maintenance and optional coordinated design

ADR-026 is the existing product baseline: ordinary mapping, translation and hierarchy changes are
live; a change set is an explicit alternative for coordinated work. Apply this to the specialist
views and reconcile contradictory change-set-only wording in the technical roadmap before implementation.
A specialist screen must not introduce a mandatory release step for changing an ordinary value.

## Product 0.9 — Integration-grade APIs

**Why here:** extend validated single-record semantics to reliable larger exchanges.
**Depends on:** stable identity, data validation, explicit live/change set scope and mapping concurrency for
bulk mapping. **Acceptance:** SC-10–SC-11, stories US-I03–I09. Format, failure policy and business-date
semantics must be settled before their implementation packages.

### User outcome

External systems exchange and synchronize large reference datasets through stable, resumable contracts
rather than loops over user-interface operations or undocumented unlimited responses.

### Planned functions

- advanced model-aware query beyond configured daily-use filters;
- model-defined effective dates and “as of” reads where explicitly configured;
- bounded bulk create, update and upsert with per-item outcomes and idempotency;
- bounded bulk relationship and mapping operations;
- asynchronous CSV/Excel import and export with validation preview and resumable job status;
- ordered change feed; and
- retryable webhooks.

### Validation guardrails

- Every result is bounded or resumable.
- Partial failure and lifecycle state are machine-readable.
- Bulk behavior is a first-class service, not client-side repetition of one-item calls.
- Current type, relationship, workspace and concurrency rules still apply.

## Product 0.10 — Production hardening and staged model rollout

**Why it matters:** this is the gate for authenticated shared production use, not optional polish.
Earlier milestones are pre-production capabilities. **Acceptance:** SC-13, stories US-S01, US-O03–O06
and US-P07, with measured operating and recovery targets agreed before validation.

### User outcome

Authenticated teams operate safely with multiple writers and nodes, while workspaces move between
immutable models through controlled migrations.

### Planned functions

- PostgreSQL deployment and representative performance evidence;
- database-backed hardening of uniqueness under concurrent writers;
- OIDC authentication and application/record-type/operation authorization;
- authenticated audit identity, metrics and structured logs;
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

## Product 1.0 — Self-service model authoring and extensions

**Why after production controls:** easier authoring still needs protected changes and safe migration.
**Acceptance:** SC-12 through structured controls, stories US-P05 and US-P08; demonstrate reuse with
two real configuration consumers before defining extension abstractions.

### User outcome

An authorized model administrator evolves applications through structured, reference-aware tools
instead of relying only on raw JSON.

### Planned functions

- catalogues and forms for model definitions;
- relationship matrices and safe reference selection;
- useful live preview;
- dependency visualization only where it improves comprehension;
- protected publish, activation and rollback on the 0.10 migration boundary; and
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

Source: [delivery roadmap](../ROADMAP.md), [current queue](../TODO.md),
[Base 0.6 plan](../BASE_0_6_IMPLEMENTATION_PLAN.md) and [ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-change sets-are-the-design-path).

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

## 0.7 delivery refinement — planned

WP-1–WP-3 are frozen. Mapping coverage/actions are independently accepted in WP-8A/WP-8B;
WP-4/WP-5 define bounded view-specific reads and preserve selected relationship identity/attributes.
WP-6/WP-7 require whole-candidate compatibility, atomic pin changes and safe model-context refresh.
WP-9 proves independent bindings, same-schema differing releases, race/isolation behavior and the new
controls' accessibility/visual behavior. Conditional WP-10 addresses only confirmed foundation gaps.
See [the 0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md); these refinements add no delivery evidence.


## 0.7 mapping backend delivery and remaining story acceptance — 2026-09-14

WP-4 query and WP-5 replacement contracts are delivered. WP-5 acceptance includes an independent
binding and overlapping generic writes; WP-10A makes cascades invalidate continuations, and WP-10B
refuses divergent touched live mapping sets at publishing. Source/live identity/version
comparison preserves unrelated live work and permits a restored source graph. Validation: 486
backend tests, Ruff, frontend format/lint (zero errors, 12 existing warnings), 164 tests and build.
US-M01–M04 still require WP-8A/WP-8B browser delivery and WP-9 composed evidence. This API/component
evidence does not establish PostgreSQL concurrency or close SC-07 browser acceptance.
