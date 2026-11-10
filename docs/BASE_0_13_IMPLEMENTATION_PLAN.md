# Base 0.13 implementation plan

## Restarted 2026-11-02

The first approach failed and was stopped by the user. It built the guide around what a test could
check: briefs written by Claude with recorded API requests and responses that the writer had to copy, so
pages for people who work in the browser carried JSON, and the one page written (by Claude, against
DOC-D15) explained nothing a real reader needed. The packages below this section are superseded; they are
kept as history.

**The approach now.** Codex writes the guide directly from the application, guided by one page,
[`guide/AGENTS.md`](../guide/AGENTS.md): who reads which section and what each needs (about, use, model,
administer, run, integrate), and plain rules (write for the reader's task; people in the browser see
screens, never JSON; integrators get concepts and sequences with links to `/docs/api`, which 0.14 completes;
only what exists; the Graubünden reference data as the one example world). Claude writes no page text.

| Step | What | Who |
| --- | --- | --- |
| 1 | The guidance page, read by the user before Codex writes | Claude; the user reads |
| 2 | Pilot: four steward pages (`guide/_waves/PILOT.md`), read by the user in `/docs` | Codex, run through `guide/tools/codex-wave.mjs` |
| 3 | Screenshots the pages ask for, from the reference instance with the browser runners | Claude (mechanical) |
| 4 | The other sections, one audience at a time, the user reading each section's first pages | Codex |
| 5 | 0.16's AI pages after 0.16's release step (DOC-D21) | Codex |
| 6 | Publication, review and release (DOC12, R) | Claude |

