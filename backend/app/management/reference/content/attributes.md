# attributes

An attribute value is one stored value of a record, such as a stop's height. You use these operations to read, set, correct or remove a single value without sending the whole record; `PATCH /api/v1/objects/{object_type_key}/{object_id}` changes several at once.

A record holds at most one value per attribute type, so a value is addressed by the attribute type's key. Every write names the record's `version`, raises it by one and answers with the whole record.

1. Set a value the record does not hold: `POST`; change one it holds: `PATCH`.
2. Remove one: `DELETE`, with the record's version.

## GET /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}

Title: Get an attribute value

Reads one stored value together with the version of the record that holds it, which a following write names as `expectedVersion`. A value the record does not hold is `ATTRIBUTE_NOT_FOUND`, not `null`.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- attribute_type_key: The attribute type's key.
- workspaceKey: The workspace whose model describes the value; name it for a record outside the default workspace.
- changeSetId: Read the value in this change set.
- publicationId: Read the value in this publication.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: the record is not live, or not in the change set
- 404 ATTRIBUTE_NOT_FOUND: no value is stored; in a publication also no record
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## POST /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}

Title: Set an attribute value

Sets a value the record does not hold yet; use `PATCH` for one it holds. The record's required, unique, range and at-least-one rules are checked over the result. In a change set the at-least-one rule is left to the change set's validation.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- attribute_type_key: The attribute type's key; the type must bind it.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: no such record in the context
- 409 ATTRIBUTE_ALREADY_EXISTS: the record already holds a value; use `PATCH`
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 VERSION_CONFLICT: `expectedVersion` is not the record's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 DUPLICATE_ATTRIBUTE_VALUE: another record holds a unique value
- 409 DUPLICATE_RELATION_SCOPE: the value repeats a relationship's ancestor scope
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `value` or `expectedVersion` is missing or invalid
- 422 UNKNOWN_OBJECT_TYPE: in a change set, the model has no such type
- 422 UNKNOWN_ATTRIBUTES: the type does not bind the attribute
- 422 READ_ONLY_ATTRIBUTES: the attribute is read-only
- 422 MISSING_REQUIRED_ATTRIBUTES: the attribute is required and the value empty
- 422 INVALID_ATTRIBUTE_VALUE: the value is not of the attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 422 OBJECT_ATTRIBUTE_RULE_VIOLATION: an at-least-one-of rule is not met
- 422 INVALID_EFFECTIVE_PERIOD: the period does not end after it starts
- 422 RELATION_ANCESTOR_REQUIRED: a relationship's record lacks the scope's ancestor
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## PATCH /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}

Title: Change an attribute value

Replaces a value the record already holds; use `POST` for one it does not. The checks are those of `POST`, and the same limits apply in a change set.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- attribute_type_key: The attribute type's key.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: no such record in the context
- 404 ATTRIBUTE_NOT_FOUND: the record holds no value; use `POST`
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 VERSION_CONFLICT: `expectedVersion` is not the record's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 DUPLICATE_ATTRIBUTE_VALUE: another record holds a unique value
- 409 DUPLICATE_RELATION_SCOPE: the value repeats a relationship's ancestor scope
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `value` or `expectedVersion` is missing or invalid
- 422 UNKNOWN_OBJECT_TYPE: in a change set, the model has no such type
- 422 UNKNOWN_ATTRIBUTES: the type does not bind the attribute
- 422 READ_ONLY_ATTRIBUTES: the attribute is read-only
- 422 MISSING_REQUIRED_ATTRIBUTES: the attribute is required and the value empty
- 422 INVALID_ATTRIBUTE_VALUE: the value is not of the attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 422 OBJECT_ATTRIBUTE_RULE_VIOLATION: an at-least-one-of rule is not met
- 422 INVALID_EFFECTIVE_PERIOD: the period does not end after it starts
- 422 RELATION_ANCESTOR_REQUIRED: a relationship's record lacks the scope's ancestor
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## DELETE /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}

Title: Remove an attribute value

Removes a stored value, so the attribute reads as not set. A required or read-only attribute cannot be removed, and the record's at-least-one rule must still hold without the value.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- attribute_type_key: The attribute type's key.
- expectedVersion: The record's `version`.
- changeSetId: The change set to remove it in; live when omitted.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: no such record in the context
- 404 ATTRIBUTE_NOT_FOUND: the record holds no value
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 VERSION_CONFLICT: `expectedVersion` is not the record's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or below 1
- 422 UNKNOWN_ATTRIBUTES: the type does not bind the attribute
- 422 READ_ONLY_ATTRIBUTES: the attribute is read-only
- 422 CANNOT_DELETE_REQUIRED_ATTRIBUTE: the attribute is required
- 422 OBJECT_ATTRIBUTE_RULE_VIOLATION: an at-least-one-of rule would fail
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## Schemas

### AttributeOutput, AttributeValueResponse

- id: The stored value's ID; in a change set or publication, `<record ID>:<attribute type key>`.
- attributeTypeKey: The attribute type's key.
- name: The attribute type's display name.
- valueType: `text`, `longText`, `integer`, `decimal`, `boolean`, `date`, `dateTime` or `json`.
- value: The value. Text and long text are strings, integers and booleans their JSON types, a decimal a string without trailing zeros, a date `YYYY-MM-DD`, a date-time an ISO 8601 instant in UTC, JSON any JSON.

### AttributeValueResponse

- objectVersion: The version of the record that holds the value.
- changeSetVersion: Always `null`: a read does not name the change set's version; read the change set.

### AttributeValueWrite

- value: The value to store, in the attribute type's JSON form; a decimal may be a number or a string.
- expectedVersion: The record's `version`.
- changeSetId: Write in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.
