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
| Records and structure | J01 find, J02 correct, J03 add, J04 delete, J13 relate, J14 hierarchy, J15 reshape across types |
| Relationship sets and coverage | J10 replace a record's related records, J16 coverage across ancestors (J09 retired) |
| Change sets and history (designer) | J05 prepare and publish, J06 live beside a change set, J07 withdraw and restart from history, J17 review changes, J18 next model version |
| Administration | J08 model release, J19 workspaces, J25 consumer API definition |
| Integration | J11 bulk change, J20 discover, J21 read completely, J22 precise dataset, J23 business date, J24 background job, J26 follow changes, J27 supplier file (planned) |
| Operations | J12 run, refuse and recover |

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

**Refusals:** `404 workspace_not_found`, `404 object_not_found`, `404 unknown_object_type`,
`422 invalid_filter`, `422 invalid_sort`, `422 mutually_exclusive_context`,
`404 change_set_not_found`, `404 publication_not_found`.

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

**Refusals:** `409 version_conflict`, `409 duplicate_attribute_value`, `422 invalid_attribute_value`
(a value of the wrong type), `422 attribute_below_minimum`, `422 attribute_above_maximum`,
`422 unknown_attributes`, `422 object_attribute_rule_violation`,
`422 cannot_delete_required_attribute`, `422 read_only_attributes`, `409 attribute_already_exists`,
`404 attribute_not_found`, `409 workspace_retired`.

**Evidence today:** `wp9-authoring`; `test_api`, `test_attributes`, `test_rule_parity`,
`test_pg3_concurrency`.

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

**Refusals:** `422 parent_required`, `422 invalid_parent_type`, `422 parent_wrong_scope`,
`422 missing_required_attributes`, `422 missing_required_relations`,
`422 invalid_object_type_for_application` (live; `object_type_not_in_application` in a change set),
`404 unknown_application`, `409 duplicate_attribute_value`, `409 duplicate_relation_scope`,
`409 object_already_exists`, `422 duplicate_initial_relation`, `409 cardinality_violation`,
`404 workspace_not_found`, `409 workspace_retired`.

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

**Refusals:** `409 deletion_preview_required`, `409 deletion_preview_changed`,
`409 object_has_dependants`, `409 version_conflict`, `422 required_relation`.

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

**Refusals:** `422 unknown_relation_type`, `422 invalid_relation_pair`, `422 relation_endpoint_missing`,
`422 relation_wrong_scope`, `422 unknown_relation_attributes`, `422 immutable_relation`,
`409 cardinality_violation`, `409 duplicate_relation_scope`, `409 relation_set_version_conflict`,
`422 relation_set_claim_incomplete`, `422 required_relation`, `409 version_conflict`,
`409 duplicate_relation`, `404 relation_not_found`.

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

**Refusals:** `422 parent_cycle`, `422 invalid_parent_type`, `422 parent_wrong_scope`,
`409 duplicate_relation_scope`, `409 version_conflict`.

**Evidence today:** `b3-tree-lens`, `b4-hierarchy-acceptance`, `s6-sidebar-tree`,
`ui03b-hierarchy`; `test_parent_candidates`, `test_pg3_concurrency`.

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

**Refusals:** `422 restructuring_not_ready`, `422 restructuring_too_large`,
`409 restructuring_plan_changed`, `422 invalid_type_mapping`, `422 object_type_unchanged`,
`409 object_type_changed`, `422 type_changes_need_change_set`; a single record's type change is
refused with `422 child_type_not_allowed` or `422 required_relation_without_place`, which a
restructuring preview reports instead as problems of its plan, in its `200` answer.

**Evidence today:** `c4-restructuring`, `c5-restructuring-acceptance`; `test_restructuring_api`,
`test_restructuring_planner`, `test_type_changes`.

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

**Refusals:** `409 mapping_version_conflict`, `422 invalid_clear_attributes`,
`422 required_ownership_binding`, `422 relation_ancestor_required`, `422 required_relation`,
`409 cardinality_violation`, `409 duplicate_relation_scope`; publishing a change set whose set live
changed meanwhile is `409 version_conflict` with a `mapping_set_changed` conflict; `422 invalid_cursor`, and the view and binding refusals (`mapping_view_*`, `mapping_*`). Through a batch
(J10.10): `409 relation_set_version_conflict`, `409 version_required`, `409 duplicate_relation`,
`422 immutable_relation`, `422 reference_type_mismatch`.

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

**Refusals:** `404 relation_matrix_view_not_found`, `404 relation_matrix_row_not_found`,
`404 relation_matrix_column_not_found`, `404 relation_matrix_parent_not_found`,
`422 relation_matrix_action_not_allowed`, `422 relation_matrix_parent_scope_mismatch`,
`422 relation_matrix_state_requires_columns`, `422 too_many_columns`, `422 duplicate_column_ids`,
`422 conflicting_column_parameters`.

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

