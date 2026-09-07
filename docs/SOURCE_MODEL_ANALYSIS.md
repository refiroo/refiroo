# Source model analysis

## Scope

The supplied `Reference Data Management` package is approximately 155 KB and declares:

| Concept | Count |
| --- | ---: |
| Applications | 3 |
| Object types | 23 |
| Attribute types | 27 |
| Relation types | 72 |
| Allowed object-type relations | 55 |
| User relation types | 2 |
| Translation keys | 93 |

The three configured applications are RDM Master, RDM Systems and RDM Translations. Together they
demonstrate that an application is primarily a grouping, entry point and presentation definition over
shared model concepts.

## Concepts worth retaining

### Applications are configuration

Applications select object types, a default object type, hierarchy behavior, search, settings and
templates. This is central to RDM Engine: additional applications must be possible without application-
specific backend code.

### Attributes are reusable definitions

Attribute types are declared globally and attached to object types. The source model contains string,
boolean, integer and date values. RDM Engine schema 0.2 keeps the same useful separation: reusable
attribute types are global definitions, while object-type bindings add context such as required,
read-only and UI overrides.

### Relations carry domain meaning

Relation types have forward and reverse identities, orientation and behavioral features. Allowed
source/relation/target triples constrain their use. RDM Engine retains typed first-class edges and
makes cardinality explicit.

The supplied relation-type API response declares 201 relation types; the captured excerpt contains 20
complete entries. Each entry confirms a stable key, forward and reverse names, orientation and typed
features. These are represented independently from the 55 RDM-specific allowed object-type triples in
the application package. Source numeric IDs remain import concerns and are not public engine keys.

### Structure and presentation are both modelled

Object templates describe panels and elements for attributes, relations, labels and tables. The source
contains 77 panels, 27 API tables, 24 attribute sections, 17 code-table selectors and 15 relation
tables. This provides strong evidence that the UI must be model-driven.

### Hierarchy is a relation pattern

Parent/child behavior is represented through relation features and object constraints. RDM Engine
should treat hierarchy as a generic relation capability with explicit cycle and depth rules rather than
a separate hardcoded RDM object family.

## Areas to redesign

### Presentation is too closely coupled to backend implementation

Source templates embed an API path (`api/mr-object/customizable-overview-filter`) and backend-oriented
column expressions such as `toGrandParentObjectName`. RDM Engine views reference object-type,
attribute and relation keys instead. Components resolve traversal declaratively and use stable public
APIs.

### UI elements describe mechanics rather than user tasks

Elements such as `codetable-label` and relation tables expose implementation structure. The new UI
model should offer task-level components: mapping grid, translation matrix, hierarchy browser, lookup
with create-new, and bulk editor.

### Behavioral flags need typed semantics

Features such as `not_creatable_in_root`, `create_without_concept`, `is_single_value` and
`is_creatable_on_child_add` are useful but loosely structured. RDM Engine replaces them with typed
behavior and cardinality properties that can be validated and documented.

### API scale must be independent of the UI

The source package uses one customizable overview endpoint throughout its tables. RDM Engine separates
UI views from integration contracts and standardizes cursor pagination, bulk operations, streaming
exports, change feeds and webhooks. No internal implementation should rely on a fixed `take` value to
obtain a complete collection.

### Model and content versions must be distinct

The new design separates model-language version, model release, workspace content revision and
draft-record version. This is needed for safe schema migration, coherent publication, optimistic
concurrency and reproducible integrations.

## Clean implementation boundary

The source file remains discovery material and is not distributed with the project. The starter model
is a manually authored, product-owned representation of the general concepts. No source API endpoint,
vendor core key, schema URL, visual design or proprietary runtime assumption is required by the engine.

## Immediate implications

The current implementation proves applications, tabs, tables, typed forms, CRUD and one parent-child
relation flow from the independent model. The next slice should prove a mapping workflow using the
`system-value-maps-to-master` relation, including unmapped filtering and safe remapping. That is the
next meaningful test of the model before expanding all 23 source object types.
