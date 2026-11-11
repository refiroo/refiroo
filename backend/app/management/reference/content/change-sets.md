# change-sets

A change set is a copy of a workspace's data that you change in private. Publishing applies only what the change set changed onto the live data and then removes it; what others changed live meanwhile is kept, and a record both sides changed refuses the publication as a conflict. The publication is a numbered snapshot of the merged result, and the workspace's current publication is the newest not withdrawn. A workspace can require an approval: you submit the change set and a holder of Approve publications decides it.

1. Start with `POST /api/v1/workspaces/{workspace_key}/change-sets`, write records with `changeSetId`, and review with `object-changes` and `relation-changes`.
2. Check with `.../validation`, then publish with `.../publication`, or `.../submission` and `.../decisions`.

## GET /api/v1/workspaces/{workspace_key}/change-sets

Title: List a workspace's change sets

Lists the workspace's open change sets, the oldest first, all of them or those one person or client started. Change sets are shared: anyone who may work in change sets there may change any of them. A published or discarded change set is gone from the list. Use `GET /api/v1/me/change-sets` for the caller's own across workspaces.

### Parameters

- workspace_key: The workspace's key.
- createdBy: The ID of the person or client who started them; an ID that belongs to nobody lists none.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/workspaces/{workspace_key}/change-sets

Title: Start a change set

Starts a change set in the workspace. `source: currentLive` copies the live data as its base; `publication` starts from `derivedFromPublicationId`. With neither it starts empty: it can add records but cannot change existing ones. It works under the workspace's model release unless `modelReleaseId` names another that its content fits.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Work in change sets; `modelReleaseId` needs a model role
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 404 PUBLICATION_NOT_FOUND: `derivedFromPublicationId` is no publication of this workspace
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_SNAPSHOT_RETRY: live data or the model changed while copying
- 409 PINNED_MODEL_UNAVAILABLE: `modelReleaseId` names no installed release
- 409 MODEL_RELEASE_RETIRED: `modelReleaseId` names a retired release
- 409 CHANGE_SET_CONTENT_INCOMPATIBLE: the data does not fit that release
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or the fields contradict each other

## GET /api/v1/me/change-sets

Title: List my change sets

Lists the open change sets the caller started, in every workspace where they may browse, the most recently changed first. Each carries its workspace's label and how many records and relationships it changes, so a start page needs no call per change set.

### Parameters

- pageSize: 1 to 100; 20 by default.

### Errors

- 409 CHANGE_SET_BASE_INVALID: a change set's base is unusable
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/change-sets/{change_set_id}

Title: Get a change set

Reads one change set: its `version`, which every write into it names as `expectedChangeSetVersion`, the model release it works under, what it started from and its latest publication request.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Browse in the change set's workspace
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID

## PATCH /api/v1/change-sets/{change_set_id}

Title: Rename a change set

Renames a change set; `name: null`, or no `name`, clears the name. It raises the change set's `version`, so read it again before the next write. A submitted change set is refused unless the request carries `withdrawSubmission=true`, which withdraws the submission first.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## DELETE /api/v1/change-sets/{change_set_id}

Title: Discard a change set

Discards a change set with everything in it. Live data and publications are not touched, and nothing brings the change set back. A submitted change set is refused unless the request carries `withdrawSubmission=true`.

### Parameters

- change_set_id: The change set's ID.
- expectedVersion: The change set's `version`.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or invalid

## PATCH /api/v1/change-sets/{change_set_id}/model-release

Title: Move a change set to another release

Pins the change set to another installed model release, after checking that all of its content fits that release; a change set that does not fit is refused and stays as it was. Naming the release it already works under changes nothing. It never converts content: use `POST /api/v1/change-sets/{change_set_id}/model-migrations` for a release the content does not fit.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 PINNED_MODEL_UNAVAILABLE: `modelReleaseId` names no installed release
- 409 MODEL_RELEASE_RETIRED: `modelReleaseId` names a retired release
- 409 CHANGE_SET_CONTENT_INCOMPATIBLE: the content does not fit that release
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: a release is too new
- 409 PINNED_MODEL_INVALID: a release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## POST /api/v1/change-sets/{change_set_id}/model-migrations

Title: Move a change set onto the workspace's release

Starts moving a change set that works under a release its workspace no longer runs onto the release the workspace runs, converting its content. It answers 202 with a `migration` job whose preview lists every conversion, loss and refusal and changes nothing. Review the rows, then confirm with `POST /api/v1/jobs/{job_id}/confirm`. A submitted change set stays submitted.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 WORKSPACE_RETIRED: the workspace is retired
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 MIGRATION_TARGET_NOT_WORKSPACE_RELEASE: `targetReleaseId` is not the workspace's release
- 422 MIGRATION_TARGET_IS_CURRENT: the change set already works under it
- 422 UNSUPPORTED_SCHEMA_VERSION: a release's schema is not supported
- 422 INVALID_MIGRATION_MAPPING: `typeMappings` names something a release lacks

## GET /api/v1/change-sets/{change_set_id}/object-changes

Title: List the records a change set changes

Lists the records the change set adds, changes or removes, compared with its source, by type and name. A record added and removed inside the change set is not listed. `before` is the source as it was, not today's live data: whether live data moved since is reported when you publish.

### Parameters

- change_set_id: The change set's ID.
- kind: `added`, `changed` or `removed`; repeat the parameter for several. All when omitted.
- objectTypeKey: Only records of these types under the change set's model; repeat for several. A record whose type the change set changed matches either type.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the change set's workspace
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 UNKNOWN_OBJECT_TYPE: `objectTypeKey` is not in the change set's model
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/change-sets/{change_set_id}/relation-changes

Title: List the relationships a change set changes

