# Application model specification

## Design

The schema mirrors a generic object–attribute–relation engine while remaining independently named and
typed. Metadata definitions are reusable; bindings state where they may be used; applications and views
control presentation.

## Top-level structure

```json
{
  "schemaVersion": "0.7",
  "release": {},
  "product": {},
  "attributeTypes": [],
  "objectTypes": [],
  "relationTypes": [],
  "objectTypeRelations": [],
  "applications": []
}
```

Unknown top-level properties are rejected. Stable definitions currently allow extension properties so
new ideas can be tested before being promoted into the typed schema.

## Attribute types

An attribute type is global and reusable. It defines a stable key, label, value type, default, features,
validation and optional UI hints. The current schema supports `text`, `longText`, `integer`, `decimal`, `boolean`,
`date`, `dateTime` and `json`.

Features are typed JSON values. For example:

```json
{
  "key": "active",
  "name": "Active",
  "valueType": "boolean",
  "default": true,
  "features": { "filterable": true }
}
```

Attribute-type features control engine behavior. `unique: true` enforces workspace-scoped uniqueness
for the value at create and update (HTTP `409 duplicate_attribute_value`); it is not supported for
`json` values and is rejected at model load. `searchable` includes the attribute in object search.
`filterable` enables the schema 0.5 daily-use filter grammar for non-JSON attributes; table views
select the subset exposed as filter controls, and the API validates the capability from the attribute
definition itself. Every non-JSON attribute sorts, whatever its `sortable` flag: every data column of
a list sorts from its header (Base 0.8 S4R3 revision). `sortable` is still accepted and no longer
changes behavior.
`validation.minimum` and `validation.maximum` are numeric bounds and apply only to `integer` and
`decimal` value types. Bounds must be finite numbers, and `minimum` cannot exceed `maximum`; invalid
bounds or bounds declared on another value type are rejected at model load.

## Object types and attribute bindings

An object type defines its stable key, labels, display attribute, features and behavior. Its
`attributes` array binds global attribute types and supplies object-specific required, read-only, order
and UI properties.

This separation permits one `description` definition to be reused while allowing it to be mandatory in
one object type and optional in another.

Schema 0.4 adds object-level `validation.atLeastOneOf`. It contains attached attribute keys and requires
at least one of them to hold a non-empty value across object creation, partial updates and individual
attribute deletion. The starter Translation uses it for `translated-name`, `translated-description`
and `translated-value`.

## Relation types

A relation type defines forward and reverse keys and names, orientation and typed features. It does not
itself decide which object types may participate.

`objectTypeRelations` declares allowed triples:

```json
{
  "relationTypeKey": "system-value-maps-to-master",
  "fromObjectTypeKey": "system-value",
  "toObjectTypeKey": "master-value",
  "cardinality": "many-to-many"
}
```

This is deliberately separate because one reusable relation type can be permitted between several
object-type pairs.

An allowed triple's `attributeTypeKeys` enumerates the global attribute types that relation instances
may store. Relation create and update reject undeclared keys and validate each supplied value using its
declared type and numeric bounds before persistence. An empty list therefore means the relation carries
no instance attributes rather than accepting arbitrary JSON.

In the live and optional change-set deletion contract, a directed non-parent binding with `required: true` and `one-to-one` or
`one-to-many` cardinality represents PK→FK ownership: the `from` object is the owner and the `to`
object is its dependent. An explicitly confirmed cascade from the owner deletes the dependent. An
optional binding or a `many-to-many` binding is an association; cascade removes the relation instance
but preserves the object at the other endpoint. Parent containment remains governed by
`parentObjectId` and always cascades from parent to descendants when cascade deletion is confirmed.
The same ownership rules apply live or within an explicitly selected change set. Live deletion is immediate;
change set deletion changes only the candidate until publishing. Publications remain immutable in
both cases (ADR-026/027).

## Relation patterns

Relation types follow three patterns, distinguished by their features:

### Containment (`parentOf: true`, `creatableOnChildAdd: true`)

Parent-child ownership. The parent "contains" the child; the reverse direction means "belongs to".
Always one-to-many. When the child object type names the relation in
`behavior.parentRelationTypeKeys`, creating an object with a `parentObjectId` writes the containment
relation atomically alongside the parent foreign key. `creatableOnChildAdd` records the intended
interaction semantics; creation controls are currently configured by child/table panels.

