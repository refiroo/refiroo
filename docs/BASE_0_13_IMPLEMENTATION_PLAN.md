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
| What refiroo is | Explanation | PRODUCT.md, BRANDING.md | the four things a team manages; F01 |
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
| [DOC11](#doc11-fresh-reader-check) | DOC9, DOC9A | Each tutorial completed by a reader from outside; the unrun commands rehearsed on a clean host | The user finds the reader; primary agent records |
| [DOC12](#doc12-publish) | DOC11 | The public site, versioned; the README points to it | Primary agent |
| [HD](#hd-one-header-for-the-app-the-documentation-and-the-api-reference) | DOC1 | One header style for the app, the guide and the API reference; logo to the app; Documentation \| API reference switch; "?" help; one theme choice | Primary agent. **Approved 2026-11-03; delivered 2026-11-03** |
| [TH](#th-a-theme-choice-normal-or-website-purple) | HD | A theme choice, Normal or Website purple, beside the light and dark choice, in the app, the guide and the API reference | Primary agent. **Approved 2026-11-05** |
| [RL](#rl-record-pages-and-related-columns-in-the-model-editor) | DOC1 | Record pages with one panel per relationship by default; Add panel… on a record page; columns showing a field of the related records or where they sit, chosen in the editor | Primary agent. **Approved 2026-11-05** |
| [AD](#ad-an-assistant-task-makes-its-own-model-draft) | - | A workbook task's session makes its own model draft; a proposal on a draft it did not make goes back to the session instead of failing the task | Primary agent. **Delivered 2026-11-06** |
| R | all | Full review of every change since 0.12, the exit gate, the release | Primary agent |

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
- Still open with the user: the engine image build was not run (no Docker daemon on the machine), and the list of
  private-model names for the banned-terms check is empty until the user supplies the names.

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
  say the API is unauthenticated. Open: `compose.yml` does not pass `WEB_MAX_BODY` to the web container.

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

### DOC12: Publish

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
  and the ink underline on the current item. That shared part is one stylesheet in `frontend/public/brand/`,
  which the engine already serves at `/brand/`. The guide's `customCss` and the API page both use it, so the
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
dark, since they key on the mode only; the engine's copy under `backend/app/management/brand/` kept equal), the
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
  too: the shared header stylesheet (`frontend/public/brand/refiroo-header.css`), `guide.css` (Starlight's
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
fields and where they sit: brand, system, language) gives rich record pages; the same data on a model without
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

## The writing rules

These go into `guide/AGENTS.md` in DOC1; they are the contract between the briefs and the writer.

1. **The brief is the boundary.** State only what the brief's sources support. A fact not in a source is
   not written. When the brief seems wrong or incomplete, stop and say so on the page's review list; do not
   fill the gap from memory of how such systems usually work.
2. **One reader, one purpose per page**, in the page kind's template; kinds are not mixed.
3. **Plain language, product terms.** "refiroo" for the application and anything a person sees; "the
   engine" in technical text ([BRANDING](BRANDING.md)). The glossary's words, one term per concept. Short
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
| DOC-D14 | What is the product called? | **Approved 2026-10-26.** "refiroo" for the application and everything a reader sees, "the engine" in technical text, per [BRANDING](BRANDING.md). DOCUMENTATION_PLAN's older wording ("RDM Engine") is corrected. Settings, packages and codes keep their names |
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

## Exit gate (0.13)

- Every item in the coverage inventory is covered by a written page or is a reasoned exclusion; both lists
  are otherwise empty.
- Every page is `status: written`; every example runs in the `docs` group, or is marked `unrun` and was
  rehearsed on a clean host.
- Every generated reference has no undescribed entry.
- Each of the ten points is stated where the table above places it.
- Every tutorial was completed by a reader from outside, and their findings were closed.
- The fact-check of each wave is recorded with its removals.
- The guide is served offline by the engine at `/guide`, published as a static site with search, in light
  and dark, and passes the accessibility gate.
- AGENTS.md's guide step is in force and the `docs` and coverage checks run for a change to `guide/`.
- The full review of every change since 0.12 (release step R) is done.

## Composable domains (ADR-032)

No door is affected: the guide describes contracts and does not change them. Pages describe capabilities
in generic terms with the reference domain as one configuration of them (writing rule 11). A product-catalogue or MDM-lite reader
should recognise their case without the guide naming domains the engine does not have.
