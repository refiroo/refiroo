# From product needs to technical plans

## Authority and review boundary

This is the product planning input reviewed on **2026-09-08**, against working-tree base `60b99d3`
plus pre-existing uncommitted changes. The user subsequently accepted GAP-01–GAP-08 with the comments
preserved below and authorized technical documentation/planning updates. ADR-027 consolidates those
answers. Documentation acceptance does not close their implementation or validation work.

The product guide describes intended value; story acceptance describes the behavior to preserve;
the catalogue records availability; the roadmap sequences delivery. Newly detailed future acceptance
criteria are proposals for planning review, not evidence of implemented contracts. Existing accepted
decisions remain binding until explicitly amended. Where they conflict with code or older plans,
record the gap below instead of silently choosing the most convenient interpretation.

## Accepted gap resolutions — implementation and evidence still pending

| ID | Finding and user impact | Required planning action | Priority / stories | User decision (verbatim) |
| --- | --- | --- | --- | --- |
| GAP-01 | Detail requests omit workspace context and record controls are disconnected. A steward can select another workspace but cannot finish the task there. | Restore the complete live browser journey and preserve context through lookup, detail, history and return. Optional change set context must remain explicit.  | 0.6 blocker; US-D01–D12, US-L01–L02 | OK, Accepted. |
| GAP-02 | ADR-026 promises a fresh current-live change set base. `create_draft` currently creates an empty change set or points to a supplied immutable publication; it does not capture current live data. Live changes since the last publication are therefore absent from that starting view. | Specify and implement “start from current live data,” including a workspace with live records but no published publication. Retain separately labelled historical derivation. Add direct boundary evidence for SC-05.  | Before coordinated design is accepted; US-W01, US-W08 | OK, Accewpted. Creating a change set was always planned to make a copy of the actual active or a previously retired one. The empty change set was a temporary solution for the development phase, this has to be extended with the copy from active functionality. If a change set created from a preiously retired workspace is not compatible with the current active schema in case of publishing, then the merge functionality gives a warning on this and asks for comfirmation of overridding the active scheme with potential data loss, or cancel the publishing. |
| GAP-03 | “Restore from history” implies undo. Publishing applies only authored changes over live data; selecting an older base alone does not restore old content or remove newer records. | Rename the existing action to “start a change set from history.” Specify recovery as reviewed new changes. A full dataset rollback would require a separate explicit product decision and is not promised here. | 0.6 wording and acceptance; US-W07, SC-08 | Ok. The active cannot be restored from history. A change set be created from the active or a previous histroy, see GAP-03. |
| GAP-04 | Publication withdrawal clears the publication selection but retains live records; active reads use those live records. “Stop publishing” can be misread as withdrawing data from consumers. | Clearly distinguish removing the current publication label, making a workspace read-only, marking a business value unavailable and deleting data. Decide whether any future withdrawal operation is needed; do not infer one. | Before exposing retirement controls; US-W06, US-A03 | ok, Accepted. |
| GAP-05 | Current publications is oldest first, whereas the interaction baseline asks for newest first. | Align the history order or explicitly amend the interaction baseline; validate the user's ability to find the latest publication. | 0.6 history gate; US-W05 | Ok. Newest first. |
| GAP-06 | Technical 0.7 mapping, 0.8 hierarchy/translation and 0.9 bulk scope still includes mandatory change set wording. It conflicts with direct daily maintenance. | Rewrite those plans to offer live maintenance and an explicit optional design context under ADR-026. If an operation needs extra review, state its particular risk and obtain a product decision. | Before planning each specialist/integration release | Ok. Plans has to be rewritten based on the recent product functionality. |
| GAP-07 | Component and service tests are described as functionality evidence, but no composed browser proof is supplied here. | Attach actual executed scenarios, results, skips and limitations before changing availability to browser validated. | 0.6 WP10; all browser stories |Ok. the validations and testing have to be extended. |
| GAP-08 | A change set (data) and a model draft (application definition) are different tools. Some “design playground” wording suggests editing both together today. | Keep data coordination separate from definition release management. Treat coordinated schema/data migration and workspace-specific model selection as 0.11 work. | All lifecycle plans; US-W01–W08, US-P07 | Ok, accepted, these have to be different concepts. The documentation has to be upgraded accordingly. |

Read-only evidence inspected for this update (links repointed to the modules' current locations; the
findings describe the code as it was on 2026-09-08):

- [Change set creation and merge service](../../backend/app/engine/change_sets/):
  `create_draft`, `effective_change_set_membership`, `_merge_draft_over_live`, `retire_publication`.
