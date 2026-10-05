# Documentation plan

**Status:** Draft, 2026-10-05. Started at the user's request: the engine needs very good user
documentation, built up before 1.0. [DOC-D1–DOC-D3](#decisions) approved by the user on 2026-10-05;
DOC-D4–DOC-D9 are recommendations awaiting approval. ROADMAP, TODO and AGENTS.md are not yet
changed.

## Why

RDM Engine does things users do not expect from a reference-data tool. For example, one model file
becomes a set of applications, a REST API and a typed consumer contract. Change sets merge onto live
data that kept changing. XREF scores a code against declared rules. A publication is a snapshot that
an extract can page through while live data moves on. Features like these are only useful if people
understand them. If they don't, users see behaviour they can't predict, or don't notice the feature at
all.

Today the documentation describes the engine to the people who build it. Nobody has written a guide
for the people who use it.

### What exists today (checked 2026-10-05)

| Document | Lines | Written for | Fit as user documentation |
| --- | --- | --- | --- |
| [API.md](API.md) | 2,944 | Builders: the delivered management and consumer contracts | Accurate and complete, but organised by delivery (`Base 0.9 C2`, `WP-5 delivered`) and full of design history. It is a contract record, not a guide |
| [CONSUMER_API.md](CONSUMER_API.md), [INTEGRATION_API.md](INTEGRATION_API.md) | 876, 730 | Builders: designs and decisions | Explains why things work as they do, mixed with packages and decision IDs |
| [APPLICATION_MODEL.md](APPLICATION_MODEL.md) | 627 | Model authors and builders | The closest thing to a user reference, but no tutorial leads into it |
| [OPERATIONS.md](OPERATIONS.md) | 179 | Operators | Settings and runbooks. A good seed for operator documentation |
| [PRODUCT.md](PRODUCT.md), [PRODUCT_GUIDE.md](product-functionality/PRODUCT_GUIDE.md) | 193, 62 | Evaluators | Plain-language overview and three worked examples. A good seed for the guide's opening pages |
| [CURRENT_FUNCTIONALITY.md](product-functionality/CURRENT_FUNCTIONALITY.md) | 536 | Planning: capabilities F01–F25 with a status for each | A catalogue of what exists, not instructions for doing it |
| [GLOSSARY.md](product-functionality/GLOSSARY.md) | 81 | Everyone | Directly reusable |
| `/docs` (Scalar) | — | Integrators | The management API and every consumer API as OpenAPI, served offline. Good reference. Its quality depends on the operation, parameter and schema descriptions |

[TODO](TODO.md#open-decisions) records that user documentation is not scheduled, and lists five
points it must state very clearly: reading an older publication after a model release (C-D60), the
consumer search limits (C-D37), which workspace a consumer read addresses (C-D16, C-D23),
publications and `latest` (C-D61, C-D62), and ETag (C-D65). Each one has a page in this plan
([below](#the-points-that-must-be-stated-clearly)).

## Readers

The readers are the roles in [PRODUCT.md](PRODUCT.md#who-it-is-for), grouped by the channel they work
through:

| Reader | Works through | Comes to the documentation to |
| --- | --- | --- |
| **Evaluator** | Reading | Decide whether the engine fits: what it is, what makes it different, what it does not do |
| **Data steward** (owner, mapping, localisation) | Browser | Edit, connect, translate, prepare and publish data; understand conflicts and history |
| **Model administrator** | Model workbench, then the 0.10 editor | Model a domain, release and activate it, change it safely |
| **Integrator, management API** | REST | Load, upsert and synchronise data: batches, jobs, the change feed, queries, idempotency, concurrency |
| **Integrator, consumer API** | REST | Declare a consumer API and read through it: lists, XREF, batch resolve, crosswalk, publications, caching, events |
| **Operator** | Shell, environment | Install, configure, upgrade, back up, restore and observe |

Contributors keep the current `docs/` (plans, design, decisions, testing). This plan does not change
them, apart from [DOC-D3](#decisions).

## Principles

1. **Written for one reader at a time.** Each page has one reader and one purpose. Pages are organised
   by the reader's goal, not by the engine's structure or delivery history.
2. **Four kinds of page** ([Diátaxis](https://diataxis.fr)), never mixed. *Tutorials* teach by doing,
   one path from start to finish. *How-to guides* complete one task. *Explanations* say how something
   works and why. *Reference* describes what exists, completely and precisely.
3. **The magic is explained, not just listed.** Every distinctive behaviour gets an explanation page
   with a worked example on real data: what happens, why, and what it means for the reader's work.
   [Explanations](#explanations-the-magic) lists them.
4. **Every example runs.** Every request, response, model fragment and command in the guide is executed
   against the engine in a test group. A response shown in the guide is the response the engine gives
   (IDs and times normalised). A change that breaks an example fails the build, as a broken contract
   does ([DOC-D5](#decisions)).
5. **Reference is generated where the code holds the facts.** Error codes, settings, the model language,
   limits and capabilities come from the code, or are checked against it. Writing them by hand would
   create a second copy that drifts ([DOC-D6](#decisions)).
6. **One home per fact** (AGENTS.md). The guide explains and links to the reference; it does not restate
   contracts. API.md stays the builders' contract record.
7. **Plain language, product terms.** No package IDs, decision IDs or delivery history (`C6a`, `D47`,
   `Base 0.9`). The style the current documents use (short sentences, one term per concept, the
   glossary's words) becomes the guide's written style guide.
8. **Shipped with the engine.** The guide is versioned with the code, and the engine serves its own
   version offline, as it serves the API reference ([DOC-D2](#decisions)).
9. **Limits are stated where they bite.** Every documented limit (page sizes, batch maxima, contains
   from 3 characters, 10,000 matches, retention) is on the page of the task it limits, with the
   setting that changes it, and in one limits reference.

## Information architecture

The guide's top-level sections, with the pages each holds. "Seed" names an existing document the page
starts from.

### Start here

- **What RDM Engine is.** The four things a team manages (the model, live data, change sets,
  publications), what makes the engine different, and what it does not do. Seed: PRODUCT.md.
- **Run it in five minutes.** Docker, open the browser, see the example applications. Seed: README
  quick start.
- **A tour of the example applications.** Seed: EXAMPLE_MODEL.md, PRODUCT_GUIDE.md.
- **Which path is yours.** One line per reader, each leading to their tutorial.

### Tutorials

One per reader. Each one follows a single running example from start to finish, and runs as a test
([DOC-D4](#decisions)):

| # | Tutorial | Reader | Ends with |
| --- | --- | --- | --- |
| 1 | Your first correction, then your first publication | Data steward | A live edit, a change set reviewed and published, a conflict resolved, the history read |
| 2 | Model your own domain | Model administrator | An empty model grown into an installed, active release with a hierarchy, a relationship and views; then a compatible change released |
| 3 | Load and keep in sync | Integrator, management API | A file loaded as a batch, retried safely with an idempotency key, then the change feed followed from a position |
| 4 | Publish a consumer API and translate codes | Integrator, consumer API | A consumer API declared in the model; a list paged; a code resolved by XREF, by batch and across systems; an extract pinned to a publication |
| 5 | Upgrade and recover | Operator | An upgrade, a backup and a restore rehearsed |

### How-to guides

Task pages grouped by reader. The list is derived from the journeys ([USER_JOURNEYS](product-functionality/USER_JOURNEYS.md))
and the capabilities F01–F25, one page per task a reader names. Examples:

- *Steward:* fix a value someone else just changed; move a record and its subtree; map a system's
  values; fill missing translations from the relation matrix; delete a record with dependants;
  restructure a hierarchy; withdraw a publication.
- *Model administrator:* add a field to a released type; declare an effective period; add a view;
  read a release diff; know when a change needs a new contract version.
- *Integrator:* upsert by a business key; replace a record's relationship set; run a background job
  and resume it; recover from `410` on the feed; query with criteria and one relationship hop; read
  data as of a date.
- *Consumer integrator:* narrow a lookup with parameters; resolve a file of codes; cache with ETag;
  extract a consistent snapshot; move to a new contract version.
- *Operator:* every runbook in OPERATIONS.md; tune limits; turn capabilities off.

### Explanations (the magic)

Each page has a worked example on the running example's data:

| Page | Explains |
| --- | --- |
| One engine, many applications | How a model becomes screens and APIs; why no code knows an application; what that guarantees |
| Three kinds of change | Live edits, change sets and model releases: when to use each; why daily work needs no change set |
| How a change set publishes | Base, overlay, merge onto live data that moved on; conflicts; what a publication holds |
| History and time | Audit history, pinned reads, publications as frozen copies, effective periods and `asOf`, and how they differ |
| Connections | Containment, recursive hierarchy, cross-reference, mapping, the relation matrix; cardinality and scope |
| Concurrency without locks | Record versions, relation-set versions, conflicts, `unchanged`, why nothing is overwritten silently |
| Identity | Object IDs, business keys, unique attributes, client-assigned IDs; why consumers read by object ID |
| Model releases and contracts | Drafts, installation, activation, compatibility, the consumer contract version and what breaks it |
| Consumer APIs | A declaration becomes an API: the shared object, roles, projections, parameters, lists |
| How XREF scores | Own and promoted weights, exact before contains, ties, `scoresFrom`, crosswalk; a scored example worked by hand |
| Consistency for consumers | Live versus pinned reads, `latest`, cursors that keep their publication, ETag |
| The change feed | Positions in commit order, what an entry names, retention, recovery from a publication |
| Jobs | Inline and background runs, failure policies, item outcomes, idempotency, resumption, cancellation |
| Limits and why they exist | Each limit, what it protects and the setting that changes it |

### Reference

| Reference | Source |
| --- | --- |
| Management API | OpenAPI, served by Scalar; the descriptions improved ([DOC2](#doc2-generated-reference)) |
| Each consumer API | Its generated OpenAPI document |
| Model language | Generated from the schema (`models/schema.py`), with APPLICATION_MODEL's explanations as descriptions |
| Error codes | Generated from the code: every code, its status, its meaning and what to do |
| Settings | Generated from `app/config.py`: name, default, allowed values, effect |
| Limits and capabilities | Generated from the settings and `GET /capabilities` |
| Glossary | GLOSSARY.md |
| Release notes and upgrade notes | CHANGELOG, written for readers; compatibility policy from 0.11 |

### The points that must be stated clearly

TODO's five points, each placed where its reader will meet it:

| Point | Stated on |
| --- | --- |
| Reading an older publication after a model release (C-D60) | Consistency for consumers; How-to: move to a new contract version; Model releases and contracts; tutorial 4 |
| Contains from 3 characters, at most 10,000 matches (C-D37) | How XREF scores; Limits; the error code reference for `QUERY_TOO_BROAD`; tutorial 4 |
| Which workspace a consumer read addresses (C-D16, C-D23) | Consumer APIs; tutorial 4's first request names `workspace`; a warning on every consumer how-to |
| `latest` and publications by ID (C-D61, C-D62) | Consistency for consumers; How-to: extract a consistent snapshot |
| ETag (C-D65) | Consistency for consumers; How-to: cache with ETag |

Points like these keep arising: a decision says "state this clearly". From DOC1 on, such a
requirement is recorded as a page entry here, not as a TODO note.

## Timing: built up across releases, completed in a documentation release

Two facts set the timing. Every API example changes in **0.12**, when every request gains
authentication. The browser changes through **0.12**: the UI foundation and settings area (Track U),
and the model editor in 0.10. Final tutorials and screenshots written now would be rewritten twice.
But the concepts are stable today: live data, change sets, publications, the model, consumer APIs
and the feed.

So the recommendation ([DOC-D1](#decisions)):

- **Foundation and the stable layers now.** The site, the tested-examples harness, generated
  reference and the explanation pages, as packages between releases.
- **A rule from the foundation on.** A package that changes user-visible behaviour updates its guide
  pages in the same change, as it already updates API.md. The step joins "How a package is delivered".
- **A documentation release, 0.13, after 0.12 and before 1.0.** Tutorials and how-to guides in their
  final form, with authentication; screenshots; a fresh-reader check; publishing. 1.0's exit gate
  gains "the guide covers every 1.0 capability".

## Packages

Package IDs DOC1 onward. Every package uses the delivery steps of the release it lands in.

#### DOC1: Foundation

**When:** after 0.9.0 is released, before 0.10's editor work. **Scope:**
- the location (DOC-D3) and the site generator, chosen by a short comparison against these criteria:
  Markdown sources, offline build, served by the engine, search, versioning, accessible output,
  maintained, permissive licence (DOC-D2);
- served at `/guide` with a link from `/docs` and the UI's help entry (DOC-D2);
- the style guide (principle 7) and a page template for each kind;
- the `docs` test group: it extracts the guide's examples, runs them against the seeded example model
  and compares the responses (DOC-D5), proven on one page;
- a link and anchor check;
- the AGENTS.md step: user-visible changes update their guide pages.

**Exit:** one explanation page ("Three kinds of change") published at `/guide`, its examples running
in the `docs` group.

#### DOC2: Generated reference

**When:** with 0.10. **Scope:** the error code, settings, limits and model language references
generated from the code (DOC-D6). A check fails when a code, setting or schema field has no
description. An audit of the management OpenAPI's descriptions: every operation, parameter and error
code described, with an example where the shape is not obvious.

#### DOC3: Explanations

**When:** across 0.10 and 0.11, a few pages per gap in the queue. **Scope:** the explanation pages
above, each with its worked example running in the `docs` group. The five points are written here
first.

#### DOC4–DOC8: Release 0.13, Documentation

| Package | Scope |
| --- | --- |
| DOC4 Tutorials | The five tutorials on the running example, authenticated, each run end to end as a test |
| DOC5 How-to guides | Every task page per reader, checked against the journey catalogue so no journey lacks a page |
| DOC6 Screenshots | Generated by the browser runners from the running example, light and dark, so they stay current |
| DOC7 Fresh-reader check | Each tutorial completed by a reader who has not used the engine; every point where they got stuck fixed and recorded (DOC-D8) |
| DOC8 Publish | A public static build of the same sources, versioned per release (DOC-D7), and the README pointing to it |
| R | Acceptance: the exit gate below |

### Exit gate (0.13)

- Every reader in [Readers](#readers) has a tutorial, and each tutorial runs green as a test.
- Every journey in USER_JOURNEYS has a how-to page or is covered by a tutorial step.
- Every capability has an explanation or reference entry; each of the five points is stated where
  the table above places it.
- Every example in the guide runs in the `docs` group; generated references have no undescribed entry.
- A fresh reader completed each tutorial, and their findings were closed.
- The guide is served offline by the engine and published as a site, with search, in light and dark,
  and passes the accessibility gate.

## Decisions

| # | Question | Recommendation |
| --- | --- | --- |
| DOC-D1 | When is the documentation written? | **Approved 2026-10-05.** Foundation, generated reference and explanations from after 0.9 (DOC1–DOC3); a documentation release **0.13** after 0.12 for tutorials, how-tos, screenshots and the fresh-reader check; a "user-visible change updates the guide" rule from DOC1 on. Basis: 0.12 changes every API example and Track U and 0.10 change the browser, so writing earlier means rewriting; the concepts are stable now. Alternative: everything in 0.13, which leaves the rule-based upkeep unused for three releases and makes 0.13 large |
| DOC-D2 | Where is it served? | **Approved 2026-10-05.** By the engine at `/guide`, offline, from the version it runs (as `/docs` serves the API reference). The same sources build a public site (DOC8). The generator is chosen in DOC1 against the criteria listed there. It has not been evaluated yet, so no tool is recommended here |
| DOC-D3 | Where do the sources live? | **Approved 2026-10-05.** A new top-level `guide/` directory, so that `docs/` stays the builders' record and the two cannot be confused. PRODUCT.md's overview moves to the guide's "What RDM Engine is" (one home), and `docs/PRODUCT.md` links to it. CURRENT_FUNCTIONALITY stays as the planning catalogue |
| DOC-D4 | The running example | The bundled example model (delivery methods, systems, translations; PRODUCT.md's "Collection" / "PICKUP" story), with the starter consumer API U4 adds. Tutorial 2 builds a second, small domain from an empty model (countries, regions, cities, the case C-D27 used), which shows that the engine is generic |
| DOC-D5 | Tested examples | A `docs` test group runs every request and command in the guide against the seeded example model, once per seed (seed once, reuse), and compares the response with the one shown, with IDs and times normalised. It is a check on the documentation, not a test programme. It reuses the journey harness |
| DOC-D6 | Generated reference | Error codes, settings, limits and the model language generated from the code, each with a check that fails on an undescribed entry. The descriptions live beside the code (the code's own description field or docstring), so a new code cannot ship without one |
| DOC-D7 | Versions | One guide per minor release. The engine serves its own; the public site keeps the latest release and the one before. Older versions stay in git |
| DOC-D8 | The fresh-reader check | A person who has not used the engine works through each tutorial; their findings are recorded and closed. If no such reader is available, a fresh agent session given only the published guide (no repository) does it, and that is recorded as the weaker check |
| DOC-D9 | Language | English only before 1.0 |

## Not included

- Translating the guide.
- Video.
- Rewriting API.md, CONSUMER_API or INTEGRATION_API: they stay the builders' contract and design
  record. The guide links to the generated reference instead.
- Documentation of post-1.0 directions (composable domains, workspace groups).

## Composable domains (ADR-032)

No door is affected: the guide describes contracts and does not change them. The explanation pages
describe capabilities in generic terms, with the example model as one configuration of them. A product
catalogue or MDM-lite reader should recognise their own case without the guide naming domains the
engine does not have.
