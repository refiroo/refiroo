# Real-world RDM product research

**Reviewed:** 2026-09-07

**Status:** Research input only. Nothing in this document changes the accepted product definition,
roadmap, implementation plan, interaction specification or functionality catalogue. Candidate
conclusions below require an explicit product discussion and approved merge.

**Purpose:** Check the RDM Engine product definition against established reference-data and adjacent
master-data products, then use the recurring user jobs to challenge this repository's capability and
roadmap assumptions.

This is a product benchmark, not a request to copy another product's architecture or enterprise scope.
Only first-party product documentation was used. Vendor terminology is translated into the language of
RDM Engine.

## Products and evidence reviewed

### Ataccama Reference Data Manager

Ataccama describes reference-data work as browsing, changing, creating and deleting records, with
validation and approval workflow around governed changes. Its validation material covers both
individual values and rules across fields in one record.

Product implications:

- A record detail that cannot edit mutable fields is not a minimally usable daily-stewardship product.
- Validation belongs in the editing loop and must point to the affected value or record rule.
- Approval is a governance option layered over change, not a substitute for the ability to author it.

Sources: [Ataccama RDM overview](https://docs.ataccama.com/rdm/14.5.x/overview.html),
[Ataccama RDM features](https://docs.ataccama.com/rdm/13.9.x/product-overview/features.html).

### Semarchy xDM

Semarchy's model-driven authoring examples generate forms, collections, search and actions from a
logical model. Its documented data actions include create, edit, mass update, copy, delete, import and
export. It separately provides collaborative workflows for proposing, reviewing, correcting and
approving changes.

Product implications:

- Model-driven generation is valuable only when it produces complete authoring actions, not read-only
  metadata screens.
- Search, forms and collections are one connected stewardship experience.
- Bulk edit and spreadsheet exchange are common operational needs, but can follow a complete
  single-record flow.
- Optional collaborative workflow should not be confused with routine direct editing.

Sources: [Semarchy data-authoring application tutorial](https://semarchy.com/tutorials-content/build-your-first-data-authoring-app/),
[Semarchy guided data authoring](https://www.semarchy.com/tutorials-content/guided-data-authoring/),
[Semarchy workflow tutorial](https://www.semarchy.com/tutorials-content/create-your-first-workflow/).

### Informatica Reference 360

Reference 360 treats code lists, code values, crosswalks/value mappings and hierarchies as first-class
reference-data concepts. It supports CSV import with preview and field mapping, export, history for
values/mappings/hierarchy changes, and approval tasks that compare versions and allow approve, reject
or send back.

Product implications:

- A mapping is a dedicated stewardship task, not merely a generic relationship record.
- Hierarchy change and mapping change both need their own understandable history.
- Import must include preview, field mapping and row-level outcomes rather than being a blind upload.
- Reviewers need a change comparison and an explicit decision; approval cannot be credible without
  identity, roles and actor audit.

Sources: [Reference 360 import](https://docs.informatica.com/master-data-management-cloud/reference-360/current-version/reference-360/import-data.html),
[import file preview and settings](https://docs.informatica.com/master-data-management-cloud/reference-360-saas/current-version/reference-360/import_data/import_process/step_1_upload_a_file.html),
[crosswalk history API](https://docs.informatica.com/master-data-management-cloud/reference-360-saas/current-version/reference-360/reference-360-rest-api/crosswalks/get-history-of-a-crosswalk-by-time-range.html),
[hierarchy history API](https://docs.informatica.com/master-data-management-cloud/reference-360-saas/current-version/reference-360/reference-360-rest-api/codelists-version-2/get-history-of-code-value-hierarchies-by-time-range--v2-.html),
[approval task review](https://docs.informatica.com/master-data-management-cloud/reference-360-saas/current-version/reference-360/manage_workflows/reviewing_tasks.html).

### Oracle Enterprise Data Management

Oracle presents list and hierarchy viewpoints as editable working surfaces. Users can add, move,
reorder, remove and delete nodes, propose grouped changes through requests, compare viewpoints,
validate them and export results. Its task catalogue separates browse, manage, compare, validate,
synchronize, import and export responsibilities.

Product implications:

- Hierarchy usability needs direct add/move/remove operations and must not stop at a tree-shaped read
  view.
- Comparing a candidate with current content is a normal review task for coordinated changes.
- Different views of the same governed data should preserve context and make their purpose clear.
- Full, filtered and incremental extracts are distinct integration needs.

Sources: [getting started with data management](https://docs.oracle.com/en/cloud/saas/enterprise-data-management-cloud/dmcaa/get_started_data_mgmnt_100x263fd7c9.html),
[data-management user tasks](https://docs.oracle.com/en/cloud/saas/enterprise-data-management-cloud/dmcaa/get_started_dm_user_tasks_100x28368ba9.html),
[working with extracts](https://docs.oracle.com/en/cloud/saas/enterprise-data-management-cloud/dmcaa/viewpoint_extract_working_with_102x5701b82d.html),
[administration and use task index](https://docs.oracle.com/en/cloud/saas/enterprise-data-management-cloud/admin_use.html).

### TIBCO EBX

EBX combines model-defined datasets, record authoring, hierarchy management, validation, versioned
working areas, history, data services, permissions and collaborative workflows. Its history is
available from record, table and dataset contexts. It also treats localized labels, messages and
locale-aware value formatting as product concerns.

Product implications:

- Audit must be reachable from the user's working context, not only exposed as raw events.
- Working areas and workflow are useful governance layers, but permissions determine whether content
  is hidden, readable or writable.
- API behavior and browser behavior must enforce the same permissions and validation.
- Localizing reference-data content and localizing the product/model labels are separate capabilities.

Sources: [EBX history](https://docs.tibco.com/pub/ebx/6.0.6/doc/html/en/references/history.html),
[EBX permissions](https://docs.tibco.com/pub/ebx/6.1.0/doc/html/en/references/permissions.html),
[EBX data workflows](https://docs.tibco.com/pub/ebx/6.1.2/doc/html/en/user_dataworkflow/userdataworkflow_intro.html),
[EBX internationalization](https://docs.tibco.com/pub/ebx/5.9.18/doc/html/en/references/i18n.html),
[EBX REST services](https://docs.tibco.com/pub/ebx/6.0.6/doc/html/en/data_services/dataservices_rest_v1.html).

## Recurring real-world user jobs

Across the reviewed products, the recurring jobs are:

1. Browse and search known governed datasets.
2. Open a record and edit every permitted field in context.
3. Create and delete records with validation and understandable impact.
4. Add, move, remove and inspect hierarchy nodes.
5. Maintain crosswalks or mappings between code sets.
6. See field, record, mapping and hierarchy history with actor and time.
7. Validate proposed data before accepting it.
8. Import and export data with preview, mapping and explicit outcomes.
9. Propose, compare, review, approve, reject or return governed changes where policy requires it.
10. Restrict browse, edit, approval and administration through authenticated roles.
11. Consume equivalent governed data through supported APIs.
12. Work with localized content and, in mature deployments, localized product/model labels.

## Candidate conclusions for later product discussion

### Foundational product behavior

The reviewed products suggest treating the following as a coherent daily-stewardship baseline. This is
a research hypothesis to compare with RDM Engine's intended product, not an accepted release scope:

- select a workspace and retain it through every screen and request;
- browse, search, filter, sort and page records;
- open a record and edit all model-declared mutable core fields and attributes;
- create and delete live records with clear validation and impact confirmation;
- choose and change valid parents through the record flow;
- maintain ordinary relationships and basic translations;
- preserve typed values and reject invalid configurations or data with actionable messages;
- prevent silent overwrite and retain entered values during conflict recovery;
- show record and relationship history in context; and
- expose equivalent bounded APIs using stable public identities.

One candidate conclusion is that unconditional `readOnly` detail wiring and loss of non-default
workspace context should be discussed as possible Base 0.6 release blockers rather than accepted as
intended product behavior.

### Specialist workflows

These are standard RDM capabilities, but they can follow the complete generic foundation:

- mapping coverage, ambiguity resolution and atomic replacement;
- translation coverage by target and language;
- lazy, keyboard-operable hierarchy browsing and reparenting; and
- localized model labels and locale-aware formatting.

The present RDM Engine roadmap sequences mapping in 0.7 and translation/hierarchy specialization in
0.8. A later merge discussion should test whether that sequence assumes basic relationships,
translations and parent editing are already usable in 0.6.

### Integration workflows

Import/export and bulk maintenance are common operational expectations. Deferring them from 0.6 is
reasonable for a pre-production release, provided 0.9 remains a committed integration milestone and
does not implement “bulk” as client repetition of single-record calls.

The minimum credible import flow is upload, format review, field mapping, validation preview, explicit
row outcomes and resumable execution. Export must distinguish bounded interactive reads from full,
filtered or incremental extraction.

### Governed review and production controls

Approval workflow is common in mature RDM products, but it depends on identity, roles, assignments and
actor audit. A later product discussion can decide whether optional policy-driven review belongs after
OIDC and authorization, and whether it applies to coordinated designs, bulk imports or neither. A
candidate minimum flow is submit, compare, claim, approve/reject/send back with comments, notify and
audit.

Routine live editing remains the default where policy permits. A later approval policy may require a
design path for selected workspaces or operations, but must do so explicitly rather than making every
deployment ceremonial.

## What the benchmark does not require this product to copy

The reviewed suites include much broader MDM and governance functionality. RDM Engine does not need
matching, deduplication, survivorship, enrichment marketplaces, data-catalogue scanning, business
glossaries or a general BPMN designer to deliver its stated reference-data product.

The benchmark suggests the following sequence for discussion; it is not merged into the roadmap:

1. complete direct daily stewardship;
2. complete optional coordinated design and release validation;
3. add specialist mapping, translation and hierarchy experiences;
4. add first-class integration exchange;
5. add authenticated governance and production hardening; and
6. add structured self-service model authoring.
