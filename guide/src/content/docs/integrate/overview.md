---
title: Integrating with refiroo
description: Choose the interface and sequence your integration needs.
reader: integrator
---

Use refiroo's APIs to read reference data, supply changes or keep another system in step. Choose an interface by the contract your system needs, then give that system its own [client identity](/docs/administer/clients/).

| Your task | Start with |
| --- | --- |
| Work with records, relationships, models or change sets | The management API in the [API reference, objects and model tags](/docs/api/?api=management#tag/objects) |
| Read a stable business contract without knowing the underlying model | [Consumer APIs](/docs/integrate/consumer-apis/) |
| Load many changes or exchange a file | [Bulk writes](/docs/integrate/writing-in-bulk/) and [files](/docs/integrate/files-imports-and-exports/) |
| Maintain a local copy | [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/) |
| Receive notifications at your endpoint | [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) |

The management API exposes the model and its runtime capabilities, including operations the browser does not use. Its names come from the model; applications and record types are configuration. Consumer APIs present selected business objects under names and versions declared by a model administrator. They are read-only.

Bulk writes, imports and exports produce [jobs](/docs/integrate/jobs/). A successful HTTP request can still contain refused items: inspect the job result. The raw change feed identifies changes without carrying values; consumer events identify affected business objects and can include their current representation.

Start by [getting a token](/docs/guide/integrate/get-a-token/), [discovering the model](/docs/integrate/discovering-the-model/) and learning [paging and errors](/docs/integrate/identifiers-paging-and-errors/). For reviewed changes, use [change sets and publication](/docs/integrate/changes-approvals-and-publication/).

The documentation is at `/docs`. Operation details, request schemas and examples are in the [API reference](/docs/api/). These pages explain which operations to combine and how to recover when a sequence cannot finish.
