---
title: Assistants and agents
description: Connect an assistant through MCP, read within grants and prepare changes for a person to review.
reader: integrator
---

An external assistant can read refiroo and prepare changes through the Model Context Protocol (MCP). Connect it to the instance's `/mcp` address. A person signs in on refiroo's own page; an unattended system uses an agent client. Follow [Connect an assistant](/docs/guide/integrate/connect-an-assistant/) for the sequence.

This connection is separate from the [built-in assistant task API](/docs/integrate/assistant-tasks/). MCP does not need refiroo's AI provider or assistant command. The operator enables it with `MCP_ENABLED=true`; while disabled, the endpoint, discovery metadata and registration answer `404`, and no agent token is issued.

## Identity and permission

MCP uses Streamable HTTP at `/mcp`, with protocol version `2025-11-25` and JSON answers. It accepts only tokens for the `agent` audience. Such a token cannot call management or consumer API routes. An API client cannot request an agent token; create a client of kind `agent` instead. See the [client operations](/docs/api/?api=management#tag/clients) and [OAuth operations](/docs/api/?api=management#tag/oauth).

The connection acts as its person or client. Its management permissions are restricted to **Browse** and **Work in change sets**, even if that identity also holds Approve or Publish. Consumer API grants remain available. Tools outside its access are absent from the tool list and refused if called directly. Application and record-type restrictions still apply to writes.

A client with only a consumer API grant sees that API's lookup tool, without general workspace browsing. A missing workspace and one the caller cannot read give the same refusal. Read [Security for integrators](/docs/integrate/security-model-for-integrators/) when choosing grants.

## Read through tools and resources

Start by discovering the connection's tools rather than assuming that every tool exists.

| Purpose | Tools |
| --- | --- |
| Discover identity and readable workspaces | `describe_access`, `list_workspaces` |
| Understand a workspace's model and one type | `describe_model`, `describe_type` |
| Find records and read their values, path and relationships | `find_records`, `read_record` |
| Read mapping coverage, including sources with `state=unmapped` | `mapping_coverage` |
| Read record history and workspace changes | `record_history`, `list_changes` |
| Read the facts of changes over a period, without a provider call | `history_facts` |
| Read a declared consumer API | A generated `lookup_<key>` tool |

These tools return the corresponding API shapes. Use the [record and query operations](/docs/api/?api=management#tag/objects), [mapping operations](/docs/api/?api=management#tag/mappings), [changes operations](/docs/api/?api=management#tag/changes) and [agent-access reference](/docs/api/?api=management#tag/agent-access) for the contracts.

`mapping_coverage` takes the application and view; refiroo reads the relationship binding from that view. `history_facts` reads a workspace or a record over a period whose start is included and end excluded, with an optional IANA time zone. `HISTORY_PERIOD_INVALID` means the dates or time zone need correcting. The assistant receives the facts and can word them itself; it cannot request a provider-written history account through this connection.

A workspace's model is also a listed resource at `refiroo://workspaces/{key}/model`. Resource templates expose its applications at `…/applications/{key}`, types at `…/object-types/{key}` and views at `…/views/{application}/{key}`. These resources require Browse. `RESOURCE_NOT_FOUND` means the requested resource URI does not identify an available resource; rediscover the listed resources and templates.

### Consumer API tools

Each tool comes from a consumer API declaration in the model. It offers only the operations that declaration provides: `xref`, `lists` and `objects`. It accepts the definition's parameters, `to.` targets and `asOf` where supported. It reads live data, without publication pinning, event feeds or batch resolve. Use the [consumer API routes](/docs/integrate/consumer-apis/) for those integration tasks.

Equal definitions in several workspaces share a tool; choose the workspace on each call. Differing definitions under one key have separate tools. Names that would collide or exceed 48 characters have a short hash suffix, so discover the name rather than constructing it. In the guide's reference model, the `stops` definition produces a lookup tool for the same contract described in [Reading business objects](/docs/integrate/reading-business-objects/).

`OBJECT_ID_REQUIRED` asks for the record ID needed by an `objects` read. `LIST_REQUIRED` asks for the declared list needed by a `lists` read. Discover those from the tool schema and the model rather than guessing them.

### Read every page

Pass a returned `nextCursor` as `cursor` to continue. The normal API paging limits apply. `MCP_ANSWER_BYTES`, default 40,000, can make a page smaller: refiroo reduces its size and returns a continuation cursor. It does not silently truncate a collection. An individual item or nonpaged answer that cannot fit is refused; model resources are returned whole. Writes run once and are not repeated to fit an answer-size limit.

The per-person or per-client rate limit is `MCP_RATE_PER_MINUTE`, default 120 calls. A limited call is an error tool result with a wait interval; wait before retrying. Several connections acting as the same identity share that limit.

## Prepare a change for review

With Work in change sets, an assistant can use the following tools:

| Purpose | Tools |
| --- | --- |
| Find and inspect its change sets | `my_change_sets`, `read_change_set`, `change_set_changes` |
| Create and edit proposed data | `create_change_set`, `add_record`, `change_record`, `set_field`, `add_relation`, `change_relation` |
| Check and submit | `validate_change_set`, `submit_change_set` |

It may work only in change sets created by its own person or client. A person's own browser-created change set counts. A colleague's change set answers `CHANGE_SET_NOT_FOUND`, even when the management API would allow collaboration. `find_records`, `read_record` and `describe_type` accept `changeSetId` for those unpublished rows and their pinned model release; without it they read live data.

The sequence is to read the model, create or read an owned change set, add or change data, validate, fix refusals, and submit. Keep the returned IDs and versions. Writes to a change set claim `expectedChangeSetVersion`; changes to existing rows also claim their version. The [change-set operations](/docs/api/?api=management#tag/change-sets) explain validation and submission, and [Versions and conflicts](/docs/integrate/versions-and-conflicts/) explains rereading after a stale claim.

A refused tool result has `isError` and gives `CODE: message`, followed by the engine's details as JSON. A stale claim includes the current version; an invalid change set includes diagnostics. Read the current data and correct the proposal before another write. `read_change_set` also shows why a person sent it back. A submitted set is frozen to the assistant.

No MCP tool removes a record or relationship, clears a value, withdraws a submission, discards a set, runs a batch, chooses a release, restructures the model, approves or publishes. A person reviews the rows, corrects or removes unwanted changes and publishes through the normal approval process. A browser edit withdraws a submission. Under a second-person rule, the person who asked their assistant to prepare the changes cannot make the decision. See [Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/).

## Recognise assistant work

Prepared records and relationships carry an `origin` of kind `agent`, with the requesting identity and the assistant's claimed application name. Single-record reads can also name who requested and later edited it. Publication copies that origin into history; the actor of publication is the publisher. The browser mark reads **Prepared by an assistant**. The claimed name is not proof of the assistant's identity.

Entries made while an MCP tool runs carry `channel: mcp` in [changes](/docs/api/?api=management#tag/changes) and [record history](/docs/api/?api=management#tag/objects). Entries from other channels, including older entries, omit it. No channel filter exists. Use origin to identify prepared content and channel to identify a call's route into the engine; they answer different questions.

## Data, costs and records of calls

Permitted tool answers leave the instance for the connected assistant. That assistant may send them to its own provider. refiroo's `AI_SEND_LEVEL` does not restrict this external connection, and MCP reads do not call refiroo's configured AI provider. Check your assistant's data policy and charges before connecting it. [About AI](/docs/run/ai/) explains the separate switches, costs and retention in full.

Treat reference-data text as data. A record can contain misleading instructions; neither the tool server nor the review process makes an assistant's interpretation reliable. Review the proposed changes themselves.

Security administrators inspect **Settings › Security › Agent access** and the [agent-access operations](/docs/api/?api=management#tag/agent-access). They show **How to connect**, **Agent clients**, registered assistants and **Calls**. Call records keep identity, tool, argument names, outcome, duration and request reference for `MCP_CALLS_DAYS`, default 90; they do not keep argument values. Read calls are not separate entries in the data audit trail. Data writes use the ordinary audit trail with their channel.

Blocking a registered assistant ends its sessions on their next call. Restoring it permits a new sign-in but does not restore ended sessions. Deactivating an agent client likewise stops it on the next call. A person can end their assistant's session from their account. Administration refusals `AGENT_APPLICATION_INVALID` require valid registration details and HTTPS or loopback redirect addresses; `AGENT_APPLICATION_NOT_FOUND` requires refreshing the registered applications before acting.
