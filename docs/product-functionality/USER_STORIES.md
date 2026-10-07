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

**Coverage:** F02. **Status:** Browser validated and API available (0.6 WP9, [navigation runner](../../frontend/e2e/wp9-navigation.mjs)).
### US-D02 — Return to my working list

**Story:** As a data steward, I want to open a record and return to the same search, filters and sort so
that investigating one item does not destroy my place.

**Accepted when:** Back/return restores the same workspace, application, view, search, typed filters,
sort and page size without issuing a broader request.

**Coverage:** F03, F04. **Status:** Browser validated and API available in every workspace (0.6 WP9).
### US-D03 — Find a value by business data

**Story:** As a data owner, I want to search names and configured fields and apply type-appropriate
filters so that I can locate a record without knowing its identifier.

**Accepted when:** Search is server-side, filter choices come from the active model, dates/numbers/
booleans are interpreted as their declared types, and invalid input is explained.

**Coverage:** F03, F06. **Status:** Browser validated and API available (0.6; any size since 0.8 Track S).
### US-D04 — Browse a large collection safely

**Story:** As a data steward, I want stable pages rather than an unbounded list so that the product
remains responsive as data grows.

**Accepted when:** Results have a documented page size, next/previous navigation keeps the selected
query, and a continuation from a different query is rejected.

**Coverage:** F03, F16. **Status:** Browser validated and API available; continuous scrolling, totals and jumps since 0.8 Track S.
### US-D05 — Understand one record in context

**Story:** As a data owner, I want to see a record's fields, parent, children, relationships and history
together so that I can understand its meaning and impact.

**Accepted when:** The detail composition follows the model, linked records can be opened, and empty
collections are shown as valid empty states rather than failures.

**Coverage:** F04, F07, F08, F11. **Status:** Browser validated and API available in every workspace and context (0.6 WP9).
### US-D06 — Add a live reference value directly

**Story:** As a data owner, I want to add an everyday reference value directly to an active workspace
so that routine maintenance does not require a change set and publication ceremony.

**Accepted when:** One create flow collects the core data, typed fields, parent and required
relationships; success is immediately visible and audited; no publication is created.

**Coverage:** F05-F07. **Status:** Browser validated and API available (0.6 WP9).
### US-D07 — Correct a live value directly

**Story:** As a data owner, I want to correct a name, availability flag, code or other field directly
so that live reference data stays accurate.

**Accepted when:** The saved correction becomes immediately visible with the same identity and
connections. Values keep their meaning. If someone saved a newer change, my attempted input remains
available while I review it; the product does not overwrite their work silently.

**Coverage:** F05, F06, F17. **Status:** Browser validated and API available (0.6 WP9).
### US-D08 — Distinguish missing, empty and false values

**Story:** As a data owner, I want optional values to retain their real meaning so that a missing value
is not confused with zero, false, empty text or a deliberate null.

**Accepted when:** Read, edit, filtering and history preserve the declared value and its missing/null
state.

**Coverage:** F03, F06. **Status:** Browser validated and API available (0.6 WP9).
### US-D09 — Move a record safely in a hierarchy

**Story:** As a data steward, I want to choose a new valid parent so that both navigation and business
relationships remain consistent.

**Accepted when:** The move changes the parent path and typed containment relationship together, rejects
cycles or invalid parent types, and cannot be bypassed by editing the relationship separately.

**Coverage:** F07, tree lens move dialog. **Status:** Delivered 0.8 (B3, accepted in B4 through SC-09).

### US-D10 — Manage an ordinary relationship

**Story:** As a data steward, I want to connect records using a meaningful relationship and edit its
own fields so that cross-references are governed, not hidden in free text.

**Accepted when:** I can find permitted records throughout my selected workspace, understand the
relationship in either direction and supply its required fields. The product rejects a connection
between incompatible records or too many/few connections, and does not overwrite a newer change.

**Coverage:** F08. **Status:** Browser validated and API available (0.6 WP9).
### US-D11 — Delete only after understanding the impact

