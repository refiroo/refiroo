# C13-AI-INTEGRATE reconciliation

Code takes precedence over historical wording. Each row records the heading read and its reader-facing destination.

| Source heading | Reconciliation and destination |
| --- | --- |
| guide/AGENTS.md; COMPLETE-COMMON.md | Read in full. This wave explicitly supersedes the common after-0.16 deferral. Scoped build and verify required. |
| API.md — Agent access | Read full section; checked mcp_tools.py, routers/mcp.py, agent_access/lookup.py and routers/agent_access.py. Document current tools, agent tokens, ownership, pagination, provenance and administration in assistants-and-agents. |
| OPERATIONS.md — Agent access | Read section. Tool-call records retain argument names, not read values; reads are not separate data-audit writes. AI_SEND_LEVEL is not an external MCP assistant policy. Link run/ai for costs and retention. |
| CURRENT_FUNCTIONALITY.md — F30 | Read full section. Distinguish MCP preparation from the built-in task assistant. No UI channel filter or mark on Changes. |
| USER_JOURNEYS.md — J51 | Read heading and all variants; connect as person or client, discovery, revocation, registration and rate ceiling. |
| USER_JOURNEYS.md — J52 | Read heading and all variants; consumer lookup tools, resources, live reads and cursor continuation. |
| USER_JOURNEYS.md — J53 | Read heading and all variants; own change sets, version refusals, submission and human decision. |
| CHANGELOG.md — 0.16 Added (agent access) | Read heading; earlier "two tools so far" is historical, not the present tool list. Use the current API and code. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — Track A / AG1 scope | Read scope and located detailed decision headings; present server mount and authority come from current code, not superseded task designs. |
| API.md — AI proposals / Loading a workbook, or changing records, with the assistant | Read current task contract including route table, states, proposal, results and saved layouts. Code checks: routers/ai_tasks.py; tasks/store.py; design_job.queue_accept, sync and loaded-task cleanup; agent.end_session. New assistant-tasks page and file/job cross-links. |
| OPERATIONS.md — AI proposals | Read full section. Separate assistant command, provider and MCP switches; send-level ceilings, costs, call content and session retention link to run/ai. Older structure-only question paragraph is superseded by current query-translation contract. |
| CURRENT_FUNCTIONALITY.md — F29 | Read full section. Some limits are stale: correction words are possible after the proposal, provider includes search and accounts. Current routes and later delivered decisions win. |
| USER_JOURNEYS.md — J50 | Read main sequence and targeted variants 19-24, 30-60; current task sequence and migration vs change-set completion. No empty-change-set promise for a whole-type migration. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AP10 in detail | Read targeted discovery and decision excerpts. Removed rules-only planner is historical, not a feature to document. Engine saves repeatable profiles. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AP12 in detail | Read targeted reshaping decisions. Whole-type migration can load without a changeSetId. Equal final and change-set releases require no removal activation. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AP13 in detail | Read targeted continuation decisions; confirmed in current task and session code. Loaded is not session-end: cleanup follows publication/discard/confirmed migration or expiry. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AG2 in detail / AG3 in detail | Read targeted scope and decision excerpts; superseded read-audit promise corrected: reads in calls, writes in audit with channel. Tool list and version semantics verified in code. |
| guide/samples — README / SOURCES | Read reference-domain definition and sources; no private model or source exports used. Only stops reference model named. |
| API.md — AI proposals | Read base contract; feature requests use configured provider and permissions, system discovery distinguishes assistant from provider. Link each feature to AI reference instead of repeating schemas. |
| API.md — Mapping targets | Read full heading and checked mapping_job.py selection, tallies and writes. writing-in-bulk covers candidate limits, half-context sizing, cancellation, proposed filter, provenance and refusals. |
| USER_JOURNEYS.md — J49 | Read full heading and variants; only candidate targets proposed, version-changed sources left alone, corrections reviewed before publication. |
| API.md — A question in words | Read full heading and checked query_translation.py preparation, SHORT_LIST and applied property. reading-records covers partial answers, names sent at higher levels and unsupported questions. |
| USER_JOURNEYS.md — J54 | Read main journey and located variants; code confirms no application for notExpressed. No screenshot required for API-only explanation. |
| API.md — An account of a model change | Read full heading and checked impact_summary.py facts contract. model-and-release-operations covers human-requested explanation, facts, citations, cache and graceful provider failure. |
| USER_JOURNEYS.md — J55 | Read main sequence and initial variants; summaries explain, never decide safety or activation. |
| API.md — What changed in a period | Read full heading and checked history_account.py scope, names and shared summary path. following-changes covers live facts, named data policy, links, failure and cache. |
| USER_JOURNEYS.md — J56 | Read main journey and located variants; history_facts needs Browse only, no provider. History accounts need Use AI proposals. |
| USER_JOURNEYS.md — J57 | Read main sequence; deterministic digests and following are not AI, already covered in existing approval/notification text; no AI deferral to introduce. |
| CHANGELOG.md — 0.16 Changed (one path for the assistant, AP10) | Read full heading. Removed plan route, table argument and rules-only fields are not documented as available; task changes uses source. |
| CHANGELOG.md — 0.16 Added (0.16 AP6, the assistant designs and loads) | Read targeted session, sandbox, one-session and empty-load bullets. Whole-type migration exception and later continuation contract supersede early wording. |
| CHANGELOG.md — 0.16 Added (0.16 AP6a, loading a workbook with the assistant) | Read full heading. Historical planner/provider loop superseded by AP10; retained promise is task submission, visibility, review and repeatable layouts. |
| CHANGELOG.md — 0.16 Added (0.16 AP2, AI targets for unmapped values) | Read full heading. Candidate selection, origin, send level and context sizing covered in writing-in-bulk. |
| run/ai; run/set-up-ai | Read targeted existing pages to link data, permission, costs and retention consistently; remain read-only. Their correct retention anchor is what-is-kept. |
| Frontend — AgentAccessPage / connection and client headings | Read exact current labels: New agent client (not earlier inventory New client), Calls, 30 days, How to connect and Address. Existing admin-agent-access.png inspected: disabled state only; request enabled state. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AG1 in detail | Read discovery and correction excerpts: use delivered discovery and audience contract, not pre-implementation gaps. |
| BASE_0_16_IMPLEMENTATION_PLAN.md — AP11 in detail | Read timing context only; not a performance promise for integrators. No timings copied to the guide. |