Kept from the first approach: the documentation site at `/docs` (DOC1's serving, links, image build), the
Graubünden reference data and its Docker instance (DOC-D17), the Codex tool, and the corrections to the
repository's documents and `compose.yml`. Removed: the briefs, the recorded examples, the coverage
inventory, the `docs` test group and DOC2's description and error-catalogue work (the error catalogue stays
0.14's). Claude's part is kept small; the writing is Codex usage.

**Earlier status (superseded):** Planned 2026-10-26 at the user's request. All decisions DOC-D10–DOC-D20 are decided by the
user (2026-10-26). **DOC1 delivered 2026-11-02; DOC3 part 1 (samples, reference instance, coverage inventory) and part 2 (ownership, briefs of waves A and B) delivered the same day**; waves C to F briefs and the writing are not built yet. **Revised 2026-11-02:** the guide also documents 0.16's AI
integration ([DOC-D21](#decisions), decided by the user), in its own wave once 0.16's surfaces are final;
each Codex wave gets a prompt file in the repository, and DOC2's description batches run in an agreed
window.

**Target:** Product 0.13.0, [the documentation release](ROADMAP.md#product-release-013--documentation).
The strategy, readers and principles are in [DOCUMENTATION_PLAN](DOCUMENTATION_PLAN.md); this plan is
what is delivered, in what order, by whom and how it is checked.

**Depends on:** 0.12 complete (every example carries authentication, and the browser's screens, the
Security pages and the deployment guide are final). 0.14 (the management API reference on `/docs`) and
0.15 (interface language) do not block this release; the guide links to what 0.14 writes
([DOC-D12](#decisions)). 0.16 (AI integration) is documented here too ([DOC-D21](#decisions)): waves A–F
do not wait for it, but wave G (DOC9A) starts only after 0.16's release step R, and DOC11, DOC12 and R
need wave G.

## Why

[DOCUMENTATION_PLAN](DOCUMENTATION_PLAN.md) (2026-10-05) spread the work over three earlier packages
(DOC1–DOC3, foundation, generated reference and explanations) and a documentation release. Those earlier
packages were never built: there is no `guide/` directory, no `/guide` route, no `docs` test group and no
rule in AGENTS.md. So 0.13 delivers the whole guide, and the plan was also too narrow in three places,
found by checking it against what the repository now holds (2026-10-26):

- **Operating the engine had one tutorial** ("upgrade and recover"). OPERATIONS.md is 1,120 lines:
  settings, authentication setup, roles and grants, sign-in with the organisation's provider, second
  factors, mail, the database, startup checks, monitoring, jobs, webhooks, deploying with HTTPS,
  topologies, model releases, upgrades, backup and restore. A new organisation cannot install, secure and
  run refiroo from the plan's pages.
- **Architecture was left with the builders.** [ARCHITECTURE](ARCHITECTURE.md) is 1,246 lines of design
  record. An evaluator, an operator or a security reviewer needs a plain account of how refiroo is put
  together, which no page in the plan gave.
- **Security and access had no pages.** 0.12 added sign-in, roles, groups, grants, OAuth clients, signing
  keys, approvals and the audit of who changed what (F26–F28, J39–J47). An administrator's pages and a
  security overview were missing.

## Outcome

A person who has never seen refiroo can find the page for their goal, follow it, and get the result it
promises. The guide covers every capability, journey, setting, error code and command; every request and
command it shows ran against the engine; and a reader from outside the project completed each tutorial.
It is served by the engine at `/guide` and published as a site from the same sources.

## Who does what

| Role | Does | Does not |
| --- | --- | --- |
| **Codex** (DOC-D15) | Writes the pages from their briefs, in waves; writes the descriptions of settings, error codes and model-language fields beside the code (DOC2) | Edit code outside the files a package names; change an example's expected response; commit; read or quote a private model |
| **Primary agent** (strong model) | Builds the mechanism (DOC1, DOC2), writes every brief and the coverage matrix (DOC3), runs each wave's checks and fact-check, builds the screenshots and the publication | Write pages the brief assigns to Codex, except to correct a fact the fact-check found |
| **The user** | Decides the open decisions, reads the pages named for a read, commits | |

**Changed 2026-11-02 at the user's request:** the primary agent runs Codex through
`guide/tools/codex-wave.mjs` (Codex CLI `exec`, sandboxed to the repository): `run` starts a wave from
its prompt file, `check` lists every file the run changed against the wave's allowed list and runs the
checks, `reply` sends the fact-check list back to the same Codex session, `status` reports each run's
turns and token usage. A file changed outside the list is reported, never reverted. Each wave's usage is
reported to the user. What Codex needs must still be in the repository:
`guide/AGENTS.md` (written in DOC1) holds the writing rules; each page has a brief; each wave has a
prompt file, `guide/_waves/<package>.md` (written in DOC3), naming the wave's pages, the only files it
may edit and the checks to run before it stops, so the user starts a wave with one line pointing Codex
at that file; the checks run without the primary agent. Codex edits only the files in its wave's list,
so waves do not touch each other's files in the shared working tree. A page is never half-finished: it is `status: stub`
(a brief and a title) or `status: written` (all of its brief), and the build refuses a published page
that is a stub.

## The guide

Navigation is by the reader's goal ([DOC-D10](#decisions)); every page is labelled with its kind
(tutorial, how-to, explanation, reference) and the kinds are never mixed on a page
([DOCUMENTATION_PLAN principle 2](DOCUMENTATION_PLAN.md#principles)). The pages below are the
inventory. "Seed" names the documents and code a brief points the writer to. "Covers" are the
inventory items the page claims for the coverage matrix ([below](#coverage-the-check-that-nothing-is-missing)).
The page count is not a target: a topic with no reader goal gets no page, and a goal needing two pages
gets two.

### 1. Start here

| Page | Kind | Seed | Covers |
| --- | --- | --- | --- |
| What refiroo is | Explanation | PRODUCT.md, OPERATORING.md | the four things a team manages; F01 |
| What makes it different | Explanation | PRODUCT_GUIDE.md, REAL_WORLD_RESEARCH.md | |
| What it does not do | Explanation | PRODUCT.md "not", ROADMAP "Unscheduled" | |
| Run it in five minutes | Tutorial | README, `compose.yml`, `.env.example` | quick start |
| A tour of the example applications | Explanation | EXAMPLE_MODEL.md | F01 |
| Which path is yours | Explanation | [Readers](DOCUMENTATION_PLAN.md#readers) | |
| Glossary | Reference | GLOSSARY.md | every term |
| Questions people ask | Explanation | gathered from the fresh-reader check (DOC12) | |

### 2. How refiroo works (concepts and architecture)

Explanations, each with a worked example on the running example's data. The first four are the
architecture the user asked for: they are written for evaluators, operators and security reviewers, and
describe the product as one whole. ARCHITECTURE.md remains the builders' design record; these pages are
derived from it and from the code, and do not copy it.

| Page | Explains | Seed | Covers |
| --- | --- | --- | --- |
| The parts of refiroo | The browser, the web proxy, the engine, PostgreSQL, the job files, and the path of one request through them | ARCHITECTURE "Overview", "Deployment topology" | |
| One engine, many applications | A model becomes screens and APIs; why no code knows an application | ARCHITECTURE, EXAMPLE_MODEL | F01 |
| Where data lives | Workspaces, records, typed values, relations, versions; what is in the database and what is not (the job files, the keys). **Stated as an explanation, not a contract: the tables are not an interface** | ARCHITECTURE "Runtime data" | F02, F06 |
| How refiroo is secured | Sign-in, tokens, roles, groups and grants, scopes, clients, the audit of who changed what, secrets at rest, what the web proxy must do, what refiroo does not protect against | ARCHITECTURE "Security (0.12)", [SECURITY_REVIEW_0_12](SECURITY_REVIEW_0_12.md), OPERATIONS "Authentication" | F26, F27, J39–J47 |
| Three kinds of change | Live edits, change sets, model releases | PRODUCT.md | F05, F12, F15 |
| How a change set publishes | Base, overlay, merge onto live data that moved on, conflicts, what a publication holds | ARCHITECTURE "Live data, change sets and publications" | F12–F14 |
| History and time | Audit history, pinned reads, publications as frozen copies, effective periods, `asOf` | ARCHITECTURE | F11, F21 |
| Connections | Containment, recursive hierarchy, cross-reference, mapping, the relation matrix, cardinality, scope | APPLICATION_MODEL | F07–F09 |
| Concurrency without locks | Record versions, relation-set versions, conflicts, `unchanged` | ARCHITECTURE "Writes and concurrency" | F17 |
| Identity | Object IDs, business keys, unique attributes, client-assigned IDs | CONSUMER_API, APPLICATION_MODEL | |
| Models and releases | What a model declares, drafts, installation, activation, compatibility, schema version against release version, a workspace's own model | ARCHITECTURE "Model definition and releases", APPLICATION_MODEL | F15 |
| Consumer APIs | A declaration becomes an API: the shared object, roles, projections, parameters, lists | CONSUMER_API | F23 |
| How XREF scores | Own and promoted weights, exact before contains, ties, `scoreOnlyMatching`, crosswalk; a scored example worked by hand | CONSUMER_API | F20, F23 |
| Consistency for consumers | Live against pinned reads, `latest`, cursors that keep their publication, ETag | CONSUMER_API | |
| Reading and querying | Cursors and positions, `asOf`, model-aware queries, one relationship hop, contexts | ARCHITECTURE "Reads and queries" | F03, F16, F20 |
| The change feed, events and webhooks | Positions in commit order, retention, recovery, signed deliveries, retries | INTEGRATION_API, CONSUMER_API | F25 |
| Jobs and bulk work | Inline and background runs, failure policies, item outcomes, idempotency, resumption, cancellation | ARCHITECTURE "Jobs" | F22 |
| Approvals | Submit, approve, send back, four-eyes, self-approval | ADR-045 | J42 |
| Limits and why they exist | Each limit, what it protects, the setting that changes it | OPERATIONS "Batch and job limits", the generated limits reference | |
| Running several processes and nodes | What is shared (the database), what is local, what a node needs | ARCHITECTURE "Deployment topology", OPERATIONS "Several processes" | J24 |

### 3. Tutorials

Seven, one per reader goal. Each follows one running example from start to finish and runs as a test
where it can ([How examples are checked](#how-examples-are-checked)).

| # | Tutorial | Reader | Ends with |
| --- | --- | --- | --- |
| 1 | Your first correction, then your first publication | Data steward | A live edit, a change set reviewed and published, a conflict resolved, the history read |
| 2 | Model your own domain | Model administrator | An empty model grown into an installed, active release (the reference domain's Network part, canton > district > municipality > stop: a hierarchy, a relationship and views), then a compatible change released |
| 3 | Load and keep in sync | Integrator, management API | A client created and a token obtained; a file loaded as a batch, retried safely with an idempotency key; the change feed followed from a position |
| 4 | Publish a consumer API and translate codes | Integrator, consumer API | A consumer API declared; a list paged; a code resolved by XREF, in a batch and across systems; an extract pinned to a publication |
| 5 | Install, secure and sign in | Operator | From a clean host to a running instance behind HTTPS: configured, first administrator created, signed in, health checked |
| 6 | Upgrade, back up and restore | Operator | An upgrade, a backup and a restore rehearsed, with the restore check |
| 7 | Give people and systems access | Access administrator | People, a group, a role, a grant narrowed to a workspace and a record type, an OAuth client for an integration; a rotated secret |

### 4. Use refiroo (data steward)

How-to guides, one per task, taken from the journeys J01–J19, J32, J45 and capabilities F01–F14, F18.
The brief of each page names its journeys. Pages (the DOC3 briefs may split or join them; the
coverage matrix decides completeness):

- Find, filter, sort and select records; read a record and its context (J01); the display preferences
- Correct a record (J02); add a record where it belongs (J03); delete a record and what depends on it (J04);
  change many records at once (J32)
- Relate records and maintain their relationships (J13); review and replace a record's related records
  (J10); see and fill relationship coverage across ancestors (J16)
- Build and change a hierarchy (J14); reshape a hierarchy across types (J15); move a record and its subtree
- Map a system's values to their shared meaning; fill missing translations from the relation matrix
- Prepare, review and publish a change set (J05, J17); keep working live meanwhile (J06); prepare under the
  next model version (J18); withdraw a publication and start from history (J07)
- Fix a value someone else just changed (F17); read a record's history; see one person's changes across
  workspaces (J44)
- Propose and approve a change (J42)
- Administer workspaces (J19); start from Home (J45)
- Use the keyboard, a narrow screen and the accessibility features (F18)

### 5. Model your domain

- Design a model in the editor (J33); add a field to a released type; declare an effective period; add a
  view; define a consumer API in the model (J25)
- Create and activate a model release (J08); read a release diff; know when a change needs a new contract
  version; roll back
- Add a relation matrix in the editor: an overview of records against an ancestor type's values, listing
  an existing type in another application for it. State clearly: types or relation types sharing a name
  are separate, each with its own records or pairs, so a view over one does not show the other; a new pair
  on an existing relation type does not take over its one-per rule
- Onboard a workbook (J34); load the next version of a workbook (J35)
- **Shape a workbook on the canvas (added 2026-10-31 at the user's request; arrives with 0.17, PL3b):** place
  cards, make lists, connect a hierarchy or a relationship, add filters and navigation groups, read refused rows,
  turn wide sheets and grouped rows into records, repeat the load from the saved profile, and do it all without
  dragging and through the API. With screenshots. If this guide is written before 0.17, it covers today's
  editor and PL3b adds this page in its own change
  ([0.17 plan](BASE_0_17_IMPLEMENTATION_PLAN.md#pl3b-the-workbook-canvas))
- Run a workspace on a model of its own (J36); move a workspace to another release (J37); move data
  between workspaces whose models differ (J38)
- Reference (generated): the model language. Seed for the prose around it: MODEL_AUTHORING.md,
  APPLICATION_MODEL.md

### 6. Integrate

Management API (J11, J20–J24, J26, J27):

- API conventions: base URLs, workspaces and contexts, identifiers, versions and conflicts, paging, the
  error envelope, idempotency. Links to `/docs` for each operation ([DOC-D12](#decisions)); states the
  conventions in prose only where `/docs` does not
- Authenticate an integration: create a client, obtain a token, refresh, what a `401` and a `403` mean
- Discover the model and the API (J20); read a collection completely and resume (J21); request the
  precise dataset (queries, one relationship hop, `expand` and its cost) (J22); answer a business-date
  question (J23)
- Submit a bounded bulk change (J11); upsert by a business key; replace a record's relationship set;
  run a large background job and recover (J24); follow changes reliably, and recover from `410` (J26)
- Exchange a supplier file (J27)
- Receive and verify webhooks; rotate a signing key (J43); the retry schedule and batch limits
- Handle errors: which to retry, which to correct, which to report

Consumer APIs (J28–J30):

- Read a business object (J28); resolve a code and a file of codes, with XREF (J29)
- Narrow a lookup with parameters; cache with ETag; extract a consistent snapshot; follow a consumer API's
  changes (J30); move to a new contract version
- Design a consumer API (what to expose, which types, what XREF then searches)

### 7. Run refiroo (operators)

| Page | Kind | Seed | Covers |
| --- | --- | --- | --- |
| Before you install: requirements and sizing | How-to | OPERATIONS, [POSTGRESQL_BUDGETS](POSTGRESQL_BUDGETS.md), the 0.11 volume measurements | Only figures that were measured, each with where it was measured. Where nothing was measured, the page says so |
| Install with Docker Compose | How-to | `compose.yml`, `.env.example`, OPERATIONS "Deploying" | the reference installation |
| Publish it with HTTPS | How-to | `compose.acme.yml`, `caddy/`, `frontend/nginx/`, OPERATIONS "Automatic HTTPS" | |
| Deployment topologies | Explanation | OPERATIONS "Deployment topologies" | |
| Install without Docker | How-to | OPERATIONS "A developer instance", `scripts/` | Only if it is a supported way; otherwise a page saying what is supported (DOC-D19) |
| How configuration works | Explanation | `app/config.py`, OPERATIONS "Settings" | where a setting comes from, precedence, which need a restart |
| Configure the web address, proxies and cross-origin access | How-to | `PUBLIC_URL`, `CORS_ORIGINS`, `FORWARDED_ALLOW_IPS` | |
| Configure database connections and several processes | How-to | OPERATIONS | |
| Choose which capabilities are on | How-to | OPERATIONS "Capability groups" | the capability flags |
| Tune batch and job limits | How-to | OPERATIONS "Batch and job limits" | |
| Set up sign-in: local accounts, the organisation's provider, a second factor | How-to | OPERATIONS "Authentication", I1–I4c records | F26 |
| Set up mail | How-to | OPERATIONS "Sending mail" | F28 |
| Keys and secrets: what each is, where it lives, how to rotate | How-to | `SECRETS_ENCRYPTION_KEY`, `RDM_CURSOR_SIGNING_KEY`, `generate_key`, `reseal_secrets` | |
| Create the first administrator and clients | How-to | `create_admin`, `create_client` | |
| Health, readiness and startup checks | How-to | OPERATIONS "Startup checks and health" | J12, J31 |
| Monitoring and logs | How-to | OPERATIONS "Monitoring", "Logs" | |
| Operate jobs, exports, imports and source files | How-to | OPERATIONS | F22 |
| Operate webhooks: a suspended subscription, redelivery | How-to | OPERATIONS "Webhook subscriptions" | |
| Release, roll back and migrate models | How-to | OPERATIONS "Model releases and rollback" | |
| Upgrade | How-to | OPERATIONS "Upgrades", `database_upgrade`, `model_schema_upgrade` | |
| Back up and restore | How-to | OPERATIONS "Backup and restore", `restore_check` | F19 |
| A production checklist | How-to | the above, SECURITY_REVIEW_0_12 | every item links to its page |
| Troubleshooting | How-to | the error codes, startup checks and OPERATIONS runbooks, symptom to cause to fix | |

### 8. Administer access and security

| Page | Kind | Seed | Covers |
| --- | --- | --- | --- |
| Security overview (the administrator's version) | Explanation | [How refiroo is secured](#2-how-refiroo-works-concepts-and-architecture) | |
| People, groups and roles | How-to | Settings › Security, OPERATIONS "Roles and grants" | F27, J40 |
| Grants: a workspace, a record type, a consumer API | How-to | | J40 |
| Clients for systems, and their secrets | How-to | | J41 |
| Secure your own sign-in: sessions, a second factor and passkeys (a person's own) | How-to | Settings › Account | F26, J39 |
| Second factor and lost devices (the administrator's) | How-to | OPERATIONS "A second factor for local accounts" | J39 |
| Rotate signing keys | How-to | | J43 |
| Approvals policy for a workspace | How-to | ADR-045 | J42 |
| See who changed what | How-to | | J44 |
| Check the security model | How-to | J47 | J47 |
| Reporting a vulnerability | Reference | the security policy (0.12 Track L) | |

### 9. Reference

Generated from the code where the code holds the facts ([DOC-D6](DOCUMENTATION_PLAN.md#decisions)). A
check fails on an undescribed entry.

| Reference | Source | Package |
| --- | --- | --- |
| Settings | `app/config.py`: name, default, allowed values, effect, restart needed | DOC2 |
| Capabilities and limits | the settings and `GET /capabilities` | DOC2 |
| Error codes | every code the backend raises: status, meaning, usual cause, what the client does | DOC2 ([DOC-D13](#decisions)) |
| Model language | `models/schema.py`, per field, with the schema versions | DOC2 |
| Command line | the commands in `app/cli/` (`create_admin`, `create_client`, `generate_key`, `database_upgrade`, `model_schema_upgrade`, `reseal_secrets`, `restore_check`) from their own `--help` | DOC2 |
| Roles and permissions | the permission catalogue: each role, what it allows, the operations behind each permission | DOC2 |
| Event types and webhook headers | the event schema and delivery headers | DOC2 |
| Management API | `/docs` (0.14 writes it) | link only |
| Each consumer API | its generated document | link only |
| Glossary | GLOSSARY.md | DOC1 |

### 10. About this release

- Release notes written for readers (from CHANGELOG), the compatibility commitment and the supported
  schema versions with their dates (0.12 Track L), upgrade notes between releases
- The licence and where to contribute, and one page "For people who build refiroo" that links to the
  repository's `docs/` and says what it holds (the builders' record, not the guide)

## The points that must be stated clearly

[DOCUMENTATION_PLAN](DOCUMENTATION_PLAN.md#the-points-that-must-be-stated-clearly) lists eight. TODO
records two more from the browser side. All ten are page entries here, each in its brief's "must
state" list, and the coverage check fails when a brief's required statement is not on the page:

| Point | Stated on |
| --- | --- |
| The eight in DOCUMENTATION_PLAN (older publication after a release, contains from 3 characters, which workspace a consumer read addresses, `latest`, ETag, XREF searches only what its API exposes, webhook retries, webhook batch size) | As listed there |
| Which records a relationship may choose (0.9 K7): a binding's `candidates`, examples of each criterion, what pickers offer and say, why a record is not offered, relationships made before are kept, free-text criteria are the model administrator's responsibility | Model your domain › design a model; Connections; Use refiroo › relate records |
| How many relation columns a table may show (0.9 K6a): as many as the type has relationships, read only for the rows on the page, dropped when hidden; what `expand` costs (page size × columns × `expandLimit`) | Use refiroo › find and filter; Integrate › precise dataset; Limits |

New points keep arising. A decision that says "state this clearly" is recorded as a page entry in this
table from now on, not as a TODO note.

## How examples are checked

An example is a request, a response, a command or a model fragment shown in the guide. Four kinds:

| Kind | Where it runs | Compared |
| --- | --- | --- |
| `api` | The `docs` test group, against the seeded starter model and the guide's sample data, with authentication | The response, with IDs and times normalised |
| `cli` | The `docs` test group, against a scratch database | The exit status and the output lines the page shows |
| `model` | Validated by the engine's own model validation, and installed in the test | Valid, or the exact refusal the page shows |
| `shell` (Docker, Compose, the web proxy, backup and restore on a host) | The deployment runner (`frontend/e2e/dp3-deployment.mjs`) for the commands it covers; the rest are marked `unrun` in the page's front matter and are rehearsed once on a clean host in DOC12 | The page lists which of its commands are `unrun` |

The group is a check on the documentation, not a test programme ([AGENTS.md](../AGENTS.md#testing): tests
serve the feature). It reuses the journey harness, seeds once and reuses the seed until the model,
schema or sample data change, and runs only when `guide/` or the engine boundary a page covers has
changed. The guide's sample data is its own: small files in `guide/samples/` loaded through the public
API (an import or a batch). It never uses a private model or a source export
([AGENTS.md](../AGENTS.md), invariants).

## Coverage: the check that nothing is missing

Every page has front matter:

```yaml
title: Correct a record
kind: how-to            # tutorial | how-to | explanation | reference
reader: steward         # evaluator | steward | model-admin | integrator | consumer-integrator | operator | access-admin
status: written         # stub | written
covers: [J02, F05, F06, F17, setting:RDM_EXAMPLE, error:RECORD_VERSION_CONFLICT]
must_state: [version-conflict-keeps-newer-value]
examples: [api, model]
```

An inventory script lists the things the guide must account for, and the check fails on any item that no
page covers and that is not in `guide/_coverage/exclusions.yaml` with a reason:

| Inventory | Source |
| --- | --- |
| Capabilities, every F entry (F01–F28 in 0.12, and 0.16's) | CURRENT_FUNCTIONALITY |
| Journeys, every J entry (J01–J47 in 0.12, J48 onward from 0.16) | USER_JOURNEYS (the retired J09 is an exclusion) |
| Settings and capability flags | `app/config.py` |
| Error codes | the codes the backend raises (the set the API journey tests already collect) |
| Commands | `app/cli/` |
| Roles and permissions | the permission catalogue |
| Event types | the event schema |
| Model-language fields | `models/schema.py` |
| Required statements | the `must_state` lists of the briefs |

Like Track V's gap list, the exclusions and the not-yet-covered list may only shrink; the release closes
when both are empty but for reasoned exclusions.

## Packages

| Package | Needs | Scope in one line | Who |
| --- | --- | --- | --- |
| [DOC1](#doc1-foundation) | 0.12 | Generator, `guide/` layout, `/guide` serving, templates, the writing rules, the `docs` group proven on one page, the AGENTS.md rule | Primary agent. **Delivered 2026-11-02** |
| [DOC2](#doc2-generated-reference) | DOC1 | The generated references and their completeness checks; descriptions written beside the code | Primary agent (mechanism); Codex (descriptions) |
| [DOC3](#doc3-briefs-samples-and-coverage) | DOC1 | The coverage inventory, a brief for every page, the guide's sample data | Primary agent |
| [DOC4](#doc4doc9-the-writing-waves) | DOC2, DOC3 | Wave A: how refiroo works, with the architecture and security overview | Codex |
| [DOC5](#doc4doc9-the-writing-waves) | DOC2, DOC3 | Wave B: run refiroo, and administer access and security | Codex |
| [DOC6](#doc4doc9-the-writing-waves) | DOC4 | Wave C: integrate (management and consumer APIs) | Codex |
| [DOC7](#doc4doc9-the-writing-waves) | DOC4 | Wave D: use refiroo and model your domain | Codex |
| [DOC8](#doc4doc9-the-writing-waves) | DOC4–DOC7 | Wave E: the seven tutorials | Codex |
| [DOC9](#doc4doc9-the-writing-waves) | DOC4–DOC8 | Wave F: start here, about this release, the questions page | Codex |
| [DOC9A](#doc9a-wave-g-ai-integration) | DOC9, 0.16 R | Wave G: 0.16's AI integration, its briefs first, its pages in the sections they belong to | Primary agent (briefs); Codex (pages) |
| [DOC10](#doc10-screenshots) | DOC7, DOC8, DOC9A | Screenshots from the browser runners, light and dark | Primary agent |
| [DOC11](#doc11-fresh-reader-check) | DOC9, DOC9A | Each tutorial completed by a reader from outside; the unrun commands rehearsed on a clean host | The user finds the reader; primary agent records. **The weaker check (a fresh agent, no outside person) is done 2026-11-08 and 2026-11-09, assistant journey included; the outside reader is still open** ([Open for 0.13](#open-for-013)) |
| [DOC12](#doc12-publish) | DOC11 | The public site, versioned; the README points to it | Primary agent. **Delivered 2026-11-08** (README, `docs/PRODUCT.md`, `CODE_OF_CONDUCT.md`, CONTRIBUTING; the versioned site build runs in R) |
| [HD](#hd-one-header-for-the-app-the-documentation-and-the-api-reference) | DOC1 | One header style for the app, the guide and the API reference; logo to the app; Documentation \| API reference switch; "?" help; one theme choice | Primary agent. **Approved 2026-11-03; delivered 2026-11-03** |
| [TH](#th-a-theme-choice-normal-or-website-purple) | HD | A theme choice, Normal or Website purple, beside the light and dark choice, in the app, the guide and the API reference | Primary agent. **Delivered 2026-11-05** |
| [RL](#rl-record-pages-and-related-columns-in-the-model-editor) | DOC1 | Record pages with one panel per relationship by default; Add panel… on a record page; columns showing a field of the related records or where they sit, chosen in the editor | Primary agent. **Delivered 2026-11-05**, guide pages with the wave `guide/_waves/RL.md`. One page rule on the server (`layout.detail_page`, `place_relation`, `place_child`) and in the frontend (`model/defaults.ts`, checked against `stop-page.fixture.json`); `addPanel`; Add panel… and the unfolding Columns dialogs. A panel's Columns… offers `ancestor:<type>` and `objectType`; `ancestor:<type>.<field>` stays a related-column field, since a panel does not accept it |
| [ED](#ed-the-model-editor-sets-everything-a-model-holds) | CP 2a | Every model setting the engine reads gets a control in the model editor; three deletions get their screens | Primary agent. **Delivered 2026-11-07** |
| [MG](#mg-changes-that-need-a-migration-made-in-the-editor) | - | A change to released structure that data holds (an application move, a new parent, a key, a split, a merge, a conversion, a removal) is made in the editor; installing the draft runs the migration the draft itself states, previewed and confirmed. Moved from 1.0 | Primary agent (plan); implementer. **Delivered 2026-11-09** |
| [CP](#cp-completeness-from-the-code) | all waves | Every capability in the code listed mechanically and held against the pages; each one documented to working depth | Primary agent (inventory, check); Codex (pages). **Delivered 2026-11-10** (steps 1, 2, 2a and the depth waves 2026-11-06 to 2026-11-08; the coverage check passes: 911 entries, 902 covered, 9 excluded, 0 uncovered; the waves' notes are classified under CP) |
| [AD](#ad-an-assistant-task-makes-its-own-model-draft) | - | A workbook task's session makes its own model draft; a proposal on a draft it did not make goes back to the session instead of failing the task | Primary agent. **Delivered 2026-11-06** |
| [AT](#at-the-assistant-starts-from-the-engines-reading) | AD | A workbook task's session starts from a draft the engine has already read the workbook into (its inference and one dry run), not from nothing; a draft's dry run reads the draft's own profile | Primary agent (plan); implementer. **Planned and ordered by the user 2026-11-08. Built; tries slower than AP11; the user removed the start, kept the dry-run fix and accepted the timings (2026-11-08)** |
| [DF](#df-findings-of-the-depth-waves) | CP | Workspace-event webhooks from the browser; a deactivated client's secret rotated; an old consumer API contract version served beside the new one; the exit gate matched to how 0.13 was built | Primary agent; Codex (guide pages). **Approved 2026-11-07; delivered 2026-11-08**, guide pages with the wave `guide/_waves/D-DF.md` |
| [RA](#ra-attributes-of-the-relationship-in-consumer-api-related-fields) | - | A consumer API related block's fields can read an attribute of the relationship itself (`relation:<attribute>`), typed, validated and offered in the editor's field picker | Primary agent (plan); implementer. **Ordered by the user 2026-11-09; RA-D1 to RA-D3 decided 2026-11-09; built 2026-11-09** |
| [AW](#aw-an-ai-tasks-progress-line-in-words-not-the-command) | - | An AI task's "Working on it" line says what the session does in words; the session's shell command never reaches the page | Primary agent. **Added to the 0.13 build by the user 2026-11-09; delivered 2026-11-09** |
| [TN](#tn-an-ai-task-named-by-what-it-asks) | - | An AI task given in words gets a short title the assistant writes from the request, shown on the task page, the task lists and the draft it makes, instead of the cut-off request | Primary agent (plan); implementer. **Added to the 0.13 build by the user 2026-11-10; delivered 2026-11-10: the session writes the title (`agent/20`, `ai_tasks.title`), the task page, confirm bar, Jobs group and draft use it, words cut at a word until then; J50.72; try $0.44** |
| [AQ](#aq-the-assistant-loads-a-laid-out-workbook-and-asks-only-what-a-person-decides) | - | A laid-out workbook loads through the assistant without guessed operation names, replayed profiles or questions the engine could answer; the session limit is a handled ending | Primary agent (plan); implementer. **Found 2026-11-08; delivered 2026-11-08** (`f34d2c24`, `dbcc8f28`; the try, task 97, run the same day) |
| [JG](#jg-related-jobs-grouped-on-the-jobs-page) | - | The Jobs page groups the jobs an assistant task or a model draft requested, with a trail back and the group in the address | Primary agent (plan); implementer. **Approved 2026-11-08; delivered 2026-11-08** (`0059d6a4`) |
| [AB](#ab-the-assistant-loads-a-file-as-one-checked-batch) | AQ | The assistant loads a file as one batch the engine has previewed in full; accepting runs exactly those items with no assistant turn | Primary agent (plan); implementer. **Approved 2026-11-09; built 2026-11-09; acceptance runs 2026-11-10, accepted by the user; closed** |
| [NG](#ng-relation-matrices-in-navigation-groups) | - | A relation matrix is an entry of a navigation group of its own, a collection has an opening view, and a group has a panel in the editor | Built by the 0.13 build, not planned beforehand; recorded 2026-11-10. **Delivered 2026-11-09** (`30d29a8d`, guide wave `NAV-GROUPS`). Narrows [0.17 NG1](BASE_0_17_IMPLEMENTATION_PLAN.md#ng1-views-in-navigation-groups) |
| [RV](#rv-attributes-of-the-relationship-in-views) | RA | A relationship's own attributes in a matrix cell, a relationships panel, a relationships table and a relationships grid with a bulk change | Primary agent (plan); implementer. **Approved 2026-11-09; delivered 2026-11-09** (`075675bb`, `a2a672dc`, `f9e82a2f`, `538c4b97`, `d69cb0bd`, `e696076c`); guide pages with the waves `RV-GUIDE` and `RV-GUIDE-FIX` (`0dcb0f0b`, `9a341f83`) |
| [CL](#cl-images-built-in-ci-and-ci-as-a-quick-gate) | - | The engine and web images built once in CI and tagged only after they start; CI on GitHub a quick gate | Primary agent. **Delivered 2026-11-07 to 2026-11-08** (twelve commits, listed under CL) |
| [MS](#ms-mail-through-microsoft-365-graph) | - | Mail sent through Microsoft 365 (Graph, client credentials) as a second method beside SMTP, set on Settings › Mail; extends 0.12's D419 | Primary agent (plan); implementer. **Approved by the user 2026-11-10 (MS-D1 to MS-D5); delivered 2026-11-10 except the real try at the organisation refiroo is deployed for** |
| [FX](#fx-fixes-found-during-the-013-build) | - | Fixes found while building 0.13 that no package names: one row each with where it was found | Primary agent. **Recorded 2026-11-10** |
| R | all | Full review of every change since 0.12, the exit gate, the release | Primary agent |

## Open for 0.13

Written 2026-11-10 after every uncommitted change and every commit since `v0.16.1-alpha.1` was assigned to a package
above. This is the one list of what is still pending; statements elsewhere in this plan that read "open" or "not yet"
either point here or are closed. Nothing else is open.

| # | Item | Evidence | Who acts |
| --- | --- | --- | --- |
| 1 | **Closed 2026-11-10: AB acceptance runs**, accepted by the user ("this is good and accepted, the ab can be closed"). Record under [AB](#ab-the-assistant-loads-a-file-as-one-checked-batch), "Acceptance runs" | the 0.16 usage log, 2026-11-10 rows | - |
| 2 | **Six assistant pictures of the guide are out of date** (`use-assistant-proposal`, `model-assistant-workbook-proposal`, `use-assistant-loaded`, `model-assistant-workbook-loaded`, `use-assistant-words`, `use-assistant-reload`): they show the saved-profile load, "Accept the model" and proposal-file wording | `guide/_coverage/notes/C11-FIX3/report.md`, "Existing pictures that no longer illustrate this flow correctly"; none was retaken (last change `f173c53a`, 2026-11-06) | Primary agent retakes them from a real task, in the same announced runs as item 1 |
| 3 | **The outside reader of DOC11.** The exit gate asks for every tutorial completed by a reader from outside the project; the checks done are the weaker one (a fresh agent with a browser, no person) | DOC11 status; `guide/_coverage/notes/C11-READER2/report.md`, `C11-READER2-AI/report.md`, `C11-HOST/findings.md` | The user accepts the weaker check as the gate or arranges a reader |
| 4 | **Live tries the depth waves could not run.** Statements written from the code and never run on a live system: phone trust of the developer instance, provider sign-in and mail receipt, collector setup, a backup and restore onto a public replacement host, an interrupted upgrade, webhook receiver deliveries, a physical passkey ceremony | the `Open:` lines of `guide/_coverage/notes/D-RUN/depth.md`; the clean-host rehearsal (DOC11, 139 commands) covered install, backup, restore and upgrade on one host only | R's rehearsal, or the outside reader (item 3) |
| 5 | **`test_model_independence` fails** on `frontend/src/features/ai-tasks/designFixture.ts` (the starter model's keys `domain` and `codelist` as literals in a fixture). Run once on 2026-11-10: 1 failed; the file is committed (`a1fbbac9`), so the failure predates this record | `backend/tests/test_model_independence.py::test_runtime_sources_contain_no_starter_model_key_literal` | Primary agent decides the fix (the fixture keys come from the model, or the fixture is outside the test's reach) |
| 6 | **The guide home's title repeats**: "refiroo documentation \| refiroo documentation" (Starlight joins the page and site titles) | `guide/src/content/docs/index.md` (`title`) and `guide/astro.config.mjs` (`title`) are equal; the built `index.html` carries both; website W8, 2026-11-06 | Primary agent (a home title that does not repeat the site title) |
| 7 | **DOC-D26 is undecided**: AI in the reference instance (recommendation 2026-11-02: not now; at DOC9A an optional, off-by-default setup) | [Decisions](#decisions), DOC-D26 | The user |
| 8 | **RV's browser look.** The grid's sticky columns, group tints and floating editors in a wide table at 390 px are not inspected, and no browser runner exists for the relationships table, the grid or the cell dialog | RV, "Still manual / not built" | The user decides whether a runner is wanted; primary agent otherwise looks once in a browser |
| 9 | **MS: mail through Microsoft 365**, delivered 2026-11-10 (secret, certificate, managed identity in both modes); the real try waits for the organisation refiroo is deployed for (managed identity) | [MS](#ms-mail-through-microsoft-365-graph) | Implementer builds; primary agent checks and reports |
| 10 | **Release step R**: the full review of every change since 0.12, the exit gate, the versioned site build (`website/tools/engine.mjs <tag>`) and the release | R row; Exit gate; DOC12 | Primary agent, each heavy run announced one at a time |

Closed by this record, with evidence: `WEB_MAX_BODY` is passed to the web container (`compose.yml`, `web.environment`);
the CP notes (classified under [CP](#cp-completeness-from-the-code)); the DOC11 assistant journey (recorded under
[DOC11](#doc11-fresh-reader-check)).

The waves are ordered by dependence, not by importance: concepts first (the how-tos and tutorials link
to them), the operator and access pages next (they stand alone), then the integrator, steward and model
pages, then the tutorials (which link to the how-tos), then the entry pages (which link to everything).

### DOC1: Foundation

- **The generator.** Chosen by a comparison against these criteria, with the evidence of each checked,
  not recalled: Markdown sources, an offline build, serving from the engine's image, search, versioned
  output, accessible output in light and dark, maintenance activity, permissive licence, and one
  more dependency set or two (the repository already has Python and Node). The comparison and the choice
  are reported to the user; nothing is recommended before it is made ([DOC-D18](#decisions)).
- **Layout.** `guide/` at the top level ([DOC-D3](DOCUMENTATION_PLAN.md#decisions)): the sections above
  as directories, `guide/samples/`, `guide/_briefs/` (one brief per page, not published),
  `guide/_coverage/`, `guide/AGENTS.md`, `guide/tools/`.
- **Serving.** The engine serves the built guide at `/guide`, offline, from the version it runs, with a
  link from `/docs` and from the browser's help entry. It is part of the engine image. The browser
  application's own navigation does not change.
- **Templates and the writing rules.** One template per page kind; `guide/AGENTS.md` holds the style
  guide ([below](#the-writing-rules)) and the process Codex follows.
- **The `docs` group**, proven on one explanation page ("Three kinds of change") whose examples run.
- **Checks**: links and anchors, front matter, a published page is not a stub, banned terms
  (package IDs, decision IDs, private-model names), spelling of the product name, the page template's
  headings present.
- **AGENTS.md** gains the step: a change to user-visible behaviour updates its guide pages in the same
  change, as it updates API.md. The step joins "How a package is delivered" and the definition of done.

**Exit:** one page published at `/guide` inside the running engine and in a static build, its examples
running in the `docs` group, the checks green, and `guide/AGENTS.md` in place.

**Delivered 2026-11-02.** Starlight (Astro), chosen by the user (DOC-D18). What was built:

- **`guide/`**: a Starlight project (own `package.json` with exact versions and a lockfile; `base: /guide`),
  the ten sections as content directories, `samples/`, `_briefs/` (with `templates/`, one per page kind),
  `_coverage/`, `_waves/`, `tools/` and `AGENTS.md`. Only `src/content/docs/` is built into the site. The
  content schema carries the front matter and refuses `status: stub`.
- **Checks** (`guide/tools/check.mjs`, one `npm run` command each, listed in `guide/AGENTS.md`): front matter,
  no published stub, template headings, banned terms (package, decision, journey and capability IDs, delivery
  history, private-model names by hash), the spelling "refiroo", the examples a page shows, and links and
  anchors in the built site. The private-model list is empty until the user supplies the names
  (`node tools/check.mjs hash-term "<name>"` makes the line to add).
- **Serving**: `app/management/guide_site.py` serves the built files at `/guide` with a content security
  policy that keeps every load on the engine; the web image's proxy and the Vite dev server forward `/guide`;
  `/docs` and Settings › About link to it. The built files are found in `/app/guide` (the image) or
  `guide/dist` (a checkout); without a build the engine starts and `/guide` answers a page that says how to
  build it. The engine image builds the guide in its own first stage and carries only the built files.
- **The `docs` group**: `tests/test_guide_examples.py` runs each file in `guide/examples/` (an `api` example
  against the starter model, IDs and times normalised; a `model` example through the engine's validation),
  and a page prints the same file with `<Example id="…" />`, so it shows exactly the tested text.
- **The proof page**: "Three kinds of change" (How refiroo works), `status: written`, with its brief in
  `guide/_briefs/` and four examples (a live correction and a stale save, a change set published, a valid and a
  refused model change).
- **Offline and accessibility**: `node e2e/accessibility-gate.mjs --only guide` serves the page through the
  running engine and records every request (all to the page's own origin) and runs axe on the page and the search
  dialog, light and dark, at 1440px and 390px: no violations.
- AGENTS.md: the guide step is in "Working method" step 7 and the Definition of done (the file has no section
  named "How a package is delivered").
- **Notices**: `scripts/third_party_notices.py` also reads the guide's production closure (`npm ls --omit=dev` in
  `guide/`, sharp's LGPL platform binaries `@img/*` excluded because they only resize the logo at build time) and
  holds it to the same licence gate (BlueOak-1.0.0, CC0-1.0 and Python-2.0 added to the allowed set);
  `THIRD_PARTY_NOTICES.md` is regenerated and `--check` passes. The sitemap is disabled until the public host is
  decided (DOC12).
- The engine image build was not run in DOC1 (no Docker daemon on the machine); since 2026-11-07 CI builds and starts the
  images ([CL](#cl-images-built-in-ci-and-ci-as-a-quick-gate)). The list of private-model names for the banned-terms
  check stays empty by decision (DOC-D25).

### DOC2: Generated reference

The references in the table above, each generated from its source into the guide's reference section,
each with a check that fails on an undescribed entry (a setting without text, an error code without an
entry, a schema field without a description, a command without help text, a permission without a
description). The descriptions live beside the code (a `description` on the setting or schema field, a
docstring, the code's own catalogue entry), so a new entry cannot ship without one
([DOC-D6](DOCUMENTATION_PLAN.md#decisions)). The primary agent builds the generators and the checks and
writes the first entry of each kind as the pattern; Codex then writes the rest in batches, editing only
the description text in files the package lists, and the primary agent reviews each batch's diff. The
error catalogue follows [DOC-D13](#decisions).

These files (`app/config.py`, `models/schema.py`, the error and permission catalogues) are also edited by
0.16's sessions in the same working tree. A description batch therefore runs in a window agreed with the
user when no other session edits its files, and is committed before that window closes, so neither
release's commit carries the other's hunks.

**Exit:** each reference is built into the guide; each check is green with no gap list.

### DOC3: Briefs, samples and coverage

- The coverage inventory and its check (the table above), run once to produce the full list of what the
  guide must cover.
- **A brief for every page** in the inventory, written by the primary agent from the code, the journeys
  and the seeds. This is what makes the pages Codex writes accurate, and it is the largest single piece of
  the primary agent's work in this release. A brief holds:

  | Field | Content |
  | --- | --- |
  | Reader and goal | One sentence: who comes to this page, and what they leave able to do |
  | Kind and template | Which of the four, and the template to use |
  | Prerequisites | The pages the reader must have read, and the state the instance must be in |
  | Sources | The exact files, sections, journeys and routes the facts may come from. The writer uses nothing else |
  | Steps or sections | The outline, in order |
  | Examples | Each example to include: its kind, the request or command, and the expected result, written by the primary agent and run before the writer starts |
  | Must state | The statements the page must make (the points that must be stated clearly, the limits, the settings that change them, and what the reader should do on each error the steps can meet) |
  | Must not | What the page must not claim or describe (planned features, internals, other readers' tasks) |
  | Links | The pages it links to, and the reference entries |
  | Length and form | A bound, and whether a diagram or table is expected |

- **The guide's sample data**: the small files the tutorials and examples load (`guide/samples/`),
  loaded by one documented command so a reader can repeat every example, and a second small model for
  tutorial 2.
- **The wave prompt files** (`guide/_waves/DOC4.md` … `DOC9A.md`), one per wave: its pages and briefs,
  the files it may edit, the checks it runs, and the stop rule (a wrong brief is reported, not filled).
- **0.16's items** are owned by wave G's pages from the start, so the coverage list is complete; their
  briefs are written in DOC9A, after 0.16's R, not here.

**Exit:** the coverage list has an owning page for every item; every brief but wave G's is reviewed by
the user's spot read of the ones they name; every example named in a brief runs.

**Part 1 delivered 2026-11-02** (the briefs are part 2):

- **The reference domain is in the guide** (DOC-D17): `guide/samples/` holds `model.json` (the model
  release `guide-reference-swiss`, without the GTFS system and its codes, whose licence is unverified),
  `fetch.py` and `load.py`, the two dated data sets in `data/` (docs: 598 records, the 116 train stops with
  their 44 municipalities, 10 districts, canton, 3 operators, 15 modes, 5 languages, 231 translations and 170
  codes; reference: 3,528 records, all 2,443 current stops of Graubünden), the fictional workbook and its
  generator, `SOURCES.md` (attribution lines and licences) and `_correspondence/` (the two drafts of the
  e-mail to the publisher, not sent). One command loads either set through the public API:
  `python3 guide/samples/load.py --set docs|reference --base <instance> --env <env file>`. The raw
  download (`snapshot/`) is git-ignored; the repository ships the two derived sets and the script.
  The docs set has 598 records, not the proposal's roughly 480: the Wikidata item numbers of all 114
  stations are loaded (the proposal counted about 60 codes).
- **The reference instance** is `guide/reference/` (`compose.override.yml`, `.env.example`, `reference.sh`);
  project `refiroo-guide-ref`, ports 8480 and 8443, generated secrets in the git-ignored `.env`.
- **The `docs` group seeds the docs set** through the public API (the load script's `load_set`), once, and
  reuses it until the model, the set or the script changes. The proof page's four examples are rerecorded
  on it (a language added and corrected, renamed in a change set; a field added to the reference model, and
  one bound but never defined); the page changed only where the domain's words did.
- **The coverage inventory** (`guide/tools/inventory.py`, `npm run inventory`) writes
  `guide/_coverage/inventory.json`: 30 capabilities, 57 journeys, 63 settings, 337 error codes, 9 commands,
  10 roles, 16 permissions (action groups), 10 event types and 319 model-language fields, 851 items. 12 are
  owned by wave G (J48 to J57, F29, F30). `npm run check:coverage` compares it with the briefs and pages;
  `-- --strict` is the release gate. `exclusions.yaml` holds J09 (retired). Required statements are counted
  from the briefs.

**Part 2 delivered 2026-11-02** (ownership complete, waves A and B briefed; the briefs of waves C to F follow):

- **Ownership.** All 144 pages of the guide exist as stub briefs in `guide/_briefs/<section>/` (stubs are not
  in `src/content/docs/`, which the build keeps free of stubs), each with title, kind, reader, wave, `covers`,
  `must_state` and example kinds. Per section: start-here 8, how-refiroo-works 20, tutorials 7, use-refiroo 25,
  model-your-domain 15, integrate 23, run-refiroo 23, administer-access 11, reference 7, about-this-release 5.
  Per wave: A (DOC4) 20, B (DOC5) 34, C (DOC6) 23, D (DOC7) 40, E (DOC8) 7, F (DOC9) 13, generated reference
  (DOC2) 7. `npm run check:coverage` shows 0 unowned items of 853: 1 excluded (J09), 65 owned by wave G (J48 to
  J57, F29, F30 and the settings, error codes, command, role, permissions and event 0.16 introduced, listed in
  `guide/_coverage/wave-g-items.txt`), the rest owned by a brief. The generated reference pages own the rest of
  their kind through `kind:*` in `covers`. Wave G's pages are not stubbed: DOC9A creates them. The pages the plan
  adds for the workbook canvas (0.17) do not exist yet and have no stub.
- **Freshness.** `test_the_coverage_inventory_is_fresh` (the `docs` group) fails when `inventory.json` differs from
  a fresh generation. It caught two 0.16 error codes added by another session the same day.
- **Briefs for waves A and B** (54, with the eleven fields of the brief table; `npm run check:briefs` checks the
  headings, the statements and the examples they name) and 76 tested examples (72 new), recorded with
  `GUIDE_RECORD=1 pytest -m docs` and run green. Operator shell commands are listed as `unrun` in the briefs.
  Signed cursors are shown as `<cursor>`.
- **Wave prompt files** `guide/_waves/DOC4.md` and `DOC5.md`, validated with `codex-wave.mjs run --dry-run`.
- **Where the code contradicted repository documents** (the briefs follow the code): a webhook batch holds 1 to
  1,000 events (default 1), not 100; no command `model_schema_upgrade` exists (`database_upgrade`,
  `model_release_raise`, `model_release_prune` do); a session ends after 12 hours idle (`SESSION_IDLE_HOURS`),
  not a day; the limits in MB are MiB; the `scoresFrom` of the plan is `scoreOnlyMatching` in a model; the
  ETag is a digest and the contract version, not the data version; a consumer read after a release is refused
  only when the older release declared another contract version; `GET /api/v1/system` does not show the
  settings (`/system/configuration` does); the retired webhook key setting is still named in OPERATIONS; the
  action groups are 14 (plus 2 of 0.16), not 13; the jobs switch also gates imports, source files and model
  mappings; multi-process operation is built, while OPERATIONS says "0.11 work"; `README` and OPERATIONS still
  say the API is unauthenticated. `compose.yml` did not pass `WEB_MAX_BODY` to the web container; it does now
  (`web.environment`, default `256m`), checked 2026-11-10.

### DOC4–DOC9: The writing waves

Each wave is one package. The same steps run for each, so a wave is finished only when all are done:

1. **Codex writes** the wave's pages from their briefs, following `guide/AGENTS.md`, into the wave's
   directories only. Codex writes `status: written` only when the page holds all of its brief.
2. **The checks run**: the `docs` group for the wave's examples, the coverage check for the wave's
   items, links and banned terms, front matter, the template.
3. **The fact-check.** The primary agent (or a fresh agent given only the page, its sources and the code)
   compares every statement of behaviour on the page with the code or the cited source, and lists each
   claim it cannot support, each omission against the brief and each statement the page makes outside the
   brief's sources. The writer corrects the list. Behaviour claims with no example and no source are
   removed, not softened.
4. **The user's read** of the pages the user names (the five points first, the security overview and the
   install tutorial always).
5. The wave is recorded: pages, checks run, claims removed, what remains `unrun`.

Waves are announced and run one at a time; a wave that finds a fact the briefs got wrong stops and
reports it, since the brief is the primary agent's to correct.

### DOC9A: Wave G, AI integration

0.16's capabilities and journeys (J48 onward), described once its release step R has fixed them, so no
page describes a screen or an operation that is still changing (writing rule 9). The primary agent writes
the briefs and their examples as in DOC3, then the wave runs the five steps above. The pages go where the
reader looks for them, not into a separate AI section: the steward's work with the assistant under Use
refiroo, model changes and their accounts under Model your domain, assistant and agent access under
Integrate, the AI provider and its usage under Run refiroo, the AI permissions under Administer. Pages
written in earlier waves that 0.16 changed are corrected in this wave, listed in its prompt file.

### DOC10: Screenshots

The browser runners produce the guide's screenshots from the sample data, light and dark, at the
standard width and at 390 px where a page speaks of a narrow screen. The guide references them by name;
a command regenerates them, so 0.14 (palettes) and 0.15 (interface language) refresh them cheaply.
Pages carry text alternatives written by the writer; the check refuses a screenshot without one.

The website's feature pages show eight of the guide's screens in light and dark (website W5, approved by the user
2026-11-05), so the tool has one more option: `guide/tools/screens.mjs --scheme dark` sets the browser's colour scheme and
the application's own Appearance setting (`rdm:theme:v1`) to dark and writes `<name>-dark.png` beside the light file; without
the flag nothing changes. The dark files exist for `model-editor-overview`, `change-set-review`, `mapping-grid-codes-to-stops`,
`names-matrix`, `admin-api-reference`, `list-display-panel`, `use-assistant-workbook` and `model-assistant-change-dialog`;
`list-display-panel` has a spec (PILOT) now. The website's `tools/engine.mjs` copies them into its build.

### DOC11: Fresh-reader check

A person who has not used refiroo completes each tutorial and tries the quick start and the production
checklist; where they get stuck is recorded and fixed ([DOC-D8](DOCUMENTATION_PLAN.md#decisions)). The
`unrun` shell commands are rehearsed once on a clean host in the same pass. If no such reader is
available, a fresh agent session given only the built guide (no repository) does it, and that is
recorded as the weaker check.

**Status:** The first weaker run (waves C11-READER and C11-FIX, 2026-11-06) read every journey but could do
none of it: Codex's sandbox had no network to the reference instance and no browser, and no command was
rehearsed. Pages changed since (CP, ED, RL, DF, AT). **Planned again and approved by the user 2026-11-08**:

1. **Tool.** `guide/tools/codex-wave.mjs` gets `--network` (network access in Codex's sandbox) and `--browser`
   (a Playwright Chromium started outside the sandbox for the turn, driven by Codex through its endpoint;
   a browser cannot start inside the macOS sandbox, probed 2026-11-08). Both off unless named. Implementer.
2. **Reader run** (wave `C11-READER2`, Codex): the quick start, every journey but the assistant one, and the
   production checklist, each step done on the reference instance rebuilt from the current code; writes only
   in workspaces it makes; no host commands, no AI. The assistant journey follows in `C11-READER2-AI` once AT
   is delivered.
3. **Clean-host rehearsal** (implementer): a fresh copy of the checkout, its own Compose project, job directory
   and ports; the run pages' commands word for word (install, administrator, backup, restore, upgrade from
   the last release, v0.16.0); each command recorded as ran, worked or differs; removed afterwards. Steps needing a public DNS name
   are read only.
4. **Fix wave** (`C11-FIX2`, Codex) on the findings of 2 and 3; product defects fixed by the implementer with
   their CHANGELOG entry and guide text.
5. **Record:** this status, the CHANGELOG, `npm run verify`.

Still the weaker check (no outside person), now done rather than read.

**Clean-host rehearsal done 2026-11-08** (`guide/_coverage/notes/C11-HOST/findings.md`): 139 commands run on 15
pages, 128 as the page says, 11 differ, 24 not run with reasons. Product findings: the tag `v0.16.0` cannot be built
(its `backend/Dockerfile` ends with two stray `ENV` lines after `CMD`; `v0.16.1-alpha.1` builds). The tag predates the
images workflow (2026-11-07), which now builds and starts the images for every `v*` tag, so R's tag is checked (the pages
name no particular release, only `v<version>`). `generate_key --help` and `database_upgrade --help` did the work, and `create_admin` without a
terminal failed with a traceback: fixed in the command-line tools. The rest go to the fix wave.

**Reader run and fix wave done 2026-11-08.** The reader (`guide/_coverage/notes/C11-READER2/report.md`) did the quick
start, every journey but the assistant one and the production checklist's outside checks in a browser and with real
requests on the reference instance, every path the journeys name. Ten findings: two were the instance's setup (stale
accounts); seven product defects were fixed with tests and browser checks (an empty hierarchy has no first-root Add,
a follower notice opens nothing, a retired workspace's band said edits apply, a supplier profile saved and listed
against the default workspace's model, "Update them anyway" still refused rows changed since the export, Preview again
after a partly refused deletion kept the old version, a draft conflict named a rename by its new name); one was a
label in the page. Two paths could not be set up on this installation and the pages now say what they need: the
Conflict state of a matrix (needs already-inconsistent data) and raising an older model language (needs an older
release stored before an upgrade). The fix wave (`guide/_coverage/notes/C11-FIX2/report.md`) brought the pages in line
with all 23 findings; the model editor's "migration (planned for 1.0)" sentence was corrected to name the JSON view and
the install review; the three tree pictures were taken again. `reference.sh update` now rebuilds the web image too.
**The assistant journey done 2026-11-09** (wave `C11-READER2-AI`, then the fix wave `C11-FIX3`). AT and AB were
delivered, so the reader ran the journey in a browser on the reference instance (`reader-ai`, an isolated workspace)
with a real provider: the provider check and data disclosure, a workbook load to publication with its design review,
correction, review and discard, a words task with Stop and Go on as it was, a model-only change, a whole-type move, a
partial type move through its three steps, asking a list and explaining a period, proposed mapping targets, an outside
system assistant (read, prepare, review, publish, deactivate) and a personal assistant (discovery, registration,
consent, exchange, refresh, sign-out, block), and stopping AI as a person. Fifteen findings
(`guide/_coverage/notes/C11-READER2-AI/findings.md`, `report.md`). Product defects fixed by the implementer, with tests and
their CHANGELOG entries (0.13 DOC11, assistant journey): the person's Stop in a container, a message that asks for a
correlation ID, a failed assistant job reaching its task, a failed correction leaving a change set behind, the checked
relationship count that left out parent links, a records-only words task named for what it is, a no-change proposal
claiming a workbook fits, internal words in the model summary and the closing note, Go on as it was after an early
Stop, a partial move described as manual work, its final release found without the session's last line, and the top
Accept button. Findings 7, 12, 13 and 14 were retested and cleared (12 was the reader's own setup: no listener at the
return address). The fix wave `C11-FIX3` brought twelve guide pages in line with the findings, source-checked, and
named six pictures that no longer illustrate the flow (open item 2). Left, as recorded: the saved-layout path could not
be exercised (the profile available needed seven binding fixes, no assistant-created profile existed), contingent states
(questions, refusals, mappings changed meanwhile, permission loss, expiry) were not manufactured, host switches were not
run, and no independent recount of the partial move was made. The reader's calls cost about $2.07 reported. This is still
the weaker check: there was no outside person, and the exit gate's outside reader is [open item 3](#open-for-013).

### DOC12: Publish

**Status:** Delivered 2026-11-08: `CODE_OF_CONDUCT.md`, the README's Status brought up to Base 0.16, and refiroo.org/docs linked from the README and `docs/PRODUCT.md`; the versioned site build is run by the release step R.

A public static build of the same sources, versioned per release ([DOC-D7](DOCUMENTATION_PLAN.md#decisions)),
with search and the light and dark themes; the README and the repository's `docs/PRODUCT.md` point to it.
Where the site is hosted is the user's decision when this package is reached; the build produces plain
static files that any host serves.

The public site is refiroo.org/docs (website W4, approved by the user 2026-11-05): the website's
`tools/engine.mjs <release tag>` builds the guide with `npm run build:public` and copies it under `/docs` (the latest) and
`/docs/<minor>/` (the one before, DOC-D7). Five build settings of the public build only (an instance's guide does not
change), made in W4:

- **E1 Canonical and sitemap.** `PUBLIC_GUIDE_SITE_URL` sets Astro's `site`: every page names its address as canonical, and
  the sitemap (disabled before) is written.
- **E2 Base path.** `PUBLIC_GUIDE_BASE` sets `base` (default `/docs`; `/docs/<minor>` for the version before the latest).
  The static API page and its script follow it.
- **E3 The way back and the version.** The logo leads to the site's home (`/`, W4-D5); `PUBLIC_GUIDE_VERSION` shows a
  version mark after the Documentation | API reference pair; `PUBLIC_GUIDE_OLDER=1` adds "Guide for 0.13 · Latest version"
  (a link to `/docs/`) to every page, the API page included (`src/components/Banner.astro`).
- **E4 The flight.** `src/styles/public-site.css` (public build only) and the API page: under `prefers-reduced-motion:
  no-preference`, `@view-transition { navigation: auto; }`, the header mascot named `mascot`, the guide's content `page`
  and the API page's content `terminal` (the names of the website's `base.css`).
- **E5 A host's theme (the user, 2026-11-05).** `PUBLIC_GUIDE_THEME=<absolute directory>` lets any host of the public guide
  give it its own header and look: the directory's `Header.astro` replaces the guide's header component and its `theme.css`
  loads after the guide's styles; its `api/` folder (`head.html`, `header.html`, `theme/`, with `/__BASE__` and `__VERSION__`
  filled in by the build) gives the static API page the same header in place of HD's, with the Content-Security-Policy hashing
  its inline scripts and Scalar leaving room for `--rdm-header-h`. Unset, the guide and the API page are as before. The website
  supplies one (`guide-theme/`, built from the site's own nav component), so refiroo.org/docs has the site's header, colours and
  fonts; the guide's content is written once.

The release step R runs the website's script at the release tag; the tag is the guide's version.

Pending (website W8, 2026-11-06): the guide home's title reads "refiroo documentation | refiroo documentation" (Starlight joins the page title and the site title); the home page's title in `guide/` should be set so it does not repeat. Still true 2026-11-10 ([open item 6](#open-for-013)).

Also in DOC12, for the website's Community page (website W3-D7, approved 2026-11-04): `CODE_OF_CONDUCT.md` at the
repository root, the Contributor Covenant 2.1 (CC BY 4.0) with krisztian.toth@refiroo.org as its reporting contact, and CONTRIBUTING.md's last sentence ("A separate code of conduct
will be added when contributions open") replaced by a link to it. The README's Status section is brought up to Base
0.16 in the same change (it still describes Base 0.9).

## HD: One header for the app, the documentation and the API reference

**Status:** Delivered 2026-11-03. Proposed 2026-11-03 at the user's request; plan and mock-up approved by the user on 2026-11-03, placed in 0.13 because it concerns the guide. Mock-up:
[`prototypes/shared-header/index.html`](../prototypes/shared-header/index.html). Help opens in a new tab (the
user, 2026-11-03).

**Why.** The app (`TopBar.tsx`), the guide (Starlight's default header) and the API reference (the header in
`management/reference/__init__.py`, `_PAGE`) look like three products. Each keeps its own theme: the app saves
`rdm:theme:v1`, Starlight saves `starlight-theme`, and the API page follows only the operating system, while Scalar
offers its own toggle. The guide's logo goes to the guide's home, and the app has no way into the guide except
the About page.

**What changes.**

- **One look.** All three bars are 56 px high and share the app's top surface, border, logo (mascot and wordmark)
  and the ink underline on the current item. That shared part is one stylesheet in `frontend/public/operator/`,
  which the engine already serves at `/operator/`. The guide's `customCss` and the API page both use it, so the
  look is defined once. The app's bar stays the React component and keys on the same tokens.
- **The logo goes to the app's home** (`/`) from the guide and the API page.
- **Documentation | API reference** comes before the search box in the guide's header (a Starlight `Header`
  override), and the same pair is in the API page's header. The current one is underlined. The API page has no
  search box, because Pagefind indexes only the guide.
- **"?" in the app bar,** left of the bell, opens `/docs/` in a new tab (`target="_blank"`,
  `rel="noopener"`), on every page and at phone width.
- **One theme choice.** The guide's `ThemeProvider` and `ThemeSelect` overrides and the API page read and write
  `rdm:theme:v1`, in the app's format (JSON `"system"`, `"light"` or `"dark"`) and with its labels (System,
  Light, Dark). Each page applies the theme before first paint. The API page hides Scalar's toggle
  (`hideDarkModeToggle`) and sets Scalar's mode from the choice. All three follow the `storage` event, so an
  open app tab changes when the theme is picked in the guide.
- **Phone width.** The wordmark is dropped, the pair reads Docs | API, and search and the theme picker stay
  where Starlight puts them on a phone.
- **The public site** (DOC12) is built from the same sources without an app. A build setting turns the logo's
  link into the site's home page (`/`; first the guide's home, changed by W4-D5, approved by the user 2026-11-05: a reader who arrives in the guide has no other way back to refiroo.org); the "API reference" link stays in both builds (the user, 2026-11-03: the public site has the API reference); everything else stays the same. HD's look is the application's and the instance guide's: a public build may take a host's theme instead (DOC12, E5, the user 2026-11-05), the site's own header, colours and fonts on refiroo.org.
- **The public site's API reference** (decided by the user 2026-11-03, the recommendation: built now, with the
  example consumer API). The public build writes a static `/docs/api/` page with the engine's own
  `render_page`, never a second page template. Its sources are static OpenAPI files the build writes beside it:
  the management API (the engine's OpenAPI document, produced from the code without a database) and the
  `stops` consumer API of the guide's reference domain (`consumer_openapi` over `guide/samples/model.json`),
  titled as the example domain's API. Scalar is the engine's bundled copy, so the page loads nothing from
  outside. There is no instance behind it: the sign-in script is left out and the page is for reading, not
  for sending requests. A static host sends no headers, so the page carries its Content-Security-Policy in a
  `<meta>` element.

**Planning defaults.** The guide and the API page show the refiroo mark alone, never an instance's own name
(the app shows it beside the mark): the guide is static and does not know the instance. The API page's inline
scripts stay listed by hash in its Content-Security-Policy; `page_headers` already computes the hashes from the
page.

**Tests (targeted).** The API page test (`test_api_reference.py`): the header's links, the hidden Scalar toggle,
and the policy still covering every inline script. A unit test for the app bar's help link. One browser check
through the dev server: pick Dark in the guide, then the API page and an open app tab are dark; the logo leads to
the app; the switch marks the current page. The guide build and the frontend production build pass, and the
accessibility gate covers the three headers.

**Said plainly:** nothing changes in what the guide or the API reference contain. The help link opens the guide's
home, not the page that matches the screen; that would be a later change.

## TH: A theme choice, Normal or Website purple

**Status:** Approved by the user 2026-11-05 with the mock-up `prototypes/purple-theme/` ("it seems good"), and the
shape set by the user the same day: a theme selector in Settings › Appearance, **Normal** or **Website purple**;
the light and dark selector stays as it is, and picks the light or dark of the chosen theme. Placed in 0.13 by the
user. **Delivered 2026-11-05.**

**Delivered.** `frontend/src/lib/scheme.ts` (the store, `rdm:scheme:v1`, `data-scheme`, `theme-color`, the storage
event), the first-paint script in `frontend/index.html`, `tokens.css` (the `--wp-*` primitives, the purple light
block and the two identical dark blocks, before the palette A blocks so A applies inside both), the Theme selector in
`AppearancePage.tsx`, `refiroo-header.css` (header and Scalar values; the dark wordmark rules already match purple
dark, since they key on the mode only; the engine's copy under `backend/app/management/operator/` kept equal), the
API page's theme script (`reference/__init__.py`; left out of a host-themed static page), `ThemeProvider.astro` and
`ThemeSelect.astro` (not applied when `PUBLIC_GUIDE_SITE` and `PUBLIC_GUIDE_THEME` are both set) and `guide.css`.
Two groups on Appearance are now both labelled "Theme" (the colours first, then the existing light and dark one),
as the labels were set; the second's help text and the first's tell them apart. The hue bands and the proposed
line are not set by the purple blocks: they come from the same rules as Normal's (bands mixed from the fills), so
palette A's bands follow its fills in purple too.

**Why.** The website's look (periwinkle, mint, navy, cream, coral; `website/src/styles/tokens.css`) is liked; the
app offers it as a theme of its own. Normal is today's look, unchanged.

**What changes.**

- **Two independent choices,** as the type palettes A and B already are (U-D13): the mode (System, Light, Dark;
  `rdm:theme:v1`, `data-theme`, unchanged) and the theme (Normal, Website purple; a new key `rdm:scheme:v1`, JSON
  `"normal"` or `"purple"`, default Normal, on the document element as `data-scheme="purple"`; Normal sets no
  attribute). Four looks: Normal light, Normal dark, Website purple light, Website purple dark. System still follows
  the operating system for light or dark, in the chosen theme.
- **The tokens.** `frontend/src/styles/tokens.css` keeps its layers. Website purple adds a primitive ramp from the
  site's colours and two semantic-role blocks, light (`:root[data-scheme="purple"]`) and dark
  (`[data-scheme="purple"][data-theme="dark"]` and the system-dark media block, kept identical as the dark blocks
  are today), taken from the mock-up's `purple-light.css` and `purple-dark.css` with the contrast adjustments they
  record. Each sets every role the Normal blocks set. Type palettes A and B apply inside both themes. The dark
  wordmark rules (`layout.css`, `refiroo-header.css`) cover purple dark.
- **The choice in the interface.** Settings › Appearance gets a **Theme** selector (Normal, Website purple) beside
  the existing light and dark selector; the first-paint script in `index.html` applies both; `theme-color` follows.
  The account popover keeps its light and dark choice as it is.
- **The guide and the API reference an instance serves** (HD's one theme choice) read and follow `rdm:scheme:v1`
  too: the shared header stylesheet (`frontend/public/operator/refiroo-header.css`), `guide.css` (Starlight's
  variables) and the API page (Scalar coloured by the stylesheet) get the purple light and dark values; all follow
  the `storage` event as they do for the mode.
- **The published guide on the website** keeps the site's own look (W4); it ignores `rdm:scheme:v1`.

**Tests (targeted).** `tokens.test.ts`: the purple blocks set the same roles as the Normal blocks, its two dark
blocks are identical, contrast for the purple pairs. The theme store's unit test (scheme values, unknown falls back
to Normal). The API page test (the scheme script). One browser check through the dev server: pick Website purple and
Dark in the app; the guide and the API page follow; an open app tab follows. The frontend production build and the
guide build pass; the accessibility gate runs in Website purple light and dark.

**Said plainly:** DOC10's screenshots stay in Normal light and dark; Website purple is not photographed for the guide.

## RL: Record pages and related columns in the model editor

**Status:** Proposed 2026-11-05 at the user's request, placed in 0.13 by the user the same day. Mock-up: [`prototypes/record-layout-editor/index.html`](../prototypes/record-layout-editor/index.html).
Plan and mock-up approved by the user on 2026-11-05 ("its cool"), with delivery in this session.
**Delivered 2026-11-05** (code, tests, API.md, CHANGELOG; the guide pages follow with the DOC1 wave `guide/_waves/RL.md`). Differences from the text below: a panel's Columns… offers `ancestor:<type>` and `objectType`, not `ancestor:<type>.<field>`, because a panel's columns refuse that form (it is a related-column field, offered in the table's Columns); the ancestor column is the related type's direct parent type when all related types share one (a hierarchy of one type adds none); the checkbox list gained grouped and unfolding options (`ChoiceOption.group`, `under`) in the one `OperationDialog`. Older tests that expected the old generated page (`test_j33_layout`, `test_j33_operations`, `ObjectDetail.test`) follow the rule.

**Why.** A model whose pages were written by hand (one panel per relationship, with the related records' own
fields and where they sit: operator, system, language) gives rich record pages; the same data on a model without
written pages gives a bare one. The editor cannot build the rich one, so only JSON or the assistant can, and a
model administrator cannot be asked to open JSON. Found in the code (2026-11-05):

- **The page a type gets lumps every relationship into one panel.** The server's `detail_page`
  (`backend/app/engine/model/authoring/layout.py:79`) writes one relations panel for all outgoing relations;
  `place_relation` (`layout.py:164`) adds each newly allowed relation to that panel; the page shown when an
  application declares none (`frontend/src/model/defaults.ts`) lists every relationship, both directions, in one
  "Relationships" panel with name and type only. Incoming relationships (the system codes mapped to a record, the
  records offered at a place) have no panel of their own in the server's page.
- **A record page cannot gain a panel in the editor.** Edit layout › Record page moves, renames, hides and
  removes panels, groups attribute fields and sets a panel's columns; there is no way to add a relations or
  children panel. The server already inserts one (`insertViewItem` on a page's `panels`, API.md § Draft
  operations); the editor has no form for it.
- **Columns cannot show a field of the related records or where they sit.** The table Columns dialog offers
  each relationship as `related:<key>` only (`relatedChoices`, `frontend/src/features/model-editor/layout.ts:357`),
  though the model accepts `related:<key>.<field>` and `related:<key>.ancestor:<type>.<field>` (Base 0.9 K5a;
  "Has translation · Language code"). A panel's Columns… offers the related type's attributes only
  (`columnChoices`, `layout.ts:154`), though panels accept `ancestor:<type>` columns ("System", "Language").

**What changes.**

1. **One rule for the page a type gets,** used by the server's `detail_page`, by `place_relation` and
   `place_child`, and by the frontend's undeclared page, so the three never differ (the frontend's copy is
   checked against the server's on a shared fixture):
   - **Side:** the attributes panel ("Details") and, when the type has a parent, the hierarchy.
   - **Main:** the contained types (one children panel, as now), then **one relations panel per relationship
     the type holds, in each direction** (containment excluded), in the model's order. Its title is the
     relationship's name read from this type (`name` outgoing, `reverseName` incoming); its columns are `name`,
     an `ancestor:<type>` column when the related records sit under a parent type, then the related type's
     attributes in their order up to four, and `objectType` when the panel lists more than one type;
     `showRelationshipColumn: false`; sorted by the ancestor column where there is one.
   - `place_relation` gives a newly allowed relationship its own panel on the pages of both its types, and a
     `related:<key>` column and filter on both types' table views; removing the binding takes them away again
     (undo restores them). Pages written by hand or by the assistant are never rewritten: the rule applies to a
     new page, a new relationship and the undeclared page.
2. **Add panel… on a record page.** Edit layout › Record page gets **Add panel…** beside **New field group**. It
   asks what the panel shows: **Related records** (one of the type's relationships, both directions, named as
   read from the type; ones already on the page are marked so), **Contained records** (the contained types), or
   **Fields** (today's field group). Region, Main or Side, and a title filled from the choice. The server builds
   the panel with the rule above: a new draft operation `addPanel` (`applicationKey`, `detail`, `show`:
   `relations` with `relation` and `direction`, or `children` with `objectTypeKeys`; `region`; `title`), undone by
   `removeViewItem`, so every client gets the same panel (ADR-041). Its columns are changed afterwards with the
   panel's **Columns…**.
3. **Fields of related records in the Columns dialogs.**
   - **Table Columns:** each relationship row unfolds into the fields of its related records, the name and the
     attributes of the types at the other end, and **where they sit**: each ancestor type's name and attributes
     (Has translation ▸ Language › Language code; Mapped from system code ▸ System › System code). A checked
     field is the column `related:<key>.<field>`, headed "Has translation · Language code". The helpers already
     exist (`relatedTargetTypes`, `relatedAncestorTypes` and `relatedFieldLabel` in `frontend/src/model/lookup.ts`).
     **Filters** keep offering the relationship itself, since a filter on a field is refused (K6).
   - **A panel's Columns…:** besides the related type's attributes, **where it sits**: `ancestor:<type>` and
     `ancestor:<type>.<field>` for each type the listed records can sit under, and **Type** (`objectType`) when
     the panel lists several types.

**Planning defaults.** Four attribute columns at most in a generated panel (more are one Columns… away). The
undeclared page keeps no declaration, so a model that writes none gets the rule without a migration. No schema
change: every field the editor writes is already in the model language. The guide pages
`guide/model/edit-a-record-page.md`, `guide/model/choose-table-columns-filters-and-sort.md` and the concept page
`model/record-pages-and-tables.md` are rewritten by Codex after delivery (one wave prompt, DOC-D15), and their
screenshots retaken.

**Tests (targeted).** Backend authoring group: `detail_page` on the guide's example model (stop: one panel per
relationship in each direction, titles, ancestor columns), `place_relation` adding and its undo removing,
`addPanel` for both kinds with its refusals (unknown relationship, a type the application does not list, an
existing panel key). Frontend: `layout.test.ts` for the unfolded column choices and the panel choices, and the
undeclared page against the shared fixture. One browser journey through the dev server, as a model
administrator in a draft: on the example model's stop, **Declare its page**, **Add panel…** for "Mapped from
system code" with the System column, then the Stops table's Columns › Has translation › Language › Language code;
apply to a scratch workspace and read the record page and the table with real records. The frontend production
build passes.

**Said plainly:** pages already declared stay as they are; a model that wants the new panels on an existing page
adds them with **Add panel…**. A relationship's own attributes (stored on the link) still cannot be columns;
that is a model-language change outside RL.

## AD: An assistant task makes its own model draft

**Status:** Found 2026-11-06 from a failed task (a workbook task whose words asked to update one mapping and change no model); placed in 0.13 by the user the same day; **delivered 2026-11-06**.

**Why.** The session needs a draft (a workbook task always does) and the prompt said only "build the model in a model draft", not how. The session opened the workspace's own draft (`POST /workspaces/{key}/model/draft`, 0.16 WM1), which answers with the draft the workspace remembers: one a person had been editing. It checked it, proposed it, and the engine failed the task with "proposed a draft it did not create; try again". The ownership rule is right (R-F3: a task names only drafts its own client made, so discarding a task never deletes a person's draft), but the failure ended the task, and "try again" could not help: every retry got the same draft.

**What changes.**

1. **The prompt (`agent/10`)** tells the session to make its own draft with `POST /model-drafts` (the release the workspace runs as base, from `GET /workspaces/{key}/model`), never to open the workspace's draft, never to use or change a draft it did not make, and to keep using its own on a later turn.
2. **A proposal naming a draft the task's client did not create goes back to the session** with a plain finding (make your own draft and write the proposal again), through the same rounds as the consumer-contract and records findings (`LANDING_ROUNDS`). Only when the rounds are spent does the task fail, with a note in the person's terms that says trying again with the same draft cannot help.

**Decisions (recommended, recorded).**

- **A draft another task holds** keeps failing at once. Clients are one per task, so a draft its own client made cannot be held by another task except by a defect; sending it back would hide one.
- **Refusing a task session's token on `POST /workspaces/{key}/model/draft`** is not done: a refusal by client kind would be a second rule beside the ownership check, which already catches the effect, and it would reach into the model-draft API for one client kind. The prompt and the send-back carry the fix. If a session still opens the workspace's draft, the draft is remembered by the workspace as a side effect; that stays open.

**Tests.** J50.30: a proposal on a person's draft goes back to the session twice and then fails with the new note, the draft untouched; a session that makes its own draft on the second turn lands at `checked`.

**A second point (found 2026-11-06 on the same task, after the person accepted it).** The session loaded the workbook into its change set and named it, and the task still ended `failed` with no note. `accepted()` judged a load by its records only (`_counts` read `change_set_objects`); a load that only adds relationships holds no record, so it read as empty. Two changes:

1. **`_counts` counts the change set's relationships too**, in SQL: new, changed and removed relationships (`relationsCreated`, `relationsUpdated`, `relationsRemoved`) and removed records (`deleted`) beside the existing figures. `applied` keeps its meaning (new and changed records). A change set that holds any of them is a load. The task page's sentence names the relationships ("231 relationships new").
2. **A task never fails without a reason.** Every failure in `accepted()` that had none now has a note in the person's terms: no change set of the task's own named, another workspace, or nothing in it to add, change or remove.

**Test.** J50.41: a session that only links existing records lands `loaded` with `relationsCreated` counted; one whose change set holds nothing fails with the note.

**A third point (found 2026-11-06, approved by the user the same day: "yes you can fix this").** A person never lands on a task page with no way forward. The task that hit the counting bug above stood `failed` with its session's change set (231 relationships) unreachable: the page said "Nothing was installed or loaded", and Try again or Tell would have loaded into a second change set and orphaned the first. Four changes:

1. **A failed load that left work behind keeps it reachable.** When a load fails but the change set the session named, which the task's own client made, is in the task's workspace and holds changes, `accepted()` records it on the task (`result.changeSetId`, `changeSetName`, `counts`, the existing result fields) while the state stays `failed` with its reason. The landing checks are one function (`_landing`) for the load and for the re-read below.
2. **The failed page shows it.** `TaskEnd` says why, then "It loaded <what> into "<name>" before it stopped. Live data is unchanged.", with **Review the change set** (the route the loaded view uses), the Tell box and **Discard the task and its change set** (confirmed, as on the loaded view). Never "Nothing was installed or loaded" when something was. The journey bar's sentence for such a task says the same.
3. **Retry and Tell discard that change set first** (`_go_on`), and **Discard** of the failed task discards it with the task (`discard`), so there are never two.
4. **A failed load is re-evaluated when the task is read** (`sync` calls `agent.recover_load`): for a failed task at the load stage whose session has not ended, the most recent open change set the task's client made in its workspace is judged by the rules of the day. If it passes the landing checks the task lands `loaded` with the result `accepted()` would build (the failure warnings dropped); otherwise the change set is attached as in point 1. Idempotent; a kept change set published or discarded elsewhere is dropped from the task. The words the session ended with are kept (`design.loadWords`) so a final-release line is honoured. This recovers the task above without a database edit.

**Test.** J50.41: a load that fails after the session wrote a change set shows it on the task and a retry discards it; a failed task re-read under the current rules lands `loaded`. `AiTaskPage.test.tsx`: the failed page with a change set.

## AT: The assistant starts from the engine's reading

**Status:** An open product finding of the guide pictures (`guide/_waves/HANDOVER.md`, "the assistant is far over the import time limit"); 0.16 AP11 closed it unmet, accepted by the user on 2026-11-01. Planned in 0.13 and ordered for delivery by the user on 2026-11-08 ("plan a package in 0.13 and implement it").

**Requirement served.** "A few words + workbook → the model and the import", within 1 to 2 minutes for a workbook like Timetables and 5 at most for a complex one (0.16 plan, AP11). Lower effort and a smaller model stay ruled out (the user, 2026-11-01).

**Where the time goes (read 2026-11-08 from what is still stored; no new AI run).**

- **AP11's tries** (0.16 plan, AP11): Timetables 821 s proposal + 66 s load, its first model written at 334 s, then 14 dry runs to 789 s. Tariff File 384 + 66 s. The engine's jobs took 26 s of the Timetables proposal; the rest is the model generating, at about 125 output tokens a second.
- **The 14 dry runs of `ap11-mot`** (`jobs.report`, kept after the files expired): the session added the workbook one source at a time and learned the binding rules from the refusals. Round 1: `NAME_REQUIRED` on every row; rounds 2 and 3: `PARENT_WRONG_SCOPE`, `REFERENCE_NOT_FOUND` (master values not yet a source); round 4: `RELATION_CANDIDATE_REFUSED`; rounds 7 to 10: new system-value and system-group sources, `REFERENCE_NOT_FOUND` and `PARENT_REQUIRED`; round 12: the translations, `MISSING_REQUIRED_RELATIONS` on 1,619 rows. Each round is a full turn: the profile sent again (123 KB of profile over the task's jobs), the answer read, the next change thought out.
- **The session logs still on disk** (`var/job-files/agent`): about half of the output is thinking (task 89: 20,175 of 38,864 output tokens), and a session spends its first 10 to 15 turns reading the workbook and the model with small scripts before it writes anything.
- **The engine already reads a workbook into a model and a profile** (0.10 A6, `POST /model-drafts/{id}/inference`), and no session uses it. Run on the two AP11 workbooks with an empty model (a scratch probe, 2026-11-08): profiling, inference and application under 2 s, the draft compiles and its profile is valid. **Timetables:** 9 types (timetable, its category, flags, duration, reserved slot code and name, other diary, language, translation) and 8 relations; the draft's dry run reads all 1,743 rows in 3 s, 1 rejected (`MISSING_RECORD_KEY`): 14 categories, 200 timetables with 812 relationships, the 1,500 translations as relationships. **Tariff File:** the Packages sheet only, 200 rows, 0 rejected; the Products sheet (400 rows, a header of two rows) is not read.
- **Found on the way:** the profile `GET /model-drafts/{id}/profile` answers is refused by the draft's own dry run (`422`: the profile's `key` and `name`, each source's `id`). A session that reads the draft's profile and sends it back hits that wall.

**What changes.**

1. **The engine prepares the start.** Before the first turn of a workbook task that goes to a session (not the saved-layout path, which needs no session), the engine, as the task's client: makes the task's draft (`POST /model-drafts` semantics: the workspace's running model, its release as base, named after the task); gives it the task's workbook as its source file and profiles it; runs the inference, `extend` when the workspace holds records and `newApplication` when it holds none (the same rule as `_starting_point`); applies every proposal; and runs one dry run of the draft's profile over every row. Each step is the existing capability, called in-process; the draft is the task's own (its client made it), so AD's ownership rules hold unchanged. If any step fails or proposes nothing, the session starts as today and the prompt names no start; the reason is logged, not shown.
2. **The prompt (`agent/11`)** replaces AD's "make your own draft" with one fact when the start exists: the draft's id is the session's own, the engine read the workbook into it (its model and the profile `GET /model-drafts/{id}/profile` answers), and its dry run's figures (rows read, rejected by code). The words still go first (`_WORDS` unchanged): the start is the file's shape, not the person's request. Without a start the prompt is `agent/10`'s.
3. **A draft's dry run reads the draft's own profile.** `profile` in `POST /model-drafts/{id}/dry-run` becomes optional; without it the dry run reads with the profile `GET /model-drafts/{id}/profile` answers. With it, the profile that GET answers is accepted unchanged: the read-only `key`, `name` and source `id` are ignored, not refused. So a session changes a profile by editing what it read, and checks a draft whose profile it has not changed without sending it.
4. **Nothing else.** No engine change to imports or their limits, to the model the session runs, or to its effort.

**Decisions (my recommendations, recorded under the user's order to deliver).**

- **AT-D1: The engine makes the draft, not the session.** Telling the session to call the inference itself would cost a turn per step and leave it the choice; the engine doing it in-process costs under 2 s and never a turn. Cost: AD's prompt sentence changes when a start exists.
- **AT-D2: Every proposal is applied.** The session changes what the words ask; a person's review comes after the session, as today. Cost: a start with types the words do not want, which the session removes.
- **AT-D3: The start is not reported to the person.** It is the session's material; the proposal the person reviews is the session's, as today.

**Expected effect (my estimate, not measured).** The reading turns and the first model (334 s of AP11's Timetables run) shrink to reading the start; the early rounds of refusals go, as the start's profile already reads every row. The Timetables words ask for much the inference does not build (stations and drivers, a CRM system with external IDs, a filtered field, translations by language), so the 120 s limit is not expected; Tariff File's Products sheet is still the session's work. The tries measure it.

**Tries, each announced and run without a stop (after the checks pass).** As AP11's: fresh scratch workspaces, the same words (tasks 80 and 81), Sonnet at medium, none published; `ai_calls.prompt_version = agent/11` proves the server runs the new code. Timetables, then Tariff File, one each. **A try counts only if the result holds:** 0 rejected; the workbook's filled cells found in the change set; Timetables has its station and driver types, the filter the words ask for, and the category translations on the categories. Reported against AP11's figures and the limits, with tokens and cost at API prices, in the usage log and here. **If the limits are not met,** AT is recorded as not met with the figures and where the remaining time went; no further runs.

**Journey cases (J50).**

- **J50.46 A session starts from the engine's reading.** Given a workbook task in a workspace without records and one with records, when the first turn starts (test command), then the task's client has made one draft, its source file is the workbook, the inference's proposals are applied (`newApplication`, `extend`), its dry run is recorded, and the prompt names the draft and the dry run's figures; given a workbook the inference proposes nothing for, the session starts with no draft and `agent/10`'s sentence. On two model configurations.
- **J50.47 A draft's dry run reads its own profile.** Given a draft with a profile, a dry run without `profile` reads every row with it; one with the profile `GET /model-drafts/{id}/profile` answered, sent back unchanged, gives the same figures.

**Checks.** J50, J34 (inference and dry run), `contract` with the OpenAPI lock (re-baselined; the diff holds the optional `profile` only), `test_boundaries`, Ruff on the changed files, the frontend production build. **Migration:** none. **Docs:** `docs/API.md` (the dry run's optional profile), CHANGELOG, and the guide text the change touches (the dry run's profile; what the assistant starts from).


**Built (2026-11-08).** Items 1 to 3 of "What changes", J50.61 and J50.62 and the docs; the tries are not run.

- **Journey numbers.** J50.46 and J50.47 were already taken by 0.16 (a merge from words; the proposal says what moves), so the two cases are **J50.61** (a session starts from the engine's reading) and **J50.62** (a draft's dry run reads its own profile), added to `USER_JOURNEYS.md` and `API_JOURNEYS.md`.
- **The start is made in the task's job, not by the worker.** `tasks/engine_start.py` (new): `prepare` runs before the first turn of a workbook task (`agent._engine_reading`, called from `agent.start`; words alone and the saved-layout path never reach it). As the task's client it makes the draft (`draft_plan.open_draft`: the workspace's running release as base, named "Assistant: <file>"), stores the workbook as the draft's source file and profiles it, runs the inference (`extend` when the workspace holds records, `newApplication` when it holds none), applies every proposal (`apply_inference`) and dry-runs the draft's own profile. The profile and the inference are run inline: `store_source_file(profile=…)` and `inference.run.infer_now` create the job as running and finish it in the same transaction, so no worker takes it. The dry run is the worker's (it binds and previews in chunks), queued as the task's requester and waited for in the job, with the task's stop check, for at most `START_SECONDS` (300). The inference and application steps were split out of `submit_inference` (`_inference_job`).
- **The draft's creator** is recorded by the engine's own audit hook: `prepare` runs the draft, file and inference steps under `writing_as(…)` with the job's writer and `principal=("client", task.client_id)`, so the `model_draft created` audit event names the task's client, which is what `agent._drafted_by` looks for. The client is made before the start (`create_session_client`, as `_access` does) and `_access` finds it. A session that proposes the start's draft lands without any change to AD's rule (J50.61 runs with the real `_drafted_by`).
- **When there is no start:** any failure, a refusal or `NOTHING_TO_APPLY` (a sheet with no shape), a failed or slow dry run (the job is asked to stop): the draft the start made is deleted, the reason is logged, and the prompt is `agent/10`'s with `PROMPT_VERSION = "agent/11"`. `design.startDraft` holds the start's draft until a proposal lands; a proposal that names another draft or none deletes it (`_drop_unused_start`), so no draft stays that nobody holds.
- **The prompt** (`agent._engine_start`, used by `_propose_prompt(start=…)`): the draft is the session's own, the engine read the workbook into it (its model and the profile `GET /model-drafts/{id}/profile` answers), "the words go first", the dry run's rows and rejections by code, and how to dry-run without a profile; the AD sentences (never the workspace's draft, never another's) stay. The task page's checklist counts the start's draft as "Model draft started" (`_turn`).
- **Item 3:** `DryRunRequest.profile` is optional (`models/sources.py`); without it `submit_dry_run` reads the draft's own profile (`sources/profile_export.definition`, moved out of `draft_profile` so the dry run can use it without a cycle); a `before` validator ignores `key`, `unmapped`, `ignoredSheets` and each source's `id` of a profile sent back. A draft whose profile loads no column answers `422 INVALID_IMPORT_PROFILE` at `/profile`.
- **Tests.** J50.61 (two workspaces, one with and one without records; a sheet with no shape), J50.62 (the profile held, and the profile read sent back, give the same figures). The stand-in session reads the draft id from the prompt (`startDraft`). Two existing tests run only the assistant worker, which now waits for the start's dry run: `test_a_job_the_session_queues…` and `Way.stop` also run the job worker while they wait (the first also takes the turn's start from the token file's time, since the engine's draft precedes the turn).
- **Docs.** `docs/API.md` (the dry run's optional profile), CHANGELOG, `guide/…/integrate/assistant-tasks.md` and `model-and-release-operations.md` (one sentence each); the guide is not rebuilt.
- **Checks.** J50 (`test_j50_ai_workbook_load`, `_reshape`, `_way_out`, `tests/unit/engine/tasks`): 150 passed (66 + 84). J34: 110 of 112 pass; the two that fail (`test_an_import_creates_the_list_values_a_lookup_names_once_whatever_the_rows`, both configurations) fail in their own model set-up with `INVALID_MODEL` (a detail panel "cannot sort by …", `detail_view_rules.py`, which AT does not touch); four others failed first with `AdminShutdown` while other sessions ran pytest, and passed alone. `contract` (`test_openapi_contract`, `test_boundaries`, `test_error_codes`, `test_api_journeys`, `test_api_reference`): 32 passed, 1 failed: `test_boundaries` fails only on `app.management.reference.static_site` (another session's), none of AT's modules. **The OpenAPI lock is not re-baselined:** the locked document is the default one, which does not hold the draft routes (they need `MODEL_ADMIN_MUTATIONS_ENABLED`), so its hash is unchanged. In the enabled document the only difference is `DryRunRequest`: `profile` leaves `required` and becomes `InlineProfile | null`, and its description. Ruff check on every changed file and format on the new and wholly-AT files; `store.py`, `inference/run.py` and `agent.py` were not Ruff-formatted before and are not now. Frontend `npm run build` passes (no UI change).
- **Not verified:** the tries (the time limits); a start on a workbook with tens of thousands of rows (the 300 s wait for its dry run is a guess, measured only on the 50 to 1,743-row workbooks of the probe and the tests); the job worker's capacity when every worker thread is held by task sessions (the dry run of the start then waits behind them); the guide was not rebuilt.

**Tries (2026-11-08): not met, and slower than AP11.** Both on the dev server running `agent/11`, AP11's words, fresh workspaces, through the API to `loaded`, none published; logged in the usage log (0.16 plan).

| | AP11 (proposal + load) | AT (proposal + load) | Output tokens (design) | Cost at API prices | Limit |
|---|---|---|---|---|---|
| Timetables (`at-mot`) | 814 + 60 s | 793 + 141 s | 83,286 (AP11 86,395) | $3.11 + $0.73 | 120 s |
| Tariff File (`at-price`) | 379 + 60 s | 606 + 159 s | 61,233 (AP11 39,065) | $2.47 + $0.48 | 300 s |

- **The start worked as built.** Timetables: the session had its draft 14 s after the task started, the dry run reading all 1,743 rows, 1 rejected. Tariff File: 200 rows (Packages), 0 rejected, in 33 s.
- **Both sessions removed it.** Timetables, step 50 of 143: "the draft now matches the workspace model, with the generated import types removed"; Tariff File, step 62 of 128: "the draft is back to the workspace's own model". Each then built its own model and profile as in AP11, after the turns spent reading the start and undoing it. On Timetables the words ask for a structure the file's columns do not give (stations, drivers, a CRM system, translations per language, a filtered field); on Tariff File the start lacked the Products sheet. The session's rounds of dry runs fell (Timetables 8 completed and 4 cancelled, against AP11's 14; Price 2), but the reading turns did not.
- **The results hold.** Timetables: 2,129 records and 4,535 relationships, 0 rejected; the load's cell report: 15,120 cells, 652 empty, 9,984 converted, 4,484 resolved, 0 refused or not found; station and driver types, the `ancestor:mot-category.name` candidate filter and the category translations in the installed release. Tariff File: 9,747 records and 19,919 relationships, 0 rejected; 58,696 cells, 37,633 empty, 19,729 converted, 1,334 resolved, 0 refused or not found; both sheets loaded. AP11's separate cell-by-cell comparison with the change set was not repeated; the figures are the load's own report.
- **Three sessions were killed** ("The worker stopped while the session ran"): the dev server runs `uvicorn --reload`, and another session saved `static_site.py` and its tests at 11:49, 11:51 and 12:11. Each task went on in a new session with a new start, and the killed session's draft was removed; the figures above are the sessions that finished. The load times (141 and 159 s, AP11 60 s) were not looked into.
- **No further runs**, as planned. What to keep is the user's decision: the dry run reading a draft's own profile (item 3) is an API fix that stands alone; the start (items 1 and 2) made both tries slower.

**Decided by the user (2026-11-08):** the start (items 1 and 2) is removed and the session starts as before (`agent/10`'s prompt); the dry run reading a draft's own profile (item 3) stays. **The timings are accepted** as these tries measured them (Timetables 793 + 141 s, Tariff File 606 + 159 s).

**Start removed (2026-11-08).** Items 1 and 2 are out: `tasks/engine_start.py` is deleted; `agent.py` lost `_engine_reading` (and its call in `start`), `_engine_start`, `_propose_prompt`'s `start=`, `_drop_unused_start`, the `design.startDraft` handling and the `_turn` checklist change; the prompt is `agent/10`'s text again and `PROMPT_VERSION = "agent/10"`. `infer_now` and `_inference_job` (`inference/run.py`) and `store_source_file(profile=…)` (`store.py`) had no other user and are back as before AT. J50.61 and the stand-in's `startDraft` are removed, and the two test adjustments (`test_a_job_the_session_queues…`, `Way.stop`) are back. The number J50.61 stays unused in `USER_JOURNEYS.md`; `API_JOURNEYS.md`, the CHANGELOG and `assistant-tasks.md` no longer mention the start. **Stays:** item 3 (`DryRunRequest.profile` optional with its `before` validator, `submit_dry_run` reading the draft's own profile, `422 INVALID_IMPORT_PROFILE`) and J50.62. `profile_export.py` stays: `draft_profile` imports `dry_run`, so `dry_run` cannot import `definition` back from `draft_profile` without a cycle. Checks: `test_j50_ai_workbook_load` 62 passed; `test_j50_ai_way_out`, `test_j50_ai_reshape`, `tests/unit/engine/tasks` and `test_openapi_contract` 95 passed (the lock hash unchanged); Ruff check passes on the changed files (`store.py` and `inference/run.py` were not formatted before and are not now); `cd guide && npm run verify` passes.

## AQ: The assistant loads a laid-out workbook and asks only what a person decides


**Why (read 2026-11-08 from the tasks, their jobs and the session logs; no new AI run).** The files are simple lists laid out side by side for people: a title, a group row (4), a header row (6), a blank shaded row, data from row 8, empty spacer columns between the blocks. The session read them correctly in its first commands, and so did the engine's profile (header row 6, the blocks). The time, the cost and the questions came from the engine:

- **Operation names guessed.** `openapi.json` gives `POST /model-drafts/{id}/operations` an untyped list (`ModelDraftOperationsRequest.operations: list[dict]`), so both sessions tried names until one passed (`setProfile`/`setImportProfile`/`replaceProfile`, `bindColumn`/`mapColumn`, `removeValueMap`/`deleteValueMap`/`dropValueMap`, `layOut`/`layout`…). The kinds and their parameters exist only in `authoring/kinds.py` and `mapping.py` and as prose in `docs/API.md`.
- **A tested profile replayed step by step.** `setProfile` takes `key` and `name` only. After a clean inline dry run, task 94 replayed its profile as about 220 operations (draft version 1 to 224, about 8 minutes); task 95 reached version 370 and was still replaying when it hit the session limit.
- **The session limit ends as a crash.** `TIMEOUT_SECONDS = 1800` (`agent.py`) raises `TimeoutError`, which nothing catches: the worker's generic branch logs a traceback and the task says "internal error … report the correlation ID" (task 95, 16:32:16, exactly 30 minutes after it started). The limit is not a setting.
- **Questions the prompt asks for.** Task 94's check returned nine questions; two are a person's decision (pairs or exact result–reason–sub-reason combinations; exposing the lists in a consumer API). Three prompt rules say "raise that as a question" (two names for one thing, no key column, a repetition kept flat), so keep-as-is points became questions, and two came from the binding limits above.
- **Answering costs a turn.** `queue_answers` (`design_job.py`) always queues a new session turn, also when every answer is the `assumed` default the draft already holds.
- **A waiting task says it is working.** The task's state is written when its job is queued (`reading`, `checking`); with one assistant worker per process the second and third tasks waited 25 minutes while the page said "Checking every row".
- **Undoing a value map drops later ones.** `setValueMap` writes the whole `valueMaps` object (`mapping.py`), so its inverse restores every map as it was; undoing an earlier step while later ones stay removes the later maps (task 94 saw it).

**What changes.**

1. **The session limit is a handled ending.** A turn over the limit ends through the same path as a person's stop (AP-D55): the session is stopped, its jobs are cancelled and a partial load is undone as today, the task goes back to where the person can go on with its draft kept, and the note says in the person's terms that the session took longer than the limit and was stopped, with Try again and Tell. The log has one WARNING line, no traceback; the job ends `cancelled`-like, never `JOB_FAILED`. The limit becomes `AI_AGENT_TIMEOUT_SECONDS` (default 1800), in `config.py`, `.dev/settings.env`'s template and `docs/OPERATIONS.md`. Both places that raise (`_turn` and `_await_its_jobs`) use it.
2. **The draft operations are typed in the OpenAPI.** The operations body becomes a list whose items are a `oneOf` discriminated by `kind`, one schema per public kind, generated from the kinds registry (`KINDS`, each kind's allowed parameters, its docstring as description); `INTERNAL_KINDS` are not listed. The server's checking is unchanged (the registry stays the one place); the schema only describes it. A test fails when a kind is added without its schema.
3. **A whole profile in one operation.** `setProfile` accepts the profile as `GET /model-drafts/{id}/profile` answers it in `definition` (`sources`, `valueMaps`, besides `key` and `name`) and replaces the draft's profile with it, one undoable step. Read-only fields of a profile sent back (`key`, source `id`) are ignored, as AT made the dry run do.
4. **A column is named by its letter too.** `ColumnBinding` takes `letter` (a sheet column letter, as `Block` uses) as the alternative to `column`; exactly one of them. The import, the dry run, the draft's operations (`mapColumn`, `ignoreColumn`, `setColumnReading`, `splitColumn`, `unmapColumn`, `addValuesToList`, `setValueMap`'s `column`) and `_column` accept it. A letter reaches a column whose header cell is empty. The draft's `_column` also accepts the reader's names for repeated headers (`Checklist #2`), so the two never disagree. The profile `GET /source-files/{id}/profile/sheets` answers lists a column with data under an empty header with its letter, so a session sees it.
5. **The prompt (`agent/11`) asks only what a person decides.** Questions are only for a choice that changes the model or a consumer contract, and the draft already holds the assumed answer. What the data gives as it is (two names for one thing, likely typos, no key column, a repetition kept flat) is one line of the final note, never a question. Something the load cannot read is never a question: bind it by letter. The prompt names `letter`, and `setProfile` with the whole profile.
6. **Answers that keep the defaults cost nothing.** When every answer equals its question's `assumed` option, `POST /ai/tasks/{id}/answers` records them and the task stays `checked`; no turn is queued. Any other answer queues the turn as today.
7. **A waiting task says it waits.** `AiTaskResponse` carries `ahead`: while the task's job is queued, the number of assistant jobs before it (queued or running, lower `sequence_id`); `null` once it runs. The task page and the journey bar say "Waiting for the assistant: 2 tasks ahead" (one: "1 task ahead"; zero: "Starting…") instead of "Reading the workbook" or "Checking every row" while `ahead` is not null.
8. **A value map's undo restores that map only.** `setValueMap` records its change at `valueMaps/<name>`, so undoing it restores or removes that map and leaves the others.
9. **Model-only requests end in a migration with no type mappings (`agent/12`).** Found in task 99 (`stops`, "add relation matrixes for languages in the lead application…"): nine valid `relationMatrix` views, no questions, no moves; the session installed release 0.2.9 and made an empty change set, and `accepted()` failed the task as "nothing was loaded". The accepted prompt now tells the session that when the words ask nothing of the stored records it installs one release, activates none, makes no change set and ends with `RELEASE: <id>`; `accepted()` lands such a task as `loaded` with `{"migration": {"releaseId", "typeMappings": []}}` after the same contract and landing checks, and discards an empty change set the session made. The task page offers the migration as "Move the workspace to the new model" (no record moves). J50.66.
10. **A question reaches the person whole (`agent/13`).** Found in task 98: the engine kept a question's first 500 characters, and the session had written its reason first and its ask last, so the page showed the reason ending mid-word ("…Run load-profile") with the ask gone. The engine keeps the session's text whole (a runaway one over 2,000 characters is shortened at a word, with an ellipsis), and the prompt asks for the question itself first, in at most three short sentences. J50.30 proposes a 700-character question and finds it whole.
11. **The session's scratch folder is inside its own folder (`agent/14`).** Found in task 95: the session kept its helper files in the machine's scratch folder (`$TMPDIR`), and on the accept turn it wrote that path out in a command; Claude Code's read block refuses reading outside the working folder, in don't-ask mode nobody is asked, the session gave up and the task failed, a paid turn with nothing done. The engine now sets `TMPDIR` to `<folder>/tmp`, and the prompt says to keep every file in the folder by a relative path and to run a refused command again that way rather than end the turn. A resumed session keeps its earlier turns' habits (task 95's next turn named the old path again, $6.97 for 14 s with nothing done), so every later turn's prompt ends with the folder rule and the folder's and `$TMPDIR`'s paths. Unit tests in `test_agent.py`.
12. **One key is one record across the load's sources (D69).** Found in task 95: two sources of `iso-country`, both `upsert` keyed by name, gave 487 records for 200 codes, each code two half-records (one with the name and numbers, one with the relation). `binding._KEY_GROUP` grouped upsert rows by source and key, so only a name under a parent (D142) was one key across sources; it now groups upsert rows by type, key kind, key attribute and key value whichever source they come from, so `_duplicates` merges the rows of two sheets with the same rule (equal values and relations add up, an empty cell agrees, a field filled differently refuses every such row), the preview and the draft dry run included (one binding). `DUPLICATE_KEY_IN_FILE` names the rows with their sheet (`details.refs`, `Sheet!2`) beside `details.rows`. Two sheets that listed one new number with different values no longer load the later sheet's value over the first (0.16 AP6): they are refused, as one sheet's rows are.
- **The answers card (same day).** Answers that are all the assumed ones start no design round (AQ-D4); the card now says the draft is already built on them and shows "Answer and design again" only once a choice differs.

**Not in AQ.** More than one assistant worker per process (`WEB_CONCURRENCY` gives one per process today); a source with `record: existing` not finding records made earlier in the same load (task 94 kept a second result list for it); the session's model and effort.

**Decisions (my recommendations, recorded under the user's order to deliver).**

- **AQ-D1: The limit stays 30 minutes by default.** Items 2 to 4 remove the work that made task 95 run over; an operator can raise it.
- **AQ-D2: `setProfile` takes the whole profile,** rather than a new kind: it is the name sessions tried first, and the shape is the one `GET …/profile` answers.
- **AQ-D3: `letter` beside `column`,** rather than renaming empty headers: a letter is stable whatever the header says, and `Block` already speaks letters.
- **AQ-D4: Defaults-only answers queue nothing.** The draft already holds the assumed answers; the person goes on to accept.
- **AQ-D5: `ahead` counts assistant jobs by `sequence_id`,** the worker's claim order; leases are ignored (a close count, not a promise).

**Mock-up (task page while waiting).**

```
 ───────────────────────────────────────────────────────────
 Waiting for the assistant: 1 task ahead. You can leave this page.
 [ Stop ]
```

**Journey cases.** J50.63 a session over the limit (a stand-in session and a limit of a few seconds) ends with the task back at its last point, its draft kept, the note, the job not `JOB_FAILED`; J50.64 answers equal to the defaults queue no job and keep `checked`, one other answer queues a turn; J50.65 a second task queued behind a running one reads `ahead: 1`, then `null` once it runs. J34 (imports): a block with an empty-header column and three equal headers loads every column by `letter` and by `Name #2`, in the import and in the draft's dry run. Draft operations (J-case of the draft journeys): `setProfile` with a whole profile read from `GET …/profile` gives the same dry-run figures as the original and undoes in one step; undoing an earlier `setValueMap` keeps the later maps. Contract: every public kind has its schema in the OpenAPI.

**Checks.** J50 (`test_j50_ai_workbook_load`, `_reshape`, `_way_out`, `tests/unit/engine/tasks`), J34, the draft-operation journeys, `contract` with the OpenAPI lock (re-baselined if the locked document changes), `test_boundaries`, Ruff on the changed files only, frontend tests of the task page and the production build. **Migration:** none. **Docs:** `docs/API.md` (operation schemas, `setProfile`'s profile, `letter`, `ahead`, answers), `docs/OPERATIONS.md` (`AI_AGENT_TIMEOUT_SECONDS`), CHANGELOG, the guide sentences the change touches, and a guide rebuild.


**Built (2026-11-08).** All eight items, the journey cases, the checks and the docs; the try is not run (below).


## JG: Related jobs grouped on the Jobs page

**Status:** Asked by the user on 2026-11-08 ("add a groupping layer, so the tasks which are connected are groupped together and you can dig in … also add a navigation for this … much more better thing than just standard hyperlinks"). Planned in 0.13; the plan and its HTML mock-up (https://claude.ai/artifact/Lko7rRVeqCdz27AweJFHFa) **approved by the user on 2026-11-08** ("yes this is good"), with JG-D1 to JG-D3 as recommended.

**Why.** Settings › Data operations › Jobs lists every job flat, newest first. An assistant task's session queues dry runs, profiles and inferences one after another: on the dev database 663 of 1,191 jobs other than `aiTask` were requested by a task's session client, and a single task makes dozens (task 94: 11 dry runs; task 95: more). A person's model draft adds its own dry runs (144 jobs on drafts with no task). The jobs a person came for are buried.

**What changes.**

1. **A job says where it comes from.** The job response gets `origin`: `{"kind": "aiTask", "id", "name"}` for a task's jobs (the `aiTask` jobs, whose parameters name the task, and every job its session client requested), else `{"kind": "modelDraft", "id", "name"}` for a job on a draft (`parameters.draftId`), else `null`. Worked out in the query (a join on `ai_tasks.client_id` and `model_drafts`), not per row in Python.
2. **The list can be grouped (API).** `GET /jobs?grouped=true` answers one row per origin and one per job without one, newest activity first, with the same cursor paging: a group row has `origin`, `jobs` (count), `states` (count per state), `latestAt` and its newest job; a single row is the job as today. `GET /jobs?origin=aiTask:<id>` (or `modelDraft:<id>`) lists that group's jobs, newest first. Without these parameters `GET /jobs` is unchanged.
3. **The Jobs page shows groups.** The table lists groups and single jobs. A group row shows its name and kind ("Assistant task", "Model draft"), its job count, a summary of states (pills: 1 running, 2 failed, 8 completed), the workspace and the latest activity. A row's chevron and the row itself open the group; a single job opens its page as today. A **Grouped / All jobs** switch above the table shows the flat list as before; the choice is remembered in the browser.
5. **Cancel stays where it is**: on each job row while it may be cancelled; a group row has no cancel (stopping a task is the task's own action).

**Decisions (my recommendations).**

- **JG-D1: Model drafts are groups too**, besides assistant tasks: a person's draft piles up dry runs the same way, and the grouping is one mechanism (origin), not a task feature.
- **JG-D2: Grouped is the default**, with the switch to the flat list; nothing of today's list is lost.
- **JG-D3: The trail bar, not links.** The shared `TrailBar` (a back button and a trail of buttons), a summary card with filter chips, Esc to go up and addressable state; no new navigation component.

**Mock-up.**

```
 Jobs                                        [ Grouped | All jobs ]   [Refresh]
 ─────────────────────────────────────────────────────────────────────────────
 ▸ Model draft · Timetables v3            at-mot 4 jobs ✓ 4                  12:05
   Export · 7c1e…                           stops            ✓ Completed          11:20
 ─────────────────────────────────────────────────────────────────────────────

 After a click on the first row:

 ┌───────────────────────────────────────────────────────────────────────────┐
 │ ( All 12 )  ( Running 1 )  ( Failed 0 )  ( Completed 11 )                │
 └───────────────────────────────────────────────────────────────────────────┘
   Job                 State        Items                       Created  Finished
   Assistant task      ● Running                                16:34
   Dry run 0cf1…       ✓ Completed  195 of 195 processed …      16:01    16:01
   Dry run bba7…       ✓ Completed  94 of 94 processed …        15:46    15:46
   …
```

**Journey cases.** An API journey: a task's session jobs and a draft's dry runs come back as two groups with their counts and states; `origin=` lists one group; the flat list is unchanged. Frontend tests of the Jobs page: groups, drill-in, trail back, the state filter, Esc, the switch, a reload on a group's address.

**Checks.** The jobs journeys, `contract` with the OpenAPI lock (re-baselined: `origin`, `grouped`, `origin=`), `test_boundaries`, Ruff on the changed files, the Jobs page tests and the frontend production build, a look at the page in the browser on the dev data. **Migration:** none expected (an index if the grouped query needs one, measured on the dev data). **Docs:** `docs/API.md`, CHANGELOG, the guide's Jobs page text and a guide rebuild.

**Built (2026-11-08), JG.** As approved, with these choices:

- **Grouping in SQL.** `engine/jobs/origins.py` joins each job to its task (by `parameters.taskId`, else by the task's session client) and to its draft, and groups with `GROUP BY` on the origin (a job with neither is its own group); the page is keyset-paged on the group's newest job. A task wins over a draft when a job has both. A task's name is its workbook's file name, else its instruction shortened to 80 characters, else "Instruction".
- **One migration, `20261124_01`.** On the dev data the grouped read cost 300 ms, all of it parsing the JSON `parameters` of every job; `jobs.task_ref` and `jobs.draft_ref` are generated stored columns over `taskId` and `draftId` (index on the task), and the read fell to 3 ms.
- **API shape.** `grouped=true` rows are `{job, group}`: `job` is the group's newest job or the single job, `group` is null for a job without an origin. With `origin` the same call answers that group's one row (the page's summary and chips); `state`, `kind` and `workspaceKey` apply before counting. A malformed `origin` is `422 INVALID_ORIGIN`.
- **Open the task / Open the draft** are offered once the engine has let the person read the task (`GET /ai/tasks/{id}`) or the draft (`GET /model-drafts/{id}`); a refusal leaves the button out.
- **Addresses.** `/settings/jobs/groups/{aiTask|modelDraft}/{id}?state=…`; a job opened from a group is `/settings/jobs/{id}?group=aiTask:{id}&state=…`, which keeps the trail. Esc goes job to group to list and does nothing while a dialog is open or a field has focus.
- **Switch** is stored in the browser as `refiroo.jobs.view` (default Grouped). The grouped table has an Actions column for the cancel of a job without an origin; a group row has none. A group's jobs table drops the Workspace column.
- **The browser look did not use the dev data.** Signing in to the developer instance needs a person's password and creating one for the look was refused by the permission system, so the look ran on the repo's isolated browser harness (real engine and sign-in; the grouped and group reads answered with fixtures shaped like the engine's). The grouped query itself was run on the dev database.

## AB: The assistant loads a file as one checked batch

**Status:** Asked by the user on 2026-11-09 ("I expect the llm to understand: file, model, capabilities and propose a solution … whatever you propose, this has to work"); placed in 0.13 by the user ("yes its part of 0.13"). The plan and its HTML mock-up **approved by the user on 2026-11-09** ("mock accepted, the ab can be delivered too"), with AB-D1 to AB-D6 as recommended.


**What changes.**

1. **The draft dry run takes items** (engine). `POST /model-drafts/{id}/dry-run` accepts `workspaceKey` and `items` (the batch item format, with `ref` naming the cells each item comes from, e.g. `Person!Q31:S31`) in place of a source file and a profile; or `itemsFileId`, a file of items uploaded to the draft, for large sets. The worker previews every item against the draft's compiled model, as today's dry run previews the items a profile binds, and stores the items with the job. The summary gives, per type: new, matched, changed, refused, the relationships per type, a few example items per type with their refs, and the finding the engine works out in the database: a name that appears more than once in one type once the load is in (with the parents it sits under). What the assistant noticed in the data (two existing records that look like one thing, rows that disagree) is in its summary.
2. **Accept runs no assistant turn** (engine). Accepting installs the draft as one release, makes the change set on it and runs the dry run's stored items into it as one atomic background batch: the engine does what the load turn did, with no AI cost and no session to fail. The task ends `loaded` with the batch's counts, or `failed` naming the refused items (data changed since the preview), with **Give the assistant other words** to go on. Model-only tasks keep their migration ending (AQ item 9); tasks that move whole types keep theirs.
3. **The assistant works as in an ordinary session** (prompt, `agent/15`). It reads the workbook in Python (layout, hidden columns, shifted blocks), reads the model and the workspace's records through the API, changes the draft model where the file needs it, writes a script that turns the file into items (new records get IDs it generates so later items can point to them; existing records are found by reading them and named by ID), sends one items dry run and reads its summary. It fixes its own items until the dry run refuses nothing and the findings are explained, then writes the proposal. It writes no load profile. It asks the person only what the file and the words leave open, in the person's terms; never about the engine.
4. **The task page shows what the load does** (frontend). "Where each sheet goes" is replaced by **What the load does**: the figures (records new, existing matched, relationships, refused, rows read), a table per type (new, matched, changed, refused, linked to) whose rows open to example records with their cells, the engine's findings, and a folded **Where each part of the file goes** (cell ranges and what they become, from the items' refs). The summary, the model change, the questions and the notes stay as they are. The accept text says the engine loads exactly these records. Mock-up: see the link under Decisions.
5. **Saved layouts are untouched.** A file whose layout a saved import profile already holds still loads through it (0.10–0.12), with AQ item 12's merge.

**Decisions (my recommendations).**

- **AB-D1: The batch is the load.** The assistant no longer writes load profiles; whatever the file holds, it expresses as records and relationships the engine checks. The import language stays for saved layouts only.
- **AB-D2: Accept is the engine's.** The previewed items are what is loaded, so accepting needs no assistant turn: it cannot fail on the session, costs nothing and is exactly what the person saw.
- **AB-D3: Records are named by ID.** The assistant reads existing records and refers to them by ID, and gives new ones IDs of its own, so matching is the assistant's reading of the data (as a person's would be), checked by the engine, not a key rule the file must fit.
- **AB-D4: All or nothing.** The accepted batch is atomic: a refusal at accept writes nothing and says which items and why.
- **AB-D5: Findings are shown, not asked.** A name twice in one type (the engine's) and what the assistant noticed in the data are listed on the proposal with what the load does about them. The person acts on them if they want to; they are not questions.
- **AB-D6: Done means the acceptance files load.** See below.


**Mock-up:** https://claude.ai/artifact/P8QgsMLZ29C7xGdGB7JQ6f (task 95's workbook with the numbers a correct load gives).

**Built (2026-11-09), AB.** All five items; the acceptance files run on 2026-11-10 (below).

- **Items dry run (item 1).** `POST /model-drafts/{id}/dry-run` takes `workspaceKey` and `items` in place of `sourceFileId` and `profile` (`DryRunRequest`, exactly one form, `422 REQUEST_VALIDATION_ERROR` otherwise). `itemsFileId` is dropped: the body is inline, held to `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES` and also `ATOMIC_JOB_MAX_ITEMS`, since accepting loads the set as one atomic batch (`413 BATCH_TOO_LARGE` names the setting). The job is a `dryRun` with `parameters.mode: "items"` and the items as its inputs; the worker previews every one in the existing preview path (`preview_items`, a batch's preview rules: not the import's file-row rules). Refusals are item outcomes with their `ref`.
- **Where the items are kept.** In the job's inputs (`job_inputs`), not a job file: a completed items dry run keeps them (`jobs/store._finish`), retention removes them as any job's, and a newer items dry run of the draft deletes the older ones' in the same transaction. Accepting then copies them to the load's batch with one `INSERT … SELECT`, never through Python.
- **Summary (item 2).** `sources/items_summary.py`: SQL over the job's inputs and outcomes (per type new, matched, changed, removed, refused; relationships per relation type, including a created record's `initialRelations`; the types each type is linked to; three examples per type, a refused one first, with values, links and ref; the refs grouped into the parts of the file; rows read from the distinct sheet and row of the refs; the refused items and their counts by code). The finding "a name twice in one type" is read inside the preview's transaction before the rollback (`name_twice`), among the records the accepted items touch, with the parent each sits under. `GET …/dry-run` answers it as `items` (`ItemsDryRunSummary`, `sourceFileId` null, `summary` null). The task's design stores it as `design.load` and `design.itemsLoad`; the task's `check` is the same run in the old check's shape (`mode: items`, no sheets). The "new records beside the records held" check is not made for an items run (the type table says new and matched).
- **Accept (item 3).** `tasks/items_load.py`, dispatched by `tasks/job.run_design` (not `agent.accepted`, to keep the tiers acyclic): installs the draft through `draft_profile.install_draft` (extracted from `POST …/installation`, which now calls it; a taken release version gets the next one by `setRelease`; a retry for the same draft version reuses the release), makes the change set on it with the current-live source (on the current release, no install, when the draft does not change the model), copies the items to an atomic `batch` job of the task (`parameters.taskId`) and runs it inline in the task's own job with the batch executor (`run_items`), a stop by the person ending that batch `cancelled`. `loaded`: `result` has the change set, `counts` (the change set's own), `importJobId` and `releaseId`. A draft changed since the dry run (`superseded`: a step that can change what the load writes) has every item previewed again first; a refusal fails the task before anything is installed. A refusal in the batch (data moved) discards the change set and fails the task naming up to five records with their cells, and withdraws the release this accept installed (the draft goes back to the release it was based on, the refused batch job is removed, then the engine's `delete_release`; a release already installed before, or one the engine refuses to delete, stays and the note says so). A retry installs again. An items load saves no import profile. A failed or loaded items task given words goes to the session as a correction of the proposal (stage `model`), which sends a new items dry run, as there is no session turn to repeat. Moves and model-only tasks keep their endings.
- **Prompt (item 4).** `agent/15`: `_KEYS` and the profile guidance of `_QUESTIONS` are gone, `_ITEMS` and a shorter `_QUESTIONS` replace them; `_SHAPE` stays (it is model design, not a profile instruction); the correction prompt says to send the items to the dry run again.
- **Page (item 6).** `DesignLoad` (Card, SettingsTable, Disclosure, Notice) in `ModelProposal` after the model change, and in `DesignView` in place of `DesignSheets`, which stays for designs that hold a profile. Rows with examples open with Enter, Space and click. The proposal's accept is the bottom bar of the mock-up ("Accept and load to change set", "Give the assistant other words", which focuses the words box); the header's model accept is not offered for an items proposal. A check from before the draft's last change is said inside the card.
- **Tests.** J50.67 to J50.70 in `tests/journeys/test_j50_ai_items_load.py` (`test_a_session_sends_items_to_its_drafts_dry_run_and_the_proposal_shows_what_they_do`, `test_accepting_runs_the_previewed_items_with_no_assistant_turn`, `test_an_item_the_data_has_moved_away_from_fails_the_accept_and_writes_nothing`, `test_a_draft_changed_after_the_check_is_checked_again_before_anything_is_installed`, `test_an_items_dry_run_refuses_an_item_with_its_cells_and_takes_exactly_one_form`), a unit test of `items_check`, `DesignLoad.test.tsx`. The OpenAPI lock is re-baselined to `2a7b406009eb3574b6489924f11179c51b0377d7a423f97a1c2aa397e4b87442` for the working tree (it includes other sessions' uncommitted schema changes).
- **Guide pages (updated 2026-11-10).** The pages that described the check of every row, the saved profile after a session load and "Where each sheet goes" were rewritten by the wave `AB-GUIDE` (2026-11-09: ten pages, among them `use/load-a-workbook-with-the-assistant`, `model/review-an-assistants-workbook-design`, `integrate/assistant-tasks`, `use/loading-with-the-assistant`, `model/ai-model-changes`, `journeys/work-with-an-assistant`; notes in `guide/_coverage/notes/AB-GUIDE`, progress in `guide/_waves/progress/AB-GUIDE.md`) and corrected a second time by the fix wave `C11-FIX3` (twelve pages, `guide/_coverage/notes/C11-FIX3/report.md`: the publication handoff, the relationship counts, the "Accept and load to change set" label, the saved-profile statement). What `AB-GUIDE` reported as contradictions is closed: `docs/API.md` states that an items load saves no profile (the accept entry, `profileKey` absent) and the task bar's "Accept the model" matches the page (checked by `C11-FIX3`). Six pictures still show the earlier flow ([open item 2](#open-for-013)).

## CP: Completeness from the code

**Status:** Planned 2026-11-06. The requirement is the user's: a full documentation of refiroo. Each time the user read a
section, most of what a reader needs to do the work was missing (how to configure HTTPS and renew its certificates, how
to add a navigation bar), and the user had to ask for it piece by piece. Cause: the waves' topics came from the
repository's documents (the reconciliation ledgers in `guide/_waves/reconcile/` go heading by heading through
OPERATIONS, the model documents, the consumer API document and CURRENT_FUNCTIONALITY). Where those are thin, the guide is
thin, and nothing asked what a reader needs to finish a task. CP takes the list from the code and the depth from fixed
questions. DOC11 (a reader with network access and a browser, planned 2026-11-08) checks whether written steps can be
followed, not whether anything is missing.

**1. The inventory (primary agent).** `guide/tools/inventory.py` writes `guide/_coverage/inventory/<kind>.json`, one
entry per item, from the code:

| Kind | Source |
| --- | --- |
| Settings | `SETTINGS_CATALOGUE` (`backend/app/config.py`, 63 entries) |
| Management API operations, MCP tools | `app.main.app.openapi()`; `management/mcp_tools.py` |
| Consumer API | the generic router (`consumer/router.py`) and `consumer_openapi` over the guide's reference model |
| Commands | the modules of `backend/app/cli/` (9) and their argparse options |
| Permissions | `engine/authorization/catalogue.py`: `GROUPS`, `ACTIONS`, `PREDEFINED_ROLES`, `AGENT_CEILING` |
| Screens and actions | `RouteState` kinds (`frontend/src/routing/routes.ts`, about 56), model editor `OPERATIONS` (`features/model-editor/operations.ts`), the action menus and confirmation dialogs |
| Model features | every field of `ModelDefinition.model_json_schema()` (`backend/app/models/schema.py`): types, attributes, pages and panels, tables, navigation, applications, relations, matrices, mappings, consumer APIs |
| Deployment | the services, volumes and profiles of `compose.yml` and `compose.acme.yml`, `caddy/Caddyfile`, and each setting the Compose files pass |

Error codes are not in CP's inventory: the restart left the error catalogue with 0.14 (above, "Restarted 2026-11-02").

**2. The coverage check (primary agent).** `node tools/check.mjs coverage`: every inventory entry is named on a page
(its key, its label on the screen or its operation), or it has a line in `guide/_coverage/exclusions.md` with a reason.
It runs in `npm run verify`, so a capability added later fails the build until it is documented.

**2a. What the screens cannot do (primary agent, before any wave).** The inventory also holds the lists against each
other. Each model feature in `ModelDefinition` is matched to the model editor operation that sets it, and each
management API operation a browser user needs is matched to its screen. A feature with no screen is a product gap, not a
page to write: RL found record pages could be built only in JSON, and a model administrator cannot be asked to open
JSON. Finding such a gap while writing or taking pictures on the reference instance is too late. All gaps are found
first, in one list (`guide/_coverage/inventory/gaps.md`) with the code that shows each, and reported to the user
together with a recommended package for each. The depth waves document the features as they are after those packages.

**3. The depth waves (Codex, one per section).** For every entry the section owns, the page answers the questions that
apply. How is it set up? How is it changed? Does it expire or renew, and what happens then? How does it fail, and how
is it recovered? How is it moved to another server or restored from a backup? How is it turned off? What are its
limits? Which permission does it need? Codex answers from the code and writes the answers on the page; anything the
code cannot answer is listed in the wave's notes. Order: Run, Administer, Model, Use, Integrate, About. Each wave's
fact-check is the same as before.

**Progress (2026-11-07).** Steps 1, 2 and 2a delivered (`guide/tools/inventory.py`, `node tools/check.mjs coverage`,
`gaps-verified.md`; the gaps became package ED). A management operation counts as covered by the generated API
reference at `/docs/api`; 153 of 911 entries were uncovered before the waves. The depth waves are
`guide/_waves/D-RUN.md`, `D-ADMIN`, `D-MODEL`, `D-USE`, `D-INTEGRATE` and `D-ABOUT` (the last also brings About and the
journeys up to the other sections), with their shared rules in `guide/_waves/DEPTH-COMMON.md`, run in that order by
`guide/tools/codex-chain.sh`. After them, the screenshots they ask for are taken from the reference instance, rebuilt
with ED.

**Done when** the coverage check passes with an empty uncovered list, each depth wave is finished with no open notes,
and the build, terms, operator and link checks pass.

**Delivered 2026-11-10.** The record of the closing check, with the notes of every depth wave
(`guide/_coverage/notes/D-RUN`, `D-ADMIN`, `D-MODEL`, `D-USE`, `D-INTEGRATE`, `D-ABOUT`, `D-DF`) read and classified:

- **Coverage.** `node guide/tools/check.mjs coverage` passes: 911 entries, 902 covered by a page or the generated
  reference, 9 excluded with a reason in `guide/_coverage/exclusions.md`, 0 uncovered. The waves' `uncovered.md` files
  (144 and 113 uncovered entries in the first waves) are the checker's output at the time, not open notes.
- **Closed since the notes were written.** The writers' product findings: Settings › AI said "up to N per column" for the
  Values level (fixed, CHANGELOG "findings of the documentation waves"); `EVENTS_EXPIRED` on resume sent the caller to
  an older publication (fixed, same entry); Workspace events could not be created in the browser and a deactivated
  client's secret could not be rotated there (DF1, DF2); an earlier contract version was not served (DF3); the install
  and activate summaries hid the warning that stopping an earlier version raises (`KEPT_VERSION_STOPPED`,
  `InstallDialog.tsx:84`, `ActivateDialog.tsx:318`); a tree's Change… dropped declared actions and "Oriented" promised
  more than it did (both fixed, same entry). The screenshots the waves asked for (`D-ABOUT` 8, `D-USE` 8, `D-MODEL` 9,
  `D-DF` 3, the guide's links to them) exist in `guide/public/screens/` and no page keeps a pending-picture comment;
  `npm run verify` (below) checks every link.
- **Not open: the writers' "not exercised" lines.** Each `Open:` line of `D-RUN/depth.md` and the closing paragraphs of the
  other waves say the writer read the code and ran nothing live. They are limits of method, not a missing capability or
  a page that is not written; the commands were rehearsed by DOC11's clean-host run. What no run reached is listed once,
  as [open item 4](#open-for-013).
- **No note is a gap in a page.** Step 3's rule lists in the wave's notes what the code cannot answer; the waves report
  none left ("No known factual depth question remains unanswered", D-ADMIN; "No additional unanswered
  source question", D-INTEGRATE; "No applicable question was left unanswered by guessing", D-DF).
- **Guide pages of the package.** The depth waves above, with the pictures requested in `guide/_waves/D-SCREENS.screens.json`
  and `ADMIN.screens.json`. ED's pages were written in these waves (a model-editor control is documented where the depth
  wave of its section ran); the pages of NG, RV, AB, DF and the assistant's fixes have waves of their own (see those
  packages).

## ED: The model editor sets everything a model holds

**Status:** Found by CP's step 2a on 2026-11-06 (`guide/_coverage/inventory/gaps-verified.md`). The user placed it in 0.13
on 2026-11-07 ("move it to a package and deliver it"). No separate mock-up round: the controls follow the editor's
existing side panel and dialogs. **Delivered 2026-11-07.**

**Why.** The model can hold settings that take effect, but no screen sets them. Today they are set only in the JSON
view, by the assistant, or by the defaults a new type gets. A model administrator cannot be asked to open JSON (RL).
Checked in the code: the engine reads every setting below (`records/values.py` minimum and maximum,
`records/attributes.py` `atLeastOneOf`, `ui.hidden` and `ui.helpText` in the record screens, `behavior.parentRelationTypeKeys`
in the matrix and mapping projections, `isOriented` in `records/deletion.py`, `displayAttributeTypeKey`,
`effectivePeriod`, a page's header and breadcrumbs, the tree and mapping grid view settings).

**What the editor gains.** Each control writes through the model edit operations, so undo, redo, history, the dry run,
release checks and the API are the same as for every other edit.

| Element (side panel) | New controls | Server |
| --- | --- | --- |
| Type | Display attribute (which attribute names a record); Effective period (start and end date attributes, or none); At least one of (attributes of which one must be filled); Parent relationships (`behavior.parentRelationTypeKeys`) | a new kind `setObjectTypeProperty` |
| Attribute type | Minimum and maximum (number and date types); Hidden; Help text | `setAttributeTypeFeatures` stays for features; a new kind `setAttributeTypeProperty` for `validation` and `ui` |
| Attribute on a type | Hidden on this type; Help text on this type | `setAttributeBinding` takes `ui` |
| Relation type | Oriented (deleting a record removes the relationships it points to; on or off) | `setLabel`'s neighbour: `setRelationTypeProperty` |
| Allowed relationship | Attributes carried by the relationship | `setRelationRule` takes `attributeTypeKeys` |
| Application | Colour; Default view; State (draft, active, retired) where the engine reads it, otherwise left out with its reason recorded | `setLabel` (colour exists); `setApplicationProperty` |
| Record page | Title field, subtitle field, show the type in the header; breadcrumbs: application, type, ancestors | `setViewProperty` (`header.*`, `breadcrumbs.*`) exists |
| Table view and panels | Sort menu (`sortFields`), page size; a relations panel's relationships (`relationTypeKeys`), relationship column, parent, ancestors, filter by parent | `setViewProperty` (`config.*`) exists |
| Views | **Add view…** offers a tree view (root types, label, secondary field, child order, availability field) and a mapping grid (from and to types, source columns, target columns, search fields) besides the table and the matrix; each view's settings in its side panel | `addView`, `setViewProperty` exist |
| Consumer API | Public names, per-type settings, preferred types and contract version as form fields | `setConsumerApiPart` exists |

Outside the editor, three deletions that the API has and no screen offers: an import profile (Import profiles page), a
source file (its list) and a model mapping (the mappings list), each with a confirmation in its own words.

`applications[].settings` is a free map the engine does not read, and `schemaVersion` is not an administrator's choice:
both go to CP's exclusions with that reason.

**Checks.** Server kinds: refusals (unknown attribute, wrong value type for minimum and maximum, effective period on
non-date attributes, a display attribute not on the type), undo, and the release compatibility rules the engine already
has for validation changes. The frontend: each control writes its operation and shows the value back; the production
build. One browser try on the reference instance: set each control in a draft, see it in the preview, undo it.
Targeted test groups only. The guide pages follow in CP's Model wave.

**Delivered 2026-11-07.** What was decided and built:

- **Server.** New kinds `setObjectTypeProperty` (display attribute, effective period, at least one of, parent
  relationships), `setAttributeTypeProperty` (minimum, maximum, hidden, help text), `setRelationTypeProperty`
  (oriented) and `setApplicationProperty` (default view); `setAttributeBinding` takes `ui`, `setRelationRule` takes
  `attributeTypeKeys`. The draft's outline carries every setting the editor shows. Class and inverse per kind are in
  [API.md § Kinds](API.md#kinds); the three that edit `validation`, `behavior` or `ui` undo with `restoreElements`, so a
  container they emptied comes back exactly.
- **Application `state` is left out.** Nothing reads it: no engine rule, projection or consumer call, and no browser
  code. An editor control would change nothing, so the editor does not offer it and CP's exclusions record the reason
  (as for `settings` and `schemaVersion`). Application `color` is left out too: `setLabel` can write it, but no
  screen draws it, so a control would change nothing; it is in the exclusions with that reason.
- **Minimum and maximum are for number types only** (whole and decimal). The engine checks bounds on numbers alone
  (`records/values.py`) and the model validation refuses them on any other type, so a date bound would only be refused.
- **Where the controls are.** A type's **Settings** tab; an attribute type's, a relation type's, an application's and a
  consumer API's **Settings** table; **Hidden** and **Help text** columns in a type's attribute table; **Carries** in the
  relations tables; **Header and breadcrumbs…**, **Sort menu and page size…** and a panel's **Settings…** in the layout
  editor; **Add a view…** (table, tree, mapping grid, relation matrix) replaces the matrix-only entry, and a tree's or a
  mapping grid's **Change…**. The consumer API's public names and per-type events were forms already; the contract version
  and a match's preferred types are now too.
- **Deletions.** An import profile and its file on the profile's page (people who may import), a mapping in the Mappings
  list of Copy and move (people who may copy and move); each asks in its own words and is hidden otherwise. There is no
  source-file list page; the file is deleted where it is shown, on its profile.
- **Tests.** Unit: the new kinds generated over both configurations with their inverses, refusals by field, a bound
  above the other. Journey: `test_j33_operations` (settings set, undone in one step, refused at their pointers, a
  tightened bound meeting a stored value). Frontend: descriptors, the Settings controls writing their operations, the
  layout settings, the history words, the three deletions.

## MG: Changes that need a migration, made in the editor

**Status:** Asked by the user on 2026-11-09 ("can we bring that wp from 1.0 to 0.13? I would like to use this
feature now"), after the editor refused to move a type to another application. Moved from
[1.0](ROADMAP.md#product-release-10--self-service-model-authoring-and-extensions), whose first scope line it is
("Migration-class operations in the 0.10 editor … each with its impact preview, on the 0.11 migration boundary").
The rest of 1.0 stays there. Plan and mock-up **approved by the user on 2026-11-09** ("The above is accepted"), with MG-D1 to MG-D3 as recommended.

**Why.** A model administrator cannot reshape a model once its types hold records: the editor refuses the change
(`OPERATION_REQUIRES_MIGRATION`, AP-D28), and the only way round is the JSON view plus migration mappings typed by
hand. Moving a type to another application is the first case the user needs.

**Checked in the code on 2026-11-09.**

- The refusals are `Context.unreleased` (data holds the element) and `Context.key_free` (any released key) in
  `model/authoring/kinds.py`. They are called by `setKey`; the removals; `splitObjectType`, `mergeObjectTypes`,
  `convertAttributeToListType`; `setAttributeTypeFeatures`, `setValueType`, `attachAttribute`, `detachAttribute`,
  `moveAttribute`, `setAttributeBinding`, `setObjectTypeProperty`; `setContainment` when it names `parent`; and
  `allowRelation`, `disallowRelation`, `setRelationRule`. The count is `released.impact()`: live records, values
  and relationships plus staged change-set content, in every workspace running the model.
- `setContainment` with `application` alone is not refused, but Move to… also sends `parent: null` for a type that
  has a parent (`MoveToDialog.tsx`, `keepsParent`). So a top-level type with records already moves, and a type
  under a parent does not.
- The workspace migration (`model/migrations.py`, `plan_migration`) takes only `typeMappings` (from type, to type,
  attribute sources). The migration page starts them empty: nothing is derived from the draft, so a renamed key
  has to be mapped by hand. A moved type's records go to the one application listing it (0.11 R, R-F3). A record
  keeps its `parent_object_id`, and one whose parent no longer fits is refused ("no place for this record under its
  parent"). A split (one type to two) and a conversion to a list type cannot be expressed at all.
- Installing a draft already detects the migration (`compatibility.py`, `migration_required`), says so in the
  install dialog ("Activation needs a migration") and opens the migration page with its preview. A change set on
  the old release has its "Move … and publish" banner.

**What changes.** One mechanism for every kind above, not a slice per kind (MG-D1).

1. **The editor applies the change.** `unreleased` no longer refuses: the step is applied and marked **Needs a
   migration** in the history, with what it affects (the existing impact counts: records, values, relationships).
   The menu reads "Needs a migration when installed" instead of "Refused if data uses it", and Move to…'s notice
   says the same. Undo, redo, the dry run and the API stay the same as for every other step. Key changes follow
   MG-D2.
2. **The draft states its migration.** From the draft's steps since its base release the server derives the
   migration's input: which type becomes which (a key change, a merge's from and into, a split's new type, a
   conversion's list type), which attribute becomes which (a key change, a move to another type, a detach), which
   application a moved type goes to, and the parent each moved type's records get. It is readable through the API
   on the draft and shown in the install dialog. The migration page opens with it filled in, each row marked
   Proposed and editable, never as an accept-or-reject list. Computed on read from the history, not stored (MG-D3).
3. **The migration carries what it cannot today,** as whole-set statements in PostgreSQL:
   - **A new parent:** a record keeps its parent where the new containment allows it, becomes top level where its
     type became a top-level type, and otherwise is listed in the preview as refused, by reason.
   - **An application move:** the mapping names the target application, so a type listed in several moves too.
   - **A split:** each record gives a record of the new type with the moved attributes and the split's
     relationship, with the split's cardinality (identical values share one record where the cardinality says
     many to one).
   - **A conversion to a list type:** the attribute's distinct values become records of the list type, and each
     record is linked to its value's record by the conversion's relationship.
   - **A merge and a key change:** through the derived type and attribute mappings.
   - **A tighter rule** (cardinality, required, a value type): checked in the preview, with the records that break
     it listed, as today.
   - **A removal:** shown as loss in the preview and confirmed, as today.
4. **Publishing stays as it is.** Install, the migration preview, confirmation and activation; the change set
   banner; rollback by the earlier release. Activation still refuses a release whose migration has not run, so
   "unsafe model changes remain blocked until an explicit migration succeeds" holds (1.0's exit gate).

**Not in MG:** the rest of 1.0 (dependency visualization, protected publish and rollback workflows, extensions).

**Checks.** Journey tests through the API, one per user journey: a type under a parent moved with its records to
another application's top level, installed, the migration proposed, previewed, confirmed and the records found
there; a type key renamed and a merge, installed with no hand mapping; a split and a conversion with their new
records and relationships counted; a tightened rule listing its refused records. Targeted groups only. Before and
after on the user's model: the move the user asked for, with an inventory diff of records, values and
relationships before and after. One browser try on the reference instance through the editor, the install dialog
and the migration page. The guide pages that say these changes are refused (Model section) are rewritten by Codex
in a wave; the CHANGELOG entry and a guide rebuild finish the package. The 1.0 scope line in [ROADMAP](ROADMAP.md) moved here on approval.

**Mock-up.** The Move to… dialog, a step marked Needs a migration, the install dialog naming the migration, and the
migration page opened with the proposed rows: https://claude.ai/artifact/Jt2yhJaacchYo3KU88RRoz.

**Delivered 2026-11-09.** What was built:

- **The editor applies the step.** `Context.unreleased` and `Context.key_free` (`model/authoring/kinds.py`) no longer raise;
  they mark the operation (`Context.marks`, `Applied.migration`), and `authoring/history.py` stores on the entry's effects
  each marked element with its key-change flag and its impact (`released.impact()`, now also counted for one workspace),
  answered as `migration` on the history entries. `OPERATION_REQUIRES_MIGRATION` is no longer raised. `setContainment`
  with `application` marks the types it moves. The menu reads "Needs a migration when installed", Move to…'s notice says
  what becomes of the records, the history shows a **Needs a migration** pill with what holds the element, and the element
  panel says a released key change needs a migration.
- **The draft states its migration** (`authoring/draft_migration.py`, `GET /model-drafts/{id}/migration`, `workspaceKey`,
  `againstReleaseId`, `toReleaseId`): from the entries that stand now (`history.effective_entries`) it follows each key
  change, merge, removal, split and conversion, and from the two models it reads where each type stands (application,
  parent). It answers the workspace migration's request fields (`typeMappings` with `toApplicationKey`,
  `relationTypeMappings`, `splits`, `listConversions`), a row per type, each key change with the consumer APIs of the
  base release that name the old key (the references walker over `consumerApis`), the steps and notes, and with a
  workspace the preview's own landing check (`check_landing`: moved, created, losses, refused). Nothing is stored.
- **The migration carries it** (`model/migrations.py`, all set statements): the plan takes `toApplicationKey`, relation type
  mappings and spawns; a record whose type is at the top in the target leaves its parent (`releases`,
  `PARENT_RELEASED`, `parent_object_id` cleared and the containment relationship deleted, audited); a relation type's new
  key is carried; a split and a list conversion create records, values and relationships (`migration_spawns`,
  `migration_new_objects`, `migration_new_relations`), with `created` audit entries and feed positions, the values they
  take leaving the source records (`listed`); the preview shows the new **Created** outcome (`counts.created` only when
  records are created). The request takes `relationTypeMappings`, `splits`, `listConversions` and `draftId`.
- **Screens.** `DraftMigration.tsx` (the install and apply dialogs state the migration and start the preview with its
  mappings: **Install … and preview the migration…**), `ProposedRows.tsx` (the migration page's **What the draft proposes**,
  rows marked Proposed, the Become choice previewing again and keeping the application and the rest), the Created card.
- **Tests.** Journey J33.19 (`test_j33_migration_in_editor`, on two configurations each): a type under a parent moved with its
  records to another application's top level (proposed, installed, previewed, confirmed, the same records found there);
  a key change and a merge with no hand mapping; a split; a conversion to a list type; a tighter rule listing its refused
  records; the consumer APIs naming a changed key. J33.7's cases follow the new rule (`test_j33_operations`,
  `test_j36_workspace_resources`), the unit tests for the kinds and the application target, Vitest for the dialogs, the
  page and the history, and the browser runner `test:browser:authoring-mg` (both designer models, axe, 390px). The older
  `test:browser:authoring-a4a` case that expected a refusal now expects the mark.
- **Before and after on the user's model**, in a scratch copy of the dev database (never the dev data): an active workspace
  on the user's own model (4,657 records, 13,169 values, 11,921 relationships), a type with a type under it moved out of one
  application to the top level of another. 20 records left their parents, 47 records changed application, 0 lost, 0 refused. The
  record IDs, names and all 13,169 values are identical by fingerprint before and after; the 20 containment relationships to
  the old parents are gone (11,921 to 11,901 relationships, 3,860 to 3,840 records under a parent). The first run found a defect the
  tests had not: a type the target still lists in other applications was derived with no application, so its records would have
  been lost (4,387 items); the draft now names the application the type gained (`application_target`, with a unit test).

**Decided by recommendation while delivering (not asks).**

- Move to…'s notice carries no counts: they are not known before the step applies. The mock-up's counts appear on the history
  mark right after and in the install dialog's figures.
- Installing bases the draft on the release it installed (D17), so a migration read afterwards is empty by default. The page reads
  it from the release the workspace runs to the one installed (`againstReleaseId`, `toReleaseId`); the steps recorded before are
  read against the earlier release, and a split or conversion whose new type the earlier release holds is skipped.
- The proposal reaches the migration where the draft is known: the install and apply dialogs start it (`draftId` in the
  request). A release activated later from Settings › Model, and a change set's banner, know no draft and open the page as
  before.
- A relation type's key change needed its own mapping (`relationTypeMappings`), which the plan did not list: without it the
  relationships would be lost.
- A split names the new record by the first moved value, else by the record's name; a record holding none of the moved values gets
  none; only a many-to-one cardinality shares a record between identical values.
- Moving an attribute to another type loses its values (they belong to other records, so no mapping exists); the preview lists
  them as loss.
- A released listing taken away now applies and is marked, like the other steps; the editor still refuses it as invalid while a matrix
  needs it.
- Not built: dependency visualization, protected publish and rollback workflows and extensions (1.0).

**Decisions (approved by the user 2026-11-09 as recommended).**

| # | Question | Recommendation |
| --- | --- | --- |
| MG-D1 | Only the application move, or every change that needs a migration? | **Every one.** One mechanism serves all of them: the editor applies the step, the draft states its migration, the migration carries it. A move-only package would build the same three parts and leave them to be widened in 1.0. Cost: a split and a conversion need new data statements in the migration |
| MG-D2 | Key changes of released elements | **Allowed, with the migration.** The invariant "public IDs and model keys are stable" exists because an integration names an element by its key where no guard sees it. The change therefore shows, before install, every consumer API and contract that names the old key (the existing check, D54), and the install dialog says that integrations naming the key must change with it. 1.0's scope already listed key renames. Alternative: keep keys fixed and allow the rest |
| MG-D3 | Where the derived migration lives | **Computed from the draft's history when read.** It then always matches the steps, including after an undo. Cost: one derivation per read of the draft's migration |

**Product rule, stated by the user on 2026-11-09 (the assistant's reshape and every migration).** "Whatever a person
asks the assistant to reshape, all their data comes through: every record, value, relationship and translation. The
only exception is what they explicitly asked to remove. If the assistant cannot achieve that, it says so plainly and
offers nothing to confirm."

- **The guard measures the outcome, not the kind of change.** Before the assistant task offers a migration it runs the
  engine's landing check (`check_landing`) on exactly the migration it would hand over, against today's data, whatever
  moves, merges, splits, reparentings, list conversions, renames or regroupings caused a difference. A record, value or
  relationship (translation links among them) it would lose is sent back to the session as an engine finding; at the
  handover, `_migration_result` returns no migration and the task carries a warning naming the loss per type with counts
  and saying no data was changed. The exception is what the person's words explicitly ask to
  remove: the session lists it in the proposal's `removals` (type, application, field or relation type, each with the
  quoted words; `agent/16` tells it to list only what the words ask, never what it decided to drop). The guard allows a loss
  only when it falls entirely within them (records of a removed type or application, values of a removed field,
  relationships of a removed relation type or of removed records); any other loss blocks. The removals are stored in
  `design.removals` with the engine's counts and a plain sentence ("As you asked, the Drug list is deleted, deleting 16
  records."), shown on the task page and in the notes before acceptance, and the handover check in `_migration_result`
  uses the same list.
- **One consequence amends 0.11 D68 (2026-11-09).** Records of a type the target release still has are moved, never
  lost: to their own application when the target lists the type there, to the mapping's `toApplicationKey`, to the one
  application that lists the type, or to the one that lists it newly. When none of these is unique the records are
  **refused** with `APPLICATION_TARGET_AMBIGUOUS`, naming the candidates, until a mapping's `toApplicationKey` chooses.
  Losses remain only for what the target truly lacks. `GET /model-drafts/{id}/migration` with a `workspaceKey` and no
  `againstReleaseId` starts from the release that workspace runs, so after an install it still states the move.

**Guide pages.** The wave `MG` (`guide/_waves/MG.md`, 2026-11-09) rewrote eleven pages that said these changes are refused
(`model/types-attributes-relations`, `model/migrations`, `guide/model/rename-or-re-key-an-element`,
`guide/model/reuse-and-change-attributes` and the others in `guide/_coverage/notes/MG/report.md`); the pictures it asked for
are in `guide/_waves/progress/MG.md` and its report.

**Follow-up (2026-11-09): the migration that loses nothing, and the assistant's use of it.** Recorded 2026-11-10 from the
working tree, the CHANGELOG and the tests; the product rule and its two consequences are stated above (the guard, the
`removals`, the amendment of 0.11 D68). Four things were built after the package's first delivery, all found by trying it
on the user's own model, none a package of its own:

1. **A migration never loses the records of a type the target still has** (`engine/model/migrations.py`).
   `plan_migration` sends a record to its own application, to the mapping's `toApplicationKey`, to the one application
   that lists the type or to the one that lists it newly (`arrived_applications`, shared with the draft's
   `application_target`); when none is unique the record is refused with `APPLICATION_TARGET_AMBIGUOUS`, naming the
   candidates (`_ambiguous`), and is counted neither as a loss nor as a lost end of a relationship. The reading that
   showed it: 20 types moved between applications while a third application listed every type previewed 459 losses and
   now moves 179 records and loses none. `GET /model-drafts/{id}/migration` with a `workspaceKey` and no
   `againstReleaseId` starts from the release that workspace runs (`authoring/draft_migration.py`), so after an install the
   dialogs still state the move. `check_landing` also answers the losses by what they hang on (values by type and
   attribute, relationships by relation type and ends: `LandingCheck.value_losses`, `relationship_losses`), which the
   assistant's guard words per type. Tests: `test_records_of_a_type_the_target_still_lists_are_moved_never_lost`,
   `test_a_merge_that_would_lose_values_is_never_offered` and
   `test_what_the_words_ask_to_remove_is_offered_as_a_deletion_and_nothing_more` (`test_j50_ai_reshape.py`).
2. **The before-and-after on a real model** (recorded under Delivered, above): a type listed in several applications that
   was moved out of one would have lost its records; the draft's migration names the application it gained. The unit
   test of `application_target` stays.
3. **A task that moves types to another application hands the migration the move** (`engine/tasks/agent.py`,
   `_migration_of`, `_extra_of`). The task's migration was built from the assistant's `moves` alone, so types that keep
   their key and change application were handed over with no mapping and the preview listed every record and relationship
   of them as lost. It now starts from the engine's own migration of the draft against the workspace's release
   (`authoring/draft_migration.derive`: application moves with `toApplicationKey`, relation type mappings, splits and list
   conversions), joined with the assistant's moves, one mapping per type; the landing check, the proposal and the task's
   `result.migration` (`TaskMigration`, now with `relationTypeMappings`, `splits` and `listConversions`) use that set. The
   task page words such a move ("moves to Reference lists", `ProposalMoves.tsx`, `moveWords`). Test:
   `test_types_moved_to_another_application_are_handed_to_the_migration_with_it`.
4. **The assistant's counts say what they count** (`agent.py`, the prompt's voice rules and the workspace sentence;
   `ProposalMoves.tsx`). A summary counts the records of the types or lists the change touches, named, and states the rest
   of the workspace apart; the prompt no longer lets the workspace's total stand as the number of records a change keeps
   (a move of 179 records read as "all 4657 records keep their IDs"). The task page says "20 types move to Reference
   lists, 179 records" before the line about IDs and history.

These four are the part of the CHANGELOG's 0.13 MG section that was written under AB by the same build; the entries moved
there on 2026-11-10. Open: none.

**Follow-up (2026-11-10): an old address of a moved collection** (committed as `5e10ac49`). Reported by the user after an AI task's migration
moved the Person group's types from Person and passenger lists to Reference lists in workspace stops (release 0.3.10), and
added to the 0.13 build by the user. The old address `/apps/person-lists/views/person-type-tree` showed "person-type-tree
is not in this workspace's model" although the model has it, under the other application, with all 46 records. Cause:
`missingElement` (`routing/routes.ts`) looked only at the application the path names. `relocatedPath` now finds the one
other application of the same model holding the view, kind of record or navigation group key and rewrites only the
`/apps/<key>` segment, keeping the rest of the path and the query. The router replaces the history entry, so Back does
not loop. Home's remembered "continue" address moves the same way. A key held by none or by several applications still
shows the page. Frontend only. Checks: Vitest for `relocatedPath` and one router case; `npm run build`; the helper run
against stops's 0.3.10 model gives `/apps/reference-lists/views/person-type-tree`. The guide page
`use/open-a-retired-or-unavailable-workspace.md` stays correct for a missing element; a sentence on the relocation is
left for Codex.

## RV: Attributes of the relationship in views

**Status:** Approved by the user on 2026-11-09 (the design, delivered whole; small choices by recommendation).
Delivered 2026-11-09 (see the record below). Group label "Attributes of the relationship", as 0.13 RA words it.

**What changes.** A relationship's own attributes (the binding's `attributeTypeKeys`) were written only in the
Edit values dialog. Now:

1. **One shared component**, `RelationAttributes` (`features/objects/relations/`): the fields, the typed values,
   the save against the relationship's version and the conflict notice, used by the Edit values dialog, a matrix
   cell and a relationships table.
2. **Matrix cell.** `relationAttributes` on every cell record (live, change set, publication, history cells, in the
   same statement); the dialog shows them, edits them (own save, conflict notice), and a link or a create-in-cell
   sends the values entered.
3. **Relationships panel.** The attributes of the relation types the panel lists, for the anchor's type and
   direction, become columns after the related record's, visible by default and listed in the Display menu under
   "Attributes of the relationship"; empty on a row whose type does not declare them; no sorting by them.
4. **New view type `relationTable`** ("Relationships table", schema 0.10): configuration, validation with pointers
   (`application_rules._check_relation_table_view`), the workspace edge list read through the view (`fromObjectId`,
   `toObjectId`, `filter.<ref>.eq`, `sort`, cursors, positions and seek, `groupCounts`, `relationVersion`, all in SQL,
   live, in a change set and in a publication), `POST /relations/batch`, the `RelationTableView`, and the editor's
   **Add a view…** (kind Relationships table). No migration, no new table.

**Journey cases (from the specification, before the code).** J13.12 (a matrix cell: link with values and read them
back; a stale edit is refused with `VERSION_CONFLICT`; a change set shows its staged values, live the old),
J13.13 (a table's filter, sort, groups, paging by cursor and position, in live, a change set and a publication; a
foreign field refused), J13.14 (a batch sets values on three relationships, values kept, in a change set too; one
stale or invalid item refuses all, naming each), J33.20 (the table added to a draft, a bad column refused at its
pointer). Unit: the validation rules, each at its pointer. Frontend: `RelationAttributes`, the panel's columns, the
cell dialog's link payload and edit, `RelationTableView`, the editor's builders.

**Decisions taken by recommendation.**

| # | Choice | Why |
| --- | --- | --- |
| RV-D1 | A batch item's `attributes` are set over the stored values (`null` clears), where `PATCH` replaces | A bulk "set X to v" must not erase the other values |
| RV-D2 | Matrix values are edited in their own form with their own save and version, not inside the record's form | The record and the relationship have separate versions and one attribute type may serve both |
| RV-D3 | Filters on a table are equality only, on `filterable` attributes and names; `search` matches either end's name | The brief; the typed operators stay on collections |
| RV-D4 | A table's end types need not be listed in its application; its source collection is the `from` type | As a mapping grid |
| RV-D5 | With `groupBy` the group heading stands in the group's first row and the group end's columns leave the rows | A window measures rows by number; a separate heading row would break it |
| RV-D6 | A refused batch is `409` when a version was stale, else `422` | The caller refreshes on `409` |
| RV-D7 | The example model's table is over the mapping relationship, which declares no attributes | The starter has no relationship with attributes; adding one is a model decision |
| RV-D8 | The grid is a layout (`layout: "rows" \| "grid"`, default `rows`) of the existing view type; no new view type and no schema bump (0.10 is unreleased in 0.13) | The brief; one more setting of the same view, so validation, references, cascade and the outline need no change |
| RV-D9 | Both grid routes work on any `relationTable` view, whatever its `layout`; the layout only tells a client which to draw | API-first: the API reads the binding either way |
| RV-D10 | The grid read is `GET /workspaces/{key}/relation-grid` through the view (`applicationKey`, `viewKey`), as the rows layout is; rows are every `from` record matching the `from:` filters and `search`, sorted by a `from:` sort (any other sort field falls back to the name), columns at most 50 `to` records with the total, `relation:` filters keep the rows with a matching relationship at a shown column record | The brief; validation keeps `sortFields` as it was |
| RV-D11 | Without `attribute` the grid returns every stored value of a relationship, not only the view's `attributeColumns`; with it, only those | A cell's edit saves the stored values merged with the one changed (`PATCH` replaces); returning fewer would erase the rest. The UI picks which attributes are shown client-side and asks for all |
| RV-D12 | `POST /relations/grid-change` selects, counts and lists in PostgreSQL (rows crossed with the columns, left-joined to the relationships, one counting statement, one listing statement); the write is decided over the batch lookup and written through the write unit as one batch, as `POST /relations/batch` does | AGENTS.md: relationships are written only through the write unit; the set-based part is the selection and counting. A change over `ATOMIC_JOB_MAX_ITEMS` is `413` before anything is read into Python |
| RV-D13 | A dry run also decides every item (without writing) and answers what the apply would be refused for in `refused`, `200`; an apply with any refusal is `RELATION_BATCH_REFUSED` and writes nothing. The dry run is `413` too when the apply would be | The user sees refusals (cardinality, uniqueness scope, a minimum) before applying; "all pairs checked, no sampling" |
| RV-D14 | The record picker of the related-records menu is the matrix's `ColumnChooser`, exported and given a `max`; the picks are `gridColumn` address parameters; the attributes shown are the Display menu's (as the relationships table has it), not an address parameter | One component, no copies; the matrix keeps its limit of 20 |
| RV-D15 | The editor offers Layout in Add a view… (kind Relationships table) and as a **Layout…** action on a relationships table (`setViewProperty` `layout`); the default layout is not written out | The brief; `operations.ts` changed only by those two additions |
| RV-D16 | A yes/no value flips with one click through `RelationValueCell`'s `floating` mode (`FlagCell`); other values open the floating editor | The brief's addition; those components are not changed |
| RV-D17 | A grid's filters are its own `filterFields` plus, as `from:`/`to:` references, the filter fields of the table view each end type's collection opens with (the navigation's `opens` view, else the application's default view, else its table; the grid's application first; only `name` or `filterable` non-JSON attributes bound to the type). The engine resolves it from the model (`main_view_filter_fields`), so any client has the rule; values chosen are the grid's own, in its URL (the user, 2026-11-09). The rows and the column records are selected with the object list's filter and search code (`record_ids_selector`: typed operators, `related:`, search, the same errors), live, in a change set and in a publication, and joined to the relationships in SQL; a relationship's value takes the operators its type takes. The client uses the collection's `ObjectToolbar` and `FilterBar` for both ends, with `relation:` attributes as extra fields of the rows' bar | The user's requirement (2026-11-09): the same filter UI and behaviour as the main view; no grid-specific filter controls |
| RV-D18 | The grid uses the collection's selection (`useRecordSelection`, `SelectionBar`) and a dialog of its own built from the shared shell parts (`Modal`, `AttributeField`, `Choice`, `Section`, `DescriptionList`), not `BulkJobDialog`; "all matching" carries `exceptObjectIds`; the preview is the engine's dry run, read when the dialog's choices change; apply is worded "Apply" as the collection's | `BulkJobDialog` is a background-job flow (a preview job, then confirm); the grid's change is one synchronous all-or-none request with its own dry run. Making the job dialog generic would change every collection's bulk dialogs |
| RV-D19 | A cell saved reads its relationship again and patches its row; rows are memoised and the Display menu keeps which attributes are shown (no `gridAttribute` address parameter) | Measured lag: ticking one row drew all rows (110 ms of render for 250 rows); a cell save refetched the whole list |

**Checks.** `tests/journeys/test_j13_relation_attributes.py`, J33.20 in `test_j33_operations`,
`tests/unit/engine/model/validation/test_application_rules.py`; Vitest for the files above; the production build.
Groups: model, authoring, records, mapping, matrix, contract (the OpenAPI lock, `test_api_journeys`).

**Composable domains (ADR-032).** Generic and opens a door: any binding's attributes show and change in any view of
any model (a catalogue's price per channel, a rate per listing). No identity, attribute storage, history or
consumer `match` change; relation set versions and matrix states follow as for any relationship write.

**The grid (RG).** Added to RV by the user on 2026-11-09 from an approved mock-up, with the viewer picking which
related records and which attributes are shown: `layout: "grid"`, `GET /workspaces/{key}/relation-grid`,
`POST /relations/grid-change` (J13.15, J13.16), `RelationGridView` with its filter bar and bulk bar, the editor's
Layout, and RV-D8 to RV-D19 above. Composable domains (ADR-032): generic, and no identity, attribute storage,
history or `match` change; the bulk change writes as any relationship write.

**Commits (checked 2026-11-10).** `075675bb` (attributes of the relationship in views: the shared component, the matrix cell,
the panel's columns, the `relationTable` view, `POST /relations/batch`), `a2a672dc` (a matrix cell's relationship values
edited in place, `RelationValueField`; the cell is the matrix of RA-D3, covered by this package), `f9e82a2f` (the cell
dialog as a table), `538c4b97` (the relationships grid layout with filters and bulk change), `d69cb0bd` (Layout… opens on
the view's current layout) and `e696076c` (JSON columns and Yes/no grid filters fixed). The three fixes are under "Fixed
(Layout… of a relationships table, 0.13 RV)" in the CHANGELOG, where the Layout… bullet that sat under AW was moved.

**Guide pages.** Delivered by the waves `RV-GUIDE` (the pages for relationship values, the table, the grid, the cell
and the consumer API's `relation:` source, with their pictures) and `RV-GUIDE-FIX` (fifteen pages brought to the reference
model's own relationship values, with live examples under `guide/_coverage/live/rv-guide-fix--*`). The commits `0dcb0f0b` and
`9a341f83` hold the committed part of both; the rest of their notes and live examples are in the working tree. Notes in `guide/_coverage/notes/RV-GUIDE` and `RV-GUIDE-FIX`. RV-GUIDE found one product defect (a JSON attribute
offered as a table sort made the generated view invalid); it is fixed (CHANGELOG, 0.13 RV).

**Still manual / not built.** No sorting of a panel by a relationship attribute; no typed operators in a table's
filters; the browser acceptance runner (`test:browser`) for the table, the grid and the cell dialog is not written; the
grid's appearance at 390px, its sticky columns and group tints are not inspected in a browser
([open item 8](#open-for-013)).


## RA: Attributes of the relationship in consumer API related fields

**Status:** Raised on 2026-11-09 by an integration that needs, for each pair of related records, a value stored on the
relationship between them; added to the 0.13 build by the user on 2026-11-09 ("add to the 0.13 build as a wp"). 

**Why.** A relation binding can carry attributes of its own (`attributeTypeKeys` on the binding; the relationship's
values, edited on a record page's relationships panel with **Edit values**, `RelationsPanel.tsx`, `RelationFormDialog.tsx`).
They describe the pair, not either record: a local name one record has at the other, or yes/no flags that hold only for
that pairing. The management API reads and writes them, but the consumer API cannot publish them: a related block's
field sources resolve only against the related record (built-ins `id`, `name`, `objectType`, the related types'
attributes, `ancestor:<type>.<field>`; `projection_field_type` → `reference_value_type` in
`engine/model/consumer_contract.py`; [CONSUMER_API](CONSUMER_API.md), "Related fields"). An integrator who must know,
per related item, a fact about the pairing has no read for it, and the consumer API editor's field picker offers none.
This breaks [API first](../AGENTS.md): a capability the model holds and the management API serves is missing from the
consumer contract.

**What changes.**

1. **A source for the relationship's attribute.** In `object.related.<name>.fields`, the source
   `relation:<attribute-type-key>` reads that attribute's value on the relationship the item was reached through
   (`via`, outgoing or incoming alike). Example: `"fields": { "id": "id", "name": "name", "localName": "relation:local-name", "primary": "relation:is-primary" }`.
2. **Validated against the binding.** The source resolves only when the attribute type is in `attributeTypeKeys` of a
   binding of that relation, in the block's direction, from an exposed type. Otherwise the draft compile, install and
   model validation refuse it at the field's pointer (`/consumerApis/<key>/object/related/<name>/fields/<field>`),
   naming the field, the relation and the attribute. A `relation:` source anywhere other than a related block's fields
   and the `matchOn` that read them (RA-D2) is refused at its pointer.
3. **Typed like any field.** The output type is the attribute's value type (a boolean stays a boolean, a text a
   string) in the definition's output schema and the published OpenAPI; mixed source lists follow C-D19 as before.
4. **Read at run time.** Each related item carries the value stored on its own relationship, `null` when the
   relationship has none. The same in objects, lists, XREF and resolve answers, and in publication, `asOf` and
   change-set reads, which read the relationship's values from the same source as the records. Read in one set-based
   statement per block, with the related items, not per item.
5. **Matched like any related field (RA-D2).** An `onRelated` filter's `matchOn` and XREF's `alsoMatchThrough` may
   name `relation:<key>`; the value is compared with the relationship's attribute, so the item counts as matched only
   through that relationship.
6. **Offered in the editor.** The consumer API editor's field picker for a related block (and its `matchOn` pickers) gets a group
   **Attributes of the relationship**, listing the binding's `attributeTypeKeys`, beside the built-in, exposed-type
   and ancestor groups; choosing one writes `relation:<key>`. An existing `relation:` source shows by the attribute's
   name.

**Decisions.**

| # | Question | Recommendation |
| --- | --- | --- |
| RA-D1 | How is the relationship's attribute named in a source? | **A prefix, `relation:<attribute-type-key>`** (**decided by the user 2026-11-09 as recommended:** "okay then this can be built with d1 as you recommended"), beside the existing `ancestor:<type>.<field>`: one source string per field, the same place an integrator already looks, no new block in the definition. Alternative: a separate `relationFields` map on the block, which splits one item's fields across two maps |
| RA-D2 | Where is the source allowed? | **Asked by the user 2026-11-09 to include matching ("can it be included?"): included.** In a related block's fields, and in every `matchOn` that reads a related block's fields: an `onRelated` filter's `matchOn` (with `keepOnlyMatching`, `scoreOnlyMatching` and `crosswalk` as for any other field) and XREF's `alsoMatchThrough`. A value matches the relationship's attribute, so the item matches through that relationship only. Elsewhere (object fields, own `matchOn`, `under`/`linkedTo` filters) the source is refused at its pointer: there is no relationship per record there |
| RA-D3 | Relation-matrix cells | **Not in RA (the user, 2026-11-09: another session covers it).** Showing relationship attributes in the editor's views is delivered by its own session |

**Journey cases.** One API journey on the related-block fixture of the journey configurations (at least two
configurations, no configuration's keys named): a binding with a boolean and a text attribute of the relationship; one
relationship given values through the management API, another none; the consumer object, a list and an XREF answer
show the values on the first item and `null` on the second; the output schema types the boolean field as boolean; an `onRelated` filter on a relationship's text attribute keeps
only the item reached through the matching relationship. Unit tests of the contract: a valid source's type, an unknown attribute, an attribute the binding does not carry, the
incoming direction, the source outside a related block.

**Checks.** The consumer API journeys and contract groups (`python -m tests.affected`), the OpenAPI lock where the
published schema changes, `test_boundaries`, Ruff on the changed files; the consumer API editor's tests, frontend
format, lint and production build. **Migration:** none (the relationship's values are already stored). **Docs:**
[CONSUMER_API](CONSUMER_API.md) (sources, related fields, validation rules), the guide's consumer API editor page and
a guide rebuild, CHANGELOG.

**Composable domains (ADR-032).** Generic: any relation's attributes, any value type, any direction; no domain named.
It opens a door rather than closing one: catalogue and MDM-lite cases (a product's price at a channel, a role a party
has at a site) publish facts about a pairing the same way.

**Built (2026-11-09), RA.** As planned, with these choices:

- **Contract.** `RELATION_REFERENCE_PREFIX`, `split_relation_reference` and `relation_attribute_keys` in
  `engine/model/consumer_contract.py`; `projection_field_type` takes the block's route (relation, direction) and
  types `relation:<key>` as the attribute's value type. Refusals in `consumer_api_rules.py`: `INVALID_REFERENCE` at
  the field's pointer when no binding of the route carries the attribute, and at its pointer for the source in an
  object field, an own `matchOn` or an `under`/`linkedTo` filter. An XREF `firstOf` rule over a relationship's
  attribute reads text only (`INVALID_MODEL` otherwise); an `onRelated` filter compares any value type by its stored
  canonical form (a boolean as `true`/`false`).
- **Reads.** `ConsumerObjects._related` selects the relationship row's values in the related items' statement, from
  the source's own relationship table, so publication reads keep the published values. `asOf` filters records by
  their effective period and needs nothing of its own.
- **Matching.** A projection limit is an `ItemPredicate(entity, relation)`, so a `relation:` criterion is a
  condition on the relationship row; `keepOnlyMatching`, `scoreOnlyMatching` and `crosswalk` act per relationship
  only when a criterion reads one. XREF's `alsoMatchThrough` resolves its hits per relationship when a rule reads
  one; other entries keep the old statement. The relationship rows a rule reads have no index of their own; the
  read is bounded by the match limit and was not measured at volume.
- **Events.** An update of a relationship reaches the owner of every block that reads `relation:`. The audit entry
  does not say which attribute changed, so any update of the relationship counts.
- **Editor.** The draft outline lists each relation's `attributeTypeKeys` (`OutlineRelation`, OpenAPI lock
  re-baselined, [API](API.md)). The group **Attributes of the relationship** is in the related block's
  Add related / Fields… picker, the `onRelated` `matchOn` picker and the XREF field picker; a `relation:` source
  the picker does not offer shows under "Written by hand". Seen in the browser on the journey configuration's
  related block (the a4c consumer API runner passes but does not open that picker).
- **Tests.** Journeys in `test_j28_consumer_read.py` (values in object, list and XREF answers, `null` when unset,
  a publication keeping its values, OpenAPI types; a filter matching the relationship, not the related record; a
  boolean match; a crosswalk target), `test_j29_consumer_xref.py` (a promoted match and a scoring limit through the
  relationship), on both generated configurations; contract unit cases in `test_consumer_contract.py`; an event
  plan case; frontend picker cases. Runs: the four consumer files 115 passed, `-m consumer` and `-m contract`
  green apart from j23/j30 cases that passed when rerun alone (load, cause not established),
  `test_model_independence` fails on `ai-tasks/designFixture.ts`, which already fails before RA (still failing
  2026-11-10; [open item 5](#open-for-013)).
- **Docs.** [CONSUMER_API](CONSUMER_API.md) (sources, related fields, rules, events), two sentences in the guide's
  consumer API pages (the guide build and check pass), CHANGELOG.
## AW: An AI task's progress line in words, not the command

**Status:** Reported by the user on 2026-11-09 from a running workbook task and added to the 0.13 build by the
user ("add this to the 0.13 build"). **Delivered 2026-11-09.**

**What is wrong.** The task page's "Working on it" section showed the session's last shell command, lowercased and
without punctuation: the task folder, the `curl` call with its `Authorization` header and the token variable's
name, and an inline Python script. A command should never be shown. Cause: `engine/tasks/agent.py` defined
`_plain` twice. The first puts a call into words; the second, added later for comparing quotes with the person's
words, only lowercases and strips punctuation. The later definition replaced the first, so the progress line
received the command itself.

**What changes.** The progress helper is `_call_in_words`, and the stream reader uses it: a call to the API reads
"Reading stored … records", "Reading …" or "Writing …"; anything else reads "Working" (or "Working through the
workbook"). The quote comparison keeps `_plain`. No API, model or frontend change. A task already running keeps
the old code until the engine restarts.

## TN: An AI task named by what it asks

**Status:** Reported by the user on 2026-11-10 from the task page of a "Change this model" task
(`/settings/ai-tasks/750e8cd4-…`) and added to the 0.13 build by the user ("add this to the 0.13 build").
**Delivered 2026-11-10 (approved by the user the same day).** What was built is in "Delivered" below the checks.

**What is wrong.** A task given in words is titled by its words, cut at 80 characters
(`frontend/src/features/ai-tasks/aiTaskText.ts`, `taskTitle`): the page read "can you move the objecttypes and
objects under th person group in the person an…", with the person's typing and its typos, ending mid-word. The
draft the task makes is named the same way (`engine/tasks/design_job.py`: `"Assistant: " + words[:120]`), so the
model's draft list shows the same cut-off sentence. A workbook task is titled by its file name and is not affected.

**What changes (proposal).** The user's idea: let the assistant describe the request and use that.

1. **The session writes the title.** The task's own session states a short title with its first answer (a
   few words, the change it is asked to make, e.g. "Move types under the person group"); the engine stores it on
   the task as `title`. No second model call and no own loop: it is part of the turn the task already runs
   (see the AI rules: Claude Code inside refiroo, no own formats beyond what the task returns).
2. **Shown everywhere the task is named.** The task page heading, the task lists, the journey bar and JG's job group
   (if it names the task; to be checked at plan time) use `title`; the request's full words stay as the page's description ("You said: …"), never
   cut. The draft is named `Assistant: <title>`; a draft already opened is renamed once the title arrives.
3. **Until there is a title**, and for a task that stops before its first answer, the name stays as today (the
   words, cut at a word boundary rather than mid-word).
4. The API returns `title` on the task (null until written); the generated references and the guide page on AI
   tasks say so (guide text through Codex).

**Checks.** One journey in `test_j50_ai_reshape.py`'s group: a words task gets a title, its draft carries it, a
task stopped early keeps the words. One real try on the user's model with the provider `.dev/settings.env` names,
tokens and cost reported. Frontend build.

**Delivered (2026-11-10).**

- **Session and engine.** `proposal.json` takes an optional `title` (prompt `agent/20`, `agent.py` `_propose_prompt`; no second call, no new format). `_proposal_landed` stores it once as `ai_tasks.title` (`String(120)`, migration `20261125_01_ai_task_title.py`; `title_of` and `cut_at_word` in `engine/tasks/store.py`) and names the session's draft `Assistant: <title>` once (`design.draftNamed`; a person's later rename stays). `design_job.start` (the saved-layout path) names its draft by the title, else the words cut at a word.
- **API.** `AiTaskResponse.title` (null until written), `docs/API.md` "The task"; the OpenAPI lock re-baselined to `65a51db0…` (the working tree, other sessions' uncommitted schema changes included).
- **Where the task is named.** `taskTitle` (file name, else `title`, else the words cut at a word boundary with "…" within 80 characters, `cutAtWord`) names the task page heading and the confirm bar (`DesignCheckView`); the Jobs page group name is the same rule in SQL (`engine/jobs/origins.py` `_tasks`). "You said: …" stays uncut. **Left as they are:** the journey bar label and the trail's "Change this model" / "Change records" / "Change with the assistant" (`wordsTaskName`) name the journey, as "Import with the assistant" does for a file, not the task; there is no separate task list component.
- **Tests.** J50.72 `test_a_words_task_is_titled_by_its_session_and_its_draft_carries_the_title` in `test_j50_ai_reshape.py` (the group: 38 passed), `test_j24_job_groups.py` (4 passed), `test_openapi_contract.py` (12 passed), `aiTaskText.test.ts` and the `ai-tasks` and `jobs` frontend tests (157 passed), `npm run build`.
- **Try.** Task 105's words in `stops` (task 116, `agent/20`, Claude Code `sonnet`): title "Move the passenger lists under the People group", draft "Assistant: Move the passenger lists under the People group"; 1 turn, 778,678 tokens in, 11,403 out, 119 s, $0.44. Discarded afterwards.
- **Guide.** Wave brief `guide/_waves/TN.md` (Codex writes the prose and the guide is rebuilt after it); `CHANGELOG.md` entry "Changed (an AI task is named by what it asks, 0.13 TN)"; `USER_JOURNEYS.md` J50.72.

## NG: Relation matrices in navigation groups

**Status:** Built by the 0.13 build on 2026-11-09 (commit `30d29a8d`) without a package of its own, after the user's request of
2026-11-05 that is planned as [0.17 NG1](BASE_0_17_IMPLEMENTATION_PLAN.md#ng1-views-in-navigation-groups) ("a navigation
group places a view of its own, such as a relation matrix"). Recorded here 2026-11-10 so that the work belongs to a plan; 0.17's NG1 is
narrowed to what 0.13 left.

**What 0.13 delivered** (read from the commit, 2026-11-10).

1. **A relation matrix is an entry of a group of its own.** A group's `collections` holds collection keys and
   `{ "view": "<relation matrix view key>" }` in one shared order (schema 0.10, optional; a model without it keeps its content hash,
   so the change is compatible). The sidebar and the group page show the matrix by its view's name with a matrix glyph in its row
   type's hue, and it opens the matrix directly. The row type's entry stays and its view switch is unchanged; a matrix in no
   group stays inside its row type's entry.
2. **A collection has an opening view.** `navigation.opens` maps a collection to the view its entry opens on, in place of the
   application's `defaultView` for that collection.
3. **Validation** (`validation/application_rules.py`), each refusal at its pointer under `/applications/{app}/navigation`: a
   `view` entry that is no relation matrix of the application (`INVALID_REFERENCE`), a matrix in two groups (`INVALID_MODEL`),
   an `opens` key that is no collection or a view that is not one of that collection's.
4. **Operations.** `placeCollection` takes `view` in place of `collection` to place, move (at a `position` of the group's one
   order) or take out a matrix; the new `setCollectionOpening` sets or clears an opening view; several entries added in one
   request are one step and one undo; removing a matrix view takes its entry and its opening, and a key change keeps both
   (`authoring/cascade.py`, `references.py`); the draft outline lists each group's `entries`, `navigation.opens` and each view's
   `collection`.
5. **The editor opens a group.** A group's panel lists its entries with kind, opening view (changed in place) and state, a menu
   to move an entry up or down, to another group or out of its group, and **Add to group…** (a dialog with a search that adds
   several collections and matrices at once). The application panel's group table lists matrices and links each group's name
   to its panel; "In no group" offers **Add to a group…**; a relation matrix's menu in the Views table gains **Move to
   group…**; **Remove group** says its matrices go back inside their row type's entry (`ElementPanel.tsx`, `operations.ts`).
6. **Journeys and docs.** `test_j33_operations.py`, `test_j33_outline.py`, `test_kinds.py`, `ModelEditor.test.tsx`,
   `NavigationGroupPage.test.tsx`, `Explorer.test.tsx`; `docs/APPLICATION_MODEL.md`, `MODEL_AUTHORING.md`, `API.md`,
   `CURRENT_FUNCTIONALITY.md`, `USER_JOURNEYS.md`, the OpenAPI lock. **Guide pages:** the wave `NAV-GROUPS`
   (`guide/_waves/NAV-GROUPS.md`; four pages and four pictures; notes `guide/_coverage/notes/NAV-GROUPS`).

**Decisions the build took for matrices that 0.17's plan lists as open (PP-D11 to PP-D13).** One ordered member list per
group mixing collections and views (PP-D12's recommendation); schema 0.10, additive (PP-D13's recommendation); a matrix in a group
stays also among its row type's views, where PP-D11 recommended it leave. None was put to the user; they stay open there until
the user confirms them for the other view kinds.

**Composable domains (ADR-032).** Presentation only; no identity, attribute storage, history, bulk API, consumer `match` or mapping
coverage change.

**Not delivered here (stays in 0.17 NG1).** A group member that is a view of another kind (a table, a tree, a mapping grid, a
relationships table, a record page's view); **Move to group…** on those views' rows; a sidebar that leaves a grouped view out of its
collection's views (PP-D11); the group drop of the workbook canvas (PL3b) placing a view.

## CL: Images built in CI and CI as a quick gate

**Status:** Built 2026-11-07 and 2026-11-08 by the primary agent without a plan section; recorded 2026-11-10. The CHANGELOG
entry is "Added (images built in CI and CI as a quick gate, 0.13 CL)".

**What was delivered.**

- **Images (CL1, `530e4da3`).** `.github/workflows/images.yml` builds the engine and web images once for `linux/amd64` and
  `linux/arm64` on native runners, starts them with `compose.yml` (`.github/images/compose.smoke.yml`), checks `/health` and the
  application, and only then writes the tags in `ghcr.io/refiroo/refiroo-engine` and `-web`: `v<X.Y.Z>` (stable tag, only from a
  commit with a green CI run and only if it equals the version in `backend/pyproject.toml`), `main-<12 characters>` and `main`
  after a green CI run on `main`, `test-<label>` for a manual run; pre-release tags are not built.
  `.github/workflows/images-cleanup.yml` deletes untagged versions and old `main-*` and `test-*` versions each week
  (`aef8ae65`: the untagged age on a manual run).
- **CI is a quick gate.** The linter, the backend unit tests and the frontend tests and build on Ubuntu 24.04; the full suite runs
  on a developer's machine before a release (on GitHub it took a whole runner hour per push and ran out of memory). Steps on
  the way: parallel backend tests and a 40-minute limit (`87428ca4`), Ubuntu 24.04 and failure and slow-test listings
  (`d94c1373`), resource log and junit (`97d46cfd`), four runners (`e0e29066`, undone by `809a92eb`, which settled on the quick
  gate).
- **Test and setting fixes CI found**, each in its commit: frontend tests wait 5 s and the inbox test waits for its stream
  (`4eb12288`), the Jobs page tests mock the workspace list (`0d761cf2`), the ImportDialog test waits longer (`718a3bc1`),
  the API page build puts its settings back and stale template checks (`ea26ac8e`), the boundary allowlist for the API page build
  and a J31.2 that keeps a real database password (`4d1701f2`), the statement budgets count 0.16's client lookups
  (`e0e29066`, `test_batch_statements.py`, `volume_fixture.py`).
- **One product fix, 0.13 RL.** A relations panel that comes to list several record types drops its ancestor sort, which
  needs one type (`809a92eb`, `model/authoring/layout.py`); its CHANGELOG bullet moved to the RL entry.

**Commits:** `530e4da3`, `87428ca4`, `d94c1373`, `4eb12288`, `97d46cfd`, `e0e29066`, `809a92eb`, `aef8ae65`, `0d761cf2`,
`718a3bc1`, `ea26ac8e`, `4d1701f2`. **Open:** none. The release step R still checks the tag builds (DOC11's clean-host rehearsal found
that `v0.16.0` cannot be built; the images workflow now builds every `v*` tag).

## MS: Mail through Microsoft 365 (Graph)

**Status:** Asked for by the user on 2026-11-10 ("beside of smtp is it possible to add an email option for ms azure
graph?", then "add this to the 0.13 as a package"). **Approved by the user 2026-11-10 with MS-D1 to MS-D4 as
recommended ("the above accepted with recommendations, build it please"). Delivered 2026-11-10 except the real try** (open item 9). No separate mock-up: the page
keeps Settings › Mail's layout and adds the method choice and its fields.

**Why.** 0.12's [D419](BASE_0_12_IMPLEMENTATION_PLAN.md) chose SMTP only ("no mail API of a provider (a later package
may add one)"). An organisation on Microsoft 365 often cannot use SMTP with a user name and password: Microsoft is
retiring basic authentication for SMTP AUTH in Exchange Online (Message Center MC786329, updated 2026-01-27: the
March–April 2026 removal is on hold; basic auth off by default from late December 2026, re-enable possible; the final
date to be announced in the second half of 2027), and its
recommended way for an application to send is Microsoft Graph. Today such an organisation needs an SMTP relay connector
in Exchange to use refiroo's mail at all. This package extends D419 with a second way to send; SMTP stays as it is.

**What is there now** (read 2026-11-10). The outbox and the sender thread (`engine/mail/sender.py`, `outbox.py`) queue,
lease, retry with a growing delay, give up after 24 hours and share a server-wide failure across the leased messages;
none of that depends on SMTP. The protocol is all in `engine/mail/smtp.py`: `build` makes the MIME message (text, HTML,
inline `cid:` operator images), `deliver` sends it and turns a failure into a `MailError` with a kind (`connection`,
`tls`, `login` server-wide; `recipient`, `sender`, `rejected` per message). The settings are one row
(`mail_settings`, `engine/mail/settings.py`: host, port, security, user, sealed password, from address, application
address), set through `GET/PUT/DELETE /mail-settings` and `POST /mail-settings/test` on Settings › Mail
(`frontend/src/features/settings/MailPage.tsx`). Guide pages: `administer/mail.md`, `run/sign-in-and-mail-setup.md`.

**What changes (proposal).**

1. **A sending method on the mail settings.** The one settings row gains `method`, `smtp` (today's fields) or
   `microsoft365`: tenant ID, application (client) ID, a client secret or a certificate (sealed with
   `SECRETS_ENCRYPTION_KEY` like the SMTP password, never answered), the sending mailbox (the from address). One
   method is active at a time (MS-D1). A migration adds the columns; an existing row is `smtp`.
2. **A Graph transport beside `deliver`.** It takes a token with the client-credentials grant from
   `login.microsoftonline.com/<tenant>`, keeps it until shortly before it expires, and sends with
   `POST /users/<mailbox>/sendMail` with the MIME message `build` already makes (base64, `text/plain`), so the HTML and
   inline images are the same as through SMTP. The MIME route has no `saveToSentItems` (Microsoft's `sendMail`
   page, read 2026-11-10: "This method saves the message in the Sent Items folder"; the switch exists only in the JSON
   form): system mail lands in the mailbox's Sent Items, and the pages say so. `httpx` is already a dependency; no Microsoft library is added (MS-D3).
3. **Failures in the kinds the sender knows.** The token refused, consent missing or the mailbox not allowed (401, 403,
   `AADSTS…` codes) is `login`, server-wide; Graph out of reach is `connection`; 429 and 503 wait at least the
   `Retry-After` Graph gives; a mailbox that does not exist is `sender` and waits, as with SMTP (decided 2026-11-10 by recommendation: a mistyped mailbox must not lose a queued reset mail). Each failure is one sentence an
   administrator can act on ("The app has no Mail.Send permission with admin consent"), never the secret or Graph's raw
   body.
4. **A recipient is not checked at sending.** Graph accepts a message and reports a bad address later as a bounce to the
   sending mailbox, as an SMTP relay does (only a server that is the recipient's own, or checks addresses, refuses at
   once). A message Graph accepted shows as sent; the page and the guide say that bounces go to the sending mailbox
   (MS-D2).
5. **Settings › Mail** offers the method; choosing Microsoft 365 shows its fields and a short list of what the
   administrator sets up in Entra (an app registration, `Mail.Send` application permission with admin consent, and an
   application access policy or RBAC for Applications that limits the app to the one mailbox, without which the app can
   send as any mailbox in the tenant). **Send test mail** works for both methods. Mock-up with the plan (UI package).
6. **API and docs.** `MailSettingsResponse` and the update command carry `method` and the Microsoft 365 fields; the
   OpenAPI lock, `docs/API.md`, `docs/OPERATIONS.md` "Sending mail", `CHANGELOG.md`; the guide pages above through a
   Codex wave (`guide/_waves/MS.md`), then a guide rebuild.
7. **Managed identity, a third credential (MS-D5).** Added by the user 2026-11-10 after the first build ("can we add
   managed identity authentication option beside of the certificate?", then "yes, so with ms365 there are different
   authentication options offered, so they can choose"). Only when refiroo runs in Azure (Container Apps, App Service,
   a VM); the page says so. Two modes, read from Microsoft's
   [Configure an application to trust a managed identity](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-config-app-trust-managed-identity)
   (updated 2026-09-29):
   - **Managed identity in the organisation's tenant.** The engine asks the Azure host for a Graph token
     (`resource=https://graph.microsoft.com`) and sends with it; no tenant token request. The identity is the host's
     system-assigned one, or a user-assigned one named by its client ID. `Mail.Send` is given to the identity's service
     principal with a Graph app-role assignment (Entra has no portal button for it; the guide shows the command), and the
     mailbox access policy names the identity.
   - **Managed identity as an app's federated credential (refiroo hosted in another tenant).** A user-assigned identity
     (the only kind Microsoft allows here) is a federated credential of a multitenant app registration in the hosting
     tenant (issuer `https://login.microsoftonline.com/<hosting tenant>/v2.0`, subject the identity's principal ID,
     audience `api://AzureADTokenExchange`, `…USGov` or `…China` by cloud). The customer's admin consents the app in
     their tenant. The engine takes an identity token for `api://AzureADTokenExchange/.default` and uses it as the
     `client_assertion` of the client-credentials grant at the customer's tenant: the certificate's path with another
     assertion. Another cloud is not supported by Microsoft.
   - **The Azure host's token endpoint.** `IDENTITY_ENDPOINT` with `IDENTITY_HEADER` (App Service, Container Apps), else
     the instance metadata endpoint `http://169.254.169.254/metadata/identity/oauth2/token` with `Metadata: true` (a
     VM). No secret is stored. A host without either is a `login` failure that says refiroo does not run with a managed
     identity. AKS workload identity (a token file) is not included.

**Decisions (approved by the user 2026-11-10 as recommended).**

| # | Question | Decision |
| --- | --- | --- |
| MS-D1 | One method or both at once? | **One active method on the one settings row.** Why: an organisation sends from one place; a fallback from Graph to SMTP would hide a broken setup and needs a rule for which failures switch. Cost: switching method replaces the other method's saved fields |
| MS-D2 | Does refiroo read bounces? | **No, for either method; the page and guide say bounces go to the sending mailbox.** An SMTP relay bounces later too, so this is not Graph's alone. Reading bounces is a feature of its own: polling the mailbox or a renewed Graph subscription to a public address, parsing delivery reports (told apart from out-of-office and delay notices), matching each to its outbox message by the quoted `Message-ID` (not kept today), a new "bounced" state after "sent", and cleaning up a mailbox people may also use. The permission (`Mail.Read`, limited to the one mailbox by the same access policy) is the smallest part. Cost: a mistyped address shows as sent in refiroo; the administrator sees the bounce in the mailbox |
| MS-D3 | Microsoft's library (MSAL) or plain HTTP? | **Plain `httpx`.** The client-credentials grant is one form post; no new dependency in the shared venv. Cost: the certificate assertion (a signed JWT) is built by the engine, with the `cryptography` already installed |
| MS-D4 | Client secret, certificate or both | **Both.** Many tenants forbid client secrets by policy; a secret is what a small organisation starts with. Cost: a certificate upload field and its expiry shown on the page |
| MS-D5 | Managed identity | **Decided by the user 2026-11-10: a third credential beside secret and certificate, with both modes** (point 7): the identity in the organisation's tenant, and a user-assigned identity as a multitenant app's federated credential for refiroo hosted in another tenant. Why: no secret to store or renew where refiroo runs in Azure; the second mode is the hosting case (one instance per organisation in refiroo's Azure, the customer's Microsoft 365 elsewhere). Cost: works only on an Azure host; the real try needs one |

**Checks.** One journey beside `test_j46_mail.py`: an administrator sets Microsoft 365, a test mail and a reset mail
reach a local stub of the token and `sendMail` endpoints with the expected MIME; a refused token is a server-wide
`login` failure on every leased message; a 429 waits its `Retry-After`. The token and Graph addresses are settings with
the global defaults, which also serves national clouds and lets the journey point at the stub. Frontend build. **One
real try** sending through a real Exchange Online mailbox. **Checked 2026-11-10:** the refiroo Azure tenant has no
Microsoft 365 or Exchange Online licence (`subscribedSkus` empty), so it cannot be tried there; nothing was created in it.
The user will ask the organisation refiroo is being deployed for to set up the managed identity method; the real try
is made there, managed identity only (the user, 2026-11-10). Managed identity's checks: both modes against a local
stand-in for the Azure host's token endpoint (both `IDENTITY_ENDPOINT` and the metadata form), the federated mode's
assertion reaching the tenant token stub, and the "no managed identity here" failure.

**Delivered (2026-11-10).**

- **Engine.** `engine/mail/graph.py` (token by secret, certificate assertion, managed identity `direct` or as a federated `client_assertion`; the Azure host's `IDENTITY_ENDPOINT` or IMDS; cached tokens; failures in the sender's kinds, `Retry-After` kept), `engine/mail/transport.py` (SMTP or Graph), `smtp.py` (`MailError.retry_after`), `sender.py`, `settings.py` (one method; the other's fields cleared), `identity/resealing.py`. Migrations `20261126_01_mail_microsoft365.py`, `20261127_01_mail_managed_identity.py`. A Graph 404 (no such mailbox) waits like SMTP's `sender` (decided 2026-11-10 by recommendation). The MIME `sendMail` has no `saveToSentItems`: system mail lands in the mailbox's Sent Items.
- **API.** `GET/PUT /mail-settings` carry `method`, `credential`, `identityMode`, the Microsoft 365 fields; `422 MAIL_CREDENTIAL_REQUIRED`, `MAIL_CERTIFICATE_INVALID`; the OpenAPI lock re-baselined.
- **Settings › Mail.** One **Sign in with** menu of four entries (approved by the user 2026-11-10, layout A), each showing its own fields; the Entra checklist and "Other Microsoft clouds" folded below (`MailPage.tsx`, `mailText.ts`, `settings.css`).
- **Tests.** J46.11 `test_j46_mail_microsoft365.py` against `tests/graph_server.py` (16 passed); the J46 mail group (95), contract and startup (49; `test_startup` no longer reads pytest's argv); `MailPage.test.tsx` (11); `npm run build`. Browser: `m1-mail.mjs` section 7 (`M1_M365_ONLY=1 M1_MODELS=starter`), 1440 and 390 px, light and dark: 48 checks, axe 0, no sideways scroll; generated-b and a saved Microsoft 365 configuration not run in the browser.
- **Docs and guide.** `docs/API.md`, `OPERATIONS.md`, `CURRENT_FUNCTIONALITY.md`, `USER_JOURNEYS.md` J46.11, `CHANGELOG.md`; guide waves `MS` and `MS-MI` (Codex, 1.18M and 2.15M tokens), guide rebuilt. Pictures of the Microsoft 365 form are not in the guide yet.
- **Open.** The real try (item 9).

**Composable domains (ADR-032).** Operations only; no model, identity, attribute storage, history or consumer API change.

## FX: Fixes found during the 0.13 build

**Status:** Recorded 2026-11-10. One row per fix that no package names, with where it was found and where it is. A fix that
a package owns is named there, not here; the CHANGELOG headings carry "0.13 FX". Every other commit since `v0.16.1-alpha.1` is
named by a package in the table above (checked with `git log --oneline v0.16.1-alpha.1..HEAD`).

| Fix | Where found | Where it is |
| --- | --- | --- |
| An AI task's progress line showed the session's shell command (`_plain` defined twice in `tasks/agent.py`) | reported by the user from a running task, 2026-11-09 | package [AW](#aw-an-ai-tasks-progress-line-in-words-not-the-command), uncommitted; not repeated here |
| A tall Display popover of a relationship or collection panel looked cut off, and no popover opened with no height on a scrolled page | not recorded in the CHANGELOG | `frontend/src/ui/ControlPopover.tsx`, `styles/layout.css`; uncommitted; CHANGELOG "a tall Display popover looks cut off, 0.13 FX" |
| The assistant re-checked a stale copy of its own corrected draft (sessions keep loaded rows after a commit), so the task failed after the session had fixed the draft | the user's AI task `cbd71b4b`, 2026-11-10 | `app/engine/tasks/agent.py` (`_proposal_landed`, `_run_turn`), `tasks/store.py` (`load_task`), `tests/journeys/test_j50_ai_reshape.py`; commit of 2026-11-10; CHANGELOG "the assistant re-checked an outdated copy of its draft, 0.13 FX" |
| On a change set page the pinned band held the whole change set bar, the submit comment and the model-mismatch notice (the bar's `BelowContextBand` sat outside the slot provider), covering about half the window | reported by the user on a change set page, 2026-11-10 | `frontend/src/app/AppShell.tsx`, `features/workspaces/ChangeSets.tsx`, `styles/components.css`, `app/App.test.tsx`; commit of 2026-11-10; CHANGELOG "the change set band stays compact, 0.13 FX" |
| Apply, Install and Load ended in "Release '…@0.3.17' is already installed with different content" with no step forward: the editor proposed the base's next version without knowing which versions the assistant's drafts had installed, and the draft then kept the taken version | reported by the user on the stops workspace's Apply, 2026-11-10 | `engine/model/releases.py` (`next_free_version`), `model/authoring/outline.py` (`suggestedReleaseVersion`), `tasks/design_job.py`, `routers/model_management.py` (409 `freeVersion`), `features/model-editor/ReleaseVersionConflict.tsx` and the Apply, Install, Load dialogs and `ModelDraftEditor.tsx`, `tests/journeys/test_j36_12_workspace_draft.py`; commit of 2026-11-10; CHANGELOG "a taken release version has a way forward, 0.13 FX" |
| A words task had no neutral name before its proposal said what it changes | the fresh reader (DOC11 assistant journey, finding 7, 2026-11-09) | package DOC11 (`aiTaskText.wordsTaskName`), not FX: its CHANGELOG bullet stays in the DOC11 assistant entry |
| Jobs named the workspace by its key; the client's webhook panel showed "Not Found" with webhooks off; a cancel confirmation repeated its button; the assistant's closing note named commands and ids | not recorded; commit of 2026-11-06 | `c4ba7d8d` (`JobPage.tsx`, `JobsPage.tsx`, `ClientsPage.tsx`, `tasks/agent.py`); CHANGELOG "jobs, client webhooks, the assistant's note, 0.13 FX" |
| A mapping row with several targets was called ambiguous where the relation lets a source hold many | not recorded; commit of 2026-11-05 | `92202c27` (`reads/mapping_scope.py`, `projections/mapping.py`, `MappingGridView.tsx`); CHANGELOG "mapping coverage, 0.13 FX" |
| The Webhooks screen named a setting startup refuses (`CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` for `SECRETS_ENCRYPTION_KEY`); `restore_check` printed a refused URL's password | not recorded; commit of 2026-11-08 | `46b6ed95` (`WebhooksPage.tsx`, `cli/restore_check.py`); CHANGELOG "setting name on the Webhooks screen, 0.13 FX". The same commit's draft dry run that reads its own profile is [AT](#at-the-assistant-starts-from-the-engines-reading) |
| Choosing a relation matrix's columns was explained only as a step of the coverage check | the guide's own pages, 2026-11-05 (the wave's brief) | the wave `MX-COLUMNS` (`use/relation-matrices`, `guide/use/fill-in-a-relation-matrix`; notes `guide/_coverage/notes/MX-COLUMNS`); CHANGELOG "relation matrix columns, 0.13 FX". No product change |
| Three lines the formatter wrapped | the formatter | `engine/records/relations.py`, `management/routers/mapping.py`, one message in `models/commands.py`; uncommitted, no behaviour |

Not FX, and where they are: `f173c53a` is DOC10 (the guide's pictures and captions) and DOC11 (its first weaker run and the
container fixes it found, CHANGELOG "the assistant in a container, 0.13 DOC11"); `ba8f78c5` is DOC12 (W4) and TH; `2f9a0791` is
DOC10; `9a341f83` and `0dcb0f0b` are the RV and RA guide pages; `224de55d` and `ab47574c` are plan text (the guide home's
title, 0.17 NG1).

## The writing rules

These go into `guide/AGENTS.md` in DOC1; they are the contract between the briefs and the writer.

1. **The brief is the boundary.** State only what the brief's sources support. A fact not in a source is
   not written. When the brief seems wrong or incomplete, stop and say so on the page's review list; do not
   fill the gap from memory of how such systems usually work.
2. **One reader, one purpose per page**, in the page kind's template; kinds are not mixed.
3. **Plain language, product terms.** "refiroo" for the application and anything a person sees; "the
   engine" in technical text ([OPERATORING](OPERATORING.md)). The glossary's words, one term per concept. Short
   sentences. No package IDs, decision IDs, delivery history or "since 0.x" except on release and upgrade
   pages. Do not rename a setting, a package or an error code.
4. **Examples are copied, not composed.** Every request, response, command and model fragment comes from
   the brief's tested examples, unchanged. Do not alter an example to make the prose read better; ask for
   the brief's example to change.
5. **Limits where they bite.** Every limit a task meets is on the task's page, with the setting that changes
   it and a link to the limits reference.
6. **Say what to do on an error.** A step that can fail names the error code, what it means and what the
   reader does next, linking to the reference entry.
7. **Authentication is shown.** Every API example carries its credentials as the tutorial established.
   Never put a real secret in an example; use the placeholders the brief gives.
8. **Domain names come from the running example only.** Examples come from the guide's reference domain
   ([DOC-D17](#decisions)) in `guide/samples/`; the bundled starter model appears only on the page that
   tours it. Never use, quote or hint at a private model or a source export; never name another
   organisation's system, except the reference domain's sources as its brief cites them.
9. **Describe what exists.** No future feature, no "will". A planned capability appears only in "What it
   does not do", with no date.
10. **Do not touch what is not yours.** Edit only the files in the wave's list. Do not commit. Do not change
    code, tests, or any page outside the wave. If you find a defect in the engine, write it in the page's
    review list.
11. **The capability first, the domain second.** State each capability in generic terms, then show it in
    the reference domain. The domain is the example, never the definition: no page makes stops,
    municipalities or timetables sound like part of the product. The fact-check looks for this.

## Risks

- **A fluent page that is wrong.** The mitigations are the brief's closed sources, the executed examples,
  the independent fact-check and the user's read. A page that cannot be supported is shortened.
- **The guide drifts after release.** The AGENTS.md step, the `docs` group (a change that breaks an
  example fails), the coverage check (a new setting, error code or command without a page fails) and the
  generated references. 0.14 and 0.15 change the reference and the screens; both rerun the screenshot
  command, and 0.14's `/docs` content is linked, not copied.
- **Volume.** The inventory is large. The coverage matrix and the waves make the progress measurable, and
  a topic dropped from the guide is dropped in an exclusion with a reason, in the open.
- **Operator commands that cannot run in the `docs` group.** Marked `unrun` and rehearsed once on a clean
  host (DOC11); the page says which commands those are.

## Decisions

All decided by the user on 2026-10-26: DOC-D11, DOC-D12, DOC-D15 and DOC-D16 in conversation, the rest by
approving the recommendations, and DOC-D13 by choosing the recommended option.

| # | Question | Decision |
| --- | --- | --- |
| DOC-D10 | How is the guide navigated? | **Approved 2026-10-26.** By the reader's goal (Start here, How refiroo works, Tutorials, Use, Model, Integrate, Run, Administer, Reference, About), each page labelled with its Diátaxis kind. A steward looks for "correct a record", not for "how-to guides". Alternative: four top-level sections by kind, which suits the framework but makes a reader choose the kind before the goal |
| DOC-D11 | Does 0.13 include the foundation? | **Decided by the user 2026-10-26: yes.** The earlier packages DOC1–DOC3 were never built, so 0.13 delivers the whole guide: foundation, generated reference, concepts, tutorials, how-tos, operating, security, screenshots, the fresh-reader check and publication |
| DOC-D12 | What about the management API reference? | **Decided by the user 2026-10-26: no double writing.** 0.14's Track V writes the management API reference on `/docs`. The guide's pages (API conventions, the integration how-tos) link to it for every operation and state the conventions and the sequences in prose only |
| DOC-D13 | Who writes the error catalogue? | **Decided by the user 2026-10-26: the recommendation.** The catalogue is written once, in 0.13's DOC2, and 0.14 reuses it. 0.14's V-D5 plans one catalogue entry for every error code, shown on `/docs`; DOC2 plans an error-code reference in the guide. Writing both is double writing. Write it once, in 0.13's DOC2, in the location 0.14's V-D1 recommends (`backend/app/management/reference/content/errors.md`, shipped with the engine; V-D1 is still open in 0.14, so DOC2 asks the user to confirm the location before writing it), so the guide renders it and 0.14's `/docs` merges the same file. 0.14's V3 then keeps its other parts (the per-operation error listing, the completeness check) and drops the catalogue text. Cost: about 286 codes are written in 0.13, work 0.14 would have done anyway. Not chosen: leaving the catalogue to 0.14 and listing only status and message in the guide |
| DOC-D14 | What is the product called? | **Approved 2026-10-26.** "refiroo" for the application and everything a reader sees, "the engine" in technical text, per [OPERATORING](OPERATORING.md). DOCUMENTATION_PLAN's older wording ("RDM Engine") is corrected. Settings, packages and codes keep their names |
| DOC-D15 | Who writes? | **Decided by the user 2026-10-26: Codex writes the pages and the descriptions;** the primary agent builds the mechanism, writes every brief, runs the checks and the fact-check. Why: the user judges Codex the better writer. Cost: the page quality depends on the briefs, which is why DOC3 is the largest piece of the primary agent's work |
| DOC-D16 | Are installation, deployment, configuration, security and architecture in scope? | **Decided by the user 2026-10-26: yes, all of them, and Codex writes them too.** The sections "How refiroo works", "Run refiroo" and "Administer access and security" hold them; the earlier plan covered them only in part |
| DOC-D17 | The running example | **Revised and decided by the user 2026-11-02** (was: the bundled starter model plus small samples, and countries, regions, cities for tutorial 2). The guide's running example is one researched reference domain built from open data: the public transport stops of Graubünden, Switzerland (the Didok service-point register of opentransportdata.swiss, attribution; municipality names in five languages and second-system codes from Wikidata, CC0; a fictional ticketing system's codes and a fictional messy operator workbook, labelled fictional). Three applications: Network (canton > district > municipality > stop, operators, modes), Systems (code mappings), Names (translations). Two sizes from the same data: about 480 records for the `docs` group and tutorials, about 3,200 for a Docker reference instance that also serves DOC10's screenshots and DOC11's reader. Loaded through the public API only. Tutorial 2 builds the Network part from an empty model. GTFS route types are not used (licence unverified). The engine still ships the starter model; the guide has one page touring it. Proven by a prototype on 2026-11-02 (`prototypes/guide-reference-swiss/`: model valid, full load 18 s through the API). Open: the publisher's answer on whether a dated snapshot meets the terms' "update at the same frequency" clause (e-mail drafted 2026-11-02); if not, the repository ships the fetch script and no snapshot. No private model or export is ever used |
| DOC-D18 | The site generator | **Approved 2026-10-26.** The primary agent compares generators in DOC1 against the listed criteria, with evidence, and reports the choice before the layout is committed. **Decided by the user 2026-11-02: Starlight (Astro).** Compared with Zensical, Docusaurus, VitePress, Sphinx with MyST, and MkDocs with Material (ruled out: Material in maintenance mode, end of life 5 May 2027; MkDocs core unreleased since August 2024). Starlight has static search (Pagefind), sub-path serving (`base`), custom front matter validated by its content schema (the stub refusal), MIT, active releases. Cost: a Node project in `guide/` used only to build; the engine image carries the built files, not Node. No built-in versioning: the public site holds one build per release in its own directory; the engine serves the one build of the version it runs. Offline loading and accessibility are checked on DOC1's first page |
| DOC-D19 | Is a non-Docker installation documented? | **Approved 2026-10-26.** Document only what is supported and tested. The Docker Compose reference installation is. If installing from source for production is not supported, the page says so and points to the developer instance, which OPERATIONS already describes as a development setup. Confirmed in DOC1: the page states what is supported after checking it |
| DOC-D20 | Sizing figures | **Approved 2026-10-26.** The sizing page states only measured figures (0.11's volume measurements, POSTGRESQL_BUDGETS), each with the measurement's date and conditions. Where nothing was measured, the page says "not measured" rather than advise. A sizing guess in a guide is read as a promise |
| DOC-D21 | Does 0.13 document 0.16's AI integration? | **Decided by the user 2026-11-02: yes.** 0.16's work is on main ahead of 0.13's release, so the guide covers it. It is written in its own wave (DOC9A) after 0.16's R, since 0.16's screens and API are still changing; the earlier waves do not wait. Cost: 0.13's fresh-reader check, publication and release follow 0.16's R |
| DOC-D22 | Where does the error catalogue live? (DOC-D13 asked DOC2 to confirm) | **Decided by the user 2026-11-02: the recommendation.** `backend/app/management/reference/content/errors.md`, shipped with the engine; the guide renders it and 0.14's `/docs` merges the same file (0.14's V-D1 location for this file) |
| DOC-D23 | When does Codex edit files 0.16 also edits? | **Decided by the user 2026-11-02: the recommendation.** DOC2's description batches run in a window the user names when no 0.16 session runs, and each batch is committed before the window closes. Guide pages need no window |
| DOC-D24 | Licences of the guide's shipped libraries | **Decided by the user 2026-11-02: the recommendation.** Python-2.0, BlueOak-1.0.0 and CC0-1.0 join the notices script's allowed list (all permissive, compatible with AGPL distribution) |
| DOC-D25 | The private-model names for the banned-terms check | **Decided by the user 2026-11-02: the recommendation.** The list stays empty: Codex works only from the reference domain and never sees a private model. Names can be added at any time with `node tools/check.mjs hash-term` |
| DOC-D26 | AI in the reference instance | **Recommendation (2026-11-02), not yet decided by the user.** Not now. At DOC9A the reference instance gets an optional, off-by-default AI setup (`AI_PROVIDER=claude` and the assistant's command, key in the git-ignored `guide/reference/.env`), each try reported with tokens and cost; the `docs` group uses the engine's offline provider. Which key, and who pays, is decided then |

## DF: Findings of the depth waves

**Status:** Approved by the user 2026-11-07 ("okay" to the plan and the recommendations DF-D1, DF-D2). **Delivered 2026-11-08.** Beyond the plan: a kept version derives its own events (`consumer_api = "<key>@v<n>"`), raising keeps the version as the active release serves it, and the install and activate dialogs warn when a version stops being served. Not shown in a screenshot: the Webhooks screen with no consumer API that has events (the reference instance has one). The user asked on 2026-11-07 to fix the open findings of
CP's depth waves in a package of their own. The four plain defects (AI Values text, tree edit, Oriented help,
`EVENTS_EXPIRED` message) were already fixed on 2026-11-07 (CHANGELOG "Fixed (findings of the documentation waves)").

**Why.** The waves documented what refiroo does and listed where it falls short of what a reader expects. Three of
those are missing capabilities, and the exit gate no longer describes how 0.13 was built.

### DF1: Workspace events from the Webhooks screen

The engine accepts a subscription to a workspace's own events (`source: "workspace"`, `events/subscriptions.py`);
the Webhooks dialog creates consumer API subscriptions only (`WebhookDialog.tsx`, Source section) and only shows an
existing workspace subscription. The dialog's Source section gets a first choice, **Consumer API** or **Workspace
events**. Workspace events show the workspace select and the workspace event types; consumer API stays as today.

```
Source
  ( ) Consumer API     (•) Workspace events
  Workspace  [ Default (default) v ]   Changes to its live data are delivered.
Events
  [x] All workspace events   or pick: [ ] Change set published  [ ] ...
```

### DF2: Rotate a deactivated client's secret

`ClientsPage.tsx` hides **Rotate secret** while a client is inactive; the engine allows it (`clients.py`
`add_secret`). After a leak the administrator deactivates the client, rotates, then reactivates it with only the new
secret valid. The button is shown for inactive clients too, with the same dialog; the inactive client's note says a
new secret takes effect when it is reactivated.

### DF3: An earlier contract version served beside the new one

`docs/COMPATIBILITY.md` promises a consumer API's old contract version is still served after a breaking change;
`reads/consumer_objects.py` serves only the version in the active model. Design (DF-D1, approved 2026-11-07: kept in the model by the administrator, not taken automatically from the previous release):

- A consumer API definition may keep **earlier versions**: frozen copies of its definition at an older
  `contractVersion`, each with an optional **sunset date**. When a model administrator raises the contract version
  in the editor, the editor keeps the previous one by default ("Keep serving version 1").
- Every route `/api/consumer/{consumerApi}/v{n}/…` and its OpenAPI document answers for each kept version from the
  current data, through that version's definition, with the `Deprecation` and, when set, `Sunset` headers.
  Subscriptions on a kept version keep receiving events in its shape.
- Model validation checks a kept version against the current model like the current one, and refuses the release
  with the version and the missing type or attribute named when it reads something the model no longer has.
- A kept version stops when the administrator removes it from the model; the sunset date is announced, not enforced.
- The editor's consumer API panel lists the kept versions, with their sunset date and **Stop serving**.

The notice period (DF-D2, approved 2026-11-07: the administrator's, not enforced by the engine): 12 months and two minor releases is refiroo's own promise for its contracts. A consumer
API contract is written by the instance's model administrator, so COMPATIBILITY.md says the engine serves the
earlier version beside the new one until the administrator removes it, and the administrator chooses the notice.

### DF4: The exit gate matches how 0.13 was built

**Delivered 2026-11-07** (exit gate below and ROADMAP's 0.13 section).

The gate and the roadmap's 0.13 wording are corrected: the guide is served at `/docs`; the management API reference
is generated at `/docs/api` from the code (not left to 0.14); the coverage inventory is the one made from the code
(`guide/tools/inventory.py`), checked by `npm run verify`; the fresh-reader check (DOC11) stays required.

### DF5: A type's preview follows the application it was opened from

**Status:** Reported by the user on 2026-11-09 and added to the 0.13 build by the user ("add this to the build
0.13"); delivered as package PV and folded into DF on 2026-11-10 at the user's request. Committed as `af19c422`. Confirmed working by the
user on 2026-11-10 ("looks fine now").

**What is wrong.** The model editor's tree lists a type under every application that holds it, and each row knows
its application, but the selection keeps only the type (`{ show: "type", key }`), so the URL carries no
application. `TypePreview` then takes the first application that lists the type. In the user's draft Countries
sits in System codes, Reference lists and Translations; its two table views are in Reference lists, the preview
opened System codes and said "The draft declares no table view for Countries", and Edit layout could not reach them.
Every type in more than one application is affected.

**What changes.** The type selection carries the application (`application`, in the selection and the URL); each
tree row (a type in the tree, a collection in a group) passes its own; the preview, the record page layout and the
table views are those of that application. A link that names no application (Issues, a type link in a panel)
falls back to the first application with a detail page or a table view for the type, else the first that lists it.
An application named that does not hold the type falls back the same way. Frontend only; no API or model change.

**Delivered (2026-11-09).** `application?` on the type selection (`types/ui.ts`), read and written as
`application=<key>` in the editor address (`routing/routes.ts`) and carried through mode changes and the layout
exit in `ModelEditor.tsx`. `ModelPane.tsx` type and collection rows pass their own application and the row
highlight matches type plus application. One helper, `applicationForType` (`features/model-editor/typeApplication.ts`),
resolves the application (named, else first with a detail page or table view, else first listing it); `TypePreview`
takes `applicationKey` and uses it, and the record page, layout editor and table views follow from its place.
Issues links pass the detail element's application. Guide: one sentence in `guide/model/preview-a-type.md`. Checks:
Vitest for the helper (the user's draft shape: Countries in Reference lists gives both table views), the URL round
trip, the ModelPane selection and ModelEditor/routes; `npm run build`; guide build. 

**Follow-up (2026-11-09).** The user's draft showed the first resolution was not enough: with no `application` in
the address the preview picked System codes (first of three applications with a country page) while every country
record of workspace stops belongs to Reference lists, so the Record page tab refused the record ("belongs to another
application") and layout edits went to a page no record uses. Resolution is now: named, else the application owning
the workspace's records of the type (read from the first record's `applicationKey`), else first with a table view or
detail page, else first listing it, all in `applicationForType` (fourth argument). `TypePreview` reads records with
`applicationKey` of the resolved application; with none there it shows the empty record and one line naming the
application that holds them, with a link that switches the selection (`onApplication` in `ModelEditor.tsx`); a type
in several applications shows an Application choice in the band (`applicationsHolding`). Tests:
`typeApplication.test.ts` (records' application beats the designed fallback, named beats records),
`TypePreview.test.tsx` (records query carries `applicationKey`; the line naming the holder). The user checked it in the
running editor on 2026-11-10.

### Delivery and checks

Implementer: DF1 to DF3 code, `docs/` (API.md, CONSUMER_API.md, COMPATIBILITY.md, APPLICATION_MODEL.md), CHANGELOG,
targeted tests (webhook and client vitest files; consumer API read and validation journeys; one journey: raise a
version, read v1 and v2, a v1 webhook keeps its shape, remove v1 and get `CONTRACT_VERSION_NOT_FOUND`), frontend
build; a browser try of each screen. Primary agent: DF4. Codex: the guide pages for DF1 to DF3 in one wave, then the
coverage check and `npm run verify`.

**Done when** every point above works in the browser and the API, the guide describes it, and verify passes.

## Exit gate (0.13)

- Every item of the inventory made from the code (`guide/tools/inventory.py`, CP) is covered by a page or is a
  reasoned exclusion in `guide/_coverage/exclusions.md`, and each capability is documented to working depth
  (CP's depth questions); `npm run verify` in `guide/` runs the coverage check and passes.
- Every page is `status: written`; every example runs in the `docs` group, or is marked `unrun` and was
  rehearsed on a clean host.
- Every generated reference has no undescribed entry; the management API reference is the one generated from the code at
  `/docs/api`, which the guide links to (0.14 deepens its descriptions).
- Each of the ten points is stated where the table above places it.
- Every tutorial was completed by a reader from outside (DOC11, the fresh-reader check, run after the full
  documentation), and their findings were closed.
- The fact-check of each wave is recorded with its removals.
- The guide is served offline by the engine at `/docs` (DF4: was `/guide`), published as a static site with search, in light
  and dark, and passes the accessibility gate.
- AGENTS.md's guide step is in force and the `docs` and coverage checks run for a change to `guide/`.
- The full review of every change since 0.12 (release step R) is done.

**Against this gate, 2026-11-10.** The first bullet is met by the check run that day (911 entries, 0 uncovered; `npm run verify`
passes, 257 pages, 75,775 links). The open items against the gate are the outside reader (bullet "Every tutorial was
completed by a reader from outside", [open item 3](#open-for-013)) and release step R (last bullet, [open item 9](#open-for-013));
the other items of [Open for 0.13](#open-for-013) are not gate bullets. No other open item against the gate is known.

## Composable domains (ADR-032)

No door is affected: the guide describes contracts and does not change them. Pages describe capabilities
in generic terms with the reference domain as one configuration of them (writing rule 11). A product-catalogue or MDM-lite reader
should recognise their case without the guide naming domains the engine does not have.
