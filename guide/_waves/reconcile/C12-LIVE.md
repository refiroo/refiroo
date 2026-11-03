# Current result: C12 second turn

Compared all **66 saved responses** across 24 pages; **47 matched**, **13 examples
were corrected**, and **6 production-origin checks could not be exercised as documented**.
Another **4 write examples were skipped**, for **10 could-not-run entries** in total.
The two corrected ETag examples still need a matching-tag 304 capture. Matched results
are limited to the actual response boundary described in each entry below.

| Page | Saved responses checked | Matched | Corrected | Could not run as documented / skipped |
| --- | ---: | ---: | ---: | ---: |
| `examples/the-consumer-api.md` | 10 | 4 | 6 | 1 |
| `guide/integrate/read-through-a-consumer-api.md` | 4 | 4 | 0 | 0 |
| `guide/integrate/resolve-a-file-of-codes.md` | 1 | 1 | 0 | 0 |
| `guide/integrate/subscribe-a-webhook-and-verify-it.md` | 0 | 0 | 0 | 1 |
| `integrate/consumer-apis.md` | 2 | 2 | 0 | 0 |
| `integrate/consumer-events-and-webhooks.md` | 1 | 0 | 1 | 1 |
| `integrate/looking-up-and-resolving.md` | 3 | 2 | 1 | 0 |
| `integrate/reading-business-objects.md` | 5 | 0 | 5 | 0 |
| `integrate/signing-in-and-tokens.md` | 2 | 2 | 0 | 0 |
| `run/background-jobs.md` | 1 | 1 | 0 | 0 |
| `run/configure.md` | 3 | 3 | 0 | 0 |
| `run/developer-instance.md` | 2 | 2 | 0 | 0 |
| `run/health-and-startup-checks.md` | 3 | 3 | 0 | 0 |
| `run/https.md` | 6 | 3 | 0 | 3 |
| `run/install-with-compose.md` | 1 | 1 | 0 | 0 |
| `run/licence-and-source.md` | 2 | 2 | 0 | 0 |
| `run/monitoring.md` | 2 | 2 | 0 | 0 |
| `run/production-checklist.md` | 5 | 3 | 0 | 2 |
| `run/security-checklist.md` | 3 | 2 | 0 | 1 |
| `run/several-processes.md` | 1 | 1 | 0 | 0 |
| `run/sign-in-and-mail-setup.md` | 2 | 2 | 0 | 1 |
| `run/troubleshooting.md` | 4 | 4 | 0 | 0 |
| `run/upgrades.md` | 2 | 2 | 0 | 0 |
| `run/webhook-delivery.md` | 1 | 1 | 0 | 0 |

Six guide pages changed: examples/the-consumer-api.md, integrate/reading-business-objects.md, integrate/looking-up-and-resolving.md, integrate/consumer-events-and-webhooks.md, integrate/consumer-apis.md and run/monitoring.md. Per-example statuses, disagreements and limits follow in the second-turn sections. The first-turn record below is retained as history.

---

# C12 live-example reconciliation

## First-turn status

Inventory complete; live reconciliation has not started. The assignment states that
this sandbox cannot reach the reference instance. No requests were sent, no examples
were matched against live responses, and no documentation page was changed.

There are **70 entries across 24 pages: 66 reads and 4 excluded writes**. Two of the
reads need a real ETag before execution. Repeated requests remain separate so that
every page can be reconciled independently. All values, event positions, signatures,
response bodies, error envelopes and paging claims remain unverified.

`tools/live-requests.mjs` is absent, and `tools/CODEX_TOOL.md` has no Live requests
section. Runner compatibility therefore remains unverified. See
`../../_coverage/notes/C12-LIVE/README.md` for authentication mapping, placeholder
handling and public-proxy requirements. No instance/document disagreements can be
established until the saved responses and run log are supplied on the second turn.

## Counts by page