- [Workspace routes](../../backend/app/management/routers/workspaces.py): change set creation forwards only the selected
  source publication; it does not add a current-live snapshot operation.
- [Record service](../../backend/app/engine/records/objects.py): `create_object_record` already accepts
  permitted initial relationships together with fields and containment, then commits once. The
  single-create acceptance scenario reuses that contract; it does not propose an arbitrary
  multi-record transaction interface. Fresh failure-path proof is still needed at release validation.
- [ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-drafts-are-the-design-path):
  direct live maintenance and the current-live starting-point requirement.
- [Object detail](../../frontend/src/features/objects/ObjectDetail.tsx),
  [application shell](../../frontend/src/app/AppShell.tsx) and
  [API adapter](../../frontend/src/api/client.ts): context and reachable-action boundaries.
- [Delivery roadmap](../ROADMAP.md), [interaction baseline](../BASE_0_6_INTERACTION_SPEC.md) and
  [Base 0.6 plan](../BASE_0_6_IMPLEMENTATION_PLAN.md): delivery scope and historical wording.

These are source-review findings. This task has not run application, browser or migration tests, and
does not certify every existing functionality claim. Existing test references remain pointers to
candidate evidence, not fresh pass results.

## Delivery order and product decisions

Retain the existing 0.6–1.0 sequence in [roadmap coverage](ROADMAP_COVERAGE.md). Complete ordinary
maintenance before specializing it. Production hardening is a prerequisite for claiming suitability
for authenticated, shared production operation even though its milestone follows the pre-production
specialist releases. The release numbers are sequencing labels, not promised dates.

For future features, settle these product questions when their milestone is planned:

| Milestone | Decision needed | Minimum constraint already established |
| --- | --- | --- |
| 0.7 mapping | Which configured relationships permit zero or one chosen target, and where may a missing target be created? | Required ownership and containment cannot be cleared as if they were optional mappings; concurrent replacement must not lose a valid mapping |
| 0.8 translation | Which languages/targets define expected coverage, and what does inactive or historical-only content mean in that view? | Do not count old or unusable content as a current completed translation |
| 0.8 hierarchy | How does a user choose a new parent in a large tree, including with a keyboard? | Preserve normal parent editing; reject cycles and show the resulting path |
| 0.9 exchange | Which file formats, duplicate keys, retry rules and batch failure policy are supported? | Preview before import; expose row outcomes; never hide a partial result behind “success” |
| 0.9 synchronization | What is retained, how are expired positions recovered, and how are repeated deliveries identified? | Do not promise exactly-once delivery; consumers must be able to reconcile retries |
| 0.9 effective dates | Which date boundaries, time zone and overlaps define a valid business-time answer? | Explicit configuration; distinct from audit time and publication history |
| 0.11 production | What access scopes, supported loads, recovery time and acceptable data-loss targets are required? | Prove them under representative operation; no invented numeric service guarantee |
| 1.0 authoring | Which definition tasks justify forms, matrices, previews or an extension mechanism? | Same validation and release safety as the existing definition workbench; demonstrate two reuse cases before generalizing |

Research candidates such as approvals, copy/duplicate and localized interface labels are uncommitted.
Keep them in discovery until a named user need, smallest useful flow, acceptance examples and roadmap
owner are agreed. Existing [research notes](REAL_WORLD_RESEARCH.md) remain a separate historical input;
this review did not refresh their vendor sources or adopt their proposals wholesale.

## Decision-to-delivery mapping

| Accepted resolution | Technical owner | Completion requirement |
| --- | --- | --- |
| GAP-01 complete workspace/live browser flow | WP9 | SC-01–SC-04 in composed browser, two record types |
| GAP-02 copy current live or historical content | WP8.1-B, then WP9 | SC-05 and concurrent snapshot/merge evidence; empty change sets are development/bootstrap support |
| GAP-02 incompatible historical schema replacement | Product 0.11 migration and workspace model assignment | Preview losses, confirm exact reviewed plan or cancel, atomic migration, unaffected workspace isolation |
| GAP-03 no direct restore | WP8.1/WP9 wording and merge checks | Historical source applies only authored changes; newer untouched data survives |
| GAP-04 truthful publication withdrawal | WP9, with service proof in WP8.1 | Remove designation; preserve live access and history; distinguish catalogue retirement |
| GAP-05 newest first | WP8.1-C, then WP9 history | Deterministic reverse chronological paging and exact retry |
| GAP-06 live specialist/integration flows | Roadmap 0.7–0.9 packages | Live default plus explicit optional change set; generic paths preserve the same rules |
| GAP-07 stronger validation | WP10 and each later release | Actual composed journeys and boundary evidence, not component-only acceptance |
| GAP-08 separate data/model drafts | ADR-027, WP9, product 0.11 | No data activation silently edits model definitions or global selection |
| GAP-08 stage a candidate release in an optional draft | ADR-028, product 0.7 | A draft is created against, or explicitly moved onto, an installed supported release; a draft the target does not already accept needs the reviewed 0.11 conversion; nothing forces a change through or moves a draft without being asked |

