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

`ACTIVATION_CONFLICT` requires a fresh assignment read. `MODEL_MIGRATION_REQUIRED` means data needs reviewed conversion. `CONSUMER_CONTRACT_VERSION_REQUIRED`, `CONSUMER_CONTRACT_VERSION_DECREASED` and `CONSUMER_API_REMOVED` prevent silently breaking consumer contracts. A release change can leave open change sets on their old pin and pause incompatible subscriptions. Inspect both consequences.

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