**Story:** As a data owner, I want to preview dependants before deleting a record so that I do not
accidentally remove independent data.

**Accepted when:** The first step changes nothing and names affected owned records and relationships;
recursive deletion requires explicit confirmation; independent targets are retained.

**Coverage:** F10. **Status:** Browser validated and API available (0.6 WP9).
### US-D12 — See what changed

**Story:** As a data owner, I want to see the changes to a record over time so that I can investigate
why its content or connections differ from what I expected.

**Accepted when:** History includes the record and relevant relationship changes, supports loading
older entries, retains already loaded entries on failure and offers retry.

**Coverage:** F11. **Status:** Browser validated and API available (0.6 WP9).
### US-D13 — Use the same product for different reference-data domains

**Story:** As a data steward, I want applications, record types, fields and views to follow the active
model so that I can work in a new reference-data domain without learning a separately built product.

**Accepted when:** Navigation and presentation use the configured names and structures, the same generic
flows work for at least two differently configured record types, and no starter application or record
type receives hidden special behavior.

**Coverage:** F01. **Status:** Browser validated and API available; acceptance ran with two configured record types (0.6 WP10).
### US-D14 — Stop offering an obsolete value without deleting it

**Story:** As a data owner, I want to mark a value unavailable where my model supports it so that its
meaning and relationships remain available for investigation while consumers can exclude it.

**Accepted when:** availability is an ordinary live field edit, history and identity remain, and a
filter explicitly selecting available values excludes it. The interface does not equate this field
with deleting a record, retiring a workspace or withdrawing a publication.

**Coverage:** F05, F06, F11. **Status:** Browser validated and API available (0.6). **Example:** SC-02.
### US-D15 — Maintain a collection in its governing context

**Story:** As a data steward, I want one application browser to open an unscoped or contained
collection and its applicable model-defined tasks so that I can identify what every row belongs to
without switching between unrelated navigation systems.

**Accepted when:** containment records and collection entries share one model-driven browser; the
selected parent scope is visible and URL-backed; configured views over the same source object type are
available as labelled lenses of one collection; and applications with different or no containment and
mapping configurations receive no hidden starter-specific behavior. Search, compatible filters,
detail return and Live/Change set/History retain the selected scope.

**Coverage:** ADR-029; F01. **Status:** Browser validated (0.7 WP-14, composed acceptance in WP-9).

## Coordinated design and publication

A change set contains data changes; application-definition changes use the separate model administration stories.

### US-W01 — Prepare changes away from live data

**Story:** As a steward preparing a coordinated redesign, I want an optional change set so that I
can change several related records without affecting current users.

**Accepted when:** I can name a change set and choose current live data or a clearly identified historical source,
edit through familiar record controls and discard it without changing live data. Starting from current
live data includes all changes up to change set creation, as specified by US-W08.

**Coverage:** F12. **Status:** Browser validated and API available; a change set starts from current live data or a publication (0.6 WP9).
### US-W02 — Check the complete design before activation

**Story:** As a data owner, I want to validate the whole candidate dataset so that cross-record problems
are found before anything becomes live.

**Accepted when:** Validation checks fields, required relationships, uniqueness, cardinality,
containment and cycles without publishing or destroying the change set, and identifies actionable problems.

**Coverage:** F13. **Status:** Browser validated and API available (0.6 WP9); the review screen since 0.8 P2.
### US-W03 — Activate all coordinated changes or none

**Story:** As a data owner, I want one reviewed activation so that users never observe half of a
coordinated design.

**Accepted when:** The change set changes are merged, revalidated and published in one operation; any failure
leaves both live content and the change set preserved.

**Coverage:** F13, F17. **Status:** Browser validated and API available (0.6 WP9).
### US-W04 — Preserve unrelated live work during activation

**Story:** As a data owner, I want publishing to preserve live records that the change set did not touch so
that normal maintenance can continue while design work is open.

**Accepted when:** Untouched live changes remain, a live change to a touched record produces a precise
conflict, and no conflict is silently overwritten.