| Page (under src/content/docs) | Listed | Matched | Corrected | Not run: reference unavailable | Not run: writes excluded |
| --- | ---: | ---: | ---: | ---: | ---: |
| `examples/the-consumer-api.md` | 11 | 0 | 0 | 10 | 1 |
| `guide/integrate/read-through-a-consumer-api.md` | 4 | 0 | 0 | 4 | 0 |
| `guide/integrate/resolve-a-file-of-codes.md` | 1 | 0 | 0 | 1 | 0 |
| `guide/integrate/subscribe-a-webhook-and-verify-it.md` | 1 | 0 | 0 | 0 | 1 |
| `integrate/consumer-apis.md` | 2 | 0 | 0 | 2 | 0 |
| `integrate/consumer-events-and-webhooks.md` | 2 | 0 | 0 | 1 | 1 |
| `integrate/looking-up-and-resolving.md` | 3 | 0 | 0 | 3 | 0 |
| `integrate/reading-business-objects.md` | 5 | 0 | 0 | 5 | 0 |
| `integrate/signing-in-and-tokens.md` | 2 | 0 | 0 | 2 | 0 |
| `run/background-jobs.md` | 1 | 0 | 0 | 1 | 0 |
| `run/configure.md` | 3 | 0 | 0 | 3 | 0 |
| `run/developer-instance.md` | 2 | 0 | 0 | 2 | 0 |
| `run/health-and-startup-checks.md` | 3 | 0 | 0 | 3 | 0 |
| `run/https.md` | 6 | 0 | 0 | 6 | 0 |
| `run/install-with-compose.md` | 1 | 0 | 0 | 1 | 0 |
| `run/licence-and-source.md` | 2 | 0 | 0 | 2 | 0 |
| `run/monitoring.md` | 2 | 0 | 0 | 2 | 0 |
| `run/production-checklist.md` | 5 | 0 | 0 | 5 | 0 |
| `run/security-checklist.md` | 3 | 0 | 0 | 3 | 0 |
| `run/several-processes.md` | 1 | 0 | 0 | 1 | 0 |
| `run/sign-in-and-mail-setup.md` | 3 | 0 | 0 | 2 | 1 |
| `run/troubleshooting.md` | 4 | 0 | 0 | 4 | 0 |
| `run/upgrades.md` | 2 | 0 | 0 | 2 | 0 |
| `run/webhook-delivery.md` | 1 | 0 | 0 | 1 | 0 |

The model consumer-API page and its three related guides were also inspected; they
contain browser tasks and conceptual examples, rather than additional concrete
requests. Other integration pages name operations through reference links without
showing executable examples. Declaration JSON and generated-message illustrations
are not requests. File and job sequences contain no concrete HTTP request body to
add; the listed operator probes do not reproduce the surrounding recovery actions.

## Validation

- JSON parses; request names are unique and safe as response filenames.
- Auth values, separated paths/query objects and read/write classification checked.
- `GUIDE_OUT=_build/C12-LIVE npm run build` in `guide/`: passed, 225 pages, 5.42 s.
- Build warning: the existing `caddyfile` block in `run/https.md` uses plain-text highlighting because that language is unavailable. The build still passed.
- No screenshots needed for this inventory. No application defects established.

## Per-example status

## examples/the-consumer-api.md

- `examples--the-consumer-api--read-a-stop-by-its-id-1` (line 263): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--read-a-list-then-narrow-it-2` (line 331): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--read-a-list-then-narrow-it-3` (line 401): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--look-up-a-stop-number-4` (line 480): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--resolve-several-inputs-5` (line 549): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--reuse-an-unchanged-answer-6` (line 658): **could not run**. Reference instance unavailable from the sandbox; awaiting external run. Replace the documented ETag placeholder with the tag from the preceding GET before running.
- `examples--the-consumer-api--correct-a-request-error-7` (line 678): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--follow-the-declared-event-8` (line 707): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--receive-the-event-at-a-webhook-9` (line 765): **could not run**. Write or outbound webhook: excluded from execution.

## guide/integrate/read-through-a-consumer-api.md

- `guide--integrate--read-through-a-consumer-api--work-through-the-reference-contract-1` (line 25): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `guide--integrate--read-through-a-consumer-api--work-through-the-reference-contract-2` (line 36): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## guide/integrate/resolve-a-file-of-codes.md

- `guide--integrate--resolve-a-file-of-codes--try-two-rows-from-the-reference-world-1` (line 23): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## guide/integrate/subscribe-a-webhook-and-verify-it.md

- `guide--integrate--subscribe-a-webhook-and-verify-it--use-the-reference-event-end-to-end-1` (line 26): **could not run**. Write or outbound webhook: excluded from execution.

## integrate/consumer-events-and-webhooks.md

- `integrate--consumer-events-and-webhooks--a-declaration-and-the-event-it-exposes-1` (line 81): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--consumer-events-and-webhooks--the-actual-webhook-request-shape-2` (line 179): **could not run**. Write or outbound webhook: excluded from execution.

