# Realistic scenarios for recurring product validation

These are proposed product acceptance examples, not executed tests. Use them to build browser tests,
service tests and moderated task walkthroughs. Record the actual result separately using the
[validation guide](VALIDATION_GUIDE.md). A future capability remains planned even when its scenario is
fully specified.

## Shared example data

Use an isolated dataset with two named workspaces, “Retail Reference” and “Warehouse Reference.”
Choose Retail as the default. Give both a record called “Delivery Methods” with different records and
identities so an accidental workspace fallback is detectable.

In Retail, configure a Domain containing a Delivery Methods codelist with values such as `COLLECT`
(“Collecton”), `COURIER` (“Courier”) and `LEGACY` (“Legacy delivery”). A separate Payment Methods
codelist has `CARD` (“Card”). Configure availability as a boolean and a numeric field for a second
record type. Include enough records for at least three pages at the configured page size.

Create a Warehouse System and independent System Values, including `PICKUP`. Permit a mapping to a
Master Value. Create Czech and English Language records and valid Translation Groups. Include a
translation target relationship that is required and an optional system association that does not
own its target. These are model configuration examples, not new runtime special cases.

For future specialist tests, explicitly supply the proposed mapping, translation or tree configuration
only when that view is implemented. Never pretend today's table is the specialist view. Add a second
valid domain/configuration to exercise shared behavior beyond the delivery example.

## SC-01 — Find the correct record without losing my place

**Stories:** US-D01–D05, US-D13, US-U01. **Target:** 0.6 browser.

**Given** Warehouse is selected and a filtered list is on a later page, **when** the steward opens
Delivery Methods, follows a related record, reads history and returns, **then** each read stays in
Warehouse and the original search, filter, order, page size and position are recovered. Retail's
similarly named record must never be substituted.

Repeat with a date or numeric filter in another configured type. A record beyond the first page can
be found. A successful empty relationship section says it is empty; a failed section offers retry.
Retry preserves successful content and the selected workspace.

**Simplicity check:** no reselecting the workspace, reconstructing filters or repeating the search.

## SC-02 — Correct a label while someone else is working

**Stories:** US-D06–D08, US-D12, US-D14. **Target:** 0.6 browser and live service.

**Given** `COLLECT` is live as “Collecton,” **when** a steward changes its name to “Collection” and
saves, **then** normal reads show the correction immediately with the same identity, fields and
connections. History records the change. No draft or publication is required, including when an
unrelated design draft is open.

**Given** two stewards opened the same version, **when** the first saves and the second then saves a
different name, **then** the second save does not overwrite the first. The second steward can still
see their attempted input and review current content before explicitly retrying.

Repeat with a configured numeric zero and an availability value of false. Neither becomes blank or
missing. Marking `LEGACY` unavailable retains its record and links; only a query explicitly selecting
available values excludes it. A cancelled edit changes nothing.

**Simplicity check:** one editing surface and one save for an ordinary correction; no activation.

## SC-03 — Add a value or translation without incomplete intermediate records

**Stories:** US-D06, US-D08–D10, US-L01–L02. **Target:** 0.6 browser and service.

**Given** Delivery Methods is open, **when** a steward adds `LOCKER` (“Parcel locker”), **then** one
flow collects the required fields and parent. The saved value appears under the codelist with the
correct relationship. The user need not create a second connection manually.

**Given** the Czech group is selected, **when** a localization steward adds “Výdejní místo” for
`COLLECT`, **then** one save creates the translation, its grouping and its required target connection.
Missing required content, a disallowed target or a duplicate active target/language produces a clear
correction request and leaves no incomplete translation. Preserve the entered text.

Repeat creation for a root record and another valid target type. An optional field can be removed
without removing the record. Removing the last required meaningful content must fail clearly.

**Simplicity check:** choose each context once; no “save an invalid record, then repair its links” step.

## SC-04 — Delete with a truthful impact preview

**Stories:** US-D10–D11. **Target:** 0.6 browser and service.

**Given** a codelist owns child values and has an optional association with a System Value, **when**
the owner requests deletion, **then** the preview identifies owned records and affected connections.
Cancel preserves everything. Confirm removes the intended owned records and their affected links,
while the independent System Value and its own hierarchy survive.

Repeat in an optional design draft: the candidate changes, but live reads and old snapshots do not.
The preview locks the displayed hierarchy. If any displayed object, attribute, parent link or affected
relationship changes, or another descendant/affected relationship is added before confirmation, the
service rejects deletion without side effects and asks the user to retry. Confirmation always uses the
opaque token returned by that exact preview and never silently expands or changes the confirmed set.

**Simplicity check:** confirmation explains concrete impact rather than requiring generic repeated
“Are you sure?” acknowledgements.

## SC-05 — Start a design from what is live today

