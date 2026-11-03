---
title: Sharing data with other systems
description: Read, load and follow shared reference data through governed interfaces.
reader: evaluator
---

refiroo is API first: everything the browser does is available through the API. Consumer APIs give other systems a common way to read agreed data, with a consistent shape within each contract. Systems can also load corrections and follow changes under the same model rules and permissions as browser work. See [What refiroo is](/docs/about/what-is-refiroo/) for the overview.

## Maintain data or consume it

The **management API** exposes the capabilities used by the browser: records, fields, relationships, models, workspaces, change sets, publications and history. Integrations can maintain reference data through it without automating screens.

A **consumer API** provides a read contract declared in the model. It presents the fields and related records a consuming system needs under agreed public names. Systems can read lists, look up values by their identifiers and resolve a code to another representation where the model declares that operation. A separate contract version protects consumers when the model evolves.

Consumer APIs share a consistent way to present data and read it. Within a contract, every kind of record comes in the same form, with its selected fields and related information together. A consuming system can reuse the way it reads lists, looks up a value, handles an error and follows changes across the consumer APIs your organisation declares. A new kind of record does not need its own reading process.

The model chooses what is shared; refiroo supplies the common patterns. Public names and available operations can differ between contracts, so the consuming system still needs to know the contract it reads. Its own contract version lets that agreement stay stable while the underlying model changes.

A client needs a grant for the particular consumer API in the particular workspace. A management role alone does not give consumer access, and a consumer grant does not permit management operations. See [Consumer APIs](/docs/integrate/consumer-apis/) and [Who can do what](/docs/about/people-and-access/).

## Choose the state to read

Normal reads return Live data. A publication provides a fixed snapshot for an extract that must remain consistent while live editing continues. A publication read uses a compatible consumer contract; it cannot automatically be reinterpreted through any later contract.

Where a record type declares a validity period, an integration can ask which records are valid on a business date. This is a question about the data's declared dates, separate from asking what was stored in the past. See [Business dates](/docs/integrate/business-dates/) and [Reading records](/docs/integrate/reading-records/).

## Exchange files and larger loads

Scattered spreadsheets can become an agreed list: upload an existing workbook, map its columns through an import profile and check a preview before loading; a workbook can also start a model draft and load into a change set. See [Workbook onboarding](/docs/model/workbook-onboarding/) for that starting point.

Files let people review data in a workbook and bring changes back. Integration loads can create, update, connect and remove records in bulk, either together or with a result for each independent item. Background jobs report progress and refusals. A preview helps check the intended effect before applying it; an import is still subject to type, uniqueness, relationship and access rules.

See [Imports and exports](/docs/use/importing-and-exporting/) for browser work and [Files, imports and exports](/docs/integrate/files-imports-and-exports/) for integration choices.

## Keep another system in step

The change feed records live changes in order. A system remembers where it stopped and continues from there. Prepared changes appear when published, rather than while someone is working on them. If the saved position has expired, the system must load a suitable publication and resume from its position.

Webhooks push model-declared events to a receiver. Deliveries are signed, retried on failure and may arrive more than once. Receivers must recognise repeated events and verify signatures. These events do not include the author's identity; management history does. See [Following changes](/docs/integrate/following-changes/) and [Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/).

Start implementation in [Integrating with refiroo](/docs/integrate/overview/). The [API reference](/docs/api) describes the available operations and their exact contracts.