## integrate/looking-up-and-resolving.md

- `integrate--looking-up-and-resolving--a-lookup-with-a-score-1` (line 62): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--looking-up-and-resolving--a-crosswalk-from-a-stop-number-to-another-system-s-code-2` (line 159): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--looking-up-and-resolving--resolve-a-small-file-in-one-request-3` (line 231): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## integrate/reading-business-objects.md

- `integrate--reading-business-objects--a-complete-object-read-1` (line 36): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--reading-business-objects--a-list-page-with-navigation-2` (line 102): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--reading-business-objects--the-same-list-narrowed-by-a-declared-parameter-3` (line 174): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--reading-business-objects--reuse-an-unchanged-answer-4` (line 251): **could not run**. Reference instance unavailable from the sandbox; awaiting external run. Replace the documented ETag placeholder with the tag from the preceding GET before running.
- `integrate--reading-business-objects--a-request-that-the-declaration-cannot-answer-5` (line 271): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/background-jobs.md

- `run--background-jobs--curl-1` (line 130): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/developer-instance.md

- `run--developer-instance--curl-1` (line 85): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--developer-instance--curl-2` (line 85): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/health-and-startup-checks.md

- `run--health-and-startup-checks--curl-1` (line 15): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--health-and-startup-checks--curl-2` (line 15): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--health-and-startup-checks--curl-3` (line 129): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/https.md

- `run--https--curl-1` (line 65): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--https--curl-2` (line 65): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--https--curl-3` (line 176): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--https--curl-4` (line 176): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--https--curl-5` (line 176): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--https--curl-6` (line 176): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/install-with-compose.md

- `run--install-with-compose--curl-1` (line 54): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/licence-and-source.md

- `run--licence-and-source--curl-1` (line 52): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/monitoring.md

- `run--monitoring--curl-1` (line 205): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/production-checklist.md

- `run--production-checklist--curl-1` (line 61): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--production-checklist--curl-2` (line 61): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--production-checklist--curl-3` (line 61): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--production-checklist--curl-4` (line 61): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--production-checklist--curl-5` (line 61): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/security-checklist.md

- `run--security-checklist--curl-1` (line 62): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--security-checklist--curl-2` (line 62): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--security-checklist--curl-3` (line 62): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/several-processes.md

- `run--several-processes--curl-1` (line 84): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/sign-in-and-mail-setup.md

- `run--sign-in-and-mail-setup--curl-1` (line 50): **could not run**. Write or outbound webhook: excluded from execution.
- `run--sign-in-and-mail-setup--curl-2` (line 50): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--sign-in-and-mail-setup--curl-3` (line 194): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/troubleshooting.md

- `run--troubleshooting--curl-1` (line 9): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--troubleshooting--curl-2` (line 9): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--troubleshooting--curl-3` (line 95): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--troubleshooting--curl-4` (line 95): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/upgrades.md

- `run--upgrades--curl-1` (line 115): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--upgrades--curl-2` (line 115): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/webhook-delivery.md

- `run--webhook-delivery--curl-1` (line 115): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## examples/the-consumer-api.md