Examples from the starter model:

| Relation key | From | To |
|---|---|---|
| `domain-contains-codelist` | domain | codelist |
| `codelist-contains-value` | codelist | master-value |
| `system-contains-group` | system | system-group |
| `system-contains-value` | system | system-value |
| `system-group-contains-value` | system-group | system-value |
| `language-contains-group` | language | translation-group |
| `translation-group-contains-translation` | translation-group | translation |

### Hierarchy / self-reference (`parentOf: true`, `hierarchical: true`)

The same object type appears on both sides, enabling arbitrary-depth nesting within a single type.
Also one-to-many. The child object's `behavior.parentRelationTypeKeys` binding makes the engine create
the relation atomically on child creation. `hierarchical` records the relation semantics; tree and
hierarchy presentation are configured separately through views and panels.

| Relation key | Object type |
|---|---|
| `master-value-has-child` | master-value |
| `system-group-has-child` | system-group |
| `translation-group-has-child` | translation-group |

### Cross-reference / mapping (no `parentOf`)

Links between independent object types. These are business-level associations, not
parent-child ownership, and are created explicitly through the relations API. `searchable` records
intended discovery semantics; current object search covers names and searchable attributes, not
relation expansion. Optional cross-reference relations are fully mutable through relation CRUD.
Required relations can be created atomically with their dependent object and cannot be independently
deleted because that would leave the object invalid.

| Relation key | From | To |
|---|---|---|
| `reference-has-system-representation` | domain or codelist | system-value |
| `system-value-maps-to-master` | system-value | master-value |
| `object-has-translation` | domain, codelist or master-value | translation |

`reference-has-system-representation` is an optional one-to-many association. A Domain or Codelist
may have multiple System Value representations, while each represented System Value belongs to at
most one Domain or Codelist through this relation type. It does not change the System Value's parent:
System and System Group containment remains the separate system hierarchy. Because the association is
optional rather than an ownership binding, cascade deletion of the Domain or Codelist removes the edge
but preserves the System Value. Association edits are live by default; explicitly change-set-scoped edits
remain staged until activation. The system containment hierarchy is independent in both contexts.

`object-has-translation` is a required one-to-many ownership binding. Its shared relation type ensures
that a Translation has exactly one target across all permitted target types. Each binding declares
`uniqueToAncestorTypeKey: language` together with an `active == true` target-attribute condition,
preventing multiple business-active Translations for the same object and Language while allowing
business-inactive current content. The rule is enforced for live changes and effective change set content,
then checked across the merged graph during publishing. Historical publications do not reserve the
current scope. Future
translatable object types are enabled by adding another explicit allowed triple to the JSON model.

### Feature flags summary

| Feature | Effect |
|---|---|
| `parentOf` | Declares parent/containment semantics; atomic maintenance is bound by `behavior.parentRelationTypeKeys` |
| `creatableOnChildAdd` | Declares that adding a child is meaningful; current controls come from panel configuration |
| `hierarchical` | Declares recursive hierarchy semantics; tree presentation remains view-configured |
| `searchable` | Reserved relation-discovery hint; relation-expanded search is not implemented yet |
| `uniqueToAncestorTypeKey` | Makes a relation unique per source object and the target object's named containment ancestor |
| `uniqueWhenToAttributeEquals` | Applies scoped relation uniqueness only when the target attribute equals the configured value |

## Hierarchy

An object type may declare `behavior.parentRelationTypeKeys`. When an object is created with a parent,
the engine uses the parent and child object types to select exactly one allowed relation. It writes both
the parent ID and typed relation atomically. Self-relations support arbitrary-depth groups and values.

Relations named in an object type's `behavior.parentRelationTypeKeys` — the containment and hierarchy
relations above — are engine-maintained. The relations API returns them on reads but rejects direct
creation, update or deletion with `422 immutable_relation`, so `parent_object_id` and the typed
relation cannot diverge. Reparenting updates both representations atomically in live or explicit change set
context; activation revalidates staged changes with current live content (ADR-026/027).

## Applications and views

An application selects object types and exposes model-defined views. Object types may be shared across
applications. Applications use immutable keys; names are presentation labels and are not API filters.

