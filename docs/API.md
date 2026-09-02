# API principles and contract

## Model endpoints

- `GET /api/v1/model`
- `GET /api/v1/applications`
- `GET /api/v1/applications/{applicationKey}`
- `GET /api/v1/attribute-types/{attributeTypeKey}`
- `GET /api/v1/object-types/{objectTypeKey}`
- `GET /api/v1/relation-types/{relationTypeKey}`
- `GET /api/v1/object-type-relations`

All identifiers are stable model keys. Internal metadata sequence IDs are never part of the contract.

## Object endpoints

- `GET /api/v1/objects/{objectTypeKey}`
- `POST /api/v1/objects/{objectTypeKey}`
- `GET /api/v1/objects/{objectTypeKey}/{objectId}`
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}`
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}`

Collections accept `cursor`, `pageSize`, `applicationKey`, `workspaceKey`, `parentObjectId`, `state` and
`search`. Page size defaults to 100 and has a documented maximum of 500. `nextCursor` is null only when
that traversal is complete.

Object attributes are keyed by stable attribute-type keys and retain JSON types:

```json
{
  "applicationKey": "rdm-master",
  "name": "Initial train",
  "parentObjectId": "5e159775-...",
  "attributes": {
    "master-id": "MOT-001",
    "value-code": "IC",
    "value-name": "Initial train",
    "active": true,
    "sort-order": 10
  }
}
```

Updates and deletes require `expectedVersion`; stale writes return HTTP 409.

## Relation endpoints

- `POST /api/v1/relations`
- `GET /api/v1/relations?objectId={id}`

Relation creation validates the relation type, source and target object types, and cardinality. Parent
relations are normally created through object parent operations rather than directly.

## Planned integration endpoints

- Model-aware query with explicit `select` and `expand`
- Bounded bulk create/update/upsert with per-item results
- Relation update and delete
- Asynchronous import/export jobs
- Ordered change feed and webhook subscriptions

There will be no equivalent of enumerating numeric attribute IDs `1..1000` or using `take: 0` for a full
extract.