- `examples--the-consumer-api--discover-index` (line 789): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `examples--the-consumer-api--discover-openapi` (line 790): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## guide/integrate/read-through-a-consumer-api.md

- `guide--integrate--read-through-a-consumer-api--discover-index` (line 10): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `guide--integrate--read-through-a-consumer-api--discover-openapi` (line 10): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## integrate/consumer-apis.md

- `integrate--consumer-apis--discover-index` (line 167): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--consumer-apis--discover-openapi` (line 167): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## integrate/signing-in-and-tokens.md

- `integrate--signing-in-and-tokens--inline-read-1` (line 37): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `integrate--signing-in-and-tokens--inline-read-2` (line 37): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/configure.md

- `run--configure--inline-read-1` (line 37): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--configure--inline-read-2` (line 38): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.
- `run--configure--inline-read-3` (line 38): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/licence-and-source.md

- `run--licence-and-source--inline-read-1` (line 26): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## run/monitoring.md

- `run--monitoring--inline-read-1` (line 67): **could not run**. Reference instance unavailable from the sandbox; awaiting external run.

## model/consumer-apis.md

No concrete request example to run. Browser steps and conceptual examples link to the integrator requests; there is no additional concrete HTTP request to inventory.

## guide/model/define-a-consumer-api.md

No concrete request example to run. Browser steps and conceptual examples link to the integrator requests; there is no additional concrete HTTP request to inventory.

## guide/model/see-a-consumer-apis-documents.md

No concrete request example to run. Browser steps and conceptual examples link to the integrator requests; there is no additional concrete HTTP request to inventory.

## guide/model/raise-a-contract-version.md

No concrete request example to run. Browser steps and conceptual examples link to the integrator requests; there is no additional concrete HTTP request to inventory.


# Second turn: saved-response comparison

The first-turn inventory above is historical. The entries below supersede its pending statuses. Responses were supplied by the owner after an external runner execution; no network requests were made by this comparison. The runner is now present and its schema matches the manifest. It replaces every example origin with http://localhost:8480, so production HTTPS and private-engine scrapes have bounded evidence only.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--read-a-stop-by-its-id-1`: **corrected**. Replaced ETag placeholder with captured value. Status, displayed header subset and complete JSON body compared.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--read-a-list-then-narrow-it-2`: **corrected**. Replaced response values at `/nextCursor`, `/anchor`. Status, displayed header subset and complete JSON body compared.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--read-a-list-then-narrow-it-3`: **corrected**. Replaced response values at `/nextCursor`, `/anchor`. Status, displayed header subset and complete JSON body compared.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--look-up-a-stop-number-4`: **matched**. Status, displayed header subset and complete JSON body match the saved response.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--resolve-several-inputs-5`: **matched**. Status, displayed header subset and complete JSON body match the saved response.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--reuse-an-unchanged-answer-6`: **corrected**. Saved request returned 200 with the unchanged object because it sent a literal placeholder. Replaced it with `W/"6d7feaf1a7d44b42750a:1"` from the earlier object GET; 304 is now labelled conditional, not a captured response. Matching-tag 304 still needs a fresh external check.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--correct-a-request-error-7`: **corrected**. Removed absent RDM-Workspace response header. Status, displayed header subset and complete JSON body compared.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--follow-the-declared-event-8`: **corrected**. Replaced response values at `/items/0/code`, `/items/0/id`, `/items/0/eventId`, `/items/0/position`, `/items/0/occurredAt`, `/items/0/change`, `/items/0/cause/kind`, `/items/0/cause/id`, `/items/0/name`, `/items/0/changed`, `/headPosition`, `/caughtUp`, `/cursor`. Status, displayed header subset and complete JSON body compared.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--receive-the-event-at-a-webhook-9`: **could not run**. Excluded write; no saved response. Outbound webhook examples remain explicitly illustrative; subscription creation and token issuance were not verified.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--discover-index`: **matched**. HTTP 200 index identifies stops contract 1, its workspace-specific OpenAPI URL and paged index shape; workspace/release headers match discovery prose.

