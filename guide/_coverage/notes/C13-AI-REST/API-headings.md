# Selected source headings and bounded excerpts

## docs/API.md:6833 — AI proposals (Product 0.16)

**Delivered by AP1 (2026-10-28):** the provider, its settings and its call record. A proposal is made through its feature's own route, which builds what is sent within the send level; there is no route that sends a provider free text. The provider is set in the environment and read at start (OPERATIONS § AI proposals); nothing here changes it, and the key is never answered. Feature: [mapping targets](#mapping-targets-ap2). - `GET /api/v1/system` answers `ai: {configured, provider, sendLevel, ass

## docs/API.md:6878 — Mapping targets (AP2)

`POST /api/v1/workspaces/{workspaceKey}/mapping-proposals` asks the provider for a target for each unmapped source of a mapping view and writes the answers into a change set; it never writes live data. It needs Work in change sets with the right to write the mapping (as the mapping `PUT` in a change set) and Use AI proposals in the workspace, and send level `values` (purpose `mappingTarget`). - **Body:** `applicationKey`, `viewKey` (a `mappingGrid` view; its binding is used), optional `search` a

## docs/API.md:6921 — A question in words (AG4)

`POST /api/v1/workspaces/{workspaceKey}/query-translations` turns a question about a table view into that view's own filters. It is answered directly, not as a job. The provider is sent the question, today's date and the list's fields with their labels, kinds and conditions: every relationship the listed type has in either direction (whether the view declares it in `filterFields` or not), the view's `filterFields` and, on a live list, `createdAt` and `updatedAt`. For a relationship it is sent th

## docs/API.md:6962 — An account of a model change (AO1)

`POST /api/v1/model-releases/{releaseId}/impact-summary` and `POST /api/v1/model-drafts/{draftId}/impact-summary` (the second only where model drafts are, `MODEL_ADMIN_MUTATIONS_ENABLED`) put into words what activating a release, or applying a draft, in a workspace does. They are answered directly, not as jobs. The engine writes the **facts**; the provider only words them. A release is compared with the release the workspace runs, a draft with the release it is based on (as its compilation is); 

## docs/API.md:6998 — What changed in a period (AO2)

`POST /api/v1/workspaces/{workspaceKey}/history/account` and `POST /api/v1/objects/{objectTypeKey}/{objectId}/history/account` put into words what changed in a workspace, or in one record, over a period. They are answered directly, not as jobs, and have no period limit. The engine counts the **facts** in PostgreSQL over every live change of `[since, until)`, never rows loaded into the application; the provider only words them. Counts are of live data: an entry that changed live data. Work in an 

## docs/API.md:7180 — Agent access (Product 0.16)

An assistant reaches the instance at `/mcp` (MCP Streamable HTTP, protocol 2025-11-25, stateless, JSON answers) with `MCP_ENABLED`; off, `/mcp`, the resource metadata and `/oauth/register` answer `404` and no `agent` token is issued. **Tools and resources.** The reads below answer live data in their route's shape (with `changeSetId`, see _Writing_ below, a change set's). `describe_access`; with Browse, `list_workspaces`, `describe_model`, `describe_type`, `find_records` (the body of `POST …/quer

