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
