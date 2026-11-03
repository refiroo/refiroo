# C6b: the consumer API's main strength, stated as a concept

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`.

What the person who owns refiroo asked for: the consumer API pages show the unified schema in their
examples but never say it as an idea. It is a main strength and must be explained as a concept:

**Every consumer API has the same schema and works the same way, whatever the model declares.** Every
business object comes in one object shape (the same common fields, then the parts the definition adds, each
of a known form: related objects as id, code and name; system codes; translations; the parent and path);
every consumer API offers the same operations (get by ID, lists with the same paging and envelope, the
lookup, batch resolve, crosswalk, business dates, publications, the API index and its OpenAPI); errors,
ETags, events and webhook deliveries have the same envelopes. So an integrator learns it once, writes one
parser and one flow pattern, and uses it for every type and every consumer API an organisation declares; a
new type or a new consumer API needs no new code on their side. The contract is versioned and stays stable
while the model and the management API change. What varies is declared in the model (which types, which
fields and related parts, which lookups and events), never the form.

Source: `docs/CONSUMER_API.md` "Why a second API tier" and "Engine design" › "Principle", and the code in
`backend/app/consumer/` (check each claim; the code wins; say what does not hold). Use only the reference
data's `stops` API for examples, never the "Reference implementation" example of that document.

Write it where each reader needs it, briefly where it is not the page's subject:
- `integrate/consumer-apis.md`: a section near the top stating the concept in full, then showing it with
  two object types side by side (a stop and a municipality or operator, from the existing examples or the
  same sources), and what stays the same across consumer APIs.
- `about/sharing-data-with-other-systems.md`: the strength in plain words for an evaluator.
- `model/consumer-apis.md`: for the designer: what they declare changes the content, never the form; what
  that means for the systems that read it.
- `examples/the-consumer-api.md`: one sentence and a link.

## Files you may edit

- `src/content/docs/integrate/consumer-apis.md`
- `src/content/docs/about/sharing-data-with-other-systems.md`
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/examples/the-consumer-api.md`

## Report

The pages changed and any claim of the concept the code does not support.
