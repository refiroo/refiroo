# Project status

## In progress — Product 0.12, security and the first public release

[Planned](BASE_0_12_IMPLEMENTATION_PLAN.md) 2026-10-22, the security plan and D224–D242 accepted
the same day. **P0, the design pass, is delivered (2026-10-23):** D243–D257 accepted (access tokens
last an hour, D251 changed by the user); ADR-043 (identity and tokens), ADR-044 (authorization:
action groups, roles, grants; reads per workspace, writes narrowed) and ADR-045 (change-set
publication approvals); the catalogue of all 159 operations in API.md § Security with the OAuth,
caller, administration and approval routes; J39–J43; U8 detailed from the approved
[mock-ups](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo)
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#p0-record-2026-10-23)). **I1, the engine issuing tokens,
is built (2026-10-23)**, D258–D265 accepted: the OAuth metadata, JWKS and client credentials token
endpoint; people, clients and signing keys through the API; `create_admin` and `create_client`;
every route but the open ones needs a token; `SECRETS_ENCRYPTION_KEY` and `PUBLIC_URL`; both test
harnesses on real tokens ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i1-record-2026-10-23)).
The whole backend suite passed but for one timing budget under parallel load, and the
settings browser runner passed. D266 (the consumer index and documents take a management token
too) decided and built. **I2, signing in from the browser, is delivered (2026-10-23)**, D267–D275
accepted: the engine's sign-in page with PKCE, sessions in an `HttpOnly` cookie renewed unseen (each
refresh token once), sign-out, failed sign-ins slowed, the account menu and Settings › Account
(password, sessions, sign out everywhere), the one-time password link and signing a person out
through the API, the job stream and downloads through `fetch`, and the browser runners signing in as
a test person ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i2-record-2026-10-23)). Its journeys, unit
tests, three browser runners and the touched Vitest files passed; the full suites and the other
browser runners wait for R. **Z1, roles, groups and grants at the route, is delivered
(2026-10-23)**, D277–D288 accepted: every operation declares its action and refuses with
`403 FORBIDDEN` what the caller's roles do not allow; nine predefined roles and custom ones, local
groups, grants at the instance or in a workspace, who can do what in a workspace, the caller's own
permissions and grants; lists filtered; permissions follow a generation PostgreSQL raises on every
change; the first administrator and the principals from before hold the setting-up roles; Account
and the account menu show the person's roles
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z1-record-2026-10-23)). Its journeys, unit tests, the
neighbouring journey groups, the sign-in runner and the touched Vitest files passed; the full suite
runs with Z6 (the user, 2026-10-24). **Z2, record types at the write unit, is delivered
(2026-10-24)**, D289–D297: a narrowed grant limits every write (live, change sets, restructurings,
batches, imports, publications, moves) with `403 FORBIDDEN` naming the record types; jobs run as
their requester at every step; an import profile's files stay with their uploader and workspace;
stale grants are reported and allow nothing
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z2-record-2026-10-24)). Its journeys, unit tests and the
neighbouring write-path, migration, event and several-process groups passed; the full backend
suite runs with Z6, which closes Track Z (moved from Z5 by the user, 2026-10-24). **SP1, the Security pages, is delivered (2026-10-24)**,
D298–D305: Settings › Security › People, Groups and Roles for Security administrators, a
workspace's Access, one grant dialog with the narrowing and a sentence of what it allows, the
one-time password link shown once; the people list names each person's roles, a person's grants
include their groups', groups and clients are found by name, and a role held only at the instance
is refused in a workspace ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#sp1-record-2026-10-24)). Its
journeys, the J40 and identity journeys, the contract tests, the touched Vitest files and the new
`sp1-security` runner on two models passed. No clients page until SP2; no sign-in provider until
I3. **Z3, consumer APIs per client, is delivered (2026-10-24)**, D306–D312: a consumer API is read
in a workspace only with a grant of it there (a grant naming `consumerApi` instead of a role, to a
client, person or group); `403 FORBIDDEN` naming the API and workspace, checked after the workspace
and before the definition; the index lists what a consumer token is granted, every API for Browse
with a management token; each OpenAPI document declares the client credentials scheme and `401`
and `403`; subscriptions name their owner; Access shows "Consumer API: *name*"
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z3-record-2026-10-24)). Its journeys, every journey
module reading the consumer API, the contract and foreign-key tests and the `sp1-security` runner on
two models passed. **Z4, audit identity, is delivered (2026-10-24)**, D313–D320: every audit entry
names its actor beside its cause (the caller, a job's requester, a publication's publisher, or the
engine; nobody before Z4), shown on record history, the feed and activations; change sets name
their creator, publications their publisher and withdrawer, jobs their requester and editor
operations their author; changes to access and sign-ins are security events, read at
`/security-events` and on a person's Recent activity; consumer events name no one
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z4-record-2026-10-24)). Its journeys, the journeys whose
reads gained a field, the registries and contract tests, the touched Vitest files and the
`sp1-security` runner on two models passed. **Z5, the interface following permissions, is
delivered (2026-10-24)**, D321–D330 (D323 changed by the user: hidden, never disabled, and a flow
only when it can finish): a Reader sees no way to change anything and the band says so; a
Contributor proposes a change into a change set of their own; a narrowed writer edits only the
permitted types; the application opens in a workspace the person may read or says there is none;
Settings lists only the pages of groups held; `GET /me/action-groups`, `holding=` on workspaces and
`createdBy=` on change sets ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z5-record-2026-10-24)). Its
journeys, the contract tests, the touched Vitest folders, the new `z5-permissions` runner on two
models and every other runner the execution guide selects passed but `j4-import` and the
navigation runner, which fail the same before Z5 (TODO). **HM1, a home page after sign-in, is
delivered (2026-10-25)**, added by the user and D331–D339: signing in opens Home, with the person's
workspaces as cards on their own models, what waits for them, Continue where they left off and
their change sets across workspaces; `GET /me/workspaces`, `GET /me/change-sets` and the instance's
product on `GET /system` ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#hm1-record-2026-10-25)). Its
journeys, J31, the contract tests, the touched Vitest folders and the runners `hm1-home`,
`z5-permissions`, `w4-workspace-admin` and `u3-settings` passed. **Z6, one person's changes across
workspaces, is delivered (2026-10-25)**, D340–D347, which closes Track Z: `GET /changes` reads the
data and model changes the caller may see, by person or client, workspace, kind and time; every
audit entry of a workspace now names it, also a change set's work (migration `20261102_01` places
the existing ones); a person's or client's Changes page, opened from a name in a record's history,
a person's page and Home's Your recent changes ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#z6-record-2026-10-25)).
Its journeys and those whose entries changed, the unit and contract tests, a smoke start and timing
on a copy of the development database, the touched Vitest folders and the runners `z6-changes`,
`hm1-home` and `sp1-security` passed. The full backend suite ran: of its five failures, three from
Z3 and Z4's test budgets and harness are fixed, one fails only under its load (TODO), and it took
13 min 9 s, over its ceiling (TODO). **SP2, clients and their access, is delivered (2026-10-25)**,
D348–D357: Settings › Security › Clients (the ID and secret shown once, rotation with a chosen
overlap, secrets told apart by their last four characters, the previous one ended early, rename,
deactivate and restore, its access, the webhooks it created, its recent activity) and Signing keys;
the grant dialog grants a consumer API and reads `GET /workspaces/{key}/grant-options`, so a Security
administrator without Browse can use it; a client's reads name its roles, consumer APIs and creator
(migration `20261103_01`) ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#sp2-record-2026-10-25)). Its
journeys, the identity, security-page and consumer-grant journeys, the contract, startup and
foreign-key tests, the touched Vitest folders and the runners `sp2-clients`, `sp1-security`,
`u5-webhooks` and `u3-settings` passed; the development database upgraded through the running
server. **I3, a sign-in provider, is delivered (2026-10-25)**, D361–D370: OpenID Connect providers
on Settings › Security › Sign-in (checked when saved, the address to register shown), the sign-in
page's "Continue with" button, a person found by the provider and subject or created at their first
sign-in, provider groups under their provider with members seen, made ahead and granted like any
group, and local sign-in turned off with the administrators made on the server keeping it
(migration `20261104_01`) ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i3-record-2026-10-25)). Its
journeys against the harness's minimal provider, the identity, security-page and authorization
journeys, the unit, contract, startup and foreign-key tests, the touched Vitest folders and the
runners `i3-sign-in-providers`, `i2-sign-in`, `sp1-security` and `u3-settings` passed; the
development database upgraded through the running server. **I4a, a provider identity linked, signing
out of the provider and the last kept person, is delivered (2026-10-25)**, D377–D381 ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i4a-record-2026-10-25),
migration `20261105_01`). **I4b, a second factor for local accounts, is delivered (2026-10-25)**,
D383–D388 ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i4b-record-2026-10-25), migration
`20261106_01`). **I4c, passkeys, is delivered (2026-10-25)**, D389–D394
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i4c-record-2026-10-25), migration `20261107_01`); I4
is complete. A sign-in against a real provider the user
names waits for its registration, before E1. **K1, webhook signing-key rotation, is delivered
(2026-10-25)**, D413 and D414: a webhook's key rotated with an overlap, both signatures in
`RDM-Signature` meanwhile, Rotate key… on its page, and `python -m app.cli.reseal_secrets` for a new
`SECRETS_ENCRYPTION_KEY` ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#k1-record-2026-10-25), migration
`20261108_01`). **C1, the "try it" console authenticated, is delivered (2026-10-26)**: `/docs`
holds the signed-in person's token, a client's token may be pasted
([record](BASE_0_12_IMPLEMENTATION_PLAN.md#c1-record-2026-10-26)). **M1, sending mail, is delivered
(2026-10-26)**, D418–D422 and D423: Settings › Integration › Mail holds the SMTP server (password
sealed), a test message names what failed, and an outbox sent by a thread in each process retries for
24 hours; nothing queues a link yet (SP3, I6, M2) ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#m1-record-2026-10-26),
migration `20261109_01`). **SP3, a new person's link by mail, is delivered (2026-10-26)**: New person and
Reset password mail the one-time link when mail is set up and the person has an address, and still show it
once ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#sp3-record-2026-10-26)). **I6, a forgotten password on the sign-in screen, is delivered (2026-10-26)**: the screen asks by username or e-mail address, answers the same whoever is named, and mails a link to the application's reset page ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#i6-record-2026-10-26)). **Track DP, deployment, is delivered (2026-10-26)**, D404–D411: one address for the application and the engine
(DP1), the engine and web images and `compose.yml` as the reference installation (DP2), the deployment
guide in OPERATIONS § Deploying and `npm run test:deployment` (DP3), automatic HTTPS as an overlay
(DP4). **E1, the security checkpoint, is delivered (2026-10-26)**: a generated sweep of every operation
by every predefined role, the consumer routes, the routes outside OpenAPI, person tokens and reset with a
second factor ([J47](product-functionality/USER_JOURNEYS.md)); the deployment runner and a ten-case
sign-in against Keycloak (which found and fixed the provider callback's `iss` defect); and an
independent review of the 0.12 changes whose findings are all fixed or accepted
([record](SECURITY_REVIEW_0_12.md)), among them deletions skipping the narrowing check (high), source
files and the import profile check across workspaces, the forwarded address behind a balancer, a 500 on
a binary body and a 503 on a NUL byte. **A1, a publication request and its approval, is delivered
(2026-10-26)**, D424–D427: Approve publications (Data owner), submit, withdraw, approve (which publishes) or send
back with a comment, a per-workspace policy (`requireApproval`, `secondPerson`), a submitted change set frozen
unless a write carries `withdrawSubmission=true`; the API only ([record](BASE_0_12_IMPLEMENTATION_PLAN.md#a1-record-2026-10-26),
migration `20261110_01`). 0.12 is released complete: next A2, A3, M2, L1, L2 and R (no cut
line, the user, 2026-10-26).

## Current development baseline — Base 0.11 complete (2026-10-22)

**Base 0.11 is complete**, build acceptance R included
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#r-build-acceptance-and-release)), versions 0.11.0; the
commit and the tag `v0.11.0` follow the user's instruction. Production hardening and staged model
rollout: each workspace runs a model of its own (Track M), moves to another release with a preview
and confirmation, a change set published with that migration or moved onto the workspace's release
(Track V), records move between workspaces whose models differ (Track X), and the engine runs on
several processes and nodes, at volume, observable and with a rehearsed backup (Tracks N, Q, O),
with touch drag in the tree (U1). L1 and L2 (licensing, policies, the compatibility commitment) moved
to 0.12, the first public release, since the project's name is not chosen yet.

R reviewed every change since 0.10.0 with an independent reviewer (12 findings: 10 fixed with their
regression tests, R-F7 kept and documented and R-F11 left by the user's decision and in TODO), and
ran: the backend suite (6,180 cases, 10 min 51 s with `-n 6`, under S1's ceiling; 4 failures from R's
own test-device change, fixed and rerun), Vitest (939), all 55 browser runners and a new one walking
J36–J38 by keyboard alone on two models (`workspace-r`), the accessibility (217 checks) and visual
(172) gates with Settings › Operations, an upgrade of a database built by 0.10.0, a smoke start on a
copy of the development database, and the budgets (9, 12 min 12 s with the full-volume fixture
rebuilt). The runners found three more product defects, fixed: notice actions overflowing at 390px,
a dialog's list drawn by row number staying empty, focus lost after applying a restructuring; seven
runners were brought up to date with delivered changes, and one flake is in TODO. **Waiting for the
user:** approval of 13 re-recorded and 3 new visual baselines, with X5's ten and U1's screenshots,
and the real-phone try of touch drag (D215). Next: 0.12, security and the first public release.

## Base 0.10 complete (2026-10-15)

**Base 0.10 is complete**, build acceptance R included
([record](BASE_0_10_IMPLEMENTATION_PLAN.md#r-build-acceptance-and-release)): the model designer and
spreadsheet onboarding, with schema 0.10 released (D153; the starter stays content release 0.9.5).
R reviewed every change since 0.9.0 (14 findings, one independent reviewer for migrations,
concurrency and contracts) and ran: the backend suite (5,771 cases, 8 min 31 s, over its ceiling as
D152 expected), Vitest (861), all 49 browser runners, a new runner walking US-P09 and US-P10 by
keyboard alone at 1440px and 390px (`authoring-r`), the accessibility (173 checks) and visual (143)
gates with 14 new spreadsheet and cell scenarios, a smoke start and schema 0.10 checks on a copy of
the development database (D150: no upgrade from a tag), and the budgets. It fixed all 19 findings
(R-F1–R-F19; migration `20261017_01` for R-F14), among them: an import deleting records a
refused row named, a file's profile blocking the next upload and the editor, inference ignoring
cancels, a rename stopping the dry run for good, the next version's check of a translated workbook
(56 s at 200 rows) and of W1 at 10,000 rows (101 s, now 16 s), and relation chips no longer using
the cell's width since A9. The commit and the tag `v0.10.0` follow the user's instruction (D153).
Open: the backend suite's time (D152, the next build's first package) and, in TODO, one
visual-gate flake whose cause was not found. Next: 0.11, [planned](BASE_0_11_IMPLEMENTATION_PLAN.md) 2026-10-15
in the shape of 0.10's plan. Part 1, first at the user's request, groups the workspace models (each
workspace a model of its own, a workspace moved to another release, data moved between workspaces
whose models differ); Part 2 is production hardening; Part 3 the release (the first public release moved to 0.12 on 2026-10-22). The P0 design
pass was delivered on 2026-10-15 (decisions D4–D29 and the move inventory accepted, ADR-042, the API
design, J36–J38, the M5 and X4 mock-ups approved). **M1, a release per workspace, is delivered
(2026-10-15)** with M2 folded in (the user rejected a bridge between them, D32): each workspace runs a
release of its own, a workspace is created on one, a release is activated into one workspace, and
every request resolves its workspace before its model, the commit guard per workspace
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#m1-record-2026-10-15)). **M3, what was instance-wide,
is delivered (2026-10-16)** through the API: import profiles belong to a model and are refused in a
workspace running another; a draft is compared with its own model, with compatibility reported for
each workspace running it; the consumer API index and OpenAPI documents per workspace; a model built
from a workbook installed into a new workspace. The editor's choice of workspace moved to M5 (D38).
**M4, reads spanning workspaces, is delivered (2026-10-16)** through the API: the cross-type lookup
reads several workspaces when asked for them, each record under its own workspace's model and naming
its release, refusing a type or application one of their models lacks; counterparts are refused
between workspaces whose models differ; every other read stays within one workspace
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#m4-record-2026-10-16)). **M5, the UI following the
workspace's model, is delivered (2026-10-16), screenshots approved**: the shell
loads each workspace's model and says when an address asks for something it lacks; Settings › Model
shows each workspace's model and activates into one workspace; a workspace is created on a chosen
release; the editor installs into an existing or new workspace
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#m5-record-2026-10-16)). **M6, the workspace-model
checkpoint, and M6a are delivered (2026-10-16)**: J36 composed in the browser on two generated models
beside the starter, from installing each into a new workspace to published change sets and a release
changed in one workspace; a page built on a replaced release cannot save (M6a, the optional
`X-Expected-Model-Release-Id` header); M5's surfaces in the accessibility and visual gates; the
upgrade of a 0.10.0 database checked by hand. Fixed on the way: the header's name following the
workspace's model, the phone band's workspace choice by tapping, two of M5's small findings, two
failing or order-bound tests. Settings › Model was reworked at the user's request and left laid out
as Settings › Workspaces; its redesign is recorded for 0.14
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#m6-record-2026-10-16)). **Released as 0.11.0-alpha.1
(2026-10-17, tag `v0.11.0-alpha.1`).** **V1, a workspace's data migrated to another release, is
delivered (2026-10-18):** decisions D68–D78 accepted; through the API a migration previews every
conversion, type change, loss and refusal of one workspace's data under another release, changing
nothing, and once confirmed (bound to the reviewed versions, accepting the loss) switches the data
and the release together ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#v1-record-in-progress-2026-10-17)).
Its screen is built on the approved mock-up (2026-10-18): the activation dialog's Preview the
migration… opens a page in Settings › Model listing what the release no longer has, the items by
outcome, and confirming once the loss is accepted. A workspace of 100,000 records migrates in under
three minutes (preview 66 s, execution 111 s). **V2 is delivered (2026-10-18):** decisions D79–D86
accepted; a change set on a release its workspace no longer runs, such as one started from an older
publication, is published by migrating the workspace to that release, previewed and confirmed in one
job, through the API and from the change set bar
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#v2-record-2026-10-18)). **V3 is delivered (2026-10-18):**
decisions D87–D96 accepted; a change set left on a release its workspace no longer runs moves onto
the release the workspace runs even when its content does not fit: one preview lists the conversions
and losses in its content and what must be fixed (a record changed both in it and live since it
started, a rule it breaks), and the confirmation converts its content and makes live data its base,
never touching live data, through the API and from the change set bar
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#v3-record-2026-10-18)). **V4 is delivered (2026-10-18):**
decisions D97–D103 accepted; the schema-language window, 0.5–0.10, is declared once and its
conversion rules are written in APPLICATION_MODEL (reading, writing, side by side, between releases
of different versions by declarations only, outside the window); installing a draft outside the
window is refused naming the window, as activation is; a model file outside it refuses startup with
what to do, and a workspace on a release a later engine wrote is logged with that recovery
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#v4-record-2026-10-18)). **X1 is delivered (2026-10-18):**
decisions D104–D113 accepted; a mapping between two models is saved through the API, proposed by an
inference over the two models and the records two workspaces share (each proposal with evidence and
alternatives, applied as steps marked as proposed), corrected with operations, undone and redone, and
read with its problems and coverage; drafts and mappings share one history (migration
`20261020_01`; [record](BASE_0_11_IMPLEMENTATION_PLAN.md#x1-record-2026-10-18)). **X2 is delivered
(2026-10-18):** decisions D114–D123 accepted; `POST /moves` runs the dry run of a move through the
API: what each selected record and relationship becomes in a workspace of another model, created,
updated, refused by the target's rules or not moved with the mapping's reason, every row listed and
counted, nothing written (migration `20261021_01`, which adds the `pgcrypto` extension;
[record](BASE_0_11_IMPLEMENTATION_PLAN.md#x2-record-2026-10-18)). X2 went before S1 on the user's
go-ahead (D2 revised). **S1, the suite's time, is delivered (2026-10-18):** journey cases now
spread over the test workers one at a time instead of a module holding one worker, so J34 no longer
holds a run up (with J35, 1 min 10 s; alone 5 min 3 s in M1); measured twice, the suite's summed
test time is about 6 minutes over 10 cores even uncontended, so D126 runs the full suite with six
workers (10 min 15 s, the machine usable) under a ceiling revised to 11 minutes
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#s1-record-2026-10-18)). Three failures found failing
at `a73d667` too are in TODO (J35's eight, unique-value rows, an export over a release change).
**X3 is delivered (2026-10-18):** decisions D128–D137 accepted; a move's dry run waits for
confirmation, and confirming it (or `stage: execute`) loads what it previewed into a new change set
of the target workspace for review; each record a move creates keeps its origin (migration
`20261022_01`), so a second move updates it and a record moved back finds its original; `mode:
move` adds a change set of the source deleting what loaded, which publishes only after the copy; a
record's history names the move's origin; all through the API
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#x3-record-2026-10-18)). **X4, the move editor, is delivered (2026-10-19):** decisions
D138–D148 accepted; Settings › Data operations › Moves and New move…, the editor on the approved
boards (both workspaces, what moves, copy or move, the dry run's figures run again after every step,
the mapping by type with its Proposed rows, undo and redo, why a row was proposed), the report of
what cannot move and the start into a change set of the target, 390px as tabs; no backend change
([record](BASE_0_11_IMPLEMENTATION_PLAN.md#x4-record-2026-10-19)). Screenshots wait for the user's
approval. **X5, the move checkpoint, is delivered (2026-10-19):** decisions D149–D154 accepted; the exit item composed in the browser (`test:browser:workspace-x5`: a proposed and hand-completed mapping between partly compatible models, the report, the reviewed change sets published, a second copy updating the same records, records moved back, a subtree moved with its deletions), X4's surfaces in the accessibility and visual gates, and the whole volume workspace moved into another model at full volume (110,254 records: dry run 212 s, load 155 s, publish 206 s). Six defects fixed on the way: the publication's and change-set capture's copy pairing every record with every other on fresh rows (a publish of 11,000 moved records 544 s → 19 s; X3's 13-second wait), the dry run's per-record relationship read, writes of more than 65,535 records failing, a whole subtree's top record kept in the source, the deletions' refusal naming an ID; and the mapping grid, broken since `ad0d19c` ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#x5-record-2026-10-19)). Screenshots and ten new baselines wait for the user's approval. **X6, list reads within the agreed budget, is delivered (2026-10-19):** a relation column's related records read in one narrow statement in every context (the reported table opens in 0.66 s, 2.2 s before; budget cases in the volume baseline); every long list drawn by row number, reading the reader's page and filling itself in the background; rows cheap to draw (chips fitted from their text, edit buttons only on the active row), so the reported view scrolls at 60 frames a second in the production build; D159's full-volume run dropped with the user ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#x6-record-2026-10-19)). **N1, several processes on one database, is delivered (2026-10-19):** D165–D169 accepted; model administration with `WEB_CONCURRENCY` above 1 or several instances, a switch served by every process from its next request, installations and startup under database locks, and the read guard (a read whose release switched while it ran answers `409 MODEL_RELEASE_CHANGED`); a hole in the commit guard fixed on the way (a write waiting on an activation's lock committed under the old release) ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#n1-record-2026-10-19)). **N2, the job worker on several nodes, is delivered (2026-10-19):** D170–D175 accepted; a running job keeps its lease by a heartbeat whatever its step (before, a move's binding and long chunks were taken over and rolled back, two processes passing a job back and forth indefinitely), a job queued on a busy process starts at once on an idle one, submissions of one subject sent together leave the later one standing, a one-step job asked to stop writes nothing, a profile checks its newest file, a cancel answers at once during a move's long steps, and an export taken over by another process serves a whole file; checked with two workers per walk of every job kind and with real processes frozen and resumed ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#n2-record-2026-10-19)). **Q1 is delivered (2026-10-20), amended with the user (D176): no full-volume run; N3 no longer waits for Q1 and is no longer at full volume.** Each process's pool can be set (`DATABASE_POOL_SIZE`, `DATABASE_POOL_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`); a request with no database connection answers `503 DATABASE_UNAVAILABLE` naming why, instead of `500`; a start with more processes than the server takes warns; a pool of one connection can start (it could not); five `NOT IN` subqueries are `NOT EXISTS` and the move binding's and people export's working tables are analyzed, neither measured at full volume ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#q1-record-2026-10-20)). **N3, concurrency invariants with several processes, is delivered (2026-10-21):** D182–D185 accepted; the roadmap's first exit item met as D176 worded it: a unique value, a record's version, a parent cycle, a cardinality limit, feed positions and a job's item against a live write raced across two server processes on one database; a frozen process's locks released by the database after `DATABASE_IDLE_TRANSACTION_TIMEOUT` (300 s), where its workspace's writes waited until it resumed; a job step whose connection was lost no longer fails the job; no database constraint needed, the three writers of SQL text outside the write unit listed by the boundary test with their locks ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#n3-record-2026-10-21)). **Q2, model-derived indexes, is delivered (2026-10-21):** D186–D190 accepted; the value indexes stay the same for every model, and what follows a workspace's model is which values are looked up; a change set's unique checks and key references on numbers, decimals, dates and instants seek four new partial indexes (without them a check read and filtered all 3,231 values of the attribute at 1,000 items; with them it reads the 9 holders at 2,000 items; change-set creation within its run-to-run spread), live ones already sought their value; a move's match seeks the target's unique values by digest; the mapping inference counts unique values of every type and proposes the match on the attribute whose values the records share; the derived-values door decided (stored value rows only) ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#q2-record-2026-10-21)). **O1, metrics, logs, health and readiness, is delivered (2026-10-21):** D191–D197 accepted; `/health/live` beside the readiness probe; every process reports itself through the database, so `GET /api/v1/system/readiness` names each workspace served or unavailable with the processes that cannot serve it and why, and `GET /api/v1/system/processes` every process live or silent with its threads, pool and counters; `GET /metrics` the whole instance in the Prometheus format in one scrape; `LOG_FORMAT=json` lines, `LOG_LEVEL`, one access line and one `X-Request-Id` per request; a collision of processes starting together over the matrix state build fixed on the way ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#o1-record-2026-10-21)). **O2, backup, restore and the Operations page, is delivered (2026-10-22):** D198–D204 accepted; a backup restored into a separate database is checked with `python -m app.cli.restore_check` (prepared as startup would, every workspace served under its own model, each workspace counted beside live) and the result, passed or failed, recorded in the instance and read through `GET /api/v1/system/backup-rehearsals`; `GET /api/v1/system/summary`; Settings › Operations shows the instance, its workspaces and processes and the last rehearsal; rehearsed on the development database (six workspaces on three models, passed); screenshots approved by the user on 2026-10-22 ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#o2-record-2026-10-22)). **Q3, attribute sorts over very large parents, is delivered (2026-10-22):** D205–D209 accepted; a change set's list sorted by an attribute reads in value order, its base's kept records and its own each through its value index, merged by their first rows (the 20,000-child parent's first page 168 → 14.5 ms at full volume); a total under an attribute sort reads no values (live 94 → 11 ms); ties by record ID in every context; a boolean value index for change sets; a position deep under an attribute sort still grows with the children, over budget in a change set (124 ms at row 15,000), stored sort keys in TODO; ancestor sorts within budget, nothing built ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#q3-record-2026-10-22)). **U1, touch drag in the tree lens, is delivered (2026-10-22):** D210–D215 accepted; a record in a tree view or the sidebar lifts after a half-second hold and drags as with a mouse into the same confirmation; a swipe scrolls, a tap opens, a lifted record never scrolls the page except at the edge, and one let go where it was lifted opens the sidebar's menu (Move to…); checked at 390px on Chromium with Pixel 7 emulation and real touch input and on WebKit with iPhone 15 emulation (`test:browser:touch-u1`); the drag's top edge band at desktop widths now starts below the sticky top bar; screenshots and the user's real-phone try wait for the user ([record](BASE_0_11_IMPLEMENTATION_PLAN.md#u1-record-2026-10-22)). **L1 and L2 moved to 0.12 (2026-10-22, with the user):** the project's name is not chosen yet; 0.11.0 is released as an ordinary release and 0.12, the security release, becomes the first public release ([0.12 plan](BASE_0_12_IMPLEMENTATION_PLAN.md)). Next: 0.11's R. Accepted by the user 2026-10-15: the data move in 0.11 (D3), the suite's
time (D152) as a filler during Part 1 before X2 at the latest (D2), and 0.11.0-alpha.1 after the M6
checkpoint (D12).

### How 0.10 was built

**Base 0.9 is complete**, build acceptance R included ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#r-build-acceptance-and-release)).
R reviewed every change since 0.8.0 and ran every gate: the backend suite (2,201 cases), Vitest
(642), the 38 browser runners, the accessibility (109 checks) and visual (100 baselines) gates with
every 0.9 surface added, the upgrade of a database built by 0.9.0-alpha.1 (with an interrupted and a
resumed upgrade), schema 0.7 → 0.8 → 0.9 activations, the ROADMAP exit gate, and every budget at
full volume. It fixed 28 defects (R-F1–R-F28), each with its regression test: the review's 21, one
found by a browser runner, and six by the full-volume runs, among them a deletion of 100,000 records
that could not finish and now takes under a minute live and in a change set. What stays open is in
TODO: the backend suite's time over its 5-minute ceiling, three browser runner flakes, two `NOT IN`
subqueries to measure, and the recorded read exceptions. Schema 0.9 is released with it (D206). The
version strings and the tag (`v0.9.0`) follow the user's instruction (D207). Next is 0.10, planned on
2026-10-11 ([plan](BASE_0_10_IMPLEMENTATION_PLAN.md)): the model designer first, then spreadsheet
onboarding, starting with the A0 design pass. **A0 is delivered (2026-10-11):** its decisions
accepted, the API design, ADR-041, journeys J33–J35, and the editor mock-up and W1 sample approved
by the user. **N1, navigation groups and schema 0.10, is delivered (2026-10-11)**: schema 0.10
opened with an application's optional `navigation.groups`, validated at their pointers; the
sidebar's foldable group sections and the group page with its search; on a phone a one-line band
choosing workspace, application and data context, with no top-bar tabs (D28); supported schema
versions listed oldest first by number. **A2, the operation API on model drafts, is delivered
(2026-10-11)**: a draft changes by typed operations through the API (34 model-side kinds), each
request one step of a readable history with undo and redo; a change that would need a migration of
released structure is refused with its impact; the server generates the layout of new types; a JSON
edit is recorded as one step, and installation makes the installed release the draft's base. **A4a,
the editor's model pane, is delivered (2026-10-11)**, approved by the user after a revision of its
dialogs, menus and layout: a draft opens in the model editor from Settings › Model, with the model pane, the
selected element and its operations, the relationship matrix, issues and history with undo and redo,
Move to… and drags, the stale-version question and install and activate in one step; the server serves
the draft's outline. The user added **A4c, a consumer API editor** beside the model
editor, before T1 (2026-10-11). **A4b, the preview and layout editing, is delivered (2026-10-12)**, approved by the user: **Preview** in a type's header shows its record page and
table from the draft over records read live, its controls shown and disabled, in the editor's centre
under a band of its own; **Edit layout** opens the layout editor over the whole editor, where panels,
fields and table columns are moved by menu, keyboard or drag, grouped, hidden and sorted, one step
each; `GET /model-drafts/{id}/model` and the kinds `addDetailPage` and `removeDetailPage`. The user
moved the preview from a side pane into the centre while it was built; the side pane is kept in
SAVED_UI_PATTERNS. **A4c, the consumer API editor, is delivered (2026-10-12)**, approved by the user: the editor's left pane has Model and Consumer APIs tabs; a consumer API
opens with its exposed types and related records, fields, operations, lists, match rules, events and
filters, each change one of six operation kinds with undo, and with two documents an integration
takes from the draft, the Schema of its message and a Message example; a change its consumers would
notice shows as needing a higher contract version, raised in a step, and the install dialog checks
each one; `setKey` rewrites the definitions that name a new element. **T1, the designer checkpoint,
is delivered and the designer released as 0.10.0-alpha.1 (2026-10-12, tag `v0.10.0-alpha.1`)**: US-P05 walked end to end on both designer models, each walk
once by keyboard alone and once by clicking (`test:browser:authoring-t1`); the designer's surfaces in
the accessibility and visual gates, light and dark; the backend groups and the upgrade of a database
built by 0.9.0. It fixed two defects: marks read changed after an installation (A4a), and the
preview's History panel read the live API (A4b). **A3, source files, their profiles and the dry
run, is delivered (2026-10-12)** through the API: a workbook kept with a draft or a profile and
staged once in PostgreSQL; its sheets' blocks and header rows and each column's statistics; a dry
run of the whole file through an inline profile against the draft's model, writing nothing, with its
difference from the last one and the rows behind each figure (D65–D71; D67, changed by the user,
replaces D9's sample); `sourceFileId` on imports; the W1–W3 generators. Measuring the dry run found an
import binding defect (relationship links looked up per row), fixed the same day, and **A3a** (a
trial run records no audit entries, relation sets advance from arrays) brought the dry run of a
10,000-row workbook from 19.8 s to about 7 s. **A5 is planned in three slices (D74, accepted
2026-10-12); A5a, a draft's import profile edited by operations, is delivered (2026-10-12)**
through the API: eleven source and mapping kinds, the model kinds carrying the profile with them
(renames, moves, splits, merges, list types; removals leaving unmapped columns), the dry run queued
after each step that can change the load, the profile saved at installation, and `missing:
"create"` on lookups and parents (D75–D80). **A5b, the editor with a workbook, is committed
(2026-10-12)**, not accepted as complete: a workbook's draft has nothing proposed, and what it still
needs is settled in A6, which comes next, before A5c. Built: New from a workbook on Settings ›
Model; a source pane left of the model pane with the sheets and each column's status and
statistics; a selected column's mapping in the centre; Map to… by keyboard or by dragging a column
onto a type, value maps; the dry run as a drawer tab with each figure's rows; Load into a change
set (install, activate, load, review); `test:browser:authoring-a5` on both designer models. **A6,
inference, is planned in two slices (D86–D98, accepted 2026-10-12 after the user turned a first
design of Accept/Reject cards into proposals written into the editor as steps); A6a, inference
through the API, is delivered (2026-10-12)**: `POST /model-drafts/{id}/inference` proposes from the
draft's workbook in new-application or extend mode, each pattern with its evidence, operations and
alternatives; `…/inference/application` writes them as one step each; proposing again follows what
is still the engine's and reports where the administrator decided otherwise; W1 goes from upload to
a published change set by applying its proposals; `missing: "create"` on flag sets and related
records' parents. Its group runs went over the 2-minute ceiling (TODO). **A6b, the editor filled
by the inference, is delivered (2026-10-14, screenshots approved after its run on the user's
workbooks, D99–D103)**: New
from a workbook asks what to propose and the editor opens with the proposals applied, one step each;
what is still as proposed reads Proposed, with Proposed because, its evidence and its alternatives
in the centre; ⋯ › Propose again…; Map to… matches by an attribute and fills a related record's
value; `test:browser:authoring-a6` on both designer models. **A5c, the next version of a workbook,
is delivered (2026-10-14, screenshots approved by the user)** ([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a5c-record-2026-10-14)):
a file uploaded to a stored profile is checked by a `profileCheck` job, writing nothing (columns
new, missing and renamed, the profile against the active release, the dry run, new values, name
drift, records missing from the file; `GET /import-profiles/{key}/check` and its lists); a source's
`missing: delete` deletes them in a change set only, each with its own relationships (D104); a
lookup onto a single-valued relation replaces (D105); **Settings › Data operations › Import profiles** with a
profile's page to upload, check, accept a rename, ignore a column and load into a change set whose
review holds only the differences. Measuring the check at 10,000 rows found two defects, fixed: the
check locked itself out at the binding's first lease renewal, and the 0.9 binding's lookup by key
attribute compared every row with every record (21.9 s; now 2.4 s for the whole binding). The
check of W1′ at 10,000 rows takes 10.1 s after 6.1 s of profiling. Migration `20261015_01`.
**A7, model-description sheets and matching across files, is delivered (2026-10-14, screenshots
approved by the user)** ([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a7-record-2026-10-14)):
a sheet of field, type and target columns is read before the lists it names (the described type,
each list from its sheet by its ID, placeholder IDs skipped by a source's new `rowsWithoutKey:
"skip"`, lists to be defined added with nothing to load); a flat table then comes as additions to
the model, matched to the stored type by its fields, to the stored lists by name and to stored
codes by their ID, with missing values and name drift reported and each an alternative; the
editor's description sheet reads Describes the model. It fixed an A6 defect: the editor's
workbooks were compared with no records, so additions to the model never matched by value.
**A8 is planned in three slices (D114–D121, accepted 2026-10-14); A8a, lists of a sheet laid out
for reading through the API, is delivered (2026-10-14)**
([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a8a-record-2026-10-14)): a sheet holding no table but
lists side by side and under each other is read list by list, each with its header, the titles
above it and a note under its header; column statistics are kept per block (migration
`20261016_01`); each list is proposed as a list type loading its block by name (a source's new
`key: {"field": "name"}`), with its translations, yes/no columns and note, and the lists under one
title as a navigation group. On the user's reading-layout workbook it proposes 87 lists and 10
groups whose dry run refuses no row. It fixed an A5/A6 defect: a header ending in a space could not
be mapped. **A9, a list's cells edited in place, is delivered (2026-10-15)**
([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a9-record-2026-10-15)), added by the user and its
screenshots approved: in a collection or a record's table a value, a name or a relationship is
edited from its cell (the icons on the hovered cell, beside the value); a single relationship set,
changed or deleted, a many-valued one edited in a dialog of ticked records. **A8b, the source pane list by list, is delivered (2026-10-15), its screenshots approved**
([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a8b-record-2026-10-15)), D122–D130 and the
[mock-up](https://claude.ai/artifact/V31U2wkFwnfA4XR4oMrrPv) accepted by the user: a sheet laid out for reading shows its lists under their titles,
each Proposed, Loaded or Not loaded, a selected list its cells; Adjust list… (a header row moved
keeps each column on its letter), Don't load this list, Load as a list… (`POST
…/inference/list`); `GET …/sheets/{sheet}/cells`. It fixed an A6 defect: a list removed and loaded
again read as still proposed. **A8c, lists of one shape as one list under their headers, is
delivered (2026-10-15)** ([record](BASE_0_10_IMPLEMENTATION_PLAN.md#a8c-record-2026-10-15)),
D140–D146 accepted by the user: three lists or more of one shape under one title (or none) offer,
on each, to be read as one list in a parent list of their headers; an import source may fix every
row's parent (`parent`), and a source keyed by name finds records among their parent's children; a
row under a header answering none of its yes/no columns is a second header row, skipped. On the
user's reading-layout workbook a run of 11 lists loads as one list under 11
categories, refusing nothing, a second load changing nothing.

### How 0.9 was built

**Base 0.8 is released (2026-09-29)**: scalable browsing (Track S), workspace terminology and
capability boundaries (Track W), the relation matrix (Milestone A), the hierarchy editor (Milestone B),
the change set review (P2) and hierarchy restructuring (Milestone C). The starter model is content
release 0.8.0 on schema language 0.7. Next is 0.9, integration-grade APIs
([plan](BASE_0_9_IMPLEMENTATION_PLAN.md)): **Q1, the cross-type lookup `GET /objects`, is delivered
(2026-09-29)**, and so is the backend boundaries refactor E1–E3 ([record](BACKEND_BOUNDARIES_PLAN.md):
tiers, one rule set for live data and change sets, one write path; no contract change), and so is
**Q2, the workspace edge list** (`publicationId` on `/mappings`, the same list at
`/workspaces/{key}/relations`, 2026-09-29), and so is **Q3, the model-aware query**
(`POST /workspaces/{key}/queries/objects`: criteria, `ancestor:<type>`, one relation hop, `select`,
`expand`; D17–D19; 2026-09-30). The queue was reordered after Q3
([delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue)), and **C1, consumer API definitions**
(schema 0.8 opened with `consumerApis`, the breaking-change check at activation; C-D17–C-D20;
2026-09-30) is delivered, and so is **Q4, effective periods and `asOf`** (`effectivePeriod` in schema
0.8, the `invalid_effective_period` write rule, `asOf` on the per-type list and the model query, the
starter as content release 0.9.0 on schema 0.8; SC-11 passes through the management API; D20–D22;
2026-09-30), and so is **V1, the API reference page** (Scalar at `/docs` over the management API,
the script bundled so the page works offline, `RDM_API_REFERENCE_SCRIPT=cdn` to load it from a CDN;
2026-09-30), and so is **B1, the job model and inline object batches** (`POST /batches` with create,
update, upsert and delete items under `atomic` or `independent`, record references by unique key,
idempotency keys, `GET /jobs`; D23–D26, D13 confirmed; 2026-10-01), and so is **B2, background
jobs** (`run: background`, the in-process worker with chunks, lease, resumption, cancellation,
release and claim stops, and retention; D27–D30; 2026-10-01; delivered before F1, whose
workspace lock the chunks' write path will take). On SQLite a background job blocks other writes
until it ends. Next is the interim release **0.9.0-alpha.1, PostgreSQL runtime**
([plan](POSTGRESQL_RUNTIME_PLAN.md): PostgreSQL only, decisions PG-D1–PG-D10 accepted 2026-10-01),
with the test harness ([plan](TEST_HARNESS_PLAN.md): seeded databases built once and reused until
the schema, model or seed changes, inside PG1; parallel runs and budget sizes after PG2), then F1.
**PG1 is delivered (2026-10-01):** PostgreSQL only with the startup refusals, one baseline migration,
ICU root collation (PG-D11), `scripts/postgres.sh`, and the test harness's private server with seeds
built once (H1's core); `startup` and `contract` pass except four tests that need PG2. **PG2 is
delivered (2026-10-01):** current-live capture on a REPEATABLE READ snapshot, row locks instead of
SQLite's writer lock, `pg_trgm` search (revision `20261001_02`), the matrix forms with a linear state
build (0.1 volume in 7 s), names ordered as the database orders them, every foreign-key rule pinned,
no dialect branch in `app/`, and the browser runners on the development server with their seeds;
every backend group except `volume` passes on PostgreSQL. **H2 is delivered (2026-10-01):**
`pytest -n auto` runs the suite on one worker per core with a session database each; timing-based
`serial` tests (the `volume` group and two timer tests) run in a second invocation without `-n`. The
968 parallel tests take 1 min 49 s; the whole serial suite took 28 min 39 s, 21 min of it the two
full-size budgets ([record](TEST_HARNESS_PLAN.md#h2-parallel-runs)). The test plan was revised
the same day with [time ceilings](TEST_HARNESS_PLAN.md#time-ceilings), and PG-D12–PG-D17 accepted:
batch items decided in memory and written in bulk
([PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk)), with large
batch deletes noted to revisit (PG-D18). **H3 is delivered (2026-10-01):** the two full-size
budgets carry `budget` and leave every run whose `-m` does not name it, `serial` is narrowed to three
wall-time tests, the summary lists tests over 10 s and the wall time, and the ceilings are rules in
AGENTS.md; the full suite without `budget` takes 2 min 41 s (2.7×, short of the 4× target). Its run
found a deadlock between a relation create and a mapping save on one edge, recorded for PG3
([record](TEST_HARNESS_PLAN.md#h3-budgets-out-of-everyday-runs-the-time-ceilings-enforced)). **PG3
is delivered (2026-10-02):** every live write locks its workspace row (`FOR NO KEY UPDATE`) before
it reads, so live writes of one workspace serialize and workspaces write in parallel; the lock
order (workspace, change set, runtime state, records, job row) is in ARCHITECTURE, H3's deadlock is
gone, the cascade deletion's table locks are removed, and `test_pg3_concurrency` races every
checked invariant and the D28 job cases on two connections
([record](POSTGRESQL_RUNTIME_PLAN.md#pg3-concurrency)). Its seven groups took 2 min 7 s, over the
2-minute ceiling, so H4 is due. Its amendment the same day locks the workspace for change-set
writes too (key share), so a retirement waits for them; the activation deadlock found in PG3 and the
time of one chunk beside a live write moved into PG3b's scope. **PG3b is delivered (2026-10-02):**
create, update and upsert items are decided in memory through the single writes' decide steps over
a batch lookup (preloaded per chunk, each item seeing the items before it) and written together in
multi-row statements; a single write is a batch of one through the same code, delete items keep
their per-item path, and a bulk write failing on a row the rules could not see is redone item by
item. A chunk costs 30–49 statements for 100 or 500 items at both seeded sizes (a live upsert item
cost 20.5 before) and 0.25–0.46 s for 500 items; the release is checked before matrix states are
written, so PG3's activation deadlock is closed; an `atomic` job looks for a cancel request every
500 items and before writing (D28 amended). The package's review found that a single live update
would overwrite a write committed between its read and its lock; it now reads again under the
lock ([record](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk)). Its
four groups took 2 min 31 s, over the ceiling (H4). **Testing consolidation planned (2026-10-02):**
an audit of the 1,063-case backend suite found it written per work package after the code, from the
code, with no test tied to a user journey and every package over its ceiling. The user decided a
[testing strategy](testing/STRATEGY.md) (unit tests for each piece of code's purpose, journey tests
for every user journey of every client, the API as the product, specification-first test cases) and
[H4](TEST_HARNESS_PLAN.md#h4-testing-consolidation) moves the suite onto it in slices H4a–H4e.
**H4a is delivered and approved (2026-10-02):** the journey catalogue (26 generic journeys, 138 variants,
every client) and the API inventory mapping every route, parameter, error code and setting to journeys,
with seven decisions, all taken the same day ([record](TEST_HARNESS_PLAN.md#h4a-the-journey-catalogue)). **H4b is delivered
(2026-10-02):** journey markers checked against the catalogue, the journey and unit layout, the API
inventory check, selection by change (`pytest-testmon`, on the C tracer) with `tests.affected` for
what coverage cannot see, and the trace report; mutation testing was tried and dropped in favour of
planted faults per area in H4d ([record](TEST_HARNESS_PLAN.md#h4b-traceability-and-selection)).
**H4c is delivered (2026-10-03):** journey tests for every catalogue entry with an API or operator
side, with every deviation decided ([record](TEST_HARNESS_PLAN.md#h4c-journey-tests)). **H4d, the unit
layer and the move, runs in 14 area slices** ([plan](TEST_HARNESS_PLAN.md#h4d-the-unit-layer-and-the-move));
**H4d-1, jobs and batches, is delivered (2026-10-03):** four old modules (73 cases) replaced by unit
tests of the job engine (62 cases) and four checks merged into J11 and J12, with all 14 planted faults
caught. **H4 then stopped (user's decision, 2026-10-03):** H4d-2 onwards and H4e are postponed and
no dependency of any release up to 1.0, and test work per package is capped in proportion to the
feature (AGENTS.md, Testing). **PG4 is dropped (2026-10-03):** the SQLite data was moved by hand, so
no copy command is built. **PG5 is delivered and 0.9.0-alpha.1 released (2026-10-03):** every volume
budget re-measured on PostgreSQL (statements and rows hold; 143 of 154 full-volume reads within
100 ms), the 100,000-item batch measured once (52 s live, 64 s in a change set), the SQLite planner
constructs removed, name search through trigram indexes with candidates read first (revision
`20261003_01`), and the eleven remaining read exceptions deferred to the first fixes after 1.0, with a
complete handoff in [POSTGRESQL_BUDGETS.md](POSTGRESQL_BUDGETS.md)
([record](POSTGRESQL_RUNTIME_PLAN.md#pg5-budgets-acceptance-and-release)). **F1 is delivered
(2026-10-03):** the change feed `GET /workspaces/{key}/feed`.
- Every change to live data has a position, gapless and in commit order, taken under the workspace
  lock (revision `20261003_02`).
- A publish writes one entry per record and relationship it changed, then `published` (D15, D32).
- The read pages by position with bounded filters, and refuses a position past the head (D31–D34).

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#f1-feed-positions)). **B3 is delivered (2026-10-03):**
relationship items in batches.
- `createRelation`, `ensureRelation`, `updateRelation`, `deleteRelation` and `replaceRelationSet`
  (any number of targets) are decided in memory and written in bulk, 40–43 statements per chunk
  (D35).
- The single relationship writes and the mapping save are batches of one through the same steps.
- A replacement keeps a required relationship its record needs (D36).
- `GET /relations?objectId=…` names each set's version, an empty set included (D38).
- A duplicate relationship is `409 duplicate_relation` (live it answered 500).

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#b3-relation-and-relation-set-items)). **F2 is delivered
(2026-10-03):** feed retention and recovery.
- `FEED_RETENTION_DAYS` (30) sets how long the feed answers a position, reported by
  `GET /capabilities`; an older one is `410 feed_position_expired`, naming the active publication
  and its `feedPosition` to re-read (revision `20261003_03`).
- The earliest position never passes the active publication's, and a workspace without one keeps
  every entry (D40); the export as a second baseline is J1's (D41).
- A 500-entry page costs 4 statements, 25–35 ms, at the head and the middle of a 1,000,000-entry
  feed.

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#f2-feed-retention-and-recovery)). **T1 is delivered
(2026-10-03):** the checkpoint for Tracks Q, B and F.
- A composed journey (a background job followed through the feed, with dated queries and the edge
  list in live data, a change set and a publication) passes.
- Two defects in creating a change set from current live data and in publishing are fixed. Both
  answered `500` above about 65,000 records (a parameter list per record), and both flushed in
  quadratic time.
- Dated reads are measured at full volume, four of them over 100 ms (POSTGRESQL_BUDGETS E8).
- Applying a publish no longer flushes per record. Publishing 1,000 changes in 26,000 records now
  takes 11.3 s instead of 25.0 s.
- At T1, publishing and creating a change set copied the workspace through Python. Decided: the
  copies move into PostgreSQL as plain `INSERT … SELECT` (amendment T1a), sized for the volume
  fixture at 0.1 scale; larger workspaces are deferred until after 1.0.

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#t1-track-checkpoint-q-b-f)). **T1a is delivered
(2026-10-04):** current-live bases and publications copy records, relationships and typed values
inside PostgreSQL, with matrix states and history cells also copied by set statements. Revisions
`20261004_01` and `20261004_02` add the shared SQL value encoding, preserving the existing 28-digit
decimal rounding at every scale a decimal column holds (the review found 1e-16383 answering `500`).
At 0.1 scale, capture takes 3.3 s instead of 7.7 s and loads 7 ORM rows rather than the whole
workspace; publishing 1,000 changes takes 9.0 s instead of 11.2 s. The full-size completion probe
passes; publication merge and graph validation remain in Python
([evidence](BASE_0_9_IMPLEMENTATION_PLAN.md#t1a-copies-inside-the-database)). **T1b is delivered
(2026-10-04):** every error code on every API is upper case (`OBJECT_NOT_FOUND`), stored job
results included (revision `20261004_03`); a breaking change for clients comparing codes
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#t1b-one-error-code-pattern)). **C2 is delivered
(2026-10-04):** the consumer API tier at `/api/consumer` with get by ID, which answers a definition's
shared object (roles, attributes, parent, path, hierarchy and projections) read live by the object
ID, in the default or a named workspace (`RDM-Workspace`); a consumer API's identity is now always
the object ID (C-D21–C-D26, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c2-delivery-record)). **C3 is
delivered (2026-10-04):** consumer lists (every record of a type, or those below parent IDs, in the
list's `sortBy` order, with ADR-030 paging) and every parameter kind on lists and get by ID
(C-D27–C-D33). **C3a is delivered (2026-10-04):** lists sorted by an attribute read in value order through new
indexes (migration `20261004_04`), so consumer lists by `sortBy` page in 10–12 ms at full volume
(were 0.5–2.6 s) and the live E3 exception is closed (9.9 ms); a deep position jump (123 ms) and an
ancestor filter with its total (101 ms) remain at the budget line (D46–D48,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c3a-delivery-record)). **C3b is delivered (2026-10-04):**
consumer API parameters list several values as OpenAPI 3 serialises a list in a query, repeated or
comma-separated with `%2C` for a comma inside a value; C3's `\,` escape, which the user had not
approved, is withdrawn ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#c3b-delivery-record)). **C4 is
delivered (2026-10-05):** XREF lookup (`GET /api/consumer/{consumerApi}/v{n}/xref`): the definition's
`match` scores live records at read time, own and promoted weights, several terms, deterministic
order, paging with a total, `expect=one` with `404 NO_MATCH` and `409 AMBIGUOUS_MATCH`; contains from
3 characters, `400 QUERY_TOO_BROAD` past 10,000 matches. Exact matches read new `lower(…)` indexes
(migration `20261005_01`); lookups take 34–58 ms at full volume and the too-broad refusal 116 ms,
recorded (C-D34–C-D41, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c4-delivery-record)). **C5 is
delivered (2026-10-05):** the definition's parameters narrow XREF, acting on the scored objects, and a
`projection` parameter with `scoresFrom` limits which related records pass scores; `scoresFrom` is
validated and part of the contract (C-D42–C-D46,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c5-delivery-record)). **C14 is delivered (2026-10-05):** batch
resolve (`POST /api/consumer/{consumerApi}/v{n}/resolve`), up to 1,000 lookups or IDs, each outcome the
single read's answer; XREF became a batch of one, seeking a single best match with exact rules first;
a trigram index on names with workspace and type (`btree_gin`, migration `20261005_02`); 1,000
lookups in 816 ms at full volume (C-D47–C-D53,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c14-delivery-record)). **C14a and C14b (2026-10-05):** repeated
lookups resolved once, the ancestor walk read by ID and contains selects built without aliases; the
1,000-lookup batch now takes 236 ms. **C15 is delivered (2026-10-05):** crosswalk, `to.{parameter}`
on get by ID, lists, XREF and batch resolve with `target`, `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET` and
`MULTIPLE_TARGETS`; `targetable` is part of the contract (C-D54–C-D58,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c15-delivery-record)). **CN1 is delivered (2026-10-05):** the
consumer API's name is `consumerApi` in routes and planned contracts, not `apiKey`; no response
changes (U-D1, C-D59, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#cn1-delivery-record)). **C6a is delivered
(2026-10-05):** consumer reads pinned to a publication (`publication=<id>` or `latest`), the
publications list with `eventSequence`, `RDM-Publication`, ETag and `304`; publication read indexes
(`20261005_03`); C-D60–C-D68 ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#c6a-delivery-record)). **C6b is
delivered (2026-10-05):** the API index `GET /api/consumer` and each consumer API's own OpenAPI 3.1
document, paths written out with its name and version (C-D69, C-D70,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c6b-delivery-record)). **V2 is delivered (2026-10-05):**
`/docs` lists every consumer API of the active release beside the management API, labelled
`{name} · v{contractVersion}`; a link to a source (`?api=`) opens it
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#v2-delivery-record)). **C8 is delivered (2026-10-05):** parity
acceptance on a fixture shaped like the reference deployment, every answer checked against the API's
own document; a projection may name each item's type (`objectType`) and the parent's fields take the
roles' output names (C-D72–C-D75, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c8-delivery-record)).
**C16 is delivered (2026-10-05):** `asOf` on every consumer read, over the model's declared effective
periods; only the returned records are dated, `asOfApplied` and `RDM-As-Of-Applied` name the dated
types, `AS_OF_NOT_SUPPORTED` and `INVALID_AS_OF`; SC-11 passes through the consumer API too
(C-D76–C-D80, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c16-delivery-record)).
**C9 is delivered (2026-10-05):** a consumer API declares its change events (types, change kinds,
watched outputs), validated at their pointers and guarded by the contract check; no event is
produced yet (C-D81–C-D86, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c9-delivery-record)).
**C10 is delivered (2026-10-06):** a deriver thread turns each workspace's feed into the declared
consumer events after commit, without writes waiting, and `GET …/events` serves them in position
order with a lasting cursor, each with its object (or identity only), narrowed like a list,
expiring with the feed and naming the publication to re-read; a container rename's fan-out stays in
PostgreSQL (20,001 objects in 0.7 s at full volume). Webhook signing moved into 0.9 and events carry
the object (C-D7 and C-D12 revised); C-D87–C-D92, C-D95
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#c10-delivery-record)).
**U2 is delivered (2026-10-06)**, alongside C10: the UI's tokens are in three layers with a contrast
test, the fonts are bundled, and the shell is rebuilt to ADR-039. It has a top bar with the workspace
switcher and the applications, a toned rail, and a data-context band that turns amber in a change
set and violet in a publication. Every screen takes the new look through aliases until U6
(U-D7–U-D9, [record](SETTINGS_AND_UI_PLAN.md#u2-delivery-record)).
**C11 is delivered (2026-10-06):** webhook subscriptions are managed through
`/api/v1/consumer-subscriptions` when the deployment turns them on (`CONSUMER_SUBSCRIPTIONS_ENABLED`).
Each is checked against the active definition, a host allowlist and its workspace, and gets a
signing key that is shown once and stored sealed with a deployment key. An activation or a workspace
retirement that leaves one behind suspends it with a reason, and a resume after expired events needs
the loss acknowledged. Nothing is delivered until C12 (C-D96–C-D102,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c11-delivery-record)).

**C12 is delivered (2026-10-06):** a dispatcher in the API process delivers every active
subscription's events to its URL in position order: per change in signed requests of up to 100
events and 1 MiB, or coalesced as one notice per event once changes pause (C17 later made the batch
size a subscription setting and retired the coalesced mode). A failing receiver is
retried with the same batch for 24 hours, then the subscription is suspended; the subscription shows
its delivery state. A host no longer allowed, a filter value that matches nothing and events expired
before delivery also suspend it, and a resume can `reset` to the feed's head instead of resuming
from the first unacknowledged event (this replaces `acknowledgeLoss`). Several processes share
delivery through a lease. The background threads now log a database outage without a traceback
(C-D103–C-D111, C-D93 and C-D94 revised,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c12-delivery-record)).
**C13 is delivered (2026-10-06):** the events are accepted end to end, from a write through the
deriver and the dispatcher to a receiver, on two generated models: a publish arrives in batches as
the pull feed has it, work that never reaches live data sends nothing, filters scope deliveries as
the lists do, a reset and re-sync after expired events misses nothing, and a running application
delivers on its own. At full volume one subscription receives about 3,500 events a second, a batch
of 100 costs 61 ms and the dispatcher's idle claim 5 ms. A filtered subscription is not told when a
record leaves its filter's scope; this is now documented with the workarounds, and a fix is in TODO
for the user to place (C-D112–C-D114,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c13-delivery-record)). The events line (C9–C13) is complete.
**U3 is delivered (2026-10-06):** the Settings area at `/settings` with its own shell (About,
Appearance, Workspaces, Model, Deployment; old `/models` and `/workspaces` addresses redirect), the
account popover beside a Settings link in the top bar, a default table density, and
`GET /api/v1/system` with a settings catalogue in `config.py` (U-D10, U-D11,
[record](SETTINGS_AND_UI_PLAN.md#u3-delivery-record)). The same day, after using it, the user had
Workspaces and Model restored to their earlier screens beside the settings navigation, the pages
widened, a drawer for phones and the workspace switcher returned to the rail
([revisions](SETTINGS_AND_UI_PLAN.md#u3-revisions-after-delivery-2026-10-06)). Finding the UI
incoherent, the user then chose a new visual direction, **Atlas** (ADR-040): today's shell with a
colour for every kind of record. Then **UA**, the Atlas redesign of every surface
([plan](SETTINGS_AND_UI_PLAN.md#ua-the-atlas-redesign)), before U4 and U5. **UA0 is implemented
(2026-10-06)**, approved by the user 2026-10-07: popovers no longer swallow the first
click on the page, the workspace switcher lists every workspace when opened while loading, and
every page, Settings included, has one top bar and one frame, with copied markup replaced by
shared components (U-D14, [record](SETTINGS_AND_UI_PLAN.md#ua0-record-2026-10-06)). **UA1 is implemented (2026-10-06)**: the
eight-hue type palette and the context strips as tokens under the contrast test, a type's or an
application's hue from its position in the model (`model/hues`), and `ui/HueTile` in the top bar
and the rail's Collections; the user picked palette B (U-D13); approved 2026-10-07
([record](SETTINGS_AND_UI_PLAN.md#ua1-record-2026-10-06)). **UA2 is implemented (2026-10-06)**: the record
browser shows each record's type tile, a branch's guide line, quiet type headings and the selected
record in its type's colour; approved 2026-10-07
([record](SETTINGS_AND_UI_PLAN.md#ua2-record-2026-10-06)). **UA3 is implemented (2026-10-06)**: the
collection page's type tile, the green Live strip, record chips in a column that shows a record,
the selected row in its type's colour, plain-text booleans, and table-shaped loading and empty
states; no model or backend change; approved 2026-10-07
([record](SETTINGS_AND_UI_PLAN.md#ua3-record-2026-10-06)). **UA4 is implemented (2026-10-07)**: the
record's header band in its type's colour with ancestor chips, and the inspector's ruled sections,
side-by-side fields and **Connected** list; no model or backend change; approved 2026-10-07
([record](SETTINGS_AND_UI_PLAN.md#ua4-record-2026-10-07)). **UA5–UA7 are implemented (2026-10-07)**:
change sets and publications, the remaining surfaces, then dark mode and the gates: every screen
checked in dark, checkboxes and radios drawn from the tokens, column headers named by their label
alone, and `test:a11y` (73 checks) and `test:visual` (64 baselines, light and dark) passing; approved
2026-10-07 ([record](SETTINGS_AND_UI_PLAN.md#ua7-record-2026-10-07)). **U4 is implemented
(2026-10-07)**: Settings › Integration with **Consumer APIs** (each definition's version, base URL,
exposed types, lists and events), **Jobs and feed** (jobs of every workspace, cancel, the limits)
and **API reference** (each `/docs` source), over existing routes; the starter is content 0.9.2
with a small consumer API `rdm` and one event (U-D5); screenshots approved by the user 2026-10-10
([record](SETTINGS_AND_UI_PLAN.md#u4-record-2026-10-07)). **U5 is implemented (2026-10-07)**:
Settings › Integration › **Webhooks** over the subscriptions API (create with the signing key shown
once, delivery state, each suspension reason with its fix, edit, suspend, resume with or without
`reset`, delete), and a workspace refused deletion names its webhooks; no backend change;
screenshots approved 2026-10-07 ([record](SETTINGS_AND_UI_PLAN.md#u5-record-2026-10-07)). **U5a is
implemented (2026-10-07)**: webhooks have names, every delivery request and attempt is logged
(`/consumer-subscriptions/{id}/deliveries`, `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`, revision
`20261007_01`, C-D115–C-D119), and the Webhooks page has a rebuilt dialog and Configuration and
Deliveries tabs; revised the same day with resending an event by hand (C-D129–C-D131, revision
`20261007_02`) and an event's object linked to its record; screenshots approved 2026-10-07
([record](SETTINGS_AND_UI_PLAN.md#u5a-record-2026-10-07)). **C17 is implemented
(2026-10-07)**: a webhook chooses one event per request (the default) or batched up to 1,000, with
the object or the notification only, in RDM JSON or CloudEvents 1.0; the coalesced mode is retired
(revision `20261007_03`, C-D120–C-D128); screenshots approved 2026-10-07
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#c17-record-2026-10-07)). **J1 is delivered
(2026-10-07):** export jobs.
- `POST /api/v1/exports` exports live data, a change set or a publication: types each with their
  own criteria, a subtree, `asOf`, relationships, as JSON Lines, CSV or XLSX, from one snapshot, on
  an export worker of its own; `GET /jobs/{id}/output` serves the file once the job is completed,
  and the job's `output` states what it holds (D49–D56, revision `20261007_04`, `JOB_FILE_DIR`).
- JSON Lines is batch items with each record's version, so the file sent back changes nothing; CSV
  and XLSX share one table layout; a live export is a feed baseline (`410` names it).
- The whole volume workspace exports in 23 s (JSON Lines), 24 s (CSV) and 32 s (XLSX).

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j1-record-2026-10-07)). **J1u is delivered
(2026-10-07)**: Export on a collection page and New export on Jobs and feed, a page per job, and
notifications that a job started and ended (with Download and View job), pushed over
`GET /jobs/{id}/events` from a trigger at commit, never polled (D57–D63, revision `20261007_05`);
screenshots approved ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j1u-record-2026-10-07)).
**J2 is delivered (2026-10-07)**: import profiles (`/import-profiles`, checked against the model with
every problem at its pointer) and `POST /imports`, a file sent with its request and run as a job:
XLSX or CSV through a profile, JSON Lines items or an export's tables without one; keys, matches,
hierarchy order and related records resolved in PostgreSQL, rejected rows named by sheet, row and
column (D64–D74, revision `20261007_06`; [record](BASE_0_9_IMPLEMENTATION_PLAN.md#j2-record-2026-10-07)).
**J2a is delivered (2026-10-07)**: the database holds live unique attribute values
(`unique_attribute_values`, kept by PostgreSQL triggers under a deferred constraint, D75–D78,
revision `20261007_07`; [record](BASE_0_9_IMPLEMENTATION_PLAN.md#j2a-record-2026-10-07)).
**J3 is delivered (2026-10-07)**: an import sent with `stage: preview` is bound, run against the
data and rolled back, and waits for `POST /jobs/{id}/confirm` with what execution would do (counts,
the result under the policy, `complete` or `sample`), a binding report per column, outcomes by row
(`GET /jobs/{id}/rows`) and every failing cell of a row; confirming binds the file again and
executes it (D80–D88, revision `20261007_08`, `IMPORT_PREVIEW_MAX_ITEMS`). A 10,000-row preview
takes 10.6 s and a 100,000-row execution 110.7 s
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j3-record-2026-10-07)). **J4 is delivered (2026-10-08)**:
the import screen, SC-10 in the browser. Import on a writable collection and New import on Jobs and
feed preview a file through a profile or none; the import's page shows the preview, the refused rows
by row and column and the binding report, loads on confirmation and says how to load refused rows
(D89–D95; frontend only, `test:browser:j4`)
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j4-record-2026-10-08)). **J4a is delivered (2026-10-08)**,
reported by the user: an export of one workspace previewed into another refused every row with no
reason; the job now says its rows' IDs are another workspace's (`notices`), and each refusal names
that workspace ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j4a-why-another-workspaces-export-cannot-load)).
**J5 is delivered (2026-10-08)**: another workspace's export loads as this workspace's own records,
with counterpart IDs derived from the file's IDs and the workspace (`otherWorkspaceIds` on imports
and batches; the import dialog loads them by default; D96–D101)
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j5-record-2026-10-08)). Then Track K and R.
**K1 is delivered (2026-10-08)**: selecting records in a collection by hand, by range and as "all
matching" (also Cmd+A), with exceptions, the selection bar, and a selection over the bulk limit
explained; no writes, frontend only; D102–D111 decided; screenshots approved by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k1-record-2026-10-08)). **K2 is delivered (2026-10-09)**:
changing values of a selection from the collection (Change values…: set or clear fields, previewed,
applied, refused records named and openable), on a batch preview the engine now offers to any
background batch (`stage: preview`, then confirm), the limit renamed `JOB_PREVIEW_MAX_ITEMS`;
deletion moved to K2b; D112–D119; screenshots approved by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k2-record-2026-10-09)). **K2b is delivered (2026-10-09)**:
deleting a selection from the collection (Delete…: previewed with what goes with each record,
applied exactly as previewed, a record changed meanwhile refused), on cascading batch delete items
(J11.6) and one set-based deletion path for the single delete and a batch, live and in a change set
(PG-D18 closed); D120–D126; the deletion timing on the full-size fixture (D124) deferred by the user
to R; screenshots approved by the user
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k2b-record-2026-10-09)). **K3 is delivered (2026-10-09)**:
changing the relationships of a selection from the collection (Change relationships…: every
relationship the model allows the type, the actions its cardinality allows, the other records from
the record picker, previewed and applied), on an `ensureNoRelation` batch item (removal by the two
records, J11.10) and set replacements claiming what their preview showed (J11.11); D127–D135;
screenshots approved by the user 2026-10-09
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k3-record-2026-10-09)). **K3a is delivered (2026-10-09)**:
many-to-one relationships, a fourth cardinality in schema 0.9 (a `from` record holds one, a `to`
record serves many), enforced on every write path and at activation, read through one rule by the
matrix, the mapping grid and the consumer API (a single object), never `required` (D137, in TODO);
on a record, Set while none is held and Change (one write) and Delete on the one held; D136–D139;
screenshots approved by the user 2026-10-09; the example model 0.9.1 active on the development
instance
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k3a-record-2026-10-09)). **UA8 is implemented
(2026-10-09)**: the record header's title and subtitle edited in place through the details panel's
own field component, Edit record only in the ⋯ menu, and a relationship row's actions as icons;
U-D15–U-D20; screenshots approved by the user 2026-10-10
([record](SETTINGS_AND_UI_PLAN.md#ua8-record-2026-10-09)). **UA9 is implemented (2026-10-09)**: the
record tree scrolled as one list and folded at the start (the user's experiment, kept), several
records selected and moved together by drag or Move to…, in the sidebar too; U-D21–U-D28;
screenshots approved by the user 2026-10-10 ([record](SETTINGS_AND_UI_PLAN.md#ua9-record-2026-10-09)).
**K5 is delivered (2026-10-09)**: relation columns, `related:<key>` in a table view's or a children
or table panel's columns in schema 0.9, each row's first three related records as chips with "+N
more", sorted by the related name where a row holds at most one; `expand` and `expandLimit` on the
per-type list (Q3's `expanded` shape, `INVALID_EXPAND`) and `sort=related:<key>`; Q3's expansions
read in one `LATERAL` statement per expansion; the starter 0.9.4; D140–D147 (D143 and D145 amended
by the user); screenshots approved by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k5-record-2026-10-09)). **K5a is delivered (2026-10-10)**,
added by the user: a relation column may show a field of the related records or of a record above
them (`related:<key>.<field>`, the consumer API's field form), and `expand` reads it; D148–D152
accepted by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k5a-record-2026-10-10)). **K5b is delivered (2026-10-10)**,
D143 revised by the user: a relation cell shows as many related records as its column's width holds
and "+N more" for the rest, none when all fit; screenshots approved by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k5b-record-2026-10-10)). **K6 is delivered (2026-10-10)**: filtering a
list by its records' relationships (any of chosen records, none, any) from the Filter menu and
`filter.related:<key>…` on the per-type list, carried into selection, bulk actions and Export; the
starter 0.9.5; two defects found and fixed (lower-case filter and sort codes; exports with a related
criterion failing in the worker); D153–D159; screenshots approved by the user 2026-10-10
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k6-record-2026-10-10)). **K6a is delivered (2026-10-10)**:
collection filters as pills with a field menu and one editor per field, a bottom sheet on phones;
the selection bar and both bulk dialogs redesigned; `GET /relations/held` so Remove lists only what a
selection holds; D160–D167, with D142 revised (no fixed number of relation columns); one defect
found and fixed (the checklist's layout inside a dialog's form)
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k6a-record-2026-10-10)). **K7 is delivered (2026-10-10)**:
a binding's `candidates` limit which records a relationship may choose, applied by every picker,
listed and enforced by the API, relationships made before kept; Q3's ancestor field criterion;
D168–D178 ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#k7-record-2026-10-10)). Screenshots of both
approved by the user 2026-10-10. **J6 is delivered (2026-10-10)**: a workbook for people exported from a
collection (the table's columns, relation columns as lists, a sheet per chosen relationship, the
type hues) and read back without a profile through the one it carries, rows claiming their versions;
`layout: "people"` on `POST /exports`; import profiles gain version, name and relationship-row
bindings; D179–D190 ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j6-record-2026-10-10)). Screenshots
approved by the user 2026-10-10. **J6a is delivered (2026-10-10)**: owned records as columns per parent
(a new language filled in one column), dropdowns from reference sheets of the records a relationship
may choose, borders; D191–D199 ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j6a-record-2026-10-10)).
Screenshots approved by the user 2026-10-10. Then R. Track V's V3–V9 and the palette rework moved to
a new release, [0.14](BASE_0_14_IMPLEMENTATION_PLAN.md), before 1.0 for now (2026-10-10).
**C18, the consumer API definition written for readers, is delivered (2026-10-08):** schema 0.9
writes `consumerApis` as what a definition exposes, offers, looks like and filters by, with defaults
written out by `GET /api/v1/model/consumer-apis/{consumerApi}`; an operation not offered is
`404 OPERATION_NOT_OFFERED`; a new 0.8 document with `consumerApis` is refused, stored 0.8 releases
read as before; the starter is 0.9.3 and the example model 0.9.0 on schema 0.9, active on the
development instance, and every converted definition compiles to the same internal form as before
(C-D132–C-D141; [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c18-record-2026-10-08)).

Base 0.5 is the completed operational/model-release foundation. Base 0.6 is released (2026-09-11).
**Base 0.7 is released (2026-09-25)**: core mapping, schema 0.6 and draft version selection. The starter
model is content release 0.7.0 on schema language 0.6. WP-1 (accessibility gates), WP-2 (schema 0.6
`mappingGrid` view contract), WP-3 (relation-set version persistence), WP-4 (mapping query APIs),
WP-5 (atomic mapping replacement), WP-6 (backend draft version selection) and WP-7 (browser draft
version selection) are delivered.
WP-8A/WP-8B and WP-14 are delivered (committed in `f8e39a8`, 2026-09-15): mapping is a lens of a
contextual collection inside one model-driven application browser rather than a separate primary
destination. The Base 0.7 frontend redesign (`936a70e`) and dark mode with the settings menu
(`315e6f7`) followed on 2026-09-24, then WP-12 and WP-13A/B/C. All triggered WP-10 slices (A–G) are
delivered; WP-10E/F/G closed on 2026-09-25. **WP-9 composed build acceptance passed on 2026-09-25**:
SC-07 and SC-15 run as composed browser + API journeys (`test:browser:sc07`, `test:browser:sc15`,
`test_build07_wp9_acceptance.py`), the full backend/frontend suites, all browser runners and the
accessibility and visual gates are green, and WP-10H/I/J found on the way are closed. The draft
timestamp decision it surfaced is delivered as WP-10K (not recorded in drafts and history).

**0.8 delivery record.** [Track S](BASE_0_8_IMPLEMENTATION_PLAN.md#work-packages--track-s) (S1–S8,
scalable browsing, ADR-030) and [Track W](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries)
(W1–W6, ADR-031 terminology and capability boundaries) were delivered on 2026-09-26. Next are the
relation matrix (Milestone A, a generic rows × ancestor-columns view; A1 schema 0.7 `relationMatrix`
contract delivered 2026-09-27; A2 relation matrix query, A3 writes from a cell and A3b stored cell
states for the row state filter (ADR-033) delivered 2026-09-27; the A4 lens and A5 acceptance
delivered 2026-09-28; A6, the snapshot table index drift found in A2, delivered 2026-09-28)
and hierarchy editor (Milestone B; B1 schema 0.7 `tree` contract delivered 2026-09-28; B2 move targets with
D14 eligibility delivered 2026-09-28, the matrix container move a known budget exception, D29; B3 tree
lens and B4 acceptance delivered 2026-09-28; B5 drag and drop in the tree lens, added in the Milestone B
review, delivered 2026-09-29; its amendment B5b (move to the top level) delivered 2026-09-29, which
closes Milestone B; D34–D36 accepted),
and P2 (P2a change lists API and P2b review screen delivered 2026-09-28; D31–D33 accepted), then R1 build
acceptance (passed 2026-09-28, without B5; [record](BASE_0_8_IMPLEMENTATION_PLAN.md#r1-build-acceptance-and-release))
and its amendment R1b for B5 and B5b. Milestone C (structure refactoring: type changes derived from
the model, with preview and history as the way back; C0–C5 and R2) was added 2026-09-28; C0 is
delivered 2026-09-29 with [ADR-034](DECISIONS.md#adr-034--a-records-type-can-change-derived-mapping-preview-and-apply-history-as-the-way-back)
and D37–D43 accepted; C1, a record's type change in the engine with the D42 refusal, is delivered
2026-09-29; C2, the restructuring planner (possible types, the cascade, the D40 mapping, offers back,
refusals, the plan digest), is delivered 2026-09-29; its dry run took 48 s at C0's 5,000-record limit, so D44 lowers
the D41 limit to 500 records (a 2.8 s preview); C3, the restructuring API (preview and apply for `move`,
`changeType`, `insertLevel`, `removeLevel` and `changeTypeUnder`, parent candidates' `includeTypeChanges`),
is delivered 2026-09-29; C4, restructuring in the tree lens (Move to… and drag to places that change
the type, Change type…, Insert level above…, Remove this level…, Change type of all … in here…, the
preview by record and by type pair, the review's type change and the browser following D42), is
delivered 2026-09-29. C5, the milestone acceptance (`test:browser:c5` on the starter and generated
models, SC-17, US-H03; the preview and dialogs in both gates), is delivered 2026-09-29, which completes
Milestone C; on the way it made change set validation linear (D46; 125 s → 1.4 s at 2% volume) and
fixed a reclassified-then-removed record in the review and the lens's late refocus. **R1b and R2
passed together on 2026-09-29** ([record](BASE_0_8_IMPLEMENTATION_PLAN.md#r2-milestone-c-build-acceptance)):
the full backend suite (829), Vitest (381), all 22 browser runners and both gates are green with no
fix or re-baseline, and no migration was needed. D43 is resolved, and **0.8.0 is released (2026-09-29).**
Residual 0.7 gaps are listed in the
[plan's WP-9 record](BASE_0_7_IMPLEMENTATION_PLAN.md#wp-9-composed-product-validation--sc-07-and-sc-15).

The generic model defines applications, object types, reusable fields, allowed relationships and views.
Master, Systems and Translations are configurable starter examples; runtime code must remain unaware
of their keys. The selected immutable model governs current behavior; the configured source JSON is
bootstrap input, not a parallel activation mechanism.

## Accepted product direction and actual availability

ADR-026 restored direct live reference-data maintenance. ADR-027 consolidates the user's accepted
GAP-01–GAP-08 answers and distinguishes accepted targets from implementation evidence.

| Area | 0.6 state | Next |
| --- | --- | --- |
| Live data | Complete: generic object, field, parent, relation and translation APIs and browser controls; record concurrency and audit | — |
| Optional change sets | Complete: current-live and historical source selection, shared browser editing, validation and delta merge | — |
| Historical data | Complete: newest-first browser discovery, pinned-model immutable reads and historical draft derivation | — |
| Publication withdrawal | Complete: truthful browser confirmation removes only the designation while retaining live data/history | — |
| Workspace administration | Complete (0.8 W3–W6): Workspaces screen to create, rename, retire, reactivate, delete an unused workspace and choose the default, gated by `WORKSPACE_ADMIN_MUTATIONS_ENABLED`; the change-set workflow is always available | — |
| Model administration | Complete: immutable releases, JSON drafts, validation/diff/install/activation workbench | Browser administration acceptance (0.7+) |
| UI foundation | Complete: catalogue selection, typed tables, generic panels, redesigned navigation/collections/inspector/inline editing, automated accessibility and visual-regression gates (UI-07); 0.7 redesign (header application tabs, Live/Drafts/History control, record tree, Filter popover), dark mode and settings menu; WP-9 a11y/visual acceptance passed | — |
| Specialist workflows | Schema 0.6 `mappingGrid` contract, live/draft/revision coverage, target-detail, candidate APIs, atomic replacement and contextual mapping lens with in-context target creation delivered; SC-07 composed acceptance passed | Lazy arbitrary-depth hierarchy/translation specializations 0.8; integration 0.9 |
| Production and model migration | Basic readiness and actionable startup refusal | Production hardening, staged assignments and reviewed historical model migration 0.11; authentication and authorization 0.12 |

Ordinary live saves create neither a change set nor a publication. Publishing a change set applies authored changes
over current live data, preserves unrelated live work and publishes nothing on a touched-record conflict
or divergent touched mutable relation set, or invalid merged graph. Historical derivation is not a direct restore. Publication withdrawal does
not withdraw live data or make the workspace read-only; catalogue retirement is the read-only control.
Change sets and application-definition drafts are different concepts.

The current default/non-default browser gap and disconnected record controls are documented in the
[functionality catalogue](product-functionality/CURRENT_FUNCTIONALITY.md). A component or API present
in code does not establish that a browser user can complete its story.

## Product 0.7 delivery sequence (released 2026-09-25)

1. **Typed `mappingGrid` (WP-2, delivered 2026-09-12):** schema 0.6 with a strict `mappingGrid` view
   contract, discriminated union dispatch, full validation rules and an initial frontend placeholder.
   WP-4 delivered 2026-09-14: cursor-paged batched mapping coverage, exact counts with bounded
   version-bound target details, view-specific typed projections and candidate search in live/draft
   contexts. WP-5 delivered 2026-09-14: atomic mapping replacement with retained identity, typed
   attributes and direction-aware validation. WP-8A/WP-8B and WP-14 now implement the composed UI.
2. **ADR-022 relation-set versions (WP-3, delivered 2026-09-12):** exact-binding relation-set versions
   integrated into all generic relation writes in live and optional-draft contexts. Atomic mapping
   replacement is delivered in WP-5.
3. **ADR-028 draft version selection:** WP-6 backend delivered 2026-09-14: installed-release
   creation, whole-candidate compatibility, atomic audited pin changes and pinned model/metadata
   reads. WP-7 browser version selection and model-context refresh delivered 2026-09-14:
   model-release selector in draft creation, release display on draft cards and detail, informational
   banner and activation refusal when versions differ, version-change action with incompatibility
   diagnostics, model-context refresh after pin change, and dirty-input protection via navigation
   guards. WP-11 delivered 2026-09-15: unsupported-schema diff/compile/activation refusals return structured 422,
   correlation-ID error boundary, API client HTML/non-JSON hardening, compact Modal version-change dialog,
   supported-schema pinned-model loading, shell-aligned workspace error recovery and historical-release
   informational state. Non-retryable pinned-schema limitations do not offer Retry. Focused wide/narrow
   browser evidence is recorded. WP-12 delivered 2026-09-24: explained, copyable Release ID and
   content hash under Technical details; release history compares the recorded predecessor (or a
   labelled installation-order fallback, or an explicit baseline) to the selected release, including
   the active one, while activation readiness stays current-active to candidate.
4. **UI-07 (carried from 0.6, delivered 2026-09-12):** automated accessibility and visual-regression
   gates using the existing Playwright harness with `@axe-core/playwright` and visual comparison
   baselines. Light-theme baselines committed; dark mode and dark baselines followed on 2026-09-24.
5. **Contextual collections (WP-8A/WP-8B/WP-14, delivered 2026-09-15 in `f8e39a8`):** one generic application browser combines collection entry points and runtime
   hierarchy. Views sharing a source type are collection lenses; mapping adds visible server-backed
   coverage state and atomic actions without adding another primary navigation destination. Direct-parent
   scope is URL-backed and valid in live, draft and immutable-revision contexts. ADR-029 records the
   durable terminology and the 0.7/0.8 boundary.

Moving a draft onto a version its content does not already fit, and the accepted historical-model
warning and confirm-or-cancel behavior, belong to the planned 0.11 workspace assignment/migration flow.

See [implementation plan](BASE_0_7_IMPLEMENTATION_PLAN.md), [delivery queue](TODO.md),
[roadmap](ROADMAP.md) and [product acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md).

### 0.7 plan review boundary — 2026-09-12

This is the historical plan-review boundary. WP-1–WP-3 scopes are frozen and delivered.
WP-1/WP-2 fixes were subsequently committed in `3de2f88`; WP-3 participation and mapping
query review evidence follows below. The plan review established later-package requirements, not foundation
defects or new runtime pass evidence. WP-4/WP-5 add view-specific bounded reads, retained relation
identities and direction-aware mapping validation. WP-6/WP-7 add atomic complete-candidate compatibility
and browser model-context refresh; both are delivered. WP-8A delivers coverage; WP-8B adds mapping actions. WP-9 extends
new-control accessibility/visual evidence and checks independent bindings, differing same-schema
releases, generic-write races and activation/live set conflicts. Confirmed missing foundation behavior
triggers bounded WP-10 work before acceptance. Dark mode and dark baselines were added on 2026-09-24.

### WP-4 delivery and review — 2026-09-14

WP-4 mapping queries and the WP-10A cascade-deletion version fix are committed in `0c459ef`.
Pending WP-3 relation-write participation, draft cleanup/activation and migration test expectations
were committed separately in `022abec`. Both commits together contain the code covered by the final
401-test backend run on SQLite; Ruff passed. WP-4 integration checks cover paging, bounded ambiguous
sets, view-specific projections, draft pins, concurrent reads and stale continuation rejection after
live/draft cascades in both directions. The review found no further confirmed issues.

This was backend query evidence at the WP-4 boundary. Atomic replacement (WP-5) was subsequently
delivered and reviewed; WP-8A/WP-8B and WP-14 browser work is delivered, while composed product 0.7
acceptance (WP-9) remains pending.

### WP-5 acceptance and WP-10B activation hardening — 2026-09-14

WP-5 acceptance now includes an independent allowed binding in live/draft contexts, ownership and
clearing refusals, and overlapping real HTTP generic create/update/delete versus replacement.
WP-10B reproduced activation accepting a new live edge in a mapping set the draft cleared. Activation
now compares complete source/live relation identities and versions in touched mutable, non-ownership
binding sets and refuses divergence before applying rows. Diagnostics identify binding, anchor and
direction, preserve the draft/live graph/revision, and explain safe reapplication under current live
context. Current-live and revision-derived drafts, both directions and unrelated live mapping work
are exercised. API and ADR-022 contracts and the WP-8B consumer handoff are reconciled.

The final follow-up also closes ancestor-scope validation gaps in mapping/generic draft writes,
rejects non-oriented ownership replacement, and rejects empty supplied view identities. Twelve
HTTP regressions exercise these refusals and valid final-graph replacement.

The final implementation gate passed 486 backend tests (including 73 replacement/activation cases),
Ruff, frontend format/lint (zero errors, 12 existing warnings), 164 frontend tests and build. These
are API/integration and component results on SQLite; recorded in the active implementation plan.
WP-8A/WP-8B browser delivery was subsequently composed through WP-14. WP-9 US-M01–M04 acceptance
remains separate; PostgreSQL concurrency is not established.

### WP-8/WP-14 contextual-browser delivery and review — 2026-09-15

The then-uncommitted WP-8 renderer was reviewed as part of WP-14; both were committed in `f8e39a8`.
Mapping coverage and actions now render as a lens of the same source collection as its table views. The application rail presents collection
groups and runtime hierarchy in one model-driven browser. Direct-parent scope, typed field facets and
mapping coverage state are visible and URL-backed; the server applies parent/state filters before
cursor pagination. Live, draft and immutable-revision reads resolve their governing model and data
projection. No renderer branches on the starter application or object-type keys.

The review removed duplicate configured identity fields and corrected mapping-conflict handling so a
steward must inspect the returned current targets before explicitly continuing with a retry. The final
package gate passed 39 backend mapping/OpenAPI tests, 95 frontend component/adapter/routing tests,
Ruff, frontend format, lint (zero errors, 12 configured warnings) and production build. A six-check
real-backend/browser journey covers direct-parent composition, table/mapping lens changes, both
configured directions, live replacement, narrow layout and an axe check. Comprehensive suites and
reviewed visual baselines remain WP-9 build acceptance.

### Frontend redesign and dark mode — 2026-09-24

The Base 0.7 UX pass (`936a70e`) reworked the generic shell and renderers without changing routes,
data contexts, API contracts or the model: applications as header tabs, a segmented Live / Drafts /
History control, a collapsed-by-default record tree, one Filter popover, lens tabs with a scope banner,
a record header with a visible Edit action and a rewritten token stylesheet. Mapping lenses gained a
segmented coverage filter, row-click to map, a candidate radio list, **Save and next** and an explicit
**Remove mapping**. `315e6f7` added a dark token set with a System / Light / Dark choice, the settings
menu and dark accessibility scenarios and baselines, and aligned the Models page. Presentation rules
are in [UI model](UI_MODEL.md); reviewed light and dark baselines are committed.

### WP-10E/F/G — 2026-09-25

- **WP-10E:** timestamp columns use one UTC column type, so SQLite keeps the instant and every
  response carries an explicit offset (server timestamps as well as `dateTime` fields). Decimals read
  back in one form without trailing zeros in every context. The browser's zone-less workaround is
  removed. No local database holds a live `dateTime` value, and offsets lost earlier cannot be
  recovered, so no data migration was added.
- **WP-10F:** a target created from a mapping lens goes to the application the user chooses; every
  application containing the target type is listed, the lens's application is the default, and parent
  choices are limited to that application's types.
- **WP-10G:** the narrow candidate search keeps its height; draft-mismatch and historical-revision
  notices name releases by key and version.

Evidence: the full backend suite (533 passed; run once because the column type affects every
timestamp read), 167 affected frontend component tests, Ruff, frontend format, lint (zero errors, 11
warnings) and build. `test:browser:wp13c` (12 checks) creates, selects and saves a target in both
directions, live and in a draft, and checks the narrow search height and mismatch text.
`test:browser:authoring`, `test:browser:publications` and `test:browser:wp14` pass. The changed
screenshots were inspected at 1440px and 390px. The full frontend suite and the a11y/visual gates
remain WP-9.

## Evidence boundary

The subsequent [WP8 implementation review](../review-notes/wp8-implementation-review-2026-09-08.md)
reviewed the uncommitted diff and corrected confirmed lifecycle/CRUD defects. Its backend, frontend,
migration and installed-wheel evidence is recorded separately; subsequent packages now close WP8.1-A
through WP9, while composed release acceptance remains in WP10.
The follow-up closes SC-04's service boundary: cascade confirmation requires the signed identity from
the exact displayed preview and rejects intervening hierarchy changes without deleting data. Live
deletion also claims active workspace status for the transaction and refuses stored graph edges that
cross workspace boundaries. The frontend adapter carries live or draft confirmation context. The WP9
browser control must show the returned retry message when it becomes reachable.

Prior WP0–WP8 and ADR-026 reports record backend/component/build validation at their own snapshots.
This technical-documentation update ran document/contract/traceability checks only; it did not execute
runtime, browser or migration suites. Prior green totals cannot close the newly identified gaps.
Release acceptance needs the actual evidence specified by WP10, with relevant skips reported as gaps.

## Product correction retained from the ADR-026 retrospective

Earlier lifecycle decisions routed every reference-data edit through a draft and release ceremony,
contradicting continuous maintenance in the product statement. The correction restores live editing
and keeps coordinated data changes optional. Every future gate must ask whether a data owner can
still perform daily work without unnecessary steps. Model definitions, live data and history each
need explicit authority; an appended amendment does not repair contradictory canonical instructions.
Record capability removals and contract reversals for explicit product review before implementing them.

## Source evidence incorporated

The supplied RDM application package declares 3 applications, 23 object types, 27 attribute types, 72
relation types and 55 allowed object-type relations. The accompanying API examples show:

- object-type metadata with features and attribute bindings;
- a custom-overview query that asks for numeric attribute and relation IDs;
- a relation-type catalogue declaring 201 entries, with 20 complete entries in the captured excerpt;
- forward/reverse relation names, orientation and typed relation features; and
- separate runtime retrieval for the Master and Translation applications.

The engine keeps the useful object–attribute–relation separation and configurable applications. It
intentionally replaces numeric integration IDs, unbounded `take: 0` queries and UI-coupled endpoint
configuration with stable keys, explicit schemas, cursor pagination and resource APIs.

## Implemented

- `model/rdm-starter.json`: schema-language 0.7/content-release 0.8.0 model (Base 0.8 S4R2; relations panels declare sort options) with 22 attributes, 9 object
  types, 13 relation types, 16 allowed triples, three applications, table and mapping grid collection
  views and typed detail compositions. Domain
  and Codelist objects can have optional System Value representations without joining the independent
  system containment hierarchy.
- Translation objects support translated name, description and value content, are contained by a
  Translation Group, and have exactly one required target chosen from every explicitly configured
  translatable Master object type. Active Target and Language combinations are unique.
- `backend/app/models/schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/engine/model/compiler.py`, `model/diff.py` and `model/compatibility.py`:
  side-effect-free canonical compilation, stable JSON-path diagnostics, key-based structural diff and
  bounded runtime-data compatibility checks exposed through validation and release-diff APIs.
  Compatibility covers object and relation attribute constraints and relation-type-wide cardinality;
  diffs distinguish JSON null from omission and ignore ordering for set-like stable-key memberships.
- `backend/app/engine/model/drafts.py`, `model/releases.py` and the model-management router:
  persisted draft CRUD with optimistic concurrency, side-effect-free draft compilation and atomic,
  idempotent immutable installation serialized across drafts in the supported single-process
  topology. Complete model JSON is excluded from lifecycle audit payloads, and all write routes are
  absent unless model administration mutations are enabled.
- Guarded release activation with runtime-data compatibility diagnostics, dual-token optimistic
  concurrency, old/new release audit identities and hashes, post-commit registry refresh, unhealthy
  readiness on publication failure and startup rejection of configured multi-worker mutation mode.
- `backend/app/models/database.py` and `backend/app/db.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations, exact-binding relation-set versions and audit events.
- `backend/app/engine/records/attributes.py`: attribute validation, defaults and typed persistence conversion.
- The Base 0.5/pre-WP6 `backend/app/routers` and `backend/app/services` implementation established
  generic object CRUD, search/cursors, concurrency checks, hierarchy maintenance and relation instance
  CRUD (create/read-one/update/delete) with optimistic concurrency, cardinality checks and
  model-declared typed relation attributes. WP6 removed these public mutation routes before their
  workspace-backed replacements existed; corrective WP7 restored their behavior selectively from Git
  history. Engine-maintained parent-containment relations remain read-only through the relation API. The
  established object-scoped attribute-value endpoints
  (`GET`/`POST`/`PATCH`/`DELETE` on `/objects/{type}/{id}/attributes/{attributeTypeKey}`) set, read,
  update and delete single stored values with the same validation, uniqueness and object-version
  concurrency as object writes. Standalone reads expose the current object version, and mutations
  atomically claim that version before writing; `backend/app/main.py` contains application assembly
  only.
- Git history retains workspace-scoped attribute uniqueness and transactional object deletion with
  dependency preview/cascade behavior. WP7 restored those generic semantics in the selected workspace
  draft without restoring rejected WP4 lifecycle. ADR-026 also restores these semantics for live writes.
- `backend/app/migrations`: versioned Alembic database migrations are the single source of schema truth;
  the initial migration provisions new databases and upgrades existing ones, and startup runs only
  `alembic upgrade head`. The environment-aware `app.cli.database_upgrade` command and startup
  boundary turn failures into actionable, credential-safe operator messages without tracebacks. The
  WP4 migration recovers only recognized empty SQLite DDL from an interrupted attempt and refuses
  unsafe cleanup. Startup regression coverage now exercises clean boot, restart, preceding-revision
  upgrade, interrupted-DDL recovery and maintenance-mode refusal against real temporary databases.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  workspace-explicit routes, view and panel component registries, URL-backed searchable/filterable/
  sortable cursor-paged collections, composable object details and cursor-paged audit history.
  Complete workspace lifecycle UI with live CRUD, optional drafts, newest-first immutable history,
  historical draft sources, truthful publication withdrawal and conflict reconciliation. Frontend
  redesign (UI-01–UI-06) delivers compact navigation, focused collections, record inspector, inline
  field editing, resizable panels and refined draft presentation. Failed collection and lookup reads
  remain retryable; genuinely empty relationship/translation collections render as empty states;
  engine-maintained containment edges remain read-only.
- The global model workbench provides release inspection and structured model summaries in read-only
  deployments, and capability-gated JSON draft, validation, diff, installation and activation flows in
  the supported model-administration topology.
- Tests cover model validation and a Domain → Codelist containment flow including the generated typed
  relation, search/cursor behavior, update concurrency and deletion behavior. Composition tests mutate
  panel order, visibility, fields and relation-table configuration without renderer changes. Frontend
  unit tests (Vitest + Testing Library) exercise the model helpers and generic renderers with two
  object types. Frontend adapter and helper tests also cover typed field conversion, structured API
  errors, cross-application lookup queries and incoming/outgoing relationship derivation.

## Important design decisions

- Global attribute definitions and object-type bindings are separate.
- Relation definitions and permitted object-type triples are separate.
- Containment stores both an indexed parent ID and a semantic typed relation, updated atomically.
- Attribute values use typed columns rather than a single string or opaque JSON value.
- Model releases are immutable; a changed definition requires a new release key/version.
- Vendor exports and their numeric IDs are source research, not distributable runtime dependencies.

See `docs/DECISIONS.md` for the durable decisions and `AGENTS.md` for coding invariants.

## Remaining limitations

- Automated accessibility gates (`npm run test:a11y`) and visual-regression gates
  (`npm run test:visual`) are delivered. No violation is allowlisted: WP1-001 was fixed on
  2026-09-24 and WP1-002 by Base 0.8 S5 (its exception was removed in S7). Light baselines cover the core
  page types and dark baselines a representative subset; the accessibility gate runs core pages
  and the settings menu in both themes.
- Schema 0.6 supports strict table and `mappingGrid` collection lenses. Exact-binding relation-set
  versions are integrated into all generic relation writes; coverage, target details, candidate
  search and atomic replacement are delivered with the contextual mapping lens (WP-8/WP-14). Base 0.7
  limits contextual hierarchy queries to direct-parent scope. Lazy arbitrary-depth traversal and
  specialist translation/tree renderers follow the 0.8 roadmap; top-level `form`, `dashboard` and
  `tree` are not implemented renderers.
- Imports/exports and webhooks remain planned (0.9); the
  model-aware query, `asOf`, inline and background object batches with upsert, and the change feed
  read are delivered.
  No synchronous collection has an undocumented unlimited mode.
- The model workbench remains JSON-centred; the structured editor and spreadsheet onboarding are 0.10
  work ([MODEL_AUTHORING.md](MODEL_AUTHORING.md)), changes to released structure and extensions 1.0.
- Multi-writer uniqueness hardening, PostgreSQL performance, authenticated access, actor attribution,
  observability, backup/restore rehearsal and multi-node model propagation remain production work.
- The version serving live data is chosen globally today. Per-workspace migration/assignment, moving
  a draft onto a version its content does not fit, and confirmed potential-loss historical model
  changes require 0.11 and supported parser/runtime versions. A draft can work under a compatible
  version the user chooses (ADR-028; WP-6 backend, WP-7 browser). A draft on a replaced version can be read, edited and discarded,
  but activation still requires agreement with the active model.
- The starter remains representative rather than a one-to-one reproduction of the source export.

## Historical delivery record

Base 0.5 delivered runtime model selection, model compilation/diff/compatibility, versioned drafts,
immutable install, guarded activation, bounded query/audit improvements and the JSON workbench.
Base 0.6 WP1–WP3 delivered UI primitives, workspace catalogue and typed tables. WP4's individual-object
publication design was rejected before release and removed through the corrective WP6 migration;
WP5 refroze workspace scope, WP7 restored generic CRUD and WP8 implemented lifecycle services.
ADR-026 then restored direct live data and delta merge. WP8.1-A–C subsequently closed the remaining
backend authority, draft-source and history/retirement corrections; WP9 completed the isolated
browser journeys; WP10 validated the composed product. The frontend redesign (UI-01–UI-06) delivered
compact navigation, focused collections, record inspector, inline field editing, resizable panels
and refined draft presentation. UI-07 was carried into early 0.7.
UI-07 (automated accessibility and visual-regression gates) was delivered in early 0.7 (2026-09-12).
WP-2 (schema 0.6 `mappingGrid` view contract) was delivered 2026-09-12: discriminated union dispatch,
full validation rules, starter model 0.7.0 with two mapping grid views, and the initial frontend
placeholder later replaced by WP-8/WP-14. WP-3 (relation-set version persistence) was delivered 2026-09-12: `relation_set_versions`
table with lazy row creation, integrated into all six generic relation mutation paths (live and draft),
draft deletion cascade and activation merge. The earlier plans and changelog preserve delivery details;
do not rebuild rejected object lifecycle.

## Coding-agent handoff

Read `AGENTS.md`, the product stories/scenarios, ADR-027, `ROADMAP.md`, `API.md` and `TODO.md`.
Base 0.7 is released (2026-09-25): WP-1–WP-9, WP-10A–K, WP-11, WP-12, WP-13A/B/C and WP-14, plus the
2026-09-24 frontend redesign and dark mode. WP-13A's [coverage map](testing/COVERAGE_MAP.md), WP-13B's
[execution guide](testing/EXECUTION_GUIDE.md) and WP-13C's [UI acceptance](testing/UI_ACCEPTANCE.md)
supply the audited selections. **0.8 in progress**: Tracks S and W are delivered; next are the
Relation matrix and Hierarchy editor milestones, P2 and R1
([plan](BASE_0_8_IMPLEMENTATION_PLAN.md), [roadmap](ROADMAP.md)).
Use one implementation owner per slice, focused verification and appropriate review. Do not commit
unless explicitly requested. Summarize each completed batch while work continues so scope can be
corrected before the entire task finishes.

Use the focused work-package checks in `AGENTS.md`; expand for actual shared-boundary risk.
Run startup/migration and other named boundary checks only where relevant; comprehensive suites
and browser gates belong to WP-9. WP-13 supplies audited selections and UI acceptance guidance.
Report evidence and limits; no documentation change counts as a runtime fix.
