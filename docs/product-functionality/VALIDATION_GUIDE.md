# Product functionality validation guide

Use this guide at feature review, work-package completion and release candidate gates. The goal is to
validate the user's job, not merely the existence of code, a route or a component.

This is a validation specification, not an execution report. The 2026-09-08 documentation review
checked source and document consistency only. Existing evidence descriptions below refer to test
coverage identified in the prior catalogue, not new pass results. Use the concrete
[acceptance scenarios](ACCEPTANCE_SCENARIOS.md) when executing these journeys.

## Evidence levels

| Level | Evidence                                                            | What it proves                                                |
| ----- | ------------------------------------------------------------------- | ------------------------------------------------------------- |
| E1    | Real browser against a real backend and temporary/isolated database | The composed user journey works.                              |
| E2    | API integration test against a real temporary database              | The supported service behavior and persistence boundary work. |
| E3    | Interface/component test                                            | The isolated presentation or interaction behaves as designed. |
| E4    | Unit or contract test                                               | A rule, conversion or public shape behaves in isolation.      |
| E5    | Accepted decision and roadmap only                                  | Intended future behavior; not delivered functionality.        |

“Browser implementation present” requires a reachable interface path, not merely an isolated E3
component. “Browser validated” requires E1. A passing suite with a skipped relevant journey is not
acceptance evidence.

## Core traceability matrix

| Story  | Function                          | Current strongest evidence                          | Release target                   |
| ------ | --------------------------------- | --------------------------------------------------- | -------------------------------- |
| US-D01 | F02 workspace selection           | E3 selector/list + E2 workspace API tests           | WP9 context fix; E1 in WP10      |
| US-D02 | F03/F04 list return state         | E3 routing; non-default detail currently fails      | WP9 context fix; E1 in WP10      |
| US-D03 | F03 typed find                    | E3 table tests + E2 typed-query tests               | 0.6 E1 proof in WP10             |
| US-D04 | F03/F16 bounded paging            | E2/E3 cursor tests                                  | Current; E1 proof in WP10        |
| US-D05 | F04 contextual detail             | E3 default-workspace panels across record types     | WP9 context fix; E1 in WP10      |
| US-D06 | F05 live create                   | E2 live-write tests; E3 disconnected form           | 0.6 WP9/WP10                     |
| US-D07 | F05/F17 live update               | E2 live-write/conflict tests; E3 disconnected form  | 0.6 WP9/WP10                     |
| US-D08 | F06 value semantics               | E2 attribute tests + E3 panel/editor tests          | 0.6 WP9/WP10                     |
| US-D09 | F07 hierarchy maintenance         | E2 containment/cycle tests + E3 disconnected form   | 0.6 generic; 0.8 specialist tree |
| US-D10 | F08 relation maintenance          | E2 relation tests + E3 disconnected panel           | 0.6 WP9/WP10                     |
| US-D11 | F10 deletion impact               | E2 cascade tests + E3 disconnected dialog           | 0.6 WP9/WP10                     |
| US-D12 | F11 record history                | E2 audit + E3 default-workspace history panel       | WP9 context fix; E1 in WP10      |
| US-D13 | F01 model-defined applications    | E3 shell/view/panel tests across record types       | Current; E1 proof in WP10        |
| US-W01 | F12 design draft                  | Current-live/history-source API tests; browser gap | 0.6 WP9/WP10                    |
| US-W02 | F13 graph validation              | E2 whole-graph validation tests                     | 0.6 WP9/WP10                     |
| US-W03 | F13 atomic activation             | E2 activation tests                                 | 0.6 WP9/WP10                     |
| US-W04 | F13/F17 delta merge               | E2 activation-merge tests                           | 0.6 WP10                         |
| US-W05 | F14 lineage                       | E2 history tests                                    | 0.6 WP9/WP10                     |
| US-W06 | F14 publication retirement        | E2 retirement tests                                 | 0.6 WP9/WP10                     |
| US-W07 | F12-F14 historical-source draft      | E2 draft/history/activation tests                   | 0.6 WP9/WP10                     |
| US-L01 | F09 translation creation          | E2 translation tests + disconnected generic UI      | 0.6 WP9/WP10                     |
| US-L02 | F09 translation uniqueness        | E2 translation/graph tests                          | 0.6 WP10                         |
| US-L03 | Translation coverage matrix       | E5 roadmap                                          | 0.8                              |
| US-M01 | Mapping coverage                  | E5 roadmap/ADR-022                                  | 0.7                              |
| US-M02 | Atomic mapping replacement        | E5 roadmap/ADR-022                                  | 0.7                              |
| US-M03 | Ambiguity resolution              | E5 roadmap/ADR-022                                  | 0.7                              |
| US-I01 | F16 stable identities             | E2/E4 public-contract tests                         | Current                          |
| US-I02 | F16 resumable bounded reads       | E2 cursor/query tests                               | Current                          |
| US-I03 | Bulk changes                      | E5 roadmap                                          | 0.9                              |
| US-I04 | Import/export jobs                | E5 roadmap                                          | 0.9                              |
| US-I05 | Change feed/webhooks              | E5 roadmap                                          | 0.9                              |
| US-I06 | Effective/as-of query             | E5 roadmap                                          | 0.9                              |
| US-A01 | F02 workspace creation            | E2 workspace tests                                  | Current API                      |
| US-A02 | F02/F17 default switch            | E2 workspace-state concurrency tests                | Current API                      |
| US-A03 | F02 retirement/read-only          | E2 workspace tests                                  | Current API                      |
| US-P01 | F15 inspect/export model          | E3 workbench + E2 release APIs                      | Current                          |
| US-P02 | F15 check proposed model          | E2/E3 model lifecycle tests                         | Current when enabled             |
| US-P03 | F15 install inactive release      | E2/E3 model lifecycle tests                         | Current when enabled             |
| US-P04 | F15 activate model                | E2/E3 activation tests                              | Current supported topology       |
| US-P05 | Structured authoring              | E5 roadmap                                          | 1.0                              |
| US-U01 | F18 accessible/responsive use     | E3 UI-foundation and shell tests                    | 0.6 E1/accessibility proof WP10  |
| US-O01 | F19 actionable startup refusal    | E2 real temporary-database lifespan/migration tests | Current                          |
| US-O02 | F15/F19 older model activation    | E2/E3 compatibility and activation tests            | Current boundary                 |
| US-O04 | Application/database restore      | E5 roadmap and current unrehearsed runbook          | 0.10                             |
| US-S01 | Authentication/authorization      | E5 roadmap                                          | 0.10                             |
| US-O03 | Multi-writer/multi-node operation | E5 roadmap                                          | 0.10                             |

