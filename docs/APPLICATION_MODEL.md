# Application model specification

## Design

The schema mirrors a generic object–attribute–relation engine while remaining independently named and
typed. Metadata definitions are reusable; bindings state where they may be used; applications and views
control presentation.

## Top-level structure

```json
{
  "schemaVersion": "0.3",
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
validation and optional UI hints. Schema 0.2 supports `text`, `longText`, `integer`, `decimal`, `boolean`,
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

## Object types and attribute bindings

An object type defines its stable key, labels, display attribute, features and behavior. Its
`attributes` array binds global attribute types and supplies object-specific required, read-only, order
and UI properties.

This separation permits one `description` definition to be reused while allowing it to be mandatory in
one object type and optional in another.

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

## Hierarchy

An object type may declare `behavior.parentRelationTypeKeys`. When an object is created with a parent,
the engine uses the parent and child object types to select exactly one allowed relation. It writes both
the parent ID and typed relation atomically. Self-relations support arbitrary-depth groups and values.

## Applications and views

An application selects object types and exposes model-defined views. Object types may be shared across
applications. Applications use immutable keys; names are presentation labels and are not API filters.

Current view types are `table`, `form`, `mappingGrid`, `tree` and `dashboard`. Configuration refers to
stable object, attribute and relation keys—never backend URLs or database IDs.

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

Every panel has a type-specific configuration. Unknown properties are rejected. Startup validation
also checks header and column fields, application membership, containment compatibility, relation
existence and direction, unique detail/panel keys and page-size bounds. Configuration contains only
stable model keys and presentation semantics; the React API adapter owns all backend routes.

## Versioning

`schemaVersion` versions the model language. Schema 0.3 adds typed application detail composition to
the 0.2 object–attribute–relation contract. `release.version` versions one model package. Each distinct
validated model is installed as an immutable database release identified by its content hash.
