# Testing strategy

**Decided** 2026-10-02 by the user, after an audit of the backend suite. It replaces the habit of
writing API tests per work package. The suite is moved onto it by
[H4](../TEST_HARNESS_PLAN.md#h4-testing-consolidation); until H4 is delivered, the
[execution guide](EXECUTION_GUIDE.md) still selects checks by group. The general findings and their
sources are in [LLM_TESTING_RESEARCH.md](LLM_TESTING_RESEARCH.md).

## What the engine is, for testing purposes

**An integration engine.** The API is the product. It exposes every capability the engine and the
model schema provide, so integrators can embed the engine or use it in ways the built-in UI never
does. The frontend is one client of the API, not the reason for it. A capability that exists in the
engine or the schema but cannot be reached through the API is a defect, even when the UI has no use
for it. An API option is never removed just because the UI does not use it.

So journeys are not only a steward's clicks. Integrators (another system paging, syncing, importing,
resolving identities), operators (starting, upgrading, recovering) and model authors are users with
journeys of their own, and the API's options are justified by theirs.

## The model: two kinds of tests

### Unit tests: the purpose of a piece of code

Every piece of code serves a purpose, and that purpose is tested, even where no specification
describes it in detail. A unit test exercises one module or function directly: no application
start, no HTTP, and a database only where the unit is a query or a write. Unit tests hold the code's
edge cases, its parametrization and its combinations. A combination space (contexts × sorts ×
directions, the "873 ways" of a button and a field) is generated, not written out: property-based
tests (Hypothesis) for rules that must hold for every input, pairwise selection for option grids.

Unit tests check behaviour, never internals: no spies on private functions, no assertion on which
internal path was taken. A statement or row count is a behaviour only where a decision fixed it as a
budget (the `volume` group).

### Journey tests: what a user achieves

Every journey and each of its variants has a test that walks it through the public API, written as
given/when/then, asserting what that user sees: the data, the status and the error code. Journeys
with a UI side also have a browser runner.

**The engine is tested, never the example model.** The example model delivered with the engine
(translations, systems, mappings) is one configuration of generic capabilities: records, hierarchies,
relationships within and across applications, and the rules the model declares on them. A journey
is stated in those terms, and its test runs on at least two model configurations that differ in keys
and shape (the example model and a generated one), asserting nothing that names a configuration's
keys. The [acceptance scenarios](../product-functionality/ACCEPTANCE_SCENARIOS.md) supply realistic
situations (two workspaces, a deep hierarchy, a large ambiguous set); the journey tests reproduce
the situation, not the example's domain.

**Every piece of code traces to a journey.** Mechanisms that no button shows have explicit journeys
too: the workspace write lock is "two stewards change the same codelist at once" and "an import runs
while stewards work"; the startup refusals are "the operator starts the service on the wrong
database". Many journeys may cover one capability in different ways; the link is many-to-many.

**Every way of doing something is a journey, a variant of one, or removed.** If a goal can be
reached ten ways, each way is either a journey of some client (UI, integrator, operator), a named
variant of one, or closed because no client needs it. Closing one is a product decision, and the API
contract principle above applies.

### What is not a test here

A test written by reading the code (it asserts what the code returns), a test per branch at the API
level, a database state no client could produce, a check of which private function ran, and a status
check without the error code.

## Choosing what to run

The code is a hierarchy: each piece is part of something larger, and every piece has unit tests.

| What changed | What runs |
| --- | --- |
| A piece at the bottom that others use | its unit tests, the unit tests of everything above it that uses it, and the journeys linked to any of them |
| A piece no other code uses | its own unit tests and its journeys |
| A piece at the top (a route, an operation) | its unit tests and its journeys. The data it needs comes through the real lower layers (API-built fixtures), so it is exercised as it would be in use. Lower unit tests are not rerun: their code did not change. If the top now uses a lower piece in a new way, that lower piece gets a new unit case |
| Data the code reads: the model schema, a migration, the starter model, seed code, configuration | treated as the bottom: everything that reads it |
| Anything, at release | everything |

Selection uses coverage, not file names: `pytest-testmon` records which code each test executes and
selects the tests whose code changed. Changes coverage cannot see (the rows of the last table line
but one) are rules in the execution guide.

## Traceability

- A journey test carries `@pytest.mark.journey("<id>")` with every journey or variant it walks.
- Which code a journey reaches is not written by hand: the coverage the journey tests record names
  the modules each journey executes. A module no journey test executes is reported: it is either
  dead code or serves a journey nobody wrote down.
- The catalogue lives in [USER_JOURNEYS.md](../product-functionality/USER_JOURNEYS.md): each
  journey with its variants, each variant with its scenario data, its channel (API, UI, operator)
  and the test that walks it.