## Additional story traceability (2026-09-08)

| Story | Function/outcome | Evidence position | Scenario / target |
| --- | --- | --- | --- |
| US-D14 | Availability without deletion | Existing generic field semantics; composed proof pending | SC-02 / 0.6 |
| US-W08 | Fresh live draft starting view | Accepted decision; source gap GAP-02 | SC-05 / 0.6 |
| US-W09 | Draft model-version selection | Accepted decision; global selection today | SC-15 / 0.7 with schema 0.6 |
| US-M04 | Missing mapping target creation | Roadmap; no completed specialist flow | SC-07 / 0.7 |
| US-L04 | In-context translation edit | Roadmap; generic service is not matrix proof | SC-09 / 0.8 |
| US-H01 | Large hierarchy navigation | Roadmap | SC-09 / 0.8 |
| US-H02 | Contextual hierarchy maintenance | Generic service exists; specialist interaction planned | SC-09 / 0.8 |
| US-I07 | File validation preview | Roadmap; format/policy decisions pending | SC-10 / 0.9 |
| US-I08 | Scoped export | Roadmap | SC-10 / 0.9 |
| US-P06 | New domain without bespoke software | Model/workbench source; composed authoring proof pending | SC-12 / 0.6 foundation |
| US-P07 | Staged assignment and reviewed historical migration | Accepted GAP-02/GAP-08; global selection today | SC-13 confirm/cancel/loss variants / 0.10 |
| US-O05 | Authenticated change attribution | Roadmap; current audit is not identity proof | SC-13 / 0.10 |
| US-I09 | Advanced integration query | Roadmap; query grammar requires agreement | SC-10 extension / 0.9 |
| US-O06 | Service observability | Health foundation; production measures planned | SC-13 / 0.10 |
| US-P08 | Reusable definition package | Roadmap; two reuse cases required | SC-12 extension / 1.0 |

## Required recurring journeys

At minimum, every 0.6 release candidate should execute these against the composed product:

1. In a non-default workspace, find a Domain using a typed filter, open it, inspect related Codelists
   and history, and return to the exact list.
2. Create and edit a live root record without a workspace draft; verify immediate visibility, version
   conflict behavior and audit.
3. Create a contained record of another type with typed fields and a parent in one flow.
4. Create a Translation with its Translation Group and one permitted target; reject missing content and
   duplicate active target/language scope without losing input.
5. Create, edit and delete an ordinary relationship while keeping containment relationships read-only.
6. Preview and confirm deletion of an owner with dependants; prove an independent associated record
   survives.
7. Create a design draft, change multiple record types and a relationship, validate and activate once;
   prove staged changes were not visible before activation.
8. Make an unrelated live edit while that draft is open and prove activation preserves it.
9. Make a conflicting live edit to a draft-touched record and prove activation changes nothing and
   preserves the draft.
10. Branch from an older revision and prove “created from” differs from “superseded on activation.”
    Separately start from current live data after post-publication edits, including a workspace without
    a publication (SC-05 / GAP-02); historical-source draft tests do not cover this requirement.