**Refusals:** `409 change_set_version_conflict`, `409 change_set_required`,
`409 change_set_snapshot_retry`, `422 workspace_graph_invalid`, `409 version_conflict` (a record
changed live since the change set's source, listed in `details.conflicts`),
`409 workspace_active_publication_conflict`, `409 model_release_changed`,
`404 change_set_not_found`, `409 workspace_retired`.

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

**Refusals:** `409 version_conflict`, naming each record changed on both sides in `details.conflicts`.

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

**Refusals:** `409 workspace_active_publication_conflict`, `404 publication_not_found`,
`409 workspace_retired`.

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

**Refusals:** `404 change_set_not_found`, `422 unknown_object_type`, `422 unknown_relation_type`,
`422 invalid_cursor`.

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

**Refusals:** `409 change_set_content_incompatible`, `409 change_set_model_release_conflict`,
`409 model_release_changed`, `409 change_set_version_conflict` (J18.4), and for J18.3
`409 pinned_model_unavailable`, `409 pinned_model_invalid`, `409 unsupported_pinned_model_schema`.

**Evidence today:** `sc15-model-version-acceptance`, `wp11-model-admin`; `test_build07_wp6`,
`test_build07_wp9_acceptance`, `test_wp81a_context`.

## Administration

### J08 — Create and activate an application-model release

**Actor:** model administrator; model author. **Channel:** UI, API (model administration enabled).
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
- **J08.9 Read a model draft's history** (planned, decided D-5).

**Refusals:** `422 invalid_model` (with the JSON pointer), `409 release_identity_conflict`,
`409 model_migration_required`, `409 activation_conflict` (stale runtime state),
`409 consumer_contract_version_required`, `422 unsupported_schema_version`,
`404 model_draft_not_found`, `503 model_registry_refresh_failed`; with administration disabled the
mutating routes are absent.

**Evidence today:** `wp11-model-admin`, `wp12-release-identity`, `wp9-authoring`;
`test_model_lifecycle`, `test_model_compatibility`, `test_build07_wp11`, `test_w5_activation_write_race`,
`test_model`, `test_model_diagnostics`.

### J19 — Administer workspaces

**Actor:** workspace administrator; integrator. **Channel:** UI, API. **Stories:** US-A01–A03,
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

**Refusals:** `409 workspace_already_exists`, `409 version_conflict`, `409 workspace_retired`,
`409 default_workspace_cannot_be_retired`, `404 workspace_not_found`, and for deletion `409 workspace_is_default`,
`409 workspace_has_publications`, `409 workspace_not_empty`.

**Evidence today:** `w4-workspace-admin`; `test_workspaces`, `test_w6_workspace_deletion`,
`test_pg3_concurrency`.

### J25 — Define a consumer API in the model

**Actor:** model author. **Channel:** API (model documents), UI (model administration).
**Stories:** US-I09 (consumer side), US-P04. **Status:** definitions delivered (0.9 C1); the
consumer tier's reads follow in C2–C16 ([CONSUMER_API.md](../CONSUMER_API.md)).

1. Declare a consumer API in the model: exposed types and their public names, fields with their
   sources, projections, parameters and lists, and a contract version.
2. Validate and compile it with the release; every reference is checked at its JSON pointer.
3. Compare with the active release: breaking changes need a higher contract version.
4. Activate; a break without a higher version is refused.

**Variants:**

- **J25.1 Additions are compatible**; removals and lower versions are reported.
- **J25.2 A model change** (a cardinality) changes a projection's shape and is reported.

**Refusals:** `422 invalid_model` (with the pointer), `409 consumer_contract_version_required`.

**Evidence today:** `test_consumer_api_model`.

## Integration

### J20 — Discover the model and the API

**Actor:** integrator. **Channel:** API. **Stories:** US-I01, US-P01. **Status:** delivered.

1. Read the capabilities: which groups are enabled and their limits.
2. Read the active model, or the model of a change set or publication, and its placements (where
   each type may stand).
3. Page the model's applications, attribute types, object types, relation types and allowed type
   pairs, or read one by key.
4. Read the API reference (`/docs`) and the OpenAPI document.

Every identifier is a stable public key or UUID; no internal sequence number is exposed. The model
read names the release it was read under (`X-Model-Release-Id`).

**Variants:**

- **J20.1 In a change set pinned to another release**: the model and metadata follow the pin.
- **J20.2 Releases**: list and read installed releases and the runtime state.

**Refusals:** `404 change_set_not_found`, `422 mutually_exclusive_context`,
`503 model_registry_unavailable`, `503 model_runtime_state_unavailable`.

**Evidence today:** `v1-api-reference`; `test_model_placements`, `test_request_scope`,
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

**Refusals:** `422 invalid_cursor`, `422 conflicting_page_parameters`, `422 invalid_seek`,
`422 invalid_sort`, `422 unknown_parameter` (J21.8).

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

**Refusals:** `422 invalid_query` (with the JSON pointer), `422 invalid_filter`, `422 invalid_sort`,
`422 mutually_exclusive_context`.

**Evidence today:** `test_model_query`, `test_cross_type_lookup`, `test_workspace_edge_list`,
`test_typed_table_queries`, `test_search_index`; the composed journey `test_j24_j26_composed` (the
edge list beside a job, a change set and a publication, 0.9 T1).

### J23 — Answer a business-date question

**Actor:** integrator. **Channel:** API. **Stories:** US-I06. **Scenario:** SC-11.
**Status:** management API delivered (0.9 Q4, ADR-038); the consumer side follows in C16.

1. Ask for a configured list's records applicable on a date (`asOf`).
2. Page through them; every page answers for that date.

The question is a date, not a time; only a model-declared effective period answers it.

**Variants:**

- **J23.1 The boundary day itself**, and **J23.2 overlapping periods.**
- **J23.3 In a change set or publication.**
- **J23.4 A period that does not end after it starts** is refused on every write.
- **J23.5 A model removing or adding a period.**

**Refusals:** `422 as_of_not_supported` (a type without a period, or the cross-type lookup),
`422 invalid_effective_period` on writes.

**Evidence today:** `test_effective_periods`; the composed journey `test_j24_j26_composed` (dated
queries over a job's records in live data, a change set and a publication, 0.9 T1).

### J11 — Submit a bounded bulk change

**Actor:** integrator. **Channel:** API. **Stories:** US-I03. **Scenario:** SC-10 (its batch part).
**Status:** delivered (0.9 B1; relationship items 0.9 B3).

1. Send items (create, update, upsert, delete; create, ensure, update and delete a relationship;
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
- **J11.6 Delete with cascade** (planned, decided D-6): a delete item removes a record with its
  dependants, as a single delete does, under a confirmation of the impact it deletes (PG-D18).

**Refusals:** `413 batch_too_large`, `422 invalid_batch_context`, `422 idempotency_key_reused`,
`409 idempotency_in_progress`, `409 change_set_required`, `409 model_release_changed`; per item, the
single writes' codes.

**Evidence today:** the J11 journey tests; unit tests of `engine/jobs/batches.py` and `inline.py`;
`test_rule_parity` (batch context), `test_pg3b_batch_writes`,
`test_batch_statements` (object and relationship items).

### J24 — Run a large background job and recover

**Actor:** integrator; exchange operator. **Channel:** API. **Stories:** US-I03, US-I04.
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

**Refusals:** `409 job_finished`, `404 job_not_found`; job errors `model_release_changed`,
`change_set_version_conflict`, `workspace_retired`, `job_failed` (with a correlation ID).

**Evidence today:** the J24 journey tests; unit tests of `engine/jobs/worker.py`, `store.py` and
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
  reader always has a way back.

**Refusals:** `404 workspace_not_found`, `409 feed_position_ahead` (a position past the head, from
another workspace or a restored database), `410 feed_position_expired` (a position older than
retention), `422 request_validation_error` (page size, position).

**Evidence today:** the J26 journey tests; `test_pg3_concurrency` (commit order under a held write,
publish beside a live write); the composed journey `test_j24_j26_composed` (a reader following a
background job across a restart, its publish and its cancellation, 0.9 T1).

### J27 — Exchange a supplier file (planned)

**Actor:** exchange operator; data owner. **Channel:** API, UI. **Stories:** US-I04, US-I07, US-I08.
**Scenario:** SC-10. **Status:** planned, 0.9 J1–J4.

1. Choose the destination and identify the file's columns.
2. Preview proposed additions, updates and errors by row and field; nothing changes.
3. Execute under the chosen failure policy; act on rejected rows without redoing applied ones.
4. Export a chosen, stated scope.

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
  **J12.4 `pg_trgm` missing**: each refused with its instruction.
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

## Guardrails kept from 0.7

In J10, clear is offered only where empty is valid. Search continues beyond page one; large ambiguous
sets expose counts and continuation. Keeping a selected existing target preserves its relationship
identity and attributes. Mapping and change-set-version conflicts retain the attempted choice for
review. When changing a change set's model (J18), the full candidate must already fit; failure changes
nothing. Success reloads model-dependent views, forms and lookups, resets obsolete cursors and
recovers removed routes without silently discarding dirty input. Older pinned releases remain usable
and are labelled neutrally. See SC-07, SC-15 and [the 0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md).
