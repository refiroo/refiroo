# Base 0.12 implementation plan

**Status:** Created 2026-10-22, when the user moved Track L here from
[Base 0.11](BASE_0_11_IMPLEMENTATION_PLAN.md#part-3--moved-to-012): the project's name is not chosen
yet, and the first public release needs it. 0.12 is therefore the first public release. L1's plan
was written on 2026-10-22 inside 0.11 and moved unchanged, waiting for the user's acceptance; its
decisions keep their 0.11 numbers (D216–D223). **The security tracks were planned on 2026-10-22,
after 0.11.0, with the user's ideas of the same day** ([below](#the-users-ideas-2026-10-22)); their
decisions continue the numbering (D224 onward). **The security plan and D224–D241 were accepted by
the user on 2026-10-22**, D232 included: change-set publication approvals in 0.12 as Track A, after
the cut line; ROADMAP's 0.12 scope gains them in P0. Work
packages are specified at package level; each package's detailed plan, test cases and decisions are
written and accepted when it starts, delivered by the
[0.11 delivery steps](BASE_0_11_IMPLEMENTATION_PLAN.md#how-a-package-is-delivered) in the order of
the [delivery queue](#delivery-queue).

**Target:** Product 0.12.0, [security, authentication and authorization](ROADMAP.md#product-release-012--security-authentication-and-authorization),
and the first public release.

**Depends on:** Product 0.11.0. **The project's name before L1 and L2:** the name appears in public
contracts (the `RDM-Signature`, `RDM-Workspace`, `RDM-Publication`, `RDM-As`, `RDM-Redelivery` and
`RDM-Timestamp` headers, the `RDM_*` settings), so a rename that changes them lands before L2 commits
those contracts. Until the name is chosen, identifiers new in 0.12 (the token issuer, scope names)
are kept free of it.

## Product outcome

Every caller, person or system, is authenticated; every operation is authorized against a role the
caller holds for that workspace; and every change records who made it. A security administrator
manages people, groups, roles and OAuth clients in Settings › Security. A person who should only
read cannot change anything through any channel; a person who should only propose changes works in
a change set and asks someone to publish it. 0.12 is also the first public release (Track L).

Exit gate: the [roadmap's 0.12 exit gate](ROADMAP.md#product-release-012--security-authentication-and-authorization)
in full, plus the approval items below if D232 is accepted.

## The user's ideas (2026-10-22)

Raised by the user while 0.12 was being planned, "ideas which came up along the way", to be checked
against what is already planned:

1. User groups, access groups, predefined roles, then configurable roles.
2. Action groups per user journey, from which roles are made.
3. Actions with approvals, for example a change set's publication when the person's role requires
   an approval; perhaps every publication needs one, and a person with the right approves their own.
   Approvals need some internal notification.
4. Roles like those of the data management and governance world.
5. For non-technical users: read-only, and editing with minimal options plus approvals.
6. Roles for systems as well as people: the consumer APIs and the management API are both APIs.
7. Basic (advanced) user management.

**What was already planned** (ROADMAP 0.12, CONSUMER_API C-D1, ADR-031, SETTINGS_AND_UI_PLAN U8):
engine-provided OAuth 2.0 with JWT access tokens for people and systems, no API keys; permissions
per application, record type and operation; OAuth clients authorized per consumer API; roles within
ADR-031's three groups with the deployment flags kept; audit identity beside `cause`; the Security
pages (sign-in and account, users and roles, OAuth clients, signing keys); key rotation; the "try it"
console authenticated. **What was not:** groups, a named role list, roles built from journey-shaped
action groups, and approvals: protected publishing is in **1.0**'s scope, and a research note keeps
approval flows in discovery.

**How this plan takes them:**

| Idea | Where | Note |
| --- | --- | --- |
| 1 Groups | Z1, SP1 (D229) | Local groups, and groups taken from the sign-in provider |
| 1 Predefined, then configurable roles | Z1, SP1 (D227, D230) | Both in 0.12: a predefined role is a fixed set of action groups, a custom role another set; one mechanism |
| 2 Action groups per journey | P0, Z1 (D227) | The permission catalogue is written as action groups named after journeys; roles are made of them, never of single routes |
| 3 Approvals with self-approval | Track A, after the cut line (D232) | **Conflicts with the roadmap's placement in 1.0 and needs the user's explicit decision (PRODUCT.md)**; explained below |
| 3 Internal notifications | A2 (D233) | An inbox in the app and on the API, and webhook events for routing elsewhere; no e-mail |
| 4 Governance roles | D230 | Predefined roles named after the [personas](PRODUCT.md#who-it-is-for), which already follow governance practice |
| 5 Read-only; minimal editing with approvals | D230, D231, Z5, A1 | A Reader role, and a Contributor who edits only in change sets and submits them |
| 6 Roles for systems | I1, Z3 (D226) | An OAuth client is a principal like a person and holds roles the same way; consumer API access is one of its grants |
| 7 User management | I1, I2, SP1 | Create, invite, deactivate, reset, sign out everywhere, last sign-in, sessions; the account page |

**Two conflicts with recorded decisions, explained before anything is built** (CLAUDE.md):

- **Approvals (idea 3) against the roadmap and PRODUCT.md.** ROADMAP puts "protected publish,
  activation and rollback" in 1.0, and PRODUCT.md says "any additional mandatory review step needs a
  stated user benefit and an explicit product decision", because a data owner's daily correction
  must stay live when saved (ADR-026). The proposal in D232 keeps that rule: nobody is forced through
  an approval unless a role or a workspace policy says so, and a person allowed to approve their own
  publication publishes in one step, as today. It moves only change-set publication approvals into
  0.12; approving a model activation or a rollback stays in 1.0. The user decides.
- **"Model-configurable permissions"** (ARCHITECTURE) against ADR-031 ("lives in the database,
  managed in the UI, set by an authorized administrator"). Roles and grants are runtime data, not
  part of a model release: a model change would otherwise be able to grant itself access, and roles
  could not change without a release. Grants **refer to** the model's applications and record types.
  P0 corrects ARCHITECTURE's wording.

## Principles and exclusions

1. **One gate, every path.** Every route declares the action it performs; a request is checked once
   at the route for the action and the workspace, and again at the write unit for the record types
   it writes. Bulk work, jobs, imports, moves and the feed go through the same check; a route without
   a declaration fails a contract test (the exit gate: "cannot be bypassed").
2. **People and systems alike.** A user, a group and an OAuth client are principals; each holds roles
   at a scope. No path is reserved to one kind.
3. **Roles are data.** Built from action groups, granted at the instance or a workspace, narrowed to
   applications and record types. They are never in the model and never in a deployment setting.
4. **The deployment flags stay** (ADR-031): a flag decides whether this installation exposes an
   operation at all, a role whether this caller may use it. Neither replaces the other.
5. **The engine issues the tokens** (C-D1): one issuer, one token format, for the browser, the
   management API, the consumer APIs and the "try it" console. A sign-in provider (OIDC) may prove a
   person's identity; the engine still issues the token.
6. **No ceremony by default** (ADR-026): with the predefined roles, a data owner's correction is
   still live when saved. An approval applies only where a role or policy asks for it.
7. **API first.** Users, groups, roles, grants, clients, keys, approvals and the inbox are API
   resources; the Security pages are one client.
8. **Generic.** No permission names an application or record type in code; grants refer to them as
   data, and every journey runs on `generated-a` and `generated-b` side by side.
9. **Nothing secret is read back.** Passwords, client secrets and signing keys are shown once at
   creation or rotation; reads return their age, never their value.

Excluded: record-level permissions (ARCHITECTURE: only on demonstrated need), hiding record types
from readers inside a workspace (D228), multi-tenancy, e-mail (D233), approvals of model activation
and rollback (1.0), SAML and LDAP (D224), API keys, a workflow or business-process engine (D242).

**Composable domains (ADR-032):** the identity and audit doors are touched. The actor is recorded
beside `cause`, never instead of it, so a value source stays additive; an OAuth client writing for a
source system is that source's natural name (ROADMAP 0.12).

## What already exists

Checked against the code at `272a9c0`:

- **No authentication anywhere.** No middleware, dependency, session, token or credential; the
  frontend's `api/client.ts` sends no `Authorization` header. The account menu shows "Local
  session", "Single-user mode" and a disabled "Sign in" (`app/SettingsMenu.tsx`).
- **Attribution by cause only.** `audit_events.cause_kind/cause_id` are set for a job or a
  publication (`engine/records/audit.py`), otherwise null, and the feed shows `cause.kind: "user"`
  as a literal. `model_draft_operations.author` and `model_mapping_operations.author` exist and are
  always null. No table has `created_by`; `jobs` has no requester.
- **Four capability flags** (`config.py`) decide which routers are registered at startup
  (`main.py`): model administration (off), workspace administration (on), integration jobs (on),
  consumer subscriptions (off). `GET /api/v1/capabilities` reports them.
- **About 157 management operations** in 19 routers under `/api/v1`, eight consumer routes under
  `/api/consumer` (registered with no dependency), and `/health`, `/health/live`, `/metrics` and
  `/docs` outside both.
- **Change sets have no state**: they are created, renamed, validated (an audit event, not a state),
  published or discarded; publication re-validates. Jobs have `awaiting_confirmation` and a confirm
  bound to the reviewed versions, the pattern an approval reuses.
- **Webhook signing keys**, one per subscription, sealed with AES-256-GCM under a format byte meant
  for re-sealing (C-D96); no rotation. `cryptography` is already a runtime dependency.
- **Notifications** are `pg_notify` + SSE for jobs, shown as toasts only in the tab that started the
  job (0.9 J1u: "per-person notifications need the users of 0.12").
- **Cross-process signals** (0.11 N1): assignment changes reach every process through `pg_notify`;
  permission changes reuse it.

## Design documents

| Document | Holds | State |
| --- | --- | --- |
| This plan | Outcome, tracks, packages, decisions, records | Planned 2026-10-22 |
| [DECISIONS.md](DECISIONS.md) | ADR-043 identity and tokens; ADR-044 authorization (catalogue, roles, scopes, where checks run); ADR-045 approvals if D232 is accepted; ADR-031's prose corrected ("0.11" → 0.12) | Written in P0 |
| [API.md](API.md), [CONSUMER_API.md](CONSUMER_API.md) | The OAuth endpoints, principals, roles, grants, `/me`, clients, rotation, approvals, inbox | Designed in P0 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | "Model-configurable permissions" corrected; the request's path through the two checks | P0 |
| [SETTINGS_AND_UI_PLAN.md](SETTINGS_AND_UI_PLAN.md) | U8 detailed: the Security pages, the sign-in page, the inbox | P0 with the mock-ups |
| [USER_JOURNEYS.md](product-functionality/USER_JOURNEYS.md), [API_JOURNEYS.md](testing/API_JOURNEYS.md) | J39 sign in, J40 manage access, J41 a system calls with a client, J42 propose and approve, J43 rotate a signing key | P0 |
| [OPERATIONS.md](OPERATIONS.md) | Token signing keys, the first administrator, a sign-in provider, recovering a locked-out instance | I1, I3 |

## Scope inventory

| # | Roadmap 0.12 item, or the user's idea | Package |
| --- | --- | --- |
| 1 | OAuth 2.0 and JWT for the management API, frontend and consumer APIs | I1, I2, Z3 |
| 2 | Authorization per application, record type and operation; per consumer API for clients | Z1, Z2, Z3 |
| 3 | Rotation of webhook signing keys | K1 |
| 4 | UI administration: the Security pages (U8) | SP1, SP2 |
| 5 | Audit identity | Z4 |
| 6 | Protected model and workspace administration; flags kept | Z1, Z2 |
| 7 | Authentication in the "try it" console | C1 |
| 8 | Licensing, policies, the compatibility commitment | L1, L2 |
| — | Groups; predefined and custom roles; action groups (ideas 1, 2, 4) | Z1, SP1 |
| — | A sign-in provider (OIDC) and its groups | I3 |
| — | The interface follows the caller's permissions; read-only and minimal editing (idea 5) | Z5 |
| — | Approvals and the inbox (idea 3, D232) | A1–A3 |
| — | The security exit gate composed; independent review (AGENTS.md) | E1 |

## Tracks overview

**P0 — design pass:** the permission catalogue (every route mapped to an action, actions grouped by
journey), the predefined roles, ADR-043/044, the API design, J39–J43, and browser mock-ups of the
sign-in page, the account menu, Settings › Security and the approval flow, shown with P0's plan for
one approval.

**Track I — identity:** I1 the issuer, users and clients, every route authenticated; I2 the browser's
sign-in; I3 a sign-in provider.

**Track Z — authorization:** Z1 roles, groups and grants enforced at the route; Z2 record types at the
write unit, and jobs, moves and the feed; Z3 the consumer APIs per client; Z4 audit identity; Z5 the
interface follows permissions.

**Track SP — the Security pages:** SP1 people, groups and roles; SP2 OAuth clients and their access.
**K1** signing-key rotation. **C1** the "try it" console. **E1** the security checkpoint.

**Track A — approvals (if D232 is accepted), after the cut line:** A1 a publication request and its
approval; A2 the inbox; A3 the approval policy per workspace in the interface.

**Track L — first public release:** L1 licensing and policies; L2 the compatibility commitment, which
now includes the authentication contracts. **R** build acceptance and release.

### Why identity first, then authorization

Nothing can be authorized without a principal, and no test can call the API once routes require a
token unless the harness can obtain one. I1 therefore makes every route require authentication with a
single all-powerful role in the same package, and switches the journey harness to real tokens; Z1
then narrows what each role may do. Each later package changes only what a role may do, not how a
test reaches the engine.

## Packages

### P0: Design pass

**Scope:** the permission catalogue: every one of the ~157 management operations, the eight consumer
routes and the infrastructure routes mapped to an action, and the actions grouped into action groups
named after journeys (draft list below, completed against the routers); the predefined roles (D230);
ADR-043 and ADR-044; the API design in API.md and CONSUMER_API; J39–J43 with their cases; the browser
mock-ups listed above; the corrections to ARCHITECTURE and ADR-031. Every decision below settled.

**Draft action groups** (P0 completes and checks them against every route):

| Action group | What it allows | Scope it can be granted at |
| --- | --- | --- |
| Browse | Read records, lists, history, relations, matrices, the cross-type lookup, exports to a file | Workspace (application) |
| Edit live | Create, change and delete records, values, parents, relations and translations without a change set | Workspace, application, record types |
| Work in change sets | Create, edit, validate, rename and discard change sets; edits inside them | Workspace, application, record types |
| Publish | Publish a change set; withdraw a publication | Workspace |
| Approve publications (Track A) | Approve or reject another person's request; with "own", one's own | Workspace |
| Bulk and import | Batches, imports, profiles, source files, dry runs | Workspace, application, record types |
| Copy and move | Model-to-model mappings; moves (read on the source, write on the target, 0.11 I33) | Workspace pair |
| Model authoring | Model drafts, compiling, mapping editing | Instance |
| Model release | Installing, activating and migrating a workspace's release | Instance or workspace |
| Workspace administration | Create, rename, retire, delete workspaces; the default | Instance |
| Integration administration | Consumer API subscriptions, webhook keys and deliveries | Workspace |
| Feed | Read the change feed | Workspace |
| Operations | `/system`, `/metrics`, readiness detail, the backup rehearsal record | Instance |
| Security administration | Users, groups, roles, grants, clients, sign-in providers, token keys | Instance |

A consumer API is not an action group: a client is granted **read of a named consumer API in a
workspace** (Z3), because a consumer API key may mean different contracts in two workspaces
(ADR-042).

### Track I — Identity

#### I1: The issuer, people and clients; every route authenticated

**Needs:** P0.

**Scope:** the engine as an OAuth 2.0 authorization server: token signing keys in the database
(sealed like webhook keys, rotated with overlap, published at the JWKS endpoint for every node),
the token, revocation and discovery endpoints; **users** (local accounts with a password hashed
with Argon2id, deactivation, never deletion, D237) and **OAuth clients** (client credentials grant,
secret shown once, two secrets valid during a rotation); a refresh-token store with revocation
("sign out everywhere"). Every route requires a valid access token except the discovery, token,
JWKS, `/health/live` and the sign-in page; `/health` readiness detail and `/metrics` become
Operations-only in Z1. The first administrator is created with `python -m app.cli.create_admin`
(D235). The journey harness and the browser harness obtain real tokens; with one temporary role,
"all actions", until Z1. `/me` returns the caller.

#### I2: Signing in from the browser

**Needs:** I1.

**Scope:** the engine's sign-in page (username and password; a sign-in provider's button from I3),
the authorization code flow with PKCE for the frontend (D234), the access token kept in memory and
renewed through a refresh token in an `HttpOnly`, `SameSite=Strict` cookie; sign-out; the account
menu showing the person, "Account" and "Sign out" in place of the placeholder; the account page
(change password, sessions with "sign out everywhere", the person's roles read-only). Expired or
revoked sessions return to the sign-in page and back to where the person was.

#### I3: A sign-in provider

**Needs:** I2.

**Scope:** one or more OpenID Connect providers configured in Settings › Security › Sign-in (issuer,
client ID, secret, the claim holding groups): a person signs in there, the engine finds or creates
the user by issuer and subject, takes the provider's groups as **provider groups** (D229), and issues
its own token. Local accounts can be switched off once a provider works, with the first
administrator kept as the way back (OPERATIONS). Tested against a minimal provider in the harness;
one sign-in against a real provider the user names (Microsoft Entra ID, Google, Keycloak) before E1.

### Track Z — Authorization

#### Z1: Roles, groups and grants at the route

**Needs:** I1, P0's catalogue.

**Scope:** action groups, predefined roles (D230, read-only) and custom roles (made of action groups,
copied from a predefined one or empty); local groups and membership; **grants**: a principal (user,
group, client) holds a role at the instance or in a workspace, optionally narrowed to applications
and record types (D228). Every route declares its action; the request is refused with
`403 FORBIDDEN` naming the action and the workspace when no grant allows it, and the contract test
refuses a route without a declaration. Effective permissions are resolved on the server per request
from a cache invalidated across processes through `pg_notify` (D226). `GET /me/permissions` per
workspace. The temporary "all actions" role from I1 becomes the predefined Security administrator
plus Owner of every workspace for the first administrator.

#### Z2: Record types at the write unit, jobs, moves and the feed

**Needs:** Z1.

**Scope:** the record-type narrowing enforced where writes happen, so a bulk change, an import, a
move, a change set's publication and a type change (ADR-034) are refused for the types the caller may
not write, checked as one set in PostgreSQL over the work's distinct types, never row by row.
**Jobs run with their requester's permissions** (`jobs.requested_by`), checked at submission and
again at confirmation and execution (D236). A move needs read on the source and write on the target
(0.11 I33). A grant naming a record type the workspace's model no longer has is reported on the
grant, never silently widened. The feed, exports and the cross-type lookup across workspaces return
only workspaces the caller may browse.

#### Z3: Consumer APIs per client

**Needs:** Z1.

**Scope:** the consumer routes require a token; a client reads a consumer API in a workspace only with
a grant for that consumer API there (Z1's grant with a consumer API instead of a role). Subscriptions
are owned by the client or person who created them and managed under Integration administration.
The per-definition OpenAPI document states the security scheme. `401` and `403` are added to the
consumer contract (CONSUMER_API) with the same envelope.

#### Z4: Audit identity

**Needs:** Z1.

**Scope:** `audit_events` and `consumer_events` gain the actor (`actor_kind`: user or client,
`actor_id`) beside `cause`; `author` on model draft and mapping operations is filled; change sets
record who created them, publications who published them, jobs who requested them, subscriptions who
created them. History, the feed, change-set review and the model editor's history show the actor's
name, resolved when read (D237). Changes from before 0.12 show "Before sign-in". Whether consumer
events carry the actor: D239.

#### Z5: The interface follows the caller's permissions

**Needs:** Z1, Z2, I2.

**Scope:** the frontend reads `/me/permissions` for the current workspace and hides what the person may
not open (settings pages, model administration) and disables, with the reason, what they may see but
not do ("You can read this workspace"). A Reader's record view has no edit affordance at all. A
Contributor (D231) edits only in change sets: the record view offers "Propose a change", which opens
or continues their change set, instead of saving live. Every guard stays on the server; the interface
only avoids offering what would be refused.

### Track SP — The Security pages (U8)

#### SP1: People, groups and roles

**Needs:** Z1, I2; the mock-up approved in P0.

**Scope:** Settings › Security › People (list and detail: create, invite with a one-time link,
deactivate, reset password, sign out everywhere, last sign-in, their grants), Groups (local and
provider groups, members, grants), Roles (predefined read-only, custom created and edited as a
matrix of action groups), and the grants per workspace from both sides ("who can do what here").
Every page uses the list-and-detail pattern (U-D10) and the UI foundation; no page names an
application or record type.

#### SP2: OAuth clients and their access

**Needs:** Z3, SP1.

**Scope:** Settings › Security › Clients: create a client, its secret shown once, rotate it with an
overlap, deactivate it; its roles on the management API and its consumer API grants per workspace;
last use. Sign-in providers (I3) on Settings › Security › Sign-in.

### K1: Webhook signing-key rotation

**Needs:** Z1.

**Scope:** `POST /api/v1/consumer-subscriptions/{id}/rotate-secret` (CONSUMER_API): a new key shown
once; during an overlap window (D238) deliveries carry both signatures in `RDM-Signature`, after it
only the new one, so a rotated key stops verifying (the exit gate). The re-sealing of every key under
a new `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (C-D96's format byte) as a CLI command. "Rotate key" on
the webhook's page.

### C1: The "try it" console authenticated

**Needs:** I2.

**Scope:** `/docs` sends requests with the signed-in person's token (D240); a client's token can be
pasted for testing a client's view. `/docs/oauth2-redirect` stays 404.

### E1: Security checkpoint

**Needs:** Z1–Z5, I1–I3, SP1, SP2, K1, C1.

**Scope:** the exit gate composed: a sweep that calls every operation in the catalogue as each
predefined role and as a client without grants and checks allowed or refused against the catalogue
(generated from the declarations, so a new route is covered by adding it); a reader refused on every
write path including bulk, jobs, imports, moves, feed and consumer routes (SC-13, US-S01); an editor
narrowed to one record type refused on the others through every path; tokens expired, revoked,
signed by a retired key or for another audience refused. **An independent security review** of the
changes (AGENTS.md), with its findings fixed or recorded before R. The real sign-in provider try (I3)
is reported here.

### Track A — Approvals (if D232 is accepted), after the cut line

#### A1: A publication request and its approval

**Needs:** Z1, Z4.

**Scope:** a change set gains states: open → **submitted** (its content frozen; an edit withdraws the
submission) → **approved** or **sent back** with a comment → published. The approval is bound to the
change set's version and the workspace's active publication, as a job confirmation is bound to the
reviewed versions; publication re-validates as today. Who must ask: a person holding Work in change
sets without Publish. Who approves: Approve publications; with "own", a person approves their own
request in the same step as publishing, which is today's single click (the user's idea). A workspace
policy "a second person approves" (four-eyes) removes "own" in that workspace. API first: submit,
approve, send back, withdraw, list requests. Audit records each step with its actor. Each decision is
stored as its own row (who, when, the version, the outcome, the comment), not as one "approved by"
field, so several approvers or ordered stages can be added later without a contract change (D242).

#### A2: The inbox

**Needs:** A1, I2.

**Scope:** per-principal notifications in the database (a request to approve; a decision on one's
request; a job one started finished, replacing the tab-only toasts of J1u), `GET /me/notifications`
cursor-paged with read and unread, a live stream over the existing `pg_notify`/SSE path, and an inbox
in the top bar. Approval requests are also consumer webhook events (`change-set.submitted`,
`change-set.approved`, `change-set.sent-back`) so an organisation routes them to e-mail or chat
itself (D233).

#### A3: Approvals in the interface

**Needs:** A2, Z5; the mock-up approved in P0.

**Scope:** "Submit for publication" for a Contributor, "Approve and publish" and "Send back" on the
change-set review for an approver, the request's state and comments in the change set's header, the
four-eyes policy on Settings › Workspaces. Smoke on a real Contributor → Steward round trip.

## Decisions

**Accepted by the user on 2026-10-22**, each as recommended (D232: yes, Track A after the cut
line). Each is explained in plain words: what is decided, why the recommendation, and what it costs.

| # | Question | Recommendation |
| --- | --- | --- |
| D224 | Where people's identities come from | **Recommended:** local accounts **and** OpenID Connect sign-in providers (I3), the engine issuing its own token either way (C-D1). Why: an organisation already has a directory (Entra ID, Google, Okta, Keycloak) and expects its people to sign in with it, its MFA and its leavers' process; local accounts are still needed for the first administrator, small installations and a way back when the provider fails. SAML and LDAP are left out: most providers speak OIDC, and SAML adds a second protocol to keep secure. Cost: I3 as a package, a minimal provider in the test harness |
| D225 | Multi-factor authentication | **Recommended:** left to the sign-in provider in 0.12; local accounts have password only, which OPERATIONS states with the advice to use a provider in production. TOTP for local accounts in TODO for after 1.0. Why: MFA is what the organisation's provider already does well; building TOTP, recovery codes and resets is a package of its own. Cost: an installation with local accounts only has no second factor |
| D226 | Where permissions live in a request | **Recommended:** the token proves **who** (subject, client, expiry, a coarse audience: management or consumer); **what** they may do is looked up on the server per request from a cache invalidated across processes when a grant changes. Why: a role removed takes effect on the next request, not when a token expires; tokens stay small however many workspaces a person works in. Cost: one cached lookup per request; the cache invalidation (reusing N1's signal) |
| D227 | How roles are made | **Recommended:** the user's idea as stated: **action groups** named after journeys (P0's table) → **roles** made of action groups → **grants** of a role to a user, group or client at a scope. Predefined roles are read-only; a custom role is created from scratch or copied from one. Why: an administrator thinks in jobs ("may publish"), not in 157 routes; a new route joins an existing group without touching any role. Cost: the catalogue's upkeep, checked by the contract test |
| D228 | Scopes of a grant | **Recommended:** the instance or one workspace; within a workspace optionally narrowed to applications and record types **for writes**; reads are per workspace (and application). Why: SC-13 asks that "a permitted editor can edit only the assigned scope"; hiding a record type from a reader would need every list, query, relation column, feed, export and lookup filtered, with no user need recorded (ARCHITECTURE: record-level and finer rules only on demonstrated need). Workspaces are already the governed scope (ADR-031). Cost: data that must be hidden from some readers goes in its own workspace |
| D229 | Groups | **Recommended:** local groups managed in the engine, plus **provider groups** taken from a sign-in provider's claim at each sign-in; both hold grants the same way; no nested groups. Why: the user's idea 1, and in an organisation with a directory, membership is managed there and only the grant lives in the engine. Cost: a provider group's members are only known after they sign in once |
| D230 | The predefined roles | **Recommended**, named after the PRODUCT personas and common governance practice: **Reader** (Browse), **Contributor** (Browse, Work in change sets: proposes, cannot publish, D231), **Editor / Data steward** (Browse, Edit live, Work in change sets, Publish, Bulk and import), **Data owner** (Steward's groups plus Approve publications with own, Feed, Copy and move), **Model administrator** (Model authoring, Model release), **Workspace administrator**, **Integration administrator** (Integration administration, Feed), **Operator** (Operations), **Security administrator** (Security administration only, no data). For clients: **Consumer** (consumer API grants only) and any role above. Why: covers ideas 4 and 5 with names people recognise, and separates security administration from data so no single default role does everything. Cost: names to agree; nine roles to keep true in the catalogue |
| D231 | Editing live as its own permission | **Recommended:** Edit live and Work in change sets are separate action groups. Why: it is what makes the Contributor of idea 5 possible: a person who can change things only by proposing them. With today's behaviour (a correction is live when saved) the Editor keeps live editing. Cost: Z2 checks the two separately on every write path |
| D232 | Approvals in 0.12 | **The user decides; conflicts with the roadmap (1.0) and PRODUCT.md's rule.** Recommended: **yes, change-set publication only, as Track A after the cut line**, with self-approval for those whose role allows it and a per-workspace four-eyes policy. Why: with D231, a Contributor's change set otherwise waits for someone to notice it; approval needs identity and roles, which 0.12 brings, and its smallest useful flow (submit, review, approve or send back with a comment, notify, audit; REAL_WORLD_RESEARCH) is small once they exist. No one is forced into it: the default roles publish as today, which keeps ADR-026. Approvals of model activation and rollback stay in 1.0's protected publishing. Cost: Track A (three packages); if 0.12 must ship sooner, the cut line releases without it and it follows in 0.12.x |
| D233 | How approvals notify | **Recommended:** an inbox in the engine (API and top bar) and webhook events for each step; **no e-mail** in 0.12. Why: API first: an organisation routes the events to its e-mail, Teams or Slack with its own tooling; sending mail needs SMTP settings, templates, bounces and unsubscribes. Cost: without integration work, a person learns of a request only when they open the app |
| D234 | How the browser holds its session | **Recommended:** authorization code with PKCE; the access token (short, about 10 minutes) in memory, the refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie that only the token endpoint reads. Why: the current OAuth guidance for browser applications; a script injected into the page cannot read the refresh token, and the engine still issues one token format for all clients. Cost: the frontend and engine must share a site (one origin or a same-site subdomain), which OPERATIONS states |
| D235 | Is there a way to switch authentication off? | **Recommended:** **no**. Development and tests use real tokens; the first administrator comes from a CLI command on the server. Why: a switch that disables security is eventually left on in production, and ADR-031 already says "a switch cannot guard itself". Cost: the harness changes in I1 (one fixture), and the local dev server needs a sign-in once |
| D236 | Whose permissions a job runs with | **Recommended:** its requester's, checked at submission, at confirmation and when it runs; a requester deactivated or losing the right makes the job fail with the reason. Why: a job is the bulk path the exit gate names; a job queued before a permission was removed must not keep it. Cost: one check per job step |
| D237 | People in the audit | **Recommended:** the audit stores the principal's ID; names are resolved when read. Users and clients are deactivated, never deleted, so history always resolves; a person's name and e-mail can be anonymised in one place. Why: a name copied into every audit row could not be erased, and a deleted user would leave unexplained IDs. Cost: a join when history is read |
| D238 | The webhook key's overlap window | **Recommended:** both signatures sent for 24 hours after a rotation by default, set per rotation from 0 (immediate) to 7 days. Why: receivers switch keys without missing deliveries; 0 covers a leaked key. Cost: a contract change: `RDM-Signature` carries one `sha256=<hex>` today and becomes a comma-separated list, which receivers must accept (CONSUMER_API, before L2 commits the header) |
| D239 | The actor in consumer events | **Recommended:** management feed and history show the actor; **consumer events do not**. Why: consumer events go to external systems, and the person who edited a record is personal data they rarely need; a value source (the composable-domains door) is the right field for systems. Cost: an integrator who needs the person reads the management feed |
| D240 | The "try it" console | **Recommended:** it uses the signed-in person's token, so it shows what that person may do; a client token may be pasted. Why: no second sign-in, and the console never offers operations the person would be refused. Cost: none beyond C1 |
| D242 | Configurable workflows | **Accepted by the user, 2026-10-22 ("let's go for simplicity").** No workflow or business-process engine: no process designer, branches, task routing, timers or escalations. The approval is configured as a policy (who must ask, which roles approve, own approval, one or two approvers), and an organisation's own process tool (ServiceNow, Jira, Power Automate, Camunda) drives longer processes through A2's webhook events and the approval API with an OAuth client. Why: reference-data review is one flow (propose, check, publish); a process engine would be the largest part of the product for that one job, and PRODUCT.md excludes an enterprise governance suite. Each decision stored as its own row keeps several approvers or stages additive. Cost: multi-stage processes with deadlines live outside the engine |
| D241 | The workspace administration flag's default | **Recommended:** stays on; now a role protects it, as ROADMAP's "replacing the default-enabled workspace mutation posture" asks. The other flags keep their defaults. Why: the flag was on only because nothing else protected it; turning it off would hide a feature behind a deployment setting with no security gain. Cost: none |

## Delivery queue

| # | Package | Needs | Scope in one line |
| --- | --- | --- | --- |
| 0 | — | 0.11.0 released | **Met 2026-10-22** |
| 1 | [P0](#p0-design-pass) | — | The catalogue and action groups, roles, ADR-043/044, API design, J39–J43, mock-ups; D224–D241 settled |
| 2 | [I1](#i1-the-issuer-people-and-clients-every-route-authenticated) | P0 | The issuer, users and clients, every route authenticated, harnesses on real tokens |
| 3 | [I2](#i2-signing-in-from-the-browser) | I1 | The sign-in page, PKCE, the account menu and page |
| 4 | [Z1](#z1-roles-groups-and-grants-at-the-route) | I1 | Roles, groups and grants; every route checked; `/me/permissions` |
| 5 | [Z2](#z2-record-types-at-the-write-unit-jobs-moves-and-the-feed) | Z1 | Record types at the write unit; jobs as their requester; moves; the feed |
| 6 | [Z3](#z3-consumer-apis-per-client) | Z1 | Consumer APIs per client and workspace |
| 7 | [Z4](#z4-audit-identity) | Z1 | The actor beside `cause` everywhere |
| 8 | [Z5](#z5-the-interface-follows-the-callers-permissions) | Z2, I2 | The interface follows permissions; Reader and Contributor |
| 9 | [SP1](#sp1-people-groups-and-roles) | Z1, I2 | Settings › Security: people, groups, roles, grants |
| 10 | [SP2](#sp2-oauth-clients-and-their-access) | Z3, SP1 | Settings › Security: clients and their access; sign-in providers |
| 11 | [I3](#i3-a-sign-in-provider) | I2, SP2 | OpenID Connect providers and their groups |
| 12 | [K1](#k1-webhook-signing-key-rotation) | Z1 | Signing-key rotation with overlap; re-sealing |
| 13 | [C1](#c1-the-try-it-console-authenticated) | I2 | The console with the person's token |
| 14 | [E1](#e1-security-checkpoint) | all above | The exit gate composed; independent security review |
| — | _cut line_ | | _If R is out of reach, 0.12.0 releases here and Track A follows in 0.12.x_ |
| 15 | [A1](#a1-a-publication-request-and-its-approval) | Z1, Z4 | Submit, approve or send back, self-approval, four-eyes policy |
| 16 | [A2](#a2-the-inbox) | A1, I2 | The inbox; webhook events per step |
| 17 | [A3](#a3-approvals-in-the-interface) | A2, Z5 | Approvals on the change-set review |
| 18 | [L1](#l1-licensing-and-policies) | — | Licensing and policies (filler, any time) |
| 19 | [L2](#l2-the-compatibility-commitment) | E1 (A3 if delivered), the project's name | The compatibility commitment, now including the authentication contracts |
| 20 | R | all above the cut | Build acceptance and the first public release |

```text
Design:     P0
Identity:   P0 ─ I1 ─ I2 ─────────────── I3 (needs SP2)
Authz:           I1 ─ Z1 ─┬─ Z2 ─ Z5 (needs I2)
                          ├─ Z3 ─ SP2
                          ├─ Z4
                          ├─ SP1 (needs I2) ─ SP2
                          └─ K1
Console:              I2 ─ C1
Gate:       everything above ─ E1 ── cut line ── A1 ─ A2 ─ A3
Public:     L1 (filler) ; E1/A3 + the name ─ L2 ─ R
```

**The project's name** blocks L2 and should be chosen before I1 ships its token issuer and before L2
commits the `RDM-*` headers; until then new identifiers stay free of it (as above).

## Track L — First public release

### L1: Licensing and policies

**Scope:** the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md); contribution
and security policies.

#### L1 plan (2026-10-22)

**Planned 2026-10-22, waiting for the user's acceptance.** Checked against the code at `272a9c0` by
reading it.

**What was found:**

- **The licence is chosen, the documents say it is not.** `LICENSE` is the unmodified AGPL-3.0 and
  LICENSING_TODO records `AGPL-3.0-or-later`; the README's last paragraph ("not ready for public
  release until an open-source licence is selected") and OPEN_SOURCE.md's "Licence decision" (no
  licence, Apache-2.0 as default) predate it.
- **No policy file exists:** no `CONTRIBUTING.md`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`,
  `COMMERCIAL.md` or `TRADEMARKS.md`. The repository has no remote, so no public URL exists yet to
  link source, reports or tags to.
- **A running instance does not offer its source** (AGPL §13). `GET /system` (J31) serves
  `engine.version` and `engine.managementApi`; Settings › About shows them; the OpenAPI document has
  no `info.license`.
- **Third-party inventory, runtime closure** (read from the installed environments): backend 27
  distributions, all permissive (MIT, BSD-3-Clause, Apache-2.0, PSF-2.0, MIT-0) except
  **psycopg / psycopg-binary, LGPL-3.0-only** (compatible with AGPL-3.0-or-later; the binary wheel
  also bundles libpq, OpenSSL 3, MIT Kerberos and OpenLDAP, whose licences the wheel does not carry).
  Frontend 21 packages: MIT, Apache-2.0 (React Aria, `@swc/helpers`), ISC (lucide), 0BSD (tslib),
  OFL-1.1 (the two fonts). Vendored in the repository: Scalar's `standalone.js` (MIT, with its
  `LICENSE`). Nothing incompatible.
- **Authorship:** the history has one author, Krisztian Toth (316 commits). No secret scanner is
  installed.

**What is built:**

1. **README** licence section: `AGPL-3.0-or-later`, the copyright line, where each release's source
   is (its tag), what a networked modified deployment must offer and how the setting below does it.
2. **`CONTRIBUTING.md`**: issues and discussion welcome; code contributions not merged until the
   contribution agreement exists (D217); the coding, test and review expectations by reference to
   AGENTS.md and the testing strategy; inbound licence AGPL-3.0-or-later; the copyright convention
   (D216, D222).
3. **`SECURITY.md`**: the private reporting route (D218), the supported releases (the latest minor
   only, before 1.0), acknowledgement within 7 days as a solo maintainer's best effort with no
   24/7 promise, coordinated disclosure, credit in the advisory and CHANGELOG, and that a security
   fix is a new tagged release whose tag is the corresponding source.
4. **`THIRD_PARTY_NOTICES.md`**, generated by `scripts/third_party_notices.py` (D220): the backend's
   runtime closure from the installed environment (dev tools excluded), the frontend's production
   closure from `node_modules`, the vendored Scalar file and the libraries inside the psycopg
   wheel; each with version, licence and the licence text, Apache-2.0 `NOTICE` files included. The
   script fails on a licence outside an allow-list, so an incompatible addition stops R.
5. **`TRADEMARKS.md`** and **`COMMERCIAL.md`**, short (D221).
6. **The source offer in a running instance** (D219): a setting `SOURCE_CODE_URL`; `GET /system`
   gains `engine.license` (`AGPL-3.0-or-later`) and `engine.sourceCode`; the OpenAPI document gains
   `info.license` (SPDX identifier); Settings › About gains two rows, and the account menu a footer
   line, so every page reaches it in two clicks:

   ```text
   Account menu, below "All settings":     Settings › About › Engine
     Source code · AGPL-3.0-or-later         Engine version     0.11.0
                                             Management API     v1
                                             Schema languages   0.5, …, 0.10
                                             Licence            AGPL-3.0-or-later
                                             Source code        <link to the URL>
   ```

7. **Secret scan** of the whole history with `gitleaks` (Homebrew binary), once; findings reported,
   not rewritten without the user (D223).
8. **Documents:** LICENSING_TODO ticked item by item, with what remains the user's or counsel's;
   OPEN_SOURCE.md's licence section replaced by the ownership record (D216) and the dependency
   decisions; OPERATIONS (the setting), API.md (`GET /system`), J31 gains J31.4, API_JOURNEYS,
   CURRENT_FUNCTIONALITY, CHANGELOG, PROJECT_STATUS, TODO.

**What L1 cannot close.** Legal advice, counsel's review of a contribution agreement, the
commercial agreement template and trademark registration are the user's with counsel; the
confirmation that no employer, client or vendor holds rights is the user's alone. They stay open in
LICENSING_TODO, named as the user's, and L1 is reported done without them only if the user accepts
this split.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D216 | Copyright holder and ownership record | **Recommended:** "Copyright (C) 2026 Krisztian Toth", the personal name, in README and the ownership record, since the history has one author. **The user confirms** that no employer, former employer or client holds rights in the work, and that the committed example model and data are synthetic. Cost: none; a company name later is a notice change on new files, not a relicence |
| D217 | Outside contributions before 1.0 | **Recommended:** not merged until a counsel-reviewed contributor licence agreement exists; issues welcome. Keeps commercial relicensing open (a DCO alone would not). Cost: no outside pull requests until then |
| D218 | The private security reporting route | **The user names it.** Recommended: an address used only for this (not the personal one), plus GitHub private vulnerability reporting once the public repository exists. Cost: one mailbox to watch |
| D219 | How a running instance offers its source | **Recommended:** `SOURCE_CODE_URL`, default the public repository's tag of the running version (`<repository>/tree/v<version>`); an operator running a modified version must set it to their own source, which README and OPERATIONS say. Shown in `GET /system`, OpenAPI `info.license`, About and the account menu. **Needs the public repository URL from the user**; until then the default is empty and About shows "Not set". Cost: one setting, a contract change on `/system` (lock re-baselined) |
| D220 | Notices: written or generated | **Recommended:** generated by a script from the installed environments, checked in, regenerated in every R; the four libraries inside the psycopg wheel and their licence texts listed in the script by hand, since the wheel does not carry them. Cost: the script; it reflects this machine's platform wheel, which R states |
| D221 | Commercial and trademark pages in the first public release | **Recommended:** both, short: TRADEMARKS.md says "RDM Engine" may be used to refer to the software, and a modified build must not present itself as the official one; no logo exists yet. COMMERCIAL.md says licences, support and assistance are negotiated per customer through D218's contact route (or another the user names), with no service level promised. The agreement template stays counsel's. Cost: two pages to keep true |
| D222 | Per-file licence headers | **Recommended:** none; the notice in README and LICENSE covers the repository, and CONTRIBUTING says so. Cost: a file copied out alone carries no notice, which the AGPL does not require |
| D223 | A secret found in the history | **Recommended:** reported with its commit and path; the secret is rotated and, if the user wants, the history rewritten before the first push. Nothing rewritten in L1 |

**Journey test cases** (J31.4, `GET /system` and the OpenAPI document, both harness model
configurations):

1. Given no `SOURCE_CODE_URL`, when `GET /system` is read, then `engine.license` is
   `AGPL-3.0-or-later` and `engine.sourceCode` is the default (D219: the repository's tag of the
   version, or `null` while no repository is named).
2. Given `SOURCE_CODE_URL` set to an operator's URL, when `GET /system` is read, then
   `engine.sourceCode` is that URL, and the setting reads it back in `GET /system`'s settings with
   source `environment`.
3. When the OpenAPI document is read, then `info.license.identifier` is `AGPL-3.0-or-later`.
4. Given a `SOURCE_CODE_URL` that is not an `http(s)` URL, when the engine starts, then it refuses
   with the setting named (J12's configuration refusal).

Unit: the notices script's licence allow-list refusal. UI: About and the account menu in Vitest,
and one look at both at 1440px and 390px in light and dark (the reference pattern: About's
`DescriptionList`).

### L2: The compatibility commitment

**Needs:** 0.11 V4 (delivered).

**Scope:** the compatibility commitment for the public contracts; the supported schema versions and
their migration and removal dates published; the [composable domains doors](COMPOSABLE_DOMAINS.md#doors-to-keep-open)
checked against it (a retired-ID redirect, a value source, derived read-only values and a new value
type each addable without a breaking change).
