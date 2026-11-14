---
title: Versions and conflicts
description: Keep concurrent changes safe and recover from stale data or models.
reader: integrator
---

Keep the version you read with the change you intend to make. Updating against that version lets refiroo refuse a stale change instead of silently replacing somebody else's work. The [object](/docs/api/?api=management#tag/objects), [relationship](/docs/api/?api=management#tag/relations), [model administration](/docs/api/?api=management#tag/model%20administration) and [change-set operations](/docs/api/?api=management#tag/change-sets) document their claims.

## Claim what you are changing

Records and relationships have versions. A mapping replacement claims the relationship set, since the membership can change without changing the anchor record. A model draft, change set, release retirement and workspace model activation each have their own concurrency claim. A write inside a change set can need both the record's version and the change set's version.

On `VERSION_CONFLICT`, read the current resource, compare it with your source and decide whether to rebuild or abandon the change. The refusal identifies the current version. Do not simply replace your saved claim with the latest number and send the old change again. More specific failures include `CHANGE_SET_VERSION_CONFLICT`, `RELATION_SET_VERSION_CONFLICT` and `ACTIVATION_CONFLICT`.

A batch update or upsert that would change nothing is reported as unchanged before its version claim. It advances no record version and produces no data-change event. Mapping replacement has a deliberate distinction: a mapping save still checks a stale set token when unchanged, while a bulk set-replacement item can report unchanged before checking it.

## Claim the model as well

Read the model release identity with the model, then use the expected-model-release request header on requests built from it. A `MODEL_RELEASE_CHANGED` refusal means the workspace or context now resolves another release, or it changed during execution. Read the model again and rebuild the request. A live write refused by the commit guard saves nothing. A background job can already have committed earlier chunks: inspect its outcomes before resubmitting.

## Publishing is another comparison

Publishing checks the change set, the workspace's current publication, its model release and the records and mutable relationship sets touched by the changes. Unrelated newer live records are preserved. Record divergences appear as conflicts; a changed relationship set can report `MAPPING_SET_CHANGED`. Review current live data and reapply the intended changes in a new current-live change set when necessary. Revalidating an unchanged conflicting change set cannot resolve its stale base.

`CHANGE_SET_MODEL_RELEASE_CONFLICT` needs an explicit model decision. [Move the change set onto the workspace's release, or migrate the workspace](/docs/integrate/model-and-release-operations/); no implicit rebase happens. Unique-value, cycle and relationship-cardinality checks still apply to racing writers. Retrying must not bypass the rule that refused one writer.

## Use the exact context’s release and version

Model reads identify their release in `X-Model-Release-Id`. Return it as `X-Expected-Model-Release-Id` on management requests built from those definitions. Live requests compare the workspace’s release; change-set and publication requests compare their pinned release. A mismatch is `409 MODEL_RELEASE_CHANGED` before the requested read or write. Details identify the workspace, expected and current release, and the change set where applicable. Without that header, the server still checks the release under which an in-flight write was validated at commit.

A concurrent model switch can also refuse a read with `MODEL_RELEASE_CHANGED`; retry after rediscovery. Read the change-set resource for its current aggregate version: record GET responses do not consistently supply it. Do not infer that claim from a nullable field on another response.
