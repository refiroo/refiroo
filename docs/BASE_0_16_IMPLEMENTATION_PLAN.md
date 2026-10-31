# Base 0.16 implementation plan

**Status:** Drafted 2026-10-27 at the user's request, for revision. AP-D3, AP-D12–AP-D26, AG-D5 and AG-D9
are decided by the user and marked so; every other AP-D, AG-D and AO-D below is a recommendation. Planned before 1.0 for now, like 0.14 and 0.15. Idea source:
the AI integration discussion of 2026-10-27. First drafted as three releases (0.16–0.18); merged into
one on the user's suggestion the same day because the three share one foundation, one permission and
one acceptance step, and together are about the size of 0.15.

**Target:** Product 0.16.0, [AI integration](ROADMAP.md#product-release-016--ai-integration).

**Depends on:** 0.12 (identity, roles and grants, change-set approvals, the inbox: a proposal is an
authorized act, and a change set is where it waits for a person). Nothing in 0.13–0.15 blocks it.

## Why

The engine already proposes: a model draft's inference proposes types, fields and relations from a
workbook, and a model mapping's inference scores every pair of types, both landing as steps marked
Proposed. Both rest on rules and cannot know that "PICKUP" and "Store collection" are the same thing.
The hook for a language model exists (`INFERENCE_ASSISTANT`, 0.10 A6, D95: a factory, no provider
bundled, never applies anything). The engine is also an integration engine whose API is the product,
so an AI assistant is one more client, and the people who run it read structured output they must turn
into prose. This release does three things with one foundation.

**What this release is not.** It is not a bot that edits data. A proposal never writes live data and
never publishes; an agent can only prepare and submit a change set that a person approves; a summary changes nothing. Reads, validation,
publication and the consumer API stay deterministic and never wait for a provider. With no provider
configured and MCP off, nothing is sent anywhere and no AI action appears.

## Outcome

**The requirement every package serves (the user's, restated 2026-10-28):** a person says a few words,
uploads a workbook, and gets the model and the import. The model has whatever the workbook needs:
any number of applications, types, attributes and relations within and across applications. The
AI is an add-on on top of the building blocks that already work (profiling, the rule-based
inference over every row, model-draft operations, the import profile, the dry run, the import); it
drives them through the engine's own capabilities and is limited only by what they can express. No
package narrows this, and a gap found in a building block (such as the inference proposing into one
application, found 2026-10-28) is closed as part of AP3 and AP6, not handed back as a question.

- **Track P, proposals.** A steward sees machine-made proposals in the screens they already use: a
  likely target for each unmapped value, a draft of a missing label or translation, better names and
  relations for a spreadsheet's columns, a grouped explanation of why a dry run failed. Each carries a
  confidence and a reason, is edited like any other step, and is recorded as machine-proposed and
  human-approved.
- **Instruction-driven tasks (AP6).** The user's scenarios, word for word (2026-10-27). Every AP6 plan
  is checked against each of them, and each is an acceptance case:

  > "I imagine it in a way, that someone uploads a complex xls and says so, create a model for this
  > and import, or map it to the current model and import, or extend. the current model, etc.
  > or as per your example: change the values of x based on the xls column y, add this translation,
  > add this system variant, add a new business
  > add a new relationship between duration and stations but only if driver assigned, etc."

  > "of course it is an instruction driven assistant. people already got used that they just use even
  > a loosely formulated english to describe what they would like to and they give it as a prompt,
  > attaching the material they are refering to. … please do all the necessary checks, this function
  > has to be usefull and make working with external sources kind of easy and fun"

  The cases (the user, 2026-10-28, word for word; cases A–E of the workbook assistant):

  > An update of existing data: import or update the data.
  > Additions to existing data: extend the model with new attributes on existing types, then update
  > the data.
  > A new relation to existing data: add new object types and their relations to the existing types,
  > then import the new data.
  > Something new but related to existing data: add new applications, their object types and
  > relations, and link them to the existing applications and types.
  > Something totally new: a new application or model.

  And 2026-10-28: "The user says a few words, uploads an xls, expects the model and the import." "we
  don't build limitations." They get a plan they can read and edit, a count of what would happen row
  by row, and one step to run it.

  **Status 2026-10-29:** AP6a delivers none of these scenarios fully (its record has the table).
- **Track A, agent access.** An organisation points an MCP-capable assistant at its instance; the
  assistant looks up and explains reference data, reads the model, finds unmapped values and prepares
  changes. It can submit changes for approval but never approve or publish them.
- **Track O, operations.** A model administrator reads a plain-language impact summary beside the
  activation preview; an owner asks what changed in a workspace and gets an account citing its
  sources; a person who opted in receives one digest instead of many mails.

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [AP1](#ap1-the-proposal-provider) | 0.12 | **Foundation.** Provider interface, settings, adapters, send levels, call record, permission, jobs, provenance, Settings › AI |
| [AP2](#ap2-targets-for-unmapped-values) | AP1 | Ranked target candidates for the unmapped rows of a mapping view, landing as edits in a change set |
| [AP3](#ap3-model-authoring-and-model-mappings) | — | **Folded into AP6 (AP-D27, 2026-10-28):** model authoring is steps 3–8 of the workbook flow |
| [AP4](#ap4-values-for-empty-fields-and-missing-related-records) | — | **Folded into AP6 (AP-D27):** value drafts are a tool of the assistant, offered in place on a filtered collection |
| [AP5](#ap5-dry-run-triage) | — | **Folded into AP6 (AP-D27):** the grouped refusals feed the assistant's loop (AP6c) and are shown to the person |
| [AP6](#ap6-instruction-driven-tasks) | AP1, AP2–AP5 patterns | **Tell the assistant what you need, attach the material.** A free-text instruction and a workbook become a plan of steps made only of what the engine already does, shown for editing, dry-run over every row and run into a change set |
| [AG1](#ag1-the-server-and-its-authority) | 0.12 | The MCP endpoint, its setting, sign-in with the existing OAuth, audit channel, the agent role, Settings › Agent access |
| [AG2](#ag2-read-tools-and-resources) | AG1 | Read tools generated from the consumer API definitions plus a curated set; the model as resources |
| [AG3](#ag3-changes-prepared-and-submitted-for-approval) | AG1, AG2 | Write tools that create a change set, add validated changes and submit it for approval; no approve or publish tool |
| [AG4](#ag4-natural-language-search) | AG2, AP1 | A question turned into the existing search and filter parameters, explained back |
| [AO1](#ao1-model-change-impact-summary) | AP1 | A plain-language impact summary of a release diff or activation preview, with its facts |
| [AO2](#ao2-what-changed-an-account-of-history) | AP1 | An account of a workspace's history over a period, with citations |
| [AO3](#ao3-notification-digests) | AP1 (the AI sentence only) | A daily or weekly digest of a person's inbox notices by mail, opt-in; useful without a provider |
| [WM1](#wm1-change-a-workspaces-model-from-the-workspace) | 0.12 | **Not AI.** Edit a workspace's model from the workspace: a draft made for it, one "Apply to this workspace" |
| [R](#r-build-acceptance-and-release) | all | Full review of every change since 0.15, the gates, one bounded real-provider try and one real-assistant try, the release |

**Order (revised 2026-10-28).** AP1 first. Then AP6 with what it needs of AP3: the built-in chat in refiroo (attach a workbook, say a few words, get the model and the import) is the product's way to the requirement. Track A (MCP) is an additional route for organisations that bring their own assistant, never a precondition. Earlier wording: the tracks are independent: Track A (except AG4) does not need AP1 and could
come first if the user prefers the cheapest slice; recommended order after AP1 is AP2, AP6 (the heart of the release,
next because it reuses the import, inference and batch machinery rather than waiting on Track A), AG1–AG3, AO1,
AP3–AP5, AO2, AO3, AG4. The `origin` provenance field (AP-D5) is introduced by whichever package comes
first and reused by the others.

**Tracks A and O stay in 0.16 (decided by the user 2026-10-31).**

## Decisions

### Track P: proposals

| # | Question | Recommendation |
| --- | --- | --- |
| AP-D1 | One interface or one per feature? | **One.** `ProposalProvider.propose(request) -> proposals`, where a request has a `purpose` (`mappingTarget`, `modelNames`, `fieldValue`, `failureTriage`, later ones), a bounded context and the schema of the answer expected. Features differ in the context they build and the step they make of the answer, not in the provider. Why: a feature must not be able to reach a provider on its own, and the data policy (AP-D3) is checked in one place. |
| AP-D2 | Which providers ship? | **The interface, a fake for tests, and two adapters:** the Claude API and any OpenAI-compatible endpoint (which also covers a local model, for organisations that may not send data out). Chosen by `AI_PROVIDER` (`claude`, `openai-compatible`, or a factory `package.module:function` as `INFERENCE_ASSISTANT` is today); key and endpoint by settings read from the environment, never from the model or the database. Why: one organisation per instance brings its own key; a local endpoint answers "we cannot send reference data out". |
| AP-D3 | What may leave the instance? | **Decided by the user 2026-10-27 (default and range): the default is `values`, so the helpers have the data they need; the levels below it stay selectable.** The operator sets the ceiling with `AI_SEND_LEVEL`: `structure` (keys, labels, attribute names and types; no record values), `samples` (plus a bounded number of values per attribute, default 20 like `INFERENCE_ASSISTANT_ROWS`) or `values` (plus record values for the features that need them). Why `values` first: reference data is short and its meaning is in the values (a model with many similar types and codes cannot be proposed on from names alone), and a proposal that misses costs the steward more than it saves. A feature that needs more than the level allows is hidden, not degraded. The context builder is the only code that reads data for a provider and it is the unit-tested boundary. **Decided by the user 2026-10-28:** a person may also choose a lower level for their own request, never a higher one than the ceiling. Not built in AP1 (its one feature has no level choice); the first feature that sends data, AP2, adds it to its request. |
| AP-D4 | What is recorded about a call? | **A call record, without content by default:** who, purpose, provider and model, when, size in and out, outcome, the job. `AI_LOG_CONTENT=true` (off) also keeps the request and answer for a bounded time, for an operator debugging a prompt. Settings › AI lists the records and the totals. Why: an operator must see what was sent and how often; the content is reference data and is not kept without being asked. |
| AP-D5 | How is a proposal marked once it is a step or a change? | **Provenance on the step.** A proposed step or change carries `origin = {kind: "ai", provider, model, promptVersion, confidence, reason}`; the history shows it as machine-proposed with the person who approved. A person's edit of the step keeps the origin and adds the editor. **Checked 2026-10-27:** model-draft steps already have an `origin`; change-set entries do not, so AP1 adds a nullable `origin` column to both change-set tables and copies it into the audit event at publication (see [AP6 in detail](#ap6-in-detail)); AP1 settles this first. Door affected (ADR-032, value provenance): it is the first use of the door; the field is additive and the record of origin stays outside the record's own values. |
| AP-D6 | Review shape | **The editor, not a questionnaire** (the user's rule): a proposal is a step marked Proposed in the model editor, or a change in a change set the person opens in the mapping grid, edited in place. No separate accept/reject list. The reason and confidence show on the step; a confidence below the operator's floor (`AI_MIN_CONFIDENCE`, default 0.5) is not offered. |
| AP-D7 | Who may ask for a proposal? | **A new action group, "Use AI proposals"**, granted by role like the others (ADR-044); the predefined Data steward, Model, Workspace administrator and Integration administrator roles get it, Reader does not. With the provider off, or the send level too low for a feature, the action is hidden, not disabled with a reason. A proposal still needs the permission to write what it proposes: the change is made by the person's own request. |
| AP-D8 | Sync or job? | **A job** (kind `aiProposal`, on the existing worker, with cancel, lease renewal, inbox notice on finishing and a progress count), because a provider call can take seconds and a set of unmapped rows can be thousands. Batches are sized by the provider's limits and run in the database where the candidate set is selected (INSERT…SELECT into a work table), not row by row through Python. A failing provider is a warning on the job; deterministic proposals stand (the 0.10 rule). |
| AP-D9 | Candidates first, the model second | **Retrieval narrows, the model ranks.** For mapping targets the engine's existing candidate search (view-specific, bounded) selects at most N targets per source; the provider only chooses and explains among them. It cannot invent a target that does not exist, so every proposal refers to a real record and is validated by the same rules as a hand edit. Why: cheap, checkable, and the data policy sends only the candidates. |
| AP-D10 | Model change | **None to the model schema in this release.** Which attribute a field proposal reads from is chosen in the request, not declared in the model. Reopen only if a real model needs the declaration to be permanent. |
| AP-D11 | Tests | **A deterministic fake provider** answers from a table keyed by purpose and context, so the journeys run in CI without a network. **One bounded try with a real provider** in R, in the style of [REAL_PROVIDER_TRY_PLAN](testing/REAL_PROVIDER_TRY_PLAN.md): run on the user's go-ahead, one provider, a small fixed set, cost stated first. No quality benchmark of providers in this release. |
| AP-D12 | What can an instruction become? | **Approved by the user 2026-10-27. Only what the engine already does, nothing new for the model to execute.** A plan is a list of steps of five kinds: **model-draft operations** (the 67 kinds, to create or extend a model), **an import profile** (sheets, blocks, key columns, attribute columns, parent, relation, `relationFlags` and `relatedRecord` columns, value maps, `record` mode and `missing` handling), **batch items** (`update`, `upsert`, `ensureRelation`, `replaceRelationSet`, …), **a query** (the model-aware `where`, one relation hop, `not`), and **a change set** to hold the result. The assistant writes these as the same steps the editors show. An instruction that needs something outside them is answered "I can't do this because…", never approximated. Why: every step is validated by the rules of a hand edit, the dry run already checks every row, and the engine stays deterministic. |
| AP-D13 | Where does the result go? | **Approved by the user 2026-10-27. A change set by default, live only when the person says so and the permission allows.** The profile is saved (the 0.10 profile mechanism), so next month's file runs through it unchanged: this is what makes working with an outside source repeatable. Nothing runs before the person confirms the dry run's counts (the 0.9 preview-and-confirm is reused for imports and for batches). |
| AP-D14 | How much of the file does the provider see? | **Revised 2026-10-28 to follow the requirement (Outcome): as much as it needs, through tools, within the send level.** It starts from the file's profile (each column's type, distinct count, fill rate, patterns and sample values, computed in the database over every row) and the model's structure, and reads further through read-only tools over what the engine already computes: any sheet's rows by range, a column's distinct values with counts, overlaps between columns and sheets, the rule-based inference's findings. No fixed sample bounds it; `AI_SEND_LEVEL` is the only limit on what may leave. Whole-set truth still comes from the dry run, which checks every row (D67). *(Approved 2026-10-27 as "the profile plus a bounded number of rows per sheet"; that would have kept the AI's view sampled.)* |
| AP-D15 | One shot or a conversation? | **Revised 2026-10-28 to follow the requirement: an agent loop with the engine's tools, plus follow-ups.** The assistant calls the read tools of AP-D14 and the planning tools (read the model, count a query, write plan steps, dry-run its plan) as often as the task needs, revising the plan when the dry run refuses rows, until the dry run is clean or it has a question only the person can answer (AP-D16). `AI_MAX_STEPS` stays as an operator's safety and cost limit, defaulting high enough for a workbook of many sheets, never as a design limit. Follow-ups as before ("no, column D is the name"); it never writes anything but the plan. *(Approved 2026-10-27 with at most 8 steps.)* |
| AP-D16 | Questions back | **Approved by the user 2026-10-27. Few, specific, answerable by a click.** When an ambiguity changes the result (two plausible target types, which column is the key, whether to create or only update), the assistant asks once, with the candidates and what each would do, and goes on with its best reading marked Proposed. It does not interview. It never asks what the engine can tell it. |
| AP-D17 | Relation "only where" conditions | **Approved by the user 2026-10-27. Supported to the extent the query is: one relation hop, `not`, field criteria, ancestor criteria, ANDed.** Checked 2026-10-27 in API.md (model-aware query): OR groups and nested hops "wait for a second real case" (D4). A condition that needs them is refused with that reason, which also makes a real case for D4 visible. The model part of such an instruction (the new relation type and its permitted binding) is model-draft operations (AP-D12); the data part is the items below. |
| AP-D18 | Creating items for every record a query matches | **Approved by the user 2026-10-27. Recommended: the task job builds the batch items from the query inside the database, and the existing batch preview and confirm run them.** No new engine item kind. It is per-record writes, as any batch is. Measure the basics at 200 and 2,000 records first (the user's rule) and only then decide whether a true set operation (one statement, `ensureRelation` for every match) is needed; if so it is an engine capability of its own, generic and API-first, and gets its own decision. |
| AP-D19 | One set of tools, two drivers | **Approved by the user 2026-10-27. The planning tools of AP-D15 are the engine's own capabilities, exposed in-process to the built-in assistant and, in Track A, over MCP to an outside assistant.** Same authorization, same validation, one implementation. The cost is that file upload is not an MCP tool (binary): an outside assistant works on files already uploaded in the browser or by API. |
| AP-D20 | What the person sees | **Approved by the user 2026-10-27. The editor, extended by one panel.** A task page (reachable from home and from a workspace) with the attachment, the instruction, the assistant's reading of the file (sheets, blocks, columns and what it thinks each is, editable), the plan as steps marked Proposed in the editors people know, and the dry run beside it in plain counts ("412 rows: 380 new, 20 changed, 12 refused", each refusal with its reason and row). A workbook attached with no instruction offers three or four likely tasks. A mock-up goes with AP6's detailed plan for approval before any build (the user's rule). |
| AP-D21 | Providers that cannot do this | **Approved by the user 2026-10-27. AP6 needs a provider that supports tool use and structured answers.** The Claude adapter does; an OpenAI-compatible endpoint does if the model behind it supports tool calls, which a small local model may not. Settings › AI reports per feature whether the configured provider can do it, and the task page is hidden when it cannot. No quality promise for small models. |
| AP-D22 | How is it tested? | **Approved by the user 2026-10-27. Scripted journeys with the fake provider, which returns a prepared plan for a prepared instruction.** They prove the engine's side: the plan is applied exactly, refused rows are reported, follow-ups revise, nothing runs unconfirmed, the file is not sent beyond the level. They cannot prove the assistant understands loose English; that needs **a real-file try**: the user's own complex workbooks, the five task kinds of AP6, run with a real provider on the user's go-ahead, cost stated first, results judged by the user. This is a package acceptance step, not left to R. |

### Track A: agent access

| # | Question | Recommendation |
| --- | --- | --- |
| AG-D1 | Where does the MCP server run? | **In the same process, mounted at `/mcp` (Streamable HTTP), off by default (`MCP_ENABLED`).** Not a separate server, not a stdio package. Why: one deployment, one set of settings, one token verifier, no second process to secure or to forget (no side servers); an assistant on a laptop reaches it like any client. A stdio bridge can be a thin client later without changing the engine. |
| AG-D2 | How does an agent authenticate? | **With the access tokens the engine already issues.** Clients (service principals, `create_client`) use client credentials; a person signing in to an assistant uses the existing OAuth authorization flow, so the MCP client's own sign-in discovery works against `/oauth`. The `MCP` surface is a new token audience `agent`, so an agent token is refused by the management and consumer APIs and the reverse (D226/D258 audiences). Why: a stolen agent token reaches only the agent surface; revoking works as for any token. |
| AG-D3 | What may an agent do? | **Exactly what its principal's roles and grants allow, intersected with the predefined `Agent` role,** which holds read of the consumer definitions it is granted, read of the model, read of history, and "prepare changes" (AG3); no publish, no model administration, no security administration, no deletion of anything. A tool the principal cannot use is not listed (hide, not disable). |
| AG-D4 | Where do the tools come from? | **Generated from what exists,** not written per capability. Consumer API definitions (read, model-derived, already permissioned per definition) become one lookup/search tool each, with the definition's fields as the tool's schema. A curated set covers what has no consumer definition: the model description, a record's relations and mapping, mapping coverage ("unmapped values"), history of a record. Each tool calls the same service functions as the route it mirrors. A tool that cannot be built from an existing route is a missing API capability and is added to the API first (the API is the product). |
| AG-D5 | Writes | **Decided by the user 2026-10-27: an agent may write, with approval; the 0.12 approvals are the control.** The write tools create or choose a change set and add object, field and relation changes to it; validation runs; the tool may **submit** the change set for approval (ADR-045). There is no tool that approves, activates, publishes, withdraws or writes live, and an agent principal can never approve, whatever the workspace's approval mode: 0.12 lets a person publish their own change set in one step unless four-eyes is on, and an agent must not inherit that. A person approves, and live data changes then. Each change carries `origin = {kind: "agent", client}` (the provenance field of AP-D5, introduced by whichever package comes first). |
| AG-D6 | Audit | **Every call is attributed to its principal with `channel = "mcp"`** in the audit trail, the same trail the API uses, plus the tool name and the arguments' shape (not their values for reads). Settings › Agent access lists agent clients, their last use and counts. |
| AG-D7 | Limits | **The API's limits apply, plus the agent's:** the same pagination (an agent pages with cursors; no tool has a hidden cap), a request rate per principal (`MCP_RATE_PER_MINUTE`), and a response size cap that returns a cursor, not a truncated answer. Tool results are structured data with IDs, so an agent can cite them. |
| AG-D8 | Prompt-injection stance | **Reference data is data, never instructions.** Tool results are labelled as data; no tool follows text found in a record; the only write path is a change set a person reviews. This is the main reason AG-D5 has no live write. Documented in the guide for operators. |
| AG-D9 | Do we ship AG4 here? | **Decided by the user 2026-10-27: yes, in this release, after AG1–AG3 and AP1.** The assistant asking in natural language is already an agent's own job (it calls the search tool with the filter it chose); AG4 is for the built-in search box and for assistants without tool use. |
| AG-D10 | Tests | **Journeys through the MCP endpoint with a test MCP client** (the protocol's own SDK), for: a client reads a definition and cannot read an ungranted one; an agent token is refused by `/api/v1`; a write tool leaves live data unchanged and produces a change set awaiting approval; `MCP_ENABLED` off returns 404. One try with a real assistant (Claude Desktop or Claude Code as the MCP client) in R, on the user's go-ahead. |

### Track O: operations

| # | Question | Recommendation |
| --- | --- | --- |
| AO-D1 | What does the model see? | **The facts, not the data.** AO1 sees the diff's operations and the counts the preview already computes (records affected per type, mappings touched, consumer definitions changed). AO2 sees change records (kind, type, field, count, actor, time) grouped in the database, and record names only at send level `values`. AO3 sees notice kinds, counts and titles. Send level per feature is stated in its package; below it the feature is hidden (AP-D3). |
| AO-D2 | Citations | **Every statement cites at least one fact by its ID,** and the interface renders the citation as a link. The prompt requires it; the answer schema carries `statements: [{text, factIds[]}]`; a statement without a valid fact ID is dropped and counted ("2 statements removed: no source"). Why: the reader can check, and a hallucinated sentence cannot survive without a source. |
| AO-D3 | Whole set, not a sample | **The facts are computed over every change in the period** (aggregates in PostgreSQL), the user's rule for checks and dry runs (D67). The model receives the aggregates and a bounded number of top items per group, with the group's true count, and the account says "and N more" instead of implying completeness. |
| AO-D4 | Stored or on demand? | **On demand, cached per input.** The summary is keyed by the hash of its facts; the same facts return the same text without a second call. Not stored in history and not part of a release: it is a reading aid. A model release's summary is cached on the release preview only for the session of the preview. |
| AO-D5 | Who may ask? | **AO1: model administrators** (those who may activate). **AO2: those who may read the history of the scope** being summarised, and the facts are filtered by what they may read (visibility, ADR-044): the summary cannot say what the person cannot see. **AO3: the recipient, for their own inbox.** A summary is not a proposal, so a second action joins "Use AI proposals" in the AP1 group: "Use AI summaries". |
| AO-D6 | Digest opt-in and shape | **Opt-in per person, off by default,** in the notification settings beside the existing per-kind choice (D434): `none`, `daily` or `weekly`, replacing the per-notice mails for the kinds the person has switched to digest. A digest is built by a scheduled job from the person's unread notices, sent through the existing outbox and templates; the plain list of notices is always in the mail below the summary. Quiet when there is nothing to say: no mail. |
| AO-D7 | Where does AO2 live? | **A "What changed" panel on the workspace and on a record's history,** a period picker, and a route `POST …/history/account` (job when the period is large) returning statements and facts. Not a chat. The same route is reachable by the AG2 tools (the API is the product). |
| AO-D8 | Language | **The account is written in the person's interface language** (0.15's setting passed to the request), English if the language is not one the provider writes well, noted on the account. |
| AO-D9 | Tests | **Fake provider for the journeys,** including the case where it returns an uncited statement (dropped) and where it fails (facts alone). **A fact-completeness test** per package: the facts shown equal the facts computed from the database for the period, independent of the provider. One bounded real-provider try in R, on the user's go-ahead. |

## Track P: proposals

## AP1: The proposal provider

**Journeys:** an operator configures a provider and sees it ready; a steward without the permission
does not see the action; a provider failing leaves the deterministic result standing; every call is
visible to the operator.

**Scope.**
- `engine/proposals/`: the `ProposalProvider` protocol, the request and answer shapes, the registry
  that resolves `AI_PROVIDER`, the two adapters, the fake, and the structured-answer check (an answer
  that does not match the requested schema is a failed call, never a guess).
- The context builder with the send levels (AP-D3) and a unit test per level that proves a value
  never leaves above its level.
- The `ai_calls` table (migration), the `aiProposal` job kind, the "Use AI proposals" action group
  and its role grants, `GET /system` reporting `ai: {configured, sendLevel, provider}`.
- The existing `INFERENCE_ASSISTANT` setting folded onto the provider (pre-1.0, nothing to keep; the
  setting is removed, OPERATIONS.md updated).
- Provenance (AP-D5) on model-draft steps and change-set changes.
- Settings › AI: status, send level, the call records and totals. No provider keys on a page: the
  page shows that one is set, never the value.
- API: `GET /ai/status`, `GET /ai/calls`; proposals are made through each feature's own route
  (AP2–AP5), so there is no generic "ask the model" route (it would bypass the context builder).

**Out of scope:** streaming, an open-ended agent, fine-tuning, a prompt editor. (AP6 adds a bounded, read-only planning loop and follow-up instructions; AP1 itself is single-shot.)

### AP1 record (2026-10-28)

**Delivered 2026-10-28** on the user's "deliver build 0.16 ap1", without a separate detailed plan or
mock-up, as 0.12 M1 was: the page reuses the Mail page's pattern. The recommendations AP-D1, AP-D2,
AP-D4–AP-D9 and AP-D11 are built as written; the user may reopen any of them.

- **Engine** (`engine/proposals/`): `provider.py` (the request, the answer, `ProviderError` and its
  kinds, the closed answer schema), `context.py` (the send levels; a value read only when the level
  allows it), `claude.py` and `openai_compatible.py` (over `httpx`), `fake.py` (deterministic, records
  what it was sent), `registry.py` (`AI_PROVIDER` resolved at start, a setting that cannot work refusing
  it), `calls.py` (`ask`: the answer checked against its model, one `ai_calls` row per call, a job's
  written apart; content kept and expired by `AI_LOG_CONTENT[_DAYS]`; paging and 30-day totals).
- **Migration** `20261117_01`: `ai_calls`. **Settings:** `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` (secret),
  `AI_BASE_URL`, `AI_SEND_LEVEL` (default `values`, AP-D3), `AI_SAMPLE_VALUES`, `AI_MIN_CONFIDENCE`,
  `AI_LOG_CONTENT`, `AI_LOG_CONTENT_DAYS`, `AI_TIMEOUT_SECONDS`; `INFERENCE_ASSISTANT[_ROWS]` refused by name.
- **Authorization:** the group `ai-proposals` (Use AI proposals, workspace reach) in the steward, owner,
  model-admin, workspace-admin and integration-admin roles; the action `ai.test` (Operations). The group is
  a `FEATURE_GROUPS` entry: a feature's route checks it for its `assistant`-like option, no route
  declares it (AP-D1: no generic route).
- **API:** `GET /ai/status`, `GET /ai/calls`, `POST /ai/test`; `ai` on `GET /system`; `assistant` on the
  inference's request and read; codes `AI_NOT_CONFIGURED`, `AI_SEND_LEVEL_TOO_LOW`. OpenAPI lock re-baselined,
  additive (diffed against 0.12.0 in a worktree).
- **The 0.10 assistant folded in** (`sources/inference/assistant.py`, purpose `modelNames`): its names are
  proposals whose `evidence.origin` is the AP-D5 provenance, copied into the applied step's
  `origin.proposedBy`.
- **Frontend** (built by a Sonnet agent from a brief): Settings › Administration › **AI**
  (`AiPage.tsx`, Operations), the shared `AssistantChoice` in New from a workbook and Propose again (shown
  only with a provider and the group), "Proposed by the AI assistant (model), N% confident" in Proposed
  because, the Deployment page's AI group, the group's texts. **Runner** `ap1-ai`.
- **Documents:** API.md § AI proposals and § Inferences, OPERATIONS § AI proposals, ARCHITECTURE § AI
  proposals, USER_JOURNEYS J48, API_JOURNEYS, CURRENT_FUNCTIONALITY F29, PRODUCT, UI_ACCEPTANCE AP1-1–AP1-5,
  EXECUTION_GUIDE, CHANGELOG.

**Where it differs from the plan:**

- **Revised 2026-10-28 with AP-D14:** at send level `values` nothing caps what a feature asks for; `AI_SAMPLE_VALUES` caps only `samples`. The naming helper asked for 50 rows per sheet, its own choice; replaced on 2026-10-28 by the column profiles over every row (AP-D14), the fixed slice having no basis.
- **The change-set `origin` column and the `aiProposal` job kind move to AP2**, their first writer: in AP1
  nothing could write or exercise them (no client could produce the state a test would need). The design
  stands as AP-D5 and "AP6 in detail" describe it; ARCHITECTURE says so.
- **The Claude adapter is plain HTTP, not the Anthropic SDK:** the SDK brings `httpx2`, which Starlette's
  test client then prefers, breaking the harness; one client serves both adapters. It asks for structured
  output and sends `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`); default model
  `claude-opus-5-5`.
- **`POST /ai/test`** was added (not in the plan): an operator otherwise learns of a bad key only at a
  steward's first proposal. It sends no data.
- **The fake is in the app** (`app.engine.proposals.fake:provider`), as the plan says, reachable only by
  naming it; the browser runner uses it.
- **Tests written after the code**, not seen failing first.

**Checks:**

- `test_j48_ai_proposals`: 20 passed (J48.1–J48.7, two configurations). Unit tests of
  `engine/proposals/` (context per level, calls, both adapters over a mock transport, registry), the
  assistant and `test_config`: 119 passed.
- The guide's groups for the boundary: `contract` 82 passed; `startup` 191 passed and 4 failed, all fixed
  and rerun (25 passed: the FK inventory, `SystemSetting.group`, J31's `/system` keys, and the stale head
  pin); J34, J40, J47 (sweep and cases), the unit tests of jobs, sources and authorization: 495 passed.
  `ruff check` on the changed files.
- Frontend: `tsc -b`, `npm run lint` (0 errors; 9 older warnings), `npm run build`, focused Vitest (153,
  then 16 after the shared choice), `test:browser:ai` (30 checks, axe 0 violations, a backend with the fake
  on two models and one without a provider).

**Found on the user's first real try (2026-10-28, `gpt-oss:20b` through Ollama) and fixed in AP1:** the
inference held its transaction open during the AI call (J48.8, which fails without the fix); the editor did not
show or wait for the AI and an edit meanwhile discarded every proposal (now a phase, paused editing, Stop and the
outcome); a draft profile key taken by another model was refused only at load, with no way to change the key in
the editor (now an Issue with a free key, J36.4). The model itself answered in 84 s and found the names good as they
were; `qwen3.8:27b-mlx` answered after 400 s with text that is not JSON (the build does not hold the schema).
Prompt quality is AP3/AP6 work.

**Not verified:** a real provider (the R try, on the user's go-ahead); screenshots at 390px on generated-b,
dark at 390px and the dialogs at 390px were not inspected; a failed test request and kept content in the
browser (Vitest only); Load more on the calls list. The development database was upgraded by the user's
`uvicorn --reload` server (health answered `ok` after it); no side server was started.

**What the user cannot do yet:** get AI proposals anywhere but the inference's names (AP2–AP6), reach the
engine from an outside assistant (AG1–AG4), read plain-language summaries (AO1–AO3); choose a lower send
level per request (AP-D3, decided 2026-10-28; built from AP2).

## AP2: Targets for unmapped values

**Journey:** a mapping steward opens a mapping view with 300 unmapped values, asks for target
proposals, and finds a change set whose changes map each value to its best target with a confidence
and reason; they correct a few in the grid, and publish through the normal approval.

**Scope.** `POST …/mapping-views/{view}/proposals` (job): the unmapped source rows of the chosen
context, candidates from the existing candidate search (AP-D9), the provider's ranking, a change set
created or chosen by the person, each proposal an edit marked machine-proposed. A source with no
candidate above the floor stays unmapped and is counted in the result. Atomic set claims and draft
aggregate tokens (ADR-022) apply unchanged: a divergent live set is refused as for a hand edit.
Generic: any relation binding with a mapping view; the example model's mappings are one configuration
and a second binding with different types and direction is the second proof.

### AP2 in detail (approved by the user 2026-10-28, with the mock-up)

The mock-up is the visual reference (a Design canvas, not kept in the repository): the grid's
**Propose targets** button and **Proposed** segment, a target's mark "Proposed by the AI · 86%" with
its reason, the dialog (scope, current or new change set, what is sent), progress and result counts,
the phone layout (reason folded under "why?") and the history entry.

| # | Decision |
| --- | --- |
| AP2-D1 | **Route** `POST /api/v1/workspaces/{key}/mapping-proposals` → `202` with the job (kind `aiProposal`). The view is named as coverage names it (`applicationKey`, `viewKey`; the binding comes from the view). Body: `search`, `parentObjectId` (the grid's narrowing), and `changeSetId` + `expectedChangeSetVersion` or `changeSetName` (a new change set, created by the request), exactly one; `sendLevel` (AP-D3). Only unmapped sources; never live. |
| AP2-D2 | **Candidates** (AP-D9): the binding's eligible targets as the candidate search defines them (candidate criteria, one-to-one occupancy), in the change set's context. At most `WHOLE_LIST` (100) eligible targets: every call gets the whole list. More: each source gets its top `PER_SOURCE` (20) by `pg_trgm` similarity of the target's name and candidate search fields to the source's name and source columns. Computed in PostgreSQL when the job binds, stored as its inputs. An answer naming anything outside a source's candidates is dropped and counted. |
| AP2-D3 | **Send level**: purpose `mappingTarget` needs `values` (record names are values) and is hidden below it. `sendLevel` on the request is checked in one place (`ai_requested`): never above the ceiling; for AP2 anything below `values` is `409 AI_SEND_LEVEL_TOO_LOW`, so the dialog offers no choice. |
| AP2-D4 | **Batches** of 25 sources per provider call; the call holds no transaction (J48.8); each batch's proposals are written into the change set and committed before the next. Cancel keeps what was written. A failed call is a warning and its sources count as not proposed. A source whose set version changed since binding is refused by the version token and counted. Result: `proposed`, `unmatched` (no target at or above `AI_MIN_CONFIDENCE`), `changed`, `notAnswered`, `changeSetId`, `warnings`. |
| AP2-D5 | **Provenance** (AP-D5, moved from AP1): nullable `origin` JSON on `change_set_relations` and `change_set_objects` (additive migration) = `{kind: "ai", provider, model, promptVersion, confidence, reason, proposedBy}`; copied into the publication's audit event (`changes.origin`); record history answers `origin` on the entry, whose actor stays the publisher. A person's change of the target is a new relation without origin, so the mark goes. |
| AP2-D6 | **Review**: coverage target summaries carry `origin` (omitted when none); coverage takes `proposed=true` (change set context only: the sources with a target holding an AI origin), the grid's Proposed segment. No sort by confidence. |

**Journey J49 (two configurations each):** J49.1 proposed into a new change set, origin on the
relations and on coverage, live unchanged; J49.2 an invented, null or below-floor answer leaves the
source unmapped and counted; J49.3 the provider receives only eligible candidates (whole list, or
top 20) and names; J49.4 a failing provider: warning, failed call, nothing written; J49.5 a source
mapped meanwhile is refused by its version token and counted; J49.6 hidden: `403 FORBIDDEN`
(`groups: ["ai-proposals"]`), `409 AI_NOT_CONFIGURED`, `409 AI_SEND_LEVEL_TOO_LOW`; J49.7 the
`proposed` filter, a changed target loses its mark, published history carries origin with the
publisher as actor. Unit tests: candidate selection and answer filtering.

### AP2 record (2026-10-28)

**Delivered 2026-10-28** on the user's "deliver build 0.16 ap2", after the plan and the mock-up
were approved. Backend and frontend were built by Sonnet agents from briefs, reviewed by the lead.

- **Engine:** `engine/reads/mapping_scope.py` (`MappingScope`: the binding's edges, eligibility and
  unmapped sources, shared with the mapping reads), `engine/proposals/mapping_selection.py` (the
  sources and candidates in one `INSERT … SELECT` into the job's inputs), `mapping_targets.py` (prompt
  `mapping-targets/2`, short refs, `chosen`, `shown_fields`, `sized`), `mapping_job.py` (`queue`,
  `bind`, `step`), the worker's `aiProposal`, `ChangeSetWrites.set_origins`, `MergedRelation.origin`
  into the relation audit event, `context_projection` moved to `engine/reads/mapping_projection.py`.
- **Migration** `20261118_01`: `origin` on `change_set_relations` and `change_set_objects`, the job kind,
  the inbox trigger's kinds. **Setting** `AI_CONTEXT_TOKENS`.
- **API:** `POST /workspaces/{key}/mapping-proposals`; `aiProposal` on the job read and in `GET /jobs`
  `kind`; coverage `proposed`; `origin` on target summaries and history entries; `sendLevel` checked in
  `ai_requested`. OpenAPI lock re-baselined, additive.
- **Frontend:** `MappingProposalDialog`, the grid's Propose targets and Proposed segment, `ui/AiOriginMark`
  (also the model editor's sentence), the history entry's mark, the job kind's texts. Runner `ap1-ai`
  extended with the AP2 checks.

**Decided within the approved package:**

- `refused` counts a target a rule refused (cardinality, two sources taking one exclusive target); `changed`
  a version-token mismatch; `notAnswered` a failed call or a source the answer left out.
- Each step claims the change set's current version, so a person editing meanwhile does not stop the job.
- **Calls sized to the model's window** (AP-D8, found on the real try): `AI_CONTEXT_TOKENS` (empty: no limit);
  a step takes as many sources as fit half of it; a whole list too large for one source becomes each source's
  closest 20; a source with no candidate is not sent and no call is made for none. What is sent of a record
  leaves out a field that repeats its name or holds a UUID.
- The reason must name records, never the references (prompt `mapping-targets/2`).

**Found by the user on realistic data (2026-10-28) and fixed:** the mapping grid listed every record of
the source type as a source of every mapping view, ignoring the binding's criteria at the source end
(0.9 K7, D171), so its "unmapped" rows, counts and the proposals included records that may never be
mapped there. `MappingScope.source_clauses`: a source meets the source-end criteria or already holds an
edge of the binding (D175); coverage, its counts and filters and the proposal job's selection all use
it (J10.12, J49.3). The user's development model was given the criteria through the API (release
`rdm-operators-timetables` 0.9.13 in `default`, `candidates.from` = `ancestor:system-group.name` per
target; before/after inventory: only those five and the release version changed); in `default` both
timetable views then have 0 unmapped values, where they showed 200 and 14. The example model file is
unchanged: 31 older test modules and runners map system values without groups. The relation matrix's
row side may have the same gap; not checked.

**Real-model try** (the user's local `qwen3.5:9b-mlx`, `.dev/settings.env`, one transaction rolled back, tool
`scratchpad/ap2-try/try_mapping_targets.py`). The first three calls, before the sizing, ran back to back
without being announced: 19 s with no candidates (the workspace has none of the target type), 82 s not
answering in shape, 133 s ending in Ollama's `500` with a prompt of about 6,100 tokens against the 4,096
window Ollama serves the model with. They loaded the user's laptop for about four minutes. After the
fixes, one announced call with the window set to 4,096: 14 sources and 15 candidates (about 940 tokens),
answered in 54 s in shape; 7 sensible targets (98%, 95%, 90%), 7 left unmapped, among them sources whose
code prefix names a candidate; the reasons named the references, fixed in `mapping-targets/2` (not tried
again).

**Checks:** J49 (30 cases, two configurations), the proposal unit tests, `test_config`, J48, J31 and the
contract module: passed after the final change (the last run 216 and 11). Earlier, by the backend agent:
`contract` 82, `startup` 198, `mapping or feed` 425, `change_sets or jobs` 1,200 (5 min 43 s, over the
3-minute package ceiling: a harness ceiling defect to raise), the serial part 3. Frontend: focused Vitest
(149), `npm run lint` (0 errors, 9 older warnings), `npm run build`, `tsc -b`, `test:browser:ai` (73
checks, axe 0 violations, light, dark, 390px, keyboard, on an outgoing and an incoming view).

**Not verified:** the J49 inbox notice of a finished job (the trigger lists the kind); a stopped, failed or
partly refused job in the browser (the fake answers at once); the published history mark in a browser
(component test only); a second model in the browser runner (the starter's two bindings); the screenshots
of the result dialog and 390px dialog after the final layout fix; the reason wording of `mapping-targets/2`
on a real model; the quality of the 9b model's matches beyond one call. The job page shows an `aiProposal`
job in the generic layout without its tally. On a phone the grid's own scroll area hides the end of the mark
pill, as it hides the Action column already.

**What the user cannot do yet:** values for empty fields and missing related records (AP4), dry-run triage
(AP5), instruction-driven tasks (AP6), AI in model authoring beyond names (AP3), assistant access (AG1–AG4),
summaries (AO1–AO3).

## AP3: Model authoring and model mappings

**Folded into AP6 on 2026-10-28 (AP-D27);** the text below is kept as the scope the assistant's tools cover.

**Journey:** a model administrator imports a workbook; the inference's proposals now carry better
names, descriptions, enum detections and relation guesses, each with a reason, in the editor as
Proposed steps. A model mapping's candidate list is re-ranked by meaning, with the reason shown.

**Scope.** The 0.10 assistant's request (headers, a bounded number of rows, the proposals' types)
becomes the `modelNames` purpose and is widened to descriptions, enumerations and relations; its
answers become proposals of the existing patterns, requiring the proposal they refine. For model
mappings, the provider re-ranks each source type's top alternatives (evidence stays; a semantic score
is added). Needs send level `samples` for enumerations, `structure` for the rest.

## AP4: Values for empty fields and missing related records

**Folded into AP6 on 2026-10-28 (AP-D27);** the text below is kept as the scope the assistant's tools cover.

**Journeys:** (1) a steward filters the records with an empty description, asks for drafts and gets a
change set of proposed values they edit in the list's cells. (2) A localisation steward filters the
records with no German translation and gets proposed translations as new related records.

**Scope.** A bulk action on a collection selection or filter (the 0.9 bulk-dialog pattern). Two
targets, both chosen in the request (AP-D10): an **attribute** of the record, or a **related record**
the record lacks (a record of a chosen type, under a chosen parent, joined by a chosen relation type:
the shape the import profile's `relatedRecord` binding already writes, where a translation and a
system mapping are configurations, ADR-032). In the example model a translation is a related record,
not an attribute, so (2) is the translation case; nothing in the code names it. The result is
machine-proposed changes in a change set. Needs send level `values`; hidden below it. AP6 can
produce the same plan from a sentence, and AP4 is the one-click form of it.

## AP5: Dry-run triage

**Folded into AP6 on 2026-10-28 (AP-D27);** the text below is kept as the scope the assistant's tools cover.

**Journey:** after a dry run of a 40,000-row file with 3,100 failures, the person asks for a
summary and sees eight groups ("200 rows: trailing spaces in `code`"), each with a count, three
example rows and, where one exists, a suggested step (a trim rule, a value map entry).

**Scope.** The dry run already checks every row (D67, checks cover the whole set). The grouping is
deterministic: failures grouped in PostgreSQL by code, field and a normalised pattern. The provider
only names and explains each group from its aggregates and a few examples and proposes a step; it
never sees, and never replaces, the full result. Suggested steps appear as Proposed steps in the
import profile's editor. Send level `samples`.

## AP6: Instruction-driven tasks

**What it is.** The way people already use an assistant: type what you need in loose English and attach
what you mean. It is the engine's inference, import, mapping, batch and change-set machinery driven
by a sentence, with every step visible and nothing run until the person confirms.

**What exists to build on (checked 2026-10-27 against API.md and MODEL_AUTHORING.md):**

| A person says | Becomes | Exists |
| --- | --- | --- |
| "Create a model for this and import it" | A model draft from the workbook (inference, new application or new model), then the import profile and its dry run | Yes (0.10 A5/A6) |
| "Map this to the current model and import" / "extend the current model" | Inference in extend mode (columns to existing types and attributes first), additions as Proposed steps, then the import | Yes (0.10 A6, "additions to the model") |
| "Change the values of X from column Y" | An import profile with a key column, `record` mode and attribute columns; `key.versionColumn` for a version claim; a preview before it writes | Yes (0.9 J2/J6, previews K2) |
| "Add these translations / this system variant" | A `relatedRecord` binding (a translation and a system mapping are its configurations) or a `relation` binding with `matchBy`; `missing: create` for languages and targets that do not exist yet | Yes (0.9 J3, 0.10 A5a) |
| "Add a new business" (a record) | A batch `create` or `upsert` item, with its parent and relations | Yes (0.9 B1) |
| "Relate A to B but only where C is assigned" | Model-draft operations for the relation type and its binding, then `ensureRelation` items for every record the query matches (`related`, `not`) | Model part yes; the items from a query: AP-D18; conditions beyond one hop: AP-D17 |

**The journeys (the test cases come from these, one per kind):**

1. *New model.* The person attaches a 9-sheet workbook and writes "build a model for this and load it".
   The assistant shows what it read (sheets, blocks, columns, guessed meaning), proposes the model as
   Proposed steps in the model editor and the import profile beside it; the dry run says "41,200
   rows: 41,000 new, 200 refused" with the reasons; the person fixes two columns by saying so and
   runs it into a change set.
2. *Into the current model.* "Add these to the existing lists, update the ones that exist, match on
   the code column." The profile it writes shows the key column, record mode and a count of what
   would be created and changed; no new type is proposed unless the file needs one.
3. *Extend, then load.* "The file has a column the model doesn't have." The assistant proposes the
   attribute as a model-draft step and the profile that fills it, both in one change set order.
4. *Values from a column.* "Set the sort order from column Y." Only the changed records are shown,
   with old and new value.
5. *Translations and variants.* "Add the German names in column F and the webshop codes in G."
   Related records and relations with the missing language or target created, as the profile already
   does.
6. *A conditional relationship.* "Link every duration to the stations, but only stations with a
   driver assigned." The model gets the relation (steps), the preview counts the pairs the query
   matched, and a condition the query cannot say is refused with its reason.
7. *Next month.* The same file layout arrives; the saved profile runs it without the assistant, and the
   assistant can be asked only for what changed.

**Scope.** The `task` resource and its routes (`POST /tasks`, `POST /tasks/{id}/messages`, `GET
/tasks/{id}`, plan and dry-run reads; a job on the existing worker, with cancel, progress and inbox
notice), the planning tools of AP-D15, the plan model (steps of the AP-D12 kinds, each with origin and
reason), the revision rule (a follow-up creates a new plan version; the person's own edits to steps
survive it), the clarifying question shape (AP-D16), the task page (AP-D20), Settings › AI's
per-feature provider check (AP-D21). Permissions: the task needs "Use AI proposals" plus, to run its
result, the permissions that import, batch, model editing and publishing already need; the assistant
can do nothing the person cannot.

**Out of scope:** files other than XLSX and CSV (what source files accept today), reading a document or
image as data, a task that runs by itself on a schedule, changing the engine's import semantics to suit
the assistant.

**Risks, said plainly.** (1) Loose English is ambiguous, so the plan's reading is shown before any
number, and it asks when the answer changes the outcome. (2) A confident wrong plan is the main danger;
the controls are the dry run of every row, the change set, the approval, and the origin on every step.
(3) The first plans on a messy workbook will be wrong sometimes; the real-file try (AP-D22) is how we
find out how often, before release. (4) Provider cost grows with the thread; AP-D14 keeps each call
small and `AI_MAX_STEPS` bounds the loop.

### AP6 in detail

**Status of this part:** drafted 2026-10-27 after the user approved AP-D12–AP-D22 and the mock-up of
the task page and of the editor with its side pane (the mock-up is the visual reference; it is not
kept in the repository). AP-D23–AP-D26 below were approved by the user the same day.

**What the code already offers (read 2026-10-27, so the plan names real places):**

- A model draft's step has an `origin` JSON (types `patch`, `undo`, `proposal`; the proposal origin
  carries the anchor, keys, elements created and a snapshot), written by `history.apply_steps`; the
  inference's proposals have stable IDs and statuses `open`, `held`, `applied`, `rejected`
  (`engine/sources/inference/run.py`, `compare.py`). An assistant's step is one more origin type, so
  the editor's "Proposed because", undo/redo and "held" logic apply unchanged.
- The model editor is `features/model-editor/ModelEditor.tsx` (1,239 lines) over a two-column grid
  (`--editor-pane` and the centre); it already has `DryRunPanel`, `IssuesAndHistory`, `ProposedBecause`,
  `useInference` and `ProposeDialog`. `ui/` has `ResizeHandle` but no `SidePane`; the pattern is
  saved in SAVED_UI_PATTERNS.md and nothing of it is in the product.
- Change-set entries (`ChangeSetObject`, `ChangeSetRelation`) hold the current state of a record or
  relation (name, attributes, version, deleted), with **no origin column**. Audit events
  (`AuditEvent`) carry `cause_kind`, `cause_id`, the actor and a `changes` JSON. So AP-D5's
  "origin on a change" needs a nullable `origin` column on the two change-set tables (additive
  migration) and, at publication, the origin copied into the audit event's `changes` so history can
  show it. This is more than the one line AP-D5 implied; it is AP1's first spike and is settled
  there before AP2 or AP6 depend on it.
- A draft's import profile is edited by operations (`setSource`, columns, `valueMaps`, …;
  API.md § A draft's import profile) and checked by the dry run on every row (`POST
  /model-drafts/{id}/dry-run`); an instance profile is checked by the import preview and confirm
  (`POST /imports`, `POST /jobs/{id}/confirm`); a batch has `stage: preview` and confirm. These are
  the three "check" mechanisms the task reuses, one per kind of step.
- Jobs: kinds are dispatched in `engine/jobs/worker.py`; a new kind `aiTask` is added there with
  cancel, lease renewal and the inbox notice that other kinds have.

#### Decisions (new, approved)

| # | Question | Recommendation |
| --- | --- | --- |
| AP-D23 | Who sees a task? | **Approved by the user 2026-10-27. Its owner, and a person with the permission to administer the workspace it targets.** A task holds the person's instructions and the assistant's replies, which can name records. Not shared by default; handing a task to a colleague is out of scope for this release. |
| AP-D24 | What is stored, for how long? | **Approved by the user 2026-10-27. The instructions, the assistant's replies, the plan versions and the dry-run summaries, for `AI_TASK_RETENTION_DAYS` (default 90) after the task finishes or is abandoned; never the rows or samples sent to the provider** (AP-D4: content is not kept unless `AI_LOG_CONTENT` is on). The source file follows the existing source-file retention. A saved profile and the change set are ordinary resources and outlive the task. |
| AP-D25 | How many files and how large? | **Approved by the user 2026-10-27. Up to three files per task (`AI_TASK_MAX_FILES`), each within `IMPORT_MAX_BYTES`;** XLSX and CSV only, as source files accept today. A task over a limit is refused when attached, not when it runs. |
| AP-D26 | How does a revision treat the person's edits? | **Approved by the user 2026-10-27. A step the person edited or removed is theirs: a revision never overwrites it.** Each step has an `owner` (`assistant` or `person`); the assistant may propose an alternative for a person-owned step in its reply, as text, never in place. A person-owned step also keeps its mark off. This is the rule that makes the editor feel like an editor and not a regenerate button. |
| AP-D27 | One assistant or a helper per feature? | **Approved by the user 2026-10-28. One assistant, every AI capability a tool of it, offered where its situation occurs.** The AP6 loop is the only AI that plans: it starts from the rules' result, reads through tools (the profile over every row, any sheet by range including skipped ones, distinct values, overlaps, the model and records, AP2's matcher, the dry run) and writes only the editor's operation catalogue and profile operations, as proposals in the editor's Proposed list. A question is answered in the thread from what it read; an action becomes a plan that runs on one confirmation (AP-D13). AP-D12 gains a sixth step kind, **a capability's job** (AP2's matcher, value drafts, the dry-run grouping). Entries: the task page, the editor's pane and **New from a workbook**, whose AI path is the workbook and an optional words field (the assistant proposes the dialog's choices with reasons); without a provider the dialog stays as it is. AP1's rename becomes step 3 of the workbook flow; AP3, AP4 and AP5 are folded in. Why: the separate helpers did not reach each other (AP2 could not serve a workbook load), and a capable provider (Claude, ChatGPT) can be called as often as a task needs. |
| AP-D28 | A draft-only change to a released element nothing holds | **Approved by the user 2026-10-31. It applies when it would affect 0 records, values and relationships**, counted in every workspace running the model and their change sets; above 0 it is refused as before. Amends 0.10 D17 and the roadmap's "blocked until 1.0". Why: activation checks the workspace's data again (`*_IN_USE`, required checks) and consumer contracts, so the refusal at edit time protected no data, and a released model with no data could not be edited. A key change stays refused whatever the count: "public IDs and model keys are stable", and an integration names elements by key where no guard sees it. Cost: one count per released element an operation touches, once per request. The menu cannot know the count without counting every element on each outline read, so a released element's actions stay listed, reading "Refused if data uses it" |

#### The plan, as data

A **plan** is a numbered version of a task's steps (a new version for every revision, the earlier ones
kept for undo). A step is `{id, kind, owner, params, reason, evidence, confidence, status}`:

| `kind` | `params` are | Applied as | Checked by |
| --- | --- | --- | --- |
| `modelOperation` | one model-draft operation (kind and parameters, the 67 kinds) | `history.apply_steps` on the draft, origin `assistant` | the draft's validation and the dry run |
| `profileSource` | a draft profile operation or an instance profile document part | the draft's profile operations, or a saved import profile | the dry run, or the import preview |
| `batchItems` | an item template and the query that selects its records (AP-D18) | a batch with `stage: preview`, then confirm | the batch preview |
| `destination` | the change set (new or chosen), and the profile key to save | creates the change set; saves the profile | none |
| `note` | text only | nothing | none (used for "I can't do this because…", AP-D12) |

`status` is `proposed`, `applied`, `held` (the person decided otherwise) or `refused` (the engine
refused it, with the code and path). The reading of the file (sheets, blocks, columns, guessed meaning
and evidence) is part of the plan version, so it is edited and revised the same way.

#### Routes (management API; all need the AP1 permission and the owner check of AP-D23)

| Route | Purpose |
| --- | --- |
| `POST /api/v1/ai/tasks` | Create a task: instruction, source file IDs, target (a workspace, optionally a draft or a change set). `202` with the job. |
| `GET /api/v1/ai/tasks`, `GET /api/v1/ai/tasks/{id}` | The person's tasks, newest first (ADR-030 paging); one task with its latest plan, reading, question and check. |
| `POST /api/v1/ai/tasks/{id}/messages` | A follow-up instruction or the answer to a question. `202` with the job; the plan gets a new version. |
| `GET /api/v1/ai/tasks/{id}/plans`, `…/plans/{version}` | The plan versions. |
| `PATCH /api/v1/ai/tasks/{id}/steps/{stepId}` | The person edits or removes a step (it becomes theirs, AP-D26). |
| `POST /api/v1/ai/tasks/{id}/run` | Confirm: runs the checked plan into its destination, with `expectedPlanVersion` (a plan changed since is `409`). |
| `POST /api/v1/ai/tasks/{id}/cancel` | Cancel the job in progress. |

The model-editor side pane uses the same routes with the draft as the task's target; no editor-only
route exists (the API is the product).

#### The planning tools (AP-D15, AP-D19)

Read-only and in-process, one implementation each, later exposed by Track A: `describeModel` (applications,
types, attributes, relations, bindings), `describeFile` (sheets, blocks, columns, the profile's
statistics and a bounded number of rows), `findRecords` (the model-aware query with a count and a
bounded sample), `trialPlan` (the dry run or preview of the current plan, returning the summary and
the first refusals). The loop is bounded by `AI_MAX_STEPS`; a tool call that would exceed the send
level returns "not available at this level" and the plan says what it could not check.

#### The workbook flow (AP-D27)

What the assistant adds at each step of New from a workbook (MODEL_AUTHORING § The editor, § Operation
catalogue, § Pattern catalogue):

| Step | The rules today | The assistant adds |
| --- | --- | --- |
| 1 Start | The dialog's choices, made before anything is known | Proposes the choice (new application, new model, additions) with its reason |
| 2 Read | Sheets, blocks, lists; a sheet without a table is skipped | Reads skipped and prose sheets; which lists belong together or are not data |
| 3 Types | One type per sheet or list, named from headers | Merges, splits, names as the business does, writes descriptions |
| 4 Applications | One application per workbook | Groups types into applications and navigation groups by meaning |
| 5 Hierarchy | Repeated parent, level columns, fixed thresholds | Confirms or corrects the parent by meaning; multi-level trees |
| 6 Attributes | Value type from cells; one header, one attribute type | One field under different headers; dates as text; required by meaning |
| 7 Relations | Keys matched at 90%; delimiters; flags | Relations the values hide; across applications; names, cardinality and binding criteria |
| 8 Translations | Language by header word or value shape | The language from the values; column pairs |
| 9 Matching | Exact key or name; missing IDs reported | AP2's matcher: a proposed record per unmatched value, as a value-map entry; new ones proposed for creation |
| 10 Values | Placeholders; drift by frequency | Variants by meaning; which name is right |
| 11 Views | Defaults from the model | Useful columns and filters per type |
| 12 Dry run | Every row checked, refusals listed | Refusals grouped by cause, a fixing operation proposed, run again |
| 13 Next file | The saved profile, differences reported | What changed and the profile change it needs |

#### The workbook assistant by what the file means (designed 2026-10-28, replacing the step-based slice)

**Why the earlier slice went.** It cut the work along the rules' steps (types, applications, hierarchy)
and so covered a part of one case, a totally new file, and only the model's shape: no import, no update,
no extension of a model that holds data. The user named the cases (2026-10-28); the design starts from
them.

**Requirement trace.** "A few words and a workbook give the model and the import", against the data a
workspace already holds: every case below ends in the model the file needs and its data loaded into a
change set. Reached from New from a workbook, a workspace's Import, the task page and the editor's pane
(the same assistant, AP-D27). Calls the rules, AP2's matcher, the dry run and restructuring.

**The journey.**

1. The person gives the workbook, a few words if they like, and where it goes: the workspace they are
   in, or a new one.
2. The assistant reads the file against that workspace's model and records (profiles over every row,
   any sheet by range, distinct values, overlaps with stored records by key, by name and, through AP2's
   matcher, by meaning) and shows **its reading per table** (a sheet or a list; a file mixes cases),
   each with its evidence:

| Case | A table is | Recognised by | Model | Data |
| --- | --- | --- | --- | --- |
| A | An update of existing data | Its keys or names match a type's records ("180 of 200 codes") | none | Update the matched; create the rest, or hold them back; changed values listed |
| B | Additions to existing data | It matches a type, with columns the type lacks | New attributes on the type | Update, filling them |
| C | A new kind of thing related to existing data, or a new relation between existing types | New records whose column points to existing ones; or two existing types' keys side by side | A new type in the application and its relation; or only the relation | Create and link; or only link |
| D | Something new beside existing applications | Tables that belong together, related to existing types | A new application, its types and relations, linked across applications | Create and link |
| E | Something totally new | Nothing matches | A new application, or a new model in a new workspace | Create |

3. The person corrects the reading where it is wrong, by the choices it offers ("an update of Services,
   not a new list"; "match on the code"); the words may say so up front. It asks only where the answer
   changes the outcome (AP-D16).
4. The plan: the model part as model-draft steps marked Proposed in the editor (attributes, types,
   applications, relations, hierarchy, names, binding criteria); the data part as the import profile
   (keys, record mode, relation columns, value maps from the matcher, translations, `missing`).
5. One dry run of every row, counted per table: created, updated (old and new values), unchanged, linked,
   refused with reasons. The assistant fixes what it can and runs it again.
6. On confirmation, in the order the engine needs: **data for a changed model loads only once that model
   is active in the workspace**, so a model change (B–E) is installed and activated first, after the
   compatibility preview shows what it does to existing data; then the load runs into a change set. Case
   A loads at once.
7. The result: the workspace on the model the file needs, a change set of created, updated and linked
   records for the normal approval, and the saved profile, so the next file of the layout runs without
   the assistant.

**Also in the design (found beyond the five cases):** records missing from a full list (retire or leave
them: the profile's `missing`); conflicts per field between the file and stored records (name drift:
which wins); duplicates by meaning (the matcher, so no second record is created); translations and
variants of existing records (`relatedRecord`); a system's codes as system values under the right group,
mapped to master records (AP2's case arriving as a file); existing records moved under new parents and an
existing model reshaped (the 0.8 restructuring in a change set, in phases); the next file of a layout (the
saved profile; the assistant explains what changed).

**How it talks to the provider** (AP6a-D1, kept): turns of structured answers (`reads`, `operations`,
`done`, `note`) through both adapters; the engine runs the reads, tries the operations as hand edits are
tried and sends the results back; refusals return with their reason. `AI_MAX_STEPS` and the window
sizing bound a run; a failure keeps what was proposed and the rules' result. The rename helper goes
(AP6a-D6).

**Providers for the work** (the user, 2026-10-28): the local 9b and 27b models for development tries,
DeepSeek through its API for cheaper real tries (OpenAI-compatible; its acceptance of strict JSON-schema
answers is checked before the first try), Claude or ChatGPT later. A 9b model is not expected to plan a
workbook well; the engine's side is judged with it, the quality with a stronger model. **Added 2026-10-29:**
Claude Sonnet through the developer's Claude Code sign-in (`AI_PROVIDER=devtools.claude_code_provider:provider`,
`backend/devtools/`, never deployed) for development tries; every try's usage goes into the
[AI usage log](#ai-usage-log-for-hosting-cost-planning).

**Slices, each usable end to end in the browser on a real file** *(superseded 2026-10-29: the user rejected splitting the cases; AP6a stays as delivered, AP6b–AP6e are replaced by [one package](#ap6-the-assistant-designs-and-loads-one-package-replacing-slices-ap6bap6e-planned-2026-10-29))*:

| Slice | Delivers | With |
| --- | --- | --- |
| AP6a | First, the removal of the naming helper (New from a workbook's "Also ask the AI assistant for clearer names", the inference's `assistant` option, purpose `modelNames` and `inference/assistant.py`, its texts, J48.2/J48.6/J48.7 and their docs; New from a workbook runs on the rules alone until AP6c). Then case A and the core every case needs: the reading per table against a workspace, correcting it, the plan (profile), the dry run with the assistant fixing what it can, the run into a change set | Matching by meaning, conflicts, records missing from the file |
| AP6b | Cases B and C: model extension, installed and activated before the load | Translations and variants, a system's codes as mappings |
| AP6c | Cases D and E: new applications and new models | Restructuring of existing records and models |
| AP6d | The free-text chat on the same plan (questions answered, actions planned) | The task page and the editor's pane |
| AP6e | Conditional relations; the real-file close-out | AP-D17, AP-D18; the acceptance workbook |

Each slice's plan lists its journey cases and its mock-up for one approval.

#### AP6: the assistant designs and loads (one package, replacing slices AP6b–AP6e; planned 2026-10-29)

**The requirement, checked line by line.** The user's words in the [Outcome](#outcome): the five cases
(an update; additions; a new relation; something new but related; something totally new), the eight
scenarios of 2026-10-27, and "a few words, an xls, the model and the import; we don't build
limitations". Every one is an acceptance case below. No case is left to a later slice; there is none.

**Why AP6a cannot be extended into it.** In AP6a the engine's rules decide what a file is, and the
language model gets narrow turns to correct them, against the model as it is. The cases B–E need the
opposite: the language model **designs** (which concepts become new applications, types, attributes
and relations, which are plain lists, what are translations and mappings to other systems) and the
engine **carries out and checks** the design. Evidence (AI usage log, 2026-10-29): one call with the
file's profile and the model, asked to design, gave the user's Timetables workbook a new
application and object type, codelists for the plain lists, the external system's IDs as mappings and
the translations under the model's translation types, with four real questions. AP6a's parts are
kept as tools: profiling over every row, the reading per table and its evidence, matching by key,
name and meaning, value maps, the dry run of every row, the fix turn, the change set, the task page.

**How it works.**

1. **The person** gives the workbook, a few words (the instruction: "create a model for this and
   import", "add this translation", "change the values of x from column y", "relate durations and
   stations only where a driver is assigned"…) and where it goes: the workspace they are in, or a new
   one.
2. **The assistant designs** (prompt `workbook-design/1`): it reads the file's profile, the
   workspace's model with its hierarchy, relationships and applications, and what the workspace holds,
   and reads further with tools (any range of cells, a column's distinct values, stored records by a
   word, the rules' reading of a table) until it can answer the design:
   - **the model changes**: applications, object types with their parents, attributes, relationships
     (within and across applications), as model-draft operations;
   - **the records the structure needs** that the rows do not give (a domain, a codelist, a language,
     a system and its groups);
   - **per table**: what its rows become (records of a type, translations, mappings to a system,
     relationships between existing records, changed values of matched records, or not data), its
     key, every column's target, where its records stand, and conditions ("only where a driver is
     assigned": the query of AP-D17);
   - **questions**: only what the data cannot answer.
3. **The engine carries it out in a model draft** of the workspace's model (or a new model for a new
   workspace): the operations are applied as the editor applies them, each checked by the draft's
   validation; the draft's import profile binds the file. A refused operation goes back to the
   assistant with its reason, which revises; an answer that only repeats a refusal ends the turns
   (AP6a's guard). Case A (nothing to change in the model) needs no draft and uses the workspace's
   profile as AP6a does.
4. **The person sees the design**, not a report: the task page shows the model changes (new
   applications and types as a small diagram, new attributes and relationships, each with its reason
   and marked Proposed), the records to create, each table's destination and the questions with their
   choices. "Open in the model editor" opens the draft itself, where every step is edited as any other.
   Answering a question or changing a step re-plans what depends on it.
5. **One dry run of every row** against the draft (the draft's dry run): counted per table, refused rows
   with reasons; the assistant's fix turn proposes value maps and runs it again (AP6a).
6. **On confirmation**, in the order the engine needs: the draft is installed and activated in the
   workspace after the compatibility preview (a model administrator's step: a person without it gets
   the design saved and the task waits for an administrator, who sees it in the inbox); then the load
   runs into a change set for the normal approval, and the import profile is saved so the next file
   of the layout loads without the assistant. Live data is never written by the task.

**The instructions without a model change** (scenarios "change the values of x based on column y",
"add this translation", "add this system variant", "add a new business", "a relationship only where
a driver is assigned") are the same plan with an empty model part: the import profile's record mode
and value columns, `relatedRecord` translations, system values mapped to records, one record, or the
AP-D17/AP-D18 query building `ensureRelation` items in the database. An instruction the engine has no
operation for is answered "I can't do this because…", never approximated (AP-D12).

**What changes in the code.**
- Engine `tasks/`: `design.py` (the design turn, its answer, its checks), `draft_plan.py` (the design
  as draft operations and the draft's import profile, through `model/authoring`), the turn loop with the
  read tools of AP-D15 (`describeModel` with hierarchy and relationships, `describeFile`, `findRecords`,
  `trialPlan`), the conditional relation step; `reading.py` and `turns.py` stay as tools.
- A task has a `draftId`; states add `designing`, `designed`, `awaitingActivation`; the job phases add
  `design` and `activate`. Migration: the column and the states.
- API: `GET /ai/tasks/{id}` adds `design` (model changes, records, tables, questions);
  `POST /ai/tasks/{id}/answers` (answers to questions); `POST /ai/tasks/{id}/run` installs, activates
  and loads, or waits for an administrator. Documented in API.md; the OpenAPI lock re-baselined.
- Frontend: the task page's design view (diagram of new and changed types, the records, the tables'
  destinations, the questions), "Open in the model editor", the activation step; the reading, check and
  loaded views of AP6a reused.

**Acceptance (each with a real provider on the user's own files, usage logged; done only when all
pass):**

| Case | Try |
| --- | --- |
| A An update | Lines & Routes into the workspace whose model and records came from it |
| B Additions | The same workbook with new columns, into that workspace |
| C A new relation to existing data | A sheet of new records pointing to existing ones (a workbook the user names, or the Timetables workbook's categories into a workspace holding them) |
| D Something new but related | The Timetables workbook into a workspace holding the master data: a new application linked to it |
| E Something totally new | The Timetables workbook into an empty workspace, and into a new one |
| Scenarios | Each of the eight instructions on the user's workbooks, as worded by the user |

Journey cases J50.18 onward with the fake provider prove the engine's side (each case's draft, the
activation order, refusals, the waiting task); the quality is judged on the real tries above.

**Not in this package, said plainly:** a document or an image as data; a task handed to a colleague or
run on a schedule; Track A (the same tools over MCP) is its own package.

#### AP6r: the assistant proposes the model, the steward shapes it, then it loads (planned 2026-10-30)

**Why.** The AP6 loop measured success by "the engine refuses nothing". On the user's samples it
loaded cleanly and still built the wrong model: flat lists where the data groups rows, new types
duplicating records the workspace holds, relationships readable from one end only. Whether a model
is good is not something a dry run checks, and the steward saw the model only after the load. The
requirement (§ Outcome) asks for what a Claude Code session does: analyse, decide the structure,
let the person steer in plain words, then load. AP6r changes what the assistant decides and when,
not the engine: every operation it uses is one the editor and the import already have.

**What changes, for any workbook (no file, sheet or name is known to the code or the prompt):**

1. **Two phases.** *Model*: the assistant reads what it needs (sheets, values, stored records,
   queries) and proposes the model: model-draft operations plus a plain description per type
   ("Countries, under their region; a sponsor belongs to several countries, so it is related to
   them"). No import profile yet. *Load*: only after the steward accepts the model, the assistant
   maps the sheets onto it (profile, data sheets) and the dry run decides, as today.
2. **The steward shapes the proposal.** The task page shows the proposed model as a short outline
   (types under their parents, what each reuses from the workspace, the relationships with the
   page that shows each end, the translations, the columns left out with their reasons) and a box
   for corrections in words ("Sponsors belong to operators, not to new stations"). A correction is a
   new model turn with the words; "Accept the model" moves to the load phase. Nothing is installed
   or loaded before that.
3. **Design checks the engine computes for any workbook**, sent to the assistant with every model
   turn and shown beside the outline:
   - *Reuse*: a new type whose record names match a stored type's records (by the sheet's
     values) — "these 7 names are already Countries in the workspace";
   - *Grouping*: a column whose value determines other columns of its rows (few distinct values,
     each always with the same companions) loaded as a plain attribute or relation instead of a
     parent — "REGION groups the rows";
   - *Both ends*: a relationship no page of its "to" type shows;
   - *Translations*: a column headed by a language (the reading's own detection) not loaded as
     a translation;
   - *Left out*: columns without a reason (as AP6's `leftOut`).
   The assistant fixes or explains each one; the steward sees what is still open.
4. **Full context for the configured model.** The request is sized to the provider's window as
   configured (`AI_CONTEXT_TOKENS`), not to a small local model's: with Sonnet the whole reading,
   the model and the design are sent; compaction stays for small windows only.
5. **Acceptance by target, not by refusals.** Each sample the user gave has a written target (kept
   outside the repository: it names the example data). A run is judged against it; new samples get
   the same treatment. The code and the prompt never see a target.

**What stays.** The task, the draft, the reads, the working copy, the dry run, the load, the
journey bar, the engine's import-path fixes of 2026-10-30. **What goes.** Designing the model and
the profile in one answer; the call budget as the only stop (the model phase stops when the steward
accepts).

**Tests.** J50 for the two phases with the fake provider (a correction in words starts a new model
turn; nothing installs before acceptance; each design check fires on a small workbook built to show
it). Real tries: each sample against its target, Stations first, one run each, usage logged.

#### AP6 progress (2026-10-29, in delivery)

**The core is built and works on the user's own workbooks** (real tries in the AI usage log):

- **Timetables** into an empty workspace (cases D/E), checked with nothing refused:
  - a new application, with an timetable type and an timetable category type and their
    attributes;
  - the translation join, made required as the model's other translation joins are;
  - the 7 languages and translation groups the structure needs;
  - 1,756 records and 1,500 translations;
  - one real question (category translations).
- **Lines & Routes** into the workspace built from it (case A): the saved profile kept, no
  model change, every one of 87 lists checked; one call, 3 s, $0.08.

**What was built:**

- **Engine** `tasks/`:
  - `design.py`: the design turn, its answer and the model brief with the hierarchy, required joins,
    type rules, and what the draft added marked `new`;
  - `draft_plan.py`: the draft, the working copy with `Structure` sheets, applying operations, the
    profile check, refusals with examples;
  - `design_job.py`: the turns in the task's job, the dry run against the draft, design rounds on
    refusals (up to 3), answers, and the load (install, activate, change set, saved profile);
  - lists with nothing to decide go in a line each and load as the rules read them; the request is
    sized to the model's window;
  - the retention sweep deletes a task's draft with it.
- **Migration** `20261119_03` (`ai_tasks.design`, `ai_tasks.draft_id`). The worker runs a task's dry
  run against its draft when it names one.
- **API:**
  - `design`, `draftId`, the design check, `result.releaseId`, phase `designing`;
  - `POST /ai/tasks/{id}/answers`;
  - `/run` on a design installs and activates when the model changed (needs Model release);
  - the OpenAPI lock re-baselined.
- **Frontend:** the task page's design view (summary, model changes, Open in the model editor, records,
  where each sheet goes, questions) and the design check (per sheet, refusals, the order of what
  confirming does; the load button hidden without Model release).
- **Tests:**
  - J50.1–J50.20 rewritten to the design flow (with the fake provider: the default design, scripted
    model changes for cases B and C/D installed, activated and loaded, answers, fix rounds, failure,
    the window, Model release);
  - unit tests of the brief and the structure sheets;
  - J47 lists `/answers`;
  - the foreign key review lists the task's draft.

**Found and fixed on the way:**

- refusals went back without their messages;
- a reused required relationship was not marked required;
- a shadowed variable sent the model alone;
- a request of about 236,000 characters for 87 lists;
- the loop resending an accepted design;
- the load reading the workspace's model before the activation committed;
- the saved profile missing the kept lists.

**Also built since:**

- **An instruction without a workbook**, and **relationships where a condition holds**
  (`tasks/links.py`):
  - two model-aware queries, the pairs counted in the database;
  - one batch built by `INSERT … SELECT`, after the import when there is one, queued by the worker;
  - where a record may hold only one, its set is replaced (counted as `replaces`); a rule giving it
    two is refused.
  - Real try: "Give every timetable type in the Lab category the duration 15 min" gave 15 durations
    replaced in a change set.
- **The page:** model names instead of keys, the relationships card, "Ask the assistant" without a
  workbook, the spacing and the 390px stacks.
- **Tests:** J50.21, J50.21b and J50.22; the browser runner on the design flow.

**Where the cases stand on real files (2026-10-29):**

| Case | Status |
| --- | --- |
| A, an update | works: Lines & Routes, 87 lists, one call |
| E/D, new or related application | works: Timetables into an empty workspace, nothing refused |
| B/C, additions and new relations to existing data | works (2026-10-30, run 6): Timetables into the workspace holding the example model, two attributes added, every row and translation loaded into a change set |
| Scenario: relationships only where a condition holds | works (Lab durations) |
| Scenarios as worded by the user (translations, system variants, a new business, values from a column) | not tried yet |
| The user's further samples (2026-10-30) | Reductions and Tariff File work (new applications, nothing refused); Sponsor Sources loaded by the user (477 new, 54 changed); Stations stopped mid-run, its two refusal causes (empty cells in repeated rows, one key in two sheets) fixed in the import engine since |

**Still to do in this package:**

- **Cases B/C on the existing model.** The refusals are about reserved slots matched by name
  (ambiguous or missing), a cardinality and a required code; the translations sheet is left out.
  The design needs more rounds and a way to look up stored records before matching by name.
- **Real tries of the remaining scenarios.**
- ~~**`GET /ai/tasks/{id}/changes` for a design.**~~ Done 2026-10-30: `?source=` pages a design
  sheet's changed records through the dry run's own profile and the draft's model; the design check
  shows them behind a button per sheet (J50.1).
- ~~**Removing AP6a's unreachable parts.**~~ Done 2026-10-30: the read, match and fix turns, their
  prompts and `matching.py` are gone, and the phases `asking`, `matching`, `fixing` with them. The
  per-table choices and the plan route stay: they are the path of a task read without the assistant
  offered.

**Found on the real B/C runs of 2026-10-30 and fixed (each in the AI usage log):**

- the dry run's refusals were lost on a round's later turns: they are kept until the next dry run;
- each turn was sent the outcome but not the design so far, so a round rebuilt the design instead of
  fixing it (round 3 went from 1 refused row back to 11): the design so far goes with every turn, and
  a part the answer leaves out is kept (`workbook-design/4`);
- the working copy dropped the formulas' last values (the Translations sheet's ID column is a
  formula), so every row was skipped for an empty key without a word: the copy keeps the values, and
  the check reports skipped rows (`skipped`, refused as `ROWS_SKIPPED` when most of a source's are);
- a related record's parent read from a column took no value map, so a language word could not find
  its language record: `parent.valueMap` in import profiles (J27.1);
- `CARDINALITY_VIOLATION` did not say which relation: it names the relation and the end.
- a change-set edit re-checked relationships the record already held against their candidate
  criteria, so the load refused rows the dry run passed: kept as live does (D175);
- a dry run that could not run (a header under a row of group headings) failed the task: it goes
  back to the assistant as `dryRun.failed`; each round's refusals are a history it sees;
- rows repeating a key conflicted where one left a cell empty; rows of two sheets keyed alike made
  two records: both merged now;
- loading the same file again refused the profile save: the profile's next version;
- the loaded page listed the rules' first reading as not loaded, the shown model stayed stale after
  activation, and the installed release was numbered below the newest: all three fixed.

**AP6r built (2026-10-30):** the two stages, the correction and acceptance routes, the design checks,
the proposal page, the bar's step, the assistant's page operations, `unpivots` (see the AP6r section).

**Still to do:** the journey bar the user asked for (2026-10-30: a bar below the top bar following the
import across the task page, the model editor and the change set, Close returning to the task,
Stop / Start again / Open the change set) — built 2026-10-30 (`JourneyBar`, `AiTaskJourneyBar`, the
`journey` route parameter); the proposal page not yet looked at in a browser. Also open: the wide
price file's load, the update and additions files under AP6r, and the release's docs.

#### AP6a record (2026-10-29)

**Delivered 2026-10-29** after the user approved the plan, the mock-up and J50.1–J50.11. After the
user's first try on their own workbook ("everything looks off": junk records from note rows, a report
hundreds of lines long), the user approved a revision on the same day (mock-up boards 5–7, J50.12–16,
"its good"). Backend and frontend were built by Sonnet agents from briefs and reviewed by the lead.

- **Removal first:** the naming helper (`inference/assistant.py`, its option, read fields, texts and
  tests, J48.2/6/7). A call recorded for `modelNames` stays readable: Settings › AI answered 500 on the
  user's instance because of it. Fixed, with J48.1 *a call made for a feature since removed stays
  readable*.
- **Engine** `engine/tasks/`:
  - `store`, `reading`, `matching`, `turns`, `plan`, `job` (the phases read, plan and fix, one job each,
    no transaction held during a provider call), `changes`;
  - added by the revision: `catalog`, `sql`, `translations`, `placement`, `profile_reading` (a stored
    profile that fits the file is followed first), `workbook`.
- **Migrations:**
  - `20261119_01`: `ai_tasks`, a source file's `task_id`, the job kind `aiTask`;
  - `20261119_02`: the inbox notices a task once, when its reading is ready, and on a failure; not on
    every phase.
- **Settings:** `AI_MAX_STEPS`, `AI_TASK_RETENTION_DAYS`.
- **API:** `/ai/tasks` (create, list, read, plan, changes, run, cancel), the codes `AI_TASK_*`, and a
  column's `known`. The OpenAPI lock was re-baselined. J47 narrowing decisions were added for the new
  routes and for AP2's mapping-proposals route.
- **Frontend** `features/ai-tasks/`:
  - the task page with the reading (summary, Needs you, grouped by the model), the check (totals and
    the lists that change something) and the loaded state;
  - `ui/Disclosure`.
- **Import order (asked by the user during the package):** with the assistant offered, Import opens it
  first, and "Import without the assistant…" opens the manual import.

**Decisions within the package:**
- A column the followed profile left out of the file it read before too is no decision now (`known`).
- An updated record is listed under its stored name; a rename shows as a field.
- The evidence sentence is built from the current figures, without zero counts.

**Checks:**
- Last runs: J50, the `tasks` unit tests and the contract test, 110 passed; J48 and J49 passed; AP6a
  components 29 passed; tsc, eslint and the production build clean.
- Runner `ap1-ai` with the AP6a screens (a 33-list workbook): passed.
- Real try (logged in the AI usage log): the user's workbook, read phase in a rolled-back
  transaction. The stored profile was followed: 87 tables on 4 sheets, 0 to decide, and the assistant
  confirmed the reading. $0.056 at API prices, against $0.24 for the same turn before the revision.

**Pre-existing failures, not from AP6a** (both fail at HEAD before AP6a, checked in a worktree):
- the J47 sweep gives a contributor 422 on AP2's mapping-proposals route;
- J38.1 fails on 'Bsrc'.

**Not verified:**
- the plan, check and fix phases with a real provider on the user's workbook (the try covered the
  read phase);
- matching by meaning and fixes with a real provider on a file whose layout the instance does not
  know.

**What the user cannot do yet:**
- extend the model from a workbook, or load a system's codes as mappings (AP6b);
- create new applications or models from a workbook (AP6c);
- talk to the assistant in free text (AP6d).

The assistant reads by the engine's rules and gets narrow turns. It does not yet decide the structure
itself with the engine's operations as tools.

**The user, 2026-10-29: no splits.** The assistant is meant to work as a language model with the
engine's capabilities as its tools. It analyses the workbook, decides a reference data structure that
fits the model, and when none fits, aligns the model. Splitting this into slices that each give the
model a little more room (AP6b–d) is rejected: a slice delivered and left behind is not revisited. So
AP6a is not finished as the feature. It is the base the assistant's loop builds on, and its reading,
check and pages are the loop's first tools. The next plan replaces AP6b–d with that one piece of work.

**Against the user's scenarios (Outcome, word for word):**

| Scenario | AP6a |
| --- | --- |
| Create a model for this and import | No |
| Map it to the current model and import | Only when the model already fits the file; no mappings of other systems' codes |
| Extend the current model | No |
| Change the values of x based on column y | Only as an update by matched keys, not from the instruction |
| Add this translation | Only language columns where the model has one fitting structure; not a translations sheet |
| Add this system variant | No |
| Add a new business | No |
| A relationship between duration and stations, only if driver assigned | No |

The person's words reach the provider only as context: nothing plans from them.

**After the record:**
- the loaded page's "(show)" became a Show/Hide button (`ui/Disclosure`, `link` variant);
- the list count of a check stored before the revision said "87 of 87": it is now worked out from the
  figures.
- **The user's second real file** (a code list and its translations, into an empty workspace) loaded
  nothing in 10 calls ($0.52). Three causes, all fixed (J50.17):
  - no operation existed for "these rows are new records of a type": `readTable` `update` now takes
    the key column and its key when no stored record matches, and the table reads "New records of …";
  - the assistant could repeat a refused operation on every turn: an answer that only repeats one now
    ends the turns;
  - every turn's note was shown, and refusals named `t1` and column letters: now only the last note is
    kept, and refusals name the sheet and the column's header. Prompt `workbook-read/2`.

  The same file afterwards: 2 calls, $0.106; the list is read as 200 new records. It still cannot load.
  Its rows need a codelist and a domain that the workspace does not hold, and the translations sheet
  needs the model's own translation types. That is the assistant deciding the structure: the next plan.

#### Work packages (as first planned 2026-10-27; superseded by the slices above)

| Package | Needs | What changes | Journeys it must pass |
| --- | --- | --- | --- |
| **AP6a** Task, plan and planning core | AP1 | Tables for tasks, messages and plan versions (migration), the `aiTask` job kind, the routes above, the plan schema, the four tools, the revision rule (AP-D26), retention (AP-D24), limits (AP-D25), the fake provider's scripted plans; a plain question answered in the thread from the read tools (AP-D27) | A question is answered and changes nothing; a task is created, planned and revised; a person-owned step survives a revision; nothing runs without `run`; a stale `expectedPlanVersion` is refused; limits and retention |
| **AP6b** Steps into engine operations | AP6a | The workbook flow's steps 3–8 as write tools over the operation catalogue (AP-D27); the translators of the table above: model operations into a draft with origin `assistant`, profile parts into a draft or saved profile, destination into a change set and a saved profile; the origin on change-set entries and into the audit event (the AP1 spike's result) | New model and extend-model journeys; values from a column; translations and variants; the origin is visible on a published record's history |
| **AP6c** The check | AP6b | One normal form for the three checks (draft dry run, import preview, batch preview): counts (change, new, same, refused), refusals by reason with row and column, suggested fixes as steps (the AP5 grouping, folded in), the trial inside the planning loop; AP2's matcher as a capability step writing value-map entries (steps 9, 10, 12) | A refused row is reported with its reason; a suggested fix applies and the counts change; every row is checked (D67) |
| **AP6d** The task page and New from a workbook | AP6a–AP6c | New from a workbook's AI path (the workbook, an optional words field, the assistant's steps as progress, the result in the editor; AP1's rename checkbox removed); the page of the mock-up: attachment, thread, question with candidates, reading and plan with steps expandable and editable, the check, the destination, "Run into change set"; the starting suggestions for a file with no instruction; the home page entry | A data task end to end in the browser; the question changes the plan; a follow-up chip; a phone layout; light and dark; the accessibility and visual gates |
| **AP6e** The editor's side pane | AP6a, AP6b | `ui/SidePane` extracted from SAVED_UI_PATTERNS (frame, fold button, folded strip, resize handle, width and open state remembered); the editor's grid gets a third column (`ModelEditor.tsx` and `model-editor.css`), a tab on a phone; the assistant thread inside it; an assistant step shows in the editor as any step with its mark and "Proposed because" | New model and extend-model journeys in the browser; renaming a Proposed type clears its mark; undo reverses an assistant step; the pane folds and the width is remembered; 390px tabs |
| **AP6f** A relationship that depends on a condition | AP6b, AP6c | The query conditions (one hop, `not`) into a `batchItems` step with the items built in the database; the refusal of a condition the query cannot say (AP-D17); the measurement at 200 and 2,000 records (AP-D18) | The conditional relationship journey with its count; an inexpressible condition is refused with its reason; a measurement report |
| **AP6g** Real-file try and close-out | all | The AP-D22 try on the user's own workbooks; the documentation (PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, OPERATIONS settings `AI_MAX_STEPS`, `AI_TASK_MAX_FILES`, `AI_TASK_RETENTION_DAYS`, API, journeys, CHANGELOG) | The real-file try: five task kinds, each with a real provider, judged by the user |

Order: AP6a, AP6b, AP6c, then AP6d and AP6e (independent of each other), AP6f, AP6g. AP6d is the
first the user can try in the browser; recommended to show it before AP6e is built.

#### Tests

Journey-driven with the fake provider, which returns a scripted plan for a scripted instruction (the
test supplies both): per task kind one journey through the API, from `POST /ai/tasks` to the records
in the change set, asserting the plan's steps, the check's counts and the final records; plus the
journeys named in the table. Component and browser tests follow the user journeys of AP6d and AP6e
(two object types, as the repository rule asks). Test work stays within about a quarter of each
package; groups are those of the execution guide for the changed boundary. No measurement loops: the
200 and 2,000 measurement of AP6f runs once, is reported with its cause and options, and is not
repeated without asking.

#### Composable domains (ADR-032)

Plans use only generic steps, so the example model's translation and system-mapping cases are
configurations of `relatedRecord` and `relation` bindings, as for the import. Provenance (AP-D5) is
additive. Identity, attribute storage, the consumer API `match` declaration and mapping coverage are
not touched.

#### Said plainly: what the user still cannot do after AP6

- Hand a task to a colleague, or run one on a schedule.
- Use a document or an image as data.
- Ask for something the engine has no operation for; the assistant says so.
- Rely on a small local model; AP-D21 hides the page when the provider cannot do tool calls.

## WM1: Change a workspace's model from the workspace

**Added 2026-10-28 at the user's request; not AI, a basic the release needs.** Found on the user's first real
import: to change the model of the workspace they were in, a person had to know to go to Settings › Model, find or
make a draft of the right release, open the editor, then install, then activate in the workspace. Even the user,
who knows the application, could not tell what to do or where.

**Journey:** a person holding Model authoring and Model release in a workspace opens the workspace, chooses
**Edit model**, and lands in the model editor on a draft of exactly that workspace's model. They change it, and
one main action, **Apply to this workspace**, installs the draft as a new release and activates it in that
workspace (migrating it when the change needs it), with the confirmation saying in plain words what changes and
what happens to the records. They return to the workspace with the new model. Without the groups the action is
not shown (hide, never disable).

**Scope.**
- **On the workspace:** an **Edit model** action (the workspace's header or ⋯ menu, also on a phone) that opens the
  editor on that workspace's draft: the draft that already targets the workspace's active release when there is
  one (a person is not handed a second, competing draft), otherwise a new draft of that release, named after the
  workspace. No detour through Settings › Model; Settings › Model stays for whole-instance model work.
- **In the editor, for a draft opened from a workspace:** the main action reads **Apply to this workspace** and runs
  the existing install-and-activate in one confirmed step against that workspace; the confirmation lists the
  model changes, whether records move (a migration) and what a refusal means, in the activation preview's words.
  After success the person is back in the workspace. Opened from Settings › Model, the editor is as today.
- **The draft remembers its workspace** (where it was opened from), so a later visit from the workspace reopens it,
  and the editor's header names the workspace it will apply to.
- **API first:** whatever the UI needs is a route a client can call (for example "the draft of this workspace's
  model, created when there is none"); existing routes are reused where they suffice. Contract and journeys
  updated as for any route.
- **Mock-up with the plan** (the user's rule for UI packages): the workspace action, the editor header naming
  the workspace and the Apply confirmation, shown and approved before the build.

**Out of scope:** reshaping a workspace whose records must move between types, and any AI help (both
[AP12](#ap12-reshaping-and-asking-from-the-workspace)). An assistant's draft is not WM1's: a session installs without
activating, and WM-D2 keeps a task's draft, finished or not, away from Apply.

**Tests:** journeys through the API on two model configurations: a workspace's model edited and applied from
the workspace (new release active there, other workspaces untouched); an existing draft for that release reused,
not duplicated; a change needing a migration applied with its records; a caller without the groups refused
by code and not shown the action. One browser runner: the path by keyboard at 1440px and 390px, with no
error line in the server log and no 5xx.

### WM1 record (delivered 2026-10-31)

**Exercised:** journey tests J36.12 (12 cases on generated A and B, confirmed failing first) and the J08, J36, J37, J40 and
J50 modules, boundaries and the OpenAPI lock; unit tests of `ApplyDialog` and the selector's menu; runner `wm1-edit-model`
(menu, editor, Apply by keyboard at 1440px on two configurations, a migration, the Settings button, 390px, axe on the
dialog, no 4xx/5xx); the changed runners `j1u-export`, `j4-import`, `j6-people-workbook`, `j6a-people-columns`,
`k6-relationship-filters`, `z5-permissions`; lint and the production build. Screenshots of the menu, editor, Apply and the
phone menu inspected.

**Changes from the plan:** Edit model also needs Browse in the workspace, as Apply reads the workspace's model with it;
J36.12's holder has Browse for that. The sweep's rule is tested in the journey, not a unit test.

**`ap1-ai`:** its workbook section still expected the designs from before AP8, which a backend with only `AI_PROVIDER`
cannot reach: the task stops at `read` (`job.py`, unchanged by WM1), so it timed out at "What the assistant understood". The
section now runs AP8's journey with a stand-in session (`helpers/session-stand-in.py`), as J50.30 does: 105 checks passed.
The stand-in proves the engine and the pages, not the assistant's judgement (AP13).

**The guide's other runners for the changed files** also passed: `w4`, `authoring-n1`, `k1`, `wp9-navigation`, `wp11`, `wp12`,
`wp13c`, `authoring-a4a`, `authoring-a4b`, `authoring-a4c`, `authoring-a5`, `authoring-a6`, `authoring-a7`, `authoring-t1`.

**Not run:** the visual baselines and the accessibility gate, at R, where the collection header's baselines change.

**Fixed with it, on the assistant's pages:** the correction box no longer takes the JSON field's 440px height. The loaded page
says each change notes the assistant only where that is true: a session's changes do not yet (AP9). `GET /system`'s `ai` gains
`assistant` (`AI_AGENT_COMMAND` set): only then does Import offer Load a workbook, whose sentence now says what the session is
given. A provider without a session gets the ordinary Import. `POST /ai/tasks` still reads by the rules there, and a session
still needs `AI_PROVIDER` too: the rest of AP10's one switch.

### WM1 in detail (planned 2026-10-31; approved by the user 2026-10-31 with the mock-up)

Mock-up: [WM1 Edit model](https://claude.ai/artifact/Kzt6bM9BS8jxvh6K8ast3y) (a Design canvas, not kept in the
repository). Reference patterns: the activation dialog (`ActivateDialog`) for the confirmation and the migration
page for records that must move.

**What already works and stays:** the draft operations and editor, `compile` (its `compatibility.workspaces` gives
each workspace's check before anything is installed), `installation`, `activation`, the migration preview and
confirmation, and `Install and activate…`, which moves into ⋯ on a draft opened from a workspace.

#### Decisions (recommended, approved with this plan)

| # | Decision | Why and what it costs |
| --- | --- | --- |
| WM-D1 | **A draft remembers one workspace** in `model_drafts.workspace_key` (foreign key, `ON DELETE SET NULL`), with a partial unique index: a workspace has at most one remembered draft. | The rule "no second, competing draft" is held by the database. One column, one index, one migration. |
| WM-D2 | **Which draft opens.** (1) The remembered draft while it is current: its base is the release the workspace runs, or a release installed after the workspace's model last changed (an Apply stopped at the migration preview). (2) Otherwise the newest draft of the running release that remembers no workspace and that no assistant task names (`ai_tasks.draft_id`), whatever the task's state; it now remembers this workspace. (3) Otherwise a new draft of the running release, named "The model of ‹workspace›". A remembered draft that is no longer current, because the workspace's model was changed elsewhere, gives up the link and stays in Settings › Model. | Without (1)'s second half, leaving a migration preview would orphan the person's work. Without the last sentence, an old draft could silently undo someone else's activation. A finished task's draft is left out too: after an accepted load and its activation its base is the running release, so it would match, and the task's sweep deletes it with the task (`tasks/store.py`, `expire`), taking the person's edits. The sweep in turn keeps a draft that remembers a workspace, as a session may reach one (the new route is in its OpenAPI; sessions reused another task's draft, AP10). |
| WM-D3 | **The install is allowed by Model release in the draft's workspace.** `POST /model-drafts/{id}/installation` checks `model.install` at the draft's remembered workspace; a draft remembering none is checked at the instance, as today. | The check today reads instance grants only (`management/access.py`, `permissions.allows`), so a person holding Model release in one workspace is refused with 403 at Apply, against the journey. Model release is already a workspace-scoped group whose description includes installing; a release does nothing until it is activated. Model authoring stays instance-wide, so "in a workspace" means Model authoring at the instance and Model release there. |
| WM-D4 | **The API adds one route and one field.** `POST /api/v1/workspaces/{key}/model/draft` (action `model.author`; 200 with the draft found, 201 with a new one; `404 WORKSPACE_NOT_FOUND`, `409 WORKSPACE_RETIRED`). `workspaceKey` joins the draft and its outline. Apply stays the existing `installation`, then `activation` or `migrations`. | A client takes the same steps as the UI, with no combined route, like the load (D81). A concurrent first open waits on the workspace's row and gets the same draft. |
| WM-D5 | **A ⋯ menu on the Workspace label's line**, at its right end, holds **Import…**, **Export…** and **Edit model**; Import and Export leave the collection page's header, which keeps its Add. The menu is `ui/ActionMenu` in `WorkspaceSelector`, the one component behind the rail on desktop and the band's workspace choice on a phone, with one workspace too. Each item follows its existing rule: Import where the data shown can be written and the person holds Bulk and import; Export where jobs run; Edit model with Model authoring and Model release in that workspace, not for a retired one. With no item the menu is not shown. Export keeps what the collection page shows (type, filters, search, parent, columns), which the page hands to the shell; on any other page it opens on the application's types. Manage workspaces stays where it is. | The user, 2026-10-31: these are not frequent actions and the page must not overwhelm. Cost: moving Import and Export changes existing tests and browser runners that press them, and PL6 (0.17), which reworks these two dialogs, starts from the menu. **Edit model is also a button on the workspace's existing page in Settings › Workspaces, in 0.16 (the user, 2026-10-31)**, beside Rename, under the same rule, opening the same route. PL3's new overview page (0.17) reuses it. |
| WM-D6 | **The workspace mode is in the URL**: `/settings/model/drafts/{id}/editor?workspace={key}`, and the same parameter on the migration page. Without it the editor is as today, including for a draft that remembers a workspace. | Survives a reload and a shared link, and keeps "Opened from Settings › Model, the editor is as today". The journey parameter is not reused: it drives the journey bar. |

#### The Apply dialog

A new `ApplyDialog` on the existing pieces; the parts it shares with `InstallDialog` and `ActivateDialog`
(`summarizeChanges`, `ConsumerContracts`, `useReleaseIdentity`, the left-behind list and the migration reasons) are
extracted once, not copied. It reads `compile` and shows, in order: what changes in the model; what happens to the
records; change sets left behind; the workspaces not changed; the release identity folded under "Becomes release
‹name› ‹version›".

| State | The main action | After it |
| --- | --- | --- |
| Records fit | **Apply to ‹workspace›**: install, activate | Back in the workspace, with one sentence saying it now runs the release |
| Records must move | **Preview what happens to the records…**: install, start the migration | The migration page; on done, back in the workspace. Leaving changes nothing there and the draft reopens |
| Records must move, migrations not available here | None; says that this deployment does not run migrations | Cancel |
| A consumer API needs a higher contract version | None until raised, with the Raise step in the dialog, as today | The state above it |
| Draft invalid | None; the Issues list has each reason | Cancel |
| Nothing to apply | None; "Nothing to apply yet: this draft matches what ‹workspace› runs" | Close |
| Installed, then activation refused | **Try again**; says the workspace did not change | The draft's base has moved, so the install finds the same release and only activation repeats |

#### Tests (cases for approval)

Journey tests in `tests/journeys/`, new variants of J36, each on two model configurations:

1. **Apply to one workspace.** Given two workspaces on one release, when the first's draft is opened, a field added,
   it is installed and activated there, then the first runs the new release with the field, the second is unchanged,
   and opening again answers 200 with the same draft.
2. **An existing draft is reused.** Given a draft of the running release remembering no workspace and one of another
   release, when the draft is opened, then the first is answered, now naming the workspace, and no draft is created. Given instead only the draft of a task that ended, a new draft answers 201.
3. **The model changed elsewhere.** Given a remembered draft, when another release is activated in the workspace and
   the draft is opened, then a new draft of that release answers 201, and the old one still exists, naming no workspace.
4. **Records move.** Given records of a type the draft removes, when it is installed, then activation answers
   `MODEL_MIGRATION_REQUIRED`; opening before the migration confirms answers the same draft; after the confirmation
   the workspace runs the release with its records converted.
5. **Who may.** No Model authoring: `FORBIDDEN` on the route. Model authoring and Model release in workspace A: installs
   A's draft; `FORBIDDEN` on B's draft and on a draft remembering none. A retired workspace: `WORKSPACE_RETIRED`.

Unit tests: `ApplyDialog` for each state above, the ⋯ menu's items and the Settings button shown and hidden, Export keeping the collection's context, the route's `workspace` parameter. A new
browser runner on two configurations: ⋯ menu → editor → Apply → back, and the migration path, by keyboard at 1440px and
390px, axe on the dialog, no 5xx and no server error line; its screenshots inspected against the reference patterns.

#### Delivery

- **Backend:** the migration, written in one go; `engine/model/drafts.py` (the choice in WM-D2); the sweep's condition in `engine/tasks/store.py`, with a unit test; the route and `draftResponse`
  field; the workspace-aware check in `management/access.py`; the journey tests, confirmed failing first.
- **Frontend:** the ⋯ menu with Import and Export moved into it, the Edit model button in `WorkspaceAdmin`, `ApplyDialog`, the route parameter, the editor's crumb, header and main action (desktop and
  phone menu), the migration page's way back, a workspace's model reloaded after Apply.
- **Documents:** `API.md`, `API_JOURNEYS.md`, `USER_JOURNEYS.md` (J36), `CURRENT_FUNCTIONALITY.md`, `PRODUCT.md`, `CHANGELOG.md`.
- **Door check (ADR-032):** no door is affected; the package touches none of identity, attribute storage, audit and
  history, bulk APIs, `match` or mapping coverage.

**What a person still cannot do after WM1:** move records between types in one reshaping (AP12),
or ask the assistant to change the model from here (AP12). Edit model starts from the workspace ⋯ menu on any of its pages and from the
button on the workspace's page in Settings › Workspaces. PL3 (0.17) builds a new overview page, which reuses the same action.

## Track A: agent access

## AG1: The server and its authority

**Journeys:** an operator enables MCP and creates an agent client; the client connects and lists only
the tools its grants allow; with MCP disabled the endpoint does not exist; revoking the client stops
it on the next call.

**Scope.** `management/routers/mcp.py` (the Streamable HTTP endpoint on the MCP Python SDK, pinned in
pyproject's ranges with `pip check`), the `agent` audience in `engine/identity/tokens.py`, the `Agent`
predefined role and its action group in the catalogue, the audit `channel` column, `GET /system`
reporting `mcp: {enabled}`, Settings › Agent access (clients, last use, counts, how to connect
including the URL and the sign-in), `MCP_ENABLED`, `MCP_RATE_PER_MINUTE` in OPERATIONS.md.

### AG1 in detail (planned 2026-10-31, approved by the user the same day with the mock-up)

Mock-up: [AG1 Agent access](https://claude.ai/artifact/TqCG2VCdQV1Cti6Y6cgnCo) (a Design canvas, not kept in the
repository). Reference patterns: the AI page (`AiPage`) for a setting read from the environment, the Clients page for
a client's detail, secret and access, which are reused and not copied.

**Checked against the code and the MCP specification of 2025-11-25.** Four things in the scope above do not hold as written:

- **"The existing OAuth flow" cannot sign in an assistant.** `check_request` and `/oauth/token` accept only
  `client_id=browser` and the configured redirect addresses, and the refresh token goes in a cookie. The specification
  also requires protected resource metadata (RFC 9728), which the engine does not have. AG-D2's person sign-in needs AG-D12.
- **An `agent` token would read as `management`:** `_audience()` in `authentication.py` turns every value but
  `consumer` into `management`. It must name each audience.
- **A session is not tied to an audience:** `/oauth/token` issues whichever `scope` is asked for on a refresh, so a
  refresh token held by an assistant could obtain a management token (AG-D12).
- **The current MCP SDK breaks the test harness:** `mcp` 2.x requires `httpx2`, which Starlette's test client then
  prefers. AP1 found this break with the Anthropic SDK (AG-D11).

| # | Decision | Why |
| --- | --- | --- |
| AG-D11 | **`mcp>=1.30,<2`.** A dry run against the shared environment adds `mcp`, `httpx-sse` and `sse-starlette` and moves nothing. 1.30 speaks protocol 2025-11-25. Stateless, JSON answers, a session manager per application started in `lifespan`, `Origin` and `Host` checked from `PUBLIC_URL`. | 2.x would change the test client for everyone using the environment. Stateless needs no affinity between processes. Moving to 2.x waits until the harness moves to `httpx2`. |
| AG-D12 | **An assistant is a registered application, and a person signs in for it.** New: `/.well-known/oauth-protected-resource` and its `/mcp` form, the 401's `resource_metadata`, `POST /oauth/register` (RFC 7591), the table `agent_applications`, and `user_sessions.agent_application_id`. A public client with PKCE; `resource` must be this instance's `/mcp` when sent. Open registration (`MCP_OPEN_REGISTRATION`, default on) accepts loopback addresses and HTTPS hosts in `MCP_REDIRECT_HOSTS` (default none); anything else is registered by an administrator. Unused registrations are removed after 30 days. Client ID Metadata Documents are not built. **A session is bound:** one started for an application issues only `agent`, with its refresh token in the answer's body and rotated by the existing `sessions.renew`; a browser session never issues `agent`. | Registration is what Claude Code uses by default; a metadata document makes the engine fetch addresses an unknown caller names, a request-forgery risk and outbound traffic a closed deployment may not have. The session rows give sign-in rules, ending a session and "revoked on the next call" with no new mechanism. |
| AG-D13 | **The sign-in page is the consent.** When an application sent the person, the page says who asks (its own claimed name), where it returns (the host, which the specification requires shown), what it can and cannot do, and the buttons read "… and allow". Password, passkey, provider and second factor run unchanged. | Every sign-in route ends in `issue_code`; one banner in `check_request`'s page needs no extra state or step. An open registration can claim any name, so the page says the name is claimed. |
| AG-D14 | **`oauth_clients.kind`: `api` (existing) or `agent`.** An agent client gets only `scope=agent`, an API client never does. The AP8 session's client stays `api`. | An agent principal can then never hold a token that reaches an approve route (AG-D5), enforced at issue and not by each route. |
| AG-D15 | **The `agent` role holds `browse` and `change-sets`; the same set is the ceiling** for every `agent` token, applied to the permissions read after the cache. A person needs no new grant: their own roles cut down to the ceiling. A client needs a grant as usual. `publish` and `approve` are not in it; consumer API grants pass unchanged. | AG-D3 as code, one definition. `change-sets` carries no capability until AG3 adds tools, and only the tools are reachable on this audience. |
| AG-D16 | **Revises AG-D6. Each call is a row in a new `agent_calls` table, not an audit event:** who, application, tool, argument names (never values), outcome, duration, request ID; removed after `MCP_CALLS_DAYS` (90). **The audit `channel` column moves to AG3**, its first writer. | Today reads write no audit entry, and rows per read in `audit_events` would be permanent and sit in the trail that holds changes. `ai_calls` is the precedent; so is AP1 moving `origin` to its first writer, because nothing could write or test it earlier. |
| AG-D17 | **The rate limit is a count over `agent_calls` in the last minute,** per principal, on tool calls: `MCP_RATE_PER_MINUTE` (120), a tool error with the seconds to wait. | One statement, right across processes, no new store. |
| AG-D18 | **Two tools prove the registry:** `describe_access` (always: who I am, my ceiling, my workspaces) and `list_workspaces` (needs Browse somewhere, paged, the service function of `GET /workspaces`). A tool declares the group it needs; one the principal lacks is not listed and is refused if called. | The journey "lists only the tools its grants allow" cannot run with no tools. AG2 adds to the same registry. |

**Scope.**

- **Engine:** `engine/agent_access/` (settings, applications and registration, the call log, the limit, the ceiling, the
  tool registry); `tokens.py` and `_audience()`; `/oauth/token`, `check_request` and `issue_code` for applications; the
  `agent` scope offered only while MCP is on.
- **Endpoint:** `management/routers/mcp.py` mounted only with `MCP_ENABLED`. The token is checked by `authenticate` on
  every request, so revoking applies on the next call. `/mcp` joins the proxy paths in `frontend/nginx/snippets/locations.inc.template`
  and `frontend/vite.config.ts`.
- **API:** `GET /agent-access` (status and totals), `GET /agent-access/calls`, `GET` and `POST /agent-access/applications`,
  `POST …/applications/{id}/block` and `/restore`; `kind` on `POST` and `GET /clients`; `application` on `GET /me/sessions`;
  `mcp: {enabled}` on `GET /system`. Action `agent-access.read` and the writes under Security administration.
- **Migration, one file:** `agent_applications`, `agent_calls`, `oauth_clients.kind`,
  `user_sessions.agent_application_id`, the `agent` role row.
- **Frontend:** Settings › Security › Agent access as in the mock-up. An agent client opens the existing client page, and
  New agent client reuses the existing dialog with its one-time secret. The person's sessions list names the assistant.
- **Documents:** API.md, OPERATIONS.md (settings, and the prompt-injection stance of AG-D8), ARCHITECTURE.md, USER_JOURNEYS
  J51, API_JOURNEYS, CURRENT_FUNCTIONALITY, PRODUCT, UI_ACCEPTANCE, EXECUTION_GUIDE, CHANGELOG.

**Out of scope:** reading data and the model (AG2), writing and `channel` (AG3), Client ID Metadata Documents, a stdio bridge.

**Tests, J51, through the endpoint with the SDK's client on two model configurations:**

1. **Off:** `/mcp`, the resource metadata and `/oauth/register` answer 404, and `scope=agent` is refused.
2. **A client:** made as `agent`, granted, connects and lists its tools; without Browse, `list_workspaces` is neither
   listed nor callable. Deactivated, it is refused on the next call.
3. **Audiences, in every direction:** an `agent` token is refused by `/api/v1` and the consumer API; management and
   consumer tokens are refused by `/mcp`; an agent client asking for `management` and an API client asking for `agent` are refused.
4. **A person through an assistant:** a 401 leads to metadata, registration, sign-in with PKCE, a tool call and a rotated
   refresh. The same refresh token asking for `management` is refused, and a browser session asking for `agent` is refused.
   Ending the session, or blocking the application, stops it on the next call.
5. **The ceiling:** a person holding Approve and Publish keeps neither on this audience (`describe_access`).
6. **Registration:** an outside HTTP or unlisted HTTPS address is refused; with open registration off, only a registered
   application signs in.
7. **Limit and log:** the call past the limit is refused with its wait; a row names the argument, not its value.

One browser runner: the page at 1440px and 390px, by keyboard, with the sign-in banner.

**The real try:** one sign-in with Claude Code through the dev server, since the SDK's client cannot prove a real client's
discovery. It needs `MCP_ENABLED=true` in `.dev/settings.env` and the user's restart, and the user's own password in the
browser. The bounded R try stays as AG-D10 says.

**Working beside other sessions:** install the packages first, as the dev server imports what `main.py` names on save. The
migration's `down_revision` and `HEAD` in `test_startup.py` are taken from the head at the moment of writing, the file
written in one go (WM1 also adds a migration). The OpenAPI lock is re-baselined last and diffed for AG1's additions only. J51 is
checked for being free before use. Commits hold AG1's hunks only.

**Door check (ADR-032):** identity gains a client kind and an application on a session, additive; audit and history are untouched
in AG1. No door closes.

**What the user cannot do after AG1:** ask an assistant about data or the model (AG2), or have it prepare a change (AG3). An
assistant connects, signs in and sees where it may work, nothing more.

### AG1 record (2026-10-31)

**Delivered as planned**, with the build's tests below; the one real sign-in is the user's step and has not happened yet. Frontend built by a Sonnet agent from a brief.

**Where it differs from the plan:**

- `GET /agent-access/clients` was added: the page's call counts per client need it.
- The five `MCP_*` settings sit in the `ai` settings group, beside the rest of this release's settings.
- AG-D11's `Host` check is left out: only `Origin` is checked. A proxy's forwarded host differs by deployment, and a bearer token carries no ambient authority.
- Registrations use the `client` security events (`application-registered`, `-blocked`, `-restored`), so the audit index's aggregate list stays as it is.
- `/mcp` loads the SDK on every start, flag or not: the boundary test refuses a deferred import in `app.main`.

**Checks:** J51: 16 passed (two configurations). J39, J40, J41 with J51: 168 passed; an earlier run of the same set had one J51 failure under parallel load (`test_an_assistant_never_holds_approve_or_publish`, generated-b), whose log was not kept; it passed alone three times and in the rerun, cause not established. `contract` and `startup`: 284 passed, 4 failed, all from WM1's uncommitted migration `20261120_02` (the `HEAD` pin and the `model_drafts` rule). OpenAPI lock re-baselined, additive, diffed against HEAD. Frontend: `tsc -b`, `npm run build`, focused Vitest, `test:browser:agent-access` (18 checks, axe 0 violations).

**The real try (the user, 2026-10-31):** Claude Code through the dev server at `PUBLIC_URL`: discovery, self-registration, sign-in and both tools worked. The person's Data owner role showed only Browse and Work in change sets. On a development certificate Claude Code needs `NODE_EXTRA_CA_CERTS` with mkcert's root.

**Not verified:** Claude Desktop's and claude.ai's return addresses.

**What the user cannot do yet:** ask an assistant about data or the model (AG2), or have it prepare a change (AG3).

## AG2: Read tools and resources

**Journeys:** "what is the code of this value in the webshop system?" is answered from a consumer
definition; "which values of this list have no mapping to the webshop?" is answered from mapping
coverage; the model description is readable as a resource.

**Scope.** The generator from consumer definitions (one tool per definition, schema from its fields,
authorization from its grant), the curated tools (AG-D4), the model, applications, object types and
views as MCP resources, structured results with IDs, cursor paging. Proven on two definitions whose
types differ (the generic-capability rule), not on the example model's keys.

## AG3: Changes prepared and submitted for approval

**Journey:** an agent asked to add five missing values creates a change set, adds the five, reads the
validation and submits it; a steward is notified in the inbox, opens it, edits one value and approves;
live data changes only at that approval.

**Scope.** Tools: create/select change set, add or change an object, set a field, add a relation, read
the change set's validation. Optimistic concurrency applies (versions are inputs); conflicts return the
engine's own error code and message. No approve, publish, delete, model or security tool exists, and the agent principal cannot approve through any route (AG-D5).

## AG4: Natural-language search

**Journey:** a steward types "values changed last month without a webshop mapping" in the search box
and sees the filters it became, editable, and the results.

**Scope.** The `queryTranslation` purpose of the AP1 provider (`structure` send level: the question
and the list's filterable fields, no record values); the answer is the existing filter parameters,
validated like a hand-typed filter, shown as chips the person edits. The engine answers; the model
only builds the query. A question it cannot express is said so, not approximated.

## Track O: operations

## AO1: Model change impact summary

**Journey:** a model administrator opens a release's activation preview for a workspace; beside the
counts and the list of operations, a short account says: "Two attributes are added to Delivery method
(optional, no data change); the mapping to the webshop gains one relation; 3 consumer definitions
change shape, one of them removing a field" with each statement linking to the operation or
definition. It never says a change is safe; it says what the facts are.

**Scope.** The fact set from the existing diff and preview (operations, affected counts, consumer
definition changes, mapping changes, blocked items), the `impactSummary` purpose, `POST …/releases/{id}
/impact-summary`. Send level `structure`. Also available on a model draft's validation result.

## AO2: What changed, an account of history

**Journey:** a data owner picks "last week" on a workspace; the account says "Translations: 200
labels changed by 3 people, 190 of them in one bulk import on Tuesday; Master: 4 values retired; one
change set (CS-18) was sent back", each statement linking to the records and the change set.

**Scope.** Fact aggregates from history and the change feed, grouped in PostgreSQL by type, kind,
actor and source (job, change set, direct), restricted to what the requester may read; the
`historyAccount` purpose; the panel and the route (AO-D7). Send level `structure` for counts and
groups, `values` to name records.

## AO3: Notification digests

**Journey:** a steward sets daily digests; the next morning one mail says "3 change sets wait for
your approval, 1 job failed (import of the operators file, 14 rows rejected)", then lists the notices
as today with their links.

**Scope.** The `digest` setting per person, the scheduled job (an existing worker with the lease
rules: one digest per person per period, no duplicates across nodes), the `digest` purpose (kinds,
counts, titles; send level `structure`), the mail template, the outbox. With the provider off, the
digest is the plain list with counts, which is already an improvement over many mails; AI only writes
the opening sentence. (This makes AO3 useful without a provider: recommended to build it so.)

## Door check (ADR-032)

Provenance (`origin`, AP-D5) is the first use of the value-provenance door and is additive, kept
outside a record's own values. Audit gains a `channel`, additive. Identity, attribute storage, bulk
APIs, the consumer API `match` declaration and mapping coverage states are read or reused, not
changed. Summaries (Track O) are derived and stay outside history, the model and the records. No door
closes.

## Tests

Journey-driven through the API, at most about a quarter of a package. Track P and O use a deterministic
fake provider (AP-D11, AO-D9): per package the happy journey, the provider-failure journey, the
permission-hidden journey, and where data is read a send-level journey; Track O adds the
uncited-statement, the visibility and the fact-completeness tests. Track A uses a test MCP client
(AG-D10). The context builder's level tests are unit tests. Execution-guide groups for the changed
boundary only; the OpenAPI lock re-baselined per package and marked additive.

## AP8: The assistant is a Claude Code session (decided 2026-10-31)

Supersedes the turn format of AP6r and the engine-first calls of AP7. The working setup was the user's own: a few words, the workbook, the model and the OpenAPI document, and a model free to explore. Each limit added around it was the limit that failed. Journey J50.30. Open: a client that cannot publish (the session runs with the rights of who asked), isolation on a shared server, speed against the time limits, and the old J50 cases removed with the loop, to be replaced as journeys demand.

### AP8 record: model shape and speed (2026-10-31)

- **Model shape. Built 2026-10-31, the user's decisions.** The same words gave five types on one run and one type of 87
  attributes on another, and both pass the dry run. **Separated by default:** one generic sentence in the prompt makes what
  a file repeats into types of their own, and a session keeping a repetition flat raises it as a question. **What the
  workspace holds decides the start:** with records the session adds to the model; with none, words asking for a model may
  get a new one. The proposal shows the shape from the engine's figures (attributes and records per type, relationships
  apart from records), and warns when a model leaves out types the workspace holds records of; Accept stays available.
  **Tried on real files, three runs each, from the same words:** all six separated and loaded with 0 rejected. Price
  Catalogue: the same 9,746 records each time; run 1's prices, VAT, enabled flags and ledgers match task 56's flat load
  value for value. Timetables: 1,964, 1,966 and 400 records; the third keeps its 1,500 translations on relationships
  rather than as records, and every workbook value is found in all three. **Still varies, by design:** names and details
  of the structure (Station or Operator; translations as records or on relationships). A run may start from the workspace's
  model and still replace it, which labels same-keyed types "Changed".
- **Speed.** Open: the separated runs took 200 to 348 s on Timetables and 497 to 633 s on Tariff File, proposal and load, without a person's wait. Tariff File's atomic import is refused at the 10,000-item limit, so the session falls back to row-by-row success, and pays for the failed try.

## AI usage log (for hosting cost planning)

**Why (the user, 2026-10-29):** refiroo may be hosted on a subscription that includes the AI provider,
so what a real task costs is planning data. Every real-provider try in a package or in R adds one row
here. A row is reported to the user with the try.

**How it is measured.** The call records (`ai_calls`, Settings › AI) give each call's purpose, duration
and tokens in and out; the tokens in are the sum of plain input, cache writes and cache reads. Through
the Claude Code provider, each call also logs those three kinds apart and `total_cost_usd`: Claude
Code's price of the same call at API rates, whatever the sign-in. So that figure is the API cost, and on
a subscription it is not money spent. For another provider the API cost is worked out from its
published prices, and the date of those prices is given.

| Date | Package, what was tried | Provider, model | Calls | Tokens in (plain / cache write / cache read) | Tokens out | Time | Cost at API prices | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

**What a hosting estimate needs from these rows:** the cost per task kind (e.g. loading one workbook of
N rows and M sheets), how it grows with the file (the reading is sent as column profiles, so it grows
with columns and distinct values, not with rows), and how much prompt caching saves on repeated turns.

## R: Build acceptance and release

Full review of every change since 0.15 (it is one review for three tracks, the main saving of merging);
the contract lock marked additive (the `agent` audience, `/mcp` and the new routes); documentation
(PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, OPERATIONS for the AI and MCP settings and connecting an
assistant, API, journeys, CHANGELOG); **one** bounded real-provider try and **one** real-assistant try,
each only on the user's go-ahead with its cost stated first (AP-D11, AG-D10); the release.

## Exit gate

- A few words and a workbook give the model and the import, with as many applications, types and
  relations (across applications too) as the workbook needs; tried on the user's own workbooks (AP-D22).
- With no provider and MCP off, no screen shows an AI action, no request leaves the instance, `/mcp`
  does not exist, the existing inference behaves as before, and digests are the plain list.
- No value above the configured send level reaches a provider (the context builder's tests).
- Every proposal refers to an existing record or valid step and passes the validation of a hand edit;
  it can be edited, kept or removed with existing tools; every accepted one is recorded as
  machine-proposed with its approver.
- An agent token works on `/mcp` only; no tool approves, publishes, withdraws, administers the model or security,
  or deletes; an agent's change set leaves live data unchanged until a person approves it; every call
  is in the audit trail with its channel.
- Every summary statement cites a fact that exists; the facts equal the database for the period; a
  summary never contains what its requester may not read and changes nothing.
- A failing provider never fails a deterministic result.
- An instruction becomes only steps of the AP-D12 kinds; nothing runs before the person confirms a dry
  run of every row; the result lands in a change set by default; the saved profile repeats the load.
- The real-file try (AP-D22) on the user's own workbooks has been run and judged by the user.
- **The acceptance workbook** (the user, 2026-10-28): `Lines & Routes v2.0.xlsx`, a data dictionary laid
  out for reading (lists side by side, group headings above list headings, English and Spanish column pairs, `Y`
  flags, notes). The rules alone made one application of 101 types and 31 relation types of it. Through AP6 it gives
  a model a person reads as the business does, about four applications and a dozen types with group hierarchies,
  translations and relations, and its import, judged by the user.
- **Reshaping a workspace's model is an instruction too:** from the workspace, "reorganise this model" (or a
  narrower change) becomes the same kind of plan as a new workbook, so a person never needs the model editor's
  draft, install and activate path to fix a model; where the change needs the 1.0 merge of types holding data, the
  plan says so and offers a new workspace loaded from the same file. *(Corrected 2026-10-28: merging types that
  hold data does not wait for 1.0. The 0.8 restructuring (`changeType`, `changeTypeUnder`, `move`, `insertLevel`,
  `removeLevel` in a change set, records keeping their IDs, previewed first) does it today, so a reshaping plan is
  three phases: a model version with the target types beside the old, a change set restructuring every record into
  them, a version without the emptied types. Restructuring joins AP-D12's step kinds, an existing engine
  capability like the other five.)*
