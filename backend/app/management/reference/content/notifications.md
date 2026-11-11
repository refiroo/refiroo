# notifications

The inbox holds a person's or a client's notices: change sets waiting for their approval, decisions on their requests, jobs they started that finished or failed, and publications in the workspaces they follow. Read the list, mark notices read or remove them; the stream tells a client of each new one. Mail copies of notices are chosen under `mail`.

1. Follow a workspace: `PUT /api/v1/me/followed-workspaces/{workspace_key}`.
2. Read: `GET /api/v1/me/notifications?unread=true`, then `POST /api/v1/me/notifications/read`.

## GET /api/v1/me/followed-workspaces

Title: List the workspaces I follow

Lists the workspaces the caller follows and may still browse, by label. A client has none.

### Parameters

- pageSize: 1 to 500; 100 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## PUT /api/v1/me/followed-workspaces/{workspace_key}

Title: Follow a workspace

Follows a workspace, so a notice arrives in the caller's inbox when a change set is published there, but not for the person who published it. Repeating is harmless and keeps the first time.

### Parameters

- workspace_key: The workspace to follow.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 404 NOT_FOUND: no active workspace, or the caller may not browse it

## DELETE /api/v1/me/followed-workspaces/{workspace_key}

Title: Stop following a workspace

Stops following a workspace. It is harmless when the caller did not follow it.

### Parameters

- workspace_key: The workspace to stop following.

### Errors

- 403 NOT_A_PERSON: the caller is a client
- 404 NOT_FOUND: no such workspace

## GET /api/v1/me/notifications

Title: List my notices

Lists the caller's notices, newest first, with the count of all their unread ones. Filter by read state, by the words a person sees in the notice, by kind or by workspace.

### Parameters

- q: Words a person sees in the notice: its kind, the change set's name, the comment, who acted, the job's kind.
- sort: `newest` (the default) or `oldest`.
- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/me/notifications/events

Title: Follow my notices live

Streams the caller's inbox as server-sent events: `event: unread` with the count at once and after every change, and `event: notification` with the notice for each one made while the stream is open. Earlier notices are not replayed; read them with the list. Read it with `fetch` and the `Authorization` header, which `EventSource` cannot send. A comment line every 15 seconds keeps an idle stream open.

## GET /api/v1/me/notifications/{notification_id}

Title: Get a notice

Reads one of the caller's notices by ID, for example where a digest's link leads.

### Parameters

- notification_id: The notice's ID.

### Errors

- 404 NOT_FOUND: no notice has this ID, or it is another person's

## POST /api/v1/me/notifications/read

Title: Mark notices read

Marks notices read, or unread with `read` false: those named in `ids`, those about `subjectId`, or all of them. It is idempotent. An ID that is unknown or another person's is left alone.

### Errors

- 422 REQUEST_VALIDATION_ERROR: not exactly one of `ids`, `subjectId` or `all` true

## POST /api/v1/me/notifications/removal

Title: Remove notices

Deletes notices for good, those named in `ids` or every read one with `read` true. What the notices were about stays. A notice is removed only by its owner; an ID that is unknown or another person's is left alone.

### Errors

- 422 REQUEST_VALIDATION_ERROR: not exactly one of `ids` or `read` true

## Schemas

### FollowedWorkspaceResponse

A workspace the caller follows: a notice arrives in their inbox when a change set is published there.

- workspaceKey: The workspace's key.
- label: Its label.
- since: When the caller began following it.

### NotificationPage

The caller's notices, newest first. `unreadCount` counts every unread notice, whatever the page and filter.

- unreadCount: The caller's unread notices in all, whatever the page and filters.

### NotificationResponse

A notice. `kind` is `change-set.submitted` (a request waiting for your approval), `change-set.approved` or `change-set.sent-back` (a decision on yours), `change-set.published` (a change set was published in a workspace you follow), or `job.completed`, `job.failed` or `job.awaiting-confirmation` (a job you started). `details` holds what a client words it from: for a change set `changeSetName`, `version`, `comment`, `actor` (who submitted or decided: kind, id, name) and `publicationId`; for a job `jobKind` and `state`. A change set's name is as it was when the step happened.

- id: The notice's ID.
- kind: What happened: `change-set.submitted` (waiting for your approval), `change-set.approved` or `change-set.sent-back` (a decision on yours), `change-set.published` (in a workspace you follow), `job.completed`, `job.failed` or `job.awaiting-confirmation` (a job you started).
- workspaceKey: The workspace it concerns.
- subject: The change set or job it is about.
- details: What a client words it from: for a change set `changeSetName`, `version`, `comment`, `actor` and `publicationId`; for a job `jobKind` and `state`.
- read: Whether the caller has read it.
- readAt: When it was marked read; null while unread.
- createdAt: When it was made.

### NotificationSubject

- kind: `change-set` or `job`.
- id: The change set's or job's ID.

### NotificationsRead

- ids: The notices to mark, 1 to 500 IDs.
- subjectId: Mark every notice about this change set or job.
- all: True marks every notice.
- read: `false` marks the notices unread.

### NotificationsReadResult

- unreadCount: The caller's unread notices after the change.

### NotificationsRemoval

Deletes notices for good: those named in `ids` (another person's or an unknown one is left alone), or every read one with `read` true. What they were about stays.

- ids: The notices to delete, 1 to 500 IDs.
- read: True deletes every read notice.

### NotificationsRemovalResult

- unreadCount: The caller's unread notices after the removal.
