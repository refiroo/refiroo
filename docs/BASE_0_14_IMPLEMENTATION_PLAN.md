# Base 0.14 implementation plan

**Status:** Created 2026-10-10 by the user, to hold the work left open when 0.9 closes: Track V's
V3–V9 (the management API documented, planned 2026-10-07 inside 0.9) and the rework of the type
palettes A and B (TODO since 2026-10-07). Planned before 1.0 for now; the user expects to move this
release after 1.0 later. V-D2–V-D10 are decided by the user (2026-10-07); V-D1 (where the text lives)
is open. The palette rework is not planned in detail yet.

**Overlap with 0.13 (decided by the user 2026-10-26):** the documentation release 0.13 writes the guide and
links to this release's `/docs/api` text (no double writing). The **error catalogue text (V-D5) is written in
0.13's DOC2**, once, and V3 reuses that file: V3 keeps the per-operation error listing and the
completeness check (V-D6) and drops the catalogue writing.

**Target:** Product 0.14.0, [management API reference and UI refinements](ROADMAP.md#product-release-014--management-api-reference-and-ui-refinements).

**Depends on:** Product 0.9.0 released (V2, the consumer contracts as reference sources; UA's type
palettes, ADR-040, U-D13). Neither track depends on 0.10–0.13, and nothing in them blocks those
releases; their packages can be taken earlier as fillers when the user asks. A V package delivered
after 0.12 documents authentication too.

## Packages

| Package | Needs | Scope in one line |
| --- | --- | --- |
| [V3–V9](#track-v--the-management-api-documented) | 0.9 V2 | The management API documented on `/docs/api`: the starter extended, content and examples beside the document, the error catalogue; V3 first, then V4–V8 in any order, then V9 |
| [V10](#v10-the-operation-kinds-in-the-document) | — | The 67 operation kinds of model drafts and model mappings declared in the OpenAPI document, each with its parameters |
| [UP1](#up1-type-palettes-a-and-b-reworked) | 0.9 UA | The type palettes A and B reworked so a person tells them apart at a glance |
| [UP2](#up2-an-application-opens-on-a-start-page-optional) (optional) | 0.10 | _Superseded for the first screen by 0.12 HM1 (D336)._ An application opens on an empty start page asking to choose a list in the sidebar, not on its default view |

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
| V-D1 | Where does the text live? | **Open; the user asked for a minimal footprint in the code (2026-10-07).** Recommendation: **the code holds no documentation text and no examples.** One function merges a content directory into the generated OpenAPI document when the app builds it, the way FastAPI's documented `app.openapi()` override does. The directory is `backend/app/management/reference/content/`, shipped as package data like the bundled Scalar script. It holds an `index.md` for the document's conventions and, per tag, one Markdown file with the area overview and a section for each operation, headed by its method and path (`POST /api/v1/objects`) and holding the purpose, behaviour, limitations, errors and parameter notes. It also holds `errors.md`, the code catalogue (V-D5), and `examples/`, one JSON file per operation with its named example requests and responses, written by the recording (V-D3). Keys are method and path, the public contract, not FastAPI's generated `operationId`, which follows Python function names. The in-code descriptions that already exist (15 operations, 151 parameters, 75 schemas) stay. New field text goes in the code only where the field is otherwise undescribed and a sentence is enough. A section naming a route that no longer exists fails the V-D6 check. API.md remains the builders' contract record (DOCUMENTATION_PLAN "Not included"). API.md says what was decided and why, and `/docs/api` says how to use it |
| V-D2 | Which model and data do the examples use? | **Decided by the user 2026-10-07: the bundled starter, extended until it holds every capability the documentation must show, both for the examples and for demonstrating the engine.** The extension is a new content release of the starter, shipped to every new deployment, so a reader can repeat every example on a fresh install. The starter has no domain-specific content (domains, codelists, master values such as delivery methods, systems and translations). Today it holds only part of the structures the journey tests name (checked in `configurations.py`, `example()`): a root type with a unique code, and languages, translation groups and translations with a scoped uniqueness rule. It lacks a self-hierarchy, a many-to-many relation with its own attributes, a one-to-one relation, a type ladder to restructure across, the integer range, required, read-only-with-default and at-least-one rules, and a consumer API with match rules and every parameter kind. V3 lists every capability the documented operations need, maps each to the starter type that shows it or to the smallest addition in the same domain, and adds them. The journey tests on the `example` configuration then cover more structures, because the starter holds more. The example model is not used, because its content reads as one business domain |
| V-D3 | Where do the examples come from? | **Decided by the user 2026-10-07: recorded from a run, and kept current by a rule, not by a comparison check.** A reference scenario calls the public API on the extended starter's seed, built once and reused. Each step records a request and its response into the operation's example file, normalised: IDs become stable readable placeholders (consistent across steps, so a created ID reappears in the next request) and times are fixed. Each step asserts only the status and code it records. The rule (V-D8): a change to a route's behaviour or shape regenerates that route's examples in the same change, and the git diff of the example files shows the change for review. There is no committed-versus-rerun comparison |
| V-D4 | How many cases? | **Decided by the user 2026-10-07: one example per operation to start**, the operation's main successful use. The errors are described in text (V-D5), not shown as examples. After V3, the user looks at how the examples read, how much space they take and how manageable they are, and decides whether more are added (more use cases, error examples) |
| V-D5 | How are errors documented? | **Decided by the user 2026-10-07: a few sentences for every error code**, in the code catalogue `errors.md`, written once per code: what the code means, why it happens with a hint at the usual root cause, and what the client does about it. Today a code carries a short message at the place it is raised; the catalogue explains it. Each operation lists its statuses as OpenAPI responses with the codes each can carry, linked to the catalogue, from reading the operation's code path. One check: every code the backend raises (the set `test_api_journeys` already collects) has a catalogue entry and is listed on at least one operation |
| V-D6 | How does completeness stay visible? | **Approved by the user 2026-10-07.** A contract test from V3 on lists every operation without a content section or example, every parameter and schema field without a description, every content section or example naming a route that does not exist, and every code without a catalogue entry. It compares them with a committed gap list that may only shrink. Each package empties the list for its area, and V9 deletes the list. The text is written for integrators: no package or decision IDs and no history (DOCUMENTATION_PLAN principle 1). Each statement can be checked against the code |
| V-D7 | What if the code and API.md disagree? | **Decided by the user 2026-10-07: logged, highlighted and decided separately.** The package documents what the code does, records the discrepancy in TODO under "API documentation discrepancies" (the route, what API.md says, what the code does, where) and lists it at the top of its record and its report, so it is not missed. The decision (fix the code or correct API.md) is taken separately. API.md is read on every prompt, so few discrepancies are expected |
| V-D8 | How does the documentation stay current? | **Approved by the user 2026-10-07, as part of the coding-agent guide.** V3 adds the rule to AGENTS.md (working method, the documentation step) and to "How a package is delivered", step 3: a change that adds or changes a management route updates its content section, its error listing and catalogue entries, and regenerates its examples, in the same change |
| V-D9 | Where in the queue? | **Decided by the user 2026-10-07: Track V's V3–V9 are independent and block no release, neither 0.9.0 nor 1.0.** _Amended 2026-10-10 by the user: moved from 0.9 to release 0.14, planned before 1.0 for now and expected to move after it; still independent of every other release._ They are fillers taken when chosen. R and R-a do not wait for them. DOC2's audit of the OpenAPI descriptions is done here instead, and DOC2 keeps the settings, limits and model language references; DOCUMENTATION_PLAN gets a pointer in V3 |
| V-D10 | Document size | **Approved by the user 2026-10-07.** Examples stay short: pages of two or three items, and long arrays trimmed in the recording with a note saying so. The document is 290 KB today. V3 measures it with V3's examples, projects the full size and reports. If the projection is over about 2 MB, examples are served as separate files that the document references, not inline. Measured once and not tuned in a loop |

### Packages

Each package documents one area completely by V-D1–V-D6 and empties its part of the gap list. Its
tests are the `reference` group (new in V3: the recording run, whose steps assert their status and
code) and `contract` (the OpenAPI lock, re-baselined for each package by diffing the document). Each
package covers about 10–25 operations.

| Package | Needs | Area (operations) |
| --- | --- | --- |
| **V3** Foundation and the service | V2 | The starter extended (V-D2: the capability inventory, the additions, a new content release, the `example` configuration's structure map updated). The mechanism: the content directory and its merge (V-D1), the scenario harness and recording (V-D3), the error catalogue and per-operation responses (V-D5), the gap list and its check (V-D6), and the size measurement (V-D10). The V-D8 rule in AGENTS.md and the delivery steps. Text: the document's conventions, every error code's catalogue entry, and the `system`, `health`, `capabilities`, `workspaces` and workspace runtime state operations (about 12). Ends with the user's review of how the examples look (V-D4) |
| **V4** Records | V3 | Objects: create, read, update, delete, the per-type list and the cross-type lookup, the model-aware query, attribute values, history and parent candidates (15). Contexts, `asOf`, filters and sorts, uniqueness and required rules, moving a record |
| **V5** Relations and mappings | V3 | Relations (5), the edge list and the mapping reads and replacement (5), and the relation matrix (3). Relation rules, cardinality, containment as a relation, coverage |
| **V6** Change sets and publications | V3 | Change sets (list, create, read, update, delete, model release, object and relation changes, validation, publication), restructuring preview and apply, publications (read, list, withdrawal) (17). How a change set merges onto live data, conflicts, publication snapshots |
| **V7** Bulk and following changes | V3 | `POST /batches` with every item kind, jobs (read, list, items, cancel), the feed, and the export routes once J1 is delivered (about 8). Idempotency, failure policies, item outcomes, background runs, feed positions, retention and `410` |
| **V8** The model | V3 | Model reads (applications, types, relations, placements, the model, runtime state), releases, diffs and activations, validations, and the model administration surface when enabled (about 25). The model is the bulk of the area overview: the operations are simple reads, but what they describe is the whole engine |
| **V9** Webhooks, and close-out | V3, V4–V8 | Consumer subscriptions: create, read, update, suspend, resume, delete, deliveries and resend (10). Retries, batching and signing, as DOCUMENTATION_PLAN's points require. Then the close-out: the gap list empty and deleted, the V-D5 check passing over the whole document, the API.md pointer to `/docs/api` added, and the DOC2 audit item marked done |

**Not included:** the consumer read API (`/consumer/...`). Its documents are generated per
definition from the model, and their descriptions are a separate question (TODO once V-D1 is
approved). Also excluded: tutorials and how-to guides (DOCUMENTATION_PLAN 0.13) and translations.

**Composable domains (ADR-032):** no door is affected. The text describes contracts and does not change
them. The examples use one configuration of generic capabilities and are presented as such.

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
| V-D11 | Do the schemas also check the request? | **Open.** Recommendation: **they describe; the kinds keep checking.** Today a kind refuses a wrong parameter with its own code at its own path (`unknownParameter`, `missingParameter`, `invalidValue`, `unknownKind`), which the editor and the journey tests rely on. A Pydantic union at the request boundary would answer `422 REQUEST_VALIDATION_ERROR` instead, a contract change for every client. So the per-kind models are merged into the document only, and one unit test holds each kind's schema and the parameters its `Params` accepts in agreement, both registries in full, so a kind added or changed without its schema fails. The other choice (validate at the boundary) is cheaper to keep in step but changes the refusals |

**Scope.** The per-kind schemas (generated from each kind's accepted parameters where that is
enough, written where a parameter's shape needs words), their merge into the document, the agreement
test, and the `contract` lock re-baselined. Independent of V3: it does not need the content directory
or the recordings, and it can be taken first. A kind added later brings its schema in the same change
(V-D8's rule).

## UP1: Type palettes A and B reworked

_Moved from [TODO](TODO.md) on 2026-10-10; asked by the user 2026-10-07._

A and B differ only in slots 3 and 4 (magenta and olive against plum and gold), and side by side the
user could not tell them apart: in the example model only five types' tiles change, and pink against
purple, olive against gold, read as near shades. Rework them into two palettes a person tells apart at
a glance, keeping what both must hold: eight hues distinguishable from each other and from the Live,
change-set and publication colours (green, amber, violet; ADR-040), ink at 4.5:1 on its fill and the
page, markers at 3:1, in light and dark (`tokens.test.ts`). Show both on the real app for the user to
judge (Settings › Appearance › Type colours switches them). Where: `styles/tokens.css`, the palette
section of [SETTINGS_AND_UI_PLAN](SETTINGS_AND_UI_PLAN.md#type-palettes-a-and-b). Planned in detail,
with its screenshots, when it starts.

## UP2: An application opens on a start page (optional)

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
