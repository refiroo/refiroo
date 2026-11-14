# Product functionality from the user's perspective

This directory is the detailed, user-centred reference for RDM Engine: what people are trying to
achieve, which product functions support them, what is available now and what is planned. Start with
the [product overview](../PRODUCT.md); use this directory during planning, implementation and release
reviews to prevent two kinds of regression:

- losing a useful capability that already exists; and
- making a common task more complicated than the user's job requires.

The documents use product language. Implementation links are evidence, not the main description.

## Documentation set

- [Current functionality](CURRENT_FUNCTIONALITY.md): the capability catalogue, F01–F30, with what
  works in the browser and through the API.
- [Worked examples](PRODUCT_GUIDE.md): everyday situations, the three kinds of change and what history
  answers.
- [User stories](USER_STORIES.md): durable user needs and observable acceptance statements.
- [User journeys](USER_JOURNEYS.md): the shortest understandable flows for important tasks.
- [Acceptance scenarios](ACCEPTANCE_SCENARIOS.md): fictional but realistic data, observable outcomes,
  failure cases and simplicity measures.
- [Roadmap coverage](ROADMAP_COVERAGE.md): user outcomes per release, 0.5 through 1.0 (0.17.1 is the latest release).
- [Validation guide](VALIDATION_GUIDE.md): traceability, regression checks and the recurring review
  method.
- [Planning handoff](PLANNING_HANDOFF.md): the gap register GAP-01–GAP-08 and its accepted answers.
- [Glossary](GLOSSARY.md): consistent, non-technical product terms.
- [Real-world research](REAL_WORLD_RESEARCH.md): background research behind the stories.

## The four things users manage

| Concern | Plain-language meaning | Change rhythm |
| --- | --- | --- |
| Application model | The definition of applications, record types, fields, relationships and views | Deliberate draft, check, install and activation |
| Live reference data | The codes, names, availability, translations and relationships people maintain every day | Direct edit with conflict protection and history |
| Change set | An optional place to prepare a coordinated set of data changes | Edit, review, validate and publish as one |
| Publication | A read-only snapshot created when a change set is published | Never edited in place |

A routine data edit never requires a change set or a model release.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| **Browser validated** | The flow has passed a real-browser check against a real backend in its claimed scope |
| **Browser implementation present** | A reachable interface flow exists in code; any missing composed-browser proof or limitation is stated |
| **Available through the API** | The backend function exists; the browser may not expose the full flow |
| **Component present, flow unavailable** | Interface pieces and tests exist, but no usable journey connects them |
| **In progress** | Required for the release currently being delivered |
| **Roadmap** | A direction for a later release, not current functionality |
| **Not planned** | Deliberately outside the stated product scope or release |

"Available" does not imply that a caller may use a function: authentication and authorization arrived in 0.12, and what a person or system may do is set by role (F26, F27). Where a deployment
setting controls a function, the catalogue says so.

## Maintenance rule

When implementation, tests and planning text disagree:

1. user-observable implementation and direct tests determine what is available now;
2. accepted decisions determine the intended product semantics;
3. the roadmap determines future scope; and
4. the discrepancy is recorded rather than blended into an ambiguous claim.

Update this directory whenever a capability becomes available in a new channel, a user story changes,
or a roadmap outcome is rescheduled, and update [PRODUCT.md](../PRODUCT.md) with it. Do not mark a
story "browser implementation present" solely because an API or an isolated component exists, and do
not mark it "browser validated" without a composed real-browser result.

Product boundaries are in [PRODUCT.md](../PRODUCT.md#boundaries). Primary sources: the
[roadmap](../ROADMAP.md), the [project status](../PROJECT_STATUS.md) and the
[architecture decisions](../DECISIONS.md).
