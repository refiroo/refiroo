---
title: The API reference
description: Find operation contracts and try requests against your instance.
reader: integrator
---

Open the [API reference](/docs/api/) to find the operations, request schemas and responses your integration uses. The pages at `/docs` explain capabilities and sequences; `/docs/api` renders the OpenAPI documents as an interactive reference using Scalar.

## Choose the right source

The reference opens with **Management API** and lists the consumer APIs declared by the selected workspace's model, each with its contract version. Retained earlier versions also have their own OpenAPI documents; their operations are marked deprecated and their introduction names the replacement and any announced sunset day. Select the version your client actually calls. Without an explicit workspace, it uses the default workspace. Reload the reference after changing a workspace's model release so its sources reflect that release. A consumer API missing from this list may belong to another workspace's model; check the workspace before changing your client.

In the browser, **Settings › Connections › API reference** lists the sources, versions and OpenAPI document links. Select a source name to open its reference. You can also open the [management source](/docs/api/?api=management), or discover consumer sources through the [API index](/docs/api/?api=management). See [Discovering the model](/docs/integrate/discovering-the-model/) for selecting a contract programmatically.

The management document describes the engine's management interface. Each consumer API has a separate document describing the contract declared in the model. A response containing business objects shows **One of** in its schema: choose a type to see only its fields, with objectType marked as the discriminator. Under **The answer.**, the named example picker offers one example per exposed type; a list offers its own type’s example. These examples are generated from field types without reading records. Use those documents for generated clients and validation; the guide does not duplicate their schemas.

## Try an operation

The console sends real requests to the instance that serves it. When you are signed in in that browser, it starts with your identity and permissions and renews its console token while needed. A successful request can change data, start a job or publish a change when your permissions allow that operation.

To exercise an integration's access, supply its client token instead. A token you paste replaces the console's automatic token and is not renewed for you. Without a browser session, supply a token before trying protected operations. Consumer data requires a client token with the consumer audience and an API grant in the workspace; the browser identity alone cannot read it. Follow [Get a token](/docs/guide/integrate/get-a-token/) and [Read through a consumer API](/docs/guide/integrate/read-through-a-consumer-api/).

If the reference opens but the request is refused, inspect the operation's error and your [permissions](/docs/integrate/security-model-for-integrators/). If only management appears, the workspace's model may be unavailable or declare no consumer APIs. Check its [model context](/docs/integrate/workspaces-contexts-and-models/).

## Use it without internet access

The reference script is bundled with the engine by default. It does not need an external font, hosted client or telemetry service. An operator can instead select the pinned CDN script; that mode needs internet access from the browser. See [Configuration](/docs/run/configure/) for deployment settings.

The bundled reference uses Scalar 1.72.2. The operator can set `RDM_API_REFERENCE_SCRIPT=cdn` to use the pinned jsDelivr copy, checked by its integrity hash; `bundled` is the default. A pasted token is used as supplied, so use a consumer client token when trying consumer data operations. Consumer source links use `api=consumer-<name>-v<version>` and can include the intended workspace.

The [consumer index](/docs/api/?api=management) marks retained entries with `deprecated: true` and an optional `sunset`. These entries remain callable until a model release explicitly stops them. See [Earlier contract versions](/docs/integrate/consumer-apis/#earlier-contract-versions) for response headers and stopped-version errors.
