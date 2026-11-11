# Selected source headings and bounded excerpts

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1 — Base 0.16 implementation plan

**Status:** Drafted 2026-10-27 at the user's request, for revision. AP-D3, AP-D12–AP-D26, AG-D5 and AG-D9 are decided by the user and marked so; every other AP-D, AG-D and AO-D below is a recommendation. Planned before 1.0 for now, like 0.14 and 0.15. Idea source: the AI integration discussion of 2026-10-27. First drafted as three releases (0.16–0.18); merged into one on the user's suggestion the same day because the three share one foundation, one permission and one acceptance step, and togethe

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:16 — Why

The engine already proposes: a model draft's inference proposes types, fields and relations from a workbook, and a model mapping's inference scores every pair of types, both landing as steps marked Proposed. Both rest on rules and cannot know that "PICKUP" and "Store collection" are the same thing. The hook for a language model exists (`INFERENCE_ASSISTANT`, 0.10 A6, D95: a factory, no provider bundled, never applies anything). The engine is also an integration engine whose API is the product, s

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:31 — Outcome

**The requirement every package serves (the user's, restated 2026-10-28):** a person says a few words, uploads a workbook, and gets the model and the import. The model has whatever the workbook needs: any number of applications, types, attributes and relations within and across applications. The AI is an add-on on top of the building blocks that already work (profiling, the rule-based inference over every row, model-draft operations, the import profile, the dry run, the import); it drives them t

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:83 — Packages

| Package | Needs | Scope in one line | | --- | --- | --- | | [AP1](#ap1-the-proposal-provider) | 0.12 | **Foundation.** Provider interface, settings, adapters, send levels, call record, permission, jobs, provenance, Settings › AI | | [AP2](#ap2-targets-for-unmapped-values) | AP1 | Ranked target candidates for the unmapped rows of a mapping view, landing as edits in a change set | | AP3, AP4, AP5, AP6, AP7 | — | **Superseded by AP8.** See [History](#history-of-the-assistant). AP4 and AP5 are rem

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:110 — Decisions



## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:112 — Where each decision stands

Checked against the code 2026-10-31. Where this differs from a decision's own text below, this table is current; the text keeps the reasoning. | Decision | Stands? | Now | | --- | --- | --- | | AP-D1 One interface | Changed | Holds for AP2, AG4 and Track O. A session is not a provider call; `AI_PROVIDER` serves those only (AP10, AP-D38) | | AP-D2 Providers | Kept | Plus `AI_AGENT_COMMAND`, which alone turns the assistant on (AP10, AP-D38) | | AP-D3 Send levels | Changed | A task below `values` i

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:150 — Track P: proposals

| # | Question | Recommendation | | --- | --- | --- | | AP-D1 | One interface or one per feature? | **One.** `ProposalProvider.propose(request) -> proposals`, where a request has a `purpose` (`mappingTarget`, `modelNames`, `fieldValue`, `failureTriage`, later ones), a bounded context and the schema of the answer expected. Features differ in the context they build and the step they make of the answer, not in the provider. Why: a feature must not be able to reach a provider on its own, and the dat

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:184 — Track A: agent access

| # | Question | Recommendation | | --- | --- | --- | | AG-D1 | Where does the MCP server run? | **In the same process, mounted at `/mcp` (Streamable HTTP), off by default (`MCP_ENABLED`).** Not a separate server, not a stdio package. Why: one deployment, one set of settings, one token verifier, no second process to secure or to forget (no side servers); an assistant on a laptop reaches it like any client. A stdio bridge can be a thin client later without changing the engine. | | AG-D2 | How doe

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:199 — Track O: operations

| # | Question | Recommendation | | --- | --- | --- | | AO-D1 | What does the model see? | **The facts, not the data.** AO1 sees the diff's operations and the counts the preview already computes (records affected per type, mappings touched, consumer definitions changed). AO2 sees change records (kind, type, field, count, actor, time) grouped in the database, and record names only at send level `values`. *(AO3 sends nothing to a provider: AO-D32.)* Send level per feature is stated in its package;

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:213 — Track P: proposals



## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:215 — AP1: The proposal provider

**Journeys:** an operator configures a provider and sees it ready; a steward without the permission does not see the action; a provider failing leaves the deterministic result standing; every call is visible to the operator. **Scope.** - `engine/proposals/`: the `ProposalProvider` protocol, the request and answer shapes, the registry that resolves `AI_PROVIDER`, the two adapters, the fake, and the structured-answer check (an answer that does not match the requested schema is a failed call, never

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:239 — AP1 record (2026-10-28)

**Delivered 2026-10-28** on the user's "deliver build 0.16 ap1", without a separate detailed plan or mock-up, as 0.12 M1 was: the page reuses the Mail page's pattern. The recommendations AP-D1, AP-D2, AP-D4–AP-D9 and AP-D11 are built as written; the user may reopen any of them. - **Engine** (`engine/proposals/`): `provider.py` (the request, the answer, `ProviderError` and its kinds, the closed answer schema), `context.py` (the send levels; a value read only when the level allows it), `claude.py`

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:318 — AP2: Targets for unmapped values

**Journey:** a mapping steward opens a mapping view with 300 unmapped values, asks for target proposals, and finds a change set whose changes map each value to its best target with a confidence and reason; they correct a few in the grid, and publish through the normal approval. **Scope.** `POST …/mapping-views/{view}/proposals` (job): the unmapped source rows of the chosen context, candidates from the existing candidate search (AP-D9), the provider's ranking, a change set created or chosen by th

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:332 — AP2 in detail (approved by the user 2026-10-28, with the mock-up)

The mock-up is the visual reference (a Design canvas, not kept in the repository): the grid's **Propose targets** button and **Proposed** segment, a target's mark "Proposed by the AI · 86%" with its reason, the dialog (scope, current or new change set, what is sent), progress and result counts, the phone layout (reason folded under "why?") and the history entry. | # | Decision | | --- | --- | | AP2-D1 | **Route** `POST /api/v1/workspaces/{key}/mapping-proposals` → `202` with the job (kind `aiPro

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:357 — AP2 record (2026-10-28)

**Delivered 2026-10-28** on the user's "deliver build 0.16 ap2", after the plan and the mock-up were approved. Backend and frontend were built by Sonnet agents from briefs, reviewed by the lead. - **Engine:** `engine/reads/mapping_scope.py` (`MappingScope`: the binding's edges, eligibility and unmapped sources, shared with the mapping reads), `engine/proposals/mapping_selection.py` (the sources and candidates in one `INSERT … SELECT` into the job's inputs), `mapping_targets.py` (prompt `mapping-

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:429 — AP8: The assistant is a Claude Code session

**Decided by the user 2026-10-31; this section is the current design of the assistant.** It replaces the designs of AP3 to AP7, which are kept under [History of the assistant](#history-of-the-assistant) for their reasons. The requirement in the [Outcome](#outcome) did not change. Reconciled against the code 2026-10-31; nothing was run. **How it works** (`engine/tasks/agent.py`, journey J50.30). The person's words, the workbook, the workspace's model and the API's OpenAPI document go to one Claud

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:464 — AP9: Who did it

- **Provenance (AP-D5, AP-D7).** A session's changes carry no `origin` and act as the shared client. The change-set columns exist, and the import path does not fill them. Accepted changes must read as machine-proposed, asked for by the person, approved by the person, through publication into history. - **One client per session.** All sessions share one client and its grants come and go per session, so sessions overlapping across nodes could use each other's workspace grant. Found by reading the 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:475 — AP9 in detail (planned 2026-10-31, for approval)

Mock-up: [AP9 Who did it](https://claude.ai/artifact/DSPUiWVd2DJUncrCkAxXkT) (a Design canvas, not kept in the repository). **Checked against the code.** The four items above hold, and six more things belong to them: - **The folder does not go with its task.** `task_store.expire` returns only source files, and `remove_folder` is called only on a load and on a discard. A failed or abandoned task leaves its workbook copy and session logs on disk for good. - **Claude Code keeps its own copy.** Each

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:536 — AP9 record (built 2026-10-31; the real try is open)

Built as planned, with three changes found in the work: - **AP-D32:** the stamp is one `before_flush` listener in `records/proposed.py`, not code in `ChangeSetWrites`, so every row those writes make is covered from one place. Tombstones take it in `deletion.py`. The origin holds public IDs, and a read names them as they are now, as `principals.py` does for everyone. A list's records carry the mark without names. - **AP-D37:** expiry does not return folders. The sweep removes any folder without a

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:556 — AP10: One path

- **One switch and one assistant.** `AI_PROVIDER` and `AI_AGENT_COMMAND` are separate today: with only the provider set, a workbook is read by the rules alone and words alone go to the old turns. Settings › AI says what is available and the page is hidden when it cannot work (AP-D21). `AI_PROVIDER` stays for AP2, AG4 and Track O. - **The old design removed.** Whatever only the turns of AP6 to AP7 reach in `design_job.py`, `design.py`, `draft_plan.py`, `design_checks.py`, `links.py`, `matching.py

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:572 — AP10 in detail (planned 2026-10-31, approved by the user 2026-10-31 with AP-D39 and AP-D43)

**Checked against the code and the development database; nothing was changed or run for this plan.** - **The switches.** `POST /ai/tasks` needs `AI_PROVIDER` (`ai_requested`, `409 AI_NOT_CONFIGURED`), and Settings › AI shows "No AI provider" without it, though a session uses no provider. With only `AI_PROVIDER`, words alone reach `_propose`, which reads a saved profile from a reading the task does not have, so it looks set to fail; not run. - **The old design is mostly gone already.** Nothing wr

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:647 — AP10 record (2026-10-31)


## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:663 — AP11: Good models, in time

- **Model shape. Built 2026-10-31, the user's decisions.** The same words gave five types on one run and one type of 87 attributes on another, and both pass the dry run. **Separated by default:** one generic sentence in the prompt makes what a file repeats into types of their own, and a session keeping a repetition flat raises it as a question. **What the workspace holds decides the start:** with records the session adds to the model; with none, words asking for a model may get a new one. The pr

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:683 — AP11 in detail (planned 2026-11-01, for approval)

Model shape is built; this plan is the rest: the time limits. **Requirement served:** "a few words + workbook → the model and the import", within 1 to 2 minutes for a workbook like the example model and 5 at most for a complex one, without the person's wait. Reached from the existing task page; no other capability calls it. No screen changes, so no mock-up. **Where the time goes (read from the session logs still on disk and `ai_calls`, `jobs`; no new AI run):** | Run | Total | Model generating | Engi

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:734 — AP11 record (2026-11-01)

**The time limits are not met.** The fixes are built and the results hold, but the time did not move. **Accepted and closed by the user on 2026-11-01 with the limits unmet.** Sonnet at medium, prompt `agent/4`, the user's words, fresh workspaces, none published. | Try | Proposal + load | Limit | Model generating, proposal | Engine jobs | Output tokens, proposal | Cost at API prices | Earlier run | | --- | --- | --- | --- | --- | --- | --- | --- | | The example model, `ap11-example` | 821 + 66 = 887 s | 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:770 — AP12: Reshaping, and asking from the workspace

- **Moving records between types.** The exit gate asks for it. The 0.8 restructuring does it. Prove it through a session with a before/after count on a real model, and make the reshaping's three phases work under AP-D29. - **"Change this model…".** A way from the workspace to ask the assistant, with the workspace's model as its start. It is the existing task, offered there, and lands in the proposal page. WM1's Apply does not serve it: a session installs without activating, and WM-D2 keeps a tas

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:779 — AP12 in detail (planned 2026-11-01, approved by the user the same day with the mock-up and AP-D46's two ways)

Mock-up: [AP12 Change this model](https://claude.ai/artifact/9U4YPasLC7NZADihz9rXiT) (a Design canvas, not kept in the repository). **Requirement served:** the exit gate's "reshaping a workspace's model is an instruction too": words from the workspace become a proposal, a person never needs the editor's draft, install and activate path, and a before/after count on a real model shows nothing lost. **What the code does today (read 2026-11-01; nothing was run):** - **The session stops short of a re

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:837 — AP12 record (2026-11-01)

**Built as planned, with the changes below.** Journey cases J50.46 to J50.52 were written from the plan's text first (`backend/tests/journeys/test_j50_ai_reshape.py`, 7 cases on two configurations, a stand-in session working through the API with the token the engine gives it) and run before the engine changed: J50.46 to J50.50 and the retiring half of J50.52 failed, as the engine did not know `moves`, `RELEASE:` or `THEN_RELEASE:`. J50.51 and the discard half of J50.52 passed before any change, 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1002 — AP13: Always a way out (AP-D22)

**Revised by the user 2026-11-02.** Acceptance is not whether the assistant's result matches what the person had in mind; the person and the assistant find their common ground together. It is that the application gives them everything to get there: **at every state of a task there is a way out, on the page itself and easy to find, without a fall-back.** Starting the task again, or doing the step by hand somewhere else (the model editor's draft, install and activate path, a list of records change

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1027 — AP13 in detail (planned 2026-11-02, approved by the user the same day with the mock-up)

**The review's findings (read from the code, 2026-11-02; the failed page and the discard guard checked by hand).** A proposal with questions, a correction in words and a proposal the engine refuses already have their way out. Not so: | State | Today | Verified | | --- | --- | --- | | The session fails (no proposal, a consumer API it would break, moves it cannot make, an empty load) | "The assistant could not finish." The reason is in the task's notes, which this page does not show (`AiTaskPage.t

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1098 — AP13 record (2026-11-02)

**Built as planned, with the changes below; the real walk-through was run after (below).** Journey cases J50.53 to J50.60 are in `backend/tests/journeys/test_j50_ai_way_out.py` (8 cases on the two generated configurations, 16 runs; a stand-in session working through the API with the token the engine gives it, held and stopped from outside as a person would). The cases were written from the plan's text; they were not confirmed to fail first, as the test file was written after the engine change in

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1159 — WM1: Change a workspace's model from the workspace

**Added 2026-10-28 at the user's request; not AI, a basic the release needs.** Found on the user's first real import: to change the model of the workspace they were in, a person had to know to go to Settings › Model, find or make a draft of the right release, open the editor, then install, then activate in the workspace. Even the user, who knows the application, could not tell what to do or where. **Journey:** a person holding Model authoring and Model release in a workspace opens the workspace,

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1200 — WM1 record (delivered 2026-10-31)

**Exercised:** journey tests J36.12 (12 cases on generated A and B, confirmed failing first) and the J08, J36, J37, J40 and J50 modules, boundaries and the OpenAPI lock; unit tests of `ApplyDialog` and the selector's menu; runner `wm1-edit-model` (menu, editor, Apply by keyboard at 1440px on two configurations, a migration, the Settings button, 390px, axe on the dialog, no 4xx/5xx); the changed runners `j1u-export`, `j4-import`, `j6-people-workbook`, `j6a-people-columns`, `k6-relationship-filter

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1228 — WM1 in detail (planned 2026-10-31; approved by the user 2026-10-31 with the mock-up)

Mock-up: [WM1 Edit model](https://claude.ai/artifact/Kzt6bM9BS8jxvh6K8ast3y) (a Design canvas, not kept in the repository). Reference patterns: the activation dialog (`ActivateDialog`) for the confirmation and the migration page for records that must move. **What already works and stays:** the draft operations and editor, `compile` (its `compatibility.workspaces` gives each workspace's check before anything is installed), `installation`, `activation`, the migration preview and confirmation, and 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1245 — Decisions (recommended, approved with this plan)

| # | Decision | Why and what it costs | | --- | --- | --- | | WM-D1 | **A draft remembers one workspace** in `model_drafts.workspace_key` (foreign key, `ON DELETE SET NULL`), with a partial unique index: a workspace has at most one remembered draft. | The rule "no second, competing draft" is held by the database. One column, one index, one migration. | | WM-D2 | **Which draft opens.** (1) The remembered draft while it is current: its base is the release the workspace runs, or a release installe

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1256 — The Apply dialog

A new `ApplyDialog` on the existing pieces; the parts it shares with `InstallDialog` and `ActivateDialog` (`summarizeChanges`, `ConsumerContracts`, `useReleaseIdentity`, the left-behind list and the migration reasons) are extracted once, not copied. It reads `compile` and shows, in order: what changes in the model; what happens to the records; change sets left behind; the workspaces not changed; the release identity folded under "Becomes release ‹name› ‹version›". | State | The main action | Aft

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1274 — Tests (cases for approval)

Journey tests in `tests/journeys/`, new variants of J36, each on two model configurations: 1. **Apply to one workspace.** Given two workspaces on one release, when the first's draft is opened, a field added, it is installed and activated there, then the first runs the new release with the field, the second is unchanged, and opening again answers 200 with the same draft. 2. **An existing draft is reused.** Given a draft of the running release remembering no workspace and one of another release, w

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1295 — Delivery

- **Backend:** the migration, written in one go; `engine/model/drafts.py` (the choice in WM-D2); the sweep's condition in `engine/tasks/store.py`, with a unit test; the route and `draftResponse` field; the workspace-aware check in `management/access.py`; the journey tests, confirmed failing first. - **Frontend:** the ⋯ menu with Import and Export moved into it, the Edit model button in `WorkspaceAdmin`, `ApplyDialog`, the route parameter, the editor's crumb, header and main action (desktop and p

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1309 — Track A: agent access



## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1311 — AG1: The server and its authority

**Journeys:** an operator enables MCP and creates an agent client; the client connects and lists only the tools its grants allow; with MCP disabled the endpoint does not exist; revoking the client stops it on the next call. **Scope.** `management/routers/mcp.py` (the Streamable HTTP endpoint on the MCP Python SDK, pinned in pyproject's ranges with `pip check`), the `agent` audience in `engine/identity/tokens.py`, the `Agent` predefined role and its action group in the catalogue, the audit `chann

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1323 — AG1 in detail (planned 2026-10-31, approved by the user the same day with the mock-up)

Mock-up: [AG1 Agent access](https://claude.ai/artifact/TqCG2VCdQV1Cti6Y6cgnCo) (a Design canvas, not kept in the repository). Reference patterns: the AI page (`AiPage`) for a setting read from the environment, the Clients page for a client's detail, secret and access, which are reused and not copied. **Checked against the code and the MCP specification of 2025-11-25.** Four things in the scope above do not hold as written: - **"The existing OAuth flow" cannot sign in an assistant.** `check_reque

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1404 — AG1 record (2026-10-31)

**Delivered as planned**, with the build's tests below; the one real sign-in is the user's step and has not happened yet. Frontend built by a Sonnet agent from a brief. **Where it differs from the plan:** - `GET /agent-access/clients` was added: the page's call counts per client need it. - The five `MCP_*` settings sit in the `ai` settings group, beside the rest of this release's settings. - AG-D11's `Host` check is left out: only `Origin` is checked. A proxy's forwarded host differs by deployme

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1424 — AG2: Read tools and resources

**Journeys:** "what is the code of this value in the webshop system?" is answered from a consumer definition; "which values of this list have no mapping to the webshop?" is answered from mapping coverage; the model description is readable as a resource. **Scope.** The generator from consumer definitions (one tool per definition, schema from its fields, authorization from its grant), the curated tools (AG-D4), the model, applications, object types and views as MCP resources, structured results wi

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1435 — AG2 in detail (planned 2026-10-31, approved by the user the same day)

No screen changes, so no mock-up: Settings › Security › Agent access already lists whatever tool is called, and the client page already grants a consumer API to an agent client. **Checked against the code.** Five things in the scope above do not hold as written: - **A person can never hold a consumer API grant** (`CONSUMER_API_CLIENTS_ONLY`, D306). "Authorization from its grant" would give a person signing in through an assistant no generated tool, and that is the route the AG1 real try used (AG

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1505 — AG2 record (2026-10-31)

**Delivered as planned.** AG-D19 was taken as recommended: the user approved the plan without answering it separately, so it stands open to their correction. **Where it differs from the plan:** - The moved check is in a new module, `engine/reads/consumer_request.py`, not `consumer_parameters.py`, which `consumer_lists` imports: the check needs `consumer_lists`. - **AG-D24 revised by the real try:** `resources/list` names each workspace's model only, and applications, record types and views are r

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1531 — AG3: Changes prepared and submitted for approval

**Journey:** an agent asked to add five missing values creates a change set, adds the five, reads the validation and submits it; a steward is notified in the inbox, opens it, edits one value and approves; live data changes only at that approval. **Scope.** Tools: create/select change set, add or change an object, set a field, add a relation, read the change set's validation. Optimistic concurrency applies (versions are inputs); conflicts return the engine's own error code and message. No approve

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1541 — AG3 in detail (planned 2026-10-31, approved by the user the same day, with AG-D27 as written)

**Checked against the code; nothing was changed or run for this plan.** Seven things in the scope above do not hold as written, or need a rule: - **`_run` cannot write.** It never calls `set_writer`, and without a writer a change-set write is refused `WRITER_UNKNOWN`. It always rolls back at the end, and the engine's write functions commit themselves (AG-D28). - **`_fitted` is unsafe for a write.** It runs a tool again to shrink a page, and refuses a long answer after the tool has run, which aft

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1610 — AG3 record (2026-10-31)

**Delivered as planned; the real try passed and the user accepted it (2026-11-01).** Tools, route splits, frontend, tests and documents built by Sonnet agents from briefs; `_run`, the origin, the channel and the review by Opus. **Where it differs from the plan:** - A stale version answers two codes: `CHANGE_SET_VERSION_CONFLICT` on a write, and `VERSION_CONFLICT` with `currentVersion` on a submission. Each is the engine's existing code, and J53 asserts both. Test 3 above names the first only. - 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1635 — AG4: Natural-language search

**Journey:** a steward types "values changed last month without a webshop mapping" in the search box and sees the filters it became, editable, and the results. **Scope.** The `queryTranslation` purpose of the AP1 provider (`structure` send level: the question and the list's filterable fields, no record values); the answer is the existing filter parameters, validated like a hand-typed filter, shown as chips the person edits. The engine answers; the model only builds the query. A question it canno

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1645 — AG4 in detail (planned 2026-11-01, approved by the user the same day with the mock-up)

The user approved this plan and the mock-up (three boards: a question answered as pills, a part it cannot express, a phone) on 2026-11-01, including the extension of the list filters. **What was found.** Today's list filters cannot say the journey's question. A relationship filter says "related to any of these records", "none" or "any", never "none **under** this record", which is what "without a webshop mapping" means: the mapped records stand under a system, and the question names the system. 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1677 — AG4 record (2026-11-01)

**Delivered as planned, in a worktree beside AP11's delivery, then applied to the shared checkout in a gap between AP11's tries; the real-provider try is done.** On the OpenAPI lock, re-baselined last on top of AP11's: the document differs from AG4's own only in AP11's schemas. On the merged code: the lock, `test_boundaries` and J54, 35 passed. **Where it differs from the plan:** - The journey tests were written after the first backend pass, not before it, so "confirmed to fail first" was not sh

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1697 — AG4 revision (2026-11-01): the user's report on the real provider

**Closed by the user on 2026-11-01.** The user tried the question "show me all the services types which are above 30 minute duration" on the `default` workspace's example types and was refused ("above 30 minute duration": Duration is a relationship to records named 10 min, 15 min, 30 min, 45 min, 60 min and 180 min); "values changed last month without a CRM mapping" was refused because the view does not declare the relationship to mappings. His words: "I did not expect comparison, I

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1712 — Track O: operations



## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1714 — AO1: Model change impact summary

**Journey:** a model administrator opens a release's activation preview for a workspace; beside the counts and the list of operations, a short account says: "Two attributes are added to Delivery method (optional, no data change); the mapping to the webshop gains one relation; 3 consumer definitions change shape, one of them removing a field" with each statement linking to the operation or definition. It never says a change is safe; it says what the facts are. **Scope.** The fact set from the exi

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1726 — AO1 in detail (planned 2026-11-01, approved by the user the same day with the mock-up)

Mock-up: [AO1 Impact summary](https://claude.ai/artifact/9cvJxd3mTPfcKE2LwtwJyv) (a Design canvas, not kept in the repository; three boards: the account beside the check, before asking and when it fails, a phone). **Requirement served:** the Outcome's "a model administrator reads a plain-language impact summary beside the activation preview". **What the code does today (read 2026-11-01; nothing was run):** - **The facts exist, in three places.** `GET /model-releases/{id}/diff` gives `changes` (`

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1780 — AO1 record (2026-11-01)

**Delivered as planned**, with the differences below. The tests were written after the first backend pass, not before it, so "confirmed to fail first" was not shown. **Where it differs from, or fills, the plan:** - **Which models are compared.** A release is compared with the release the workspace runs; a draft with the release it is based on (the newest of its model without a base), as its compilation is. The workspace's data is checked against the candidate by `analyze_compatibility` against t

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1809 — AO2: What changed, an account of history

**Journey:** a data owner picks "last week" on a workspace; the account says "Translations: 200 labels changed by 3 people, 190 of them in one bulk import on Tuesday; Master: 4 values retired; one change set (CS-18) was sent back", each statement linking to the records and the change set. **Scope.** Fact aggregates from history and the change feed, grouped in PostgreSQL by type, kind, actor and source (job, change set, direct), restricted to what the requester may read; the `historyAccount` purp

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1820 — AO2 in detail (planned 2026-11-01, approved by the user the same day with the mock-up and AO-D21 to AO-D23 as recommended)

Mock-up: [AO2 What changed](https://claude.ai/artifact/J1cg6aHNt4YNqGoJiKd1Fj) (a Design canvas, not kept in the repository; four boards: the workspace's Activity, before asking and when it fails, a record's history, a phone). **Requirement served:** the journey above, and AO-D1 to AO-D9. **What the code and the dev database hold today (read 2026-11-01, read-only queries, no server started):** - **The audit holds staged and live work side by side.** On the dev database, of 261,417 entries, stage

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1875 — AO2 record (2026-11-01)

**Delivered as planned**, with the assistant's tool as revised (below). The journey cases J56.1 to J56.9 were written first and confirmed to fail (20 failed, the route being absent) before the code; the cases were not altered, apart from the tool clause of J56.9, reworded with AO-D28 and met by the `history_facts` tool (2026-11-02). **A spec gap, decided 2026-11-02: AO-D28 revised to a facts-only tool.** An assistant's token is cut to the `agent` role's groups, Browse and Work in change sets (`A

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1903 — AO3: Notification digests

**Journey:** a steward sets daily digests; the next morning one mail says "3 change sets wait for your approval, 1 job failed (import of the labels file, 14 rows rejected)", then lists the notices as today with their links. **Scope.** The `digest` setting per person, the scheduled job (an existing worker with the lease rules: one digest per person per period, no duplicates across nodes), the `digest` purpose (kinds, counts, titles; send level `structure`), the mail template, the outbox. With the

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:1915 — AO3 in detail (planned 2026-11-02, approved by the user the same day with the mock-up; AO-D38 and its place on the home page decided by the user)

Mock-up: [AO3 Notification digests](https://claude.ai/artifact/FMHbeBUsYt7ErMCXrPnd7M) (a Design canvas, not kept in the repository; three boards: Settings › Notifications › Email with the three-way choice, the digest's time and the followed workspaces; the daily digest as plain text; the home page's workspace cards with Follow). **Requirement served:** the Outcome's "a person who opted in receives one digest instead of many mails", and the exit gate's "with no provider … digests are the plain l

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2011 — AO3 record (2026-11-02)

**Delivered as planned** (AO-D31 to AO-D38 as approved, no AI, no new permission). The journey cases J57.1 to J57.8 were written first and confirmed to fail (16 failed, the digest and the follow routes being absent) before the code; no assertion was weakened afterwards (the subject comparison was made independent of the product's name, below). **Where it differs from, or fills, the plan:** - **The product's name in the subject** is the one every mail uses (`templates.product`: the model's name w

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2040 — Door check (ADR-032)

Provenance (`origin`, AP-D5, and AP9 for a session's changes) is the first use of the value-provenance door and is additive, kept outside a record's own values. Audit gains a `channel`, additive. Identity, attribute storage, bulk APIs, the consumer API `match` declaration and mapping coverage states are read or reused, not changed. Summaries (Track O) are derived and stay outside history, the model and the records. No door closes.

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2048 — Tests

Journey-driven through the API, at most about a quarter of a package. Track P and O use a deterministic fake provider (AP-D11, AO-D9): per package the happy journey, the provider-failure journey, the permission-hidden journey, and where data is read a send-level journey; Track O adds the uncited-statement, the visibility and the fact-completeness tests. Track A uses a test MCP client (AG-D10). The context builder's level tests are unit tests. A session is tested with a scripted command (J50.30).

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2057 — AI usage log (for hosting cost planning)

**Why (the user, 2026-10-29):** refiroo may be hosted on a subscription that includes the AI provider, so what a real task costs is planning data. Every real-provider try in a package or in R adds one row here. A row is reported to the user with the try. **How it is measured.** The call records (`ai_calls`, Settings › AI) give each call's purpose, duration and tokens in and out; the tokens in are the sum of plain input, cache writes and cache reads. Through the Claude Code provider, each call al

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2132 — R: Build acceptance and release

Full review of every change since 0.15 (it is one review for three tracks, the main saving of merging); the contract lock marked additive (the `agent` audience, `/mcp` and the new routes); documentation (PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, OPERATIONS for the AI and MCP settings and connecting an assistant, API, USER_JOURNEYS, API_JOURNEYS, PROJECT_STATUS, CHANGELOG); **one** bounded real-provider try and **one** real-assistant try, each only on the user's go-ahead with its cost stated 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2140 — R record (2026-11-02)

**Review.** Every change since 0.12.0 (`deff1ff7`, 38 commits and AO3 uncommitted; 0.13–0.15 were never built), by five reviewers by area: the assistant sessions, the provider and summaries, agent access over MCP, migrations and digests, the frontend and its runners. 45 findings were fixed (R-F1–R-F45, listed in CHANGELOG [0.16.0] "Fixed (the 0.16 release review)"); none turned out not to be a defect. The four that broke the release's own limits: - R-F1: an assistant turned its refresh token int

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2201 — Exit gate

- A few words and a workbook give the model and the import, with as many applications, types and relations (across applications too) as the workbook needs; tried on the user's own workbooks (AP-D22). - With no provider and MCP off, no screen shows an AI action, no request leaves the instance, `/mcp` does not exist, the existing inference behaves as before, and digests are the plain list. - No value above the configured send level reaches a provider (the context builder's tests). - Every proposal

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2238 — History of the assistant

**Superseded by [AP8](#ap8-the-assistant-is-a-claude-code-session). Kept for the reasons and findings, not as the plan.** Nothing here is open work: what is still open moved to AP9 to AP13. What replaced what: AP3 to AP5 folded into AP6 (AP-D27), and AP4 and AP5 were then removed from 0.16; AP6 as first planned was a plan of steps; AP6a read by rules with the AI fixing refusals; AP6 and AP6r designed in turns, with the steward accepting the model first; AP7, the engine matching first with the AI

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2247 — AP3: Model authoring and model mappings

**Folded into AP6 on 2026-10-28 (AP-D27);** the text below is kept as the scope the assistant's tools cover. **Journey:** a model administrator imports a workbook; the inference's proposals now carry better names, descriptions, enum detections and relation guesses, each with a reason, in the editor as Proposed steps. A model mapping's candidate list is re-ranked by meaning, with the reason shown. **Scope.** The 0.10 assistant's request (headers, a bounded number of rows, the proposals' types) be

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2261 — AP4: Values for empty fields and missing related records

**Removed from 0.16 by the user 2026-10-31.** Never built; the text is kept as history. **Journeys:** (1) a steward filters the records with an empty description, asks for drafts and gets a change set of proposed values they edit in the list's cells. (2) A localisation steward filters the records with no German translation and gets proposed translations as new related records. **Scope.** A bulk action on a collection selection or filter (the 0.9 bulk-dialog pattern). Two targets, both chosen in 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2278 — AP5: Dry-run triage

**Removed from 0.16 by the user 2026-10-31.** Never built; the text is kept as history. **Journey:** after a dry run of a 40,000-row file with 3,100 failures, the person asks for a summary and sees eight groups ("200 rows: trailing spaces in `code`"), each with a count, three example rows and, where one exists, a suggested step (a trim rule, a value map entry). **Scope.** The dry run already checks every row (D67, checks cover the whole set). The grouping is deterministic: failures grouped in Po

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2292 — AP6: Instruction-driven tasks

**What it is.** The way people already use an assistant: type what you need in loose English and attach what you mean. It is the engine's inference, import, mapping, batch and change-set machinery driven by a sentence, with every step visible and nothing run until the person confirms. **What exists to build on (checked 2026-10-27 against API.md and MODEL_AUTHORING.md):** | A person says | Becomes | Exists | | --- | --- | --- | | "Create a model for this and import it" | A model draft from the wo

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2352 — AP6 in detail

**Status of this part:** drafted 2026-10-27 after the user approved AP-D12–AP-D22 and the mock-up of the task page and of the editor with its side pane (the mock-up is the visual reference; it is not kept in the repository). AP-D23–AP-D26 below were approved by the user the same day. **What the code already offers (read 2026-10-27, so the plan names real places):** - A model draft's step has an `origin` JSON (types `patch`, `undo`, `proposal`; the proposal origin carries the anchor, keys, elemen

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2384 — Decisions (new, approved)

AP-D23 to AP-D28 stand in [Decisions](#decisions).

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2388 — The plan, as data

A **plan** is a numbered version of a task's steps (a new version for every revision, the earlier ones kept for undo). A step is `{id, kind, owner, params, reason, evidence, confidence, status}`: | `kind` | `params` are | Applied as | Checked by | | --- | --- | --- | --- | | `modelOperation` | one model-draft operation (kind and parameters, the 67 kinds) | `history.apply_steps` on the draft, origin `assistant` | the draft's validation and the dry run | | `profileSource` | a draft profile operati

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2405 — Routes (management API; all need the AP1 permission and the owner check of AP-D23)

| Route | Purpose | | --- | --- | | `POST /api/v1/ai/tasks` | Create a task: instruction, source file IDs, target (a workspace, optionally a draft or a change set). `202` with the job. | | `GET /api/v1/ai/tasks`, `GET /api/v1/ai/tasks/{id}` | The person's tasks, newest first (ADR-030 paging); one task with its latest plan, reading, question and check. | | `POST /api/v1/ai/tasks/{id}/messages` | A follow-up instruction or the answer to a question. `202` with the job; the plan gets a new version. 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2420 — The planning tools (AP-D15, AP-D19)

Read-only and in-process, one implementation each, later exposed by Track A: `describeModel` (applications, types, attributes, relations, bindings), `describeFile` (sheets, blocks, columns, the profile's statistics and a bounded number of rows), `findRecords` (the model-aware query with a count and a bounded sample), `trialPlan` (the dry run or preview of the current plan, returning the summary and the first refusals). The loop is bounded by `AI_MAX_STEPS`; a tool call that would exceed the send

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2429 — The workbook flow (AP-D27)

What the assistant adds at each step of New from a workbook (MODEL_AUTHORING § The editor, § Operation catalogue, § Pattern catalogue): | Step | The rules today | The assistant adds | | --- | --- | --- | | 1 Start | The dialog's choices, made before anything is known | Proposes the choice (new application, new model, additions) with its reason | | 2 Read | Sheets, blocks, lists; a sheet without a table is skipped | Reads skipped and prose sheets; which lists belong together or are not data | | 3

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2450 — The workbook assistant by what the file means (designed 2026-10-28, replacing the step-based slice)

**Why the earlier slice went.** It cut the work along the rules' steps (types, applications, hierarchy) and so covered a part of one case, a totally new file, and only the model's shape: no import, no update, no extension of a model that holds data. The user named the cases (2026-10-28); the design starts from them. **Requirement trace.** "A few words and a workbook give the model and the import", against the data a workspace already holds: every case below ends in the model the file needs and i

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2529 — AP6: the assistant designs and loads (one package, replacing slices AP6b–AP6e; planned 2026-10-29)

**The requirement, checked line by line.** The user's words in the [Outcome](#outcome): the five cases (an update; additions; a new relation; something new but related; something totally new), the eight scenarios of 2026-10-27, and "a few words, an xls, the model and the import; we don't build limitations". Every one is an acceptance case below. No case is left to a later slice; there is none. **Why AP6a cannot be extended into it.** In AP6a the engine's rules decide what a file is, and the lang

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2624 — AP6r: the assistant proposes the model, the steward shapes it, then it loads (planned 2026-10-30)

**Why.** The AP6 loop measured success by "the engine refuses nothing". On the user's samples it loaded cleanly and still built the wrong model: flat lists where the data groups rows, new types duplicating records the workspace holds, relationships readable from one end only. Whether a model is good is not something a dry run checks, and the steward saw the model only after the load. The requirement (§ Outcome) asks for what a Claude Code session does: analyse, decide the structure, let the pers

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2675 — AP6 progress (2026-10-29, in delivery)

**The core is built and works on the user's own workbooks** (real tries in the AI usage log): - **The example model** into an empty workspace (cases D/E), checked with nothing refused: - a new application, with an example type and an example category type and their attributes; - the translation join, made required as the model's other translation joins are; - the 7 languages and translation groups the structure needs; - 1,756 records and 1,500 translations; - one real question (category trans

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2799 — AP6a record (2026-10-29)

**Delivered 2026-10-29** after the user approved the plan, the mock-up and J50.1–J50.11. After the user's first try on their own workbook ("everything looks off": junk records from note rows, a report hundreds of lines long), the user approved a revision on the same day (mock-up boards 5–7, J50.12–16, "its good"). Backend and frontend were built by Sonnet agents from briefs and reviewed by the lead. - **Removal first:** the naming helper (`inference/assistant.py`, its option, read fields, texts 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2900 — Work packages (as first planned 2026-10-27; superseded by the slices above)

| Package | Needs | What changes | Journeys it must pass | | --- | --- | --- | --- | | **AP6a** Task, plan and planning core | AP1 | Tables for tasks, messages and plan versions (migration), the `aiTask` job kind, the routes above, the plan schema, the four tools, the revision rule (AP-D26), retention (AP-D24), limits (AP-D25), the fake provider's scripted plans; a plain question answered in the thread from the read tools (AP-D27) | A question is answered and changes nothing; a task is created, 

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2915 — Tests

Journey-driven with the fake provider, which returns a scripted plan for a scripted instruction (the test supplies both): per task kind one journey through the API, from `POST /ai/tasks` to the records in the change set, asserting the plan's steps, the check's counts and the final records; plus the journeys named in the table. Component and browser tests follow the user journeys of AP6d and AP6e (two object types, as the repository rule asks). Test work stays within about a quarter of each packa

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2926 — Composable domains (ADR-032)

Plans use only generic steps, so the example model's translation and system-mapping cases are configurations of `relatedRecord` and `relation` bindings, as for the import. Provenance (AP-D5) is additive. Identity, attribute storage, the consumer API `match` declaration and mapping coverage are not touched.

## docs/BASE_0_16_IMPLEMENTATION_PLAN.md:2933 — Said plainly: what the user still cannot do after AP6

- Hand a task to a colleague, or run one on a schedule. - Use a document or an image as data. - Ask for something the engine has no operation for; the assistant says so. - Rely on a small local model; AP-D21 hides the page when the provider cannot do tool calls.