- `examples/the-consumer-api.md` — `examples--the-consumer-api--discover-openapi`: **matched**. Public HTTP 200 OpenAPI 3.1.0, Stops API contract version 1 and concrete object/list/xref/resolve/events paths match discovery prose. Schema shapes checked against the captured object, list, lookup, resolve and event responses.

- `integrate/reading-business-objects.md` — `integrate--reading-business-objects--a-complete-object-read-1`: **corrected**. Replaced ETag placeholder with captured value. Status, displayed header subset and complete JSON body compared.

- `integrate/reading-business-objects.md` — `integrate--reading-business-objects--a-list-page-with-navigation-2`: **corrected**. Replaced response values at `/nextCursor`, `/anchor`. Status, displayed header subset and complete JSON body compared.

- `integrate/reading-business-objects.md` — `integrate--reading-business-objects--the-same-list-narrowed-by-a-declared-parameter-3`: **corrected**. Replaced response values at `/nextCursor`, `/anchor`. Status, displayed header subset and complete JSON body compared.

- `integrate/reading-business-objects.md` — `integrate--reading-business-objects--reuse-an-unchanged-answer-4`: **corrected**. Saved request returned 200 with the unchanged object because it sent a literal placeholder. Replaced it with `W/"6d7feaf1a7d44b42750a:1"` from the earlier object GET; 304 is now labelled conditional, not a captured response. Matching-tag 304 still needs a fresh external check.

- `integrate/reading-business-objects.md` — `integrate--reading-business-objects--a-request-that-the-declaration-cannot-answer-5`: **corrected**. Removed absent RDM-Workspace response header. Status, displayed header subset and complete JSON body compared.

- `integrate/looking-up-and-resolving.md` — `integrate--looking-up-and-resolving--a-lookup-with-a-score-1`: **corrected**. Replaced response values at `/anchor`. Status, displayed header subset and complete JSON body compared.

- `integrate/looking-up-and-resolving.md` — `integrate--looking-up-and-resolving--a-crosswalk-from-a-stop-number-to-another-system-s-code-2`: **matched**. Status, displayed header subset and complete JSON body match the saved response.

- `integrate/looking-up-and-resolving.md` — `integrate--looking-up-and-resolving--resolve-a-small-file-in-one-request-3`: **matched**. Status, displayed header subset and complete JSON body match the saved response.

- `integrate/consumer-events-and-webhooks.md` — `integrate--consumer-events-and-webhooks--a-declaration-and-the-event-it-exposes-1`: **corrected**. Replaced response values at `/headPosition`, `/cursor`, `/caughtUp`, `/items/0/object/stopNumber`, `/items/0/object/validFrom`, `/items/0/object/operator/name`, `/items/0/object/operator/code`, `/items/0/object/operator/id`, `/items/0/object/longitude`, `/items/0/object/modes/0/name`, `/items/0/object/modes/0/code`, `/items/0/object/modes/0/id`, `/items/0/object/latitude`, `/items/0/object/name`, `/items/0/object/height`, `/items/0/object/id`, `/items/0/object/systemCodes`, `/items/0/object/abbreviation`, `/items/0/object/code`, `/items/0/cause/kind`, `/items/0/cause/id`, `/items/0/position`, `/items/0/changed`, `/items/0/eventId`, `/items/0/name`, `/items/0/stateAt`, `/items/0/id`, `/items/0/occurredAt`, `/items/0/change`, `/items/0/code`. Status, displayed header subset and complete JSON body compared.

- `integrate/consumer-events-and-webhooks.md` — `integrate--consumer-events-and-webhooks--the-actual-webhook-request-shape-2`: **could not run**. Excluded write; no saved response. Outbound webhook examples remain explicitly illustrative; subscription creation and token issuance were not verified.

- `guide/integrate/read-through-a-consumer-api.md` — `guide--integrate--read-through-a-consumer-api--work-through-the-reference-contract-1`: **matched**. HTTP 200 bare Stop object, typed values, parent/path, operator and arrays match the guide and linked complete response.

