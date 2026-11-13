# CA1 guide: the parent carries fields and related blocks; a block can be served on request

Read `guide/AGENTS.md`. Readers: model authors who define consumer APIs, and integrators who read them.

## Why

One 0.17 package, built (plan `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, section "CA1: The parent carries fields and related
blocks", decisions PP-D29 to PP-D32; CHANGELOG, Unreleased, the CA1 entry). The code wins over the plan wherever they differ:
- model shape: `backend/app/models/schema.py` (`ParentSpec`, `RelatedSpec.served`, `ConsumerProjection`, `ConsumerParentField`);
- expansion and rules: `backend/app/engine/model/consumer_expansion.py`, `validation/consumer_api_rules.py`
  (`_check_parent_fields`, `_check_projections`), `consumer_contract.py` (parent types, the breaking-change check);
- reads: `backend/app/engine/reads/consumer_objects.py` (`_parent`, `compose`), `consumer_parameters.py` (a filter on a
  parent block), `consumer_request.py` (`include`), `consumer_resolve.py`;
- OpenAPI: `backend/app/engine/model/consumer_openapi.py` (`_include`);
- events: `backend/app/engine/events/plan.py` (what the parent shows reaches its children);
- editor: `frontend/src/features/model-editor/ConsumerApis.tsx` (Parent section, Served column, Include list),
  `consumer.ts`, `operations.ts` (`consumer-add-parent-related`, `consumer-parent-fields`, the filter dialog's block list);
- API: `docs/API.md` (get by ID, filters, the error table), `docs/CONSUMER_API.md` (the parent, Served rules).

## What the product does now (check each point in the code)

**The parent (PP-D29).**
- A record's `parent` already served its type, ID, code and name. A definition can now also list, in `parent.fields`, any
  attribute a parent type binds (the key in the answer is the attribute key) and `ancestor:<type>.<field>` read from the
  parent's own ancestors; where the record's parent has no value or its type does not bind the attribute, the answer is
  `null`. The parent types are the types that can directly contain an exposed type.
- The parent also takes `related` blocks of its own, written as the object's (a `via` and its `fields`). One level only:
  the parent has no parent, path or hierarchy of its own. The short list form of `parent` is still valid; the editor writes
  it out in full the first time something is added to the parent.
- A block of the parent is not named `parent.…` in the definition; `parent.<block>` is only how `include` and a filter
  name it. An object block named `parent.…` is refused.
- Mistakes are refused at the pointer the author wrote (`/object/parent/fields/<n>`, `/object/parent/related/<block>/via`).

**Served always or on request (PP-D30).**
- Every related block, the object's and the parent's, has `served`: `always` (the default, so every existing definition
  answers as before) or `onRequest`. An on-request block is in an answer only when the read names it in `include` (repeat the
  parameter or separate names by commas: `include=translations&include=parent.systemVariants`). Get by ID, lists and XREF take
  it; batch resolve takes `include` in each item and in `defaults`. A name that is no on-request block is
  `400 UNKNOWN_INCLUDE`, with `details.valid` naming the valid ones.
- The OpenAPI document lists the valid names as an enum on those operations and types an on-request block as an optional
  property (the object's and the parent's).
- Why: the default answer stays small and the shape stays typed.
- `include` is a reserved name; a filter cannot be called `include`.

**A filter on a parent's block (PP-D31, PP-D32).**
- An On related filter may name `parent.<block>`. It limits that block as it limits the object's; keep only matching drops the
  results whose parent has no matching item. The filter's parameter name is the author's, as for every filter. Crosswalk is
  for the object's own blocks, not the parent's.
- A filter on an on-request block narrows the results with no `include`; the block is then not in the answer.
- Events and deliveries have no request, so they leave on-request blocks out. A change to what the parent shows (an
  attribute it reads, an item of its blocks) now makes `updated` for each child of that parent.

**The editor.**
- Fields tab, below the fields: a **Parent** section when the parent is served (turned on with "Parent, path and hierarchy…"):
  its output name, its fields (a picker of the four built-in names and the attributes of the parent types), and "Parent's related
  records" with Add related, a Via, Fields and a **Served** column.
- Types and related: the related table has a **Served** column (Always or On request), changed in place.
- Operations: the **Include** list shows the names the parameter accepts, written by the engine from the Served column.
- Filters: the On related block picker lists the object's blocks and the parent's (`parent.<block>`).
- Serving a block only on request that was served always leaves the default answer, so it needs a higher contract version
  (the editor says so as for any breaking change); adding parent fields, parent blocks, include and filters does not.

**What an integrator sees.** Get by ID, lists, XREF and resolve answers carry the parent's extra fields and its always-served
blocks as before; on-request blocks appear with `include`. Check every claim against `docs/API.md` and the integrator pages'
existing wording.

## What to do

- Extend the pages that own each topic; no new pages. Say where each control is, step by step, and why (the integrator wants
  a parent's IDs and its values in one answer; the cost: a parent block repeats on every child row, which is why it can wait
  for `include`).
- Use neutral examples only (a catalogue with categories and items, a ledger with entries).
- The model-author pages: `src/content/docs/model/consumer-apis.md` and `src/content/docs/guide/model/define-a-consumer-api.md`.
  The integrator pages: `src/content/docs/integrate/consumer-apis.md`, `reading-business-objects.md` and
  `looking-up-and-resolving.md`. The worked example page `src/content/docs/examples/the-consumer-api.md` gets one short,
  checked addition only where it already shows a parent or a related block.
- Pictures: list in the report each picture the text calls for that is not taken yet.

## Files you may edit

- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/integrate/consumer-apis.md`
- `src/content/docs/integrate/reading-business-objects.md`
- `src/content/docs/integrate/looking-up-and-resolving.md`
- `src/content/docs/examples/the-consumer-api.md`
- `_waves/progress/CA1-GUIDE.md`

## Report

Per page: what changed and why (one line each), what you checked and left, pictures needed, and any point the guide cannot
describe honestly.
