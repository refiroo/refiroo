# C3b: consumer APIs in "Model your data", with what they produce

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/steer/C6-INTEGRATE.md` (what the person who
owns refiroo asked for consumer APIs).

`model/consumer-apis.md` and the guides `guide/model/define-a-consumer-api.md` and
`guide/model/see-a-consumer-apis-documents.md` explain the editor but give no idea of what a declaration
produces. A model administrator designs the API other systems will read, so they must see the result:
for each part of the declaration (business object and its fields, parameters, lookups, events, version,
defaults, grants), what changes in the API, shown with the reference data's `stops` consumer API
(`guide/samples/model.json`): the declaration as the editor shows it, and the request and the response body
an integrator then gets, briefly (the full sequences are on the Integrate pages written at the same time:
link `integrate/consumer-apis` and its neighbours). Model pages are for people in the browser: show the
payloads as examples of the result, clearly labelled, never as something they must type. Payload shapes
from `backend/app/consumer/` and the tests, as the steering file says.

## Files you may edit

- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/guide/model/see-a-consumer-apis-documents.md`
- `_waves/coverage/model.md`
- `_waves/screens-wanted/C3b-CONSUMER.md`

## Report

As `COMPLETE-COMMON.md` says.
