---
title: Integrate a system
description: Discover contracts, read complete datasets, submit changes and follow events reliably.
reader: integrator
---

These journeys connect an integration's first contract read to ongoing synchronisation and
recovery. Use the management API to work with the model and records, or a model-declared consumer
API to read business objects. Start with [the integration overview](/docs/integrate/overview/)
and [signing in and tokens](/docs/integrate/signing-in-and-tokens/). Roles and consumer API grants
are separate; a token must also be intended for the API it calls.

The linked documentation explains sequences. Use the [API reference](/docs/api) for management
operations and their exact inputs and responses. Consumer API shapes depend on the model and are
explained with examples in [Consumer APIs](/docs/integrate/consumer-apis/).

## Discover the model and the API

An integrator first checks what the deployment enables, its limits, and the workspace and model
release to use. [Discovering the model](/docs/integrate/discovering-the-model/) connects these
reads to types, attributes, relationships and permitted placements. Choose the data context before
reading metadata: a change set or publication can use a different release from Live.

Next open the [API reference documentation](/docs/integrate/api-reference/) and the
[management operations](/docs/api). Discover consumer APIs and their own generated contracts
rather than assuming all models expose the same paths. Stable public keys and record IDs identify
resources. If a model cannot be served, resolve the named workspace's problem instead of substituting
another workspace's definitions.

## Read a collection completely and resume

An integrator reads a bounded first page, processes it and follows the returned cursor until the
end. [Identifiers, paging and errors](/docs/integrate/identifiers-paging-and-errors/) explains
page positions, totals, reverse traversal and seeking where supported.
[Read a collection completely and resume](/docs/guide/integrate/read-a-collection-completely-and-resume/)
connects processing to saving a continuation point and restarting the same query.

Keep the query, workspace and context with that continuation. Reusing a cursor for a different
read is refused; do not construct or edit one. A page maximum is a page limit, not a limit on the
whole collection. A live traversal is not a frozen extract: choose a retained publication when the
integration needs a fixed snapshot. Browser readers can
[continue a long list](/docs/guide/use/continue-a-long-list/) through scrolling and position controls.

## Request the precise dataset an integration needs

An integrator selects types and a data context, combines typed field filters with hierarchy and
relationship criteria, chooses returned fields and related data, then pages the result.
[Reading records](/docs/integrate/reading-records/) explains the choices and links to the
[query operations](/docs/api). Use type-specific reads for model-declared fields; the cross-type
lookup serves the common fields it supports. A workspace relationship list answers questions
about connections rather than just records.

An invalid filter or sort is a refusal, rather than permission to return a broader dataset.
Correct the named criterion and restart with cursors for that query.

**Example:** read stops below chosen municipalities and include connected operators. Those types
and fields belong to the example model; the querying capability works over the selected model.

## Answer a business-date question

An integrator asks which records apply on a calendar date using a model-declared validity period.
[Business dates](/docs/integrate/business-dates/) explains inclusive starts, exclusive ends and
open boundaries. [Read as of a date](/docs/guide/integrate/read-as-of-a-date/) carries the date
through every page in the chosen live or published data.

A business date does not reconstruct an old database state or date every related record in a
projection. Check which types the answer actually dates. A type without a configured period cannot
answer a dated object or list read; mixed supported consumer lookups identify which types were
dated. Use a publication when you need a saved snapshot rather than validity on a date.

## Submit a bounded bulk change

An integrator sends a bounded group of record and relationship changes as one batch.
[Writing in bulk](/docs/integrate/writing-in-bulk/) leads to
[Submit a bulk change](/docs/guide/integrate/submit-a-bulk-change/) and the
[batch operations](/docs/api). Choose atomic execution for everything or nothing, or independent
execution when other items may succeed despite a refused item. Reference existing records by
ID or unique key and inspect each item's result before retrying.