**Stories:** US-W01, US-W08. **Target:** 0.6 design acceptance; GAP-02 is accepted, implementation remains WP8.1-B.

**Given** the latest publication predates a live `LOCKER` addition and a corrected label, **when** a
steward chooses “start from current live data,” **then** the new draft contains both the addition and
the correction exactly as they were when the draft started. Later live changes do not silently rewrite
that draft's starting content.

Repeat in a workspace containing live records but no published revision. The user must not publish a
dummy change or copy live records manually merely to begin a design. Choosing an older historical
snapshot is a separate, explicitly labelled action.

**Simplicity check:** “current” never means “the last time someone published.”

## SC-06 — Publish coordinated changes while preserving normal maintenance

**Stories:** US-W01–W04. **Target:** 0.6 design browser and service.

**Given** a draft changes two Delivery Methods records and a permitted relationship, **when** someone
corrects the live Payment Methods `CARD` description and the design is then validated and activated,
**then** live readers see none of the staged changes before activation and all of them afterward.
The live Card correction survives and is included in the new historical snapshot.

Make a separate live addition while the draft is open; it survives too. Then run the conflict variant:
change `COLLECT` both live and in the draft. Activation must identify the conflict, preserve the draft
and all live data, and publish none of the other staged changes.

Also introduce a cross-record rule violation. Validation identifies the relevant records without
publishing; activation checks the final combined result again even if a previous check passed.

**Simplicity check:** one workspace-level activation; no activation buttons on each record.

## SC-07 — Resolve a mapping without losing the existing answer

**Stories:** US-M01–M04. **Target:** 0.7; planned.

**Given** `PICKUP` needs a canonical target, **when** the steward opens mapping coverage, searches for
“Collection” and saves the selection, **then** the row has that one target. Repeat from an unmapped
row, an existing different mapping and an ambiguous row with several targets. Clear is offered only
where an empty mapping is allowed.

If another steward changes the mapping first, show the current targets and preserve the attempted
choice for review. Never temporarily leave a previously mapped source unmapped while replacing it.
An unrelated mapping relationship remains unchanged. Where allowed, create a missing target in context;
cancelling creation leaves the existing mapping intact.

Repeat with another relationship configuration, including different direction and labels.

**Simplicity check:** the user selects a business target, not individual links to delete and recreate.

## SC-08 — Understand history without accidentally promising rollback

**Stories:** US-W05–W07, US-A03, US-D12. **Target:** 0.6 history browser and service.

**Given** two publications and later live corrections, **when** a steward opens the older snapshot,
**then** its content remains as published. Starting a draft from it clearly identifies the source.
Activation of reviewed changes identifies the publication it replaces separately and preserves
unrelated newer live records. Simply selecting the old snapshot does not undo today's data.

**When** the current publication is retired, **then** publication history has no current selection,
old snapshots remain readable and the interface does not claim that live records were withdrawn.
**When** the workspace itself is retired after choosing another default, **then** it remains readable
and rejects changes. Business unavailability of one record is a third, separate operation.

**Simplicity check:** each action says what will change and what remains available, in user language.

## SC-09 — Fill translation gaps and maintain a deep hierarchy

**Stories:** US-L03–L04, US-H01–H02. **Target:** two separately accepted 0.8 workflows; planned.

For translation, show Delivery Methods by the configured target languages. Include a current Czech
translation, a missing English translation and a translation found only in history. From the missing
cell, enter the English content and save in context. Only usable current content counts as covered;
duplicate active content is rejected. Ordinary correction must still be possible without a draft.

For hierarchy, find a nested System Group without loading every branch, add a child under it and move
that child to another permitted group. Show the new path and leave unrelated branches alone. Reject a
move beneath the child's own descendant. Repeat with a hierarchy containing different record types.

**Simplicity check:** each task starts from the relevant cell or branch and can be completed by
keyboard; users do not reconstruct language, target or parent context on separate screens.

## SC-10 — Exchange a supplier file and recover an interrupted synchronization

**Stories:** US-I03–I05, US-I07–I08. **Target:** 0.9; planned.

An operator receives a supplier code file containing a new value, an existing value, an invalid
number and a duplicate business key. They select the destination, identify the columns and preview
the proposed changes. The preview reports errors by row and field and changes no live data.

Execution follows the explicitly chosen failure policy. The result distinguishes applied, rejected
and unprocessed rows. An interrupted job can be reopened; retry does not create duplicate records.
Exporting the chosen filtered scope states that scope and preserves supported field meanings. Do not
promise a lossless format round trip until the file contract defines one.

Separately, an integration reads changes, stores its position and restarts after interruption. It can
recognize repeated delivery and recover from an unavailable old position without silently missing
changes. Change-feed recovery is distinct from retrying an import job.

**Simplicity check:** users can act on failed rows without redoing successful work blindly.

