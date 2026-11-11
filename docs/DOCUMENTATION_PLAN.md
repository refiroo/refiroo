# Documentation plan

**Status:** Draft, 2026-10-05; revised 2026-10-26. Started at the user's request: the engine needs very
good user documentation. [DOC-D1–DOC-D3](#decisions) approved by the user on 2026-10-05; DOC-D4–DOC-D9
are recommendations awaiting approval. _Revised 2026-10-26:_ the earlier foundation packages were never
built, so the release 0.13 delivers the whole guide, and its inventory, packages and further decisions
(DOC-D10–DOC-D20) are in [BASE_0_13_IMPLEMENTATION_PLAN](BASE_0_13_IMPLEMENTATION_PLAN.md). This
document keeps the strategy: why, the readers, the principles, the points that must be stated clearly
and the decisions DOC-D1–DOC-D9.

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
| **Operator** | Shell, environment | Install, deploy, configure, secure, upgrade, back up, restore and observe |
| **Access administrator** (added 2026-10-26, since 0.12) | Browser (Settings › Security) | Give people and systems the access they need: people, groups, roles, grants, clients, keys, approvals |

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
   [the 0.13 plan](BASE_0_13_IMPLEMENTATION_PLAN.md#2-how-refiroo-works-concepts-and-architecture) lists them.
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

## Information architecture, tutorials, explanations and reference

_Moved 2026-10-26_ to [BASE_0_13_IMPLEMENTATION_PLAN](BASE_0_13_IMPLEMENTATION_PLAN.md#the-guide), which holds the full page
inventory: Start here, How refiroo works (the concepts and the architecture), seven tutorials, Use
refiroo, Model your domain, Integrate, Run refiroo (installation, deployment, configuration, operating),
Administer access and security, Reference and About this release. The older plan covered operating,
architecture and security only in part; the inventory now covers them in full. One home per fact: the
inventory is not repeated here.

### The points that must be stated clearly

TODO's five points and those found since, each placed where its reader will meet it:

| Point | Stated on |
| --- | --- |
| Reading an older publication after a model release (C-D60) | Consistency for consumers; How-to: move to a new contract version; Model releases and contracts; tutorial 4 |
| Contains from 3 characters, at most 10,000 matches (C-D37) | How XREF scores; Limits; the error code reference for `QUERY_TOO_BROAD`; tutorial 4 |
| Which workspace a consumer read addresses (C-D16, C-D23) | Consumer APIs; tutorial 4's first request names `workspace`; a warning on every consumer how-to |
| `latest` and publications by ID (C-D61, C-D62) | Consistency for consumers; How-to: extract a consistent snapshot |
| ETag (C-D65) | Consistency for consumers; How-to: cache with ETag |
| XREF searches the types its consumer API exposes, not an application or the whole model: one lookup across the model needs one definition exposing every type, and several definitions give several separate lookups (found 2026-10-05 in Scalar, when the example model's four APIs each resolved only their own IDs). Exposing a type and a representation of it (a system value with the same code) makes a bare `expect=one` on that code ambiguous; `type` or `system` narrows it | Consumer APIs; How XREF scores; How-to: design a consumer API; tutorial 4 |
| Webhook retries (C-D103, user's request 2026-10-06): the waits (10 s, 30 s, 1, 2, 5, 10, 30 min, then hourly), ±20 % jitter, 24 hours from the batch's first failure, a success resetting it, the same delivery ID on every retry, then `DELIVERY_FAILED` and how resume continues | Webhooks how-to (receive and verify events); Limits and why they exist; the operator runbook for a suspended subscription; the capabilities reference |
| Webhook batch size (C-D104, user's request 2026-10-06): at most the subscription's `maxEventsPerBatch` events (1 to 1,000, default 1) and 1 MiB per request, an event over 1 MiB sent alone, and the request size a receiver's server must accept (nginx's default is exactly 1 MiB) | Webhooks how-to; Limits and why they exist; the capabilities reference |

Points like these keep arising: a decision says "state this clearly". From DOC1 on, such a
requirement is recorded as a page entry here, not as a TODO note.

## Timing

_Revised 2026-10-26._ The plan of 2026-10-05 spread the work over three packages between 0.9 and 0.12
and a documentation release. Those three (the foundation, the generated reference and the
explanations) were not built, so **the release 0.13 delivers everything**: foundation, generated
reference, concepts and architecture, tutorials, how-to guides, operating and security pages,
screenshots, the fresh-reader check and publication. 0.12 is complete first, since every example needs
authentication and the browser's final screens. The packages are DOC1–DOC12 in the
[0.13 plan](BASE_0_13_IMPLEMENTATION_PLAN.md#packages). The rule "a package that changes
user-visible behaviour updates its guide pages in the same change" starts when DOC1 lands, so it applies
to 0.14, 0.15 and every later release.

The 0.14 release writes the management API reference on `/docs` (Track V). The guide links to it and
does not repeat it; the error catalogue has one owner ([DOC-D13](BASE_0_13_IMPLEMENTATION_PLAN.md#decisions)).

## Decisions

| # | Question | Recommendation |
| --- | --- | --- |
| DOC-D1 | When is the documentation written? | **Approved 2026-10-05; revised 2026-10-26** (the foundation, generated reference and explanation packages were not built, so all of it is in 0.13: [DOC-D11](BASE_0_13_IMPLEMENTATION_PLAN.md#decisions)). Original text: Foundation, generated reference and explanations from after 0.9 (DOC1–DOC3); a documentation release **0.13** after 0.12 for tutorials, how-tos, screenshots and the fresh-reader check; a "user-visible change updates the guide" rule from DOC1 on. Basis: 0.12 changes every API example and Track U and 0.10 change the browser, so writing earlier means rewriting; the concepts are stable now. Alternative: everything in 0.13, which leaves the rule-based upkeep unused for three releases and makes 0.13 large |
| DOC-D2 | Where is it served? | **Approved 2026-10-05.** By the engine at `/guide`, offline, from the version it runs (as `/docs` serves the API reference). The same sources build a public site (DOC12 in the 0.13 plan). The generator is chosen in DOC1 against the criteria in the 0.13 plan (DOC-D18). It has not been evaluated yet, so no tool is recommended here |
| DOC-D3 | Where do the sources live? | **Approved 2026-10-05.** A new top-level `guide/` directory, so that `docs/` stays the builders' record and the two cannot be confused. PRODUCT.md's overview moves to the guide's "What RDM Engine is" (one home), and `docs/PRODUCT.md` links to it. CURRENT_FUNCTIONALITY stays as the planning catalogue |
| DOC-D4 | The running example | _Superseded by [DOC-D17](BASE_0_13_IMPLEMENTATION_PLAN.md#decisions)._ The bundled example model (delivery methods, systems, translations; PRODUCT.md's "Collection" / "PICKUP" story), with the starter consumer API U4 adds. Tutorial 2 builds a second, small domain from an empty model (countries, regions, cities, the case C-D27 used), which shows that the engine is generic |
| DOC-D5 | Tested examples | A `docs` test group runs every request and command in the guide against the seeded example model, once per seed (seed once, reuse), and compares the response with the one shown, with IDs and times normalised. It is a check on the documentation, not a test programme. It reuses the journey harness |
| DOC-D6 | Generated reference | Error codes, settings, limits and the model language generated from the code, each with a check that fails on an undescribed entry. The descriptions live beside the code (the code's own description field or docstring), so a new code cannot ship without one |
| DOC-D7 | Versions | One guide per minor release. The engine serves its own; the public site keeps the latest release and the one before. Older versions stay in git |
| DOC-D8 | The fresh-reader check | A person who has not used the engine works through each tutorial; their findings are recorded and closed. If no such reader is available, a fresh agent session given only the published guide (no repository) does it, and that is recorded as the weaker check |
| DOC-D9 | Language | English only before 1.0 |

## Not included

_Revised 2026-10-26: the management API reference is not written here at all; it is 0.14 Track V's ([DOC-D12](BASE_0_13_IMPLEMENTATION_PLAN.md#decisions))._

- Translating the guide.
- Video.
- The management API reference at `/docs/api` (its conventions, area texts, error catalogue and examples) is written and kept by 0.14's Track V in `backend/app/management/reference/content/`, not here; the audit of the OpenAPI descriptions is done there (V-D9): **done 2026-11-11 (0.14 V9)**: every operation, parameter and schema field is described, no description names a package or a decision, and `backend/tests/test_reference_complete.py` holds it.
- Rewriting API.md, CONSUMER_API or INTEGRATION_API: they stay the builders' contract and design
  record. The guide links to the generated reference instead.
- Documentation of post-1.0 directions (composable domains, workspace groups).

## Composable domains (ADR-032)

No door is affected: the guide describes contracts and does not change them. The explanation pages
describe capabilities in generic terms, with the example model as one configuration of them. A product
catalogue or MDM-lite reader should recognise their own case without the guide naming domains the
engine does not have.
