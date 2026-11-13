# workspaces

A workspace is a separate body of reference data on the instance, with its own records, change sets, publications and change feed, running its own model release. Instances usually keep one per dataset, for example per year or region. One workspace is the default: every request that names none works in it.

You use this area to find the workspace to work in, to set one up or take it out of use, and to follow a workspace's changes from another system. Changing or deleting a workspace names the `version` you read, as `expectedVersion`.

1. Set up: `POST /api/v1/workspaces`, then give people roles with the `security` operations.
2. Follow changes: read `GET /api/v1/workspaces/{workspace_key}/feed`, storing `nextAfter` after every page.

## GET /api/v1/workspaces

Title: List workspaces

Lists the workspaces the caller has a role in, in key order. Use `GET /api/v1/me/workspaces` for the workspaces a person can open. An item does not say whether the workspace is the default or can be deleted: read `GET /api/v1/workspace-runtime-state` or the single workspace.

### Parameters

- search: Part of the key or label, ignoring case.
- status: `active` (the default), `retired` or `all`.
- holding: Only workspaces where the caller holds this action group, for example `publish`. `GET /api/v1/action-groups` lists them.
- pageSize: 1 to 500; 100 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: `pageSize`, `status` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 ACTION_GROUP_UNKNOWN: `holding` is not an action group

## POST /api/v1/workspaces

Title: Create a workspace

Creates an empty, active workspace. It does not become the default; use `PATCH /api/v1/workspace-runtime-state` for that. Without `modelReleaseId` it runs the release the default workspace runs. The operation exists only while `WORKSPACE_ADMIN_MUTATIONS_ENABLED` is on.

### Errors

- 403 FORBIDDEN: needs Workspace administration at the instance
- 404 MODEL_RELEASE_NOT_FOUND: `modelReleaseId` names no installed release
- 405 HTTP_ERROR: workspace administration is switched off
- 409 WORKSPACE_ALREADY_EXISTS: the key is taken, even by a retired workspace
- 409 MODEL_RELEASE_RETIRED: the release is retired
- 422 REQUEST_VALIDATION_ERROR: the key, label or release ID is invalid
- 422 UNSUPPORTED_SCHEMA_VERSION: this engine cannot run the release's schema
- 503 MODEL_REGISTRY_UNAVAILABLE: no release named, and the default runs none

## POST /api/v1/workspaces/from-workbook

Title: Create a workspace from a workbook

Turns a workbook's model draft into a running workspace in one step: the draft is installed as a release, the workspace is created on it and the workbook is loaded into its live data as an import job (`GET /api/v1/jobs/{jobId}`). A refused row is reported and the rest load.

- A release version or import profile key already taken is replaced by a free one.
- A refusal leaves nothing behind.
- Needs Workspace administration, Install a model (or Model release) and Bulk and import, at the instance.

### Errors

- 403 FORBIDDEN: a group is missing; `details.groups` names it
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 405 HTTP_ERROR: workspace administration, model administration or integration jobs are switched off
- 409 VERSION_CONFLICT: the draft changed, or the same request was sent twice
- 409 WORKSPACE_ALREADY_EXISTS: the key is taken, even by a retired workspace
- 409 SOURCE_FILE_PROFILE_NOT_READY: the workbook is not read yet
- 409 DRAFT_HELD_BY_WORKSPACE: another workspace remembers the draft
- 409 AI_TASK_DRAFT_HELD: an assistant task names the draft
- 422 DRAFT_HAS_NO_WORKBOOK: the draft has no workbook
- 422 INVALID_MODEL: the draft's model does not compile; `details` lists why
- 422 INVALID_IMPORT_PROFILE: the draft's mapping does not fit its model; `details.problems` lists why
- 422 UNSUPPORTED_SCHEMA_VERSION: this engine cannot run the draft's schema
- 422 REQUEST_VALIDATION_ERROR: a field is missing or malformed

## GET /api/v1/me/workspaces

Title: List my workspaces

Lists the active workspaces the caller can open, the default first, with what is waiting for them in each. Use it for a workspace picker or a home page. `GET /api/v1/workspaces` lists by role instead and can show retired workspaces.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/workspaces/{workspace_key}

Title: Get a workspace

Reads one workspace, active or retired. Read it before changing or deleting the workspace: it gives the `version` to send and says whether it can be deleted.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: the caller lacks Browse in this workspace
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 503 MODEL_REGISTRY_UNAVAILABLE: the workspace runs no installed release

## PATCH /api/v1/workspaces/{workspace_key}

Title: Rename, retire or reactivate a workspace

