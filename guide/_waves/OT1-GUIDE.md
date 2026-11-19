# OT1 guide: each object in its type's shape

Read `guide/AGENTS.md`. Readers: integrators who read a consumer API, and model authors who define one. Write plain
prose; no package or decision numbers. The code wins over this text wherever they differ.

## Why

A consumer API definition has one object shape (`object.fields` and the related blocks) for every type it exposes. The
engine used to write every declared field on every object, so a field the type cannot hold read as `null`: an
operator answered a stop's number and coordinates, a stop answered an operator's `sboid` and a municipality's
`fsoNumber`, all `null`. Now an object carries only what its own type holds. The pages below say the old thing in
places; correct them.

## What the product does now (check each point in the code)

- **A field is on an object only when its type holds it** (`engine/model/consumer_contract.py`, `object_outputs`): one
  of the field's sources is a built-in field (`id`, `name`) or an attribute the object's type binds. A field the type
  holds and the record has no value for is `null` (or the field's default, when it declares one); a field the type
  cannot hold is not there at all. A default never puts a field on a type that does not hold it. `objectType`,
  `parent`, `path`, `hierarchy` (where declared), `matchScore` (XREF) and `target` (a crosswalk) stay on every object.
  So `null` now always means "this record has no value", and an absent field means "this type has none".
- **A related block is on an object only when its type is an end of the block's relation** in the block's direction
  (for a block of the parent, `parent.<block>`, the parent's type). Otherwise it is absent, not `[]` or `null`. A block
  the type holds and the record has no related records for is `[]` (many) or `null` (one), as before. Blocks served on
  request are unchanged (present only when the read names them in `include`).
- This is one rule for every read that composes objects: Get by ID, lists, XREF, Batch resolve, event payloads and
  webhook deliveries, and reads of a publication.
- **The reference data's `stops` API now answers**, by type (values below are the exact fields; `objectType` first):
  - Stop: `objectType`, `id`, `code`, `name`, `validFrom`, `validTo`, `stopNumber`, `abbreviation`, `latitude`,
    `longitude`, `height`, `parent`, `path`, `operator`, `modes`, `systemCodes`, `translations`. **No `fsoNumber`, no
    `sboid`**: a stop cannot hold them.
  - Municipality: `objectType`, `id`, `name`, `fsoNumber`, `parent`, `path`, `systemCodes`, `translations`.
  - Operator: `objectType`, `id`, `code`, `name`, `sboid`, `parent`, `path`, `translations`.
  - Mode: `objectType`, `id`, `code`, `name`, `parent`, `path`.
  Values for a record keep what the old pages show; only the fields a type cannot hold disappear (the stop's
  `fsoNumber` and `sboid`; the operator's `validFrom`, `validTo`, `stopNumber`, `abbreviation`, `fsoNumber`,
  `latitude`, `longitude`, `height`, `operator`, `modes`, `systemCodes`).
- **The consumer API's OpenAPI document has a schema for each exposed type**, named and titled by its public name
  (`Stop`, `Operator`, …) with that type's fields, each required (a block served on request optional). `Object` is a
  "one of" over them, discriminated on `objectType`. Every response that holds objects has one named example per
  exposed type (a list has its own type's). On the API reference page (`/docs/api`, a consumer source) a response shows
  **One of · <Type>** in its schema (pick the type to see its fields, `objectType` marked as the discriminator) and a
  **named example picker** under the example ("The answer." and the type's name, a list of every type); each type's
  example holds only that type's fields. No record is read for the examples.
- **Contract:** an attribute unbound from a type, or a related block whose relation no longer reaches a type, removes an
  output from that type's objects: a breaking change needing a higher contract version (or keeping the current one when
  activating). An output joining a type is additive.
- **Model editor, a consumer API's Schema and Message example tabs** (`frontend/src/features/model-editor/ConsumerApis.tsx`):
  both get an **Object type** dropdown right under the tab's description: one button showing the chosen type with its
  coloured tile, opening a searchable list of every exposed type (each with its tile, the chosen one ticked). The
  **Schema** offers **All types** first (the whole document: the "one of" over the types, with each type's schema
  under `$defs`) and a type shows that type's own schema; the **Message example** has no All types and shows one
  message of the chosen type, the first exposed type until another is chosen. The choice is shared by the two tabs
  while the editor stays on the API. **Copy** copies what is shown; **Download** names the file after the type
  (`<api key>-<type>-schema.json`, `<api key>-<type>-example.json`; without a type `schema.json`; the link reads
  `Download <type>-example.json`). The draft's management routes take `?objectType=<PublicName>` on
  `…/schema.json` and `…/example.json`; an unknown name is `400 UNKNOWN_OBJECT_TYPE` naming the valid ones (API
  details: link the reference, do not repeat it).
- The tabs' own descriptions now read: Schema: "The JSON Schema of the message consumers receive: one of the types
  below, told apart by objectType, each with only the fields its type holds. An integration validates messages
  against it or generates its types from it." Message example: "One message of the chosen type as Get by ID would
  answer it, valid against the schema. An integration uses it as a test fixture or to agree the format with a partner.
  No record is read: the values come from each field's type."

## Pictures (taken, in `guide/public/screens/`; look at them, then keep or reword their captions)

- `model-consumer-tab-schema`: the Schema tab of the Stops API with the **Object type** dropdown opened on **All
  types**: All types, Stop, Municipality, Operator and Mode, each with its coloured tile, All types ticked.
- `model-consumer-tab-example`: the Message example tab with the dropdown on **Stop** and the example of a stop below
  it (no `fsoNumber`, no `sboid`).
- Both replace the older pictures of the same names (the old example showed one object mixing the fields of every
  type under `"objectType": "Mode"`). Look at both before writing their captions; the captions and the sentences
  around them must describe what is now shown.

## What to do

Search each page for the old claim and correct it; keep every other sentence. Examples captured from the reference
instance keep their values; remove or add only what the rules above change.

- `src/content/docs/integrate/consumer-apis.md`: the paragraph that says every exposed type uses the same declared object
  shape, and the section **Two types, one declared shape** (a table of a stop and an operator with "exactly the same
  fields") are no longer true. Rewrite them: one declared object definition, each type answered in its own shape.
  The table becomes the stop and the operator side by side with the fields each type holds (an absent field is shown as
  absent, for example "not in the answer", never as `null`), then the prose that says what `null` and absence now mean,
  and that a client reading several types should treat a field as present only for the types that hold it (the type's
  schema in the OpenAPI document says which). Fix the paragraph near line 104 ("Reads by ID, lists and lookups use
  the same declared business representation…") and the closing remark that says the generated document can differ
  between declarations: add that it has one schema per exposed type. Mention the reference page's schema and example
  pickers where the guide describes the generated document.
- `src/content/docs/integrate/reading-business-objects.md`, `looking-up-and-resolving.md`,
  `consumer-events-and-webhooks.md`, `src/content/docs/examples/the-consumer-api.md`: in every example answer of a
  **Stop** (Get by ID, a list item, an XREF result, a Resolve object, an event's `object`) delete the lines
  `"fsoNumber": null` and `"sboid": null`; a stop does not hold them. Where a sentence explains those nulls or lists the
  fields of a stop, correct it (for example "Null fields have no applicable value here": `null` now means the record has
  no value for a field its type holds). Do not touch the declaration excerpts that name `fso-number` or
  `operator-sboid` as sources: they are the definition, which still has them. Do not change examples that are not of
  the reference data (`Item`, `Category`).
- `src/content/docs/integrate/api-reference.md`: where it describes what a consumer source shows, say that a response
  shows one schema per type ("One of") and a picker of named examples, one per type, and that the guide does not repeat
  the schemas.
- `src/content/docs/integrate/compatibility.md` and `src/content/docs/guide/model/raise-a-contract-version.md`: where
  they list what is breaking for a consumer API, add that an attribute unbound from a type or a related block whose
  relation no longer reaches it takes the field away from that type's objects and needs a higher version, while a field
  joining a type does not.
- `src/content/docs/guide/model/see-a-consumer-apis-documents.md`: the steps that open **Schema** and **Message
  example** gain the **Object type** dropdown (All types on the Schema, one type on the example, the choice shared by the
  two tabs, Download named after the type); replace the two pictures' captions and the paragraph **Reference-data
  example** under them (it describes the old schema and the old example); keep the steps about compatibility.
- `src/content/docs/guide/model/define-a-consumer-api.md`: the steps that tell the author to review **Schema** and
  **Message example** say to choose each exposed type in **Object type** and check that it has the fields its type
  holds (a field an author expected on a type but missing there means that type does not bind its attribute, or is not
  an end of the block's relation).
- `src/content/docs/model/consumer-apis.md` (the tab table and the paragraph about the shared object near its top),
  `src/content/docs/model/the-model-editor.md`, `src/content/docs/guide/integrate/read-through-a-consumer-api.md`,
  `src/content/docs/journeys/shape-a-model.md`: correct a sentence that says every type has the same fields, and add the
  per-type shape and the dropdown where they describe the tabs.

## Files you may edit
- `src/content/docs/integrate/consumer-apis.md`
- `src/content/docs/integrate/reading-business-objects.md`
- `src/content/docs/integrate/looking-up-and-resolving.md`
- `src/content/docs/integrate/consumer-events-and-webhooks.md`
- `src/content/docs/integrate/api-reference.md`
- `src/content/docs/integrate/compatibility.md`
- `src/content/docs/examples/the-consumer-api.md`
- `src/content/docs/guide/model/see-a-consumer-apis-documents.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/guide/model/raise-a-contract-version.md`
- `src/content/docs/guide/integrate/read-through-a-consumer-api.md`
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/model/the-model-editor.md`
- `src/content/docs/journeys/shape-a-model.md`
