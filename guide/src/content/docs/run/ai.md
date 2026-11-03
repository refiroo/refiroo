---
title: About AI in refiroo
description: Choose which AI features to enable, control what leaves the instance, and understand access, costs and retention.
reader: operator
---

AI is optional. You choose which features to enable in the engine's environment, then restart it.
People review the proposals before using them. To enable it, follow [Set up AI](/docs/run/set-up-ai/).

## Choose what to switch on

Three settings control separate capabilities. None requires the other two.

| Setting | What it enables | When left unset |
| --- | --- | --- |
| `AI_AGENT_COMMAND` | The built-in assistant: a Claude Code session that reads a workbook or instructions, works with the workspace's model and records, and prepares changes for review. | No built-in assistant is offered. |
| `AI_PROVIDER` | Requests for mapping targets, questions in words, and accounts of model changes or what changed over a period. | No provider features are offered. |
| `MCP_ENABLED=true` | Access for external assistants through the Model Context Protocol (MCP). | The MCP endpoint, metadata and registration are absent. |

The built-in assistant uses Claude Code's own credentials. Setting `AI_PROVIDER` does not configure
it. Conversely, you can run the assistant without a provider. With both AI settings empty, refiroo
sends no AI requests; separately enabled MCP access still lets an external assistant read what its
permissions allow.

The provider can be `claude`, `openai-compatible` for an endpoint using the chat-completions
protocol, or an operator-supplied factory named `package.module:function`. A locally hosted provider
is an option when reference data must stay within your organisation.

## Control what leaves the instance

`AI_SEND_LEVEL` sets the most data an AI feature may send. The default is `values`.
A feature that needs more than you allow is unavailable.

| Level | What may be sent |
| --- | --- |
| `structure` | Model keys, labels, headers and types, with the question or facts needed by the feature; no record values. Summaries can include counts. |
| `samples` | Also sample values, normally up to `AI_SAMPLE_VALUES` per column or attribute. The default is 20. |
| `values` | The values the feature needs. `AI_SAMPLE_VALUES` does not cap this level. |

A question in words is available at every level. At `samples` and `values`, it can also send all
record names for a relationship's type when its list in the current context has at most 50 records.
That list is not capped by `AI_SAMPLE_VALUES`. At `structure`, it sends none of those names.

The assistant requires `values`: it receives your words, the workspace's model and the whole workbook
if supplied, and can read workspace records as needed. Mapping targets also require `values`:
requests include the source and candidate target names and the fields displayed in the view.
Sources are sent in groups of 25; candidates are all eligible targets up to 100, or each source's
20 closest targets by name for larger sets.

An account of a model change sends the changes and record counts, without record values. An account
of what changed sends counts and model labels; names of records, people, change sets and files are
included only at `values`.

These settings govern refiroo's AI features. They do not impose a send policy on an external MCP
assistant after it reads permitted data. Check that assistant's settings and your organisation's
agreement with its provider too. Even `structure` sends information outside the instance when the
provider is external.

## Who can use it

The **Use AI proposals** action group allows a person to request AI help. The predefined **Data
steward**, **Data owner**, **Model administrator**, **Workspace administrator** and **Integration
administrator** roles include it. Grants determine where those rights apply.

Other permissions still matter: AI access alone does not grant permission to import, edit a model
or work in a change set. People without the action group are not offered AI actions. Operators need
**Operations** to inspect **Settings › Administration › AI** and send a provider test request.

External MCP assistants act within their person's or client's permissions, restricted to browsing
and work in change sets. They cannot approve, publish or write directly to live data. Security
administrators manage them on **Settings › Security › Agent access**.

## The assistant's session

In the shipped engine container, the assistant runs as a separate operating-system user,
`assistant`. Each task has its own working folder under `/data/assistant`. Claude Code keeps its
configuration and transcripts under `/data/assistant-claude`, set by `CLAUDE_CONFIG_DIR`.

The session receives a dedicated refiroo client and temporary grants drawn from the requesting
person's permissions. It cannot publish a change set or activate a model release, even if that
person can. A person reviews the result and takes those steps. Grants end with the session's turn.

The engine does not pass its database address, encryption key or other server secrets to the
session. It does pass the environment names Claude Code needs, including `ANTHROPIC_*` and
`CLAUDE_*` names; treat credentials placed there as available to the session. The assistant user
cannot read the engine's job-file directory or its process environment.

With `AI_AGENT_SANDBOX=container`, the container provides the boundary because Claude Code's own
operating-system sandbox cannot run there. **The container does not restrict the session's network
access.** Apply any required outbound network restrictions in your deployment. Outside a container,
refiroo requires the operating-system sandbox; an unavailable sandbox refuses the session.

A turn running for more than 30 minutes is stopped and fails. The task can be continued after the
cause is addressed. Text in records is treated as data, but AI output can still be wrong; review
proposals before accepting them.

## Calls and costs

Open **Settings › Administration › AI** to see which switches are on, the send level and, when a
provider is configured, its model, endpoint, whether a key is set, and the features available.
The key itself is never shown. This page displays settings; change them in the environment.

**Calls** lists provider requests and assistant turns, newest first: who asked, what for, the model,
outcome, tokens, cost when reported, and duration. A failed call includes a failure message.
Totals cover the last 30 days. An assistant turn counts as one call, including cache reads and
writes in its token figures. A dash for cost means no cost was reported, not that the call was free.

Claude Code authentication and billing belong to Claude Code. An API key uses API billing; a
subscription token uses its Claude subscription. Provider requests use their separately configured
credentials. Check actual charges and usage limits with the provider; refiroo's call log is not a
billing statement.

**Send a test request** sends a fixed request containing none of your reference data. It tests the
provider, appears in the call log and may incur usage. It does not test the assistant.

## What is kept

| Information | Retention in refiroo |
| --- | --- |
| Call metadata, outcome, tokens and reported cost | Kept after request content expires. There is no configured expiry for the call records themselves; the 30-day totals are a reporting window. |
| A call's request and answer | Not kept in the call log by default. `AI_LOG_CONTENT=true` keeps them for `AI_LOG_CONTENT_DAYS`, default 7, after which content is cleared while the call record remains. For assistant turns this is the prompt and final answer, not the full stream. |
| Assistant task and workbook | `AI_TASK_RETENTION_DAYS`, default 90 days after completion or the last change. The worker's expiry sweep deletes the task and its files. |
| Session folder, session logs and Claude Code transcript | Kept while the task can continue, including failed, stopped and loaded tasks. Once the change set is published or discarded, the migration confirmed, or the task discarded, the next task read removes them and deactivates its client. Expiry also triggers cleanup. |
| MCP tool-call records | `MCP_CALLS_DAYS`, default 90 days. Argument names are recorded, not their values. |

`AI_LOG_CONTENT=false` does not disable the assistant's working files or Claude Code transcripts.
Enable call-content logging only while needed: it can contain reference data. These settings do not
control the provider's own retention.

The shipped Compose file persists job files but does not mount the assistant's working folders or
Claude Code directory as volumes. Replacing the container can therefore remove session files before
their normal cleanup date. Keep this in mind before recreating a container with unfinished tasks.