Every view type is available to every application. Validation checks a view against its type's
contract and the structure it names (object types, relations, containment, attributes), never against
the application that declares it. Two applications differ only in what their declarations say. The
example model's applications declare different view sets as a demonstration, not as a rule
([EXAMPLE_MODEL.md](EXAMPLE_MODEL.md)).

ADR-029 distinguishes a declaration from its navigation placement. In schema 0.5–0.7, the frontend
groups views by their source object type and presents them as lenses of one contextual collection:

- `table.objectTypeKey` is the source type;
- an outgoing `mappingGrid` uses `fromObjectTypeKey`;
- an incoming `mappingGrid` uses `toObjectTypeKey`;
- a `relationMatrix` uses `rowObjectTypeKey`;
- a `tree` uses its first `rootObjectTypeKeys` entry.

This is a backwards-compatible presentation rule, not a new model field. It lets an arbitrary
application expose several configured tasks for one collection without multiplying primary navigation.
The engine does not infer a translation, mapping or other domain workflow from keys. A genuinely new
interaction still requires a typed generic view contract and renderer. Explicit collection/lens
composition is deferred until real models show that source-type grouping is insufficient.

Schema 0.5 supports the strict `table` contract. Schema 0.6 adds the `mappingGrid` contract for
mapping coverage views, and schema 0.7 the `relationMatrix` and `tree` contracts. Each view type has an extra-forbidden configuration that rejects unknown
properties. Configuration refers to stable object, attribute and relation keys—never backend URLs or
database IDs.

### Table view (`type: "table"`)

Requires non-empty unique `columns`, `filterFields`, `sortFields`, a `defaultSort` selected from the
declared sort fields and a `pageSize` from 1 to 100. Every column sorts regardless of `sortFields`;
the declared fields add further fields (such as ones without a column) to the list's Sort menu. A sort
field is a built-in (`id`, `name`, `objectType`, live timestamps) or a non-JSON attribute of the type.

### Mapping grid view (`type: "mappingGrid"`, schema 0.6)

A mapping grid displays coverage for a configured relation binding and supports atomic mapping
replacement. Configuration:

```json
{
  "key": "system-to-master-mapping",
  "name": "System → Master mapping",
  "type": "mappingGrid",
  "config": {
    "relationTypeKey": "system-value-maps-to-master",
    "fromObjectTypeKey": "system-value",
    "toObjectTypeKey": "master-value",
    "direction": "outgoing",
    "sourceColumns": ["name", "value-code", "value-name"],
    "targetDisplayColumns": ["name", "value-code", "value-name"],
    "candidateSearchFields": ["name", "value-code", "value-name"],
    "pageSize": 20
  }
}
```

| Field | Description |
| --- | --- |
| `relationTypeKey` | Must reference a declared relation type |
| `fromObjectTypeKey` | Must match a declared `objectTypeRelations` triple with the relation type |
| `toObjectTypeKey` | Must match the same triple |
| `direction` | `outgoing` or `incoming` — determines which side is the source (grid rows) |
| `sourceColumns` | Built-in or attached fields on the source object type; must be non-empty and unique |
| `targetDisplayColumns` | Built-in or attached fields on the target object type; must be non-empty and unique |
| `candidateSearchFields` | `name` or searchable attached attributes on the target type; must be non-empty and unique |
| `pageSize` | 1–100 |

The mapping coverage query may additionally apply a browser-selected direct-parent scope and one of
the semantic coverage states (`mapped`, `unmapped`, `ambiguous`). These are runtime query values, not
model configuration. They are valid only for a configured mapping view and are included in cursor
binding.

Validation rejects containment relations (`parentOf: true`) and required-ownership bindings
(`required: true` with `one-to-one` or `one-to-many` cardinality), since mapping replacement is
designed for voluntary association relations.

### Relation matrix view (`type: "relationMatrix"`, schema 0.7)

A relation matrix lists the records of one type as rows and the records of an ancestor type as
columns. A cell holds the row's related records, through one declared binding, that sit under the
column's record at any depth. The same contract serves values by language (a required, uniquely
scoped translation per cell), codelists by system (an optional representation) and master values by
system (a many-to-many mapping read from its target end); a catalogue's prices per market or
listings per channel are the same shape. Configuration:

