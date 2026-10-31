# Base 0.13 implementation plan

**Status:** Planned 2026-10-26 at the user's request. All decisions DOC-D10–DOC-D20 are decided by the
user (2026-10-26). Nothing is built yet.

**Target:** Product 0.13.0, [the documentation release](ROADMAP.md#product-release-013--documentation).
The strategy, readers and principles are in [DOCUMENTATION_PLAN](DOCUMENTATION_PLAN.md); this plan is
what is delivered, in what order, by whom and how it is checked.

**Depends on:** 0.12 complete (every example carries authentication, and the browser's screens, the
Security pages and the deployment guide are final). 0.14 (the management API reference on `/docs`) and
0.15 (interface language) do not block this release; the guide links to what 0.14 writes
([DOC-D12](#decisions)).

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
| **The user** | Decides the open decisions, reads the pages named for a read, runs Codex, commits | |

Codex is run by the user, outside this session. So what Codex needs must be in the repository:
`guide/AGENTS.md` (written in DOC1) holds the writing rules; each page has a brief; the checks run
without the primary agent. Codex edits only the files in its wave's list, so waves do not touch each
other's files in the shared working tree. A page is never half-finished: it is `status: stub`
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
| How XREF scores | Own and promoted weights, exact before contains, ties, `scoresFrom`, crosswalk; a scored example worked by hand | CONSUMER_API | F20, F23 |
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
| 2 | Model your own domain | Model administrator | An empty model grown into an installed, active release (countries, regions, cities: a hierarchy, a relationship and views), then a compatible change released |
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
| Sessions, a second factor and passkeys | How-to | Settings › Account | F26 |
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
| Capabilities F01–F28 | CURRENT_FUNCTIONALITY |
| Journeys J01–J47 | USER_JOURNEYS (the retired J09 is an exclusion) |
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
| [DOC1](#doc1-foundation) | 0.12 | Generator, `guide/` layout, `/guide` serving, templates, the writing rules, the `docs` group proven on one page, the AGENTS.md rule | Primary agent |
| [DOC2](#doc2-generated-reference) | DOC1 | The generated references and their completeness checks; descriptions written beside the code | Primary agent (mechanism); Codex (descriptions) |
| [DOC3](#doc3-briefs-samples-and-coverage) | DOC1 | The coverage inventory, a brief for every page, the guide's sample data | Primary agent |
| [DOC4](#doc4doc9-the-writing-waves) | DOC2, DOC3 | Wave A: how refiroo works, with the architecture and security overview | Codex |
| [DOC5](#doc4doc9-the-writing-waves) | DOC2, DOC3 | Wave B: run refiroo, and administer access and security | Codex |
| [DOC6](#doc4doc9-the-writing-waves) | DOC4 | Wave C: integrate (management and consumer APIs) | Codex |
| [DOC7](#doc4doc9-the-writing-waves) | DOC4 | Wave D: use refiroo and model your domain | Codex |
| [DOC8](#doc4doc9-the-writing-waves) | DOC4–DOC7 | Wave E: the seven tutorials | Codex |
| [DOC9](#doc4doc9-the-writing-waves) | DOC4–DOC8 | Wave F: start here, about this release, the questions page | Codex |
| [DOC10](#doc10-screenshots) | DOC7, DOC8 | Screenshots from the browser runners, light and dark | Primary agent |
| [DOC11](#doc11-fresh-reader-check) | DOC9 | Each tutorial completed by a reader from outside; the unrun commands rehearsed on a clean host | The user finds the reader; primary agent records |
| [DOC12](#doc12-publish) | DOC11 | The public site, versioned; the README points to it | Primary agent |
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

**Exit:** the coverage list has an owning page for every item; every brief is reviewed by the user's
spot read of the ones they name; every example named in a brief runs.

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

### DOC10: Screenshots

The browser runners produce the guide's screenshots from the sample data, light and dark, at the
standard width and at 390 px where a page speaks of a narrow screen. The guide references them by name;
a command regenerates them, so 0.14 (palettes) and 0.15 (interface language) refresh them cheaply.
Pages carry text alternatives written by the writer; the check refuses a screenshot without one.

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
8. **Domain names come from the running example only.** Examples come from the bundled starter model and
   the guide's samples. Never use, quote or hint at a private model or a source export; never name another
   organisation's system.
9. **Describe what exists.** No future feature, no "will". A planned capability appears only in "What it
   does not do", with no date.
10. **Do not touch what is not yours.** Edit only the files in the wave's list. Do not commit. Do not change
    code, tests, or any page outside the wave. If you find a defect in the engine, write it in the page's
    review list.

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
| DOC-D17 | The running example | **Approved 2026-10-26.** Unchanged from DOC-D4: the bundled starter model and the guide's own sample data (`guide/samples/`), loaded through the public API; tutorial 2 builds a second small model (countries, regions, cities). The guide does not depend on 0.14's extension of the starter (V-D2); if that lands first, the samples use it. No private model or export is ever used |
| DOC-D18 | The site generator | **Approved 2026-10-26.** The primary agent compares generators in DOC1 against the listed criteria, with evidence, and reports the choice before the layout is committed. No tool is named here: none has been evaluated |
| DOC-D19 | Is a non-Docker installation documented? | **Approved 2026-10-26.** Document only what is supported and tested. The Docker Compose reference installation is. If installing from source for production is not supported, the page says so and points to the developer instance, which OPERATIONS already describes as a development setup. Confirmed in DOC1: the page states what is supported after checking it |
| DOC-D20 | Sizing figures | **Approved 2026-10-26.** The sizing page states only measured figures (0.11's volume measurements, POSTGRESQL_BUDGETS), each with the measurement's date and conditions. Where nothing was measured, the page says "not measured" rather than advise. A sizing guess in a guide is read as a promise |

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
in generic terms with the starter as one configuration of them. A product-catalogue or MDM-lite reader
should recognise their case without the guide naming domains the engine does not have.