## How a package uses this

1. **The catalogue first.** A package that adds or changes a capability a user reaches extends the
   [catalogue](../product-functionality/USER_JOURNEYS.md) in the same package, before its cases are
   written: a new journey or variant, its refusals by error code as API.md states them, and the
   route, parameter and code entries in [API_JOURNEYS.md](API_JOURNEYS.md) (the inventory check fails
   without them). Where the catalogue and API.md disagree, the package reconciles them; a behaviour
   neither document states is raised with the user, checked against the code first and asked in
   plain words (decided 2026-10-02, H4c).
2. **Specification first.** The package's spec section names the journeys it adds or changes. Their
   cases are written as given/when/then from the specification, in a context separate from the
   implementation (a subagent), and shown to the user as a short list before code is written.
3. **Confirm they fail** against the current code, for the reason the package addresses.
4. **Implement without editing them.** A case the code cannot pass is a code defect or a
   specification gap. A gap is recorded as a decision and the case changes only with the user's
   approval, never to fit the code.
5. **Unit tests for the new code's purpose** are written with the code, edge cases and combinations
   included.
6. **Evidence:** the selected run (testmon plus the journeys linked to the change), its counts, and
   what was not run and why.

## Quality meters

- **Planted faults.** A fault planted on purpose in a critical rule (a uniqueness check, a cascade,
  a version claim) must make a test fail; one that passes is a missing assertion. Used whenever tests
  are removed or moved (H4d) and when a package's own tests are in doubt. A full mutation tool
  (`mutmut`) was tried and dropped in H4b: about 1.5 hours to generate the engine's mutants before
  any test runs, and many hours to run them.
- **Journey coverage:** every catalogue entry has a test; every module is reached by some journey.
- **Time:** the [ceilings](../TEST_HARNESS_PLAN.md#time-ceilings) hold. A package's selected run
  should take under a minute.

## Findings that led here (audit, 2026-10-02)

Measured on one full parallel run: 1,063 backend cases in 74 modules, 2 min 17 s wall time, 989
test-seconds in cases over 0.3 s.

**Count and time.**

- 119 cases were renamed-model copies, 75 of them in modules where model keys never drive the code
  (consumer model compile 43, job mechanics 20, batches 12).
- About 30 write refusals were tested twice: `test_rule_parity` pins all 32, live and in a change
  set, and `test_api`, `test_attributes`, `test_relations` and `test_translations` repeat many.
- About 40 model rules were tested twice: in `test_model.py` (123 cases) and `test_model_diagnostics`.
- Mapping: 12 `test_list_mappings_*` tests predate the edge list that tests the same list under both
  routes; `test_mapping_replacement` has 74 cases, 20 of them one-step tests, and grids of up to 12.
- Time concentrated in a few tests: change-set position reads 100 s (one case 51 s, a slow read path
  in itself), mapping replacement 86 s, rule parity 56 s, mapping coverage 53 s, model query 52 s.

**Realism.**

- About 90% of the cases drive the real HTTP API on PostgreSQL: the boundary is real.
- The suite is organised by work package and review finding (`test_wp8_review_regressions`,
  `test_build07_wp11`, `test_wp81a_context` with tests numbered `test_0_…`), not by user goal. No
  test refers to a journey J01–J12. Of 17 acceptance scenarios, four have a backend test that walks
  them (SC-05, SC-07, SC-11, SC-15). The browser runners walk more (SC-01 to SC-09 in parts, SC-15,
  SC-17; corrected in H4a, which mapped them), but only through the UI, so no API-only client's path
  is walked as a journey; SC-10 (a supplier file) is planned.
- About a dozen modules write database rows directly: some build states no client can produce (a
  relation between two workspaces), others hand-build history that a real publish and activation
  would produce.
- Some tests check which internal function ran (a spy on `pagination._locate`; matrix reads made to
  refuse a private path).
- About 100 assertions check only that some 4xx came back, not which error.
- Found in H4b: seven modules replace the test client with one that sends every record and
  relationship call through a change set (`ChangeSetTestClient`), so at least 75 tests named as live
  operations never reach live code. A fault planted in the live relation read left "get relation by
  id returns stored relation" green.

**Process.** The tests were written after the code, by the agent that wrote it, from the code. This
is the failure the research describes: the tests confirm the implementation and cannot catch a
misread specification.

**Operations.** A smoke-start server left running for 15 hours wrote a 28 GB log when its database
stopped, because the job worker spun without waiting and logged a traceback on every pass (fixed,
with a regression test, in `engine/jobs/worker.py`). Three more servers from earlier runs, an
orphaned test database server and 17 GB of old SQLite copies were also left behind. Every server,
clone and log a run starts is now stopped or deleted before the run reports (AGENTS.md).
