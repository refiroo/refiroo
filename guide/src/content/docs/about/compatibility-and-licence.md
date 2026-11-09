---
title: Versions, compatibility and licence
description: Understand the compatibility commitment, model language window and source offer.
reader: evaluator
---

The software version, a model release and a publication number describe different things. **Settings → About** shows the running engine version, management API version, supported schema languages, licence, source address and active model release. A workspace's own model release determines the definition its data uses. About is available to
signed-in people; the additional Deployment and Operations pages need Operations permission. See
[About, Deployment and Operations](/docs/administer/deployment-pages/) for reading these details.

## What stays compatible

From 0.12.0, refiroo commits to additive evolution of its documented management API, consumer API contract versions, change events and webhook formats, sign-in contracts, deployment setting names and documented commands.

An addition preserves existing behaviour: for example, a new optional choice or an extra field in an answer. Integrations must tolerate additions they do not recognise. Removing a choice, changing a field's meaning or type, making an optional input required or refusing a previously accepted request is a breaking change.

For contracts published by refiroo, a breaking replacement must be offered alongside the old contract. The old version stays available for **at least twelve months and two minor releases after the deprecation announcement**. This protects existing callers while their owners arrange an update.

Your organisation’s consumer APIs are defined by its model administrator, who chooses the
notice period with the consuming teams. Earlier contract versions can remain available
beside the new one, reading current data in their original shape. An announced sunset day
does not stop service automatically: the administrator explicitly stops the version through
a model release. See [Consumer APIs in the model](/docs/model/consumer-apis/#keep-an-earlier-version-available).

The commitment does not freeze screen layouts and addresses, internal code or database tables. Integrations use the public contracts rather than the database. See [Compatibility for integrators](/docs/integrate/compatibility/) for caller responsibilities and [Upgrades](/docs/run/upgrades/) for operational planning.

## Model languages have a separate window

A model release versions the definition your team installed. Its **schema language** describes the format refiroo understands. Neither is a publication number or a record's editing version.

Before 1.0, each software release reads the schema language it writes; unused older languages can leave the supported window without the contract notice period. Stored models have a raising procedure, while an unsupported workspace may need administrator or operator recovery before it can be opened. Do not assume an old model remains usable merely because an API contract stays compatible.

From 1.0, a language version leaves the window only in a major release, with the notice period and an offline upgrader for stored releases and publications. See [Model language versions](/docs/model/model-language-versions/) for the currently supported window and recovery choices.

Before 1.0, only the latest minor software release receives security fixes. See the project's [security policy](https://github.com/refiroo/refiroo/blob/main/SECURITY.md).

## Licence and corresponding source

refiroo is offered under the **GNU Affero General Public License, version 3 or later**, shown as **AGPL-3.0-or-later**. The [licence text](https://github.com/refiroo/refiroo/blob/main/LICENSE) contains its terms, including the corresponding-source offer for people interacting with a modified version over a network in section 13.

The account menu offers **Source code**, and **Settings → About** shows the source address and licence. The default source address points to the running software's release tag. For a modified installation, its operator must point that offer to the corresponding modified source. Changing the address does not itself publish that source. Operator instructions are in [Licence and source](/docs/run/licence-and-source/).

Source availability and permission to use the refiroo name and artwork are separate: see the [trademark policy](https://github.com/refiroo/refiroo/blob/main/TRADEMARKS.md). Separate [commercial terms](https://github.com/refiroo/refiroo/blob/main/COMMERCIAL.md) are also offered.

## Taking part

Bug reports, questions and discussion are welcome. Outside code contributions are not currently merged while the contributor agreement is absent. Check the [contribution policy](https://github.com/refiroo/refiroo/blob/main/CONTRIBUTING.md) before preparing code, and report security vulnerabilities privately through the security policy.