Lists the relationships the change set adds, changes or removes, compared with its source, by type. It includes the parent edges the engine maintains from each record's parent (a moved record has one removed and one added), so every row that publishes is visible; set `containment=false` to leave them out.

### Parameters

- change_set_id: The change set's ID.
- kind: `added`, `changed` or `removed`; repeat the parameter for several. All when omitted.
- relationTypeKey: Only relationships of these types under the change set's model; repeat for several.
- containment: `true` lists only parent edges, `false` leaves them out; both when omitted.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the change set's workspace
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 UNKNOWN_RELATION_TYPE: `relationTypeKey` is not in the change set's model
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/change-sets/{change_set_id}/validation

Title: Check a change set

Checks the whole change set, its source and its changes together, against its model, and answers `valid` with a diagnostic for each problem; problems are an answer, not an error. It does not compare with live data: a record live data changed since is found when you publish. It changes nothing but the change set's history.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged

## POST /api/v1/change-sets/{change_set_id}/restructurings/preview

Title: Plan a restructuring

Plans a change to the shape of a hierarchy in the change set (a move, a type change, a level inserted or removed) and writes nothing. The plan says whether it is `ready`, needs input or is refused, and pages the records it changes. Send the same operation to `POST .../restructurings` with the plan's `planDigest` to apply it. One operation changes at most 500 records.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or a record is named twice
- 422 UNKNOWN_OBJECT_TYPE: a type the change set's model lacks
- 422 OBJECT_TYPE_UNCHANGED: a type change to the record's own type
- 422 INVALID_TYPE_MAPPING: a mapping names an attribute the types cannot map
- 422 UNKNOWN_ATTRIBUTES: `inputs` name attributes the new type lacks
- 422 RESTRUCTURING_TOO_LARGE: more than 500 records
- 422 INVALID_CURSOR: the cursor belongs to another plan
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/change-sets/{change_set_id}/restructurings

Title: Apply a restructuring

Applies a previewed restructuring to the change set. The plan is computed again and written only if it is the one whose `planDigest` you send and it is `ready`; otherwise nothing is written. The change set's `version` rises once for the whole operation.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 RESTRUCTURING_PLAN_CHANGED: the plan differs from the previewed one
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or a record is named twice
- 422 RESTRUCTURING_NOT_READY: the plan needs input or is refused
- 422 UNKNOWN_OBJECT_TYPE: a type the change set's model lacks
- 422 OBJECT_TYPE_UNCHANGED: a type change to the record's own type
- 422 INVALID_TYPE_MAPPING: a mapping names an attribute the types cannot map
- 422 UNKNOWN_ATTRIBUTES: `inputs` name attributes the new type lacks
- 422 RESTRUCTURING_TOO_LARGE: more than 500 records

## POST /api/v1/change-sets/{change_set_id}/publication

Title: Publish a change set

Publishes the change set: its changes are merged onto the live data, the result becomes the workspace's current publication and the change set is removed. `expectedActivePublicationId` is the current publication as you read it, or `null` for none. Where the workspace requires an approval, only a holder of Approve publications may publish directly, and not when a second person is required.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Publish in the change set's workspace
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 APPROVAL_REQUIRED: the policy needs a submission and an approval
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 WORKSPACE_ACTIVE_PUBLICATION_CONFLICT: the current publication is not the expected one
- 409 VERSION_CONFLICT: live data changed under a record the change set changed
- 409 CHANGE_SET_MODEL_RELEASE_CONFLICT: the workspace runs another release
- 409 MOVE_COPY_NOT_PUBLISHED: a deletion waits for the copy of a move
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 WORKSPACE_GRAPH_INVALID: the merged data breaks a rule

## POST /api/v1/change-sets/{change_set_id}/submission

Title: Submit a change set for approval

Asks for the change set to be published, which needs it to validate. A submitted change set is frozen: a write to it is refused unless the request carries `withdrawSubmission=true`, which withdraws the submission first. Submitting does not change the `version`; the approver decides on that version.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: it is already submitted
- 409 CHANGE_SET_INVALID: the change set does not validate
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## DELETE /api/v1/change-sets/{change_set_id}/submission

Title: Withdraw a submission

Takes a submitted change set back to open. Only the person who submitted it, or a holder of Approve publications, may; the request stays in the list as `withdrawn`.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: not the submitter, and no Approve publications
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 NOT_SUBMITTED: the change set is not submitted
- 409 WORKSPACE_RETIRED: the workspace is retired

## POST /api/v1/change-sets/{change_set_id}/decisions

Title: Decide a submitted change set

Decides a submitted change set. `approve` publishes it in the same step, bound like `POST .../publication`, and answers the publication; `sendBack` needs a `comment`, opens the change set again and answers it. Where the policy requires a second person, the submitter cannot decide.

### Parameters

- change_set_id: The change set's ID.

### Errors

- 403 FORBIDDEN: needs Approve publications; not the submitter under `secondPerson`
- 404 CHANGE_SET_NOT_FOUND: no open change set has this ID
- 409 NOT_SUBMITTED: the change set is not submitted
- 409 VERSION_CONFLICT: not the submitted version, or live data changed
- 409 PUBLICATION_CONFLICT: the current publication is not the expected one
- 409 CHANGE_SET_MODEL_RELEASE_CONFLICT: the workspace runs another release
- 409 MOVE_COPY_NOT_PUBLISHED: a deletion waits for the copy of a move
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the release is too new
- 409 PINNED_MODEL_INVALID: the release is damaged
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 COMMENT_REQUIRED: `sendBack` without a comment
- 422 WORKSPACE_GRAPH_INVALID: the merged data breaks a rule

## GET /api/v1/workspaces/{workspace_key}/publication-requests

Title: List publication requests

