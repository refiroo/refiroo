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
| — | A record's parent as a list column and filter (the user, 2026-10-25) | TV1 |
| — | The security exit gate composed; independent review (AGENTS.md) | E1 |

## Tracks overview

**P0 — design pass:** the permission catalogue (every route mapped to an action, actions grouped by
journey), the predefined roles, ADR-043/044, the API design, J39–J43, and browser mock-ups of the
sign-in page, the account menu, Settings › Security and the approval flow, shown with P0's plan for
one approval.

**Track I — identity:** I1 the issuer, users and clients, every route authenticated; I2 the browser's
sign-in; I3 a sign-in provider; I5 the application's own sign-in screen.

**Track Z — authorization:** Z1 roles, groups and grants enforced at the route; Z2 record types at the
write unit, and jobs, moves and the feed; Z3 the consumer APIs per client; Z4 audit identity; Z5 the
interface follows permissions; Z6 one person's changes across workspaces.

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

##### P0 plan (2026-10-22)

**Planned 2026-10-22; accepted by the user on 2026-10-23** ("otherwise ok"): D243–D257, the
catalogue and the mock-ups, with D251 changed (access tokens last an hour) and D254 confirmed after
the user asked whether it needs action from anyone (it does not; recorded in D254). Checked against the code at `5622b67` by
reading it and by listing every operation of an app built with all four capability flags on.

**What the check found:**

- **157 management operations** (plus `/health` and `/health/live`), the eight consumer routes, and
  `/docs` with its bundled script. Every management router is registered with
  `MANAGEMENT_DEPENDENCIES` (`management/dependencies.py`); the consumer router with none. That
  list is the one place I1 adds authentication and Z1 the route check.
- **One route, two actions.** The record, value, relation and relationship-set writes (10 routes)
  are live writes without `changeSetId` and change-set writes with it, in the body or the query. Edit
  live and Work in change sets (D231) are therefore decided per request, not per route (D244).
- **The browser reads two things a header cannot reach.** The job toast streams
  `/jobs/{id}/events` with `EventSource` (`features/jobs/useJobStream.ts`), and "Download" is an
  `<a href download>` to `/jobs/{id}/output` (`features/jobs/JobNotifications.tsx`). Neither sends
  `Authorization`, and a token in the URL is excluded (C-D1). D247.
- **`GET /system` mixes two audiences.** It carries the engine version and schema languages (read by
  About and by "New draft" for an empty model) beside the database and every setting (Deployment).
  L1 adds the licence and the source offer there, which every user must reach (AGPL §13). D246.
- **`/health` is the readiness probe** (status only, `503` when the registry or database is down);
  a probe carries no token. I1's list of open routes omits it. D245.
- **Instance-wide resources hold different things.** Import profiles and model mappings are
  configuration bound to a model; source files carry an uploaded workbook and an optional workspace;
  job rows and outputs carry a workspace's data. D248.
- **Relationships cross applications** (USER_JOURNEYS: "related … within one application and across
  applications"; mapping coverage and the cross-type lookup read both ends). Reading narrowed to an
  application meets the same filtering D228 avoided for record types. D243.
- **`CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`** seals webhook keys and is required only with
  subscriptions on; token signing keys and sign-in provider secrets need sealing on every
  installation. D253.
- **Change sets have no owner** and are edited by anyone today; nothing records who made one. D255.

**The catalogue, completed** (every operation; the full per-route table goes to API.md, D256). The
draft's groups stand; two pseudo-groups are added for routes every caller needs.

| Group | Key | Operations | What they are |
| --- | --- | --- | --- |
| Public (no token) | — | 2 + 3 + OAuth | `/health`, `/health/live`; `/openapi.json`, `/docs` and its script (C1 signs the page in); the OAuth metadata, JWKS, authorize, token and revocation endpoints (D245) |
| Signed in | `signed-in` | 5 + `/me` | Capabilities; the workspace list and the default workspace, **filtered** to what the caller may browse (D249); which model each workspace runs, filtered alike; `GET /system`'s engine part (D246); `/me` and its sub-resources |
| Browse | `browse` | 38 | The workspace's model (12 reads, the default workspace when none is named); a workspace and its model; records, values, relations, history, parent candidates, the query, relation matrix, mapping coverage, candidates and targets; change sets and their changes; publications; **exports** (a job, read like the rest) |
| Edit live | `edit-live` | 10, shared | Record, value, relation and relationship-set writes **without** `changeSetId` (D244) |
| Work in change sets | `change-sets` | 8 + the 10 | Create, rename, discard, validate, restructure (preview and apply), move onto a release (`model-release`, `model-migrations`); the 10 writes **with** `changeSetId` |
| Publish | `publish` | 2 | Publish a change set; withdraw a publication |
| Approve publications | `approve` | Track A | Submit is `change-sets`; approve and send back are `approve` |
| Bulk and import | `bulk` | 20 | Batches and imports; import profiles and their checks; source files and their profiles |
| Copy and move | `copy-move` | 13 | Model-to-model mappings, their operations and inference; moves (read on the source, write on the target, checked in Z2) |
| Model authoring | `model-authoring` | 26 + 4 | Model validation; drafts, operations, outline, consumer API previews, undo and redo, profile, compile, dry run, inference; **reads** of releases and their diff (shared with Model release) |
| Model release | `model-release` | 3 + 4 | Install a draft; activate a release into a workspace; migrate a workspace; reads of releases and their diff |
| Workspace administration | `workspace-admin` | 4 | Create, rename and retire, delete a workspace; set the default |
| Integration administration | `integration-admin` | 10 | Consumer subscriptions, deliveries, resends, suspend and resume (K1 adds rotation) |
| Feed | `feed` | 1 | The workspace's change feed |
| Operations | `operations` | 5 + 1 | Processes, readiness detail, summary, backup rehearsals, `/metrics`; `GET /system/configuration` (D246) |
| Security administration | `security-admin` | new | Users, groups, roles, grants, clients, token signing keys, sign-in providers (I1–I3, SP1, SP2) |
| Jobs | — | 8 | Not a group: a job is read, followed, cancelled or confirmed by its requester, or by a holder of the group that started its kind in its workspace (the import's `bulk`, the move's `copy-move`, the migration's `model-release`, the export's `browse`) |
| Consumer API grant | — | 8 consumer routes | Read of a named consumer API in a workspace (Z3); the index lists only the APIs granted; the per-definition OpenAPI needs the grant too (D245) |

**The predefined roles** (D230; names settled, D257):

| Role | Action groups | Granted at |
| --- | --- | --- |
| Reader | Browse | Workspace |
| Contributor | Browse, Work in change sets | Workspace |
| Data steward | Browse, Edit live, Work in change sets, Publish, Bulk and import | Workspace |
| Data owner | The steward's, plus Approve publications (own), Feed, Copy and move | Workspace |
| Model administrator | Model authoring, Model release | Instance or workspace (release only) |
| Workspace administrator | Workspace administration | Instance |
| Integration administrator | Integration administration, Feed | Workspace |
| Operator | Operations | Instance |
| Security administrator | Security administration | Instance |
| Consumer (clients) | Consumer API grants only | Workspace |

**API design** (written in API.md and CONSUMER_API on delivery; routes free of the project's name):

- **OAuth** (outside `/api/v1`): `GET /.well-known/oauth-authorization-server` (RFC 8414),
  `GET /oauth/jwks`, `GET|POST /oauth/authorize` (the sign-in page; code flow with PKCE `S256`
  only), `POST /oauth/token` (`authorization_code`, `refresh_token`, `client_credentials`),
  `POST /oauth/revoke` (RFC 7009). Errors in the RFC's own shape (D250).
- **The caller:** `GET /api/v1/me`, `GET /me/permissions?workspaceKey=`, `GET|DELETE /me/sessions`
  (one or all: "sign out everywhere"), `POST /me/password`.
- **Security administration:** `/users` (create, read, change, deactivate; a password-reset link
  shown once; sign out everywhere), `/groups` and their members, `/action-groups` (read: the
  catalogue), `/roles` (predefined read-only, custom created, copied, changed, deleted when unused),
  `/grants` (principal, role or consumer API, scope: instance, or a workspace optionally narrowed to
  applications and record types for writes), `/workspaces/{key}/access` (who can do what here),
  `/clients` and `/clients/{id}/secrets` (a second secret during a rotation),
  `/token-signing-keys` (ages, "rotate now"), `/sign-in-providers` (I3).
- **Approvals and the inbox (Track A):** `POST|DELETE /change-sets/{id}/submission`,
  `POST /change-sets/{id}/decisions` (approve or send back, one row each),
  `GET /workspaces/{key}/publication-requests`, `PUT /workspaces/{key}/approval-policy`,
  `GET /me/notifications` (cursor-paged, read and unread) and its stream.
- **K1:** `POST /consumer-subscriptions/{id}/rotate-secret`; `RDM-Signature` a comma-separated list
  (D238).
- **Refusals:** `401 AUTHENTICATION_REQUIRED`, `401 TOKEN_INVALID` (with the reason: expired,
  revoked, audience, unknown key), `403 FORBIDDEN` naming the action, its groups and the workspace;
  `WWW-Authenticate: Bearer` on every 401.

**Journeys** (wording final in USER_JOURNEYS, a new "Security" group; routes and codes in
API_JOURNEYS):

- **J39 Sign in and work.** Variants: sign in with a password and return to the page asked for; the
  session renewed silently; signed out, or signed out everywhere from another device; a deactivated
  person's next request refused; a wrong password, then throttling (D252); a sign-in provider (I3).
- **J40 Manage who can do what.** Variants: create a person and grant a role in a workspace; a group
  holding the grant; a custom role copied from a predefined one; a grant narrowed to record types; a
  grant removed takes effect on the next request; "who can do what here"; the last Security
  administrator cannot be removed.
- **J41 A system calls with a client.** Variants: client credentials to a token; the management API
  within its roles; a consumer API with and without its grant; the secret rotated with two valid
  during the overlap; a deactivated client refused.
- **J42 Propose and approve a change** (Track A). Variants: a Contributor submits; an approver
  approves and publishes, or sends back with a comment; an edit withdraws the submission; an owner
  publishes their own in one step; four-eyes refuses self-approval; the inbox and webhook events.
- **J43 Rotate a key.** Variants: a token signing key rotated with tokens of the old one valid until
  they expire; "rotate now" after a leak refuses them at once; a webhook key rotated with both
  signatures during the overlap, then only the new one (K1).

**Decisions raised by the check.** D224–D242 stand; these are new.

| # | Question | Recommendation |
| --- | --- | --- |
| D243 | Reading narrowed to applications (**revisits D228**) | D228 says reads are per workspace "(and application)". **Recommended: reads per workspace only; applications and record types narrow writes alone.** Why: a record's relations, mapping coverage, the cross-type lookup, the feed and exports cross applications, so a reader limited to one application would need every one of them filtered, the cost D228 refused for record types; no user need for it is recorded. Cost: data that must be hidden from some readers goes in its own workspace, as D228 already says |
| D244 | The record writes with and without a change set | **Recommended:** the 10 shared routes declare both actions; the request's `changeSetId` picks which is checked (Edit live without, Work in change sets with). Why: splitting them into two routes each would break the record-write contract for no gain; the check runs on the same request data the route already reads. Cost: the contract test checks these routes for both actions |
| D245 | Which routes need no token | **Recommended:** `/health` (status only) and `/health/live`, because probes carry no token; `/openapi.json`, `/docs` and its script, because the management contract is published anyway and C1 signs the page in; the OAuth endpoints. Everything else needs a token, including `/metrics` (a scraper uses a client with the Operator role, which Prometheus supports) and the consumer index and per-definition OpenAPI (they reveal a workspace's model). Cost: a monitoring set-up needs a client |
| D246 | `GET /system` | **Recommended:** split. `GET /system` keeps the engine, the schema languages and (L1) the licence and source, readable by anyone signed in; `GET /system/configuration` takes the database and settings, for Operations. Why: About and the source offer must reach everyone; settings and database details are an operator's. Cost: a contract change; Deployment reads the new route |
| D247 | The job stream and downloads in the browser | **Recommended:** both read with `fetch` and the `Authorization` header: the stream from the response body (the same `text/event-stream` format), the download as a file saved from the response. Why: `EventSource` and a link cannot send the header, and a token in a URL is excluded (C-D1). Cost: a small stream reader in place of `EventSource` (I2); a client of the API is unaffected |
| D248 | Who reads instance-wide resources | **Recommended:** configuration without data (import profiles, model mappings) is read and changed by anyone holding its group at any scope; resources carrying data (source files, job rows and outputs) by their owner and by holders of the group in their workspace, or at the instance for a source file without one. Why: a steward granted one workspace must still build a profile; an uploaded workbook or a job's rows hold one workspace's data. Cost: source files gain an owner (Z4 records it) |
| D249 | Lists and single reads the caller may not see | **Recommended:** lists are filtered to what the caller may browse (workspaces, jobs, the cross-type lookup, the feed); a named resource the caller may not use answers `403 FORBIDDEN` naming the action and the workspace, not `404`. Why: one organisation per instance, so a workspace's key is not a secret, and an integrator needs to know which grant is missing. Cost: none |
| D250 | Error shapes of the token endpoint | **Recommended:** the OAuth endpoints answer in the RFC's shape (`{"error": "invalid_grant", "error_description": …}`), every other route in the engine's envelope. Why: every OAuth client library parses the RFC's shape. Cost: two shapes, each documented where it applies |
| D251 | Token lifetimes | **Accepted with a change by the user (2026-10-23): access tokens last an hour.** As settings with these defaults: access tokens 60 minutes for people and clients; refresh tokens (people only) rotated on every use, a reused one revoking its whole session; a session ends after 12 idle hours or 14 days. An hour loses nothing: the per-request lookup (D226) also checks that the principal is active and that the token's session (`sid`) is not signed out, so a removed role, a deactivation or "sign out everywhere" takes effect on the next request, not at expiry. Cost: a stolen access token works for up to an hour while its holder is still active; a person working past 14 days signs in again. Amends D234's "about 10 minutes" |
| D252 | Local passwords and failed sign-ins | **Recommended:** at least 15 characters, at most 128, no composition rules, refused when equal to the username or in a short built-in list of the most common; failed sign-ins slowed per account and per address with a growing delay, never a hard lock; each failure in the audit. Why: NIST SP 800-63B (rev. 4) for a password used alone (D225); a hard lock lets anyone lock out an administrator. Cost: long passwords for local accounts, which OPERATIONS explains |
| D253 | Sealing secrets | **Recommended:** one setting, `SECRETS_ENCRYPTION_KEY`, required on every installation, seals token signing keys, webhook keys and sign-in provider secrets, **replacing** `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (startup refuses the old name and names the new one). Passwords and client secrets are hashed with Argon2id, never sealed. Why: three keys for one purpose is three things to lose; pre-1.0 a renamed setting is allowed. Cost: an operator renames one setting |
| D254 | Token signing keys | **Recommended:** ES256, a new key every 30 days on its own, the previous one verifying until its last token expires; "rotate now" (J43) retires the current key at once. Why: small tokens, supported by every JWT library, and a leaked key is closed without a restart. Cost: one scheduled step in the existing worker. **Nobody acts on a rotation** (the user asked, 2026-10-23): refresh tokens and client secrets are database records, never signed with the key, so a browser session renews onto the new key unnoticed; after "rotate now" a client's current token is refused with `401 TOKEN_INVALID` and it obtains a new one with its unchanged credentials, as OAuth client libraries do on a 401; tokens are for the engine alone, and anyone verifying one picks the key by its `kid` from the published set. Webhook keys are separate (K1, D238) |
| D255 | Whose change set | **Recommended:** change sets stay shared: anyone holding Work in change sets in the workspace edits any open one; the creator is recorded and shown (Z4), not enforced. A1's submission freezes it. Why: change sets are coordinated work, as today. Cost: none |
| D256 | Where the catalogue lives | **Recommended:** P0 writes the full per-route table in API.md; Z1 moves it into each route's declaration, published per operation in the OpenAPI document (its `security` and the action and groups), and API.md keeps the groups and points there. Why: one home, checked by the contract test, readable on `/docs`. Cost: none beyond Z1 |
| D257 | The predefined roles' names | **Recommended:** as in the table above; "Editor / Data steward" becomes **Data steward** (key `steward`). Why: one name per role; the PRODUCT persona's. Cost: none |

**Mock-ups** ([security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), twelve
boards on the Atlas tokens, each with a dark tweak, 1440px and 390px, in an invented herbarium
domain): the sign-in page with its refusals; the account menu and account page; Settings ›
Security › People, Groups and Roles (the role matrix); a workspace's access ("who can do what here")
and the grant dialog; Clients with the secret shown once and a rotation; a Reader's and a
Contributor's record view (Z5); the approval round trip and the inbox (A3).

**What P0 produces on acceptance:** ADR-043 (identity and tokens: D224, D225, D234, D235, D250–D254)
and ADR-044 (authorization: D226–D231, D236, D243–D249, D255, D256) and ADR-045 (approvals: D232,
D233, D242); ADR-031's prose corrected ("0.11" → 0.12, the table's second row); ARCHITECTURE's
"model-configurable permissions" corrected and the request's path through the two checks; API.md
(the catalogue, the routes above, the refusals) and CONSUMER_API (`401`, `403`, the grant, the
signature list); J39–J43 and API_JOURNEYS; SETTINGS_AND_UI_PLAN's U8 detailed from the approved
mock-ups; ROADMAP's 0.12 scope gains the approvals (D232); PRODUCT's persona note; package scopes
amended (I1: D245, D251–D254; I2: D247; Z1: D243, D244, D249, D256; Z2: D248); the P0 record.

**Composable domains (ADR-032):** P0 changes documents only. The identity and audit doors are
touched by Z4's design: the actor beside `cause`, never instead of it (unchanged from the plan).

**Checks:** `pytest tests/test_api_journeys.py`; links to the anchors added; no product code.

##### P0 record (2026-10-23)

**Delivered 2026-10-23.** The user accepted the plan, D243–D257, the catalogue and the mock-ups
("otherwise ok"), changing D251 (access tokens last an hour) and asking whether D254 needs action
from anyone (it does not: recorded in D254 and ADR-043).

- **Decisions:** D243–D257 recorded in the table above; D228 narrowed by D243; D234's "about 10
  minutes" replaced by D251's hour. Package scopes amended: I1 (D245, D246, D250–D254), I2 (D247),
  Z1 (D243, D244, D249, D256), Z2 (D248).
- **ADRs:** [ADR-043](DECISIONS.md#adr-043--identity-and-tokens-issued-by-the-engine) identity and
  tokens, [ADR-044](DECISIONS.md#adr-044--authorization-action-groups-roles-and-grants)
  authorization, [ADR-045](DECISIONS.md#adr-045--change-set-publication-approvals) approvals;
  ADR-031's "0.11" corrected to 0.12 and its table's authorization row restated.
- **ARCHITECTURE** § Security: "model-configurable permissions" replaced by roles and grants as
  runtime data, and the request's path through authentication, the permission lookup, the route
  check and the write-unit check.
- **API design:** [API.md § Security](API.md#security-product-012-designed): the OAuth endpoints and
  tokens, the caller's routes, the action groups and their rules, the predefined roles, `403`'s
  envelope, Security administration, approvals and the inbox, changes to existing routes, and the
  catalogue of all 159 operations, generated from an app with every flag on. CONSUMER_API: tokens,
  grants per consumer API and workspace, `401` and `403`, rotation with a signature list.
- **Journeys:** J39 (7 variants), J40 (10), J41 (6), J42 (6), J43 (5) in a new "Security" group of
  USER_JOURNEYS; their planned routes, codes and settings in API_JOURNEYS.
- **U8** detailed in SETTINGS_AND_UI_PLAN from the mock-ups, with the new pages in the settings
  table. ROADMAP's 0.12 scope gains the approvals (D232) and 1.0's protected publishing points to
  ADR-045; PRODUCT's persona note names the roles.
- **Mock-ups:** [security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo),
  approved; private until shared.

**Checks:** `pytest tests/test_api_journeys.py` (5 passed). **Not done:** the mock-ups were not opened
in a browser at either width or in dark before approval; the anchors of the new links were checked
by reading the headings, not by a link checker. No product code changed.

### Track I — Identity

#### I1: The issuer, people and clients; every route authenticated

**Needs:** P0.

**Scope:** the engine as an OAuth 2.0 authorization server: token signing keys in the database
(sealed like webhook keys, rotated with overlap, published at the JWKS endpoint for every node),
the token, revocation and discovery endpoints; **users** (local accounts with a password hashed
with Argon2id, deactivation, never deletion, D237) and **OAuth clients** (client credentials grant,
secret shown once, two secrets valid during a rotation); a refresh-token store with revocation
("sign out everywhere"). Every route requires a valid access token except those D245 names
(`/health`, `/health/live`, `/openapi.json`, `/docs`, the OAuth endpoints); readiness detail and
`/metrics` become Operations-only in Z1. _Amended by P0:_ ES256 keys rotated every 30 days and
"rotate now" (D254); lifetimes as settings (D251: access tokens an hour; the per-request check of the
principal and session); passwords and slowing (D252); `SECRETS_ENCRYPTION_KEY` replacing
`CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (D253); `GET /system` split (D246); OAuth errors in the RFC's
shape (D250). The first administrator is created with `python -m app.cli.create_admin`
(D235). The journey harness and the browser harness obtain real tokens; with one temporary role,
"all actions", until Z1. `/me` returns the caller.

##### I1 plan (2026-10-23)

**Planned 2026-10-23; accepted by the user the same day** ("its oky"): D258–D265 and the test
cases as written. Checked
against the code at `5622b67` with P0's documents.

**What the check found:**

- **No JWT library**; `cryptography` 46 (already a dependency, OpenSSL 3.5) provides ES256 and
  Argon2id, so only token encoding needs a choice (D258).
- **Every management router is registered with `MANAGEMENT_DEPENDENCIES`**, the consumer router and
  `/metrics`' router with none or the same list: three places to add authentication.
- **The tests build 293 `TestClient`s in 51 modules**, plus the journey world (`scenario.application`),
  the several-process journeys (`journeys/processes.py`, `httpx`) and the browser harness
  (`e2e/helpers/harness.mjs`, one `newContext`, an `api()` helper, and direct `fetch` in 12 runners).
  Every database a test uses is a clone of the `schema` seed or a seed built on it (journey
  scenarios, the browser seeds), so credentials placed in that seed reach them all (D263).
- **No user can obtain a token in I1.** The token endpoint's grants for a person are
  `authorization_code` and `refresh_token`, both I2's sign-in page; only clients sign in with I1.
  So the first administrator from `create_admin` cannot act until I2, and the first client needs
  another way in (D262). Sessions, refresh tokens, `/oauth/revoke`, the password-reset link and
  failed-sign-in slowing have no caller before I2 either (D261).
- **`RDM_CURSOR_SIGNING_KEY` and `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`** are the existing secrets;
  the second is read in `config.py`, `SubscriptionSettings`, `generate_key` and nine test modules.
- **`GET /system`** carries `activeModelRelease` too; it stays there with the engine (D246 moves only
  `database` and `settings`). Settings › Deployment is the one browser reader of what moves.

**What is built:**

1. **Settings:** `SECRETS_ENCRYPTION_KEY` required on every installation (startup refuses a missing
   one, and refuses `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` naming the new setting, D253);
   `ACCESS_TOKEN_MINUTES` (60, D251); `PUBLIC_URL` (D259); `generate_key` prints a key for the new
   setting. All reported in Settings › Deployment like the others, secrets as "set".
2. **Migration** `20261027_01`: `users` (public ID, username unique ignoring case, name, e-mail,
   Argon2id password hash or none, active, version, created and last sign-in), `oauth_clients`
   (public ID, name, active, version, last used), `oauth_client_secrets` (hash, created, expires
   after an overlap, last used), `token_signing_keys` (`kid`, the private key sealed, the public
   JWK, created, rotated, retired).
3. **Engine** `engine/identity/`: passwords (D252's rules, Argon2id), signing keys (created when
   none is current, rotated lazily at issue after 30 days, D264, or on request; retired at once by
   "rotate now"), tokens (issue and verify, D258), clients and their secrets (two valid during an
   overlap), users (create, change, deactivate; never deleted). The request's principal is one
   query by primary key with the token's key state; the permission cache of D226 comes with Z1,
   which first has permissions to cache.
4. **Routes:** `GET /.well-known/oauth-authorization-server`, `GET /oauth/jwks`, `POST /oauth/token`
   (`client_credentials` only in I1; `client_secret_basic` and `client_secret_post`; `scope`
   picks the audience, D260; RFC errors, D250); `GET /api/v1/me`; `GET|POST /users`,
   `GET|PATCH /users/{id}`; `GET|POST /clients`, `GET|PATCH /clients/{id}`,
   `POST /clients/{id}/secrets`, `DELETE /clients/{id}/secrets/{secretId}`;
   `GET /token-signing-keys`, `POST /token-signing-keys/rotation`; `GET /system/configuration`.
   Lists cursor-paged, writes with `expectedVersion`, as API.md designs them.
5. **Every other route needs a token:** the management routers and `/metrics` a `management` one,
   the consumer routes a `consumer` one (D260); `401 AUTHENTICATION_REQUIRED` and
   `401 TOKEN_INVALID` (`expired`, `revoked`, `audience`, `unknownKey`) with `WWW-Authenticate:
   Bearer`. Any active principal may do everything until Z1 (the temporary "all actions").
   The OpenAPI document declares the bearer scheme and the token URL; the lock is re-baselined.
6. **CLI:** `python -m app.cli.create_admin` (a user with a password read from the terminal, D252
   applied) and `python -m app.cli.create_client` (D262).
7. **Harnesses** (D263): the `schema` seed holds a harness client and a signing key; the backend
   tests take one token per process from `POST /oauth/token`; the 51 modules import a `TestClient`
   carrying it; the several-process journeys and the browser harness obtain theirs the same way.
8. **Frontend:** Settings › Deployment reads `GET /system/configuration`. Nothing else changes until
   I2 (D265).
9. **Documents:** API.md's delivered parts moved out of "designed"; OPERATIONS (the settings, the
   first administrator, the first client, the public URL); CONSUMER_API's "until those packages"
   sentence (D260); journeys' status; CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D258 | Encoding and verifying tokens | **Recommended:** PyJWT (`pyjwt>=2.10`) for the JWT format, verifying with `algorithms=["ES256"]` only, over keys `cryptography` generates. Why: token parsing is where hand-written code goes wrong (algorithm confusion, claim checks); PyJWT is the library most Python OAuth servers use and adds no other dependency. Cost: one new runtime dependency |
| D259 | The issuer's address | **Recommended:** a setting `PUBLIC_URL`, the engine's address as callers reach it (default `http://localhost:8000`, the address the frontend already assumes), used as `iss` and for the absolute URLs in the server metadata. Why: RFC 8414 needs absolute URLs and a fixed issuer; reading it from each request would give every node behind a proxy another issuer. Cost: a production installation sets one more setting, which OPERATIONS lists |
| D260 | Asking for a consumer token, and consumer routes in I1 | **Recommended:** the token request's `scope` is `management` (the default) or `consumer` and becomes `aud`; I1 makes the consumer routes need a `consumer` token, which any active principal may use until Z3 adds grants per consumer API. Why: every OAuth client library can send `scope` in client credentials; and leaving the consumer API open after I1 would break "every route authenticated" for no gain. Cost: CONSUMER_API's sentence that the consumer API stays open until Z3 is corrected; an integrator asks for `scope=consumer` |
| D261 | What moves from I1 to I2 | **Recommended:** sessions and refresh tokens, `/oauth/revoke`, the `sid` check, `DELETE /users/{id}/sessions`, the password-reset link and the slowing of failed sign-ins go to I2, where the sign-in page first creates sessions and checks passwords. Why: in I1 nothing can create a session or try a password from outside, so this code would have no journey and no honest test (AGENTS: no test builds a state no client could produce). Client secrets are 32 random bytes, so slowing guesses at them protects nothing. Cost: none; I2 is next |
| D262 | The first client | **Recommended:** `python -m app.cli.create_client --name …`, run on the server like `create_admin`, printing the client's ID and secret once. Why: until I2 nobody can sign in, so without it no one could reach the API at all; afterwards it is how an installation is automated without a browser (infrastructure as code). Cost: a second command, the same trust as the first |
| D263 | How the tests reach the engine | **Recommended:** the `schema` seed holds a signing key and a harness client with fixed test credentials, created by the same engine function as the CLI; each test process takes one real token from `POST /oauth/token` and reuses it on every clone; the 51 modules change one import to a `TestClient` that carries it; a test of a refusal builds a client without it. Why: one token request per test would add Argon2id's cost to thousands of tests, past the 11-minute ceiling; one per process costs nothing. Cost: the 51 import lines, the seeds rebuilt once |
| D264 | When the signing key rotates on its own | **Recommended:** when a token is issued and the current key is 30 days old, under a lock, instead of a step in the job worker (D254 said worker). Why: the same result without a timer; works on a process with jobs off, and a test can see it. Cost: none |
| D265 | The interface between I1 and I2 | **Recommended:** the browser shows the engine's refusals until I2 (next in the queue) signs it in; the browser runners pass by sending the harness token on every request (Playwright's headers). Why: anything in the frontend or the dev server that hands the browser a token without signing in is the switch D235 refused, and I2 replaces it at once. Cost: no one uses the interface on a dev server between I1 and I2 |

**Journey test cases** (`tests/journeys/test_j39_j41_j43_identity.py`, on two configurations;
written first and seen failing):

1. **J39, refused without a token:** given the engine, when a management read, a consumer route and
   `/metrics` are called with no token, then each answers `401 AUTHENTICATION_REQUIRED` with
   `WWW-Authenticate: Bearer`; `/health`, `/health/live`, `/openapi.json`, `/docs`, the server
   metadata and the JWKS answer without one.
2. **J39, a token not ours:** given a token signed by another key, or altered, when it calls a
   management read, then `401 TOKEN_INVALID` (`unknownKey`, and for the altered one the signature
   reason) with `error="invalid_token"`.
3. **J41, a client calls:** given an administrator creates a client (the secret shown once, never on
   a read), when the client posts its credentials to `/oauth/token` (basic, and in the body), then it
   gets a Bearer token for an hour; `GET /me` names it; it reads and writes records in the
   workspace. A wrong secret answers `invalid_client`, an unknown grant `unsupported_grant_type`, in
   the RFC's shape.
4. **J41.3, the secret rotated:** given a client, when a second secret is created with an overlap,
   then both obtain tokens; when the old one is deleted, or the overlap is 0, only the new one does.
5. **J41.4, a deactivated client:** given a client with a token, when it is deactivated, then that
   token's next request answers `401 TOKEN_INVALID` (`revoked`) and the token endpoint
   `invalid_client`.
6. **J41.5, the other audience:** given a `consumer` token, when it calls the management API, then
   `401 TOKEN_INVALID` (`audience`); a `management` token on a consumer route likewise.
7. **J43.1 and J43.2, the token key rotated:** given a token, when the key is rotated with
   `immediate: false`, then the old token still works, new tokens carry the new `kid` and the JWKS
   lists both; when rotated with `immediate: true`, the old key's tokens answer `401 TOKEN_INVALID`
   (`unknownKey`), the JWKS drops it, and the client obtains a new token with its unchanged secret.
8. **J40 (I1 part), people:** given an administrator, when a person is created, read, changed and
   deactivated with `expectedVersion`, then each read shows it; a stale version answers
   `409 VERSION_CONFLICT`; a person is never deleted. `create_admin` refuses a short or common
   password and creates the user with one that passes.
9. **J31, `/system` split:** `GET /system` carries the engine, the schema languages and the active
   release but no database or settings; `GET /system/configuration` carries them, secrets as "set".

Startup (J12, the existing startup journeys extended): a missing `SECRETS_ENCRYPTION_KEY`, and the
old setting's name, each refuse to start with a message naming `SECRETS_ENCRYPTION_KEY`.
Unit tests: the password rules' edges, token verification (expiry, algorithm, audience, issuer,
an unknown `kid`), sealing of a signing key, lazy rotation's age check.

**Checks:** the new journey module; the journey groups the harness change touches selected by
`python -m tests.affected`; `test_openapi_contract` with the lock diffed; `test_startup`'s settings
cases; the unit tests; Ruff on the changed files; frontend Vitest for Deployment, format, lint,
build; one browser runner (`u3-settings`) to show the harness token and the Deployment page, at
1440px and 390px. The harness change touches every test's setup, so a wider run than three minutes
may be needed: it is announced with its expected time before it runs.

**Composable domains (ADR-032):** the identity door is touched: principals are users and clients,
with public IDs and deactivation, never deletion; no value source or `cause` changes (Z4).

##### I1 record (2026-10-23)

**Built 2026-10-23; the backend run the harness change needs is waiting for the user's go-ahead**
(below). What was built is the plan's list, items 1–9:

- **Engine** `engine/identity/` (`passwords`, `keys`, `tokens`, `clients`, `users`,
  `authentication`, `settings`); migration `20261027_01`; PyJWT added (D258).
- **Routes:** `oauth.py` (metadata, JWKS, token) outside `/api/v1` with no token; `identity.py`
  (`/me`, `/users`, `/clients` and secrets, `/token-signing-keys` and rotation) and
  `/system/configuration` behind the token. `authenticated` is the first of
  `MANAGEMENT_DEPENDENCIES`; the consumer router has its own `consumer` check. The OpenAPI document
  declares `engineOAuth` (client credentials, `/oauth/token`) on every operation but the open ones.
- **CLI** `create_admin`, `create_client`; `generate_key` prints the secrets key.
- **Harnesses:** `tests/harness_identity.py` (the `schema` seed's client and key, one token per
  process, `TestClient` carrying it), the 48 modules importing it, the several-process journeys,
  `browser_seeds.py` handing the credentials to the browser harness, which sends the token from the
  browser context and from the runners' `fetch`.
- **Frontend:** Settings › Deployment reads `/system/configuration`; About keeps the engine and the
  release.
- **Documents:** API.md (the system split, the delivered security routes, the refusal reasons),
  CONSUMER_API, OPERATIONS (§ Authentication, the settings, startup refusals, metrics with a token,
  upgrading from 0.11), ARCHITECTURE's authentication step, USER_JOURNEYS' statuses, API_JOURNEYS'
  inventory, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- `TOKEN_SIGNING_KEY_DAYS` (30) is a setting: the test seeds are reused for longer than 30 days, and
  a key replaced in one clone would make the shared harness token unknown in the others; the harness
  sets it to 100 years. D254's 30 days stay the default.
- Two more `TOKEN_INVALID` reasons: `malformed` (not a JWT this engine issues, including an HS256
  token: algorithm confusion is refused before a key is chosen) and `signature`.
- The token lifetimes are in the `runtime` settings group, not `limits` ("Batch and job limits").
- About showed the migration revision, which moved to `/system/configuration`; it is shown on
  Deployment instead, so About stays readable by everyone after Z1.
- Case 9 extends `test_j31_system.py`; the startup cases are J12.7's invalid-setting cases plus
  `test_startup`'s rewritten key test.
- **The journey cases were written after the engine code**, not seen failing first: the harness
  needs the token endpoint to reach the engine at all. They were then run and passed.
- One more check: every operation of the document with all four flags on refuses an anonymous call
  (`test_openapi_contract`).

**Checks** (single process unless noted):

- `tests/journeys/test_j39_j41_j43_identity.py`: 18 passed (9 cases × 2 configurations).
- `tests/journeys/test_j31_system.py` with `tests/unit/test_config.py`: passed (after OPERATIONS
  listed the new settings).
- `tests/unit/engine/identity/`: 23 passed (password rules, token verification, lazy rotation).
- `tests/test_openapi_contract.py` (lock re-baselined after a diff against `5622b67`: 13 paths, 17
  schemas, `SystemResponse` narrowed, `security` added, nothing else), `tests/test_api_journeys.py`,
  `tests/unit/harness`: passed.
- Ruff on the changed files; frontend Vitest for Settings, IntegrationPages and App's settings cases
  (23), `format:check`, `lint` (0 errors), `build`.

**The stopped run, and what it hid.** A first run of seven exposed modules in one parallel
invocation was left in the background for 50 minutes, far past the 3-minute package ceiling; it
should have been stopped at the ceiling and split. Blaming the machine's load (51, macOS services,
disk 97% full) was premature. Run one module at a time under a 3-minute cap, they found real defects,
all fixed:

- **The harness had no token for databases built from empty** (startup tests): it now falls back to a
  client made in that database, as `create_client` makes one.
- **In maintenance mode** (startup could not prepare the database) a request with a token, the token
  endpoint and the JWKS answered `500 INTERNAL_ERROR` reading identity tables that may not exist;
  they answer `503 MODEL_REGISTRY_UNAVAILABLE` again, checked before a session is opened
  (`require_started`), with a regression check in `test_startup`'s refusal helper.
- `test_startup`'s hard-coded head revision; J12's pool test reading `settings` from `/system`.
- **The user, 2026-10-23: no upgrade, downgrade or interrupted-migration scenarios are tested or
  measured before 1.0.** On the user's instruction the existing ones were removed: 34 tests of
  `test_startup` (upgrades from older revisions with an interrupted run each, downgrades, a failed
  migration's recovery) and J12.5's two tests, with the harness retry built for one of them. J12.5 is
  marked not tested before 1.0. `test_startup` keeps the clean start, the refusals, the unknown
  revision, the job file directory and the secrets key (8 tests).

Then: `test_startup` 45 passed (1 min 57 s), J12 run the service 62 passed (1 min 47 s), J30
subscriptions 14, J31 12, `test_pg3_concurrency` 21, each alone.

**The whole suite** (`-n 6`, then `-m serial`), on the user's go-ahead, after the removal above:

- A first run stopped at once: a new unit test built signed tokens at collection, so each worker
  named its cases differently and xdist ran nothing. Fixed ids.
- The second: 153 failed, 6,020 passed, 20 errors, 12 min 36 s. Causes: the harness sent its
  `management` token to the consumer routes (most failures: it now picks the audience by path);
  the job-stream journeys call `httpx.stream` directly without the token; maintenance mode had been
  tied to the registry's health, which `wp6`/`wp81a` mark unhealthy for another purpose (now an
  application flag set only when startup fails on the database); `session.delete` in
  `identity/clients` broke the tier rule; the foreign-key review lacked the client-secret rule; each
  request now costs one more statement (the token lookup), so the batch statement budgets rose by
  one; the harness's first token fetch was counted inside measured requests (the volume app now takes
  both tokens before anything is measured).
- The third: **6,190 passed, 3 failed, 12 min 26 s**: the consumer xref and event budgets (the same
  first-fetch count, fixed in the volume app; their modules then passed, 20) and the 2,000-record
  move dry run at 3.7 s against 2.5 s in the parallel run, which passes alone (load from parallel
  tests, not this change). `-m serial`: 5 passed.
- **Browser:** `u3-settings` at 1440px and 390px, on the harness token: 10 checks, keyboard order, axe
  0 violations; the runner reads the revision on Deployment now. Screenshots of About and Deployment
  inspected at 1440px; at 390px only the no-horizontal-scroll check, the page being too tall to read
  as one image.

**D266, decided by the user (2026-10-23):** the browser reads the consumer API index and its OpenAPI
documents (Settings › Consumer APIs, the API reference page), and with D260 its one `management` token
was refused there. **Accepted as recommended:** those two describing routes take a `consumer` or a
`management` token; the consumer data routes take only `consumer`. Why: they describe contracts the
management API's model reads show anyway, and the browser keeps one token. Cost: J41.5 now refuses a
management token only on the data routes. Built in the consumer router (`DESCRIBING`); J41.5's case
changed with it (2 passed); the identity module, the token unit tests and J20 then passed (55, one
J20 case failing once in that mixed run and passing alone and in its module's rerun; in TODO).

**What the user cannot do yet:** sign in from the browser (the interface shows the refusals until
I2, D265); reset a password or end sessions (I2); narrow anyone's rights (Z1: every active client and
person may do everything); limit a client to some consumer APIs (Z3). A local development server needs
`SECRETS_ENCRYPTION_KEY` set to start, and a client from `create_client` to call the API.

#### I2: Signing in from the browser

**Needs:** I1.

**Scope:** the engine's sign-in page (username and password; a sign-in provider's button from I3),
the authorization code flow with PKCE for the frontend (D234), the access token kept in memory and
renewed through a refresh token in an `HttpOnly`, `SameSite=Strict` cookie; sign-out; the account
menu showing the person, "Account" and "Sign out" in place of the placeholder; the account page
(change password, sessions with "sign out everywhere", the person's roles read-only). Expired or
revoked sessions return to the sign-in page and back to where the person was. _Amended by P0:_ the
job stream and downloads read with `fetch` and the header (D247).

##### I2 plan (2026-10-23)

**Planned 2026-10-23; accepted by the user the same day** ("okay"): D267–D275 and the test cases
as written. Checked
against the code at `3633627` with P0's documents and the approved mock-ups (sign-in at 1440px and
390px, the account menu and the Account page).

**What the check found:**

- **The token endpoint** knows `client_credentials` only; `authenticate` reads the key and the
  principal in one statement and has no session to check. The `Principal` carries no session.
- **No session, code, reset or failure table** exists; `users.last_sign_in_at` is never written.
- **The browser** calls the engine on another origin (`VITE_API_URL`, `localhost:5173` against
  `localhost:8000`, `127.0.0.1` on two ports in the browser harness): the same site, so a
  `SameSite=Strict` cookie reaches the engine on a credentialed `fetch`; CORS already allows
  credentials for `CORS_ORIGINS`.
- **Three places read without the header:** the job stream (`EventSource` in `useJobStream`), the
  export download (`<a href download>` in the job page and the job toast) and the consumer API's
  `openapi.json` link on Settings › API reference, which has answered `401` since I1 (D266 accepts
  a management token there, but a link carries none).
- **The account menu** (`app/SettingsMenu.tsx`) shows "Local session" and a disabled "Sign in".
- **The browser harness** puts the harness client's token on every page (D265); the app has no
  notion of signing in, so with I2 every page would be sent to the sign-in page.
- **The mock-ups show four things later packages own:** the person's main role in the menu and
  "What you can do" on Account (Z1's `/me/permissions`), the provider's button (I3), and the source
  link with the licence (L1).

**What is built:**

1. **Migration** `20261028_01`: `user_sessions` (public ID, user, created, last used, idle and
   absolute ends, user agent, how signed in, ended and why), `session_refresh_tokens` (hash, session,
   issued, used), `authorization_codes` (hash, user, redirect URI, PKCE challenge, expires in 60
   seconds, used), `password_reset_links` (hash, user, expires, used), `sign_in_failures` (per
   account and per address: count, last failure).
2. **Engine** `engine/identity/`: `sessions` (start, renew with rotation, end one or all, the
   reuse that ends a session, idle and absolute ends), `sign_in` (the password check with D271's
   slowing, the authorization code with PKCE `S256`), `resets` (D272). Refresh, code and reset
   tokens are 32 random bytes stored as SHA-256 (high-entropy tokens checked on every renewal;
   Argon2id stays for passwords and client secrets). Access tokens for people carry `sid`;
   `authenticate` reads the session with the key and the principal in the same statement and
   refuses an ended one as `revoked`.
3. **OAuth routes:** `GET /oauth/authorize` (the sign-in page) and `POST /oauth/authorize` (its
   form), for the browser's client only (D267); `POST /oauth/token` gains `authorization_code`
   (with `code_verifier`) and `refresh_token` (read from the cookie, or the form for a client
   library), both setting a new refresh cookie; `POST /oauth/revoke` (RFC 7009) ends the session
   and clears the cookie; `GET|POST /oauth/password` (the reset link's page). The metadata names
   the new endpoints and grants.
4. **Caller and administration routes:** `GET /me` gains `signedInWith` and `sessionId`;
   `GET /me/sessions` (cursor-paged, `current` on this browser's), `DELETE /me/sessions/{id}`,
   `DELETE /me/sessions`; `POST /me/password` (ends every other session); `POST
   /users/{id}/password-reset` and `DELETE /users/{id}/sessions`. Deactivating a person ends their
   sessions. OpenAPI lock re-baselined.
5. **Settings:** `SESSION_IDLE_HOURS` (12), `SESSION_DAYS` (14), `PASSWORD_RESET_HOURS` (24), in
   the `runtime` group, on Deployment like the others.
6. **The sign-in page** (D275): the default workspace's product name, username and password,
   "Forgotten your password? Ask a security administrator for a reset link.", the messages of the
   mock-up (wrong username or password, slowed with the wait, the session ended: D270), one column
   at 390px, light and dark from the device.
7. **Frontend:** a session layer in `api/` (sign in with PKCE, the token in memory, renewal under a
   Web Lock shared by the tabs (D269), one retry after a `401`, back to the sign-in page with the
   address kept); the app starts behind it with a short "Signing in…" state; `/signed-in` finishes
   the code exchange. The account menu as the mock-up without the role line: name, e-mail,
   Account, All settings, theme, Sign out. **Settings › General › Account**: you, change password,
   where you are signed in with "Sign out" per row and "Sign out everywhere". The job stream read
   with `fetch` (an SSE reader beside `useJobStream`), the export and the consumer `openapi.json`
   saved from a `fetch` (D247).
8. **Harnesses** (D274): the `schema` seed gains a harness person; each browser context signs in
   through the real form with Playwright's request context (it shares the context's cookies);
   the header on pages goes, the runners' own `api()` keeps the client token. The backend journey
   harness is unchanged (clients).
9. **Documents:** API.md's delivered parts; OPERATIONS (the sign-in page, sessions, the cookie and
   `https`, the reset link, slowing and proxies); ARCHITECTURE's sign-in path; USER_JOURNEYS'
   statuses; API_JOURNEYS; SETTINGS_AND_UI_PLAN's settings table (Account); UI_ACCEPTANCE's state
   rows; CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D267 | Which addresses may receive a sign-in | **Recommended:** the browser is one built-in public client, `browser`, with no secret and no database row; its redirect addresses are `<origin>/signed-in` for each origin in `CORS_ORIGINS`, matched exactly. Why: the origins allowed to call the API with the browser's credentials are exactly where the app runs, so no second list can disagree with the first; PKCE protects a public client. Cost: the app must be served at the root of its origin (as today); another browser app is another origin in `CORS_ORIGINS` |
| D268 | The cookie's `Secure` flag | **Recommended:** set when `PUBLIC_URL` is `https`, left off when it is `http` (a development server). Why: a browser drops a `Secure` cookie set over plain `http` on any host but `localhost`, so a developer on another machine or address could never sign in; production runs on `https` (OPERATIONS says so, as D234 requires). Cost: an installation wrongly run on `http` sends the cookie unprotected, which OPERATIONS warns of |
| D269 | Two tabs renewing at once | **Recommended:** the browser renews under a Web Lock (`navigator.locks`), so tabs renew one at a time and the second uses the cookie the first received; the engine keeps the strict rule that a used refresh token ends the session. Why: without it, opening two tabs at once would present the same token twice and sign the person out; a grace window on the engine would weaken reuse detection. Cost: none; every current browser has Web Locks |
| D270 | "Your session ended" | **Recommended:** the sign-in page says "Your session ended. Sign in again to return to where you were." without the page's name (the mock-up named it), and the app returns to the exact address afterwards. Why: the engine would otherwise print text taken from a link, which anyone can craft to show a misleading message on the real sign-in page. Cost: the page is not named |
| D271 | How failed sign-ins are slowed | **Recommended:** per account, the first 5 failures cost nothing, then each further attempt waits 1 s, doubling to at most 15 minutes; per address the same after 20; a success clears the account's count; counts lapse after 24 hours without a failure. While waiting, an attempt is refused with the time left without checking the password. Each failure is logged with the username and address; the audit entry comes with Z4. The address is the connection's, or the proxy's forwarded one when uvicorn trusts it (`--forwarded-allow-ips`, OPERATIONS). Why: D252's "growing delay, never locked"; 5 lets a person mistype, 20 lets an office behind one address work. Cost: an attacker can slow one account's owner by guessing, never lock it |
| D272 | The password-reset link | **Recommended:** `POST /users/{id}/password-reset` answers `{url, expiresAt}` once; the link opens the engine's page (`/oauth/password?token=…`) where the person sets a password under D252's rules; valid 24 hours (`PASSWORD_RESET_HOURS`) and once; a newer link replaces an older one; using it ends the person's sessions and leads to the sign-in page. Why: a person created through the API has no password, and API.md designs a one-time link; it is a token in a URL, which C-D1 excludes for API credentials, but a single-use, short-lived link that only sets a password is the standard way and no API accepts it. Cost: the administrator passes the link on (no e-mail, D233); the page arrives in SP1 |
| D273 | What of the mock-ups I2 leaves out | **Recommended:** the role line in the menu and "What you can do" on Account come with Z1 (`/me/permissions`), the provider's button with I3, the source link and licence with L1; I2 shows none of them. Why: U-D11, nothing is shown before it works. Cost: the menu and Account are shorter than the mock-ups until then |
| D274 | How the browser runners sign in | **Recommended:** the `schema` seed holds a harness person with a fixed test password; each browser context signs in through the real sign-in form and token exchange with Playwright's request context, which shares the cookie jar, so the app starts with a real session; the token header on pages goes. Why: the runners then pass through the same sign-in as a person, and any page that forgets the header fails in a runner. Cost: the seeds rebuilt once; one password check per context |
| D275 | The engine's pages | **Recommended:** the sign-in and reset pages are HTML built in one module with every value escaped, no template library and no script; styles inline with the app's colours, light or dark by the device. Headers: `Content-Security-Policy` allowing no script, form posts to the engine only and redirects to D267's origins, `frame-ancestors 'none'`, `Cache-Control: no-store`; a form post whose `Origin` is not `PUBLIC_URL`'s is refused (forged sign-ins). Why: two small pages do not justify a dependency, and a page with no script cannot leak a password to one. Cost: the page's look is maintained beside the app's tokens |

**Journey test cases** (`tests/journeys/test_j39_sign_in.py`, on two configurations; written first
and seen failing):

1. **J39, sign in:** given a person with a password, when the browser's authorization request
   (PKCE) opens the sign-in page and the form is posted with the right credentials, then it
   redirects to `<origin>/signed-in` with a code and the `state`; the code with its verifier at
   `/oauth/token` answers a token for an hour and sets the `HttpOnly`, `SameSite=Strict` cookie;
   `GET /me` names the person, `signedInWith: "password"`, `lastSignInAt` set; the person reads
   and writes records. A code used twice, a wrong verifier, or a redirect address not in
   `CORS_ORIGINS` is refused (`invalid_grant`, or the page refuses to redirect).
2. **J39.2, renewing:** given a session, when the cookie renews it, then a new token and a new
   cookie; when the old cookie is presented again, `invalid_grant` and the session is ended: the
   new cookie is refused too and the access token answers `401 TOKEN_INVALID` (`revoked`).
3. **J39.3, sign out everywhere:** given a person signed in twice, when one session is ended from
   `/me/sessions/{id}`, then only that one is refused; when `DELETE /me/sessions`, or an
   administrator's `DELETE /users/{id}/sessions`, then every session's next request is refused and
   no cookie renews; `POST /oauth/revoke` ends the session it is sent with.
4. **J39.4, a deactivated person:** given a signed-in person, when deactivated, then the token
   answers `401 TOKEN_INVALID` (`revoked`) and the cookie no longer renews; restored, they sign in
   again.
5. **J39.5, a wrong password, then many:** a wrong password and an unknown username give the same
   message; after D271's free failures the next attempt is refused with the wait even with the right
   password; after the wait the right password signs in and clears the count.
6. **J39.6, change one's password:** without the right current password `422`; a short or common
   one `422 PASSWORD_REJECTED`; with both right, the other sessions end, this one goes on, and the
   new password signs in.
7. **J40 (I2 part), the reset link:** given a person without a password, when an administrator
   creates a link, then the link's page sets a password under the rules and the person signs in;
   the link used again, or after a newer one, is refused; using it ends the person's sessions.

Unit tests: PKCE verification, the slowing schedule's edges, session ends (idle, absolute), the
SSE reader in the frontend, the renewal under the lock.

**Browser** (a new runner `i2-sign-in`, on two models): open a record page signed out → the
sign-in page → a wrong password, then the right one → back on that page; the account menu → Account
→ change the password; sign out → the sign-in page; a session ended elsewhere → the sign-in page and
back to the same page; an export downloaded and a job's progress followed through `fetch`; keyboard
only and at 390px; axe; screenshots of the sign-in page (light, dark, 390px) and Account inspected
against the mock-ups.

**Checks:** the new journey module and the identity journeys; the unit tests; `test_openapi_contract`
with the lock diffed; Ruff on the changed files; Vitest for the session layer, the job stream, the
account menu and Account; format, lint, build; the runners `i2-sign-in`, `u3-settings` and the job
runner on the new harness sign-in. The other browser runners change only through the harness and run
at R.

**Composable domains (ADR-032):** the identity door is touched: sessions belong to a person, and a
provider sign-in (I3) records itself in the same `signedInWith`; no value source or `cause` changes.

##### I2 record (2026-10-23)

**Delivered 2026-10-23.** What was built is the plan's list, items 1–9:

- **Engine** `engine/identity/`: `sessions` (start, renew with each refresh token used once, end one
  or all, a reused token ending its session), `sign_in` (the password check slowed per D271, the
  one-time code with PKCE `S256`), `resets` (the reset link, the password change); refresh, code and
  link tokens stored as SHA-256; `tokens` carry `sid` for a person and `authentication` reads the
  session in the same statement as the key and principal. Deactivating a person ends their sessions.
  Migration `20261028_01` (five tables).
- **Routes:** `GET|POST /oauth/authorize`, the `authorization_code` and `refresh_token` grants with the
  `oauth_refresh` cookie (path `/oauth`, `HttpOnly`, `SameSite=Strict`, `Secure` under `https`),
  `POST /oauth/revoke`, `GET|POST /oauth/password`; `/me` with `signedInWith` and `sessionId`,
  `/me/sessions`, `/me/password`, `/users/{id}/password-reset`, `/users/{id}/sessions`. The pages are
  `management/sign_in_pages.py` (D275). Settings `SESSION_IDLE_HOURS`, `SESSION_DAYS`,
  `PASSWORD_RESET_HOURS`.
- **Frontend:** `api/session.ts` (PKCE, the token in memory, renewal under a Web Lock, one retry after
  a `401`, the sign-in page with the address kept), the app started behind it in `main.tsx` ("Signing
  in…", or the engine out of reach with Try again); `api/eventStream.ts` reading the job stream with
  `fetch`; `api/download.ts` and `ui/DownloadLink` for the export (job page and toast) and the consumer
  `openapi.json`; the account menu (`useMe`, initials, Account, Sign out); Settings › General ›
  Account (`AccountPage`, `browserName`).
- **Harnesses:** the `schema` seed's harness person; `signInContext` in the browser harness signs each
  context in through the real form (D274); the harness sets `PUBLIC_URL` to its engine's address.
- **Documents:** API.md, OPERATIONS (§ Signing in from the browser, the settings), ARCHITECTURE,
  USER_JOURNEYS, API_JOURNEYS, SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (I2-1 to I2-5), EXECUTION_GUIDE,
  CURRENT_FUNCTIONALITY (F26, and F16's limit, wrong since I1), CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **The journey cases were written after the engine code**, as in I1, then run: they were not seen
  failing first.
- **The sign-in and reset pages are outside the OpenAPI document** (HTML, `include_in_schema=False`);
  `/oauth/revoke` is in it and listed among the open operations.
- **Found by the browser runner, fixed:** the pages' form policy and the forged-post check used only
  `PUBLIC_URL`, so an engine reached at another address (the harness, `127.0.0.1:<port>`) could not
  post its own form. Both now also accept the page's own origin, and the harness sets `PUBLIC_URL`.
  `Referrer-Policy: no-referrer` made Chrome send `Origin: null` on the form post, refused as forged;
  it is `same-origin` (nothing is sent to another site, the app included).
- Two codes not named in the plan: `PASSWORD_INCORRECT` (`422`, the current password wrong) and
  `NOT_A_PERSON` (`403`, a client on `/me/sessions` or `/me/password`); `404 SESSION_NOT_FOUND`.
- After `/oauth/revoke` the cookie is gone, so a renewal sends nothing and answers `invalid_request`
  rather than `invalid_grant`; J39.3's case asserts that.
- `test_startup`'s pinned head revision and `u3-settings`' expected keyboard order (Account in the
  rail) brought up to date.

**Checks** (single process):

- `tests/journeys/test_j39_sign_in.py`: 14 passed (7 cases × 2 configurations);
  `tests/journeys/test_j39_j41_j43_identity.py` with `tests/test_foreign_keys.py` and
  `tests/test_openapi_contract.py`: 30 passed, after the lock was re-baselined from a diff against
  `3633627` (six paths, five schemas, `MeResponse`, the token form, `PATCH /users/{id}`'s description;
  nothing else) and the paged-collection count rose to 48.
- `tests/unit/engine/identity/`: 37 passed (slowing at its edges, the PKCE challenge, session ends).
- `tests/test_boundaries.py`, `tests/unit/test_config.py`, `tests/journeys/test_j31_system.py`: 77
  passed after OPERATIONS listed the new settings; `tests/test_startup.py`: 11 passed. Ruff on the
  changed files.
- Vitest, one run of the touched areas (`src/api`, `src/app`, `src/features/settings`,
  `src/features/jobs`, `src/routing`, UI foundation, the three bulk dialogs moved off `EventSource`):
  26 files, 265 passed, among them `session.test` (6), `eventStream.test` (2), `AccountPage.test` (3),
  `browserName.test` and `SettingsMenu.test` (7). `format`, `lint` (0 errors; 8 warnings, all in
  untouched files), `build`.
- **Browser:** `i2-sign-in` on two models: 24 checks, axe 0 violations on the sign-in page light and
  dark and on Account; `u3-settings`: 10 checks; `j1u-export` (the job stream and the download through
  `fetch`): 12 checks, axe 0. Screenshots inspected against the mock-ups: the sign-in page at 1440px
  light and dark and at 390px, the wrong-password state, Account at 1440px (a column misalignment
  found and fixed) and 390px.
- A read-only smoke check of the development server on `rdm` after it applied the migration: health
  `200`, the metadata with the new endpoints, the sign-in page `200`.

**Not run:** the full backend suite (the selection for an authentication or migration change is
"everything", which waits for R); the other 60 browser runners, which change only through the
harness's sign-in and run at R; the accessibility and visual gates (R).

**D276, decided by the user (2026-10-23), after delivery:** a short password on a development
machine. The user could not create a person on the development database with a password they would
type there, and said it is "only for development, you can have strong password for production". Built:
`PASSWORD_MIN_LENGTH`, 15 by default (D252 unchanged for production), which a development machine
lowers, down to 1; `create_admin`, the reset page and `/me/password` apply it; the most common
passwords stay refused at any length, with short ones added to the list for that case. Account's hint
no longer names a number. Checks: the identity unit tests and `test_config` (100), both identity
journey modules (32), `AccountPage.test`.

**Account reworked, at the user's request (2026-10-23), after delivery:** from a mock-up the user
approved (the security canvas, "Account page reworked" at 1440px and 390px): a profile card, the
password changed in a form opened in place with a reveal button per field and a length bar, sessions
as rows with a laptop or phone tile and relative times, and **What you can do** kept at the user's
request: each active workspace with **Everything** and a line that roles come later, true until Z1,
which fills it with roles (this revises D273 for that section only). Checks: `AccountPage.test` (4),
`dates.test`, Settings and app Vitest (111), lint, build, `i2-sign-in` (24 checks, axe 0) with
screenshots of Account closed and open at 1440px and at 390px inspected; dark Account not inspected.

**What the user cannot do yet:** sign in with the organisation's provider (I3); narrow what anyone
may do (Z1: every signed-in person and active client may do everything, and Account's "What you can
do" waits for it); manage people and clients in Settings (SP1, SP2: the reset link and signing a
person out are API calls until then).

#### I3: A sign-in provider

**Needs:** I2.

**Scope:** one or more OpenID Connect providers configured in Settings › Security › Sign-in (issuer,
client ID, secret, the claim holding groups): a person signs in there, the engine finds or creates
the user by issuer and subject, takes the provider's groups as **provider groups** (D229), and issues
its own token. Local accounts can be switched off once a provider works, with the first
administrator kept as the way back (OPERATIONS). Tested against a minimal provider in the harness;
one sign-in against a real provider the user names (Microsoft Entra ID, Google, Keycloak) before E1.

##### I3 plan (2026-10-25)

**Planned 2026-10-25; accepted by the user the same day** ("you can go ahead with the above"): D361–D370, the test cases and the "I3 as
planned" boards ([security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), the
tenth row: Settings › Security › Sign-in, a provider group, the sign-in page with local sign-in off,
Sign-in at 390px). Checked against the code at `9c702d7` with TV1 in the working tree, the approved
sign-in and Groups boards (the provider's button, "From Northfield Entra ID", "Members seen"),
API.md § Security (sign-in providers, provider groups' `source`), J39.7, D224, D225, D229 and D253.

**What the check found:**

- **The sign-in already has a place for a provider:** an authorization code and a session record
  `signed_in_with` (`password` today), `/me` answers `signedInWith`, and `issue_code` takes it as a
  parameter; the browser's side of the flow (PKCE with the engine, the refresh cookie) needs nothing
  new. A provider sign-in ends where the password form ends: `issue_code` and the redirect.
- **Nothing stores a provider, an identity or a provider group:** `users` has no issuer or subject,
  `user_groups` no source, and no table holds a provider's settings. API.md designs the routes
  (`/sign-in-providers`, `PATCH /sign-in-providers/local`) and a group's `source: {provider, name}`.
- **The engine has no HTTP client for the provider:** `httpx` is a development dependency only;
  `engine/events/webhook_client.py` speaks HTTP with the standard library and checks the address
  before connecting. `pyjwt` and `cryptography` are installed and verify RS256 and ES256.
- **"The administrator created by the CLI" is not recorded:** `create_admin` makes a person like any
  other; only its `created` security event, which names no actor, tells the two apart.
- **The approved boards** show the button on the sign-in page ("Continue with Northfield Entra ID")
  and a provider group ("From Northfield Entra ID", the claim, "Members seen" with when each was seen,
  membership changed in the provider). **No board shows Settings › Security › Sign-in**, nor the
  sign-in page with local sign-in off; the "I3 as planned" row draws both.
- **Microsoft Entra ID sends groups as object IDs** (GUIDs) unless configured otherwise, so a group's
  claim value is not a name a person can read; the approved board's "herbarium-staff" needs a name of
  its own (D364).
- **Reference patterns:** `ClientsPage` (the catalogue beside the entry, `CopyValue`),
  `SigningKeysPage` (a paragraph saying what the page does), `ConfirmDialog`, `GroupsPage`,
  `useHoldsGroup` (D303, D328); the harness's own servers in `test_j30_delivery.py` (a receiver on a
  loopback port).

**What is built:**

1. **Migration** `20261104_01_sign_in_providers`: `sign_in_providers` (key, name, issuer, client
   ID, the client secret sealed with `SECRETS_ENCRYPTION_KEY`, groups claim, enabled, version, last
   sign-in); `local_sign_in` (one row: enabled, version); `user_identities` (person, provider,
   subject; unique per provider and subject); `provider_sign_ins` (a pending sign-in: the state's
   hash, the browser binding's hash, nonce, the provider's PKCE verifier, the browser's own
   authorization request, expiry, used); `user_groups.provider_id` and `claim_value` (unique per
   provider); `user_group_members.seen_at`; `users.local_kept` (D365), set for every person whose
   `created` event names no actor.
2. **Engine** `engine/identity/providers.py` (settings, the discovery check, the secret sealed),
   `provider_client.py` (D362), `provider_sign_in.py` (start, callback, the ID token checked, the
   person found or created, the provider groups, D361, D363, D364), and the local switch (D365).
3. **Pages** (open, outside the API, D361): `GET /oauth/providers/{key}/start` with the browser's
   authorization request, redirecting to the provider; `GET /oauth/providers/{key}/callback`, ending
   with the same `303` and one-time code the password form gives, or the engine's page explaining why
   not (D368). The sign-in page lists each enabled provider as **Continue with *name*** below the
   form; with local sign-in off, only the buttons and **Sign in with a local administrator account**
   (D365).
4. **API** (`security-admin` at the instance, cursor-paged list, writes with `expectedVersion`):
   `GET|POST /sign-in-providers`, `GET|PATCH|DELETE /sign-in-providers/{key}` (`key`, `name`,
   `issuer`, `clientId`, `clientSecret` write-only and answered as `clientSecretSet`, `groupsClaim`,
   `enabled`, `redirectUri`, `lastSignInAt`, `people`: how many have signed in with it, D366);
   `GET|PATCH /sign-in-providers/local` (`enabled`, `keptPeople`, D365). A group answers `source`
   (`{provider: {key, name}, claimValue}`, `null` for a local group) and `POST /groups` takes it to
   make a provider group ahead (D364); a provider group's member reads `seenAt`. A person answers
   `identities` (`[{provider: {key, name}, subject}]`) and `localKept`. Refusals:
   `404 SIGN_IN_PROVIDER_NOT_FOUND`, `409 SIGN_IN_PROVIDER_KEY_TAKEN`,
   `422 SIGN_IN_PROVIDER_UNREACHABLE` (with the reason), `409 SIGN_IN_PROVIDER_IN_USE`,
   `409 NO_WORKING_PROVIDER`, `409 LOCAL_SIGN_IN_OFF`, `409 GROUP_FROM_PROVIDER`. OpenAPI lock
   re-baselined from a diff.
5. **Settings › Security › Sign-in** (`/settings/sign-in[/{key}]`), as the "I3 as planned" board:
   what the page does in a paragraph; the catalogue with **Local accounts** first (On or Off, the
   kept administrators counted) and each provider (Enabled or Disabled, people, last sign-in);
   **New provider** (name, key, issuer, client ID, client secret, groups claim); a provider: the
   **address to register** with Copy, its settings edited in place (the secret "Saved · type a new
   one to replace it"), **Disable** or **Enable**, **Delete** when nobody signed in with it; Local
   accounts: **Turn off** (a confirmation naming who can still use a password) or **Turn on**.
6. **Groups:** provider groups under "From *provider*" in the catalogue; a provider group as the
   approved board, with its claim value, **Rename**, no Add a member or Remove, "Members seen" with
   when; **New group** offers "From a sign-in provider" (the provider and the claim value) (D364).
7. **People:** a person's page says "Signs in with *provider*" (or "Signs in with a password", and
   "Keeps local sign-in" for a kept administrator); while local sign-in is off, **New person** and
   **Send a password link** are hidden for people who could not use them (D365). **Account** names
   the provider the session came from ("Signed in with Northfield Entra ID").
8. **The harness provider** (D369) and a seeded provider in neither seed: the journeys and the runner
   configure it through the API or the page.
9. **Documents:** API.md (the delivered parts), OPERATIONS (registering the engine with a provider:
   Entra ID, Google, Keycloak; the groups claim and Entra ID's object IDs and overage; turning local
   sign-in off and the way back with `create_admin`; leavers, D367), ARCHITECTURE (the provider
   sign-in), DECISIONS (ADR-043's consequences: a provider person), SETTINGS_AND_UI_PLAN (U8, the
   settings table), USER_JOURNEYS (J39.7, J40's provider groups) and API_JOURNEYS,
   CURRENT_FUNCTIONALITY, UI_ACCEPTANCE (I3 state rows), EXECUTION_GUIDE (the runner), CHANGELOG,
   PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D361 | How the engine signs a person in through a provider | **Recommended:** the engine is the provider's confidential client and uses the authorization code flow with PKCE (`S256`) and a nonce. The sign-in page's button opens `/oauth/providers/{key}/start` carrying the browser's own authorization request; the engine keeps a pending sign-in in the database (the state's hash, nonce, verifier, the browser's request; 10 minutes, used once) and binds it to the browser with an `HttpOnly`, `SameSite=Lax` cookie on `/oauth/providers`; the provider returns to `/oauth/providers/{key}/callback`, where the engine exchanges the code with the client secret, checks the ID token (signature against the provider's published keys, RS256, PS256 or ES256 only; `iss`, `aud`, `azp`, `exp`, `iat`, `nonce`) and ends as the password form ends: a one-time code to the browser. Why: the browser's token flow stays the one I2 built; the database holds the pending sign-in so any process can finish it; the cookie stops someone from signing a victim in to the attacker's account (login CSRF); `Lax` is needed because the provider's redirect is a cross-site navigation. The userinfo endpoint is not read: the ID token holds what is needed. Cost: one table and a second cookie |
| D362 | How the engine reaches the provider | **Recommended:** a small client on the standard library beside `webhook_client.py`, sharing its address check (link-local refused); `https` required unless the issuer names a loopback host (the harness); 10 seconds per call; the discovery document and the keys cached per process for an hour, the keys fetched again once when a token names an unknown `kid`. Why: no new runtime dependency (`httpx` is development-only); the webhook client already proves the pattern; the key refetch follows a provider's key rotation without waiting for the cache. Cost: a client of our own to keep |
| D363 | Who a provider's person is | **Recommended:** found by the provider and the token's `sub` (`user_identities`), never matched to an existing person by e-mail or username. At the first sign-in a person is created: name from `name`, e-mail from `email`, username from `preferred_username`, else `email`, else `<provider key>-<sub>`, with `-2`, `-3` added when taken; no password. Name and e-mail are refreshed from the token at each sign-in. A deactivated person is refused. Reads of a person answer `identities`. Why: an e-mail claim does not prove ownership with every provider (Entra ID lets some be set by the user), and matching on it is a known way to take over an account; `sub` is the provider's stable identifier. Cost: someone who already has a local account becomes a second person at their first provider sign-in; an administrator grants the new one and deactivates the old (OPERATIONS). Linking an identity to an existing person is left out (D370) |
| D364 | Provider groups (D229) | **Recommended:** a provider group is a row of `user_groups` with its provider and **claim value**; its name starts as the claim value and can be renamed, the claim value cannot. It is created when a sign-in first names it, or ahead of anyone's sign-in with `POST /groups {name, source: {provider, claimValue}}`, so roles can be granted before people arrive. At each sign-in the person's memberships in that provider's groups become exactly the claim's values (`seen_at` updated, groups no longer named left); adding or removing members through the API is refused (`409 GROUP_FROM_PROVIDER`). A provider without a groups claim uses no groups; a token without the claim means no groups. A sign-in that removes the last Security administrator's group is not refused (D283): the provider is where membership is decided. Why: membership lives in the organisation's directory (D229); Entra ID's claim values are object IDs, which need a readable name; granting ahead lets an administrator prepare access before go-live. Cost: membership is as fresh as each person's last sign-in, which the board's "Members seen" says |
| D365 | Turning local sign-in off | **Recommended:** `PATCH /sign-in-providers/local {enabled: false}` is refused with `409 NO_WORKING_PROVIDER` unless an enabled provider has signed someone in. While off, the sign-in page shows the providers' buttons and a small link, **Sign in with a local administrator account**, which opens the form; the form accepts only people who **keep local sign-in** (`localKept`): those made by `create_admin`, and those the migration finds were made on the server. A password link for anyone else is refused with `409 LOCAL_SIGN_IN_OFF`, and the page hides New person and Send a password link. Clients are unaffected. Why: the scope's "the first administrator kept as the way back"; `create_admin` on the server stays the way back when every provider fails (OPERATIONS); requiring a provider that has worked stops an administrator from locking everyone out. Cost: one column and a one-row table; a kept administrator still signs in with a password only (D225) |
| D366 | A provider's settings | **Recommended:** a provider has a `key` (fixed, in its addresses), a `name` (the button reads "Continue with *name*"), `issuer`, `clientId`, `clientSecret` (sealed with `SECRETS_ENCRYPTION_KEY`, D253; never answered, `clientSecretSet` instead), `groupsClaim` (empty by default) and `enabled`; it answers `redirectUri` (`<PUBLIC_URL>/oauth/providers/{key}/callback`) to register with the provider. Saving an enabled provider fetches its discovery document and keys and refuses `422 SIGN_IN_PROVIDER_UNREACHABLE` with the reason (no answer, TLS, an issuer that differs, no code flow, no keys); a disabled one saves without the check. The scopes asked are `openid profile email`. Delete only when nobody has signed in with it (`409 SIGN_IN_PROVIDER_IN_USE`); otherwise disable. Why: a mistyped issuer is found when it is saved, not when people cannot sign in; the key in the address must not change under a registration. Cost: an enabled provider cannot be saved while it is unreachable |
| D367 | Sessions, leavers and signing out | **Recommended:** a session started through a provider renews as any session (12 hours idle, 14 days at most, D251); disabling or deleting the provider ends its sessions; signing out of the engine does not sign the person out of the provider. A person removed in the provider keeps an open session until it ends, an administrator deactivates them or signs them out everywhere. Why: asking the provider at every renewal would put it in every request path and make an outage sign everyone out. Cost: a leaver's open session lasts until its idle end; OPERATIONS says to deactivate leavers in the engine too, or shorten `SESSION_IDLE_HOURS` |
| D368 | When a provider sign-in fails, and the audit | **Recommended:** a sign-in that cannot finish (a state unknown, used, expired or from another browser; the provider's `error`; the code exchange or the ID token refused; a deactivated person; a disabled provider) shows the engine's page: "*name* could not sign you in", a plain reason and **Try again**, never a redirect carrying details. Each is a `sign-in` `failed` security event with `provider` and `reason`; a success is `succeeded` with `provider`; a person made at sign-in is `user` `created` with `provider`; memberships a sign-in changes are `group` `member-added` and `member-removed` with `provider`; a provider's changes are `sign-in-provider` `created`, `updated`, `deleted`, and the switch `local-sign-in` `updated`. Provider sign-ins are not slowed (D271): the provider does its own. Why: the person sees what happened; the administrator finds why in Recent activity. Cost: none |
| D369 | The harness provider and the real try | **Recommended:** `tests/support/oidc_provider.py`, a minimal OpenID Connect provider (discovery, keys, an authorize page where the test chooses the subject, name, e-mail and groups, a token endpoint checking the secret and PKCE) on a loopback port, run in a thread by the journeys and as a script by the browser runner; it can be told to misbehave (another issuer, a wrong nonce or audience, an error). The real provider's sign-in is tried before E1 with the provider the user names and reported in E1. Why: D224's cost; the same provider serves both channels. Cost: a test server to keep |
| D370 | What I3 leaves out | **Recommended:** SAML and LDAP (D224); signing out of the provider; linking a provider identity to an existing person; claims beyond name, e-mail, username and groups, and the userinfo endpoint; Entra ID's group overage (more than 200 groups, the claim replaced by a link), which OPERATIONS explains how to avoid (groups assigned to the application). Why: each is its own design, and none blocks signing in. Cost: as listed, in the record's "cannot do yet" |

**Journey test cases** (`tests/journeys/test_j39_provider_sign_in.py`, on two configurations;
written first and seen failing; the harness provider, the harness client acting as Security
administrator through the API, the browser's flow followed with a plain HTTP client keeping its
cookies):

1. **J39.7, a first and a second sign-in:** given a provider with the groups claim, when a person
   the engine has never seen signs in through it with groups `g1` and `g2`, then they reach the
   browser's address with a code that gives a session, `/me` answers `signedInWith` the provider's
   key, the person exists with the provider's identity and no password, and two provider groups
   exist with them as members; when they sign in again with `g2` only and a new name, then the same
   person is found, renamed, and a member of `g2` only.
2. **J40, a provider group granted ahead:** given a provider group made ahead for `staff` and granted
   Reader in workspace A, when a person signs in with `staff`, then they read A's records and are
   refused a live write with `403`; signed in again without `staff`, their next read of A is
   refused; adding a member to the group through the API answers `409 GROUP_FROM_PROVIDER`.
3. **J39.7, refused sign-ins:** the callback with an unknown state, with a used state, and with
   another browser's cookie each shows the page without a code; the provider answering another
   issuer, a wrong nonce or another audience is refused; a deactivated person is refused; a disabled
   provider's start is refused. Each refusal is a `sign-in` `failed` security event with its reason.
4. **J39, local sign-in off:** turning it off with no working provider answers
   `409 NO_WORKING_PROVIDER`; after a provider sign-in it is turned off; then a local person's
   password is refused on the form, a person made by `create_admin` signs in, a password link for
   the local person answers `409 LOCAL_SIGN_IN_OFF`, and the sign-in page lists the provider and the
   administrator's link; turned on again, the local person signs in.
5. **J40, a provider's settings:** an enabled provider with an issuer nobody answers is refused
   `422 SIGN_IN_PROVIDER_UNREACHABLE`; a provider read never answers its secret; deleting a provider
   someone signed in with answers `409 SIGN_IN_PROVIDER_IN_USE`; disabling it ends that person's
   session (their next request `401`).

Unit tests: the ID token checks (each claim, algorithms refused), username derivation, the discovery
check's reasons; Vitest: the provider's state line, the local switch's confirmation sentence.
Startup: the migration's bootstrap, upgrade from `20261103_01`, restart, interrupted-migration and
lifespan checks, and a smoke start on a copy of the development database.

**Browser** (a new runner `i3-sign-in-providers`, on two models, with the harness provider; reference
pattern: Security › Clients): add the provider on Sign-in by keyboard and copy its address; sign out,
sign in through the provider choosing two groups, back to the page asked for; as the harness person,
see the person ("Signs in with …") and the two provider groups, rename one and grant it Reader;
turn local sign-in off (the confirmation), see the sign-in page with the button and the
administrator's link only, sign in with the kept administrator, turn it on. Keyboard only through New
provider and the local switch; 390px (Sign-in, the sign-in page); axe; screenshots of Sign-in, a
provider group and the sign-in page with local off at 1440px light and dark and Sign-in at 390px,
inspected against the boards.

**Checks:** the new journey module, `test_j39_j41_j43_identity.py`, `test_j40_security_pages.py`,
`test_j40_authorization.py`; `test_openapi_contract` with the lock diffed; `test_api_journeys`;
`test_boundaries`; the startup and migration groups the execution guide selects for a migration;
Ruff on the changed files; Vitest for `src/features/security`, `src/features/settings`,
`src/routing`; format, lint, build; the runners `i3-sign-in-providers`, `i2-sign-in` (the page's
form unchanged with no provider), `sp1-security` (Groups) and `u3-settings` (the navigation).

**Composable domains (ADR-032):** none of the doors is touched: the identity door is a record's
identity, and I3 changes people's; no attribute storage, audit row of data, `cause`, bulk API or
`match` declaration changes.

**What the user will still not be able to do after I3:** link a provider identity to an existing
person (D370); sign out of the provider from the engine; use a second factor with a local account
(D225); sign in with a real provider until they register the engine with one (the try before E1);
rotate a webhook's signing key (K1); try the API console with their token (C1); submit and approve
publications (Track A).

##### I3 record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's list, items 1–9:

- **Migration** `20261104_01_sign_in_providers`: `sign_in_providers`, `local_sign_in` (one row),
  `user_identities`, `provider_sign_ins`, a group's `provider_id` and `claim_value`, a member's
  `seen_at`, `users.local_kept`, and the security events' index taking the new aggregate.
- **Engine** `engine/identity/`: `providers.py` (settings, the secret sealed, the discovery check,
  the local switch, D365, D366), `provider_client.py` (discovery, keys, the code exchange, the ID
  token's checks, D361, D362), `provider_sign_in.py` (start, finish, the person, the provider
  groups, D363, D364, D368); `create_admin` marks its person as keeping local sign-in; the password
  check accepts only them while local sign-in is off.
- **Pages and API** as items 3 and 4; `signInProvider` on `/me` for Account. OpenAPI lock
  re-baselined from a diff against `a11f71e` holding only I3's additions.
- **Frontend:** `SignInPage` (Local accounts and the providers, New provider, a provider's address
  and settings, the local switch), provider groups on `GroupsPage`, a person's sign-in line and the
  password actions hidden while local sign-in is off on `PeoplePage`, the provider on Account; route
  `/settings/sign-in[/{key}]`; Sign-in in the Security group.
- **Harness:** `tests/oidc_provider.py`, run in a thread by the journeys and as a script by the
  runner `i3-sign-in-providers`.
- **Documents:** API.md, OPERATIONS (registering with a provider, the groups claim and Entra ID's
  object IDs and overage, local sign-in off and the way back, leavers), ARCHITECTURE, DECISIONS
  (ADR-043's consequences), SETTINGS_AND_UI_PLAN, USER_JOURNEYS (J39.7, J40), API_JOURNEYS,
  CURRENT_FUNCTIONALITY (F26), UI_ACCEPTANCE (I3-1 to I3-3), EXECUTION_GUIDE, CHANGELOG,
  PROJECT_STATUS, the queue.

**Where it differs from the plan:**

- **One security aggregate:** a provider's changes and the local switch are both `sign-in-provider`
  events, the switch on `local`, instead of a separate `local-sign-in` aggregate; one name keeps the
  security events' index to one more value.
- **Who keeps local sign-in, widened:** people made before Z4 have no `created` event, so the
  plan's rule ("created on the server") missed the first administrator of an existing instance;
  the migration also keeps everyone without a `created` event, and `PATCH /users/{id}` takes
  `localKept` to change it. On the development database the running server had applied the first
  version of the migration, so the same update was run there by hand: `krisztian`, `user1` and
  `user2` keep local sign-in.
- **A code added:** `409 GROUP_CLAIM_TAKEN` when a group is made ahead for a claim value that has
  one.
- **Deleting a provider** nobody signed in with deletes the groups made ahead for it, with their
  grants (said in the confirmation).
- **Shared HTTP client:** the webhook client's `post` became `exchange`, which the provider client
  calls with a larger read limit, so both keep the one address check (D362).
- **No "Recent activity" link on a provider's page:** security events filter by a person or client,
  not a provider; the provider's events are found on Security events by aggregate (U-D11).
- **The runner's kept administrator** is the harness person marked through `localKept`; the journey
  uses a person made by `create_admin`.
- **Found by the runner and fixed:** a group's page kept its old name after Rename (SP1's dialog
  updated only the list); the provider's settings form used the browser's own inputs until it joined
  the shared field look; the paired fields stacked without a gap at 390px; the provider group's note
  moved above Roles, as the board has it.
- **Asked by the user during the delivery:** Client ID and Client secret on one line, aligned, in
  the New provider dialog. They already shared a row; the secret's help text stretched the row and
  pushed the Client ID's input down. `dialog-pair` now aligns its fields at the top, for every dialog
  using it. The user also asked whether providers are built in: there is one generic OpenID Connect
  kind and no vendor presets (OPERATIONS names each vendor's issuer).
- **The journey cases were seen failing first** (10 of 10: no routes), then passed.

**Checks:**

- `tests/journeys/test_j39_provider_sign_in.py`: 10 passed (5 cases × 2 configurations), seen
  failing first; with `test_j39_j41_j43_identity.py`, `test_j39_sign_in.py`,
  `test_j40_security_pages.py`, `test_j40_authorization.py`, `test_openapi_contract.py`,
  `test_api_journeys.py`, `test_boundaries.py`, `test_startup.py`, `test_schema_drift.py`,
  `test_foreign_keys.py`: 121 passed; after the migration's widened rule, the startup, schema,
  foreign-key and provider journeys again: 27 passed. Unit `tests/unit/engine/identity` and
  `tests/unit/engine/events` with `test_j30_delivery.py` (the shared HTTP client): 131 passed,
  `test_provider_client.py` among them (the ID token's claims and algorithms, the groups claim, the
  username, the discovery check's reasons). Ruff check and format on the files I3 wrote.
- **Migration:** clean bootstrap and restart (`test_startup`, head `20261104_01`), the schema against
  the ORM; the development database upgraded by the running `--reload` server, which still answers.
- Vitest: `src/features/security`, `src/features/settings`, `src/routing`, `src/ui`, `src/app`,
  `src/features/workspaces`: 42 files, 373 passed (`securityText.test`: the provider and local lines,
  the turn-off sentence, a person's sign-in line, the events' titles; `SignInPage.test`: the key from
  a name, the groups' sections; `routes.test`: the route). `format`, `lint` (0 errors; the 8 warnings
  in untouched files), `build`.
- **Browser:** `i3-sign-in-providers` on two models: 24 checks, axe 0 violations on New provider, a
  provider (light and dark), a provider group, the turn-off confirmation and the sign-in page with
  local sign-in off (light and dark); `i2-sign-in` 28 checks (the form unchanged without a provider),
  `sp1-security` 46 checks (Groups), `u3-settings` 10 checks (the navigation). Screenshots inspected
  against the boards: New provider, a provider at 1440px light and dark and at 390px, a provider
  group, the sign-in page with local sign-in off.

**Not run:** the full backend and frontend suites and the other browser runners (R); the
accessibility and visual gates (R); a sign-in against a real provider, which needs the engine
registered there (before E1, D369).

**Shared working tree:** other sessions are working on HM1a and LS1 (the collection's scrolling,
D371–D375) in the same checkout, touching CHANGELOG, this plan and shared style sheets
(`base.css`, `components.css`, `settings.css`); I3's hunks are separate from theirs.

**What the user cannot do yet:** link a provider identity to an existing person (D370); sign out of
the provider from the engine; use a second factor with a local account (D225); sign in with a real
provider until they register the engine there (the try before E1); clear `localKept` on a page (API
only); rotate a webhook's signing key (K1); try the API console with their token (C1); submit and
approve publications (Track A).

#### I4: A provider identity linked, signing out of the provider, a second factor

**Needs:** I3. _Added by the user, 2026-10-25,_ after I3's delivery, from its "cannot do yet": "can
you please plan these into a package? … linking a provider identity to an existing person, signing
out of the provider from the engine, a second factor for local accounts, and changing localKept on a
page." Then, on the plan: "I would like the passkey too included", and on SMS: answered that
no SMS gateway is planned (D395).

**Scope:** an administrator moves a provider sign-in onto the person who already had a local account;
signing out of the engine can sign the person out of the provider too; local accounts can use an
authenticator app or a passkey as a second factor, optionally required, and a passkey alone signs a
person in; whether a person keeps local sign-in is changed on their page. Delivered in three parts,
each finished on its own: **I4a** (linking, signing out of the provider, the switch), **I4b** (the
authenticator app, recovery codes, the requirement, D383) and **I4c** (passkeys, D389–D394).

##### I4 plan (2026-10-25)

**Planned 2026-10-25; accepted by the user the same day** ("cool above accepted"): D377–D395
(D389–D395 added for passkeys and SMS at the user's request; D383 revises D225, D390 revises D275),
the test cases and the "I4 as planned" boards ([security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), the
eleventh row). Checked against the code at `ebd2a2a`.

**What the check found:**

- **A person's provider identity is one row** (`user_identities`: person, provider, subject), and a
  provider group's memberships are rows of the person; moving both onto another person is two
  updates. A person made at a provider sign-in has no password, and starts with no direct grants and
  no local groups.
- **Signing out** is `POST /oauth/revoke` from the page (`api/session.ts`), then the sign-in page;
  the engine never sees the browser leave, so it cannot send it to the provider. The provider's
  sign-out address is `end_session_endpoint` in its discovery document (OpenID Connect RP-Initiated
  Logout 1.0); most providers want the ID token back (`id_token_hint`), which the engine does not
  keep after the sign-in.
- **The sign-in page runs no script** (D275), so a second step there is a form, and a QR code there
  must be drawn by the server; neither the backend nor the frontend has a QR library. WebAuthn
  (passkeys) is reached only from script, so passkeys on that page revise D275 (D390).
- **A passkey belongs to one site name** (the relying party ID): it works only on pages at that host
  or below it. The application and the engine may be on different hosts of one site
  (OPERATIONS' "one site"), and the sign-in page is the engine's.
- **D225 left a second factor for local accounts to after 1.0**; I4b reopens it (D383).
- **`localKept`** is changed through `PATCH /users/{id}` only (I3); nothing keeps the last person
  who has it while local sign-in is off.

**What is built:**

*I4a*

1. **Linking** (D377, D378): `POST /users/{id}/identities {fromUserId, expectedVersion}` moves the
   other person's provider identities and their provider-group memberships to this person,
   deactivates the other person (their sessions end; never deleted, D237) and answers this person;
   refused `409 PERSON_HAS_ACCESS` when the other person has a password, direct grants or local
   groups, `409 IDENTITY_PROVIDER_TAKEN` when this person already signs in with that provider.
   `DELETE /users/{id}/identities/{provider}` undoes a wrong link (the next sign-in with that
   provider makes a new person). Security events `user` `identity-linked`, `identity-unlinked`.
   On the page: a person made at a provider sign-in has **Link to an existing person…** (pick the
   person, a sentence saying what moves and that this one is deactivated); a person's sign-in line
   gains **Unlink** per provider, behind a confirmation.
2. **Signing out of the provider** (D379, D380): a provider's setting **Sign people out of
   *name* too** (`signOutOfProvider`, off by default; turning it on needs the provider's
   `end_session_endpoint`, `422 SIGN_IN_PROVIDER_UNREACHABLE` otherwise), with a second address to
   register, `<PUBLIC_URL>/oauth/providers/{key}/signed-out`. A session started through such a
   provider keeps the ID token sealed until it ends. The page signs out by opening
   `GET /oauth/sign-out` (new, open): it ends the session from the cookie, clears it, and sends the
   browser to the provider's sign-out address with the ID token, which returns it through
   `signed-out` to the sign-in page; for anyone else straight to the sign-in page. Sign out
   everywhere and an administrator's sign-out stay in the engine (another browser cannot be sent).
3. **The switch** (D381): a person's page shows **Keeps local sign-in** as a switch with a
   confirmation; turning it off for the last active person who has it while local sign-in is off is
   refused `409 LAST_LOCAL_ADMINISTRATOR` (the API too).

*I4b*

4. **Migration** `user_second_factors` (person, the TOTP secret sealed with `SECRETS_ENCRYPTION_KEY`,
   confirmed when, the last step used), `user_recovery_codes` (hashed, used when), `sign_in_steps`
   (a password checked and waiting for its code: hashed token, person, the browser's request,
   expiry), `local_sign_in.second_factor_required`.
5. **Engine** `engine/identity/second_factor.py`: TOTP per RFC 6238 (D384), recovery codes (D385),
   the sign-in's second step, enrolment, removal; codes counted in the same slowing as passwords
   (D271).
6. **API** (D386): `GET /me/second-factor`; `POST /me/second-factor` (an unconfirmed secret:
   `secret`, `otpauthUri`, `qrSvg`, answered once); `POST /me/second-factor/confirmation {code}`
   (answers ten recovery codes, once); `POST /me/second-factor/recovery-codes {code}` (new ones,
   the old ones void); `DELETE /me/second-factor {code}`; `DELETE /users/{id}/second-factor`
   (Security administration, audited, D387); `secondFactor` on a person's reads;
   `secondFactorRequired` on `/sign-in-providers/local`. Refusals `422 CODE_INCORRECT`,
   `409 SECOND_FACTOR_EXISTS`, `404 SECOND_FACTOR_NOT_FOUND`.
7. **The sign-in page** (D388): after the right password, a person with a second factor gets
   **Enter the code from your authenticator app** (or **Use a recovery code**); with the requirement
   on, a person without one sets it up there (the QR code as an inline SVG, the key to type, a code
   to confirm, then the recovery codes) before any session starts. People signing in through a
   provider are not asked (their provider's own factor applies, D225).
8. **Account › Second factor:** set up (QR code, key, code), the recovery codes shown once with Copy,
   **New recovery codes**, **Remove** (with a code). Settings › Security › Sign-in › Local accounts:
   **Require a second factor with a password**. A person's page: "Second factor: authenticator app"
   and **Remove second factor** (D387).
*I4c*

9. **Passkeys** (D389–D394): migration `user_passkeys` (person, credential ID, public key, sign
   count, a name, created, last used); `engine/identity/passkeys.py` on `webauthn` (py_webauthn,
   BSD; D391). Both ceremonies run on the engine's own pages, bound to `PUBLIC_URL`'s host (D392):
   **Add a passkey** on Account opens `/oauth/passkeys/new` (the person's session checked, a name
   asked, the browser's passkey prompt, back to Account); the sign-in page offers **Sign in with a
   passkey** (a passkey alone, user verification required, D393) and, after a password, a passkey
   as the second step beside the app's code. API: `GET /me/passkeys`, `PATCH|DELETE
   /me/passkeys/{id}`, `GET /users/{id}/passkeys`, `DELETE /users/{id}/passkeys/{id}`
   (Security administration, D387); the ceremonies' options and results at
   `POST /oauth/passkeys/{registration|authentication}/{options|verify}` (open, the page's script
   only calls them). The requirement (D388) is met by an app or a passkey.
10. **The engine's pages' script** (D390): one file, `/oauth/passkey.js`, served by the engine;
   the pages' policy allows exactly that script (`script-src 'self'`), nothing inline, nothing from
   elsewhere; pages without a passkey step keep no script.
11. **Documents** for all parts: API.md, OPERATIONS (registering the sign-out address; a lost
   phone; requiring the factor), ARCHITECTURE, DECISIONS (ADR-043: D225 revised), USER_JOURNEYS
   (J39.8, J39.9, J40.13), API_JOURNEYS, CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE,
   EXECUTION_GUIDE, CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D377 | How a provider identity reaches an existing person | **Recommended:** an administrator moves it from the person the provider sign-in made onto the existing one, after it was made; never automatically, and never by entering a subject ahead. Why: matching by e-mail is the takeover I3 refused (D363); a subject is not known ahead (Entra ID's `sub` differs per application), but the duplicate appears at the person's first sign-in, so the administrator links it then. Cost: until linked, the person signs in as the new, empty person (their roles are on the old one) |
| D378 | What linking moves, and what it refuses | **Recommended:** the identities and the provider-group memberships move; the other person is deactivated and their sessions end; their history stays under their name. Refused when the other person has a password, direct grants or local groups (`409 PERSON_HAS_ACCESS`): those are a real person's, which an administrator removes deliberately first. Unlink is offered for a wrong link. Why: a link must never merge two people's access silently, and the deactivated person keeps history resolvable (D237). Cost: anything the duplicate changed before the link stays under its name |
| D379 | Signing out of the provider | **Recommended:** per provider, off by default: **Sign people out of *name* too**. Why: with Entra ID or Google, signing out of the provider signs the person out of every application of the organisation (mail, chat); some organisations want that on a shared computer, most do not. Cost: one setting, one more address to register |
| D380 | How the engine sends the browser to the provider's sign-out | **Recommended:** the page signs out by navigating to `GET /oauth/sign-out` (the engine ends the session from its cookie, as `/oauth/revoke` does) instead of `fetch`; a provider session keeps its ID token sealed until it ends, for `id_token_hint`. Why: only a navigation can take the browser to the provider; most providers need the ID token to know whom to sign out. Cost: an ID token held per open provider session (sealed); `/oauth/revoke` stays for other clients |
| D381 | `localKept` on a page | **Recommended:** a switch on the person's page with a confirmation; refused for the last active person who has it while local sign-in is off (`409 LAST_LOCAL_ADMINISTRATOR`), as the last Security administrator is (D283). Why: it is the way back; `create_admin` stays the last resort on the server. Cost: none |
| D382 | One package or several | **Recommended:** one package, I4, delivered as I4a, I4b and I4c, each reported finished on its own; I4 before E1, and E1 needs it. Why: I4a is small and closes I3's gaps; I4b and I4c change sign-in itself, which the security review in E1 must see. Cost: E1 waits for I4 |
| D383 | A second factor for local accounts in 0.12 (**revises D225**, which left it to after 1.0) | **Recommended:** yes, an authenticator app (TOTP), optional per person, and an instance switch to require it. Why: the user asked; an installation without a provider otherwise has passwords alone, which OPERATIONS warns about. Cost: I4b, a second sign-in step, codes to support (a lost phone) |
| D384 | Which second factors | **Recommended:** both an authenticator app (TOTP, RFC 6238: SHA-1, 6 digits, 30 seconds, one step either side, each step used once) in I4b and passkeys (WebAuthn) in I4c (**the user, 2026-10-25**); a person may have either or both. Why: every authenticator app speaks TOTP and it needs no script; passkeys cannot be phished and need no typing. Cost: two methods to support |
| D385 | Losing the phone | **Recommended:** ten one-time recovery codes, shown once at set-up and on demand (the old ones void), stored hashed; a Security administrator removes a person's factor (D387); `create_admin` stays the way back on the server. Why: the person recovers alone first; an administrator second. Cost: codes to keep somewhere safe |
| D386 | The QR code | **Recommended:** drawn on the server as SVG with `segno` (pure Python, no dependencies, BSD), answered beside the `otpauthUri` and the key. Why: the sign-in page's set-up step has no script, so the server must draw it; one drawing serves the page, Account and any client. Cost: one new runtime dependency |
| D387 | Removing someone's second factor | **Recommended:** **Remove second factor** on the person's page (Security administration, a confirmation, a security event); the person sets one up again, at their next sign-in when it is required. Why: the lost-phone path when the recovery codes are lost too. Cost: an administrator can lower one person's protection, which the event records |
| D388 | When the factor is asked, and requiring it | **Recommended:** after the right password, before any session or code is issued: the password page answers the code page (a step token, five minutes, hashed); a wrong code counts in the same slowing as a wrong password (D271). With **Require a second factor with a password** on, a person without one sets it up on that page before signing in, the people made on the server included. Provider sign-ins are never asked. Why: no session exists with one factor while the requirement is on; the slowing already protects against guessing. Cost: a person who loses both phone and codes needs an administrator |
| D389 | Passkeys in I4 | **Recommended:** yes, as I4c after I4b (the user asked); a passkey is a second factor after a password and also signs a person in alone. Why: a passkey is possession plus the device's fingerprint, face or PIN, so on its own it is already two factors, and it cannot be phished. Cost: I4c, a script on the sign-in page (D390), a dependency (D391) |
| D390 | Script on the engine's pages (**revises D275**, which allowed none) | **Recommended:** one script file of the engine's own, `/oauth/passkey.js`, allowed by the pages' policy as `script-src 'self'`, nothing inline and nothing from another site, loaded only on the pages that offer a passkey; it calls the browser's WebAuthn and posts the result. Why: WebAuthn exists only for script; D275's point, that nothing foreign runs beside a password field, holds with one file served by the engine and no inline code. Cost: the sign-in page is no longer script-free; the file is reviewed in E1 |
| D391 | Checking passkeys | **Recommended:** `webauthn` (py_webauthn, BSD, maintained by Duo; depends only on `cryptography` and `cbor2`, which come with it) verifies registrations and sign-ins; no attestation required (`none`), user verification required. Why: WebAuthn's verification is long and easy to get subtly wrong; a maintained library carries it. Cost: a runtime dependency and its one transitive dependency |
| D392 | Where passkeys are made and used | **Recommended:** on the engine's own pages only, the relying party ID being `PUBLIC_URL`'s host; Account's **Add a passkey** opens the engine's page and returns. Why: the sign-in page is the engine's, and a passkey made on the application's host would not work there when the two hosts differ. Cost: a hop to the engine's page to add one; changing `PUBLIC_URL`'s host later invalidates every passkey (OPERATIONS says so) |
| D393 | A passkey alone | **Recommended:** **Sign in with a passkey** on the sign-in page signs a person in without a password, user verification required; it meets the requirement (D388); a person keeps their password as a fallback (local sign-in off: only the people who keep it, as for passwords, D365). Why: the strongest and simplest sign-in a local account can have. Cost: a second way in to explain |
| D394 | Managing passkeys | **Recommended:** Account lists a person's passkeys by the name they gave (and when last used), renames and removes them; a Security administrator sees and removes them on the person's page (D387, audited); recovery codes (D385) are shared with the app. Why: people lose devices; the administrator path is the same as the app's. Cost: none beyond the pages |
| D395 | SMS or e-mail codes | **Recommended:** none: no SMS gateway setting and no codes by e-mail. Why: SMS needs a paid outside service with its credentials, stores phone numbers, fails abroad and is the weakest factor (SIM swap; NIST SP 800-63B restricts it); an organisation wanting SMS or push approvals gets them from its sign-in provider. Cost: someone without a smartphone or a passkey device uses a provider, or a hardware key (a passkey) |

**Journey test cases** (on two configurations; written first and seen failing):

- `tests/journeys/test_j40_identity_links.py` (I4a): **J40.13** a person with roles and a password
  signs in through the provider the first time, becoming a new person; the administrator links the
  new person's identity to them; their next provider sign-in is them, with their roles and the
  provider's groups; the new person is deactivated; linking a person who has a password or grants is
  refused; unlinking makes the next sign-in a new person again. **J39.8** with sign-out on, signing
  out sends the browser to the provider's sign-out address with the ID token and back through
  `signed-out` to the sign-in page, the session ended; with it off, straight to the sign-in page;
  turning it on for a provider without `end_session_endpoint` is refused. **J40** turning
  `localKept` off for the last kept person while local sign-in is off is refused.
- `tests/journeys/test_j39_second_factor.py` (I4b): **J39.9** a person sets up the factor (a wrong
  code refused, the right one answering ten recovery codes); their password alone then gives the
  code page, not a code; a wrong code is refused and counted, the right one signs them in, the same
  code again is refused; a recovery code works once; with the requirement on, a person without one
  sets it up on the sign-in page before a session exists; an administrator removes a person's
  factor; a provider sign-in is never asked.

- `tests/journeys/test_j39_passkeys.py` (I4c, with a software authenticator in the harness):
  **J39.10** a signed-in person adds a passkey on the engine's page and names it; it signs them in
  alone; after a password it serves as the second step; a passkey of another site or with user
  verification missing is refused; renaming, removing, and an administrator removing one; the
  requirement met by a passkey; the sign-in page's policy allows only the engine's script.

Unit tests: TOTP against RFC 6238's test vectors, the step window and replay, recovery codes,
linking's refusals. Vitest: the link sentence, the factor's lines. Startup checks for each migration.

**Browser** (one runner per part, on two models with the harness provider): I4a: a duplicate linked
from its page and the person signing in as themselves, unlink; sign-out through the provider and
back; the switch refused for the last kept person. I4b: set up on Account with the QR code, sign in
with a code and with a recovery code, the requirement turned on and a person setting up on the
sign-in page, an administrator removing a factor. Keyboard, 390px, axe, screenshots light and dark
inspected against the boards.

**Composable domains (ADR-032):** none of the doors is touched (people's identity, not records').

**Delivery notes** (the user, 2026-10-25: save tokens, no repeated checks across the parts; deliver
in a fresh session, Sonnet allowed):

- **Each part is finished on its own** (its code, its journey module seen failing then passing, its
  unit and Vitest tests, its docs and record, its runner section) and committed on request, only its
  own hunks (other sessions share the checkout).
- **Checked once, at the end of I4c, not per part:** the neighbouring groups (`test_j39_*`,
  `test_j40_*`, `test_j41_*` identity modules, `test_startup`, `test_schema_drift`,
  `test_foreign_keys`, `test_boundaries`, `test_api_journeys`) and the other runners (`i2-sign-in`,
  `i3-sign-in-providers`, `sp1-security`, `u3-settings`). Per part: only its own journey module, the
  unit tests of the modules it changed, `test_openapi_contract` (the lock re-baselined from a diff,
  a hash) and the startup test for its migration.
- **One runner,** `frontend/e2e/i4-sign-in.mjs` (`test:browser:i4`), grown by each part, with a
  `--part a|b|c` switch; each part runs its own section, and I4c runs the whole once. The harness
  provider (`backend/tests/oidc_provider.py`) gains `end_session_endpoint` in I4a; a software
  WebAuthn authenticator in I4c (Playwright's CDP virtual authenticator for the runner; a test
  helper signing with a generated key for the journeys).
- **One migration per part** (I4a: `user_sessions.provider_id_token`; I4b: the factor tables; I4c:
  `user_passkeys`), each written in one go: the user's `--reload` server applies a migration when
  its file is saved.
- **Records:** one "I4a/b/c record" subsection per part under this plan, as I3's record.

**What the user will still not be able to do after I4:** codes by SMS or e-mail (D395); a provider telling
the engine that someone signed out or left (back-channel logout: Entra ID does not offer it); link
an identity before the person's first provider sign-in (D377).

##### I4a record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's items 1–3:

- **Migration** `20261105_01_provider_sign_out`: `sign_in_providers.sign_out_of_provider`,
  `user_sessions.provider_id_token` and `authorization_codes.provider_id_token` (the ID token travels
  from the callback to the session in the sign-in's one-time code, sealed).
- **Engine:** `engine/identity/links.py` (link, unlink), `provider_sign_in.sign_out`,
  `provider_client.check_sign_out` and `sign_out_url` (the discovery document's
  `end_session_endpoint`), `providers.refuse_last_kept`, `sessions.end_by_refresh_token` answering
  what the session held and `end_provider_sessions`.
- **Pages and API:** `GET /oauth/sign-out` and `GET /oauth/providers/{key}/signed-out`;
  `POST /users/{id}/identities`, `DELETE /users/{id}/identities/{provider}`; `signOutOfProvider` and
  `signedOutUri` on providers; `409 LAST_LOCAL_ADMINISTRATOR`. OpenAPI lock re-baselined.
- **Frontend:** a person's **Sign-in** section (a row per provider with **Unlink…**, the password,
  **Keeps local sign-in** as a switch with a confirmation, new `ui/Switch`), **Link to an existing
  person…** and its dialog, a provider's **Signing out**, the app's sign-out as a navigation
  (`api/session.ts`), the security events' titles for a link, an unlink and `localKept`.
- **Harness:** `tests/oidc_provider.py` gains `end_session_endpoint` (`end_session`), a `/logout`
  endpoint and `logouts`; the runner `e2e/i4-sign-in.mjs` (`test:browser:i4`, `--part`), and the
  provider's start moved to `e2e/helpers/oidc-provider.mjs`, which `i3-sign-in-providers` now uses.
- **Documents:** API.md, OPERATIONS (linking, the switch, signing out of the provider), ARCHITECTURE,
  DECISIONS (ADR-043's consequences), USER_JOURNEYS (J39.8, J40.13), API_JOURNEYS,
  CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (I4a-1, I4a-2), EXECUTION_GUIDE,
  CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **Three columns, not one:** the ID token needs the one-time code to carry it; the setting needs its
  own column.
- **Deactivating** the last person who keeps local sign-in while it is off is refused too
  (`LAST_LOCAL_ADMINISTRATOR`), not only the switch: both remove the way back.
- **New codes:** `409 NO_IDENTITY_TO_LINK`, `422 LINK_SAME_PERSON`, `404 IDENTITY_NOT_FOUND`. Unlinking
  also ends the sessions that provider started for the person.
- **A session without an ID token** (started before the setting was turned on) signs out of the engine
  only; the plan did not say. `return` on the sign-out address must be at one of the browser's origins,
  otherwise the first origin's front page; the provider's `signed-out` takes the `state` it echoes.
- **The page offers Link** when the person has a provider identity and no password. Whether they hold
  direct roles or local groups is not on the page, so the dialog shows the engine's
  `PERSON_HAS_ACCESS` in those cases; the plan's "hide what cannot finish" holds for the password only.
- **The linked person takes the provider's name** at the next sign-in (D363), so the person the
  administrator picked changes name; the dialog says what moves, not that.
- **OpenAPI lock:** the working tree also holds the record-history changes of another session (RH1:
  `HistoryRelated`, `HistoryValue`, `kind` and `actorId`), so the hash is of HEAD plus I4a's files
  alone, diffed against `ebd2a2a`. `test_openapi_contract` fails in the shared tree until RH1's
  hunks are re-baselined on top of it.

**Checks:**

- `tests/journeys/test_j40_identity_links.py`: 6 passed (3 cases × 2 configurations), seen failing
  first (6 of 6); with `test_j39_provider_sign_in.py`, the identity unit tests (provider client with
  the sign-out address among them), `test_startup` (head `20261105_01`) and `test_schema_drift`:
  75 passed. Ruff check on `app/` and `tests/`; format on the files I4a wrote.
- **Migration:** clean bootstrap and restart (`test_startup`), the schema against the ORM; the
  development database upgraded through the running `--reload` server (head `20261105_01`).
- Vitest: `src/features/security` and `src/api/session.test.ts`: 39 passed (the link and unlink
  sentences, the events' titles, sign-out as a navigation). `tsc`, `eslint` (0 errors), `build`.
- **Browser:** `i4-sign-in --part a` on two models: 26 checks, axe 0 violations on the made person,
  the link dialog, the linked person, the unlink confirmation, a provider's Signing out, the last-kept
  confirmation and the person in dark. Screenshots inspected against the boards: the made person, the
  link dialog, a provider's Signing out, the last-kept confirmation, the person at 390px and in dark.

**Not run:** the neighbouring groups and the other runners (once, at the end of I4c); the full
suites (R); a sign-out against a real provider (before E1, D369).

**Shared working tree:** other sessions edit RH1's history, RA1's recent activity and LS1's scrolling
in the same checkout (CHANGELOG, this plan, the API document, `client.ts`, shared style sheets); I4a's
hunks are separate from theirs.

**What the user cannot do yet:** a second factor for local accounts and passkeys (I4b, I4c).

##### I4b record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's items 4–8:

- **Migration** `20261106_01_second_factor`: `user_second_factors`, `user_recovery_codes`,
  `sign_in_steps` and `local_sign_in.second_factor_required`. One new runtime dependency, `segno`.
- **Engine** `engine/identity/second_factor.py`: TOTP (RFC 6238), the secret sealed, recovery codes as
  SHA-256, the QR code drawn as an inline SVG from `segno`'s modules, enrolment, confirmation, new
  codes, removal (own, with a code; an administrator's), and the sign-in's step (`open_step`,
  `load_step`); `sign_in.check_password(finish=False)`, `complete` and `record_failure`;
  `providers.set_local` takes `secondFactorRequired`.
- **API and pages:** `GET|POST /me/second-factor`, `POST /me/second-factor/confirmation`, `POST
  /me/second-factor/recovery-codes`, `DELETE /me/second-factor`, `DELETE /users/{id}/second-factor`,
  `secondFactor` on a person, `secondFactorRequired` on local sign-in; the sign-in page's code step,
  recovery step, set-up and recovery codes (`POST /oauth/second-factor`). OpenAPI lock re-baselined.
- **Frontend:** Account's **Second factor** (`SecondFactorPanel`), **Require a second factor with a
  password** on Local accounts, a person's second-factor row with **Remove second factor…**, the
  events' titles. **Runner** `i4-sign-in --part b`.
- **Documents:** API.md, OPERATIONS (a second factor for local accounts, a lost phone), ARCHITECTURE,
  DECISIONS (ADR-043: D225 revised), USER_JOURNEYS (J39.9), API_JOURNEYS, CURRENT_FUNCTIONALITY
  (F26, and its limits corrected for I4a), SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (I4b-1 to I4b-4),
  EXECUTION_GUIDE, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **A code of the app signs in once per step.** The code that confirmed the app is spent, so the first
  sign-in after set-up takes the next step's code (accepted: one step either side). The journey
  cannot show a second distinct app code within one test without waiting 30 s; the unit tests show the
  window and the replay with RFC 6238's vectors.
- **Recovery codes:** twelve characters in three groups of four (the board's), 60 bits, stored as
  SHA-256 (not keyed); a code or recovery code is also accepted by New recovery codes and Remove.
- **The password's own success** is logged, and the account's count of failures cleared, only when the
  whole sign-in is done; otherwise a known password would let someone guess codes without being slowed.
- **Found while writing:** a code typed in non-ASCII digits (Arabic-Indic) made the comparison raise
  and the page answer `500`; the code is now read as ASCII digits only (unit test). The runner's
  provider helper passed `--client-secret <secret>`, which argparse took for an option when the random
  secret began with `-`; it passes `--client-secret=<secret>` (I3's runner uses the helper too).
- **Account offers it when the session is a password's** (as Change password): a person signed in with
  a provider has no use for it. Remove is not shown while the instance requires a second factor.
- **A test over 10 s:** the second-factor journey case is 11 s, ten Argon2id password checks and the
  1.2 s wait of the slowing.

**Checks:**

- `tests/journeys/test_j39_second_factor.py`: 6 passed (3 cases × 2 configurations), seen failing
  first (6 of 6); with the I4a module, `test_j39_provider_sign_in.py`, the identity unit tests
  (`test_second_factor`: RFC 6238's vectors, the window, replay, what people type, the QR drawing),
  `test_startup` (head `20261106_01`) and `test_schema_drift`: 90 passed. Ruff check and format on
  the files I4b wrote.
- **Migration:** clean bootstrap and restart, the schema against the ORM; the seeds rebuilt.
- Vitest: `src/features/security`, `settings`, `api`, `ui`, `routing`, `app`: 44 files, 354 passed
  (`SecondFactorPanel.test`: the key grouped, a wrong code then the codes once, removing with a code,
  no Remove while required). `tsc`, `eslint` (0 errors), `build`.
- **Browser:** `i4-sign-in --part b` on two models: 38 checks, axe 0 violations on Account in each
  state, the code page (and with a wrong code), the recovery page, the requirement's confirmation, the
  set-up page, its recovery codes, a person's row, the removal confirmation and the code page in dark.
  Screenshots inspected against the boards: Account setting up, with the codes and on, the set-up
  page, a person's page, the code page at 390px.

**Not run:** the neighbouring groups (`test_j39_sign_in` among them, whose password check this part
changed) and the other runners, once at the end of I4c; the full suites (R); a second factor with
an authenticator on a real phone (the codes are made from the key by RFC 4226's arithmetic).

**Shared working tree:** as I4a's.

**What the user cannot do yet:** passkeys (I4c).

##### I4c record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's items 9 and 10, and the documents of item 11:

- **Migration** `20261107_01_passkeys`: `user_passkeys`; `sign_in_steps.challenge` and a `user_id` that
  may be empty, which keep a ceremony's challenge. Dependency `webauthn` (py_webauthn).
- **Engine** `engine/identity/passkeys.py`: the relying party (the host and origin of `PUBLIC_URL`),
  registration and authentication ceremonies, the passkey alone and as the second step, rename and
  remove, the requirement met by an app or a passkey (`second_factor.required_step`).
- **The engine's pages and script:** `GET /oauth/passkeys/new`, `GET /oauth/passkey.js` (the file
  `management/passkey.js`), `POST /oauth/passkeys/{registration,authentication}/{options,verify}`; the
  sign-in page's **Sign in with a passkey** and the second step's **Use a passkey** ("Confirm it is
  you"); the policy `script-src 'self'` only on the pages that offer one.
- **API:** `GET|PATCH|DELETE /me/passkeys`, `GET|DELETE /users/{id}/passkeys`, `passkeys` on a person
  and on `/me/second-factor`. OpenAPI lock re-baselined.
- **Frontend:** Account's **Passkeys** (`PasskeysPanel`) before **Authenticator app**, a person's
  passkey rows with **Remove passkey…**, the events' titles, "Signed in with a passkey". **Runner**
  `i4-sign-in --part c`; the browser harness takes `host` (`localhost`).
- **Harness:** `tests/software_authenticator.py`; the runner's Chromium virtual authenticator.
- **Documents:** API.md, OPERATIONS (passkeys, `PUBLIC_URL`'s host), ARCHITECTURE, DECISIONS (ADR-043:
  D275 revised), USER_JOURNEYS (J39.10), API_JOURNEYS, CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN,
  UI_ACCEPTANCE (I4c-1 to I4c-4), EXECUTION_GUIDE, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **A challenge table was not needed, but a column was:** a ceremony's challenge lives in
  `sign_in_steps` (I4b's table), which gains `challenge` and may have no person yet; the plan's
  migration named `user_passkeys` only.
- **The dependency is larger than the plan said:** `webauthn` 2.x also needs `pyOpenSSL` and
  `pyasn1`, and its newest release (3.x) needs `cryptography` 49, which the project pins below 48.
  The pin is `webauthn>=2.7,<3`; installing it unpinned moved the shared virtual environment's
  `cryptography` to 50 for a while, and it was put back to 47.0.0, within the project's range.
- **`signedInWith` `passkey`:** a passkey alone makes a session of that name; a provider's key can no
  longer be `password`, `passkey` or `local`.
- **A passkey-only person has no recovery codes** (they belong to the app): a lost device is an
  administrator removing the passkey. The plan's "recovery codes shared with the app" holds for
  people who have both.
- **Removing the app while the instance requires a second factor** is allowed once the person has a
  passkey (the requirement is met by either); Account hides Remove otherwise.
- **Found by the runner and fixed:** a helper function I added for the passkey pages was named like
  the token endpoint's `_error` and replaced it, so every error of `/oauth/token` answered `500`
  (the journeys had not yet exercised that path in this combination; `test_j39_sign_in` now passes
  and was run with the neighbouring groups); the password's own success was logged and cleared the
  account's failures before the second step because the form did not pass `finish=False` (`sp1-security`
  saw two "Signed in" events; the journey now asserts one and that a right password does not wipe the
  count of wrong codes).
- **Account's two cards** follow the I4c board (**Passkeys**, **Authenticator app**), so I4b's heading
  "Second factor" on Account became "Authenticator app".
- **Journeys over 10 s:** the second-factor case (17 s: Argon2id password checks and three waits of the
  slowing) and the passkey case (12 s: seven sign-ins).

**Checks:**

- `test_j39_passkeys.py`: 6 passed (3 cases × 2 configurations), seen failing first (6 of 6); unit
  `test_passkeys` (the relying party) and `test_second_factor`.
- **Once, at the end of I4c:** the identity journeys (`test_j39_*`, `test_j40_*`, `test_j41_*`) with
  the unit tests for `app/engine/identity`, `test_startup` (head `20261107_01`), `test_schema_drift`,
  `test_foreign_keys` (the four new rules added), `test_boundaries` (a cycle and a row delete in the
  new module were refused and fixed), `test_api_journeys` and `test_openapi_contract`: 224 passed and
  one failed, `test_openapi_contract`'s lock, which fails in the shared tree because it also holds
  RH1's changes; the document of HEAD plus I4's files alone has the hash the test now holds
  (`04a8bcae…`). Its paged-operation count rose by two (62).
- **Migration:** clean bootstrap and restart, the schema against the ORM, the foreign-key rules; the
  development database at `20261107_01`.
- Vitest: `src/features/security`, `settings`, `api`, `ui`, `routing`, `app`, `workspaces`: 53 files,
  433 passed (`PasskeysPanel.test`: the list, the engine's page to add, rename, remove). `tsc`,
  `eslint` (0 errors; 8 warnings in untouched files), `build`, prettier on the files I4 wrote.
- **Browser, once:** `i4-sign-in` with its three parts on two models: 90 checks, axe 0 violations on
  Account's Passkeys in each state, the engine's Add a passkey page, the sign-in page with the
  button, the second step, a person's passkey rows and the removal confirmation, and the sign-in page
  in dark; with `i2-sign-in` (28 checks), `i3-sign-in-providers` (24), `sp1-security` (50) and
  `u3-settings` (10), which run the pages I4 touched. Screenshots inspected against the boards:
  Account's Passkeys, the sign-in page's button, the second step; I4a's and I4b's as recorded.

**Not run:** the full suites and the other runners (R); the accessibility and visual gates (R); a
passkey on a real device and a real domain (Chromium's virtual authenticator and the software
authenticator stand in; `https` on the real `PUBLIC_URL` is the E1 review's); a sign-in against a
real provider (before E1, D369).

**Shared working tree:** as I4a's. `test_openapi_contract` needs RH1's hunks re-baselined on top of
I4's hash when both are committed.

**What the user cannot do yet** (after I4): codes by SMS or e-mail (D395); a provider telling the
engine that someone signed out or left; an identity linked before the person's first provider sign-in
(D377); a passkey before the engine's address is final (changing `PUBLIC_URL`'s host invalidates them).

##### I4 review record (2026-10-25)

**Delivered 2026-10-25,** after a review of I4a–c; every finding fixed, none postponed:

- **Passkey removal asks for proof** (password, or a code): `PasskeyRemoval {proof}`,
  `second_factor.prove` (slowed and counted like a wrong password); Account's removal dialog asks
  for it.
- **Recovery codes keyed:** HMAC-SHA-256 under the encryption key (`_recovery_hash`); codes made
  before stop working (pre-1.0, no upgrade path kept).
- **Password required** for an app or a passkey (`409 PASSWORD_REQUIRED`); the passkey closes a way
  past a provider.
- **Link** locks both rows in id order; `409 LINK_TARGET_DEACTIVATED`.
- **Passkey ceremonies capped** at 2000 open (`MAX_OPEN_CEREMONIES`), `429` with `Retry-After: 60`.
- **Tests:** `test_j39_passkeys` (proof required and wrong, the cap), `test_j40_identity_links`
  (`PASSWORD_REQUIRED`, `LINK_TARGET_DEACTIVATED`), unit `test_recovery_codes_are_stored_keyed`,
  `PasskeysPanel.test`. **OpenAPI lock:** the hash is now of the whole working tree, RH1's history
  changes included (the earlier I4-only hash could not be re-derived), so the test passes in the
  shared checkout.

#### I5: A sign-in screen in the application

**Needs:** I4 (retrofitted into 0.12 on the user's request, 2026-10-25). _Asked by the user,
2026-10-25,_ after the engine's sign-in page was branded: "we can offer the current for external
applications to sign in using web, but can we just build a signing page with an additional oauth
endpoint just for the signing page? (covering all the signing options of course)", and "they have to
use the same code, so no double coding any rule".

**Scope:** the application signs a person in on a screen of its own, which follows the saved theme and
the application's components and carries the refiroo welcome words, instead of leaving for the
engine's HTML page. The engine's `/oauth/authorize` pages stay unchanged for outside OAuth clients.
The screen covers every way in: a password, the second factor (code or recovery code), a passkey, a
sign-in provider's button, and the pages a reset link opens. The token flow is unchanged (code flow
with PKCE, `/oauth/token`, the `oauth_refresh` cookie).

**The rule of the package (D415):** every rule lives once. The checks now in
`management/routers/oauth.py` that are mixed with rendering (the client and redirect-address checks,
PKCE, the password check, the rate limits, the second-factor and recovery-code handling, the
provider state, the security events) move into engine functions that return an outcome (signed in,
second factor needed, wrong credentials, wait N seconds, ...). The HTML routes and the new JSON
routes are both thin: read the input, call the function, present the outcome. Nothing is copied.

**Plan to write when it starts:** the list of what in `oauth.py` mixes rules and rendering; the JSON
endpoints (D416); the sign-in screen and its mock-up, shown with the plan for one approval; the
journeys J39 and I2 run unchanged against the HTML pages and extended to the JSON path; the test
that both paths refuse an unregistered client, a foreign redirect address and a wrong PKCE verifier.

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
workspace. _Amended by P0:_ reads per workspace only, narrowing for writes (D243); the record
writes check the live or change-set action by `changeSetId` (D244); lists filtered, named resources
`403` (D249); the declarations published per operation in the OpenAPI document, API.md's table
then pointing there (D256). The temporary "all actions" role from I1 becomes the predefined Security administrator
plus Owner of every workspace for the first administrator.

##### Z1 plan (2026-10-23)

**Planned 2026-10-23; accepted by the user the same day** ("otherwise its good"): D277–D288, the
test cases and the mock-up, with one correction: the account menu's Account and All settings were
plain hyperlinks beside the Sign out button and become buttons like it (the mock-up corrected; built
in item 8). Checked
against the code at `ffe558b` with P0's catalogue (API.md § Security), ADR-044, J40 and the approved
mock-ups (the Account board's "What you can do" and the menu's role line, in the reworked Account's
style).

**What the check found:**

- **159 operations need a declaration**, and they name the workspace they act in **37 different
  ways** (counted from the document with every flag on): a path `workspace_key` (10 routes, 7 more
  with a change set or publication in the query); `workspaceKey`, `changeSetId` or `publicationId` in
  the query, the default workspace without them (16); a change set (11), publication (2), record (9),
  relation (3), job (7) or subscription (8) named in the path; `workspaceKey` or `changeSetId` in the
  body (batches, exports, record and relation creates, subscriptions), or inside the import form's
  JSON field; two workspaces in the body (moves, model mappings); none (38: the caller, security
  administration, system, drafts, releases). A live relation's create names only `fromObjectId`;
  a live record's update and delete name only the record.
- **No cross-process signal exists for model assignments.** P0's "What already exists" said 0.11 N1
  sends them through `pg_notify`; it reads the assignment on each request instead (the read guard),
  and the only `pg_notify` is the job channel. D226's cache invalidation therefore has nothing to
  reuse (D278).
- **The authentication statement** already reads the key, the principal and the session in one
  query per request; I1 raised the batch statement budgets by one for it.
- **Jobs** carry `workspace_key` (nullable) and ten kinds; nothing records a requester (Z2 adds it).
  Subscriptions carry their workspace.
- **FastAPI 0.141** includes routers lazily; the request body is read before dependencies run and
  kept on the request, so a dependency can read `workspaceKey` or `changeSetId` from it without a
  second parse.
- **Every database a test uses** holds the harness client and person (I1, I2), and a database built
  from empty gets a client made in it: all three must hold grants, or every test is refused.
- **The development database** has the user's person and possibly a client from `create_client`;
  neither has a grant, so Z1 alone would lock the user out of their own instance (D282).
- **Account** shows "Everything" per active workspace (I2's rework); the account menu has no role
  line (D273).

**What is built:**

1. **Migration** `20261029_01`: `roles` (key, name, description, `predefined`, version; the nine
   predefined rows inserted, D279), `role_action_groups` (a custom role's groups), `user_groups` and
   `user_group_members` (local groups, D229), `grants` (public ID; one of user, client or group;
   role; the instance or a workspace, removed with the workspace; `applications` and `recordTypes`
   for writes), and `authorization_state` (one row, a generation number kept by PostgreSQL triggers
   on the five tables and on a principal's `active`, D278). Every existing active person and client
   gets D282's grants.
2. **Engine** `engine/authorization/`: the catalogue (14 action groups, each action with its groups;
   the predefined roles' groups, D279), roles (create from scratch or copied, change, delete when
   unused), groups and members, grants (validated: a workspace grant's narrowing names applications
   and record types of that workspace's model; an instance grant is never narrowed, D281), the last
   Security administrator rule (D283), and the caller's permissions: one query over their grants,
   direct and through groups, cached per process by generation (D278).
3. **The route check** `management/access.py`: every operation declares `requires(action, at=…)`,
   naming where its workspace comes from (D277); the declaration is a dependency and appears in the
   operation's OpenAPI entry as `x-action` and `x-action-groups` (D256). The check runs once per
   request, after authentication: allowed, or `403 FORBIDDEN` with `action`, `groups` and
   `workspaceKey`. The ten shared record writes pick `edit-live` or `change-sets` by `changeSetId`
   (D244). Jobs by their kind's group (D285), moves and mappings by both workspaces (D286), profiles,
   mappings and source files at any scope (D287).
4. **Lists filtered** (D249, D288): workspaces, workspace models and the runtime state's list show the
   workspaces where the caller holds any group; jobs and subscriptions those whose group the caller
   holds in their workspace. A named workspace the caller holds nothing in answers `403`.
5. **Routes** (all `security-admin` at the instance, cursor-paged lists, writes with
   `expectedVersion`, as API.md designs them): `GET /action-groups`; `GET|POST /roles`,
   `GET|PATCH|DELETE /roles/{key}`; `GET|POST /groups`, `GET|PATCH|DELETE /groups/{id}`,
   `GET|POST /groups/{id}/members`, `DELETE /groups/{id}/members/{userId}`; `GET|POST /grants`,
   `DELETE /grants/{id}`; `GET /workspaces/{key}/access`. For anyone signed in:
   `GET /me/permissions?workspaceKey=` and `GET /me/grants` (D284). Refusals `ROLE_PREDEFINED`,
   `ROLE_IN_USE`, `LAST_SECURITY_ADMINISTRATOR`, `GRANT_SCOPE_UNKNOWN`, `GROUP_NOT_FOUND`,
   `ROLE_NOT_FOUND`, `GRANT_NOT_FOUND`. OpenAPI lock re-baselined.
6. **CLI:** `create_admin` grants D282's roles; `create_client --role <key>` (repeatable, at the
   instance) grants roles to the new client, none without it.
7. **Harnesses:** the harness client, the harness person and a client made in a database built from
   empty hold every predefined role at the instance, granted by the engine's own function; the seeds
   are rebuilt once.
8. **Frontend:** Account's **What you can do** lists the person's grants from `GET /me/grants` in the
   reworked card style: per row the workspace (or "Every workspace" for an instance grant), the role,
   and a faint line with what writes are narrowed to and whether it comes directly or through a group;
   "You have no roles yet. Ask a security administrator." when empty. The account menu gains the role
   line, "Data steward in Herbarium" (the roles that apply in the current workspace, from
   `/me/permissions`). The menu's Account and All settings become buttons like Sign out (the user,
   2026-10-23). The mock-up below shows both.
9. **Documents:** API.md (the delivered parts; the catalogue table replaced by the groups and a
   pointer to the operations' `x-action`, D256); OPERATIONS (the first administrator's roles, the
   upgrade's grants, recovering a locked-out instance with `create_admin`); ARCHITECTURE's route
   check; USER_JOURNEYS' and API_JOURNEYS' statuses; CURRENT_FUNCTIONALITY; CHANGELOG,
   PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D277 | How a route finds the workspace it is checked in | **Recommended:** each operation declares where its workspace comes from, from a short list (the path's workspace, a change set, publication, record, relation, job or subscription named in the path, the query's or body's `workspaceKey` or `changeSetId`, the default workspace, two workspaces, the instance, any scope), and the route check resolves it with the engine's own lookups before the handler runs; an unknown change set, record or job answers the same `404` the handler would. Why: the check runs once, in one place, before anything is read or written, and a route that forgets is caught by the contract test; leaving the check to each handler would let one forget silently. Cost: routes naming a change set, record, relation, job or subscription by ID look it up twice (one indexed read); statement budgets for those routes rise by one |
| D278 | How a permission change reaches every process (**revises D226's `pg_notify`**) | **Recommended:** a generation number in one row, raised by PostgreSQL triggers whenever a grant, role, role's groups, group, membership or principal's `active` changes, read in the authentication statement the request already makes; each process keeps the caller's permissions with the generation they were read at and reads them again when it differs. Why: N1 has no `pg_notify` to reuse (see above); this needs no listener, cannot miss a message, and is exact on the very next request in every process, also when the change was made by SQL; a trigger cannot be forgotten by a code path. Cost: security writes queue on one row (they are rare); a change empties every process's cache, not only the affected principal's |
| D279 | Where the predefined roles live | **Recommended:** all roles are rows in `roles`, the nine predefined inserted by the migration and marked `predefined`; a predefined role's groups are in the code's catalogue, a custom role's in `role_action_groups`; grants refer to the role row. Why: the database then refuses deleting a granted role on its own (`ROLE_IN_USE`), and a predefined role cannot be changed by editing data. Cost: changing a predefined role is a code change, noted in CHANGELOG |
| D280 | Approve publications in Z1 | **Recommended:** left out until A1; Z1's catalogue has the 13 groups that have routes, and the Data owner gains `approve` with "own" in A1. Why: A1 designs "own" and four-eyes, and Track A is after the cut line; a group with no routes would show in Roles as a right that does nothing. Cost: the Owner's definition grows in A1 |
| D281 | Narrowing before Z2 | **Recommended:** grants store and check their narrowing in Z1 (a workspace grant only; its applications and record types must exist in that workspace's model, `422 GRANT_SCOPE_UNKNOWN`); the route check counts a narrowed grant as holding its groups, and Z2 enforces the narrowing at the write unit, the one place that knows which types a batch, import, move or publication writes. Why: checking types at the route would be wrong for every bulk path and duplicated in Z2. Cost: between Z1 and Z2 a narrowed grant writes every type; nothing is released between them, and the record says so |
| D282 | The first administrator and the principals that exist today (**revises the scope's "Security administrator plus Owner"**) | **Recommended:** `create_admin` grants, at the instance, Security administrator, Data owner, Model administrator, Workspace administrator, Integration administrator and Operator, so the first person can set the instance up; the migration grants the same to every active person and client that exists, so nothing that worked yesterday stops; people and clients created afterwards start with none. Why: until SP1, a grant is an API call; a first administrator who cannot install a model or create a workspace without writing one is stuck, and the user's development instance would be locked out on upgrade. Cost: the first administrator, and today's principals, hold everything until someone narrows it (SP1 makes that a page); separation of duties is something an organisation sets up, which OPERATIONS says |
| D283 | What "the last Security administrator" counts | **Recommended:** active **people** holding Security administration at the instance, directly or through a group; clients do not count. Refused with `409 LAST_SECURITY_ADMINISTRATOR`: removing such a grant, deactivating the person, removing them from the group, deleting the group, or taking the group out of a custom role. Why: a client cannot sign in to the Security pages to repair access; `create_admin` on the server stays the way back. Cost: none |
| D284 | The caller's own grants, for Account (**new route**) | **Recommended:** `GET /me/grants` (cursor-paged): the caller's grants, direct and through groups, each with the role's name, the scope and narrowing, and the group it comes through; `/me/permissions` names the roles behind each group. Why: Account lists roles per workspace, as the approved mock-up shows, and `/me/permissions` answers one workspace at a time. Cost: one route |
| D285 | Jobs until Z2 | **Recommended:** a job is read, followed, cancelled and confirmed by a holder of its kind's group in its workspace (`bulk` for batches, imports, profiles and profile checks; `browse` for exports; `copy-move` for moves and mapping inference; `model-release`, or `change-sets` for a change set's, for migrations; `model-authoring` for dry runs and inference), at any scope for a job without a workspace; the requester's own right comes with Z2's `requested_by`. Why: the job's workspace and kind are already stored; the requester is not. Cost: until Z2 a requester who loses the group loses sight of their job, which Z2 keeps |
| D286 | Moves and model mappings at the route | **Recommended:** a move needs `copy-move` in the target and `browse` in the source, both checked at the route in Z1; a mapping's routes need `copy-move` at any scope (D248). Z2 adds the target's record types. Why: both workspaces are named in the request; checking them at the route is exact. Cost: none |
| D287 | Source files until Z2 | **Recommended:** `bulk` at any scope reads and changes source files in Z1; Z2 gives them their owner and narrows them to the owner and the file's workspace (D248). Why: the owner needs Z2's column. Cost: until Z2 any holder of `bulk` sees every uploaded file |
| D288 | Which workspaces a list shows (**narrows D249's "browse"**) | **Recommended:** the workspace list, the workspace models and the runtime state show every workspace where the caller holds **any** group, not only Browse. Why: an Integration administrator or a Model administrator granted one workspace has no Browse there but must pick it in the interface; a workspace's key and label reveal no data (one organisation per instance, D249). Cost: a person may see the name of a workspace whose records they cannot read |

**Mock-up** (on the security mock-ups canvas, beside the Account boards: "Account with roles" at
1440px and 390px, light and dark): What you can do with grants per workspace, an instance grant, a
narrowed one and one through a group; the account menu with the role line.

**Journey test cases** (`tests/journeys/test_j40_authorization.py`, on two configurations; written
first and seen failing; clients unless a person is named, created and granted through the API by the
harness client acting as security administrator):

1. **J40.1, a Reader:** given a client granted Reader in workspace A, when it reads the model,
   records, relations, history, change sets and publications in A, or starts an export, then each
   answers; when it writes a record live, creates a change set, sends a batch or an import, or
   publishes, then each answers `403 FORBIDDEN` with `action`, `groups` and `workspaceKey: A`; in
   workspace B every read answers `403`.
2. **J40.2, a Contributor:** given Contributor in A, when it creates a change set and writes a record
   in it, then both pass; the same write without `changeSetId` answers `403` naming `edit-live`;
   publishing the change set answers `403` naming `publish`.
3. **J40.4, through a group:** given a person signed in (J39's form) in a group granted Data steward
   in A, when they write a record live, then it passes; when they are removed from the group, then
   their next request answers `403`.
4. **J40.5, a custom role:** given a role copied from Data steward without Publish, granted in A,
   then a live write passes and publishing answers `403`; changing a predefined role answers
   `409 ROLE_PREDEFINED`; deleting the granted role `409 ROLE_IN_USE`, and once the grant is removed
   it is deleted.
5. **J40.6, on the next request in every process:** given two engine processes (the several-process
   harness) and a client granted Data steward, when its grant is removed through the first, then its
   next request to the second answers `403`; granted again, it passes.
6. **J40.7 and J40.8, who can do what, the last administrator:** given a direct grant in A, a group's
   grant in A and an instance grant, when A's access is read, then all three are listed with where
   they come from; given one person holding Security administration, removing that grant, or
   deactivating the person, answers `409 LAST_SECURITY_ADMINISTRATOR`.
7. **J40.9, lists follow permissions:** given a client granted Reader in A only, the workspace list,
   the workspace models and the jobs list show A and nothing of B; `GET /workspaces/B` answers `403`.
8. **J40, what I may do:** given grants in A (direct, narrowed to one record type) and at the
   instance, `GET /me/permissions?workspaceKey=A` lists each group with its narrowing, role and
   source; `GET /me/grants` lists the grants; a grant naming a record type A's model lacks answers
   `422 GRANT_SCOPE_UNKNOWN`.

The contract test (`test_openapi_contract`) refuses an operation without `x-action`, an action the
catalogue lacks and a declared workspace source the route cannot provide. Unit tests: the
permission resolution (instance against workspace, groups, any scope, the shared writes), the
generation check, the last-administrator rule's cases.

**Browser:** `i2-sign-in` extended (two models): Account's What you can do and the menu's role line
for the harness person, and for a person granted Reader in one workspace; keyboard, 390px, axe;
screenshots inspected against the mock-up. Reference pattern: the reworked Account page.

**Checks:** the new journey module; the identity journeys (their principals now need grants); the
groups `python -m tests.affected` selects for the route-check change, announced with their expected
time if beyond three minutes; `test_openapi_contract` with the lock diffed; the unit tests; Ruff on
the changed files; Vitest for Account and the menu; format, lint, build; the browser runner above.
The route check touches every route, so the whole suite runs at R.

**Composable domains (ADR-032):** the identity door is touched: grants name principals by kind and
public ID and refer to applications and record types as data; no value source, audit row or `cause`
changes (Z4).

**What the user will still not be able to do after Z1:** narrow writes to record types in effect (Z2);
keep their own job's visibility after losing a group (Z2); limit a client to some consumer APIs (Z3:
any `consumer` token still reads every consumer API); see who changed what (Z4); an interface that
hides what a person may not do (Z5: a Reader or a Security administrator without Browse sees the
engine's refusals on pages they open); manage people, groups, roles and grants on a page (SP1: API
calls until then).

##### Z1 record (2026-10-23)

**Delivered 2026-10-23.** What was built is the plan's list, items 1–9:

- **Migration** `20261029_01`: `roles` (the nine predefined inserted), `role_action_groups`,
  `user_groups`, `user_group_members`, `grants` (one principal; the instance or a workspace, removed
  with it; narrowing arrays; an instance grant cannot narrow, a check constraint), and
  `authorization_state` with statement-level triggers on the five tables and on `users.active` and
  `oauth_clients.active` (D278). Every active person and client existing before it holds the first
  administrator's roles at the instance (D282). It ran on the user's development database through
  the running dev server; checked afterwards: nine roles, the user's person with six grants, seven
  triggers.
- **Engine** `engine/authorization/`: `catalogue` (13 groups, 27 actions each with its groups and the
  phrase a refusal uses, the predefined roles' groups, the first administrator's roles, the job
  kinds' groups), `permissions` (one statement over direct and group grants; a per-process cache
  keyed by database, principal and generation), `administration` (roles, groups, members, grants,
  the access list, the caller's grants, the last Security administrator rule) and `visibility` (the
  filtered lists' conditions). `authenticate` reads the generation in its statement; deactivating
  the last Security administrator is refused in `identity/users`.
- **The route check** `management/access.py`: `requires(action, at=…)` on all 183 operations but the
  six open ones, `AuthorizedRoute` publishing `x-action`, `x-action-groups` and `x-action-scope`,
  and `authorized` in `MANAGEMENT_DEPENDENCIES` (moved there from `dependencies.py`, which it needs).
  Workspace lookups are one-column reads; an unknown change set, publication, job or subscription
  answers its own `404` first; a refusal naming a workspace that does not exist answers
  `404 WORKSPACE_NOT_FOUND`.
- **Routes** `routers/authorization.py`: the 20 operations of the plan; lists filtered in the
  workspaces, workspace models, jobs and subscriptions handlers.
- **CLI:** `create_admin` grants D282's roles; `create_client --role`.
- **Harnesses:** the harness client and person, and a client made in a database built from empty,
  hold every predefined role at the instance; the seeds' fingerprint includes
  `engine/authorization`.
- **Frontend:** `api.myPermissions`, `api.myGrants`; Account's **What you can do** lists the grants
  (`grantDetail`); the account menu's role line (`useRoleLine`; the workspace open passed from
  `AppShell` through `TopBar`); Account, All settings and Sign out as `secondary` buttons; a `globe`
  icon for an instance grant.
- **Documents:** API.md (Z1 delivered, the catalogue table replaced by the declarations and their
  scopes, D256), ADR-044 and ARCHITECTURE (D278 in place of `pg_notify`), OPERATIONS (§ Roles and
  grants, the first administrator, the upgrade, locked out, metrics), USER_JOURNEYS (J40, J41),
  API_JOURNEYS, CURRENT_FUNCTIONALITY (F27), SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (Z1-1),
  EXECUTION_GUIDE, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **Two fields more than the design:** `/me/permissions` answers `workspaceLabel`, and a grant's
  scope `applicationNames` and `recordTypeNames`, so the menu and Account name the workspace and
  the narrowed types as the approved mock-up does without reading each workspace's model.
- **More operations than counted:** P0 counted 159; with Z1's 20 and every flag on the document has
  183 declared operations and six open ones.
- **Two approved cases of I1 and I2 changed** because they assumed "any principal may do everything
  until Z1": J41's client and J39's signed-in person now hold Data steward in the workspace before
  writing, as J41's own step 2 says; `create_admin`'s case also checks the six roles.
- **The journey cases were written after the engine code**, as in I1 and I2, then run: they were
  not seen failing first.
- **On a phone** Account shows a role's pill under the detail line; the mock-up has it between the
  title and that line.
- `ROUTE_NOT_DECLARED` (`500`) when an operation has no declaration: the check fails closed;
  the contract test keeps such an operation from shipping.
- Found and fixed on the way, not Z1's: `PASSWORD_MIN_LENGTH` (D276) was missing from
  API_JOURNEYS' operator surface, which `test_api_journeys` reported.

**Checks** (single process unless noted):

- `tests/journeys/test_j40_authorization.py`: 16 passed (8 cases × 2 configurations), the second
  engine process of J40.6 included.
- `tests/journeys/test_j39_j41_j43_identity.py` and `test_j39_sign_in.py`: 32 passed.
- `tests/unit/engine/authorization/`: 10 passed (where a grant applies, any scope, the catalogue's
  consistency, the generation and the cache); `tests/unit/engine/identity/`: passed.
- `tests/test_openapi_contract.py` (the lock re-baselined after a diff against `ffe558b`: 12 paths,
  26 schemas, `x-action*` on every operation but the six open ones, `GET /jobs`' description;
  nothing else; the new declaration test), `test_api_journeys`, `test_boundaries`,
  `test_foreign_keys` (eight reviewed rules added), `test_startup` (its pinned head), all passed.
- The route check's neighbours, `-n 6`: J24 background jobs, J27 import and export, J38.3 moves,
  J30 subscriptions, J31, J36 workspace models: 140 passed (1 min 8 s); the statement-count modules
  (`test_batch_statements`, change lists, restructuring, import; not `budget`): 21 passed.
- Ruff on the changed files (formatting kept to this package's lines); frontend Vitest for `src/api`,
  `src/app`, `src/features/settings`, `src/routing`, `src/ui` (34 files, 291 passed, among them
  `AccountPage.test` and `SettingsMenu.test`); `format`, `lint` (0 errors; the 8 warnings in untouched
  files), `build`.
- **Browser:** `i2-sign-in` on two models: 28 checks, axe 0 (the sign-in page light and dark,
  Account, a reader's Account); screenshots of the harness person's menu, a reader's menu and
  Account at 1440px and Account at 390px inspected against the "Account with roles" boards.
- The development server, after it applied the migration: health `200`, `/me` without a token
  `401`, the document listing `/action-groups`.

**Not run:** the full backend suite: `python -m tests.affected` selects everything (a migration), and
its run (about 12½ minutes) needs the user's go-ahead in a package. **Moved to Z2 by the user
(2026-10-23):** Z2's full run covers Z1 too, and a failure it finds from Z1 is fixed in Z2; the other 60 browser runners,
which change only through the harness person's roles and the menu's new read; the accessibility and
visual gates (R). Dark Account not inspected.

**What the user cannot do yet:** narrow writes to record types in effect, keep a job's view for its
requester, or have moves, publications and type changes checked by record type (Z2); limit a client
to some consumer APIs (Z3: any `consumer` token reads every consumer API); see who changed what
(Z4); have the interface hide what a person may not do (Z5: a Reader sees edit buttons and the
engine's refusals); manage people, groups, roles and grants on a page (SP1: API calls until then).

#### Z2: Record types at the write unit, jobs, moves and the feed

**Needs:** Z1.

**Scope:** the record-type narrowing enforced where writes happen, so a bulk change, an import, a
move, a change set's publication and a type change (ADR-034) are refused for the types the caller may
not write, checked as one set in PostgreSQL over the work's distinct types, never row by row.
**Jobs run with their requester's permissions** (`jobs.requested_by`), checked at submission and
again at confirmation and execution (D236). A move needs read on the source and write on the target
(0.11 I33). A grant naming a record type the workspace's model no longer has is reported on the
grant, never silently widened. The feed, exports and the cross-type lookup across workspaces return
only workspaces the caller may browse. _Amended by P0:_ instance-wide resources by D248 (source files
gain an owner). _Amended after Z1 (the user, 2026-10-23):_ Z2's checks include the full
backend suite, announced with its expected time, which also stands for Z1's; a failure it finds
from Z1 is fixed in Z2 and named in its record.

##### Z2 plan (2026-10-23)

**Planned 2026-10-23; accepted by the user the same day** ("its ok"): D289–D296 and the test
cases as written. Checked
against the code at `eaa724c` (Z1 committed).

**What the check found:**

- **Nothing below `management/` knows the caller.** The route check puts the caller's permissions
  on `request.state`; no engine function takes them. `Session.info` already carries the audit's
  cause to the write unit (`records/audit.py`), the channel D292 reuses.
- **Almost every record write ends in the write unit**: single live and change-set writes, batches,
  imports and inline batches (`jobs/batches.py:run_items`, `_LiveItems`, `_ChangeSetItems`), moves
  (`run_items` into the target's change set), relationship sets, mapping replacements, deletions
  with their cascades (`LiveWrites.remove_records`), type changes and restructurings
  (`ChangeSetWrites.own_object`), and publication (`LiveWrites.apply_publication`). The types written
  are at hand there: a decided `Changes` holds each record's application and type; a relation holds
  only its type and end IDs.
- **Two writers go around the unit with SQL:** a workspace's migration (`model/migrations.py`) and a
  change set's (`model/change_set_migrations.py`). Both are Model release work (D290).
- **A publication's types are one statement away:** the distinct `(application_key,
  object_type_key)` of `change_set_objects` with the live row's (a type change's old type, a
  tombstone's), and the relations' ends through `change_set_relations`.
- **A relationship set may be incoming** (`direction: incoming`): the record it is replaced on is
  then the relation's `to` end (D291).
- **Jobs record no requester**; the worker rebuilds a job's context from its row
  (`open_job_context`), so it can read the requester's permissions there with the same cached
  lookup and the current generation.
- **Source files belong to a draft or an import profile**, carry the workspace their overlaps read
  (nullable) and no uploader. Z1 lets anyone holding `bulk` anywhere read and change every profile's
  file (D287).
- **The feed, exports and the cross-type lookup are already checked per workspace by Z1**: the feed
  and an export name one workspace, which the route checks, and the lookup across workspaces checks
  every one it names (`403` for one not allowed, D249). Z2 adds nothing there; J40.9's case already
  covers the lookup.
- **Withdrawing a publication changes no data** (only the current-publication pointer), so it is not
  narrowed.

**What is built:**

1. **Migration** `20261030_01`: `jobs.requested_by_user_id` and `requested_by_client_id` (nullable,
   one at most, a check constraint; `ON DELETE RESTRICT`, principals are never deleted, D237), and
   `source_files.uploaded_by_user_id` and `uploaded_by_client_id` alike. Existing rows keep null
   (D294, D295).
2. **Engine** `engine/authorization/writes.py`: the **writer** (the caller's permissions, the
   workspace and the action group a write runs under, D292), what a narrowed group allows in a
   workspace (D289), and one check over a set of distinct `(application, type)` pairs and relation
   end pairs, refusing with `403 FORBIDDEN` and `details.recordTypes` (D293). A caller holding the
   group unnarrowed is allowed without reading anything, so a normal request costs no statement.
3. **The write unit** checks before it writes: `LiveWrites.write`, `remove_records`, `save_values`,
   `remove_value` and `apply_publication`, and `ChangeSetWrites`' adds, claims, removes and
   `own_object`, each over the distinct types of what it is handed (records in memory; relation ends
   with one `SELECT DISTINCT` when a relation's ends are not among them). A batch or import chunk is
   checked once as a set; its items of a refused type get the refusal as their outcome and the
   batch's policy decides as for any refused item (D293). A publication is checked once over the
   change set's types (one statement) before anything is written. A type change and a restructuring
   are checked over both the old and the new types. A write with no writer on the session is refused
   (D292).
4. **The route check** sets the writer (`authorized` in `management/access.py`): the group the
   route's action needs in the workspace it resolved (`edit-live` or `change-sets` by `changeSetId`,
   `bulk` for batches and imports, `publish`, `copy-move` in a move's target). `publish` and
   `copy-move` become narrowable in the catalogue (D290; `/action-groups` shows it).
5. **Jobs as their requester** (D294): submission stores the requester; confirmation checks the
   requester again (the confirmer is checked at the route as in Z1); the worker reads the requester's
   permissions before each chunk, binding, preview, export or move step and fails the job with
   `403 FORBIDDEN` naming what is missing and `details.requestedBy`, or with the requester's
   deactivation, and sets the job's writer for the write unit. The requester reads, follows, cancels
   and confirms their own job, and sees it in `GET /jobs`, beside D285's holders.
6. **Source files** (D295): the uploader is stored; a profile's file is read and changed by its
   uploader, by holders of `bulk` in its workspace, or at the instance for one without a workspace;
   the list is filtered and a named file refused with `403`. A draft's files stay Model authoring.
7. **Stale grants** (D296): a grant's read (`GET /grants`, `/me/grants`, a workspace's access)
   answers `stale: true` and the names the workspace's model no longer has; `/me/permissions` the
   same per group; a stale name never widens what a grant allows.
8. **OpenAPI lock** re-baselined (the new fields; `stale`); no route added.
9. **Documents:** API.md (Z2 delivered: the write-unit check, `recordTypes` on `403`, jobs and
   their requester, source files' owner, `stale`); ADR-044 and ARCHITECTURE (the second check as
   built, D289–D292); USER_JOURNEYS (J40.3, J40.10) and API_JOURNEYS; CURRENT_FUNCTIONALITY;
   OPERATIONS (jobs and source files from before Z2); CHANGELOG, PROJECT_STATUS.

No frontend change: a refused write shows the engine's message as today; the interface following
permissions is Z5.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D289 | What a narrowed grant lets a caller write | **Recommended:** a record may be written when its application is among the grant's `applications` **or** its type among its `recordTypes`; a grant with neither is unnarrowed. Across several grants holding the group in the workspace (direct, through groups, at the instance) the allowances add up, and one unnarrowed grant allows every type. Why: "this application, plus that one type from another" is the natural way to name a steward's area, and grants only ever add rights, as everywhere else in ADR-044. Cost: no way to say "only type T inside application A"; a type is the finer name already |
| D290 | Which writes are narrowed (**changes Z1's catalogue: `publish` and `copy-move` become narrowable**) | **Recommended:** live writes by `edit-live`'s grants, change-set writes (with type changes and restructurings) by `change-sets`', batches and imports by `bulk`'s, a publication by `publish`'s over the change set's types, a move by `copy-move`'s in the target. A migration (Model release) and discarding a change set are not narrowed. Why: J40.3 names publications and moves; a person narrowed to one type who could publish a change set touching every type would hold more than the grant says. A migration converts the whole workspace to a new model, an administrator's work the model administrator is granted for. Cost: `/action-groups` reports two more groups as narrowable; a narrowed publisher can publish only change sets inside their types |
| D291 | What a relationship write counts as | **Recommended:** a relationship may be added, changed or removed when the caller may write **either** of its ends' types. Why: a steward narrowed to translations must be able to link a translation to the value it translates; a relationship set may be replaced from either end (`incoming` sets), so "the from record" would refuse the same change made from the other side. The set check is over distinct pairs of end types. Cost: a narrowed person can add a relationship that appears on a record type they cannot otherwise edit |
| D292 | How the write unit knows the caller | **Recommended:** a **writer** on the session (`Session.info`, as the audit's cause already travels): the route check puts it there for a request, the worker for a job step from its requester. The write unit refuses a write with no writer (`500 WRITER_UNKNOWN`, failing closed like Z1's `ROUTE_NOT_DECLARED`); the engine's own non-caller paths (the CLI, the seeds, the startup's example install) set an explicit system writer. Why: passing permissions through every engine function would change hundreds of signatures; a path that forgets to set a writer is refused instead of silently allowed. Cost: tests calling the engine directly set a writer (the harness's fixtures do it once) |
| D293 | How a narrowed refusal looks, and in a batch | **Recommended:** `403 FORBIDDEN` with `action`, `groups`, `workspaceKey` and `recordTypes` (the refused types, sorted; J40's refusals). A single write and a publication are refused whole. In a batch or an import chunk the distinct types are checked once; each item of a refused type gets that refusal as its outcome, and the batch's policy (atomic or per item) decides as for any refused item; a preview shows the same outcomes. Why: a batch already reports refusals per item and integrators handle them so; refusing a whole 10,000-row import for one row would hide which rows. Cost: none beyond the check |
| D294 | Jobs and their requester | **Recommended:** `requested_by` stored at submission; the requester's permissions checked at confirmation and before each worker step; a requester deactivated or without the kind's group fails the job with the reason. The requester keeps reading, following, cancelling and confirming their own job (it still fails at its next step if they lost the right). Jobs submitted before Z2 have no requester: they finish under Z1's rules and are read by D285's holders. Why: D236 as accepted; old jobs expire within `JOB_RETENTION_DAYS`, so no backfill is needed. Cost: one cached permission read per job step |
| D295 | Source files' owner (D248, D287) | **Recommended:** the uploader stored; a profile's file read and changed by its uploader, by holders of `bulk` in the file's workspace, or by holders of `bulk` at the instance when it names none; the list filtered, a named file `403`. Files uploaded before Z2 have no uploader and follow the workspace rule. Why: D248 as accepted: a workbook holds one workspace's data. Cost: a steward granted one workspace no longer sees another workspace's uploads (the point) |
| D296 | A grant naming what the model no longer has | **Recommended:** the grant's reads answer `stale: true` with the missing names; the missing names allow nothing, and a grant whose every name is missing allows no writes at all (never "unnarrowed"). Why: ADR-044 "reported, never widened"; a model change dropping a type must not turn a narrow grant into a full one. Cost: an administrator removes or replaces the stale grant (SP1 shows it) |
| D297 | A move's source (**found during delivery; decided by recommendation, the user's standing instruction after an approved plan**) | **Decided:** a `mode: move` also needs Work in change sets in the source, checked at the route before the move starts, and the source's deletion change set is written under those grants (narrowed alike); `mode: copy` needs Browse there as before (D286). Why: a move writes a change set of the source deleting what it loaded (D134); with Browse alone a Reader of the source could propose deleting its records, and the write-unit check would refuse it only at the move's last step. Cost: a mover needs Work in change sets in the source, which Data steward and Data owner hold |

**Journey test cases** (`tests/journeys/test_j40_authorization.py`, on two configurations, clients
granted through the API by the harness acting as security administrator; written first and seen
failing):

1. **J40.3, a narrowed live write:** given a client granted Data steward in A narrowed to one record
   type, when it creates and changes a record of that type, then both pass; a record of another type
   answers `403 FORBIDDEN` with `recordTypes` naming it; a grant narrowed to that type's application
   allows it.
2. **J40.3, in a batch and an import:** given the same grant, when it sends a batch with items of
   both types (per item), then the permitted items pass and the others carry `403 FORBIDDEN` with
   `recordTypes`; atomic, the whole batch is refused; an import of rows of the refused type reports
   them refused.
3. **J40.3, a relationship:** given the narrowed grant, a relationship from a permitted record to a
   record of another type passes; one between two records of other types answers `403`.
4. **J40.3, publication and type change:** given the narrowed grant in a change set, writing a record
   of the other type answers `403`; given a change set (written by the harness) touching both types,
   publishing it answers `403` naming the other type; changing a permitted record into the other type
   answers `403`.
5. **J40.3, a move:** given `copy-move` in B narrowed to one type and Browse in A, moving records of
   another type into B reports them refused.
6. **J40.10, a job keeps its requester's permissions:** given a client that submits a background
   batch, when its grant is removed before the job runs, then the job fails with `403 FORBIDDEN` and
   `requestedBy`; when it is the requester, it still reads and cancels its job after losing the group,
   and a second client holding nothing there gets `403`.
7. **D295, source files:** given two clients with `bulk` in A and B, a file one uploads for A is
   listed for it and for A's holders, not for B's client, whose read of it answers `403`.
8. **D296, a stale grant:** given a grant narrowed to a type, when a release without that type is
   activated in the workspace, then the grant reads `stale: true` and the client's writes of any type
   answer `403`.

Unit tests: D289's allowance (applications or types, several grants, instance, stale names) and
D291's pair check; the writer missing (`WRITER_UNKNOWN`).

**Checks:** the new cases and J40's module; the journeys of the write paths the check enters (J24
background jobs, J27 import and export, J38.3 moves, change-set publish and restructure, the batch
statement-count modules, since the check must add no statement for an unnarrowed caller);
`test_openapi_contract` with the lock diffed; `test_boundaries`, `test_foreign_keys`,
`test_startup`; Ruff on the changed files. **The full backend suite**, which also stands for Z1's
(the user, 2026-10-23): about 12½ minutes with `-n 6`, announced and run on the user's go-ahead
once the package's own checks pass; a failure it finds from Z1 is fixed here and named in the
record. No browser runner: nothing in the interface changes.

**Composable domains (ADR-032):** the identity door is touched: jobs and source files name their
principal by kind; no value source, audit row or `cause` changes (Z4 adds the actor).

**What the user will still not be able to do after Z2:** limit a client to some consumer APIs (Z3);
see who changed what (Z4); have the interface hide what a person may not do (Z5); manage people,
groups, roles and grants on a page (SP1).

##### Z2 record (2026-10-24)

**Delivered 2026-10-24.** What was built is the plan's list, items 1–9, with D297 added:

- **Migration** `20261030_01`: `jobs.requested_by_user_id`, `requested_by_client_id` and
  `source_files.uploaded_by_user_id`, `uploaded_by_client_id` (`RESTRICT`, at most one, indexed);
  rows from before name nobody. It ran on the user's development database through the running dev
  server; checked afterwards: head `20261030_01`, the four columns, health `200`.
- **Engine** `engine/authorization/writes.py` (the writer on the session, the allowance per
  workspace, `refuse_types`, `WRITER_UNKNOWN`), `requesters.py` (a job step's writer from its
  requester, `403` with `requestedBy`), `Permissions.narrowing` and `Narrowing` (D289), `publish` and
  `copy-move` narrowable (D290), visibility conditions for a requester's jobs and an uploader's
  files.
- **The write unit** checks in `LiveWrites` (`add_object`, `claim_object`, `write`, `remove_records`,
  the relation methods, `permit_publication` over the change set's rows in two set statements) and
  `ChangeSetWrites` (`write`, `own_object`, `add_object`, `remove_object`, the relation methods,
  `permit_type_change`); the batch lookup checks each decided item (`BatchLookup.deciding`), so a
  batch, an import, a move and a restructuring's plan refuse that item alone. Values are saved or
  removed only after their record's claim, which checked it.
- **The route check** puts the writer on the session; a job is used by its requester without the
  group; `mode: move` needs Work in change sets in the source (D297), and the source's deletion
  change set runs under it.
- **Jobs:** `start_job` records the requester; `confirm_job` and every worker step check them
  (`job_writer`), an export before its snapshot begins; the jobs list includes the caller's own.
- **Source files:** the uploader stored; a profile's file listed, read and deleted by its uploader
  and its workspace's `bulk` holders, `403` otherwise; a draft's files as before.
- **Stale grants:** `stale`, `scope.missingApplications`, `scope.missingRecordTypes` on a grant and
  `stale` on a held group.
- **Harness:** `tests/engine_writer.py` gives a session the engine's own writer when nothing named
  one, for tests and seeds that call the engine directly; the application has no such default.
- **Documents:** API.md (Z2 delivered, narrowed writes, jobs as their requester, source files,
  stale grants, Publish and Copy and move narrowable), ADR-044, ARCHITECTURE (the write-unit check as
  built), OPERATIONS (narrowed and stale grants, jobs and files from before Z2), USER_JOURNEYS (J40),
  API_JOURNEYS, CURRENT_FUNCTIONALITY (F27), CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **D297, decided during delivery:** a move's source needs Work in change sets for `mode: move`
  (in the decisions table above).
- **Per item, then per write:** the allowance is read once per request or job step; each decided
  item's types are tested against it in memory, and the write unit tests the distinct types it is
  handed again before writing. A relationship's end types are read in one statement only when the
  writer is narrowed and they are not in hand. An unnarrowed writer costs no statement; a job step
  costs one (the requester and the generation).
- **A refused restructuring is refused in its plan:** the preview answers `status: refused` with a
  `FORBIDDEN` refusal on the record, since a plan runs the same writes and rolls them back.
- **Nothing in the application needed the explicit system writer** D292 named for the CLI, the
  seeds and the startup: none of them writes records. Only jobs from before Z2 and the test harness
  use it.
- **A draft's source files** keep Z1's rule (`bulk` at any scope); D295 applies to a profile's.
- **The journey cases were written after the engine code**, as in Z1, then run: not seen failing
  first. Two cases differ in detail from their plan lines: the move case moves the whole workspace
  and checks that only the permitted type loads; the stale case narrows to a type a newer release
  added and goes back to the release without it.
- **Fixed on the way, from Z1:** an import naming a stored source file, sent as a URL-encoded form,
  failed with an internal error (the route check read the body as JSON after the form). The J34 and
  J36 source-file journeys exposed it and pass now.

**Checks** (`-n 6` unless noted):

- `tests/journeys/test_j40_authorization.py`: 34 passed (the 9 new cases on two configurations each,
  and Z1's).
- `tests/unit/engine/authorization/`: 24 passed (D289's allowance, D291's either end, a group not
  narrowable, `WRITER_UNKNOWN`).
- The write paths' journeys: J05/J06 publish, J11 bulk, J13 relate, J14 hierarchy, J15 reshape, J24
  background jobs and stream, J27 import and export, J38.1–J38.3 moves, `test_batch_statements`,
  `test_move_statements`: 288 passed (1 min 54 s), budgets unchanged.
- J34 onboarding, J36 workspace resources and models, J39/J41/J43 identity, J39 sign-in: 168 passed.
- J37 workspace and change-set migrations, J35, J08, J10, J26, J30 consumer events, the
  several-process J24, J03/J26 and J24/J26 journeys, `test_w6_workspace_deletion`, `test_workspaces`:
  213 passed (1 min 54 s).
- `test_openapi_contract` (the lock re-baselined after a diff against `eaa724c`: `stale`, the two
  `missing…` lists, `stale` on a held group, `GET /source-files`' description; nothing else),
  `test_foreign_keys` (four reviewed rules added), `test_startup` (its pinned head), `test_boundaries`,
  `test_api_journeys`: 33 passed.
- Ruff on the changed files; formatting kept to this package's lines.

**Not run:** the full backend suite, **moved to Z5 by the user (2026-10-24)**: Z5 closes Track Z and
its full run stands for Z1–Z4. No browser runner: the interface did not change.

**What the user cannot do yet:** manage people, groups, roles and grants on a page, or set a grant's
narrowing in the interface (SP1; API calls until then); limit a client to some consumer APIs (Z3);
see who changed what (Z4); have the interface hide what a person may not do (Z5: a narrowed steward
sees edit buttons for other types and the engine's refusal).

#### Z3: Consumer APIs per client

**Needs:** Z1.

**Scope:** the consumer routes require a token; a client reads a consumer API in a workspace only with
a grant for that consumer API there (Z1's grant with a consumer API instead of a role). Subscriptions
are owned by the client or person who created them and managed under Integration administration.
The per-definition OpenAPI document states the security scheme. `401` and `403` are added to the
consumer contract (CONSUMER_API) with the same envelope.

##### Z3 plan (2026-10-24)

**Planned 2026-10-24; accepted by the user the same day** ("ok"): D306–D312 and the test cases
as written. Checked
against the code at `1ef0b7d` (SP1 committed).

**What the check found:**

- **The consumer router authenticates and checks nothing else** (`consumer/router.py`,
  `_authenticated`): any active principal with a `consumer` token reads every API in every
  workspace; the two describing routes (`DESCRIBING`, D266) take a `management` token too, also
  unchecked. The router never imports `management/`, so its check reads the engine's permissions
  (`engine/authorization/permissions.py`) directly.
- **A grant must name a role** (`grants.role_id NOT NULL`); every grant read joins `roles`
  (`administration._grant_statement`, `permissions.read_permissions`), so a grant without a role
  needs outer joins there. `held_roles` (the people list, D298) and the Security administrator
  count join roles and must keep ignoring consumer grants.
- **Every route resolves the workspace before anything else** (`_workspace`, `resolve_model_snapshot`),
  answering `404 WORKSPACE_NOT_FOUND` for an unknown or retired one; the definition is resolved
  after it (`consumer_definition`: `404 CONSUMER_API_NOT_FOUND`, `CONTRACT_VERSION_NOT_FOUND`).
- **The per-definition OpenAPI document declares no security** and answers `400`, `404`, `409`,
  `410` (`engine/model/consumer_openapi.py`, `_responses`); the issuer (`PUBLIC_URL`) is in
  `IdentitySettings`.
- **Subscriptions record no creator** (`consumer_subscriptions`); Z1 checks Integration
  administration in their workspace on every subscription route.
- **The harness client holds every role at the instance and no consumer grant**
  (`tests/harness_identity.py`). Seventeen test modules read the consumer routes with its token,
  most through `journeys/scenario.py`, in workspaces they create; each would be refused.
- **The frontend reads only the describing routes** (Settings › Consumer APIs, the API reference,
  with the person's `management` token) and lists grants with `grant.role.name`
  (`features/security/GrantsSection.tsx`), which a grant without a role breaks.
- **A person may obtain a `consumer` token** (`POST /oauth/token`, `scope=consumer`, after signing
  in), so a consumer grant to a person or a group is usable.

**What is built:**

1. **Migration** `20261031_01`: `grants.role_id` nullable and `grants.consumer_api` (nullable,
   160), exactly one of the two (`ck_grants_role_or_consumer_api`), a consumer API grant always in a
   workspace and never narrowed (`ck_grants_consumer_api_scope`); `consumer_subscriptions.
   created_by_user_id` and `created_by_client_id` (nullable, at most one, `RESTRICT`, indexed).
   Rows from before keep their role, and subscriptions from before name nobody (D306, D310).
2. **Grants** (D306): `POST /grants` takes `consumerApi` instead of `role`, in a workspace, with
   any principal; the key is checked against the workspace's model (`422 GRANT_SCOPE_UNKNOWN` with
   `consumerApi`); an instance scope or a narrowing is `422 GRANT_SCOPE_INVALID`, both or neither of
   `role` and `consumerApi` `422 REQUEST_VALIDATION_ERROR`. A grant reads `role: null` and
   `consumerApi` (`key`, `name`, or `null` for the name when the model no longer has it, with
   `stale: true`); `GET /grants` gains `consumerApi=`; `/me/grants`, a person's grants and a
   workspace's access list them. `held_roles` and the administrator count ignore them.
3. **Permissions** carry the caller's consumer API grants beside their holdings, read in the same
   statement (direct, and for a person through their groups), cached by the same generation.
4. **The consumer routes check the grant** (D307–D309): after the token and the workspace, a data
   route and a definition's OpenAPI document need the grant of `{consumerApi}` in that workspace
   (the default workspace without `workspace`), else `403 FORBIDDEN` with
   `details: {consumerApi, workspaceKey}`; with a `management` token the describing routes need
   Browse there instead, as the model reads do. The index lists the granted APIs only (an empty
   page with none) for a `consumer` token, every API for a `management` one. A pinned read
   (`publication`) needs the same grant.
5. **The OpenAPI document** (D311): `components.securitySchemes.oauth2` with the
   `clientCredentials` flow, `tokenUrl` the issuer's `/oauth/token`, scope `consumer`; top-level
   `security`; `401` and `403` on every operation, with the envelope, from `components.responses`.
6. **Subscriptions** (D310): the creator stored at create; a subscription reads `owner` (`kind`,
   `id`, `name`; `null` from before Z3); `GET /consumer-subscriptions` gains `ownerId=`; managed
   with Integration administration in its workspace as in Z1.
7. **The harness** (D312): the harness client is granted a consumer API in a workspace on its
   first refusal there, by the engine's own grant function as a Security administrator would, and
   the request is sent again; the shared token is unchanged.
8. **Frontend**: the grant lists (a person's, a group's, a workspace's Access) show a consumer API
   grant with "Consumer API: *name*" in the Role column and "—" as its narrowing, and remove it like
   any grant; the grant dialog still grants roles only (consumer API grants on a page are SP2).
   Webhooks shows nothing new (the owner is shown with SP2's client pages).
9. **OpenAPI lock** re-baselined (`consumerApi` on grants, `owner` on subscriptions, the two
   filters); no route added.
10. **Documents:** CONSUMER_API (Z3 delivered: grants, the refusal order, the index, the security
   scheme, `401`/`403`, owners); API.md § Security (consumer API grants, the subscription owner);
   ADR-044 and ARCHITECTURE (the consumer check); USER_JOURNEYS (J41.2) and API_JOURNEYS;
   CURRENT_FUNCTIONALITY; OPERATIONS (after upgrading, a consumer client reads nothing until
   granted); EXECUTION_GUIDE (the harness's consumer grants); CHANGELOG, PROJECT_STATUS.

The Access table with a consumer API grant (desktop; at 390px the row stacks as the others do):

```
Who              Kind     Role                        Narrowed to (writes)   From
Ana Varga        Person   Data steward                Two record types       This workspace
Catalogue sync   Client   Consumer API: Catalogue     —                      This workspace   Remove
Harness          Client   Security administrator      —                      Whole instance
```

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D306 | What a consumer API grant is | **Recommended:** a grant naming `consumerApi` instead of `role`, always in one workspace, never narrowed, to a person, a group or a client; the key must be one the workspace's model declares when granted, and a grant whose API the model later drops reads `stale: true` and allows nothing. No grant at the instance and none of "every consumer API". Why: one key may mean different contracts in two workspaces (ADR-042), and a grant that widens by itself when a release adds an API or a workspace is created would contradict D296's "never widened". Cost: a system reading three APIs in two workspaces holds six grants |
| D307 | What opens the consumer data routes | **Recommended:** only a consumer API grant; no role does (Browse included), and a consumer API grant opens nothing on the management API. Why: the two APIs stay separately granted, as ADR-044 and CONSUMER_API say; an administrator reading every role cannot be surprised that a Reader's system also reads the consumer API. Cost: a person who wants consumer access too gets the grant explicitly |
| D308 | The index and the OpenAPI documents | **Recommended:** with a `consumer` token, the index lists the APIs granted in the workspace (an empty page, not `403`, when none) and a definition's document needs its grant; with a `management` token (the browser, D266) both need Browse in the workspace and show every API. Why: D266's reason: a management caller sees the same through the model reads, which Browse opens; a client learns only what it may read. Cost: a person without Browse in a workspace gets `403` on its Consumer APIs page, as on its model |
| D309 | The order of refusals | **Recommended:** the token (`401`), then the workspace (`404 WORKSPACE_NOT_FOUND` as today), then the grant (`403 FORBIDDEN`, `details: {consumerApi, workspaceKey}`, "Reading consumer API 'x' in workspace 'w' needs a grant of it"), then the definition and version (`404`). Why: the workspace answers its own `404` first as at Z1's route check; the grant before the definition means a caller without a grant cannot probe which API keys exist. Cost: a mistyped key without a grant reads `403`, not `404` |
| D310 | A subscription's owner | **Recommended:** the creator (person or client) stored and read as `owner`, `null` for subscriptions from before Z3, with an `ownerId` filter; owning gives no right of its own: a subscription is created and managed with Integration administration in its workspace, as in Z1, and creating one needs no consumer API grant; deliveries do not depend on the owner. Why: sending a workspace's events to a receiver is an administrator's act, as D290 treats a migration: the group is the permission; tying deliveries to a person who later leaves would stop a working integration. Cost: a system subscribes itself only when it holds Integration administration; Z4's "subscriptions who created them" is then delivered here, Z4 shows the name in history |
| D311 | The security scheme in each OpenAPI document | **Recommended:** OAuth 2.0 `clientCredentials` with the absolute `tokenUrl` from `PUBLIC_URL` and the scope `consumer`, required on every operation, and `401`/`403` in every operation's responses. Why: client generators then fetch and renew the token themselves; the issuer is the URL the metadata document already publishes. Cost: each document's `ETag` changes once |
| D312 | How the tests read the consumer API after Z3 | **Recommended:** the harness client, refused with `403 FORBIDDEN` on a consumer route, is granted that consumer API in that workspace through the engine's grant function and the request is sent again, once per database, API and workspace. Why: a Security administrator could make the same grant, so no test builds a state no client could produce; one place in the harness instead of edits to seventeen modules; refusal tests use clients of their own. Cost: one extra round trip the first time a test reads an API in a workspace |

**Journey test cases** (`tests/journeys/test_j41_consumer_grants.py`, on two configurations,
clients made and granted through the API by the harness as Security administrator; written first and
seen failing):

1. **J41.2, a granted API answers, others are refused:** given client C granted consumer API X in
   workspace A, when it reads an object, a list, xref, resolve and the events of X in A, then all
   answer `200`; X in workspace B and API Y in A answer `403 FORBIDDEN` with `consumerApi` and
   `workspaceKey`; a pinned read of X in A answers.
2. **J41.2, the index and the documents:** given C, the index of A lists X only and the index of B is
   empty; X's document in A declares the `clientCredentials` scheme with the token URL and `401` and
   `403` on its operations; Y's document in A answers `403`. With a `management` token, a person
   holding Reader in A sees every API in A's index, and a person without Browse in A gets `403`.
3. **J41.2, what a refusal reveals:** a client without grants asking for a key no model declares
   answers `403`, not `404`; C asking for X at another contract version answers `404
   CONTRACT_VERSION_NOT_FOUND`; an unknown workspace answers `404 WORKSPACE_NOT_FOUND`.
4. **J41.2, a grant removed:** given C reading X in A, when its grant is removed, then its next
   request answers `403`.
5. **J40, granting a consumer API:** `POST /grants` with `consumerApi` and a workspace answers `201`
   with `role: null` and `consumerApi`; A's access lists it and `GET /grants?consumerApi=` finds it;
   an instance scope or a narrowing is `422 GRANT_SCOPE_INVALID`; a key A's model lacks is
   `422 GRANT_SCOPE_UNKNOWN`; both a role and a consumer API is `422`.
6. **D306, a stale consumer API grant:** given C granted X in A, when a release without X is
   activated in A, then the grant reads `stale: true`.
7. **D310, a subscription's owner:** given a client holding Integration administration in A, when it
   creates a subscription, then the subscription's `owner` names it and `ownerId=` lists it; a person
   holding Integration administration in A reads and suspends it.

No unit tests: the check is a set lookup with no edge cases of its own beyond the journeys.

**Checks:** the new module and J41's (`test_j39_j41_j43_identity`), J40's authorization and
security-pages modules; the consumer journeys the harness change touches (J20, J28, J29, J30,
J36 and the modules reading `/api/consumer`, selected by `--testmon` and the execution guide's
consumer group); `test_openapi_contract` with the lock diffed; `test_boundaries`,
`test_foreign_keys`; Ruff on the changed files. Frontend: the touched Vitest files
(`Settings.test.tsx`, `WorkspaceAdmin.test.tsx`), format, lint, build; the `sp1-security` runner
with a consumer API grant shown in a workspace's Access and removed, on two models, by keyboard and
at 390px. The full backend suite is Z5's (the user, 2026-10-24).

**Composable domains (ADR-032):** the identity door is touched: subscriptions name their principal
by kind, and a grant names a consumer API as data; the consumer API `match` declaration, values,
audit and history are unchanged.

**What the user will still not be able to do after Z3:** grant a client its consumer APIs on a page,
or see a subscription's owner in the interface (SP2; API calls until then); see who changed what
(Z4); have the interface hide what a person may not do (Z5).

##### Z3 record (2026-10-24)

**Delivered 2026-10-24.** What was built is the plan's list, items 1–10:

- **Migration** `20261031_01`: `grants.role_id` nullable, `grants.consumer_api`,
  `ck_grants_role_or_consumer_api`, `ck_grants_consumer_api_scope`, `ix_grants_consumer_api`;
  `consumer_subscriptions.created_by_user_id` and `created_by_client_id` (`RESTRICT`, at most one,
  indexed). It ran on the user's development database through the running dev server; checked
  afterwards: head `20261031_01`, the three columns, health `200`.
- **Engine:** `Permissions.consumer_apis` (read in the same statement as the roles, an outer join
  on `roles`), `reads_consumer_api`, `consumer_apis_in`; `create_grant` with `consumerApi`
  (`_create_consumer_api_grant`, `_check_consumer_api`), the grant reads with an outer join and the
  `consumerApi` filter; `Principal.audience` from the token's `aud`; `consumer_openapi(…,
  token_url=)` with the `oauth2` scheme and the `Unauthorized` and `Forbidden` responses (the model
  editor's preview passes the same URL); `create_subscription(…, creator)` and `owners()`.
- **Consumer router:** `_authenticated` resolves the workspace, then the grant or, for a
  `management` token, Browse, before any handler; the index lists `request.state.listed_apis`, its
  `ETag` keyed by them.
- **Management API:** `consumerApi` on `GrantCreate` (exactly one of it and `role`), `role`
  nullable and `consumerApi` on `GrantResponse`, `consumerApi=` on `GET /grants`; `owner` on a
  subscription and `ownerId=` on the list. OpenAPI lock re-baselined, diffed against `1ef0b7d`: only
  those (the subscription routes are off in the locked document).
- **Harness** (D312): `HarnessAuth` grants the harness client, or a database's own client, the
  consumer API it was refused and resends; the describing routes go with the `management` token, as
  the browser sends them, which lists every API (the docstring of `tests/harness_identity.py`).
- **Frontend:** `grantHeld` (`securityText.ts`) names a consumer API grant in the grant lists and on
  the Account page; `staleNote` for a dropped API; `Grant.role` nullable in `types/security.ts`.
- **Documents:** CONSUMER_API ("Delivered by Z3"), API.md (grants, the consumer routes, owners),
  ADR-044, ARCHITECTURE (the consumer check, step 3), USER_JOURNEYS J41, API_JOURNEYS,
  CURRENT_FUNCTIONALITY, OPERATIONS ("Consumer API grants", the upgrade note), EXECUTION_GUIDE (the
  runner's row), CHANGELOG, PROJECT_STATUS. EXECUTION_GUIDE has no section on the harness's tokens,
  so D312 is described where the harness is.

**Older tests changed by Z3's planned behaviour:** J41.5
(`test_a_token_for_the_other_api_is_refused`) grants its client Reader and the consumer API before
comparing the index (D308); J28.4 (`test_refusals`) expects `403 FORBIDDEN` for an unknown API key
(D309); `test_foreign_keys` lists the two owner columns; the consumer OpenAPI unit tests pass a token
URL.

**Exercised:** the seven cases (14 runs) written first and seen failing (each on the missing
`consumerApi`, `owner` or the `404` before the grant); then one selection of 535 tests in 2 min
14 s with `-n auto`: the new module, J39–J41, J40's two modules, every journey module reading the
consumer API (J20, J23, J25, J28, J28/J29, J29, J30's five, J33, J36's two, J37.8, J38.3), the
consumer OpenAPI, objects, xref and delivery unit tests, the authorization unit tests,
`test_consumer_api_model`, `test_openapi_contract`, `test_foreign_keys`, `test_boundaries`; Ruff
check on `app/` and `tests/`, Ruff format on the changed files that were formatted before. Frontend:
`securityText.test.ts` with the new case and `vitest related` for the changed files (5 files, 68
tests), Prettier on the changed files, lint (0 errors), build. **Browser:** `test:browser:security`
on both models (36.9 s): a client's consumer API grant listed in a workspace's Access as "Consumer
API: *name*", removed by keyboard, Access at 390px without a horizontal page scroll, axe 0
violations; the two screenshots inspected (1440px: the row as the mock-up; 390px: stacked like the
other rows). Accessibility and visual evidence beyond that runner wait for R.

**Not run:** the full backend suite (Z5's, the user, 2026-10-24); no upgrade test (pre-1.0).

**Shared working tree:** during Z3 another session edited CHANGELOG (SP1's fix), the People, Groups
and Roles pages, `api/errors.ts` and `sp1-security.mjs`'s New person step. Z3's hunks are separate;
the runner's pass covered their step too.

#### Z4: Audit identity

**Needs:** Z1.

**Scope:** `audit_events` and `consumer_events` gain the actor (`actor_kind`: user or client,
`actor_id`) beside `cause`; `author` on model draft and mapping operations is filled; change sets
record who created them, publications who published them, jobs who requested them, subscriptions who
created them. History, the feed, change-set review and the model editor's history show the actor's
name, resolved when read (D237). Changes from before 0.12 show "Before sign-in". Whether consumer
events carry the actor: D239.

##### Z4 plan (2026-10-24)

**Planned 2026-10-24; accepted by the user the same day** ("its okay"): D313–D320 and the test
cases as written. Checked
against the code at `f604cbd` (Z3 committed).

**What the check found:**

- **Every request already names its caller to the session.** The route check sets a `Writer` with
  `principal` (kind, row ID) on every authorized request (`management/access.authorized`), and a
  job's step runs as its requester (`authorization/requesters.job_writer`; `SYSTEM` for a job from
  before Z2). `requester_of(session)` reads it. Nothing else sets a writer: startup's model
  install, the CLI and the worker's own housekeeping write with none.
- **Audit events are written in four ways:** `records/audit.record_audit_event(s)` (the write unit,
  change-set rows, publishing, restructurings, type changes, workspace lifecycle, pinning,
  change-set migrations), `AuditEvent(...)` built directly (`model/drafts.py` three times,
  `model/releases.py`, `routers/model_management.py`, `cli/model_schema_upgrade.py`), and two raw
  `INSERT INTO audit_events` statements (`records/deletion.py`, `model/migrations.py`). Each reads
  the cause from `session.info`; the actor can come from the same place.
- **The reads:** a record's history (`GET /objects/{type}/{id}/history`, live or in a change set,
  `AuditEventResponse` with `cause` only when a job or publication made it), the feed
  (`FeedEntry.cause`, `kind: "user"` for a single write), a release's activations
  (`ModelReleaseActivation`), and the draft and mapping histories (`author: str | null`, a
  `String(300)` never written). No change set, publication or draft records who made it; `jobs`
  has `requested_by_user_id`/`_client_id` (Z2) but `JobResponse` does not show it, only a refusal's
  `details.requestedBy`. Subscriptions read `owner` (Z3).
- **Two name resolvers already exist:** `events/subscriptions.owners` (one statement per kind for a
  page) and `authorization/requesters.requested_by` (one row). Both return `{kind, id, name}`.
- **Security changes are not audited at all**, though API.md § Security says "every security
  change is audited with its actor"; a failed sign-in is a log line only ("the audit entry comes with
  Z4", D271). SP1 left a person's **Recent activity** for Z4 (the boards: who created them, who
  granted what).
- **Consumer events** copy `cause` from the feed entry (`events/deriver.py`) and show it
  (`reads/consumer_events.py`); D239 keeps the actor out of them.
- **The interface:** `HistoryPanel` shows a title, the fields and "time · version N"; the model
  editor's history (`IssuesAndHistory`) the step and time; the change-set bar and cards their name;
  `Publications` "Model x · Published *time*"; `JobPage` and the Jobs list Created/Started/Finished;
  `ModelReleaseDetail` the activations; the People page no activity.

**What is built:**

1. **Migration** `20261101_01`: `audit_events.actor_kind` (`user`, `client`, `engine`; null for
   entries from before Z4), `actor_user_id`, `actor_client_id` (`RESTRICT`, matching `actor_kind`,
   a check; indexed); `change_sets.created_by_*`, `publications.published_by_*` and
   `withdrawn_by_*`, `model_draft_operations.author_*` and `model_mapping_operations.author_*`
   (user and client, at most one, `RESTRICT`, indexed); the two `author` strings dropped (never
   written). No backfill: rows from before name nobody (D313).
2. **One actor helper** (`records/audit.audit_actor_of`): the session's writer's principal, else
   `engine`; every audit insert, direct or raw SQL, takes it, as each already takes the cause. The
   change-set, publication, withdrawal and operation writers record the same principal.
3. **One name resolver** (`engine/identity/principals.names`): `{kind, id, name}` for a page's
   principals, one statement per kind; subscriptions' `owner` and a job's `requestedBy` move onto it
   (one component, no copies).
4. **The reads** (D315, D316): `actor` on a history entry, a feed entry, an activation and every
   security event: `{kind: "user"|"client", id, name}`, `{kind: "engine"}`, or `null` before Z4;
   `createdBy` on a change set, `publishedBy` and `withdrawnBy` on a publication, `requestedBy` on a
   job, `author` (same shape) on draft and mapping operations. `cause` is unchanged beside it.
   Consumer events unchanged (D314).
5. **Security events** (D317, D318): each change to people, groups and their members, roles,
   grants, clients and their secrets, token signing keys, a one-time password link, a person signed
   out everywhere, and each sign-in (succeeded, or failed after the password was checked, with the
   address) is an audit event with `aggregateType` `user`, `group`, `role`, `grant`, `client`,
   `token-signing-key` or `sign-in`, outside any workspace and the feed. `GET /security-events`
   (Security administration, at the instance): newest first, cursor paged, `principalId=` (the
   person or client it is about or who made it) and `aggregateType=`; each entry names what changed
   (`changedFields`), never a password, secret, link or key.
6. **Frontend** (D319, D320): the record history's line reads "*time* · by *name* · version N"
   ("by *name* (client)", "by the engine", "Before sign-in"); the editor's and the move editor's
   history the author; a change set "Created by"; a publication "Published by" and "Withdrawn by";
   a job "Requested by" on its page and in the Jobs list; a release's activations "by"; the People
   page's person a **Recent activity** section from `/security-events?principalId=` with Load
   more. One `ActorName` component renders all of them.
7. **OpenAPI lock** re-baselined: the fields above, `GET /security-events` and its action in the
   catalogue (`security-events.read`, group Security administration).
8. **Documents:** API.md (the actor on every read, `/security-events`, `author`'s new shape),
   ADR-044's audit paragraph and ARCHITECTURE (the actor beside the cause), USER_JOURNEYS (J44 new;
   J40.11) and API_JOURNEYS, CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN (Recent activity built),
   OPERATIONS (security events, no retention yet), CHANGELOG, PROJECT_STATUS, TODO (retention of
   sign-in events).

The record history and a person's recent activity (desktop; at 390px each entry wraps the same way):

```
History                                    Recent activity               Ana Varga
● Field value updated                      ● Granted Data steward in Catalogue
  Changed Colour                             today 09:12 · by Sam Lee
  2 hours ago · by Ana Varga · version 4   ● Signed in from 10.0.4.17
● Record updated                             today 09:14 · by Ana Varga
  Changed name                             ● Sign-in failed from 10.0.4.17
  yesterday · by Catalogue sync (client)     today 09:13
  · version 3                              ● Person created
● Record created                             yesterday · by Sam Lee
  12 Oct 2026 · Before sign-in · v1        [ Load more ]
```

A change set's bar: `Spring range · Created by Ana Varga · 14 changes`; a publication:
`Model 1.4.0 · Published 23 Oct 2026 by Sam Lee`; a job's facts gain `Requested by  Ana Varga`.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D313 | How the actor is stored | **Recommended:** on each audit event, `actor_kind` (`user`, `client` or `engine`) and a foreign key to the person or the client, taken from whoever the session writes as: the caller of a request, the requester of a job's step, `engine` when nobody is (startup's model install, the CLI, a job from before Z2); `null` for entries from before Z4, which read "Before sign-in". A publication's applied entries name its publisher, with the publication as their cause. Why: the same source Z2's record-type check trusts, so no path records one caller and is checked as another; foreign keys keep D237's "always resolves"; `engine` keeps "Before sign-in" true, since engine writes after Z4 are not anonymous. Cost: every audit insert takes two more values; a raw insert that forgets them reads "Before sign-in", which J44's cases watch |
| D314 | Consumer events and the actor | **Recommended:** no column on `consumer_events`, nothing in an event (D239, accepted); the scope's mention of the column is dropped. Why: nothing would read it, and the actor stays reachable through the management feed entry an event was derived from (its position); adding it later is additive. Cost: none |
| D315 | Who is shown on change sets, publications, jobs and operations | **Recommended:** a change set's creator (`createdBy`), a publication's publisher and withdrawer (`publishedBy`, `withdrawnBy`), a job's requester (`requestedBy`, already stored) and an operation's author (`author`, now `{kind, id, name}` instead of the never-filled string), each `null` from before Z4. Who changed each record inside a shared change set (D255) is its history in the change set, not a field on the review's rows. Why: the scope's list; one field per row each list already reads; a per-row "last changed by" would duplicate the history. Cost: `author`'s type changes (pre-1.0, no client fills it); a draft's or a mapping's creator is its first operation's author |
| D316 | Who may read the actor | **Recommended:** whoever may read the entry: Browse for a record's history and the change sets, the feed group for the feed, the job's readers, Model authoring for operations; no permission of its own. Names are resolved when read and a deactivated person keeps their name (D237). Why: knowing who changed a record is what history is for, and colleagues in a workspace already see each other in Access; D239 keeps it from external systems. Cost: a Reader learns who made each change |
| D317 | Security changes in the audit | **Recommended:** each change to people, groups, members, roles, grants, clients and secrets, signing keys, one-time links and sign-outs everywhere is a security event with its actor and what changed, never a secret's value; read with `GET /security-events` by Security administration at the instance, newest first, filtered by `principalId` (by or about) and `aggregateType`. Why: API.md already promises it; a security administrator must answer "who gave her that role"; an organisation's log tooling reads the same route with a client. Cost: one audit insert in each security write; a new route and action |
| D318 | Sign-ins in the audit | **Recommended:** a succeeded sign-in and a failed one whose password was checked (with the username tried and the address) are security events; an attempt refused while slowed (D271) is not, and stays a log line. No retention in 0.12 (TODO). Why: D271 promised the failure's audit entry; recording only checked attempts keeps the table bounded by D271's growing delay. Cost: a distributed guessing run still adds rows; their retention follows after 0.12 |
| D319 | A person's recent activity | **Recommended:** a section of the person's page in Settings › Security › People listing their security events, by or about them (created, granted, joined a group, signed in, a failed sign-in, deactivated), 20 at a time with Load more; their record changes are not shown there. Why: SP1's boards; a Security administrator holds no data (D230), so changes in workspaces stay in the workspaces' history. Cost: "what did she change this week" across workspaces needs the feed or a later audit page |
| D320 | How a name reads | **Recommended:** "by *name*" after the time; a client "by *name* (client)"; `engine` "by the engine"; before Z4 "Before sign-in" and nothing else; a deactivated person by their name. One component renders it everywhere. Why: the scope's wording, readable in a line; the kind matters when a system made a change. Cost: none |

**Journey test cases** (`tests/journeys/test_j44_who_changed_what.py` and J40.11 in the security
module, on two configurations, people and clients made and granted through the API by the harness
as Security administrator; written first and seen failing):

1. **J44.1, a single write names its caller:** given person P and client C, both Editors in A, when
   P changes a record live and C changes it next, then its history lists C then P (`actor` kind, id
   and name, no `cause`), the feed's two entries name the same actors with `cause.kind: "user"`, and
   the consumer events derived from them carry no actor.
2. **J44.2, a job names its requester:** given P submits a batch that changes two records, when it
   runs, then their history entries carry `cause` the job and `actor` P, and the job reads
   `requestedBy` P.
3. **J44.3, a change set:** given P creates a change set in A, Q (Contributor) changes a record in
   it and R (Editor) publishes it, then the change set reads `createdBy` P, the record's history in
   the change set names Q, the publication reads `publishedBy` R, and the live entries it applied
   name R with the publication as cause; when R withdraws it, `withdrawnBy` is R.
4. **J44.4, the model editor:** given P with Model authoring, when P applies an operation to a
   draft and to a model mapping, then each history's entry reads `author` P; an activation P makes
   reads `actor` P.
5. **J44.5, names when read:** given P's change in A's history, when P is renamed and then
   deactivated, then the entry reads P's new name.
6. **J44.6, before sign-in:** an audit entry from an older release (written without an actor, the
   test says so) reads `actor: null`; an entry the engine wrote at startup (a release installed)
   reads `{kind: "engine"}`.
7. **J40.11, security events:** given S (Security administrator) creates person P, grants P a role
   in A and adds P to a group, and P signs in once with a wrong password and once rightly, then
   `/security-events?principalId=P` lists, newest first, the sign-in (by P), the failed sign-in
   (address, no actor), the membership, the grant and the creation (by S), and no entry holds a
   password or link; a person without Security administration gets `403 FORBIDDEN`.

Unit tests: `audit_actor_of` for its three outcomes (a request's caller, a job's requester, none);
nothing else has edge cases of its own.

**Checks:** the new module and J40's two modules; the journeys whose reads gain a field (J02/J01
history, J05–J07 change sets and publications, J17, J24 jobs, J26 the feed, J30 consumer events,
J33 editor history, J38 mappings, J08 activations), selected by `--testmon` and the execution
guide's groups for the audit, feed and change-set boundaries; `test_openapi_contract` with the lock
diffed; `test_foreign_keys`, `test_boundaries`, the `startup` group (a migration); Ruff on the
changed files. Frontend: the touched Vitest files, format, lint, build; the `sp1-security` runner
extended with a person's Recent activity and a record's history naming its actor, on two models, by
keyboard and at 390px. The full backend suite is Z5's.

**Composable domains (ADR-032):** the identity and provenance doors are touched: the actor is
recorded beside `cause`, never instead of it, and a value source stays an additive field on values;
consumer events, the `match` declaration and bulk APIs are unchanged.

**What the user will still not be able to do after Z4:** see a client's activity or a
subscription's owner on a page (SP2's client pages; the API until then); read every change a person
made across workspaces in one place (the feed per workspace; no audit page planned); have the
interface hide what a person may not do (Z5); expire old sign-in events (TODO, after 0.12).

##### Z4 record (2026-10-24)

**Delivered 2026-10-24.** What was built is the plan's list, items 1–8:

- **Migration** `20261101_01`: `audit_events.actor_kind`, `actor_user_id`, `actor_client_id`
  (`ck_audit_events_actor_kind`, partial indexes), `ix_audit_events_security`; the creator,
  publisher, withdrawer and author pairs on `change_sets`, `publications`, `model_draft_operations`
  and `model_mapping_operations` (`RESTRICT`, at most one, partial indexes); the two `author`
  strings dropped. It ran on the user's development database through the running dev server;
  checked afterwards: head `20261101_01`, the three actor columns, its 49,483 earlier entries naming
  nobody, health `200`.
- **Engine:** `records/audit.audit_actor_of` and a `before_flush` hook that names the actor on
  every audit entry the ORM inserts (an entry built naming its actor, even nobody, keeps it); the
  two raw inserts (`records/deletion.py`, `model/migrations.py`) take it; the offline
  `model_schema_upgrade` names the engine. `identity/principals` (`names`, `named`, `actors`,
  `columns`) resolves principals, and a subscription's `owner` and a job's `requestedBy` moved onto
  it. Change sets, publications (and the one a publication supersedes) and editor operations record
  the caller. `identity/security_events` records and pages security events; they are written in
  `administration.py` (roles, groups, members, grants), `users.py`, `clients.py`, `resets.py`,
  `sessions.py`, `keys.py` and `sign_in.py`.
- **API:** `ActorResponse` and `PrincipalResponse` (`SubscriptionOwner` replaced by the latter);
  `actor` on history, feed entries and activations; `createdBy`, `publishedBy`, `withdrawnBy`,
  `requestedBy`, `author`; `GET /security-events`. OpenAPI lock re-baselined, diffed against
  `f604cbd`: only those (the mapping routes and the subscription routes are off in the locked
  document).
- **Frontend:** `ui/ActorName` (`actorText`, `principalName`) renders every name; `ui/Timeline`
  extracted from the history panel, which the person's **Recent activity** reuses;
  `useWorkspaceLabels` extracted from `GrantsSection` so grant events name a workspace by its label;
  "by *name*" in the record history and the model editor's history; "Created by" on a change set's
  bar and list; "Published … by" and "Withdrawn by" on a publication; "Requested by" on a job and
  as a Jobs list column; the activation baseline sentence names who activated.
- **Documents:** API.md (history's `actor`, security events, the changes to existing routes),
  ADR-044 and ARCHITECTURE (the actor from the writer), USER_JOURNEYS (J44, J40.11) and
  API_JOURNEYS, CURRENT_FUNCTIONALITY (F11, F27), SETTINGS_AND_UI_PLAN, OPERATIONS ("Who changed
  what"), EXECUTION_GUIDE (the runner's row), TODO (retention of sign-in events), CHANGELOG,
  PROJECT_STATUS.

**Where it differs from the plan, decided by recommendation:**

- `GET /security-events` declares the existing `security.manage` action rather than a new
  `security-events.read`: every other Security read does, an action only names its group, and the
  group (and so who may read) is the same.
- J44.6's engine half ("an entry the engine wrote at startup (a release installed)") has no path
  to test: startup writes no audit entry. The engine's entries come from the offline schema
  upgrade and from a job submitted before Z2; the unit test `test_entries_name_whoever_the_session_
  writes_as` covers them (`SYSTEM` and no writer read `engine`). J44.6 tests the entry from before
  Z4.
- The move editor shows no history list, so its operations' `author` is on the API only.
- Security events also record a password set through a link and a password changed (`user`
  `password-set`, `password-changed`), the same kind of change as the link itself. Grants made at
  startup or by `create_admin`/`create_client --role` are not events (the creation is). A failed
  sign-in for a username nobody has reads `aggregateId: "unknown"`.
- A publication superseded by a new publish reads `withdrawnBy` the new publisher, as its status
  reads `withdrawn`.

**Older tests changed by Z4's planned behaviour:** the Vitest fixtures of change sets,
publications, jobs, activations and history entries gained the new fields (the server's shape);
`test_foreign_keys` lists the twelve new columns; `test_api_journeys`' inventory needed
`GET /security-events`. `test_startup.HEAD` still read `20261030_01`, stale since Z3's migration
(Z3 did not run that module); it now reads `20261101_01`.

**Exercised:** the seven cases (14 runs) written first and seen failing (on the missing `actor`,
`createdBy`, `requestedBy` and the route), then passing; the actor unit test. One selection of 540
tests in 1 min 52 s with `-n auto`: J44, J01, J02, J04, J05/J06, J07, J08, J11, J17, J24, J26, J30
events and subscriptions, J33 operations, J37 migration, J38.1, J39, J39/J41/J43, J40's two modules,
J41.2, the records, identity and authorization unit tests, `test_layout`, `test_openapi_contract`,
`test_foreign_keys`, `test_boundaries`, `test_schema_drift`, `test_startup`,
`test_model_schema_upgrade`, `test_api_journeys`: 534 passed, the six registry failures above
fixed and those modules rerun (24 passed); after the final formatting, the directly touched modules
again (110 passed). Ruff check on `app/` and `tests/`; Ruff format on the changed files that were
formatted before and on the new ones. Frontend: `vitest related` for the changed files (15 files,
168 tests) and the changed test files (12 files, 113 tests), Prettier on the changed files, lint (0
errors, the listed warnings), build. **Browser:** `test:browser:security` on both models (46 checks,
39 s): a person's Recent activity naming who did what (the administrator's changes, their own
sign-in and password), a record changed by a client naming it in its history, axe 0 violations on
every page including the record's; the screenshots inspected (Recent activity at 1440px and 390px,
a record's history). Accessibility and visual evidence beyond that runner wait for R.

**Not run:** the full backend suite (Z5's, the user, 2026-10-24); no upgrade test (pre-1.0).

**What the user still cannot do after Z4:** see a client's activity or a subscription's owner on a
page (SP2; `/security-events?principalId=` and the API until then); read every change one person
made across workspaces in one place (each workspace's feed; Z6, added by the user the same day);
have the interface hide what a person may not do (Z5); expire sign-in events (TODO, after 0.12).

#### Z5: The interface follows the caller's permissions

**Needs:** Z1, Z2, I2.

**Scope:** the frontend reads `/me/permissions` for the current workspace and hides what the person may
not open (settings pages, model administration) and disables, with the reason, what they may see but
not do ("You can read this workspace"). A Reader's record view has no edit affordance at all. A
Contributor (D231) edits only in change sets: the record view offers "Propose a change", which opens
or continues their change set, instead of saving live. Every guard stays on the server; the interface
only avoids offering what would be refused. _Changed by the user with D323 (2026-10-24):_ nothing
is shown disabled; what the person may not do is not offered, and no flow is offered that would be
refused before it finishes. _Amended after Z2 (the user, 2026-10-24):_ Z5's checks
included the full backend suite; _moved to Z6 by the user (2026-10-24),_ since Z6 now closes Track Z.
Z5's checks are its own groups.
_Found in SP1 (2026-10-24):_ a person without Browse in the default workspace (a person just
created and given a role elsewhere, or none) sees only "Reading the model in workspace 'default'
needs Browse" instead of the application; Z5 opens the application in a workspace they may use and
says plainly when there is none.

##### Z5 plan (2026-10-24)

**Planned 2026-10-24; accepted by the user the same day** ("yes"): D321–D330 (D323 changed by the
user before acceptance: hidden, never disabled, and no flow offered that is refused at its end), the test cases and the "Z5 as
planned" boards. Checked against the code at `260bac0` with P0's approved "Reader's and Contributor's
record view" board, U8 in SETTINGS_AND_UI_PLAN, J40.1–J40.3 and D291.

**What the check found:**

- **One gate decides every record write in the browser today:** `readOnly` in `App.tsx` (a
  publication, a retired workspace, another workspace), passed to the collection, the record, the
  tree, the matrix, the mapping grid, the panels, the change-set bar and the bulk selection. It knows
  nothing of permissions, and it is one boolean: it cannot say "this record type yes, that one no",
  which a narrowed grant needs (Z2: "a narrowed steward sees edit buttons for other types").
- **Which group a write needs is known where the data is chosen:** `WorkspaceDataProvider` swaps in
  the change-set client when a change set is open, which is exactly D244's rule (Edit live without a
  change set, Work in change sets with one).
- **Permissions are read three times, uncached** (`useRoleLine`, `useHoldsGroup` in the settings
  navigation and on a workspace's page), always for the default workspace in the last two.
- **Startup:** `useRouter` resolves the default workspace's model; a `403` on it is the whole page
  ("Reading the model in workspace 'default' needs Browse"). Settings is drawn inside a loaded
  model (`SettingsShell` takes `model` for the top bar), so a person who can browse nothing cannot
  even reach Account or, for a Security administrator, People.
- **The workspace selector** lists `GET /workspaces` (D288: any role there), so a Security
  administrator, whose instance grant covers every workspace, is offered workspaces they cannot read.
- **Settings lists every page to everyone** except Security (D303); each page then shows the
  engine's refusal.
- **Change sets have no "mine":** the list has no filter; `createdBy` is on every change set (Z4);
  published and discarded change sets are deleted, so the list holds the open ones.
- **Reference patterns:** the data-context band's line saying what an edit does here
  (`DataContextBand`, ADR-040); `Notice`; the gate `bulkSelectionFor` and `onImport` already use
  (an entry not offered when its writes cannot be made).

**What is built:**

1. **API** (documented in API.md, OpenAPI lock re-baselined from a diff):
   - `GET /workspaces?holding=<action group>`: the workspaces where the caller holds that group
     (all of them for an instance grant); an unknown key is `422 ACTION_GROUP_UNKNOWN` (D327).
   - `GET /me/action-groups`: every group the caller holds anywhere, each with `instance` (held at
     the instance) and the `workspaces` (key and label) it is held in otherwise (D328).
   - `GET /workspaces/{key}/change-sets?createdBy=<principal ID>`: the open change sets a person or
     client created (D325).
2. **One permission read in the browser** (D321): `PermissionsProvider` reads `/me/permissions` for
   the open workspace and `/me/action-groups` once, kept for the page load and per workspace, read
   again when the workspace changes and after any `403 FORBIDDEN`. `useRoleLine` and
   `useHoldsGroup` move onto it; nothing else reads permissions.
3. **What a record write may touch** (D329): `useWorkspaceData()` gains `writes`: whether the open
   context allows record writes at all (the existing `readOnly`, plus Edit live without a change set
   or Work in change sets with one) and `permits(application, recordType)` from that group's
   narrowing; a relationship is offered when either end's type is permitted (D291). Every surface
   the `readOnly` gate reaches reads it: create (only permitted types are offered), edit, inline
   cells, delete, remove a value, relationships and their dialogs, matrix cells, the mapping grid,
   the tree's moves and drag, restructuring. The bulk selection and Import also need Bulk and import;
   Export stays (Browse).
4. **The Reader** (D322, D323): the data-context band's line says "You can read this workspace. To
   change records, ask a security administrator for a role that allows it." in place of "Edits apply
   immediately"; no create, edit, delete, inline, relationship, tree-move or selection affordance on
   any view or panel; on the change sets and publications lists, New change set, Start a change set
   from this publication and Withdraw are not offered.
5. **The Contributor** (D324, D326): in live data, the record's **Edit** becomes **Propose a
   change** and a collection's **New** becomes **Propose a new record**; each continues the person's
   newest open change set (D325) or, when they have none, asks for its name in a small dialog
   ("Changes by *name*", editable) and creates it, then opens the same record (or the new record's
   form) in it. The band's line in live says "Changes you make go into your change set, not live. A
   data steward or owner publishes it." and, when they have one open, a button "Your change set:
   *name* · *n* changes" opens it. In the change set they edit as today; **Publish** is not offered
   (the band's line says who publishes: "Edits stay in this change set until someone who holds
   Publish in *workspace* publishes it."); Validate, Rename and Discard stay.
6. **A narrowed writer** (D329): types outside the narrowing are read-only as for a Reader, and the
   record's page says, in the band's line, "Your role changes *Specimen* and *Determination*
   records here; others you can read." (the model's names, as data).
7. **Startup and no workspace** (D326): the application opens the default workspace when the
   person may browse it, otherwise the first by label of `GET /workspaces?holding=browse`; with none,
   a page "There is no workspace you can open yet" naming the roles they hold ("You hold no roles
   yet." or their roles) and "Ask a security administrator for a role in a workspace.", with
   Settings and Account; a Security administrator reads instead "A role in a workspace is granted
   on People." with People. Settings and the no-workspace page open without a workspace model: the top bar then
   shows the product and the settings button without applications. The workspace selector lists
   `holding=browse`.
8. **Settings follows the groups** (D328, D330): a page is listed only to someone holding its group
   anywhere: About, Appearance, Account, Jobs and API reference to everyone; Workspaces to
   everyone (each workspace's page reads it), its create, rename, retire, delete and set-default
   only with Workspace administration and Access with Security administration (as now); Model with
   Model authoring or Model release (drafts and their actions with Model authoring; Install,
   Activate and Migrate with Model release in the workspace); Deployment and Operations with
   Operations; Import profiles with Bulk and import; Copy and move with Copy and move; Consumer APIs
   with Browse; Webhooks with Integration administration; Security as now. A group of the
   navigation with no page left is not shown. An address of an unlisted page shows the engine's
   refusal as today.
9. **A refusal still reaches the person** (D330): the interface only avoids offering what would be
   refused; a `403 FORBIDDEN` (a role changed meanwhile) shows the engine's message and re-reads the
   permissions, so the page follows on the spot.
10. **Documents:** API.md (the three reads), USER_JOURNEYS (J40.1–J40.3's UI channel, J40.12),
    API_JOURNEYS, CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN (U8: Z5 built), UI_ACCEPTANCE (Z5 state
    rows), EXECUTION_GUIDE (the new runner), CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D321 | How the browser knows what the person may do | **Recommended:** one provider reads `/me/permissions` for the open workspace and `/me/action-groups` once; kept per workspace for the page load, read again on a workspace change and after any `403 FORBIDDEN`; the account menu, the settings navigation and the views all read it. Why: three uncached reads today, two of them for the wrong workspace; a role changed meanwhile is caught on the first refusal, without polling. Cost: a role granted meanwhile shows after the next refusal or a reload, not at once |
| D322 | Where the Reader's and Contributor's note goes (**differs from the board**, which puts it on the record) | **Recommended:** in the data-context band's line, which already says what an edit does in this context, on every view. Why: one place for every view, collection, tree, matrix and record, instead of a note repeated on each record page; the band is the reference pattern (ADR-040). Cost: the record page carries no note of its own |
| D323 | Hidden or disabled | **Changed by the user (2026-10-24): hidden.** What the person may not do is **not offered**: no disabled button with a reason (a Reader's Edit, a narrowed writer's Edit on another type, a Contributor's Publish, Withdraw without Publish); a settings page they cannot open is not listed. **A flow is offered only when it can be finished:** its entry (a button, a menu item, a dialog's opening) checks every group its steps need in every workspace it writes before anything opens, so nobody fills in a dialog to be refused at its last step. The flows and what each needs: Import, a profile's load and the bulk changes (Bulk and import, with its narrowing); a move (Copy and move in the target, and Browse in the source for a copy or Work in change sets for a move); a change set's Change model version and migrate-and-publish (Model release; Publish for the second); Start a change set from a publication (Work in change sets); Install and Activate (Model release in the workspace); a draft's actions (Model authoring); the grant dialog (Security administration). Why: the user's rule: being able to click, open the dialog and be refused a few steps later makes no sense. Cost: the scope's "disables, with the reason" wording is replaced; the band's line is where a person learns who can do what they cannot |
| D324 | What "Propose a change" does | **Recommended:** continues the person's newest open change set (by `updatedAt`) and opens the same record in it with its form; with none, a small dialog asks the change set's name ("Changes by *name*", editable) and creates it. The band's button names it and its count; other change sets are opened from Change sets as today. Why: a Contributor should not have to know about change sets before their first change; the name dialog is the one step that cannot be guessed. Cost: with several open change sets, the newest is chosen; another is opened from the list |
| D325 | Finding "their" change set | **Recommended:** `createdBy=<principal ID>` on `GET /workspaces/{key}/change-sets`, the person's or client's public ID. Change sets stay shared (D255); the filter only finds them. Why: an integrator's journey too (a client continuing its own change set), and the list stays one route. Cost: none |
| D326 | Which workspace opens first | **Recommended:** the default workspace when the person may browse it; otherwise the first by label they may browse; with none, the "no workspace yet" page with their roles and Settings. Why: SP1's finding; the default stays the organisation's choice for those who can read it. Cost: Settings must open without a model (the top bar without applications) |
| D327 | Workspaces the person may use | **Recommended:** `holding=<action group>` on `GET /workspaces` (any group with D288's meaning without it); the selector asks for `browse`. Why: a Security administrator's instance grant lists every workspace, though they cannot read one; the filter is the engine's own visibility rule (`in_workspaces`). Cost: none |
| D328 | Which settings pages are listed | **Recommended:** by the groups held **anywhere**, from `GET /me/action-groups`, as item 8's table. Why: Webhooks or Copy and move held in one workspace must not vanish because another is open; one read answers every page. Cost: one route; the table to keep with the catalogue |
| D329 | A narrowed writer in the interface | **Recommended:** the open context's group's narrowing decides per record type, through `writes.permits`; relationships when either end is permitted (D291); create lists only permitted types; the band's line names the permitted types or applications. Why: Z2's finding (edit buttons for types that are refused); the same rule the engine applies, read from the same answer. Cost: every write surface reads `permits` instead of one boolean |
| D330 | When the interface and the engine disagree | **Recommended:** the engine decides; a `403 FORBIDDEN` is shown as worded and the permissions are re-read. An unlisted settings page opened by its address shows the refusal as today. Why: the interface only avoids offering what would be refused (the scope). Cost: none |

**Journey test cases** (`tests/journeys/test_j40_interface_permissions.py`, J40.12 "The interface
follows permissions", on two configurations; written first and seen failing):

1. **Workspaces holding a group:** given a person who is Reader in workspace A and Integration
   administrator in B, and a Security administrator holding only that role, when
   `GET /workspaces?holding=browse` is read, then the person sees A only and the administrator none;
   `holding=integration-admin` gives the person B; an instance Reader sees every workspace;
   `holding=nonsense` is `422 ACTION_GROUP_UNKNOWN`.
2. **The groups held anywhere:** given the same person, when `GET /me/action-groups` is read, then it
   lists Browse in A, Integration administration in B and nothing else; the administrator's lists
   Security administration with `instance: true`; after the person's grant in B is removed, B is
   gone on the next request.
3. **Their change sets:** given two Contributors in A each creating a change set, when
   `GET /workspaces/A/change-sets?createdBy=` is read with each one's ID, then each sees only their
   own; after one is published it is no longer listed; another workspace's change sets are never
   listed.
4. **A Contributor proposes:** given a Contributor in A with no change set, when they create one, write
   a record in it and try to publish, then the write passes, the publish is `403 FORBIDDEN` naming
   Publish, and the live record is unchanged (J40.2's flow as the interface walks it).

Unit tests (Vitest): `writes.permits` (unnarrowed, narrowed by type, by application, a
relationship's two ends, live against change set); the settings navigation from held groups; the
startup choice (default browsable, another, none); the band's line for Reader, Contributor and
narrowed writer.

**Browser** (a new runner `z5-permissions`, on two models; reference patterns: the data-context
band, P0's board, the change set's bar): as a Reader, a collection, a record, the tree and the matrix
offer no write and the band says so; as a Contributor, Propose a change on a record names a new
change set, opens the record in it with its form, saves, the band's button shows "1 change", Publish
is not offered; a person without Bulk and import is offered no Import and no selection; a
second Propose a change continues the same change set; as a Data
steward narrowed to one record type, another type's record has no Edit and the band names the
permitted type; a person with Browse only in a second workspace lands there; a Security
administrator without data roles sees the no-workspace page and reaches People; a Reader's settings
navigation lists only their pages. Keyboard through Propose a change and its dialog; 390px (the
band, a Contributor's record); axe; screenshots of a Reader's and a Contributor's record, the dialog
and the no-workspace page at 1440px light and dark and at 390px, inspected against the boards.

**Checks:** the new journey module, J40's authorization module, `test_openapi_contract` with the
lock diffed, `test_api_journeys`, `test_boundaries`; Ruff on the changed files; Vitest for the
touched folders (`src/app`, `src/features/objects`, `src/features/workspaces`, `src/features/settings`,
`src/features/security`, `src/routing`); format, lint, build; the runners `z5-permissions`,
`sp1-security`, `u3-settings` and those EXECUTION_GUIDE §2 selects for the data-context band and
the change-set bar (`authoring-n1`, `change-sets`), each named with its result. No migration. The
full backend suite is Z6's.

**Composable domains (ADR-032):** no door is touched: the interface reads permissions and one list
gains a filter on its creator; no identity, attribute storage, audit or bulk contract changes.

**What the user will still not be able to do after Z5:** submit a change set for approval or be told
when it is published (A1–A3: a Contributor tells someone who can publish); see one person's changes
across workspaces (Z6); manage clients on a page (SP2); sign in with a provider (I3).

##### Z5 record (2026-10-24)

**Delivered 2026-10-24.** What was built is the plan's list, items 1–10:

- **API:** `holding` on `GET /workspaces` through the engine's own visibility rule, an unknown group
  refused with `ACTION_GROUP_UNKNOWN` by the check roles already used (`known_groups`, D327);
  `GET /me/action-groups` (`held_anywhere`, D328); `createdBy` on a workspace's change sets
  (`principals.named_by`, D325). OpenAPI lock re-baselined from a diff against `260bac0`: the three
  and their schemas (`HeldAnywhereList`, `HeldAnywhere`, `HeldWorkspace`); nothing else.
- **One permission read** (D321): `features/security/permissions.ts` keeps `/me/permissions` per
  workspace and `/me/action-groups` for the page load, read again after any `403 FORBIDDEN`
  (`api/forbidden.ts`); `useRoleLine` and `useHoldsGroup` read it. **What a record write may touch**
  (D329): `recordWrites` (the engine's rule: the group's narrowing by application or type, a
  relationship by either end) on the data context as `useRecordWrites()`, Edit live's in live data,
  Work in change sets' in a change set, none in a publication.
- **The surfaces:** App's `readOnly` adds "no record write here"; the record (its header, menu,
  values and deletion by its type), table cells and row menus by each row's type, the child tables'
  Add, relationships by either end (the far end by type before its record is chosen), matrix cells
  by the cell type, the mapping grid, the tree's actions and drags, the sidebar's moves; Import and
  the bulk selection with Bulk and import (its narrowing for the collection's type); a many-records
  cell and moving several records (batches) with Bulk and import; the change set's bar (Validate,
  Change model version, Discard with Work in change sets; Publish also with Publish; migrate and
  publish also with Model release); New change set, Start a change set from a publication and
  Withdraw; Manage workspaces, the workspace page's actions and Open workspace; the Model page's
  drafts, Install and Activate per workspace; Copy or move data… and its source and target lists;
  the Jobs page's New import; the import, export and webhook dialogs' workspace lists (D323).
- **The band** (D322): `permissionLine` for a Reader, a Contributor in live data, a narrowed writer
  and someone in a change set who cannot publish; the Contributor's "Your change set: *name* · *n*
  changes" in the band's actions. **Propose a change** (D324): `features/workspaces/Proposal.tsx`
  (the person's newest open change set by `createdBy`, its changes counted, the name dialog); the
  record's "Propose a change" and a collection's "Propose a new *type*", which open the record's form
  or the create form in the change set (a one-shot `createRequest` on the list route).
- **Startup** (D326): `openingWorkspace` in `useRouter`; with none, the router shows Settings under
  an empty model (`model/emptyModel.ts`, its product named after the instance's release) and
  `app/NoWorkspace.tsx` in the application's place; an address naming a workspace the person may not
  browse opens their own with the refusal said, as an unknown workspace is. **Settings** (D328):
  `navigationFor` lists pages by the groups held anywhere; a group with no page left is not shown.
- **Tests and runners:** the journey module and unit tests below; the shared fixture
  `test/permissions.ts` (the person holding every group, as before Z5) in the App, Settings,
  WorkspaceAdmin and ModelWorkbench tests, and the permission store reset after each test in
  `test/setup.ts`; the new runner `z5-permissions`.
- **Documents:** API.md, USER_JOURNEYS (J40.12), API_JOURNEYS, CURRENT_FUNCTIONALITY (F27),
  SETTINGS_AND_UI_PLAN (U8), UI_ACCEPTANCE (Z5-1 to Z5-4), EXECUTION_GUIDE, CHANGELOG, TODO,
  PROJECT_STATUS; the "Z5 as planned" boards on the security canvas.

**Where it differs from the plan:**

- **The first other workspace is the first by key**, the order `GET /workspaces` lists (D326 said
  by label); one page of one workspace is read.
- **J40.12 case 2 corrected:** the approved case said the caller holds "Browse in A and Integration
  administration in B and nothing else", but the predefined Integration administrator also holds
  Feed (D230); the case now expects Feed in B too. The code was right; the case was written wrong
  (found when it ran).
- **At 390px** the band's line stays in the context popover, where the phone band holds every
  context's line; the change set's button is in the band, as on the phone board.
- **Import is offered before its file is read:** a holder of a narrowed Bulk and import learns in
  the preview that rows of other types are refused (TODO).
- **The journey cases were seen failing first** (8 of 8, for the missing filter or route), then
  passed.
- **Found and fixed on the way, not Z5's:** `wp9-change-sets` and `wp9-navigation` started their
  own servers without the secrets key and token every engine needs since I1, so neither could run;
  both now boot through the shared harness. `wp12` expected the activation's sentence as it was
  before Z4 added who made it.
- **Found, not fixed (TODO):** a record's live history lists its change-set edits as if live
  (version 2 on a version 1 record); `j4-import` fails at the Jobs list and `wp9-navigation` at the
  list's read-ahead retry, each the same on `260bac0`; `wp9-authoring`, `wp9-publications` and
  `v1-api-reference` still cannot start.

**Checks** (single process):

- `tests/journeys/test_j40_interface_permissions.py`: 8 passed (4 cases × 2 configurations), seen
  failing first; with `test_openapi_contract`, `test_api_journeys`, `test_boundaries`: 20 passed.
  Ruff check and format on the changed backend files.
- Vitest: `src/app`, `src/features/settings`, `src/features/security`, `src/features/workspaces`:
  197 passed before the new unit tests; `src/features/objects`, `src/features/model-admin`,
  `src/features/moves`, `src/features/jobs`, `src/routing`, `src/api`: 441 passed; the new
  `permissions.test`, `permissionText.test`, `NoWorkspace.test`, `Proposal.test`: 26 passed.
  `format`, `lint` (0 errors; the 8 warnings in untouched files), `build`.
- **Browser:** `z5-permissions` on two models: 26 checks, axe 0 violations on the Reader's record,
  the Propose a change dialog, the Contributor's record and the no-workspace page; `sp1-security`:
  46 checks; `u3-settings`: 10; `authoring-n1`: 8; `change-sets` (on the harness) passed; `ua8`,
  `w4`, `k1`, `wp11` passed; `j4` and `wp9-navigation` failed the same as on `260bac0` (above).
  Screenshots inspected against the "Z5 as planned" boards: a Reader's record, the dialog, a
  Contributor's record at 1440px and at 390px light and dark, a narrowed steward's record dark, the
  no-workspace page.

- **The rest of EXECUTION_GUIDE §2's selection, on the user's go-ahead (2026-10-24), one at a
  time:** `b3`, `b4`, `c4`, `c5`, `a4`, `a5`, `wp14`, `wp13c`, `s6`, `ua9`, `authoring-a9`, `k3`,
  `j1u`, `webhooks`, `workspace-x4` passed; `wp12` failed on the activation's sentence, which Z4
  ended with "by *name*" without updating the runner; its expectation now allows the name, and it
  passed.

**Not run:** the full backend suite is Z6's (the user, 2026-10-24); the accessibility and visual
gates are R's.

**What the user cannot do yet:** submit a change set for approval or be told when it is published
(A1–A3; a Contributor tells someone who can publish); see one person's changes across workspaces
(Z6); manage clients on a page (SP2); sign in with a provider (I3).

#### Z6: One person's changes across workspaces

**Needs:** Z4, Z5. _Added by the user, 2026-10-24,_ after Z4 named the gap: each workspace's history
and feed show who changed what, but nothing lists everything one person or client changed.

**Scope:** a read of the audit entries a person or client made (Z4's actor), across workspaces,
newest first and cursor paged: their record and relationship changes, change-set work,
publications and model administration, each naming its workspace, what it changed and its cause.
Filtered as every list is (D249): the caller sees the entries in workspaces where they hold Browse,
and entries outside any workspace (model administration) only with the group that reads them; a
Security administrator without data roles therefore sees none of the data changes (D230), which
stay apart from Recent activity's security events (D319). In the interface, a "Changes" view
reachable from a person, and from a client once SP2 builds its page. The plan settles the route
(a filter on a general audit read, or one per principal), the time filter, the view's place and
mock-up, and the journey (J44 variant). _Moved from Z5 by the user (2026-10-24):_ Z6's checks
include the full backend suite, announced with its expected time, which closes Track Z and stands
for Z1's to Z5's; a failure it finds from them is fixed in Z6 and named in its record.
_Amended by HM1 (2026-10-25):_ Z6 also adds "Your recent changes" to the home page (D335), from
the same read for the signed-in person.

##### Z6 plan (2026-10-25)

**Planned 2026-10-25; accepted by the user the same day** ("yes"), with the full backend suite run at its end. Checked against the code at `56903d2`
(HM1 committed) with Z4's plan and record, D249, D316, D319, D323 and D335, and against the
development database (read only).

**What the check found:**

- **The actor is on every entry since Z4** (`actor_kind`, `actor_user_id`, `actor_client_id`), with
  a partial index on each ID alone, so a person's entries newest first would sort all of them for
  every page; a batch of 16,000 records is 16,000 entries.
- **Only live changes know their workspace.** `workspace_key` is set where an entry takes a feed
  position (`records/audit._place_in_feed`): live records and relationships, publishing and
  withdrawing. Change-set work (`change-set-object`, `relation` with `changes.changeSetId`, the
  `change-set` lifecycle) names its change set but no workspace, and a published or discarded change
  set is deleted, so after publishing nothing in the row says where the work was. A workspace's
  model activation (`workspace_model`) has the key only inside `changes`. Model drafts, release
  installs and the activations from before 0.11 (`model_runtime_state`) belong to no workspace.
- **Only live entries know what they changed.** `feed_subject` (record type, a relationship's type
  and ends) is filled for feed entries only; a change-set entry has the record's ID and its values,
  not its type.
- **On the development database** (49,496 entries): every change-set entry (54 lifecycle, 16,213
  record, 13,300 relationship) can be placed from its change set, the publication entry naming it, or
  its lifecycle entries naming `workspaceKey`; 4,557 live entries from 2026-10-02, before the feed,
  name neither and stay unplaced.
- **Deleting a workspace clears `workspace_key`** on its entries (`workspaces/catalogue`, 0.9 D208);
  they stay as history belonging to no workspace.
- **`mapping` `transition` entries** summarise a relation set's change; each relationship it changed
  is its own entry.
- **The interface:** `ui/Timeline` (record history, Recent activity), `ui/ActorName`,
  `useCursorFeed` with Load more, the person's page in Security › People, Home's sections
  (`features/home`). Settings and Home open without a workspace model.
- **Reference patterns:** Home's page frame and sections; `Timeline` with Load more; the change
  sets list's filters (`ui/SearchField` and selects).

**Mock-up:** [security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), row "Z6
as planned": a person's Changes page at 1440px (filters; dark and "nothing you can read" in Tweaks),
the ways to it (a person's page, a name in a record's history), Home's Your recent changes, and the
Changes page at 390px.

**What is built:**

1. **Migration** `20261102_01`: `feed_subject` renamed `subject`; every entry that belongs to a
   workspace records `workspace_key`, with or without a feed position (change-set work, a
   workspace's model activation); a record or relationship entry inside a change set records its
   `subject` as live entries do. Filled in SQL for existing entries (D341). Indexes
   `(actor_user_id, occurred_at, sequence_id)` and `(actor_client_id, occurred_at, sequence_id)`
   replace the two single-column ones (D347).
2. **Writers:** `record_audit_event(s)` take the workspace for an entry outside the feed
   (`ChangeSetWrites`, the change-set lifecycle, restructurings, type changes, pinning, change-set
   migrations, the per-workspace activation); `subject` is filled for change-set records and
   relationships.
3. **The read** `engine/reads/changes.py` and `GET /changes` (D340, D342, D343, D344): data and model
   changes newest first, cursor paged (50, up to 500), filtered by `actorId`, `workspaceKey`, `kind`
   (`record`, `relationship`, `change-set`, `publication`, `model`, any of), `from` and `until`, and
   always by what the caller may see. Each entry: `id`, `occurredAt`, `kind`, `action`, `workspace`
   (key and label, or `null`), `changeSet` (ID and name while it is open, or `null` live),
   `subject` (what it changed, named as it is now), `changedFields`, `attributes` (key and name),
   `cause`, `actor`. Names and labels are resolved for the page in one statement per kind, type and
   attribute names from each workspace's own model. Action `changes.read`, open to anyone signed
   in.
4. **The page** (D345), `features/changes/`, route `/changes?actorId=…` outside any workspace, as
   Home is: "*Name*'s changes" ("Your changes" for oneself) with the person's or client's name and
   kind; filters Workspace (those the caller reads), What, Period (Any time, Last 24 hours, Last 7
   days, Last 30 days); entries as a `Timeline` grouped by day, 50 at a time with Load more; each
   entry's title links to what it changed while it exists (the record in its workspace or in its
   change set, the change set's review, the publication, the draft, the release).
5. **Ways to it** (D345, D323): a person's page in Security › People, "See changes" (shown only when
   the caller holds Browse somewhere or Model authoring at the instance); a person's or client's
   name in a record's history (`ActorName` as a link there); Home's Your recent changes.
6. **Home** (D346): Your recent changes under Your change sets, the caller's latest five, shown only
   when there is one, with "See all your changes".
7. **Documents:** API.md (`GET /changes`, `subject`, the paged-collections inventory),
   ARCHITECTURE (an entry's workspace and subject), USER_JOURNEYS (J44.7–J44.11) and API_JOURNEYS,
   CURRENT_FUNCTIONALITY, SETTINGS_AND_UI_PLAN (Changes, Home), UI_ACCEPTANCE (the page's state
   row), EXECUTION_GUIDE (the new runner), CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D340 | The route | **Recommended:** one general read, `GET /changes`, of data and model changes across workspaces, with `actorId` (a person's or client's public ID) as one filter beside `workspaceKey`, `kind`, `from` and `until`; security events stay at `/security-events` (D319). Home reads it with the caller's own ID. Why: "what did this client change", "what changed in the workspaces I read since Monday" and "what did I change" are the same read with different filters, and an integrator's audit export needs the unfiltered one; a route per principal would be one case of it. Cost: one route and one action; `actorId` names who made a change (not who it is about, as `principalId` does on security events) |
| D341 | Where an entry was made | **Recommended:** every entry that belongs to a workspace records it, not only those in the feed: change-set work and a workspace's model activation gain `workspace_key` without a feed position, and a change-set record or relationship entry records its `subject` (type; a relationship's type and ends) as live ones do; `feed_subject` is renamed `subject` since it no longer belongs to the feed alone. Existing entries are filled in the migration from the change set, the publication entry naming it, or the change set's lifecycle entries; those from before the feed stay without (4,557 on the development database). Why: after a publish the change set is gone and nothing else says where its work was; filtering by workspace must be a column, not a join through rows that are deleted. Cost: one migration over the audit table (49,496 rows here, statements per kind); the feed, the deriver and the retention floor read `feed_position` and are unchanged |
| D342 | Who sees which entry | **Recommended:** D249's rule: an entry in a workspace with Browse there; model administration outside workspaces (drafts, release installs, activations from before 0.11) with Model authoring at the instance; an entry of a deleted workspace or one never placed only with Browse at the instance. Security events never; relation-set `transition` summaries left out (each relationship is its own entry). A Security administrator without data roles reads an empty list (D230), not a refusal. Why: every list filters so; Browse already shows who made each change in history (D316). Cost: anyone with Browse in a workspace sees everyone's changes there, as history already shows |
| D343 | What an entry says | **Recommended:** its kind and action, its workspace (label), its change set (name while open), what it changed named as it is now (a record's type and name, a relationship's type and both ends' names, a change set's name, a publication's number, a draft's name, a release's name and version), the fields and attributes it changed by name (from that workspace's model), the cause and the actor; never values. A record since deleted keeps its type and reads "a record since removed". Why: a line someone can read without opening each entry, across models that differ; values stay in a record's history and the feed's rule (names, not values) holds. Cost: names as they are now, not as they were then |
| D344 | The time filter | **Recommended:** `from` and `until` (instants, `from` included, `until` not), alone or together; the page offers Any time, Last 24 hours, Last 7 days and Last 30 days. Why: the API takes any range an integrator needs; four periods cover what a person asks. Cost: no date picker on the page |
| D345 | The view's place | **Recommended:** a page of its own outside any workspace, `/changes?actorId=…`, like Home: the person's or client's name, the filters, a timeline grouped by day with Load more, each title linking to what it changed while it exists. Reached from a person's page in Security › People ("See changes", shown only to a caller who would see something, D323), from a name in a record's history, and from Home. A client's page links to it when SP2 builds one. Why: data people find it from history and Home, where a Settings page would not be theirs; a Security administrator without data roles would see nothing there (D230). Cost: one route kind; `ActorName` gains a link form, used in record history only |
| D346 | Home's Your recent changes | **Recommended:** the caller's five latest entries, under Your change sets, shown only when there is one (D335), with "See all your changes". Why: HM1's amendment; five keeps Home short. Cost: one more read on Home |
| D347 | Speed of a person's page | **Recommended:** indexes on `(actor, occurred_at, sequence_id)` for people and clients, replacing the single-column ones, so a page is an index range whatever the person's total; the workspace and kind filters apply within it. Timed once on a copy of the development database for its busiest actor, and in the journey at 200 and 2,000 entries. Why: a batch writes an entry per record. Cost: two indexes rebuilt in the migration |

**Journey test cases** (`tests/journeys/test_j44_changes.py`, J44.7–J44.11, on two configurations,
workspaces A and B on different models, people and clients made and granted through the API; written
first and seen failing):

1. **J44.7, one person's changes:** given P (Data steward in A and B) changes a record live in A,
   creates a change set in B, changes a record and a relationship in it and publishes it, and Q
   changes a record in A, when the harness (Browse at the instance) reads `/changes?actorId=P`, then
   it lists, newest first, the publication and the entries it applied (B, cause the publication),
   the relationship and the record changed in the change set (B, with its change set), the change
   set's creation (B) and the live change (A), each with its workspace's label, the record's type
   and name from its own model and actor P; nothing of Q's.
2. **J44.8, what the caller may see:** given R with Browse in A only, S a Security administrator
   with no data role, and M with Model authoring at the instance only, and P also changed a model
   draft, when each reads `/changes?actorId=P`, then R sees only A's entries, S an empty list
   (`200`), M only the draft's entry; the harness sees all.
3. **J44.9, filters and pages:** given J44.7's entries, `workspaceKey=B`, `kind=record` and a
   `from`/`until` range each keep only theirs; pages of two continue without repeats or gaps; an
   unknown `kind` is refused with `400 VALIDATION_ERROR` naming it.
4. **J44.10, a client:** given client C (Editor in A) submits a batch changing two records, when C
   reads `/changes?actorId=<C>`, then both entries name C with the job as cause.
5. **J44.11, after things go:** given P's record in A is deleted and A is deleted later, when the
   harness reads `/changes?actorId=P`, then the earlier entries read `workspace: null` and the
   record as removed, and R (Browse in A, which no longer exists) no longer sees them.

Unit tests: the migration's placement statements on rows of each kind (a change set open,
published, discarded, never placed); the read's visibility condition for the four kinds of caller.
Vitest: an entry's title and line for each kind, the period's `from`, the `/changes` route.

**Browser** (a new runner `z6-changes`, on two models; reference patterns: Home's frame,
`Timeline`): from a record's history, the name opens that person's changes; the workspace, what and
period filters narrow the list and Load more continues; an entry opens its record in its own
workspace; Home shows Your recent changes and "See all your changes" opens the caller's own; a
Security administrator's person page shows "See changes" only when they hold Browse. Keyboard from
the filters through Load more; 390px; axe; screenshots at 1440px light and dark and at 390px,
inspected against the boards.

**Checks:** the new journey module and J44's; the journeys whose entries gain a workspace or
subject (history J01/J02, change sets J05–J07, J26 the feed and J30 consumer events, which must not
change); `test_openapi_contract` with the lock diffed, `test_api_journeys`, `test_paging_contract`,
`test_boundaries`, `test_schema_drift`, `test_foreign_keys`; the `startup` group (a migration) and a
smoke start on a copy of the development database with the placement counts compared before and
after; Ruff on the changed files. Frontend: Vitest for `src/features/changes`, `src/features/home`,
`src/features/security`, `src/ui`, `src/routing`; format, lint, build; the runners `z6-changes`,
`hm1-home`, `sp1-security`. **Then the full backend suite**, which closes Track Z (the user,
2026-10-24): about 11 minutes with `-n 6` (0.11's R: 10 min 51 s), plus its serial part; approving
this plan is the go-ahead for that one run. A failure it finds from Z1–Z5 is fixed in Z6 and named
in its record.

**Composable domains (ADR-032):** the audit and provenance door is touched: entries gain where they
were made and what they changed, beside the actor and cause, never instead; values stay out of the
audit read; identity, attribute storage, bulk APIs, the `match` declaration and mapping coverage are
unchanged.

**What the user will still not be able to do after Z6:** see what waits for their approval (A3); open
a client's changes from a client's page (SP2; from a record's history until then); see the values a
change wrote in the cross-workspace list (a record's history has them); export the list to a file
(not planned); see model-to-model mapping operations in it (they are in the mapping's own history,
not the audit).

##### Z6 record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's list, items 1–7:

- **Migration** `20261102_01`: `feed_subject` renamed `subject`; existing entries placed in SQL
  (`_PLACES`, `_ACTIVATIONS`) and change-set records and relationships named (`_RECORD_SUBJECTS`,
  `_RELATION_SUBJECTS`); the actor indexes `(actor_*_id, occurred_at, sequence_id)`.
- **Engine:** `record_audit_event(s)` take `feed=False` for an entry in a workspace without a feed
  position; `ChangeSetWrites` records with its workspace and keeps the subject it was dropping; a
  `before_flush` hook in `records/audit.py` (`_place_entries`) places every other ORM-inserted entry
  from its change set or a workspace activation's `workspaceKey`, one statement per flush; the two
  raw inserts (`records/deletion.py`, `model/migrations.py`) name the workspace and subject; the
  change-set record writers outside the write unit (attribute patches, restructurings, type changes)
  and the batch lookup's change-set entries name their subject. `reads/changes.py` (`visible`,
  `change_page`) and the action `changes.read`.
- **API:** `GET /changes` (`routers/changes.py`, `projections/changes.py`, `schemas/changes.py`);
  `presenters.actor_response` made public for it. OpenAPI lock re-baselined, diffed against
  `56903d2`: the route and its eight schemas, nothing else; the paged-collections inventory 58 → 59.
- **Browser:** `features/changes/` (`ChangesPage`, `changeText`), the `changes` route, Home's Your
  recent changes, "See changes" on a person's page, a name in a record's history linking
  (`ActorName`'s `onOpenChanges`, passed only by the record page), `Timeline` titles that may be
  links; styles in `home.css` on existing tokens.
- **Documents:** API.md, ARCHITECTURE, OPERATIONS, PRODUCT, CURRENT_FUNCTIONALITY (F11),
  USER_JOURNEYS (J44.7–J44.11), API_JOURNEYS, SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (Z6-1, Z6-2),
  EXECUTION_GUIDE (`z6-changes`), ROADMAP, TODO, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan, decided by recommendation:**

- **The time filter is `since`/`until`, not `from`/`until`** (D344): `from` is already every paged
  collection's (`from=end`, ADR-030); the first journey run refused `from=<instant>` as a paging value.
- **An unknown `kind` is `422 REQUEST_VALIDATION_ERROR`**, the engine's refusal for every query
  parameter out of its values, not the `400 VALIDATION_ERROR` the plan's J44.9 wrote; J44.9 asserts
  the engine's code. The plan's wording was the error, not the behaviour.
- **A change set keeps its name once published or discarded** (D343 said "while it is open"): the
  name comes from the change set while open, else from its last lifecycle entry naming one, so a
  publication's and its applied entries' change set still reads by name. `changeSet.open` says
  whether it can still be opened.
- **`subject.applicationKey`** added: a record's link needs its application.
- **The Changes page draws the timeline's markers**, not the boards' kind tiles (the plan said
  "a `Timeline`"); Home's Your recent changes has the tiles, in type-hue slots and status surfaces.
- **The workspace filter's options** are the workspaces the reader may browse (`GET /me/workspaces`),
  and its address parameter is `workspace=`, so the router never opens that workspace's model.
- **A name links only in a record's history**; the editors' histories, activations and Recent
  activity keep it plain (D345).

**Found on the way and fixed:**

- **The migration missed 30,250 entries' subjects** on the development database: the ORM wrote "no
  subject" as JSON `null`, not SQL `NULL`. The migration's unit test caught it; both statements now
  take either.
- **Load more with a period chosen replaced the list with an error:** each request computed a new
  `since`, so the next page's cursor no longer matched its filters (`z6-changes` step 4). The period's
  start is fixed when it is chosen (`useMemo`); the runner's keyboard step pages under a period.

**Found, not Z6's (TODO):** on a copy of the development database started with another deployment
key, the engine starts but `POST /oauth/token` fails as `500 INTERNAL_ERROR` (`SealError`), not an
actionable refusal (I1's signing keys).

**Older tests changed by Z6's planned behaviour:** `test_startup.HEAD` (`20261102_01`), the OpenAPI
lock and the paged count, `test_api_journeys`' inventory (API_JOURNEYS), `feed_subject` renamed in
`unit/engine/events/test_plan.py` and `volume_fixture.py`.

**Checks:**

- **Journeys:** J44.7–J44.11 (`test_j44_changes.py`, 5 cases × 2 configurations) seen failing (10 of
  10 on the missing route), then passing. Selected journeys whose entries gained a workspace or
  subject: J01, J02, J04, J05, J06, J07, J11, J15, J17, J26, J30, J37, J44 — 386 passed (2 min 12 s).
- **Unit:** the migration's placement and subject statements (open, published, discarded, never
  placed, a key created again), `visible` for four callers; `tests/unit/engine/records`, `events`,
  `reads`, `migrations` — 83 passed. The `startup` group: 192 passed.
- **Contract:** `test_openapi_contract`, `test_api_journeys`, `test_paging_contract`,
  `test_boundaries`, `test_schema_drift`, `test_foreign_keys`, `test_layout` — passed.
- **Ruff** check on `app/` and `tests/`; format on the new files and on the changed files that were
  formatted before (the others keep their formatting, only Z6's lines changed).
- **Smoke start on a copy of the development database** (`rdm` copied to a scratch database, then
  dropped): upgraded `20261101_01` → `20261102_01`, `/health` ok. Entries with a workspace 14,424 →
  44,644 of 49,496 (the 30,220 the plan measured); unplaced: the 4,557 entries from before the feed
  and 24 relation-set summaries; 7,864 change-set entries keep no subject (their records were only
  in discarded change sets) and read "a record since removed". Started with a scratch key, so the
  copy's signing keys were replaced on it to issue tokens (see the TODO above).
- **Timing (D347), on that copy:** a client changed 200 records, then 2,000 by batch; `GET /changes`
  for it, best of five: first page 15 ms at 200 entries, 11 ms at 2,200, page 31 12 ms; everyone's
  first page over 51,000 entries 10 ms; filtered by kind and workspace 11 ms.
- **Frontend:** Vitest `src/features/changes`, `src/features/home`, `src/features/security`,
  `src/ui`, `src/routing`, `src/app`, `src/features/objects/panels` — 33 files, 284 tests passed;
  Prettier on the changed files, lint (0 errors, the 8 listed warnings), build.
- **Browser:** `z6-changes` 12 checks on two models, axe 0 on the Changes page (a Reader, dark,
  390px) and on Home; `hm1-home` 11 checks; `sp1-security` 46 checks on two models. Screenshots
  inspected against the boards: Home's Your recent changes at 1440px, a Reader's view of Ana's
  changes, Your changes in dark with the filters, the page at 390px with the filters stacked and a
  16px gutter.
- **Full backend suite** (Track Z's, the user, 2026-10-24; stands for Z1–Z5's): `-n 6`, 6,348
  passed and 5 failed in **13 min 9 s, over the 11-minute ceiling** (TODO); the serial part, 5
  passed. The five, each named:
  - `test_batch_statements` live creates and upserts (36 > 35, 50 > 49 statements per chunk), the
    same on `56903d2`: Z4's `requestedBy` names a job's requester in the batch's response, one
    statement per chunk whatever it holds. The budgets gained one, as I1's did; 14 passed.
  - `test_consumer_xref_volume` (28 statements → 23 between sizes), the same on `56903d2`, and
    `test_consumer_event_volume` (only in the full run): since Z3 (D266) the consumer index takes the
    management token, so `volume_app`'s warm-up no longer obtained the consumer token and the first
    consumer read measured paid for it. `volume_app` asks for the consumer token directly; the 23
    modules using the volume fixture, 255 passed.
  - `test_build07_wp6::test_selected_capture_keeps_active_identity_and_snapshot_retry`: failed only
    under the full run's load, passed alone and in its group (`model_admin`, 387 passed); its message
    was not kept. A flake, cause not found (TODO).

**Composable domains (ADR-032):** the audit and provenance door, as planned: entries gain where
they were made and what they changed, beside the actor and cause; values stay out of the read.

**What the user will still not be able to do after Z6:** see what waits for their approval (A3); open
a client's changes from a client's page (SP2; from a name in a record's history until then); see the
values a change wrote in the list (a record's history has them); export the list (not planned); see
model-to-model mapping operations in it (the mapping's own history has them).

### HM1: A home page after sign-in

**Needs:** Z5. _Added by the user, 2026-10-25,_ choosing a personal home page over workspace icons
alone or opening a record at once: "add the option 3 to the build 0.12 as a workpackage and start
delivery".

**Scope:** signing in, or opening the bare address, lands on a home page instead of the first
application's default list. It shows the workspaces the person can open as large cards (each with
its model and its applications), what waits for them in each (their open change sets; for those who
publish, every open change set), their change sets across workspaces, and a link back to where they
left off. Supersedes 0.14's UP2 for the first screen (D336).

##### HM1 plan (2026-10-25)

**Planned 2026-10-25; accepted by the user the same day** ("yes you can build this"), after the boards were redrawn at the user's request ("more nice and lovely like usually the other pages"): D331–D337, the test cases and the "HM1 as planned" boards. Checked against the code at `56f090d`
with Z5's plan and record, D321–D330, and 0.14's UP2.

**What the check found:**

- **The first screen:** `defaultRoute` (`routing/routes.ts`) opens the first application's default
  view in the opening workspace (D326: the default when browsable, else the first by label); with no
  workspace, `NoWorkspace`. The product name in the top bar (`onHome`) goes to the same route. Since
  0.11 each workspace may run its own model, so "the first application" depends on which workspace
  opened.
- **Settings and `NoWorkspace` already open without a workspace model** (Z5): the top bar then shows
  the product and the settings button without applications. A home page needs the same, since its
  cards span workspaces with different models.
- **What the API has:** `GET /workspaces?holding=browse` (D327) lists the workspaces; each carries its
  release's name and version but not its applications. `GET /workspaces/{key}/change-sets?createdBy=`
  (D325) finds a person's change sets in **one** workspace; published and discarded change sets are
  deleted, so the list holds the open ones. A change set's size is two more reads
  (`object-changes` and `relation-changes` with `includeTotal`), as `useOwnChangeSet` does. A card
  with applications, counts and change sets would cost about four reads per workspace.
- **Nothing records what a person opened.** No favourites, no recently opened records, no
  "last address" anywhere.
- **Not built yet:** one person's changes across workspaces (Z6) and approvals waiting for someone
  (A1–A3).
- **Browser runners opening the bare address:** five (`w4-workspace-admin`, `workspace-m5`,
  `workspace-m6-checkpoint`, `z5-permissions`, `helpers/workspace-surfaces`); all but two name
  `?workspaceKey=`, which keeps opening that workspace (D331), so only `w4-workspace-admin:152` and
  `z5-permissions:85` change.
- **Reference patterns:** `ShellFrame` and `TopBar` without applications (Settings, `NoWorkspace`);
  `NoWorkspace` itself as the empty state; the change sets list's rows; `Notice`.

**Mock-up:** [security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), row "HM1
as planned": the home page at 1440px (a Data steward in three workspaces with two models; dark in
Tweaks; a Reader with one workspace in Tweaks) and at 390px.

**What is built:**

1. **API** (documented in API.md, OpenAPI lock re-baselined from a diff):
   - `GET /me/workspaces` (D332): the workspaces where the caller holds Browse, active only, the
     default first and then by label, cursor paged. Each: key, label, `isDefault`, its model
     (release name and version), its `applications` (key, name; from the workspace's release, the
     model the engine already resolves per workspace), `ownChangeSets` (the open change sets the
     caller created) and `openChangeSets` (all open change sets there, only where the caller holds
     Publish, otherwise `null`). Counts are one grouped statement per page, not per workspace.
   - `GET /me/change-sets` (D333): the open change sets the caller created, across the workspaces
     where they hold Browse, newest change first, cursor paged. Each is the change set as
     `GET /change-sets/{id}` returns it plus `workspaceLabel` and `changeCount` (records and
     relationships it changes, counted in SQL for the page).
2. **The home route** (D331): `/` without `workspaceKey` is `{ kind: "home" }`; after sign-in with no
   address asked, and the product name in the top bar, lead there. `/?workspaceKey=<key>` opens that
   workspace as today. Home opens without a workspace model, as Settings does.
3. **The page** (D337), in `features/home/`, in the reworked Account page's style (the hero card
   with its band, tiles, pills, rows): a **welcome card** ("Good morning/afternoon/evening, *first
   name*" from `/me` and the browser's clock; one sentence from the counts, such as "Three workspaces
   are yours to work in. Two of your change sets are open, and five change sets wait for someone to
   publish them."; the person's roles as pills, from `GET /me/grants`) beside **Continue where you
   left off** (D334) when there is an address to return to; **Your workspaces**, a grid of cards
   (three across at 1440px, one at 390px): a large two-letter tile in a colour taken from the
   workspace's key, the label, "Default" on the default one, the model's name and version, the
   person's role there, each application as a link opening its default view there, and a footer of
   two figures, "*n* your change sets" and, for a publisher, "*n* open change sets to publish", each
   opening that workspace's change sets, or "Nothing open here" with a line on what the role can do;
   **Your change sets**, rows of name, workspace and model, "*n* changes" and when it last changed,
   each opening its review; shown only when there is one, 20 at a time with Load more. With no
   workspace, `NoWorkspace`'s content is the page, unchanged.
4. **Continue where you left off** (D334): the browser keeps the last data address the person opened
   (a list, a record, a group, a change set's review or a publication), per person, in local storage;
   the link names the application, view or record type and the workspace. It is shown only when the
   workspace is still among the cards; an address whose view has gone falls back as any address does.
5. **Startup** (D326 narrowed): the "which workspace opens first" rule now serves only an address
   that needs a workspace and names none (an `/apps/…` address without `workspaceKey`).
6. **Documents:** API.md (the two reads), USER_JOURNEYS (J45 new), API_JOURNEYS,
   CURRENT_FUNCTIONALITY, PRODUCT (the first screen), SETTINGS_AND_UI_PLAN (the home page),
   UI_ACCEPTANCE (Home's state row), EXECUTION_GUIDE (the new runner), 0.14's UP2 (superseded, D336),
   Z6's and A3's scope (their sections on Home, D335), CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D331 | When the home page shows | **Recommended:** always after sign-in (when no address was asked), on the bare address and from the product name, including for a person with one workspace. An address naming a workspace, application, view or record opens it as today; `/?workspaceKey=<key>` keeps opening that workspace. Why: a page that appears only sometimes is hard to find again, and the first screen stops being a list nobody chose (UP2's complaint). _This differs from the chat answer of 2026-10-25,_ which skipped Home for one workspace and nothing waiting; the reason to change is that the product name must lead somewhere stable. Cost: a person with one workspace clicks once more (Continue, or an application on the card) |
| D332 | One read for the cards | **Recommended:** `GET /me/workspaces`, the workspaces where the caller holds Browse with their applications and two counts. Why: about four reads per workspace otherwise; an integrator's journey too (a client asking where it may work and what it has open). It sits under `/me` because the counts are the caller's. Cost: one route; `GET /workspaces?holding=browse` stays for the selector |
| D333 | The person's change sets across workspaces | **Recommended:** `GET /me/change-sets`, newest change first, with each one's workspace label and change count. Why: the list on Home without one read per workspace and two per change set; a client continuing its own work anywhere. Change sets stay shared (D255); this only finds the caller's. Cost: one route; the count is two grouped counts per page |
| D334 | Where "Continue where you left off" is kept | **Recommended:** in the browser, per person (local storage keyed by the person's ID): the last data address opened. Why: it is navigation state like a remembered tab; no integrator journey needs it, and a server store would write on every page opened. Cost: it does not follow the person to another browser or device, and clearing site data forgets it |
| D335 | What Home leaves out until its package | **Recommended:** nothing is shown as a placeholder (D323). **Your recent changes** arrives with Z6 (its read for the signed-in person), **Waiting for your approval** with A3. Recently opened records are not planned: they need a server store of every record opened. Cost: Home is workspaces, change sets and Continue until Z6 |
| D336 | 0.14's UP2 | **Recommended:** superseded for the first screen; UP2 is closed in 0.14's plan with a pointer here. Switching application inside a workspace keeps opening its default view. Why: UP2 asked that the first screen not be a list nobody chose; Home answers it. Cost: an application still opens on its default view when switched to; UP2 can be reopened for that alone |
| D337 | What a card shows | **Recommended:** a two-letter tile from the label in one of a few soft colours picked from the workspace's key (the same workspace always gets the same colour, in light and dark), the label, "Default" on the default workspace, the model's name and version, the person's role there, the applications as links, and the counts as links to the change sets. The default first, then by label; retired workspaces not shown. Above the cards, a welcome card with the person's name, one sentence from the counts and their roles. Why: the user's "big icons" and "nice and lovely" (2026-10-25), with what makes a workspace worth opening; with per-workspace models (0.11) the applications differ by card. Cost: three tile colours in the tokens (light and dark, ink at 4.5:1); the role per card comes from `GET /me/grants`, one read |

**Journey test cases** (`tests/journeys/test_j45_home.py`, J45 "Start from home", on two
configurations, each workspace of a case on a different model where the case has two; written first
and seen failing):

1. **J45.1, the workspaces I can open:** given a person who is Reader in A, Data steward in B and has
   no role in C, and a Security administrator with no data role, when `GET /me/workspaces` is read,
   then the person sees A and B (the default first), each naming its own model's applications; A's
   `openChangeSets` is `null` and B's counts every open change set; the administrator sees none; a
   retired workspace the person may browse is not listed.
2. **J45.2, what is mine:** given the person creates a change set in B and changes two records and one
   relationship in it, and another person creates one in B, when both reads are taken, then B's
   `ownChangeSets` is 1 and `openChangeSets` 2, and `GET /me/change-sets` lists the person's one with
   `changeCount` 3 and B's label.
3. **J45.3, it follows the work:** given the same change set, when it is published, then it is gone
   from `GET /me/change-sets` and both counts drop; when the person's role in B is removed, B and
   their change sets there are gone on the next request.
4. **J45.4, a client:** given a client holding Contributor in A that created a change set there, when
   it reads `GET /me/change-sets`, then it sees its own change set and no one else's.

Unit tests (Vitest): the home route (`/` with and without `workspaceKey`, `routePath`); the
continue-address store (per person, another person's ignored, an unparseable entry dropped, a
workspace no longer listed hides the link); a card's lines (no counts, a Reader's `null`, one and
several).

**Browser** (a new runner `hm1-home`, on two models; reference patterns: `ShellFrame`/`TopBar`
without applications, `NoWorkspace`): signing in lands on Home; two workspaces' cards name their
own models' applications and one opens its view; after opening a record, the product name returns
Home and Continue reopens the record; a Contributor's change set is listed with its count and opens
its review; a Reader's card has no open change sets count; a person with no workspace sees the
no-workspace text at `/`. Keyboard from the first card's application through Continue; 390px; axe;
screenshots of Home at 1440px light and dark and at 390px, inspected against the boards.

**Checks:** the new journey module, `test_openapi_contract` with the lock diffed,
`test_api_journeys`, `test_boundaries`; Ruff on the changed files; Vitest for `src/app`,
`src/routing`, `src/features/home`, `src/features/workspaces`; format, lint, build; the runners
`hm1-home`, `z5-permissions` and `w4-workspace-admin` (their bare-address steps), `u3-settings` (the
top bar), each named with its result. No migration.

**Composable domains (ADR-032):** no door is touched: two reads for the caller over existing
workspaces and change sets; no identity, attribute storage, audit, bulk or consumer contract changes.

**What the user will still not be able to do after HM1:** see their recent changes on Home (Z6) or
what waits for their approval (A3); pin a record or a view to Home (not planned); have Continue
follow them to another browser (D334).

##### HM1 record (2026-10-25)

**Delivered 2026-10-25.** Everything in the plan, with the boards' layout; the user looked at the
page during the package and asked for three changes, made in it (below).

**What was built:**

- **API:** `GET /me/workspaces` (`management/routers/workspaces.py`, the cards from
  `management/projections/home.py`: applications from each workspace's own release, both counts in
  one grouped statement per page) and `GET /me/change-sets` (`management/routers/change_sets.py`,
  each change set's size from `engine/reads/change_lists.count_changes`, the totals of its two change
  lists in one statement, so Home's count and Z5's band agree); `product` on `GET /system` (D338).
  API.md, the OpenAPI lock (diffed against `56f090d`: the two routes, `product` and their six
  schemas, nothing else) and the paged-collections inventory (56 → 58).
- **Browser:** the home route (`{ kind: "home" }`, `/`; `isApplicationRoute` where the router and
  the shell meant "not Settings"), `features/home/` (the page, its text and the Continue store), the
  product name and Settings' product mark leading Home, `styles/home.css` on the Account page's
  panels and pills (`account-pill.warning` added beside `success`).
- **Documents:** API.md, USER_JOURNEYS (J45, J45.1–J45.5), API_JOURNEYS, CURRENT_FUNCTIONALITY (F02),
  PRODUCT, SETTINGS_AND_UI_PLAN, UI_ACCEPTANCE (HM1-1), EXECUTION_GUIDE (`hm1-home`), 0.14's UP2,
  Z6's and A3's scope, CHANGELOG, PROJECT_STATUS.

**Decided within the approved package:**

| # | Question | Decision |
| --- | --- | --- |
| D338 | What a person with no workspace sees in the top bar | _Reported by the user during the package:_ the empty model was named after the release ("… Example"), not the product everyone else sees. **Decided:** `GET /system`, readable by anyone signed in, names the instance's product (the default workspace's model's `product`), and the top bar reads it when the model itself is closed to the person. Why: the instance's name is not data of a workspace. Cost: one optional field on `/system`; J31's key list gains `product` (an older approved case changed for the contract it pins, named here) |
| D339 | What a workspace's name on its card opens | _Asked by the user during the package_ ("the workspace admin … or opening the first application?"). **Decided as recommended:** the workspace at its start, the first application's default view, as `/?workspaceKey=` does. Why: most people on Home read or change data; workspace administration is offered only to whoever holds it (D323) and stays one click away in Settings. Cost: an administrator opens the workspace's page from Settings |
| — | The counts under a card | _Asked by the user:_ "these somehow can be like buttons". Each figure is a bordered, raised link with its label and a chevron, opening the workspace's change sets; the boards drew them as plain figures |
| — | The tile's colour (D337 named three new colours) | The type palette's eight hue slots (`[data-hue]`, light and dark, ink checked by `tokens.test`), picked from the workspace's key; no new tokens. Why: one palette, already contrast-checked (U-D14) |
| — | Continue's icon | `undo` (a turning arrow), the icon set having no history icon |
| — | Before anything was opened | The welcome card takes the whole row; Continue appears once an address is remembered |

**Found on the way and fixed:** a browser runner's starter seed built on an older schema seed was
reused after the schema seed was rebuilt with the same inputs (the harness client is made anew each
build), so its backend refused the harness client (`401 invalid_client`); `z5-permissions`' second
model failed so. `tests/seeds.py` now rebuilds a seed whose base was built after it.

**Where it differs from the plan:** Continue's title for a list is the view's name and its second
line the workspace; a card whose model this version cannot serve says so instead of listing
applications; the summary reads "… workspaces are open to you" for every role (the board's "yours to
work in" does not fit a Reader).

**Checks:**

- **Journeys:** J45 (5 cases × 2 configurations) seen failing before the routes existed (8 of 8 for
  J45.1–J45.4), then passing; with J31: 22 passed.
- **Contract:** `test_openapi_contract`, `test_api_journeys`, `test_boundaries`, `test_paging_contract`:
  passed (51 + 11 after the first lock, 20 after `product`).
- **Ruff** on the changed backend files: clean.
- **Vitest:** `src/app`, `src/model`, `src/routing`, `src/features/home`: 14 files, 173 tests passed;
  two App cases that opened `/` and expected a list now open `/?workspaceKey=default` and an
  application address without a workspace (D331 changes what `/` means).
- **Frontend:** format (changed files), lint (0 errors; the 8 listed warnings), build: passed.
- **Browser:** `hm1-home` 11 checks, axe 0 on Home at 1440px light and dark and at 390px;
  `z5-permissions` 26 checks on both models (step 4 now finds the second workspace on Home, then
  an application address naming none); `w4-workspace-admin` 21 checks (step 8 reads the default
  first on Home and opens it); `u3-settings` 10 checks. Screenshots inspected against the boards:
  the welcome card, Continue, tiles, application chips, the count buttons and Your change sets at
  1440px light and dark, a Reader's single card at 390px with a 16px gutter.
- **Not run (build acceptance):** the full suites, `test:a11y`, `test:visual` (Home has no baseline
  yet), other runners.

**Composable domains (ADR-032):** no door is touched.

**What the user will still not be able to do after HM1:** see their recent changes on Home (Z6) or
what waits for their approval (A3); pin a record or view to Home (not planned); have Continue follow
them to another browser (D334).

### HM1a: Home's workspace tile and Continue

**Needs:** HM1 (delivered). _Added by the user, 2026-10-25,_ during LS1's delivery: "on the home page
the workspace cards have a link to the workspace … I would like that their icon (initials) have this
link too. I also would like that the continue where you left off has a bit different shade of
background (also then reflecting this to the dark scheme)".

**Built, 2026-10-25:** a workspace card's tile (its initials) opens the workspace as its name does,
out of the tab order and hidden from assistive technology, so keyboard and screen-reader users meet
one link per workspace, as before. Continue where you left off sits on a soft tint of the action
colour with a border to match (`--home-continue-surface`, `--home-continue-border`), its own value in
dark, held to AA for its text and 3:1 for the focus ring in `tokens.test.ts`. No decision was needed.
`hm1-home` passed on `ebd2a2a` with this session's files, axe clean in light, dark and at 390px.


### RH1: A record's history, shorter and with its values

**Needs:** 0.12 Z4 (actors, delivered). _Added by the user, 2026-10-25:_ "for the history of the
records. its a free long list on the records page, I would like to make it somehow a better ux";
the recommendation (compact entries by day, filters, paging) and the
[history and activity mock-up](https://claude.ai/artifact/CFS7AtndnBosJ7yjdksVLr) accepted ("okay",
twice), and old → new values chosen over D16 (below).

**Scope:** a record's history groups its changes by day, one line each, opened for the old and new
values; it is filtered by kind and by person, and shows the 10 newest, then 20 more at a time.

##### RH1 plan (2026-10-25)

**What the check found:** `GET /objects/{type}/{id}/history` answers each entry's action, the field
names and attribute keys it changed, its actor and cause, never values (D16 of 0.9). A record write
stores the new values in the entry (`changes.attributes`) and a name or parent change both ends
(`{"from", "to"}`); a change set's edit stores the record's whole attribute set; a publish's entry
and a type change store names only (D15, ADR-034). Live values are not versioned. A relationship's
entry names its type and both ends (`subject`). The panel (`HistoryPanel`) reads 20 at a time and
appends without end.

**What is built:**

1. **API.** The history read takes `kind` (`values`, `relationships`, `structure`: a parent or type
   change) and `actorId` (a person's or client's ID, or `engine`), both filtered in PostgreSQL, and
   answers on each entry `kind`, `values` (each changed field's `from` and `to`, with `fromKnown`)
   and, on a relationship's entry, `related` (the relation type, the direction read from this
   record, the other record's ID, type and current name). A parent's ID is answered with its name.
2. **The values** (D390): `to` is what the entry stored; `from` is what the record's previous entry
   in the same context stored for that field, found in one query per page (`LATERAL`); where that
   entry stored names only, `fromKnown` is false and the page says the earlier value was not
   recorded. A field whose `from` equals its `to` is left out.
3. **The panel.** Entries by day, one line each (what, who, when), opened for the values; the kind
   chips and a By choice of the people seen so far; the 10 newest, **Load older history** adds 20,
   **Show fewer** returns to 10. Day groups live in `ui/Timeline`, so a person's recent activity and
   their changes across workspaces (Z6) are grouped by day too.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D389 | Values in a record's history (**revises D16** for history) | **Accepted by the user, 2026-10-25:** a record's history answers each changed field's old and new value, to whoever may read the record; the change feed and consumer events stay names only. Why: "Code changed" alone sends people looking for what it was. Cost: a later redaction (the erasure door, COMPOSABLE_DOMAINS) must also clean the values the audit log stores, which that section now says |
| D390 | Where an old value comes from | **Recommended:** the record's previous entry in the same context (live, or the change set) that named the field; unknown where that entry stored names only (a publish, a type change), never guessed. Why: live values keep no versions; a wrong old value is worse than none. Cost: after a publish, the next change's old value reads "not recorded" |
| D391 | Filtering | **Recommended:** by `kind` and `actorId` in the API, the panel's chips and By choice over it. Why: filtering only the loaded entries would show wrong or empty lists with Load more; every capability is in the API. Cost: two query parameters |
| D392 | Names in relationship entries | **Recommended:** the other record's current name, its type and the relation's name read from this record ("Offered in French added"); a parent by its name. Why: an ID tells a person nothing. Cost: a name lookup per page; a record renamed since shows its new name |
| D393 | Paging and day groups | **Recommended:** the 10 newest, 20 more at a time, Show fewer; day headings in `ui/Timeline` for every timeline. Why: the app's other feeds load more by a button; day headings shorten a long list. Cost: recent activity and Z6's list change look with it, before their own package |
| D394 | What RH1 leaves out | **Recommended:** a publish's values (they stay in the change set's own history); a list of every person who ever changed the record (By offers those seen so far); recent activity's filters (RA1, after I3). Cost: as listed |

**Test cases:** API journey: a record edited live twice, a relationship added, moved, read with its
values (old and new, the first value's old empty), filtered by kind and by person; a change set's
edit and its publish, the next live change's old value not recorded. Unit: `ui/Timeline` (day
groups), `HistoryPanel` (paging, Show fewer, filters, an entry opened).

##### RH1 record (2026-10-25)

**Built 2026-10-25,** everything in the plan; a person's recent activity followed the same day as RA1
(below), at the user's reminder ("the Recent activity is still not yet fixed though I highlighted
that too"). One check waits for I3 (below).

**What was built:** `engine/records/history_details.py` (the kind, `kind_condition` for the filter,
the values with one `LATERAL` query a page, the other records' names); `object_history`'s `kind`
and `actor_id`; `HistoryValue`, `HistoryRelated` and `kind`, `values`, `related` on
`AuditEventResponse`; the route's `kind` and `actorId`. In the browser: `ui/Timeline`'s `byDay`
(day headings, one line per entry, an entry opened for its `details`), `byDay` and `dayLabel`
moved to `lib/dates` from the Z6 page (re-exported there), `HistoryPanel` rewritten (the `Choice`
of kinds, By, 10 then 20, Show fewer, the values table). Documents: API (the history read), DECISIONS
(ADR-037 amended), COMPOSABLE_DOMAINS (History and erasure), CURRENT_FUNCTIONALITY (F11),
USER_JOURNEYS (J01.6), EXECUTION_GUIDE (the module's row), CHANGELOG.

**Checks:**

- **Backend**, in the worktree of `a11f71e` with only RH1's files, against the development
  PostgreSQL server: J01.6 (extended: values, the first value's old empty, kinds, the other record,
  both filters, the old value not recorded after a publish), J15 and J44, both models: 36 passed.
  `test_boundaries`, `test_api_reference`, `test_api_journeys`: passed.
- **The OpenAPI lock:** `ebd2a2a` with RH1 hashes to `a1b97453e10e…`, and with RH1 and SP1b to
  `3de8ab1dff7e…`; diffed against `ebd2a2a`, only RH1's and SP1b's paths and schemas are new. The
  shared tree's lock holds I4a's value (`ebd2a2a` with I4a alone), so whichever is committed second
  re-baselines on top of the other.
- **Browser runners** reading the history panel, changed to the new lines (a line opens to show who
  made it, with the link): `sp1-security`, `z6-changes` and `c5-restructuring-acceptance` passed.
- **Frontend:** `src/features/objects`, `security`, `changes`, `src/ui`, `src/lib`, `src/api`: 62
  files, 468 tests passed (new: the values with "not recorded", the kind asked of the API, Show
  fewer); typecheck, lint and format on the changed files clean.
- **Not run:** a browser runner (no runner covers the history panel's look; the user tries it).

**Composable domains (ADR-032):** the erasure door is touched and kept open: the values the history
shows are those the audit entries already stored, the one other place a redaction must reach, which
COMPOSABLE_DOMAINS now says (D389).

**What the user still cannot do after RH1:** see a publish's values in the live history (the change
set's own history has them, D394); pick a person who has not appeared in the loaded entries in By.

### RA1: A person's recent activity, like the history

**Needs:** RH1. _Asked by the user, 2026-10-25,_ with RH1 ("I would like to limit the visibility of the
recent activity on the user page since it can get very long"), the
[mock-up](https://claude.ai/artifact/CFS7AtndnBosJ7yjdksVLr)'s second screen accepted.

**Built, 2026-10-25:** `RecentActivity` on `ui/Timeline`'s `byDay`; the kinds **Signing in**
(`sign-in`), **Roles and groups** (`grant`, `group`, `role`) and **Account** (`user`, `client`) as
the API's existing `aggregateType` filter, All asking for every kind (keys and providers too); the
10 newest, then 20, Show fewer, through `ui/TimelinePaging`, which `HistoryPanel` now uses too (one
paging, no copy). No API change and no decision beyond RH1's D391 and D393. Its one change in
`api/securityClient.ts`, a file I3 also edits, is the `securityEvents` call.

**Checks:** Vitest `src/features/security`, `src/features/objects/panels`, `src/ui`: passed, with
`RecentActivity.test.tsx` (10 then 20, Show fewer, a kind asked of the API); typecheck, lint and
format clean. `sp1-security` and `sp2-clients` passed once their activity locator named the group
(the day groups hold a list each).

### SP1b: A group's members, several at once

**Needs:** SP1, I3. _Asked by the user, 2026-10-25:_ "for the group membership dialog, please make it
more realistic than just a dropdown list for picking users one by one"; the
[group members mock-up](https://claude.ai/artifact/VpWrqXLoAUfXpSFtScpnu3) accepted ("yes the mock
looks good"). Decision numbers D401–D403 leave D395–D400 to I4, which was numbering in parallel.

**Built, 2026-10-25:**

- **API.** `POST /groups/{group_id}/members/batch` (`userIds`, `identifiers`, `dryRun`) and `POST
  /groups/{group_id}/members/removal` (`userIds`), answering each input's outcome and how many
  changed (`GroupMembersResult`); the people read in one query, the memberships written in one
  statement, one security event per member (`administration.add_members`, `remove_members`).
- **The page.** **Add members** opens `AddMembersDialog`: **Search and tick** (the first 20 matches,
  each asked of the engine with `dryRun`, so those already in and the deactivated are shown and not
  tickable; Tick all shown) and **Paste a list** (checked with `dryRun`, the people found joining the
  people to add, every line saying what it is); the people to add as chips under both tabs; one
  request adds them. The members table gains a checkbox column (`SettingsTable` takes a control as a
  column head) and the selection bar's **Remove N from the group**; Remove on a row stays.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D401 | How several people join a group | **Recommended:** up to 500 in one transaction, by ID or by username or e-mail address in any case, checked first with `dryRun`; people already in the group are answered, deactivated people left out and said so, a line nobody has said so. Why: the mock-up's two ways (search and tick, paste a list) share one call, and checking first shows what will happen before anything changes. Cost: a deactivated person can still be added alone with the one-person call, as before |
| D402 | Removing several members | **Recommended:** ticked and removed together, refused whole when it would leave no Security administrator (D283); Remove on a row stays. Why: the same rule as one removal, so nothing is half done. Cost: none |
| D403 | What SP1b leaves out | **Recommended:** a person's page keeps adding one group at a time (its page is in I4's work); the search offers the first 20 matches and asks to narrow beyond them. Cost: as listed |

**Checks:** API journey J40.4 (`test_several_people_join_and_leave_a_group_at_once`: a pasted list
checked, three added by ID with the deactivated one left out, two removed with an unknown ID), both
models; Vitest `AddMembersDialog.test.tsx` and the `security` group; the `sp1-security` runner walks
the dialog (search and tick, a pasted list with an unknown line, axe) and `i3-sign-in-providers`
finds no Add members on a provider group.

**Record (2026-10-25):** delivered as above, in a worktree of `ebd2a2a` with this session's files:
J40 and J40.4 66 passed on both models; `sp1-security` and `i3-sign-in-providers` passed, axe
clean; the contract group passed but the OpenAPI lock (RH1's record) once `API_JOURNEYS` listed both
routes; Vitest `src/ui`, `src/lib`, `src/features/objects`, `security`, `changes`, `home`,
`src/styles`, `src/api` 66 files, 492 tests passed in the shared tree; the build passed. The new
routes, schemas and fields are the only differences of the API document from `ebd2a2a`'s.
**Composable domains:** no door touched. **What the user still cannot do:** add a person to several
groups at once from their page (D403).

### TV1: A record's parent in its list

**Needs:** 0.9 K5 and K6 (delivered). _Added by the user, 2026-10-25,_ during SP2's delivery: "on the
collections table views, when its possible to add filter, I miss the filter about the parent and also
maybe adding the parent in a column in the table view, so it is filterable"; after the check below,
"we can start with your proposal … add this to 0.12 to track and build this up on the same go".

**Scope:** a table view's Columns… and Filters… in the layout editor offer the listed type's
relationships, so a list of records under a parent shows which parent each belongs to and is
filtered by it.

##### TV1 plan (2026-10-25)

**Planned and accepted 2026-10-25** in the user's words above, the proposal being the per-relationship
choice (D358, D359); D360 is recorded as recommended. Checked against the code at `20bfd27`.

**What the check found:**

- **The engine already serves it.** A table view's `columns` and `filterFields` take
  `related:<key>`, a relation type's key read from the `from` end or its reverse key read from the
  `to` end (0.9 K5, D140; K6, D153–D158). The model validates them
  (`validation/application_rules.py`: a filter names the relationship alone, a sort only a column
  whose row holds one), the list expands them, and the filter bar offers "is any of / has none /
  has any". A parent is a relation type marked `parentOf`, named in the child's
  `behavior.parentRelationTypeKeys`.
- **Nothing in the interface chooses them.** The layout editor's Columns… and Filters… for a table
  view offer the name and the type's attributes only (`model-editor/layout.ts`, `viewChoices`); a
  relationship column or filter could be written only in the model file.
- **A type may have more than one parent relationship** (a record under a parent of another type, or
  under one of its own type), so one relationship's column is empty for records under the other.

**What is built:** `viewChoices` adds every relationship the type takes part in, read from its side,
as `related:<key>` (from the `from` end) or `related:<reverseKey>` (from the `to` end), the ones in
`parentRelationTypeKeys` first, labelled as every relationship column is: the relationship's name in
that direction. Columns… and Filters… both read it; the engine, the list and the filter bar are
unchanged.

```text
Columns of <view>                       The list after Apply
  [x] Name                                Name ↑   Code   Active   Belongs to <parent type>
  [x] Code
  [x] Active                            ＋ Filter → Belongs to <parent type> → is any of …
  [ ] Belongs to <parent type>   ← parents first
  [ ] Has parent <same type>
  [ ] <other relationships>
```

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D358 | What Columns… and Filters… offer | **Accepted:** the name, the type's attributes, then each relationship the type takes part in, read from its side, the relationships to a parent first. Why: the engine lists and filters by any relationship; a parent is the one people asked for, so it comes first. Cost: a longer list of choices on a type with many relationships |
| D359 | One column per parent relationship, or one "Parent" column | **Accepted:** one per relationship, headed by the relationship's name read from the record ("Belongs to …"), as every relationship column already is; renaming the reverse name in the model changes the header. Why: no engine change; a filter picks records of one type. Cost: a type with two parent relationships needs two columns, each empty for records under the other. One "Parent" column across them is new engine work (a read and a filter across relation types), left until it is asked for |
| D360 | Sorting by the parent | **Recommended:** not in TV1. The default sort chooser picks among the view's sort fields and has no way to add one; making a single-record relationship column a sort field (the engine allows it, D145) is a small later step. Cost: a list cannot be sorted by its parent from the interface yet (the model file can) |

**Test cases:** unit (`layout.test.ts`): a child type's Columns… and Filters… offer its parent
relationship before its other one, labelled by name, and choosing it inserts `related:<reverseKey>`.
Browser (`authoring-a4b`, both designer models): a type under a parent given its parent as a column
and a filter from Columns… and Filters…, the draft holding both, then installed and activated.

##### TV1 record (2026-10-25)

**Delivered 2026-10-25.** Everything in the plan.

**What was built:** `relatedChoices` beside `viewChoices` (`frontend/src/features/model-editor/layout.ts`);
the unit case in `layout.test.ts`; a step in `e2e/authoring-a4b-preview-layout.mjs` (`childView`
picks the first table view of a type under a parent, read from the model). Documents:
CURRENT_FUNCTIONALITY (the layout editor), EXECUTION_GUIDE (the `authoring-a4b` row), CHANGELOG.

**Checks:**

- **Vitest:** `src/features/model-editor`, `src/model`: 19 files, 216 tests passed.
- **Frontend:** format and lint on the changed files clean; typecheck clean; build passed.
- **Browser:** `authoring-a4b` 31 checks (29 before, plus the new step on both models), the drafts
  with the parent column and filter installed and activated; the screenshot of the codelist-shaped
  starter type's layout inspected: "Belongs to …" among the column frames and in the preview's
  table header.
- **Not run:** backend tests (no backend change); other runners.

**Composable domains (ADR-032):** no door is touched.

**What the user will still not be able to do after TV1:** sort a list by its parent from the
interface (D360, the model file until then); show one "Parent" column for a type with several parent
relationships (D359, not planned).

### LS1: A collection's rows scroll on their own

**Needs:** 0.11 X6 (delivered). _Added by the user, 2026-10-25:_ "scrolling it immediately laggy …
200 timetable types, with some language relations … if it's laggy for 200 records … what could we
expect for a larger set?", asking for a code review and a solution, not more measuring. After the
review: "I accept the decision", then, on how the page would avoid the sidebar scrolling away and
columns ending at different bottoms, the layout below; "ok"; "add this to the build 0.12 then deliver
it".

**Scope:** a collection's table page is fitted to the window: the window does not scroll, the rows
do, and every row drawn while scrolling is drawn once. The reader's wheel goes straight to the
browser.

##### LS1 plan (2026-10-25)

**Planned and accepted 2026-10-25** in the user's words above, with the
[scrolling mock-up](https://claude.ai/artifact/SGjSLyQJfEGcWk2SKpAEu3) (laptop with 200 records,
laptop with 9, phone). D371–D376 are recorded as recommended. Checked against the code at `9c702d7`
by reading it; nothing was measured.

**What the review found** (most serious first):

1. **Pointing at a cell while scrolling draws the table again.** Rows moving under a still pointer
   fire `pointerover`; `ui/CellReveal` measures the cell (layout reads, text ranges, a clone) and,
   where it is cut, sets state held in `DataTable`. `DataTable`'s `secondary` is a new function at
   every draw and goes to every row, so the row memo (X6) never holds: every drawn row, about three
   screens, draws again, and the scroll listener closing the box draws them a second time. The
   hovered row's edit icons are drawn for each row passing under the pointer.
2. **Any draw of the page draws every row.** `ObjectTable` builds its columns, row attributes,
   selection and actions anew at each draw, `useCellEditing`'s `renderCell` and
   `useRecordSelection`'s `isSelected` are new each time: 200 records at the page size of 20 arrive
   as eleven background pages after the list opens, each drawing every drawn row again.
3. **The wheel waits for the script.** `ScrollWindow`'s wheel listener is not passive and reads the
   layout at each event (`getComputedStyle` up the ancestors, `scrollHeight`, a bounding box), so
   the browser holds every scroll step until the main thread answers, which 1 and 2 keep busy.
4. **The layout is read at every scroll frame.** The window's layout effect lists `virtualRows`, a
   new array at each range change, and calls `measure()`, which reads sizes right after rows were
   written: the table is laid out again in the middle of the frame.
5. **Row heights differ.** Cells wrap, so each new row is measured and the scroll position corrected
   where it differs from the estimate.

**What is built:**

1. **The page fitted to the window (D371).** On a collection's table page (the `list` route of a
   table view), `ShellFrame` gives the frame a fill layout through its `main` option (the model
   editor's, D37): the frame is the window's height; the top bar, the band, the page header, the
   lenses, the toolbar and the selection bar keep their heights; the collection's card takes the
   rest down to the window's bottom, also when it holds few rows; the table's header stays at the
   card's top and its footer (range, Go to, page, start and end) at its bottom. The rail keeps its
   own scroll. On a phone the same, the band and the top bar included (they scroll with the page
   today). The split view (a record beside its list) and every other page keep their layout.
2. **One kind of scrolling per window (D372).** `ScrollWindow` takes `fill`: a window that fills its
   page has no wheel handler, only passive listeners noting the reader's gestures. A window nested
   in a page that scrolls (a record's panels, dialogs, the model editor's preview, the split view)
   keeps today's wheel behaviour, with the scroller around it found once per gesture instead of at
   every event.
3. **A row is drawn once (D373).** `CellReveal`'s box holds its own state in a small store, drawn by
   its own component, so showing and closing it draws no row; it ignores rows passing under a still
   pointer while the list scrolls and acts on the pointer's own movement. The hovered row follows the
   same rule. `DataTable`'s functions to the rows are stable; `ObjectTable` memoises what it gives
   the rows, with the handlers read through a ref; `useCellEditing`'s `renderCell` changes only with
   the cell editing state and the permissions; `useRecordSelection`'s `isSelected` only with the
   selection; `CollectionView`'s row actions only with read-only. A page arriving in the background
   draws only its own rows.
4. **The layout read only when it can change (D374).** The window's geometry (where the rows start,
   the header it covers) is read when the list, its landing or its size changes, and when the header
   or the start marker resizes (observed); a change of the drawn range runs only the cheap steps (a
   pinned landing, a focus waited for, the visible range).
5. **One-line rows in a record list (D375).** Once the columns are laid out (frozen or sized, wide
   screens), a record list's cells (`ObjectTable`: collections, a record's children) keep to one
   line and end in an ellipsis; the whole value is shown by `CellReveal`, as for a sized column.
   Every row is then as tall as the first, so the estimate is exact and nothing is corrected while
   scrolling. Other tables (relationships, reports, the model editor's) keep wrapping.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D371 | Which pages are fitted to the window | **Recommended:** a collection's table page, on every width. Why: it is the page reported, and the one that holds a long list as its whole content; the window not scrolling is what keeps the rail, the list and its footer on one bottom line (the user's question, 2026-10-25). Cost: the header, lenses and toolbar always take their height, so a short screen shows fewer rows; the matrix, mapping grid and tree views, the split view and a record's page keep today's layout |
| D372 | The wheel over a list | **Recommended:** a list that fills its page leaves the wheel to the browser; a list nested in a page that scrolls keeps the 2026-10-19 behaviour (the list brought into view first, the page carrying on at its ends), made cheap. Why: the wheel handler is what made the browser wait; where nothing scrolls around the list it has nothing to do. Cost: two behaviours in `ScrollWindow`, chosen by the page |
| D373 | How hovering a cell and pointing at a row work while the list scrolls | **Recommended:** rows passing under a still pointer show no cell's whole value and draw no edit icons; moving the pointer does, as today. Why: each of them drew the table again during scrolling. Cost: after scrolling stops, the cell under the pointer shows its value once the pointer moves |
| D374 | Overscan | **Recommended:** unchanged, one screen either side (D156). Why: with rows drawn once, the rows drawn ahead cost only when they enter; a steady scroll adds about one row per row height either way. Cost: none |
| D375 | One-line rows | **Recommended:** in record lists on wide screens once the columns are laid out; the narrow layout (columns by their content) keeps wrapping. Why: equal rows remove the measuring and the scroll corrections behind the jumps found in X6; a cut value is shown whole on hover, focus or a long press. Cost: a long text value no longer shows whole in the row; the phone keeps measured rows |
| D376 | How LS1 is tried | **Recommended:** the changed modules' unit groups, the frontend build, and S5's runner, its collection steps changed to the fitted page; then the user tries it on the dev instance with the steps the record lists. No new measuring. Why: the user's request; S5 is the guide's group for continuous lists. Cost: no figure for scrolling speed, which the user's own try stands for |

**Test cases:** unit: `ScrollWindow` (a filling window registers no wheel handler that cancels; a
nested one still carries the wheel on), `CellReveal` (no box while the list scrolls, one on the
pointer's movement), `DataTable` (a re-draw of the table with the same rows draws no row again;
one-line rows class), `ObjectTable`. Browser: `s5-continuous-lists` with its collection walk on the
fitted page (the window's scroll stays at 0, the footer and the rail's bottom on the window's bottom
line at 1440px and 390px), the record panel and mapping grid walks unchanged.

##### LS1 record (2026-10-25)

**Built 2026-10-25,** everything in the plan; one browser check is still open (below).

**What was built:** `ShellFrame`'s `main.fill` and `AppShell`'s `fill`, set by `App` on a table view's
`list` route; `fill` through `ViewComponentProps`, `CollectionView`, `ObjectTable`, `DataTable` and
`ScrollWindow` (no wheel handler, passive gesture listeners; the nested handler finds its scroller
once per gesture); `ScrollWindow`'s layout effect split into the list's (geometry, landing) and the
drawn range's (`settle`), the header and start marker observed; `ui/CellReveal`'s box in a store of
its own, drawn by `RevealBox`, acting on the pointer's movement; `lib/scrollActivity`; the hovered
row left alone while the list scrolls; `DataTable`'s `secondary` stable and `oneLine`;
`ObjectTable`'s row props memoised with its handlers through a ref; `useCellEditing`'s `renderCell`,
`useRecordSelection`'s `isSelected` and `CollectionView`'s row actions memoised; the fill layout in
`layout.css` and `responsive.css`, the one-line rows in `components.css`. Documents:
CURRENT_FUNCTIONALITY (F03), EXECUTION_GUIDE (the `s5` row), CHANGELOG.

**Found during delivery:** on the fitted page the band, still sticky, took its top bar offset inside
the content and covered the page's header (the user's screenshot); on that page it no longer
sticks, and S5's fitted-page check asserts the band stands above the heading.

**Checks:**

- **Vitest:** `src/ui`, `src/lib`, `src/features/objects`: 49 files, 377 tests passed (new: the
  filling window's wheel, the box and the edit icons while the list scrolls, a table drawn again
  drawing no row). A `RestructuringDialog` case timed out once under load and passed alone and in two
  reruns of the groups.
- **Frontend:** typecheck, lint and format on the changed files clean; build passed.
- **Browser, `s5-continuous-lists`** in a worktree of `a11f71e` with only LS1's files (I3's backend
  was mid-change in the shared tree): the first run passed the lens walks and the new fitted-page
  check at 1440px (window and content at 0, footer and rail on the bottom line) and failed later
  waiting for the 2,000-child record panel; the panel drew at once in two separate tries of the same
  sequence. The second run failed at "live wheel up from the end" (a row moved 36 px). **The same
  step fails on `a11f71e` without LS1** (a row moved 33.7 px), so it is not LS1's; it is recorded
  below.
- **Done after I3 landed** (worktree of `ebd2a2a` with this session's files): the fitted page at
  1440px and 390px with the wheel: the window and the content at 0, the footer 17 px and 13 px above
  the window's bottom (the page's bottom padding), the rail on it, the band clear of the heading, no
  horizontal scroll. At 390×844 the bars, header, actions and toolbar leave room for about four or
  five rows and the footer wraps to two lines (D371's cost, seen on the screenshot).
- **Not run:** backend tests (no backend change); other runners.

**Recorded for later:** S5's "live wheel up from the end" fails without LS1 too: after Ctrl+End,
the first wheel steps up meet rows not measured yet, and one row moves by about a row's height
while the virtualizer corrects (`a11f71e`: 33.7 px; with LS1: 36 px).

**Composable domains (ADR-032):** no door is touched.

**What the user still cannot do after LS1:** see a long text value whole in the row (hover, focus or
a long press shows it, D375); the matrix, mapping grid and tree views and the split view keep their
layout (D371).

### Track SP — The Security pages (U8)

#### SP1: People, groups and roles

**Needs:** Z1, I2; the mock-up approved in P0.

**Scope:** Settings › Security › People (list and detail: create, invite with a one-time link,
deactivate, reset password, sign out everywhere, last sign-in, their grants), Groups (local and
provider groups, members, grants), Roles (predefined read-only, custom created and edited as a
matrix of action groups), and the grants per workspace from both sides ("who can do what here").
Every page uses the list-and-detail pattern (U-D10) and the UI foundation; no page names an
application or record type.

##### SP1 plan (2026-10-24)

**Planned 2026-10-24; accepted by the user the same day** ("above accepted"): D298–D305, the test
cases and the "SP1 as planned" boards, after the user asked where the workspace's Access board is
(the new row's fourth) and where token scopes are set (nowhere: `management` and `consumer` are the
two audiences any active client may ask for; what a token may do is its principal's grants, D226;
a client's consumer API grants are Z3 and SP2). Checked against the code at `eea6ca1` with the approved boards (People, People at 390px,
Groups, Roles, Access), U8 in SETTINGS_AND_UI_PLAN and J40.

**What the check found:**

- **Every write the pages need exists** (I1, I2, Z1): people (create, change, deactivate and
  restore, the one-time link, sign out everywhere), groups and members, roles (created empty or
  copied, changed, deleted when unused), grants (created, removed), a workspace's access, and the
  catalogue at `/action-groups`.
- **Four reads the boards show do not:** a person's roles in the People list ("Data steward ·
  Herbarium"): `GET /users` carries no roles; a person's roles **through their groups** (the
  board's "Through" column): `GET /grants?principalId=` answers only direct grants, and
  `/me/grants`, which includes groups, is the caller's own; **a person's groups**: no route answers
  them; **finding a group or a client** for the grant dialog's "Who": `/groups` and `/clients` take
  no search (`/users` has `q`).
- **A role whose action groups are all instance-only** (Security administration, Model authoring,
  Workspace administration, Operations: `grantableAt: instance`) **can be granted in a workspace,
  where it allows nothing**: `create_grant` does not check the groups' reach, and the route check
  and the last-administrator count read only instance grants. A dialog offering it would let an
  administrator make a grant that silently does nothing (D302).
- **The workspace page has no tabs** (`WorkspaceAdmin`: a header, actions, then sections such as its
  webhooks); the Access board drew tabs Overview, Model, Access, Approvals (D301).
- **The boards show five things other packages own:** a person's **Recent activity** (who granted,
  who created: the actor is recorded only from Z4), **provider groups** and "from Entra ID" (I3),
  the **Clients, Sign-in and Signing keys** entries (SP2, I3), a client's **consumer API grant** in
  Access (Z3, SP2), and the **Approvals** tab (A3).
- **No page hides itself yet** (Z5): every settings page is listed for everyone and a page the person
  may not use shows the engine's refusal. The account menu already reads `/me/permissions` for its
  role line.
- **Reference patterns in the code:** `CatalogueLayout` with `useCursorFeed` and Load more
  (Workspaces, Webhooks) for the list beside the detail; `SigningKeyDialog`'s "shown once" dialog
  with `CopyValue` (Webhooks), which the one-time link reuses after extracting it; `ConfirmDialog`;
  Account's grant rows (`grantDetail`).

**What is built:**

1. **API** (`security-admin` at the instance, cursor-paged, documented in API.md):
   - `GET /users` and `GET /users/{id}` gain `roles`: each role the person holds, directly or through
     a group, with where (`instance`, or the workspaces by key and label), one PostgreSQL aggregation
     per page (D298).
   - `GET /users/{id}/grants`: the person's grants, direct and through groups, in the shape of
     `/me/grants` (a group's grant names the group) (D299).
   - `GET /groups?q=&memberId=` and `GET /clients?q=` (D300).
   - `POST /grants` refuses, `422 GRANT_SCOPE_INVALID`, a workspace grant of a role none of whose
     groups can be held in a workspace (D302).
   OpenAPI lock re-baselined from a diff.
2. **Settings › Security › People** (`/settings/security/people[/{id}]`): the catalogue beside the
   person, as the People board: search, Active and Deactivated as filters with their counts, each
   row the name and the role line (D298); the person: name, username, e-mail, Active or Deactivated,
   "Has not set a password yet" or the last sign-in; **Edit** (name, e-mail), **Reset password**
   and, for someone without one, **Send a password link** (D304), **Sign out everywhere**,
   **Deactivate** or **Restore**, each refusal shown as the engine words it
   (`LAST_SECURITY_ADMINISTRATOR`); **Roles**: where, role, narrowed to (writes), through (directly,
   or the group with a link to it), a stale narrowing marked (D296), Remove for a direct grant,
   **Grant a role** (the dialog, item 6); **Groups**: their groups with Remove, **Add to a group**.
   **New person**: username, name, e-mail, then the one-time link shown once (D304).
3. **Groups** (`/settings/security/groups[/{id}]`): local groups with members and roles counted;
   **New group**, Rename (name and description), Delete (refusals as worded); **Roles** as on a
   person, with **Grant a role**; **Members** (paged) with **Add a member** (people found by `q`)
   and Remove.
4. **Roles** (`/settings/security/roles`): the matrix of the 13 action groups (each with its
   one-line description) by role, predefined columns read-only; **New role** (a name, empty or
   copied from any role) and a custom role's column edited in place: its groups as checkboxes, its
   name and description, Save and Cancel, how many grants hold it ("a change applies on their next
   request"), Delete when unused (`ROLE_IN_USE` otherwise). At 390px the matrix scrolls sideways in
   its box with the group column fixed (D305).
5. **A workspace's Access** (D301): a section on the workspace's page in Settings › Workspaces
   listing every grant that applies there (who, kind, role, narrowed to, from: this workspace or the
   whole instance; through a group named with a link), Remove for a grant made here, **Grant a
   role**.
6. **The grant dialog**, one component for all three places: from Access, **who** (people, groups
   and clients found by name); from a person or group, **where** (the whole instance or a
   workspace); the **role** with its groups in a sentence; **Narrow what they may change**
   (everything, or chosen applications and record types from the workspace's model, offered only
   for a workspace grant of a role with narrowable groups), "Reading is never narrowed", and a
   sentence of what the grant allows, as the Access board. A role that can only be held at the
   instance offers only the whole instance (D302).
7. **Who sees Security** (D303): the navigation's Security group and the workspace's Access section
   appear only to a person holding Security administration, read from the `/me/permissions` the
   account menu already reads; Z5 extends the same check to the other pages.
8. **Left out until their packages** (U-D11, as D273 did): Recent activity (Z4), provider groups
   (I3), Clients, Sign-in and Signing keys (SP2, I3), consumer API grants (Z3, SP2), Approvals (A3).
9. **Documents:** API.md (the four reads, D302's refusal), SETTINGS_AND_UI_PLAN (U8 and the
   settings table: SP1 built), USER_JOURNEYS (J40's UI channel) and API_JOURNEYS,
   CURRENT_FUNCTIONALITY, UI_ACCEPTANCE (SP1 state rows), EXECUTION_GUIDE (the new runner),
   CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D298 | A person's roles in the People list | **Recommended:** `GET /users` and `GET /users/{id}` answer `roles`: each role the person holds, directly or through a group, with `instance: true` or the workspaces (key and label), computed in one PostgreSQL aggregation per page; the list's line reads "Data steward · Herbarium", "Data owner · Herbarium, Field stations", "Reader · 3 workspaces", "Security administrator" (an instance role), "No roles yet". Why: the approved board shows it, a person is found by what they do as much as by name, and an integrator listing people needs the same; one statement per page, not one call per row. Cost: every user read joins grants and groups |
| D299 | A person's roles through their groups | **Recommended:** `GET /users/{id}/grants` (cursor-paged): direct grants and those of the person's groups, the same rows as `/me/grants` (D284), so "Through" is the grant's group. Why: a person's page must answer "why can Ana do this"; `GET /grants?principalId=` keeps meaning the grants made to that principal. Cost: one route |
| D300 | Finding groups and clients | **Recommended:** `q` on `GET /groups` (name) and `GET /clients` (name), and `memberId` on `GET /groups` (the person's groups). Why: the grant dialog's "Who" searches people, groups and clients alike, and a person's page lists their groups; both are filters on existing lists. Cost: none beyond the filters |
| D301 | Where a workspace's Access goes (**differs from the Access board's tabs**) | **Recommended:** a section **Access** on the workspace's page in Settings › Workspaces, below its details and before its webhooks; no tabs. Why: the page has no tabs today and holds three short sections; tabs for one more section would reshape the page; A3's approval policy becomes another section. Cost: on a workspace with many grants, the page is long (the section pages with Load more) |
| D302 | A role that cannot be held in a workspace (**a refusal added**) | **Recommended:** `POST /grants` refuses a workspace grant whose role has no group grantable in a workspace, `422 GRANT_SCOPE_INVALID` naming the role; the dialog offers only "the whole instance" for it, and for a mixed role (a custom one, or Model administrator's Model authoring) says which of its groups apply only at the instance. Why: today such a grant is stored and allows nothing, so an administrator would believe they gave Security administration to someone who has none; refusing it makes the mistake visible through every client. Cost: a client that made such grants gets a refusal (none can have relied on them: they allowed nothing) |
| D303 | Who sees the Security pages before Z5 | **Recommended:** the Security group in the navigation and the workspace's Access section are shown only to a person holding Security administration, read from `/me/permissions` (an instance group appears in every workspace's answer); a person without it who opens the address sees the engine's refusal. Why: a page the person can only be refused on is a dead end, and the read is already made for the menu; Z5 makes the same check general. Cost: none |
| D304 | Inviting a person | **Recommended:** New person creates the person (username, name, e-mail) and, in the same dialog, shows their one-time password link once with Copy, its expiry and "Pass this link to the person yourself; it is not shown again"; **Reset password** on a person makes a new link the same way and says that it replaces an earlier one and that using it signs them out everywhere; the "shown once" dialog is extracted from Webhooks' signing key so both use one component. Why: D272 designed the link for this page and D233 sends no e-mail; one dialog for every secret shown once. Cost: the administrator passes the link on |
| D305 | Roles at 390px (**no board**) | **Recommended:** the same matrix, scrolling sideways in its own box with the action-group column fixed; a custom role edited the same way. Why: a matrix is how roles are compared, and a list of roles each opening its groups would be a second design to keep; phones are not where roles are designed. Cost: sideways scrolling on a phone |

**Journey test cases** (`tests/journeys/test_j40_security_pages.py`, on two configurations; written
first and seen failing; the harness client acting as security administrator):

1. **J40, the people list names roles:** given a person granted Data steward in workspace A
   directly and Reader in B through a group, and another with an instance role, when `GET /users`
   (and `GET /users/{id}`) is read, then the first lists Data steward in A and Reader in B, the
   second the role with `instance: true`, and a person with none an empty list; `q` and `active`
   still narrow the list.
2. **J40.4, a person's grants through groups:** given the same person, when
   `GET /users/{id}/grants` is read, then both grants are listed, the group's naming the group; when
   they leave the group, then only the direct one; an unknown person answers `404 USER_NOT_FOUND`.
3. **J40, finding groups and clients:** given two groups and two clients, `GET /groups?q=` and
   `GET /clients?q=` answer the matching one; `GET /groups?memberId=` answers the person's groups.
4. **J40, a role held only at the instance:** granting Security administrator in workspace A answers
   `422 GRANT_SCOPE_INVALID`; at the instance it passes; Model administrator in A passes (Model
   release is held in a workspace).

Unit tests (Vitest): the role line (D298's wording, several roles and workspaces), the grant
dialog's sentence (narrowed, instance, through which groups apply only at the instance).

**Browser** (a new runner `sp1-security`, on two models; reference pattern: Settings › Workspaces'
catalogue beside the detail, and Account's grant rows): as the harness person, create a person and
copy their link; open the link's page and set the password in a second context, then sign in as
them; grant them Data steward in a workspace narrowed to one record type of that workspace's model;
add them to a new group, grant the group Reader in another workspace, see both on the person with
"Through"; copy Data steward into a custom role, untick Publish, save; the workspace's Access lists
all of it; remove a grant; deactivate the harness person and see `LAST_SECURITY_ADMINISTRATOR`'s
message; a person without Security administration sees no Security entries. Keyboard only through
the grant dialog; 390px (People, a person, Roles' matrix scrolled); axe; screenshots of People,
Groups, Roles and Access at 1440px light and dark and People and Roles at 390px inspected against
the boards.

**Checks:** the new journey module and J40's authorization module; `test_openapi_contract` with the
lock diffed; `test_api_journeys`; Ruff on the changed files; Vitest for the new pages, the dialog and
`WorkspaceAdmin`; format, lint, build; the runners `sp1-security`, `u3-settings` (the navigation)
and `u5-webhooks` (the extracted dialog). No migration, so no startup groups.

**Composable domains (ADR-032):** the identity door is touched only by reads (a person's roles and
grants); no value source, audit row or `cause` changes.

**What the user will still not be able to do after SP1:** manage clients, their secrets and their
consumer API grants on a page (SP2; API calls until then); sign in with a provider or see provider
groups (I3); see who granted or changed what (Z4); have the rest of the interface hide what a person
may not do (Z5).

##### SP1 record (2026-10-24)

**Delivered 2026-10-24.** What was built is the plan's list, items 1–9:

- **API:** `roles` on every read of a person, from one statement per page over direct and group
  grants (`administration.held_roles`, D298); `GET /users/{id}/grants` (`user_grant_page`, sharing
  `/me/grants`' query, D299); `q` and `memberId` on `GET /groups`, `q` on `GET /clients` (D300);
  `POST /grants` refuses a workspace grant of a role held only at the instance with
  `422 GRANT_SCOPE_INVALID` and `details.role` (D302). OpenAPI lock re-baselined from a diff
  against `eea6ca1`: `UserRole`, `UserRoleWorkspace`, the route, the three filters and two
  descriptions; nothing else.
- **Frontend** `features/security/`: `PeoplePage`, `GroupsPage`, `RolesPage`, `GrantsSection` (a
  person's, a group's and a workspace's grants), `GrantDialog`, `PrincipalPicker` (people, groups and
  clients found by name), `PickDialog`, `securityText`; `api/securityClient.ts`; routes
  `/settings/people[/{id}]`, `/settings/groups[/{id}]`, `/settings/roles`; the Security group in the
  navigation for holders of Security administration (`useHoldsGroup`, D303); Access on the
  workspace's page (D301); `ui/ShownOnceDialog`, extracted from Webhooks' signing key and used for
  the password link (D304); a `users` icon; `SettingsTable` names a column for assistive technology
  only (the rows' actions).
- **Documents:** API.md (SP1 delivered), USER_JOURNEYS (J40's UI channel), API_JOURNEYS,
  CURRENT_FUNCTIONALITY (F27), SETTINGS_AND_UI_PLAN (U8 and the settings table), UI_ACCEPTANCE
  (SP1-1 to SP1-4), EXECUTION_GUIDE (`sp1-security`), CHANGELOG, PROJECT_STATUS; Z5's scope gains
  what SP1 found (below).

**Where it differs from the plan:**

- **Addresses** are `/settings/people`, `/settings/groups` and `/settings/roles`, like every other
  settings page, not `/settings/security/…`.
- **The groups list** shows each group's member count and description; a group's roles are on its
  page (counting them in the list needed another field on every group read, not planned).
- **The new person signs in after a grant** in the browser runner: a person without Browse in the
  default workspace sees only "Reading the model in workspace 'default' needs Browse" instead of the
  application. This was so since Z1 and is Z5's to fix; recorded in Z5's scope (decided within the
  approved package).
- **The journey cases were seen failing first** (8 of 8, each for the missing field, route, filter
  or refusal), then passed.
- **Found and fixed on the way, not SP1's:** `u5-webhooks` and the release gates' surface helper
  still passed `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup has refused since I1 (D253), so
  neither could start; the harness already supplies `SECRETS_ENCRYPTION_KEY`, and the old setting is
  removed from both. `u3-settings`' keyboard order now includes Security.
- **Found by the runner and fixed:** the Roles matrix widened the page (at 1440px through its long
  descriptions, at 390px through its cells' visually hidden labels escaping the scroll box); the
  box now takes its width from the page and is the labels' containing block.

**Checks** (single process):

- `tests/journeys/test_j40_security_pages.py`: 8 passed (4 cases × 2 configurations), seen failing
  first; with `test_j40_authorization.py`, `test_j39_j41_j43_identity.py` and `test_api_journeys.py`:
  65 passed; after the final backend change `test_j40_security_pages`, `test_openapi_contract`,
  `test_api_journeys`, `test_boundaries`: 28 passed. Ruff on the changed files (check and format).
- Vitest: `src/features/security`, `src/routing`, `src/features/settings`, `src/features/workspaces`,
  `src/app`, `src/ui`: 36 files, 331 passed (`securityText.test` new: the role line and the grant
  sentence; `Settings.test`: Security listed only to a Security administrator; routes). `format`,
  `lint` (0 errors; the 8 warnings in untouched files), `build`.
- **Browser:** `sp1-security` on two models: 34 checks, axe 0 violations on the link dialog, the
  grant dialog, People (light and dark), Groups, Roles and Access; `u3-settings`: 10 checks;
  `u5-webhooks`: 19 checks (the extracted dialog). Screenshots inspected against the boards: People
  and a person at 1440px light and dark and at 390px, the grant dialog, Groups, Access, Roles at
  1440px and 390px (two layout defects found and fixed, above).

**Not run:** the full backend suite (with Z5, the user's decision of 2026-10-24) and the other
browser runners, which SP1 changes only through the navigation's Security group (R); the
accessibility and visual gates (R).

**Fixed after delivery (the user, 2026-10-24):** New person with the username "user 1" said only
"Request validation failed": the engine refuses a username with a space (`^\S+$`), and the dialog
showed the `422`'s message without its details. Now New person says a username has no spaces as it
is typed and sends nothing; the engine's refusal of a field is said under that field in New person
and Edit (`invalidFields`), and by field name in the group and role dialogs (`refusalMessage`).
Checks: `errors.test` and `PeoplePage.test` (both dialog cases seen failing on the delivered code),
Vitest for `src/api`, `src/features/security`, `src/features/settings`; lint, format, build;
`sp1-security` on two models: 36 checks (a space refused before sending, a malformed e-mail
refused by the engine and said under its field).

**What the user cannot do yet:** manage clients, their secrets and their consumer API grants on a
page (SP2; API calls until then), or limit a client to some consumer APIs (Z3); sign in with a
provider or see provider groups (I3); see who granted or changed what, or a person's recent
activity (Z4); open the application as a person without Browse in the default workspace, or have the
rest of the interface hide what a person may not do (Z5).

#### SP2: OAuth clients and their access

**Needs:** Z3, SP1.

**Scope:** Settings › Security › Clients: create a client, its secret shown once, rotate it with an
overlap, deactivate it; its roles on the management API and its consumer API grants per workspace;
last use. Sign-in providers (I3) on Settings › Security › Sign-in.

##### SP2 plan (2026-10-25)

**Planned 2026-10-25; accepted by the user the same day** ("its good"): D348–D357, the test cases and the "SP2 as
planned" boards ([security mock-ups canvas](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo), the
ninth row: a client, Rotate secret, granting a consumer API, Signing keys, a client at 390px).
Checked against the code at `56903d2` with Z6 in the working tree, the approved Clients board, U8
and the settings table (Clients; Signing keys, "I1, SP2"), J41 and Z3's and Z4's notes left for
SP2's client pages.

**What the check found:**

- **Every client write exists** (I1): create (the secret answered once), rename, deactivate and
  restore (`active`), a new secret with an overlap of 0 to 168 hours, ending a secret; `lastUsedAt`
  on the client and each secret; `q` on the list (SP1); a client's grants at
  `GET /grants?principalId=` (clients belong to no group, so these are all of them); its security
  events at `/security-events?principalId=` (Z4); its changes at `/changes?actorId=` (Z6); the
  webhooks it created at `/consumer-subscriptions?ownerId=` (Z3); token signing keys and their
  rotation (I1).
- **Three things the board shows are not answered:** the list's line ("specimen-catalogue in
  Herbarium", "Reader in Herbarium"): `GET /clients` carries no access; **"created by Mei Sato"**:
  a client stores no creator, though its `created` security event names the actor (Z4); a secret's
  **last four characters** ("…a91F"): only the hash is stored.
- **A Security administrator cannot fill the grant dialog.** It reads the workspace's model for the
  narrowing (`GET /model`, which needs Browse), and SP2's consumer API choice would read the
  consumer index, which also needs Browse with a management token (D308). Security administrator
  holds only Security administration (D230), so a person holding just that role sees the dialog's
  model read refused. SP1 did not meet it because the harness person holds every role (D282).
- **The grant dialog grants roles only** (Z3 item 8); Access, a person's and a group's grants
  already list and remove consumer API grants.
- **Webhooks names no owner** (Z3 left it for these pages).
- **Reference patterns in the code:** `PeoplePage` (the catalogue beside the entry, Active and
  Deactivated filters with counts, the header's actions, Recent activity on `ui/Timeline`),
  `GrantsSection` and `GrantDialog`, `ui/ShownOnceDialog` (the password link, Webhooks' signing
  key), `ConfirmDialog`, `useHoldsGroup` (D303, D328).

**What is built:**

1. **API** (`security-admin` at the instance, documented in API.md):
   - `GET /clients` and `GET /clients/{id}` gain `roles` (D298's shape: the role, `instance: true`
     or the workspaces) and `consumerApis` (each API's key with the workspaces it is granted in),
     one statement per page, and `createdBy` (the actor of the client's `created` security event;
     `null` when made on the server or before Z4) (D348, D349).
   - Each secret gains `hint`, its last four characters, stored when it is made; `null` for secrets
     made before SP2. Migration `20261103_01_client_secret_hints` adds the column (D350).
   - `GET /workspaces/{workspaceKey}/grant-options`: the applications, record types and consumer
     APIs the workspace's model declares, by key and name (D355).
   OpenAPI lock re-baselined from a diff.
2. **Settings › Security › Clients** (`/settings/clients[/{id}]`), as the board and the "SP2 as
   planned" row: the catalogue beside the client, search, Active and Deactivated with counts, each
   row the name, the access line and the last token (D348); **New client** (a name), then the client
   ID and secret in the shown-once dialog ("afterwards only its last four characters are kept"); the
   client: name, client ID with Copy, created by and when, Active or Deactivated, the last token;
   **Rename**, **Rotate secret** (D352), **Deactivate** or **Restore** (a confirmation saying its
   tokens are refused from the next request), **See changes** (Z6's page, shown only to a caller
   who would see something, D323); **Secrets** (the last four characters, created, valid until,
   last used; **End now** on a secret with an end, D351); **Access** (where, grant, narrowing,
   Remove, **Grant**); **Webhooks it created** (D353); **Recent activity** (its security events,
   as a person's, Z4).
3. **Rotate secret** (D352): the overlap chosen from 1 hour, 24 hours (the default), 7 days or
   "Stop it now", then the new secret shown once with when the previous one stops.
4. **The grant dialog grants a consumer API** (D354): "What": a role or a consumer API, from every
   place it opens (Access, a person, a group, a client); a consumer API is granted in one workspace,
   chosen from those the workspace's model declares, never narrowed, with its sentence. The
   section's button reads **Grant** in all four places. The dialog reads its choices from
   `grant-options` (D355), so a Security administrator without Browse can use it.
5. **Settings › Security › Signing keys** (`/settings/signing-keys`, D356): what the keys do in a
   paragraph; the keys newest first with Load more (key ID, Signing / Verifying until *time* /
   Retired, created, replaced, retired); **Start a new key** and **Retire the current key now** (a
   confirmation saying what happens to sessions and clients, D254).
6. **Webhooks** names a subscription's owner ("Created by *name*", a link to the person's or
   client's page for a Security administrator) (D353).
7. **Who sees them:** Clients and Signing keys in the Security group, for holders of Security
   administration (D303, D328).
8. **Left out** (U-D11): Sign-in and provider groups (I3); webhook key rotation (K1) (D357).
9. **Documents:** API.md (the three additions, `hint`), SETTINGS_AND_UI_PLAN (U8, the settings
   table), USER_JOURNEYS (J41's UI channel) and API_JOURNEYS, CURRENT_FUNCTIONALITY, OPERATIONS
   (rotating a client secret and a signing key from the page), UI_ACCEPTANCE (SP2 state rows),
   EXECUTION_GUIDE (the new runner), CHANGELOG, PROJECT_STATUS.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D348 | A client's access in the list | **Recommended:** client reads answer `roles` (D298's shape) and `consumerApis` (`[{key, workspaces: [{key, label}]}]`), computed in one statement per page; the list's line reads "specimen-catalogue · Herbarium, Field stations; Reader · Herbarium", "Operator" (an instance role), "No access yet", and a second line "Last token 4 min ago", "No token yet" or "Deactivated". Why: the approved board; a client is found by what it does, and an integrator listing clients needs the same. Consumer APIs by key, because a key's name comes from each workspace's model (ADR-042). Cost: every client read joins grants |
| D349 | Who created a client | **Recommended:** `createdBy` on client reads, the actor of the client's `created` security event (a person or client), `null` when made by `create_client` on the server or before Z4; no new column. Why: the board names the creator, and the event already records it (Z4); a column would hold the same fact twice. Cost: one join per page |
| D350 | Telling a client's secrets apart (**a migration**) | **Recommended:** each secret stores and answers `hint`, its last four characters, shown as "…a91F"; secrets made before SP2 answer `null` and show "—". Why: during an overlap two secrets are valid, and whoever runs the system must know which one it holds before ending the other; the approved board's dialog promises it. Four of 43 characters (24 of 256 bits) leave the rest unguessable. Cost: a column and its migration |
| D351 | Ending a secret | **Recommended:** **End now** is offered on a secret that has an end (the previous one during an overlap); the newest secret is replaced by rotating with "Stop it now". The API keeps ending any secret. Why: ending the only secret leaves the client unable to sign in with nothing to show for it; rotating ends it and hands over a new one in one step. Cost: none |
| D352 | Rotate secret | **Recommended:** a dialog choosing how long the current secret keeps working: 1 hour, 24 hours (default), 7 days, or "Stop it now" (0, for a leaked secret); then the new one in the shown-once dialog with the time the previous one stops. Why: the board's dialog states the overlap; four choices cover the API's 0–168 hours without a number field. Cost: other overlaps are API-only |
| D353 | Webhooks and their owner | **Recommended:** a client's page lists **Webhooks it created** (name with a link, workspace, consumer API, state) only to a caller holding Integration administration somewhere, as the route lists those in the caller's workspaces; a webhook's page says "Created by *name*", linked to the person's or client's page for a Security administrator, "—" when it has no owner (before Z3). Why: Z3 left the owner for these pages; D323 hides what the caller cannot open. Cost: a Security administrator without Integration administration sees no webhooks on a client |
| D354 | Granting a consumer API on a page | **Recommended:** the one grant dialog gains "What: A role / A consumer API" wherever it opens; a consumer API asks for a workspace (never the whole instance) and the API from that workspace's model, has no narrowing, and says "*who* may read the *name* consumer API in *workspace*. It changes nothing and opens nothing on the management API." The sections' button reads **Grant** (was "Grant a role"); the client's section is **Access**, a person's and a group's stay **Roles**. Why: D306 grants consumer APIs to clients, people and groups alike, and one dialog keeps one design (U-D14). Cost: SP1's button label changes, and its runner with it |
| D355 | What the grant dialog reads (**a route added; fixes SP1's dialog for a Security administrator**) | **Recommended:** `GET /workspaces/{workspaceKey}/grant-options` with Security administration at the instance: the workspace's model's applications, record types and consumer APIs, each key and name; `404 WORKSPACE_NOT_FOUND` for an unknown workspace. Why: a Security administrator holds no data (D230), so `GET /model` and the consumer index refuse them; granting must not need Browse. Cost: one route that reveals the model's names to Security administrators, who already grant by them |
| D356 | Signing keys on a page | **Recommended:** Settings › Security › Signing keys lists the keys newest first, states read as Signing, "Verifying until *retiredAt*" and Retired; **Start a new key** (rotation with `immediate: false`, said in a toast) and **Retire the current key now** (`immediate: true`, after a confirmation: tokens it signed are refused from the next request, sessions renew, clients are refused once and fetch a new token). Why: the settings table gives the page to SP2; D254 says nobody has to act on a rotation, which the page repeats. Cost: none beyond the page |
| D357 | What SP2 leaves out | **Recommended:** Sign-in and provider groups wait for I3, which builds their page (the queue's "sign-in providers" on SP2's line moves to I3's); webhook key rotation is K1. Why: U-D11, nothing is listed before it works. Cost: none |

**Journey test cases** (`tests/journeys/test_j41_client_pages.py`, on two configurations; written
first and seen failing; the harness client acting as Security administrator):

1. **J41, a client's access in its reads:** given a client granted Reader in workspace A, Operator
   at the instance and a consumer API of each workspace's model in A and B, and a second client with
   nothing, when `GET /clients` and `GET /clients/{id}` are read, then the first lists Reader in A,
   Operator with `instance: true`, and the API in A and B, the second empty lists, and both name the
   caller as `createdBy`; `q` and `active` still narrow the list.
2. **J41.3, telling secrets apart:** given a new client, its secret answered once, when the client
   is read, then its secret's `hint` is the secret's last four characters; after a new secret with a
   one-hour overlap, both are listed with their own hints and the older with `expiresAt`; neither
   value is answered again.
3. **J41, what a grant is made from:** given two workspaces on different models,
   `GET /workspaces/{key}/grant-options` answers each model's applications, record types and
   consumer APIs (the same keys and names `GET /model` shows there); a person holding only Security
   administrator reads it and grants a client one of those consumer APIs; an unknown workspace
   answers `404 WORKSPACE_NOT_FOUND`; a person without Security administration `403 FORBIDDEN`.

Unit tests (Vitest): the client's access line (D348's wording), the consumer API grant sentence,
the signing key's state. Startup: the migration's bootstrap, upgrade from `20261102_01`, restart,
interrupted-migration and lifespan checks, and a smoke start on a copy of the development database.

**Browser** (a new runner `sp2-clients`, on two models; reference pattern: Security › People):
create a client and copy its ID and secret; obtain a token with them and see the last token on the
page; grant it a consumer API in a workspace of each model from its page and Reader in one; rotate
with a one-hour overlap and see both secrets by their last four characters; end the older; rename,
deactivate and restore; the workspace's Access shows the consumer API grant; as a person holding
only Security administrator, the grant dialog offers the narrowing and the consumer APIs; Signing
keys: start a new key and see two keys' states; Webhooks names the owner. Keyboard only through New
client, Rotate secret and the grant dialog; 390px (Clients, a client, Signing keys); axe;
screenshots of Clients, the rotation dialog, the grant dialog and Signing keys at 1440px light and
dark and a client at 390px, inspected against the boards.

**Checks:** the new journey module, `test_j39_j41_j43_identity.py` and `test_j40_security_pages.py`;
`test_openapi_contract` with the lock diffed; `test_api_journeys`; `test_boundaries`; the startup
and migration groups the execution guide selects for a migration; Ruff on the changed files; Vitest
for `src/features/security`, `src/features/settings`, `src/routing`, `src/ui`; format, lint, build;
the runners `sp2-clients`, `sp1-security` (the dialog and its button), `u5-webhooks` (the owner) and
`u3-settings` (the navigation).

**Composable domains (ADR-032):** the identity door is touched by reads (a client's access and
creator) and a secret's hint; no value source, audit row, `cause`, bulk API or `match` declaration
changes.

**What the user will still not be able to do after SP2:** sign in with a provider, see provider
groups or turn local sign-in off (I3); rotate a webhook's signing key (K1); try the API console
with their token (C1); submit and approve publications (Track A).

##### SP2 record (2026-10-25)

**Delivered 2026-10-25.** What was built is the plan's list, items 1–9:

- **API:** `roles`, `consumerApis` and `createdBy` on every read of a client, from one statement per
  page each (`administration.client_roles`, which shares SP1's aggregation with `held_roles`,
  `client_consumer_apis`, `clients.creators` over the `created` security events; D348, D349); a
  secret's `hint` stored when made (migration `20261103_01_client_secret_hints`, D350);
  `GET /workspaces/{workspaceKey}/grant-options` (`administration.grant_options`, D355). OpenAPI
  lock re-baselined: the document with SP2's additions removed hashes to Z6's lock exactly.
- **Frontend** `features/security/`: `ClientsPage` (the catalogue, New client, the client's page,
  `RotateDialog`, `Secrets`, `ClientWebhooks`), `SigningKeysPage`, `RecentActivity` (extracted from
  `PeoplePage`, used by both), the grant dialog's "What" and its reads from `grant-options`,
  `GrantsSection`'s one **Grant** button and its link to a client's page; the client's words in
  `securityText`; the owner on a webhook's page; routes `/settings/clients[/{id}]` and
  `/settings/signing-keys`; Clients and Signing keys in the Security group.
- **Documents:** API.md, USER_JOURNEYS (J40, J41), API_JOURNEYS, CURRENT_FUNCTIONALITY (F26, F27,
  F11), OPERATIONS, SETTINGS_AND_UI_PLAN (U8 and the settings table), UI_ACCEPTANCE (SP2-1 to
  SP2-4), EXECUTION_GUIDE (the runner and a selection row for the Security pages), CHANGELOG,
  PROJECT_STATUS, the queue (Sign-in on I3's line).

**Where it differs from the plan:**

- **A list line that follows a grant:** the runner found the client's access line unchanged after a
  grant on its page; `GrantsSection` now tells its page when a grant is made or removed, and the
  client is read again.
- **Found by the screenshots and fixed:** "Created by by …" (the actor component says "by" itself),
  and the grant dialog's segmented choice drawn taller than its options, because the dialog-wide
  `.dialog form label` rule reached its labels; one rule now keeps every choice in a dialog form as
  drawn, which also fixes SP1's "Where".
- **The webhook in the runner** is created by the client itself with Integration administrator, on a
  consumer API with an event added to the starter as `u5-webhooks` does, since the starter's own
  consumer API declares none.
- **The journey cases were seen failing first** (6 of 6: the missing `roles`, `hint` and route),
  then passed.

**Checks** (single process for the runners):

- `tests/journeys/test_j41_client_pages.py`: 6 passed (3 cases × 2 configurations), seen failing
  first; with `test_j39_j41_j43_identity.py`, `test_j40_security_pages.py`,
  `test_j41_consumer_grants.py`, `test_openapi_contract.py`, `test_api_journeys.py`,
  `test_boundaries.py`, `test_startup.py`, `test_schema_drift.py`, `test_foreign_keys.py`: 83
  passed after API_JOURNEYS gained the route (22 s). Ruff check on `app/` and the new module; Ruff
  format on the files SP2 wrote (three files it edited keep older unformatted lines outside its
  hunks, left as they are).
- **Migration:** clean bootstrap and restart (`test_startup`, head `20261103_01`), the schema
  against the ORM (`test_schema_drift`); the development database upgraded from `20261102_01` by
  the running `--reload` server when the file was saved, which still answers. One `ADD COLUMN` in
  one transaction; no upgrade test (pre-1.0).
- Vitest: `src/features/security`, `src/features/settings`, `src/routing`, `src/ui`, `src/app`,
  `src/features/workspaces`: 41 files, 362 passed (`securityText.test`: the access line, the last
  token, the consumer API sentence, a key's state, a client's events; `routes.test`: the two
  routes). `format`, `lint` (0 errors; the 8 warnings in untouched files), `build`.
- **Browser:** `sp2-clients` on two models: 17 checks, axe 0 violations on the secret dialog, the
  grant dialog, Rotate secret, a client (light and dark), Signing keys and the retirement's
  confirmation; `sp1-security` on two models (the renamed button and dialog), `u5-webhooks`: 19
  checks (the owner line), `u3-settings`: 10 checks (the navigation). Screenshots inspected against
  the boards: a client at 1440px light and dark and at 390px, the grant dialog, Rotate secret,
  Signing keys.

**Not run:** the full backend and frontend suites and the other browser runners (R); the
accessibility and visual gates (R).

**Shared working tree:** another session is working on TV1 (the model editor's layout files, a
CHANGELOG entry, D358–D360) in the same checkout; SP2's hunks are separate from it, and Z6 is still
uncommitted beneath both.

**What the user cannot do yet:** sign in with a provider, see provider groups or turn local sign-in
off (I3); rotate a webhook's signing key (K1); try the API console with their token (C1); submit and
approve publications (Track A); choose a secret overlap other than 1 hour, 24 hours, 7 days or none
except through the API.

### Track DP — Deployment

_Added by the user, 2026-10-25,_ after "The engine cannot be reached … http://localhost:8000" on a
phone: "there has to be a deployment track in this build where these questions are answered well and
have their assigned work packages". **Planned, awaiting the user's approval** of D404–D411.

**What the check found** (at `ebd2a2a`):

- **The browser application calls a build-time address.** `api/address.ts` reads `VITE_API_URL`,
  else `http://localhost:8000`, so a page opened from any other device calls that device. OPERATIONS
  lists `VITE_API_URL`, `PUBLIC_URL` and `CORS_ORIGINS` and the one-site rule for the session cookie
  (D234, D268) but never says how the application is served or reached.
- **There is no production way to serve the application.** `frontend/Dockerfile` runs `npm run dev`;
  `docker-compose.yml` starts the dev server with `VITE_API_URL: http://localhost:8000`.
- **The compose file no longer starts the engine.** Since 0.12 I1 the engine refuses to start
  without `SECRETS_ENCRYPTION_KEY`, which the compose file does not set; nor does it set
  `PUBLIC_URL`, `CORS_ORIGINS`, `RDM_CURSOR_SIGNING_KEY` or create a first administrator. The image
  runs as root and Uvicorn trusts no proxy headers, so behind a proxy every caller would share the
  proxy's address (the sign-in throttle counts per address, D271).
- **What the engine serves:** `/api/v1`, `/api/consumer`, `/oauth` (the sign-in pages and token
  endpoints), `/.well-known`, `/docs` and `/openapi.json`, `/health` and `/health/live`, and
  `/metrics`. Everything else the browser asks for is the application.

**Packages:**

| # | Package | Needs | Scope |
| --- | --- | --- | --- |
| DP1a | A developer instance on the network (**delivered 2026-10-25**) | — | `scripts/dev.sh` (`settings`, `admin`, `engine`, `frontend`, `cert`, `address`): `.dev/settings.env` with the database and the secrets key, the first administrator, and with `--network` the engine and frontend over https on the address `cert` finds, `PUBLIC_URL`, `CORS_ORIGINS` and `VITE_API_URL` set to match; `vite.config.ts` serves https when `DEV_HTTPS_CERT` and `DEV_HTTPS_KEY` are given; README's setup and OPERATIONS § A developer instance. The user's request: "we prepare this to be accessible once we release the code on github, so other people can run their developer instance very easily". Checked: the script's syntax, the address found (`192.168.0.36`), the build with the config; the servers are tried by the user in their own terminals (no server started for it) |
| DP1 | One address for the application and the engine | DP1a | The application calls the engine's paths on its own address unless `VITE_API_URL` names another (D404); the Vite dev server forwards those paths to the engine, so `vite --host` serves a phone on the same network (D411); `PUBLIC_URL` is the address people open; the sign-in, provider and second-factor flows checked through it; OPERATIONS' settings and "Signing in from the browser" amended |
| DP2 | Images and a reference installation | DP1 | A `web` image built in two stages (the application built, then served by nginx with the engine's paths forwarded, D405, D406); the engine image as a non-root user, Uvicorn behind the proxy (`--proxy-headers`, the proxy's address trusted), a health check; `compose.yml` as the reference installation (database, engine, web) reading an `.env` the operator fills from `.env.example` (D408, D409); HTTPS at `web` with the organisation's certificate files, HTTP sent to HTTPS (D407); the first administrator by `docker compose run`; the development compose file retired (D408) |
| DP3 | The deployment guide and its check | DP2 | OPERATIONS § Deploying: the topology, the settings in the order they are needed, the certificate, the public paths and `/metrics` kept inside, the first administrator, a sign-in provider's addresses, upgrading and backups by reference, "From a phone on the same network" for development; a deployment runner that builds the images, starts the installation from empty, creates the first administrator, signs in through `web` at a non-`localhost` address from a second browser context (a phone's size) and opens a collection (D410) |

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D404 | Where the application calls the engine | **Recommended:** on its own address by default (`/api/…`, `/oauth/…` relative to the page); `VITE_API_URL` stays for an engine on another address. Why: one build serves every installation and every device; the session cookie's one-site rule and `CORS_ORIGINS` stop mattering in the common setup. Cost: an installation with the engine on its own host sets `VITE_API_URL`, `CORS_ORIGINS` and the one-site rule as today |
| D405 | Who serves the application in production | **Recommended:** a `web` image: nginx serving the built files, the engine's paths forwarded to the engine, which stays an API. Why: the usual shape organisations run and their proxies and load balancers understand; caching, compression and certificates stay out of the engine; the engine and the application can be upgraded together from one release. Cost: a second container; an organisation with its own proxy copies the forwarding rules from the guide |
| D406 | Which engine paths are public | **Recommended:** `/api/v1`, `/api/consumer`, `/oauth`, `/.well-known`, `/docs`, `/openapi.json`, `/health`, `/health/live`; `/metrics` only inside (the monitoring network reaches the engine directly). Why: everything people and integrations need, and the process metrics only to monitoring. Cost: a monitoring system scrapes the engine's own port, not the public address |
| D407 | HTTPS | **Recommended:** ended at `web` with the organisation's certificate and key mounted as files, plain HTTP answered with a redirect, HSTS on; the engine trusts the proxy's forwarded address and scheme. An organisation's own load balancer in front may end HTTPS instead (the guide says how). Automatic certificates (ACME) are left out of the image. Why: organisations issue their own certificates for internal services; the session cookie is `Secure` only over HTTPS (D268). Cost: the operator provides and renews the certificate |
| D408 | The compose file | **Recommended:** `compose.yml` becomes the reference installation (database, engine, web, with health checks and the `.env`); the development compose file is retired, since development runs the servers locally (AGENTS.md) and the file no longer starts. Why: one compose file that works and that the guide describes. Cost: anyone using Docker for development uses the reference installation with the development settings the guide names |
| D409 | Secrets | **Recommended:** never in an image or the repository; the operator generates `SECRETS_ENCRYPTION_KEY`, `RDM_CURSOR_SIGNING_KEY` and the database password once into `.env` (`.env.example` lists every setting with a sentence each, the generating commands included), and keeps it beside the backups. Why: losing `SECRETS_ENCRYPTION_KEY` makes the stored signing and webhook keys unreadable (D253). Cost: one file the operator guards |
| D410 | How Track DP is tried | **Recommended:** DP1 by the browser runner of the sign-in (I2) through the Vite proxy at the laptop's network address; DP2 and DP3 by one deployment runner that builds the images and runs the installation from empty, once per package, each run announced (Docker builds load the laptop). Why: the questions are about reaching the installation, which only a real build answers. Cost: a runner of its own, run before R |
| D411 | A phone in development | _Revised 2026-10-25 after the user's iPhone try:_ **Recommended:** **accepted by the user, 2026-10-25, and delivered as DP1a:** `scripts/dev.sh` runs the developer instance, and with `--network` both servers over https on the computer's network address with an mkcert certificate (`scripts/dev.sh cert` finds the address on macOS and Linux and makes it), so another developer after the GitHub release runs one with a few commands; plain `vite --host` is not enough, because a page on `http://<address>` is not a secure page, and the sign-in (PKCE's `crypto.subtle`) and passkeys need one. On an insecure page the application says so instead of "The engine cannot be reached" (it said that on the iPhone). Why: the user's setup stays the two servers they run, with one documented switch. Cost: a one-time certificate per laptop; the phone accepts its warning or trusts the certificate |
| D412 | Consumer OpenAPI documents need no token (**narrows D266**) | _Reported by the user, 2026-10-25:_ `/docs` listed the three consumer sources and each answered `401`, because Scalar loads them from the browser with no header. **Decided by the user (2026-10-25):** each definition's `openapi.json` is public, like the management `/openapi.json`; the index and the data routes keep their tokens. Why: the document is the contract, with no data, and a client needs it before it has a token. Cost: the shape of a workspace's consumer contracts is readable without signing in; `?workspace=` still answers `404` for a workspace that does not exist |
| D413 | How a webhook key rotates | **Recommended (decided under the approved plan, 2026-10-25):** the previous key signs for the overlap and a second rotation inside it ends the earlier key's at once, so at most two keys sign; a suspended subscription may be rotated; a batch being retried is kept and signed again at each attempt with the keys in play then, so an overlap of 0 reaches a retry already waiting; a rotation is not a security event (subscription changes write no audit entry, C11). Why: the receiver's two-key window stays small, and a leaked key is closed for a failing receiver too. Cost: a receiver still on the old key after a rotation at once refuses everything until it has the new one, and the engine retries for 24 hours |
| D414 | Re-sealing the engine's secrets | **Recommended (decided under the approved plan, 2026-10-25):** `python -m app.cli.reseal_secrets` takes the current key from `SECRETS_ENCRYPTION_KEY` and the new one from `NEW_SECRETS_ENCRYPTION_KEY` (never an argument); it opens every sealed value first and writes none unless all open, in one transaction, and names a failure by kind and identity; `--check` only opens; the engine is stopped meanwhile. It covers every sealed column: token signing keys, webhook keys (current and previous), a provider's client secret, authenticator secrets and the provider ID tokens kept with a session and a sign-in. Why: the plan named webhook keys under a setting D253 had replaced; a partial re-sealing would leave values the new key cannot open. Cost: a stopped engine for the run, and a backup taken before it needs the old key |
| D415 | One implementation of every sign-in rule | **Asked by the user, 2026-10-25:** the JSON sign-in routes and the HTML pages use the same code; no rule is written twice. **Recommended:** the rules move out of the routes into engine functions that return outcomes; both kinds of route only translate input and present the outcome. Why: a fix or a new rule reaches both paths, and the JSON path cannot become a way round a check. Cost: `oauth.py` is reworked before the screen is built, and its journeys prove nothing changed for outside clients |
| D416 | The application's sign-in endpoints | **Recommended:** JSON routes beside the HTML ones (for example under `/oauth/sign-in/...`), included in the API reference, answering with the next step or the error; passkey ceremonies, which already answer in JSON, are shared. Providers keep their redirects (`/oauth/providers/{key}/start` and the callback). Why: the application draws the screens and reads "wrong password" or "wait 40 seconds" as data. Cost: a second, documented contract to keep stable (L2) |
| D417 | The engine's HTML pages | **Recommended:** they stay for outside applications that sign people in on the web, with the welcome words and branding already on them. Why: an outside client cannot use the application's screen. Cost: two presentations of one flow, kept thin by D415 |

### K1: Webhook signing-key rotation

**Needs:** Z1.

**Scope:** `POST /api/v1/consumer-subscriptions/{id}/rotate-secret` (CONSUMER_API): a new key shown
once; during an overlap window (D238) deliveries carry both signatures in `RDM-Signature`, after it
only the new one, so a rotated key stops verifying (the exit gate). The re-sealing of every key under
a new `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (C-D96's format byte) as a CLI command. "Rotate key" on
the webhook's page.

##### K1 record (2026-10-25)

**Delivered 2026-10-25.** D413 and D414 were decided by recommendation under the approved plan (the
user may reopen them).

- **Migration** `20261108_01_webhook_key_rotation`: `consumer_subscriptions.previous_signing_key` and
  `previous_signing_key_expires_at`.
- **Engine:** `subscriptions.rotate_secret` (claims the version, seals a new key, moves the current one
  to the previous column with the end of its overlap, or drops it with an overlap of 0) and
  `signing_secrets` (the keys signing at a moment); `delivery.headers` signs with each and joins the
  signatures with a comma; the dispatcher and a manual resend both call `signing_secrets`.
  `engine/identity/resealing.py` and `python -m app.cli.reseal_secrets` (D414).
- **API:** `POST /consumer-subscriptions/{id}/rotate-secret`, `previousSigningKeyExpiresAt` on a
  subscription. The OpenAPI lock holds the default configuration, where the subscription routes are off,
  so it did not move; the route inventory test lists the new route.
- **Frontend:** **Rotate key…** on a webhook's page, the new key shown once with how long the old one
  signs, "Previous key signs until" in its facts. The client's rotation dialog became the shared
  `ui/RotateOverlapDialog`, which both pages use. **Runner** `u5-webhooks` gains the rotation, with
  both signatures checked at the receiver and a 390px check.
- **Documents:** API.md (a section of its own), CONSUMER_API, OPERATIONS (Changing
  `SECRETS_ENCRYPTION_KEY`), ARCHITECTURE, USER_JOURNEYS (J43.3–J43.5), API_JOURNEYS,
  CURRENT_FUNCTIONALITY, UI_ACCEPTANCE (K1-1, K1-2), EXECUTION_GUIDE, CHANGELOG, PROJECT_STATUS.

**Where it differs from the plan:**

- **The re-sealing takes `SECRETS_ENCRYPTION_KEY`, not `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`:** D253
  replaced that setting in I1, and the sealed values are no longer only webhook keys. The command covers
  every sealed column (D414).
- **The tests were written after the code,** not seen failing first; they exercise it through the API
  and the real command.

**Checks:**

- `test_j43_webhook_key.py`: 8 passed (4 cases x 2 configurations): the overlap with both signatures and
  then one, a second rotation ending the first key's overlap, an overlap of 0 reaching a waiting retry
  and a suspended subscription, refusals (`VERSION_CONFLICT`, `SUBSCRIPTION_NOT_FOUND`, `422`,
  `FORBIDDEN` for a Reader), and the re-sealing command run for real (wrong key, same key, missing key,
  `--check`, success, signing keys opening under the new key, none under the old). Unit
  `test_delivery`: the list of signatures.
- **The groups the guide selects for the boundary** (`feed or startup or contract`, parallel): 488 passed
  and one failed, `test_api_journeys::test_every_error_code_is_listed` for `NOT_FOUND`, which
  `management/operator_assets.py` raises since the branding commit `68dfc8a` and API_JOURNEYS does not list:
  not K1's. Its serial part selects nothing. Also the unit tests for `engine/events` and
  `engine/identity` and the `test_j39_*` identity journeys: 34 passed, `test_startup` (head
  `20261108_01`) and `test_schema_drift`.
- Vitest: `WebhooksPage.test` (two new cases), `RotateOverlapDialog.test` and `src/features/security`;
  lint 0 errors (its 8 warnings are older), `prettier`, `tsc`, build.
- **Runner `u5-webhooks`:** passed, 21 checks, axe 0 violations on its eight scans; the rotate and key
  dialogs inspected at 1440px and 390px.

**Not verified:**

- **The Clients page's rotation in a browser** was unverified when K1 was delivered, because `sp2-clients`
  had drifted from U9's grant dialog. It was brought up to date afterwards (the grid's ticks, one Grant
  for both consumer APIs, Roles by card, the narrowing) and passes, rotation included. `sp1-security`
  drives the older Role dropdown too and has not been run.
- **A smoke start against the development database:** the migration was applied by the tests' databases;
  the user's `uvicorn --reload` server upgrades theirs when it reloads.

**What the user cannot do yet:** nothing from this package; C1 followed (2026-10-26).

### C1: The "try it" console authenticated

**Needs:** I2.

**Scope:** `/docs` sends requests with the signed-in person's token (D240); a client's token can be
pasted for testing a client's view. `/docs/oauth2-redirect` stays 404.

### E1: Security checkpoint

**Needs:** Z1–Z5, I1–I4, SP1, SP2, K1, C1 (I4 by D382).

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
_Amended by HM1 (2026-10-25):_ A3 also adds "Waiting for your approval" to the home page (D335).

## Decisions

**Accepted by the user on 2026-10-22**, each as recommended (D232: yes, Track A after the cut
line). Each is explained in plain words: what is decided, why the recommendation, and what it costs.

| # | Question | Recommendation |
| --- | --- | --- |
| D224 | Where people's identities come from | **Recommended:** local accounts **and** OpenID Connect sign-in providers (I3), the engine issuing its own token either way (C-D1). Why: an organisation already has a directory (Entra ID, Google, Okta, Keycloak) and expects its people to sign in with it, its MFA and its leavers' process; local accounts are still needed for the first administrator, small installations and a way back when the provider fails. SAML and LDAP are left out: most providers speak OIDC, and SAML adds a second protocol to keep secure. Cost: I3 as a package, a minimal provider in the test harness |
| D225 | Multi-factor authentication | **Recommended:** left to the sign-in provider in 0.12; local accounts have password only, which OPERATIONS states with the advice to use a provider in production. TOTP for local accounts in TODO for after 1.0. Why: MFA is what the organisation's provider already does well; building TOTP, recovery codes and resets is a package of its own. Cost: an installation with local accounts only has no second factor |
| D226 | Where permissions live in a request | **Recommended:** the token proves **who** (subject, client, expiry, a coarse audience: management or consumer); **what** they may do is looked up on the server per request from a cache invalidated across processes when a grant changes. Why: a role removed takes effect on the next request, not when a token expires; tokens stay small however many workspaces a person works in. Cost: one cached lookup per request; the cache invalidation (reusing N1's signal) |
| D227 | How roles are made | **Recommended:** the user's idea as stated: **action groups** named after journeys (P0's table) → **roles** made of action groups → **grants** of a role to a user, group or client at a scope. Predefined roles are read-only; a custom role is created from scratch or copied from one. Why: an administrator thinks in jobs ("may publish"), not in 157 routes; a new route joins an existing group without touching any role. Cost: the catalogue's upkeep, checked by the contract test |
| D228 | Scopes of a grant | _Narrowed by D243 (2026-10-23): reads are per workspace only._ **Recommended:** the instance or one workspace; within a workspace optionally narrowed to applications and record types **for writes**; reads are per workspace (and application). Why: SC-13 asks that "a permitted editor can edit only the assigned scope"; hiding a record type from a reader would need every list, query, relation column, feed, export and lookup filtered, with no user need recorded (ARCHITECTURE: record-level and finer rules only on demonstrated need). Workspaces are already the governed scope (ADR-031). Cost: data that must be hidden from some readers goes in its own workspace |
| D229 | Groups | **Recommended:** local groups managed in the engine, plus **provider groups** taken from a sign-in provider's claim at each sign-in; both hold grants the same way; no nested groups. Why: the user's idea 1, and in an organisation with a directory, membership is managed there and only the grant lives in the engine. Cost: a provider group's members are only known after they sign in once |
| D230 | The predefined roles | **Recommended**, named after the PRODUCT personas and common governance practice: **Reader** (Browse), **Contributor** (Browse, Work in change sets: proposes, cannot publish, D231), **Editor / Data steward** (Browse, Edit live, Work in change sets, Publish, Bulk and import), **Data owner** (Steward's groups plus Approve publications with own, Feed, Copy and move), **Model administrator** (Model authoring, Model release), **Workspace administrator**, **Integration administrator** (Integration administration, Feed), **Operator** (Operations), **Security administrator** (Security administration only, no data). For clients: **Consumer** (consumer API grants only) and any role above. Why: covers ideas 4 and 5 with names people recognise, and separates security administration from data so no single default role does everything. Cost: names to agree; nine roles to keep true in the catalogue |
| D231 | Editing live as its own permission | **Recommended:** Edit live and Work in change sets are separate action groups. Why: it is what makes the Contributor of idea 5 possible: a person who can change things only by proposing them. With today's behaviour (a correction is live when saved) the Editor keeps live editing. Cost: Z2 checks the two separately on every write path |
| D232 | Approvals in 0.12 | **The user decides; conflicts with the roadmap (1.0) and PRODUCT.md's rule.** Recommended: **yes, change-set publication only, as Track A after the cut line**, with self-approval for those whose role allows it and a per-workspace four-eyes policy. Why: with D231, a Contributor's change set otherwise waits for someone to notice it; approval needs identity and roles, which 0.12 brings, and its smallest useful flow (submit, review, approve or send back with a comment, notify, audit; REAL_WORLD_RESEARCH) is small once they exist. No one is forced into it: the default roles publish as today, which keeps ADR-026. Approvals of model activation and rollback stay in 1.0's protected publishing. Cost: Track A (three packages); if 0.12 must ship sooner, the cut line releases without it and it follows in 0.12.x |
| D233 | How approvals notify | **Recommended:** an inbox in the engine (API and top bar) and webhook events for each step; **no e-mail** in 0.12. Why: API first: an organisation routes the events to its e-mail, Teams or Slack with its own tooling; sending mail needs SMTP settings, templates, bounces and unsubscribes. Cost: without integration work, a person learns of a request only when they open the app |
| D234 | How the browser holds its session | **Recommended:** authorization code with PKCE; the access token (short-lived: an hour, D251 as amended 2026-10-23) in memory, the refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie that only the token endpoint reads. Why: the current OAuth guidance for browser applications; a script injected into the page cannot read the refresh token, and the engine still issues one token format for all clients. Cost: the frontend and engine must share a site (one origin or a same-site subdomain), which OPERATIONS states |
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
| 1 | [P0](#p0-design-pass) | — | **Delivered 2026-10-23.** The catalogue and action groups, roles, ADR-043/044/045, API design, J39–J43, mock-ups approved; D224–D257 settled |
| 2 | [I1](#i1-the-issuer-people-and-clients-every-route-authenticated) | P0 | The issuer, users and clients, every route authenticated, harnesses on real tokens |
| 3 | [I2](#i2-signing-in-from-the-browser) | I1 | **Delivered 2026-10-23.** The sign-in page, PKCE, the account menu and page |
| 4 | [Z1](#z1-roles-groups-and-grants-at-the-route) | I1 | **Delivered 2026-10-23.** Roles, groups and grants; every route checked; `/me/permissions` |
| 5 | [Z2](#z2-record-types-at-the-write-unit-jobs-moves-and-the-feed) | Z1 | **Delivered 2026-10-24.** Record types at the write unit; jobs as their requester; moves; source files |
| 6 | [Z3](#z3-consumer-apis-per-client) | Z1 | Consumer APIs per client and workspace |
| 7 | [Z4](#z4-audit-identity) | Z1 | **Delivered 2026-10-24.** The actor beside `cause` everywhere; security events |
| 8 | [Z5](#z5-the-interface-follows-the-callers-permissions) | Z2, I2 | **Delivered 2026-10-24.** The interface follows permissions; Reader and Contributor |
| 8a | [Z6](#z6-one-persons-changes-across-workspaces) | Z4, Z5 | **Delivered 2026-10-25.** One person's or client's changes across workspaces, filtered to what the caller may browse |
| 8b | [HM1](#hm1-a-home-page-after-sign-in) | Z5 | **Delivered 2026-10-25.** A home page after sign-in: workspaces as cards, what waits for the person, Continue where you left off |
| 8c | [TV1](#tv1-a-records-parent-in-its-list) | — | **Delivered 2026-10-25.** A table view's Columns… and Filters… offer the record's relationships, its parent's first |
| 8d | [LS1](#ls1-a-collections-rows-scroll-on-their-own) | — | **Delivered 2026-10-25.** A collection's table page fitted to the window, only its rows scrolling; each row drawn once; the wheel left to the browser |
| 8e | [HM1a](#hm1a-homes-workspace-tile-and-continue) | HM1 | **Delivered 2026-10-25** (`hm1-home` passed, axe clean). A workspace card's tile opens the workspace; Continue on its own shade, light and dark |
| 8f | [RH1](#rh1-a-records-history-shorter-and-with-its-values) | Z4 | **Delivered 2026-10-25;** the OpenAPI lock re-baselines with I4a (see its record). A record's history by day, filtered, with old → new values (D16 revised for history) |
| 8g | [RA1](#ra1-a-persons-recent-activity-like-the-history) | RH1 | **Delivered 2026-10-25.** A person's recent activity like the history: by day, kinds, 10 then 20, Show fewer |
| 8h | [SP1b](#sp1b-a-groups-members-several-at-once) | SP1, I3 | **Delivered 2026-10-25.** Group members: search and tick, paste a list checked first, several removed at once |
| 9 | [SP1](#sp1-people-groups-and-roles) | Z1, I2 | **Delivered 2026-10-24.** Settings › Security: people, groups, roles, grants |
| 10 | [SP2](#sp2-oauth-clients-and-their-access) | Z3, SP1 | **Delivered 2026-10-25.** Settings › Security: clients and their access, signing keys (sign-in providers moved to I3, D357) |
| 11 | [I3](#i3-a-sign-in-provider) | I2, SP2 | **Delivered 2026-10-25.** OpenID Connect providers and their groups; Settings › Security › Sign-in |
##### C1 record (2026-10-26)

**Delivered 2026-10-26** under D240, with no new decision. What was built:

- **Engine:** `POST /oauth/console-token` (`management/routers/oauth_console.py`, outside the OpenAPI
  document, under `/oauth` where the refresh cookie is readable): the person's open session is found
  from the cookie by `sessions.open_session_of_refresh_token` **without renewing it** (so it never
  uses a refresh token the application's tabs hold, D269) and a `management` token bound to that
  session is issued; `401 not_signed_in`, and `403 access_denied` when `Origin` is not the address the
  request reached.
- **The page:** `/docs` still renders the same configuration call; a second script asks for the token
  and hands it to Scalar for both schemes the documents declare (`engineOAuth`, `oauth2`) through
  `updateConfiguration`, with an `onBeforeRequest` hook that renews it in its last minute only when the
  request carries it, so a pasted token is never replaced.
- **Journey J39.11** (4 cases, two configurations): the person's token and an unchanged cookie, the
  person's own permissions, no session or signed out, another site. Runner `v1-api-reference`
  extended: the console sends the person's token (200), a pasted client token is the one sent, a
  browser with no session gets 401; the runner was also repaired for the OAuth section now first on
  the page (it had waited for a model operation and sent unauthenticated since I1).

**Exercised:** `test_j39_api_reference` (8), `test_api_reference`, `test_j20_discover`,
`test_boundaries`, `test_openapi_contract` (43 passed together), `ruff`; `v1-api-reference` at 1440px
and 390px, passed (axe findings are Scalar's own markup, as before).

**Not verified:** the renewal in the token's last minute in a browser (the hook's shape was read from
a live request, the renewal path was not run); the console's appearance was not compared in dark mode.

| 11a | [I4](#i4-a-provider-identity-linked-signing-out-of-the-provider-a-second-factor) | I3 | Planned 2026-10-25 (D382): I4a linking, provider sign-out, the local sign-in switch; I4b an authenticator app for local accounts; I4c passkeys |
| 11b | [I5](#i5-a-sign-in-screen-in-the-application) | I4 | Planned 2026-10-25 (D415–D417): the application's own sign-in screen over JSON sign-in routes; every rule once, shared with the engine's HTML pages |
| 12 | [K1](#k1-webhook-signing-key-rotation) | Z1 | **Delivered 2026-10-25.** Signing-key rotation with overlap, Rotate key… on a webhook's page; re-sealing as `python -m app.cli.reseal_secrets` |
| 13 | [C1](#c1-the-try-it-console-authenticated) | I2 | **Delivered 2026-10-26.** The console with the person's token |
| 12z | [DP1a](#track-dp--deployment) | — | **Delivered 2026-10-25.** `scripts/dev.sh`: a developer instance, on this computer or over https on the network |
| 13a | [DP1](#track-dp--deployment) | DP1a | One address for the application and the engine; a phone in development (planned, D404, D411) |
| 13b | [DP2](#track-dp--deployment) | DP1 | The `web` and engine images, `compose.yml` as the reference installation, HTTPS, secrets (planned, D405–D409) |
| 13c | [DP3](#track-dp--deployment) | DP2 | OPERATIONS § Deploying and the deployment runner (planned, D410) |
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
Authz:           I1 ─ Z1 ─┬─ Z2 ─ Z5 (needs I2) ─┬─ Z6 (needs Z4)
                          │                     └─ HM1
                          ├─ Z3 ─ SP2
                          ├─ Z4
                          ├─ SP1 (needs I2) ─ SP2
                          └─ K1
Lists:      TV1 (on 0.9 K5/K6; any time)
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
