---
title: AI and your data
description: Understand who can use AI help, what is sent, the costs and what is kept.
reader: steward
---

Before asking AI for help, check that the task and the data suit your organisation's rules.
AI can misunderstand a question or propose the wrong change. You review its work before
publishing it. Asking a list changes its filters, not its records.

## Which help is available

refiroo offers three separate kinds of help. Your operator chooses which are enabled.

- An AI provider turns a question into list filters, proposes mapping targets and explains changes.
  The provider can use the Claude API or a compatible service, including a model run inside your organisation.
- The built-in assistant uses Claude Code to read a workbook or your instructions and prepare
  a model and records for review. It can be enabled without the provider.
- An external assistant can connect through the Model Context Protocol (MCP), if your organisation
  enables agent access. It acts within your access, limited to reading and preparing change sets.

The **Use AI proposals** permission is needed for built-in AI actions. The predefined
**Data steward**, **Data owner**, **Model administrator**, **Workspace administrator** and
**Integration administrator** roles include it. Your grant determines which workspaces it covers.
Other permissions still apply: AI access alone does not let you import, change a model or publish.
An absent action can mean the feature is disabled, the data allowed to be sent is insufficient,
or you do not have the required access.

## What leaves the instance

An operator sets a ceiling on what refiroo's AI features may send. These are the send levels
named by the screens:

| Send level | What it allows |
| --- | --- |
| structure | Names of types and fields, headers, their rules and counts; no stored record values. Your question or instructions are still sent. |
| samples | Also sample values, normally up to a limit chosen by the operator. Questions in words have the short-list exception below. |
| values | The record values the feature needs. The sample limit does not cap this level. |

[Asking a list](/docs/use/ask-in-words/) sends your question, today's date and the fields and
relationships the list can filter. At samples or values, it also sends related-record names when
that type's list has at most 50 records in the current context. Ancestor names can be included too.
Those short lists are sent whole, regardless of the ordinary sample limit. At structure, no
stored record names are included. Anything you type into the question is sent at every level.

[Proposed mapping targets](/docs/use/mapping-grids/#targets-proposed-by-ai) need values. The
provider receives source and candidate target names and the fields shown by the grid.
[The assistant](/docs/use/loading-with-the-assistant/) also needs values: it receives your words,
the workspace's model and the whole workbook, if supplied, and reads the records its task needs.

[Explaining a period](/docs/use/history/#what-changed-in-a-period) sends counts and model labels.
Names of records, people, change sets and files are included only at values. Explaining a model
change sends the model's differences and counts, without record values. See
[Explain a model change](/docs/guide/model/explain-a-model-change/) for that model-administrator task.

Read the line beside an action before sending. An external provider receives the information
under your organisation's agreement with it. A local provider can keep it inside the organisation.
These send levels do not control what an external MCP assistant sends on after reading permitted data;
check that assistant's settings too.

## Costs and saved information

AI requests and assistant turns can incur charges or consume your organisation's subscription
allowance, even if they fail or you later discard the work. Your operator can see call records
under **Settings › This instance › AI**, including who asked, what for, the outcome, tokens and
reported cost. A missing cost means none was reported; it does not mean free usage. Provider
billing and Claude Code billing are separate. A saved workbook layout that fits the next file
can prepare it without another assistant session and without AI cost.

Call metadata is kept. Request and answer text is not kept in the call log by default; an operator
can enable it, normally for seven days. Assistant tasks keep instructions, proposals, checks and
the workbook for the configured retention period, normally 90 days after completion or the last
change. The session's working files and Claude Code transcript remain while the task can continue,
including after a failure, stop or load awaiting publication. They are removed when the completed
work is next checked, or on expiry. Turning off call-text logging does not remove those files.
Published records and their history remain when a task expires. The provider's own retention is
separate. See [AI operation and retention](/docs/run/ai/) for the full settings and limits.

## Your review stays necessary

Proposed mappings and loaded records wait in a change set. You correct them and follow the
workspace's normal approval and publication rules. The assistant cannot approve, publish or
activate a model. A whole-type model migration is different: a person's explicit migration
confirmation moves the records live. Read that preview before confirming it.

An external assistant cannot approve or publish either. If you sign in for one, refiroo's sign-in
page names the assistant and where it returns. That name is supplied by the assistant itself.
Check both before allowing it. Find its session in [your account](/docs/use/account/) to sign it out.
