---
title: Three kinds of change
description: Choose between correcting live data, preparing coordinated changes and changing the model.
reader: evaluator
---

refiroo separates three kinds of change: a live edit, a coordinated change set and a model release. Daily work continues while related changes are prepared separately; approval policies can require review before publication. See [What refiroo is](/docs/about/what-is-refiroo/) for how these choices fit together.

| You need to… | Use… | What becomes different |
| --- | --- | --- |
| Correct today's data | A live edit | The saved record is immediately current. |
| Prepare related data changes | A change set | Its changes become live together when published. |
| Change what the application allows | A model draft and release | The workspace uses the new definition when it is activated there. |

## Correct today's data

A person with permission can add, edit or delete live records without naming a change set. Saving records the change in history and protects against overwriting a newer version. It does not create a publication or a model release.

For example, correcting a stop's name in the Graubünden data is an ordinary live edit. Changing a model-defined availability field is also an edit: its business meaning is separate from publication status. See [Records](/docs/use/records/).

## Prepare related changes

A change set lets people prepare several changes away from Live. It starts from live data or an earlier publication and has its own proposed content. **Review changes** shows additions, changes and removals, including fields before and after. Validation checks the complete result without publishing.

Publishing applies the prepared changes over current Live data and creates the next read-only publication in the same operation. Unrelated live edits survive. A conflict or invalid result publishes nothing and keeps the prepared work. Review the reported conflicts; a new change set from current Live data is the way to prepare a fresh proposal when the old source no longer fits.

Where the workspace's approval policy requires it, the author submits the change set for a permitted reviewer to decide. The submitted content is frozen; withdraw the request before editing it. Approval publishes the reviewed content. See [Change sets](/docs/use/change-sets/) and [Inbox and approvals](/docs/use/inbox-and-approvals/).

## Change what the application allows

A model administrator edits a model draft to add a field, change a relationship rule or offer another view. Validation checks the definition; a preview or dry run helps examine its effect. Installing makes an immutable model release. Activation selects it for a workspace, leaving other workspaces on their own releases.

Installing alone changes no workspace. A release that existing data does not fit cannot simply be activated: the administrator reviews a migration, including any potential loss, before confirming it. An unsupported model language or invalid definition must be corrected rather than overridden. See [Model releases](/docs/model/releases/) and [Migrations](/docs/model/migrations/).

## Ask the right history question

| Question | Where to look |
| --- | --- |
| Who changed this record, and what changed? | [Record history](/docs/use/history/). Some older entries lack an author or a previous value. |
| What did a coordinated publication contain? | Its [publication](/docs/use/publications/), preserved even after later live edits. |
| Which fields and rules did a model define? | The installed [model release](/docs/model/releases/). |
| Which records were valid on a business date? | A [business-date read](/docs/integrate/business-dates/), for types whose model declares a validity period. |

A business-date read is not a reconstruction of everything stored on that date. A publication is not an archive of every intervening live edit. Withdrawing a publication removes its current designation without undoing data; starting a change set from it is not a full restore. Recovery of an entire dataset belongs to [backup and restore](/docs/run/backup-and-restore/).

## Keep something readable without offering it for new work

Changing a record's model-defined availability or validity dates can keep its identity and
history while ending its use under the agreed reading rules. It does not delete the record,
withdraw a publication or schedule publication for a future date. See
[Stop offering a value](/docs/guide/use/stop-offering-a-value/).

Retiring a model release instead hides it from future choices; workspaces already using it keep
working. Retiring a workspace preserves reading and stops changes. These choices have different
consequences from permanent deletion. See [Releases](/docs/model/releases/) and
[Managing workspaces](/docs/model/managing-workspaces/).
