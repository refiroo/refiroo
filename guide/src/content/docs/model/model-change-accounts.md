---
title: Accounts of model changes
description: Understand the explanation of a proposed activation, its source facts and its limits.
reader: model-admin
---

Before activating a release or applying a workspace's draft, you can ask for a plain-language
account of what the change does. **What this change does** appears in the activation dialog and
in **Apply to this workspace** when an AI provider is available and you hold **Model release**
and **Use AI proposals** in that workspace. Follow
[Explain a model change](/docs/guide/model/explain-a-model-change/) to use it.

The account helps you read the change. It does not approve it, activate anything or remove a
blocking rule. Keep reading the data and consumer API checks alongside it.

## What is sent, charged and kept

Opening the dialog sends nothing to the AI provider. Only **Explain this change** asks it to
write an account. The request contains model changes and record counts, without record names
or values. The account is available at every configured send level. It needs the separate AI
provider; enabling the Claude Code assistant alone does not offer it.

A request can incur provider charges. refiroo records the call and its usage; request and answer
content is not kept in the call log unless the operator enables it. A successful account can
be reused for the same inputs within an hour without another provider call. It is a reading
aid, not part of the release or a permanent history entry. The provider's own retention is
separate. See [About AI in refiroo](/docs/run/ai/) for full access, costs and retention details.

## Facts first, wording second

refiroo supplies the facts that the provider puts into sentences:

- Differences between the model definitions.
- Rules the workspace's records would break, with counts.
- Changes that affect consumer APIs.
- Reasons activation is blocked, including a required migration or a consumer contract version change.
- Record counts for each affected type in the workspace.

The counts cover the whole relevant set of records. A release's differences are against the
workspace's running release. A draft's differences are against its base release; the data check
still uses the selected workspace. Check the workspace and baseline shown in the surrounding
dialog rather than assuming every comparison has the same starting point.

Each AI-written statement has numbers that lead to the facts it cites. **The facts** lists all
facts, initially showing ten; **Show the other …** reveals the rest. For a large change, the
provider receives at most 40 facts of each kind and the true totals. A **+** citation refers to
other facts of a kind. You still have the complete fact list in the dialog.

The note below the statements says the account was written by AI and can be wrong. A citation
shows the source; it does not prove the sentence interprets it correctly. Statements without
a valid source are removed, and the page reports how many were removed. If none remain, the
facts themselves are the account.

## Failure and limits

**The account could not be written** means the provider failed or returned an unusable answer.
The facts remain available because they do not depend on it. **Try again** makes another
attempt. A failure to request the account instead shows **The account could not be asked for**;
read its reason before retrying.

An invalid draft cannot be explained: fix its issues first. If a newer draft version exists,
reload and review it before asking again. A fresh compatibility check clears the old account.
Changed facts, including record counts, need a fresh request; failures and accounts with no
usable statements are not cached for reuse.

The browser account is in English. There is no follow-up conversation, and the account is not
shown in the install dialog or on the migration page. The [migration preview](/docs/model/migrations/)
lists its own conversions, removals and refusals; read those before confirming. An account saying
why activation is blocked is an explanation of the block, not permission to bypass it.
