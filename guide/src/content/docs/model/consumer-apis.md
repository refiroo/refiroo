---
title: Consumer APIs in the model
description: Define the types, fields and read operations that other systems can consume.
reader: model-admin
---

A consumer API gives other systems a deliberate view of workspace data. Its contract chooses
which types and fields they read and the operations available to them. It is not a second copy
of the records. You need **Model authoring** to edit the draft; activation needs release access.
Start with [Define a consumer API](/docs/guide/model/define-a-consumer-api/).

## Choose the content within a shared form

Every consumer API uses the same patterns for presenting business objects, reading lists,
looking up values, resolving several inputs and reporting changes. Within your API, all exposed
record types share one declared object shape. Selected fields, related records, system codes,
translations and parent information fit into that shape. A field without a value uses its declared
fallback or stays empty; it does not require a different form for that record type.

Your choices supply the content: which types are exposed, what fields mean, which relationships
are followed, how lookups match and which changes are reported. The engine supplies the common
forms for objects, pages, errors and events. Systems that read your API can reuse their reading
and change-handling processes across types and contracts.

You still choose public field names, related fields and whether a relationship returns one record
or several. You also choose which operations are offered. These choices define your particular
contract; another consumer API can make different choices. A consuming system that reads the
contract's declared structure can adopt new types through configuration, while one written for
fixed names may need changes. Review the generated documents with that system's team.

