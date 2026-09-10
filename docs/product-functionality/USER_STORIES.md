# User stories

These stories describe durable user value rather than a particular screen or endpoint. Each acceptance
statement is observable from outside the implementation. Status uses the vocabulary in
[README](README.md#status-vocabulary). Concrete starting data, failure examples and simplicity checks
live in [acceptance scenarios](ACCEPTANCE_SCENARIOS.md). New roadmap acceptance detail is proposed for
planning review; it does not claim a delivered contract. Existing story IDs are retained for tracking.

## Data owner and data steward

### US-D01 — Enter the right workspace

**Story:** As a data steward, I want to select a workspace by its recognizable name so that I know
which governed dataset I am viewing or changing.

**Accepted when:** The chosen label and stable key remain visible or recoverable from the page address;
an unknown key is not silently accepted; a retired workspace is clearly read-only.

**Coverage:** F02. **Status:** Browser selector/list implementation present and API available; opening
detail from a non-default workspace is a known WP9 gap and composed-browser validation is pending.

### US-D02 — Return to my working list

**Story:** As a data steward, I want to open a record and return to the same search, filters and sort so
that investigating one item does not destroy my place.

**Accepted when:** Back/return restores the same workspace, application, view, search, typed filters,
sort and page size without issuing a broader request.

**Coverage:** F03, F04. **Status:** Browser implementation present for the default workspace;
non-default detail context is a known WP9 gap and composed-browser validation is pending.

### US-D03 — Find a value by business data

**Story:** As a data owner, I want to search names and configured fields and apply type-appropriate
filters so that I can locate a record without knowing its identifier.

**Accepted when:** Search is server-side, filter choices come from the active model, dates/numbers/
booleans are interpreted as their declared types, and invalid input is explained.

**Coverage:** F03, F06. **Status:** Browser implementation present and API available; composed-browser
validation is pending.

### US-D04 — Browse a large collection safely

**Story:** As a data steward, I want stable pages rather than an unbounded list so that the product
remains responsive as data grows.

**Accepted when:** Results have a documented page size, next/previous navigation keeps the selected
query, and a continuation from a different query is rejected.

**Coverage:** F03, F16. **Status:** Browser implementation present and API available; composed-browser
validation is pending.

### US-D05 — Understand one record in context

**Story:** As a data owner, I want to see a record's fields, parent, children, relationships and history
together so that I can understand its meaning and impact.

**Accepted when:** The detail composition follows the model, linked records can be opened, and empty
collections are shown as valid empty states rather than failures.

**Coverage:** F04, F07, F08, F11. **Status:** Browser read implementation present for the default
workspace; non-default detail context and writable related flows are not yet connected.

### US-D06 — Add a live reference value directly

**Story:** As a data owner, I want to add an everyday reference value directly to an active workspace
so that routine maintenance does not require a draft and publication ceremony.

**Accepted when:** One create flow collects the core data, typed fields, parent and required
relationships; success is immediately visible and audited; no workspace revision is created.

**Coverage:** F05-F07. **Status:** Available through the API; browser flow is in progress for 0.6 WP9.

### US-D07 — Correct a live value directly

**Story:** As a data owner, I want to correct a name, availability flag, code or other field directly
so that live reference data stays accurate.

**Accepted when:** The saved correction becomes immediately visible with the same identity and
connections. Values keep their meaning. If someone saved a newer change, my attempted input remains
available while I review it; the product does not overwrite their work silently.

**Coverage:** F05, F06, F17. **Status:** Available through the API; browser flow is in progress for
0.6 WP9.

### US-D08 — Distinguish missing, empty and false values

**Story:** As a data owner, I want optional values to retain their real meaning so that a missing value
is not confused with zero, false, empty text or a deliberate null.

**Accepted when:** Read, edit, filtering and history preserve the declared value and its missing/null
state.

**Coverage:** F03, F06. **Status:** API available; browser editors are present but not connected to a
writable flow.

### US-D09 — Move a record safely in a hierarchy

**Story:** As a data steward, I want to choose a new valid parent so that both navigation and business
relationships remain consistent.

**Accepted when:** The move changes the parent path and typed containment relationship together, rejects
cycles or invalid parent types, and cannot be bypassed by editing the relationship separately.

**Coverage:** F07. **Status:** API available; browser editor is present but not connected. Specialist
tree interaction is planned for 0.8.

### US-D10 — Manage an ordinary relationship

**Story:** As a data steward, I want to connect records using a meaningful relationship and edit its
own fields so that cross-references are governed, not hidden in free text.

**Accepted when:** I can find permitted records throughout my selected workspace, understand the
relationship in either direction and supply its required fields. The product rejects a connection
between incompatible records or too many/few connections, and does not overwrite a newer change.

**Coverage:** F08. **Status:** API available; browser components are present but not connected.

### US-D11 — Delete only after understanding the impact

**Story:** As a data owner, I want to preview dependants before deleting a record so that I do not
accidentally remove independent data.

**Accepted when:** The first step changes nothing and names affected owned records and relationships;
recursive deletion requires explicit confirmation; independent targets are retained.

**Coverage:** F10. **Status:** API available; browser dialog is present but not connected.

### US-D12 — See what changed

**Story:** As a data owner, I want to see the changes to a record over time so that I can investigate
why its content or connections differ from what I expected.

**Accepted when:** History includes the record and relevant relationship changes, supports loading
older entries, retains already loaded entries on failure and offers retry.

**Coverage:** F11. **Status:** Browser implementation present for default-workspace detail and API
available; non-default context repair and composed-browser proof are pending.

### US-D13 — Use the same product for different reference-data domains

**Story:** As a data steward, I want applications, record types, fields and views to follow the active
model so that I can work in a new reference-data domain without learning a separately built product.

**Accepted when:** Navigation and presentation use the configured names and structures, the same generic
flows work for at least two differently configured record types, and no starter application or record
type receives hidden special behavior.

**Coverage:** F01. **Status:** Browser implementation present and API available; composed-browser
validation is pending.

### US-D14 — Stop offering an obsolete value without deleting it

**Story:** As a data owner, I want to mark a value unavailable where my model supports it so that its
meaning and relationships remain available for investigation while consumers can exclude it.

**Accepted when:** availability is an ordinary live field edit, history and identity remain, and a
filter explicitly selecting available values excludes it. The interface does not equate this field
with deleting a record, retiring a workspace or withdrawing a publication.

**Coverage:** F05, F06, F11. **Status:** API field behavior available; browser completion 0.6.
**Example:** SC-02.

## Coordinated design and publication

The live starting-point limitation is tracked in [GAP-02](PLANNING_HANDOFF.md). A design draft
contains data changes; application-definition changes use the separate model administration stories.

### US-W01 — Prepare changes away from live data

**Story:** As a steward preparing a coordinated redesign, I want an optional workspace draft so that I
can change several related records without affecting current users.

**Accepted when:** I can name a draft and choose current live data or a clearly identified historical source,
edit through familiar record controls and discard it without changing live data. Starting from current
live data includes all changes up to draft creation, as specified by US-W08.

**Coverage:** F12. **Status:** Empty and historical-source drafts are available through the API; the
current-live starting point is GAP-02. Browser flow is in progress for 0.6 WP9.

### US-W02 — Check the complete design before activation

**Story:** As a data owner, I want to validate the whole candidate dataset so that cross-record problems
are found before anything becomes live.

**Accepted when:** Validation checks fields, required relationships, uniqueness, cardinality,
containment and cycles without publishing or destroying the draft, and identifies actionable problems.

**Coverage:** F13. **Status:** Available through the API; browser flow is in progress for 0.6 WP9.

### US-W03 — Activate all coordinated changes or none

**Story:** As a data owner, I want one reviewed activation so that users never observe half of a
coordinated design.

**Accepted when:** The draft changes are merged, revalidated and published in one operation; any failure
leaves both live content and the draft preserved.

**Coverage:** F13, F17. **Status:** Available through the API; browser flow is in progress for 0.6 WP9.

### US-W04 — Preserve unrelated live work during activation

**Story:** As a data owner, I want activation to preserve live records that the draft did not touch so
that normal maintenance can continue while design work is open.

**Accepted when:** Untouched live changes remain, a live change to a touched record produces a precise
conflict, and no conflict is silently overwritten.

**Coverage:** F13, F17. **Status:** Available through the API.

### US-W05 — Understand where a revision came from

**Story:** As a data owner, I want history to distinguish the snapshot used to start a draft from the
snapshot replaced at activation so that branching from older history remains truthful.

**Accepted when:** “Created from” and “superseded on activation” are separately visible and may contain
different revision identities.

**Coverage:** F14. **Status:** API available; browser flow is in progress for 0.6 WP9.

### US-W06 — Retire a publication without erasing history

**Story:** As a data owner, I want to remove the current-publication designation so that publication
history is accurate while its evidence remains available.

**Accepted when:** Retirement checks the expected current revision, clears publication as one workspace
action and retains workspace identity, record identities, snapshots and audit history. The interface
explains that live records remain readable and that this action does not make the workspace read-only.

**Coverage:** F14. **Status:** API available; browser flow is in progress for 0.6 WP9.

### US-W07 — Start reviewed changes from history

**Story:** As a data owner, I want to start a draft from an older snapshot so that I can use historical
content as a reference for reviewed new changes without editing history.

**Accepted when:** The old snapshot stays immutable, the new draft records its source, and activation
uses fresh conflict and validation checks. Choosing the old snapshot alone does not undo live changes;
only explicitly authored changes are applied, and untouched newer live records remain.

**Coverage:** F12-F14. **Status:** API available; browser flow is in progress for 0.6 WP9.

### US-W08 — Begin a design with today's complete live content

**Story:** As a steward preparing coordinated changes, I want my draft to start with the data people
are using now so that recent corrections and additions are not absent from my working view.

**Accepted when:** starting from live includes changes made since the last publication and works when
live data exists without a publication. Later live edits do not rewrite that starting view. Starting
from an older historical snapshot remains an explicitly different choice.

**Coverage:** F12, F13. **Status:** SQLite API implemented by WP8.1-B; browser acceptance remains
WP9/WP10 work. **Example:** SC-05.

### US-W09 — Work on the next model version in one draft while live keeps the current one

**Story:** As a steward, I want one draft to work under a not-yet-active model version while live data
and my other drafts keep the version in use, so that I can prepare for a model change without moving
the whole workspace onto it.

**Accepted when:** that draft reads, writes and validates under the version selected for it rather than
the globally active one, while live data, immutable history, every other draft and every other
workspace continue under the active version unchanged. A draft may select only a version that is
installed, complete and supported by this deployment; an unavailable, corrupt or unsupported selection
is refused with an explanation and changes nothing. Once the selected version becomes the active one,
that draft activates through the ordinary path. A draft still on the replaced version is never quietly
moved onto another one: it can be discarded without model agreement, or explicitly moved onto the new
version where its content already satisfies it. Choosing a version changes nothing but that draft: it
never forces a model change through and never switches the version used anywhere else.

**Coverage:** F12, F15, F17. **Status:** Roadmap 0.7 with the schema 0.6 release (ADR-028). Moving a
draft onto a version its content does not already satisfy is reviewed 0.10 migration work.
**Example:** SC-15.

## Localization steward

### US-L01 — Create a valid translation in one operation

**Story:** As a localization steward, I want to enter translated content and select its language and
target together so that no incomplete translation is saved.

**Accepted when:** The translation, its group/containment and required target relationship succeed
together or not at all; at least one configured translated field is meaningful.

**Coverage:** F09. **Status:** API available through generic record operations; browser flow is in
progress for 0.6 WP9.

### US-L02 — Avoid duplicate active translations

**Story:** As a localization steward, I want the product to prevent two active translations for the
same target and language so that consumers receive an unambiguous result.

**Accepted when:** The complete candidate scope is checked and a duplicate reports a clear conflict
without losing input.

**Coverage:** F09, F17. **Status:** Available through the API.

### US-L03 — See translation coverage

**Story:** As a localization steward, I want a bounded target-by-language view of present and missing
translations so that I can focus on gaps without opening every record.

**Accepted when:** I can see which expected target/language combinations are missing, current or
present only in history, including beyond the first displayed page. Historical content does not count
as a completed current translation.

**Coverage:** Planned translation workspace. **Status:** Roadmap 0.8.

### US-L04 — Correct or add a translation from its coverage cell

**Story:** As a localization steward, I want to edit where a target and language intersect so that I
can fill a gap without selecting the same target and language again.

**Accepted when:** the context is preselected, permitted content fields are editable, duplicate active
translations are prevented and the cell reflects a successful save. Routine changes can be live;
explicitly selected draft changes remain staged. Failed input is retained.

**Coverage:** Planned translation workspace. **Status:** Roadmap 0.8. **Example:** SC-09.

## Mapping steward

### US-M01 — See mapping coverage

**Story:** As a mapping steward, I want to see mapped, unmapped and ambiguous source values together so
that I can prioritize work and understand data quality.

**Accepted when:** The list distinguishes a missing mapping, one selected target and several conflicting
targets. I can find candidates beyond the visible rows, using the configured relationship names and
direction, without opening each source individually.

**Coverage:** Planned mapping grid. **Status:** Roadmap 0.7.

### US-M02 — Replace one mapping atomically

**Story:** As a mapping steward, I want to create, clear or replace a selected mapping in one action so
that users never observe a delete-then-create gap.

**Accepted when:** A replacement becomes visible as one complete change. Clearing is offered only where
leaving the mapping empty is allowed. If another person changed the mapping, I can inspect their current choice before
retrying; my attempted replacement changes nothing until then.

**Coverage:** Planned mapping operation. **Status:** Roadmap 0.7.

### US-M03 — Resolve an ambiguous mapping safely

**Story:** As a mapping steward, I want to select the correct target for an ambiguous source so that the
result is protected by the same concurrency rule as an existing or missing mapping.

**Accepted when:** Resolving several conflicting targets has the same protection against overwriting
newer work as choosing a first target. Connections with another business meaning remain unchanged.

**Coverage:** Planned mapping operation. **Status:** Roadmap 0.7.

### US-M04 — Create a missing mapping target in context

**Story:** As a mapping steward, I want to add a missing permitted target while mapping a source so
that I do not abandon the task and reconstruct its context elsewhere.

**Accepted when:** configuration permits creation, the usual target fields and validation apply, and
the new target can be selected on return. Cancelling or failing target creation leaves the current
mapping intact. Creating a target does not silently change the mapping before the chosen save action.

**Coverage:** Planned mapping workflow. **Status:** Roadmap 0.7. **Example:** SC-07.

## Hierarchy steward

### US-H01 — Find an item in a large hierarchy

**Story:** As a data steward, I want to expand relevant branches and see my location so that I can
work in a deep hierarchy without loading or navigating every item.

**Accepted when:** roots and children load in manageable portions, the path is clear, keyboard
navigation is supported and retry keeps already loaded branches. Both mixed record types and repeated
levels of one type work when configured.

**Coverage:** F07 plus planned specialist tree. **Status:** Roadmap 0.8. **Example:** SC-09.

### US-H02 — Add or move a hierarchy item from its branch

**Story:** As a data steward, I want to create a child or choose a new parent in context so that I can
reorganize reference data without managing hidden connections.

**Accepted when:** child creation carries the selected parent, moving offers valid parents, the path
and parent relationship change together, and a move into the item's own descendants is rejected.
Routine edits stay live unless I explicitly choose a design draft; my place and input survive failure.

**Coverage:** F07 plus planned specialist tree. **Status:** Generic service available; specialist
browser flow roadmap 0.8. **Example:** SC-09.

## Integration consumer and data exchange operator

### US-I01 — Use stable public identities

**Story:** As an integration developer, I want stable record IDs and model keys so that my integration
does not depend on database sequence numbers or presentation labels.

**Accepted when:** public contracts expose stable UUIDs/keys and do not require internal numeric IDs.

**Coverage:** F16. **Status:** Available through the API.

### US-I02 — Page and resume bounded reads

**Story:** As an integration developer, I want explicit bounded pages so that large datasets do not
cause unpredictable load.

**Accepted when:** every synchronous collection has a documented maximum, continuation tokens are
opaque, and changing the query cannot silently reuse a continuation.

**Coverage:** F03, F16. **Status:** Available for current collections.

### US-I03 — Submit bounded bulk changes

**Story:** As an integration developer, I want to submit a batch of changes and learn the outcome for
each item so that I can recover rejected work without creating duplicates.

**Accepted when:** the supported batch size and failure policy are explicit, applied/rejected/unprocessed
items are distinguishable, and retry does not duplicate successful work. The same data and conflict
rules apply as for individual edits. Live changes and optional staged changes are clearly distinguished.

**Coverage:** Planned integration APIs. **Status:** Roadmap 0.9.

### US-I04 — Import and export asynchronously

**Story:** As an integration operator, I want validated, resumable import/export jobs so that large
files do not require an unbounded synchronous request.

**Accepted when:** validation can be previewed, job status resumes safely, failures are itemized and
completed output can be retrieved without holding one request open.

**Coverage:** Planned integration APIs. **Status:** Roadmap 0.9.

### US-I05 — Follow and deliver changes reliably

**Story:** As an integration developer, I want an ordered change feed and retryable webhooks so that
downstream systems can synchronize without repeatedly scanning all data.

**Accepted when:** a consumer can retain its position, resume in the documented order and recognize
repeated delivery. An expired position has an explicit recovery path. Delivery guarantees and retention
are documented; exactly-once delivery is not assumed.

**Coverage:** Planned integration APIs. **Status:** Roadmap 0.9.

### US-I06 — Query effective historical data

**Story:** As an integration consumer, I want model-declared effective-date and “as of” behavior so that
I can retrieve the correct business-time view where the data model supports it.

**Accepted when:** semantics are explicitly configured, bounded and consistent across paging rather
than inferred from arbitrary date fields.

**Coverage:** Planned advanced query. **Status:** Roadmap 0.9.

### US-I07 — Preview a file before changing reference data

**Story:** As a data steward receiving a supplier file, I want to identify its columns and inspect
proposed changes and errors so that I can correct mistakes before importing them.

**Accepted when:** the destination and supported file format are explicit, columns are associated
with declared fields, and the preview explains invalid values, duplicate keys and proposed additions
or updates by row. Preview changes no data; execution reports its agreed failure policy and outcomes.

**Coverage:** Planned import jobs. **Status:** Roadmap 0.9; format and duplicate policy require
planning decisions. **Example:** SC-10.

### US-I08 — Export the intended dataset

**Story:** As a data owner, I want to export a clearly selected workspace and scope so that the
recipient knows which reference data the file represents.

**Accepted when:** workspace, live/draft/history context where supported, filters and output format
are explicit. Completion can be checked later, large output is retrievable in the supported way and
partial output cannot be mistaken for a complete export. Field representation follows the documented
format contract.

**Coverage:** Planned export jobs. **Status:** Roadmap 0.9. **Example:** SC-10.

### US-I09 — Request the precise dataset an integration needs

**Story:** As an integration developer, I want supported combinations of business criteria beyond a
single screen's filters so that I can retrieve relevant reference data without downloading everything.

**Accepted when:** supported criteria and ordering are documented, declared field meanings and workspace
scope are respected, and every page continues the same request. Unsupported criteria produce an
explicit explanation. The implementation plan must agree the advanced query scope before promising
particular relationship filters or multiple sort fields.

**Coverage:** Planned advanced model-aware query. **Status:** Roadmap 0.9. **Example:** extend SC-10
with a configured integration query whose matching records span several pages.

## Workspace administrator

### US-A01 — Provision a workspace safely

**Story:** As a workspace administrator, I want to create a stable workspace and choose a clear label so
that users can select a governed scope without free-text invention.

**Accepted when:** the key is immutable and unique, the label can change, and the new workspace appears
in bounded discovery.

**Coverage:** F02. **Status:** Available through the API when the deployment capability is enabled.

### US-A02 — Change the default without ambiguity

**Story:** As a workspace administrator, I want to change the default workspace atomically so that
links without an explicit workspace resolve consistently.

**Accepted when:** the update uses the current runtime-state version and fails on concurrent change
instead of creating two defaults.

**Coverage:** F02, F17. **Status:** Available through the API when enabled.

### US-A03 — Retire a workspace without hiding its evidence

**Story:** As a workspace administrator, I want to prevent further changes while retaining read access
so that an obsolete workspace remains auditable.

**Accepted when:** the workspace remains discoverable/readable, mutations fail clearly, and the current
default cannot be retired.

**Coverage:** F02. **Status:** Available through the API when enabled.

## Model administrator

### US-P01 — Inspect the active application definition

**Story:** As a model administrator, I want to inspect and export installed definitions so that I can
understand the reproducible configuration currently in use.

**Accepted when:** installed releases remain readable even when mutation is disabled, and exported JSON
is the immutable installed content.

**Coverage:** F01, F15. **Status:** Browser implementation present and API available; composed-browser
validation is pending.

### US-P02 — Check a proposed model without changing runtime

**Story:** As a model administrator, I want to check a proposed definition and compare it with current
rules so that I understand mistakes and effects on existing data before putting it into use.

**Accepted when:** problems identify the definition that needs correction, comparison distinguishes
added/changed/removed rules, and checks explain incompatible existing data. Checking alone changes
neither the active definition nor reference data.

**Coverage:** F15. **Status:** Browser implementation present and API available when mutations are
enabled where needed; composed-browser validation is pending.

### US-P03 — Install without activating

**Story:** As a model administrator, I want installation to create an immutable inactive release so
that review and deployment selection remain separate.

**Accepted when:** installing the same definition again does not create a conflicting release, changing
an already released version is rejected, and users continue working under the current definition until
activation is explicitly chosen.

**Coverage:** F15, F17. **Status:** Browser implementation present and API available when mutations are
enabled; composed-browser validation is pending.

### US-P04 — Activate a compatible model safely

**Story:** As a model administrator, I want to put a checked definition into use so that everyone works
under consistent rules and existing valid data remains usable.

**Accepted when:** incompatible data or another administrator’s intervening change stops activation
with a clear explanation. A successful switch applies one consistent definition. If the service cannot
serve the selected definition, it reports unavailable rather than serving guessed or mixed rules.

**Coverage:** F15, F17, F19. **Status:** Browser implementation and API available in the supported
single-process administration mode; composed-browser validation is pending.

### US-P05 — Design a model with structured tools

**Story:** As an authorized model administrator, I want reference-aware forms and relationship matrices
so that I can evolve a model without editing raw JSON or relying on a graph canvas for simple tasks.

**Accepted when:** references are selected from catalogues, unsafe changes remain blocked pending an
explicit migration, previews use the same validation as installation and releases stay reproducible.

**Coverage:** Planned self-service authoring. **Status:** Roadmap 1.0.

### US-P06 — Introduce another reference-data application without bespoke software

**Story:** As a product administrator, I want to define a new reference-data domain using reusable
fields, relationships and views so that the organization can expand without commissioning another app.

**Accepted when:** after a valid definition release is activated, the configured navigation, fields,
rules and supported views are available through existing generic behavior. The standard maintenance
journeys work for two differently configured types without a custom domain-specific code path.

**Coverage:** F01, F15. **Status:** Definition foundation and JSON workbench present; composed browser
maintenance still needs 0.6 completion. Structured authoring follows in 1.0. **Example:** SC-12.

### US-P07 — Introduce new rules to one workspace in a controlled stage

**Story:** As a model administrator, I want to migrate one workspace to a new definition before
others so that I can control the change and preserve usable data throughout the rollout.

**Accepted when:** supported old and new definitions remain usable in their assigned workspaces,
data migration is checked, each request observes one consistent selection and a failed switch
preserves the prior usable state. For a historical draft incompatible with the active definition, the
user sees the named target definition (normally the historical draft’s definition), affected rules/data
and potential loss, then confirms that exact reviewed migration or
cancels. Cancel changes nothing; stale review requires a fresh check; confirmation still requires a
valid target graph and supported schema. Other workspaces and immutable history remain unchanged.
Recovery and the supported compatibility period are documented.

**Coverage:** Planned staged model rollout. **Status:** Roadmap 0.10; model selection is global today.
**Example:** SC-13.

### US-P08 — Reuse a proven definition package

**Story:** As a model administrator, I want to reuse a tested set of reference-data definitions so
that a new application does not require manually recreating the same fields and relationships.

**Accepted when:** two real reuse cases establish the package boundary, dependencies and compatibility
are explicit, and composed definitions pass the normal validation and release checks. Reuse does not
require special runtime behavior for a particular application.

**Coverage:** Planned reusable model modules and extensions. **Status:** Roadmap 1.0; package contract
follows demonstrated reuse needs. **Example:** extend SC-12 with two independently configured consumers.

## All users

### US-U01 — Operate the product with different input and screen needs

**Story:** As a user, I want core navigation and tasks to work with a keyboard and on a narrow screen so
that the product does not depend on hover, a pointer or a wide desktop layout.

**Accepted when:** Structure and controls have meaningful labels, focus is visible and restored after a
dialog, modal interaction is contained, essential actions remain discoverable, tables retain their
meaning and the target journeys work at both desktop and narrow sizes.

**Coverage:** F18. **Status:** Foundation available with component evidence; real-browser, automated
accessibility, screen-reader and visual proof remain 0.6 WP10 work.

## Platform operator and security administrator

### US-O01 — Receive an actionable startup refusal

**Story:** As a platform operator, I want an expected migration or schema problem explained without a
framework traceback so that I know the service state and exact safe recovery action.

**Accepted when:** readiness is 503, the message omits credentials, names current/target state, explains
the cause and gives the exact environment-appropriate command or escalation information.

**Coverage:** F19. **Status:** Available.

### US-O02 — Reactivate an older compatible model

**Story:** As a platform operator, I want to reactivate an older compatible model through the normal
release controls so that I do not mistake a bootstrap file change for model rollback.

**Accepted when:** the old installed release passes current compatibility and concurrency checks, the
runtime selection changes atomically, and changing the bootstrap path alone is not treated as
activation.

**Coverage:** F15, F19. **Status:** Available through the current model-release controls.

### US-O03 — Run safely with multiple writers and nodes

**Story:** As a platform operator, I want production database constraints and model propagation so that
uniqueness, activation and runtime selection remain correct across concurrent processes.

**Accepted when:** production-like tests prove multi-writer uniqueness, release propagation,
workspace migration, backup/restore and rollback without mixed-model requests.

**Coverage:** Planned production hardening. **Status:** Roadmap 0.10.

### US-O04 — Restore a matching application and database backup

**Story:** As a platform operator, I want a rehearsed application/database restore procedure so that a
schema rollback uses a known-consistent backup and matching software rather than an unsafe reverse
migration.

**Accepted when:** production-like rehearsal restores the database, application version and deployment
configuration together, verifies readiness and data, and keeps this procedure separate from model
release activation.

**Coverage:** Planned production hardening. **Status:** Roadmap 0.10.

### US-O05 — Know who changed governed data

**Story:** As a data owner investigating a change, I want reliable actor and time information so that
I can follow up with the responsible person or integration.

**Accepted when:** protected operations record authenticated identity rather than trusting a submitted
display name; record, relationship and administrative changes remain traceable through the appropriate
history. Access to history follows the agreed permissions.

**Coverage:** F11 plus authenticated audit. **Status:** Change history exists; authenticated attribution
is roadmap 0.10. **Example:** SC-13.

### US-O06 — Detect and investigate service degradation

**Story:** As a service operator, I want useful health and operating information so that I can notice
failures or slow operation and investigate without exposing private data to ordinary users.

**Accepted when:** agreed service measures can be observed, failed operations can be correlated with
controlled diagnostic information, and recovery guidance distinguishes expected refusal from an
unexpected fault. Representative load and recovery tests report results against explicitly agreed
operating targets.

**Coverage:** F19 plus metrics and structured operational diagnostics. **Status:** Health and expected
refusal foundation present; production observability is roadmap 0.10. **Example:** SC-13 under the
agreed representative workload.

### US-S01 — Authenticate and authorize sensitive operations

**Story:** As a security administrator, I want identity and permissions for applications, record types
and operations so that deployment flags are not mistaken for user access control.

**Accepted when:** administrative, ordinary and bulk paths enforce the same authenticated scope and
cannot be bypassed through a less-visible API.

**Coverage:** Planned production hardening. **Status:** Roadmap 0.10.
