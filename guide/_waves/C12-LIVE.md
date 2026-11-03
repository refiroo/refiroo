# C12: check the examples against the running instance

Read `guide/AGENTS.md` and `guide/tools/CODEX_TOOL.md` (sections Screenshots and Live requests).

The pages carry request and response examples (consumer APIs, the management API, files and jobs, events
and webhooks) that were built from the code and the tests, never run. This wave checks each against the
reference instance and corrects the pages to what refiroo really answers.

1. **List the requests.** For every request example on the pages (`integrate/`, `guide/integrate/`,
   `model/consumer-apis.md` and its guides, `examples/the-consumer-api.md`, and any other page with one),
   add an entry to `_waves/C12.requests.json` in the format `tools/live-requests.mjs` reads: a name saying
   which page and example it is, the auth (`consumer` for the `stops` consumer API, `admin` for the
   management API, `none` for public paths), method, path, query, headers and body as the page shows them.
   Only reads, lookups, resolves and previews; a request that writes is listed with `"write": true` and is
   not run. An example of an error gets `"expectStatus"`. You cannot reach the instance from your sandbox:
   stop after the list, and say so.
2. **Compare (second turn).** The requests are then run and their responses saved in
   `_coverage/live/<name>.json`; you get the run's log. Compare every example on the pages with the real
   response: status, headers, field names, shapes, values, paging, error envelopes. Correct each page to the
   real answer (use the real values, shortened with "…" only where a page already shortens). Where the code
   and the instance disagree with what a page or a document promises, the instance wins on the page; list
   the disagreement in your report. Record each example's result in `_waves/reconcile/C12-LIVE.md` (page,
   example, matched / corrected / could not run and why) before the next one.

## Files you may edit

- `_waves/C12.requests.json`
- `_waves/reconcile/C12-LIVE.md`
- `src/content/docs/**/*.md`

## Report

The examples checked, matched and corrected per page, the requests not run and why, and every
disagreement between the instance and the documents.
