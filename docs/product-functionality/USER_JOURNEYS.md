# User journeys

These journeys are what the engine is for. Every client is a user: a steward in the browser, an
integrator calling the API from another system, an operator running the service, a model author.
The engine is an integration engine and the API is the product: every journey with an API channel is
complete through the API alone, and the browser is one client of it
([testing strategy](../testing/STRATEGY.md#what-the-engine-is-for-testing-purposes)).

Each journey is the shortest flow that satisfies its user's goal; a change should not add ceremony
unless it protects a named risk. Concrete data and expected outcomes are in the
[acceptance scenarios](ACCEPTANCE_SCENARIOS.md), on their shared example data.

**Catalogue, 2026-10-02 (H4a).** Revised the same day to generic journeys: records, hierarchies and
relationships within and across applications, never the example model's domains. Extended from
J01–J12 to every client of the engine for the
[testing consolidation](../TEST_HARNESS_PLAN.md#h4-testing-consolidation). Every test will name the
journey or variant it walks (`@pytest.mark.journey("J02.2")`), every piece of code traces to a
journey, and every API route and parameter is mapped to journeys in
[API_JOURNEYS.md](../testing/API_JOURNEYS.md). J11 was split the same day: bulk changes stay J11,
background jobs are J24, the change feed J26 and supplier files J27.

## How to read a journey

- **Actor** and **Channel**: who, and through what: `API` (the management API), `UI` (the browser
  application), `Operator` (process, settings, commands).
- **Stories** and **Scenario**: the [user stories](USER_STORIES.md) it serves and the
  [acceptance scenario](ACCEPTANCE_SCENARIOS.md) whose data it runs on.
- **Status**: delivered, or the package that delivers it.
- **Steps**: the main path.
- **Variants** (`J02.1`, `J02.2`, …): other ways to reach the same goal and the situations that
  threaten it, including concurrency. A variant is tested like a journey.
- **Refusals**: what the actor is told when the goal cannot be reached, by error code. A refusal
  changes nothing unless the journey says otherwise.
- **Evidence today**: the tests and runners that walk it before H4c replaces them with journey
  tests. Listed to find gaps, not as a coverage claim.
- **Data.** A journey is the engine's, never the example model's. Its test runs on at least two
  model configurations that differ in keys and shape (the example model is one, a generated model
  another), and asserts nothing that names a configuration's keys. The example scenarios give
  realistic situations; they are not what is tested.

## Journey index

| Group | Journeys |
| --- | --- |
| Records and structure | J01 find, J02 correct, J03 add, J04 delete, J13 relate, J14 hierarchy, J15 reshape across types, J32 change many at once |
| Relationship sets and coverage | J10 replace a record's related records, J16 coverage across ancestors (J09 retired) |
| Change sets and history (designer) | J05 prepare and publish, J06 live beside a change set, J07 withdraw and restart from history, J17 review changes, J18 next model version |
| Administration | J08 model release, J19 workspaces, J25 consumer API definition |
| Model authoring | J33 design a model in the editor, J34 onboard a workbook, J35 load the next version of a workbook |
| Integration | J11 bulk change, J20 discover, J21 read completely, J22 precise dataset, J23 business date, J24 background job, J26 follow changes, J27 supplier file, J28 consumer read, J29 consumer lookup, J30 consumer events |
| Operations | J12 run, refuse and recover, J31 check the deployment |

## Records and structure

The engine's core: records of model-declared types, placed in containment hierarchies and related
to each other within one application and across applications, under the rules the model declares.
Every journey here is stated in those terms. The example model's translations, systems and mappings
are one configuration of them; no journey, and no test, is about the example model itself.

The rules these journeys exercise, all declared by the model:

- **Containment:** a parent contains children (`parentOf`), within one type (a self-hierarchy of any
  depth) or across types; a type may have parents of several types; root types stand at the top.
  The containment relationship is maintained by the engine with the record's parent.
- **Relationships** between independent records, of an allowed type pair, oriented with a forward and
  a reverse name, with a cardinality (one-to-one, one-to-many, many-to-many), optional or required,
  carrying typed attributes the pair declares.
- **Ownership:** a required one-to-one or one-to-many relationship makes its target a dependant of
  its source; an optional or many-to-many one is an association.
- **Scoped uniqueness:** a relationship unique per source and an ancestor of its target, optionally
  only while a target attribute has a given value; a record attribute unique in the workspace.
- **Attribute rules:** required, read-only, unique, at least one of a set, minimum and maximum, and an
  effective period.

### J01 — Find and inspect a record

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-D01–D05, US-D13, US-I01.
**Example scenario:** SC-01, SC-16. **Status:** delivered.

1. Select a workspace by label (an integrator names its key).
2. Select an application and view, or the object type.
3. Search, filter or sort by the fields the view or type offers.
4. Open a result: its fields, its path up the hierarchy, its related records in both directions, and
   its history.
5. Return to the exact list state.

The user never needs a database ID or a second manual search. An empty relationship section is an
empty result, not an error. A failed page or panel can retry without losing successful content.

**Variants:**

- **J01.1 In a change set or a publication**: the staged or published content, never live.
- **J01.2 In a non-default workspace**: every read stays in the named workspace; a similarly named
  record elsewhere is never substituted.
- **J01.3 Typed filters**: text, number, boolean, date and null-or-unset keep their types; `false`
  and `0` are values, not blanks.
- **J01.4 Across types**: one search over every type, or over chosen types.
- **J01.5 One value**: read one attribute value of a record, in any context.
- **J01.6 History**: a record's audit history, newest first, with the events of its relationships.
- **J01.7 Related records of another application**: the relationships of a record list records of
  any application, searched and sorted by their fields.
- **J01.8 Related records in a list** (0.9 K5): a list's rows show their first related records of
  a relationship (three in the UI, `expandLimit` through the API) in name order, and how many there
  are, live, in a change set and in a publication; the model's view or panel declares the column
  (`related:<key>`), an integrator names it with `expand`. A column whose row holds at most one
  related record sorts by its name, rows without one last; a hidden column is not read.
- **J01.9 A field of the related records in a list** (0.9 K5a): the column names a field of the
  related records or of a record above them (`related:<key>.<field>`, the field as the consumer API
  writes it: `name`, an attribute, `ancestor:<type>.<field>`), and each chip shows that value, "—"
  where a record has none; such a column does not sort.
- **J01.10 Filter a list by its records' relationships** (0.9 K6): the records related, through one
  relationship, to any of chosen records, to none, or to any (`filter.related:<key>.eq` and
  `.isNull`); with the search and other filters, in every context, paged with totals; in the
  browser from the view's `filterFields`, the chip naming the chosen records after a reload. A column
  showing a field of the related records offers no filter.
- **J01.11 Records under an ancestor with a field** (0.9 K7, D178): the model-aware query keeps the
  records under an ancestor of a type whose name or attribute meets a criterion
  (`ancestor:<type>.<field>`, the list's operators), at any depth, in every context.

**Refusals:** `404 WORKSPACE_NOT_FOUND`, `404 OBJECT_NOT_FOUND`, `404 UNKNOWN_OBJECT_TYPE`,
`422 INVALID_FILTER`, `422 INVALID_SORT`, `422 INVALID_EXPAND`, `422 MUTUALLY_EXCLUSIVE_CONTEXT`,
`404 CHANGE_SET_NOT_FOUND`, `404 PUBLICATION_NOT_FOUND`.

**Evidence today:** `wp9-navigation`, `ui03a-navigation`, `s5-continuous-lists`,
`wp14-contextual-browser`; `test_typed_table_queries`, `test_query_foundations`,
`test_cross_type_lookup`, `test_context_read_parity`, `test_attributes`.

### J02 — Correct a record

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-D07, US-D08, US-D12, US-D14.
**Example scenario:** SC-02. **Status:** delivered.

1. Open the live record.
2. Change its name or typed values.
3. Save against the version originally read.
4. See the updated record and an audit entry.

No change set and no publication is involved, also when an unrelated change set is open. One
coherent edit is one save; the record keeps its identity, its place and its relationships.

**Variants:**

- **J02.1 Rename a record**: it keeps its identity, place and relationships, and the paths of its
  descendants show the new name.
- **J02.2 Two writers save the same version**: the second is refused with the record's current
  version, to read it again; nothing is overwritten.
- **J02.3 Zero and false** stay values, never blank.
- **J02.4 One value through its own resource**: set, change or remove one attribute value against
  the record's version.
- **J02.5 Attribute rules**: a value outside its bounds, a unique value already taken, removing a
  required value, emptying the last of an at-least-one-of set, and changing a read-only value are
  each refused with the rule named.
- **J02.6 Correct it from the header** (UI, Base 0.9 UA8): the record's title (usually its name) and
  subtitle are edited in place in its header, on the full page and in the inspector, as a details
  field is; an empty editable subtitle offers Add; saving claims the record's version.

**Refusals:** `409 VERSION_CONFLICT`, `409 DUPLICATE_ATTRIBUTE_VALUE`, `422 INVALID_ATTRIBUTE_VALUE`
(a value of the wrong type), `422 ATTRIBUTE_BELOW_MINIMUM`, `422 ATTRIBUTE_ABOVE_MAXIMUM`,
`422 UNKNOWN_ATTRIBUTES`, `422 OBJECT_ATTRIBUTE_RULE_VIOLATION`,
`422 CANNOT_DELETE_REQUIRED_ATTRIBUTE`, `422 READ_ONLY_ATTRIBUTES`, `409 ATTRIBUTE_ALREADY_EXISTS`,
`404 ATTRIBUTE_NOT_FOUND`, `409 WORKSPACE_RETIRED`.

**Evidence today:** `wp9-authoring`, `ua8-record-in-place`; `EditableField.test`; `test_api`,
`test_attributes`, `test_rule_parity`, `test_pg3_concurrency`.

### J03 — Add a record where it belongs

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-D06, US-D08–D10, US-L01,
US-L02. **Example scenario:** SC-03. **Status:** delivered.

1. Start from where the record belongs: a root collection, a parent, or a record it must be related to.
2. Enter its name and typed values.
3. Name its parent, when its type has one, and its required relationships, in the same request.
4. Save once.

The record, its values, its containment and its required relationships appear together or none of
them do.

**Variants:**

- **J03.1 A root record** of a type that may stand at the top.
- **J03.2 A contained record** under a parent of an allowed type, in a self-hierarchy or under
  another type.
- **J03.3 A dependent record** created with its required relationship to an owner, in the same or
  another application.
- **J03.4 Relationships given at creation**, with their typed attributes.
- **J03.5 Scoped uniqueness at creation**: a second record related to the same source within the
  same ancestor is refused, and allowed once the condition attribute no longer holds.
- **J03.6 With a supplied ID**, which the integrator keeps.
- **J03.7 In a change set**, invisible to live readers until published.
- **J03.8 Two creates racing for one unique value**: one is refused.
- **J03.9 An initial relationship to a record the model does not let be chosen** (0.9 K7) is refused
  with `422 RELATION_CANDIDATE_REFUSED`, and the record is not created.

**Refusals:** `422 PARENT_REQUIRED`, `422 INVALID_PARENT_TYPE`, `422 PARENT_WRONG_SCOPE`,
`422 MISSING_REQUIRED_ATTRIBUTES`, `422 MISSING_REQUIRED_RELATIONS`,
`422 INVALID_OBJECT_TYPE_FOR_APPLICATION` (live; `OBJECT_TYPE_NOT_IN_APPLICATION` in a change set),
`404 UNKNOWN_APPLICATION`, `409 DUPLICATE_ATTRIBUTE_VALUE`, `409 DUPLICATE_RELATION_SCOPE`,
`409 OBJECT_ALREADY_EXISTS`, `422 DUPLICATE_INITIAL_RELATION`, `409 CARDINALITY_VIOLATION`,
`404 WORKSPACE_NOT_FOUND`, `409 WORKSPACE_RETIRED`.

**Evidence today:** `wp9-authoring`; `test_api`, `test_translations`, `test_rule_parity`,
`test_pg3_concurrency`.

### J04 — Delete a record and what depends on it

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-D10, US-D11.
**Example scenario:** SC-04. **Status:** delivered.

1. Request deletion of a live record or a record in a change set.
2. Review the impact: descendants in its hierarchy, dependants it owns through required
   relationships, and the relationships that will be removed.
3. Cancel with no change, or confirm with the preview's token.
4. See the result and the audit outcome.

Containment cascades to descendants and ownership cascades to dependants; an association removes
only the relationship, and the record at its other end survives, in any application. Live deletion
is immediate; a change set's does not touch live data until publishing. Publications never change.

**Variants:**

- **J04.1 A record with nothing depending on it** is deleted without a preview.
- **J04.2 A deep subtree** with relationships at several levels, to records inside and outside it.
- **J04.3 An owner across applications**: its dependants in another application go with it.
- **J04.4 In a change set.**
- **J04.5 Something changed after the preview** (a value, a parent, a new descendant or
  relationship): the confirmation is refused and nothing is deleted.
- **J04.6 A dependant whose required relationship would be removed alone** is refused.

**Refusals:** `409 DELETION_PREVIEW_REQUIRED`, `409 DELETION_PREVIEW_CHANGED`,
`409 OBJECT_HAS_DEPENDANTS`, `409 VERSION_CONFLICT`, `422 REQUIRED_RELATION`.

**Evidence today:** `wp9-authoring`, `wp9-change-sets`, `ui03b-deletion`; `test_cascade_delete`,
`test_wp8_review_regressions`, `test_wp7_canonical_crud`.

### J13 — Relate records and maintain their relationships

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-D10, US-M02.
**Example scenario:** SC-03, SC-04, SC-07. **Status:** delivered.

1. Find the record to relate, through a candidate search in the workspace, in any application.
2. Create the relationship of an allowed type pair, with its declared typed attributes.
3. Change its attributes against its version.
4. Remove it, unless it is required.

The containment relationship is not edited here: it follows the record's parent (J14).

**Variants:**

- **J13.1 Across applications**, in both directions, read by its forward and reverse names.
- **J13.2 Each cardinality**: a one-to-one or one-to-many limit is refused when exceeded; many-to-many
  is not limited.
- **J13.3 Typed relationship attributes**: undeclared attributes and invalid values are refused.
- **J13.4 Scoped uniqueness**: a relationship that would make two related records share the scope
  ancestor is refused; it holds only while its condition attribute does.
- **J13.5 With a relationship-set claim**: an integrator that read a record's relationships of one
  type claims the set's version on create or delete; a set changed meanwhile is refused. The
  version is read from the record's relationship list (`GET /relations?objectId=…`), which names
  the version of every set the record anchors, including a set with no relationship (never had
  one, or all removed); a matrix or mapping view and the workspace edge list show it too.
- **J13.6 A required relationship** cannot be removed while its dependant needs it.
- **J13.7 In a change set.**
- **J13.8 Two relationships racing for one cardinality limit**: one is refused.
- **J13.9 Only the records a relationship may choose** (0.9 K7, D168–D177): the model limits a
  binding's ends by criteria over the records' fields and their ancestors' fields; the per-type list
  offers a record of the anchor's type only those (`candidateFor`, `anchorTypeKey`), live and in a
  change set; a new relationship to any other, alone, in a batch or as a set replacement's addition,
  is refused naming the end; a record the set already holds is kept.
- **J13.10 A relationship outlives its criteria** (D175): when the data changes so a related record
  no longer meets them, the relationship is kept, the change set publishes, and the record is no
  longer offered.

**Refusals:** `422 UNKNOWN_RELATION_TYPE`, `422 INVALID_RELATION_PAIR`, `422 RELATION_ENDPOINT_MISSING`,
`422 RELATION_WRONG_SCOPE`, `422 UNKNOWN_RELATION_ATTRIBUTES`, `422 IMMUTABLE_RELATION`,
`409 CARDINALITY_VIOLATION`, `409 DUPLICATE_RELATION_SCOPE`, `409 RELATION_SET_VERSION_CONFLICT`,
`422 RELATION_SET_CLAIM_INCOMPLETE`, `422 REQUIRED_RELATION`, `409 VERSION_CONFLICT`,
`409 DUPLICATE_RELATION`, `404 RELATION_NOT_FOUND`, `422 RELATION_CANDIDATE_REFUSED` (0.9 K7).

**Evidence today:** `test_relations`, `test_relation_set_versions`, `test_rule_parity`,
`test_translations`, `test_pg3_concurrency`.

### J14 — Build and change a hierarchy

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-H01, US-H02, US-D09.
**Example scenario:** SC-09. **Status:** delivered (0.8 B).

1. Find a nested record without loading every branch: by parent, or by search with its path.
2. Add a child under it (J03).
3. Move a record to another permitted parent, chosen from its parent candidates, or to the top.
4. See the new path; the moved record's descendants and relationships go with it; unrelated
   branches are untouched.

**Variants:**

- **J14.1 A self-hierarchy of any depth**, and **J14.2 a hierarchy of mixed types**, where a type
  has parents of several types.
- **J14.3 To the top level**, for a type that may stand there.
- **J14.4 Into its own subtree** is refused (a cycle).
- **J14.5 A move that changes a scope ancestor**: relationships of the moved subtree that are unique
  within an ancestor are re-checked; a move that would make two share it is refused.
- **J14.6 A move that changes which records relate across applications**: relationships of the
  moved records, from inside and outside the subtree, stay and are read in the new place.
- **J14.7 In a change set**, with the moved subtree's paths, candidates and relationships following.
- **J14.8 Two moves racing into a cycle**: one is refused.
- **J14.9 Move several records at once** (UI, Base 0.9 UA9): in the sidebar's tree or a tree lens,
  records selected with Cmd/Ctrl and Shift (or Ctrl+Space and Shift+arrows) are dragged together
  onto a new parent, or moved with Move to…, live or in a change set; one confirmation and one
  all-or-nothing batch, each record claiming its version. A target that cannot take one refuses
  them all and names it; several records whose type a target would change are refused (one at a
  time). Selecting opens nothing on the page.

**Refusals:** `422 PARENT_CYCLE`, `422 INVALID_PARENT_TYPE`, `422 PARENT_WRONG_SCOPE`,
`409 DUPLICATE_RELATION_SCOPE`, `409 VERSION_CONFLICT`.

**Evidence today:** `b3-tree-lens`, `b4-hierarchy-acceptance`, `s6-sidebar-tree`, `ua9-tree-selection`,
`ui03b-hierarchy`; `Explorer.test`, `TreeView.test`; `test_parent_candidates`, `test_pg3_concurrency`.

### J15 — Reshape a hierarchy across types, and change a record back

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-H03, US-H02.
**Example scenario:** SC-17. **Status:** delivered (0.8 C).

1. In a change set, choose an operation: a move where the record's type must change, inserting a
   level, removing a level, or changing the type of every record of a type under a parent.
2. Preview the plan: each record's new type, the values it takes and from where, the values and
   relationships its new type has no place for (kept in history), and the values still needed.
3. Answer the plan's questions once per type pair or per record.
4. Apply the previewed plan; review and publish the change set.

Records keep their IDs and history; nothing is written before apply.

**Variants:**

- **J15.1 Change a record back**: the preview offers back the values and relationships kept in
  history.
- **J15.2 A cascade over several levels.**
- **J15.3 A relationship the new type cannot have**, to a record of another application, is kept in
  history and offered back.
- **J15.4 The data changed after the preview**: apply is refused.
- **J15.5 Too large a subtree** is refused with the limit.

**Refusals:** `422 RESTRUCTURING_NOT_READY`, `422 RESTRUCTURING_TOO_LARGE`,
`409 RESTRUCTURING_PLAN_CHANGED`, `422 INVALID_TYPE_MAPPING`, `422 OBJECT_TYPE_UNCHANGED`,
`409 OBJECT_TYPE_CHANGED`, `422 TYPE_CHANGES_NEED_CHANGE_SET`; a single record's type change is
refused with `422 CHILD_TYPE_NOT_ALLOWED` or `422 REQUIRED_RELATION_WITHOUT_PLACE`, which a
restructuring preview reports instead as problems of its plan, in its `200` answer.

**Evidence today:** `c4-restructuring`, `c5-restructuring-acceptance`; `test_restructuring_api`,
`test_restructuring_planner`, `test_type_changes`.

### J32 — Change many records of a collection at once

**Actor:** steward. **Channel:** UI (its API side is J11 and J24). **Stories:** Track K (0.9).
**Status:** delivered: selection (0.9 K1), value changes (0.9 K2), deletion (0.9 K2b),
relationship changes (0.9 K3); relation columns showing the result in the list (0.9 K5, J01.8).

1. In a collection whose data can be written, select records: by hand, by a range, the loaded rows,
   or every record the search, filters and scope match.
2. Read what is selected in the bar above the table.
3. Apply a change to the selection (K2, K2b, K3) and read each record's outcome.

Selection is offered where the data can be written and the deployment lets jobs be created, since
every bulk change is a batch job; it is never offered in a publication. A selection belongs to the
list it was made over: sorting, scrolling and opening records keep it, a new search, filter, scope
or data context clears it, and a reload clears it. Records picked by hand carry the version their
row showed; "all matching" reads its records and their versions when the change runs.

**Variants:**

- **J32.1 Select records** (0.9 K1): by checkbox, Space and Shift for a range over the loaded rows;
  the header checkbox for the loaded rows; **Select all N matching** once they are all selected;
  Cmd+A (Ctrl+A) in the table for all matching; a row unchecked under all matching kept as an
  exception; a selection over `backgroundJobMaxItems` refused and explained (how many match, the
  limit, its setting, what to do); kept and cleared as above; absent in a publication or with jobs
  switched off.

- **J32.2 Change values of a selection** (0.9 K2): Change values… sets or clears one or more
  fields (not read-only or hidden ones; a required one is never cleared), all or nothing or the
  records that can change; all matching is read first, with progress and Stop; the preview says how
  many will change, are already as asked and will be refused, naming each refused record; Apply
  follows the job to its result, each refused record openable; the selection is kept with the
  versions the change left, and Preview again repeats the change for what it did not change; a
  stale change set, a request over `BATCH_BACKGROUND_MAX_BYTES` and a model activated meanwhile are
  explained. Leaving the dialog before Apply (Back, Cancel, ✕, Escape, a click outside, opening a
  record) cancels the preview; View job keeps it waiting. A batch's job page lists its items'
  outcomes and applies or cancels a waiting preview.

- **J32.3 Delete a selection** (0.9 K2b): Delete… deletes each selected record with the records
  inside it and those it owns, removing its relationships, all or nothing or the records that can be
  deleted; the preview says how many selected records are deleted, how many records go with them by
  type, how many relationships are removed and how many of those reach records that stay, and which
  selected records go with another; Delete N records (the whole) applies exactly what was previewed,
  refusing a record whose impact changed since and naming it; the deleted records leave the
  selection, the refused ones stay for Preview again, and all matching is cleared. In a change set
  any write between the preview and Apply refuses Apply whole, as for a value change. A batch's job
  page shows what deleting removes and each delete's impact.

- **J32.4 Change the relationships of a selection** (0.9 K3): Change relationships… offers every
  relationship the model allows the type, in both directions, except containment and
  required-ownership ones; by its cardinality, Add and Remove records (together), Replace with, Set
  to one record, or Clear; a required relationship is never removed or cleared. The other records
  are chosen with the record picker. The dialog states how many changes the selection makes and
  explains a change over the deployment's limits (Replace with, Set to and Clear over the preview
  limit too) before sending; the preview says how many relationships are added, removed and already
  as asked and names each refused record; Apply refuses a record whose relationships of that kind
  changed since the preview. The selection is kept, and Preview again repeats the change. A batch's
  job page says each relationship outcome in words.
- **J32.5 Set one value on the selected records** (0.9 K3a): where each selected record may hold
  only one related record of a kind (`many-to-one` from its side, `one-to-many` to it), Change
  relationships… offers Set to and Clear. On one record, the Relationships panel offers Set when the
  record holds none of that kind and Change and Remove when it holds one, never an Add the write
  would refuse (D139).
- **J32.6 Change every record a relationship filter matches** (0.9 K6): under a relationship filter,
  Select all N matching and a bulk change preview and apply exactly the filtered records.
- **J32.7 See what a selection holds before removing it** (0.9 K6a, D165): for a set of records and
  one relationship, the records at the other end with how many of the set hold each
  (`GET /relations/held`), in name order, paged, in any context; Change relationships' Remove lists
  only those.

**Evidence today:** the browser runners `k1-selection`, `k2-bulk-change`, `k2b-bulk-delete` and
`k3-bulk-relations`; `recordSelection.test`, `ObjectTable.test`, `CollectionView.test`,
`SelectionBar.test`, `bulkChange.test`, `bulkDelete.test`, `bulkRelations.test`,
`BulkChangeDialog.test`, `BulkDeleteDialog.test`, `BulkRelationDialog.test`, `RecordListField.test`,
`JobPage.test`.

## Relationship sets and coverage

### J10 — Review and replace a record's related records

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-M01–M04.
**Example scenario:** SC-07, SC-16. **Status:** delivered (0.7; several records per save through the API, 0.9 B3).

1. List the source records of a relationship view with their related records, filtered to those with
   none, one or several, before paging.
2. Search the server for the records a source may relate to (beyond page one).
3. Choose the one record the source relates to instead, or none where empty is allowed.
4. Save once, against the set's version: the chosen record replaces every record the source related
   to through that relationship.

Replacement is never a visible delete followed by a create. A chosen record the source already
related to keeps its relationship identity and attributes. The relationship view saves one chosen
record; an integrator replaces a set by several records in one write, a batch's `replaceRelationSet`
item (J10.10), through the same replacement.

**Variants:**

- **J10.1 Both directions**, and **J10.2 across applications**, with the relationship's own names.
- **J10.3 A large set**: bounded previews of the related records with exact counts and continuation.
- **J10.4 Someone changed the set first**: the save is refused with the current set; the attempted
  choice is kept for review.
- **J10.5 A single relationship write racing a set replacement** on the same records: one is
  refused, never a deadlock.
- **J10.6 In a change set, with live changing the same set before publishing**: publishing is refused.
- **J10.7 In a publication**: read-only.
- **J10.8 Create a missing related record in place**; cancelling leaves the set intact.
- **J10.9 A required or owning relationship** cannot be cleared or moved to another owner, and a
  replacement cannot take away the last such relationship of a record that requires one.
- **J10.10 Replace a set by several records** (API): the set becomes the listed records, each kept
  record keeping its relationship and values unless new values are given, under the set's version
  (or a declared overwrite); a set already equal answers unchanged; the cardinality, scope,
  required and containment rules refuse it with the single writes' codes.
- **J10.11 Only the candidates a relationship allows** (0.9 K7): a relationship view's candidates and
  a relation matrix's link candidates list only the records the binding's `candidates` let be chosen.

**Refusals:** `409 MAPPING_VERSION_CONFLICT`, `422 INVALID_CLEAR_ATTRIBUTES`,
`422 REQUIRED_OWNERSHIP_BINDING`, `422 RELATION_ANCESTOR_REQUIRED`, `422 REQUIRED_RELATION`,
`409 CARDINALITY_VIOLATION`, `409 DUPLICATE_RELATION_SCOPE`; publishing a change set whose set live
changed meanwhile is `409 VERSION_CONFLICT` with a `MAPPING_SET_CHANGED` conflict; `422 INVALID_CURSOR`, and the view and binding refusals (`mapping_view_*`, `mapping_*`). Through a batch
(J10.10): `409 RELATION_SET_VERSION_CONFLICT`, `409 VERSION_REQUIRED`, `409 DUPLICATE_RELATION`,
`422 IMMUTABLE_RELATION`, `422 REFERENCE_TYPE_MISMATCH`.

**Evidence today:** the J10 journey tests; `sc07-mapping-acceptance`, `wp14-contextual-browser`,
`wp13c-ui-states`; `test_mapping_coverage`, `test_mapping_replacement`, `test_pg3_concurrency`.

### J16 — See and fill relationship coverage across ancestors

**Actor:** steward; integrator. **Channel:** UI, API. **Stories:** US-L03, US-L04.
**Example scenario:** SC-09. **Status:** delivered (0.8 A).

1. Open a model-declared matrix: rows of records, columns of an ancestor of the records they relate
   to, and in each cell the related records under that column.
2. Filter rows by cell state (filled, missing, …) before paging, with totals.
3. From an empty cell, create the related record in a container under that column, or relate an
   existing candidate.
4. Edit or remove a relationship from a filled cell.

The state filter decides over every row, and only records counting as current fill a cell.

**Variants:**

- **J16.1 Each binding shape**: an owned dependant, an optional association, and a many-to-many
  relationship read in its reverse direction.
- **J16.2 Columns several levels above the related record** in its hierarchy.
- **J16.3 In a change set**, published afterwards; **J16.4 in a publication**, read-only.
- **J16.5 A cell filled live after it was staged** is refused at publishing.
- **J16.6 Two relationships racing into one cell** keep its stored state right.
- **J16.7 A related record moved to another column** is re-checked.

**Refusals:** `404 RELATION_MATRIX_VIEW_NOT_FOUND`, `404 RELATION_MATRIX_ROW_NOT_FOUND`,
`404 RELATION_MATRIX_COLUMN_NOT_FOUND`, `404 RELATION_MATRIX_PARENT_NOT_FOUND`,
`422 RELATION_MATRIX_ACTION_NOT_ALLOWED`, `422 RELATION_MATRIX_PARENT_SCOPE_MISMATCH`,
`422 RELATION_MATRIX_STATE_REQUIRES_COLUMNS`, `422 TOO_MANY_COLUMNS`, `422 DUPLICATE_COLUMN_IDS`,
`422 CONFLICTING_COLUMN_PARAMETERS`.

**Evidence today:** `a4-relation-matrix`, `a5-matrix-acceptance`; `test_relation_matrix`,
`test_relation_matrix_writes`, `test_matrix_states`, `test_relation_matrix_volume`.

### J09 — Retired

Was "Maintain a translation" until 2026-10-02. A translation is the example model's configuration
of generic rules, now walked by J03 (a dependent record created with its required relationship,
scoped uniqueness at creation), J13 (scoped uniqueness, required relationships) and J02 (at least
one of a set). The ID is not reused.

## Change sets and history

### J05 — Prepare and publish a coordinated design

**Actor:** designer; integrator. **Channel:** UI, API. **Stories:** US-W01–W04, US-W08.
**Scenario:** SC-05, SC-06. **Status:** delivered.

1. Create a change set from a clearly labelled source: current live data, or a publication.
2. Name it and make changes with the normal record operations (J02–J04, J13–J15).
3. Validate the complete candidate.
4. Publish once.
5. Open the new immutable publication and its lineage.

Live readers see nothing staged before publishing and the complete merged result afterwards. A
conflict or an invalid graph publishes nothing and keeps the change set.

**Variants:**

- **J05.1 From current live data**, including unpublished live work, frozen at the moment the
  change set starts. Typed values and their filters survive capture and publication; staged
  value edits, parent moves and added relationships read identically live and in the publication
  at its feed position.
- **J05.2 From a publication**; **J05.3 empty** (bootstrap support).
- **J05.4 An invalid graph**: validation answers `valid: false` and names the records; publishing
  re-checks the merged result.
- **J05.5 Rename or discard** the change set; discarding never needs model agreement.
- **J05.6 Two writers in one change set**: the change set version refuses the stale one.
- **J05.7 A write committing while current live is captured**: the capture asks for a retry.

**Refusals:** `409 CHANGE_SET_VERSION_CONFLICT`, `409 CHANGE_SET_REQUIRED`,
`409 CHANGE_SET_SNAPSHOT_RETRY`, `422 WORKSPACE_GRAPH_INVALID`, `409 VERSION_CONFLICT` (a record
changed live since the change set's source, listed in `details.conflicts`),
`409 WORKSPACE_ACTIVE_PUBLICATION_CONFLICT`, `409 MODEL_RELEASE_CHANGED`,
`404 CHANGE_SET_NOT_FOUND`, `409 WORKSPACE_RETIRED`.

**Evidence today:** `wp9-change-sets`; `test_wp8_publish`, `test_wp8_graph_validation`,
`test_wp8_change_set_lifecycle`, `test_wp81b_current_live_bases`, `test_change_sets`.

### J06 — Continue live work while a change set is open

**Actor:** steward and designer. **Channel:** UI, API. **Stories:** US-W04, US-W08.
**Scenario:** SC-06. **Status:** delivered.

1. A change set starts from a frozen copy of current live content.
2. Routine live edits continue without the change set.
3. The design team edits other records in the change set.
4. Publishing applies only the change set's changes; untouched live edits survive.

If both changed the same record, publishing stops with a record-specific conflict; it never
overwrites the live edit or deletes live-only records.

**Variants:**

- **J06.1 A live addition while the change set is open** survives publishing.
- **J06.2 The same record changed on both sides** is refused, naming it.
- **J06.3 Publishing beside live writes and other change sets' writes**: publishing waits for live
  writes of its workspace and leaves other change sets free.
- **J06.4 Publishing an exchange of unique values**: a change set that hands unique values between
  records publishes; live holds each value once.

**Refusals:** `409 VERSION_CONFLICT`, naming each record changed on both sides in `details.conflicts`.

**Evidence today:** `wp9-change-sets`; `test_wp8_publish_merge`, `test_wp81b_current_live_bases`,
`test_pg3_concurrency`.

### J07 — Withdraw a publication and start reviewed changes from history

**Actor:** designer; integrator. **Channel:** UI, API. **Stories:** US-W05–W07, US-D12.
**Scenario:** SC-08. **Status:** delivered.

1. Open the workspace's publication history and read an older snapshot exactly as published.
2. Withdraw the current publication: no publication is current; live data and history stay readable.
3. Create a change set from an earlier publication.
4. Prepare, validate and publish it. Choosing an older base alone undoes nothing; newer untouched live
   records are preserved.

**Variants:**

- **J07.1 Read a publication** through every read route, unchanged by later live writes or
  activations.
- **J07.2 Publish from a retained publication after withdrawal.**

**Refusals:** `409 WORKSPACE_ACTIVE_PUBLICATION_CONFLICT`, `404 PUBLICATION_NOT_FOUND`,
`409 WORKSPACE_RETIRED`.

**Evidence today:** `wp9-publications`; `test_wp8_history`, `test_wp8_withdrawal`.

### J17 — Review what a change set changes

**Actor:** designer or reviewer; integrator. **Channel:** UI, API. **Stories:** US-W02, US-D12.
**Scenario:** SC-06, SC-17. **Status:** delivered (0.8 P2).

1. Open a change set's object changes and relationship changes.
2. Filter by kind (added, changed, removed, moved, type changed) and type; page through them.
3. See each change's before and after, and where a moved record was.

The lists agree with what publishing would do to live data.

**Variants:**

- **J17.1 A change set from a publication** reads "before" from that publication.
- **J17.2 An empty root change set** lists only additions.
- **J17.3 A page and its paths** read one snapshot while a write commits.

**Refusals:** `404 CHANGE_SET_NOT_FOUND`, `422 UNKNOWN_OBJECT_TYPE`, `422 UNKNOWN_RELATION_TYPE`,
`422 INVALID_CURSOR`.

**Evidence today:** `p2-change-review`; `test_change_lists`, `test_change_lists_volume`.

### J18 — Prepare under the next model version while live keeps the current one

**Actor:** designer; model administrator. **Channel:** UI, API. **Stories:** US-W09, US-P03.
**Scenario:** SC-15. **Status:** delivered (0.7).

1. A candidate model release is installed but not activated.
2. Create a change set pinned to the candidate; it reads and writes with the candidate's fields,
   rules and views. Live data, history and other change sets keep the active release.
3. Activate the candidate (J08); the pinned change set then publishes normally.
4. For a change set still on the old release: discard it, or move it onto the new release when its
   content already fits.

**Variants:**

- **J18.1 An incompatible candidate** is refused at creation and at version change, naming records.
- **J18.2 Publishing a change set whose release is no longer active** is refused with an explanation.
- **J18.3 An unavailable, corrupt or unsupported release** is refused; nothing else changes.
- **J18.4 A pin changed by someone else** meanwhile is refused.

**Refusals:** `409 CHANGE_SET_CONTENT_INCOMPATIBLE`, `409 CHANGE_SET_MODEL_RELEASE_CONFLICT`,
`409 MODEL_RELEASE_CHANGED`, `409 CHANGE_SET_VERSION_CONFLICT` (J18.4), and for J18.3
`409 PINNED_MODEL_UNAVAILABLE`, `409 PINNED_MODEL_INVALID`, `409 UNSUPPORTED_PINNED_MODEL_SCHEMA`.

**Evidence today:** `sc15-model-version-acceptance`, `wp11-model-admin`; `test_build07_wp6`,
`test_build07_wp9_acceptance`, `test_wp81a_context`.

## Administration

### J08 — Create and activate an application-model release

**Actor:** model administrator; model author. **Channel:** UI (Settings › Model), API (model
administration enabled).
**Stories:** US-P01–P04, US-P06, US-P08, US-O02. **Scenario:** SC-12. **Status:** delivered.

1. Inspect the active and installed releases.
2. Create or import an editable draft; save and validate it.
3. Review its compiled identity, semantic differences and stored-data compatibility.
4. Install it as an immutable inactive release.
5. Activate it with the fresh runtime-state version.

Saving is not installing; installing is not activating. A compatibility or concurrency failure
selects nothing. Read-only inspection and export stay available when administration is disabled.

**Variants:**

- **J08.1 Validate a model without saving it** (inline validation).
- **J08.2 Compare two installed releases** (diff), including consumer contracts.
- **J08.3 Reactivate an older compatible release.**
- **J08.4 Data incompatible with the candidate** blocks activation, naming the data.
- **J08.5 Two activations from the same runtime state**: one succeeds.
- **J08.6 Activation beside live writes**: a write resolved under the old release and committing
  after activation is refused; activation does not wait for the workspace lock.
- **J08.7 Export a release** (with its model) to reuse elsewhere.
- **J08.8 Read the activation history** of a release.
- **J08.9 Read a model draft's history** (planned, decided D-5): the draft's operation history
  (0.10 A2, ADR-041), every step with its kind, parameters, inverse and time.
- **J08.10 A release dropping and restoring `unique`**: records may share a value while the
  attribute is not unique; restoring it is refused while they do, and holds the value once active.
- **J08.11 A binding tightened to many-to-one** (0.9 K3a): a release that makes a binding
  `many-to-one` needs a migration while a record at its `from` end holds more than one such
  relationship, counted at the binding's `cardinality`; activation is refused until the data fits.
- **J08.12 A relation column where the model allows it** (0.9 K5): `related:<key>` validates in a
  table view's columns and a children or table panel's, and in a table view's sort fields where a
  row holds at most one; anywhere else, with an unknown key, a key the listed type is at neither end
  of, or below schema 0.9, it is refused at its pointer. Since 0.9 K5a the same holds for
  `related:<key>.<field>`, refused too with a field the related records do not have and in sort
  fields. Since 0.9 K6 `filterFields` takes `related:<key>`, never the field form.

**Refusals:** `422 INVALID_MODEL` (with the JSON pointer), `409 RELEASE_IDENTITY_CONFLICT`,
`409 MODEL_MIGRATION_REQUIRED`, `409 ACTIVATION_CONFLICT` (stale runtime state),
`409 CONSUMER_CONTRACT_VERSION_REQUIRED`, `422 UNSUPPORTED_SCHEMA_VERSION`,
`404 MODEL_DRAFT_NOT_FOUND`, `503 MODEL_REGISTRY_REFRESH_FAILED`; with administration disabled the
mutating routes are absent.

**Evidence today:** `wp11-model-admin`, `wp12-release-identity`, `wp9-authoring`;
`test_model_lifecycle`, `test_model_compatibility`, `test_build07_wp11`, `test_w5_activation_write_race`,
`test_model`, `test_model_diagnostics`.

### J19 — Administer workspaces

**Actor:** workspace administrator; integrator. **Channel:** UI (Settings › Workspaces), API.
**Stories:** US-A01–A03,
US-I01. **Scenario:** SC-14, SC-08. **Status:** delivered (0.8 W).

1. Create a workspace with a stable key and a label; change its label later.
2. Choose the default workspace; requests without a workspace use it, explicit ones never change.
3. Retire a workspace that is not the default: it stays readable and refuses every change.
4. Delete an empty workspace that was never published.

**Variants:**

- **J19.1 Two administrators change the default from the same version**: one is refused.
- **J19.2 Retirement beside a live write or a change set write**: retirement waits for the write;
  a later write is refused.
- **J19.3 Search and page the catalogue.**
- **J19.4 Administration disabled**: the catalogue stays readable and the change-set workflow works.
- **J19.5 Read the workspace's activity** (planned, decided D-5): change sets created, renamed and
  discarded, publications published and withdrawn, the default switched, with who and when.

**Refusals:** `409 WORKSPACE_ALREADY_EXISTS`, `409 VERSION_CONFLICT`, `409 WORKSPACE_RETIRED`,
`409 DEFAULT_WORKSPACE_CANNOT_BE_RETIRED`, `404 WORKSPACE_NOT_FOUND`, and for deletion `409 WORKSPACE_IS_DEFAULT`,
`409 WORKSPACE_HAS_PUBLICATIONS`, `409 WORKSPACE_NOT_EMPTY`.

**Evidence today:** `w4-workspace-admin`; `test_workspaces`, `test_w6_workspace_deletion`,
`test_pg3_concurrency`.

### J25 — Define a consumer API in the model

**Actor:** model author. **Channel:** API (model documents), UI (model administration; a declared
definition is read on Settings › Integration › Consumer APIs, 0.9 U4).
**Stories:** US-I09 (consumer side), US-P04. **Status:** definitions delivered (0.9 C1); the
consumer tier's reads in C2–C16 ([CONSUMER_API.md](../CONSUMER_API.md)); event declarations in C9,
their events produced from C10 (J30); written in schema 0.9 since C18.

1. Declare a consumer API in the model (schema 0.9): the exposed types and their public names, the
   operations it offers, the object's fields with their sources and roles, related records, how
   XREF matches, its filters, lists and events, and a contract version.
2. Validate and compile it with the release; every reference is checked at its JSON pointer.
3. Compare with the active release: breaking changes need a higher contract version.
4. Activate; a break without a higher version is refused.

**Variants:**

- **J25.1 Additions are compatible**; removals and lower versions are reported.
- **J25.2 A model change** (a cardinality) changes a projection's shape and is reported.
- **J25.3 Declare events**: a definition names its change events (`operations.events`): one per
  exposed type with `perType`, or its own under `custom` with the exposed types, the kinds of change
  (`created`, `updated`, `deleted`) and, for an update, the outputs and related blocks it watches,
  by the names consumers read. Each mistake is refused at its pointer under
  `/consumerApis/<key>/operations/events/custom/<index>`; `event` and `after` are reserved filter
  names (C9).
- **J25.4 Events in the contract**: a release that tells consumers less (an event, a type, a change
  kind or a watched output removed, a watch added) needs a higher contract version; one that tells
  them more is compatible (C-D85).
- **J25.5 Rewriting a definition changes nothing it serves**: a workspace active on a model whose
  definitions are in schema 0.8 installs and activates the same definitions rewritten in 0.9. No
  consumer contract change is reported and no subscription is suspended; get by ID, a list with a
  parent and filters, XREF (a page, `expect=one`, a crosswalk), batch resolve, the pull feed and the
  API index answer the same bodies and headers apart from the `ETag` values, and the definition's
  OpenAPI document is the same apart from the release it names (C18).
- **J25.6 Schema 0.8 refused for new definitions**: installing, compiling or validating a schema 0.8
  document that declares `consumerApis` is refused at `/schemaVersion`, naming schema 0.9; a 0.8
  document without them installs, and a stored 0.8 release stays readable (C-D134).
- **J25.7 Operations a definition offers**: an operation the definition does not list answers
  `404 OPERATION_NOT_OFFERED` and is left out of its OpenAPI document; no longer offering one needs
  a higher contract version, offering one more is compatible; `resolve` without `xref` is refused at
  `/consumerApis/<key>/operations/resolve` (C-D132).
- **J25.8 Mistakes at the author's pointers**: a `via` naming no relation, a filter with two verbs,
  a role given to two fields and an `alsoMatchThrough` naming no related block are each
  refused at their pointer in the 0.9 document (C-D141).

The identity (the field with role `id`) reads the object ID, and any other source is refused at
`/consumerApis/<key>/object/fields/<field>/from` (C-D24). Another identifier, such as a former
system's ID, is published as a field of its own.

A list may name a `sortBy` attribute: a scalar attribute its type binds, refused otherwise at
`/consumerApis/<key>/operations/lists/<list>/sortBy`; changing it is a breaking change. `from`,
`seek` and `includeTotal` are reserved filter names, as the other paging names are (C3).

**Refusals:** `422 INVALID_MODEL` (with the pointer), `422 UNSUPPORTED_SCHEMA_VERSION` (a 0.8
document with `consumerApis`), `409 CONSUMER_CONTRACT_VERSION_REQUIRED`.

**Evidence today:** `test_consumer_api_model`; the J25 journey tests.

## Model authoring

Product 0.10 ([plan](../BASE_0_10_IMPLEMENTATION_PLAN.md),
[MODEL_AUTHORING](../MODEL_AUTHORING.md)). One editor over a model draft. Every change is an operation
the API accepts from any client ([API.md § Model authoring](../API.md#model-authoring-product-010-designed));
the browser editor is one client. The model lifecycle of J08 is unchanged: a draft, an immutable
release, an activation. Data from a workbook arrives through J27's import, in a change set reviewed
by J17. Each journey runs on two models that differ in keys and shape: the example model with every
key renamed, and the generated model B (D20); the workbook journeys on the synthetic workbooks W1
and W2.

### J33 — Design a model in the editor

**Actor:** model administrator. **Channel:** UI (Settings › Model › Open in editor), API.
**Stories:** US-P05 (additive and draft-only operations). **Scenario:** SC-12.
**Status:** planned: navigation groups N1, operations A2, editor A4a and A4b.

1. Open a draft of the active release, or an empty one, in the editor.
2. Change the model by operations: applications, object types in their containment tree, attributes,
   relation types and the relations allowed between types, navigation groups, views and panels.
3. Read the issues after each step and the history of every step; undo and redo.
4. Install and activate in one confirmed step, with the release version, the differences and the
   compatibility result shown.
5. Work with records of the new or changed types.

Keys are free to change until an element is released (in the draft's base release); after that only
its labels change, and a change that needs a migration is refused with its impact. A draft may be
invalid between steps; installation refuses an invalid draft as J08 does.

**Variants:**

- **J33.1 From an empty draft**: an application with types, attributes, a relation and a group, built
  by operations alone, installs, activates and holds records.
- **J33.2 Extend the active model**: types and attributes added beside released ones; the released
  ones marked as released.
- **J33.3 Generated layout**: a new type gets a table view and a detail page from the server; an
  attribute attached or a relation allowed appears in them.
- **J33.4 Undo and redo** a step; a new step clears what can be redone.
- **J33.5 An undo with dependants** is refused naming them; undoing them together succeeds.
- **J33.6 A stale editor**: a step at an old version is refused with the steps applied since.
- **J33.7 A released element**: a key change, a removal or a split of a released element is refused
  `OPERATION_REQUIRES_MIGRATION` with its impact; nothing of the request applies.
- **J33.8 A request that cannot apply** (an unknown element, a key taken) applies nothing.
- **J33.9 Group collections**: groups declared on an application show as sidebar sections and a
  group page with a search; collections in no group keep their place (N1).
- **J33.10 Lay out a type** in the preview: panels ordered, shown or hidden; a table view's columns,
  filters and sort; field order. The record screen shows the same layout after activation (A4b).
- **J33.11 Keyboard alone and 390px**: every drag has its Move to… path; the panes become tabs.
- **J33.12 A whole-model edit** in the JSON workbench is recorded as one step, and operations continue
  on the edited model.

**Refusals:** `422 INVALID_OPERATION`, `409 OPERATION_REQUIRES_MIGRATION`,
`409 OPERATION_HAS_DEPENDANTS`, `409 NOTHING_TO_UNDO`, `409 NOTHING_TO_REDO`, `409 VERSION_CONFLICT`,
`413 OPERATION_BATCH_TOO_LARGE`, `404 MODEL_DRAFT_NOT_FOUND`; J08's refusals at installation and
activation; with administration disabled the routes are absent.

**Evidence today:** none (planned).

### J34 — Onboard a workbook

**Actor:** model administrator. **Channel:** UI (the editor with a workbook), API.
**Stories:** US-P09. **Scenario:** SC-12. **Status:** planned: profiling A3, editor with a source
file A5, inference A6; model-description sheets A7 and sheets laid out for reading A8 (below the
cut line).

1. Upload a workbook to a new or open draft; read its sheets, blocks and column statistics.
2. Accept, change or reject the proposed model and mapping, or map by hand.
3. After every step read the dry-run summary and the rows behind each figure.
4. Install and activate; load the workbook through an import job into a new change set.
5. Review the change set (J17) and publish it.

**Variants:**

- **J34.1 Upload and profile**: header rows, blocks and per-column statistics, paged.
- **J34.2 Map by hand**: columns to attributes, parents, relations, related records; values mapped;
  a column ignored.
- **J34.3 The dry run follows the editing**: after a rename, a move or a value map, the summary and
  its difference from the last one; a sample above the row limit, the full run on request.
- **J34.4 Proposals**: each table pattern proposed with its evidence; accepted, changed or rejected;
  nothing applied unasked.
- **J34.5 Extend the active model**: columns matched to existing types and attributes, not duplicated.
- **J34.6 Pinned decisions**: re-inference after edits reports disagreements and changes nothing pinned.
- **J34.7 The profile follows the model**: a rename, move, split or merge after mapping keeps the
  draft's profile valid.
- **J34.8 Load into a change set**, review it and publish it.
- **J34.9 A model-description workbook** (A7) and **J34.10 a sheet of lists laid out for reading**
  (A8).

**Refusals:** `413 IMPORT_TOO_LARGE`, `422 UNSUPPORTED_FILE_FORMAT`, `404 SOURCE_FILE_NOT_FOUND`,
`409 SOURCE_FILE_PROFILE_NOT_READY`; J33's refusals for operations; J27's for the import.

**Evidence today:** none (planned).

### J35 — Load the next version of a workbook

**Actor:** model administrator; data steward. **Channel:** UI, API. **Stories:** US-P10.
**Status:** planned (A5).

1. Upload the next version of a workbook to its saved profile.
2. Read what differs before loading: new, missing and renamed columns, new list values, name drift,
   records missing from the new version.
3. Load into a new change set and review only the differences.

**Variants:**

- **J35.1 Differences first**: nothing loads before the report is read.
- **J35.2 Missing records** are reported and kept; retired or deleted only when the profile says so,
  in the change set.
- **J35.3 A profile against a newer release**: re-checked, with every binding that no longer resolves
  at its path.

**Refusals:** J27's import refusals; `422 INVALID_IMPORT_PROFILE` with its problems.

**Evidence today:** none (planned).

## Integration

### J20 — Discover the model and the API

**Actor:** integrator. **Channel:** API; UI (Settings › Integration › Consumer APIs and API
reference, 0.9 U4). **Stories:** US-I01, US-P01. **Status:** delivered.

1. Read the capabilities: which groups are enabled and their limits.
2. Read the active model, or the model of a change set or publication, and its placements (where
   each type may stand).
3. Page the model's applications, attribute types, object types, relation types and allowed type
   pairs, or read one by key.
4. Read the API reference (`/docs`) and the OpenAPI document; find the consumer APIs in their index
   and read each one's own OpenAPI document (J20.3, J20.4), also as a source of the reference page
   (J20.5).

Every identifier is a stable public key or UUID; no internal sequence number is exposed. The model
read names the release it was read under (`X-Model-Release-Id`).

**Variants:**

- **J20.1 In a change set pinned to another release**: the model and metadata follow the pin.
- **J20.2 Releases**: list and read installed releases and the runtime state.
- **J20.3 The consumer API index**: `GET /api/consumer` lists the active release's consumer APIs,
  paged, each with its `consumerApi`, name, contract version and the URL of its OpenAPI document; a
  release adding or removing a definition shows in it.
- **J20.4 A consumer API's document**: `GET /api/consumer/{consumerApi}/v{contractVersion}/openapi.json`
  is the API's typed contract: valid OpenAPI 3.1, its paths written out with the name and version,
  one per list, its parameters, shapes, limits and refusals; a client generated from it reads the
  API's real answers. A release raising the version moves the document to the new version's URL.
- **J20.5 The consumer APIs on the reference page**: `/docs` shows the management API and, beside
  it, one source per consumer API of the active release, labelled `{name} · v{contractVersion}`
  and read from the document the index names. A release adding, removing or re-versioning a
  definition shows on the next page load.
- **J20.6 A consumer API definition expanded**: `GET /api/v1/model/consumer-apis/{consumerApi}`
  answers the context model's definition in schema 0.9 with every default written out: each public
  name, the operations, the events `perType` generates, every `matchOn` and each list's
  `within.types`; with the model's `ETag`. A schema 0.8 release's definitions read the same way
  (C18, C-D137).

**Refusals:** `404 CHANGE_SET_NOT_FOUND`, `404 CONSUMER_API_NOT_FOUND`, `422 MUTUALLY_EXCLUSIVE_CONTEXT`,
`503 MODEL_REGISTRY_UNAVAILABLE`, `503 MODEL_RUNTIME_STATE_UNAVAILABLE`.

**Evidence today:** `v1-api-reference` (with a consumer API source); `u4-integration` (the
Integration pages); `test_model_placements`, `test_request_scope`,
`test_api_reference`, `test_model_lifecycle`, `test_openapi_contract`.

### J21 — Read a collection completely and resume

**Actor:** integrator; steward (scrolling lists). **Channel:** API, UI. **Stories:** US-I02.
**Scenario:** SC-14 (integration half), SC-01. **Status:** delivered (0.8 S, ADR-030).

1. Request a bounded page of any collection.
2. Continue with the page's opaque cursor, forward or back, until the end.
3. Store a cursor and resume the same query later.

Every collection pages the same way; a page is never larger than its documented maximum, and no
collection relies on an undocumented unlimited page.

**Variants:**

- **J21.1 Jump to a position** (`position`) and **J21.2 start from the end** (`from=end`).
- **J21.3 Seek** to the first row at or after a value of the sort.
- **J21.4 Totals** on request (`includeTotal`), with the page's start index.
- **J21.5 Records inserted between pages** are neither repeated nor skipped.
- **J21.6 In a change set or publication**: the same paging, cursors bound to the context.
- **J21.7 A cursor reused** with another query, workspace, context or route is refused.
- **J21.8 An unknown query parameter** (a typo such as `pagesize`) is refused, naming it, on every
  route (decided D-3; delivered in H4c).
- **J21.9 Sorted by an attribute**: records with a value in value order, those without one last
  in both directions; every paging mode crosses between them.

**Refusals:** `422 INVALID_CURSOR`, `422 CONFLICTING_PAGE_PARAMETERS`, `422 INVALID_SEEK`,
`422 INVALID_SORT`, `422 UNKNOWN_PARAMETER` (J21.8).

**Evidence today:** `s5-continuous-lists`, `s7-volume-acceptance`; `test_paging_contract`,
`test_pagination`, `test_change_set_position_reads`, `test_query_foundations`.

### J22 — Request the precise dataset an integration needs

**Actor:** integrator. **Channel:** API. **Stories:** US-I09. **Status:** delivered (0.9 Q1–Q3).

1. Choose the type (or every type) and the context: live, a change set or a publication.
2. Combine criteria: field filters with typed values, an ancestor, one relationship hop (or its
   absence).
3. Choose a sort, the fields to return (`select`) and related records to include (`expand`).
4. Page through the result (J21).

**Variants:**

- **J22.1 The cross-type lookup** over every or chosen types, by name and built-in fields.
- **J22.2 The edge list**: every relationship of a workspace, any type, in any context
  (`/workspaces/{key}/relations`).
- **J22.3 Relationships of one record**, searched and sorted by the related records' fields.
- **J22.4 A model-declared field on the cross-type lookup** is refused with the per-type route.

**Refusals:** `422 INVALID_QUERY` (with the JSON pointer), `422 INVALID_FILTER`, `422 INVALID_SORT`,
`422 MUTUALLY_EXCLUSIVE_CONTEXT`.

**Evidence today:** `test_model_query`, `test_cross_type_lookup`, `test_workspace_edge_list`,
`test_typed_table_queries`, `test_search_index`; the composed journey `test_j24_j26_composed` (the
edge list beside a job, a change set and a publication, 0.9 T1).

### J23 — Answer a business-date question

**Actor:** integrator. **Channel:** API. **Stories:** US-I06. **Scenario:** SC-11.
**Status:** delivered on the management API (0.9 Q4, ADR-038) and the consumer API (0.9 C16).

1. Ask for a configured list's records applicable on a date (`asOf`).
2. Page through them; every page answers for that date.

The question is a date, not a time; only a model-declared effective period answers it. On the
consumer API the date dates the records a read returns, not their projections or ancestors, and each
answer names the types it dated.

**Variants:**

- **J23.1 The boundary day itself**, and **J23.2 overlapping periods.**
- **J23.3 In a change set or publication.**
- **J23.4 A period that does not end after it starts** is refused on every write.
- **J23.5 A model removing or adding a period.**
- **J23.6 A consumer list or object on a date**: page by page, live or pinned to a publication.
- **J23.7 A consumer lookup or batch across dated and undated types**: the dated types filtered,
  the others not, `asOfApplied` naming the dated ones.
- **J23.8 A consumer date refused**: not one calendar date, or on a read that does not take one.

**Refusals:** `422 AS_OF_NOT_SUPPORTED` (a type without a period, or the cross-type lookup),
`422 INVALID_EFFECTIVE_PERIOD` on writes; on the consumer API `400 AS_OF_NOT_SUPPORTED` (a list or
record of a type without a period, a lookup that can return no dated type) and `400 INVALID_AS_OF`.

**Evidence today:** `test_effective_periods`; the composed journey `test_j24_j26_composed` (dated
queries over a job's records in live data, a change set and a publication, 0.9 T1);
`test_j23_business_date` (J23.6–J23.8 on the consumer API) and the parity module's scenario 15
(0.9 C16).

### J11 — Submit a bounded bulk change

**Actor:** integrator. **Channel:** API. **Stories:** US-I03. **Scenario:** SC-10 (its batch part).
**Status:** delivered (0.9 B1; relationship items 0.9 B3; previews 0.9 K2; cascading deletes 0.9 K2b;
removal by ends and carried set claims 0.9 K3).

1. Send items (create, update, upsert, delete; create, ensure, update and delete a relationship, or
   ensure two records are not related;
   replace a record's relationship set) with a policy: `independent` or `atomic`.
2. Refer to records by ID or by a unique key, including records created earlier in the batch.
3. Read each item's outcome: applied, rejected with its single write's code, or unprocessed.
4. Retry safely with the same `Idempotency-Key`.

The rules are the single writes' rules, item by item; a batch is a first-class service, not a loop
over single calls.

**Variants:**

- **J11.1 Atomic**: everything or nothing.
- **J11.2 Upsert** by a unique key or an ID, with a version claim or a declared overwrite.
- **J11.3 In a change set**, claiming its version once.
- **J11.4 A model activated meanwhile** refuses the whole inline batch.
- **J11.5 A key reused with another request** is refused; a replay answers the original outcome.
- **J11.7 Relationship items**: relate records named by ID or unique key, ensure a relationship
  exists (unchanged when it already does with the same values), change its values against its
  version, remove it, and claim a relationship set's version on create or delete; each refused with
  its single write's code, live and in a change set.
- **J11.8 A record, its required relationship and its relationship set in one atomic batch**:
  everything applies, or a refusal leaves nothing.
- **J11.6 Delete with cascade** (0.9 K2b; decided D-6, PG-D18): a delete item with `cascade`
  removes a record with its dependants, as a single delete does, under a confirmation of its impact:
  a batch preview gives each item's impact and token and confirming carries them, or the item sends
  a token itself (the single delete's is the same); an impact changed since refuses that item and
  the rest are deleted (nothing under `atomic`); a record an earlier item of the job deleted answers
  `unchanged` naming that item; without `cascade` a record with dependants is refused with its
  impact; live and in a change set.
- **J11.9 Preview a batch, then apply it** (0.9 K2): a background batch sent with
  `stage: "preview"` runs its items without writing anything and waits with what applying would do
  (counts, the result under its policy, whether it covered every item, each item's outcome);
  confirming it applies the items to the data as it is then, so a record changed since is refused
  for its version; a change set written meanwhile refuses the confirmation and the preview keeps
  waiting until cancelled. A preview is a background job, refused inline, and runs at most
  `JOB_PREVIEW_MAX_ITEMS` items.
- **J11.10 Keep two records apart** (0.9 K3, D129): an `ensureNoRelation` item names a relationship
  by its type and its two records and deletes it, with the single delete's refusals (a required or
  containment relationship, a stale `expectedVersion` when one is sent); when the records are not
  related it is `unchanged`, so sending it again changes nothing. Live and in a change set.
- **J11.11 A previewed set replacement claims what it showed** (0.9 K3, D130): in a preview a
  `replaceRelationSet` needs no `expectedRelationSetVersion`; its outcome names the set's version it
  found (`previousRelationSetVersion`), and confirming carries that version into the item, so a set
  changed between the preview and confirming is refused `RELATION_SET_VERSION_CONFLICT` and the
  others apply (nothing under `atomic`). Executed without a preview, a replacement still needs a
  claim.
- **J11.12 A record holds one of a kind** (0.9 K3a, D136): on a `many-to-one` binding a record at
  the `from` end holds at most one relationship, and a record at the `to` end serves any number. A
  second one is refused `CARDINALITY_VIOLATION` by the single write, a batch item, a set replacement
  with two targets and a change set's write; a set of one replaces the one held. The value needs
  schema 0.9, and a required `many-to-one` binding is refused at validation (D137).

**Refusals:** `413 BATCH_TOO_LARGE`, `422 INVALID_BATCH_CONTEXT`, `422 IDEMPOTENCY_KEY_REUSED`,
`409 IDEMPOTENCY_IN_PROGRESS`, `409 CHANGE_SET_REQUIRED`, `409 MODEL_RELEASE_CHANGED`; per item, the
single writes' codes.

**Evidence today:** the J11 journey tests; unit tests of `engine/jobs/batches.py` and `inline.py`;
`test_rule_parity` (batch context), `test_pg3b_batch_writes`,
`test_batch_statements` (object, relationship and `ensureNoRelation` items).

### J24 — Run a large background job and recover

**Actor:** integrator; exchange operator. **Channel:** API; UI (Settings › Integration › Jobs and
feed lists jobs and cancels a queued or running one, 0.9 U4). **Stories:** US-I03, US-I04.
**Scenario:** SC-10. **Status:** delivered (0.9 B2).

1. Submit a batch to run in the background; receive the queued job.
2. Follow its progress and page its item outcomes as chunks commit.
3. Cancel it if needed.
4. After a crash or restart, the job resumes at its first unfinished item.

**Variants:**

- **J24.1 An import beside stewards**: a live write in the workspace waits for one chunk at most.
- **J24.2 Cancel** a queued job, between chunks, or an atomic job (rolled back completely).
- **J24.3 Two workers**: a worker that lost its lease commits nothing; the other continues.
- **J24.4 The model, the change set or the workspace changes mid-job**: the job fails with the
  reason, keeping the chunks already applied.
- **J24.5 Retention**: finished jobs expire and keep their summary; their item outcomes are removed,
  so reading them answers an empty page.
- **J24.6 The database is unreachable**: the worker waits and retries, logging the cause once, and
  resumes when the database returns.
- **J24.7 Follow a job as it changes**: `GET /jobs/{id}/events` sends the job at once, then again
  after each committed change of its state, progress, cancel request or output, and ends after a
  final state; a finished job is sent once. A browser follows its own jobs this way and is told
  when they finish (0.9 J1u); nothing is polled.

**Refusals:** `409 JOB_FINISHED`, `404 JOB_NOT_FOUND`; job errors `MODEL_RELEASE_CHANGED`,
`CHANGE_SET_VERSION_CONFLICT`, `WORKSPACE_RETIRED`, `JOB_FAILED` (with a correlation ID).

**Evidence today:** the J24 journey tests (J24.7 in `test_j24_job_stream`, over HTTP); unit tests of `engine/jobs/worker.py`, `store.py` and
`background.py`; `test_pg3_concurrency`; the composed journey `test_j24_j26_composed` (a resumed,
a staged and two cancelled jobs read back through the feed and the queries, 0.9 T1).

### J26 — Follow changes reliably

**Actor:** integrator. **Channel:** API. **Stories:** US-I05. **Scenario:** SC-10 (feed part).
**Status:** delivered (0.9 F1, F2).

1. Read the ordered change feed of a workspace from a stored position, a page at a time, until
   caught up (`nextAfter` equals `headPosition`). Every change to live data has one entry with a
   position: gapless, in commit order, naming what changed and why, never values.
2. Restart after interruption at the stored position; recognize repeated delivery by position.
3. Recover from an expired position without silently missing changes.

**Variants:**

- **J26.1 Batches and refused writes**: a batch's applied items have entries with the job as cause;
  a rejected item, a rolled-back batch or a refused write take no position, so no gap appears.
- **J26.2 A publish**: change-set edits, validation and discard take no position. Publishing adds
  one entry per record and relationship it changed in live data (records created or changed,
  relationships removed, relationships added, records removed), with the publication as cause,
  then the publication's own entry; live data at that position equals the publication. Withdrawing
  it adds one entry.
- **J26.3 A type change published**: a record whose type changed reads as `reclassified` with its
  previous type, plus the relationship changes it brought.
- **J26.4 Filters**: by kind and by object type; a sparse filter answers short or empty pages with
  the position advanced by a bounded scan, never an unbounded one.
- **J26.5 Concurrent writers**: writes to one workspace at once get gapless positions in commit
  order; other workspaces have feeds of their own.
- **J26.6 An expired position**: entries older than the retention period expire. A position below
  the earliest one still readable is refused, naming the active publication and its position; the
  reader re-reads that publication, follows the feed from its position and ends with live data. The
  earliest position never passes the active publication's, and without one nothing expires, so a
  reader always has a way back. The refusal also names the export route: a live export is a second
  baseline, read at one instant with its feed position (0.9 J1, J27.2).

**Refusals:** `404 WORKSPACE_NOT_FOUND`, `409 FEED_POSITION_AHEAD` (a position past the head, from
another workspace or a restored database), `410 FEED_POSITION_EXPIRED` (a position older than
retention), `422 REQUEST_VALIDATION_ERROR` (page size, position).

**Evidence today:** the J26 journey tests; `test_pg3_concurrency` (commit order under a held write,
publish beside a live write); the composed journey `test_j24_j26_composed` (a reader following a
background job across a restart, its publish and its cancellation, 0.9 T1).

### J27 — Exchange a supplier file

**Actor:** exchange operator; data owner. **Channel:** API, UI. **Stories:** US-I04, US-I07, US-I08.
**Scenario:** SC-10. **Status:** export delivered in 0.9 J1 (API) and J1u (browser); import
through the API delivered in 0.9 J2, its preview and confirmation in 0.9 J3, and in the browser in
0.9 J4.

1. Choose the destination and identify the file's columns.
2. Preview proposed additions, updates and errors by row and field; nothing changes.
3. Execute under the chosen failure policy; act on rejected rows without redoing applied ones.
4. Export a chosen, stated scope: `POST /exports` queues a job; when it completes, the job states
   what the file holds and `GET /jobs/{id}/output` serves it.

**Variants:**

- **J27.1 Export a stated scope**: live data, a change set or a publication; one or several types,
  each with its own criteria; only below one record; on a business date (types with a declared
  period are dated, the others exported as they are); with or without relationships; JSON Lines,
  CSV or XLSX. The job's `output` names the counts per type, the context, the feed position, the
  release, the format, the size and the SHA-256 of the file.
- **J27.2 The export as a baseline**: everything in the file was read at one instant; writes
  committed meanwhile are not in it and appear in the feed after the export's position. A reader
  whose position expired re-reads an export and follows the feed from its position.
- **J27.3 Round trip**: a JSON Lines export sent back as a batch to the same workspace changes
  nothing; each record carries its version, so an edited file updates only records nobody changed
  since the export. CSV and XLSX hold the same records in one table layout.
- **J27.4 No partial output**: a cancelled, failed or expired export serves no file; a batch has
  none.
- **J27.5 Refusals**: an unknown type, field or operator at its pointer, a date no exported type
  is dated by, an unknown parent, two contexts at once, a type named twice; with job creation
  turned off the route is absent.
- **J27.6 In the browser**: Export on a collection page opens a dialog prefilled with its type,
  context, filters (a relationship filter included, 0.9 K6) and scope (the search is not carried); New export on Settings › Jobs exports
  any types of a workspace. A notification says the export started; another says it finished,
  with Download and View job, or that it failed or was cancelled, with View job. The job's page
  shows its state, progress, error and, once completed, what the file holds and Download.
- **J27.7 Keep import profiles**: save, read, list, change under a version and delete a profile
  that maps a file's sheets and columns to the model; a profile is refused with every problem at
  its JSON pointer; after a release changes what it names it reads as no longer valid, and an
  import naming it is refused with the same problems.
- **J27.8 Load a file through a profile**: an XLSX or CSV file into live data or a change set;
  attributes converted by their value types, value maps, parents and relationships matched by a
  name, ID or attribute (also to records the same file creates), split cells, flag columns and
  related records; each row's items name its sheet and row.
- **J27.9 Load a file without a profile**: a JSON Lines file of batch items, or an export's CSV or
  XLSX tables sent back; an unchanged export changes nothing.
- **J27.10 Rows that cannot load**: a value that does not convert, a match finding no record or
  several, one key on rows with different values, rows whose parents form a ring; a row names
  every cell that does not convert, each with its column; under `independent` the other rows load,
  under `atomic` nothing does. A file that does not fit its profile fails before anything is
  written; an unsupported or oversized file is refused before a job is stored. An import stopped
  midway resumes where it stopped, and a retry with its `Idempotency-Key` creates nothing twice.
  A file whose rows name records by IDs of another workspace (an export of it) says so before its
  rows are read, and each such row is refused naming that workspace: record IDs are unique across
  the instance, so such a file loads only into the workspace it came from.
- **J27.11 Preview before loading**: a file previewed live or in a change set changes nothing; the
  counts, the result under the policy, the binding report (per column: cells read, empty,
  converted, value-mapped, refused; for a match column resolved, not found, ambiguous) and the
  outcomes by row say what execution would do. Confirmed, it binds the file again and executes, so
  data changed meanwhile counts; a change set changed meanwhile refuses the confirmation and the
  preview keeps waiting. Cancelled, it ends at once; left, it expires with the job's retention.
- **J27.12 A large file previewed in part**: every row bound and reported, the first items run up
  to `JOB_PREVIEW_MAX_ITEMS`, the preview marked `sample` with the items and rows it covers.
- **J27.14 Load another workspace's export**: with counterparts asked for, an export of workspace A
  loads into workspace B as B's own records, each with its counterpart ID (derived from its ID in A
  and B's key) and naming its source ID; parents and relationships arrive whole. Sent again, nothing
  changes; a later file, a batch or a profile matching by ID finds the counterparts an earlier one
  loaded; B's own export stays exact; into a change set the IDs are those a live load gives. A row
  whose record names a counterpart not loaded yet is refused, saying to load the file holding it
  first. Without the option, J27.10's explained refusal stands.
- **J27.15 A workbook for people**: one type's collection exported as a workbook people work in:
  the main sheet holds the columns the table shows, in its order and labels, with typed cells,
  relation columns as "; "-separated names (or the field the column shows, or another field chosen
  for it) and the record's ID and version in hidden columns; a sheet per chosen relationship holds
  the records the exported ones own, or the relationships with their values. A column that cannot
  say what to change (a relationship with its own sheet, a field that identifies nothing) is marked
  "(not imported)". Header frozen and filtered, name and relation columns in their types' colours,
  and a hidden import profile that reads the workbook back.
- **J27.16 A workbook for people read back**: the workbook imported without a profile is read
  through the profile it carries: untouched, every item is unchanged; edited, exactly the edited
  values, names and relationship rows change, a list of names replaces the record's set, a sheet adds
  and changes relationships and never removes one, a summary column is ignored; a record changed
  since the export is refused (`VERSION_CONFLICT`), a name matching several records refuses its row.
- **J27.17 Refusals of a workbook for people**: several types, a format other than XLSX, a column
  the type's table cannot show or a relationship the type does not have: `422
  INVALID_EXPORT_LAYOUT` at its pointer, no job stored.
- **J27.18 Owned records as columns per parent**: a workbook for people lays an owned relationship
  out as one row per exported record and a column per chosen parent and field (the parents holding
  owned records, and any added); each header names its field and parent, and the ancestor the owned
  records are unique within when that is higher; a hidden version per row and parent.
- **J27.19 A parent's column filled**: an empty cell filled creates the owned record under its
  column's parent, owned by its row's record; an edited cell updates its record; a cleared cell
  changes nothing; a record changed since the export is refused (`VERSION_CONFLICT`); untouched,
  nothing changes.
- **J27.20 Lists to choose from**: cells naming one other record (a single relationship's column, a
  relationship sheet's related record, an owned record's parent and owner) offer a dropdown of the
  records that relationship may choose, from a reference sheet of them; every written cell has a
  border; a value outside the list is refused by row on import.
- **J27.21 Refusals of columns and lists**: columns per parent for a relationship that owns nothing
  or has no sheet, a parent the owned type cannot stand under or not in the context, a field it
  lacks, a list for a relationship the workbook does not name: `422 INVALID_EXPORT_LAYOUT` at its
  pointer.
- **J27.13 Import a file in the browser**: Import on a collection page loads into the data the page
  shows (live or its change set); New import on Settings › Jobs chooses a workspace and its live
  data or one of its change sets. The user picks a file, a stored profile or none, the policy and
  what happens to records the file finds, and previews; the import's page opens at once and shows
  the counts, the result under the policy, the refused rows with each failing cell and the binding
  report, then **Load the file** or **Cancel import**, then the result. Refused rows are corrected
  in the file and the file sent again: rows already loaded come back unchanged. A user who left is
  brought back by Preview ready, or by Jobs and feed.

**Refusals:** `422 INVALID_QUERY`, `422 AS_OF_NOT_SUPPORTED`, `422 WORKSPACE_CONTEXT_MISMATCH`,
`404 PARENT_NOT_FOUND`, `404 WORKSPACE_NOT_FOUND`, `404 CHANGE_SET_NOT_FOUND`,
`404 PUBLICATION_NOT_FOUND`, `422 REQUEST_VALIDATION_ERROR`; on the output `404 JOB_NOT_FOUND`,
`404 JOB_HAS_NO_OUTPUT`, `409 JOB_NOT_COMPLETED`, `410 JOB_EXPIRED`, `410 JOB_OUTPUT_MISSING`.
Profiles: `422 INVALID_IMPORT_PROFILE`, `409 IMPORT_PROFILE_EXISTS`, `404 IMPORT_PROFILE_NOT_FOUND`,
`409 IMPORT_PROFILE_VERSION_CONFLICT`. Imports: `413 IMPORT_TOO_LARGE`, `422 UNSUPPORTED_FILE_FORMAT`;
a job's `IMPORT_FILE_MISMATCH`, `IMPORT_FILE_UNREADABLE`, `IMPORT_TOO_MANY_ITEMS`,
`IMPORT_FILE_MISSING`; a row's `INVALID_ATTRIBUTE_VALUE`, `REFERENCE_NOT_FOUND`,
`REFERENCE_AMBIGUOUS`, `DUPLICATE_KEY_IN_FILE`, `REFERENCE_CYCLE`, `MISSING_RECORD_KEY`,
`NAME_REQUIRED`, `INVALID_NAME`, `INVALID_CELL`. Previews: confirm's `409 JOB_NOT_AWAITING_CONFIRMATION`,
`410 JOB_EXPIRED`, `409 CHANGE_SET_VERSION_CONFLICT` and the context's codes; rows'
`404 JOB_HAS_NO_ROWS`.

**Evidence today:** the J27 journey tests (`test_j27_export`, 0.9 J1; `test_j27_import`, 0.9 J2 and
J3, the preview);
J27.6 in the browser runner `j1u-export` and `ExportDialog.test`, `JobNotifications.test` (0.9 J1u);
J27.15–J27.17 in `test_j27_people_workbook` and the browser runner `j6-people-workbook`, `ExportDialog.test`, `ImportDialog.test` (0.9 J6);
J27.18–J27.21 in `test_j27_people_columns` and the browser runner `j6a-people-columns`, `ExportDialog.test` (0.9 J6a);
J27.13 in the browser runner `j4-import` and `ImportDialog.test`, `JobPage.test`,
`JobNotifications.test` (0.9 J4);
unit tests of `engine/imports/` (cells, profiles, readers, the binding report) and of the row read,
`test_import_volume` and the budget `test_import_budget`.

### J28 — Read a business object through a consumer API

**Actor:** consuming system. **Channel:** consumer API. **Stories:** US-I09 (consumer side).
**Status:** get by ID delivered (0.9 C2), lists and parameters (0.9 C3), publications and ETag (0.9
C6a); XREF is J29 (0.9 C4); the rest follows in C6b and C16 ([CONSUMER_API.md](../CONSUMER_API.md)).

1. Read one business object by its object ID from a consumer API's contract version:
   `GET /api/consumer/{consumerApi}/v{contractVersion}/objects/{id}`; or read a declared list of them,
   page by page: `GET /api/consumer/{consumerApi}/v{contractVersion}/lists/{listKey}`.
2. Receive the definition's shared object: exactly the declared fields, values in their declared
   types, `parent` (or `null`), `path` and `hierarchy` from the ancestors, and each projection as an
   object or `null`, or as an array, by the relationship's cardinality. A list item is the same object.
3. Narrow either read with the definition's parameters, and a list with its parent parameter.
4. Read live data in the default workspace, or in the workspace named by `workspace`; the response
   names it in `RDM-Workspace`, and a list's envelope in `workspace` as well. Or read one of its
   publications with `publication` (J28.11).

**Variants:**

- **J28.1 Identity is the object ID**: a generated or a client-assigned ID; another identifier is
  not found by get by ID (XREF finds it, J29).
- **J28.2 Live data, never unpublished work**: a live change shows at once; a record only in a
  change set is not found until published.
- **J28.3 Another workspace**: each record is found only in its own workspace.
- **J28.4 Refusals**: unknown API, contract version or parameter; a parameter the read does not
  apply (a list's parent parameter on get by ID); a record of a type the definition does not expose.
- **J28.5 The contract follows the release**: a new contract version replaces the old one, with
  the new projection shape.
- **J28.6 Every object of a type**: a list without a parent value holds every live record of its
  type, in the list's `sortBy` order (records without a value last), then name; it pages with
  cursors both ways, `anchor`, `position`, `from=end` and `seek`, and counts with `includeTotal`.
- **J28.7 Below a parent**: a parent value, by object ID only, keeps the records of the list's type
  anywhere below that record; several IDs keep those below any of them. An ID that is no record of
  the parent types is refused.
- **J28.8 Parameters narrow a list**: `ancestor`, `related` (through a projection, `self` or a shared
  projection), `projection` (limiting the projection and, with `requireMatch`, the records) and
  `objectType`; several values, repeated or comma-separated (a comma inside a value sent as
  `%2C`), are alternatives; different parameters combine.
- **J28.9 Parameters on get by ID**: a parameter limits the projection or filters the record out
  (`404`); a paging or parent parameter is not supported there.
- **J28.10 Paging refusals**: an unknown list, a page size outside 1–100, conflicting page
  selectors and a cursor sent with other parameters.
- **J28.11 Pinned to a publication**: `publication={id}` reads every record, value and relationship
  as that publication holds them, whatever live data has done since; the response names it in
  `RDM-Publication`, and a list's envelope in `publication` (`null` when live).
- **J28.12 `latest` and paging an extract**: `publication=latest` reads the workspace's current
  publication; a cursor keeps the publication it started in, so an extract pages every record once
  even when a newer publication appears meanwhile. A superseded or withdrawn publication stays
  readable by its ID; with no current publication, `latest` is not found.
- **J28.13 Publication refusals**: an unknown publication, or one of another workspace; a cursor of
  another publication or of live data; `publication` inside a batch resolve item; a publication made
  under a model release that does not declare the requested contract version.
- **J28.14 The publications list and ETag**: `GET …/publications` lists the workspace's publications
  newest first with `eventSequence`, the feed position to follow changes from, and `status`; every
  `GET` read answers an `ETag`, and `If-None-Match` with it answers `304` until the data, the model
  release or the contract changes. A pinned read's tag never changes.

**Refusals:** `404 CONSUMER_API_NOT_FOUND`, `404 CONTRACT_VERSION_NOT_FOUND`,
`404 OBJECT_NOT_FOUND`, `404 WORKSPACE_NOT_FOUND` (unknown or retired), `404 LIST_NOT_FOUND`,
`404 PARENT_NOT_FOUND`, `400 UNKNOWN_PARAMETER`, `400 PARAMETER_NOT_SUPPORTED`,
`400 UNKNOWN_OBJECT_TYPE`, `400 INVALID_PAGE_SIZE`, `400 INVALID_CURSOR`,
`400 CONFLICTING_PAGE_PARAMETERS`, `400 INVALID_POSITION`, `400 INVALID_SEEK`,
`404 PUBLICATION_NOT_FOUND`, `409 PUBLICATION_CONTRACT_MISMATCH`.

**Evidence today:** the J28 journey tests; on a model shaped like the reference deployment's, the
parity tests (`test_j28_j29_parity`, 0.9 C8).

### J29 — Resolve a business object through a consumer API

**Actor:** consuming system. **Channel:** consumer API. **Stories:** US-I09 (consumer side).
**Status:** delivered in 0.9 C4, with the definition's parameters in C5, batch resolve in C14,
crosswalk in C15 and reads pinned to a publication in C6a ([CONSUMER_API.md](../CONSUMER_API.md)).

1. Look up business objects by what the system knows, a code, an ID, a name or a related record's
   value: `GET /api/consumer/{consumerApi}/v{contractVersion}/xref?query=…`.
2. Receive the matching objects of the definition's exposed types, best first, each as the shared
   object with its `matchScore`: the definition's `match` weights its own fields (exact matches add
   up; contains counts only without an exact match) and passes a related record's first matching
   weight to the objects it relates to through a projection. Ties order by public type name, name
   and object ID.
3. Narrow the lookup with the definition's parameters, as on a list (J28.8): only the scored objects
   every parameter keeps are results.
4. Page through the results with cursors both ways, `position` and `from=end`; `totalCount` is always
   given. Or ask for the single best one with `expect=one`.
5. Read live data in the default workspace, or in the one named by `workspace`.
6. Translate what was found into another representation in the same read (crosswalk): `to.{name}`
   names a targetable `projection` parameter and a value, and each object carries the projection's
   matching items as `target`.

**Variants:**

- **J29.1 Promoted matches**: a related record's match scores the objects it relates to; with
  `preferTargetTypes` only those of the preferred types; an object keeps the higher of its own and
  its promoted score.
- **J29.2 Several terms**: comma-separated (a comma inside a term sent as `%2C`) or repeated `query`;
  an object scores its best term.
- **J29.3 `expect=one`**: the single top object; nothing matched is `404`, a shared top score `409`
  naming the tied objects.
- **J29.4 Paging**: cursors both ways, `position`, `from=end`, `totalCount` and `startIndex` on every
  page; a cursor is bound to its terms.
- **J29.5 Refusals and limits**: no term, more than 100 terms, a parameter XREF does not apply (a
  list's parent parameter, `seek`, `includeTotal`); a term shorter than 3 characters matches exactly
  only; a query matching more than 10,000 records is refused, whatever parameters narrow it.
- **J29.6 Parameters narrow the lookup**: `objectType`, `ancestor`, `related` and `projection` keep
  the scored objects they keep on a list, each with its unchanged score; `totalCount`, the pages and
  `expect=one` follow the narrowed set, so a parameter can resolve an ambiguous match; a `projection`
  parameter limits that projection's items; a cursor is bound to the parameter values.
- **J29.7 `scoresFrom`**: a `projection` parameter declaring `scoresFrom` also limits which related
  records pass their weights through that projection; the objects' own scores are untouched.
- **J29.8 Resolve many values at once**: `POST …/resolve` with up to 1,000 items, each a query or
  an object ID; each outcome, in item order with its `index` and `ref`, is the single read's answer:
  `found` with the object `xref?expect=one` or get by ID returns, or `not_found`, `ambiguous` or
  `rejected` with that read's error; `counts` sum them.
- **J29.9 Defaults and item parameters**: `defaults` give every item the definition's parameters; an
  item's own parameter replaces the default of the same name, so one item can be narrowed out of an
  ambiguous match while the others keep the defaults.
- **J29.10 Batch refusals**: an item with both or neither of `query` and `id`, a name the lookup does
  not apply, or any refusal of the single read is `rejected` with a pointer into it, and the other
  items are resolved; a body of the wrong shape, a wrong name in `defaults` or a definition parameter
  in the URL refuses the request, and more items than `CONSUMER_RESOLVE_MAX_ITEMS` (reported by
  `GET /capabilities`) is `413`.
- **J29.11 Crosswalk with `expect=one`**: `to.{name}` with `expect=one` answers the object found
  with `target`, the single matching item, which the projection also shows in place of the plain
  parameter's items; matching, scores and the plain parameter's `requireMatch` and `scoresFrom` are
  unchanged. No matching item is `404 TARGET_NOT_FOUND`, several `409 AMBIGUOUS_TARGET`, each naming
  the object; a shared top score stays `409 AMBIGUOUS_MATCH`.
- **J29.12 Crosswalk on pages and get by ID**: get by ID answers one target as `expect=one` does; a
  list or an `expect=any` page keeps every object, its order, scores and `totalCount`, each `target`
  in the projection's shape (empty where an object has none); cursors do not bind `to.` values.
- **J29.13 Crosswalk in batch resolve**: `to.{name}` in `defaults` or in an item; each outcome is the
  single read's answer, a missing or ambiguous target `not_found` or `ambiguous` with a pointer to
  where the `to.` name was given.
- **J29.14 Crosswalk refusals**: a `to.` name for anything but a targetable parameter is
  `400 UNKNOWN_PARAMETER`, two `to.` names `400 MULTIPLE_TARGETS`; in batch resolve, in an item they
  reject the item (an item's `to.` name replaces a different one from `defaults`), in `defaults` the
  request.
- **J29.15 Resolving against a publication**: XREF, crosswalk and batch resolve with `publication`
  match, score and answer from the publication's records, as J28.11 reads them; batch resolve takes
  `publication` in the URL, for every item.

An `expect=one` lookup settled by exact matches (a code, an ID or an exact name scoring above
anything a contains match could give) is answered without reading contains matches, so a contains
term matching more than 10,000 records does not refuse it.

**Refusals:** `400 QUERY_REQUIRED`, `400 TOO_MANY_TERMS`, `400 QUERY_TOO_BROAD`, `400 INVALID_EXPECT`,
`400 PARAMETER_NOT_SUPPORTED`, `400 UNKNOWN_OBJECT_TYPE`, `404 NO_MATCH`, `409 AMBIGUOUS_MATCH`,
`400 MULTIPLE_TARGETS`, `404 TARGET_NOT_FOUND` (also on get by ID), `409 AMBIGUOUS_TARGET`, and
J28's API, workspace and paging refusals; batch resolve adds `400 REQUEST_VALIDATION_ERROR` (a body
of the wrong shape), `QUERY_OR_ID_REQUIRED` (an item's outcome) and `413 BATCH_TOO_LARGE`.

**Evidence today:** the J29 journey tests and, on a model shaped like the reference deployment's,
the parity tests (`test_j28_j29_parity`, 0.9 C8); `QUERY_TOO_BROAD`, the exact-first rule and batch
statements in `test_consumer_xref_volume`.

### J30 — Follow a consumer API's changes

**Actor:** integrator; operator (subscriptions). **Channel:** API; UI (subscriptions on Settings ›
Integration › Webhooks, 0.9 U5). **Stories:** US-I05. **Status:**
the pull feed delivered (0.9 C10); subscriptions managed from 0.9 C11 and delivered as webhooks
from C12; the events accepted end to end in C13 ([CONSUMER_API.md](../CONSUMER_API.md)).

1. Read the events a consumer API declares for a workspace, in position order, from a position (`0`,
   or a publication's `eventSequence`), a page at a time by cursor until caught up.
2. Take each event's object from the event itself (the full payload), or only its identity.
3. Store the cursor and resume from it; recognise a repeated event by its `eventId`.
4. Recover from an expired position by re-reading a publication and following on from it.

**Variants:**

- **J30.1 Own changes**: creating, changing and deleting an exposed object makes `created`,
  `updated` (naming the changed outputs the event watches) and `deleted` under each event that takes
  that kind and type; a deletion says so and carries no object, code or name. Each event's position
  is its raw feed entry's.
- **J30.2 What an object shows**: changing a record the object shows makes `updated` for the object:
  its parent (`parent`), an ancestor's name (`path`, `hierarchy`), a projected record or its ancestor
  (the projection), a projection gaining or losing an item, also when the relationship is deleted.
- **J30.3 Batches, publishes and type changes**: a batch's applied items are told with the job as
  cause, a publish's changes with the publication as cause, at or below its `eventSequence`;
  change-set work, refused writes and failed items make none. A type change is `deleted`, `created`
  or `updated` with `objectType`, as seen from each event.
- **J30.4 Reading**: `event`, and the definition's parameters as a list applies them; an event whose
  object no longer exists passes every parameter but the type. A position holding many events is
  read whole by cursor; a caught-up cursor later returns the next events. A record that leaves the
  parameters' scope (moved, or edited so they stop matching) is not told by a narrowed read; its
  deletion is. `payload=full` (default)
  carries the object as get by ID answers it with the same parameters, `payload=identity` the same
  events without it. An entity tag answers `304` until a new event is derived.
- **J30.5 An expired position**: events expire with the change feed's retention, never past the
  active publication's position. A position below the earliest is refused naming that publication
  and its `eventSequence`; the reader re-reads the publication's lists and follows on from there.
  Without a publication nothing expires.
- **J30.6 Subscribe**: with the deployment's subscriptions capability on, an operator subscribes a
  URL (HTTPS on any host; plain HTTP only to a local host) to some of a consumer API's events in a workspace, narrowed by the
  definition's parameters as a list applies them, and chooses how requests are made: one event per
  request (the default) or batched up to a size of 2 to 1,000, each event with the object or the
  notification only, in RDM JSON or CloudEvents 1.0 (0.9 C17). The subscription starts after the feed's head, or after an earlier position still kept;
  its signing key is answered once. It has a name the operator gives it (required, 0.9 U5a); a
  rename alone keeps a batch being retried. The operator reads, lists, edits (with the version read),
  suspends, resumes and deletes it. Off, the routes are not served; the capabilities say which
  setting turns them on and which hosts are allowed.
- **J30.7 A subscription the model or workspace leaves behind**: activating a release that no
  longer declares a subscription's consumer API, event or filter suspends it (`MODEL_CHANGED`, with
  each finding); one that only raises the contract version suspends it until resumed
  (`CONTRACT_VERSION_CHANGED`). Retiring its workspace suspends it (`WORKSPACE_RETIRED`). A resume
  re-checks the subscription and lists what to fix; after its unacknowledged events expired it is
  refused `EVENTS_EXPIRED`, naming the lost positions, the publication to re-sync from and `reset`,
  which starts after the feed's head instead (J30.9). A workspace with subscriptions cannot be deleted.
- **J30.8 Receive**: an active subscription's receiver gets its events in position order: one event
  per request, or batched, requests of up to the subscription's size and at most 1 MiB holding what
  is waiting; each event with the object as get by ID answers it under the subscription's filters,
  or the notification only; as RDM JSON (an envelope with the events, also one) or CloudEvents 1.0
  (one structured event, or a batched array, each with the RDM event as `data`). Each request
  is signed with the subscription's key over its timestamp and body. A `2xx` answer acknowledges the
  request and the next follows; events outside the subscription's events or filters are not sent,
  and the subscription's position moves past them; so is the change by which a record leaves the
  filters' scope, so a receiver that must drop such records filters by type only and narrows
  itself. The subscription shows when it last delivered.
- **J30.9 A receiver that fails, or a subscription that cannot continue**: a failed request (an
  error status, a redirect, no answer within the timeout, an address refused) is retried with the
  same delivery ID and events, nothing later is sent past it, and the subscription shows the
  attempts, the last error and the next attempt. After 24 hours of failures it is suspended
  `DELIVERY_FAILED`; a resume delivers everything from the first unacknowledged event. A filter
  value no record matches any longer suspends it `FILTER_MATCHES_NOTHING`, before anything is sent; events that expired before they
  were delivered, `EVENTS_EXPIRED`. A resume with `reset` starts after the feed's head instead,
  and the receiver re-syncs what it missed itself.
- **J30.10 Read what was delivered** (0.9 U5a): an operator lists a subscription's deliveries,
  newest first, one row per event a request carried, each with its delivery ID, event, object, status (`queued`, `sending`, `retrying`, `succeeded`,
  `failed`, `dropped`), attempts, the receiver's latest status code, when it was sent and, while a
  retry is due, when; narrowed by status. A request's detail holds the body as sent (its latest
  attempt's) and every attempt with its start, completion, duration, answer or error and up to
  4 KiB of the response. Rows of one request share its outcome. An edit that drops a batch leaves
  it `dropped`; a day of failures, `failed`. Entries are kept for
  `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` (reported in capabilities), a batch still pending longer;
  a deleted subscription's go with it. An operator resends an event by hand, whatever its status:
  the event as it was sent, alone in a new request with the same `eventId` and `RDM-Redelivery:
  manual`, once, during the call, also while suspended, in the format it was sent in; the new
  request names the one it repeats. UI: Settings › Integration › Webhooks, Deliveries, where a
  delivered event is resent only after a confirmation.

**Refusals:** `404 EVENTS_NOT_DECLARED`, `400 UNKNOWN_EVENT`, `400 PARAMETER_NOT_SUPPORTED`
(`publication`, `asOf`, `to.`), `400 INVALID_PAGE_SIZE` (1–100 with the full payload, 1–1,000 with
identity), `400 INVALID_PAYLOAD`, `400 INVALID_POSITION`, `400 CONFLICTING_PAGE_PARAMETERS`,
`400 INVALID_CURSOR`, `409 EVENT_POSITION_AHEAD`, `410 EVENTS_EXPIRED`, and J28's API and workspace
refusals. Subscriptions: `400 CONSUMER_API_NOT_FOUND`, `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`,
`UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, `UNKNOWN_OBJECT_TYPE`, `FILTER_MATCHES_NOTHING`,
`INVALID_WEBHOOK_URL`, each at its body pointer; `404
WORKSPACE_NOT_FOUND`, `404 SUBSCRIPTION_NOT_FOUND`; `409 VERSION_CONFLICT`,
`SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED`, `SUBSCRIPTION_NEEDS_EDIT`,
`404 DELIVERY_NOT_FOUND`, `404 EVENT_NOT_IN_DELIVERY`, `409 DELIVERY_NOT_SENT` (J30.10),
`EVENT_POSITION_AHEAD`, `EVENTS_EXPIRED` (resume), `WORKSPACE_HAS_SUBSCRIPTIONS`; `410
EVENTS_EXPIRED` (`startAfter`).

**Evidence today:** the J30 journey tests (`test_j30_consumer_events`, `test_j30_subscriptions`,
`test_j30_delivery`), and the events' acceptance end to end through a receiver
(`test_j30_acceptance`: a publish in batches as the pull feed has it, work that never reaches live
data, filters as the lists scope, a reset and re-sync after expiry, a running application
delivering on its own); the deriver's plan and delivery in `tests/unit/engine/events/`; their cost
in `test_consumer_event_volume`; the Webhooks page in `u5-webhooks` (create, the key, a refused
delivery retried, suspend and resume, delete, through a receiver).

## Operations

### J12 — Run the service, and recover from an expected refusal

**Actor:** platform operator. **Channel:** Operator (settings, commands, `/health`).
**Stories:** US-O01, US-O02. **Scenario:** SC-13. **Status:** delivered.

1. Start the service: it checks its database and migrates it, then serves.
2. On a refusal, read one concise message: what failed, the service state, the safe next step.
3. Follow it, restart, and see `/health` ready.

The normal operator path never requires reading a traceback; the cause stays available through
controlled diagnostics.

**Variants:**

- **J12.1 No or a wrong database URL**, **J12.2 the wrong collation**, **J12.3 an unknown revision**,
  **J12.4 `pg_trgm` or `btree_gin` missing**: each refused with its instruction.
- **J12.5 An interrupted migration** leaves the database at its previous revision; the next start
  recovers.
- **J12.6 An unsupported model schema in the database**: startup names the offline upgrade command,
  which installs and selects a supported release atomically.
- **J12.7 Settings**: model administration, workspace administration, integration jobs and their
  limits, the API reference script; an invalid setting refuses to start.
- **J12.8 The database goes away while running**: requests and the job worker report it concisely,
  `/health` reports not ready, and all recover when it returns, without a restart (J24.6).
- J12.9 (carry a SQLite database over) was dropped with PG4 on 2026-10-03: the developer's data was
  moved by hand, and no engine command copies SQLite data.

**Evidence today:** the J12 journey tests; `test_startup`, `test_model_schema_upgrade`,
`test_schema_drift`, `test_api_reference`; unit tests of `config.py` and `main.py`.

### J31 — Check what a deployment runs and how it is configured

**Actor:** platform operator. **Channel:** API (`GET /api/v1/system`) and UI (Settings › About and
Deployment). **Status:** delivered (0.9 U3).

1. Read what the deployment runs: the engine and management API version, the schema languages it
   reads, the active model release (name, key, version, schema language, when it was activated) and
   the database's migration revision.
2. Read how it is configured: every setting, its group, what it controls, its value, its default and
   whether the value came from the environment or is the default; the capability groups on or off.

Settings change only with a restart; the API and the page read them, never edit them.

**Variants:**

- **J31.1 From the environment or the default**: a setting given in the environment reads its typed
  value (integer, boolean, list) and `environment`; one left alone reads its default and `default`.
- **J31.2 Secrets**: the cursor signing key and the webhook key-encryption key read no value, only
  whether they are set; `DATABASE_URL` reads without its password.
- **J31.3 After an activation**: the active release is the one activated, with the activation's time.

**Evidence today:** `test_j31_system`; the settings catalogue and URL masking in
`tests/unit/test_config.py`; the settings pages in `e2e/u3-settings.mjs`.

## Guardrails kept from 0.7

In J10, clear is offered only where empty is valid. Search continues beyond page one; large ambiguous
sets expose counts and continuation. Keeping a selected existing target preserves its relationship
identity and attributes. Mapping and change-set-version conflicts retain the attempted choice for
review. When changing a change set's model (J18), the full candidate must already fit; failure changes
nothing. Success reloads model-dependent views, forms and lookups, resets obsolete cursors and
recovers removed routes without silently discarding dirty input. Older pinned releases remain usable
and are labelled neutrally. See SC-07, SC-15 and [the 0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md).