**Coverage:** F13, F17. **Status:** Browser validated and API available (0.6 WP9).
### US-W05 — Understand where a publication came from

**Story:** As a data owner, I want history to distinguish the snapshot used to start a change set from the
snapshot replaced at activation so that branching from older history remains truthful.

**Accepted when:** “Created from” and “superseded on activation” are separately visible and may contain
different publication identities.

**Coverage:** F14. **Status:** Browser validated and API available (0.6 WP9).
### US-W06 — Retire a publication without erasing history

**Story:** As a data owner, I want to remove the current-publication designation so that publication
history is accurate while its evidence remains available.

**Accepted when:** Retirement checks the expected current publication, clears publication as one workspace
action and retains workspace identity, record identities, snapshots and audit history. The interface
explains that live records remain readable and that this action does not make the workspace read-only.

**Coverage:** F14. **Status:** Browser validated and API available (0.6 WP9).
### US-W07 — Start reviewed changes from history

**Story:** As a data owner, I want to start a change set from an older snapshot so that I can use historical
content as a reference for reviewed new changes without editing history.

**Accepted when:** The old snapshot stays immutable, the new change set records its source, and publishing
uses fresh conflict and validation checks. Choosing the old snapshot alone does not undo live changes;
only explicitly authored changes are applied, and untouched newer live records remain.

**Coverage:** F12-F14. **Status:** Browser validated and API available (0.6 WP9).
### US-W08 — Begin a design with today's complete live content

**Story:** As a steward preparing coordinated changes, I want my change set to start with the data people
are using now so that recent corrections and additions are not absent from my working view.

**Accepted when:** starting from live includes changes made since the last publication and works when
live data exists without a publication. Later live edits do not rewrite that starting view. Starting
from an older publication remains an explicitly different choice.

**Coverage:** F12, F13. **Status:** Browser validated and API available (0.6 WP9; on PostgreSQL since 0.9.0-alpha.1 PG2). **Example:** SC-05.
### US-W09 — Work on the next model version in one change set while live keeps the current one

**Story:** As a steward, I want one change set to work under a not-yet-active model version while live data
and my other change sets keep the version in use, so that I can prepare for a model change without moving
the whole workspace onto it.

**Accepted when:** that change set reads, writes and validates under the version selected for it rather than
the globally active one, while live data, immutable history, every other change set and every other
workspace continue under the active version unchanged. A change set may select only a version that is
installed, complete and supported by this deployment; an unavailable, corrupt or unsupported selection
is refused with an explanation and changes nothing. Once the selected version becomes the active one,
that change set publishes through the ordinary path. A change set still on the replaced version is never quietly
moved onto another one: it can be discarded without model agreement, or explicitly moved onto the new
version where its content already satisfies it. Choosing a version changes nothing but that change set: it
never forces a model change through and never switches the version used anywhere else. Creation and
version changes require the complete candidate, including inherited content, to already fit. Refusal
leaves existing content and model selection unchanged; the browser refreshes all model-dependent
navigation/forms safely, preserving unsaved input when a version change is declined or fails.

**Coverage:** F12, F15, F17. **Status:** Browser validated and API available (0.7, accepted through SC-15, ADR-028). Moving a change set onto a version its content does not already satisfy is reviewed 0.11 migration work. **Example:** SC-15.
## Localization steward

### US-L01 — Create a valid translation in one operation

**Story:** As a localization steward, I want to enter translated content and select its language and
target together so that no incomplete translation is saved.

**Accepted when:** The translation, its group/containment and required target relationship succeed
together or not at all; at least one configured translated field is meaningful.

**Coverage:** F09. **Status:** Browser validated and API available (0.6 WP9).
### US-L02 — Avoid duplicate active translations

**Story:** As a localization steward, I want the product to prevent two active translations for the
same target and language so that consumers receive an unambiguous result.

**Accepted when:** The complete candidate scope is checked and a duplicate reports a clear conflict
without losing input.

