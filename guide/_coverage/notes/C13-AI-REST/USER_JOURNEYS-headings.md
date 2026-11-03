# Selected source headings and bounded excerpts

## docs/product-functionality/USER_JOURNEYS.md:2439 — AI proposals



## docs/product-functionality/USER_JOURNEYS.md:2441 — J48 — Use AI proposals

**Actor:** an operator, who sets the provider up in the environment and watches what it is sent. **Channel:** the environment (`AI_*` settings), UI (Settings › AI, under Administration), API (`GET /ai/status`, `GET /ai/calls`, `POST /ai/test`, `GET /system` `ai`). **Status:** delivered by 0.16 AP1 (2026-10-28); the inference's better names for the types it proposes, its first feature, were removed in 0.16 AP6a, and the inference runs on its rules alone. Each feature that asks the provider has a 

## docs/product-functionality/USER_JOURNEYS.md:2471 — J49 — Targets for unmapped values

**Actor:** a mapping steward holding Use AI proposals and Work in change sets. **Channel:** UI (the mapping grid's Propose targets and Proposed segment), API (`POST /workspaces/{key}/mapping-proposals`, `GET …/mapping-coverage` `proposed`, `origin` on target summaries and history). **Status:** delivered by 0.16 AP2 (2026-10-28). 1. A steward opens a mapping view with unmapped values and asks for target proposals into a new change set, or one they already have; a job asks the provider about the u

## docs/product-functionality/USER_JOURNEYS.md:2507 — J50 — Load a workbook, or change records, with the assistant

**Actor:** a steward holding Use AI proposals and Bulk and import in the workspace (and Work in change sets to accept; Model release to activate what the load installs). **Channel:** API (`POST /ai/tasks`, `GET /ai/tasks`, `GET /ai/tasks/{id}`, `POST /ai/tasks/{id}/answers`, `/model`, `/accept`, `/retry`, `/discard`, `/cancel`, `GET /ai/tasks/{id}/changes`, and the draft the task opens at `GET /model-drafts/{id}`); the task page is the same journey in the browser. **Status:** delivered in 0.16. 

## docs/product-functionality/USER_JOURNEYS.md:2661 — J51 — Reach the engine from an assistant

An operator turns agent access on (`MCP_ENABLED`). A system's assistant connects with an agent client; a person's assistant finds the sign-in from the protocol's own metadata and the person signs in for it. Either sees only what its grants allow, cut down to reading and preparing changes, and stops on its next call once revoked. - **J51.1 Off, nothing exists**: without `MCP_ENABLED`, `/mcp`, its metadata and registration do not exist, and no `agent` token is issued. - **J51.2 An agent client**: 

## docs/product-functionality/USER_JOURNEYS.md:2673 — J52 — An assistant reads

An assistant connected as in J51 answers from what the engine holds, in the API's own shape, on live data. - **J52.1 A value's code**: a tool generated from a consumer API definition answers by terms, by list and by ID as the consumer API does. It is offered with Browse or the API's grant in the workspace; a client holding only the grant lists nothing else, and a workspace it may not read is refused. - **J52.2 Unmapped values**: naming only a mapping view, `mapping_coverage` with `state=unmapped

## docs/product-functionality/USER_JOURNEYS.md:2684 — J53 — An assistant prepares a change

An assistant connected as in J51 prepares a change in a change set of its own and submits it. Live data changes only when a person approves. No tool approves, publishes, withdraws, removes or writes live. - **J53.1 Five missing values**: a person through an assistant creates a change set, adds five records, validates and submits; live data is unchanged. A steward has the inbox notice, edits one value and publishes, and live data changes then. History says the assistant prepared it, who asked and

## docs/product-functionality/USER_JOURNEYS.md:2694 — J54 — Ask in words

**Actor:** a steward who may browse a workspace and holds Use AI proposals there. **Channel:** UI (a table list's Search | Ask switch), API (`POST /workspaces/{key}/query-translations`, and the list's `filter.` parameters, including `filter.related:<key>.under` and `.notUnder`). **Status:** delivered by 0.16 AG4 (2026-11-01). 1. On a table list the steward switches the search box to Ask and types a question ("values changed last month without a webshop mapping"), then presses Enter. 2. The provi

## docs/product-functionality/USER_JOURNEYS.md:2749 — J55 — An account of a model change

**Actor:** a model administrator who may activate releases in a workspace and holds Use AI proposals there. **Channel:** UI (Explain this change in the activation dialog and in Apply), API (`POST /model-releases/{id}/impact-summary`, `POST /model-drafts/{id}/impact-summary`). **Status:** delivered by 0.16 AO1 (2026-11-01). 1. The administrator opens the activation dialog of a release for a workspace, or Apply for a draft. The check of the workspace's data and the consumer APIs stand as before; n

## docs/product-functionality/USER_JOURNEYS.md:2794 — J56 — What changed in a period

**Actor:** a person who may browse a workspace and holds Use AI proposals there. **Channel:** UI (What changed, above the workspace's Activity and on a record's History), API (`POST /workspaces/{key}/history/account`, `POST /objects/{objectTypeKey}/{id}/history/account`), the `history_facts` tool of an assistant (the facts only, with Browse). **Status:** delivered by 0.16 AO2 (2026-11-01). 1. The person opens the workspace's Activity, or a record's History. Nothing is sent to a provider. 2. They

## docs/product-functionality/USER_JOURNEYS.md:2840 — J57 — Notification digests and following a workspace

**Actor:** a person who is mailed for their inbox (J46.10). **Channel:** UI (Settings › Notifications › Email; Follow on a workspace card on Home), API (`GET`/`PUT /me/notification-mail`, `GET /me/followed-workspaces`, `PUT`/`DELETE /me/followed-workspaces/{workspaceKey}`, `following` on `GET /me/workspaces`). **Status:** delivered by 0.16 AO3 (2026-11-02). 1. On Settings › Notifications the person chooses, for each kind of notice, whether it is mailed at once (as today, and what every kind stay

