---
title: Writing in bulk
description: Apply bounded changes with explicit failure policy, safe retries and per-item outcomes.
reader: integrator
---

Use a batch to create, update, upsert or delete records and relationships together. A batch is a job even when it runs inline. The [batch operation under jobs](/docs/api/?api=management#tag/jobs) defines the available operations. Follow [Submit a bulk change](/docs/guide/integrate/submit-a-bulk-change/) for the sequence.

## Choose policy and execution

Choose the policy explicitly. **Atomic** applies all items or none. **Independent** lets valid items apply when another is refused. Items run in order and see earlier applied items; this is not deferred validation of a final graph. For example, swapping two unique values cannot rely on an intermediate duplicate being tolerated. Use a change set for changes needing whole-graph preparation.

Choose inline or background explicitly; refiroo does not silently switch the response when a request grows. Default limits are 1,000 items and 5 MB inline, 1,000,000 items and 50 MB for a background JSON batch, and 10,000 items for an atomic job. Read the current [capabilities](/docs/api/?api=management#tag/model); operators can change these limits. `BATCH_TOO_LARGE` means split the request or choose the supported larger mode. A larger file can be loaded through [imports](/docs/integrate/files-imports-and-exports/).

A processed inline request can succeed at HTTP level while some or all items are refused. Read the job result and every item's outcome:

| Outcome | Meaning for your source system |
| --- | --- |
| Applied | The item committed, including unchanged items that needed no write. |
| Rejected | Correct the item using its machine-readable refusal. |
| Unprocessed | The item has no committed change from this execution. Inspect whether rollback, cancellation, a model change or a job failure stopped it. |

An atomic refusal rolls back earlier items and marks other items unprocessed. Independent work commits in chunks, so later failure leaves earlier committed changes intact.

## Address records and protect changes

Address an existing record by public ID or an attribute declared unique for its type. References can find a record applied earlier in the same batch. `INVALID_RECORD_KEY` requires a genuinely unique attribute; `REFERENCE_NOT_FOUND` requires loading the target first; `REFERENCE_TYPE_MISMATCH` requires the right type. A create using an occupied ID is `OBJECT_ALREADY_EXISTS`, including IDs held in another workspace.

Updates claim the version read. A changing upsert without a version is `VERSION_REQUIRED` unless the request explicitly permits overwrite. Use overwrite only when the supplying system is authoritative; it is recorded in history. An unchanged item needs no version change or event. Initial relationships on an upsert are used only when the record is created.

A batch targets either live data or a change set, not a context per item. `INVALID_BATCH_CONTEXT` needs a corrected selection. In a change set, claim its version for the job as well as applicable item versions. If the model changes during an inline batch, the request and job save nothing. A background job reports what its earlier chunks already saved.

## Relationships and sets

A batch can create, ensure, update or delete a relationship, ensure that two records are not related, or replace a whole set. Both ends must exist in the context and belong to the same workspace. Typed relationship values obey their declarations. A set replacement keeps existing relationships when possible and claims the set version read; relationship creation and deletion can also claim that set. `RELATION_SET_VERSION_CONFLICT` requires rereading the membership; `RELATION_SET_CLAIM_INCOMPLETE` requires a complete claim.

Ensure operations are useful for repeated loads. Ensuring absence removes an existing mutable relationship or returns unchanged if none exists. It cannot remove containment or a required relationship. A previewed set replacement carries the set version it showed into execution. A mapping save checks a stale set token even on an unchanged save; the bulk replacement can answer unchanged first.

The same model rules apply to single and bulk writes. `CARDINALITY_VIOLATION` means the binding allows fewer relationships; many-to-one permits at most one on its constrained side. `INVALID_RELATION_PAIR`, `RELATION_CANDIDATE_REFUSED` and `RELATION_ANCESTOR_REQUIRED` require allowed endpoint types and candidates. `RELATION_WRONG_SCOPE` or `PARENT_WRONG_SCOPE` requires one workspace. `DUPLICATE_RELATION`, `RELATION_ALREADY_EXISTS` and `DUPLICATE_INITIAL_RELATION` require removing duplicates or using an ensure operation. `IMMUTABLE_RELATION`, `REQUIRED_RELATION` and `REQUIRED_OWNERSHIP_BINDING` require the permitted containment or ownership operation rather than deleting an essential edge.

## Preview and delete safely

A background preview writes no data changes. Inspect the proposed counts and refused items, and whether the preview covered every item or only a sample. Confirm through the [job operations](/docs/api/?api=management#tag/jobs) or cancel. Execution evaluates current data: preview success is not a reservation.

Cascading deletion needs confirmation of each record's impact. Without cascade, `OBJECT_HAS_DEPENDANTS` asks you to inspect that impact. `DELETION_PREVIEW_REQUIRED` needs a preview token; `DELETION_PREVIEW_CHANGED` needs a fresh preview. Confirming a batch preview carries its per-item deletion tokens. Unpreviewed deletes in a sample remain unconfirmed. If an earlier delete in the same job already removed a selected child, its later item is unchanged and identifies that earlier item.

## Retry without duplicating a job

Give a job-creating request an idempotency key and retain the exact request with it. Retrying the same request returns the original job. `IDEMPOTENCY_IN_PROGRESS` means follow that job or wait for the retry interval. `IDEMPOTENCY_KEY_REUSED` means the same key names a different request: correct the error instead of treating it as a replay. Keys expire with job retention, so they are not permanent deduplication identifiers. An unkeyed create without a supplied ID can create a duplicate after a lost response.

## Correct refused data

Missing required values or relationships, unknown or read-only attributes, invalid types, duplicates and numeric bounds need source correction. These include `MISSING_REQUIRED_ATTRIBUTES`, `MISSING_REQUIRED_RELATIONS`, `OBJECT_ATTRIBUTE_RULE_VIOLATION`, `DUPLICATE_ATTRIBUTE`, `DUPLICATE_ATTRIBUTE_VALUE`, `READ_ONLY_ATTRIBUTES`, `UNKNOWN_ATTRIBUTES`, `UNKNOWN_RELATION_ATTRIBUTES`, `INVALID_ATTRIBUTE_VALUE`, `ATTRIBUTE_BELOW_MINIMUM` and `ATTRIBUTE_ABOVE_MAXIMUM`.

For parent changes, `PARENT_REQUIRED`, `PARENT_NOT_FOUND`, `INVALID_PARENT_TYPE`, `CHILD_TYPE_NOT_ALLOWED` and `PARENT_CYCLE` require an allowed hierarchy. Racing moves cannot create a cycle. `TYPE_CHANGES_NEED_CHANGE_SET` or `CHANGE_SET_REQUIRED` requires preparing the change in a change set; `REQUIRED_RELATION_WITHOUT_PLACE` means the new type cannot preserve required content. `OBJECT_TYPE_UNCHANGED` needs no type change. For [restructuring operations](/docs/api/?api=management#tag/objects), `RESTRUCTURING_NOT_READY` or `RESTRUCTURING_PLAN_CHANGED` needs a new valid plan; `RESTRUCTURING_TOO_LARGE` and `TOO_MANY_RECORDS` need a supported smaller scope.

## Interpret outcomes and retries

An item reference is 1–200 characters and is echoed with the item’s index. Rejections use the same machine-readable codes as single writes, with a pointer to the failing input. Unprocessed reasons distinguish `BATCH_ROLLED_BACK`, `JOB_CANCELLED`, `MODEL_RELEASE_CHANGED` and `JOB_FAILED`. Treat unknown action or reason values according to their enclosing status. A completed job’s result is `applied`, `partial` or `rejected`; HTTP 200 means the batch was processed, even when none of its items applied. Request-level refusals create no job.

A genuinely unchanged update or upsert takes no version, history entry or feed position, even if its supplied version is stale. For a changing upsert, the default `onExisting` policy rejects an unclaimed overwrite; opt in to overwrite only deliberately. An overwrite outcome reports the previous version and history records that no version was claimed.

Idempotency keys contain 1–200 printable characters and are scoped by route and workspace. Keep the same request with each key: reordering or changing its content can change its fingerprint. A completed replay carries `Idempotent-Replayed: true`; work still running answers `409 IDEMPOTENCY_IN_PROGRESS` with job ID and `Retry-After`. A changed request under that key gives `422 IDEMPOTENCY_KEY_REUSED`. Background replay returns 202 with the job’s current state. Once retention removes a key, submitting it can start new work.

## Resolve references before depending on them

Batch attribute-key references require a unique attribute on the named type, scoped to the workspace. They do not match by display name. Import profiles can match non-unique fields, but must resolve them unambiguously to IDs before the write. Order a parent or relationship endpoint before an item that refers to it. Under independent policy, a failed parent does not skip its child: the child is evaluated and gets its own missing-reference refusal.

An upsert does not change an existing record’s type or application. A key finding the wrong type or application is `REFERENCE_TYPE_MISMATCH`; prepare an intentional type change through the supported change-set workflow instead. Omitting a parent on an upsert keeps the found record where it is.

A retained relationship keeps its ID during set replacement. Omitting its attribute values keeps them; supplying an explicit values object replaces them. An empty target set requests removal of all removable members. A set claim is evaluated after the earlier items in the same batch, so it must describe the state at that point. Containment changes use the record’s parent operation; direct containment relationship items are refused as `IMMUTABLE_RELATION`.

Applied outcomes identify the changed record or relationship and its version. A live deletion has no new entity version. Set replacement reports the set version and created, kept and removed relation IDs; these describe the committed membership, not the item’s source-row identity. Page outcomes through the [job operations](/docs/api/?api=management#tag/jobs) when the inline response is incomplete.

Batch previews require background execution. They try items independently even for an atomic policy, then roll the preview back as a whole. The job waits for confirmation; execution starts again at the first stored item. Check whether `JOB_PREVIEW_MAX_ITEMS` (default 10,000) made it a sample. Confirmation carries previewed cascade-deletion tokens and relationship-set versions into execution, so changed impacts or memberships are refused rather than silently adopted.

An unpreviewed relationship-set replacement in a sample has no captured set claim and is refused with `VERSION_REQUIRED` unless execution has a valid explicit claim. Do not treat sample counts as confirmation of every destructive item. A versioned ensure-absence checks the relationship found; without a version claim, it removes that mutable relationship as it stands.

## Propose mapping targets into a change set

The [mapping-proposal operation](/docs/api/?api=management#tag/ai) can prepare targets for the unmapped sources of a declared mapping-grid view. This requires a configured provider, Use AI proposals, Work in change sets with permission to write the mapping, and send level `values`. A proposal never writes live data or publishes. Source and target names and displayed fields go to the provider and can incur charges; [About AI](/docs/run/ai/) explains data handling, costs and retained call records.

Select the application and view, optionally narrowed by search and parent, and choose a new change set or an existing open one with its current version. Follow the returned `aiProposal` job. The provider chooses only among eligible targets: all when there are at most 100, otherwise each source's 20 closest by name and fields. A source with no candidate is not sent. Calls normally contain up to 25 sources; `AI_CONTEXT_TOKENS` reduces them to fit half the configured context window. Fields that repeat the name or contain a generated identifier are omitted.

Read the separate result counts. `proposed` counts prepared targets. `unmatched` includes no eligible or sufficiently confident choice; `changed` means the source's mapping set changed meanwhile and was left alone. `refused` counts targets refused by a rule, and `notAnswered` counts missing answers or failed calls. A provider warning does not turn ordinary mapping work into a failure. Cancelling the job keeps proposals already written.

Review the change set before publication. In the browser, **Proposed** lists the marked targets; each **Proposed by the AI** entry gives the confidence and reason. Correct or remove unwanted targets and publish through the normal approval process. Changing a target makes a new relationship without AI origin. Published history preserves the original proposal's origin, with the publisher as actor.

The [mapping-coverage operation](/docs/api/?api=management#tag/mappings) supports `proposed=true` only with `changeSetId`; without it the refusal is `MAPPING_PROPOSED_NEEDS_CHANGE_SET`. `MAPPING_VIEW_NOT_FOUND` needs an available mapping-grid view in the selected model, and `MAPPING_PARENT_NOT_FOUND` needs a parent in the selected context. `CHANGE_SET_VERSION_CONFLICT` requires rereading the open set. `AI_NOT_CONFIGURED` or `AI_SEND_LEVEL_TOO_LOW` requires operator configuration or ordinary manual mapping; an API request cannot override the send ceiling.