The historical-schema confirmation requested in GAP-02 is preserved as a planned capability. It is
not a current activation flag. The 0.11 workspace model-assignment/migration boundary avoids changing
other workspaces’ rules. An unsupported schema language still needs parser/runtime support. A
catalogue-retired workspace is read-only; historical derivation means a retired publication snapshot.
ADR-028 keeps a change set on a release the user chooses without changing any data. A change set whose
content the chosen release already accepts is a change set edit with no migration and no assignment; a
change set the chosen release does not already accept needs the reviewed 0.11 conversion. Either way a
change set edit never changes the release serving data.

## 0.7 plan review follow-up — 2026-09-12

WP-1–WP-3 are frozen; WP-1/WP-2 implementation review remains separate and WP-3 is in progress.
[The 0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md) assigns view-specific bounded mapping reads and
identity/attribute/cardinality semantics to WP-4/WP-5, whole-candidate atomic compatibility and full
browser model refresh to WP-6/WP-7, coverage/actions to WP-8A/WP-8B and expanded composed evidence to
WP-9. Confirmed foundation gaps trigger bounded WP-10 work before acceptance. These are planning
requirements, not findings from the pending implementation reviews or new delivered capabilities.

## 0.7 delivered mapping backend follow-up — 2026-09-14

WP-3–WP-5 are delivered. WP-5 review/acceptance covers retained identities, typed attributes,
independent bindings, ownership/clearing refusals, and overlapping generic relation writes.
WP-10A closes cascade token invalidation; WP-10B closes divergent touched-set activation by comparing
complete source/live edge identities and versions. The SQLite gate passes 486 backend tests and
164 frontend tests; this does not complete US-M01–M04 in the browser. WP-8A delivers coverage,
WP-8B actions/conflict recovery/contextual target creation, and WP-9 composed acceptance.
View-only mapping and modal target creation are resolved in the WP-8B handoff. WP-6/WP-7 deliver
non-active change set model selection; WP-11 delivers historical-schema refusal, pinned-model loading,
retry-aware shell errors and the established version-dialog presentation. Composed SC-15 acceptance
remains WP-9. Earlier plan-review evidence remains historical.

## Technical documentation update method

1. Reconcile GAP-01–GAP-08 with the current source and record each resolution or explicit deferral.
2. Update `PRODUCT.md` to distinguish the product promise, current channels and future capabilities;
   replace the historical restart-based success condition with a complete user task.
3. Update `PROJECT_STATUS.md`, `ROADMAP.md` and `TODO.md` so current scope says direct live editing
   plus optional coordinated design. Do not mark an API-only story complete for browser users.
4. Amend architecture, model, API and interaction documents where their present-tense lifecycle
   descriptions still contradict ADR-026. Keep superseded decisions labelled as historical.
5. Rewrite the next build/implementation package around the affected story IDs and acceptance
   scenarios, with concrete scope, exclusions and evidence requirements.
6. Run the applicable implementation gates, then update the product availability and evidence record.

This ordering makes the product baseline an input to technical planning. It does not treat existing
implementation details as a reason to redefine the user's job.

## Work-package contract template

Copy this into the next implementation plan and complete it before coding:

```markdown
User outcome:
Stories and acceptance scenarios:
Current channel and gap:
Target channel:
Smallest successful user flow:
Live / optional draft / history behavior:
Configured variation (at least two different record types or relationship configurations):
Failure, conflict and retry behavior:
Existing capabilities that must remain available:
Scope and exclusions:
Product decisions required and their resolution:
Technical contracts and migration impact:
Validation to execute (including the actual composed journey):
Documentation to reconcile:
Evidence, limitations and remaining roadmap ownership:
```

Acceptance cannot be weakened merely because the implementation passed its own tests. If a package
adds a screen, confirmation, mandatory field or lifecycle step, explain the user benefit or named risk
against the previous flow. Record capability removals explicitly for product review.
