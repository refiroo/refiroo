---
title: Changes, approvals and publication
description: Prepare and validate shared changes, request approval and publish without overwriting live work.
reader: integrator
---

Use a change set when changes should be prepared and reviewed together. Publishing merges its changes into live data and records an immutable publication. Use the [change-set operations](/docs/api/?api=management#tag/change-sets) for creation, validation, submission, decisions and publication; the same record and relationship operations write within its context.

## Start from the intended base

Choose current live data or an existing publication explicitly. The source options must agree (`CHANGE_SET_SOURCE_INVALID` otherwise). Current-live capture makes a private immutable base; it does not create a publication. If concurrent capture asks for another attempt (`CHANGE_SET_SNAPSHOT_RETRY`), retry the capture rather than substituting an older publication.

Changes remain pinned to their model release. Read and claim the change-set version before edits, and the record or relationship version for updates. `CHANGE_SET_NOT_FOUND` needs the correct open change set; `CHANGE_SET_VERSION_CONFLICT` needs its current state. `CHANGE_SET_BASE_INVALID` needs operator investigation of the damaged base. `CHANGE_SET_CONTENT_INCOMPATIBLE` needs compatible content or a reviewed migration, not a forced pin change.

Read object and relationship change lists to review the delta. Before means the source base, not today's live data. Each page reads a consistent snapshot; pages still follow normal cursor rules. Records and relationships in change sets or publications have no recorded creation or update timestamp, so timestamp filtering and sorting are refused there.

## Validate and submit

Validation reports whether the complete graph is valid and names its diagnostics. A successful validation request can report invalid content. Missing records, missing relationship ends, duplicate unique values and invalid type pairs must be repaired before publication. Common codes include `OBJECT_NOT_FOUND`, `RELATION_NOT_FOUND`, `RELATION_ENDPOINT_MISSING`, `DUPLICATE_ATTRIBUTE_VALUE`, `DUPLICATE_RELATION_SCOPE`, `INVALID_RELATION_PAIR`, `OBJECT_TYPE_NOT_IN_APPLICATION`, `UNKNOWN_OBJECT_TYPE` and `UNKNOWN_ATTRIBUTES`.

Submit a valid change set for publication approval. `CHANGE_SET_INVALID` means repair the diagnostics first. Submission freezes editing: record and relationship changes, batches, imports, rename, discard and restructuring are refused with `CHANGE_SET_SUBMITTED`. An authorised submitter or approver can withdraw the request; the API also supports explicit withdrawal with an edit in the same transaction. The browser workflow is described in [Approval policies](/docs/administer/approval-policies/).

## Decide and publish

An approver approves or sends back the reviewed version. Approval publishes in the same transaction. Send-back requires a comment (`COMMENT_REQUIRED`). `NOT_SUBMITTED` requires refreshing the request state. If the workspace requires another person, the submitter cannot approve their own request. Where approval is required, a caller holding both Publish and Approve publications can publish directly. With a second-person policy, the submitter cannot decide their own request. Otherwise direct publication without the required approval is `APPROVAL_REQUIRED`. `APPROVAL_POLICY_INVALID` requires a valid policy rather than bypassing its checks.

Publication claims the change-set version and expected current publication. `PUBLICATION_CONFLICT` or `WORKSPACE_ACTIVE_PUBLICATION_CONFLICT` means another publication won the race. `VERSION_CONFLICT` can identify record-level divergences against the base; mutable relationship-set changes can produce `MAPPING_SET_CHANGED`. Nothing publishes on these refusals. Review live changes and reapply intended changes on a fresh current-live base when needed.

`WORKSPACE_GRAPH_INVALID` means the proposed merged graph breaks a rule. `CHANGE_SET_MODEL_RELEASE_CONFLICT` requires an explicit [model migration or pin decision](/docs/integrate/model-and-release-operations/). `DELETION_PREVIEW_CHANGED` requires reviewing changed impact before deletion. A retired workspace refuses changes. A missing pinned release (`PINNED_MODEL_UNAVAILABLE`) needs recovery of that release.

Publishing preserves unrelated newer live records. It emits the committed changes and a publication marker in the [raw feed](/docs/integrate/following-changes/). Withdrawing a current publication removes its current designation; it does not erase its snapshot or undo live data. `WORKSPACE_HAS_PUBLICATIONS` prevents deleting a workspace with retained publications.

Submission, approval and send-back also reach the inbox and workspace webhook events. They use a separate event sequence and are not raw data-feed entries. Integrations can follow [workspace approval events](/docs/integrate/consumer-events-and-webhooks/#workspace-approval-events). Digest preferences and following workspaces use the [notification operations](/docs/api/?api=management#tag/notifications); `DIGEST_NOT_SET` means no digest is configured to act on.

## Find the caller's work and follow notifications

The [own-change-set collection](/docs/api/?api=management#tag/change-sets) finds open change sets created by the caller across workspaces they may browse. It does not make change sets private: authorised workspace collaborators can still work on shared open change sets. The [changes collection](/docs/api/?api=management#tag/changes) can select that caller's actor identity or all visible actors, with workspace, kind and period filters. Follow its cursors for an audit export.

The [notification operations](/docs/api/?api=management#tag/notifications) read the caller's inbox, mark notices read, remove them and stream new notices and unread counts. A notification stream is an inbox convenience, not a replacement for the raw feed's durable integration checkpoint.

A person can follow a browsable workspace to receive notices about its publications. Following grants no additional access; a client cannot follow a workspace (`NOT_A_PERSON`). Following notifies eligible people about publications except their own; withdrawing a publication sends no follower notice. A person can choose immediate mail, a digest or no mail per notice kind. These choices do not remove inbox notices. Digests run daily at 07:00 or weekly on Monday at 07:00 in the chosen time zone. They count eligible unread notices, list the 50 newest at most and link to the rest; the digest does not apply immediate mail's 24-hour cutoff. Reading a notice before the digest is queued omits it. Clients have no mail preferences.

Use the [person's notification preferences](/docs/api/?api=management#tag/mail) to read the current settings before changing them. `UNKNOWN_NOTICE_KIND` requires a supported kind; `UNKNOWN_TIME_ZONE` requires a valid time-zone name. `DIGEST_NOT_SET` requires configuring the digest before acting on it. Mail must be configured and the person must have an address. See [Notification settings](/docs/use/notifications-settings/) for the person's task.

## Read a change list as a delta

Change lists compare the prepared content to its captured base. They include added, changed and removed records and relationships, including typed containment edges. A record created and deleted inside the same change set is omitted. A record edited back to its original values can still appear with no changed fields because its version advanced. Moves show the old and new path. Use these lists for review, and the feed for changes applied to live data.

A publication number increases within its workspace; it is not a record version. Withdrawing the current publication leaves live data and every saved snapshot intact. Selecting an older publication by ID remains a valid historical read. Its feed position can be absent for a snapshot created before the feed; select a usable baseline rather than assuming zero.

Changing only a change set’s model pin validates all effective content and performs no value conversion or default filling. Incompatible content returns bounded diagnostics with an exact count and truncation indication; content, pin and version stay unchanged. If conversion is required, use a reviewed migration. After successful publication the change set is consumed; capture a new current-live base for subsequent work.
