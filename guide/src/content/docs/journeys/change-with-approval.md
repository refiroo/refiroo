---
title: Change with approval
description: Prepare coordinated changes, review differences, obtain approval and publish safely.
reader: steward
---

Use these journeys when related changes must reach Live together, need review, or depend on a
model release. A change set holds the proposal; a publication preserves the result. Read
[Change sets](/docs/use/change-sets/) for their states and permissions. Work in change sets,
Publish and Approve publications are separate permissions; a reviewer does not automatically
have permission to decide or publish.

## Prepare and publish a coordinated design

A person preparing changes, or an integrator, starts a change set from current Live data or a
retained publication. Follow [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/)
to name the proposal, make the ordinary record and relationship changes, review them, and validate
the whole result. Publish when validation, access and approval policy permit it. Then inspect the
new [publication](/docs/use/publications/) and its source.

Staged edits remain invisible to Live readers until publication. Publication applies all proposed
changes together, or none. A failed validation or conflict keeps the proposal for correction.
Installing a model or saving a record inside the proposal does not publish it.

**Example:** a coordinated change can update the validity dates of several stops for a timetable
change. The dates are data; publication is the act that makes the prepared changes live.

## Continue live work while a change set is open

A steward keeps routine corrections moving while colleagues prepare a larger proposal. Read
[how a change set works apart from Live](/docs/use/change-sets/#working-apart-from-live), then
[continue live work](/docs/guide/use/continue-live-work-while-a-change-set-is-open/) in the Live
context. Later publication applies only the proposal's changes: live additions and corrections to
untouched records survive.

If both sides changed the same record, publication stops and names it, even when different fields
were edited. Inspect the live record and the proposal before deciding how to revise the work.
Successful earlier validation does not reserve the live data.

## Withdraw a publication and start reviewed changes from history

A person responsible for publication, or an integrator, begins by
[browsing a publication](/docs/guide/use/browse-a-publication/) as it was saved. If the current
publication should no longer be designated current,
[withdraw it](/docs/guide/use/withdraw-a-publication/). Its snapshot and history remain readable;
Live is unchanged and no older publication becomes current automatically.

Next, [start from an earlier publication](/docs/guide/use/start-from-an-earlier-publication/),
prepare explicit corrections and return to review, validation and publication. Choosing an older
source does not roll back Live. Newer live records that the proposal leaves untouched are kept.
See [Publications](/docs/use/publications/) for the difference between Current, earlier and Withdrawn.

## Review what a change set changes

A reviewer or integrator opens the proposal to understand its effects before deciding.
[Review what a change set changes](/docs/guide/use/review-what-a-change-set-changes/)
connects record changes and relationship changes, their filters and the before-and-after details.
Inspect additions, removals, moves, changed types and fields across the complete lists.

“Before” is the proposal's starting data, including an older publication when that was its source.
The review explains the authored differences; validation and publication also check their combined
effect against current Live. If nothing matches a filter, clear it before assuming the proposal
is empty. Continue to [approval](#propose-and-approve-a-change) or direct publication as permitted.

## Prepare under the next model version while live keeps the current one

A person preparing a proposal works with a model administrator to use a candidate release before
Live switches to it. First [install the release](/docs/model/releases/) without activating it.
Then [prepare under the next model version](/docs/guide/use/prepare-under-the-next-model-version/).
The change set's forms and rules follow that release; Live and other proposals keep theirs.
Starting data must fit the chosen release.

Normal publication needs matching releases. Coordinate activation with the administrator.
If records require conversion, read [Migrations](/docs/model/migrations/): either move the proposal
to the workspace's current release, or review a workspace migration combined with publication.
Each preview changes nothing, lists any losses and blockers, and must be refreshed if stale.
Moving a proposal alone changes no live data. A submitted proposal must leave its waiting state
before editing or changing its release; discarding remains an option for abandoned work.

## Propose and approve a change

A contributor prepares a change set, then submits it to someone allowed to approve publications.
Start with [Propose a change](/docs/guide/use/propose-a-change/), read
[Inbox and approvals](/docs/use/inbox-and-approvals/), and follow
[Approve a change set](/docs/guide/use/approve-a-change-set/) from submission to decision.
Submission validates and freezes the proposed version without changing Live. The approver opens
the notified request, reviews its differences and either approves and publishes or sends it back
with a required comment. The submitter receives the decision and can correct and resubmit returned work.

A workspace's [approval policy](/docs/administer/approval-policies/) determines whether approval
and a second person are required. With a second-person rule, the submitter cannot decide their own
request. To resume editing while waiting, the submitter or an authorised approver withdraws the
request; that keeps the proposed changes. Approval rechecks current data and can still refuse a
conflict. Reload and review the current request before another decision.

## Resume or abandon unfinished work

An open change set remains until published or discarded; job retention does not expire it.
Reopen it, check its context and review its current differences before continuing. Live or model
changes since the last visit can require fresh validation or a migration. See
[Change sets](/docs/use/change-sets/).

If the proposal is no longer needed, withdraw a waiting submission before discarding it.
Discarding removes proposed work, while sending it back keeps it available for correction.
Neither undoes Live or removes a publication. After a lost publication response, inspect
publications and history before repeating the request: a consumed change set can mean that
publication succeeded. [Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/)
explains the corresponding integration recovery.