Changes a workspace's label or status. Retiring suspends the workspace's webhook subscriptions, and reactivating it does not resume them. The default workspace cannot be retired.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Workspace administration at the instance
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 405 HTTP_ERROR: workspace administration is switched off
- 409 DEFAULT_WORKSPACE_CANNOT_BE_RETIRED: it is the default
- 409 VERSION_CONFLICT: `expectedVersion` is not the current version
- 422 REQUEST_VALIDATION_ERROR: no `label` or `status`, or a value is invalid

## DELETE /api/v1/workspaces/{workspace_key}

Title: Delete a workspace

Deletes a workspace so a mistyped key can be corrected. Only a workspace that is not the default, was never published, holds no records or change sets and has no webhook subscriptions can be deleted; otherwise retire it. A workspace created again under the key starts a new feed.

### Parameters

- workspace_key: The workspace's key.
- expectedVersion: The workspace's `version`.

### Errors

- 403 FORBIDDEN: needs Workspace administration at the instance
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 405 HTTP_ERROR: workspace administration is switched off
- 409 WORKSPACE_IS_DEFAULT: it is the default
- 409 WORKSPACE_HAS_PUBLICATIONS: it was published; retire it
- 409 WORKSPACE_NOT_EMPTY: it has records or change sets
- 409 WORKSPACE_HAS_SUBSCRIPTIONS: it has webhook subscriptions
- 409 VERSION_CONFLICT: `expectedVersion` is not the current version
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or below 1

## GET /api/v1/workspaces/{workspace_key}/model

Title: Get the release a workspace runs

Names the model release the workspace runs. It does not return the model: read that with `GET /api/v1/model` and `workspaceKey`. To change the release, see the `model administration` operations.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: the caller lacks Browse in this workspace
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 503 MODEL_REGISTRY_UNAVAILABLE: the workspace runs no installed release

## GET /api/v1/workspace-models

Title: List the release each workspace runs

Lists the release each workspace runs, in key order, retired workspaces included. Filter by `releaseKey` or `releaseId` to find the workspaces on a model before changing it.

### Parameters

- releaseKey: Shared by all releases of one model.
- releaseId: One release. With `releaseKey`, a workspace must match both.
- pageSize: 1 to 500; 100 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/workspaces/{workspace_key}/feed

Title: Read a workspace's change feed

Returns the changes to the workspace's live data in commit order, after the position you pass.

- Store `nextAfter` after every page and send it as `after` next time. You are caught up when it equals `headPosition`.
- A page filtered by `kind` or `objectTypeKey` can hold fewer than `pageSize` entries, or none. Keep reading until you are caught up.
- Entries name what changed, never values: read the record. An expired position answers 410; start again from the publication or export it names.

### Parameters

- workspace_key: The workspace's key.
- pageSize: 1 to 1,000; 500 by default.
- objectTypeKey: Object entries of these types, a reclassified record's previous type included. With `kind`, an entry must match both.

### Errors

- 403 FORBIDDEN: the caller lacks Feed in this workspace
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 409 FEED_POSITION_AHEAD: `after` is past the feed's head
- 410 FEED_POSITION_EXPIRED: `after` is older than the feed keeps
- 422 REQUEST_VALIDATION_ERROR: `after`, `pageSize` or `kind` is invalid

## GET /api/v1/workspace-runtime-state

Title: Get the default workspace

Names the default workspace and the version to send when changing it. The list of workspaces does not say which one is the default; this does.

### Errors

- 500 WORKSPACE_RUNTIME_STATE_MISSING: the database lacks the default's row

## PATCH /api/v1/workspace-runtime-state

Title: Set the default workspace

Makes an active workspace the default: the workspace of every request that names none, and the release a new workspace starts on. It moves no workspace's release.

### Errors

- 403 FORBIDDEN: needs Workspace administration at the instance
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 405 HTTP_ERROR: workspace administration is switched off
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 VERSION_CONFLICT: `expectedVersion` is not the current version
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## Schemas

### WorkspaceResponse, WorkspaceDetailResponse

- key: Names the workspace in every address. Lower case letters and digits with single hyphens between them, up to 160 characters. It never changes.
- label: The name people read, 1 to 300 characters. It can change.
- status: `active`, or `retired`: still readable, but its records refuse writes and it cannot be the default.
- version: Rises by one with every successful change to the label or status. Send it as `expectedVersion`.
- createdAt: When the workspace was created.
- updatedAt: When the label or status last changed.
- model: The release the workspace runs.
- availability: Whether this engine can serve the workspace's model release.

### WorkspaceDetailResponse

- deletable: Whether `DELETE` would be allowed now.
- deleteBlockedBy: The first reason it would not be: `default`, `published` (it was published at least once), `notEmpty` (it has records or change sets) or `subscribed` (it has webhook subscriptions). `null` when `deletable`.

### WorkspaceUnavailable