**Coverage:** F09, F17. **Status:** Browser validated and API available; refused with the input kept (0.6, 0.8 A5).
### US-L03 — See translation coverage

**Story:** As a localization steward, I want a bounded target-by-language view of present and missing
translations so that I can focus on gaps without opening every record.

**Accepted when:** I can see which expected target/language combinations are missing, current or
present only in history, including beyond the first displayed page. Historical content does not count
as a completed current translation.

**Coverage:** F09, relation matrix lens (`relationMatrix` view). **Status:** Delivered 0.8 (A4, accepted
in A5 through SC-09).

### US-L04 — Correct or add a translation from its coverage cell

**Story:** As a localization steward, I want to edit where a target and language intersect so that I
can fill a gap without selecting the same target and language again.

**Accepted when:** the context is preselected, permitted content fields are editable, duplicate active
translations are prevented and the cell reflects a successful save. Routine changes can be live;
explicitly selected change set changes remain staged. Failed input is retained.

**Coverage:** F09, relation matrix cell dialog. **Status:** Delivered 0.8 (A4, accepted in A5).
**Example:** SC-09.

## Mapping steward

### US-M01 — See mapping coverage

**Story:** As a mapping steward, I want to see mapped, unmapped and ambiguous source values together so
that I can prioritize work and understand data quality.

**Accepted when:** The collection lens distinguishes a missing mapping, one selected target and several conflicting
targets. Large conflicting sets have an exact count and a way to inspect remaining targets without
an unlimited response. I can find candidates beyond the visible rows, using the configured relationship names and
direction, without opening each source individually. Parent scope and mapped/unmapped/ambiguous state
are visible server-side filters; another mapping declaration does not require another primary
navigation destination.

**Coverage:** Coverage/candidate/target APIs delivered (WP-4); mapping browser grid remains WP-8A.
**Status:** Browser validated and API available (0.7 WP-8A, accepted through SC-07).
### US-M02 — Replace one mapping atomically

**Story:** As a mapping steward, I want to create, clear or replace a selected mapping in one action so
that users never observe a delete-then-create gap.

**Accepted when:** A replacement becomes visible as one complete change. Clearing is offered only where
leaving the mapping empty is allowed. If another person changed the mapping, I can inspect their current choice before
retrying; my attempted replacement changes nothing until then.

**Coverage:** Atomic replacement API delivered (WP-5); browser actions/conflict recovery remain WP-8B.
**Status:** Browser validated and API available (0.7 WP-8B, accepted through SC-07).
### US-M03 — Resolve an ambiguous mapping safely

**Story:** As a mapping steward, I want to select the correct target for an ambiguous source so that the
result is protected by the same concurrency rule as an existing or missing mapping.

**Accepted when:** Resolving several conflicting targets has the same protection against overwriting
newer work as choosing a first target. Connections with another business meaning remain unchanged. Retaining an existing selected target
preserves its relation identity and declared attributes unless I explicitly change them.

**Coverage:** Atomic replacement API delivered (WP-5); browser actions/conflict recovery remain WP-8B.
**Status:** Browser validated and API available (0.7 WP-8B, accepted through SC-07).
### US-M04 — Create a missing mapping target in context

**Story:** As a mapping steward, I want to add a missing permitted target while mapping a source so
that I do not abandon the task and reconstruct its context elsewhere.

**Accepted when:** configuration permits creation, the usual target fields and validation apply, and
the new target can be selected on return. Cancelling or failing target creation leaves the current
mapping intact. Creating a target does not silently change the mapping before the chosen save action.

**Coverage:** Planned mapping workflow. **Status:** Browser validated and API available (0.7 WP-8B, accepted through SC-07). **Example:** SC-07.
## Hierarchy steward

### US-H01 — Find an item in a large hierarchy

**Story:** As a data steward, I want to expand relevant branches and see my location so that I can
work in a deep hierarchy without loading or navigating every item.

**Accepted when:** roots and children load in manageable portions, the path is clear, keyboard
navigation is supported and retry keeps already loaded branches. Both mixed record types and repeated
levels of one type work when configured.

