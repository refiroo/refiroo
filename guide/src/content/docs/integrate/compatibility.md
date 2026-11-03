---
title: Compatibility
description: Build a client that survives additions to an API contract.
reader: integrator
---

Build your integration against a documented API contract and tolerate additions to its responses. refiroo's compatibility commitment applies from version 0.12.0. Before 1.0, security fixes cover only the latest minor release; an interface commitment is separate from that maintenance window. Use the [API reference](/docs/api/) for the contract your instance serves.

## What stays compatible

The commitment covers the management API's documented operations, request and response shapes, status and error codes; consumer API contracts; change events and webhook payloads, headers and signature verification; and documented sign-in and token interfaces. Deployment setting names, meanings and defaults, and documented operator commands also have a compatibility commitment.

The commitment requires a breaking change to be offered alongside the old interface. Its removal notice must allow at least **12 months and two minor releases**. Management paths, consumer contract versions and event types provide separate version boundaries. A consumer API's contract version is independent of the model release that declares it. Check [current consumer version serving](/docs/integrate/consumer-apis/#discover-and-obtain-access) before coordinating an activation: the current implementation selects the workspace's declared version, so a version increase alone does not retain an old live route.

Database tables, internal modules, browser layouts and browser addresses are outside this commitment. Use an API to connect another system, rather than querying tables or automating a screen's address. Stored-release raising is a maintenance exception to the API and command commitment; see [Model language versions](/docs/model/model-language-versions/).

## Additions your client must accept

An optional request field whose absence preserves behavior is additive. So are new operations, response fields, event types, headers and response enumeration values. A more specific error code can replace a general code for a request that already failed with the same status.

Removing or renaming a contract element, changing its type, meaning, unit or default, requiring an optional input, refusing a previously accepted request, changing response status or changing signature, token or cursor verification is breaking. Adding a value that a request must send is also breaking.

Make these rules part of your client:

- Ignore unknown fields in responses, events and tokens. Consumer response objects permit additional fields.
- Handle unknown response enumeration values as an unknown case. Handle an unknown error code by HTTP status rather than failing to parse the response.
- Keep cursors opaque and return them unchanged.
- Accept a comma-separated webhook signature header and verify any supported signature in it during key rotation.
- Keep requests within their published schemas. Unknown query parameters and closed request bodies are refused; response tolerance does not make arbitrary request fields valid.

See [Identifiers, paging and errors](/docs/integrate/identifiers-paging-and-errors/) and [Webhook verification](/docs/integrate/consumer-events-and-webhooks/#verify-before-accepting) for the corresponding sequences.

## Reserved extensions

The commitment reserves room for a retired record to point to a surviving record, a value to describe its source, a read-only value computed from related records, and new value types. These reservations describe what a client must tolerate when such extensions appear; they are not operations to use today. Avoid assuming every unknown ID always has the same outcome or every returned value is writable. A client encountering an unknown value type can display it as text and must not write it.

## Model language versions are separate

Before 1.0, the engine's readable model-language window can change at each release without the API notice period. The engine can raise eligible stored definitions to its supported language; an exported model file needs the author to update it. Read the instance's [capabilities and model metadata](/docs/api/?api=management#tag/model) and follow [Model language versions](/docs/model/model-language-versions/) before installing a definition from another version.

The compatibility commitment gives the model language a major-release removal boundary from 1.0. For integrations running now, check the supported language on the actual instance rather than deriving it from the management API or consumer contract version.

## Notices and supported model files

The commitment names `Deprecation` (RFC 9745) and `Sunset` (RFC 8594) as the response headers for a deprecated interface. Check release notes for announcements and migration instructions. There is no currently deprecated API version to exercise these headers against; do not infer an extended support window merely because a response lacks them.

For model files, the current engine reads and writes schema `0.10`. Versions `0.5`–`0.9` need raising; `0.4` and earlier cannot be carried forward by this mechanism. Stored-release raising preserves records, history, change sets and publications. Use [Model language versions](/docs/model/model-language-versions/) for the browser procedure and [Model operations](/docs/integrate/model-and-release-operations/) for integration access. Before 1.0, raising stored releases is a maintenance exception to the committed API and CLI. Do not use its current implementation as a permanent integration contract.
