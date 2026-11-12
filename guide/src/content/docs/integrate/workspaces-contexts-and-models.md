---
title: Workspaces, contexts and models
description: Select the data and model that each request reads or changes.
reader: integrator
---

A workspace owns its records and runs one installed model release. Two workspaces can run different models or different releases of the same model. Choose the workspace before discovering its types or constructing a request.

The caller's own-workspace collection lists browsable active workspaces, default first, with their applications and relevant open-change-set counts. Use the [workspace operations](/docs/api/?api=management#tag/workspaces) to discover workspaces you can read. An omitted workspace on a read generally selects the default workspace. An unknown workspace never falls back to that default. A live record create must name its workspace explicitly; `WORKSPACE_KEY_REQUIRED` means the write lacks that scope.

## Choose a context

| Context | What you read | What you can write |
| --- | --- | --- |
| Live | Current committed data under the workspace's release | Direct changes with the appropriate live permission |
| Change set | Its base plus its prepared changes under its pinned release | Prepared changes, claiming the change-set version |
| Publication | An immutable graph under the release recorded with it | Nothing; derive a change set to prepare changes |

Use the same canonical [record](/docs/api/?api=management#tag/objects) and [relationship operations](/docs/api/?api=management#tag/relations) in these contexts. Do not construct separate change-set CRUD routes. A publication remains unchanged by later live writes, and a publication is not automatically filtered by business date.

Select one context. `MUTUALLY_EXCLUSIVE_CONTEXT` means incompatible selections; `WORKSPACE_CONTEXT_MISMATCH` means the selected change set or publication belongs elsewhere. `WORKSPACE_RETIRED` prevents changes to a retired workspace. Records and relationships in snapshots have no recorded creation or update timestamps, so those fields cannot be used there for filtering or sorting.

## Read across workspaces

The management [cross-type object lookup](/docs/api/?api=management#tag/objects) can combine several named workspaces' live data. Each result identifies its workspace and model release. It cannot combine multiple workspaces with a change set or publication.

A filter naming an application or type must make sense in every selected model. `MODEL_ELEMENT_NOT_IN_EVERY_MODEL` means narrow the workspace selection or choose a common field. Do not interpret a missing type as an empty dataset. If a selected model is unavailable, the entire read fails rather than silently omitting that workspace.

Workspace catalogue changes have their own safeguards: `WORKSPACE_ALREADY_EXISTS` includes retired keys; `WORKSPACE_IS_DEFAULT` and `DEFAULT_WORKSPACE_CANNOT_BE_RETIRED` require choosing another default; `WORKSPACE_NOT_EMPTY` and `WORKSPACE_HAS_PUBLICATIONS` require reviewing the retained content instead of forcing deletion. See [Managing workspaces](/docs/model/managing-workspaces/).

## Keep assignments explicit

`POST /api/v1/workspaces/from-workbook` takes a workbook-backed model draft, its expected version and a workspace name (optionally a key), installs the draft and queues an independent import into the new workspace's live data; it answers `202` with the workspace, release identifiers and import job. A clash with another model's release version or import profile key is resolved with a free value rather than refused; errors, including a stale draft version, are listed in the [workspace operation's API reference](/docs/api/?api=management#tag/workspaces).

This route needs **Workspace administration**, **Install a model** (or **Model release**)
and **Bulk and import**, all at the instance. Installing the release, creating the workspace
and queuing its import form one transaction; the records load afterwards in the job.
Follow that [import job](/docs/integrate/jobs/) and inspect refused rows: `202` means the
load was queued, not that every record loaded.

A new workspace can name an installed usable release; otherwise it starts on the default workspace’s release. After creation its assignment is its own. Changing the default workspace does not switch any existing workspace’s model. Model discovery identifies the selected workspace with `RDM-Workspace`, and its release with `X-Model-Release-Id` and the model ETag.

One unavailable workspace does not justify reading another workspace as a fallback. Across-workspace record lookup fails as a whole if any selected workspace cannot load its release. Its cursor binds the selected workspace set, and each result carries `workspaceKey` and `modelReleaseId`. Feeds, relationship collections and exports remain within one workspace.

An administration list filtered by a consumer API name can include subscriptions from several workspaces where that name denotes different contracts. Keep both API name and workspace in integration configuration. Import profiles and model mappings identify their models; a shared instance catalogue does not mean their definitions apply to every workspace model.

## Deletion and reusing a workspace key

Deletion is restricted to a non-default, empty workspace that has never been published and
has no change sets or webhook subscriptions. `WORKSPACE_HAS_SUBSCRIPTIONS` requires removing
those subscriptions first; deletion does not silently discard them.

Deleting an eligible workspace removes its feed positions and idempotency keys. Audit history
is retained without that workspace or its feed positions. Creating a new workspace under the
same key starts a separate feed at position 1; a retried job request does not replay the deleted
workspace's job. Rediscover the new workspace rather than reusing saved positions or assuming
that an old idempotency key still protects a request. See the [workspace operations](/docs/api/?api=management#tag/workspaces).