**Coverage:** F07, tree lens (`tree` view). **Status:** Delivered 0.8 (B3, accepted in B4). **Example:**
SC-09.

### US-H02 — Add or move a hierarchy item from its branch

**Story:** As a data steward, I want to create a child or choose a new parent in context so that I can
reorganize reference data without managing hidden connections.

**Accepted when:** child creation carries the selected parent, moving offers valid parents, the path
and parent relationship change together, and a move into the item's own descendants is rejected.
Routine edits stay live unless I explicitly choose a change set; my place and input survive failure.

**Coverage:** F07, tree lens node menu and move dialog; with mouse or pen, also by dragging the record (B5); to the top level for a tree root type by either path (B5b). **Status:** Delivered 0.8 (B3, accepted in B4; drag in B5; top level in B5b).
**Example:** SC-09.

### US-H03 — Reshape a hierarchy without recreating its records

**Story:** As a data steward, I want to move a record to a place its type cannot stand, add or remove
a level, or change a record's type, so that I can reorganize reference data without recreating
records, re-importing them or losing what they held.

**Accepted when:** the places and types offered are the ones the model allows, with nothing declared
for restructuring; a record below a changed record follows level by level; before anything is written
a preview shows each record's new type, where each value comes from, what the new type has no place
for, and what is still needed, and the needed values can be given there; applying stays in a change
set and the review shows each type change; records keep their IDs and history; what had no place is
kept in history and offered back when a later type change gives it a place again. Everything works by
keyboard, and a phone gets the same dialogs without drag.

**Coverage:** F07, tree lens node menu (**Change type…**, **Insert level above…**, **Remove this
level…**, **Change type of all … in here…**), **Move to…** and drag to a place that changes the type,
the restructuring preview, the change set review; the restructuring API (ADR-034). **Status:**
Delivered 0.8 (C1–C4, accepted in C5). **Example:** SC-17.

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

**Coverage:** F03, F16. **Status:** Available through the API for every collection, by cursor or position (0.8 Track S).
### US-I03 — Submit bounded bulk changes

**Story:** As an integration developer, I want to submit a batch of changes and learn the outcome for
each item so that I can recover rejected work without creating duplicates.

**Accepted when:** the supported batch size and failure policy are explicit, applied/rejected/unprocessed
items are distinguishable, and retry does not duplicate successful work. The same data and conflict
rules apply as for individual edits. Live changes and optional staged changes are clearly distinguished.

**Coverage:** Planned integration APIs. **Status:** Available through the API for record items, inline or in the background (0.9 B1, B2); relationship and mapping items follow in 0.9 (B3).
### US-I04 — Import and export asynchronously

**Story:** As an integration operator, I want validated, resumable import/export jobs so that large
files do not require an unbounded synchronous request.

**Accepted when:** validation can be previewed, job status resumes safely, failures are itemized and
completed output can be retrieved without holding one request open.

**Coverage:** Background jobs, export and import jobs (`POST /batches`, `POST /exports`, `POST /imports`). **Status:** In progress for 0.9: background jobs with resumable status (B2), export jobs (J1) and import jobs through profiles (J2) are available through the API; the import preview follows (J3).
### US-I05 — Follow and deliver changes reliably

**Story:** As an integration developer, I want an ordered change feed and retryable webhooks so that
downstream systems can synchronize without repeatedly scanning all data.

**Accepted when:** a consumer can retain its position, resume in the documented order and recognize
repeated delivery. An expired position has an explicit recovery path. Delivery guarantees and retention
are documented; exactly-once delivery is not assumed.

**Coverage:** F25. **Status:** API available for the ordered feed, resume by position and repeat recognition (0.9 F1, journey J26); the expired-position recovery (F2) and consumer events and webhooks (C9–C13) are planned for 0.9.
### US-I06 — Query effective historical data

**Story:** As an integration consumer, I want model-declared effective-date and “as of” behavior so that
I can retrieve the correct business-time view where the data model supports it.

