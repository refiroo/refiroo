# changes

The changes area is one list of what people, clients and jobs changed across the instance: records, relationships, change sets, publications and model administration. Each entry names its workspace, what changed and who changed it, never the values.

You use it to answer "what did I or that client change" and "what happened since I last looked" without reading each workspace's feed. A caller sees only what they may browse; model administration entries need Model authoring at the instance. Use a workspace's change feed to follow live data from another system.

1. Read newest first: `GET /api/v1/changes` with `workspaceKey`, `actorId` or `since`.
2. Page on with `nextCursor`; open a record or change set from the IDs in an entry.

## GET /api/v1/changes

Title: List changes

Lists changes across workspaces, newest first, narrowed by the filters you pass, which all apply together. Any signed-in caller may use it; it returns only the changes the caller may see. The list never holds values: read the record to see them.

- `live=true` keeps only changes to live data and leaves out a change set's staged entries, which a publication repeats.
- Security events are not here; read `GET /api/v1/security-events`.

### Parameters

- actorId: The person's or client's ID: only what they made. An ID that belongs to nobody lists nothing.
- workspaceKey: Only this workspace's changes.
- kind: `record`, `relationship`, `change-set`, `publication` or `model`. Repeat the parameter to ask for several.
- since: Changes at or after this time (ISO 8601 with offset). The time itself is included.
- until: Changes before this time. The time itself is not included.
- objectTypeKey: Changes to records of this type, as it was when the change was made.
- relationTypeKey: Changes to relationships of this type, as it was when the change was made.
- causeId: Changes made by the job or publication with this ID.
- action: `created`, `updated`, `deleted`, `reclassified`, or `moved` (an update that changed the record's parent).
- attributeKey: Updates that changed this attribute.
- live: `true` keeps only changes to live data; `false` (the default) keeps all.
- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: a filter, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## Schemas

### ChangePage

- items: The page's changes, newest first.
- nextCursor: Send it as `cursor` for the next page; `null` at the end.
- prevCursor: Send it as `cursor` for the previous page; `null` at the start.
- anchor: Reopens this page.
- totalCount: Entries matching, only with `includeTotal=true`.
- startIndex: Entries before the first one, only with `includeTotal=true`.

### ChangeEntry

One change: where, what, how and by whom; never values.

- id: The entry's ID.
- occurredAt: When the change was made.
- kind: `record`, `relationship`, `change-set`, `publication` or `model`.
- action: Records: `created`, `updated`, `deleted`, `reclassified`. Relationships: `created`, `updated`, `deleted`. Change sets: for example `created`, `renamed`, `validated`, `discarded`. Publications: `published`, `withdrawn`. Model: `created`, `updated`, `deleted` (a draft), `installed`, `activated`. Ignore actions you do not know.
- workspace: The workspace it was made in; `null` for model administration outside workspaces and for a deleted workspace's entries.
- changeSet: The change set it was made in, or the one a publication published; `null` for none.
- subject: What changed, named as it is now.
- changedFields: Names of the fields that changed, never values.
- attributes: The attributes the change touched.
- cause: What made the change.
- actor: Who made it; `null` for an entry with no recorded actor.
- channel: `mcp` for a change made through an assistant; absent otherwise.

### ChangeWorkspace

- key: The workspace's key.
- label: Its label.

### ChangeSetRef

- id: The change set's ID.
- name: Its name as last named, also once published or discarded; `null` when it has none.
- open: Whether it is still open. A published or discarded change set cannot be opened.

### ChangeSubject

What an entry changed, named as it is now: a record (its type and name), a relationship (its type and both ends), a change set, a publication (its number), a model draft or a release. `removed` says whether a record or relationship is gone from where it was.

- id: The ID of the record, relationship, change set, publication, model draft or release.
- name: A record's or change set's name as it is now.
- number: A publication's number.
- applicationKey: The application a record opens in.
- objectTypeKey: A record's type key.
- objectTypeName: A record's type name.
- relationTypeKey: A relationship's type key.
- relationTypeName: A relationship's type name.
- fromObject: A relationship's source end.
- toObject: A relationship's target end.
- removed: Whether the record or relationship is gone from where it was.

### ChangeObject

- id: The record's ID.
- name: Its name as it is now; `null` for a record since removed.

### ChangeAttribute

- key: The attribute's key.
- name: Its name in the entry's workspace's model; the key when the model no longer has it.

### ChangeCause

- kind: `user` for a single write, `job` or `publication`.
- id: The job's or publication's ID; absent for a single write.

### ActorResponse

Who made a change: a person or a client, or the engine for its own changes, which has no ID or name. An entry from before actors were recorded has no actor (`null`).

- kind: `user`, `client`, or `engine` for the engine's own changes.
- id: The person's or client's ID; absent for the engine.
- name: Their name as it is now; absent for the engine.
