---
title: See a consumer API’s documents
description: Review the output shape, example and operations, then hand over the active contract.
reader: model-admin
---

Review the generated documents before asking another team to build a connection. The
schema describes the business object's fields; the message example illustrates that shape;
the OpenAPI document describes the offered requests and their responses. Together they
show what your consumer declaration produces. See
[Consumer APIs in the model](/docs/model/consumer-apis/) for how each choice affects the output.

You need access to the model draft to inspect its documents. Editing needs **Model authoring**.
Viewing a document is separate from giving a consuming client permission to read workspace data.

## Review the draft's output

1. In the model editor, select **Consumer APIs**, then the API. Check the selected API's
   name and **Contract version**. You are reviewing a draft; its changes are not yet live.
2. Open **Schema**. Compare the field names and types with **Fields**. Check required and
   nullable values, the parent and the shape of each related block. A single related
   record is an object or null; a many-valued relationship is an array. Review the whole
   object, because Get by ID, list items and lookup results share this shape.
3. Open **Message example**. It shows one object generated from the declared field types,
   not a record fetched from a workspace. Check that all intended fields and related
   blocks are present. Do not use the placeholder values as evidence that real records
   have those values, or that a lookup finds a particular record.
4. Use **Copy**, **Download schema.json** or **Download example.json** to share the
   selected document. Check the API and contract version before handing it over. After
   any draft edit, inspect the newly generated documents again.

![Generated schema tab for a draft consumer API](/docs/screens/model-consumer-tab-schema.png)

Above: the schema generated for Stops API in the reference model.

**Example of what the schema tells a consuming team.** The reference API's stopNumber
field allows an integer or null. This is an excerpt of the generated document, shown for
review rather than something to enter in the editor:

```json
{
  "stopNumber": {
    "type": ["integer", "null"]
  }
}
```

The name comes from **Output name**, the integer comes from the selected stop-number
source, and null is possible when no source or default supplies a value. The schema
also describes operator as an object or null and modes as an array. These shapes are
part of what consuming teams rely on.

![Generated message example with placeholder values](/docs/screens/model-consumer-tab-example.png)

Above: the reference API's generated example. Its values illustrate types, not live data.

For example, the current generated example includes `"name": "Example name"` and
`"stopNumber": 1`. An integrator reading the real Chur stop instead receives
`"name": "Chur"` and `"stopNumber": 8509000`. The example can choose any exposed type
and fills fields with type-based placeholders; it does not describe a realistic record
of that type. Compare the [full Chur response](/docs/model/consumer-apis/#the-business-object-consumers-read)
when agreeing how the API represents actual data.

## Review the operations as well as the object

1. Return to **Schema** and find **Against what consumers read now**. Read any compatibility
   diagnostics. **Compatible: consumers of version … notice nothing they rely on** means
   this check found no incompatible change; it is not a live connection test.
2. Choose **download the draft's OpenAPI** beneath the compatibility information. This
   document includes the operations, parameters and response shapes, rather than just
   the business object. Share it with the integrator alongside the schema and example.
3. Compare the offered operations with **Operations** and their parameter names with
   **Filters**. Check list scope and ordering, lookup rules, events and contract version.
   An object schema alone cannot tell a consumer which list or filter to use.
4. If a change needs a higher contract version, follow
   [Raise a contract version](/docs/guide/model/raise-a-contract-version/), then download
   the documents again. Agree the new address and changeover with consuming teams before
   activation. A version increase does not keep the previous live endpoint alongside it.

**Example of what an integrator checks.** Stops API at contract version 1 gives the
following request for the real Chur stop:

```http
GET /api/consumer/stops/v1/objects/745c1a52-8405-4158-8f3b-b9e9c8b979be?workspace=graubuenden
```

It returns the declared business object. The list operations return pages containing that
same shape; XREF adds a match score; Resolve returns individual outcomes; events identify
changes to the outputs you chose to watch. Use the worked examples in
[Consumer APIs](/docs/integrate/consumer-apis/),
[Reading business objects](/docs/integrate/reading-business-objects/),
[Looking up and resolving](/docs/integrate/looking-up-and-resolving/) and
[Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/) to review these
results with the integrator. Every organisation's declaration is its own contract: use
your API's generated operation document, not another API's example, for the final handover.

## Hand over the active contract

1. After the release is installed and activated, open **Settings › Integration › Consumer APIs**.
   This read-only page names the active release. Use **Open the release** to check it is
   the release you intended; it does not provide the draft's Schema and Message example tabs.
2. Find the API's section and version. Use **Base URL** and **OpenAPI document** to copy
   its addresses or open the document. The **Route** / **What it does** table lists its
   operations; a route description opens that operation in the API reference.
3. Give the integrator the active API's base address and operation document, the workspace
   they should read, and the agreed contract version. Ask the security administrator to
   confirm the client has this API's grant in that workspace. A model release does not
   create grants, and a role alone does not open consumer data.

![Active consumer API with release, version, base address, operation document and routes](/docs/screens/model-consumer-active-documents.png)

The active API also has an index and its own OpenAPI document on the instance. For the
reference API, the index is `/api/consumer?workspace=graubuenden` and the document is
`/api/consumer/stops/v1/openapi.json?workspace=graubuenden`. These are addresses to hand
to an integrator, not fields to fill in the model editor. See
[Consumer APIs for integrators](/docs/integrate/consumer-apis/) for discovery and authentication.

## If a document is unavailable

- **The draft has issues** means the documents cannot be generated. Open **Issues**,
  correct the problem or undo the last step, then return to the document. Raising a
  contract version does not repair an invalid definition.
- A document load error is not a successful review. Read the message, correct the cause
  if it names a draft problem, then retry. If copying is unavailable, select the text
  or download the file instead.
- **The active release declares no consumer API** means the active model has none.
  Use **Open model** to inspect its definitions. A draft API is not live merely because
  its documents can be generated.
- If a live read is refused, check the workspace, API grant and active contract with the
  integrator. The OpenAPI document itself is readable without signing in; opening it
  successfully does not prove that the client can read data.