**Accepted when:** semantics are explicitly configured, bounded and consistent across paging rather
than inferred from arbitrary date fields.

**Coverage:** Planned advanced query. **Status:** Available through the API (0.9 Q4): a record type declares its effective period, and `asOf` reads apply it; SC-11 passes through the management API, and since 0.9 C16 through the consumer API.
### US-I07 — Preview a file before changing reference data

**Story:** As a data steward receiving a supplier file, I want to identify its columns and inspect
proposed changes and errors so that I can correct mistakes before importing them.

**Accepted when:** the destination and supported file format are explicit, columns are associated
with declared fields, and the preview explains invalid values, duplicate keys and proposed additions
or updates by row. Preview changes no data; execution reports its agreed failure policy and outcomes.

**Coverage:** Import profiles and import jobs (`/import-profiles`, `POST /imports`). **Status:** In progress for 0.9: profiles identify a file's columns, and rejected rows are reported by sheet, row and column (J2); the preview that changes nothing follows (J3), and its screen (J4). **Example:** SC-10.
### US-I08 — Export the intended dataset

**Story:** As a data owner, I want to export a clearly selected workspace and scope so that the
recipient knows which reference data the file represents.

**Accepted when:** workspace, live/change-set/publication context where supported, filters and output format
are explicit. Completion can be checked later, large output is retrievable in the supported way and
partial output cannot be mistaken for a complete export. Field representation follows the documented
format contract.

**Coverage:** Export jobs (`POST /exports`, `GET /jobs/{id}/output`). **Status:** Available through the API (0.9 J1): live, change-set and publication context, per-type criteria, a subtree, a business date, relationships, JSON Lines, CSV and XLSX, a manifest on the job and no output unless completed; the screen follows (J1u). **Example:** SC-10.
### US-I09 — Request the precise dataset an integration needs

**Story:** As an integration developer, I want supported combinations of business criteria beyond a
single screen's filters so that I can retrieve relevant reference data without downloading everything.

**Accepted when:** supported criteria and ordering are documented, declared field meanings and workspace
scope are respected, and every page continues the same request. Unsupported criteria produce an
explicit explanation. The implementation plan must agree the advanced query scope before promising
particular relationship filters or multiple sort fields.

**Coverage:** Planned advanced model-aware query. **Status:** Available through the API (0.9 Q1–Q3): cross-type lookup, the workspace edge list and the model-aware query with field, ancestor and one related-record criteria, one sort and chosen fields. **Example:** extend SC-10 with a configured integration query whose matching records span several pages.
## Workspace administrator

### US-A01 — Provision a workspace safely

**Story:** As a workspace administrator, I want to create a stable workspace and choose a clear label so
that users can select a governed scope without free-text invention.

**Accepted when:** the key is immutable and unique, the label can change, and the new workspace appears
in bounded discovery.

**Coverage:** F02. **Status:** Browser validated and API available when workspace administration is enabled (0.8 W4).
### US-A02 — Change the default without ambiguity

**Story:** As a workspace administrator, I want to change the default workspace atomically so that
links without an explicit workspace resolve consistently.

**Accepted when:** the update uses the current runtime-state version and fails on concurrent change
instead of creating two defaults.

**Coverage:** F02, F17. **Status:** Browser validated and API available when enabled (0.8 W4).
### US-A03 — Retire a workspace without hiding its evidence

**Story:** As a workspace administrator, I want to prevent further changes while retaining read access
so that an obsolete workspace remains auditable.

**Accepted when:** the workspace remains discoverable/readable, mutations fail clearly, and the current
default cannot be retired.

**Coverage:** F02. **Status:** Browser validated and API available when enabled (0.8 W4).
## Model administrator

### US-P01 — Inspect the active application definition

**Story:** As a model administrator, I want to inspect and export installed definitions so that I can
understand the reproducible configuration currently in use.

**Accepted when:** installed releases remain readable even when mutation is disabled, and exported JSON
is the immutable installed content.

**Coverage:** F01, F15. **Status:** Browser validated and API available (0.7 WP-11).
### US-P02 — Check a proposed model without changing runtime

