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
