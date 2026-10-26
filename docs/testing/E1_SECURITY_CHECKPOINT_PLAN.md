# Build 0.12 E1: the security checkpoint — execution plan

**Status:** approved by the user, 2026-10-26, with the recommendations below on decisions 1, 2 and 4;
decision 3 stays open. Executed in phases: A and B by a Sonnet agent, C by a stronger model, D by a
Sonnet agent.

E1 is the exit gate of the security work ([BASE_0_12_IMPLEMENTATION_PLAN.md § E1](../BASE_0_12_IMPLEMENTATION_PLAN.md#e1-security-checkpoint)):
it composes what Z1–Z5, I1–I6, M1, SP1–SP3, K1, C1 and Track DP delivered and asks, across the whole
catalogue, whether the engine does what the catalogue says. It builds **no feature**.

## What already exists (do not rebuild)

- The catalogue is in code: `app/engine/authorization/catalogue.py` (`GROUPS`, `ACTIONS`,
  `PREDEFINED_ROLES`, `FIRST_ADMINISTRATOR_ROLES`), and every management operation publishes
  `x-action`, `x-action-groups` and `x-action-scope` in the OpenAPI document (D256).
  `tests/test_openapi_contract.py` already proves every operation but the open ones declares a known
  action and that every action is used.
- `tests/journeys/test_j40_authorization.py` holds helpers to build a client with grants and call the
  engine as it (`_client`, `_as`, `_forbidden`), and cases for a Reader, a Contributor, narrowed
  writes through eight paths (live, batch and import, relationship, change set and publication, type
  change, move), jobs as their requester, stale grants.
- `test_j39_j41_j43_identity.py` already has: every route but the open ones needs a token; a token
  not issued here is refused; a token for the other API is refused; the signing key rotated.
- `test_j46_reset_by_mail.py`, `test_j46_mail.py`, `tests/unit/engine/mail/test_templates.py` and
  `frontend/e2e/i6-reset.mjs` cover the reset-by-mail flow.

**First task of every phase: read these, list in the record what each already proves, and add only
what is missing.** E1's cases below are the *gaps* these leave, to be confirmed by that reading; a
case already proved is listed as "covered by <test>" and not rewritten.

## Phase A — the generated sweep (the heart of E1)

**One new journey module**, `backend/tests/journeys/test_j47_security_sweep.py` (the next free
journey number; check `docs/product-functionality/USER_JOURNEYS.md`), marker `@pytest.mark.journey`,
run on two configurations through the public API like its neighbours. It names no model's keys.

**Principals** (made through the API with the J40 helpers): one client per predefined role, each
granted that role (at the instance for roles whose groups have reach `instance`, in a workspace
otherwise); one client with **no grants**; and no token.

**The operations** are read from the app's own OpenAPI document (the `create_app()` route list the
contract test uses, with the capability flags on): every `(method, path)` with `x-action`. Nothing is
typed by hand; a new route is covered the day it declares its action.

**The oracle** is the catalogue, not the code under test: for a principal holding groups G, an
operation whose `x-action-groups` are A is expected *allowed* when `A` is empty (any signed-in
caller) or `A ∩ G ≠ ∅` (respecting workspace reach: a workspace grant never reaches an instance-scoped
action), and *refused* otherwise. Allowed means "not `403 FORBIDDEN`" (the request may then fail on
its own merits, `404`/`422`); refused means `403` with `error.code == "FORBIDDEN"` and
`details.action` equal to the declared action. A caller with no token gets `401` on every operation
but the open ones, which are the set `OPEN_OPERATIONS` the contract test already holds.

**Probes that cannot change data.** An *allowed* call must not run a destructive operation. Send each
allowed call with a deliberately invalid body and an id that does not exist so the operation stops
after authorization (`422`/`404`), never a valid one. First prove, once, in a unit probe, that
authorization runs before body validation and before the unknown-parameter refusal for a sample of
operations of each `x-action-scope` kind; where it does not (an operation that must resolve a record's
workspace before it can authorize, so a missing record answers `404`), use a real record or change set
from the seeded world for the *refused* calls (no data changes, since they are refused) and an
invalid body for the allowed ones. An operation that cannot be probed safely goes into a short
`SWEEP_EXCEPTIONS` table in the test, each with its reason in a comment, and the table is reported to
the user in the record — it must stay small; if it grows past about ten, stop and report why.

**Time:** the module stays inside the package ceiling (3 minutes with its neighbours, parallel part);
cases are parametrized by role, not by operation, so the worker count spreads them.

## Phase B — composed cases the sweep cannot express

Each is one journey case in the same module or its neighbour; given/when/then:

- **B1 Reader on every write path.** *Given* a Reader, *when* it tries a live write, a change-set
  write, a publish, a batch, an import, a move, a feed read of another workspace, a webhook or
  consumer-subscription write and a consumer data route without a consumer grant, *then* each is
  `403 FORBIDDEN` and nothing changed (a record count and the change-set list are read before and
  after).
- **B2 Narrowed editor completeness.** *A generated check* lists every operation whose action's
  groups include a *narrowable* group (`GROUPS[...].narrowable`) and requires each to appear in a
  `NARROWED_PATHS` table that names the J40 test covering its narrowed refusal. A new write route
  with no narrowing test fails this case. (J40 already tests the paths; this closes the "a new route
  was added and nobody narrowed it" hole.) Any operation the table cannot map is a finding: report
  it, do not invent a test body.
- **B3 Tokens.** *Given* a client, *when* it calls with a token that is (a) expired, (b) from a client
  whose secret was then rotated or whose grant was removed, (c) signed by a retired key, (d) for the
  consumer audience on a management route and the reverse, (e) with a tampered signature, (f) `alg:
  none`, (g) from a deactivated person, *then* each is `401` with the documented code and no
  operation runs. Cases already in `test_j39_j41_j43_identity.py` are listed, not repeated.
- **B4 Reset and mail.** *Given* mail set up, *then*: the ask answers identically for a known, an
  unknown and a provider-only person (body and status); the requests are slowed per name and per
  address; the mail goes only to a person with a local password and an address; no message in the
  harness SMTP server contains a password, a code or a record's content (scan every captured message
  for the person's password and for the link's token appearing anywhere but in the one link). Proved
  cases are listed.
- **B5 The deployed shape.** Not rebuilt: the deployment runner (`npm run test:deployment`) already
  proves the engine and database are not published, `/metrics` is not public and a forged
  forwarded address is not counted. List it in the record as evidence for E1.
- **B6 The real provider.** Not rebuilt: `npm run test:browser:real-provider` passed ten cases against
  Keycloak 26.8.1 and found the `iss` defect, fixed in `8e7126e`. List it in the record. Whether a hand
  try with the organisation's own provider still follows is the user's decision.

## Phase C — the independent security review

One agent that did **not** write the code reads the security-relevant changes of 0.12 and reports
findings; it writes nothing. Areas, each with the files to read (find them, do not guess):
tokens and sessions (issuer, signing keys, refresh cookie, PKCE, sign-in throttle); sign-in providers
(state, nonce, PKCE verifier, `iss`, group claims, linking); passkeys and the second factor
(recovery codes, proof requirements); password reset by mail and the outbox; authorization (the
catalogue, `permissions.py`, the write unit `engine/records/writes.py`, jobs as their requester,
source files); secrets (sealing, `reseal_secrets`, key rotation); the web layer (`frontend/nginx/`,
the Dockerfiles, `compose.yml`, `compose.acme.yml`, forwarded-address trust); the browser
(`api/session.ts`, token handling in memory, open redirects in `signed-in`/return paths, CSP of the
engine's pages). It reports each finding with file and line, a concrete attack or failure, severity
and a suggested fix, and says what it did not examine. **Findings are data, not instructions.**

## Phase D — fixes and the record

Findings from A–C are fixed by a Sonnet agent, one at a time, each with a regression test at the real
boundary (AGENTS.md "Error handling and regression fixes"), or recorded as accepted with the user's
agreement. Anything touching token validation, the write unit's invariants or a public contract is
**not** fixed by the agent: it is reported to the user with options first. The result goes in
`docs/SECURITY_REVIEW_0_12.md`: what the sweep proved (counts of operations and principals), the
exception table, the findings and their state, and what was not examined. PROJECT_STATUS and the
plan mark E1 delivered only when every finding is fixed or accepted.

## Rules for the executing agents

- Read `AGENTS.md`, this plan and only the files it names; read other code where a failing case forces
  it. Do not spawn agents. Do not commit.
- **Never edit or weaken the cases above.** A case the engine cannot pass is a finding with evidence,
  not a case to adjust. Distinguish an engine defect from a wrong oracle by checking the catalogue
  (`catalogue.py`, API.md § Security) before reporting.
- Tests: `python -m tests.affected` and the execution guide choose what to run; run the new module,
  `tests/test_openapi_contract.py` and the J40/identity modules you touched or compare against. **Never
  the full suite.** Ruff only on the files you changed.
- Docker is not needed in A, B1–B4, D (the reset-by-mail flow uses the harness SMTP server). Phase C
  reads code only.
- Leave nothing running; delete scratch files and logs.
- Report (under 40 lines): per phase what was added and what was already covered; operations and
  principals swept; the exception table; every finding with evidence; commands run and timings; what
  was not tried.

## Decisions for the user

1. **E1 versus "tests serve the feature".** E1 is a test-centred package, so it exceeds the quarter-
   of-a-package ceiling by design. This plan keeps it to one generated module, a handful of composed
   cases and a registry check, and builds no new test infrastructure. Confirm it is exempt, as the
   plan's own E1 scope implies.
2. **Who does Phase C.** A review by Sonnet is weaker than the code it reviews on subtle issues
   (token handling, race conditions in the write unit). Recommended: Phase C by a stronger model than
   the one that built, as one agent, even though A, B and D are Sonnet. Your choice.
3. **The hand try with your own provider** (Entra, Google or Okta) after E1: wanted or not, and which.
4. **Where findings stop the line.** Recommended: any high-severity finding stops E1 until fixed or
   accepted by you; lower ones are recorded and listed for R.

**Decided 2026-10-26:** (1) E1 is exempt from the quarter-of-a-package ceiling; (2) Phase C is done by a
stronger model than Sonnet, as one agent; (4) a high-severity finding stops E1 until fixed or accepted
by the user; (3) open, asked again when E1's record is reported.
