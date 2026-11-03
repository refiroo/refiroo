# Steering for C6 (from the person who owns refiroo, 2026-11-03)

**Consumer APIs must be explained in the documentation itself, with examples.** A consumer API is custom:
each organisation declares its own in its model, so the API reference at `/docs/api` cannot document it
for the reader, and a link there is not an explanation. Rule 3 of AGENTS.md ("link instead of repeating")
does not apply to consumer APIs. Rework `integrate/consumer-apis.md`, `integrate/reading-business-objects.md`,
`integrate/looking-up-and-resolving.md`, `integrate/consumer-events-and-webhooks.md` and their guides:

- How a declaration becomes an API: what the model declares (business object, fields, parameters,
  lookups, events, version, defaults) and, for each, what appears in the API: the paths, the parameters,
  the response.
- Show it end to end with the reference data's `stops` consumer API (`guide/samples/model.json`): the
  declaration excerpt, then each operation as a full request and a full response body (a single stop by
  ID, a page of a list with its paging, a list with a parameter, a lookup and its scoring, a batch resolve,
  an unchanged answer with ETag, a typical error), the event and the webhook payload a subscriber receives
  (with the signature headers) and how to verify it.
- Payloads must be real shapes: derive them from the code that builds them (`backend/app/consumer/`) and
  check them against what the tests assert (`backend/tests/`, consumer and journeys J25, J28–J30) and
  `docs/CONSUMER_API.md`. Values from the reference data. Say in your report anything you could not confirm.
- Keep a link to the instance's own consumer API documents (each consumer API has its index and OpenAPI on
  the instance; say where an integrator finds them), but as a pointer, never instead of the explanation.

Apply this to the consumer API pages now, before your next unit, and note it in your progress file.