Keep the agreed output stable as the underlying model evolves. The consumer contract's version
is separate from the model release version; a breaking change needs a higher contract version.
See [the shared patterns and two example record types](/docs/integrate/consumer-apis/#learn-one-way-to-read-business-objects)
for the integrator's explanation.

## From an editor choice to a consumer's answer

A **business object** is one record presented in the shape you choose for other systems.
It can include fields from that record, its parent and related records. Get by ID, lists
and lookups all return this same shape. A lookup adds a match score; a list wraps objects
in a page. Changing the shape therefore affects more than one operation.

The examples below show the reference data's **Stops API**. They illustrate the result of
browser choices; you do not type these requests or responses into the editor. They are
worked examples from the reference model and data, not captured responses from a running
instance. The full request sequences are in [Consumer APIs for integrators](/docs/integrate/consumer-apis/).

| Part of the editor | Reference declaration | What a consumer receives |
| --- | --- | --- |
| Types and related | Expose Stop, Municipality, Operator and Mode | Only those record types can be returned as business objects; a Stop has `objectType: "Stop"`. |
| Fields | Output name `code`, with sources `sloid`, `operator-code`, `mode-code` in that order | The first available value becomes `code`, so a stop and an operator use the same public field without sharing an attribute. |
| Fields | Output name `stopNumber`, source `stop-number` | The public field is `stopNumber`; its value is an integer. |
| Types and related | Related blocks `operator`, `modes`, `systemCodes`, `translations` | The object includes the selected related fields. A single-valued relationship gives an object or null; a many-valued one gives an array, including an empty array. |
| Operations | Get by ID, XREF, Resolve and five lists | Consumers can read a record, look it up, resolve a batch or request a named list. An undeclared operation is unavailable. |
| Filters | `municipality` uses Under; `mode` uses On related | These names become request parameters; they narrow records using ancestors or relationships. |
| Operations | Custom event `stops-changed`, watching `code`, `name`, `validFrom`, `validTo` | Consumers can follow that named event for stop creation, deletion and updates to those outputs. |
| Contract version | 1 | The address ends in `stops/v1`. A new contract version changes the version in the address. |

## The business object consumers read

On **Fields**, **Role** says which field supplies the identity, code, name or validity dates.
The identity role always reads the record's stable ID. A business code such as a stop number
is a separate field; it does not replace that ID. **Output name** controls the name in the
answer, while **Served type** shows the value's type and whether it can be missing.

![Stops API fields with output names, roles, ordered sources, served types and defaults](/docs/screens/model-consumer-tab-fields.png)

Above: Stops API in the reference model. The code has three ordered sources; stopNumber is
an integer and validTo can be null.

**Example result: Get by ID.** A consumer reading the Chur stop requests:

```http
GET /api/consumer/stops/v1/objects/745c1a52-8405-4158-8f3b-b9e9c8b979be?workspace=graubuenden
```

The response body has this shape and these reference values:

```json
{
  "objectType": "Stop",
  "id": "745c1a52-8405-4158-8f3b-b9e9c8b979be",
  "code": "ch:1:sloid:9000",
  "name": "Chur",
  "validFrom": "2021-04-01",
  "validTo": null,
  "stopNumber": 8509000,
  "abbreviation": "CH",
  "fsoNumber": null,
  "latitude": "46.85308416276408",
  "longitude": "9.528937733041323",
  "height": "584.6",
  "sboid": null,
  "parent": {
    "objectType": "Municipality",
    "id": "05fd46a2-964a-4870-9d40-8bec6b4822dd",
    "code": null,
    "name": "Chur"
  },
  "path": "Graubünden/Plessur/Chur",
  "operator": {
    "id": "003ff971-bd07-4396-854c-4a6acd33dd8d",
    "code": "SBB",
    "name": "Schweizerische Bundesbahnen SBB"
  },
  "modes": [
    {
      "id": "0f61601d-ec0c-4944-bab9-cf0d1d8665a9",
      "code": "TRAIN",
      "name": "Train"
    }
  ],
  "systemCodes": [
    {
      "system": "Wikidata: stations",
      "systemKey": "wikidata-stations",
      "code": "Q663869",
      "name": "Q663869 Chur"
    },
    {
      "system": "Regional ticketing (FICTIONAL)",
      "systemKey": "ticketing",
      "code": "T-0300",
      "name": "T-0300 FICTIONAL: Zone 1 hub: Chur and Chur West (two stops, one code)"
    }
  ],
  "translations": []
}
```

The path names ancestors from the root to the parent, excluding the stop itself. The model
also supports a hierarchy as an array of ancestor names; this API does not declare one.
The stop's `fsoNumber` is null: that value belongs to its municipality, and the field does
not automatically inherit it. Its `sboid` is also null; choosing an operator relationship
does not copy that operator's attributes onto the stop. Chur's municipality has translated
names, but this stop has no translation records, so its `translations` array is empty.
Decimal values use text to preserve precision; integers remain numbers, booleans remain
true or false, and dates use year-month-day text. See [Reading business objects](/docs/integrate/reading-business-objects/).

### Sources and defaults

Sources are tried in the displayed order, skipping missing values and empty text. Zero and
false are values, not missing data. If none supplies a value, the declared **Default** is
used; without one, the answer contains null. A default affects the output only and never
writes a value into a record. It must have the field's served type.

**Example result: changing a default.** The reference API has no field defaults. If you set
**Default** on `abbreviation` to the text `—`, a stop with no abbreviation changes from the
response excerpt `{"abbreviation": null}` to `{"abbreviation": "—"}`. Chur still returns
`{"abbreviation": "CH"}` because its source has a value. These are response excerpts from
the Get by ID operation above, not complete objects.

## Lists, filters and the requests they enable

A list selects the type to return and its order. **Within the filter** gives a list a
containment scope. A filter's **Name** becomes a parameter name; **Matches on** chooses
which values a consumer can supply. These are public choices: changing a filter name or
its accepted values can break a consuming system even if the output fields stay the same.

![Stops API filters and the records and related blocks they read](/docs/screens/model-consumer-tab-filters.png)

Above: the reference API's municipality filter matches an ancestor by ID, name or FSO
number on ordinary reads. A list's Within parameter with the same name takes parent IDs
only. Its mode filter reads related modes and keeps only matching records.

**Example result: a list within a municipality.** The reference list `stops` has **Of**
Stop, **Within** filter municipality and **Sorted by** stop-number. A consumer can request:

```http
GET /api/consumer/stops/v1/lists/stops?workspace=graubuenden&municipality=05fd46a2-964a-4870-9d40-8bec6b4822dd&pageSize=1&includeTotal=true
```

The response's `items` array contains business objects in stop-number order. Each item
has the full shape shown above. This excerpt shows the page metadata; the `items` array
and the opaque cursor values are omitted here:

```json
{
  "workspace": "graubuenden",
  "publication": null,
  "pageSize": 1,
  "prevCursor": null,
  "startIndex": 0
}
```

The complete answer also has `nextCursor`, `anchor` and `totalCount`. The consumer follows
cursors to read more; a page size is not a limit on the whole list. The `all-stops` list has
no Within filter. On that list, `municipality=3901` uses the ordinary filter. On `stops`,
the same parameter names a parent and must contain its stable ID. Omitting the parameter
from either list returns all stops; Within enables a scope rather than making it required.

**Example result: a related filter.** Adding `mode=TRAIN` to the request keeps only stops
with a matching mode. It also limits the returned `modes` block to matching items. The
reference mode filter matches the mode's code or name; the municipality filter matches
an ancestor instead. A filter does not create another field in the business object.
For complete page responses and scoping rules, see
[Reading business objects](/docs/integrate/reading-business-objects/).

## Lookups and batch answers

**XREF** finds records by the values another system knows. **Exact** and **Contains** are
numeric weights. Exact comparison ignores letter case for text; Contains matches part of
text and applies only to terms of at least three characters. A higher match score ranks
first; it is not a percentage or a guarantee that the record is the intended one.

**Example result: look up a stop number.** The reference stop-number rule has **Exact**
900. A consumer asking for one answer requests:

```http
GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=8509000&expect=one
```

It receives Chur's complete business object above with one extra field. Response excerpt:

```json
{
  "objectType": "Stop",
  "id": "745c1a52-8405-4158-8f3b-b9e9c8b979be",
  "name": "Chur",
  "stopNumber": 8509000,
  "matchScore": 900
}
```

Without the single-answer choice, XREF returns a paged `results` array. A unique top
candidate gives one answer; no candidate or a tie is reported as an error rather than
an arbitrary choice. **Also match through** lets related data identify its owning object:
for example, `Q663869` identifies Chur through its system code at weight 90. **First of**
tries the related rules in order; **Prefers** can favor particular exposed types when
one related record identifies several types.

**Resolve** applies the same lookup or Get by ID rules to many inputs in one request.
A consumer can supply shared parameter defaults, with individual items overriding them.
These request defaults differ from a field's Default in the editor: they narrow reads,
not fill missing output values. Example request body for the reference API's Resolve
operation (shown for review, not for typing in the model editor):

```http
POST /api/consumer/stops/v1/resolve?workspace=graubuenden
Content-Type: application/json
```

```json
{
  "defaults": {"municipality": "3901"},
  "items": [{"ref": "first-stop", "query": "8509000"}]
}
```

The answer's first item has `index: 0`, `ref: "first-stop"`, `status: "found"` and an
`object` containing the same scored Chur object. Its `counts` is
`{"found": 1, "notFound": 0, "ambiguous": 0, "rejected": 0}`. A batch can report missing,
ambiguous or rejected items alongside found items. See
[Looking up and resolving](/docs/integrate/looking-up-and-resolving/) for full responses,
errors and crosswalk examples. A **Crosswalk** filter lets a consumer request a particular
related representation as `target`; the reference system filter offers this for system codes.

## Events describe changes to the output

An event's **Types** selects the records, **Changes** selects creation, update or deletion,
and **Watches** limits which output changes trigger an update event. Leaving Watches empty
watches any change to the business object, including related blocks. **Events per type**
adds a standard event for each exposed type. The reference API leaves that option off
and declares only its custom `stops-changed` event.

**Example result: a watched change.** After a stop's name changes, a consumer can read:

```http
GET /api/consumer/stops/v1/events?workspace=graubuenden&event=stops-changed&payload=identity
```

An item in the response's `items` array identifies the event and changed output. This
excerpt illustrates a rename to Chur Bahnhof; event identifiers, positions, time and cause
are omitted here:

```json
{
  "event": "stops-changed",
  "change": "updated",
  "contractVersion": 1,
  "objectType": "Stop",
  "id": "745c1a52-8405-4158-8f3b-b9e9c8b979be",
  "code": "ch:1:sloid:9000",
  "name": "Chur Bahnhof",
  "changed": ["name"]
}
```

Changing only latitude does not trigger this reference event: latitude is not watched.
A full event payload normally also includes the current business object; deleted records
have no object body. An event is not a saved historical copy of every field at its event
position. Declaring an event does not register a webhook or grant permission to read it.
Subscription, signing and delivery are separate tasks described in
[Consumer events and webhooks](/docs/integrate/consumer-events-and-webhooks/).

## What the editor shows

Select **Consumer APIs** in the model pane, then an API. Its facts show **Contract version** and
**Compatible with what consumers read**, **Needs contract version …**, or **Checked once the
draft is valid**. Fix model errors before relying on the compatibility result.

| Tab | What you decide or inspect |
| --- | --- |
| Types and related | Exposed record types, their public names, related blocks and optional parent, path and hierarchy. |
| Fields | Output names, value sources and roles. Ordered sources use the first non-empty value. |
| Operations | Get by ID, cross-reference and resolve choices, lists and custom events. |
| Filters | Named ways to narrow or match records, including through related blocks. |
| Schema | The generated description of the data shape. |
| Message example | A generated example of the declared shape, rather than a live record sample. |

![Consumer API definition on the Types and related tab](/docs/screens/model-consumer-tab-types.png)

A field's **Output name** is the word consumers receive. **Sources…** chooses the fields it
reads, in order; **Role** identifies a purpose used by the contract. **Add related…** follows
an allowed relationship and selects the related fields to expose. The declaration can also
serve parent, path and hierarchy information.

## Operations and matching

**Get by ID**, **XREF** and **Resolve** are offered for the API’s exposed types. **Resolve**
requires both Get by ID and XREF; **Events per type** enables the standard type events. Lists specify **Of**,
an optional **Within the filter** and **Sorted by**. Cross-reference rules choose how values
identify related records. Matching can use **Exact** and **Contains** weights and **Also match
through** a related block. Check **Matches on…**, **Fields…**, **First of** and **Prefers** where
shown rather than assuming the display name is the unique identifier.

Filters have a **Name** and **Verb**: **By type**, **Under**, **Linked to** or **On related**.
Their further choices depend on what they read. **Through** can use the record itself, a related
block or records sharing that block. **On related** can keep only matching records, score only
matching items or expose a crosswalk. These choices change what a consumer can ask and receive.
Custom events select **Types**, **Changes** and **Watches**; leaving Watches empty watches any
change to what consumers read. An event declaration does not create a delivery subscription.

## Contracts, access and limits

A contract version is separate from the model release version, draft version and model language
version. Removing or changing something consumers read can require a higher contract version.
Renaming a public field or changing relationship cardinality can affect the output too. Review
the differences with the consuming teams, then
[raise the contract version](/docs/guide/model/raise-a-contract-version/). Merely raising it
neither fixes an invalid model nor gives old consumers a parallel old endpoint after activation.

A consuming system needs a client granted this particular API in each workspace it reads.
Defining the API, granting a role or giving a person Model authoring does not grant consumer
access. A security administrator manages these grants. Without the API grant, a data read
is refused with Forbidden; the consumer does not receive a reduced version of the object.
Agree the exposed fields with that administrator: a grant opens this API's declared output,
not a field-by-field selection.
**Rename…** changes its display name; **Describe…** supplies its generated description.
A released key identifies consumers' existing access point: keep it stable. A released API's
key can still be changed, but consumers of the old key then get 404, as with removal. Removing an API
stops its consumers reading it once active. Review that warning even where removal is allowed.

**Edit as JSON…** offers specialist editing for the definition or an item as one saved step.
No visual form covers every detail of the model language. Use the
[JSON view](/docs/model/json-view/) with a specialist for unsupported combinations, then inspect
Issues and the generated documents. Do not infer support solely from a field being accepted as text.

See [the generated documents](/docs/guide/model/see-a-consumer-apis-documents/) for review and handover;
integrators use [Integrate](/docs/integrate/overview/) for requests and authentication.

## Review edits that remove behavior

Turning **XREF** off asks **Stop offering XREF?**. It removes the match rules and also stops
**Resolve**, which depends on XREF. **Undo** restores the step; switching XREF on again starts
without those rules. Inspect the contract changes before activating. An operation not declared
in the contract is unavailable to consumers and absent from its generated operation document.

A field's editable **Default** supplies its declared fallback when sources do not yield a value;
it differs from a default on a record attribute. An identity-role output reads the record's
stable ID; publish other identifiers as separate fields. Output roles must not conflict, related
blocks must name valid relationships, and a filter must choose one kind of read. The Issues
list points to invalid references or combinations.

The model language also supports per-type events, watched fields and related blocks, scoped
lists and parameters based on types, ancestors or related records. Use the specialist document
view for declarations the current form does not expose. Reducing event coverage, changing
crosswalk availability or removing an operation can require a higher contract version just as
removing a field does. Adding more output is usually compatible; lowering a contract version
is refused.