- `guide/integrate/read-through-a-consumer-api.md` — `guide--integrate--read-through-a-consumer-api--work-through-the-reference-contract-2`: **matched**. HTTP 200 items envelope with workspace, publication and paging fields matches the guide; first stop is Selva, via Alpsu spv., total 2443.

- `guide/integrate/read-through-a-consumer-api.md` — `guide--integrate--read-through-a-consumer-api--discover-index`: **matched**. HTTP 200 index identifies stops contract 1, its workspace-specific OpenAPI URL and paged index shape; workspace/release headers match discovery prose.

- `guide/integrate/read-through-a-consumer-api.md` — `guide--integrate--read-through-a-consumer-api--discover-openapi`: **matched**. Public HTTP 200 OpenAPI 3.1.0, Stops API contract version 1 and concrete object/list/xref/resolve/events paths match discovery prose. Schema shapes checked against the captured object, list, lookup, resolve and event responses.

- `guide/integrate/resolve-a-file-of-codes.md` — `guide--integrate--resolve-a-file-of-codes--try-two-rows-from-the-reference-world-1`: **matched**. HTTP 200: row-1 found Tschamut-Selva at score 900, row-2 not_found/NO_MATCH; input order, refs and counts match the guide and linked complete response.

- `guide/integrate/subscribe-a-webhook-and-verify-it.md` — `guide--integrate--subscribe-a-webhook-and-verify-it--use-the-reference-event-end-to-end-1`: **could not run**. Excluded write; no saved response. Outbound webhook examples remain explicitly illustrative; subscription creation and token issuance were not verified.

- `integrate/consumer-apis.md` — `integrate--consumer-apis--discover-index`: **matched**. HTTP 200 index identifies stops contract 1, its workspace-specific OpenAPI URL and paged index shape; workspace/release headers match discovery prose.

- `integrate/consumer-apis.md` — `integrate--consumer-apis--discover-openapi`: **matched**. Public HTTP 200 OpenAPI 3.1.0, Stops API contract version 1 and concrete object/list/xref/resolve/events paths match discovery prose. Schema shapes checked against the captured object, list, lookup, resolve and event responses.

- `integrate/signing-in-and-tokens.md` — `integrate--signing-in-and-tokens--inline-read-1`: **matched**. HTTP 200 discovery advertises the reference public origin, authorize/token/revoke/JWKS endpoints, client_credentials and S256, matching the metadata example. Production HTTPS was not exercised.

- `integrate/signing-in-and-tokens.md` — `integrate--signing-in-and-tokens--inline-read-2`: **matched**. Public HTTP 200 JWKS contains ES256 verification keys with kid, matching the documented key endpoint. No token validation or rotation was exercised.

- `run/background-jobs.md` — `run--background-jobs--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/configure.md` — `run--configure--inline-read-1`: **matched**. HTTP 200 system identity includes engine.sourceCode, version 0.12.0, management API v1, licence, schema language 0.10 and active release, matching the named operation and source-location claim.

- `run/configure.md` — `run--configure--inline-read-2`: **matched**. HTTP 200 configuration has database and settings, matching the named operation. No setting was changed; environment changes and recreation were not tested.

- `run/configure.md` — `run--configure--inline-read-3`: **matched**. HTTP 200 capabilities exposes model/workspace administration, jobs, feeds, consumer API and subscription groups, matching the named operation. Capability switching was not tested.

- `run/developer-instance.md` — `run--developer-instance--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/developer-instance.md` — `run--developer-instance--curl-2`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/health-and-startup-checks.md` — `run--health-and-startup-checks--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/health-and-startup-checks.md` — `run--health-and-startup-checks--curl-2`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/health-and-startup-checks.md` — `run--health-and-startup-checks--curl-3`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/https.md` — `run--https--curl-1`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/https.md` — `run--https--curl-2`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/https.md` — `run--https--curl-3`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/https.md` — `run--https--curl-4`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/https.md` — `run--https--curl-5`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/https.md` — `run--https--curl-6`: **matched**. Public nginx returned 404 HTML, as documented for the Compose web boundary. The Prometheus response requires the internal engine address; neither the internal scrape nor OAuth monitoring-client credentials were exercised.