**Story:** As a model administrator, I want to check a proposed definition and compare it with current
rules so that I understand mistakes and effects on existing data before putting it into use.

**Accepted when:** problems identify the definition that needs correction, comparison distinguishes
added/changed/removed rules, and checks explain incompatible existing data. Checking alone changes
neither the active definition nor reference data.

**Coverage:** F15. **Status:** Browser validated and API available; draft editing needs model administration enabled (0.7 WP-11).
### US-P03 — Install without activating

**Story:** As a model administrator, I want installation to create an immutable inactive release so
that review and deployment selection remain separate.

**Accepted when:** installing the same definition again does not create a conflicting release, changing
an already released version is rejected, and users continue working under the current definition until
activation is explicitly chosen.

**Coverage:** F15, F17. **Status:** Browser validated and API available when model administration is enabled (0.7 WP-11).
### US-P04 — Activate a compatible model safely

**Story:** As a model administrator, I want to put a checked definition into use so that everyone works
under consistent rules and existing valid data remains usable.

**Accepted when:** incompatible data or another administrator’s intervening change stops activation
with a clear explanation. A successful switch applies one consistent definition. If the service cannot
serve the selected definition, it reports unavailable rather than serving guessed or mixed rules.

**Coverage:** F15, F17, F19. **Status:** Browser validated and API available in the supported single-process administration mode (0.7 WP-11).
### US-P05 — Design a model with structured tools

**Story:** As an authorized model administrator, I want reference-aware forms and relationship matrices
so that I can evolve a model without editing raw JSON or relying on a graph canvas for simple tasks.

**Accepted when:** references are selected from catalogues, unsafe changes remain blocked pending an
explicit migration, previews use the same validation as installation and releases stay reproducible.

**Coverage:** Planned self-service authoring. **Status:** Roadmap 0.10 for the editor with additive and
draft-only operations ([MODEL_AUTHORING.md](../MODEL_AUTHORING.md)); changes that need a migration in 1.0.

### US-P06 — Introduce another reference-data application without bespoke software

**Story:** As a product administrator, I want to define a new reference-data domain using reusable
fields, relationships and views so that the organization can expand without commissioning another app.

**Accepted when:** after a valid definition release is activated, the configured navigation, fields,
rules and supported views are available through existing generic behavior. The standard maintenance
journeys work for two differently configured types without a custom domain-specific code path.

**Coverage:** F01, F15. **Status:** Available: a new application is a model release edited as JSON in the workbench, and the generic browser serves it. Structured authoring follows in 0.10. **Example:** SC-12.
### US-P07 — Introduce new rules to one workspace in a controlled stage

**Story:** As a model administrator, I want to migrate one workspace to a new definition before
others so that I can control the change and preserve usable data throughout the rollout.

**Accepted when:** supported old and new definitions remain usable in their assigned workspaces,
data migration is checked, each request observes one consistent selection and a failed switch
preserves the prior usable state. For a change set started from a publication incompatible with the active definition, the
user sees the named target definition (normally the change set started from a publication’s definition), affected rules/data
and potential loss, then confirms that exact reviewed migration or
cancels. Cancel changes nothing; stale review requires a fresh check; confirmation still requires a
valid target graph and supported schema. Other workspaces and immutable history remain unchanged.
Recovery and the supported compatibility period are documented.

**Coverage:** Planned staged model rollout. **Status:** Roadmap 0.11; model selection is global today.
**Example:** SC-13.

### US-P08 — Reuse a proven definition package

**Story:** As a model administrator, I want to reuse a tested set of reference-data definitions so
that a new application does not require manually recreating the same fields and relationships.

**Accepted when:** two real reuse cases establish the package boundary, dependencies and compatibility
are explicit, and composed definitions pass the normal validation and release checks. Reuse does not
require special runtime behavior for a particular application.

**Coverage:** Planned reusable model modules and extensions. **Status:** Roadmap 1.0; package contract
follows demonstrated reuse needs. **Example:** extend SC-12 with two independently configured consumers.

