# Application model specification

## Design

The schema mirrors a generic object–attribute–relation engine while remaining independently named and
typed. Metadata definitions are reusable; bindings state where they may be used; applications and views
control presentation.

## Top-level structure

```json
{
  "schemaVersion": "0.9",
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
for the value at create and update (HTTP `409 DUPLICATE_ATTRIBUTE_VALUE`), and the database holds
live values to it as well (ADR-010); it is not supported for `json` values and is rejected at model
load. `searchable` includes the attribute in object search.
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

`cardinality` says at which ends a record holds at most one relationship of the binding, counted by
relation type at that end: `one-to-one` both ends, `one-to-many` the `to` end (a `to` record has one
`from`), `many-to-one` the `from` end (a `from` record has one `to`, which may serve many), and
`many-to-many` neither. A write that would give such a record a second one is
`409 CARDINALITY_VIOLATION`. `many-to-one` needs schema 0.9 and cannot be `required`: `required` means
the `to` record is created with its relationship (Base 0.9 K3a, D136, D137).

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

### Which records a relationship may choose (schema 0.9, Base 0.9 K7)

A binding (an entry of `objectTypeRelations`) may limit which records may be chosen at its ends with
`candidates`: criteria for the records at the `from` end, the `to` end, or both. An end without
criteria takes any record, as before.

```json
{
  "relationTypeKey": "service-uses-slot",
  "fromObjectTypeKey": "service",
  "toObjectTypeKey": "slot",
  "cardinality": "many-to-one",
  "candidates": {
    "to": [{ "field": "ancestor:slot-group.name", "op": "contains", "value": "reserved" }],
    "from": [{ "field": "bookable", "op": "eq", "value": true }]
  }
}
```

Here a service may use only a slot under a slot group whose name contains "reserved" (any case),
and only a bookable service may use one.

**What a criterion may name** (D170):

| `field` | Compares | Example |
| --- | --- | --- |
| `name` | the record's name | `{"field": "name", "op": "startsWith", "value": "EU-"}` |
| an attribute key | any non-JSON attribute the end's type binds, filterable or not | `{"field": "bookable", "op": "eq", "value": true}` |
| `ancestor:<type>.name` | the name of an ancestor of that type, at any depth | `{"field": "ancestor:region.name", "op": "contains", "value": "north"}` |
| `ancestor:<type>.<attribute>` | an attribute of such an ancestor | `{"field": "ancestor:region.region-code", "op": "eq", "value": "N1"}` |

The operators are the list filter's for the field's value type: text takes `eq`, `contains` and
`startsWith` (the last two ignore case); numbers and dates `eq`, `lt`, `lte`, `gt` and `gte`; yes/no
`eq`; every field `isNull` (`true`: empty) and an attribute `isUnset` (`true`: no value held). Criteria
are combined with AND; several `eq` on one field are alternatives (`"code" eq "A"` and `"code" eq
"B"`: either). Criteria on one ancestor type are met by one ancestor, and any ancestor of that type
counts, so a type that nests matches at each of its levels. Validation refuses an unknown field, an
attribute the end's type does not bind, a JSON attribute, an ancestor type the end's type cannot sit
under, an operator the field's value type lacks, or a value of the wrong JSON type, at the
criterion's pointer (`/objectTypeRelations/<key>/<from>/<to>/candidates/to/0/field`).

**What it does** (D171–D177):

- Every place that offers records for the relationship offers only those that meet the criteria: the
  record picker of the relations panel, a new record's required relationship, Change relationships'
  Add, Replace with and Set to, the relationship view's and relation matrix's candidates, and the
  relationship filter's picker. Each says what it offers ("Offers only slots under a Slot group whose
  name contains “reserved”."). Remove lists what the records hold, whether it matches or not.
- A mapping grid lists as sources only the records meeting the criteria at its source end (coverage, its
  counts and filters, and the sources an AI proposal asks about), unless the record already holds the
  relationship, which stays listed and editable.
- A record that does not meet its own end is not offered the relationship on its panel; the info hint
  beside the panel's heading says why ("Only bookable services can have this relationship."); in Change relationships the preview
  refuses such records by name.
- The API lists the same candidates (`candidateFor` and `anchorTypeKey` on the per-type list) and
  refuses a new relationship that does not meet the criteria (`422 RELATION_CANDIDATE_REFUSED`), alone,
  in a batch, in an import row and as a set replacement's addition.
- A relationship made before stays when the data changes so it no longer meets the criteria (a
  renamed group, a changed flag, a moved record, a new release with criteria): it is not flagged,
  blocks neither validation nor publishing, and can be changed or removed as any other.
- Adding, changing or removing `candidates` in a release is compatible; installing checks no data.

Choosing the criteria is the model administrator's responsibility: a criterion on a name or a free
text attribute follows that text when it is changed. Where the data allows, a yes/no attribute set
for the purpose ("reserved") is the sturdier criterion.

## Hierarchy

An object type may declare `behavior.parentRelationTypeKeys`. When an object is created with a parent,
the engine uses the parent and child object types to select exactly one allowed relation. It writes both
the parent ID and typed relation atomically. Self-relations support arbitrary-depth groups and values.

Relations named in an object type's `behavior.parentRelationTypeKeys` — the containment and hierarchy
relations above — are engine-maintained. The relations API returns them on reads but rejects direct
creation, update or deletion with `422 IMMUTABLE_RELATION`, so `parent_object_id` and the typed
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
- a `relationTable` uses `fromObjectTypeKey`;
- a `tree` uses its first `rootObjectTypeKeys` entry.

This is a backwards-compatible presentation rule, not a new model field. It lets an arbitrary
application expose several configured tasks for one collection without multiplying primary navigation.
The engine does not infer a translation, mapping or other domain workflow from keys. A genuinely new
interaction still requires a typed generic view contract and renderer. Collections are never
declared one by one; from schema 0.10 an application may arrange them in navigation groups
([below](#navigation-groups-navigation-schema-010)).

Schema 0.5 supports the strict `table` contract. Schema 0.6 adds the `mappingGrid` contract for
mapping coverage views, and schema 0.7 the `relationMatrix` and `tree` contracts, and schema 0.10 the `relationTable` contract (0.13 RV). Each view type has an extra-forbidden configuration that rejects unknown
properties. Configuration refers to stable object, attribute and relation keys—never backend URLs or
database IDs.

### Navigation groups (`navigation`, schema 0.10)

An application may arrange its collections, and its relation matrices, in labelled, foldable sidebar
sections (0.10 N1, A-D2), and choose the view a collection opens on:

```json
"navigation": {
  "groups": [
    { "key": "lists", "label": "Lists", "collections": ["unit", { "view": "units-by-size" }, "size"],
      "collapsed": true }
  ],
  "opens": { "unit": "units-by-size" }
}
```

- `groups` lists the sections in the order the sidebar shows them, after the collections in no
  group, which keep their own order. Without `navigation` the sidebar is as in schema 0.9.
- A group has a `key` unique within its application, a `label`, its entries in `collections` in
  their one order, and `collapsed` (default `false`), the state a reader first sees; a reader's own
  fold is kept in their browser. A group may be empty.
- An entry of `collections` is a collection of the application (the source type of one of its views,
  by the rule above: a string) or a relation matrix view of the application (`{ "view": "<key>" }`).
  A matrix in a group is an entry of its own, named after the view, with a matrix glyph in its row
  type's hue, and opens the matrix directly; its row type's collection stays where it stands and the
  matrix stays among that collection's views. A matrix in no group stays a view of its row type's
  collection, as before.
- `opens` (optional) maps a collection key to a view of that collection: the view the collection's
  sidebar entry opens on, in place of the application's `defaultView` for that collection. It is
  left out when it names nothing.
- A group also opens as a page (`/apps/{app}/groups/{group}`) listing its entries, with a search
  over their names.
- Navigation is presentation only: it changes no API, data, record validation or permission, and a
  change to it is compatible. A model that does not use `{ "view": … }` or `opens` is unchanged, and
  keeps its content hash.

Validation, each refusal at its pointer under `/applications/{app}/navigation`: `navigation` in a
document below schema 0.10 (`INVALID_MODEL`); a group key twice (`DUPLICATE_KEY`, at the second
group); an entry that is no collection of the application (`INVALID_REFERENCE`, at
`…/groups/{group}/collections/{index}`); a `view` entry that is no relation matrix view of the
application (`INVALID_REFERENCE`, at `…/collections/{index}/view`); a collection or a matrix in a
second group (`INVALID_MODEL`, at its entry there); an `opens` key that is no collection of the
application, or whose view is not a view of that collection (`INVALID_REFERENCE`, at
`…/opens/{collection}`). A member a group or `navigation` does not define is refused by shape.

### Table view (`type: "table"`)

Requires non-empty unique `columns`, `filterFields`, `sortFields`, a `defaultSort` selected from the
declared sort fields and a `pageSize` from 1 to 100. Every column sorts regardless of `sortFields`;
the declared fields add further fields (such as ones without a column) to the list's Sort menu. A sort
field is a built-in (`id`, `name`, `objectType`, live timestamps) or a non-JSON attribute of the type.

**Inactive records (`availabilityField`, schema 0.10, 0.13 LB).** Optional: a boolean attribute attached
to the view's object type. Like a tree's `availabilityField` it names what makes a record available,
but a table only marks: a record whose value is exactly `false` keeps its row, its name in the
secondary ink with a neutral "Inactive" pill (the attribute's name in lower case after "Not" when it
is not called Active), and the toolbar offers a switch, "Hide inactive (N)", that applies the ordinary
filter `<field> ne false` (the records whose value is not false, so a record with no value stays, as the
table does not mark it), which the list query takes on any yes/no attribute (`docs/API.md`). N counts the
records the list's other search and filters leave with the field `false`, exactly those the switch hides. The switch's filter is a filter pill in the address like any other, and the field need
not be among `filterFields`. A record with no value, and a table without the field, show as before;
values stay editable as usual, the attribute may be read-only, and a change set or publication marks
its own values the same way. A field that is not an attribute of the type, or not boolean, is refused
at `…/config/availabilityField`; renaming the attribute's key follows it, and removing the attribute
or its binding takes the setting away, as for a tree. The model editor's table settings offer it as
**Inactive records…**, among the type's boolean attributes.

**Relation columns (schema 0.9, Base 0.9 K5).** A column `related:<key>` shows each row's related
records of one relationship as record chips in name order: as many as the column's width holds, then
"+N more" for the rest (Base 0.9 K5b). `<key>` is a
relation type's `key` (the listed type at the `from` end) or `reverseKey` (at the `to` end), and its
header is the relation's name in that direction. Every binding of that relation type with the listed
type at that end shows in the one column. A relation column may stand in a table view's `columns` and
in a children or table panel's `columns`; in a table view's `sortFields` and `defaultSort` only where
it is single-valued (one binding behind it, whose listed end holds at most one relationship), and
never in `filterFields`, a relations panel, a mapping grid, a relation matrix, a tree or a detail
header. An unknown key, a key the listed type is at neither end of, or a model below schema 0.9 is
refused at the field list's pointer.

```json
"columns": ["name", "value-code", "related:system-value-maps-to-master", "active"]
```

A table view's `filterFields` may name `related:<key>` (Base 0.9 K6): its Filter menu then offers
the relationship, to keep the records related to any of chosen records, to none, or to any. A filter
names the relationship alone; `related:<key>.<field>` is refused there, and a column showing a field
of the related records offers no filter.

A relation column may show a field of the related records instead of their name (Base 0.9 K5a):
`related:<key>.<field>`, the field written as in a consumer API definition: `name`, an attribute one
of the types at the other end binds, or `ancestor:<type>.<field>` (`name` or an attribute of an
ancestor type they can sit under). Its header is the relation's name and the field's label ("Has
translation · Language code"); each chip shows the record's value, "—" where it has none. Such a
column never sorts. An unknown field, an attribute no type at the other end binds, a JSON attribute
or an ancestor type they cannot sit under is refused at the field list's pointer. A key may contain a
dot: the text is the whole key when it is one, otherwise the longest key it starts with.

**How many relation columns a view may show (D142, revised in Base 0.9 K6a).** There is no fixed
number. The model bounds them: each `related:<key>` must name a relationship the listed type has, and
each column is named once. A type with nine relationships may show all nine, and a column per field
besides (`related:<key>` and `related:<key>.<field>` are two columns). What a column costs is one more
read of the related records for the rows on the page: the table asks for its page (20 rows by
default) and the first few related records of each row, so a view with many relation columns stays
cheap however many records the type has. A user who does not need a column hides it in Display, and
the table stops reading it (D146).

Choose the columns for the people reading the view rather than to save reads. For example, a type
with four many-to-many relationships, one many-to-one relationship and a translation could show:

```json
"columns": [
  "name", "code",
  "related:has-tag", "related:uses-component", "related:available-in-region",
  "related:sold-through-channel", "related:replaced-by",
  "related:has-translation.ancestor:language.language-code",
  "active"
]
```

The single-valued one (`replaced-by`) may also stand in `sortFields`; the others are listed in
name order in each cell, as many as the column's width holds. Measured once on a small data set (200
records, every one of a type's nine relationships expanded, 500 rows a page, 20 related records each:
2,682 related records, about 1 MB, 0.3–0.4 s), the largest read an integrator can ask for is bounded
by the page size and `expandLimit`, not by the number of columns.

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
| `sourceColumns` | Built-in, attached or `ancestor:<type>` fields of the source type, as a matrix's `rowColumns` are (`ancestor:<type>` reads the name of the record's nearest ancestor of that type); non-empty and unique. The coverage query searches the name and attached attributes among them, not an ancestor's name |
| `targetDisplayColumns` | Built-in or attached fields on the target object type; must be non-empty and unique |
| `candidateSearchFields` | `name` or searchable attached attributes on the target type; must be non-empty and unique |
| `pageSize` | 1–100 |

The mapping coverage query may additionally apply a browser-selected direct-parent scope and one of
the semantic coverage states (`mapped`, `unmapped`, `ambiguous`; `ambiguous` — two or more targets — exists only where the binding's cardinality lets a source hold at most one, otherwise several targets are `mapped`). These are runtime query values, not
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

### Relationships table view (`type: "relationTable"`, schema 0.10, 0.13 RV)

A relationships table lists one declared binding's relationships, one row each: both records'
columns, the relationship's own attributes (the binding's `attributeTypeKeys`) as columns, filters,
sorting and optional heading of the rows by their `from` or `to` record. It is a generic view: any
application may declare it over any non-containment binding.

```json
{
  "key": "system-value-mappings",
  "name": "System value mappings",
  "type": "relationTable",
  "config": {
    "relationTypeKey": "system-value-maps-to-master",
    "fromObjectTypeKey": "system-value",
    "toObjectTypeKey": "master-value",
    "fromColumns": ["name", "value-code"],
    "toColumns": ["name", "value-code"],
    "attributeColumns": [],
    "filterFields": ["from:active", "to:active"],
    "sortFields": ["from:name", "from:value-code", "to:name", "to:value-code"],
    "defaultSort": "from:name",
    "groupBy": "to",
    "pageSize": 20
  }
}
```

| Field | Description |
| --- | --- |
| `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey` | A binding declared in `objectTypeRelations`; the relation type is not a containment |
| `fromColumns`, `toColumns` | `name` or a scalar attribute attached to that end's type; non-empty, unique |
| `attributeColumns` | Attribute types the binding declares in `attributeTypeKeys`; may be empty; unique |
| `filterFields` | `from:<field>`, `to:<field>` (`name` or a scalar attribute of that end's type) or `relation:<attribute>`; an attribute must be `filterable`; unique; may be empty |
| `sortFields` | The same references; any non-JSON attribute; non-empty, unique |
| `defaultSort` | One of `sortFields`, `-` for descending |
| `groupBy` | `from`, `to` or absent: the rows stand under their record with the group's count; ignored in the grid layout |
| `layout` | `rows` (the default, one row per relationship) or `grid`: each `from` record once, a column group per related `to` record with the `attributeColumns` under it; the first `toColumns` field labels a group, `from:` sorts order the rows and `to:` filters select the column records; a grid also filters by the filter fields of each end type's main view (the table its collection opens with) without declaring them (0.13 RG) |
| `pageSize` | 1–100 |

Each failing reference is reported at its own pointer (`…/config/attributeColumns/0`,
`…/config/filterFields/1`). The rows are read from the workspace edge list with the view's
`applicationKey` and `viewKey` ([API](API.md#relationships-table-rows-and-batch-values-rv)), live, in a
change set and in a publication; the grid layout is read from `GET /workspaces/{key}/relation-grid`
([API](API.md#relationships-grid-rg)). `layout` is one more setting of the same view type: no schema bump.

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
is **delivered in Q4 (2026-09-30)**, and the starter is content release 0.9.0 on schema 0.8 with a
period on `master-value`. Schema 0.8 is a strict superset of 0.7, as each earlier step was: 0.5–0.7 models
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
  `422 INVALID_EFFECTIVE_PERIOD`; change-set validation and publishing report the same code as a
  diagnostic.
- Reads accept `asOf` on the types that declare a period ([INTEGRATION_API Q4](INTEGRATION_API.md#q4-effective-periods-and-asof)).
  The period is business validity: it is independent of record versions, change history and
  publications (SC-11).
- Adding or removing a declaration changes no stored data. Removing one makes `asOf` on that type
  `422 AS_OF_NOT_SUPPORTED`; the consumer API's breaking-change check (package C1) counts that as a
  contract change for a definition that exposes the type. Activating a release that declares a period (or moves
  one to other attributes) over live records whose end is not after their start is refused with
  their count (`INVALID_EFFECTIVE_PERIOD`, D20), as an added `atLeastOneOf` is.
- Validation refuses, at `/objectTypes/<type>/effectivePeriod`: the declaration in schema 0.7 or
  earlier, an attribute the type does not bind (`UNKNOWN_ATTRIBUTE_TYPE`), one that is not a `date`
  and the same attribute twice.

### Consumer API definitions (`consumerApis`)

Opened in schema 0.8 and written in schema 0.9's syntax since Base 0.9 C18 ([below](#schema-09-product-09)).

### Upsert keys
### Upsert keys

Schema 0.8 adds no declaration for upsert keys. A batch or import upserts by public ID or by an
attribute already declared `unique` (D2); the uniqueness declaration is the key declaration.

## Schema 0.9 (Product 0.9)

Schema 0.9 is the schema language released with 0.9.0. From 0.9.0 on it is fixed: a later change to
the language is schema 0.10. It adds to 0.8:

- `consumerApis`, the optional top-level array of read-only consumer API definitions, written in a
  syntax organised by what a reader asks (CONSUMER_API C-D132–C-D141; [below](#consumer-api-definitions-in-schema-09));
- relation columns in table views (`related:<key>`, [above](#table-view-type-table));
- the `many-to-one` cardinality ([above](#relation-types));
- a binding's `candidates` ([above](#which-records-a-relationship-may-choose-schema-09-base-09-k7)).

Every other part of a 0.9 document is as in 0.8. Install, draft compile and validation refuse a
0.8 document that declares `consumerApis` with `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`
(C-D134), and one that uses any of the other three with `INVALID_MODEL` at the feature's path,
naming schema 0.9. A 0.8 document without them installs, and a stored 0.8 release keeps reading and
activating as stored, its consumer API definitions offering every operation. The starter
is content release 0.9.5 on schema 0.9.

### Consumer API definitions in schema 0.9

Their shape, defaults, validation and contract rules are specified in
[CONSUMER_API.md](CONSUMER_API.md#definition-shape), with the mapping from schema 0.8; in summary:

- Each definition has a `key` (`consumerApi` in routes and contracts), a `name` and its own
  `contractVersion`. It names the types it `exposes` (public names default to the key in
  PascalCase), the `operations` it offers (`objects`, `xref`, `resolve`, `lists`, `events`: listed
  means offered, C-D132), what an object looks like (`object.fields` with roles, `parent`, `path`,
  `hierarchy`, `related` blocks reached by a relation's `key` or `reverseKey`), how XREF matches
  (`operations.xref.matchOn`, `alsoMatchThrough`) and its `filters` (`byType`, `under`, `linkedTo`,
  `onRelated`).
- A definition may keep **earlier versions** (`earlierVersions`, 0.13 DF3): a list, newest first, of
  frozen copies of the definition at an older `contractVersion`. Each holds that version's `contractVersion`
  (below the definition's own, once each), everything the definition itself holds except its `key` and `name`
  (`description`, `exposes`, `publicNames`, `object`, `operations`, `filters`), the `deprecated` day it was
  superseded and an optional `sunset` day, both written `YYYY-MM-DD`. The engine serves the version beside
  the current one until it is removed from the model; the sunset day is announced in the `Sunset` header,
  not enforced. A kept version is validated like the current one, against the same release, at its own
  pointer (`/consumerApis/<key>/earlierVersions/<index>/…`) with the version named in the message, so a type
  or attribute the model no longer has refuses the release naming it; a key change (`setKey`) in a draft is
  rewritten in every kept version as in the current definition, so each keeps its public names (R13-F14); and it is compared with the same
  version in the active release (C-D2), so a kept version that would read differently is refused too
  (`CONSUMER_KEPT_VERSION_CHANGED`). Stopping to serve a version is a warning, as removing a definition is.
  The model editor raises the version with `raiseConsumerApiVersion`, which keeps the previous one by
  default ([API.md § Kinds](API.md#kinds)).
- An `onRelated` filter may declare `crosswalk: true`, which enables crosswalk reads (`to.{filter}`).
  It is part of the contract: turning it off is `version_required` at
  `/consumerApis/<key>/filters/<name>/crosswalk`, turning it on is compatible (C-D58).
- An `onRelated` filter may declare `scoreOnlyMatching: true`: on XREF, only the related records it
  matches pass scores through its block. It needs an `alsoMatchThrough` entry over that block,
  refused otherwise at `/consumerApis/<key>/filters/<name>/scoreOnlyMatching` (C-D45).
- A related field reads `id`, `name`, an attribute of the related types or
  `ancestor:<type>.<field>`, or `objectType`: the related record's public type name, allowed only
  where the definition exposes every type the block reaches, refused otherwise at
  `/consumerApis/<key>/object/related/<name>/fields/<field>` (C-D73). The `parent` block's fields
  are keyed by the roles' output names (C-D75).
- Events (`operations.events`, 0.9 C9): `perType` declares one per exposed type, and `custom` events
  name exposed `objectTypes`, `changes` (`created`, `updated`, `deleted`) and an optional `watch` of
  output names and related blocks, by the names consumers read (C-D81); each mistake is refused at
  `/consumerApis/<key>/operations/events/custom/<index>/…` (C-D84). An event that tells consumers
  less needs a higher `contractVersion` (C-D85). `event` and `after` are reserved filter names
  (C-D86).
- A list (`operations.lists.<key>`: `of`, optional `within`) may name `sortBy`: a scalar attribute
  (not JSON) its type binds, refused otherwise at `/consumerApis/<key>/operations/lists/<list>/sortBy`
  (C-D29). Records without a value come last, then name, then creation order. `from`, `seek` and
  `includeTotal` are reserved filter names besides the paging names (C-D30).
- Every reference to a type, attribute, relation binding or ancestor is validated against the same
  release, with the model's path-and-reason errors at the pointer the author wrote (C-D141).
- Each definition is compared with the **active** release's (C-D17): draft compile and release diff
  report the result as `consumerContracts`, and activation refuses a breaking change that does not
  raise `contractVersion` (C-D2): removing or retyping an output field, renaming or no longer exposing
  a type, changing a related block's shape or fields, changing scoring weights (C-D4), removing or
  changing a list (its type, `sortBy` or `within`) or a filter's verb (C-D18), turning a filter's
  `scoreOnlyMatching` on or off (C-D46), removing or narrowing an event, or no longer offering an
  operation (C-D132). Removing a whole definition is a warning. Installing a release without
  activating it is not checked.
- A field's sources share one value type (`text` and `longText` count as one), which is its output
  type (C-D19); the `id` field reads `id`, the object ID (C-D24); a match rule or match field reads
  `name`, `id` or a `searchable` or `unique` attribute (C-D20). A `contains` weight reads text only:
  `name` or a `text` or `longText` attribute; on `id` or a typed attribute it is refused at its
  `/operations/xref/…/contains` pointer, since it could never match (0.9 C4).
- `GET /api/v1/model/consumer-apis/{consumerApi}` answers a definition expanded, every default
  written out (C-D137).
- Definitions change no stored data and no management API behaviour.

## Schema 0.10 (Product 0.10)

Schema 0.10 is opened by Base 0.10 N1 (2026-10-11) and grows with 0.10's packages until 0.10.0 is
released. It adds to 0.9:

- `navigation` on an application ([above](#navigation-groups-navigation-schema-010)).

Every other part of a 0.10 document is as in 0.9, and a 0.9 document is valid unchanged, with the
same content hash. A 0.9 document that declares `navigation` is refused with `INVALID_MODEL` at the
application's `navigation`, naming schema 0.10; before 0.10 the member was ignored. The starter and
the example model stay on schema 0.9 (D3). Supported versions are listed oldest first by number
(`0.5` … `0.9`, `0.10`), in `GET /system`'s `schemaLanguages` and in a refusal's
`supportedSchemaVersions`.

## Schema versions and the window

`schemaVersion` versions the model language; `release.version` versions one model package; the
starter content release `0.9.5` uses schema `0.9`. Each distinct validated model is installed as an
immutable database release identified by its content hash.

Workspace snapshots, change sets and record versions are separate from model-language and
model-release versions. ADR-026/027 keep current data live and editable while coordinated publishing
records immutable history; there are no configurable object publication states. The model declares
rules used for live writes, effective change sets and the final merged publishing graph; the runtime
owns their context, versions, lineage and atomicity. A change set does not edit definitions.
Publications are interpreted under their pinned model, and a change set's current-live base captures
the selected model and current record versions. Replacing a workspace's model with reviewed loss is
a migration (0.11 V1–V3); it never mutates an immutable release or bypasses validation.

**The window** is the set of schema versions this deployment reads, writes and runs: from 0.12 only `0.10`
(0.12 D441; `0.5` to `0.10` before). It is listed in `GET /system`'s `schemaLanguages` and in every refusal's
`supportedSchemaVersions`. The version contains what each earlier version added:

| Added by | What |
| --- | --- |
| 0.5 | Strict typed `table` views (ADR-021) |
| 0.6 | The `mappingGrid` view type |
| 0.7 | Relations-panel sort options (`sortFields`, `defaultSort`); the `relationMatrix` and `tree` view types |
| 0.8 | `effectivePeriod` ([above](#schema-08-additions-product-09)) |
| 0.9 | `consumerApis` in its present syntax; relation columns; `many-to-one`; a binding's `candidates` ([above](#schema-09-product-09)) |
| 0.10 | An application's `navigation` ([above](#schema-010-product-010)) |

Schema 0.4 and earlier are outside the window. `form` and `dashboard` view types remain unimplemented.

**The rules** (0.11 D99, reduced by 0.12 L2a):

1. **Reading and writing.** One parser reads the version; an author writes it. `setRelease` accepts
   `schemaVersion` only for a version in the window.
2. **Side by side.** Every workspace runs its own release and every change set and publication reads under
   the release it is pinned to (ADR-042). With one version in the window, no request combines two versions.
3. **Between releases.** Activation's compatibility analysis, a migration of a workspace or of a change set
   (0.11 V1–V3) and the consumer contract check compare what the two releases declare. Values convert by the
   migration's pairs of value types; a value type a later version adds converts to and from the others only
   once its pairs are written, and until then a value converting to or from it is reported as loss
   (`VALUE_NOT_CONVERTIBLE`, D102), never dropped silently.
4. **Outside the window.** Installation, activation, workspace creation and a migration's target answer
   `422 UNSUPPORTED_SCHEMA_VERSION` with `schemaVersion` and `supportedSchemaVersions`; validation and draft
   compile report the diagnostic at `/schemaVersion`; startup refuses a model file outside it. A stored
   release outside the window makes only the workspaces running it unavailable
   (`503 MODEL_REGISTRY_UNAVAILABLE`); no activation can replace it, since its data cannot be compared. A
   release newer than the window was written by a later engine, which is the one to run (D101).

**Before 1.0 the window is cleaned at every release (0.12 L2a, D439, D441).** From 0.12 it holds the one
version the release writes, `0.10`; `0.5` to `0.9` left it, with their conversion rules and the offline
upgrade command: the example models were raised to `0.10` (each is a subset of it), and a database
holding a release of a version that left still starts: the engine serves the other workspaces, the
workspaces on that release answer `503`, and `python -m app.cli.model_release_raise` raises the stored
releases to `0.10` in place (offline; `--dry-run` reports only). How a version leaves after 1.0 is in [COMPATIBILITY](COMPATIBILITY.md).
