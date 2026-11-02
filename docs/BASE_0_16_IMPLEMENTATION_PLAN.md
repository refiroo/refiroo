# Base 0.16 implementation plan

**Status:** Drafted 2026-10-27 at the user's request, for revision. AP-D3, AP-D12–AP-D26, AG-D5 and AG-D9
are decided by the user and marked so; every other AP-D, AG-D and AO-D below is a recommendation. Planned before 1.0 for now, like 0.14 and 0.15. Idea source:
the AI integration discussion of 2026-10-27. First drafted as three releases (0.16–0.18); merged into
one on the user's suggestion the same day because the three share one foundation, one permission and
one acceptance step, and together are about the size of 0.15.

**Reconciled 2026-10-31 at the user's request:** the assistant's design moved faster than this plan, so [Packages](#packages), [Where each decision stands](#where-each-decision-stands) and the [Exit gate](#exit-gate) now describe what exists and what is open. Earlier designs are at the end, under [History](#history-of-the-assistant).

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
  likely target for each unmapped value. *(Value drafts and the grouped explanation of a failed dry run, AP4 and AP5,
  were removed 2026-10-31; names and relations for a workbook come from the assistant, AP8.)* Each carries a
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
  don't build limitations." They get a proposal they can read and shape, every row checked, and one step to load it into a change set (AP8).

  **Status 2026-10-31:** see [where the cases stand](#ap8-the-assistant-is-a-claude-code-session).
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
| AP3, AP4, AP5, AP6, AP7 | — | **Superseded by AP8.** See [History](#history-of-the-assistant). AP4 and AP5 are removed from 0.16 (the user, 2026-10-31) |
| [AP8](#ap8-the-assistant-is-a-claude-code-session) | AP1 | **Built.** A few words and a workbook go to a Claude Code session; proposal, the person's words, then install and load into a change set |
| [AP9](#ap9-who-did-it) | AP8 | **Built.** Provenance on a session's changes, one client per session, the call record, retention |
| [AP10](#ap10-one-path) | AP8 | **Delivered 2026-10-31.** One switch, the old design removed, a saved profile from a load, updating from a file, the session's leftovers, the proposal page, the documents |
| [AP11](#ap11-good-models-in-time) | AP8 | Model shape from the same words, and the time limits. **Closed 2026-11-01, accepted by the user with the time limits not met** |
| [AP12](#ap12-reshaping-and-asking-from-the-workspace) | AP8, WM1 | Moving records between types through a session, and "Change this model…" from the workspace |
| [AP13](#ap13-acceptance-on-real-files-ap-d22) | AP9–AP12 | The remaining real-file tries, judged by the user |
| [AG1](#ag1-the-server-and-its-authority) | 0.12 | The MCP endpoint, its setting, sign-in with the existing OAuth, audit channel, the agent role, Settings › Agent access |
| [AG2](#ag2-read-tools-and-resources) | AG1 | Read tools generated from the consumer API definitions plus a curated set; the model as resources |
| [AG3](#ag3-changes-prepared-and-submitted-for-approval) | AG1, AG2 | Write tools that create a change set, add validated changes and submit it for approval; no approve or publish tool |
| [AG4](#ag4-natural-language-search) | AG2, AP1 | A question turned into the existing search and filter parameters, explained back. **Closed 2026-11-01, accepted by the user** |
| [AO1](#ao1-model-change-impact-summary) | AP1 | **Delivered 2026-11-01.** A plain-language impact summary of a release diff or activation preview, with its facts |
| [AO2](#ao2-what-changed-an-account-of-history) | AP1 | An account of a workspace's history over a period, with citations |
| [AO3](#ao3-notification-digests) | AP1 (the AI sentence only) | A daily or weekly digest of a person's inbox notices by mail, opt-in; useful without a provider |
| [WM1](#wm1-change-a-workspaces-model-from-the-workspace) | 0.12 | **Not AI.** Edit a workspace's model from the workspace: a draft made for it, one "Apply to this workspace" |
| [R](#r-build-acceptance-and-release) | all | Full review of every change since 0.15, the gates, one bounded real-provider try and one real-assistant try, the release |

**Order (revised 2026-10-31).** Delivered: AP1, AP2, AO1. Built: AP8. Next: WM1, then AP9 to AP13 with the tries already running, and Tracks A and O beside them, as they touch little of the same code; then R. Track A is an additional route for organisations that bring their own assistant, never a precondition of the built-in one.

**Tracks A and O stay in 0.16 (decided by the user 2026-10-31).**

## Decisions

### Where each decision stands

Checked against the code 2026-10-31. Where this differs from a decision's own text below, this table is current; the text
keeps the reasoning.

| Decision | Stands? | Now |
| --- | --- | --- |
| AP-D1 One interface | Changed | Holds for AP2, AG4 and Track O. A session is not a provider call; `AI_PROVIDER` serves those only (AP10, AP-D38) |
| AP-D2 Providers | Kept | Plus `AI_AGENT_COMMAND`, which alone turns the assistant on (AP10, AP-D38) |
| AP-D3 Send levels | Changed | A task below `values` is refused, so the level holds. For a session the boundary is the refusal, its grants and the sandbox, not the context builder |
| AP-D4 Call record | Kept | Met for sessions by AP9 |
| AP-D5 Provenance | Kept | Met for AP2, and for sessions by AP9 |
| AP-D6 The editor, not a list | Kept | A session's draft opens in the editor. Confidence and its floor apply to AP2 only |
| AP-D7 The group | Kept | The group is checked. "Made by the person's own request" is met by AP9 |
| AP-D8 Jobs | Changed | A session runs on the assistant worker. A question in words (AG4) is answered directly, not as a job: one short call, no set of rows to batch ([AG-D34](#ag4-in-detail-planned-2026-11-01-approved-by-the-user-the-same-day-with-the-mock-up)) |
| AP-D9, AP-D10, AP-D11 | Kept | J50.30 scripts the session's command, as the fake provider cannot drive it |
| AP-D12 Five step kinds | **Replaced** | By AP-D29 |
| AP-D13 Change set, saved profile | Kept | The change set holds. A load leaves a saved profile that the engine saves, or says why not (AP10, AP-D41). "Live only when the person says so" is not offered to a session |
| AP-D14 What the provider sees | Kept | The session reads what it needs within its folder and the API |
| AP-D15 The loop | **Replaced** | By the session. `AI_MAX_STEPS` does not bound it |
| AP-D16 Questions back | Kept | In the proposal |
| AP-D17, AP-D18 Relations where a condition holds | Changed | The query's limits hold as the API's. `links.py` and the relationship rules are removed (AP10, AP-D40); set work: AP11 |
| AP-D19 One set of tools, two drivers | **Dropped** | The two drivers share the API instead. Track A is unaffected: AG-D4 calls the routes' service functions |
| AP-D20 What the person sees | Changed | A proposal, its check, the questions and the draft in the editor. Not a plan of steps |
| AP-D21 Providers that cannot do this | Changed | What it needs is a session command; without it `POST /ai/tasks` is `409 AI_NOT_CONFIGURED` (AP10, AP-D38) |
| AP-D22 Real-file try | Kept | AP13 |
| AP-D23 Who sees a task | Kept | |
| AP-D24 Retention | Kept | Met by AP9 |
| AP-D25 Files per task | Changed | One file is built; up to three is not. Kept to one unless a real case asks |
| AP-D26 A person's edits | Changed | There are no steps to own. The person's edits are in the draft, and the session reads it again before installing |
| AP-D27 One assistant | Kept | AP2's helper stays until a real case moves it. AP4 and AP5 are removed from 0.16 |
| AP-D28 Draft-only change nothing holds | Kept | |
| AP-D29 How far the session may go | New, approved | Replaces AP-D12 |
| AP-D38 to AP-D45 The one path | Delivered | The command alone switches the assistant on. The rules-only path, `/plan`, `table` on `/changes`, relationship rules and `AI_MAX_STEPS` are removed. The engine saves a profile from a load (`result.profileKey`, or `profileNotSaved` with why). A proposal warns of new records beside held ones. A source key may span several columns. A session is refused a draft another task holds. Unused releases a task installed are retired when it ends. Real tries: open |
| AG-D1 to AG-D10 | Kept | Except as [AG1 in detail](#ag1-in-detail-planned-2026-10-31-approved-by-the-user-the-same-day-with-the-mock-up), [AG2 in detail](#ag2-in-detail-planned-2026-10-31-approved-by-the-user-the-same-day) and [AG3 in detail](#ag3-in-detail-planned-2026-10-31-approved-by-the-user-the-same-day-with-ag-d27-as-written) revise them. AG-D5 and AG-D6 are now met with revisions (AG-D29's origin, AG-D30's `channel`) |
| AG-D33 to AG-D38 | New, approved | [AG4 in detail](#ag4-in-detail-planned-2026-11-01-approved-by-the-user-the-same-day-with-the-mock-up): the list filters the journey needs, a direct answer, the send level and an offer rule of its own, words found in the database, nothing applied when a part fails, pills as the explanation |
| AO-D1 to AO-D9 | Kept | They use the provider, not the session |

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
| AP-D23 | Who sees a task? | **Approved by the user 2026-10-27. Its owner, and a person with the permission to administer the workspace it targets.** A task holds the person's instructions and the assistant's replies, which can name records. Not shared by default; handing a task to a colleague is out of scope for this release. |
| AP-D24 | What is stored, for how long? | **Approved by the user 2026-10-27. The instructions, the assistant's replies, the plan versions and the dry-run summaries, for `AI_TASK_RETENTION_DAYS` (default 90) after the task finishes or is abandoned; never the rows or samples sent to the provider** (AP-D4: content is not kept unless `AI_LOG_CONTENT` is on). The source file follows the existing source-file retention. A saved profile and the change set are ordinary resources and outlive the task. |
| AP-D25 | How many files and how large? | **Approved by the user 2026-10-27. Up to three files per task (`AI_TASK_MAX_FILES`), each within `IMPORT_MAX_BYTES`;** XLSX and CSV only, as source files accept today. A task over a limit is refused when attached, not when it runs. |
| AP-D26 | How does a revision treat the person's edits? | **Approved by the user 2026-10-27. A step the person edited or removed is theirs: a revision never overwrites it.** Each step has an `owner` (`assistant` or `person`); the assistant may propose an alternative for a person-owned step in its reply, as text, never in place. A person-owned step also keeps its mark off. This is the rule that makes the editor feel like an editor and not a regenerate button. |
| AP-D27 | One assistant or a helper per feature? | **Approved by the user 2026-10-28. One assistant, every AI capability a tool of it, offered where its situation occurs.** The AP6 loop is the only AI that plans: it starts from the rules' result, reads through tools (the profile over every row, any sheet by range including skipped ones, distinct values, overlaps, the model and records, AP2's matcher, the dry run) and writes only the editor's operation catalogue and profile operations, as proposals in the editor's Proposed list. A question is answered in the thread from what it read; an action becomes a plan that runs on one confirmation (AP-D13). AP-D12 gains a sixth step kind, **a capability's job** (AP2's matcher, value drafts, the dry-run grouping). Entries: the task page, the editor's pane and **New from a workbook**, whose AI path is the workbook and an optional words field (the assistant proposes the dialog's choices with reasons); without a provider the dialog stays as it is. AP1's rename becomes step 3 of the workbook flow; AP3, AP4 and AP5 are folded in. Why: the separate helpers did not reach each other (AP2 could not serve a workbook load), and a capable provider (Claude, ChatGPT) can be called as often as a task needs. |
| AP-D28 | A draft-only change to a released element nothing holds | **Approved by the user 2026-10-31. It applies when it would affect 0 records, values and relationships**, counted in every workspace running the model and their change sets; above 0 it is refused as before. Amends 0.10 D17 and the roadmap's "blocked until 1.0". Why: activation checks the workspace's data again (`*_IN_USE`, required checks) and consumer contracts, so the refusal at edit time protected no data, and a released model with no data could not be edited. A key change stays refused whatever the count: "public IDs and model keys are stable", and an integration names elements by key where no guard sees it. Cost: one count per released element an operation touches, once per request. The menu cannot know the count without counting every element on each outline read, so a released element's actions stay listed, reading "Refused if data uses it" |
| AP-D29 | How far may the session go? | **Approved by the user 2026-10-31. Replaces AP-D12. The session may use whatever its API grants allow, and stops at what a person confirms: a change set, which a person publishes, or (AP-D46, 2026-11-01) for a whole type that becomes another, a release and its migration, which a person with Model release previews and confirms; a person activates and publishes.** It is held by the engine, not by the prompt: the session's client holds no group that publishes, activates or migrates (J50.30, J50.50). Why: each limit added around the working setup was the limit that failed (AP8). What it costs: "only known steps" can no longer be promised, so the guarantee rests on the grants, the dry run of every row and the change set. |

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

## AP8: The assistant is a Claude Code session

**Decided by the user 2026-10-31; this section is the current design of the assistant.** It replaces the
designs of AP3 to AP7, which are kept under [History of the assistant](#history-of-the-assistant) for their reasons.
The requirement in the [Outcome](#outcome) did not change. Reconciled against the code 2026-10-31; nothing was run.

**How it works** (`engine/tasks/agent.py`, journey J50.30). The person's words, the workbook, the workspace's model
and the API's OpenAPI document go to one Claude Code session, a process of the assistant worker in a folder of its
own, set up by `AI_AGENT_COMMAND`. It works through the API as the client "AI assistant".

1. **Proposal.** It builds a model draft, checks every row with the draft's dry run and writes a proposal: two
   sentences and its questions. Nothing is installed or loaded.
2. **The person's turn.** They read the proposal, edit the draft in the model editor or say what to change, and the same
   session goes on.
3. **Accepted.** It installs one release, does not activate it, and loads into a new change set. An empty change set
   is not a load.
4. **The person** activates and publishes from the change set. The engine refuses the session both (AP-D29). A whole type that becomes another ends in a release and a migration instead, which the person confirms (AP-D46).

Words without a workbook work the same way. A file whose saved profile still fits takes the engine's path with no AI.

**What stays from the earlier designs:** the task, its page and journey bar, the draft, the dry run, the guards on
the session, and every fix they made to the import engine (listed in the AP6 progress notes in the history).

**Where the user's cases stand on real files (from the [usage log](#ai-usage-log-for-hosting-cost-planning)):**

| Case | Under AP8 |
| --- | --- |
| A, an update | Words only: works (185 records). "Update from this file": works since AP10, by a key of two columns: 0 new, and a changed price changes that price alone, no AI on a saved layout. The acceptance workbook: not tried |
| B, C, additions and new relations | Not tried. They worked on the earlier design only |
| D, E, new or related application | Loaded on two workbooks, nothing refused. Over the time limits, and the same words gave very different models (AP11) |
| Reshaping | One try: 6,816 created, 667 changed. Values not checked by a before/after count, and it took 922 s (AP12) |
| Scenarios as worded: translations, system variants, a new business | Not tried (AP13) |

**The open work, every item with one package:**

### AP9: Who did it

- **Provenance (AP-D5, AP-D7).** A session's changes carry no `origin` and act as the shared client. The change-set
  columns exist, and the import path does not fill them. Accepted changes must read as machine-proposed, asked for by
  the person, approved by the person, through publication into history.
- **One client per session.** All sessions share one client and its grants come and go per session, so sessions
  overlapping across nodes could use each other's workspace grant. Found by reading the code, not reproduced.
- **The call record (AP-D4).** Session runs reach neither `ai_calls` nor the usage file, so Settings › AI does not
  show them and hosting estimates lack their tokens.
- **Retention (AP-D24).** Check that a failed or abandoned task's folder goes with its task.

#### AP9 in detail (planned 2026-10-31, for approval)

Mock-up: [AP9 Who did it](https://claude.ai/artifact/DSPUiWVd2DJUncrCkAxXkT) (a Design canvas, not kept in the repository).

**Checked against the code.** The four items above hold, and six more things belong to them:

- **The folder does not go with its task.** `task_store.expire` returns only source files, and `remove_folder` is called only on a load and
  on a discard. A failed or abandoned task leaves its workbook copy and session logs on disk for good.
- **Claude Code keeps its own copy.** Each session leaves a transcript in `~/.claude/projects/<the folder's path>`, outside the folder and
  outside any retention: 15 on this machine, up to 1.5 MB each. What it holds was not opened for this plan; a session reads the workbook, so it should be assumed to hold values.
- **The shared client reaches further than the grants.** `_await_its_jobs` waits for every session's jobs, and `_reached` counts every session's
  draft and release events, so overlapping tasks wait for each other and can show each other's steps.
- **The session can hold more than the person.** `_access` narrows only the model grant. The data grant always gives Browse, change sets and Bulk
  on the whole workspace, though "who asked" may hold writes to two record types only (D243).
- **Four-eyes can be passed through a session.** The session holds `change-sets.submit`, so it can submit, and `_require_second_person`
  compares the submitter with the approver. The person who asked could then approve their own request under `secondPerson`.
- **A record's origin stops short of history.** `MergedObject` has no origin and publication copies only a relationship's. `ProposalOrigin` requires
  `confidence` and `reason`, which a session does not have. `change_set_objects.origin` has no writer.

| # | Decision | Why |
| --- | --- | --- |
| AP-D30 | **One client per task, of a new kind `session`, recorded as `ai_tasks.client_id`.** Named "AI assistant". It has no secret, so it can hold only the token the engine issues it, and it is left out of the client lists unless asked for by `kind`. It goes inactive when the task is loaded, discarded or expired, not on a failure, which may be tried again; the row stays, as audit entries name it. Grants still open and end per turn, so each turn re-reads what the person may do. The shared client is made inactive by the migration. `_await_its_jobs` and `_reached` read the task's client. | A grant, a job and an audit entry then belong to one task with no further rule. A task, not a turn, because its turns continue one session. |
| AP-D31 | **A session holds what the person holds, and of that no more than the session's groups.** The data grant carries only the groups the person holds in the workspace, with their `applications` and `recordTypes`. Publish, Approve and activation stay out whatever the person holds (AP-D29). | AP-D7: "the change is made by the person's own request", and `_access`'s own comment promises this. A person narrowed to two types must not widen through a session. |
| AP-D32 | **The engine stamps the origin at the write, on every change-set row a session's client writes,** in `ChangeSetWrites` and the tombstones in `deletion.py`, the only places that make these rows: `{kind: "ai", provider, model, promptVersion, proposedBy, taskId}`. `proposedBy` is copied, so it outlives the task. `confidence` and `reason` become optional, and the mark omits the percentage when there is none. | It holds for whatever route the session chooses (AP-D29), where stamping after the turn would miss other change sets and any row a person touched meanwhile. Set work: the value goes in the existing multi-row statements. AG3's `kind: "agent"` uses the same place. |
| AP-D33 | **A person's edit of a marked row keeps the origin and adds `editedBy`,** as AP-D5 says. A session's write over a person's row marks it. Publication copies the origin into the audit entry of records and relationships, removals included. | The history then says what happened: proposed, edited, published. AP2's "a changed target loses its mark" is unaffected, as a new target is a new row. |
| AP-D34 | **"Approved by" is what history already records: the publication's actor and the approval's decider.** A session's submission is recorded as submitted by the person who asked, so `_require_second_person` holds. | No second record of the same fact, and it closes the four-eyes gap at its one comparison. |
| AP-D35 | **The session's model steps say who asked too:** a step written by a session's client gets `proposedBy` and `taskId` in its `origin`, and the editor's history shows it. No element is marked Proposed for it. | AP-D5 names steps. The draft is the person's to review as a whole (AP-D6), and marking every element would add noise to a draft that is all proposed. |
| AP-D36 | **One `ai_calls` row per turn,** purpose `assistantSession`, written when the turn ends however it ends: answered, or failed with kind `failed`, `timeout`, `cancelled` or `interrupted`. A worker that died leaves no row at the time, so the next turn writes it from the log named in `agentProcess`. New columns `cost_usd` and `task_id`. **Tokens** are summed from the stream's messages by message ID, so a killed run has them too; cache reads and writes count as tokens in. **Cost** comes from the result line, as the difference from the task's last figure, because the usage log found it cumulative over turns; a run with no result line has none. `bytes_in` and `bytes_out` are the prompt and the final answer only, as the session's own API traffic is not measured. With `AI_LOG_CONTENT` on, `content` holds those two, never the stream. | The exit gate asks for "every run, with its tokens and cost". Summing the stream gives one path for finished and killed runs. `usage.jsonl` stays a tool of the development provider. |
| AP-D37 | **The folder and the transcript go with the task.** `expire` also returns the task's folder, removed after the commit as its files are. `remove_folder` also removes the transcript directory, honouring `CLAUDE_CONFIG_DIR`. The sweep removes an `agent/` folder with no task, and a transcript directory of this instance's `agent/` path whose folder is gone. A failed task keeps its folder until it expires, because a person may still try it again (`queue_retry`). Retention reads `AI_TASK_RETENTION_DAYS` from settings, since `ctx.ai` is empty with no provider and the fallback ignored the setting. | AP-D24: "never the rows or samples sent to the provider". A separate config directory per session would avoid the transcript but breaks the session's sign-in. The directory's name is Claude Code's own convention, so the real try confirms it; another command has none and nothing happens. |

**Scope.**

- **Migration `20261120_03`,** written in one go as the dev server applies it on save: the `session` kind, `ai_tasks.client_id`, `ai_calls.cost_usd` and `task_id`, the shared client made inactive.
- **Engine:** `tasks/agent.py` (client, grants, record, stream), `tasks/store.py` (`expire`), `jobs/worker.py` (the sweep), `records/writes.py`, `records/deletion.py`, `change_sets/publish.py`, `change_sets/approvals.py`, `model/authoring/history.py`, `identity/clients.py`, `proposals/calls.py`.
- **API, additive:** `origin` on a record in a change set and on a record's history entry; `ProposalOrigin` gains `taskId` and `editedBy`, and its `confidence` and `reason` become optional; `purpose`, `costUsd` and `taskId` on a call, `costUsd` in the totals. OpenAPI lock re-baselined.
- **Frontend, as in the mock-up:** the mark without a percentage and with who asked and who edited, on a record's history and its panel in a change set; Settings › AI's new purpose, a cost column and total; the editor's history line. No new screen.
- **Documents:** API, ARCHITECTURE, OPERATIONS (the transcript and what retention covers), USER_JOURNEYS J50, API_JOURNEYS, CURRENT_FUNCTIONALITY, PROJECT_STATUS, CHANGELOG, and the "Where each decision stands" table (AP-D4, D5, D7, D24 met).

**Out of scope:** marking earlier sessions' change sets, which stay unmarked as nothing recorded who asked per row; a filter for machine-proposed rows; the one switch and whether Settings › AI is reachable with only `AI_AGENT_COMMAND` set (AP10); a saved profile (AP10).

**Tests, J50, through the API with the scripted session on two model configurations, within the package's quarter:**

1. **The whole trail:** a session loads into a change set; every row carries the origin. A person edits one value and publishes. A created record's history reads proposed by the AI, asked for by the person, edited by them, published by them, and still does after the task expires.
2. **Two tasks at once, in two workspaces:** one's token is refused in the other's workspace, a turn does not wait for the other's job, and each task's steps are its own.
3. **A narrowed person:** with writes to one record type, the session is refused on another; publish and activation stay refused for a person holding both.
4. **Four-eyes:** the session submits; the person who asked is refused the decision, and a second person approves.
5. **The call record:** a finished turn, a failed one, a cancelled one and a worker that died each leave a row; cost over two turns is the difference, not the running total; no content unless `AI_LOG_CONTENT` is on.
6. **Retention:** an expired failed task's folder and transcript go (with a test `CLAUDE_CONFIG_DIR`); another task's stay.

The scripted session (`helpers/session-stand-in.py`, and J50.30's command) gains stream lines with usage and a result with cost. `AiPage.test`, one check in the `ap1-ai` browser runner, and the frontend production build. Groups to run: J49, J50, the change-set publication and approval groups, `contract`, `test_boundaries`, each alone in a window, as AG2's runs also use the test database.

**One measurement:** a 2,000-record load into a change set, timed before and after the stamp (the basics rule). Nothing larger, as the stamp is one more value in existing statements.

**The real try:** one real Claude Code session in a scratch workspace on the Timetables workbook, up to publication there, as a person. It confirms what was taken from memory (the stream's message IDs and usage, the result's `usage` and cost, the session's model in its first line, the transcript's path) and compares the recorded tokens and cost with what the session reported, logged in the [usage log](#ai-usage-log-for-hosting-cost-planning).

**Working beside other sessions:** AG2 is being delivered in this checkout. Its code files do not overlap with these, and AG2 adds no migration. Several documents do overlap, so commits hold AP9's hunks only.

**Door check (ADR-032):** additive, and the first real use of the value-provenance door beyond relationships, kept outside a record's values. `session` joins `api` and `agent` as a client kind. No door closes.

**What the user cannot do after AP9:** see a filtered list of machine-proposed rows; read a per-row reason, as a session gives none; read a cost from a command that does not report one; reach Settings › AI with only `AI_AGENT_COMMAND` set, if that holds (AP10).

#### AP9 record (built 2026-10-31; the real try is open)

Built as planned, with three changes found in the work:

- **AP-D32:** the stamp is one `before_flush` listener in `records/proposed.py`, not code in `ChangeSetWrites`, so every row those writes make is covered from one place. Tombstones take it in `deletion.py`. The origin holds public IDs, and a read names them as they are now, as `principals.py` does for everyone. A list's records carry the mark without names.
- **AP-D37:** expiry does not return folders. The sweep removes any folder without a task, which also covers a crash between the commit and the removal. A session that ran and left no transcript where one is expected logs a warning, as the path is Claude Code's convention.
- **A record's panel:** J50.31 found that reading a record in a change set returned no origin (`object_projection`); fixed.

**Checked:** J49, J50 (30, with J50.31 to J50.36 new), `change_sets`, `contract` and `startup`, J51, J52, the settings and history frontend tests, the production build, and `ap1-ai` with its new check of the call record. The API diff against HEAD in a worktree is the additions listed in the lock's comment. Not run after the last lock move: the full suite, which is R's.

**Found beside AP9, not caused by it:** `test_batch_statements` (8 cases over budget) and J38.1's `test_a_mapping_proposed_with_evidence` (2 cases, `'Bsrc'` missing) fail the same way at commit `136d3cb6`, without AP9. Their cause was not looked for; they must be settled by R. AP9 adds one statement per database session for a client's change-set writes, the lookup of its task (for example 44 to 45), constant whatever the size.

**One measurement,** a 2,000-record batch into a change set: 1.77 and 1.79 s as a person, 1.89 and 1.83 s as a session, about 4%. 200 records: 0.20 to 0.34 s.

**The user's own try, task `e5f1f1e2`, first turn (2026-10-31):** one call row, `claude-sonnet-5-5`, $1.113 equal to the session's figure, 2,330,341 tokens in equal to its result line. Tokens out read 939 against its 27,542, as the stream holds a message's output before it is written; fixed, the result line's figure now stands.

**Not done: the rest of the real try.** Still unseen with real Claude Code: whether cost and tokens out are running totals over turns, the marks after a real load and publication, and the transcript's removal. A person's token needs a real sign-in, and creating a client with instance roles for the try was refused by the permission check. **It waits for the user.** Until then AP-D36's figures and AP-D37's transcript removal hold only against a scripted session.

**What the user cannot do yet:** see the mark on a relationship's own read (`GET /relations` has no origin; publication's history does carry it); filter for machine-proposed rows; see the mark on earlier sessions' change sets.

### AP10: One path

- **One switch and one assistant.** `AI_PROVIDER` and `AI_AGENT_COMMAND` are separate today: with only the provider
  set, a workbook is read by the rules alone and words alone go to the old turns. Settings › AI says what is available
  and the page is hidden when it cannot work (AP-D21). `AI_PROVIDER` stays for AP2, AG4 and Track O.
- **The old design removed.** Whatever only the turns of AP6 to AP7 reach in `design_job.py`, `design.py`,
  `draft_plan.py`, `design_checks.py`, `links.py`, `matching.py`, `plan.py` and `turns.py`, each confirmed unused first.
  The saved-layout path and the rules-only path keep what they use.
- **Repeating next month (AP-D13).** The session is not asked to save a profile, so the no-AI path may never apply to
  its loads. A load leaves a saved profile.
- **Updating from a file.** A key may span several columns (AP-D43).
- **The session's leftovers.** Unused releases (0.10.3, 0.10.5), and sessions reusing another task's draft (tasks 53, 57).
- **The proposal page** looked at in a browser, and journeys only where the tries showed a need. J50 is 9 tests, 3 on
  sessions.
- **Documents:** `API.md` and `USER_JOURNEYS.md` J50 still describe the turns, `ARCHITECTURE.md` both designs.

#### AP10 in detail (planned 2026-10-31, approved by the user 2026-10-31 with AP-D39 and AP-D43)

**Checked against the code and the development database; nothing was changed or run for this plan.**

- **The switches.** `POST /ai/tasks` needs `AI_PROVIDER` (`ai_requested`, `409 AI_NOT_CONFIGURED`), and Settings › AI shows "No AI provider" without it, though a session uses no provider. With only `AI_PROVIDER`, words alone reach `_propose`, which reads a saved profile from a reading the task does not have, so it looks set to fail; not run.
- **The old design is mostly gone already.** Nothing writes `links`, `derived`, `sheets`, `records` or `explains` into a task's design any more, but `design_job.py`, `draft_plan.py` and the page still read them. Reading the imports alone calls most of this code reachable, so each removal is confirmed by its field having no writer.
- **The rules-only path has no configuration left.** It runs only when `AI_AGENT_COMMAND` is empty and `AI_PROVIDER` is set. With one switch, nothing reaches it. This differs from the list above, which keeps it: see AP-D39.
- **A session's profile can be recovered.** Every import job holds its profile in `parameters.profile.definition`, and all the sessions' import jobs in tasks 53 to 67 loaded a file of the workbook's name and size. A saved profile is checked against the workspace's running release, which a session's new model is not yet, so it must be checked against the change set's release.
- **Most session loads would not repeat as they are.** Of the 9 tasks from 53 to 67 with a completed import, 6 have an `upsert` source with no key (56, 57, 62, 63, 64, 66), so a second run would create those rows again.
- **Leftovers.** Tasks 52 and 53 share draft 103, and tasks 56 and 57 share draft 106. Releases 0.10.3 and 0.10.5 are on no workspace and no change set.

| # | Decision | Why |
| --- | --- | --- |
| AP-D38 | **`AI_AGENT_COMMAND` alone turns the assistant on.** `POST /ai/tasks` needs it and no longer `AI_PROVIDER`; `AI_NOT_CONFIGURED` names the command. `AI_SEND_LEVEL` and Use AI proposals still apply. Settings › AI opens if either is set and says what each gives. Without the command, no assistant action is drawn and the task page's route answers not found in the shell. `AI_PROVIDER` serves AP2, AG4 and Track O only. | AP-D21 and the exit gate's "no screen shows an AI action". A session calls no provider, so the provider cannot be its precondition. |
| AP-D39 | **Approved by the user 2026-10-31. The rules-only task path is removed: it overrides "the rules-only path keeps what it uses" above.** `POST /ai/tasks/{id}/plan`, `queue_plan`, `queue_run`, `run_plan` and their helpers, and the Reading and Check views go. The ordinary import and its profile dialog are not touched. | No configuration reaches it under AP-D38. It is removed because nothing can run it, not because the UI does not use it, which the API-first rule forbids. Cost: a client that called `/plan` gets 404; before 1.0 that is allowed. |
| AP-D40 | **The old design goes.** All of `links.py` and `turns.py` (its one constant moves or goes with its reader), `design.py` and the unreached parts of `design_job.py`, `draft_plan.py`, `design_checks.py`, `matching.py`, `plan.py`, `job.py`; `workbookLoad` as a provider purpose and the fake's answer for it; `AI_MAX_STEPS`; `DesignLinks`, `DesignRecords` and what only they use. What J50.12's saved-layout path and J50.30's session run stays. Old rows in `ai_calls` stay readable. | The list above. A dead branch here reads as design and has already misled plans. |
| AP-D41 | **The engine saves a profile from the load,** in `accepted`, after the non-empty check. It reads the change set's completed import jobs whose file's hash is the task's workbook, joins their sources and value maps, checks them against the change set's release, and stores `checked_release_id` as that release. The same key next time is the next version. The session is not asked to save it. **No profile is saved, and the task says why, when:** the change came only through batches, another file was loaded, or a source has no key. | It holds whatever route the session took (AP-D29). A keyless source would create its rows again next month, so saving it would promise a repeat that duplicates. |
| AP-D42 | **The session is told each source needs a key** that finds its records on the next file, several columns if needed, and to raise it as a question if none exists. **The proposal warns** when a type the workspace holds records of would get new ones: "667 new Products beside the 667 held: if this is an update, the rows did not find their records." Accept stays available. | A prompt alone does not hold, so task 57's mistake also shows before anything is installed. Whole-set figures come from the dry run. |
| AP-D44 | **A session may not write a draft another task holds:** `409 AI_TASK_DRAFT_HELD` on its model-draft writes, by AP-D30's client and `ai_tasks.draft_id`, and the same check when a proposal lands. The session then makes a draft of its own. A person's draft that no task holds stays open to it. | Enforced by the engine, as a prompt would not hold. Otherwise one task's session can change a draft another person is reviewing, and one task's expiry deletes the other's draft. |
| AP-D45 | **When a task ends, a release its client installed that no workspace or change set uses is retired,** not deleted, as history may name it. Existing ones are left. | "Exactly one release" is only a prompt. A retry or a failed load must not leave a release behind. |

**Scope.**

- **Engine:** `imports/` (`SourceKey`, `binding.py`, `profiles.py`, a save against a named release), `tasks/` (AP-D40's removals; `agent.py`: `_propose_prompt`, `_ACCEPTED`, `_proposal_landed`, `_left_out`, `accepted`), the model-draft write path, `jobs/worker.py` (one call goes), `proposals/`. No migration: a key lives in a profile's JSON.
- **API:** `attributeTypeKeys` on a source key; `/plan` removed and `table` off `/changes`; `AI_TASK_DRAFT_HELD`; `result.profileKey` or `result.profileNotSaved` with its reason. OpenAPI lock re-baselined.
- **Frontend:** Settings › AI's assistant section; the offer read from `assistant`; the warning on the proposal; the loaded page's profile line; the Reading, Check and links views removed.
- **Documents:** API, ARCHITECTURE, OPERATIONS (settings, and what `AI_PROVIDER` no longer does), USER_JOURNEYS J50 rewritten to the session, API_JOURNEYS, CURRENT_FUNCTIONALITY, PROJECT_STATUS, CHANGELOG, the "Where each decision stands" table.

**Mock-up (the existing proposal and loaded pages; only the marked lines are new).**

```
Settings › AI
  Assistant   On   AI_AGENT_COMMAND: claude --model sonnet        <- new
                   Reads workbooks and words, up to a change set
  Provider    Not set   AI_PROVIDER                               <- new wording
                   Mapping targets, search and summaries are not offered

Proposal
  Two sentences · shape per type · questions · Accept | Say what to change
  ! 667 new Products beside the 667 held. If this is an update,   <- new
    the rows did not find their records.

Loaded
  Change set "…": 667 updated
  Saved the profile "…": the next file of this layout loads       <- exists
  without the assistant.
  Not saved as a profile: sheet "Packages" has no key, so         <- new
  a second load would create its rows again.
```

**Tests, within the package's quarter, through the API with the scripted session on two model configurations.**

1. **One switch:** given only the command, a task runs; given only the provider, `POST /ai/tasks` is `409 AI_NOT_CONFIGURED`, `GET /system` says so, and AP2 still works.
2. **The load leaves a profile:** given a session's load, a profile exists and validates against the change-set release. After activation and publication the same file takes the no-AI path and changes nothing.
3. **Not saved, with the reason:** a keyless source; a batches-only change.
4. **A key of two columns:** given a stored set where one column repeats, a re-import updates each record, and creates none. A stored duplicate of the combination refuses its row, an empty cell follows `rowsWithoutKey`. Live and in a change set.
5. **The warning:** a session's dry run creating rows of a held type shows it on the proposal, and Accept still works.
6. **Leftovers:** a second task's session is refused on the first's draft and goes on with its own; a failed load's unused release is retired, one in use is not.

Unit tests for the key's validation in `check_profile`. `AiTaskPage.test` and `AiPage.test`, cut to what stays. Groups to run: J48 to J50, the import groups, `contract`, `test_boundaries`, each alone in an agreed window with AP9. The frontend production build, and `ap1-ai`.

**One measurement:** a 2,000-record import by a two-column key against a single-column one (the basics rule). Nothing larger.

**The proposal page in a browser:** the `ap1-ai` runner with the stand-in session on two models, covering the proposal with its warning, the loaded page with and without a profile, keyboard and 390px, with screenshots inspected. Reference: the existing proposal page.

**The real try, before and after on the real model:** in a scratch workspace, Tariff File with few words through a session to publication, recording records, values and relationships. Then the same file with "Update from this file", which must give no new products. Then a copy with one price changed, which must take the no-AI path and change only that. Logged in the [usage log](#ai-usage-log-for-hosting-cost-planning) with tokens and cost.

**Working beside other sessions:** needs AP9's `ai_tasks.client_id` and `session` kind, so the build starts once those are saved in the checkout. AP9 holds `_access`, `_end`, `_await_its_jobs`, `_reached`, `_run_turn`, `_Progress`, `_retention` and `remove_folder` in `agent.py`, `store.expire`, the worker's sweep and `AiPage`; AP10 adds to `AiPage` after it, and keeps the line AP9 adds to `accepted` and `discard` that retires the task's client. AG2 is being delivered too, and backend `pytest` runs go one at a time across AG2, AP9 and AP10, in agreed windows. Commits hold AP10's hunks only. AP11 reads the same prompts.

**Door check (ADR-032):** identity and the import's key are touched additively. A combination finds a record only during an import, and the `unique` declaration, public IDs and the consumer `match` are unchanged. No door closes.

**What the user cannot do after AP10:** declare a combination unique in the model, so only an import checks it; use a several-column key in a batch `upsert` or a consumer `match`; repeat a change made only through batches without the assistant; repeat a load whose file has no key at all. Once the task that loaded a profile's file has expired, a sheet that profile left out sends the next file to a session, as nothing holds the earlier file any more.

#### AP10 record (2026-10-31)


| The same words again | AI | Result |
| --- | --- | --- |
| The same file, before the fit fix | one session, $1.52, 6 min | Every row unchanged, no duplicates; the saved layout was not taken |
| The same file | none, 11 s to the proposal | 0 created, 0 updated, 19,919 unchanged; live data identical |
| A copy with one price changed (200 to 201) | none | 1 updated, 19,910 unchanged: `price-amount` on that price alone |

**What the try found, each fixed with its test:** the fit refused any workbook with a sheet its profile left out; a session's direct upload left the next file nothing to compare with; the page's summary gave the generic matcher's figures ("8 are new") in place of the profile's; rows skipped for an empty key read as refused, and a check from before the draft's last change read as current (both found in the user's try, task e5f1f1e2). **An earlier try is not evidence:** task 2e5867a6 ran on the dev server's old code, as its reloader had stopped; the server was restarted by the user.

**Checks exercised:** J48, J49, J50 (with J50.31, J50.37 to J50.42), J27, J34, J35, J36, boundaries, error codes, API journeys and the OpenAPI lock, passing; `ap1-ai` on two object types, 1440px and 390px, light and dark, keyboard, axe 70 states with 0 violations, screenshots of Settings › AI, the proposal's warning and the loaded page inspected; Vitest for `features/ai-tasks` and `AiPage`, lint 0 errors, the production build. The 2,000-record basics: an update by two columns 2.18 s, by one 1.91 s. **Deferred to R:** the full suites. **Failing without AP10, for R:** `test_batch_statements` (8), `test_j38_1_model_mapping::test_a_mapping_proposed_with_evidence` (2), `test_export_volume::test_an_export_holds_its_statements_as_the_data_grows`; the cause is not known. The jobs and contract groups took 3 min 56 s, over the 3-minute ceiling, as they include the several-process journeys.

**Not exercised:** Timetables or another workbook under this path; a session on a workspace where the key is already declared unique. A session's model is not always the same, so the key it chooses may differ (AP11). The saved layout still asks the file's own conflicting values as questions on each repeat; they are kept as asked (the user's rule), and a person answering them each month may want that changed.

### AP11: Good models, in time

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
- **Speed** against the time limits: 1 to 2 minutes for a workbook like Timetables, 5 at most for a complex one. Runs
  take about 5 and over 5. Includes whether the session sends set work row by row. Open: the separated runs took 200 to
  348 s on Timetables and 497 to 633 s on Tariff File, proposal and load, without a person's wait. Tariff File's
  atomic import is refused at the 10,000-item limit, so the session falls back to row-by-row success, and pays for the
  failed try.

#### AP11 in detail (planned 2026-11-01, for approval)

Model shape is built; this plan is the rest: the time limits. **Requirement served:** "a few words + workbook → the model and the import", within 1 to 2 minutes for a workbook like Timetables and 5 at most for a complex one, without the person's wait. Reached from the existing task page; no other capability calls it. No screen changes, so no mock-up.

**Where the time goes (read from the session logs still on disk and `ai_calls`, `jobs`; no new AI run):**

| Run | Total | Model generating | Engine jobs | Output tokens |
| --- | --- | --- | --- | --- |
| Timetables, `agent/2`, task 6dbb584b | 660 s | 550 s | not summed for this run; all commands 95 s | 68,438 |
| Tariff File update, `agent/2`, task a2108859 | 351 s | 314 s | 7 s dry run; all commands 38 s | 41,008 |
| Timetables, `agent/3`, `ap-full-2`, proposal | 818 s | log removed by the load | 33 s, 13 dry runs | 81,394 |
| The same, load | 81 s | log removed | 14 s | 5,778 |

- **The engine is not the bottleneck, and set work is not sent row by row.** Every load was one import job: Timetables 14 to 16 s, Tariff File 20,039 items 21 s. The `atomic` refusal at 10,000 items cost 1 s each, twice, then `independent`. **Decided:** no engine change to imports or the limit.
- **Time follows output tokens,** at 124 to 130 tokens a second. So 120 s is about 15,000 tokens, against 41,000 to 81,000 now. In run 6dbb584b about 20,000 tokens are visible (estimated from 66,000 characters), so most are likely thinking, which the stream does not show. That is inferred, not measured.
- **The API does not describe the model language.** `ModelDocumentRequest.model` is an open object in the OpenAPI document, though `EngineModel` has a 31 KB schema in the code. Run 6dbb584b searched the OpenAPI text and probed the validator from 142 s to 376 s (234 s, 35% of the run), including a binding feature named `bogus` that came back valid. It concluded the filter "could not be expressed", which the engine can do. Under the API-first invariant this is a defect, whatever the assistant.
- **Walls in the session's environment.** Python cannot open a socket in the sandbox, only curl can: in run 6dbb584b one probe waited 40.7 s and the session then moved to curl; the other two logs do not show it. Two of the three logs start by reading the session's own log file in the folder. Another session tried to read the engine's source and the sandbox refused it, as it should.
- **Not known:** how much of this `agent/3` removed, as it names the filter's syntax, yet its run was slower and its log is gone.

**The work:**

1. **The model language in the API.** The `model` field of model requests and responses in the OpenAPI document names `EngineModel` and its definitions. Only the document changes: at runtime the field stays an open object, so a wrong model still gets the compiler's diagnostics with their JSON pointers, not a generic 422. Rules a schema cannot state ("not filterable") stay in the validator. **Decided:** `extra="allow"` and open `features` stay as they are, so `bogus` still passes; tightening them could refuse existing models, and it is not what costs the time.
2. **The session's environment.** The log moves out of the session's folder, beside it, and retention removes it with the folder (AP-D37); the interrupted-turn record reads it there. Prompt `agent/4` gains two facts in its connection sentence, not instructions on how to work: the network is reached with curl, and the model's language is `components.schemas.EngineModel` in `openapi.json`. Nothing else is added to the prompt.
3. **Each turn's split.** The worker logs one line per turn: total, model (`duration_api_ms`) and jobs seconds. No migration and no API change. The figures go in the usage log, as a load removes the folder and its log.
4. **Tries, each announced and run without a stop.** Fresh scratch workspaces, the user's words, none published, each logged. `ai_calls.prompt_version = agent/4` is the proof the server runs the new code (AP10's old-code mistake).

| Try | File | Command | Why |
| --- | --- | --- | --- |
| 1 | Timetables | as now, `claude --model sonnet` | The 1 to 2 minute limit |
| 2 | Tariff File | as now | The 5-minute limit |

Two sessions with their loads, about $6 at API prices going by the runs so far. **Lower effort or a smaller model is not tried (the user, 2026-11-01):** they trade the result's quality for speed. **Higher effort is not used either (the user, 2026-11-01):** sessions run at Sonnet 5.5's default, medium, as restricted mode ignores settings files. One `--effort high` try with the same words on Timetables was stopped at 706 s, having written its first model at 693 s, before any dry run; the medium run 6dbb584b wrote its model at 397 s. One run, so not proof, and no second one is planned.

**A try counts only if the result holds:** 0 rejected; every filled cell compared with the change set, 0 wrong; Timetables has the station and driver types, the filter the words ask for, and category translations on the categories; Tariff File finds its next file by its key. A faster run that loses these is reported as such, not used.

**If no try meets the limits:** AP11 stops there and is recorded as not met, with the figures and the cause, and the user decides. No further runs (one measure, then ask). The fixes above remove at most about 235 s of a 660 s run, so **they are not expected to meet the limits alone**. The report then says where the remaining tokens went, from the tries' logs (the rounds of dry-run fixes took about 235 s of that run), and what could shorten them without lowering the model.

**Journey cases (for approval, J50):**

- **J50.43 The model language is in the API.** Given the API's OpenAPI document, when a client reads a model draft's `model`, then it finds the definitions of types, relations and a binding's candidates; a model it writes from them with a candidate filter validates; a field no definition names in `candidates` is refused with its pointer, on two model configurations.
- **J50.44 A session's folder holds no log.** Given a session turn on the test command, when it runs, then the folder holds the workbook, model and OpenAPI and no log, the turn is in the call record, and a discarded task leaves neither.
- **J50.45 A worker that stopped.** Given a worker stopped during a turn, when the job comes back, then the turn is recorded as interrupted from its log in the new place.

Unit tests: none beyond these; the split's line has no edge cases that are not covered by `_Progress`'s.

**Checks:** J50, `contract` with the OpenAPI lock (re-baselined, diff read for AP11's additions only), `test_boundaries`, Ruff on the named files, the frontend production build. **Migration:** none. **Door check (ADR-032):** none affected.

**Working beside other sessions:** AP11 holds `_connection`, the log's path and `_record_turn` in `agent.py`. AP12 also touches the session's flow, so they do not overlap in a window. `pytest` runs go one at a time; commits hold AP11's hunks only.

**What the user cannot do after AP11:** rely on the same structure from the same words, which still varies by design; have reshaping within the limits (AP12); see the time split in Settings › AI, as it is a log line and the usage log.

#### AP11 record (2026-11-01)

**The time limits are not met.** The fixes are built and the results hold, but the time did not move. **Accepted and closed by the user on 2026-11-01 with the limits unmet.** Sonnet at medium, prompt `agent/4`, the user's words, fresh workspaces, none published.

| Try | Proposal + load | Limit | Model generating, proposal | Engine jobs | Output tokens, proposal | Cost at API prices | Earlier run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Timetables, `ap11-mot` | 821 + 66 = 887 s | 120 s | 699 of 811 s | 26 + 13 s | 86,395 | $2.79 + $0.43 | 817 + 80 s, `agent/3` |
| Tariff File, `ap11-price` | 384 + 66 = 450 s | 300 s | 321 of 378 s | 33 + 22 s | 39,065 | $1.22 + $0.26 | 324 + 76 s, `agent/2` |

**Where Timetables' time went:** the first model at 334 s (397 s in run 6dbb584b, an older prompt), compiled at 394 s; then 14 dry runs to 789 s, about 395 s, 9 of them with rejected rows, as it added the sources sheet by sheet. **So the time moved from working out the syntax to the rounds of fixing a load,** and these are mostly the model's own generation: the jobs took 26 s. One run each, and such runs vary.

**The results:** 0 rejected on both. Timetables: 2,138 records and 2,466 relationships; 107 category translations on the categories and 1,500 on the types. Tariff File: 10,386 records and 9,670 relationships, profile saved. Every filled cell of the columns each profile reads was looked for in the change set: Timetables 10,429, Tariff File 12,180, 0 not found. **That check is weaker than the plan's:** it finds a value in the change set, not on its own record, and on Tariff File it misses repeated headings such as `Currency #2`, so those columns are not compared.

**Not met from the words on Timetables:** the field filter is fixed to the reserved slots group and does not narrow to the slot's own category, raised as a question; stations and drivers have relations and filters, but their groups were not created, so the filters name groups that do not exist, also raised. The earlier run had built them as empty types. **Not exercised:** Tariff File finding its next file by its key, which needs publishing; the per-turn log line in a real run's output.

**Decided:** both try workspaces stay as unpublished scratch, as earlier tries' do.

**Built (items 1 to 3 of "The work").**
1. `model` in the model requests and responses names `EngineModel` (`ModelDocumentRequest`,
   `ModelDraftCreate`, `ModelDraftUpdate`, `ModelDraftResponse`, `ModelDraftModelResponse`,
   `ModelCompilationResponse`, `ModelReleaseResponse`) through `ModelDocument` in
   `app/management/schemas/model.py`, a JSON-schema annotation only: the field is still `dict[str, Any]` when
   validated, `extra="allow"` and open `features` unchanged. The lock gains `EngineModel` and its 34
   definitions in `components.schemas` and changes the `model` property of the two schemas the locked
   (model-management off) document holds; no path, no other schema changed, no name collision.
2. `agent/4`: the session's log is `agent/<task>.session-<id>.log`, beside the folder; `agentProcess.log` and
   `_record_interrupted` read it there, `remove_folder` and `sweep` remove it with the folder; the sandbox's read
   list is still the folder only. `_connection` gains the two facts (curl; `components.schemas.EngineModel`).
3. `_log_split` logs one line per turn: total, model (`duration_api_ms`) and jobs seconds.

**Checks run:** J50.43 to J50.45 failed on HEAD's code first (all six cases), then passed; J50.35 and J50.36
passed (J50.35's stopped-worker step now writes its log in the new place); `test_boundaries`, `test_api_journeys`,
`test_openapi_contract` (lock re-baselined); Ruff check on the changed files, Ruff format on the changed files
but `agent.py`, which was unformatted before AP11 (only its new function is formatted by hand); the frontend
production build.

### AP12: Reshaping, and asking from the workspace

- **Moving records between types.** The exit gate asks for it. The 0.8 restructuring does it. Prove it through a
  session with a before/after count on a real model, and make the reshaping's three phases work under AP-D29.
- **"Change this model…".** A way from the workspace to ask the assistant, with the workspace's model as its start. It is
  the existing task, offered there, and lands in the proposal page. WM1's Apply does not serve it: a session
  installs without activating, and WM-D2 keeps a task's draft, finished or not, away from WM1. The package decides how
  an accepted task's release reaches activation from there.

#### AP12 in detail (planned 2026-11-01, approved by the user the same day with the mock-up and AP-D46's two ways)

Mock-up: [AP12 Change this model](https://claude.ai/artifact/9U4YPasLC7NZADihz9rXiT) (a Design canvas, not kept in the repository). **Requirement served:** the exit gate's "reshaping a workspace's model is an instruction too": words from the workspace become a proposal, a person never needs the editor's draft, install and activate path, and a before/after count on a real model shows nothing lost.

**What the code does today (read 2026-11-01; nothing was run):**

- **The session stops short of a reshaping.** It holds Browse, Work in change sets, Bulk, Model authoring and Model install (`agent.py`, `DATA_GROUPS`, `MODEL_GROUPS`), so it can restructure in a change set on an installed release. It cannot activate, and a migration needs `model.activate` too (`catalogue.py`), so it cannot start one. `accepted` installs one release and needs a non-empty change set. After that the task is finished and its client retired, so nothing carries out the gate's third phase.
- **The restructuring is per record.** One operation changes at most 500 records (`RECORD_LIMIT`). `changeTypeUnder` needs a parent, so records at the top level change type one operation at a time, each a preview and an apply. A batch cannot change a record's type. For a whole type this is row by row through the API.
- **The migration is set work.** `typeMappings` moves a whole type to another in PostgreSQL. Records keep their IDs; a preview lists every conversion, loss and refusal; the data and the release switch in one transaction. It has no per-record condition, and containment the target has no place for is refused. Its code does not forbid two types mapping to one, but no test covers that merge.
- **The way from a change set to activation exists:** a change set on a release its workspace does not run offers **Move ‹workspace› to ‹release› and publish…**, refused where the workspace requires approval (`require_direct_publication`). Activating a release that fits, then publishing as usual, also works, approval included.
- **Task 61 (the one reshaping try) created 6,816 records.** Its log is gone, so whether anything kept its ID is not known. Nothing tells a session that a record can change type and keep its ID.

**Decisions (recommended, approved with this plan):**

| # | Decision | Why and what it costs |
| --- | --- | --- |
| AP-D46 | **Two ways, chosen by what moves.** A whole type becoming another (a rename, a merge, into another application) goes by migration: one release, the proposal's `moves` as `typeMappings`, one confirmation. Part of a type (a split by value, a new level, a new parent) goes by the gate's three phases. A task may need both only by being asked twice. | **It changes the gate's wording and AP-D29's "always stops at a change set":** a whole-type move has no change set, and it goes live at the confirmation of someone holding Model release, without the approval a change set needs. The session writes no data, so AP-D29's limit holds, and a person sees the full preview. The gate's route alone would send a merge of thousands of top-level records through the API one by one, against the rule that set work runs in PostgreSQL. |
| AP-D47 | **The proposal says what moves.** `proposal.json` gains `moves`: `[{"from", "to", "attributes"}]`. The engine checks them against the draft with `plan_migration`'s own rules when the proposal lands, drops a type it maps from `_left_out`'s warning, and adds each type's held records. A move the plan refuses fails the landing with the reason, as a held draft does. | The person reads "1,420 Suppliers become Partners" from the engine's figures, not the session's. No migration: `ai_tasks.design` is JSON. |
| AP-D48 | **The proposal is the final model.** For part of a type, the person reviews the final draft. On acceptance the session installs it, installs a second release holding the final model with the old types beside it, restructures on that one in a new change set, and ends with `CHANGE_SET:` and `THEN_RELEASE:`. | The person reviews the shape they asked for, not a scaffold. "Exactly one release" and J50.30's wording change for this case only. The engine holds `result.thenReleaseId` and leaves it out of `retire_unused_releases`, so AP-D45 still catches anything else. |
| AP-D49 | **A task's end without a change set.** `state` stays `loaded`; `result.changeSetId` becomes optional and `result.migration` holds `{releaseId, typeMappings}`. "An empty change set is no load" still holds for every task whose proposal had no `moves`. | A new state would touch every journey function and the database check for no gain. A client reads which case it is from the result. |
| AP-D50 | **Everything the person does is an existing route.** Whole type: `POST /workspaces/{key}/model/migrations` with `result.migration`, on the existing migration page, opened with those choices. Part of a type: `model/activation` of the release with both, the change set's normal review, approval and publication, then `model/activation` of `thenReleaseId`. Activation's own check refuses that last step while the old type holds a record. The task page shows each step when it can be done; a person without Model release in the workspace is told who can do it. | API-first with no new route and no second check. The approval rules hold for the change set. A task that expires before the last step leaves the empty types in place and the release installed; Settings › Model can still activate it. |
| AP-D51 | **"Change this model…" is the existing task.** A fourth item on the workspace ⋯ menu (`WM-D5`), `LoadWorkbookDialog` with the workspace fixed, the words first and required, and the workbook optional. It is shown where the assistant is on and the person holds Use AI proposals, Model authoring and Model release there, and not for a retired workspace. The task page's title and crumb stop saying "Load a workbook" for a task with no file. | One dialog, no copy. Without the model groups the session could not install, so the flow could not finish, and the item is hidden. Words-only tasks already work (J50.21), so the API does not change here. |
| AP-D52 | **Prompt `agent/5` gains facts only:** a record changes type and keeps its ID through a change set's `restructurings` or, for a whole type, the proposal's `moves`; creating new records and removing the old loses IDs and history. Nothing else is added. | Task 61's route is what this stops. The prompt cannot enforce it, so AP12's real tries count IDs. |
| AP-D53 | **No new engine capability for a large split.** Part of a type at the top level stays one restructuring per record, so a split of thousands is slow, and it is reported rather than built. | A per-record condition on `typeMappings` touches every statement of the migration, and no real case has asked for it yet. A try on a few hundred records gives the figure. |

**The time limits are not a condition.** AP11 said reshaping within the limits is AP12, but the user accepted AP11 with the limits unmet, and their cause is the model's generation, which AP12 does not change. The tries report the figures and the split; no further fix is planned.

**Journey cases (for approval, J50, each on two model configurations):**

- **J50.46 A merge from words.** Given a workspace with records of two types, when a session proposes them as one and the person accepts and confirms the migration, then every record is under the new type with its ID, values, relationships and history, the old types are gone, and the workspace runs the release.
- **J50.47 The proposal says what moves.** Given `moves`, the proposal holds each type's record count and no left-out warning for those types. Given a move naming a type the draft lacks, the task fails with the reason and nothing is installed.
- **J50.48 Part of a type.** Given records of one type, when a session restructures part into a new type on an installed release the workspace does not run, then live data is unchanged, the change set holds them with their IDs, and the session is refused activation.
- **J50.49 The three steps.** Continuing J50.48: the person activates the release with both and nothing moves; publishes, and the records are live under the new type; activates the final release, and the old type is gone. Before the publication that last activation is refused, nothing changed.
- **J50.50 Under an approval policy.** Part of a type goes through approval as any change set. A whole-type migration confirms as a migration does, by a holder of Model release; without it, `FORBIDDEN`.
- **J50.51 A move the session cannot finish.** A person without Model release or Model authoring: a task can still be read, but the session holds no model grant and nothing is installed.
- **J50.52 What stays out.** The release with both is retired if the task is discarded before the change set; `thenReleaseId` survives the end of a loaded task, and any other release the session installed is retired (AP-D45).

Unit tests: the `moves` check, `_left_out` with a mapped type, reading `THEN_RELEASE:`, the task page's steps per result, the menu's item shown and hidden.

**Tries, each announced and run without a stop.** On scratch copies, so no real workspace changes; a scratch tool counts per type before and after: records, IDs kept, values per attribute and relationships. The 200 and 2,000-record basics are timed first.

| Try | Data | Words | Holds only if |
| --- | --- | --- | --- |
| 1 | A copy of `default` (2,141 records) | Two of its types made one | The migration moves all, 0 lost, every ID kept |

Two sessions with their loads, about $3 to $6 at API prices going by task 61 and AP11. Each is logged.

**Browser:** one runner on two configurations with a stand-in session: the menu, the dialog, the proposal's moves, the migration page and back, the three steps, by keyboard at 1440px and 390px, light and dark, axe, no 5xx. Screenshots inspected.

**Checks:** J50, J37, J15, `contract` with the OpenAPI lock (re-baselined last, diff read for AP12's additions only), `test_boundaries`, Ruff on the named files, Vitest for `features/ai-tasks` and the workspace menu, lint, the production build. **Migration:** none. **Door check (ADR-032):** none affected: identity is kept, and the generic restructuring and migration are used as they are.

**Documents:** `API.md`, `API_JOURNEYS.md`, `USER_JOURNEYS.md` (J50), `CURRENT_FUNCTIONALITY.md`, `PRODUCT.md`, the exit gate's wording and AP-D29 as AP-D46 changes them, `CHANGELOG.md`, the usage log.

**Working beside other sessions.** AG4 is running and AO1 is starting. **AG4:** it has `useWorkspaceAiOffer.ts` and `aiText.ts` open; AP12 only reads the offer. **AO1:** it adds the summary beside the activation preview and may touch `ActivateDialog`, `ApplyDialog` and the migration page, which AP12 also touches (opening with choices, the way back to the task). Whichever comes second takes the other's saved file. Shared by all: this document, `CHANGELOG.md`, the OpenAPI lock, re-baselined last. `pytest` runs go one at a time. AP12 holds `_propose_prompt`, `_proposal_landed`, `accepted` and `retire_unused_releases` in `agent.py`. Commits hold AP12's hunks only.

**What the user cannot do after AP12:** split thousands of top-level records quickly (AP-D53; no package); do a whole-type move and a part-of-a-type move in one task (two tasks); review a whole-type move in a change set or send it for approval (AP-D46); have a reshaping within the time limits (accepted in AP11).

#### AP12 record (2026-11-01)

**Built as planned, with the changes below.** Journey cases J50.46 to J50.52 were written from the plan's text
first (`backend/tests/journeys/test_j50_ai_reshape.py`, 7 cases on two configurations, a stand-in session working through
the API with the token the engine gives it) and run before the engine changed: J50.46 to J50.50 and the retiring half of
J50.52 failed, as the engine did not know `moves`, `RELEASE:` or `THEN_RELEASE:`. J50.51 and the discard half of J50.52 passed
before any change, as the grants and AP-D45 already hold them; they stay as guards.

**The unverified points.**

- **J50.46, two types mapped to one: held, no engine change.** The migration merges two types into a new one with IDs, values,
  relationships and history kept (the journey on both configurations). On a scratch copy of the dev database `duration`
  (6 records) merged into `role` (10): 16 records, 0 IDs lost, 0 names changed, the values of 4 attributes hashed record by
  record before and after, 0 differing, 4,562 relationships of the workspace before and after, all kept. **What the first
  attempt showed:** with a final model that only drops `duration`, the preview refused its 6 records
  (`PARENT_RELATION_SEMANTICS_CHANGED`) and listed 208 relationships as lost (`RELATION_PAIR_IN_USE`), and so could not be confirmed. The
  engine is right: the target type had no place for them. A merged model must give the target type the places of the type it
  absorbs. A consumer API that exposes a removed type needs its `contractVersion` raised
  (`CONSUMER_CONTRACT_VERSION_REQUIRED`), and a draft's `removeObjectType` on a type data holds is refused with
  `OPERATION_REQUIRES_MIGRATION`, so a session writes the final model whole. These are the session's modelling work; the
  engine's checks tell it each one: the move check (the migration's plan) and the consumer contract check
  (`contract_diagnostics`, as the preview and an activation apply it) run when the proposal lands, and a contract error goes
  back to the session (see "Fixed after the real try").
- **J50.48, restructuring on an installed release the workspace does not run: held, with one condition.** The change set must
  be started with `source: "currentLive"` and the release; without `source` the live records are not in it and the
  restructuring is refused (`notInChangeSet`). Prompt `agent/5` says so. The session is refused activation (`403`).

**Changes from the plan, and why.**

- **The session ends with a line, as the change set does:** `RELEASE: <id>` for a whole-type move and `THEN_RELEASE: <id>`
  beside `CHANGE_SET:` for part of a type. The engine takes a release only if its own audit shows the task's client installed it, so
  a session's word is not enough. A task whose line fails that ends `failed` with a note.
- **A release named by `result.migration` or `result.thenReleaseId` is not retired with the task** (AP-D45 would
  otherwise retire the migration's target, which no workspace runs yet). Any other release the session installed is.
- **The engine re-checks the moves against the release the session installed,** not only against the draft when the
  proposal landed, since the person may have edited the draft in between.
- **The mock-up's strip "The proposal › Records moved › Done" is the existing journey bar** (one component, no copy): its
  label reads "Change this model" for a task with no file, its last step "Confirm the migration", and the way back is "Back to the
  proposal". Boards 2 and 3 are built as drawn otherwise; the migration page is the existing page with its choices filled in
  and a **Back to the proposal** button, also after it is done.
- **Steps 1 and 3 of a part-of-a-type move open the release's page,** where the existing activation dialog is; the task page reads
  the workspace's release and whether the change set still exists (a published change set is gone) when the person comes
  back, and shows the next step. No second activation dialog was built.
- **The change set's own Review button is shown at step 2, not above,** so the review is not offered before step 1.

**Tries (engine side, scratch copy of the dev database restored into its own database and dropped afterwards; the

| Try | Before | After | Time |
| --- | --- | --- | --- |
| Basics, 200 records, two types into one | 200 records | 200 under the new type, 0 lost, 0 values changed | preview 0.5 s, confirm 0.5 s |
| Basics, 2,000 records, two types into one | 2,000 | 2,000, 0 lost, 0 values changed | preview 0.5 s, confirm 1.0 s |
| Basics, 200 records split by a value, one restructuring each | 200 | 200 under two types, 0 lost, 0 changed | 15.7 s (79 ms a record), publish 0.5 s |
| Basics, 2,000 records split | 2,000 | 2,000, 0 lost, 0 changed | 186.5 s (93 ms a record), publish 3.9 s |
| Copy of `default`: `duration` into `role` | 10 + 6 records | 16 `role`, 0 lost, 0 names or values changed, 4,562 relationships kept | preview 0.5 s, confirm 0.5 s |

AP-D53's figure: a split goes one record at a time at about 80 to 140 ms each, so 2,000 records take about 3 minutes and 10,000 about
13 to 23 minutes; the migration moves the same records in about a second. Reported, not built.

**The two tries with a Claude Code session (2026-11-02, prompt `agent/6`; stopped after try 1's preview).** Run through the
API by a client with owner, model-admin and workspace-admin (a client cannot follow the browser journey; the steps are the
same routes), on the running dev server with its real `AI_AGENT_COMMAND`. Scratch copies were made through the API: a workspace
on the same release, an inference mapping applied, a move in copy mode, a publish. `ai_calls.prompt_version` of the first session
reads `agent/6`.

- **Try 1, a copy of `default` (`ap12-merge-2`), "Durations and roles are really the same kind of thing: make them one type."**
  *The copy:* 2,141 records, as `default` (same count per type, same names; values 7,035 against 7,034: the copy's target
  model filled `active=true` on one record, "Administrative - Other", that `default` leaves empty); relationships 4,554 against
  4,562: 8 `alternative-for` relationships were refused by the move (`RELATION_CANDIDATE_REFUSED`: the model's own candidate
  rule is not met by `default`'s data), so the job page said "Partly applied". *The session (proposal, 200 s, 1,355,857 tokens
  in and 17,846 out, $0.72):* it landed with the consumer API `rdm` raised 2 to 3 in `design.consumerChanges` (the fix works: the
  list names the two types, two lists and two events no longer exposed), the two moves `duration` (6) and `role` (10) into a new
  type `timetable-list-value`, and no left-out warning. It also added a group type `timetable-list` with records "Durations"
  and "Roles" and changed the containment, which was not asked. *Accept (38 s, 478,616 in and 2,219 out, $0.13; $0.85 for the
  whole session, 238 s):* task `loaded`, `result.migration` with the two mappings. *The preview answered 202 in 1.1 s but cannot be
  confirmed:* 16 reclassified, 0 loss, **16 refused, all `PARENT_RELATION_SEMANTICS_CHANGED`** ("The target release has no place
  for this record under its parent"): the records sit under the catalogue and the session's final model gives
  `timetable-list-value` a place only under `timetable-list`, a type with no records, which a migration does not create. The
  confirmation answered `409 MIGRATION_HAS_REFUSALS`. Nothing moved: the workspace still holds 2,141 records, the 6 and 10 under
  their old types, 0 IDs lost, every ID kept (no change). Cause: the session's model, not the engine; the move check at landing
  (`plan_migration`) did not catch it, since it runs on the draft and the refusal comes from the preview against the live records.
  Not fixed or worked around by hand. The session also read `default` once by mistake (no workspace named on a records read, and
  an impact summary), both refused by the grants.

**Checks run.** J50, J37 and J15 journeys: 168 passed (14 of them AP12's, on two configurations). `test_boundaries`,
`test_openapi_contract` and `test_api_journeys`: 20 passed; the lock already holds AP12's schema additions, as AO1's commit was made with AP12's
schema file in the tree (its hash is that of both), so AP12's commit adds the schema file and no new hash. Ruff check and format on the
changed files. Vitest for `features/ai-tasks`, `features/model-admin`, `routing` and `app`: 268 passed (new:
`ReshapeSteps`, `useChangeModelOffer`, the proposal's moves, the dialog's change mode, the journey's migration end). Lint 0 errors
(the 10 warnings are earlier ones), the production build, and the browser runner `ap12-change-model` (29 checks: both
configurations, the menu by keyboard and by pointer, the dialog, the proposal, the migration page and back, the steps one at a time, light and dark,
390px, axe 0 violations on every state, and a backend with no assistant offering no item); its screenshots were inspected against the mock-up.

**What stays manual:** the real sessions above; nothing else.

**Fixed after the real try (2026-11-02).** On a copy of `default`, the assistant merged `duration` and `role` into one type; accepting
installed a release and the task ended `loaded`, but "Preview the migration" answered `409 CONSUMER_CONTRACT_VERSION_REQUIRED`: the
consumer API `rdm` no longer exposed the types, their lists and events. The session's checks ran `plan_migration` only, never the
contract check that the preview and activation apply, so nothing told the session. Now `_proposal_landed` runs
`contract_diagnostics(workspace model, draft)` when the proposal moves types or the draft is based on a release; its errors go back
to the session in a further turn (up to two), which raises the `contractVersion` and makes the definition expose the new type; a
draft still in error fails the task naming the consumer API. The proposal shows each consumer API whose version it raises
(`design.consumerChanges`: name, old to new version, what its consumers stop reading or read differently, from the engine's diff
`raised_contracts`) as a line under "What happens to the records". `_migration_result` and `_then_release` re-check the contract on the
installed release and fail the task with a warning naming the API instead of ending `loaded` with an action the engine refuses.
Prompt `agent/6` tells the session that a consumer API exposing a moved type needs its version raised in the draft. Tests: J50 gains
two cases (the contract error sent back and the migration then previewing; a draft that keeps breaking fails the task). A split that keeps the old type beside the new gives a final release equal to the change set's own (`result.thenReleaseId` = `changeSet.modelReleaseId`; the engine accepts it, `_then_release` only requires an installed release); `ReshapeSteps` then shows two steps, with no "Remove the emptied types", and finishes as done once the change set is published. The task result carries `changeSetReleaseId` (the change set's release) for that comparison, so the page is right when opened after publishing too.

The second try then showed the same shape for the records: the draft gave the merged type a place only under a new group type that holds no
records, the landing check (`plan_migration`, model level) passed, and the preview refused all 16 records with
`PARENT_RELATION_SEMANTICS_CHANGED`. Now `_proposal_landed` also runs `check_landing` (`engine/model/migrations.py`): the preview's own
preparation, application and refusals over a draft as the target model, with no job or installed release, over every record of the
workspace as set work, inside a savepoint that is rolled back, and the preview's refused containment edges from the same SQL. The refusals
go back to the session with code, message, count per type and example record names, in the same loop as the contract errors
(`LANDING_ROUNDS`, two); a draft still refused fails the task with the engine's reason and count. Losses are not refusals: the proposal shows
what each moved type would lose (`design.moves[].lost`: records, values, relationships) under "What happens to the records".
`_migration_result` re-runs the check on the installed release and fails the task with a warning if it refuses. Prompt `agent/7` adds that a
merged type must give its records the places they have now and that a migration creates no records. Tests: J50 gains two cases (the
refusal sent back, the corrected draft previewing with 0 refusals and the records moved with their IDs; a session that never corrects fails).

**The two tries, third run (2026-11-02, prompt `agent/7`, both through the API by a client with owner, model-admin, workspace-admin
and security-admin; the browser journey's steps are the same routes, driven through the API; running dev server, real
`AI_AGENT_COMMAND`).** `ai_calls.prompt_version` of the first session reads `agent/7`. Copies were made through the API as before
(a workspace on the same release, an inference mapping applied, a move in copy mode, a publish): `ap12-merge-3` from `default`
(2,141 records and 4,554 relationships, the 8 `alternative-for` relationships refused as known; `default` holds 4,562) and
every row (per type: record count, ID set, one value hash per record, relationships by type, from and to), taken after the copy was
published and after the last step.

- **Try 1, `ap12-merge-3`: "Durations and roles are really the same kind of thing: make them one type."** *Proposal* (147 s of
  session, 1,435,916 tokens in and 15,274 out, $0.77): two moves, `duration` (6 records) and `role` (10) into a new type
  `timetable-option` that keeps the six attributes they share and both places under the timetable catalogue; the 208
  `has-duration` and 199 `requires-role` relationships kept; `design.consumerChanges` names `rdm`, 2 to 3, with the six lines (the
  two types, two lists and two events no longer exposed); `design.moves[].lost` empty for both; no left-out warning; three
  questions with assumed answers (unfiltered pickers, the two other empty duration types left alone, one list
  `timetable-options`). *Accept* (22 s of session, 482,522 in and 1,832 out, $0.13): task `loaded`, `result.migration` with the
  two mappings; the session raised the release version to `0.9.25` itself after a `RELEASE_IDENTITY_CONFLICT`. *Migration
  preview:* 202 in 1.1 s, 16 reclassified, 0 conversions, **0 losses, 0 refusals** (the second run refused all 16);
  confirmed without `acceptLoss` (the proposal had shown no loss), 1.1 s, 16 applied, job completed, the workspace runs
  `0.9.25`. *Before/after:* 2,141 records before and after, **0 IDs lost**, 0 new, every ID kept; the 16 records changed type and no
  other record did; `timetable-option` holds 16 = the 6 durations and 10 roles (the union), `duration` and `role` hold none; 0 names
  changed, 0 parents changed, 0 value hashes differing, 0 value counts differing; 4,554 relationships before and 4,554 after, 0 lost
  (by ID, and by type, from, to and attributes), 0 new. Against `default` minus the 8 refused: 4,562 less 8 is 4,554, as in the copy.
  Nothing lost, so nothing the proposal had to show. *Time:* proposal 141 s to "checked", accept 24 s, preview 1.1 s, confirmation 1.1 s.
  Session cost $0.91 at API prices. A second preview was started by mistake of the scratch tool and cancelled; it moved nothing.
  `madrid-transport-product` with all of Product's attributes and a table view, `moves` empty on purpose, no consumer API, two
  questions (change the type after activation; keep all attributes). *Accept* (87 s, 533,796 in and 4,712 out, $0.23; 89 s of task time):
  `loaded`, `result.changeSetId` and `thenReleaseId`, 100 records updated, 0 rejected. *The three steps:* (1) activating the
  release with both answered 200 in 0.1 s, nothing moved; (2) publishing the change set answered 200 in 4.7 s; (3) activating
  `result.thenReleaseId` answered 200 in 0.05 s. **A point to know:** the final release the session installed is the same release as
  the change set's (`thenReleaseId` equals `modelReleaseId`), because the proposal kept Product beside the new type; so step 3 is a
  re-activation of the running release (it also answered 200 when run before the publication, which the planned refusal cannot
  cover where no type is removed). I ran that re-activation once before publishing by the scratch tool's mistake; it changed
  nothing. *Before/after:* 600 records before and after, **0 IDs lost**, every ID kept; 100 changed type (to
  `madrid-transport-product`) and 469 stayed `product`, matching `transport-madrid-enabled` true and false exactly (0 in the wrong
  type); 0 names, 0 parents, 0 value hashes and 0 value counts differing across all 600 records; no relationships exist. Nothing
  lost, so nothing to show. *Time:* proposal 57 s, accept 89 s, steps 0.1 s, 4.7 s and 0.05 s: about 151 s from the words to the
  third step. Session cost $0.51.
- **Both tries:** 2 sessions each, 4 calls, 2,890,944 tokens in and 27,635 out, $1.41 at API prices. Both reached the end with
  nothing refused and nothing lost. Not changed or edited by hand: the proposals, drafts and releases are the session's own.

### AP13: Acceptance on real files (AP-D22)

The remaining tries, each announced and judged by the user: the acceptance workbook, cases B and C, the scenarios as
worded, and the other new files under the session. Done after AP9 to AP12, so they judge the finished assistant.

**Value drafts and dry-run triage (AP4, AP5): removed from 0.16 by the user, 2026-10-31.** Neither was built. A person
asks for values in words, and the session reads the dry run's refusals itself. There is no bulk action on a filtered
list and no grouped summary of refusals for the person.

**Said plainly: what a person still cannot do after AP8:** hand a task to a colleague or run one on a schedule; use a
document or an image as data; attach more than one file (AP-D25); ask for something the API cannot do, which the
session says so; rely on a small local model.

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


**What the words ask for comes before the file's shape (2026-11-01, prompt `agent/3`).** The shape line of `8ea24e14` made sessions turn what the words placed under a named category into a type of its own, so the requested field filter had nothing to filter and sessions reported it impossible. It was never an engine limit: the fixed `ancestor:` filter does it, as the earlier runs in `harbour` show. The session is now told to build everything the words ask, as they place it, also with no data, and to say a thing cannot be built only after trying it. Real run in `ap-full-2`: proposal 817 s, $2.99 (over the limit, AP11), 0 refused, 0 skipped; accepted, 2,134 records in 80 s, $0.52, 0 rejected; 7,835 cell checks, 0 wrong; station and driver types present and empty; category translations linked to the categories. Not published.

**A session stopped by its own log, and the file then loaded (2026-11-01).** A session in `harbour-2` failed with an internal error after 284 s: a refused write comes as a system event whose `message` is text, and the log reader expected an object. The reader has done so since 31 October, before AP9 and AP10. It now leaves any line it cannot read. A real run with the same words and the Timetables workbook in the scratch workspace `ap-full-1`, on `harbour-2`'s model: proposal in 661 s ($2.37, over the limit, AP11), 0 refused, 0 skipped; accepted, 3,540 records created in 62 s ($0.41), 0 rejected, profile saved; not published. Every filled cell compared with the change set, 7,817 checks, 0 wrong. Not met from the words: no station and driver types, category translations linked to the types rather than the categories, slot picker unfiltered. Each was raised as a question with an assumption.

**Empty cells read as skipped rows, found on a real try (2026-11-01).** A workbook that imports whole reported 100 rows skipped and 3,024 unchanged on a new model. The check counted per source, so a row with no value in one list's column read as skipped although other sources wrote it, and links written with their translation read as unchanged records. A row now counts only when a value a source reads there is held by no other source, or no source reads anything on it; `unchanged` counts records only. The same dry run recomputed: 0 skipped, 0 refused, 0 unchanged, 4,244 created (3,537 records, 707 links). The session's prompt says an empty cell is no skipped row. A `unchanged` figure above that predates this also counts links.

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

### AG2 in detail (planned 2026-10-31, approved by the user the same day)

No screen changes, so no mock-up: Settings › Security › Agent access already lists whatever tool is called, and the client
page already grants a consumer API to an agent client.

**Checked against the code.** Five things in the scope above do not hold as written:

- **A person can never hold a consumer API grant** (`CONSUMER_API_CLIENTS_ONLY`, D306). "Authorization from its grant" would
  give a person signing in through an assistant no generated tool, and that is the route the AG1 real try used (AG-D19).
- **One key can mean different contracts in two workspaces** (ADR-042), so "one tool per definition" needs a rule for names and
  workspaces (AG-D20).
- **The limits of a tool name.** The model allows keys of up to 160 characters. Claude's API allows 64 characters in a tool
  name, and Claude Code puts `mcp__<server>__` in front, as this session's tool names show (AG-D20).
- **The parameter check is tied to the HTTP request.** `_Parameters.check` in `consumer/router.py` reads `request`, and
  `management` may not import `consumer` (`test_boundaries.py`). It has to move to the engine (AG-D21).
- **AG-D7's answer size cap does not exist yet:** AG1 built the rate limit only. The first tools with long answers need it (AG-D23).

| # | Decision | Why |
| --- | --- | --- |
| AG-D19 | **A definition's tool is offered where the caller holds its grant or Browse in the workspace.** The tool only: `/api/consumer` stays closed to anything but a `consumer` token with a grant (D306, D307 unchanged). Refines AG-D3's "the consumer definitions it is granted". A client holding only a consumer API grant sees that tool and `describe_access`, and no other tool. | The journey "what is the code of this value in the webshop system?" must work for a person. Grants narrow writes only (D243), so Browse already reads every record of the workspace, and a definition gives it a new shape and no new data. |
| AG-D20 | **Named by the definition, not by the workspace.** `lookup_<key>`, with a required `workspace` argument listing the workspaces the caller may read it in. Workspaces whose definitions are equal share one tool. Where a key differs between them, or the name would pass 48 characters, the name ends in a short hash of the definition. Hyphens stay; the characters allowed in a key are all legal in a name. | One tool per workspace would multiply the list for no gain when many workspaces run one model. 48 leaves room for Claude Code's prefix under Claude's 64. The list is read per caller, which `_run` already allows for. |
| AG-D21 | **The check moves to `engine/reads/consumer_parameters.py`, taking the parsed names and values;** the route passes them from its request and behaves as before. A tool offers `objects`, `lists` and `xref`, those the definition offers, on live data, with `asOf`, its parameters and its `to.` targets. **Not offered:** `resolve` (a batch for systems; `xref` answers one lookup), `events`, `publications` and a pinned read. The tool's schema is flat with an `operation` argument, and what fits each operation is checked by the moved check. | One check, the same refusals. Claude's API refuses `oneOf` at the top of a tool's schema (from memory, to confirm in the real try), and the check exists anyway. An assistant asks about the current state; an integration that needs a pinned read has the consumer API. |
| AG-D22 | **Eight curated tools join the two of AG1,** all needing Browse in the named workspace. The refusal is the same whether the workspace is missing or not readable: `describe_model` (applications, views, record types, relation types and consumer APIs, by key and name), `describe_type` (its attributes with their types and filters, parents, relationships, views), `find_records` (the `ModelQuery` of `POST …/queries/objects`), `read_record` (values, path, relationships), `mapping_coverage` (a view and `state`, `search`, `parentObjectId`; the binding is read from the view, as a route's caller must repeat it only to have it checked), `record_history` (`kind`, `actorId`), `list_changes` (`GET /changes`). Live data only: `changeSetId` joins them in AG3, whose tools read their own change set. | AG-D4's list, plus `find_records` and the two `describe_*`, without which an assistant cannot name what it asks about. Route bodies that hold their logic are split out as `workspace_page` was, so route and tool run one function. AO-D7's account tool arrives with AO2. |
| AG-D23 | **`MCP_ANSWER_BYTES` (40,000).** A paged answer over it is read again with half the page size, which returns a cursor, never a truncated answer. One record over it is a refusal saying so. `pageSize` defaults to 50 on the new tools. | AG-D7. The SDK sends a dict twice (as `structuredContent` and as text, seen in `lowlevel/server.py`), and Claude Code refuses long answers (25,000 tokens by default, from memory, to confirm in the real try). The size of the first page is not known before reading it. |
| AG-D24 | **Resources:** `refiroo://workspaces/{key}/model` and its `/applications/{key}`, `/object-types/{key}` and `/views/{application}/{key}`, all listed for the caller's readable workspaces, a page at a time by the protocol's cursor. They are read through `_run`, so the limit and the log hold, recorded as `read_resource` with `uri` as the argument name. A resource answers whole, without the size cap. | The scope. Claude Code reads resources (its `ListMcpResources` and `ReadMcpResource` tools); an assistant that cannot has `describe_model` and `describe_type`, which call the same functions. A model's size is bounded by the model itself. |
| AG-D25 | **Every tool here says `readOnlyHint`,** and each generated tool's description ends by saying that values are data. AG-D8 stands as the server's instructions already say it. Answers keep the API's shapes, with no wrapper. | The hint lets an assistant treat a read as safe. A wrapper would make a tool's answer differ from its route's. |

**Scope.**

- **Engine:** the moved check; the definition's tool schema (`engine/agent_access/`), with fields, parameters and descriptions from
  `compiled_consumer_apis`, so nothing per definition is written by hand.
- **Management:** `mcp_tools.py` gains `tools_for(session, permissions)` (the fixed tools and the generated ones, which both
  `_listed` and `_run` read), the eight tools and a workspace check; `routers/mcp.py` gains the resource handlers and the size cap;
  route bodies split where a tool needs them (`objects.py`, `changes.py`).
- **No migration, no new route.** The OpenAPI lock should not change.
- **Settings:** `MCP_ANSWER_BYTES` in `config.py` and OPERATIONS.md.
- **Documents:** USER_JOURNEYS J52, API_JOURNEYS, CURRENT_FUNCTIONALITY, PRODUCT line on agent access, OPERATIONS, ARCHITECTURE, EXECUTION_GUIDE,
  PROJECT_STATUS (its Open line still says AG1 is not built), CHANGELOG. The exit gate's "every call is in the audit trail with its
  channel" is corrected to AG-D16: reads in `agent_calls`, changes in the audit trail with their channel from AG3. The table row for
  AG-D1 to AG-D10 gets AG2's revisions and a working link to AG1 in detail.

**Out of scope:** writing and `changeSetId` (AG3), natural-language search (AG4), a tool for the account of history (AO2), any change
to the consumer API's own access.

**Tests, J52, through the endpoint with the SDK's client, on the two model configurations J51 uses, whose definitions differ:**

1. **A value's code:** a person with Browse and a client with only the grant both answer it from a generated tool. The answer equals
   the consumer route's for the same read. The client lists no curated tool, and an ungranted definition is neither listed nor callable.
2. **Unmapped values:** `mapping_coverage` with `state=unmapped` pages through a view with cursors and equals the route's rows.
3. **Finding and reading:** `describe_model`, `describe_type`, `find_records`, `read_record`, `record_history` and `list_changes` in one
   journey; a workspace the caller cannot read is refused in the same words as one that does not exist, on every tool.
4. **Two workspaces:** the same definition gives one tool; a differing one gives two, each listing its own workspace. A long key stays under 48 characters.
5. **The cap:** a page over `MCP_ANSWER_BYTES` comes back smaller, with a cursor that reads every row exactly once.
6. **Resources:** listed and read only where the caller may read, and logged by argument name.
7. **The route is unchanged:** the moved check's refusals through `/api/consumer` (the existing consumer groups for that boundary).

Groups to run: J51, J52, the consumer API's journeys, `contract`, `startup`, `test_boundaries`. No browser runner, as no screen changes.

**The real try:** one Claude Code session through the dev server, signed in as a person, asks the three journey questions on the user's own
model. It needs `MCP_ENABLED=true`, which AG1 already set, and the user reconnecting `/mcp` after the dev server reloads. It confirms the two
limits taken from memory and that resources are reachable. The bounded R try stays as AG-D10 says.

**Working beside other sessions:** other sessions have uncommitted changes in this checkout, so commits hold AG2's hunks only. J52 is
checked for being free before use.

**Door check (ADR-032):** additive. The moved check keeps the consumer API's contract, and a later stdio bridge would call the same tools. No door closes.

**What the user cannot do after AG2:** have an assistant prepare a change (AG3) or read a change set through it (AG3); read an older
publication through it (not planned, the consumer API does this); ask in words in the built-in search box (AG4).

### AG2 record (2026-10-31)

**Delivered as planned.** AG-D19 was taken as recommended: the user approved the plan without answering it separately, so it stands open to their correction.

**Where it differs from the plan:**

- The moved check is in a new module, `engine/reads/consumer_request.py`, not `consumer_parameters.py`, which `consumer_lists` imports: the check needs `consumer_lists`.
- **AG-D24 revised by the real try:** `resources/list` names each workspace's model only, and applications, record types and views are resource templates. Listing every part made 208.5 KB on the user's 15 workspaces, more than Claude Code shows inline. The list is now 15 entries.
- `_run` writes its record in a session of its own and applies the read guard, as a tool's read may hold a snapshot.
- EXECUTION_GUIDE is unchanged: its group table has no row for J51 or J52, and J52 runs by its file.

**Checks:** J52: 14 passed (seven cases, each on two configurations). `consumer`, `contract`, `startup`: 715 passed. J51, J52, J41, J31, J13, J07 and `test_boundaries`: 94 passed. The OpenAPI lock is unchanged. No frontend file changed, so no frontend build or browser runner.

**The real tries (Claude Code on Sonnet, through the dev server, the user's stored sign-in):**

| Try | Result | Tokens | API price |
| --- | --- | --- | --- |
| Tool list, `describe_model`, a lookup, `mapping_coverage`, resources | All worked, no tool error. `lookup_timetables` gave a value's code. Two keys differing across workspaces got hashed names. `mapping_coverage` with `state=unmapped` found 0 on the view it chose, so a non-empty list was seen only in J52 | 10 in, 1,596 out, 224,698 cache read | $0.197 |
| The resource list after the change | 15 entries, whole | 8 in, 200 out, 114594 cache read | $0.114 |

**The two limits taken from memory:** Claude Code did not refuse a long answer: it saved the 98.5 KB model resource to a file and showed the first 2 KB, so AG-D23's reason is weaker than written. The cap stays, as a page that fits is still what an assistant can use. No tool answer reached it in the try. Claude's refusal of a top-level `oneOf` was not tested, as the schemas are flat.

**Not verified:** Claude Desktop's and claude.ai's use of these tools; reading a part through a resource template in a real assistant (J52 reads one through the SDK's client).

**What the user cannot do yet:** have an assistant prepare a change or read a change set (AG3); ask in words in the built-in search box (AG4). An older publication is not read through an assistant, which is not planned.

## AG3: Changes prepared and submitted for approval

**Journey:** an agent asked to add five missing values creates a change set, adds the five, reads the
validation and submits it; a steward is notified in the inbox, opens it, edits one value and approves;
live data changes only at that approval.

**Scope.** Tools: create/select change set, add or change an object, set a field, add a relation, read
the change set's validation. Optimistic concurrency applies (versions are inputs); conflicts return the
engine's own error code and message. No approve, publish, delete, model or security tool exists, and the agent principal cannot approve through any route (AG-D5).

### AG3 in detail (planned 2026-10-31, approved by the user the same day, with AG-D27 as written)

**Checked against the code; nothing was changed or run for this plan.** Seven things in the scope above do not hold as written, or need a rule:

- **`_run` cannot write.** It never calls `set_writer`, and without a writer a change-set write is refused `WRITER_UNKNOWN`. It always rolls back at the end, and the engine's write functions commit themselves (AG-D28).
- **`_fitted` is unsafe for a write.** It runs a tool again to shrink a page, and refuses a long answer after the tool has run, which after a commit would report a saved change as refused (AG-D28).
- **A refusal loses the engine's code.** `_run` passes on `refusal.message` only, so `VERSION_CONFLICT`, `currentVersion` and `CHANGE_SET_INVALID`'s diagnostics never reach an assistant. The scope requires the code (AG-D31).
- **AP-D32's stamp recognises a task's client, not an assistant.** `proposed.py` finds its origin from the principal. A person signing in through an assistant has the same principal as in the browser, so the stamp must come from the call (AG-D29).
- **`ProposalOrigin` cannot hold this origin.** `kind` is `"ai"` only, with `provider` and `promptVersion` required (AG-D29).
- **`POST /change-sets` and validation hold logic in the route,** and the single-record reads' change-set forms are inline in `get_object` and `list_relations`. `_write` in `attributes.py` holds the present-or-absent checks. These are split as `workspace_page` was, so route and tool run one function.
- **The journey's "edits one value and approves" is two steps in the engine.** A submitted change set is frozen, and a person's edit withdraws the submission (`withdrawSubmission=true`, D426). The steward then publishes, which records an approval as their own decision, unless `secondPerson` is on, when they submit it again and a second person decides. `ChangeSets.tsx` already offers this. Nothing changes here; J53 covers both.

| # | Decision | Why |
| --- | --- | --- |
| AG-D26 | **Eleven tools, all needing Work in change sets in the workspace.** Reading: `my_change_sets` (open ones, with state and version), `read_change_set` (version, release, submission state, the last decision's comment), `change_set_changes` (rows, `kind` records or relationships, paged), `validate_change_set`. Writing: `create_change_set`, `add_record`, `change_record`, `set_field`, `add_relation`, `change_relation`, `submit_change_set`. Every write names `changeSetId` and `expectedChangeSetVersion`, and a change to a row its version too. **`changeSetId` joins `find_records`, `read_record` and `describe_type`** (AG-D22), which then read that change set and its pinned release. A write answers with IDs and the new versions. | The scope, with what an assistant needs to know that a person sent it back and why. `describe_type` must read the pinned release, or a change set on another release would be filled from the wrong model. Choosing a release needs `model-release`, which the ceiling excludes, so it is not offered. |
| AG-D27 | **An assistant reads and writes only change sets its own principal created;** any other answers `CHANGE_SET_NOT_FOUND`. A person's own change set counts, so "add these to my change set" works. Narrower than the API, where anyone holding the group may write to any open change set. | AG-D8: text in a record could otherwise steer an assistant into a colleague's change set, under review by someone who did not ask for it. **Cost:** an assistant cannot help on a colleague's change set. Opening this later is additive. |
| AG-D28 | **A tool declares it writes.** `_run` then sets the writer (the ceiling's permissions, group `change-sets`, the tool's action, the principal), never allows withdrawal, and runs the tool once with no size check. Reads stay as they are. `validate_change_set` writes its audit entry once and cuts its own diagnostics to fit, with a cursor. `annotations` become per tool: writes and validation are not `readOnlyHint`, and no tool is `destructiveHint`. | The one writer the routes use gives the same grants, record-type limits (D243), audit actor and `created_by`. A retry after a lost answer cannot apply twice, as the version it names has moved. |
| AG-D29 | **`origin = {kind: "agent", application, proposedBy}`, a type of its own beside `ProposalOrigin`.** `proposedBy` is the person or client's public ID, and `application` the assistant's name, copied as its row may be removed. `_run` sets it on the session, and `proposed.py` reads it before a task's, so AP-D32 and AP-D33 hold with no second place. Revises AG-D5's `{kind, client}`. | A person's browser edit and their assistant's edit must differ, so the principal cannot decide. AG-D13's "claimed" name stays claimed, so the mark says so. |
| AG-D30 | **`audit_events.channel`, nullable, written `mcp` only,** set in `_name_actors` from the session, for every entry the ORM inserts during a call. Shown as `channel` on `GET /changes` and a record's history, additive. Null means not through an assistant; earlier rows stay null. No screen shows it, as the mark says it for records and relationships. | AG-D16 moved it here. The tools reach only ORM-built events, and one hook covers them. **My proposal:** no line on the Changes page, because a change-set event's actor already names a client, though for a person it does not say it came through an assistant. |
| AG-D31 | **A refused tool call says `CODE: message`, then `details` as JSON,** on every tool, reads included. `_run` records it as now. | The scope, and an assistant needs `currentVersion` and diagnostics to correct itself. The refusal for a missing and an unreadable workspace stays identical. |
| AG-D32 | **Left out on purpose:** removing a record, relation or value; clearing a field (`value` may not be null); withdrawing; discarding a change set; batches (`bulk` is outside the ceiling); restructuring. | AG-D3's "no deletion of anything", and the exit gate. A row added by mistake is corrected by a person, or the assistant starts a new change set. |

**Scope.**

- **Migration, one file, written in one go:** `audit_events.channel`. `down_revision` and `HEAD` in `test_startup.py` are taken from the head at the moment of writing, at present AP9's `20261120_03`.
- **Management:** `mcp_tools.py` (the eleven tools, the writes flag, AG-D27's check), `routers/mcp.py` (`_run`, `_listed`, instructions saying a change reaches live data only when a person approves it), route bodies split in `change_sets.py`, `objects.py`, `relations.py`, `attributes.py`; `schemas/common.py` (`AgentOrigin`); `channel` on the two reads.
- **Engine:** `records/proposed.py`, `records/audit.py`, the `AuditEvent` column.
- **Frontend:** `AiOriginMark` and the types, one component for both kinds.
- **Documents:** API, ARCHITECTURE, OPERATIONS (AG-D8's stance and what an assistant can write), USER_JOURNEYS J53, API_JOURNEYS, CURRENT_FUNCTIONALITY, PRODUCT, PROJECT_STATUS, CHANGELOG, this plan's decision table and record.

**Mock-up (the existing record history and change-set panel; only the marked lines are new).**

```
History of "Value 12"
  [Prepared by an assistant: Claude Code]                       <- new
  Asked for by Anna Steward. Edited by Ben Owner.               <- exists (AP9)
  (the name is the one the assistant gave itself)               <- new

Change set panel, a row
  [Prepared by an assistant: Claude Code] Asked for by Anna…    <- new

A client with no application
  [Prepared by an assistant: Nightly agent]                     <- new
```

**Out of scope:** AG4; a filter for an assistant's rows; a line on the Changes page; the bounded R try (AG-D10).

**Tests, J53, through the endpoint with the SDK's client on J51's two model configurations, within the package's quarter:**

1. **The journey:** a person through an assistant creates a change set, adds five records, validates and submits; live data is unchanged; a steward has the inbox notice, edits one value and publishes; live data changes only then. History says prepared by the assistant, asked for by the person, edited by the steward, and each change-set entry has `channel` `mcp`.
2. **Four-eyes:** under `secondPerson`, the person refused the decision on what their assistant submitted; a second person approves. An agent client's token cannot reach any approve or publish route.
3. **Fixing it:** an invalid change set's submission is refused with its code and diagnostics; a stale version with `CHANGE_SET_VERSION_CONFLICT`; a submitted one with `CHANGE_SET_SUBMITTED`; a sent-back one shows the comment, and is fixed and submitted again.
4. **Limits:** a colleague's change set is not found; a person narrowed to one record type is refused on another; no tool writes without a change set; a caller with only Browse lists no change-set tool.
5. **Reads:** `find_records`, `read_record` and `describe_type` with `changeSetId` show the unpublished rows and the pinned release, and without it, live data.

`AiOriginMark` test, the frontend production build, one check in an existing browser runner at 1440px and 390px. Groups to run: J51, J52, J53, the change-set and approval groups, `contract`, `startup`, `test_boundaries`, each alone in an agreed window.

**No measurement:** no set path changes, and the column adds one value to entries already written.

**The real try:** one Claude Code session on Sonnet through the dev server, signed in as a person, in a scratch workspace, asked in words to add five missing values and submit them. It then opens in the browser for the edit and the approval. It needs the user reconnecting `/mcp` after the dev server reloads. Tokens and price are logged in the [usage log](#ai-usage-log-for-hosting-cost-planning).

**Who builds:** Sonnet from precise briefs for the tools, the route splits, the mark, J53 and the test runs; Opus for `_run`, the origin and the review.

**Working beside other sessions:** AG3 starts once AP9 has saved `proposed.py`, `audit.py` hooks, `schemas/common.py`, `AiOriginMark` and its migration, as AG3 builds on all of them. AP10 touches `imports/`, `tasks/` and the model-draft path, which AG3 does not, and adds no migration. Shared with both: documents and the OpenAPI lock, re-baselined last and diffed for AG3's additions only. `pytest` runs go one at a time across AP9, AP10 and AG3. Commits hold AG3's hunks only.

**Door check (ADR-032):** additive. A second origin kind on the value-provenance door, and a column on the audit trail. A later stdio bridge would call the same tools. No door closes.

**What the user cannot do after AG3:** have an assistant remove or clear anything, withdraw, discard, batch or restructure; have it work on a colleague's change set; filter an assistant's rows; see on the Changes page that a person's change came through an assistant; ask in words in the built-in search box (AG4).

### AG3 record (2026-10-31)

**Delivered as planned; the real try passed and the user accepted it (2026-11-01).** Tools, route splits, frontend, tests and documents built by Sonnet agents from briefs; `_run`, the origin, the channel and the review by Opus.

**Where it differs from the plan:**

- A stale version answers two codes: `CHANGE_SET_VERSION_CONFLICT` on a write, and `VERSION_CONFLICT` with `currentVersion` on a submission. Each is the engine's existing code, and J53 asserts both. Test 3 above names the first only.
- `change_record` refuses a repeated key in a list (`DUPLICATE_ATTRIBUTE`), where the update route lets the last win.
- `add_record` takes no `initialRelations` and no `id`; relationships are added with `add_relation`.
- The browser check is a small runner of its own, `test:browser:ag3`, not a check in an existing one: `ap1-ai` is about tasks.
- A mapping grid's target also accepts the new origin, as a relationship an assistant adds would otherwise fail to read.
- **A record's history shows the mark on the publication's entry only.** The entry for the write inside the change set has `channel` but no mark, as AP9's origin reaches an entry at publication. Decided: left so, as the published entry is the one that tells the record's story.

**Checks:** J53: 10 passed (five cases on two configurations; the example configuration skipped). J51 and J52: 30 passed. J42 and the two J44 files: 44 passed. `change_sets`: 479 and 2 serial passed. `contract or startup`: one failure, the OpenAPI lock, re-baselined; then `test_openapi_contract.py` and `test_boundaries.py`: 15 passed; the rest of that run's count was not recorded. The lock's diff holds AG3's `AgentOrigin`, the two `channel` fields and the origin unions, beside AP9's and AP10's own uncommitted additions. Frontend: `tsc -b`, 25 Vitest tests, `npm run build`, taken before the browser runner was added; `test:browser:ag3` 10 checks, axe 0 violations, 1440px and 390px. `feed`, run at delivery: 217 passed, one failed in the parallel run: `test_events_expired_while_active_suspend_and_a_reset_starts_from_the_head[generated-a]`. It passed four times out of four alone (both configurations each time); the cause of the parallel failure was not located. `serial and feed` selects no test, though the parallel run's footer says 14 were left out.

**The real try, first attempt:** Claude Code on Sonnet through the dev server in the scratch workspace `shape-ap-1` listed read tools only, because the dev server's worker had not reloaded since before the tools were saved. It changed nothing and said so plainly. 10 in, 942 out, 177,087 cache read, 47,340 cache written; $0.234.

**The real try, after the restart:** the same words in the same workspace. The session read the model, chose a type with no required attributes or parent, created a change set, added five records, validated and submitted, with no refusal reported. 27 turns, 47 seconds; 34 in, 4,142 out, 915,472 cache read, 39,963 cache written; $0.385.

**The person's half:** the user approved and published the change set in the browser at 01:29:39 on 2026-11-01, without editing it, and said it was good. Audit holds `channel` `mcp` on the assistant's writes and none on the publication; a published value's history, read through the assistant's tool, gives `origin` of kind `agent`, "Claude Code (refiroo)", asked by the user. The change set then answers `CHANGE_SET_NOT_FOUND`, as a published change set no longer exists.

**Not verified:** a person's edit withdrawing an assistant's submission on the real change set, as the user published without editing; Claude Desktop and claude.ai.

**What the user cannot do yet:** as under "What the user cannot do after AG3" above.

## AG4: Natural-language search

**Journey:** a steward types "values changed last month without a webshop mapping" in the search box
and sees the filters it became, editable, and the results.

**Scope.** The `queryTranslation` purpose of the AP1 provider (`structure` send level: the question
and the list's filterable fields, no record values); the answer is the existing filter parameters,
validated like a hand-typed filter, shown as chips the person edits. The engine answers; the model
only builds the query. A question it cannot express is said so, not approximated.

#### AG4 in detail (planned 2026-11-01, approved by the user the same day with the mock-up)

The user approved this plan and the mock-up (three boards: a question answered as pills, a part it cannot express, a phone) on 2026-11-01, including the extension of the list filters.

**What was found.** Today's list filters cannot say the journey's question. A relationship filter says "related to any of these records", "none" or "any", never "none **under** this record", which is what "without a webshop mapping" means: the mapped records stand under a system, and the question names the system. The query (Q3) can say it, as an `ancestor:<type>` criterion, but only on the queried record: `_related_predicate` refused an ancestor criterion inside a hop. `createdAt` and `updatedAt` filter a live list only when the view declares them, so "changed last month" is unsayable too. A question the list cannot express would otherwise end in `notExpressed` every time.

| # | Decision | Why |
| --- | --- | --- |
| AG-D33 | **Two conditions on a relationship, and two stamps, so the list and the query mean the same.** `filter.related:<key>.under=<record ID>` keeps records with some related record under that ancestor record at any depth, `.notUnder=<record ID>` those with none; each such entry must hold. They are the query's hop with an `ancestor:<type>` criterion, as set statements in PostgreSQL (`list_relation_filters` builds one hop per type the related records can stand under, each starting from the ID of that type only, so a wrong type selects nothing), live and in a change set or publication, and `_related_predicate` now accepts the ancestor criterion on its hop. The query and an export say the same with `ancestor:<type>` and `not`. The filter bar's relationship editor gets "has none under" and "has any under" with a record picker over the types the related records can stand under (read from the served placements), and a pill reads "has none under Webshop". `createdAt` and `updatedAt` filter every live table list without being declared, offered in + Filter, and not in a change set or publication, which record no times (`UNRECORDED_TIMESTAMPS`). A field with two conditions, such as the two ends of a date range, is a pill for each. No domain key anywhere. | The journey cannot be said otherwise, and a capability only the question could reach would be a defect (the API is the product). The list, selection, bulk actions and export read the one filter, so what the person sees is what is exported or changed. |
| AG-D34 | **The answer is direct, not a job** (revises AP-D8 for this purpose). `POST /api/v1/workspaces/{key}/query-translations` takes `applicationKey`, `viewKey`, `question` (at most 500 characters), `changeSetId` or `publicationId`, `sendLevel`, and answers `filters`, `search`, `notExpressed` and `applied`. It needs Browse there and Use AI proposals (`ai_requested`). It reads the model, releases its transaction, asks through `calls.ask` and holds none while the provider answers (J48.8: J54.1 reads `pg_stat_activity` from inside the call), then checks the answer in a second transaction. Table views only: another type is `422 QUERY_TRANSLATION_VIEW_UNSUPPORTED`. | One short call with nothing to batch, cancel or resume; the person waits at the box. A job would add a worker round trip and an inbox notice for a second. |
| AG-D35 | **Send level `structure`, and an offer rule of its own** (revised 2026-11-01: names of short lists at `samples` and `values`, see the revision below).** The provider is sent the question, today's date and, per field, its key, label, kind, conditions and, for a relationship, the names of the types it reaches and of the types they can stand under. No record name, value or ID. The UI offers Ask when a provider is set and the person holds ai-proposals in the workspace, at any send level (`queryTranslationOffer`, beside `aiOffer`); hidden, never disabled. It is not drawn on mapping grids, trees or Changes, which are not table views. | The question and a list's field names are the least anything can send, so every level allows it. The user's rule: hide what cannot be done. |
| AG-D36 | **A record named in words is found by the engine, in the database, in the context asked about.** The model gives a name; the engine looks among the proper types (those the relationship reaches for "is any of", those its records can stand under for under and notUnder): the exact name, ignoring case, first; otherwise the one record whose name contains it. None, or several, is a part in `notExpressed` with the reason (up to five names), never a guess. A record created in a change set is found there and not live. | The model sees no record, so it cannot choose one. A wrong guess would change a list silently. |
| AG-D37 | **Nothing is applied when any part is not expressed.** `applied` is false, the filters that could be built are still returned, and the client applies nothing: it shows the part, the proposed filters as dashed pills that do nothing and Use these filters. A sort is a part not expressed (the list's sort is a control of its own); so is a question with nothing to filter by. | The user's rule that a question the list cannot express is said so, not approximated. The person decides whether the rest is wanted. |
| AG-D38 | **(Revised 2026-11-01: the fields are also every relationship of the type.) A field or condition the list does not offer, or a value its validation refuses, makes the whole answer a failed call.** The fields are the view's `filterFields` and, live, the two stamps. Each filter then goes through the list's own validation by building the list's statement with it; a refusal marks the call recorded as answered as `failed` (kind `malformed`), and the route answers `502 QUERY_TRANSLATION_FAILED` with `details.callId`, as it does for a provider that fails. Nothing comes back to apply, and the box keeps its words. | The model's answer is data to check, never a guess to repair (AP1). The UI says one sentence (`errorMessage`) and search still works. |

The answer's filters are the list's own, so the UI applies them as `query.filters` and `search`, and the pills are the explanation (AG-D37's panel and the line "Your question became these filters. Change or remove any of them."). A person edits or removes any pill as if they had typed it.

**Scope.**

- **Engine:** `engine/reads/model_query.py` (`_under_ancestor`, the hop's ancestor criterion, `list_relation_filters` and `_under_condition`; the walk's CTE is anonymous so several ancestor criteria stand in one statement), `engine/proposals/query_translation.py` (the fields, the request, the answer's check, the lookup), `Purpose` `queryTranslation` in `provider.py` with `FEATURE_LEVELS` at `structure`, the fake's default.
- **Management:** the route in `routers/ai.py`, `QUERY_TRANSLATION` in `access.py`, `QueryTranslationRequest` and the response schemas, `FEATURE_NAMES`, the list's parameter description.
- **Frontend:** `ObjectToolbar` (the Search | Ask switch, "Asking…" with Cancel, the pills, the line, the panel), `ui/SearchField` (`onSubmit`), `RelationFilter` and `filters/FilterBar` (the two modes, a pill per condition), `useQueryTranslationOffer`, `routes.ts` and `ObjectToolbar` (the stamps), `exportRequest` and `ExportDialog` (the hop with the record's type), `model/lookup` and `model/placements` (the types a record can stand under).
- **Documents:** API, CURRENT_FUNCTIONALITY, OPERATIONS (the send level's reach), USER_JOURNEYS J54, API_JOURNEYS, UI_ACCEPTANCE, EXECUTION_GUIDE, PROJECT_STATUS, CHANGELOG, this plan.

**Mock-up** (the user's, 2026-11-01): the Search | Ask switch left of the box; the answer as ordinary pills ("Updated on or after: …", "Represented by: has none under Webshop") with the line under them; a warning panel for a part it cannot express, naming it, the dashed proposed pills and Use these filters; at 390px the switch and box full width and 44px targets.

**Tests (J54, fake provider, two configurations, no configuration's keys):** J54.1 a whole question (date and none-under filters, the list with them, the call recorded with no record value sent, no transaction held); J54.2 one filter changed and the list follows; J54.3 a part not expressible; J54.4 a record not found or ambiguous; J54.5 an invented field or condition, a refused value and a failing provider are failed calls; J54.6 hidden and refused (403, 409 twice, a view that is not a table); J54.7 a change set (no date, the other filters read it); J54.8 the new conditions live and in a change set, with an export reading the same filter. A unit test that no record value reaches the provider; Vitest for the editor's new modes, the pill per condition, the offer rule and the toolbar's ask states; the browser runner `test:browser:ag4` (both states, keyboard, axe, 1440px and 390px, on master values and system values).

**Door check (ADR-032):** no door is affected. Nothing touches identity, attribute storage, audit, bulk APIs, the consumer API `match` declaration or mapping coverage states; the two list conditions read relations and containment, and the provider sees structure only.

**What the user cannot do after AG4:** ask on a mapping grid, a tree or Changes (no package delivers it); ask for an order ("sorted by name": it is said as not expressed, and the list's sort control stays); ask who changed a record, or when a record in a change set changed (not filterable); ask a question that needs a value the list's filters do not hold; see a question's earlier answers (nothing is kept but the call record).

### AG4 record (2026-11-01)

**Delivered as planned, in a worktree beside AP11's delivery, then applied to the shared checkout in a gap between AP11's tries; the real-provider try is done.** On the OpenAPI lock, re-baselined last on top of AP11's: the document differs from AG4's own only in AP11's schemas. On the merged code: the lock, `test_boundaries` and J54, 35 passed.

**Where it differs from the plan:**

- The journey tests were written after the first backend pass, not before it, so "confirmed to fail first" was not shown.
- The ancestor of a `.under` or `.notUnder` record is not asked of the database: the list names the record by ID alone, so one hop is built per type the related records can stand under and only the right one selects anything. A record ID that exists in no type filters nothing, as an unknown ID in `eq` does.
- Two entries of one field are a pill each (a date range); a boolean field and a relationship keep one pill.
- The export dialog reads the record's type by ID before Start export is enabled, as the hop needs it; a filter naming a record whose name could not be read holds Start export.
- J48 and J49 listed one feature each; they now list two (`queryTranslation` is offered at every send level).

**Checks:** J54: 20 passed (eight cases on generated A and B). J48 and J49 with the new feature count, and the unit tests of `engine/proposals` (including the request that carries no record value): 119 passed. The `queries` and `change_sets` groups: 643 and the serial part's 2 passed (4 min 13 s on a loaded machine, over the 3-minute ceiling). The K6, K7 and export journeys the guide names for `list_relation_filters` and the candidate walk (J01.10, J01.11, J08.12, J13.9, J13.10, J03.9, J10.11, J27.6): passed. `contract` 82 passed (its serial part selects nothing), `test_boundaries`, `test_error_codes`, `test_api_reference`, `test_api_journeys`, the harness layout check and `tests/unit/test_config.py`: 200 passed. `ruff check` on the changed files. The OpenAPI lock re-baselined last and diffed against HEAD: additive (the new route and four schemas, the purpose on two schemas, the list's filter description). Frontend: `tsc -b`, `npm run lint` (0 errors), `npm run format` on the changed files, `npm run build`; Vitest for `src/features/objects`, `jobs`, `model`, `routing`, `settings`, `ui`, `api` and `vitest related` for the changed files (839 passed; one workspace test failed once under load and passed on rerun); `test:browser:ag4`: 43 checks, axe 0 violations on each state, two object types, 1440px by keyboard and 390px, the screenshots inspected against the mock-up (the phone's pill text wraps instead of being cut after the first run). Not run: the full suites, `test:a11y`, `test:visual` and the other browser runners (build acceptance). `test:browser:k6` (the filter bar's runner, named by the guide) passed, 8 checks, after its one selector for Has none was made exact (Has none under made it ambiguous); `k1`, `k2`, `k2b`, `k3` and `k5`, which the guide also names for the filter bar, then passed unchanged with axe clean (light and dark). `test:browser:ag4` was rerun on the final CSS (43 checks) and its 390px screenshots viewed: the wrapped pill text and the not-applied panel read whole and fit the width.

**Real try (2026-11-01):** `harbour`'s master values, the configured Claude Code provider, `sonnet`, two calls through the route's own `prepare` and `finish` on the dev database, not over HTTP. "values changed last month without a CRM mapping" (3.8 s by the provider's record) became the month's dates and `notUnder` the CRM record's ID, applied. "active values changed by Anna last month, newest first" (4.5 s) applied nothing, named "changed by Anna" and "newest first", and returned the three filters it could make. Two calls, $0.026 at API prices, logged below. Nothing was written but the call records.

**Not verified:** a question typed in the browser on the dev server with the real provider (the browser runner covers that path with a stand-in; the dev server answers the route, 401 without a sign-in); a person's own wording on a real model.

**What the user cannot do yet:** as under "What the user cannot do after AG4" above.

### AG4 revision (2026-11-01): the user's report on the real provider

**Closed by the user on 2026-11-01.**

The user tried the question "show me all the trains types which are above 30 minute duration" on the `default` workspace's Timetable types and was refused ("above 30 minute duration": Duration is a relationship to records named 10 min, 15 min, 30 min, 45 min, 60 min and 180 min); "values changed last month without a CRM mapping" was refused because the view does not declare the relationship to mappings. His words: "I did not expect comparison, I expect AI help ... being an AI, understand that 45, 60 and 100 are above, and add them to the filter ... Humans are working with human data." The user decided the following; it revises two decisions.

- **AG-D35 revised: names of short lists.** At send level `samples` or `values` the context also carries, for each relationship field, the record names of the types it reaches (`recordNames`) and of the types they can sit under (`ancestorNames`) when that type set holds at most 50 records in the context asked about (live, change set or publication); a longer set sends none, and at `structure` none is sent, as before. Ask stays offered at every level; `FEATURE_LEVELS` is unchanged. The names are read in one set statement per type set (`query_translation.with_names`), in the route's transaction before the provider is called, which is released before the call (J48.8 holds). The call record's `sendLevel` is the level in force, so it says whether names could have been sent. `AI_SAMPLE_VALUES` does not apply (the user's rule is the 50). No record ID is sent. J54.1, which asserts that no record value is sent, now runs at `AI_SEND_LEVEL=structure`.
- **Instructions (`query-translation/2`).** The model may choose records by understanding their names, also by meaning, with one `eq` filter per chosen record with the exact name; several `eq` on a relationship mean any of them; it chooses from the names given and never invents one. Found by the real tries and fixed in the instructions: a word naming the kind of record asked for ("trains") must not be dropped (a filter or the search), and "without" a named record a relationship's records stand under is `notUnder` with its name, not `isNull`. "Never approximate" stays for what neither fields nor names can answer. `_resolve` is unchanged: a name that several records match is still refused; no engine rule turns several matches into any-of (the user accepts how "train" then behaves; the model may choose several records from the names it was sent).
- **AG-D38 revised: every relationship.** The fields an answer may use are every relationship the listed type has in either direction (the relation's key where the type is at the `from` end of a binding, its reverse key at the `to` end; `query_translation.relationship_fields`), the view's `filterFields` and, live, the two stamps. `list_relation_filters` already accepted any relationship of the type. In the browser the address kept only declared fields, which would have dropped such a filter on reload; `parseRoute` now keeps a relationship of the listed type (`relationshipFilterFields` in `model/lookup`), and `ObjectToolbar` draws an undeclared relationship's filter, or its proposed filter, as an ordinary pill (same editor, label and remove control as a declared one) while it stands. + Filter still offers the view's declared fields. Export reads `query.filters`, which now carry it. Attributes the view does not declare stay out of scope.
- **What the user cannot do after this revision:** compare with a value that is not a record's name; ask about a relationship whose types hold more than 50 records by meaning (only an exact or partial name answers there); a relationship not declared by the view is not offered in + Filter until a question has used it.

Tests: J54.9 (names at `values`, none at `structure` or above 50, an undeclared relationship asked and filtered), a unit test of `list_fields`, `routes.test` and `CollectionView.test` for the pill and the address. Written after the backend change in this pass, not before it, so "seen failing first" was not shown.

**Real tries (2026-11-01, `default`, view `timetable-types`, `rdm-master`, send level `values`, Claude Code provider `sonnet`, through the route's own `with_names` and `finish` on the dev database):** (1) "show me all the trains types which are above 30 minute duration": `Has duration` is 45 min, 60 min and 180 min and `Belongs to category` is Follow-Up Train, Initial Train and Train Train; applied, 18 rows, which a hand query over the data confirms (200 timetable types, 42 with those durations, 18 in those categories). (2) "show me the trains types which are above 30 minute duration": the same filters, 18 rows. (3) "values changed last month without a CRM mapping": updated on or after 2026-10-01 and on or before 2026-10-31, and `Is represented by system value` has none under CRM; applied, 14 rows; the hand query agrees (200 changed last month, 200 mapped under CRM, 14 not). The first prompt left "trains" out of (1) (42 rows) and answered (3) with `isNull` (the right 14 here only because every mapped type is under CRM); both fixed in the instructions, 12 calls in all, about $0.146 at API prices, logged below. Nothing was written but the call records.

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

### AO1 in detail (planned 2026-11-01, approved by the user the same day with the mock-up)

Mock-up: [AO1 Impact summary](https://claude.ai/artifact/9cvJxd3mTPfcKE2LwtwJyv) (a Design canvas, not kept in the repository; three boards: the account beside the check, before asking and when it fails, a phone). **Requirement served:** the Outcome's "a model administrator reads a plain-language impact summary beside the activation preview".

**What the code does today (read 2026-11-01; nothing was run):**

- **The facts exist, in three places.** `GET /model-releases/{id}/diff` gives `changes` (`semantic_diff`, each a kind, a path, before and after), `compatibility` (the workspace's data against the release, whose diagnostics hold a `count` for a rule the data breaks) and `consumerContracts`. `POST /model-drafts/{id}/compile` gives the same for a draft. Diagnostics name keys, not record values.
- **The activation dialog shows no list of operations.** The spec says "beside the counts and the list of operations", but `ActivateDialog` shows only the compatibility notice and the contract notice. `ApplyDialog` shows `summarizeChanges`. A citation therefore has nothing to link to in the activation dialog until AO1 draws the facts.
- **No count exists for a compatible change.** "None of its 340 records changes" has no source: compatibility counts only records that break a rule.
- **The model has no mappings section.** A mapping in a release is a relationship (`objectTypeRelations`) or an application's view. A saved model mapping (`model_mappings`) stands between two models outside any release, so a release does not change it.
- **0.15 is not built.** `frontend/package.json` holds no translation library and no language is sent on a request, so AO-D8's "0.15's setting passed to the request" has nothing to pass.
- **`ai_requested`, `calls.ask` and `FEATURE_LEVELS` serve this as they stand.** AG4's route shows the pattern: read, release the transaction, ask, then check the answer.

**Decisions (recommended, approved with this plan):**

| # | Decision | Why and what it costs |
| --- | --- | --- |
| AO-D10 | **Two direct routes, no job.** `POST /api/v1/model-releases/{id}/impact-summary` and `POST /api/v1/model-drafts/{id}/impact-summary`, with `workspaceKey`, optional `sendLevel` and `language`; the release's route compares with the release the workspace runs, the draft's route also takes `expectedVersion`. An invalid draft is `422 IMPACT_SUMMARY_DRAFT_INVALID`. No transaction is held while the provider answers. | One short call with nothing to resume, as AG-D34. Revises AP-D8 for this purpose. |
| AO-D11 | **The answer always carries every fact.** `facts: [{id, kind, text, path, count}]`, `statements: [{text, factIds}]`, `removedStatements`, `failure`, `cached`, `callId`. A provider that fails or answers out of shape is a `200` with `statements` empty and `failure` set, not a `502`. | AO-D9 asks for "facts alone" on a failure, so the route still has something true to give. Differs from AG4, where a failed call had nothing to show. |
| AO-D12 | **A fact's text and ID come from the engine.** Kinds: `change` (one per diff entry), `data` (a compatibility diagnostic with its count), `contract` (a contract diagnostic), `blocked` (a diagnostic that refuses the activation) and `records` (records per touched type). The ID derives from kind, code and path, so the same fact keeps its ID. The text is built from the model's labels. | The reader checks the sentence against a line the AI did not write. `count` per touched type is one new `GROUP BY` over the workspace, whole set (AO-D3). |
| AO-D13 | **"Mapping changes" are relationship and view facts.** No separate kind, and saved model mappings stay out. | That is what a release can change, as found above. The sentence in the journey still reads as written, since a relationship's fact names its types. |
| AO-D14 | **The provider gets at most 40 facts per kind, each with its true count; the person gets all.** The largest counts and blocked items come first; the rest is "and N more" in the context, and a statement may cite the group. | AO-D3. A release of another model can hold hundreds of changes. Text in `before` and `after` is cut at 200 characters in the context and sent as it stands in the model. |
| AO-D15 | **The cache is a small table.** `ai_summaries`: `purpose`, `input_hash` (unique), `answer` JSON, `call_id`, `expires_at`, one hour on. The hash covers the facts, language, send level, provider, model and prompt version. A hit makes no call and returns `cached: true`. Expired rows are removed in one statement when a row is written. Migration: one table. | AO-D4's "same facts, same text, no second call" must hold across worker processes, which an in-process cache cannot. One hour is the preview's session in AO-D4. AO2 and AO3 reuse it. |
| AO-D16 | **No new permission group.** AO-D5's "second action" would not be separately grantable, as grants are by group, so a holder of `model.activate` in the workspace who also holds Use AI proposals may ask. The group's description gains "and summaries". Hidden otherwise. | Grants are by group (ADR-044), so a second action changes nothing a person can see. The roles that hold Model release already hold the group. |
| AO-D17 | **One component, only on request.** `ImpactSummary` in `features/model-admin`, in `ActivateDialog` and `ApplyDialog`, after the compatibility notice. Nothing is sent until the person presses **Explain this change**; the line beside it says what is sent. A new check clears the account. | A dialog opening must not spend money or send anything. One component, no copies. Facts appear only after asking, so with no provider the dialogs are as they are today (AP-D3: hidden). |
| AO-D18 | **The prompt says what the facts are and never judges.** It asks for short statements in the given language, each citing fact IDs, and forbids "safe", "risky" and advice. A check drops a statement with no valid ID (AO-D2). It does not scan words: the wording rule rests on the prompt, the citations and the note under the account. | Filtering words would give false comfort in any language. "Written by AI … It can be wrong" stays under the account. |
| AO-D19 | **`language` is optional in the API and the UI sends none until 0.15 is built.** The default is English. A German account beside English facts is left for when 0.15 converts these dialogs. | Changes AO-D8's route to it, not its aim: an integrator can already ask for a language. |
| AO-D20 | **One bounded real try in this package, not in R.** It changes AO-D9's "in R". | AG4's real problems appeared only on a real provider, and it is one short call. |

**Journey cases (for approval, J55, fake provider, on two model configurations):**

- **J55.1 The account.** Given a release adding two optional attributes and a consumer change, when a model administrator asks, then each statement cites facts, the facts equal what the diff, the check and the database give, and the call is recorded.
- **J55.2 A draft.** The same from a draft in Apply; an invalid draft and a stale `expectedVersion` are refused.
- **J55.3 Whole set.** Given more than 40 changes of a kind, the response holds every fact, the context 40 and the true count, and the record count equals a count taken directly (AO-D9's completeness test).
- **J55.4 No source.** An answer with an uncited or unknown citation loses that statement and counts it; with none left, the facts stand alone.
- **J55.5 The provider fails.** A failure and an out-of-shape answer each give `200`, the facts, `failure` and a failed call record, and no transaction is held during the call.
- **J55.6 Same facts.** A second request makes no provider call and says `cached`; a changed record count makes a new call.
- **J55.7 Blocked and migration.** A release needing a migration gives `blocked` and `data` facts with counts, and nothing in the workspace changes.
- **J55.8 Who may ask.** Without Model release in that workspace, or without Use AI proposals: `403`. No provider: `409 AI_NOT_CONFIGURED`. A chosen level above the ceiling: `409 AI_SEND_LEVEL_TOO_LOW`.

Unit tests: no record value in the context at `structure` (a stored value planted and looked for), fact IDs stable between two runs, the bound of AO-D14, the cache's hash. Vitest: `ImpactSummary` in each state, hidden without the offer, cleared by another release.

**Real try, announced and run without a stop.** The provider in `.dev/settings.env` (Claude Code, `sonnet`), on an existing pair of releases of a scratch workspace, with one activation and one migration-needing release. Read by me for statements that judge or that the facts do not carry; tokens and cost in the usage log. The 200 and 2,000-record basics are timed for the fact set.

**Browser:** one runner on two configurations with the fake provider: asking, citation to fact, failure, Show the rest, in both dialogs, by keyboard at 1440px and 390px, light and dark, axe, no 5xx. Screenshots inspected.

**Checks:** J55, the activation journeys' group as the execution guide names it, `contract` with the OpenAPI lock (re-baselined last, diff read for AO1's additions only), `test_boundaries`, the migration's upgrade, Ruff on the named files, Vitest for `features/model-admin` and `ApplyDialog`, lint, the production build. **Door check (ADR-032):** none affected: a summary is derived and stays outside history, the model and the records.

**Scope.** **Engine:** `engine/proposals/impact_summary.py` (facts, context, prompt, answer check), `impactSummary` in `Purpose`, `FEATURE_LEVELS` at `structure`, the fake's default, the cache in `calls.py`'s neighbourhood. **Management:** the two routes, schemas, `FEATURE_NAMES`, `AiCallResponse`'s purpose, the group's description. **Frontend:** `ImpactSummary`, `useImpactSummaryOffer` in `useWorkspaceAiOffer.ts`, the two dialogs, `api`, types. **Documents:** `API.md`, `API_JOURNEYS.md`, `USER_JOURNEYS.md` (J55), `CURRENT_FUNCTIONALITY.md`, `OPERATIONS.md` (the send level's reach), `UI_ACCEPTANCE`, the execution guide, `PROJECT_STATUS`, `CHANGELOG.md`, this plan, the usage log.

**Working beside other sessions.** **AP12 is in delivery or about to be:** both touch `ActivateDialog` and `ApplyDialog`. AO1 adds one component call and one state to each and stays out of opening with choices and the way back to the task; whichever comes second takes the other's saved file. AO1 does not touch `agent.py` or `MigrationPage`. Shared: this document, `CHANGELOG.md`, `useWorkspaceAiOffer.ts` (one added function), the OpenAPI lock, re-baselined last. AO1 alone adds a migration, written in one go as the dev server applies it on save. `pytest` runs go one at a time. Commits hold AO1's hunks only.

**What the user cannot do after AO1:** read the account in German (0.15, not built); read it on the migration preview page, which lists every conversion and loss itself, and the account stands in the dialog before it (no package); read it in the install dialog, which belongs to no workspace, so nothing there changes data (no package); keep an account, as it is gone after an hour and is not part of a release (AO-D4); ask a follow-up question (not a chat, AO-D7).

### AO1 record (2026-11-01)

**Delivered as planned**, with the differences below. The tests were written after the first backend pass, not before it, so "confirmed to fail first" was not shown.

**Where it differs from, or fills, the plan:**

- **Which models are compared.** A release is compared with the release the workspace runs; a draft with the release it is based on (the newest of its model without a base), as its compilation is. The workspace's data is checked against the candidate by `analyze_compatibility` against the workspace's own release in both routes, so a draft whose base is not what the workspace runs is compared in two ways, each as the dialogs already draw it.
- **The kinds, fixed.** `blocked` is one fact per cause that refuses activation (the data needs a migration; a consumer API changes without a higher contract version), without a count; each compatibility diagnostic is a `data` fact with its count; each contract diagnostic is a `contract` fact, whatever its severity. AO-D12's "(a diagnostic that refuses the activation)" left this open: J55.7's "blocked and data facts with counts" is met this way.
- **Facts the provider is not sent are still citable.** `more-<kind>` stands for a kind's facts beyond 40; the check accepts it, and the interface leads it to the first fact of that kind.
- **No facts, no call.** A release with no difference to describe answers with no facts and statements and makes no provider call.
- **All statements dropped is not a failure.** `failure` stays empty; the interface says no statement cited a fact and shows the facts. The account is cached only when a statement survived.
- **The draft route exists only where model drafts do** (`MODEL_ADMIN_MUTATIONS_ENABLED`): it is on its own router (`draft_router`), included beside `model_management`, so the OpenAPI document without model administration has none; the release's route is always there.
- **The interface.** `ImpactSummary` takes what to ask and is keyed by the check, so another release, workspace or draft version clears it. Ten facts are listed, then "Show the other N". A number is the fact's place in the list.
- **Mock-up.** The provider's name stands in "by <provider>"; the "Not changed" and "Change sets left" lines stay where the dialogs have them, the section sits after the check's notices.
- **After the real try (`impact-summary/2`).** The account said facts were "not shown" (the provider's view, not the reader's), counted a list wrongly once ("seven … eight in total") and one fact read "changes from its definition to its definition". The prompt now says "and N more" and to take numbers from the facts and totals, the group's text no longer says "not shown", and a change of a definition reads "changes". Not tried again on the real provider (one try, no loop).
- **The browser runner's stand-in.** `e2e/helpers/ask_stand_in.py` also answers `impactSummary` by a mode a file names (`STAND_IN_MODE_FILE`), because the fake provider cannot be scripted from another process.

**Checks:** J55: 18 passed (eight cases on generated A and B, plus the no-provider case), and `tests/unit/engine/proposals` with the new unit cases: 6. J48 (12 passed) and J49 with the third feature (the feature lists now name three). `test_j54_ask_in_words`, `contract` (82 passed; the OpenAPI lock re-baselined last, hash `bb33dcfd…`: the lock's document held AP12's schemas (`TaskMigration` and changes to `TaskDesign` and `TaskResult`) when it was re-baselined, so AP12 re-baselines it again; diffed against HEAD, AO1's additions are the release route, the five schemas and `impactSummary` in two enums, the draft route being in the model-administration document only), `test_boundaries`, `test_error_codes`, `test_api_reference`, `test_api_journeys` (the new routes and code listed), `test_startup` (11 passed: the head is `20261121_01`, a clean bootstrap and the upgrade from `20261120_04`; the dev server applied the migration on save). The `workspace_models` group and J08: 162 passed and 30 passed, **2 failed**: `test_j36_12_workspace_draft` (an assistant task refused `AI_NOT_CONFIGURED`, `AI_AGENT_COMMAND`), the file untouched by AO1 and in AP12's area. Ruff on the changed files. Frontend: Vitest for `features/model-admin`, `ApplyDialog`, `features/settings` and `features/security` (222 passed; `ImpactSummary.test` has 7 cases: hidden, the line, the account and a citation landing on its fact, a removed statement, failure and Try again, ten facts then the rest, a refused request, a new check clearing it; `impactSummaryOffer` in `useWorkspaceAiOffer.test`), `npm run lint` (0 errors), `npm run format` on the changed files, `npm run build`. Browser: `test:browser:ao1`, 37 checks on the starter and generated-b (axe 0 violations on each state, light and dark, 1440px by keyboard and 390px, no console error or 4xx/5xx); screenshots inspected against the mock-up. Not run: the full suites, `test:a11y`, `test:visual`, the other runners.

**The 200 and 2,000-record basics.** On generated A and B, with 0, 200 and 2,000 more records of the touched type (created through `POST /batches`), the whole route with the fake provider (the diff, the check of the data, the contract check, the grouped count and the facts) took 17 to 25 ms at 200 and at 2,000 records, 18 to 43 ms with none: the counts are set statements, so the time does not follow the records. The record fact equalled the number added each time, and the check's counts equalled it for the release that made an attribute required.


**Not verified:** an account in the browser on the dev server with the real provider (the runner uses a stand-in; the dev server answers the route behind a sign-in); a person's wording of a German account (0.15 is not built); the prompt `/2` on the real provider.

**What the user still cannot do:** as under "What the user cannot do after AO1" above.

**Collisions with AP12:** none in the dialogs (only AO1's hunks stand in `ActivateDialog` and `ApplyDialog`); the OpenAPI lock hash carries AP12's schemas (above); `test_j36_12_workspace_draft` fails in AP12's area.

## AO2: What changed, an account of history

**Journey:** a data owner picks "last week" on a workspace; the account says "Translations: 200
labels changed by 3 people, 190 of them in one bulk import on Tuesday; Master: 4 values retired; one
change set (CS-18) was sent back", each statement linking to the records and the change set.

**Scope.** Fact aggregates from history and the change feed, grouped in PostgreSQL by type, kind,
actor and source (job, change set, direct), restricted to what the requester may read; the
`historyAccount` purpose; the panel and the route (AO-D7). Send level `structure` for counts and
groups, `values` to name records.

### AO2 in detail (planned 2026-11-01, approved by the user the same day with the mock-up and AO-D21 to AO-D23 as recommended)

Mock-up: [AO2 What changed](https://claude.ai/artifact/J1cg6aHNt4YNqGoJiKd1Fj) (a Design canvas, not kept in the repository; four boards: the workspace's Activity, before asking and when it fails, a record's history, a phone). **Requirement served:** the journey above, and AO-D1 to AO-D9.

**What the code and the dev database hold today (read 2026-11-01, read-only queries, no server started):**

- **The audit holds staged and live work side by side.** On the dev database, of 261,417 entries, staged record entries (`change-set-object`) number 116,940 and live record entries with a feed position 22,556. A published record has both, so counting every entry counts it twice. `GET /changes` returns both under the `record` kind, so the Activity list mixes them too.
- **Most bulk work reaches live data as a publication, not a job.** Live record entries by cause: 20,012 `publication`, 2,499 `job`, 45 direct. A publication's entries name who published; who prepared it stands only on the staged entries, whose job is in `cause_id` and whose change set is in `changes->>'changeSetId'`.
- **Deleted records keep no name, and attributes are named in two shapes.** A record's name is read now from `rdm_objects`, so a deleted one has none. An entry names attributes by `attributeTypeKeys` or by the keys of `attributes`; the latter holds values, so the facts read only its keys.
- **Reads are per workspace (ADR-044).** AO-D5's "filtered by what they may read" is therefore Browse in that workspace; no narrower read exists to filter by. The dev database holds only two `updated` entries caused by a publication, both naming only `name`, so how a published attribute change is recorded is checked by J56.1, not by this data.
- **Jobs are removed after `JOB_RETENTION_DAYS` (7 by default);** the audit is not. An import's parameters hold its `file`. A job older than that has only its ID left in the audit.
- **Grouping is fast.** The largest workspace's 40,085 entries, grouped by aggregate, action, type, cause, actor and day: 100 ms, once, on the existing workspace index. It does not yet unpack attribute keys.
- **`impact_summary.py` holds what AO2 needs,** `explain`, `checked`, `Fact`, `Statement`, `Summary`, tied to its purpose. `summaries.py` holds the cache, as AO-D15 foresaw.

**Decisions (recommended, approved with this plan):**

| # | Decision | Why and what it costs |
| --- | --- | --- |
| AO-D21 | **Counts are of live data.** A record, relationship or field count reads only entries with a feed position. Work in an open change set appears only as that set's events (created, submitted, sent back, approved, discarded). The facts' heading says "live data". | Otherwise a published record counts twice (found above). Cost: edits still sitting in an open change set are not counted, only that the set exists and what happened to it. |
| AO-D22 | **A publication says who prepared it.** A `source` fact for a publication reads its change set's staged entries in one grouped statement: the jobs and the people that prepared it, beside who published. `people` counts direct live changes and that preparation, as "changes". | The journey's "by 3 people, 190 in one bulk import" could otherwise almost never be said, as most bulk work reaches live data as a publication. Cost: one more grouped read over the workspace's entries, timed in the basics. |
| AO-D23 | **Names go out only at `values`.** At `structure` the provider gets counts and the model's labels, and no name of a record, person, change set or file. The reader's fact lines always show them, as Activity does. | Those names are free text and personal data. Narrows AO-D1, which lists "actor" among what is sent. Cost: at `structure` an account says "one change set was sent back" and the citation names it. |
| AO-D24 | **Two direct routes, no job.** `POST /api/v1/workspaces/{key}/history/account` and `POST /api/v1/objects/{objectTypeKey}/{id}/history/account`, with `since`, `until` (included, not included, as `/changes`), optional `timeZone` (for "on Tuesday"; UTC by default), `sendLevel`, `language`. No period limit. `422 HISTORY_PERIOD_INVALID` for an empty or reversed period or an unknown time zone. Needs Browse and Use AI proposals in the workspace; hidden otherwise. | Revises AO-D7's "job when the period is large", on the measure above, and as AO-D10. If the basics show otherwise it goes in the record, with the figures. A record's account reads through `audit_event_subjects`. |
| AO-D25 | **Fact kinds:** `records` (per type and action, distinct records), `fields` (per type and attribute), `relationships` (per relation type and action), `source` (per job, publication or "made directly", with its day), `people`, `changeSet` (each set's events), `publication` (a withdrawal), `model` (an activation in the workspace). A mapping's `transition` summaries stay out, as in `/changes`. IDs derive from kind and keys, text from the model's labels. At `values`, a `records` fact names up to 10 live records, with "and N more". | AO-D3 and AO-D12. Group facts are bounded by the model and the period, not by a cap. The provider gets at most 40 per kind (AO-D14). |
| AO-D26 | **What is shared moves, once.** `explain`, `checked` and the fact, statement and summary types move to `proposals/summaries.py`, taking instructions, context and purpose; AO1's behaviour stays, and J55 is rerun. The component's core moves out of `ImpactSummary` and both accounts use it. | One component, no copies. AO1's prompt version does not change. |
| AO-D27 | **Citation to fact, fact to the changes.** A fact carries a `link`: a record, a change set, a publication, a job, or a narrowing of the list. **Show them** narrows Activity in place under `ScopeBanner`, or filters a record's timeline by kind and person. `GET /changes` gains `objectTypeKey`, `causeId` and `live=true`, whole set, additive. A removed job has no link and says "a job, since removed". | The journey asks for links to the records. `live` is needed so the narrowed list is what the fact counted. Cost: one more filter set, on the JSON `subject`, within the workspace's rows. |
| AO-D28 | **The facts through the AG2 tools, not the account:** a `history_facts` tool returns the engine's facts for a workspace or a record over a period, with no provider call, and needs Browse only. *(Revised 2026-11-02, approved by the user: the first wording, a `history_account` tool, could never be offered, as an assistant's token is cut to Browse and Work in change sets, AG-D15.)* | AO-D7. The assistant words the facts itself; the agent ceiling is unchanged. Cost: one tool, and no provider account through an assistant. |
| AO-D29 | **Only on request.** The section sits above the Activity filters and on the record's History panel. Nothing is sent until **Explain this period**; the line beside it says what goes, at the level that applies. Default period: 7 days for a workspace, 30 for a record. An empty period makes no call and says so. | As AO-D17. Cost: without a provider the facts are not shown either (AP-D3), as in AO1. |
| AO-D30 | **`language` as AO-D19. One bounded real try here,** as AO-D20. | The same reasons. |

**Journey cases (approved, J56, fake provider, on two model configurations):**

- **J56.1 The account.** Given direct changes, a job and a change set published in the period, when a holder of Browse and Use AI proposals asks, then each statement cites facts, and the counts per type, field and source equal counts taken directly from the changes made.
- **J56.2 Not counted twice.** A record staged then published counts once; an open change set's edits are not counted, and its events are.
- **J56.3 Who prepared it.** A change set loaded by an import and edited by a second person, published by a third: the `source` fact names the job and the two, and the publisher.
- **J56.4 A record.** The same for one record, with values, relationships and moves, and no other record's changes.
- **J56.5 Names by level.** At `structure` no record, person, change set or file name is in what the provider receives (each planted and looked for), though the facts hold them; at `values` they are, with a record's name labelled as data.
- **J56.6 The period.** `since` is included and `until` is not; an entry on either side of a day boundary falls on the right day in the given time zone; a reversed period is `422`; an empty period gives no facts and no call.
- **J56.7 Whole set.** More than 40 facts of a kind: the response holds all, the provider 40 with the true count. **Show them**'s filter returns what the fact counted, through `GET /changes`.
- **J56.8 No source, failure, same facts.** As J55.4 to J55.6: an uncited statement is dropped and counted, a failure is a `200` with the facts, a second request is `cached`.
- **J56.9 Who may ask.** No Browse in that workspace or no Use AI proposals: `403`. No provider: `409 AI_NOT_CONFIGURED`. A level above the ceiling: `409 AI_SEND_LEVEL_TOO_LOW`. Asking changes no record and adds no audit entry. The `history_facts` tool, on an assistant's token: offered with Browse, refused for a workspace it cannot read, returns the same facts as the route for the same period, and makes no provider call.

Unit tests: both attribute shapes give the same field count with no value read; fact IDs stable between two runs. Vitest: the section in each state, hidden without the offer, a citation landing on its fact, the period reset clearing the account.

**Real try, announced and run without a stop.** Claude Code (`sonnet`, `.dev/settings.env`), three calls through the route's own steps on the dev database, read only but for the call records: a large workspace with publications, one with jobs, one record. Read by me for statements the facts do not carry; tokens and cost in the usage log. The 200 and 2,000-record basics are timed for the fact set, and the largest dev workspace once.

**Browser:** `test:browser:ao2`, the stand-in of AO1's runner, on two configurations: asking, citation to fact, **Show them** and its banner, failure and Try again, an empty period, the record's panel; 1440px by keyboard and 390px, light and dark, axe, no 5xx. Screenshots inspected against the mock-up.

**Checks:** J56, J55 and `tests/unit/engine/proposals` (the move), J44 (`test_j44_changes`) for the new filters, `contract` with the OpenAPI lock (re-baselined last, diff read for AO2's additions only), `test_boundaries`, `test_error_codes`, `test_api_reference`, `test_api_journeys`, Ruff on the named files, Vitest for `features/model-admin`, `features/workspaces`, `HistoryPanel`, `features/changes`, lint, format on the changed files, the production build. **Migration:** none (`ai_summaries` and the call log hold it). **Door check (ADR-032):** audit is read, not changed, and `/changes` only gains filters; no door affected.

**Scope.** **Engine:** `engine/proposals/history_account.py` (facts in set statements, context, prompt), `summaries.py`, `historyAccount` in `Purpose`, `FEATURE_LEVELS` at `structure`, the fake's default; `engine/reads/changes.py`. **Management:** the routes, schemas, `FEATURE_NAMES`, `AiCallResponse`'s purpose, the tool in `mcp_tools.py`, `/changes`' filters. **Frontend:** the shared account component, `WhatChanged`, `useHistoryAccountOffer`, `WorkspaceActivity`, `HistoryPanel`, `api`, types. **Documents:** `API.md`, `API_JOURNEYS.md`, `USER_JOURNEYS.md` (J56), `CURRENT_FUNCTIONALITY.md`, `OPERATIONS.md` (the send level's reach), `UI_ACCEPTANCE`, the execution guide, `PROJECT_STATUS`, `CHANGELOG.md`, this plan, the usage log.

**Working beside other sessions.** **AP12 is running.** It holds `agent.py`, `schemas/ai_tasks.py`, `features/ai-tasks` and the model editor; AO2 touches none of them. Shared: this document, `CHANGELOG.md`, the API and journey documents, `useWorkspaceAiOffer.ts` (one added function), the OpenAPI lock, re-baselined last by whichever finishes second. `pytest` runs go one at a time. `test_j36_12_workspace_draft` fails in AP12's area, and is not AO2's. Commits hold AO2's hunks only.

**What the user cannot do after AO2:** read the facts with no provider set up (AP-D3); see counts of edits still in an open change set (AO-D21); read a deleted record's name, which the audit does not keep; follow a job older than `JOB_RETENTION_DAYS`, or read its file's name; read the account in German (0.15, not built); keep an account or ask a follow-up (AO-D4, AO-D7). None has a package.

### AO2 record (2026-11-01)

**Delivered as planned**, with the assistant's tool as revised (below). The journey cases J56.1 to J56.9 were written first and confirmed to fail (20 failed, the route being absent) before the code; the cases were not altered, apart from the tool clause of J56.9, reworded with AO-D28 and met by the `history_facts` tool (2026-11-02).

**A spec gap, decided 2026-11-02: AO-D28 revised to a facts-only tool.** An assistant's token is cut to the `agent` role's groups, Browse and Work in change sets (`AGENT_CEILING`, AG-D15), so it can never hold Use AI proposals; the planned `history_account` tool would never be offered. The user approved the recommendation: a `history_facts` tool that returns the engine's facts with no provider call, needing Browse only, so the ceiling is unchanged. J56.9's tool clause was reworded to match and is met: `history_facts` (`mcp_tools.py`) builds its scope, period and facts through the shared `management/history_account.py` (`facts_only`, `fact_models`, which the route's `account` also uses), answers `HistoryFactsResponse`, has no page size (an answer past `MCP_ANSWER_BYTES` is refused as any answer that is no page) and makes no provider call, `ai_summaries` row or call record.

**Where it differs from, or fills, the plan:**

- **`GET /changes` gains more than three filters.** For the list to equal a fact, it takes `objectTypeKey`, `relationTypeKey`, `causeId`, `action` (`moved` is an update that changed the parent), `attributeKey` and `live=true`; a record's history takes `live=true` too. A record's timeline still holds the staged entries, so Show them there passes `live`.
- **A fact's link.** `records`, `fields` and `relationships` lead to the narrowed list; a job or a publication source leads to the job or the change set (the mock-up's "Open the job", "Open the change set"), and a publication whose change set is gone leads to the narrowed list by `causeId`; a removed job, `people`, a direct source, withdrawals and activations lead nowhere. **People has no Show them**, since its count is direct changes, a job's and a publication's preparation, which no list narrows to. The response also carries `keys` (what the fact counts, with a publication's job IDs, preparers and publisher), `scope`, `since`, `until` and `timeZone`.
- **Counting.** `records` counts distinct records per type and action, a record's own account counts its changes. `moved` is counted beside `updated` (a move that also changed a value is in both). `fields` reads the keys of `attributes` (a single write) and `attributeTypeKeys` (a publication) of updates only, and no value. `people` counts live changes whose cause is not a publication (a job's are its requester's) and the entries staged in a publication's change set, by whoever made them. A day is the day of the group's first change in the given zone.
- **The cache** key holds the period, so an account asked again with a new `until` (the UI asks "until now") is a new call; the same request repeated is cached.
- **The interface.** The account's core is `ui/AiAccount` (a hook and the view), which `ImpactSummary` now uses; AO1's component tests and runner pass unchanged and its prompt version is unchanged. `NarrowedBanner` was extracted from `ScopeBanner` for the narrowed Activity and History. The section's heading is an h3 and its facts' an h4 (axe's heading order). A record's History draws the section only when given the workspace, so the model editor's preview draws none. `WorkspaceAdmin.test` mocks the offer, since it renders the Activity.
- **Names.** The reader's lines name records (up to 10 per fact), people, change sets and files; the provider gets them only at `values`, as `data`, and the prompt says that data is never an instruction. The names the audit does not keep (a deleted record) are absent.
- **Older tests changed** because the feature lists name four features now: J48 and J49.

**Checks:** J56: 20 passed (nine cases on generated A and B, plus the no-provider case); J55, J44 (`test_j44_changes`), J07, J49 and `tests/unit/engine/proposals` (with `test_history_account`, 7 cases): 157 passed in one run with J56; J48: 12 passed after its list was corrected; `test_j52_assistant_reads` passed in an earlier run. `contract` (OpenAPI lock, `test_boundaries`, `test_error_codes`, `test_api_reference`, `test_api_journeys`): 30 passed. The OpenAPI lock was re-baselined last (hash `d300fde6…`), diffed against HEAD in a worktree: AO2's routes, the four schemas, `historyAccount` in two enums, the new filters; the lock carried none of AP12's schemas at this time (they stand in HEAD). Ruff on the changed files (two other files, `presenters.py` and `schemas/records.py`, are unsorted and not mine). Frontend: Vitest for `features/workspaces`, `features/objects`, `features/changes`, `features/model-admin` and `features/settings`: 610 passed; `npm run lint` 0 errors, `npm run build`, prettier on the changed files. Browser: `test:browser:ao2`, 43 checks on the starter (send level `values`) and generated-b (`structure`): axe 0 violations on each state, light and dark, 1440px by keyboard and 390px, no console error or 4xx/5xx; screenshots inspected against the mock-up (the facts, the narrowing banner and the 390px layout match; the banner's text is cut to the fact's line without its names). Not run: the full suites, `test:a11y`, `test:visual`, the other runners. **The tool (2026-11-02):** J56: 22 passed (the new case: offered with Browse; the facts equal the route's for a workspace and for a record in a time zone; a workspace it cannot read, a missing record, a reversed period and an unknown zone refused; no provider call, call row or audit entry added); `test_j52_assistant_reads`: 14 passed; `contract`: 82 passed, the OpenAPI lock unchanged. Ruff on the changed files.

**The 200 and 2,000-record basics.** On generated A and B, a batch job creating 200 or 2,000 records, and a change set of the same size loaded by a second job and published, then the whole route with the fake provider (every fact, including the preparation read of the publication, the grouped counts and the response): 16 to 19 ms at 200 and 63 to 83 ms at 2,000 records. The `records` fact counted exactly 400 and 4,000. **The largest dev workspace** (`ap10-run`, 40,085 entries, 20,040 live, the whole of 2026): the facts in 204 ms, once; `another-2` in 161 ms. AO-D24's "no job" holds.

**Real try (2026-11-01)**, the Claude Code provider (`.dev/settings.env`, `sonnet`, send level `values`), three calls through the route's own steps on the dev database, no HTTP: (1) `ap10-run` for 2026, 20 facts, 6 statements in 5.9 s; (2) `another-2` (jobs: a move job and batch jobs), 37 facts, 6 statements in 8.3 s; (3) one record of `default`, 3 facts, 3 statements in 3.9 s. Cache rows removed after. **Read by me:** no statement judged; every number is in a fact. **Wrong or not carried by the facts:** (2) said the publication was "prepared by one job (Move job) from the change set 'Move from default'", while the facts name two change sets and the publication's is "Move from default (9b9b…)"; it also said records "were created and also deleted in matching numbers", which the equal counts show but no fact states; (1) said "all 20039 changes were made by 1 person", reading the people fact's preparer count as authorship. Not changed in the prompt (one try, no loop). Tokens in 10,929 (6 plain, 8,467 cache write, 2,456 cache read), out 1,541, $0.051 at API prices, logged above.

**Not verified:** an account in the browser on the dev server with the real provider (the runner uses a stand-in; the dev server answers behind a sign-in); an account in German (0.15 is not built); the prompt `history-account/1` beyond the three calls; a period of a published attribute change on the dev data (the dev data holds none: the cases J56.1 and J56.2 cover it).

**What the user still cannot do:** as under "What the user cannot do after AO2" above, and have the provider word an account through an assistant's tool: `history_facts` gives an assistant the facts and the assistant words them (AO-D28 as revised).

**Collisions with AP12:** none in files; the OpenAPI lock carried nothing of AP12's in the diff; `test_j36_12_workspace_draft` was not run (AP12's area). `ApplyDialog` and `ActivateDialog` were not touched. The shared documents (`CHANGELOG.md`, this plan, the API documents, the execution guide) hold AO2's hunks beside AP12's.

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

Provenance (`origin`, AP-D5, and AP9 for a session's changes) is the first use of the value-provenance door and is additive, kept
outside a record's own values. Audit gains a `channel`, additive. Identity, attribute storage, bulk
APIs, the consumer API `match` declaration and mapping coverage states are read or reused, not
changed. Summaries (Track O) are derived and stay outside history, the model and the records. No door
closes.

## Tests

Journey-driven through the API, at most about a quarter of a package. Track P and O use a deterministic
fake provider (AP-D11, AO-D9): per package the happy journey, the provider-failure journey, the
permission-hidden journey, and where data is read a send-level journey; Track O adds the
uncited-statement, the visibility and the fact-completeness tests. Track A uses a test MCP client
(AG-D10). The context builder's level tests are unit tests. A session is tested with a scripted command (J50.30). Execution-guide groups for the changed
boundary only; the OpenAPI lock re-baselined per package and marked additive.

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
| 2026-10-31 | AG3, first attempt: an assistant asked to prepare a change, before the dev server had reloaded | Claude Code session, `sonnet` | 1 session | 10 / 47,340 / 177,087 | 942 | not recorded | $0.234 | saw read tools only, changed nothing and said so |
| 2026-10-31 | AG3 after the restart: the same words; five records prepared, validated and submitted | Claude Code session, `sonnet` | 1 session, 27 turns | 34 / 39,963 / 915,472 | 4,142 | 47 s | $0.385 | published by the user; see the AG3 record |

**What a hosting estimate needs from these rows:** the cost per task kind (e.g. loading one workbook of
N rows and M sheets), how it grows with the file (the reading is sent as column profiles, so it grows
with columns and distinct values, not with rows), and how much prompt caching saves on repeated turns.

## R: Build acceptance and release

Full review of every change since 0.15 (it is one review for three tracks, the main saving of merging);
the contract lock marked additive (the `agent` audience, `/mcp` and the new routes); documentation
(PRODUCT, CURRENT_FUNCTIONALITY, ARCHITECTURE, OPERATIONS for the AI and MCP settings and connecting an
assistant, API, USER_JOURNEYS, API_JOURNEYS, PROJECT_STATUS, CHANGELOG); **one** bounded real-provider try and **one** real-assistant try,
each only on the user's go-ahead with its cost stated first (AP-D11, AG-D10); the release.

## Exit gate

- A few words and a workbook give the model and the import, with as many applications, types and
  relations (across applications too) as the workbook needs; tried on the user's own workbooks (AP-D22).
- With no provider and MCP off, no screen shows an AI action, no request leaves the instance, `/mcp`
  does not exist, the existing inference behaves as before, and digests are the plain list.
- No value above the configured send level reaches a provider (the context builder's tests).
- Every proposal refers to an existing record or valid step and passes the validation of a hand edit;
  it can be edited, kept or removed with existing tools; every accepted one, a session's changes included, is recorded as
  machine-proposed with who asked and who approved (AP9).
- An agent token works on `/mcp` only; no tool approves, publishes, withdraws, administers the model or security,
  or deletes; an agent's change set leaves live data unchanged until a person approves it; every call
  is recorded in `agent_calls`, and a change in the audit trail with its channel (AG-D16).
- Every summary statement cites a fact that exists; the facts equal the database for the period; a
  summary never contains what its requester may not read and changes nothing.
- A failing provider never fails a deterministic result.
- A session uses only what its API grants allow and stops at a change set; the engine refuses it activation and
  publication, and a person does both (AP-D29). Nothing is installed or loaded before the person accepts a proposal
  whose every row was checked. A load leaves a saved profile that repeats it (AP10).
- A session's every run is in the call record, with its tokens and cost (AP9).
- The real-file try (AP-D22) on the user's own workbooks has been run and judged by the user.
- **The acceptance workbook** (the user, 2026-10-28): `Lines & Routes v2.0.xlsx`, a data dictionary laid
  out for reading (lists side by side, group headings above list headings, English and Spanish column pairs, `Y`
  flags, notes). The rules alone made one application of 101 types and 31 relation types of it. Through AP6 it gives
  a model a person reads as the business does, about four applications and a dozen types with group hierarchies,
  translations and relations, and its import, judged by the user.
- **Reshaping a workspace's model is an instruction too** (AP12): from the workspace, "reorganise this model" (or a
  narrower change) becomes a proposal like a new workbook's, so a person never needs the model editor's draft, install
  and activate path to fix a model. Merging types that hold data needs no wait for 1.0, and there are two ways,
  chosen by what moves (AP-D46). **A whole type becoming another** (a rename, a merge, into another application)
  goes by one migration: a model version with the new types, the proposal's `moves` as `typeMappings`, the person's
  one confirmation, records keeping their IDs. **Part of a type** (a split by value, a new level, a new parent) goes
  by the 0.8 restructuring (`changeType`, `changeTypeUnder`, `move`, `insertLevel`, `removeLevel` in a change set,
  records keeping their IDs, previewed first), in three phases: a model version with the target types beside the
  old, a change set restructuring the records into them, a version without the emptied types. A before/after count
  on the real model shows nothing lost.

## History of the assistant

**Superseded by [AP8](#ap8-the-assistant-is-a-claude-code-session). Kept for the reasons and findings, not as the plan.**
Nothing here is open work: what is still open moved to AP9 to AP13. What replaced what: AP3 to AP5 folded into AP6
(AP-D27), and AP4 and AP5 were then removed from 0.16; AP6 as first planned was a plan of steps; AP6a read by rules with the AI fixing refusals; AP6 and AP6r designed
in turns, with the steward accepting the model first; AP7, the engine matching first with the AI asked only about
the rest, had no section of its own and lives in the usage log, `workbook-design/9` and `/10`, and migration
`20261119_04`; AP8 replaced these turns with a session.

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

**Removed from 0.16 by the user 2026-10-31.** Never built; the text is kept as history.

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

**Removed from 0.16 by the user 2026-10-31.** Never built; the text is kept as history.

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

AP-D23 to AP-D28 stand in [Decisions](#decisions).

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
