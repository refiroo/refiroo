# Product functionality from the user's perspective

This directory is the user-centred reference for RDM Engine. It describes what people are trying to
achieve, which product functions support them, what is available now, and what is planned. It is meant
to be used during planning, implementation and release reviews to prevent two kinds of regression:

- losing a useful capability that already exists; and
- making a common task more complicated than the user's job requires.

The documents deliberately use product language. Implementation links are evidence, not the main
description of the product.

Start with the [plain-language product guide](PRODUCT_GUIDE.md). For recurring reviews, use the
[realistic acceptance scenarios](ACCEPTANCE_SCENARIOS.md); for the next technical planning update, use
the [planning handoff and gap register](PLANNING_HANDOFF.md).

## Product promise

RDM Engine lets a team create and operate reference-data applications from a reusable definition,
without building separate software for every reference-data domain. Data owners maintain governed
values and relationships; localization stewards maintain translations; integration teams consume
stable interfaces; and administrators evolve the application definition through controlled releases.

RDM Master, RDM Systems and RDM Translations demonstrate the product. They are not fixed product
modules and not a required shape: every application has the same capabilities, and the stories use
these example applications only to make the capabilities concrete
([example model](../EXAMPLE_MODEL.md)).

## Read this first: the four different things users manage

| Concern                | Plain-language meaning                                                                   | Change rhythm                                           |
| ---------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Application model      | The definition of applications, record types, fields, relationships and views            | Deliberate draft, check, install and activation process |
| Live reference data    | The codes, names, availability, translations and relationships people maintain every day | Direct edit with conflict protection and audit          |
| Workspace change set | An optional safe place to prepare a coordinated set of data changes                      | Edit, validate and activate as one change set           |
| Publication     | A read-only publication created when a change set is activated                 | Never edited in place                                   |

A routine data edit must not require a change set or model release. A draft is chosen when a team
needs to prepare and validate a coordinated design change away from live data.

## Status vocabulary

| Status                                  | Meaning                                                                                                           |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Browser implementation present**      | A reachable interface flow exists in code; any missing composed-browser proof or scope limitation is stated.      |
| **Browser validated**                   | The flow has passed a real-browser check against a real backend in its claimed scope.                             |
| **Available through the API**           | The supported backend function exists, but the current browser may not expose the full flow.                      |
| **Component present, flow unavailable** | Reusable interface pieces and tests exist, but the product does not currently connect them into a usable journey. |
| **In progress for 0.6**                 | It is required to finish the current product release.                                                             |
| **Roadmap**                             | It is a direction for a later product release, not current functionality.                               |
| **Not planned**                         | It is deliberately outside the stated product scope or release.                                                   |

“Available” does not imply that authentication or fine-grained authorization exists. Where a mutation
is controlled by a deployment setting, this catalogue says so explicitly.

## Documentation set

- [Product guide](PRODUCT_GUIDE.md) — purpose, intended distinction, user responsibilities and everyday functions.
- [Acceptance scenarios](ACCEPTANCE_SCENARIOS.md) — fictional but realistic data, observable outcomes,
  failure cases and simplicity measures.
- [Planning handoff](PLANNING_HANDOFF.md) — discrepancies to reconcile and inputs for technical plans.
- [Current functionality](CURRENT_FUNCTIONALITY.md) — the capability catalogue and current channel
  availability.
- [User stories](USER_STORIES.md) — durable user needs and observable acceptance statements.
- [User journeys](USER_JOURNEYS.md) — the shortest understandable flows for important tasks.
- [Roadmap coverage](ROADMAP_COVERAGE.md) — planned user outcomes from 0.6 through 1.0.
- [Validation guide](VALIDATION_GUIDE.md) — traceability, regression checks and the recurring review
  method.
- [Glossary](GLOSSARY.md) — consistent, non-technical product terms.

## Intended users

- **Data owner:** maintains canonical codes, names, availability and structure.
- **Data steward:** performs daily maintenance and resolves quality issues in an assigned workspace.
- **Localization steward:** maintains language-specific representations and translation coverage.
- **Integration consumer:** reads or synchronizes reference data from another system.
- **Workspace administrator:** provisions and retires workspaces and controls the default workspace.
- **Model administrator:** defines and releases the reusable application model.
- **Platform operator:** deploys, upgrades, monitors, backs up and recovers the service.

These are responsibilities, not implemented permission roles. Identity and authorization are planned
for product 0.11.

## Evidence and maintenance rule

The original catalogue snapshot is **2026-09-07**. This **2026-09-08** update reviewed product and
roadmap coverage, browser reachability and change-set/merge/withdrawal behavior against base
`60b99d3` plus pre-existing uncommitted changes. It adds realistic acceptance examples, fills story
coverage gaps and corrects current-live change set and historical-restore overclaims. It does not certify a
tagged release or rerun the existing tests. Other catalogue evidence remains the prior assessment;
new source findings and validation limits are recorded in [planning handoff](PLANNING_HANDOFF.md).
The user subsequently accepted GAP-01–GAP-08 and authorized the technical documentation update. ADR-027
and the revised implementation plan now own the consolidated technical direction; gap implementation
and runtime validation remain pending. User comments are retained verbatim in the handoff table.

When implementation, tests and planning text disagree:

1. user-observable implementation and direct tests determine what is available now;
2. accepted decisions determine the intended product semantics;
3. the roadmap determines future scope (new acceptance detail remains subject to planning review); and
4. the discrepancy is recorded rather than blended into an ambiguous claim.

Update this directory whenever a capability becomes available in a new channel, a user story changes,
or a roadmap outcome is rescheduled. Do not mark a story “browser implementation present” solely
because an API or an isolated interface component exists, and do not mark it “browser validated”
without a composed real-browser result.

## Product boundaries

RDM Engine is focused on reference data, mappings, translations, hierarchies and integration. It is not
intended to become a general data catalogue, business glossary, data-lineage scanner or broad enterprise
governance suite. It also does not treat a visual graph canvas as the default way to perform simple
administration.

Primary source documents:

- [Product definition](../PRODUCT.md)
- [Project status](../PROJECT_STATUS.md)
- [Delivery roadmap](../ROADMAP.md)
- [Architecture decisions](../DECISIONS.md)
- [Base 0.6 plan](../BASE_0_6_IMPLEMENTATION_PLAN.md)
