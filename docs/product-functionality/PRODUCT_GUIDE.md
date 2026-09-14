# RDM Engine: the product people use

## Purpose and intended difference

RDM Engine helps teams keep shared codes, names, translations and connections between systems
consistent. A team defines the kinds of information it manages and the rules that information must
follow. The product then supplies the screens and services for maintaining it.

For example, a company may call the same delivery method “Collection” in its central list, “PICKUP”
in its webshop and “Store collection” in its warehouse system. A data steward maintains the shared
meaning, connects the system-specific values and supplies the translated labels. Other systems can
then use the agreed data without each inventing another list.

The intended distinction is the combination of:

- **Reusable definitions:** another reference-data domain uses the same product with different record
  types, fields, rules and layouts. It does not require a separately developed application.
- **Meaningful connections:** a record's place in a hierarchy, its equivalent in another system and
  its translation have different meanings and follow the appropriate rules.
- **Simple daily maintenance:** a normal correction becomes live when saved. Coordinated changes can
  be prepared separately without blocking that daily work.
- **One set of rules across channels:** people and connected systems maintain the same governed data.
  A screen, import or integration must not become a way to avoid validation.

These are product commitments, not claims of market exclusivity. Master, Systems and Translations
are starter examples; they are not the only applications the engine should understand.

## Who gets value

| Responsibility | Typical job | A useful outcome |
| --- | --- | --- |
| Data owner or steward | Correct a code, add a value, organize a list | Colleagues immediately use accurate shared data |
| Mapping steward | Connect a source-system value to its agreed meaning | A system exchange uses the intended equivalent |
| Localization steward | Supply and correct language-specific content | Users see the right label in their language |
| Integration team | Read, exchange and synchronize reference data | Systems agree without repeated manual reconciliation |
| Workspace administrator | Establish the right working area and retire obsolete ones | People know where to work and what is read-only |
| Model administrator | Define a new domain or change its rules | The application evolves without a custom software fork |
| Service operator | Keep the product running and recover it | Users can rely on the service and its data |

These are responsibilities, not currently implemented permission roles. Authenticated access control
is planned for 0.10. The examples below are fictional acceptance examples, not customer research or
preloaded demonstration data.

## The functions in everyday language

| User goal | What the product should let the user do | Development position | Stories |
| --- | --- | --- | --- |
| Find the right information | Choose a named workspace, search and filter a list, inspect a record and return to the same place | Browser read flows exist; non-default detail context needs repair | US-D01–D05 |
| Keep a shared list accurate | Add, correct or remove a value and its fields, with clear validation and change history | Service and Base 0.6 browser authoring available; see the functionality catalogue for context limitations | US-D06–D08, US-D11–D12, US-D14 |
| Organize and connect data | Choose a valid parent, connect related records and understand deletion impact | Service and Base 0.6 browser authoring available; see the functionality catalogue for context limitations | US-D09–D11 |
| Work in several domains | Use the configured terminology, fields and views through familiar controls | Model-driven foundation exists | US-D13, US-P06 |
| Prepare a coordinated change | Work in an optional draft, check it and apply its changes together while preserving unrelated live work | Current-live/history API available; browser gaps remain | US-W01–W08 |
| Maintain translations | Enter a target, language and translated content together; prevent conflicting active translations | Basic API and Base 0.6 browser flows available; specialist coverage view remains 0.8 | US-L01–L04 |
| Manage system equivalences | See missing or conflicting mappings and choose, replace or clear a target in one action | WP-4 query and WP-5 atomic replacement APIs delivered; WP-10B protects activation against divergent live mapping sets. Browser workflow remains WP-8A/WP-8B; composed acceptance WP-9 | US-M01–M04 |
| Navigate a deep hierarchy | Expand the relevant branch, add a child or move a record without losing context | Specialist workflow planned for 0.8 | US-H01–H02 |
| Exchange larger datasets | Import with a preview, export a chosen scope, track results and resume synchronization | Basic reading available; bulk exchange and feeds planned for 0.9 | US-I01–I09 |
| Manage working areas | Create and label a workspace, select the default and retain read-only access to retired areas | Service available; no complete administration screen | US-A01–A03 |
| Evolve application definitions | Inspect, edit, check, compare, install and activate a definition safely | JSON-based workbench exists; structured designer planned for 1.0 | US-P01–P08 |
| Use and run the product reliably | Work by keyboard, recover from conflicts, control access and restore service after a failure | Interface and operational foundations exist; browser proof 0.6, production controls 0.10 | US-U01, US-S01, US-O01–O06 |