Lists the workspace's publication requests, the newest first, each with its decisions. A request is one submission of a change set. An approved request keeps the change set's name and the publication it made, though the change set no longer exists.

### Parameters

- workspace_key: The workspace's key.
- state: Only requests in this state.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/workspaces/{workspace_key}/approval-policy

Title: Get the approval policy

Reads whether publishing in the workspace needs an approval and whether a second person must give it. A workspace that never set a policy answers both off at version 0.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist

## PUT /api/v1/workspaces/{workspace_key}/approval-policy

Title: Set the approval policy

Sets the workspace's policy in one write; send `expectedVersion` as read, `0` while none was set. With `requireApproval`, a change set reaches live data only through an approval, which a holder of Approve publications may also give by publishing directly. With `secondPerson`, the submitter cannot approve their own. A change is recorded as a security event.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Workspace administration
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 APPROVAL_POLICY_INVALID: `secondPerson` without `requireApproval`

## GET /api/v1/workspaces/{workspace_key}/publications

Title: List a workspace's publications

Lists the workspace's publications, the newest first. One is `active`, the current publication, or none is; the others are `withdrawn`, whether withdrawn or replaced by a later publication. Read a publication's records by sending its ID as `publicationId` to a read.

### Parameters

- workspace_key: The workspace's key.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/publications/{publication_id}

Title: Get a publication

Reads one publication: its number, status, release, what it replaced and who published or withdrew it.

### Parameters

- publication_id: The publication's ID.

### Errors

- 403 FORBIDDEN: needs Browse in the publication's workspace
- 404 PUBLICATION_NOT_FOUND: no publication has this ID

## POST /api/v1/publications/{publication_id}/withdrawal

Title: Withdraw a publication

Withdraws the workspace's current publication, so the workspace has none. Live data and the other publications stay as they are: this is no undo. The publication in the path must be the current one, so a stale client cannot withdraw a newer one. The next publication then expects `expectedActivePublicationId: null`.

### Parameters

- publication_id: The publication's ID.

### Errors

- 403 FORBIDDEN: needs Publish in the publication's workspace
- 404 PUBLICATION_NOT_FOUND: no publication has this ID
- 409 WORKSPACE_ACTIVE_PUBLICATION_CONFLICT: it is not the current publication
- 409 WORKSPACE_RETIRED: the workspace is retired

## Schemas

### ChangeSetCreate

- name: Its name, up to 300 characters.
- source: `currentLive` copies the workspace's live data as the base; `publication` starts from `derivedFromPublicationId`. Omitted, with no publication named, the change set starts empty.
- derivedFromPublicationId: The publication to start from. Not with `source: currentLive` or `modelReleaseId`; the change set keeps that publication's release.
- modelReleaseId: The installed release to work under instead of the workspace's own. The base must fit it. Not with `derivedFromPublicationId`.

### ChangeSetUpdate

- name: The new name, up to 300 characters; `null` or no `name` clears it.
- expectedVersion: The change set's `version`.

### ChangeSetResponse, OwnChangeSetResponse

- id: The change set's ID.
- workspaceKey: The workspace it belongs to.
- name: Its name; `null` when it has none.
- modelReleaseId: The ID of the model release it works under.
- modelReleaseKey: That release's key.
- modelReleaseVersion: That release's version.
- source: What it started from: `currentLive` (a copy of live data), `publication` (the one in `derivedFromPublicationId`) or `empty`.
- derivedFromPublicationId: The publication it started from; `null` for the other sources.
- version: Rises by one with every write into the change set: a record, a relationship, a rename, a restructuring or a release change. Send it as `expectedChangeSetVersion`, or `expectedVersion` where the field is so named. Submitting does not raise it.
- createdAt: When it was started.
- updatedAt: When it last changed.
- createdBy: Who started it; `null` for a change set from before that was recorded.
- submission: Its latest publication request in any state; `null` if it was never submitted.

### OwnChangeSetResponse

One of the caller's open change sets, wherever it is.

- workspaceLabel: The workspace's label.
- changeCount: How many records and relationships it adds, changes or removes.

### ChangeSetModelReleaseUpdate

- modelReleaseId: The ID of the installed release to move to.
- expectedChangeSetVersion: The change set's `version`.

### ChangeSetMigrationRequest

A move of the change set onto the release its workspace runs, converting its content where that release differs. `targetReleaseId` may be left out; if sent it must be the workspace's release. `typeMappings` names what a type of the change set's release became in it, so its records keep their IDs.

- expectedChangeSetVersion: The change set's `version`.
- targetReleaseId: The release the workspace runs; may be left out, and no other is accepted.
- typeMappings: What each type of the change set's release became in the target, so its records keep their IDs. At most 500.

### MigrationTypeMapping

What a type of the workspace's model became in the target release: its records keep their IDs under the new type. Attributes not named take the values of the same attribute of the old type, and a display attribute the old type's display attribute.

- fromObjectTypeKey: A type of the old release.
- toObjectTypeKey: The type it became in the target release.
- attributes: Where each attribute of the new type takes its values from. An attribute not named takes those of the same key, and a display attribute the old display attribute.

### MigrationAttributeSource

- attributeTypeKey: An attribute of the new type.
- from: The attribute of the old type it takes its values from; `null` for none.

### ChangeSetPublishRequest

- expectedChangeSetVersion: The change set's `version`.
- expectedActivePublicationId: The workspace's current publication as you read it; `null` when it has none. Any other value refuses the publication.

### ChangeSetValidation

- valid: `true` when the change set has no problem.
- diagnostics: One entry per problem, each with `code`, `message` and usually `details` naming the record (`objectId`) or relationship (`relationId`). A code is the one a write of that record would answer, or `IDENTITY_COLLISION`, `CONTAINMENT_CYCLE`, `CONTAINMENT_RELATION_MISSING`, `RELATION_CARDINALITY_VIOLATION`, `DUPLICATE_RELATION_SCOPE` or `MISSING_REQUIRED_RELATION`.

