---
title: Model and release operations
description: Author models, activate releases and review migrations or moves through the API.
reader: integrator
---

Use model operations to shape what a workspace can hold. Installing a release and activating it are separate steps. Data changes in a change set are another lifecycle. Read the [model authoring operations](/docs/api/?api=management#tag/model%20administration), [release operations](/docs/api/?api=management#tag/model) and [workspace model operations](/docs/api/?api=management#tag/workspaces) for their contracts.

## Author, validate and install

A model draft changes through typed operations naming elements by key. One request's operations apply in order, all or none, and form one history step. A draft can be temporarily invalid while being assembled; inspect its diagnostics and validate before installation. Installation refuses an invalid model. Whole-model editing is also recorded as a step.

Read the outline, expanded model and operation history as needed. Undo applies inverse operations; later steps depending on a removed element must be undone first or together. `OPERATION_HAS_DEPENDANTS` identifies those steps. `NOTHING_TO_UNDO`, `NOTHING_TO_REDO` and `NOTHING_TO_APPLY` mean refresh the history rather than inventing another change. `INVALID_OPERATION` and `OPERATION_BATCH_TOO_LARGE` require a valid bounded operation request. `OPERATION_REQUIRES_MIGRATION` means an existing released element needs a migration instead of a draft-only edit.

Attached source files can be profiled, bound and dry-run without writing data. Deterministic inference can propose bindings for review; its job is separate from applying proposals. `INFERENCE_NOT_FOUND`, `INFERENCE_NOT_READY` and `INFERENCE_STALE` require a current completed inference. `PROPOSAL_NOT_FOUND`, `PROPOSAL_ALREADY_APPLIED` and `PROPOSAL_REQUIREMENT_MISSING` require reviewing the proposal and its prerequisites. `INVALID_INFERENCE_REQUEST`, `DRY_RUN_NOT_FOUND` and `IMPACT_SUMMARY_DRAFT_INVALID` require correcting or rerunning the relevant model check. See [Workbook onboarding](/docs/model/workbook-onboarding/).

Compilation checks the draft against its base release, or its model's latest installed release when it has no base. It reports contract changes and workspace compatibility. Installing saves an immutable release but does not activate it. If activation subsequently fails, that installed release remains. `MODEL_DRAFT_NOT_FOUND`, `INVALID_MODEL`, `MODEL_HASH_CHANGED` and `RELEASE_IDENTITY_CONFLICT` require the intended validated draft and release identity, not a forced overwrite.

## Activate in one workspace

Read the workspace's current assignment and claim its version and release when activating. Other workspaces keep their assignments. Read placements in the target context to discover allowed root types, children and replacement types; parent candidates can be narrowed without losing truthful totals.

`ACTIVATION_CONFLICT` requires a fresh assignment read. `MODEL_MIGRATION_REQUIRED` means data needs reviewed conversion. `CONSUMER_CONTRACT_VERSION_REQUIRED` and `CONSUMER_CONTRACT_VERSION_DECREASED` refuse incompatible version choices. `CONSUMER_API_REMOVED` is a warning: removing the whole API is allowed and ends its address after activation. A release change can leave open change sets on their old pin and pause incompatible subscriptions. Inspect both consequences.

`MODEL_RELEASE_NOT_FOUND`, `MODEL_RELEASE_RETIRED`, `MODEL_RELEASE_IN_USE` and `MODEL_RELEASE_IS_DEFAULT` require choosing or retaining an eligible release and resolving its assignments before removal. `MODEL_RELEASE_VERSION_CONFLICT` needs its current version. `UNSUPPORTED_SCHEMA_VERSION`, `UNSUPPORTED_PINNED_MODEL_SCHEMA`, `PINNED_MODEL_INVALID` and `PINNED_MODEL_UNAVAILABLE` require a supported valid release. Stored-release raising is a maintenance operation with its own refusals (`RELEASE_NOT_RAISABLE`, `RELEASE_RAISE_REFUSED`); see [Model language versions](/docs/model/model-language-versions/).

`MODEL_REGISTRY_REFRESH_FAILED` after activation means the change committed but the serving process could not load it. Have the operator recover the registry before resuming; do not assume the activation rolled back. `MODEL_REGISTRY_UNAVAILABLE` means the named workspace's model cannot currently be served.

## Migrate reviewed data

Start a workspace migration as a job, inspect conversion, reclassification, loss and refused rows, then confirm the exact reviewed assignment and feed position. Type mappings explain which old types and attributes become which new ones; unmapped content can be lost. Accept loss explicitly only after reviewing it. Execution converts and changes the workspace's release in one transaction.

`INVALID_MIGRATION_MAPPING`, `INVALID_TYPE_MAPPING` and `INVALID_CLEAR_ATTRIBUTES` require a valid mapping and clearing instruction. `MIGRATION_HAS_REFUSALS` requires correcting data and previewing again; `MIGRATION_LOSS_NOT_ACCEPTED` needs a deliberate loss decision. `MIGRATION_REVIEW_STALE` requires a new preview after intervening data or model changes. `MIGRATION_TARGET_IS_CURRENT` needs no migration. `MIGRATION_FAILED` changes nothing from that execution and supplies the failure reference.

A change set pinned elsewhere has two explicit options. If its content already fits, change its pin after validation. Otherwise migrate the change set onto the workspace's release, or migrate the workspace to the change set's release and publish it together. The target restrictions are `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE` and `MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`. Moving a change set changes its prepared content and base, not live data; migrating the workspace and publishing does both atomically. See [Migrations](/docs/model/migrations/).

## Transfer between models

A model mapping maps source types, attributes, relationships, parent placement, value conversions, defaults and target matching. Its [operations](/docs/api/?api=management#tag/model%20mappings) have versions, history, undo and redo. Read its problems and coverage against the releases involved. `INVALID_MODEL_MAPPING`, `MODEL_MAPPING_EXISTS`, `MODEL_MAPPING_NOT_FOUND`, `MODEL_MAPPING_MODEL_MISMATCH` and `MAPPING_VERSION_CONFLICT` require the correct current mapping.

Start a [move or copy](/docs/api/?api=management#tag/moves) with a source context and explicit selection. Selection does not automatically pull every related record into scope. The dry run reports created or updated records, refused items, items not moved, uncarried values and possible duplicates. It matches origins, counterparts and then the declared match before creating a target record. Values convert under the target model's rules.

Confirmation loads the source as previewed into a new target change set, reevaluating target rules. It does not make data live. A move can also prepare source deletions, retaining source records changed meanwhile or needed by records left behind. Publish the target copy first; `MOVE_COPY_NOT_PUBLISHED` blocks source deletion before that. Consumers see each side only after publication.

`MOVE_SAME_WORKSPACE` needs two workspaces; `MOVE_MAPPING_CHANGED` needs another dry run; `MOVE_MAPPING_HAS_PROBLEMS` needs a corrected mapping; `MOVE_NOTHING_TO_MOVE` means no proposed target changes can load. Follow [Move records between models](/docs/guide/integrate/move-records-between-models/) and [Model mappings](/docs/model/model-mappings/) for the task and design choices.

## Review release status separately from content

A release’s content is immutable; its active or retired status has a separate version claim. Retirement stops new selections but leaves workspaces and change sets already using it operational. The default workspace’s release cannot be retired. Reinstalling the exact content of a retired release restores it. Ask for usable releases when choosing a new assignment: that excludes retired releases and unsupported schema versions.

Deletion requires no remaining references. The release reports whether deletion is allowed and the first blocker: a running workspace, history, an import profile or a model mapping. Inspect those references rather than assuming retirement makes deletion possible. Release activation history records selections, oldest first; installation order and bootstrap do not prove an activation occurred.

A structural diff can use a selected installed baseline while activation compatibility still checks the target workspace’s current data and release. Additions omit the before side; removals omit the after side. An omitted side differs from a present null value. Compilation reports compatible, migration-required or invalid; diagnostics have severity and a JSON Pointer, and compatibility findings can also give the affected count. Identical installation can return the existing release; it still does not activate it.

## Draft steps and generated documents

Draft operation requests are bounded by `MODEL_OPERATION_MAX_ITEMS` (default 500). A key omitted for a new element is generated from its name, using lowercase hyphenated ASCII and a numeric suffix on collision. An explicit rename of an unreleased key rewrites references, including consumer definitions. Removing a referenced element can leave issues to repair in those definitions. Inspect diagnostics after every step.

Draft-only changes to released structures may require migration. A stale draft-version refusal can include up to 100 intervening operations and a continuation to history. Undo respects dependencies and reverses an entire step. A new request or whole-model edit after undo clears redo; installing does not. Installation makes the installed content the draft’s base without changing its content version.

The outline remains useful while a draft is invalid: it shows what structure can be read and attaches diagnostics to elements. A compiled draft model supplies placements but no records; reads of real records still use a running workspace model. A new type therefore has no live sample merely because its draft can be previewed.

For a consumer declaration, the draft offers its authored and expanded definitions, compatibility findings, a JSON Schema 2020-12, a type-based message example and an OpenAPI document. Generating these is read-only. Examples do not read records. Invalid drafts refuse the three document downloads with `INVALID_MODEL` and diagnostics. Use the [model-authoring reference](/docs/api/?api=management#tag/model%20administration) for operations and downloads.

## Review conversions and loss

Migration previews distinguish conversion, reclassification, loss and refusal. A target lacking a source type can lose its records; a type moving to an application must have an unambiguous destination or an explicit type mapping. Mapping named attribute sources takes precedence over same-key fallback. Records that survive retain their public identity and history; publications retain their original release.

Supported value conversions include text and long text, integer to decimal, integral decimal to integer, values to their stored text form and parseable text back to the target type. A date converts to midnight UTC; an instant converts to a date only at midnight UTC. Values can convert to JSON, and text to JSON only when parseable. Review individual losses and refusals instead of assuming a declared conversion succeeds for every value. A migration preview can hold writes to the records being converted until it ends.

Confirmation claims the reviewed assignment and feed position and explicitly accepts any loss. A stale review writes nothing. Migrating a workspace and publishing a change set can be one atomic execution: publication failure leaves the migration unapplied. Moving a change set onto its workspace’s model instead converts that prepared content, replaces its base with current live data and advances its version once; it does not write live records, feed positions or publications. Conflicts with newer live work must still be resolved.

A model mapping names its source and target releases. One source type maps to one target type; several source types may share a target. Defaults fill missing source values, not values already supplied. Inspect coverage for unmapped source content and required target content left unfilled. Deterministic inference proposes mappings from keys, names, compatible attributes, relationships and stored records; review the evidence and apply only the proposals you intend.

A move’s selection combines its type criteria, subtree and explicit IDs; it does not pull every parent or related record along. The default is a complete preview in copy mode. Source values are fixed when previewed; target writes are decided again during loading into a new change set. A source record changed since the preview is retained when preparing source deletion, as is a record still needed by content left behind. Refused or unselected records are not silently deleted.

## Ask for an account of a model change

Before activating a release or applying a draft, the [impact-summary operations](/docs/api/?api=management#tag/ai) can explain its effects in a workspace. They require Activate model releases and Use AI proposals there, with a configured provider. The engine computes model differences, data-rule failures and counts, consumer-contract effects, activation blockers and records per touched type. The provider words those facts; it does not decide whether a change is safe or approve it.

The model changes and counts go to the provider, without record values. This is available at every send level and can incur provider charges. Facts and wording are cached for an hour for the same request; a cache hit makes no second call. [About AI](/docs/run/ai/) explains what is sent, call records, costs and retention. Do not send a request until the person asks for the explanation; the browser action is **Explain this change**.

Present every returned fact alongside the statements and their citations. Statements without valid fact references are removed and counted. A failing provider can still return HTTP `200` with all facts, no statements and a `failure`; show the facts and the failure instead of an empty success. No explanation activates anything. Continue through the ordinary preview, review and activation operations only after the person's decision.

`IMPACT_SUMMARY_DRAFT_INVALID` requires correcting and validating the draft. A stale draft version requires rereading it. Missing draft or release refusals require an existing accessible resource. A summary is not attached permanently to a release and is not a substitute for migration preview.

For changes proposed from words or a workbook, use [Assistant tasks](/docs/integrate/assistant-tasks/). A result can lead to migration, a change set or staged release activations; those remain explicit actions by a person.