“Service available” means another system can perform the operation through the supported interface.
It does not mean a data steward can complete it in the browser today. The detailed
[functionality catalogue](CURRENT_FUNCTIONALITY.md) records that distinction. No fresh execution of
the application is implied by this documentation review.

## Three different kinds of change

### Correct today's data

A steward notices “Collecton” in Delivery Methods, opens the record, corrects it to “Collection” and
saves. The correction is immediately available. Its identity and connections stay the same. If someone
else has changed the record, the product keeps the attempted correction and asks the steward to review
the newer information before trying again.

No release, draft name or publication action is needed. Marking a model-defined availability field
false is also an ordinary edit. Whether a consuming system hides unavailable values depends on its
agreed query; the engine must not silently invent that business policy.

### Prepare several related changes

A steward is reorganizing delivery options and related system mappings. The team chooses a design
draft, makes the changes away from live users, checks the result and activates the coordinated change.
Another steward can still correct an unrelated live value. That correction must survive activation.
If both change the same record, activation must stop without losing either person's work.

This draft changes data. It does not by itself change the application definition. The current-live
starting point promised by the product still needs implementation reconciliation; see GAP-02 in
[planning handoff](PLANNING_HANDOFF.md).

### Change what the application allows

An administrator needs a new field or relationship rule. They edit a proposed application definition,
check it against existing data and make a new definition available before selecting it for use.
Existing released definitions remain inspectable. An incompatible change needs a migration capability;
the planned 0.10 flow previews affected data and potential loss, then allows explicit confirmation
of that migration or cancellation. Confirmation applies to the reviewed change, not to invalid data
or an unsupported model language. Current ordinary activation does not offer this override.

The current definition applies globally. Assigning different definitions to different workspaces is
planned for 0.10, not a present property of workspace selection.

## History answers different questions

- Record history answers “what changes were made to this item?” Authenticated attribution to a named
  person is future production work.
- A workspace snapshot answers “what did this coordinated publication contain?” Later live edits do
  not rewrite it. A snapshot is not a complete archive of every moment between publications.
- A released application definition answers “what fields and rules did this version define?”
- Future effective-date queries answer “what value applied on this business date?” A field containing
  a date does not provide that behavior on its own.

Starting a draft from old history is not a one-click undo of today's dataset. Activation preserves
untouched live records and checks conflicts. Stopping a publication also does not currently remove
live data from normal reads or make the workspace read-only. Use workspace retirement for read-only
status; settle publication-retirement wording before presenting it as a user-facing withdrawal action.

## What success looks like

The first usable daily-operation release lets a steward find, create, correct, connect, translate and
remove data in the chosen workspace, without learning technical identifiers or undertaking a release
for each save. The same tasks must work for differently configured record types.

Later releases shorten specialist tasks: resolve a mapping on its row, fill a missing translation in
context, move a hierarchy item from its branch, and import a file with understandable outcomes.
They preserve the simpler record flows as alternatives.

The [acceptance scenarios](ACCEPTANCE_SCENARIOS.md) provide concrete starting data and observable
results. Their review measures are proposed baselines, not claims that user testing has happened.

## Scope boundaries

Reference data is the design centre. This roadmap does not promise a data catalogue, glossary,
lineage scanner, customer matching, deduplication engine or general workflow designer. Optional
approval processes, localized interface labels and copy/duplicate shortcuts remain discovery topics;
they have no assigned delivery commitment here.

Model-driven does not mean every conceivable screen can already be configured. Current top-level
views are tables. Mapping, translation and tree experiences follow the roadmap; a configured but
unsupported view must not be advertised as delivered. General dashboards have no scheduled outcome.

Read next: [user stories](USER_STORIES.md), [product roadmap](ROADMAP_COVERAGE.md),
[planning handoff](PLANNING_HANDOFF.md).

## Planned 0.7 refinement

The [0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md) separates mapping coverage (WP-8A) from actions
(WP-8B). Large ambiguous mappings remain inspectable through bounded pages; keeping a selected target
preserves its relationship identity and attributes. A draft's chosen definition must already accept
its complete content. Failed choices change nothing; successful choices refresh the browser's fields,
rules and views safely. SC-07/SC-15 remain release acceptance requirements, not delivered evidence.
