---
title: Model language versions
description: Understand unsupported model definitions and when to ask an operator for help.
reader: model-admin
---

A model language version says which definition format refiroo can read. It is separate from
the model's release version, the draft's editing version and each consumer API's contract version.
The current supported model language is **0.10**. The release and workspace screens show it as
**schema**. See [Releases](/docs/model/releases/) for selecting usable releases.

Installation, activation and workspace creation refuse releases outside the supported window.
A historical release can still have readable metadata and an export even when semantic comparison
is unavailable. A workspace whose language cannot be served reports **Cannot be opened**;
this does not mean its records have been deleted.

Use the browser repair below where offered, or ask the operator to inspect the reported model
language and the version of refiroo running the instance. Older stored definitions have an offline procedure that first reports whether they
can be raised to the supported language. It leaves definitions that cannot be converted validly
or would duplicate another release and reports them. This is a deployment operation, not the
browser's **Raise contract version** action. See
[Model releases and rollback](/docs/run/model-releases-and-rollback/) for the operator's procedure.

A definition from a newer language needs a refiroo version that supports it. Changing its displayed
version or editing the language number alone does not convert it. If no workspace can be served,
or the configured startup model is outside the window, the operator must recover the deployment
before browser work can continue. Ordinary data [migrations](/docs/model/migrations/) and updating
the model document's language solve different problems.

## Reopen an older-language workspace in the browser

Where conversion is available, **Bring it up to date** offers **Review the change…** to someone
with instance-level model installation permission. Follow
[Raise a model language version](/docs/guide/model/raise-a-model-language-version/) to preview
and **Raise and reopen**. It lists every workspace using the release and leaves records, history,
change sets and publications unchanged. This recovery is a special in-place definition update;
ordinary model editing continues to create immutable releases. If the browser cannot offer the
repair, use the operator path above.
