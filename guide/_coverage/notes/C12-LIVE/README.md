# Current status: second turn

All 66 saved responses have now been compared. The request runner and its documentation
are present and were read; compatibility of the manifest fields is confirmed by inspection
and the supplied run. No network requests were issued during comparison. `results.json`
contains the final per-example classification; reconciliation has counts and all limitations.
Before-page snapshots support review of the six edited pages. ETag request entries now
carry the real sample tag; use a fresh response header before any later retry. The public
monitoring request expects 404. The notes below describe the earlier inventory turn only.

---

# C12 inventory handover

This is the first turn: no request has been sent and no response has been verified.
The wave explicitly says the reference instance cannot be reached from this sandbox.
`guide/_coverage/live/` and `guide/tools/live-requests.mjs` were absent when inspected.
`CODEX_TOOL.md` contains Screenshots but no Live requests section. Consequently the
manifest's compatibility with the missing runner cannot be checked here. It retains
the existing top-level `requests` array and the field names required by the wave.

Each entry has a page-specific, filesystem-safe name, auth, method, path, query,
headers, body and write flag. `page` and `line` locate the source; lines are a snapshot
and may move when another wave edits pages. `expectStatus` records an explicitly
illustrated response, including errors and conditional 304 answers. Other metadata
(`exampleOrigin`, `exampleHost`, `credentialRequired`) is advisory, not a known runner
extension. Query values are strings, as in the displayed URL.

- The runner supplies the reference host and bearer authentication selected by `auth`.
  Displayed `Host: <instance>` and bearer-token placeholders are therefore not literal
  outgoing headers. Other headers and JSON bodies are preserved from the examples.
- Do not run any `write: true` entry. This includes subscription creation, outbound
  webhook illustrations and the OAuth token exchange (conservatively excluded because
  it issues credentials). The token exchange needs real Basic credentials; its header
  is a placeholder, never an actual secret.
- Resolve POSTs are read-only and remain `write: false`.
- Conditional examples need the real ETag from their preceding object GET, substituted
  for the documented placeholder. A literal placeholder cannot test the promised 304.
  The missing runner prevents specifying a supported capture/substitution mechanism.
- Outbound webhook bodies, signatures, timestamps and delivery IDs are illustrations
  of requests sent to `receiver.example`, not callable routes on refiroo. Never replay
  them against the reference instance or a receiver.
- Preserve each curl example's intended access boundary. HTTP-to-HTTPS redirects,
  TLS certificates, security headers and public `/metrics` 404 require the public proxy;
  probing the engine directly is not equivalent. `exampleOrigin` preserves that intent.
- Expected health 200 assumes a ready reference installation. Requests shown after an
  operator recovery command inventory only the probe, never execute the recovery command.
- Repeated examples stay separate for reconciliation per page. Successful HTTP delivery
  alone cannot verify the mail, TLS trust, recovery or log observations around a probe.
- API-reference links, declaration fragments, route templates, generated-message examples,
  log lines and narrative operation names are not executable request examples. They do
  not justify inventing IDs, request bodies or query parameters.

`inventory.py` extracts fenced HTTP requests and curl examples without network access.
It checks for steering before saving each page and saves the manifest, reconciliation
entries and progress before starting the next page. Supplemental inline discovery
and management reads are listed separately in the manifest with descriptive names.

The model consumer-API page and its guides contain browser instructions and links to
integrator examples, rather than additional executable requests. No guide page has
been rewritten based on an unverified response.