```json
{
  "key": "master-values-by-system",
  "name": "Master values by system",
  "type": "relationMatrix",
  "config": {
    "relationTypeKey": "system-value-maps-to-master",
    "direction": "incoming",
    "rowObjectTypeKey": "master-value",
    "columnObjectTypeKey": "system",
    "cellObjectTypeKey": "system-value",
    "rowColumns": ["name", "value-code", "ancestor:codelist"],
    "columnLabelField": "system-code",
    "cellFields": ["value-code", "value-name", "active"],
    "searchFields": ["name", "value-code", "value-name"],
    "cellActions": ["edit", "link", "unlink"],
    "pageSize": 20
  }
}
```

| Field | Description |
| --- | --- |
| `relationTypeKey` | A non-containment relation type with a binding declared in `objectTypeRelations` between the row and cell types in the configured direction; required or optional, any cardinality |
| `direction` | `outgoing` when the row is the binding's `from` end, `incoming` when it is the `to` end |
| `rowObjectTypeKey` | The rows' object type; must belong to the application |
| `columnObjectTypeKey` | The columns' object type; must belong to the application and be able to contain the cell type at some depth through `parentRelationTypeKeys` |
| `cellObjectTypeKey` | The related records' object type; must belong to the application |
| `rowColumns` | Built-in, attached or `ancestor:<type>` fields of the row type; non-empty and unique |
| `columnLabelField` | `name` or a non-JSON attribute attached to the column type; labels the column headers |
| `cellFields` | Attributes attached to the cell type, shown and edited in a cell; non-empty and unique |
| `searchFields` | `name` or searchable attributes attached to the row type; non-empty and unique |
| `cellActions` | Optional, unique, from `create`, `edit`, `link`, `unlink`; absent or empty is read-only |
| `pageSize` | 1–100 |

A cell action is refused at `…/config/cellActions/<n>` when it could never succeed for the model:

- `edit` when every `cellFields` entry is read-only;
- `unlink` when the binding is `required`, because a required relation cannot be removed on its own;
- `create` when a required cell attribute without a default is not among `cellFields`, or when the
  cell type requires another relation besides the view's own (a cell record is created with its
  `cellFields`, its container and that one relation).

