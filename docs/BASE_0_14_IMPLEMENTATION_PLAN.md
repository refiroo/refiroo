# Base 0.14 implementation plan

**Status:** Created 2026-10-10 by the user, to hold the work left open when 0.9 closes: Track V's
V3–V9 (the management API documented, planned 2026-10-07 inside 0.9) and the rework of the type
palettes A and B (TODO since 2026-10-07). Planned before 1.0 for now; the user expects to move this
release after 1.0 later. V-D2–V-D10 are decided by the user (2026-10-07). **Re-planned for building
2026-11-11** ([below](#re-planned-for-building-2026-11-11)): measured again on the code, the areas resized
for today's 251 operations, the Settings › Model redesign added from TODO, UP2 closed, R planned. Open
for the user: none (V-D1, V-D2a, V-D11–V-D13 decided by the user 2026-11-11; V-D12 changed: Sonnet writes the text). **Track V is complete: V3 to V12 are delivered 2026-11-11** ([V3 record](#v3-record-and-the-example-data-inventory-2026-11-11), [V4 record](#v4-record-2026-11-11), [V5 record](#v5-record-2026-11-11), [V6 record](#v6-record-2026-11-11), [V7 record](#v7-record-2026-11-11), [V8 record](#v8-record-2026-11-11), [V10](#v10-the-operation-kinds-in-the-document) inside V8, [V11 record](#v11-record-2026-11-11), [V12 record](#v12-record-2026-11-11), [V9 record and the closing record of Track V](#v9-record-and-the-closing-record-of-track-v-2026-11-11)); R is not built.

**Overlap with 0.13 (decided by the user 2026-10-26; changed by 0.13's restart of 2026-11-02):** the
documentation release 0.13 writes the guide and links to this release's `/docs/api` text (no double writing,
DOC-D12). The error catalogue was to be written in 0.13's DOC2 (DOC-D13); **0.13's restart removed DOC2's
description and error-catalogue work and left the catalogue with 0.14** ([0.13 plan, "Restarted
2026-11-02"](BASE_0_13_IMPLEMENTATION_PLAN.md#restarted-2026-11-02)). The file's place stays the one the user
decided in DOC-D22 (`backend/app/management/reference/content/errors.md`); the file does not exist yet, so V3
writes the catalogue again.

**Target:** Product 0.14, [management API reference and UI refinements](ROADMAP.md#product-release-014--management-api-reference-and-ui-refinements).
0.16 was released before 0.13–0.15 and 0.13 ships as 0.16.1-alpha.5 ([PROJECT_STATUS](PROJECT_STATUS.md)), so
0.14 ships as the next 0.16.1 pre-release after 0.13's; R sets the number.

**Depends on:** Product 0.9.0 released (V2, the consumer contracts as reference sources; UA's type
palettes, ADR-040, U-D13). Neither track depends on 0.15 or 0.17, and nothing in them blocks those
releases. Packages can start before 0.13's release commit; 0.14's R comes after 0.13's, so its full review
starts from 0.13's release commit. A V package documents authentication too (every operation is signed in
since 0.12).

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [V3](#packages-1) | — | **Delivered 2026-11-11.** The mechanism (content directory and merge, recording, error listing, gap check, size), the example data, the conventions and the error catalogue (348 codes); system and workspaces |
| [V4–V8, V10–V12](#packages-1) | V3 | **Delivered 2026-11-11.** One area each, in any order: records; relations and mappings; change sets; jobs, imports and files; the model with its operation kinds; security; AI, mail and notifications |
| [V9](#packages-1) | all V | **Delivered 2026-11-11.** Webhooks (consumer subscriptions) and the close-out: gap list empty and deleted, [closing record](#v9-record-and-the-closing-record-of-track-v-2026-11-11) |
| UP1, UP3 | — | **Dropped by the user 2026-11-11** (the palettes stay as they are; Settings › Model stays as it is) |
| VD | Track V | **Decided by the user 2026-11-11, delivered 2026-11-11 ([record](#vd-record-2026-11-11)):** the 20 open API documentation discrepancies resolved: API.md corrected for 11, the code fixed for 9 (TODO "API documentation discrepancies"), one package before R |
| [R](#r-build-acceptance-and-release) | all | Full review of every change since 0.13's release commit, the announced runs, the release |
| [UP2](#up2-an-application-opens-on-a-start-page-closed) | — | **Closed** by 0.12 D336 (accepted with HM1's plan 2026-10-25): Home is the first screen |

## Re-planned for building (2026-11-11)

The track was planned on 2026-10-07 for 74 operations. Measured again on `create_app().openapi()` at
`1bcbad00` (in a clean worktree, because the shared tree's uncommitted work did not import):

| | 2026-10-07 | 2026-11-11, default settings | with `CONSUMER_SUBSCRIPTIONS_ENABLED` and `MODEL_ADMIN_MUTATIONS_ENABLED` |
| --- | --- | --- | --- |
| Operations | 74 (about 91) | 251 | 294 |
| With a description | 15 | 188 | 218 |
| With an error response besides the default | 0 | 0 | 0 |
| Parameters described | 151 of 373 | 638 of 1,064 | 709 of 1,196 |
| Schemas described | 75 of 176 | 344 of 623 | 466 of 777 |
| Schema fields described | — | 312 of 3,429 | 392 of 4,293 |
| Tags with text | 0 of 11 | 0 of 21 (no `tags` list in the document) | — |
| `info.description` | one line | 110 characters | — |
| Document size | 290 KB | 1,158 KB | — |
| Error codes the backend raises (`test_api_journeys.raised_codes`) | about 286 | 348 | — |
| Operation kinds named in the document (V10) | 0 | 0 | — |

Operations per tag (default settings): security 65, change-sets 23, model 21, ai 19, imports 12, model
mappings 12, workspaces 11, jobs 10, objects 9, mail 8, notifications 8, relations 8, oauth 7, agent-access 7,
system 7, mapping 7, source files 7, attributes 4, relation-matrix 3, changes 1, untagged 2; consumer
subscriptions with the setting on.

What follows from it:

- **The areas are resized** (V-D13): the October table covered about 91 operations and had no place for
  security, sign-in, agent access, AI, mail, notifications, imports and source files, which arrived in
  0.10–0.16. Two areas are added (V11 security, V12 AI, mail and notifications), V7 takes imports and source
  files, V8 takes model mappings and V10's operation kinds. IDs V3–V10 keep their meaning.
- **The guide links by tag.** 52 guide pages link to `/docs/api/?api=management#tag/<tag>` (objects, model,
  ai, jobs, security, consumer subscriptions…). Tag names stay as they are; V3's gap check also fails on a
  guide link to a tag the document does not have.
- **Size.** The document is already 1.16 MB without the examples, so 294 inline examples likely pass V-D10's
  2 MB line. V3 measures once with its own examples and decides by V-D10's rule (separate example files the
  document references above 2 MB).
- **The example data** (V-D2a) and **who writes the text** (V-D12) are new questions, because 0.13 settled
  both for the guide after V-D2 was decided.
- **Settings › Model's redesign** is in TODO as "For 0.14" (the user, 2026-10-16) and was in neither this plan
  nor the roadmap; it is UP3.
- **UP2 is closed**: D336 was accepted with HM1's plan on 2026-10-25. Reopened only if the user asks for the
  application switch alone.

## Track V — The management API documented

_Moved from [Base 0.9](BASE_0_9_IMPLEMENTATION_PLAN.md) on 2026-10-10 unchanged, except for V-D9's
amendment. Planned at the user's request 2026-10-07._


**Why.** `/docs/api` shows every management operation, but the document behind it says very little.
Measured on `create_app()` on 2026-10-07: 74 operations by default (about 91 with model
administration and webhooks enabled). 74 have a summary and 15 a description. No operation documents
an error response besides the shared default envelope. 151 of 373 parameters and 75 of 176 schemas are
described. `info.description` is one line, and the eleven tags have no text. The document has three
examples. The behaviour is recorded in API.md, INTEGRATION_API, CONSUMER_API and the code. API.md is
written for builders and organised by delivery, so an integrator reading `/docs/api` cannot learn from it
what an operation is for, how it behaves, what it refuses, or what a real exchange looks like.

**Outcome.** For every management operation, `/docs/api` states:

- **what it is for**, with the use cases;
- **how it behaves**: contexts (workspace, change set, publication, `asOf`), versions and optimistic
  concurrency, paging, ordering, defaults and side effects (audit, feed, events);
- **its limitations**: limits, what it does not do, and the operation to use instead;
- **its errors**: each status with the codes it can carry, what each code means and what the client
  should do;
- **an example request and response**, recorded from a run against the extended starter's seeded
  database (V-D3), not written by hand: one per operation to start (V-D4).

Each tag gets an area overview: the concepts, how its operations fit together, and the common
sequences, for example "create a change set, edit, validate, publish". The document's own
description covers the conventions every operation shares: identifiers, contexts, versions, paging,
the error envelope, idempotency, and the optional surfaces with the settings that enable them.

**Sources, in order of authority:** the code (what the API does), then API.md, INTEGRATION_API and
CONSUMER_API (what was decided), then the journey catalogue (what the use cases are). Where the code
and the documents disagree, see V-D7.

### Decisions

| # | Question | Decision |
| --- | --- | --- |
| V-D1 | Where does the text live? | **Decided by the user 2026-11-11: the recommendation.** _The user asked for a minimal footprint in the code (2026-10-07)._ _The catalogue's place inside it, `content/errors.md`, was decided by the user in 0.13's DOC-D22 (2026-11-02)._ Recommendation: **the code holds no documentation text and no examples.** One function merges a content directory into the generated OpenAPI document when the app builds it, the way FastAPI's documented `app.openapi()` override does. The directory is `backend/app/management/reference/content/`, shipped as package data like the bundled Scalar script. It holds an `index.md` for the document's conventions and, per tag, one Markdown file with the area overview and a section for each operation, headed by its method and path (`POST /api/v1/objects`) and holding the purpose, behaviour, limitations, errors and parameter notes. It also holds `errors.md`, the code catalogue (V-D5), and `examples/`, one JSON file per operation with its named example requests and responses, written by the recording (V-D3). Keys are method and path, the public contract, not FastAPI's generated `operationId`, which follows Python function names. The in-code descriptions that already exist (15 operations, 151 parameters, 75 schemas) stay. New field text goes in the code only where the field is otherwise undescribed and a sentence is enough. A section naming a route that no longer exists fails the V-D6 check. API.md remains the builders' contract record (DOCUMENTATION_PLAN "Not included"). API.md says what was decided and why, and `/docs/api` says how to use it |
| V-D2 | Which model and data do the examples use? | **Decided by the user 2026-10-07: the bundled starter, extended until it holds every capability the documentation must show, both for the examples and for demonstrating the engine.** The extension is a new content release of the starter, shipped to every new deployment, so a reader can repeat every example on a fresh install. The starter has no domain-specific content (domains, codelists, master values such as delivery methods, systems and translations). Today it holds only part of the structures the journey tests name (checked in `configurations.py`, `example()`): a root type with a unique code, and languages, translation groups and translations with a scoped uniqueness rule. It lacks a self-hierarchy, a many-to-many relation with its own attributes, a one-to-one relation, a type ladder to restructure across, the integer range, required, read-only-with-default and at-least-one rules, and a consumer API with match rules and every parameter kind. V3 lists every capability the documented operations need, maps each to the starter type that shows it or to the smallest addition in the same domain, and adds them. The journey tests on the `example` configuration then cover more structures, because the starter holds more. The example model is not used, because its content reads as one business domain |
| V-D3 | Where do the examples come from? | **Decided by the user 2026-10-07: recorded from a run, and kept current by a rule, not by a comparison check.** A reference scenario calls the public API on the extended starter's seed, built once and reused. Each step records a request and its response into the operation's example file, normalised: IDs become stable readable placeholders (consistent across steps, so a created ID reappears in the next request) and times are fixed. Each step asserts only the status and code it records. The rule (V-D8): a change to a route's behaviour or shape regenerates that route's examples in the same change, and the git diff of the example files shows the change for review. There is no committed-versus-rerun comparison |
| V-D4 | How many cases? | **Decided by the user 2026-10-07: one example per operation to start**, the operation's main successful use. The errors are described in text (V-D5), not shown as examples. After V3, the user looks at how the examples read, how much space they take and how manageable they are, and decides whether more are added (more use cases, error examples) |
| V-D5 | How are errors documented? | **Decided by the user 2026-10-07: a few sentences for every error code**, in the code catalogue `errors.md`, written once per code: what the code means, why it happens with a hint at the usual root cause, and what the client does about it. Today a code carries a short message at the place it is raised; the catalogue explains it. Each operation lists its statuses as OpenAPI responses with the codes each can carry, linked to the catalogue, from reading the operation's code path. One check: every code the backend raises (the set `test_api_journeys` already collects) has a catalogue entry and is listed on at least one operation |
| V-D6 | How does completeness stay visible? | **Approved by the user 2026-10-07.** A contract test from V3 on lists every operation without a content section or example, every parameter and schema field without a description, every content section or example naming a route that does not exist, and every code without a catalogue entry. It compares them with a committed gap list that may only shrink. Each package empties the list for its area, and V9 deletes the list. The text is written for integrators: no package or decision IDs and no history (DOCUMENTATION_PLAN principle 1). Each statement can be checked against the code |
| V-D7 | What if the code and API.md disagree? | **Decided by the user 2026-10-07: logged, highlighted and decided separately.** The package documents what the code does, records the discrepancy in TODO under "API documentation discrepancies" (the route, what API.md says, what the code does, where) and lists it at the top of its record and its report, so it is not missed. The decision (fix the code or correct API.md) is taken separately. API.md is read on every prompt, so few discrepancies are expected |
| V-D8 | How does the documentation stay current? | **Approved by the user 2026-10-07, as part of the coding-agent guide.** V3 adds the rule to AGENTS.md (working method, the documentation step) and to "How a package is delivered", step 3: a change that adds or changes a management route updates its content section, its error listing and catalogue entries, and regenerates its examples, in the same change |
| V-D9 | Where in the queue? | **Decided by the user 2026-10-07: Track V's V3–V9 are independent and block no release, neither 0.9.0 nor 1.0.** _Amended 2026-10-10 by the user: moved from 0.9 to release 0.14, planned before 1.0 for now and expected to move after it; still independent of every other release._ They are fillers taken when chosen. R and R-a do not wait for them. DOC2's audit of the OpenAPI descriptions is done here instead, and DOC2 keeps the settings, limits and model language references; DOCUMENTATION_PLAN gets a pointer in V3 |
| V-D10 | Document size | **Approved by the user 2026-10-07.** Examples stay short: pages of two or three items, and long arrays trimmed in the recording with a note saying so. The document is 290 KB today. V3 measures it with V3's examples, projects the full size and reports. If the projection is over about 2 MB, examples are served as separate files that the document references, not inline. Measured once and not tuned in a loop |
| V-D2a | Which data do the examples use, now that 0.13 chose one example world? (V-D2 against 0.13) | **Decided by the user 2026-11-11: the recommendation (the guide's reference model and data; V-D2's starter extension is dropped).** V-D2 (the user, 2026-10-07) extends the bundled starter for the examples. 0.13's restart then made the Graubünden reference data the one example world of the guide ([`guide/AGENTS.md`](../guide/AGENTS.md); `guide/samples/model.json` and its loader, the Docker reference instance, the `stops` consumer API the public API page already shows). Following V-D2 gives the reader two example worlds: the guide's stops and municipalities, and `/docs/api`'s starter records. Recommendation: **record the examples on the guide's reference model and data, and leave the starter as it is.** Why: the guide's integration pages link into `/docs/api`, so the same records appear on both; the reference model already holds a containment ladder (canton, district, municipality, stop), a self-hierarchy (`mode-has-child`), a mapping (`system-code-maps-to`), translations and a consumer API; a reader repeats an example by loading the samples (`guide/samples/load.py`) or starting the reference instance. Cost: a fresh install does not hold the examples' records until the samples are loaded; capabilities V3's inventory finds missing (for example a many-to-many relation with its own attributes, not checked) are added to the reference model, which the guide's screenshots then show too, so a screenshot rerun follows. Not chosen: V-D2 as decided, a new starter content release shipped to every deployment |
| V-D11 | (see [V10](#v10-the-operation-kinds-in-the-document)) | **Decided by the user 2026-11-11: the recommendation** (the schemas describe; the kinds keep checking) |
| V-D12 | Who writes the reference text? | **Decided by the user 2026-11-11: Claude writes all of Track V, on Sonnet (the `implementer`); no Codex and no Opus, because it is technical documentation.** Each package's statements are still checked against the code paths, with V-D7's discrepancies logged. _The recommendation it replaced:_ About 350 catalogue entries, 294 operation sections and 22 area overviews. For the guide the user decided that Codex writes all page text and Claude writes the mechanism and briefs (0.13's restart, after a Claude-written approach failed). Recommendation: **the same split.** Claude builds the mechanism, the recordings and the gap check, and writes one guidance page for the reference (who reads it, what an operation section and a catalogue entry hold, the V-D6 rules), beside `guide/AGENTS.md`; Codex writes the conventions, the catalogue and each area's text from the code, through the existing Codex tool, in agreed windows; Claude checks each area's statements against the code paths (V-D7's discrepancies logged) before the package closes. At a Codex limit the work waits for the reset. Cost: Codex usage, and an area waits on Codex availability. Not chosen: Claude writes the reference text, which keeps it in one session but is the approach 0.13 dropped |
| V-D13 | How are the 294 operations divided? | **Decided by the user 2026-11-11: the recommendation.** by tag, as the [Packages](#packages-1) table below, one area per package, 20–80 operations each; security (79 with sign-in and agent access) is the largest and is one package because its overview explains one model (people, groups, roles, grants, clients). Not chosen: more, smaller packages, each with the same review and contract re-baselining |

### Packages

Each package documents one area completely by V-D1–V-D6 and empties its part of the gap list. Its
tests are the `reference` group (new in V3: the recording run, whose steps assert their status and
code) and `contract` (the OpenAPI lock, re-baselined for each package by diffing the document). The
operation counts are today's by tag (2026-11-11, default settings unless named); the gap list, not this
table, is the measure of what is left. _Resized 2026-11-11 (V-D13, open): the October table covered about 91
operations._

| Package | Needs | Area (operations) |
| --- | --- | --- |
| **V3** Foundation and the service | — | The example data (V-D2a: the capability inventory the documented operations need, each mapped to the reference model's type that shows it, the smallest additions; under V-D2 as decided, the starter instead). The mechanism: the content directory and its merge (V-D1), the scenario harness and recording (V-D3), the per-operation responses (V-D5), the gap list and its check with the guide's tag links (V-D6), and the size measurement (V-D10). The guidance page for the writer (V-D12) and the V-D8 rule in AGENTS.md and the delivery steps. Text: the document's conventions (`info.description`: identifiers, contexts, versions, paging, the error envelope, idempotency, authentication, the optional surfaces and their settings), the catalogue entry of every one of the 348 error codes, and `system`, `workspaces`, `changes` and the two untagged operations (21). Ends with the user's look at how the examples and the catalogue read (V-D4) |
| **V4** Records | V3 | `objects` and `attributes` (13): create, read, update, delete, the per-type list and the cross-type lookup, the model-aware query, attribute values, history and parent candidates. Contexts, `asOf`, filters and sorts, uniqueness and required rules, moving a record |
| **V5** Relations and mappings | V3 | `relations`, `mapping` and `relation-matrix` (18): relations and their batch, the edge list, the mapping reads and replacement, the matrix. Relation rules, cardinality, containment as a relation, coverage |
| **V6** Change sets and publications | V3 | `change-sets` (23): list, create, read, update, delete, object and relation changes, validation, approvals, publication, restructuring preview and apply, publications and withdrawal. How a change set merges onto live data, conflicts, publication snapshots |
| **V7** Bulk, jobs, imports and files | V3 | `jobs` (with `exports`), `imports` and `source files` (29): `POST /batches` with every item kind, exports, jobs (read, list, items, cancel), workbook imports and profiles, stored files. Idempotency, failure policies, item outcomes, background runs, retention and `410` |
| **V8** The model | V3 | `model`, `model mappings`, `model administration` and `moves` (33, more with `MODEL_ADMIN_MUTATIONS_ENABLED`; `moves` assigned 2026-11-11, it had no package), with [V10](#v10-the-operation-kinds-in-the-document)'s 67 operation kinds in the same package because they are these routes' request bodies. The model is the bulk of the area overview: the operations are few, but what they describe is the whole engine |
| **V11** Security | V3 | `security`, `oauth` and `agent-access` (79): people, groups and members, roles and grants, sign-in and its providers, second factors and passkeys, clients and tokens, agent clients. The overview explains who may do what and how a client signs in |
| **V12** AI, mail and notifications | V3 | `ai`, `mail` and `notifications` (35): the provider settings, proposals, assistant tasks, query translation and summaries; mail settings; notices, digests and following. What is sent to a provider at each send level |
| **V9** Webhooks, and close-out | V3–V8, V10–V12 | `consumer subscriptions` (with `CONSUMER_SUBSCRIPTIONS_ENABLED`): create, read, update, suspend, resume, delete, deliveries and resend. Retries, batching and signing, as DOCUMENTATION_PLAN's points require. Then the close-out: the gap list empty and deleted, the V-D5 check passing over the whole document, the API.md pointer to `/docs/api` added, the guide's links checked, the public build (`static_site`) rebuilt and looked at; the code extraction widened to codes raised with a conditional status (`409 if stale else 422`, found in V5), and the codes it then finds catalogued; a schema's own description written in the content files (a line under its `### Schema` heading replaces the in-code one, settled 2026-11-11 by V-D1's rule), for every schema whose in-code description carries package or decision IDs (202 found in V11) |

**Not included:** the consumer read API (`/consumer/...`). Its documents are generated per
definition from the model, and their descriptions are a separate question (TODO once V-D1 is
approved). Also excluded: tutorials and how-to guides (DOCUMENTATION_PLAN 0.13) and translations.

**Composable domains (ADR-032):** no door is affected. The text describes contracts and does not change
them. The examples use one configuration of generic capabilities and are presented as such.

### V3 record and the example data inventory (2026-11-11)

**Delivered 2026-11-11** (V3's own text, mechanism and inventory; the areas V4–V12 follow).

**Built.** The content directory `backend/app/management/reference/content/` and its merge into `app.openapi()` (`content.py`: sections by method and path, titles, parameter notes, schema fields, error lines, shared errors, the page fields, untagged operations; anything naming something that does not exist raises `ContentError`); the writer's guidance `content/README.md`; the conventions in `index.md` (identifiers and keys, contexts, versions, paging, ordering, retrying a write, optional surfaces, authentication, errors); the catalogue `errors.md` with 347 entries and a status badge (every code `raised_codes()` finds, 351, less the 6 below, plus `HTTP_ERROR` and `DATABASE_UNAVAILABLE`); the text of `workspaces` (11 operations), `system` (7), `changes` (1) and the two untagged health checks, with 21 recorded examples; the `reference` test group (the scenario on the guide's reference model and its `docs` set, `RDM_RECORD_EXAMPLES=1` to write the examples, normalised and short); the gap list `backend/tests/reference_gaps.json` with `test_reference_gaps.py`, grouped by tag, which may only shrink; the V-D8 rule in `AGENTS.md`, in step 3 of 0.9's "How a package is delivered" and in 0.11's build step, and the pointer in `DOCUMENTATION_PLAN`.

**Examples as separate files (V-D10).** The document with all 295 operations is about 1.77 MB with only these 21 operations' text, and the projection for the whole reference is about 2.3–2.6 MB, so the request and response bodies are not inline: each is an Example Object with `externalValue` (`/docs/api/examples/<operation>/request.json` or `response.json`), served by the page's route and written by `static_site` (under its base). Scalar 1.72.2 loads such a file when the example is on screen, and only against an absolute document address, so the page makes each source's address absolute in its own script. Checked in headless Chromium on the static build with every request outside the page's origin aborted: the examples show on the operation (request panel, response panel) and no request left the origin. Parameter examples and a text body (the metrics) stay inline. Under a `root_path` the example addresses did not follow the prefix; V4 made them relative to the document, so they do ([V4 record](#v4-record-2026-11-11)).

**Gap list (items, by group).** agent-access 42, ai 478, attributes 37, change-sets 509, consumer subscriptions 143, imports 139, jobs 131, mail 60, mapping 129, model 559, model administration 969, model mappings 136, moves 12, notifications 43, oauth 30, objects 204, relation-matrix 73, relations 116, security 387, source files 93, guide links 8: 4,298 in all (operations without a section or example, parameters and schema fields without a description, the guide's links to tags the document lacks). `workspaces`, `system`, `changes` and the untagged operations have none.

**Codes kept out of the catalogue** (raised in the code, never answered): `AI_ASSISTANT_ROLE_CHANGED` (caught in a background job; only its message is kept), `CHANGE_SET_SOURCE_INVALID` (the request schema refuses the same cases first), `CHILD_TYPE_NOT_ALLOWED` and `REQUIRED_RELATION_WITHOUT_PLACE` (reported inside a restructuring plan under another name), `ROUTE_NOT_DECLARED` (every route declares its action), `WRITER_UNKNOWN` (an internal guard). `INVALID_POSITION` is answered by the consumer API, so it has an entry.

**Discrepancies** (logged in TODO, "API documentation discrepancies"): the feed needs the Feed group (API.md: ungated); `WORKSPACE_ADMIN_MUTATIONS_ENABLED` is a switch, not the guard (API.md: pre-authentication posture); the `ai` setting group; three guide links to tags that do not exist (`consumer`, `clients`, `mappings`; the guide's pages are not edited here).

**Checks.** `-m "reference or contract"`: 120 passed, 1 failed (`test_every_parameter_and_header_is_listed`, another session's `hideEmptyColumns`); the OpenAPI lock re-baselined by diffing the document (only `info`, `tags`, `paths` and schema property descriptions change; it also holds the other session's uncommitted API changes, whose own pending value did not match the tree).

**What the user cannot do yet.** Read text for any other area: V4 (records) to V12 (AI, mail, notifications) each empty their group of the gap list. The guide's three links above stay broken until the guide is edited.

#### The example data (V-D2a): what each area needs, and the reference model's type that shows it

Checked in `guide/samples/model.json` and the `docs` set (598 records) on 2026-11-11. Nothing in `guide/samples/` is changed in V3 (0.13's release is pending); an area package adds what it needs after 0.13's release commit.

| Area | Capability the operations need in the data | Where the reference model shows it | Status |
| --- | --- | --- | --- |
| V4 records | Typed attributes (text, long text, integer, decimal, date, boolean) | `stop` (`stop-number`, `latitude`, `valid-from`, `active`, `description`) | shown |
| V4 | Required, unique, searchable, filterable, sortable attributes | `stop` (`designation`, `stop-number`, `sloid`) | shown |
| V4 | A containment ladder (parent candidates, paths, restructuring across types) | `canton` > `district` > `municipality` > `stop` | shown |
| V4 | A self-hierarchy | `mode-has-child` (`mode`) | shown |
| V4 | An effective period and `asOf` | `stop` (`valid-from`, `valid-to`) | shown |
| V4 | An attribute with a default | `active` (`language`, `name-translation`) | shown |
| V4 | A value range, an at-least-one-of rule, a read-only attribute | none in the model | missing |
| V4 | Translations | `name-translation` (five languages) | shown |
| V5 relations and mappings | One-to-many, many-to-one, many-to-many relations | the containment relations, `stop-operated-by-operator`, `stop-served-by-mode`, `system-code-maps-to` | shown |
| V5 | A one-to-one relation | none | missing |
| V5 | A relation with its own attributes | `stop-operated-by-operator` (`local-name`, `is-primary`, `inspected-on`) and `system-code-maps-to`; the values are in the `reference` set only | shown by the type; values missing in the `docs` set |
| V5 | Mapping coverage, grids and the relation matrix | views `stop-operators`, `codes-to-stops`, `codes-to-municipalities` | shown |
| V6 change sets | A change set with edits, a validation and a publication; a withdrawal | made by the scenario on the `docs` set | by the scenario |
| V6 | A second person for second-person approval | the harness has one person | made by the scenario through the API |
| V7 jobs, imports, files | Batches, exports | loading the set is a batch | shown |
| V7 | An import workbook and its profile | `guide/samples/Haltestellen_Busbetrieb_Nord.xlsx`, not loaded | shown (file) |
| V8 model | A second release of the same model (activation, diff, compatibility, migration) | one release only | missing |
| V8 | A second model (model mappings, moves between workspaces on different models) | one model only | missing |
| V9 webhooks | A consumer API and a receiver | the `stops` consumer API; no receiver | API shown; receiver missing |
| V11 security | People, groups, roles, grants, clients | made by the scenario | by the scenario |
| V12 AI, mail, notifications | A provider, a mail server, a second person to notify | none in the data | missing (scenario settings, decided in V12) |

### V4 record (2026-11-11)

**Delivered 2026-11-11: `objects` and `attributes` (13 operations): create, read, update and move, delete (with the cascade preview), the per-type list, the cross-type lookup, the model-aware query, parent candidates and history, and the four attribute-value operations.** Text in `backend/app/management/reference/content/objects.md` and `attributes.md`, written to the shape in `content/README.md`: each operation has its title, a section of 29 to 70 words, its parameter notes (including the ones with placeholders, `filter.<field>.<operator>`, for which the merge's note syntax now accepts `<`, `>` and `:`) and error lines read from the code paths (live and change set, which word several refusals differently); the two overviews are 120 and 98 words. 28 schemas have every field described: the create, update and initial-relation bodies, the record and its path, the lookup and query items, parent candidates, the query body and its criteria, expansions, the history entry with its cause, values, related record and origins (AI proposal, assistant), and the attribute value and its write. Each operation has one recorded example on the `reference-docs` seed (13 files, `tests/test_reference_records.py`: a stop is added under a municipality, completed value by value, corrected, moved, read back in the history, found by a query and deleted; the refusals the text names are asserted, not recorded).

**Two fixes from V3.** The example files did not load under a non-empty `root_path`: their addresses are now relative to the document (`docs/api/examples/...`), so they resolve with the prefix; the static build still replaces them with its own absolute ones; a unit test checks the resolution and that the files answer under `/rdm`. The guide's links: `#tag/clients` is `#tag/security` and `#tag/mappings` is `#tag/mapping`; the five `#tag/consumer` links lost their anchor, because the consumer API index `GET /api/consumer` is not in the management document, so no management tag holds it (which page should describe it is open, TODO).

**Gap list (items):** `objects` 204 to 0 (9 operations without section and example, 38 parameters, 148 schema fields), `attributes` 37 to 0, `guide` 8 to 0; 10 schema fields of `change-sets` that these operations reach (`AttributeOutput`, `ObjectPathPart`, `AttributeInput`) went with them; 4,298 to 4,039 in all.

**Discrepancies** (TODO, "API documentation discrepancies"): the application and type refusals of `POST /objects` (live: `INVALID_OBJECT_TYPE_FOR_APPLICATION`; `OBJECT_TYPE_NOT_IN_APPLICATION` is a change set's); the at-least-one-of rule is left to a change set's validation on update and attribute writes; a stale version with `cascade` answers `DELETION_PREVIEW_CHANGED`; the change-set attribute writes return an empty `path`; `parent-candidates` takes `publicationId`.

**Size.** The management document is 1.75 MB compact (3.1 MB as the indented file the static build writes) with 295 operations and V3's and V4's text; the 38 example body files are 35 KB. The examples stay out of the document, as V-D10 decided.

**Checks.** The content unit tests, `-m "reference or contract"` and the OpenAPI lock, re-baselined on the tree as it stands (it holds the other sessions' uncommitted API changes); see the changelog entry.

**What the user cannot do yet.** Read text for the other areas: V5 (relations, mapping, relation matrix) to V12 each empty their group of the gap list, and `moves` has no section yet (its 1 operation and 10 schema fields are in the gap list). The consumer API index has no management-document page.

### V5 record (2026-11-11)

**Delivered 2026-11-11: `relations`, `mapping` and `relation-matrix` (18 operations).** Text in `backend/app/management/reference/content/relations.md`, `mapping.md` and `relation-matrix.md`, written to the shape in `content/README.md`: each operation has its title, a section of 39 to 66 words, its parameter notes and error lines read from the code paths (live and change set, which word several refusals differently); the three overviews are 125, 117 and 113 words. `relations` holds the eight operations of `/relations` (add, list a record's, held, read, change values, remove, batch, grid change); `mapping` holds the five mapping operations (coverage, candidates, targets, replacement, AI proposals) and the two that carry both tags, the workspace edge list and the relationships grid, because an operation with several tags is written in the file of its first tag (the rule is in `content/README.md`, and the unit test that every operation of an area has its section now reads it); `relation-matrix` holds the matrix and its two cell reads. 41 schemas have every field described (197 fields): the relationship create, update and response, the batch and the grid change with their parts, the page and its relationship sets, held records, the edge list row and page, the grid (rows, columns, relationships), the mapping rows, targets, replacement and proposal, and the matrix with its cells, containers, derived place and link candidates. The catalogue gained `RELATION_BATCH_REFUSED`, which the gap check's code extraction does not find (its status is a conditional expression, `409 if stale else 422`) and which V3's catalogue therefore lacked; the other codes the 18 operations list were all there. Each operation has one recorded example on the `reference-docs` seed (18 files, `tests/test_reference_relations.py`: Davos stops get a bus, the operator's inspection values are set one by one, in a batch and across the grid, a code is cleared and mapped again with its confirmation, the AI proposal is requested into a new change set, and the two matrices are read; the refusals the text names are asserted, not recorded). The relationship attribute values are not in the `docs` set, so the scenario sets them through the API (`guide/samples` is unchanged). The proposal example needs the deterministic provider (`AI_PROVIDER=app.engine.proposals.fake:provider`), set in the scenario's environment only. No one-to-one relation is in the data; the overview and the `cardinality` wording say what it does (each end holds one) and nothing records it.

**Mechanism changes.** The recording's call takes a list as a repeated query parameter (`objectId` of the held read); the normaliser also normalises a key that is an ID (the grid keys a row's relationships by column record). Both live in `tests/test_reference_recording.py`, so the `reference-docs` seed was rebuilt once (10 s).

**Check first (V4's prefix).** In headless Chromium with route interception and no server, the instance page served under `/rdm` and the static build both fetch an operation's request and response example files and show them (`GET` and `PATCH /api/v1/workspaces/{workspace_key}`): `/rdm/docs/api/examples/…` and `/docs/api/examples/…`; nothing else left the page's origin. No fix was needed.

**Gap list (items):** `relations` 116 to 0, `mapping` 129 to 0, `relation-matrix` 73 to 0; 4,039 to 3,721 in all.

**Discrepancies** (TODO, "API documentation discrepancies"): one: the workspace edge list takes `seek`, which API.md says it does not.

**Size.** The management document is 1.92 MB compact (3.29 MB indented, as the static build writes it) with 295 operations and V3 to V5's text; the 61 example body files are 57 KB. The examples stay out of the document, as V-D10 decided.

**Checks.** The content unit tests (35 in `tests/unit/management/reference`), `-m "reference or contract"` (128) and the OpenAPI lock, re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes); see the changelog entry. The relation matrix routes, projections and schemas are unchanged from HEAD (other sessions' changes there are in tests only), so the matrix was documented from the tree and HEAD alike.

**What the user cannot do yet.** Read text for the areas after V5: V6 (change sets and publications) to V12 each empty their group of the gap list, and `moves` has no section yet. No example shows a one-to-one relation, an error, or a change set context of these operations.

### V6 record (2026-11-11)

**Delivered 2026-11-11: `change-sets` (23 operations).** Text in `backend/app/management/reference/content/change-sets.md`, written to the shape in `content/README.md`: each operation has its title, a section of 16 to 65 words, its parameter notes and error lines read from the code paths (the permission check, the version claim, the publication merge, the approval code, the planner and the migration start); the overview is 116 words and says the merge onto live data, conflicts, approval and the publication snapshot. 80 schemas have every field described (424 fields): the change set, its create, update, release and migration bodies, the publication, the object and relation changes, the submission, decision and policy, the restructuring request, plan and result with their parts, and, because the migration job answers with them, the job, its counts and preview, the export, binding report, migration, move and AI proposal summaries (the jobs, imports and moves areas reuse these lines). The catalogue's `VERSION_CONFLICT` entry now says what a publication's conflicts carry; no code was missing (the codes raised with a conditional status that V5 met are not on these paths). Each operation has one recorded example on the `reference-docs` seed (23 files, `tests/test_reference_change_sets.py`): a change set from live data gets a new stop, a corrected name and a stop moved by a planned and applied restructuring, is reviewed, checked and published; the workspace's policy then requires an approval by a second person, made through the API (a person, its password link, a grant of Data owner in the workspace; `guide/samples` is unchanged); a change is submitted, sent back, resubmitted, withdrawn, submitted and approved; the publication is withdrawn; one change set is discarded; a second release of the model is installed and activated, one change set moved onto it and another's migration queued (its preview left to finish). The refusals the text names are asserted, not recorded.

**Corrected from V4 and V5.** Their error lines listed `UNSUPPORTED_PINNED_MODEL_SCHEMA` and `PINNED_MODEL_INVALID` as 422; the engine answers 409 (`engine/model/registry.py`) and the catalogue says 409; the lines now say 409.

**Gap list (items):** `change-sets` 499 to 0 (23 operations without section and example, 29 parameters, 424 schema fields); 3,721 to 3,222 in all.

**Discrepancies** (TODO, "API documentation discrepancies"): one: API.md names `sourcePublicationId` where the field is `derivedFromPublicationId`, and the code `CHANGE_SET_SOURCE_INVALID` is never answered. Also logged: an instance with `INTEGRATION_JOBS_ENABLED` or `WORKSPACE_ADMIN_MUTATIONS_ENABLED` off cannot build its OpenAPI document, because a section names an operation the document then lacks (V3's mechanism; a decision for V9).

**Size.** The management document is 1.99 MB compact (3.38 MB indented, as the static build writes it) with 295 operations and V3 to V6's text; the 75 example body files are 320 KB. The examples stay out of the document.

**Checks.** The content unit tests (35), `-m "reference or contract"` (129) and the OpenAPI lock, re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes); see the changelog entry.

**What the user cannot do yet.** Read text for the areas after V6: V7 to V12 each empty their group of the gap list, and `moves` has no section yet. No example shows an error, a change set started from a publication or empty, or a change set submitted by a client.

### V7 record (2026-11-11)

**Defect found in V6 and fixed first: the document built only with every optional surface on.** `merge_content` raised `ContentError` for a section naming an operation the document lacked, so an instance with `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false` or `INTEGRATION_JOBS_ENABLED=false` could not build `/openapi.json` and `/docs/api` broke. Now `merge_content(..., strict=False)` is what the application runs (`install`): text for a route, tag, schema, field or parameter the document lacks, and an example for a missing route, is skipped silently; a code with no catalogue entry still raises. The tests keep the strict check: `static_site._management_document(strict=True)` (the all-capabilities document, merged strictly) runs in the gap test and in a unit test, and a parametrised unit test builds the document with each of `INTEGRATION_JOBS_ENABLED`, `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED` and `CONSUMER_SUBSCRIPTIONS_ENABLED` off in turn, and all off, and checks each build succeeds and drops operations.

**Delivered 2026-11-11: `jobs` (with `exports`), `imports` and `source files` (30 operations; the plan's table said 29).** Text in `content/jobs.md` (11), `content/imports.md` (12) and `content/source-files.md` (7), to the shape in `content/README.md`: a title, a section of 19 to 70 words and parameter notes for each operation, and error lines read from the code paths (the permission and context checks, the limits, the idempotency key, the job store, the profile checks, the source file store). Overviews of 115, 100 and 102 words. The schemas have every field described: the batch request, its ten item kinds and their parts, the item outcomes, the import profile in full (sources, keys, bindings, matches, value maps), the import request, the check and its findings, the dry run figures, the source file, its sheets, blocks, columns and cells, the export request and the move and migration rows the jobs routes answer with. Because these operations reach them, the lines also cover schemas the gap list had under `model administration` (230 items), `oauth` (4) and `security` (3).

**Examples (30 files, `tests/test_reference_jobs.py`, `reference` group, on the `reference-docs` seed).** A batch of three item kinds with an `Idempotency-Key` (its replay and the refused reuse asserted); an export of the new stops, its event stream and its file; a background batch, its job and outcomes; a preview that is cancelled; the profile for `guide/samples/Haltestellen_Busbetrieb_Nord.xlsx` (header row 3, value maps for its date words and for the municipality's other-language names), the stored workbook and its sheets, columns and cells; the import previewed (6 Felsberg rows refused, the municipality is not in the data), its rejected rows, its confirmation (45 stops created); a changed copy of the workbook made in the test (a renamed column, a renamed stop, a stop left out), stored and checked (check, new values, renamed records, left-out records, rows); the profile replaced, a spare one deleted, the superseded file deleted; and a small CSV made in the test, previewed with a relationship column and read again by mode code. A multipart request has no JSON body in the document, so its example names the `request` part and the file in its notes (`Scenario.call` and `write_examples` take `notes`, `call` takes `headers`). Every job was followed to its end; the waiting previews were cancelled. The refusals the text names are asserted, not recorded (an unknown workspace, draft, profile, file, change set, parent or publication; an invalid context; a stale version; an unsupported format; an invalid export layout and query).

**Catalogue.** 29 new entries (347 to 376): `IMPORT_PROFILE_MODEL_MISMATCH` (422, answered by three routes, not found by the raised-code extraction because the code is a constant); the 15 problem codes of an import profile (`ATTRIBUTE_NOT_BOUND`, `ATTRIBUTE_READ_ONLY`, `CREATE_NEEDS_NAME_MATCH`, `FLAG_WITHOUT_TARGET`, `KEY_NOT_BOUND`, `KEY_NOT_UNIQUE`, `PARENT_BOUND_TWICE`, `PARENT_NOT_ALLOWED`, `RELATION_NOT_ALLOWED`, `SKIP_NEEDS_KEY`, `SOURCE_CYCLE`, `TYPE_NOT_IN_APPLICATION`, `UNKNOWN_ATTRIBUTE`, `UNKNOWN_VALUE_MAP`); the file mismatch and row codes (`SHEET_NOT_FOUND`, `HEADER_ROW_NOT_FOUND`, `COLUMN_NOT_FOUND`, `NOT_A_TABLE_LAYOUT`, `INVALID_CELL`, `INVALID_NAME`, `NAME_REQUIRED`); the item reasons (`BATCH_ROLLED_BACK`, `JOB_CANCELLED`, `JOB_FAILED`); and the two notices (`RECORD_IDS_OF_ANOTHER_WORKSPACE`, `RECORD_IDS_AS_COUNTERPARTS`). Those that are not response statuses are badged so; V9's every-entry-is-listed check has to treat them as it treats `CONSUMER_API_REMOVED`.

**Gap list (items):** `jobs` 131 to 0, `imports` 139 to 0, `source files` 93 to 0; `model administration` 969 to 739, `oauth` 30 to 26, `security` 387 to 384 (their shared schemas); 3,222 to 2,622 in all.

**Discrepancies** (TODO, "API documentation discrepancies"): two. API.md says an export job's `parameters` hold the request's `context`, `scope`, `include` and `format`; the code stores the whole request (also `view`, `layout`, `people`, and a criterion's `not` as `not_`). And `POST /imports` with `sourceFileId` reads the stored file without the access check the source file routes make. The V6 entry about the optional surfaces is marked fixed.

**Size.** The management document is 2.09 MB compact (3.51 MB indented, as the static build writes it) with 295 operations and V3 to V7's text; the 122 example body files are 127 KB indented. The examples stay out of the document.

**Checks.** The content unit tests (43), `-m "reference or contract"` and the OpenAPI lock, re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes); see the changelog entry.

**What the user cannot do yet.** Read text for the areas after V7: V8 to V12 each empty their group of the gap list, and `moves` has no section yet. No example shows an error, a batch into a change set, an import into a change set or the export of a view, a publication or a workbook for people; the move and migration rows are described but shown by V8.

### V8 record (2026-11-11)

**Defect found in V7 and fixed first: `POST /imports` with `sourceFileId` skipped the source file access check.** A caller with Bulk and import in one workspace could import another workspace's profile file or an assistant task's workbook by naming its ID. The rule of `_usable` (a task's workbook is `404 SOURCE_FILE_NOT_FOUND`; a profile's file is usable by its uploader and by holders of Bulk and import in its workspace, else `403 FORBIDDEN`) is now `management/source_file_access.py` `usable_source_file`, called by the source file routes and by `create_import`. Journey test `test_an_import_uses_only_the_source_files_the_caller_may_use` (`test_j40_authorization.py`): a person with Bulk and import in A gets 403 for B's profile file and 404 for a task's workbook, no job is stored, and the uploader's import is accepted. `imports.md`'s error lines and the TODO entry are updated. Checks: `-m "jobs or authoring"` and J40 pass; the only failures were two statement budgets of live creates in `test_batch_statements.py` (38 against 39 and 51 against 53 statements), a path the fix does not touch and that the other sessions' uncommitted record-write changes reach.

**Delivered 2026-11-11: `model` (21 operations), `model administration` (30), `model mappings` (12) and `moves` (1).** Text in `content/model.md`, `model-administration.md`, `model-mappings.md` and `moves.md` to the shape in `content/README.md`; overviews of 124, 94, 128 and 108 words; every schema field, parameter and error line written, the model's concepts in the schema fields. The gap list for these four groups went from 559, 739, 136 and 12 items (1,446) to 0; 2,622 to 1,176 in all (the `ai` group still holds the `Items*` fields the dry run of items answers with).

**The operation kinds (V10).** The plan's figures were stale: the document already held 66 draft kind schemas (0.13 AQ), untyped; the 12 mapping kinds were free-form. Now both registries are described in `schemas/model_operation_parameters.py` and `schemas/mapping_operation_parameters.py` (type, required, one line each; 275 and 32 parameters), the schemas are generated from them (`model_operations.py`, `model_mapping_operations.py`, `operation_description.py`), `ModelMappingOperationsRequest` (now in `schemas/mappings.py`) takes the union of the 12 mapping kinds, and `mapping_kinds.py` declares its parameters once. A parameter needed only under a condition says so in its line; nested shapes are described where the code checks nested names. The schemas describe; the kinds keep checking (V-D11). `tests/unit/management/schemas/test_model_operations.py` holds both registries and their schemas in agreement, and that an operation without parameters is refused at a parameter the table calls needed.

**Examples (64 files, `test_reference_model.py` and `test_reference_mappings.py`, `reference` group, on the `reference-docs` seed).** A model read in full; a draft with a step, undo and redo, its source file (a workbook of vehicles made in the test), inference, proposals and dry run; compile and install as a second release, its diff, the activation and a workspace migration to a third release, previewed and confirmed; a second model saved from a document with a workspace running it; a mapping between the two models with its operations, inference and undo; and a move of four stops between the two workspaces. The one step not made through the API is the raising example, which stages an old-schema release in the clone's database as the J37.9 journey does.

**Catalogue.** No new entries; every code the text cites had one. Two entries were extended (`VERSION_CONFLICT`, `HTTP_ERROR`: the draft's conflict details and the 405 of switched-off model administration; `AI_TASK_STATE`).

**Discrepancies** (TODO, "API documentation discrepancies"): the model release routes `PATCH`, `DELETE` and `raising` are not guarded by `MODEL_ADMIN_MUTATIONS_ENABLED`; `POST /moves` takes `mode` and `stage`; the mapping history omits `removed` and `migration`; `classification: invalid` is never produced; the plan's kind counts. The V7 entry about `POST /imports` is marked fixed.

**Size.** The management document is 2.33 MB compact (3.17 MB indented) with 295 operations and V3 to V8's text; the 169 example files are 430 KB. The examples stay out of the document.

**Checks.** The content unit tests, `tests/unit/management` and `tests/unit/engine/moves`, `-m "reference or contract"` (149) and the groups `mapping`, `authoring` and `workspace_models`; the OpenAPI lock re-baselined on the tree as it stands; see the changelog.

**What the user cannot do yet.** Read text for the areas after V8: V9 to V12 each empty their group of the gap list. No example shows an error or a move into a change set.

### V11 record (2026-11-11)

**Delivered 2026-11-11: `security` (65 operations), `oauth` (7) and `agent-access` (7).** Text in `backend/app/management/reference/content/security.md`, `oauth.md` and `agent-access.md`, written to the shape in `content/README.md`: each operation has its title, a section of 11 to 64 words, its parameter notes and error lines read from the code paths (the permission check, the version claim, the last-administrator guard, the managed sign-in, the proofs and the slowing of wrong codes, the scope rules of a grant, the provider checks); the overviews are 129, 112 and 123 words and say who may do what (roles of action groups, granted to people, groups and clients at the instance or in a workspace, narrowed to applications and record types) and how a client signs in. 70, 2 and 5 schemas have every field described (340 fields), including the schemas a person's own `/me` reads, the grants, the providers and the agent calls. The `oauth` endpoints answer in OAuth's own form, whose codes are not catalogue codes, so their text names the refusals in the section and lists no error lines.

**Examples (79 files, `tests/test_reference_security.py`, `reference` group, on the `reference-docs` seed, 5 tests).** An administrator gives a timetable team access: a custom role, two people (each sets a password through the link the administrator passes on), a group with its members added one, by batch (a dry run asserted, not recorded) and removed, and the grants that let the group edit stops of the network application in the Graubünden workspace. One person looks after their own sign-in: sessions (one ended, then all), a password change, an authenticator app (set up, confirmed, new recovery codes, removed by the person and again by an administrator) and passkeys (listed, renamed, removed by the person and by an administrator). A client for a nightly export gets a secret, rotates it with an overlap, stops the old one and signs in. The token signing key is rotated and the security events read. The harness's OpenID Connect provider (`tests/oidc_provider.py`) is connected, a person signs in through it and is linked to the person who had an account, then unlinked; local sign-in is read and a second factor required and not. An agent client is made, granted a role, signs in with `scope=agent`, calls `list_workspaces` through `/mcp` and the call is listed; an assistant registers itself and an administrator registers, blocks and restores another; the discovery endpoints are read. Passkey registration and a provider sign-in need a browser: they run as the browser makes them, with `tests/software_authenticator.py` (the engine's own page, which is not an operation of the document) and the provider's pages in the same process; what is recorded are the operations that list, rename and remove passkeys, and the link. The token and revocation endpoints take forms, so their examples name the form in the notes and record the answer.

**Secrets.** No real secret is in an example. The normaliser replaces by key, wherever they appear: `password`, `currentPassword`, `newPassword`, `clientSecret`, `client_secret`, `access_token`, `refresh_token`, `otpauthUri`, `qrSvg` and a secret's `hint` (`SECRET_MASKS` in `test_reference_recording.py`), and a reset link's token in a text; a call masks the keys that are secrets only in its answer (`secret`, `code`, `recoveryCodes`, a proof, the public key values). They read `example-client-secret`, `example-access-token`, `example-reset-token`, `JBSWY3DPEHPK3PXP` for an authenticator's seed and `abcd-efgh-0001` for recovery codes. The harness provider is given the placeholder secret itself and its loopback address becomes `https://id.example.org`. A search of the 79 files for tokens (`eyJ`), private-key headers and any 28-character run that is not an ID, an address or a placeholder finds nothing; the request IDs of the agent calls are masked too.

**Checked and corrected: V8's inferred lines.** Run on a clone with `MODEL_ADMIN_MUTATIONS_ENABLED`, `INTEGRATION_JOBS_ENABLED` and `WORKSPACE_ADMIN_MUTATIONS_ENABLED` off, as the administrator: the model mappings' lines were right (405 for `POST /model-mappings`, `DELETE /model-mappings/{key}`, `POST .../operations` and `POST .../inference`, which share an address with a read; 404 for `undo`, `redo` and `inference/application`), and so were `workspaces.md`'s (405). The model administration lines were wrong: every one of its 22 operations answers `404 HTTP_ERROR`, not 405, because none shares an address with an operation that is still registered. `model-administration.md` and the catalogue's `HTTP_ERROR` entry now say so.

**Catalogue.** No new entries: every code the 79 operations list was there. The `HTTP_ERROR` entry was corrected (above).

**Gap list (items):** `security` 384 to 0, `oauth` 26 to 0, `agent-access` 42 to 0 (79 operations without section and example, 73 parameters, 221 schema fields); 1,176 to 724 in all (`ai` 478, `consumer subscriptions` 143, `mail` 60, `notifications` 43).

**Discrepancies** (TODO, "API documentation discrepancies"): one: API.md says restoring an assistant "answers the application as the list does", and `block` and `restore` always answer `signedIn: 0`. No security or data defect was found in the paths read: every operation of the three areas declares its action (the contract test), the secrets the answers hold are shown once and never again, a password link's token and the arguments of agent calls are not in the log or the events, and the routes the caller reaches for their own credentials all refuse a managed sign-in. Also logged: 202 of the document's 800 schemas carry package or decision IDs in their own description (docstrings of the schemas), which the content directory cannot override; V9's close-out decides.

**Size.** The management document is 2.42 MB compact (3.97 MB indented) with 295 operations and V3 to V8 and V11's text; the 248 example files hold 296 request and response bodies of about 346 KB. The examples stay out of the document.

**Checks.** The content unit tests (43), `-m "reference or contract"` and the OpenAPI lock, re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes); see the changelog entry.

**What the user cannot do yet.** Read text for the areas after V11: V12 (`ai`, `mail`, `notifications`) and V9 (`consumer subscriptions`, then the close-out) each empty their group of the gap list. No example shows an error, a person who signs in with a passkey, a sign-in through a provider that fails or a grant of a consumer API (the scenario makes one and asserts it).

### V12 record (2026-11-11)

**Delivered 2026-11-11: `ai` (20 operations), `mail` (8) and `notifications` (8).** Text in `backend/app/management/reference/content/ai.md`, `mail.md` and `notifications.md`, to the shape in `content/README.md`: each operation has its title, a section of 18 to 76 words, parameter notes and error lines read from the code paths (the action groups, the send-level and provider checks, the task state and version claims, the mail settings' refusals, the outbox states, the notice-mail choices). The `ai` overview (130 words) states what a provider is sent at each send level; `mail` is 104 words and `notifications` 72. 86 schemas have every field described (486 fields), among them the dry run of items' `Items*` schemas that V8 left and the assistant task's reading, check and design.

**Examples (36 files, `tests/test_reference_ai.py` and `tests/test_reference_mail.py`, `reference` group, on the `reference-docs` seed, 6 tests).** The provider is the harness's fake (`app.engine.proposals.fake`), with `AI_LOG_CONTENT` on so the calls show what was sent; no real provider is called, no key is set and `.dev/settings.env` is not read. The administrator reads the status, tests the provider, asks a question on the stops list, reads accounts of the workspace and of one stop, and of a model draft and the release installed from it, then the calls. Mail runs against `tests/smtp_server.py` (STARTTLS with a login): settings saved, a test message, a welcome link mailed, the outbox, one message stopped, the person's own notice mail with a digest. A second person follows the workspace, the administrator publishes two change sets and the person reads, marks and removes the notices and opens the stream's first event.
**Which answers are real and which a stand-in.** Assistant tasks run Claude Code in service. Here a stand-in session (a script the harness writes, as the journeys' stand-ins are) works through the API with the token the engine gives it, over a local HTTP port the test starts and stops: its answers to a words task (create, answers, tell, accept to a loaded change set, a failure and its retry, a stopped turn, discard) are the engine's own, and the examples say so in their notes. A workbook task is read by a saved layout (an import profile), so no session runs there: create, read, accept, the check's changes, back to the proposal and the load into a change set. What needs a session that designs against a workbook (the reading of an unknown layout, the assistant's questions about a workbook, the check of its draft) is described in the text and not recorded. The stream records its first event: the next events follow new notices and need a client that stays.

**Secrets.** No secret is in an example. The mail password is replaced by `example-password` (`SECRET_MASKS`) and the harness server's address and port by an invented host (a call's `mask`); no provider key exists. A search of the 36 files for tokens (`eyJ`), private-key headers, `Bearer`, local paths, loopback addresses and any 28-character run that is not an ID, an address or a pointer finds nothing but the invented user name.

**Catalogue.** No new entries: every code the 36 operations list was there.

**Gap list (items):** `ai` 478 to 0, `mail` 60 to 0, `notifications` 43 to 0 (36 operations without section and example, 28 parameters, 486 schema fields); 724 to 143 in all (only `consumer subscriptions` is left).

**Discrepancies** (TODO, "API documentation discrepancies"): five, the first for the user: OPERATIONS.md says a question in words sends no record name, while the code sends the names of a short list's records at `samples` and `values` (as its own settings table and API.md say). Also logged: API.md's list of a call's purposes, two in-code descriptions of a mail message's kinds, a check shape (`TaskCheck` and its parts) that no code produces, and `design.outline`'s `name`. No security or data defect was found in the paths read: a lower send level sends no record or person name (asserted on what the fake was sent for a question and an account), the key is never answered, a mail password and the outbox text are never answered, a task is visible only to its requester and the administrators of its workspace.

**Size.** The management document is 2.49 MB compact (4.07 MB indented) with 295 operations and V3 to V8, V11 and V12's text; the 284 example files hold about 0.4 MB of bodies. The examples stay out of the document.

**Checks.** The content unit tests (43), `-m "reference or contract"` (160, 3 min 4 s) and the OpenAPI lock, re-baselined on the tree as it stands; see the changelog entry.

**What the user cannot do yet.** Read text for `consumer subscriptions`: V9 empties the last group of the gap list and closes the track. No example shows an error, a workbook task designed by a session or the stream's later events.

### VD record (2026-11-11)

**The 20 discrepancies of Track V resolved** (TODO, "API documentation discrepancies", each entry closed with "Done in VD"): `docs/API.md` corrected for 11, the code fixed for 9, as the user decided.

**API.md (the code is right).** The feed needs `feed.read`; `WORKSPACE_ADMIN_MUTATIONS_ENABLED` switches the operations and `workspaces.manage` guards who uses them; `GET /system/configuration` has the group `ai`; `POST /objects` lists the live and the change set's answers apart; the at-least-one-of rule (a change set's update and attribute `POST`/`PATCH` leave it to validation, its create and attribute `DELETE` check at once); a stale version on a cascading delete is `409 DELETION_PREVIEW_CHANGED`; the workspace edge list's `seek`; `CHANGE_SET_SOURCE_INVALID` removed from the list (checked: every caller of `create_change_set` passes a valid `source`, and the request schema refuses the rest, so it can never be answered); model release `PATCH`, `DELETE` and `…/raising` always registered and guarded by `model.install`; the eight AI call purposes; `design.outline`'s `name`.

**Code (contract changes, in the CHANGELOG).**
1. Attribute `POST`/`PATCH` in a change set answer the record's `path` (`management/routers/attributes.py` `_write`, with `object_path`).
2. `GET /objects/{type}/{id}/parent-candidates` takes no `publicationId`: a new dependency `workspace_model_snapshot` (`management/dependencies.py`) and a new `Where`, `RECORD_READ_NO_PUBLICATION` (`management/access.py`), since the access check read the parameter too; sending it is `422 UNKNOWN_PARAMETER`.
3. `POST /moves`: the router's description states `mode` and `stage`.
4. `ModelMappingOperationEntry` has `removed` and `migration`.
5. `ModelCompatibilityResponse.classification` is `compatible` or `migration_required`. The TODO entry's premise ("no code produces `invalid`") was wrong for one answer: `compile` of a draft that does not compile answers `invalid` (`model_management.py`), so `CandidateCompatibilityResponse` keeps it (documented on its `classification`); the frontend type is unchanged. Found when `test_model_lifecycle` failed on the narrowed schema.
6. An export job's `parameters` are `model_dump(by_alias=True, exclude_unset=True)` of the request, without `workspaceKey` (`engine/jobs/exports.py`). Readers checked: the export worker validates the stored parameters into `ExportRequest`, whose criteria accept both `not` and `not_` (`populate_by_name`), so a job stored before still runs (journey in `test_j27_export.py` rewrites a stored job to `not_` and runs it); the frontend's job page and the tests read no export parameter but `layout`, which the request still holds when sent.
7. `block` and `restore` answer `signedIn` through the list's count (`management/routers/agent_access.py` `_counted`).
8. `MailMessageResponse.kind` and `lastErrorKind` name `digest` and `stopped`.
9. `TaskCheck`, `CheckTable`, `CheckFix`, `CheckSummary` and `RefusedGroup` removed; `AiTaskResponse.check` is `DesignCheck`; the frontend's `AiTaskCheck*`, `AiTaskFix` and `AiTaskRefusal` types and `isDesignCheck` removed with it (`src/types/aiTasks.ts`, `src/features/ai-tasks/`).

**Tests.** `test_attributes.py` (the path of a change set's attribute write), `test_parent_candidates.py` (`publicationId` refused), `test_j27_export.py` (the stored parameters and a job stored with `not_`), `test_j51_agent_access.py` (`signedIn` of `restore` and `block`). Reference text and examples re-recorded where a response changed.

### V9 record and the closing record of Track V (2026-11-11)

**Defect first.** No security or data defect was found in the paths read: every operation of the area declares its action (the contract test), the signing key is answered by create and rotate only (the read and the list do not hold it) and is stored sealed, a resend is signed with every key in play, and a deleted subscription takes its delivery log with it.

**Webhooks (11 operations of `consumer subscriptions`).** Text in `backend/app/management/reference/content/consumer-subscriptions.md`, to the shape in `content/README.md`: create, list, read, edit, suspend, resume, rotate the signing key, delete, list the deliveries, read one delivery and resend an event. The overview (about 120 words) names the sequence (subscribe, verify, follow, resume) and says that requests go in event order, one at a time, with at-least-once delivery; the numbers sit where a reader looks for them: the signing recipe in `SubscriptionResponse.signingSecret`, batching in `ConsumerSubscriptionCreate.maxEventsPerBatch`, the retry schedule and the 24 hours in `PendingDelivery`, the suspension reasons and their `details` in `SubscriptionSuspension.reason`, the request statuses in `DeliveryRow.status`. 22 schemas have their description and every field described. Each operation has a title, a section, parameter notes and error lines read from the code paths (the create checks, the claim of the version, the suspended-state refusals, the log and the resend refusals).

**Example (`tests/test_reference_webhooks.py`, `reference` group, on the `reference-docs` seed, 1 test, 11 example files).** The test starts a receiver on `localhost` (the standard library's HTTP server in a thread) and stops it. A subscription to the stops of one municipality is created; a change set adds two stops and renames one and is published; the engine's event deriver and dispatcher run in the test's thread with a clock the test moves forward. The receiver answers `503` to the first attempt, so the examples show the request being retried (the `pending` block and the second attempt) and then delivered. The test asserts what the receiver got: one request with the three events, the same delivery ID on both attempts, a signature that verifies with the key the create answered, and, after a rotation, a resend signed with both keys and carrying `RDM-Redelivery: manual`. The refusals the text names are asserted without being recorded. The signing key is replaced by `rdmwh_example-signing-secret` (`SECRET_MASKS`) and the receiver's address by an invented host (a call's `mask`); a search of the 11 files and of all 295 for `rdmwh_` finds only the placeholder, and the new `test_no_recorded_example_holds_a_secret` holds it.

**Close-out.**
1. **Codes.** The extraction is widened in the completeness test (`reference_codes()`): the journeys' extraction plus an error call with a conditional status (`409 if stale else 422`) and a conditional pick of two codes. It finds one conditional status (`RELATION_BATCH_REFUSED`, catalogued in V5) and, by the conditional pick, `APPLICATION_IN_USE` and `APPLICATION_OBJECT_TYPE_IN_USE`, which are now catalogued (a migration's loss codes and compatibility diagnostics, badged "Not a response status"); the others the pick finds were catalogued. No code is unreachable beyond V3's six. The same family of codes reached an integrator through helpers and SQL that no extraction read; the follow-up below catalogues them.
2. **The V-D5 check over the whole document** (`test_every_catalogue_entry_is_listed_on_an_operation_and_every_listed_code_has_an_entry`): every code an operation lists has an entry; every entry is listed on an operation, is badged "Not a response status" (69 entries), or is named in the test with the reason it is answered elsewhere (22: the 17 codes of the consumer read API, 4 of the assistant tools and the passkey page's `TOO_MANY_PASSKEYS`; an exemption may not outlive the code being documented). It found what was wrong: ten entries that say they are an item's, a job's or a plan's code and not a response status carried a status badge and now say so (`IMPORT_FILE_MISMATCH`, `IMPORT_TOO_MANY_ITEMS`, `COUNTERPARTS_ACROSS_MODELS`, `MIGRATION_FAILED`, `INVALID_RECORD_KEY`, `MISSING_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `REFERENCE_TYPE_MISMATCH`, `VERSION_REQUIRED`, `RELATION_ALREADY_EXISTS`); `AI_TASK_DRAFT_HELD` is listed on `POST /api/v1/model-drafts/{draft_id}/operations`; and the `UNKNOWN_PARAMETER` and `UNKNOWN_OBJECT_TYPE` entries say where a subscription's filter answers them (`400`).
3. **Schema descriptions (V-D1's rule).** `content.py` reads a line of plain text under a schema's `### Schema` heading as the schema's own description, replacing the code's (two descriptions for one schema, or one for a schema the document lacks, fail). It is written for all 254 schemas whose in-code description carried a package, decision or release number (the V11 count of 202 had grown with later work), 33 field descriptions that did and two parameter descriptions; no code was edited. `test_no_description_carries_a_package_or_decision_id` scans every description and summary of the document (an operation's, a parameter's, a schema's, a field's, a response's, the tags' and the conventions') for a release number, a schema version, a decision, an ADR, a package ID, a document name or a section sign (code spans left out) and has its own test of what the pattern finds. It also found seven schemas whose description named the builders' documents or a schema version (`Schema 0.7:`, `CONSUMER_API`), now rewritten.
4. **The gap list is deleted** (`reference_gaps.json`, `test_reference_gaps.py`); `tests/test_reference_complete.py` holds the plain completeness test (V-D6): every operation has its section and example; no parameter or schema field is undescribed; no unknown name (the strict build); no description with an ID; every raised code has an entry; the V-D5 check; every guide link to a tag or an operation names one the document has; no example holds a secret. AGENTS.md, the writer's guidance and the execution guide name it.
5. **Pointers.** `docs/API.md` starts with the pointer to `/docs/api`; `DOCUMENTATION_PLAN` marks the audit of the OpenAPI descriptions done.
6. **The public build** (`static_site ../guide/dist`) was rebuilt and looked at in headless Chromium with every request outside the origin aborted (0 aborted, 0 missing files, no page error), in light and dark: the Introduction, `workspaces`, `change-sets` and `security`, the operation `POST /api/v1/consumer-subscriptions` with its request and response examples, and the catalogue entry `APPLICATION_IN_USE`. An error code's link on an operation scrolls to its entry. Loading a catalogue address directly (`/docs/api/#management/description/<code>`) shows the Introduction, where Scalar rewrites the address and does not scroll; the in-page links are the way in. `npm run check:links` in `guide/`: 75,972 links in 258 pages, ok.
7. **Size (V-D10, measured once).** The management document is 2.52 MB compact (2,518,219 bytes; 4.10 MB as the indented file the static build writes) with 295 operations, 800 schemas and 25 tags; the 361 example body files are 0.46 MB. The examples stay out of the document, as V-D10 decided (the same document with them inline would be about 3.0 MB).

**Follow-up (2026-11-11, decided by the requirement already stated).** (1) **The 28 codes are catalogued**, with `MAPPING_SET_CHANGED` that the sweep found in the same family (29 entries, all badged "Not a response status", each saying where it is met and written from the code that produces it): the 15 diagnostics of a compatibility check (`diagnostics`, and `details` of `MODEL_MIGRATION_REQUIRED`, with `count`), the 13 item codes of a migration (the `loss`, `created`, `reclassified`, `conversion`, `listed` and `refused` items of the job; one of them, `VERSION_MISMATCH`, is a publication's merge conflict in `details.conflicts` of `VERSION_CONFLICT`). The completeness test now reads `compatibility.py` (the codes handed to `_append_counted` and `_append_records`), `migrations.py` and `change_set_migrations.py` (the codes in the migration's SQL and its constant) and `publish.py` (the merge conflict), so a new code of these families fails until it has an entry; the sweep also found the publication's whole-graph diagnostics, logged in TODO. (2) **A direct link to a catalogue entry lands on it.** `/docs/api/#management/description/<code>` showed the Introduction: Scalar rewrites the address when it starts (it appends the source's slug) and does not scroll to a heading of the introduction. The page's own script (`_ANCHOR` in `management/reference/__init__.py`, first of the page's inline scripts, hashed into its policy like the others) keeps the address as it was opened, waits for the heading to exist, scrolls to it and puts the address back; it gives up when the reader scrolls, presses a key or clicks, and after 20 seconds, and touches nothing outside the page. Checked in headless Chromium, offline, requests outside the origin aborted, in light and dark, on the static build and on the instance page rendered under the root path `/rdm`: three entries each (`application-in-use`, `version-mismatch`, `workspace-not-found`) land with their heading at the top of the page and the address kept (`v9/anchor-static-light.png`, `-dark`, `anchor-instance-root-rdm-*`); the unit test `test_a_link_to_a_catalogue_entry_is_kept_and_scrolled_to_whatever_the_root_path` holds that the script is first and complete on both pages. Tag and operation addresses already worked and are untouched.

(3) **Every other code family is catalogued** (50 entries, badged as no response status where they are): the publication's whole-graph diagnostics and conflicts, a move's reasons, a mapping's problems, an import's row errors, a draft's profile warnings, the assistant check's and dry run's findings, the consumer contract and model validation findings, a subscription's suspension reasons and a backup rehearsal's failures. A final sweep of `app/` for upper-case literals found only environment and constant names left over, judged internal (listed in TODO). `_FAMILIES` in the completeness test lists the 23 files that write these codes.

**Checks.** The content unit tests (45, 41 s), `-m "reference or contract"` (169 passed in 3 min 25 s after the last change, with `test_api_reference.py`'s script count now six; known and not Track V's: the `test_batch_statements.py` budgets fail at HEAD, outside this group) and the OpenAPI lock, re-baselined on the tree as it stands (see the changelog entry).

**Closing record of Track V.**
- **What exists.** All 295 management operations (with the optional surfaces on; 251 by default) are documented on `/docs/api`: a title, a section of purpose and behaviour, parameter notes, error lines linked to the catalogue, and one recorded example (295 files, 361 bodies) for each; 25 area overviews; the conventions (`index.md`); the catalogue of 457 entries; every schema and field described, the draft and mapping operation kinds typed (V10); the writer's guidance (`content/README.md`); the V-D8 rule in AGENTS.md. The mechanism is `content.py` (the merge, strict in the tests), the `reference` test group (11 recording modules and the completeness test) and `static_site` for the public build.
- **Figures.** 295 operations, 800 schemas, 457 catalogue entries (119 as no response status), 295 example files, 2.52 MB document; the 169 tests of `reference or contract` take 3 min 27 s.
- **Open discrepancies for the user's separate decision (V-D7): 20,** all in [TODO, "API documentation discrepancies"](TODO.md#api-documentation-discrepancies), where each names the route, what API.md says, what the code does and where. The list holds 27 entries; seven are settled (the guide's links, the operation kinds, the surfaces-off build, the file check of imports and the OPERATIONS.md text). The 20: the feed's role; what `WORKSPACE_ADMIN_MUTATIONS_ENABLED` guards; the system configuration's `ai` group; the object create's application and type refusals; the at-least-one-of rule in a change set; the stale version of a cascading delete; the `path` of an attribute write in a change set; `publicationId` on parent candidates; `seek` on the edge list; the source publication's field; the model release routes the setting does not guard; what a move request does; the mapping history entry's `removed` and `migration`; the compatibility classification `invalid`; an export job's `parameters`; the `signedIn` of an agent application's block and restore; an AI call's purposes; the mail message's kinds; the task check's shape; and the design outline's `name`.
- **Still not in the reference.** The consumer read API (`/api/consumer/...`), by design (its documents are generated per definition from the model; "Not included" above); the 17 codes it answers, which the catalogue holds but no operation lists; the assistant tools' codes (4) and the passkey sign-in page's `TOO_MANY_PASSKEYS`; errors as examples (every example is the main successful use, V-D4); and the later events of the event stream, a workbook task designed by a session and a person who signs in with a passkey, which the harness cannot drive.
- **Palette reminder:** not applicable (the palette work was dropped by the user 2026-11-11).

### V10: The operation kinds in the document

_Asked by the user 2026-10-19, after searching Scalar for `setContainment` and not finding it._

**Why.** Two routes take a list of operations, each naming its `kind`: `POST
/model-drafts/{id}/operations` (55 kinds a client sends, `engine/model/authoring/kinds.py`) and `POST
/model-mappings/{key}/operations` (12 kinds, `engine/moves/mapping_kinds.py`). Their request schemas
declare `operations` as a list of free-form objects (`list[dict[str, Any]]`), so the OpenAPI document
names none of the 67 kinds and none of their parameters. Every kind is described in API.md (§ Kinds,
§ Model mappings), which `/docs/api` does not show. Measured on the running server 2026-10-19: no kind name
appears anywhere in the document. An integrator reading `/docs/api` cannot learn what either route accepts.

**Outcome.** Each kind is its own schema in the document: its `kind` value, its parameters with their
types, which are required, and one line on what it does. The two routes' `operations` items are the
union of their kinds, discriminated by `kind`. The 3 kinds only the server writes (the drafts' `replaceModel` and `restoreElements`, the mappings'
`restoreElements`) appear in the history reads, not in the request.

**What else the scan found (2026-10-19), for the record, not in scope:** 13 other request bodies have
free-form parts, each open by design: record and relation `attributes` (keyed by the model), the
`model` document of drafts and validations (the model schema is its own contract), and import
profiles' `valueMaps`. V4–V8 may point those to their sections. 71 of 153 operations have no
description, which V3–V9 cover.

| # | Question | Decision |
| --- | --- | --- |
| V-D11 | Do the schemas also check the request? | **Decided by the user 2026-11-11: the recommendation.** **they describe; the kinds keep checking.** Today a kind refuses a wrong parameter with its own code at its own path (`unknownParameter`, `missingParameter`, `invalidValue`, `unknownKind`), which the editor and the journey tests rely on. A Pydantic union at the request boundary would answer `422 REQUEST_VALIDATION_ERROR` instead, a contract change for every client. So the per-kind models are merged into the document only, and one unit test holds each kind's schema and the parameters its `Params` accepts in agreement, both registries in full, so a kind added or changed without its schema fails. The other choice (validate at the boundary) is cheaper to keep in step but changes the refusals |

**Scope.** The per-kind schemas (generated from each kind's accepted parameters where that is
enough, written where a parameter's shape needs words), their merge into the document, the agreement
test, and the `contract` lock re-baselined. It does not need the content directory or the recordings;
_since 2026-11-11 it is delivered inside V8_, whose routes take these bodies (V-D13). A kind added later
brings its schema in the same change (V-D8's rule). Checked 2026-11-11: still no kind name in the document.

## UP1: Type palettes A and B reworked (dropped)

**Dropped by the user 2026-11-11.** Both palettes stay as they are; kept below as history.

_Moved from [TODO](TODO.md) on 2026-10-10; asked by the user 2026-10-07._

A and B differ only in slots 3 and 4 (magenta and olive against plum and gold), and side by side the
user could not tell them apart: in the example model only five types' tiles change, and pink against
purple, olive against gold, read as near shades. Rework them into two palettes a person tells apart at
a glance, keeping what both must hold: eight hues distinguishable from each other and from the Live,
change-set and publication colours (green, amber, violet; ADR-040), ink at 4.5:1 on its fill and the
page, markers at 3:1, in light and dark (`tokens.test.ts`). Show both on the real app for the user to
judge (Settings › Appearance › Type colours switches them). Where: `styles/tokens.css`, the palette
section of [SETTINGS_AND_UI_PLAN](SETTINGS_AND_UI_PLAN.md#type-palettes-a-and-b). Planned in detail,
with its mock-up (both palettes side by side on the same screens, light and dark), when it starts; one
approval, then delivered whole. Checked 2026-11-11: unchanged since October, `tokens.css` still swaps
only slots 3 and 4 for `data-palette="a"`. Tests: `tokens.test.ts` for the contrast rules; the visual
baselines that show type tiles change and are re-recorded at R as intended changes.

## UP3: Settings › Model redesigned (dropped)

**Dropped by the user 2026-11-11**, after the check that 0.16 WM1 had moved changing a workspace's model into the workspace and the page had not been redesigned since 0.11 M6. Kept below as history.

_Moved from [TODO](TODO.md) on 2026-11-11, where the user placed it "for 0.14" on 2026-10-16 (0.11 M6)._

**Why.** M6 left the page laid out as Settings › Workspaces is (models in the list, the default
workspace's first; the selected model's card with where it runs, its releases and its drafts), and the
user judged it still not good. Tried in M5–M6 and rejected: columns of releases per model, a catalogue
listing every release and draft, a page per model with tabs, cards for workspaces and models with a
release timeline.

**What the user asked for on the way (M5–M6), kept as requirements:** no window nested in the page; a
row or card opens on a click anywhere on it; "Change model…" (not "Activate a release…") and its dialog
grouped by model; the default or current item first, not alphabetical; one design for every kind of
entry (no separate "New models"); the header's navigation consistent with the other Settings pages.

**What changed since (checked 2026-11-11 in `routing/routes.ts`):** the page still has model, release,
draft, migration and draft-editor addresses (`settings/model/models|releases|drafts|migrations/…`). 0.11
gave each workspace a model of its own, 0.12 MR1 retired and deleted model releases, 0.13 ED made the model
editor set everything a model holds, and 0.16 AP12 added "Change this model…". The redesign starts from
the page as it is now, read in the browser, not from the M6 description.

**The open question raised in M6**, answered with the mock-up: whether which release a workspace runs
belongs on Settings › Workspaces, leaving the model page as the library of models, versions and drafts.
The mock-up shows the recommendation and the user decides on it.

**Delivery.** A detailed plan with its mock-up (the page at 1440px and 390px, light and dark, the
"Change model…" dialog, the states: one model, several, a draft open, a migration running); one approval,
then delivered whole. Frontend first; an API change only if the mock-up needs a read the page lacks
(then documented by V-D8's rule). Tests follow the user's journeys on the page (find a model, open its
draft, change a workspace's model) with own dev credentials on every page the flow touches; the Settings
› Model visual baselines are re-recorded at R. One component per element: the list and card are the ones
Settings › Workspaces uses, extracted if needed, not copied.

## R: Build acceptance and release

As in every release: a full review of every change since 0.13's release commit (the release-review rule),
findings fixed; then the announced heavy runs, one at a time on the user's go-ahead, stopping on a failure
or an odd figure: the backend suite, Vitest, the browser runners, the accessibility and visual gates, the `reference` and `contract`
groups, the guide's `npm run verify` and the public build. The exit gate is the
[roadmap's](ROADMAP.md#product-release-014--management-api-reference-and-ui-refinements). CHANGELOG, PROJECT_STATUS and the guide rebuilt; the commit and tag on
the user's instruction.

## UP2: An application opens on a start page (closed)

**Closed 2026-11-11** by 0.12's D336, accepted with HM1's plan on 2026-10-25.

**Superseded for the first screen by 0.12 HM1 (D336, 2026-10-25):** signing in and the bare address
open the home page, not an application's list. Switching application inside a workspace still opens
its default view; UP2 can be reopened for that alone.

_Asked by the user 2026-10-15 during 0.10 (first filed under A8), moved here the same day as an
optional element; 0.10 goes on to R._

**Why.** Opening the app (the bare address, later the first screen after signing in) shows the first
application's default view, a list of records, before the user has chosen anything; the user found
it so in a private browser tab. The wish: the main area empty, with a centred text asking to choose
a list in the sidebar to start.

**What exists (checked against the code at `fcea5e0`).** An application's `defaultView` is required
by the model (`models/schema.py`, checked by `application_rules`). The browser opens it on load and
uses it as the fallback in about ten places (`app/App.tsx`): an address naming a view that no longer
exists, a change set moving to another model release, switching application, leaving a change
set's review. The bare address resolves to the first application (`routing/routes.ts`, not read in
detail).

**Proposal (not decided).** Keep `defaultView` in the model unchanged: its fallbacks still need a view,
and how an application first opens is the shell's behaviour, not the model's. Add an application's
start page: its address without a view shows the top bar and sidebar, the main area empty but for a
centred text ("Choose a list in the sidebar to start") under the application's name, the same for
every application. It shows for the bare address, after sign-in and on switching application; every
other case keeps today's fallback. The text reuses the editor centre's empty state, extracted once
into a shared component. On a phone, where the sidebar is folded, the text says how to open it
(not checked). Frontend only; no API or model change.

**Cost to check when planned:** browser runners and visual baselines that open `/` and expect a list
must open a view first (not counted). One browser check (the bare address shows the text, choosing a
list opens it, 390px) and a screenshot for the user's approval.