Reuse the same idempotency key only for the same request: replay returns its original outcome;
changing the request under that key is refused. The ordinary model and version rules apply to
every item. Previewing a batch requires a background job; use the
[large-job journey](#run-a-large-background-job-and-recover) for work beyond inline limits.

## Run a large background job and recover

An integrator or exchange operator submits background work, keeps the returned job identity,
follows progress and reads item outcomes as execution advances.
[Jobs](/docs/integrate/jobs/) connects submission to completion, cancellation and recovery;
[Follow and cancel a job](/docs/guide/use/follow-and-cancel-a-job/) gives the browser view.
A preview can wait for explicit confirmation without having written the proposed changes.

After interruption, a worker resumes at the first unfinished item. Cancellation or failure of
independent work can leave committed chunks; atomic work rolls back together. A model, workspace,
permission or change-set change can stop work before the next chunk. Read the reason and applied
outcomes before resubmitting. Retention can remove detailed item results while keeping a summary,
so collect outcomes while they are available. Operators use
[Background jobs](/docs/run/background-jobs/) for worker recovery.

## Follow changes reliably

An integrator keeps another system current by processing a workspace's ordered change feed and
saving the last safely processed position. Read [Following changes](/docs/integrate/following-changes/),
then [load, then follow changes](/docs/guide/integrate/load-then-follow-changes/) to connect an
initial publication or consistent export with later changes. Feed entries identify changes and
their causes; they do not contain field values. Read records when the integration needs values.

Recognise replay by position and save progress only after processing succeeds. Keep following
continuation even through an empty filtered page until caught up. Unpublished edits and refused
writes do not appear. An expired position needs a fresh baseline and continuation from its stated
position; an ahead-of-head position needs investigation, including whether the wrong workspace
or a restored database was used. Do not silently skip to the current head.

## Exchange a supplier file

An exchange operator, steward or integrator identifies the destination, file layout and mapping,
then previews additions, updates and refused cells without changing data.
[Files, imports and exports](/docs/integrate/files-imports-and-exports/) leads to
[Exchange a supplier file](/docs/guide/integrate/exchange-a-supplier-file/) and its
[import and export operations](/docs/api). Browser workers can instead
[import a file](/docs/guide/use/import-a-file/) or
[export records](/docs/guide/use/export-records/). Choose the failure policy and inspect whether
the preview covered all execution items or only a sample before confirmation.

Read each applied or refused outcome, correct rejected rows and retry without duplicating applied
work. A changed profile, model or change set can require another preview. For a workbook intended
for people to edit, [edit in Excel and import back](/docs/guide/use/edit-in-excel-and-import-back/)
uses the carried mapping and versions; stale records are refused. A failed, cancelled or expired
export does not provide a partial download. Check a successful export's scope and position before
using it as a synchronisation baseline.

**Example:** exchange a workbook of stops and codes from other systems. The file's destination and
mapping determine what it changes; a similar column label does not establish identity.

## Read a business object through a consumer API

A consuming system discovers a declared contract and reads an object by its stable ID, or pages
a declared list. Start with [Consumer APIs](/docs/integrate/consumer-apis/) and
[Reading business objects](/docs/integrate/reading-business-objects/), then
[read through a consumer API](/docs/guide/integrate/read-through-a-consumer-api/).
Declared parameters can narrow objects or their related blocks. The same object shape is used
across the contract's reads.

Live reads include saved live corrections, never unpublished proposals. Choose a publication for
a repeatable extract; its continuation stays with the starting snapshot even if a newer one
becomes current. An unsupported operation, wrong contract version or another workspace's record
is refused. Use the model's current contract documentation rather than guessing another path.

**Example:** the reference stops API combines a stop's fields with its names and external codes.
Those outputs are a declaration, not a fixed feature every model must expose.

## Resolve a business object through a consumer API

A consuming system starts with a code, name, ID or related value instead of a known record ID.
[Looking up and resolving](/docs/integrate/looking-up-and-resolving/) explains matching, scores,
ambiguity and translating into a target representation. [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/)
connects lookup to batch resolution and per-item found, missing, ambiguous or rejected outcomes.

Narrow ambiguous results using the definition's parameters; never pick an arbitrary tied match.
A unique best object can still have a missing or ambiguous target representation. Review those
separate outcomes before accepting a crosswalk. Use a publication to resolve the whole file
against a fixed dataset. The consumer documentation gives the contract-specific requests and
responses, including limits; broad or oversized lookups must be narrowed or divided.

## Follow a consumer API's changes

An integrator loads a publication, then follows the declared consumer events from its position.
[Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) connects full or
identity-only events, cursors, duplicate recognition and recovery after expiry. Process every
event at a position and keep its continuation; several events can share one raw change position.
Recognise repeated events by their event identity.

For pushed delivery, an authorised administrator [creates a webhook](/docs/guide/administer/create-a-webhook/)
and the integration [subscribes and verifies it](/docs/guide/integrate/subscribe-a-webhook-and-verify-it/).
Verify the signed request, process it safely and acknowledge successful receipt. Failures are
retried before later deliveries; inspect [webhook deliveries](/docs/administer/webhooks/) when
recovery is needed. Changed models, expired events or prolonged failures can suspend a subscription.
A reset skips missed events, so restore a baseline before treating the receiver as current.

Filters can hide the change by which an object leaves their scope. If your copy must remove such
objects, follow the necessary type-wide events and apply narrower criteria locally. This matters
for pull reads and webhook subscriptions alike.

## Automate a reviewed change and its approval handover

[Changes, approvals and publication](/docs/integrate/changes-approvals-and-publication/)
connects capture of an explicit base, versioned writes, complete validation and submission.
Present the differences and diagnostics to a person who may decide under the current policy.
Submission changes no Live data; approval publishes the reviewed version and can still refuse
competing live changes. Keep publication identity and feed position after success.

An open set is not a job that expires under item-result retention. To abandon it, withdraw a
submission where necessary and discard its prepared work. After losing a publication response,
read publication and change-set state before retrying. A consumed proposal can mean success.
Use approval events or inbox operations for review notifications; these are separate from the
data feed used for synchronisation. The page links to each [management operation](/docs/api).

## Administer models and transfer records through the API

[Model and release operations](/docs/integrate/model-and-release-operations/) connects draft
steps, validation, generated documents, installation and activation. Keep the model release
and record versions explicit. A data conversion needs a fresh migration preview with blockers
and losses presented for a person's confirmation; installing alone does not activate.

[Move records between models](/docs/guide/integrate/move-records-between-models/) follows a
saved mapping through selection, complete dry run and loading into change sets. Review omitted
values and dropped relationships as well as successful records. A move needs publication of
the target before source deletions. Changed releases or mappings invalidate an old review.
Use the linked [model operations](/docs/api) rather than editing stored definitions directly.

## Submit an assistant task from an integration

[Assistant tasks](/docs/integrate/assistant-tasks/) explains submitting instructions or a file,
following work, displaying checked changes and accepting a reviewed proposal. The requester
needs **Use AI proposals**, **Bulk and import**, and the permissions for model or change-set
work. This needs the built-in assistant and permission to send values, separately from an
external MCP connection.

Keep the task and job identities. Read current state before every action; distinguish a checked
proposal, a loaded change set and a migration requiring human confirmation. Session work cannot
approve, publish or activate. A matching saved-layout path can activate a draft with the right
permission, so show the actual path and result. Stopping, correcting or discarding can remove
an unpublished result and people's subsequent edits; show that consequence before acting.
Read its data, cost and retention rules, and link users to
[Work with an assistant](/docs/journeys/work-with-an-assistant/) for review and recovery.