## SC-11 — Answer a business-date question

**Stories:** US-I06. **Target:** 0.9; planned, date semantics require agreement.

**Given** an explicitly configured reference list has old and replacement values with agreed validity
boundaries, **when** a consumer asks for the values applicable on either side of a boundary, **then**
the result follows those business dates across every page. Test the boundary itself, overlapping
periods and the configured time zone. A request to an unconfigured list must not invent effective-date
behavior from an arbitrary date field.

**Simplicity check:** business validity, change history and publication time are labelled separately.

## SC-12 — Introduce a new reference-data domain

**Stories:** US-P01–P06, US-D13. **Target:** existing definition workbench; 1.0 structured authoring.

An administrator defines a new “Return Reasons” domain with its own fields, relationships and table.
They save and check a proposed definition, inspect differences and compatibility, install it, then
explicitly activate it. Installation alone changes no user's active application. Reusing a released
identity for changed content is rejected. An incompatible field change leaves the current definition
and data usable and explains the required next step.

After activation, a steward can use the new navigation and ordinary record flows without a special
software branch for Return Reasons. In 1.0, repeat authoring through structured controls using the
same release protections. Read-only inspection remains usable when administration is disabled.

**Simplicity check:** release safety is visible, but raw configuration editing is not required of the
ordinary data steward.

## SC-13 — Operate safely and move one workspace to new rules

**Stories:** US-S01, US-O01–O06, US-P07. **Target:** existing operational refusal behavior; remaining
production controls and staged rollout are 0.10 plans.

Verify an expected startup problem reports what failed, the service state and the safe recovery action
without requiring traceback interpretation. In the production milestone, a reader cannot edit through
any channel, a permitted editor can edit only the assigned scope, and history attributes the change
to authenticated identity.

Rehearse migrating Retail to a new definition while Warehouse remains on its supported definition.
Each request sees consistent rules and data. A failed migration leaves Retail usable under its old
selection. Rehearse restoring a matching backup and application, and record actual recovery time and
data loss against agreed targets rather than assuming them.

For the accepted GAP-02 historical migration variant, derive a draft from an older publication whose
model conflicts with current rules. Base 0.6 refuses activation while preserving draft/live data.
In 0.10, name the selected workspace and installed target definition (normally the historical pin),
then preview exact rule changes and potential data loss without changing data; cancelling leaves
everything unchanged. Explicitly confirm the reviewed transformation and prove the target data and
workspace model switch together, history stays immutable and Warehouse is unaffected. A live/draft/
model change after preview invalidates confirmation; a missing transform, unsupported parser or invalid
result cannot be accepted by acknowledging a warning. Failure preserves the prior usable state.

**Simplicity check:** access refusal and recovery messages identify a useful next action; the user is
not asked to understand deployment mechanics to correct an ordinary field.

## SC-14 — Establish a working area and preserve stable access

**Stories:** US-A01–A03, US-I01–I02. **Target:** current workspace administration and read services;
browser administration has no separately committed screen milestone.

An administrator creates Warehouse Reference with a stable key, then changes its display label.
Existing explicit links and integration references still select the same workspace and records.
Duplicate keys are refused. Selecting a new default changes only requests without an explicit
workspace; it does not redirect an explicit Retail request.

Two administrators attempt to change the default from the same starting selection. One succeeds; the
other receives a conflict and can review the actual default. The current default cannot be retired.
After selecting another default, retirement preserves read access and rejects mutations.

An integration reads several pages, retains a continuation and resumes the same query. A continuation
from a different workspace or query is refused explicitly. Changing a record's label does not require
replacing its public identity. Unknown workspace keys fail rather than selecting the default.

**Simplicity check:** people choose recognizable labels; stable technical identifiers are managed by
the interface or integration rather than copied manually during ordinary stewardship.

## Repeated usability measurements

For a first walkthrough, record a baseline rather than inventing completion-time promises. On later
reviews compare the same task, starting point, data volume, input device and user familiarity.

| Measure | Record | Regression signal |
| --- | --- | --- |
| Completion | Completed unaided, completed with help, or blocked | A formerly available task is blocked or needs help |
| Navigation | Screens, context switches and context re-entry | The user reconstructs context already known to the product |
| Decisions | Required choices and confirmations, with reasons | A new mandatory step has no named benefit or risk |
| Editing | Save attempts and repeated entry | An error or conflict loses input or requires avoidable re-entry |
| Time | Observed task duration and reason for delay | A repeated slowdown under comparable conditions |
| Recovery | What was preserved and what the user did next | Retry resets unrelated content or obscures partial success |

Run core tasks with keyboard-only input and a recorded narrow-screen size as well as desktop. Do not
substitute a click count for success, safety or accessibility. A justified extra confirmation for
dependent deletion differs from requiring a publication for a spelling correction.