Every other failing rule points at the config field it concerns (`…/config/cellFields/1` for one
entry). Uniqueness is not configured on the view: when the binding declares
`uniqueToAncestorTypeKey` and `uniqueWhenToAttributeEquals`, writes already enforce them and the
matrix reports cells that break them. A cell record's column is its nearest ancestor of the column
type. The rows are every record of the row type in the workspace context, including records another
application owns. The binding's condition and uniqueness scope describe its `to` end, so a matrix
read `incoming` applies neither. Base 0.8 A2 delivers the
[query](API.md#product-08-relation-matrix-api-a2-and-a3-delivered), A3 the cell writes and A4 the
browser lens: a grid of the rows by the column records, each cell's state with an icon and a label,
a Filter popover for the columns shown and a cell state, and a cell dialog offering only the view's
`cellActions`.

### Tree view (`type: "tree"`, schema 0.7)

A tree shows a containment hierarchy: records of its root types that have no parent, and beneath each
record its children of the node types the tree shows, one branch list per child type. The same
contract serves a recursive self-hierarchy with values beneath it (systems and system groups), a chain
of different types (domains, codelists, master values) and a catalogue's category tree.
Configuration:

```json
{
  "key": "system-hierarchy",
  "name": "System hierarchy",
  "type": "tree",
  "config": {
    "rootObjectTypeKeys": ["system"],
    "objectTypeKeys": ["system", "system-group", "system-value"],
    "labelField": "name",
    "secondaryField": "objectType",
    "childSort": { "system": "system-code", "system-value": "value-code" },
    "pageSize": 50,
    "actions": ["createChild", "rename", "move", "setAvailability"],
    "availabilityField": "active"
  }
}
```

| Field | Description |
| --- | --- |
| `rootObjectTypeKeys` | Non-empty and unique; each is one of `objectTypeKeys` and `rootCreatable`, so its records can stand without a parent |
| `objectTypeKeys` | The node types shown; non-empty and unique, each belonging to the application and reachable from a root type through `parentRelationTypeKeys` of types the tree shows |
| `labelField` | `name` or a non-JSON attribute attached to every node type |
| `secondaryField` | Optional; a built-in field (`id`, `name`, `path`, `objectType`, timestamps) or a non-JSON attribute attached to every node type |
| `childSort` | Optional map from a node type to a list `sort` value for its branches: `id`, `name`, `createdAt`, `updatedAt` or a non-JSON attribute of that type, `-` for descending. A type without an entry sorts by name (D22) |
| `pageSize` | 1–100; the branch fetch size |
| `actions` | Optional, unique, from `createChild`, `rename`, `move`, `setAvailability`; absent or empty is read-only |
| `availabilityField` | A boolean attribute attached to every node type; required by, and only allowed with, `setAvailability` |

The browser renders a tree as a lens beside the selected record (Base 0.8 B3): branches load by
parent and child type in the `childSort` order, a record found by search or open beside the tree is
revealed by seeking each branch on its path, and the `actions` are offered from a node's menu, with
F2 to rename. `createChild` offers each type the node can contain among the tree's node types; `move`
lists the records of every type that can contain the node (`GET …/parent-candidates`), ineligible
ones disabled with their reason. `childSort` fields recorded only in live data (`createdAt`,
`updatedAt`) sort by name in a change set or publication, where they are not recorded.

An action is refused at `…/config/actions/<n>` when it could never succeed for the model:

- `createChild` and `move` when no node type can contain another;
- `rename` when `labelField` is an attribute that is read-only on a node type (renaming a `name`
  label edits the name);
- `setAvailability` without `availabilityField`, or when that field is read-only on a node type.

Every other failing rule points at the config field it concerns (`…/config/objectTypeKeys/2` for an
unreachable node type, `…/config/childSort/<type>` for one sort). The sortable built-ins and
attributes are exactly those a list sorts by; an attribute's `sortable` flag is not consulted (D24).
Base 0.8 B1 delivers the contract with a placeholder lens; B2 adds the move-target query and B3 the
tree lens with its actions.

### Planned 0.7 consumption of the frozen mapping-grid contract

WP-4 identifies `applicationKey`/`viewKey` under the effective live or change-set-pinned model to resolve
columns and candidate search fields; supplied binding keys must match. Incoming direction anchors rows
on the physical `to` type and searches candidates on the physical `from` type. This requires no new
schema fields. WP-4/WP-5 APIs are delivered; WP-5 preserves selected relation identities and validates direction-aware cardinality;
its one-selected-target operation does not redefine the underlying binding. WP-10B adds source/live
identity/version comparison for touched mutable sets at activation without extending schema 0.6. WP-8A/WP-8B add bounded
coverage and generic actions; WP-9 exercises an independent binding beyond the starter's two views of
one binding. Any required future schema extension is a separate conditional WP-10 model-contract slice.
The schema contract delivered in WP-2 remains frozen. See [0.7 plan](BASE_0_7_IMPLEMENTATION_PLAN.md)
and the planned mapping API in [API.md](API.md).

## Detail composition

Applications may declare one `details` entry per object type. Keeping detail composition on the
application allows a shared object type to have a different task-oriented presentation in different
applications without changing its data contract.

```json
{
  "objectTypeKey": "codelist",
  "breadcrumbs": {
    "showApplication": true,
    "showObjectType": true,
    "showAncestors": true
  },
  "header": {
    "titleField": "name",
    "subtitleField": "description",
    "showObjectType": true
  },
  "panels": [
    {
      "key": "values",
      "title": "Values",
      "type": "children",
      "region": "main",
      "order": 10,
      "visible": true,
      "config": {
        "objectTypeKeys": ["master-value"],
        "columns": ["name", "value-code", "active"],
        "pageSize": 20
      }
    }
  ]
}
```

Breadcrumb flags and header field references control object context. Panels are sorted by `order`
inside either the `main` or `side` region; `visible: false` removes a panel without a frontend change.
The supported panel types are:

- `attributes`: selected built-in or attached attribute fields;
- `children`: one or more object types that have a configured containment relation from the detail
  object;
- `relations`: related objects selected by relation keys and `incoming`, `outgoing` or `both`
  direction;
- `table`: an application object type, optionally filtered to direct children; and
- `hierarchy`: parent and ancestor context from the runtime object path.

Relation panels may set `showRelationshipColumn: false` when their configured relation and direction
make the relationship label constant and therefore redundant. Columns use built-in fields, attached
attribute keys, or `ancestor:<objectTypeKey>`. An ancestor column displays the named object's entry
from the related object's runtime path and derives its heading from that object type—for example,
`ancestor:system` renders a `System` column for System Values contained directly by a System or nested
under System Groups.

Schema 0.7 lets a relations panel declare its sort options, as a table view does:

```json
"config": {
  "relationTypeKeys": ["object-has-translation"],
  "direction": "outgoing",
  "columns": ["ancestor:language", "name", "translated-name", "active"],
  "sortFields": ["ancestor:language", "translated-name", "name"],
  "defaultSort": "ancestor:language"
}
```

Every data column of a relations panel sorts from its header, as does the Relationship label, with or
without these fields. `sortFields` (optional) adds fields to the panel's Sort menu; `defaultSort`
(optional, alone or with `sortFields`) chooses the initial order, otherwise name. Each field names the
related record and must be one the relation list API accepts: `name`, `objectType`, `relationship`, a
non-JSON attribute attached to at least one related type (records without it sort last), or
`ancestor:<objectTypeKey>` for a type the related type can sit under through its
`parentRelationTypeKeys`; an ancestor field needs the panel's relation types, direction and detail type
to allow exactly one related object type. `defaultSort` may be prefixed with `-` for descending.
`sortFields` must be non-empty and unique. A schema 0.5 or 0.6 model that declares either field is
refused at the field's path. Timestamps are not panel sort options: they are recorded live only (D22).

Every panel has a type-specific configuration. Unknown properties are rejected. Startup validation
also checks header and column fields, application membership, containment compatibility, relation
existence and direction, unique detail/panel keys and page-size bounds. Configuration contains only
stable model keys and presentation semantics; the React API adapter owns all backend routes.

## Schema 0.8 additions (Product 0.9)

Designed for [Base 0.9](BASE_0_9_IMPLEMENTATION_PLAN.md) (D7); the starter becomes content release
0.9.0 on schema 0.8. **Opened in Base 0.9 C1 (2026-09-30)** with `consumerApis`; `effectivePeriod`
follows in Q4, until which schema 0.8 accepts nothing else new. Schema 0.8 is a strict superset of 0.7, as each earlier step was: 0.5–0.7 models
keep parsing and activating, absent 0.8 fields are omitted from the canonical document so earlier
releases keep their content hash, and a 0.8 field in an older schema is refused at its path.

### Effective period (`effectivePeriod`)

An object type may declare one business validity period:

```json
{
  "key": "master-value",
  "effectivePeriod": {
    "startAttributeTypeKey": "valid-from",
    "endAttributeTypeKey": "valid-to"
  }
}
```

- Both keys name `date` attributes the type binds, and they differ. A `dateTime` period is refused
  until a real case needs one.
- The start is inclusive and the end exclusive; an empty start means "since always" and an empty end
  "open". Periods of different records may overlap.
- Writes, live and in a change set, refuse an end that is not after its start with
  `422 invalid_effective_period`; change-set validation and publishing report the same code as a
  diagnostic.
- Reads accept `asOf` on the types that declare a period ([INTEGRATION_API Q4](INTEGRATION_API.md#q4-effective-periods-and-asof)).
  The period is business validity: it is independent of record versions, change history and
  publications (SC-11).
- Adding or removing a declaration changes no stored data. Removing one makes `asOf` on that type
  `422 as_of_not_supported`; the consumer API's breaking-change check (package C1) counts that as a
  contract change for a definition that exposes the type.

### Consumer API definitions (`consumerApis`)

A new optional top-level array of read-only consumer API definitions. Their shape, validation and
contract rules are specified in [CONSUMER_API.md](CONSUMER_API.md#definition-shape); in summary:

- Each definition has a `key` (the `apiKey`), a `name` and its own `contractVersion`, and declares the
  exposed object types, output fields, projections, lists, XREF parameters and scoring, and events.
- A `projection` parameter may declare `"targetable": true`, which enables crosswalk reads
  (`to.{parameter}`). Only a `projection` parameter can be targetable.
- Every reference to a type, attribute, relation binding or ancestor is validated against the same
  release, with the model's path-and-reason errors.
- Each definition is compared with the **active** release's (C-D17): draft compile and release diff
  report the result as `consumerContracts`, and activation refuses a breaking change that does not
  raise `contractVersion` (C-D2): removing or retyping an output field, renaming or no longer exposing
  a type, changing a projection's shape or fields, changing scoring weights (C-D4), removing or changing
  a list or a parameter's kind (C-D18), or (from C9) removing or narrowing an event. Removing a whole
  definition is a warning. Installing a release without activating it is not checked.
- A field's sources share one value type (`text` and `longText` count as one), which is its output
  type (C-D19); an identity source is `id` or a `unique` attribute; a match rule or match field reads
  `name`, `id` or a `searchable` or `unique` attribute (C-D20).
- Definitions change no stored data and no management API behaviour.

### Upsert keys

Schema 0.8 adds no declaration for upsert keys. A batch or import upserts by public ID or by an
attribute already declared `unique` (D2); the uniqueness declaration is the key declaration.

## Versioning

`schemaVersion` versions the model language; the starter content release `0.8.0` uses schema `0.7`.
Schema 0.4 added object-level cross-field validation, required initial relationships and scoped
relationship uniqueness to the 0.3 detail-composition contract. Schema 0.5 adds strict typed table
views. Schema 0.6 adds the `mappingGrid` view type. Schema 0.7 adds relations-panel sort options
(`sortFields`, `defaultSort`) and the `relationMatrix` and `tree` view types. Schema 0.8 (Product
0.9) adds `consumerApis` (Base 0.9 C1) and `effectivePeriod` (Q4) ([above](#schema-08-additions-product-09)). `release.version` versions one model package.
Each distinct
validated model is installed as an immutable database release identified by its content hash.

Workspace snapshots, change sets and record versions are separate from model-language and model-release
versions. ADR-026/027 keep current data live and editable while coordinated publishing records
immutable history. Base 0.6 adds no configurable object publication states. The model declares rules
used for live writes, effective change sets and the final merged publishing graph; the runtime owns their
context, versions, lineage and atomicity.

A workspace change set does not edit definitions. Publications must be interpreted under their
pinned supported model (WP8.1 correction). Current-live change set bases must capture the selected model and
current record versions without pretending that the last publication contains recent live edits.
Historical schema replacement with reviewed potential loss is an explicit 0.11 migration and model
selection operation under ADR-027; it does not mutate an immutable model release or bypass validation.

ADR-021 reserves schema 0.5 for a strict `table` definition. Product 0.7 adds `mappingGrid` in
schema 0.6; a schema 0.5 model remains valid and activatable under schema 0.6 (the `mappingGrid` view
type is an addition, not a replacement). Product 0.8 adds schema 0.7, again a strict superset: schema
0.5 and 0.6 models keep parsing and activating, and features added in a later schema are refused at their
path. Absent 0.7 fields are omitted from the canonical document, so a 0.5 or 0.6 release keeps its
content hash. Stored schema 0.4 releases remain historical immutable JSON
but cannot be activated. `form` and `dashboard` view types remain unimplemented. A future
workspace-scoped release assignment may stage model and data migrations, but mixed schema-language
operation requires explicit support for every concurrently served version.

Development databases can reset and bootstrap the schema 0.7 starter. To preserve compatible runtime
data, stop traffic and run from `backend/`:

```bash
.venv/bin/python -m app.cli.model_schema_upgrade --model ../model/rdm-starter.json
```

When startup finds a database that still selects schema 0.4, it handles that known condition without
an exception traceback, marks the process unhealthy and logs a copy-pasteable version of this command
using the running interpreter and configured model path. The command must run in the same configured
environment so it targets the same `DATABASE_URL`; `/health` remains HTTP `503` until the transition
has succeeded and the API is restarted.

The command reads the selected schema 0.4 release without starting the request runtime, validates and
installs a supported schema 0.5, 0.6 or 0.7 candidate, runs the normal compatibility analysis and atomically
changes runtime state.
Any validation, compatibility or concurrency failure rolls the transaction back.