- `run/install-with-compose.md` — `run--install-with-compose--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/licence-and-source.md` — `run--licence-and-source--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/licence-and-source.md` — `run--licence-and-source--inline-read-1`: **matched**. HTTP 200 system identity includes engine.sourceCode, version 0.12.0, management API v1, licence, schema language 0.10 and active release, matching the named operation and source-location claim.

- `run/monitoring.md` — `run--monitoring--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised. X-Request-Id echoes operator-check; server logs were not captured.

- `run/monitoring.md` — `run--monitoring--inline-read-1`: **matched**. Public nginx returned 404 HTML, as documented for the Compose web boundary. The Prometheus response requires the internal engine address; neither the internal scrape nor OAuth monitoring-client credentials were exercised.

- `run/production-checklist.md` — `run--production-checklist--curl-1`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/production-checklist.md` — `run--production-checklist--curl-2`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/production-checklist.md` — `run--production-checklist--curl-3`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/production-checklist.md` — `run--production-checklist--curl-4`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/production-checklist.md` — `run--production-checklist--curl-5`: **matched**. Public nginx returned 404 HTML, as documented for the Compose web boundary. The Prometheus response requires the internal engine address; neither the internal scrape nor OAuth monitoring-client credentials were exercised.

- `run/security-checklist.md` — `run--security-checklist--curl-1`: **matched**. HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).

- `run/security-checklist.md` — `run--security-checklist--curl-2`: **matched**. Public nginx returned 404 HTML, as documented for the Compose web boundary. The Prometheus response requires the internal engine address; neither the internal scrape nor OAuth monitoring-client credentials were exercised.

- `run/security-checklist.md` — `run--security-checklist--curl-3`: **matched**. HTTP 401 JSON with AUTHENTICATION_REQUIRED and WWW-Authenticate: Bearer matches the unauthenticated refusal.

- `run/several-processes.md` — `run--several-processes--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/sign-in-and-mail-setup.md` — `run--sign-in-and-mail-setup--curl-1`: **could not run**. Excluded write; no saved response. Outbound webhook examples remain explicitly illustrative; subscription creation and token issuance were not verified.

- `run/sign-in-and-mail-setup.md` — `run--sign-in-and-mail-setup--curl-2`: **matched**. Authenticated HTTP 200 JSON workspace collection matches the example. The runner authenticated as a person; the displayed client-credentials exchange was excluded, so client setup is not verified.

- `run/sign-in-and-mail-setup.md` — `run--sign-in-and-mail-setup--curl-3`: **matched**. HTTP 200 discovery advertises the reference public origin, authorize/token/revoke/JWKS endpoints, client_credentials and S256, matching the metadata example. Production HTTPS was not exercised.

- `run/troubleshooting.md` — `run--troubleshooting--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/troubleshooting.md` — `run--troubleshooting--curl-2`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/troubleshooting.md` — `run--troubleshooting--curl-3`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/troubleshooting.md` — `run--troubleshooting--curl-4`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/upgrades.md` — `run--upgrades--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/upgrades.md` — `run--upgrades--curl-2`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

- `run/webhook-delivery.md` — `run--webhook-delivery--curl-1`: **matched**. HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.

## Boundary classification corrections

The following six HEAD responses are counted as **could not run as documented**, rather than matched: their production origins were replaced by the development origin. The earlier per-example entries describe only the observed 200 response.

- `run/https.md` — `run--https--curl-1`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

- `run/https.md` — `run--https--curl-3`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

- `run/https.md` — `run--https--curl-4`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

- `run/production-checklist.md` — `run--production-checklist--curl-1`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

- `run/production-checklist.md` — `run--production-checklist--curl-2`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

- `run/security-checklist.md` — `run--security-checklist--curl-1`: **could not run**. Could not run the documented production-origin check: the runner replaced HTTP/HTTPS example origins with http://localhost:8480. HEAD returned 200 text/html there. HTTP-to-HTTPS redirects, certificate trust and production headers remain unverified; production instructions were retained.