### PublicationResponse

- id: The publication's ID.
- workspaceKey: The workspace it belongs to.
- modelReleaseId: The ID of the release it was published under.
- modelReleaseKey: That release's key.
- modelReleaseVersion: That release's version.
- publicationNumber: Counts the workspace's publications from 1 and never restarts.
- status: `active` for the workspace's current publication; `withdrawn` once withdrawn or replaced.
- derivedFromPublicationId: The publication its change set started from; `null` if none.
- supersedesPublicationId: The publication that was current when it was published; `null` if none.
- createdAt: When it was made.
- publishedAt: When it was published.
- withdrawnAt: When it was withdrawn or replaced; `null` while active.
- feedPosition: The position of its `published` entry in the workspace's change feed: live data at that position is the publication. `null` for one made before the feed existed.
- publishedBy: Who published it.
- withdrawnBy: Who withdrew it, or published the one that replaced it; `null` while active.

### ObjectChange

What a change set does to one record. `changedFields` names what differs between `before` and `after` (`objectType` first when the type changed, then `name`, `parent` and attribute keys); a missing side counts as holding nothing, so an added or removed record names every field it holds. A `changed` entry may name none: its version still advanced, and publishing still claims it against live. `beforePath` is where the source held a moved record (a `changed` entry naming `parent`); `null` otherwise.

- kind: `added` (the source has no such record), `changed`, or `removed` (the change set deletes a record the source has).
- objectId: The record's ID.
- objectTypeKey: The record's type; for a type change, the new type.
- applicationKey: The application the record belongs to.
- before: The record in the source; `null` for `added`.
- after: The record in the change set; `null` for `removed`.
- changedFields: What differs between `before` and `after`: `objectType` first when the type changed, then `name` and `parent`, then attribute type keys. An added or removed record names every field it holds. A `changed` entry may name none: its version still rose and publishing still checks it against live data.
- path: Where the change set puts the record, from the top down and ending with the record; for a removed record, where the source held it.
- beforePath: Where the source held a record whose parent changed; `null` otherwise.

### ObjectChangeState

A record as the change set's source holds it (`before`) or as the change set does (`after`). `objectTypeKey` is the type on that side; a type change makes the two differ.

- objectTypeKey: The record's type on this side.
- name: Its name on this side.
- parentObjectId: Its parent on this side; `null` at the top level.
- attributes: Its values on this side, as a record read gives them.
- version: Its version on this side.

### RelationChange

What a change set does to one relationship. `containment` marks a parent edge the engine maintains: its type is one of the parent relations of the `to` end's type under the change set's model.

- kind: `added`, `changed` or `removed`, as for a record.
- relationId: The relationship's ID.
- relationTypeKey: Its relation type's key.
- containment: `true` for a parent edge the engine keeps from a record's parent.
- fromObject: The record at its from end.
- toObject: The record at its to end.
- before: The relationship in the source; `null` for `added`.
- after: The relationship in the change set; `null` for `removed`.
- changedFields: The attribute type keys whose values differ between `before` and `after`.

### RelationChangeEnd

- objectId: The record's ID.
- objectTypeKey: Its type, as the change set holds it, or the source for a removed end.
- name: Its name, as the change set holds it, or the source for a removed end.

### RelationChangeState

- attributes: The relationship's values by attribute type key.
- version: Its version on this side.

### SubmissionCreate

- expectedChangeSetVersion: The change set's `version`.
- comment: What the approver should know, up to 2,000 characters.

### DecisionCreate

- outcome: `approve` publishes the change set; `sendBack` opens it again.
- comment: Required for `sendBack`, optional for `approve`; up to 2,000 characters.
- expectedChangeSetVersion: The change set's `version` as reviewed; it must also be the version submitted.
- expectedActivePublicationId: For `approve`: the workspace's current publication as you read it, or `null` when it has none.

### DecisionResponse

- id: The decision's ID.
- outcome: `approve` or `sendBack`.
- comment: The decider's comment.
- decidedAt: When it was decided.
- decider: Who decided.

### PublicationRequestResponse

- id: The request's ID.
- workspaceKey: The workspace it belongs to.
- changeSetId: The ID of the change set that was submitted.
- changeSetName: The change set's name when it was submitted.
- state: `submitted` waits for a decision; `withdrawn` was taken back; `sentBack` was returned with a comment; `approved` was published.
- submitter: Who submitted it.
- comment: The submitter's comment.
- submittedAt: When it was submitted.
- decisions: The decisions made on it, in order.

### ApprovalPolicyUpdate

- requireApproval: `true` so that a change set reaches live data only through an approval.
- secondPerson: `true` so that the submitter cannot approve their own change set. Needs `requireApproval`.

### ApprovalPolicyResponse

- workspaceKey: The workspace the policy belongs to.
- requireApproval: Whether a change set needs an approval before it reaches live data.
- secondPerson: Whether the person who submitted a change set may not approve it.
- version: Rises with each change; `0` while no policy was set.

### RestructuringPreviewRequest

- operation: What to do, by its `kind`: `move`, `changeType`, `insertLevel`, `removeLevel` or `changeTypeUnder`.
- choices: Answers to the plan's questions.
- inputs: Values and relationships for records that need them.
- expectedChangeSetVersion: The change set's `version`; when given and not current the preview is refused.
- outcome: Only records with one of these outcomes: `typeChanged`, `moved`, `withoutPlace` (values or relationships left behind), `restored`, `needsInput` or `refused`. All when empty.
- pageSize: Records per page, 1 to 500; 100 by default.
- cursor: The `nextCursor`, `prevCursor` or `anchor` of an earlier page of this plan. At most one of `cursor`, `position` and `from`.
- position: A zero-based record to start the page at.
- from: `end` reads the last page.
- includeTotal: `true` adds `totalCount` and `startIndex`.