### US-P09 — Turn a spreadsheet into an application without a model file or a script

**Story:** As a model administrator, I want to upload a workbook of reference data, get a proposed model
and import mapping, and change both freely before loading, so that new reference data does not need
model engineering and a bespoke import script.

**Accepted when:** every proposal shows its evidence and can be renamed, remapped, split, merged, moved
or removed; each change shows its effect on the real rows before anything is written; the model is
installed and activated through the normal release checks; the data arrives in a change set reviewed
before publishing; and the journey works for two differently shaped workbooks, extending an existing
model and starting a new application.

**Coverage:** Planned model authoring. **Status:** Roadmap 0.10
([MODEL_AUTHORING.md](../MODEL_AUTHORING.md)). **Example:** SC-12 through the editor.

### US-P10 — Load the next version of a workbook through its saved mapping

**Story:** As a data owner, I want to upload the next version of a workbook to its saved mapping so
that I review only what changed instead of repeating the setup.

**Accepted when:** new or missing columns, new list values and name drift are reported before loading;
records are matched by their stable keys; the change set review shows the added, changed and missing
records; and missing records are never deleted unless the mapping says so.

**Coverage:** Planned model authoring, on the 0.9 import job. **Status:** Roadmap 0.10.

## All users

### US-U01 — Operate the product with different input and screen needs

**Story:** As a user, I want core navigation and tasks to work with a keyboard and on a narrow screen so
that the product does not depend on hover, a pointer or a wide desktop layout.

**Accepted when:** Structure and controls have meaningful labels, focus is visible and restored after a
dialog, modal interaction is contained, essential actions remain discoverable, tables retain their
meaning and the target journeys work at both desktop and narrow sizes.

**Coverage:** F18. **Status:** Browser validated: keyboard and narrow-layout journeys (0.6 WP10), automated accessibility and visual regression gates in light and dark themes (0.7). No screen-reader user testing is recorded.
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

**Coverage:** Planned production hardening. **Status:** Roadmap 0.11.

### US-O04 — Restore a matching application and database backup

**Story:** As a platform operator, I want a rehearsed application/database restore procedure so that a
schema rollback uses a known-consistent backup and matching software rather than an unsafe reverse
migration.

**Accepted when:** production-like rehearsal restores the database, application version and deployment
configuration together, verifies readiness and data, and keeps this procedure separate from model
release activation.

**Coverage:** Planned production hardening. **Status:** Roadmap 0.11.

### US-O05 — Know who changed governed data

**Story:** As a data owner investigating a change, I want reliable actor and time information so that
I can follow up with the responsible person or integration.

**Accepted when:** protected operations record authenticated identity rather than trusting a submitted
display name; record, relationship and administrative changes remain traceable through the appropriate
history. Access to history follows the agreed permissions.

**Coverage:** F11 plus authenticated audit. **Status:** Change history exists; authenticated attribution
is roadmap 0.12. **Example:** SC-13.

### US-O06 — Detect and investigate service degradation

**Story:** As a service operator, I want useful health and operating information so that I can notice
failures or slow operation and investigate without exposing private data to ordinary users.

**Accepted when:** agreed service measures can be observed, failed operations can be correlated with
controlled diagnostic information, and recovery guidance distinguishes expected refusal from an
unexpected fault. Representative load and recovery tests report results against explicitly agreed
operating targets.

**Coverage:** F19 plus metrics and structured operational diagnostics. **Status:** Health and expected
refusal foundation present; production observability is roadmap 0.11. **Example:** SC-13 under the
agreed representative workload.

### US-S01 — Authenticate and authorize sensitive operations

**Story:** As a security administrator, I want identity and permissions for applications, record types
and operations so that deployment flags are not mistaken for user access control.

**Accepted when:** administrative, ordinary and bulk paths enforce the same authenticated scope and
cannot be bypassed through a less-visible API.

**Coverage:** Planned security release. **Status:** Roadmap 0.12.