## Disagreements and limits

1. Two missing-list examples showed `RDM-Workspace`, but their real 404 responses omit it. Removed it from both examples and narrowed the blanket success/error header claim on the business-object page. `backend/app/consumer/router.py` also says every response names its workspace; the instance contradicts that statement for these refusals. No backend files changed.
2. Two feed illustrations supposed a name update at position 64, head 64, and caughtUp true. The real first matching event after 63 is a creation at 207 by job 99f69475-71d1-47ce-abde-559e238691f4, head 8950, caughtUp false; the full object has stateAt 8950. Replaced the complete bodies and accompanying explanations. This is a difference between illustrative data and the instance, not evidence of a feed defect.
3. Two conditional requests sent quoted placeholder ETags and correctly returned 200. Real preceding object GETs provide `W/"6d7feaf1a7d44b42750a:1"`. Both pages and request entries now use it and explain how to obtain the entire value. The 304 exchange is explicitly conditional; no corrected-tag 304 response has been captured. The saved OpenAPI promises 304 on a matching tag and the implementation supports it, but that is not live verification.
4. Five list/lookup examples had placeholder cursors or anchors. Replaced them with complete real values; shapes, counts (2443 stops, 13 for MGB-fo), record values, lookup score 900 and resolve outcomes otherwise match.
5. The monitoring path `/metrics` is correct. The runner used public nginx at localhost:8480, where both authenticated and unauthenticated requests deliberately return 404 HTML. `frontend/nginx/snippets/locations.inc.template` explicitly returns 404 there; `backend/app/management/routers/system.py` exposes the protected Prometheus route internally. Clarified the page and changed this public-origin manifest entry to expectStatus 404. No private scrape was captured.
6. Six production HEAD examples were rewritten to the development HTTP origin, returning 200 rather than testing the documented HTTP redirect or HTTPS boundary. Production instructions remain intact; redirects, TLS and HSTS are not verified by these responses. Health probes match only their status/body boundary, not surrounding recovery/upgrade instructions. The request-ID echo matches, but no server logs were supplied.
7. Four writes were skipped: two outbound webhook illustrations, subscription creation and token issuance. Their bodies, headers, delivery signatures and creation/token responses remain unverified against the instance. Capabilities reports manageSubscriptions false on this reference instance. No settings were changed or writes attempted.
8. The consumer comparison table’s operator body is renderer-derived and has no saved standalone GET response in this run. Declaration fragments and generated schemas are not HTTP request examples; the saved public OpenAPI confirms the listed concrete operations and shared response shapes, but does not verify every declaration rule. Model-editor steps were not executed.
9. The runner is now present; its documented requests[] schema matches this manifest. Earlier missing-runner notes describe the first turn only. Every saved response was inspected without issuing a network request or changing a saved response.

## Second-turn final checks

- Compared all 66 supplied response files; all 70 inventory entries have final outcomes.
- Independently verified all 15 complete JSON response examples against saved bodies,
  statuses and every displayed response header. All match exactly after correction.
- Both conditional request entries now use the real preceding GET ETag, and both pages
  explain its origin and preserve its weak prefix and quotes. A corrected-tag 304 remains
  unverified; the saved original 200 answers were not overwritten or relabelled.
- All JSON fences on the six edited pages parse. The final diff was reviewed against
  before-page snapshots. No source code, saved responses, screenshots or other-wave
  files were edited; no commits or state-changing git commands were used.
- `GUIDE_OUT=_build/C12-LIVE npm run build` in `guide/`: passed, 225 pages in 5.07 s.
  Astro warned that the generated `/404` route conflicts with the higher-priority `/404`
  route; the build completed. The earlier Caddy highlighting warning was not emitted
  by this build. Neither routing/configuration file is in this wave's editable scope.
- No screenshots needed. No live write, private scrape, production TLS, recovery,
  model-editor, webhook delivery or full application acceptance was performed.
