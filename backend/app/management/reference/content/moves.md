# moves

A move takes records and their relationships from one workspace into another through a model mapping, even when the two workspaces run different models. You start it to copy a set of records across, or to move them and delete the originals. Starting it is a job: first a dry run that writes nothing and says what each record would become. Read the mapping first, with `GET /api/v1/model-mappings/{key}`, because the move names its `version`.

1. `POST /api/v1/moves` answers `202` with a `move` job.
2. Read the dry run's rows with `GET /api/v1/jobs/{job_id}/rows`; fix the mapping or the selection and send it again, or load it with `POST /api/v1/jobs/{job_id}/confirm`.

## POST /api/v1/moves

Title: Start a move

Starts the dry run of a move: it reads the selected records of the source workspace, live or as published, and plans what each becomes in the target through the mapping. Each row ends as `create`, `update`, `refused` with the target's refusal or `notMoved` with the mapping's reason. With `stage: execute` it loads at once instead of waiting for confirmation, always into a new change set of the target. Needs Browse in the source, and Change sets there for `mode: move`.

### Errors

- 403 FORBIDDEN: needs Copy and move in the target, and Browse in the source
- 404 WORKSPACE_NOT_FOUND: a workspace does not exist
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 PUBLICATION_NOT_FOUND: `sourceAt` names no publication of the source
- 404 OBJECT_NOT_FOUND: a selected record is not in the source
- 409 WORKSPACE_RETIRED: a workspace is retired
- 409 MOVE_MAPPING_CHANGED: the mapping's version is not `expectedVersion`
- 422 MOVE_SAME_WORKSPACE: source and target are one workspace
- 422 MODEL_MAPPING_MODEL_MISMATCH: a workspace runs another model than the mapping's
- 422 MOVE_MAPPING_HAS_PROBLEMS: the mapping does not hold against the two releases
- 422 INVALID_QUERY: a selected type, field or operator does not fit the source model
- 422 REQUEST_VALIDATION_ERROR: the body is malformed

## Schemas

### MoveMapping

- key: The mapping's key.
- expectedVersion: The mapping's `version` you read. The move is refused if it has changed.

### MoveRequest

- sourceWorkspaceKey: The workspace the records are read from; not the target.
- targetWorkspaceKey: The workspace the records are loaded into; it must be active.
- mapping: The mapping to move through, at the version you read.
- selection: What moves; omitted or empty, every record of the source workspace.
- sourceAt: `live`, read when the dry run starts, or the ID of a publication of the source.
- mode: `copy` (the source is untouched) or `move`: the copy, plus a change set of the source that deletes what was loaded.
- stage: `preview`: the dry run waits for `POST /api/v1/jobs/{job_id}/confirm`. `execute`: it loads at once. Either way it loads into a new change set of the target.

### MoveSelection

What moves: the records every given part selects; empty, the whole workspace.

- types: Source types with their own criteria. Each type once.
- objectIds: Records by ID, at most 10,000.

### MoveSelectionType

One source type and its own criteria, as an export's scope.

- objectTypeKey: The source object type.
- where: Criteria as the model query takes them; all must hold. Empty selects every record of the type.