### RestructuringApplyRequest

- operation: The operation as previewed.
- choices: The choices as previewed.
- inputs: The inputs as previewed.
- expectedChangeSetVersion: The change set's `version` as previewed.
- planDigest: The `planDigest` of the preview to apply.

### RestructuringMove

- kind: `move`: put a record under another parent.
- objectId: The record to move.
- parentObjectId: The new parent; `null` for the top level.
- objectTypeKey: The type the record becomes. Without it the record keeps its type where the new place allows, else takes the only type that fits, else the plan asks.

### RestructuringChangeType

- kind: `changeType`: change a record's type under the same parent.
- objectId: The record.
- objectTypeKey: The type it becomes.

### RestructuringInsertLevel

- kind: `insertLevel`: create a record and move records under it.
- parentObjectId: Where the new record goes; `null` for the top level.
- childObjectIds: The records to move under it, each directly under that parent. At least one, none repeated.
- objectTypeKey: The new record's type.
- name: The new record's name, 1 to 500 characters.

### RestructuringRemoveLevel

- kind: `removeLevel`: delete a record and move its children to its parent.
- objectId: The record to delete. Its relationships go with it.

### RestructuringChangeTypeUnder

- kind: `changeTypeUnder`: change the type of every matching record below a record.
- objectId: The record whose subtree changes; it is not changed itself.
- fromObjectTypeKey: The type that changes, at any depth.
- objectTypeKey: The type those records become.

### RestructuringChoices

- types: The type to take where the plan asks.
- mappings: Where attributes of a new type take their values from, per type pair.

### RestructuringTypeChoice

- objectTypeKey: The type of the records the plan asks about.
- parentObjectTypeKey: The type of their new parent; `null` for the top level.
- newObjectTypeKey: The type they become, one of the question's `options`.

### RestructuringMappingChoice

- fromObjectTypeKey: The old type.
- toObjectTypeKey: The new type.
- attributes: Sources you choose for attributes of the new type. The others keep the plan's suggestion.
- restore: Whether to take back the values and relationships the plan offers. `true` by default.

### RestructuringMappingAttribute

- attributeTypeKey: An attribute of the new type.
- from: The attribute of the old type it takes its values from; `null` for none.

### RestructuringInput

- objectId: A record's ID, or `new` for the record `insertLevel` creates. Once per record.
- attributes: Values to set, as a record create takes them.
- relations: Relationships to add, as a record create takes them.

### RestructuringRelationInput

- relationTypeKey: The relation type's key.
- direction: `outgoing` starts at the record, `incoming` ends at it.
- objectId: The record at the other end.
- attributes: The relationship's values by attribute type key.

### RestructuringPreview

A restructuring's plan, with a page of its records in plan order.

- changeSetId: The change set planned for.
- changeSetVersion: The version the plan was made on.
- planDigest: Identifies the request and the plan. Send it to apply this plan and no other.
- status: `ready` can be applied; `needsInput` has open type questions or missing inputs; `refused` cannot be applied.
- summary: The plan's counts.
- typeQuestions: The places where several types are possible, with the choice made, if any.
- pairs: One entry per pair of old and new type, with how its attributes and relationships are carried.
- refusals: Why the plan cannot be applied, at most 20.
- refusalCount: How many refusals there are, with those of single records.
- refusalsTruncated: `true` when `refusals` holds fewer than `refusalCount`.
- records: A page of the records the operation changes, in plan order.

### RestructuringResult

- operationId: Identifies the operation, as named in the change set's history.
- changeSetId: The change set restructured.
- changeSetVersion: Its new version.
- summary: What the operation changed.
- createdObjectId: The ID of the record `insertLevel` created; `null` for the other operations.

### RestructuringSummary

- recordCount: Records the operation changes.
- typeChangeCount: Records whose type changes.
- moveCount: Records whose parent changes.
- createdCount: Records created.
- removedCount: Records deleted.
- valuesWithoutPlaceCount: Values left behind because the new type has no attribute for them.
- relationshipsWithoutPlaceCount: Relationships removed because the new type cannot hold them.
- restoredCount: Values and relationships taken back.
- inputsNeededCount: Values and relationships still to be given.
- refusalCount: Refusals, for the operation and for single records.

### RestructuringTypeQuestion

- objectTypeKey: The type of the records that need a new type.
- parentObjectTypeKey: The type of their new parent; `null` for the top level.
- options: The types possible there.
- chosen: The type chosen in `choices.types`; `null` while open.
- recordCount: How many records it concerns.

### RestructuringPair

- fromObjectTypeKey: The old type.
- toObjectTypeKey: The new type.
- recordCount: Records changing from one to the other.
- restore: Whether values and relationships offered back are taken.
- attributes: Each attribute of the new type and where its values come from.
- withoutPlace: Attributes of the old type the new type has no place for, with how many records lose a value.
- relations: The records' relationships and whether the new type keeps them.

### RestructuringPairAttribute

- attributeTypeKey: An attribute of the new type.
- from: The attribute of the old type it takes its values from; `null` for none.
- rule: How the source was found: `sameType` (the same attribute), `display` (display to display), `uniqueRequired` (the one unique required attribute of each), `choice` (your mapping choice) or `none`.
- alternatives: Other attributes of the old type that could be the source.
- kept: Records that keep the value from the same attribute.
- mapped: Records that take it from another attribute.
- restored: Records given a value offered back.
- inputs: Records given a value from `inputs`.
- empty: Records left without a value.