11. Retire the publication designation, verify live records remain available, inspect retained history
    and prepare explicit new changes from an older snapshot; do not assume automatic rollback.
12. Inspect, validate, compare, install and activate a model release with mutation enabled; prove
    installation alone does not activate it.

Run the data journeys with at least two record types and two containment/ownership configurations. A
route returning 200 is insufficient: verify resulting content, history, concurrency tokens and the
absence of partial writes.

## Simplicity guardrails

Use these as design assertions, not optional usability suggestions.

### Everyday live edit

- No draft selection, validation or activation is required.
- One coherent form should include core fields, typed fields, parent and required relationships.
- A successful save is immediately visible and audited.
- Conflict recovery preserves what the user entered.

### Find and return

- Search and filters operate on the server, not only loaded rows.
- Opening a record does not discard the collection address.
- Empty data and failed data are visibly different.
- Retry does not reset successful page or panel content.

### Coordinated design

- Lifecycle controls appear at workspace level, never on individual records.
- Normal record controls are reused inside the selected draft.
- Validation is separate from activation and has no publishing side effect.
- One activation publishes the whole merged graph or nothing.
- “Created from” and “superseded on activation” are not collapsed into one vague “previous version.”

### Relationship and mapping

- Containment is changed through the Parent field, not by directly editing the maintained edge.
- Generic relationship CRUD must not be presented as the completed mapping workflow.
- Mapping replacement must eventually be one operation, not visible delete followed by create.

### Model administration

- Save, validate, install and activate remain distinct.
- The bootstrap file is not an alternative activation control.
- Read-only inspection remains available when mutation is disabled.
- A deployment flag is never described as user identity or permission.

## Regression review checklist

For every relevant changed story, answer all of the following:

- Can the intended user still complete the full journey through its claimed channel?
- Did the number of decisions, screens or confirmations increase? If so, which named risk requires it?
- Is routine live maintenance still possible without a draft?
- Does the same generic flow work for two differently configured record types?
- Are types, stable IDs, workspace scope and relationships preserved?
- Does stale input fail explicitly rather than overwrite newer work?
- Does failure preserve local input, drafts and already loaded content where applicable?
- Is every list bounded and every continuation tied to the original query/context?
- Are empty, loading, failure, read-only and success states distinct?
- Can the task be completed with a keyboard and at the narrow target size?
- Do user messages explain what failed, what was preserved and the safe next action?
- Does documentation mark the function in the correct delivery channel?

## Documentation consistency checks

The canonical technical docs have been reconciled to ADR-027. At future updates, search for recurrence
of these patterns outside explicitly labelled historical sections:

- “every write requires a workspace draft”;
- “published reads resolve only through active revision membership”;
- “translation changes must always be activated”;
- WP9 wording that says a selected draft is required before enabling any record write; and
- release criteria that call revision projections authoritative without acknowledging the live data
  store as the active read/write source; and
- history status that describes the API as oldest first; WP8.1-C changed revision discovery to bounded,
  deterministic newest-first paging. Browser history acceptance remains in WP9/WP10.
- historical model migration described as a current override, or loss confirmation that bypasses
  target validation, parser support or workspace isolation.

Historical decisions may retain superseded text when clearly labelled. Current status, API, roadmap and
user documentation must state that live data writes are direct and design drafts are optional.

## Release evidence record

For each release candidate, add a dated record elsewhere in the release documentation containing:

- commit and model release tested;
- database and browser versions;
- exact automated commands and totals, including skips;
- the journeys above that were executed manually or automatically;
- accessibility and narrow-screen evidence;
- migration/bootstrap/package evidence;
- deviations, known gaps and their roadmap ownership; and
- explicit confirmation that unrelated user-owned worktree changes were not included.

Do not replace a missing evidence category with a broad statement such as “all functionality works.”

## Recurring product review record

Keep story IDs stable. A removed or superseded story remains traceable with its replacement and the
explicit product decision; do not delete it to make coverage appear complete. Review the affected
stories during each package, all core daily journeys at the release gate, and future-story assumptions
when the relevant milestone is planned. Record deviations before updating the technical plan.

```markdown
Date and reviewed commit/worktree:
Stories, functions and scenario IDs:
Claimed delivery channel and current status:
Starting data, configuration variants and environment:
Executed steps and observable results:
Evidence links and unexecuted/skipped checks:
Previous flow versus proposed flow (steps, decisions, re-entry, time if measured):
Reason for any added complexity or removed capability:
Failures/conflicts exercised and what was preserved:
Outcome: accepted / partially evidenced / blocked / planned:
Open gap, owner or delivery milestone, and required next evidence:
Technical documents/plans requiring reconciliation:
```

A planned story cannot become accepted from a document review. A service-only pass cannot close a
browser story. Record observed usability measures from the scenarios rather than claiming “simple”
from an implementation's size or component count.