The workspace's model release cannot be served by this version of the engine, so its requests answer `503 MODEL_REGISTRY_UNAVAILABLE`.

- state: Requests for this workspace's data answer `503 MODEL_REGISTRY_UNAVAILABLE`; other workspaces are served.
- reason: `schemaLeftWindow`: the release's schema is older than this engine reads. `schemaAfterWindow`: it is newer. `invalidRelease`: its schema is readable but the release is not valid.

### WorkspaceModelResponse, WorkspaceAssignmentResponse

- releaseId: The release's ID.
- releaseKey: Shared by all releases of one model.
- releaseName: The model's name.
- releaseVersion: The release's version.
- schemaVersion: The model schema the release is written in.
- modelHash: Identifies the release's content.
- version: The assignment's own version, raised by every activation of a release into the workspace. The next activation sends it.
- updatedAt: When the workspace last changed release.

### WorkspaceAssignmentResponse

- workspaceKey: The workspace that runs the release.

### WorkspaceFromWorkbook

- draftId: The ID of the model draft the workbook made.
- expectedVersion: The draft's `version` as last read.
- name: The workspace's label, 1 to 300 characters.
- key: The workspace's key. Without it, one is made from the name, with a number after it when that is taken.

### WorkspaceFromWorkbookResponse

- workspace: The new workspace.
- releaseId: The release the draft was installed as, which the workspace runs.
- releaseKey: Shared by all releases of the model.
- releaseVersion: The release's version, which may differ from the draft's when that version was taken.
- job: The import job loading the workbook. Follow it at `GET /api/v1/jobs/{jobId}`.

### WorkspaceCreate

- key: The new workspace's key; it cannot be changed later.
- label: The name people read.
- modelReleaseId: The installed release to run: not retired, and of a schema this engine runs. Without it, the release the default workspace runs.

### WorkspaceUpdate

- expectedVersion: The workspace's `version`.
- label: The new label.
- status: `retired` also suspends the workspace's webhook subscriptions.

### WorkspaceRuntimeStateResponse

- defaultWorkspaceKey: The workspace of every request that names none.
- version: Send it as `expectedVersion` to change the default.
- updatedAt: When the default last changed.

### WorkspaceRuntimeStateUpdate

- defaultWorkspaceKey: An existing, active workspace.
- expectedVersion: The version read from the runtime state.

### OwnWorkspaceResponse

A workspace the caller may browse, with what waits for them there.

- isDefault: Whether this is the default workspace.
- applications: The applications of the workspace's model; empty when this engine cannot serve it.
- ownChangeSets: Open change sets the caller created here.
- openChangeSets: All open change sets here, for a caller who may publish; otherwise `null`.
- following: Whether the caller is told when a change set is published here. Always `false` for a client.

### FeedPage

- items: The changes after `after`, in position order.
- nextAfter: Send it as `after` in the next request.
- headPosition: The highest committed position.
- earliestPosition: The lowest `after` + 1 the feed still answers.

### FeedEntry

One change to a workspace's live data, at its position. It names what changed, never values; a reader that needs values reads the record.

- position: Rises by one with every change in the workspace, without gaps.
- action: Objects: `created`, `updated`, `deleted`, `reclassified`. Relationships: `created`, `updated`, `deleted`. Publications: `published`, `withdrawn`. Ignore actions you do not know.
- id: The record, relationship or publication that changed.
- version: Its version; a publication's number.
- changedFields: Names of what changed, never values.
- cause: `user` for a single write; `job` or `publication` with its ID.

### OwnWorkspaceResponse

- key: The workspace's key.
- label: The workspace's label.
- model: The release the workspace runs.

### WorkspaceApplication

- key: The application's key.
- name: The name people read.
- icon: The icon the application is shown with; `null` when none.
- color: The colour the application is shown with; `null` when none.
- defaultView: The key of the view the application opens on.

### WorkspaceAvailable

- state: `available`: this engine serves the workspace's model release.

### FeedCause

- kind: `user` (a single write), `job` (a batch or job) or `publication`.
- id: The job's or publication's ID; absent for a single write.

### FeedEntry

- eventId: Identifies the entry.
- occurredAt: When the change was committed.
- kind: `object`, `relation` or `publication`.
- objectTypeKey: An object entry's type.
- applicationKey: An object entry's application.
- previousObjectTypeKey: For `reclassified`, the type the record had.
- relationTypeKey: A relation entry's type.
- fromObjectId: A relation entry's first record.
- toObjectId: A relation entry's second record.
- attributeTypeKeys: The attributes whose values changed, by key.
- actor: Who made the change; `null` for an entry from before actors were recorded.
- modelReleaseId: The release the change ran under.

### WorkspaceModelResponse

The release a workspace runs. `version` is the assignment's own, raised by every activation into the workspace and claimed by the next.
