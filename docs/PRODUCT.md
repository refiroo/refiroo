# Product definition

For the user-facing functionality baseline, realistic stories, acceptance scenarios and product
roadmap, start with [the product functionality guide](product-functionality/README.md). Its
[planning handoff](product-functionality/PLANNING_HANDOFF.md) records gaps to reconcile before updating
technical documentation and implementation plans.

## Purpose

RDM Engine lets teams define and operate reference-data applications without developing a separate
application for every domain. A JSON model defines the concepts and the interface; the engine supplies
validated storage, APIs, search, history and reusable UI components.

## Product statement

An open-source, model-driven engine for building reference-data applications, mappings and integration
APIs without writing application-specific code.

## Intended users

- Data owners maintaining canonical codes and names
- Integration teams translating values between systems
- Local data stewards maintaining translations and availability
- Developers consuming reliable, scalable reference-data APIs
- Product administrators defining new RDM applications through configuration

## Product capabilities and delivery channels

The product provides a reusable definition of applications, record types, typed fields, relationships
and views. Data owners use that definition to organize codes, maintain representations and connect
values according to the selected model. Every application gets the same capabilities; the example
applications (RDM Master, RDM Systems, RDM Translations) show one way to configure them and are never
special runtime modules or a required shape ([example model](EXAMPLE_MODEL.md)). The browser composes a model-defined application from contextual collections
and supported task lenses; it does not reserve navigation or renderer branches for the starter model.

| Capability | Current development position | Product coverage |
| --- | --- | --- |
| Model-defined navigation, tables, search and record inspection | Browser available in every workspace, including record detail in a non-default workspace | F01–F04, US-D01–D05, US-D13 |
| Live record, field, parent, relationship and basic translation maintenance | API and Base 0.6 browser authoring available; context limitations tracked in the functionality catalogue | F05–F11, US-D06–D14, US-L01–L02 |
| Optional coordinated data changes | Current-live/history change set sources and delta merge available; mapping browser acceptance remains 0.7 work | F12–F14, US-W01–W08 |
| Inspect, check, install and activate application definitions | JSON workbench and release APIs present; installation and activation are separate | F15, US-P01–P04, US-P06 |
| Stable paged integration reads | Available; larger exchange and advanced query planned for 0.9 | F16, US-I01–I09 |
| Contextual collections and specialist lenses | Unified application browser and mapping lens 0.7; relation matrix and tree lenses 0.8, available to any application | US-D01–D05, US-M01–M04, US-L03–L04, US-H01–H02 |
| Authenticated shared production operation | Production hardening and staged model rollout planned for 0.11; authentication and authorization for 0.12 | US-S01, US-O03–O06, US-P07 |
| Spreadsheet onboarding and structured model authoring | Planned for 0.10: one editor for the model and the import mapping, with additive and unreleased changes ([design](MODEL_AUTHORING.md)); changes to released structure and reusable definitions in 1.0, retaining existing validation and release protections | US-P05, US-P08–P10 |

“API available” does not mean a complete browser task. Current top-level views support strict tables;
a form used for record editing is not an implemented configurable top-level `form` view. Schema 0.6
mapping-grid configuration, live/change set coverage, target-detail, candidate APIs (WP-4) and atomic
mapping replacement (WP-5) are delivered. WP-8A/WP-8B and WP-14 implement the contextual mapping
lens and unified browser (committed 2026-09-15); composed story acceptance remains WP-9.
Cascade deletions advance mapping
tokens (WP-10A), and publishing refuses divergent live sets touched by staged mutable relations
(WP-10B), preserving the change set and all live content. Schema 0.6 table and mapping declarations are
composed as lenses over their configured source object type; mapping keeps its dedicated semantics
without multiplying primary navigation destinations. Trees and other specialist declarations require
their own validated contract and renderer. Dashboards
have no scheduled user outcome. The [functionality catalogue](product-functionality/CURRENT_FUNCTIONALITY.md)
records channel limitations; no browser acceptance is implied by the presence of a component.

## Change rules

- **Daily reference data:** adding or correcting a record, field, translation, parent or ordinary
  relationship is a direct live operation. Save validates the data, prevents silent overwrite and
  records the change. It does not require a change set or create a publication.
- **Coordinated data changes:** users may explicitly select a workspace change set. Its changes stay
  separate until activation applies them together over current live data. Unrelated live changes
  survive; conflicting or invalid changes publish nothing and preserve the change set and live content.
- **Application definitions:** a model draft changes the allowed structures and rules. Installation
  produces an immutable release; activation separately selects it after compatibility checks. A data
  change set is not a model editor, and replacing the bootstrap file is not an activation mechanism.

These rules apply to the specialist mapping, translation and hierarchy flows and to later bulk
operations. Touching several records alone is not a reason to require a change set. Any additional mandatory
review step needs a stated user benefit or specific risk and an explicit product decision.

## Boundaries

The product is focused on reference data. It is not intended to become a general data catalogue,
business glossary, lineage scanner or enterprise governance suite. Generic applications are supported
where the same object/attribute/relation/view model is genuinely useful, but RDM integration remains the design
centre.

Neighbouring domains such as MDM-lite and small, specific product catalogues are modelled on the engine,
not built into it. A capability they motivate must be generic, have a second real use and compose with
live data, change sets, publications and model releases (ADR-032). The
[composable domains](COMPOSABLE_DOMAINS.md) direction records the admission tests and the design doors
current work keeps open.

## Success and recurring acceptance

An administrator can define and release another reference-data application without changing Python
or TypeScript. A steward can then select its workspace, find a record, create or correct it with its
required fields and connections, and see the live result through the same generic controls. A normal
correction takes one coherent edit and save, with no release ceremony. The same journeys work for at
least two differently configured record types. Containment context, model-declared filters and
applicable semantic lenses remain visible so a global object-type projection is never the only way to
understand a governed collection.

Acceptance is assessed through [user stories](product-functionality/USER_STORIES.md) and
[realistic scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md), not merely by whether a route,
component or model declaration exists. Each work package names the affected story IDs, existing flows
it must preserve, and the evidence needed for its claimed channel. Release gates exercise the composed
browser and service, including failure, concurrency, keyboard operation and narrow layouts.

Use the [validation guide](product-functionality/VALIDATION_GUIDE.md) to record results and compare
required steps, repeated input and recovery with the previous flow. A documentation update or passing
component suite cannot mark an unexecuted user journey complete.
