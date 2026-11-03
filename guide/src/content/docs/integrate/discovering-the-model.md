---
title: Discovering the model
description: Discover available capabilities and resolve the model before using its records.
reader: integrator
---

Discover the model in the context you plan to use. A type or relationship available in one workspace might not exist in another. Do not hardcode an application from the example data as a product feature.

Start with [capabilities and model operations](/docs/api/?api=management#tag/model). Capabilities tell you which operation groups are enabled and the configured limits. The model tells you which applications, object types, globally reusable attribute types, relation types, allowed type pairs and views exist. Metadata collections page like other collections and individual definitions can be read by stable key.

Read the full model when you need its declarations together. Use the placements read for the types permitted at the root, under a parent or as a record's replacement type. Those answers depend on context; do not infer them from a type's name.

Keep the returned model release identity. Use it to protect later requests built from that model, as explained in [Versions and conflicts](/docs/integrate/versions-and-conflicts/). A change-set or publication model read follows that context's pin. The [installed-release operations](/docs/api/?api=management#tag/model) let an authorised caller inspect other releases; an installed release need not be running in a workspace.

## Discover a consumer contract

Read the authenticated [consumer API index](/docs/api/?api=management#tag/consumer) for the intended workspace. It pages the available API names and contract versions and supplies their OpenAPI document addresses. Open the selected contract in the [API reference](/docs/api/). Each consumer API has its own OpenAPI 3.1 document; it is not part of the management OpenAPI document. The management document also describes the model document and its schema language.

The management [consumer definition read](/docs/api/?api=management#tag/model) gives an expanded declaration with defaults made explicit and supports conditional reads. Use that for model inspection. Integrations consuming business data should bind to the declared contract, not reconstruct its output from source fields.

`UNKNOWN_APPLICATION`, `UNKNOWN_OBJECT_TYPE`, `UNKNOWN_ATTRIBUTE_TYPE` or `UNKNOWN_RELATION_TYPE` require checking the chosen release and key. Statuses differ between some live routes and change-set diagnostics; handle the machine code in the operation's documented context. A model-registry refusal needs operator recovery, not a fallback to guessed metadata.

## Inspect the contract in the browser

**Settings › Integration › Consumer APIs** is a read-only catalogue for people with Browse. It shows the contract's name, version, base address, OpenAPI document, exposed types, lists and events. **Open the release** and **Open model** lead to the declaring model; they do not grant permission to edit it. Its **Change feed** section describes retention. Use the [consumer reading pages](/docs/integrate/consumer-apis/) for explanations and complete example exchanges, the [model administrator's page](/docs/model/consumer-apis/) for designing the declaration, and [The API reference](/docs/integrate/api-reference/) for trying operations.

## Separate semantics from allowed placements

A relation type defines forward and reverse meanings and orientation. Its allowed type pairs supply cardinality, required status, relation attributes and binding features. Discover those bindings instead of assuming that any two types may use a known relation type. Application navigation groups are presentation metadata; they do not scope API records or add a filter.

Capability groups identify the deployment setting that enables them. A capability describes what the deployment supports, not what the current caller is allowed to do. Disabling model mutations retains release reads, validation and diff while removing draft/installation/activation routes. Read permissions still apply. Inspect the expanded consumer definition for resolved public names, code-source match rules, default filter matches, list parent types and generated events; do not duplicate that expansion in a client.