### RestructuringAttributeCount

- attributeTypeKey: The attribute of the old type.
- count: How many records lose a value of it.

### RestructuringRelationCount

- relationTypeKey: The relation type's key.
- direction: `outgoing` starts at the changed records, `incoming` ends at them.
- outcome: `kept`, or `withoutPlace` when the new type cannot hold it and it is removed.
- count: How many relationships.

### RestructuringRecord

- objectId: The record's ID; `new` for the record `insertLevel` creates.
- name: Its name.
- path: Where it will stand, from the top down and ending with the record; for a removed record, where it stands now.
- before: Its type and parent now; `null` for a created record.
- after: Its type and parent after the operation; `null` for a removed record. The type is `null` while a question is open or no type is possible.
- outcomes: What happens to it: `typeChanged`, `moved`, `created` or `removed`.
- attributes: Each attribute of the new type and where its value comes from.
- withoutPlace: Values and relationships the new type cannot hold, which are lost.
- restoredRelationships: Relationships taken back with their old IDs.
- inputsNeeded: What you still have to give for this record.
- refusals: Why this record cannot be restructured.

### RestructuringRecordState

- objectTypeKey: The record's type.
- parentObjectId: Its parent's ID; `null` at the top level.

### RestructuringRecordAttribute

- attributeTypeKey: An attribute of the new type.
- from: The attribute of the old type the value comes from; `null` when it does not come from one.
- outcome: `kept` (same attribute), `mapped` (another attribute), `restored` (offered back), `input` (from `inputs`), `default` (a created record's default) or `empty`.
- value: The value the record will hold.

### RestructuringValue

- attributeTypeKey: The attribute of the old type.
- value: The value that is lost.

### RestructuringWithoutPlace

- attributes: Values the new type has no attribute for.
- relationships: Relationships removed because the new type cannot hold them.

### RestructuringRelationship

- relationId: The relationship's ID.
- relationTypeKey: The relation type's key.
- direction: `outgoing` starts at the record, `incoming` ends at it.
- objectId: The record at the other end.
- objectTypeKey: Its type.
- name: Its name.

### RestructuringInputNeeded

- kind: `attribute` or `relation`.
- key: The attribute type or relation type.
- reason: `required` (no value), `invalidValue` (the value does not fit the new type), `atLeastOneOf` (one of the attributes a rule names must be set; one entry for each) or `requiredRelation`.

### RestructuringRefusal

- code: Why: `noPossibleType`, `typeNotAllowed`, `application` (another application's type or parent), `cycle`, `notRoot`, `uniqueness`, `requiredRelationWithoutPlace`, `notInChangeSet`, `notUnderParent`, or the code of the write the dry run refused.
- message: The reason in words.
- objectId: The record it concerns; absent for the operation.
- conflictingObjectId: The record that collides, for `uniqueness` and `requiredRelationWithoutPlace`.
- details: Values that help: types, keys, IDs.

### AiProposalResult

What an `aiProposal` job did, as far as it has run: `proposed` sources given a target in the change set; `unmatched` left unmapped because the provider found no target at or above the confidence floor; `changed` skipped because the source or its targets changed since the job bound them; `refused` because the rules refused the target; `notAnswered` because a call failed or the answer left them out.

- proposed: Sources given a target in the change set.
- unmatched: Left unmapped: the provider found no target at or above the confidence floor.
- changed: Skipped: the source or its targets changed since the job read them.
- refused: Skipped: the rules refused the target.
- notAnswered: Skipped: a call failed or the answer left them out.
- changeSetId: The change set the proposals were written into.
- warnings: What went wrong, in words.

### JobResponse

A job. `result` says whether every item applied: a `completed` job may be `partial`. `parameters` holds the kind's choices: `run` and `onExisting` for a batch; the request as it was sent, without `workspaceKey` and without what it left out, for an export, whose `result` stays `null` (it has no item outcomes) and whose `output` describes its file once completed. A `profile` job profiles a source file and has no `result`; a `dryRun` previews a model draft's import, and its summary is read at `GET /api/v1/model-drafts/{draft_id}/dry-run`. `changeSetVersion`, for a job in a change set, is the version the job holds: its claim while it is queued or running, the version it left once finished. `leaseOwner` and `leaseExpiresAt` name the worker running a background job; `cancelRequestedAt` is set by a cancel request, which the worker carries out at its next chunk.

- id: The job's ID.
- kind: What it does: `batch`, `import`, `export`, `profile`, `dryRun`, `inference`, `profileCheck`, `migration` (also a change set's move onto a release), `mappingInference`, `move`, `aiProposal` or `aiTask`.
- workspaceKey: The workspace it works in.
- changeSetId: The change set it works in; `null` for none.
- changeSetVersion: For a job in a change set: the version it holds while queued or running, the version it left once finished.
- policy: `atomic` applies all items or none, `independent` applies each on its own; `null` for kinds without items.
- parameters: The kind's choices; a change set's migration holds `stage`, `moves` (`changeSet`), `changeSetId`, `targetReleaseId` and `typeMappings`.
- modelReleaseId: The ID of the release it works under.
- state: `queued`, `running`, `awaiting_confirmation` (previewed, waiting for `POST /api/v1/jobs/{job_id}/confirm`), `completed`, `failed`, `cancelled` or `expired`.
- stage: What a running job is doing, such as `previewing` or `applying`; `null` otherwise.
- progress: How far it has come.
- counts: Its items by status and action.
- result: Whether every item applied: `applied`, `partial` or `rejected`; `null` while open and for kinds without items.
- error: Why it failed; `null` otherwise.
- createdAt: When it was queued.
- startedAt: When a worker took it up; `null` before.
- finishedAt: When it ended; `null` before.
- expiresAt: When the job and its files are removed.
- cancelRequestedAt: When a cancel was asked; the worker stops at its next chunk.
- leaseOwner: The worker running it; `null` when none.
- leaseExpiresAt: When that worker's claim ends unless renewed.
- confirmedAt: When a previewed import or batch was confirmed.
- notices: An import's notices about its file as a whole once the file is bound, empty when there are none; null before then and for other jobs.
- migration: A migration's summary once previewed; null for other jobs.
- move: A move's dry run summary once completed; null for other jobs.
- aiProposal: An `aiProposal` job's tally, updated as it runs; null for other jobs.
- requestedBy: Who submitted it, whose permissions it runs with; null for a job from before submitters were recorded.
- origin: The assistant task or model draft the job belongs to; null for a job with neither.

### JobProgress

- total: Items to process; `null` while unknown.
- processed: Items processed so far.

### JobCounts

- applied: Items applied.
- rejected: Items refused.
- unprocessed: Items not reached.
- created: Applied items that created a record or relationship.
- updated: Applied items that changed one.
- unchanged: Applied items that found nothing to change.
- deleted: Applied items that deleted one.

### JobPreview

What executing a previewed import or batch would do. `coverage` is `complete` when every item ran, and `sample` when only the first `JOB_PREVIEW_MAX_ITEMS` did (an import's rows were still all bound, so every binding refusal is listed). `result` is what execution would give under the request's policy: `rejected` for an `atomic` job with any refusal. `rows` is an import's only. Execution is authoritative: data may change before confirmation.

- coverage: `complete` when every item ran, `sample` when only the first ones did.
- items: How many items there are and how many ran.
- counts: What executing would create, change, leave and refuse.
- result: What executing would give under the job's policy: `applied`, `partial` or `rejected`.
- previewedAt: When the preview ran.

### PreviewItems

- total: Items in the job.
- previewed: Items previewed.

### PreviewRows

- total: Rows in the file.
- previewed: Rows whose items ran.
- rejected: Rows refused.

### PreviewCounts

- created: Items that would create.
- updated: Items that would change.
- unchanged: Items that would change nothing.
- deleted: Items that would delete.
- rejected: Items that would be refused.

### DeletionTotals

What delete items remove together: their records by type, the relationships incident to them, and how many of those reach records that stay.

- objectCount: Records that would go.
- objectsByType: Those records by type key.
- relationshipCount: Relationships of those records that would go.
- retainedAssociationCount: Of them, relationships that reach records that stay.

### JobNotice

Something about an import's file as a whole, found once it is bound: for example `RECORD_IDS_OF_ANOTHER_WORKSPACE` (`details`: `workspaceKey`, `rows`), rows that name their records by IDs another workspace's records hold, which cannot load here.

- code: What was found.
- message: It in words.
- details: Values that help.

### JobOrigin

Where a job comes from: the assistant task it belongs to (`aiTask`: the task's own job, and every job its session queued) or else the model draft it works on (`modelDraft`). `name` is what the task's or the draft's page names it.

- kind: `aiTask` for a job of an assistant task, `modelDraft` for one on a model draft.
- id: The task's or draft's ID.
- name: Its name.

### ExportOutput

What a completed export's file holds, to read before downloading it from `GET /api/v1/jobs/{job_id}/output`. `feedPosition` is the position the export equals: the feed head it read live data at, or a publication's own position; `null` for a change set. `asOfApplied` names the types `asOf` dated.

- format: `jsonl`, `csv` or `xlsx`.
- contentType: The file's media type.
- counts: Records and relationships exported.
- context: What was exported.
- feedPosition: The change feed position the export equals: the head live data was read at, a publication's own position, `null` for a change set.
- asOf: The `asOf` date asked for; `null` for none.
- asOfApplied: The types that date was applied to.
- modelReleaseId: The ID of the release it was read under.
- bytes: The file's size.
- sha256: The file's SHA-256, in hex.
- layout: The technical tables, or a workbook for people.

### ExportCounts

- records: Records by object type key, every exported type, zero included.
- relations: Relationships by relation type key.

### ExportedContext

- workspaceKey: The workspace read.
- changeSetId: The change set read; `null` for live data or a publication.
- changeSetVersion: Its version when read.
- publicationId: The publication read; `null` for live data or a change set.

### BindingReportSource

- sheet: The sheet's name; for a CSV, the file's.
- objectTypeKey: The type its rows load; `null` for an export's table layout.
- rows: Rows read.
- rejectedRows: Rows refused before they ran.
- columns: What binding made of each column.
- missingRecords: Records of the source's type that the context holds with the key filled and that no row names; deleted when the source says `missing: delete`.
- skippedRows: Rows without a key that the source skips (`rowsWithoutKey: skip`).

### BindingReportColumn

What binding made of one column's cells. A converted column (`field`, `attributeTypeKey`, `relatedRecord`, `key`) counts `converted`, `valueMapped` and `refused` cells. A match column (`parent`, `relation`, `relationFlags`) counts `refused` cells and the values that found one record (`resolved`), none (`notFound`) or several (`ambiguous`); a split cell holds several values.

- column: The column's heading.
- binding: How it was read: `field` or `attributeTypeKey` (a value), `key`, `parent`, `relation`, `relationFlags` or `relatedRecord`.
- target: The field, attribute type or relation type it binds to; `null` for none.
- cells: Cells in the column.
- empty: Cells left empty.
- converted: Value columns: cells converted to the attribute's type.
- valueMapped: Value columns: cells a value map replaced.
- refused: Cells refused.
- resolved: Match columns: values that found one record.
- notFound: Match columns: values that found none.
- ambiguous: Match columns: values that found several.
- reading: For a relationship or matrix column: how it was read.

### BindingReportReading

How a matrix or relationship column was read: the `field` its cells are matched by (`name`, an attribute key or `@label`, or the older `name (display)` reading) with its `label`; whether the file `recorded` it or the engine `guessed` it, with a plain `note` when the guess was not clear; the fields it could be read by; and where a new record goes. A different field is chosen with `POST /api/v1/jobs/{job_id}/reread`.

- binding: `relation`, `relatedRecord` or `field`.
- field: The field its cells are matched by.
- label: That field's label.
- recorded: `true` when the file records the reading.
- guessed: `true` when the engine guessed it.
- note: In plain words, why a guess was not clear.
- options: The fields the cells could be matched by.
- newRecords: Where a new record of the column goes.
- updatedRows: On a value sheet's first column: rows that update a record.
- newRows: On a value sheet's first column: rows that are new records.
- valueSheet: True on the first column of a value sheet: the sheet lists the records one column offers. `updatedRows` and `newRows` count its rows that update a record and that are new records, and `newRecords` says where a new one goes.

### BindingReportFieldOption

- field: A field of the column's records.
- label: Its label.
- cells: Distinct values in the column.
- matched: Of them, values that find exactly one record by this field.
- ambiguous: Of them, values that find several.

### BindingReportNewRecords

Where a new record of a column goes: an existing container, or a place the load creates first (`willBeCreated`). `objectTypeKey` and `name` are null where the model's rules give no one place, and `reason` says whether none or several containers meet them.

- objectTypeKey: The container's type; `null` where the model gives no one place.
- name: The container's name; `null` likewise.
- willBeCreated: `true` when the load creates the container first.
- reason: Where there is no place: `none` meets the model's rules or `several` do.
- typeName: With `willBeCreated`: the new container's type in words.

### MigrationSummary

What a migration's preview found and what its confirmation binds: the workspace's assignment version (`expectedVersion`) and feed position it read. A migration that publishes a change set names it, with the version and the workspace's active publication it read.

- targetReleaseId: The ID of the release being moved to.
- currentReleaseId: The ID of the release the data works under now.
- expectedVersion: The workspace's model assignment version the preview read; confirm with it.
- feedPosition: The change feed position the preview read; confirm with it.
- counts: The migration's items by outcome.
- changeSetId: The change set it moves or publishes.
- changeSetVersion: That change set's version when read.
- activePublicationId: The workspace's current publication when read.
- publicationId: The publication it made, once it has published the change set.

### MigrationCounts

A migration's items by outcome.

- conversion: Values converted or carried to another attribute.
- reclassified: Records whose type, application or parent changes.
- loss: Records, values or relationships removed.
- refused: Items the target release refuses.
- created: Records and relationships a split or list conversion creates.

### MoveSummary

What a move's dry run found: every row (`coverage` is always `complete`) counted by outcome, by source type and by relationship type; the reasons with their counts; the attributes not carried per type; and the rows naming possible duplicates. It names the mapping and version it ran with, the source state it read (`sourceAt`, and `sourceFeedPosition` for live data) and the four releases: the two the workspaces ran and the two the mapping names.

- coverage: Always `complete`: every row was counted.
- rows: Rows the dry run found.
- counts: Rows by outcome.
- types: Rows by source type.
- relationships: Rows by relation type.
- reasons: Why rows are not moved, with counts.
- attributesNotCarried: Attributes the move leaves behind, by type and reason.
- possibleDuplicates: Rows that create a record of a type and name the target already holds.
- mapping: The model mapping and version it ran with.
- sourceWorkspaceKey: The workspace read.
- targetWorkspaceKey: The workspace written to.
- sourceAt: The state of the source read.
- sourceFeedPosition: The source's change feed position read; `null` for a change set or publication.
- sourceReleaseId: The ID of the release the source runs.
- targetReleaseId: The ID of the release the target runs.
- mappingSourceReleaseId: The ID of the source release the mapping names.
- mappingTargetReleaseId: The ID of the target release the mapping names.
- mode: `copy` leaves the source as it is; `move` deletes what was loaded there.
- source: With `mode: move`: how many source records are deleted and how many kept.
- targetChangeSetId: The change set of the target that the move loaded; none before it loads.
- sourceChangeSetId: For `mode: move`, the change set of the source that deletes what was loaded; none when nothing was deleted.
- sourceFeedPositionAtLoad: The source's feed position when the move loaded, beside `sourceFeedPosition` read at its dry run: a later change in the source belongs to the next move.

### MoveCounts

Rows by outcome.

- create: Rows that create a record or relationship in the target.
- update: Rows that update one the target holds.
- updateOriginal: Rows that update the original of a record moved back.
- refused: Rows the target refuses.
- notMoved: Rows the mapping does not move.

### MoveTypeCounts

- sourceType: A type of the source.
- targetType: The type it becomes; absent when the mapping has none.
- counts: Its rows by outcome.

### MoveRelationCounts

- relationTypeKey: A relation type of the source.
- targetRelationTypeKey: The relation type it becomes; absent when the mapping has none.
- counts: Its rows by outcome.

### MoveReasonCount

- code: Why rows are not moved.
- count: How many.

### MoveAttributeCount

- sourceType: The source type.
- attributeTypeKey: The attribute left behind.
- code: Why: `ATTRIBUTE_NOT_MAPPED`, `VALUE_NOT_CONVERTIBLE`, `ATTRIBUTE_READ_ONLY` or `EFFECTIVE_PERIOD_DROPPED`.
- count: How many records.

### MoveMappingVersion

- key: The mapping's key.
- version: Its version.

### MoveSourceCounts

For `mode: move`, the records deleted in the source and the records kept there.

- deleted: Loaded records deleted in the source.
- kept: Loaded records kept there.

### PublicationRequestPage

Publication requests, newest first.
