# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (0.12 C1)

- **The API reference's "try it" console is signed in.** `/docs` asks the engine, with the session's
  cookie, for the token of the person signed in at the browser (`POST /oauth/console-token`, answered
  `{access_token, expires_in}`, `401 not_signed_in` without a session, `403` from another site) and
  gives it to the console for the management API and the consumer APIs, so a request is answered or
  refused as the application would answer it. The cookie is read without renewing it, so the
  application's own tabs keep their session; the console renews its token in the token's last minute.
  A client's token pasted over it is sent as it is. The page itself stays open and holds no token.

### Added (0.12 K1)

- **A webhook's signing key can be rotated.** `POST /api/v1/consumer-subscriptions/{id}/rotate-secret`
  `{expectedVersion, overlapHours}` (24 by default, 0 to 168) answers a new key once, as the create
  does. For the overlap every delivery is signed with both keys, `RDM-Signature:
  sha256=<new>,sha256=<previous>`, and a receiver accepts it when either verifies; afterwards only the
  new key signs, and with 0 the old key stops with the next delivery, a retry of a waiting batch
  included. A subscription names `previousSigningKeyExpiresAt` while an overlap runs. **Receivers must
  accept a comma-separated list.** Settings › Integration › Webhooks has **Rotate key…**, with the
  overlap choices of a client's secret (one shared dialog now), and shows the new key once.
- **`python -m app.cli.reseal_secrets`** re-seals every sealed secret (token signing keys, webhook keys,
  a provider's client secret, authenticator secrets and the provider ID tokens kept with a session)
  under a new `SECRETS_ENCRYPTION_KEY`, all or none; `--check` proves every one opens. Migration
  `20261108_01`.

### Changed (grant dialog)

- **Grants are made in bulk, from a grid.** The grant dialog (a client's, person's or group's page,
  and a workspace's Access) now takes several things at once. Consumer APIs are ticked in a grid of
  APIs by workspaces (a row or column heading ticks the line, Shift extends a range; a workspace
  whose model does not declare an API has no tick for it); roles are ticked as cards, in several
  workspaces or the whole instance. What the holder already has is shown ticked and locked and is
  not sent again; a sentence says how many grants will be made. Each tick is one `POST
  /api/v1/grants`, so a refusal leaves the others made and its tick in place with the reason.
  Narrowing is offered when one role is granted in one workspace. A client's page opens on
  Consumer APIs.

### Fixed (development)

- **The API reference can call the engine in development.** `scripts/dev.sh engine` allows the
  engine's own addresses (`localhost:8000`, `127.0.0.1:8000`; with `--network` also its https address)
  in `CORS_ORIGINS`, so Scalar's `Try it` and token request are not refused as `400 Disallowed CORS
  origin`. A `CORS_ORIGINS` already in the environment is kept.

### Fixed (0.12 D412)

- **The API reference shows the consumer APIs.** A consumer API's `openapi.json` needs no token, like
  the management API's, so `/docs` and the link on Settings › API reference load it instead of
  answering `401`. The consumer index and the data routes still need a token.

### Changed (branding)

- **The application is named refiroo.** The interface shows the refiroo mark in the top bar, the
  loading and empty screens, Home and Settings › About, with the title and favicon in the browser;
  the sign-in pages and the API reference at `/docs` (and the OpenAPI title) carry the same name and
  mark, served from `/operator/<file>`. The logos are in `logos/`, renamed by what they are; the
  interface and the engine keep resized copies. Naming rules and files: `docs/OPERATORING.md`.

### Fixed (0.12 I4 review)

- **Removing a passkey asks for the password again** (or a code from the app or a recovery code):
  `DELETE /me/passkeys/{id}` takes `proof`, so a stolen session cannot strip a person's passkeys.
- **Recovery codes are stored keyed** (HMAC-SHA-256 under `SECRETS_ENCRYPTION_KEY`), not as plain
  SHA-256 of 60-bit codes. Recovery codes made before this stop working: make new ones.
- **A second factor and passkeys need a password:** `409 PASSWORD_REQUIRED` for a person who signs
  in with a provider (a passkey would have been a way in past the provider).
- **Linking** locks both people in one order (no deadlock between opposite links) and refuses a
  deactivated person as the target (`409 LINK_TARGET_DEACTIVATED`).
- **Open passkey sign-ins are capped** (2000 waiting at once, then `429` with `Retry-After`), so the
  open options endpoint cannot fill the database.

### Added (0.12 DP1a, a developer instance on the network)

- `scripts/dev.sh` runs a developer instance in two terminals: `settings` (the database and a secrets
  key in a git-ignored `.dev/settings.env`), `admin` (the first administrator), `engine`, `frontend`;
  with `--network` both over https on this computer's network address, after `cert` finds the
  address and makes an mkcert certificate, so a phone or another computer on the network signs in.
- README's setup uses it, and OPERATIONS § A developer instance explains each step and the settings.

### Changed (0.12 SP1b, a group's members)

- **Add members** on a group's page adds several people at once: searched and ticked (people already
  in the group or deactivated shown but not tickable), or pasted as a list of usernames and e-mail
  addresses that is checked first, each line saying whom it names or that nobody has it; the people
  to add gather as chips and are added together (D401).
- Members are ticked and **removed together**; the last Security administrator is still kept (D402).
- `POST /groups/{id}/members/batch` (with `dryRun`) and `POST /groups/{id}/members/removal`.

### Changed (0.12 RA1, a person's recent activity)

- **Recent activity** on a person's or client's page reads like a record's history: a heading for
  each day, one line each, filtered by kind (**Signing in**, **Roles and groups**, **Account**), the
  10 newest first, **Load more** adds 20, **Show fewer** returns to 10. The kinds use the API's
  existing `aggregateType` filter.

### Changed (0.12 RH1, a record's history)

- A record's **History** lists its changes under a heading for each day, one line each (what, who,
  when); a line opens to show each value with the one before (D389, D16 revised for history only),
  or says the one before was not recorded after a publish or a type change (D390).
- Filters by kind (values, relationships, moves) and by who made the changes; the 10 newest first,
  **Load older history** adds 20, **Show fewer** returns to 10 (D391, D393). A relationship's line
  names the record at its other end (D392).
- `GET /objects/{type}/{id}/history` takes `kind` and `actorId` and answers `kind`, `values` and
  `related` on each entry. The change feed and consumer events still name changes only.

### Added (0.12 I4c, passkeys)

- **Passkeys** (D389–D394): Settings › Account › **Passkeys** adds one on the engine's own page,
  where the browser asks for a fingerprint, face, device PIN or security key; it signs the person in
  alone from the sign-in page's **Sign in with a passkey**, or after a password as the second step,
  and meets the requirement for a second factor. Rename and remove them; an administrator removes
  one from a person's page. A passkey belongs to the host of `PUBLIC_URL`: changing it invalidates
  them.
- The sign-in page runs one script of the engine's own, `/oauth/passkey.js`, only where a passkey is
  offered, and none elsewhere (`script-src 'self'`; D275 revised, D390).
- `GET|PATCH|DELETE /me/passkeys`, `GET|DELETE /users/{id}/passkeys`, `passkeys` on a person and on
  `/me/second-factor`. Migration `20261107_01`; one new dependency, `webauthn`.

### Fixed (0.12 I4c)

- A sign-in provider's key cannot be `password` or `passkey`, nor `local`: a session's
  `signedInWith` is one of those or a provider's key.

### Added (0.12 I4b, a second factor for local accounts)

- **An authenticator app** (D383–D388, D225 revised): Settings › Account › **Second factor** sets one
  up with a QR code the engine draws, the key and a code, and shows ten recovery codes, once. After
  the password the sign-in page asks for the app's code, or a recovery code; each works once, and a
  wrong one is slowed like a wrong password. **New recovery codes…** and **Remove…** ask for a code.
- **Require a second factor with a password** (Settings › Security › Sign-in › Local accounts): a
  person without an app sets one up on the sign-in page, and sees the recovery codes, before their
  session starts; nobody removes their own factor meanwhile. Provider sign-ins are never asked.
- A Security administrator removes a person's second factor from their page (a security event).
- `GET|POST /me/second-factor`, `POST /me/second-factor/confirmation`, `POST
  /me/second-factor/recovery-codes`, `DELETE /me/second-factor`, `DELETE /users/{id}/second-factor`,
  `secondFactor` on a person, `secondFactorRequired` on local sign-in. Migration `20261106_01`; one new
  dependency, `segno` (the QR code).

### Fixed (0.12 I4b)

- The browser runner's provider helper passed its secret as a separate argument, which failed when the
  random secret began with `-`.

### Added (0.12 I4a, a provider identity linked, signing out of the provider)

- **Link to an existing person…** on the person a provider sign-in made (D377, D378): their
  identity and provider groups move onto the person who already had the account, with their roles
  and history; the new person is deactivated. Refused for a person with a password, roles of their
  own or local groups. **Unlink…** undoes it. `POST /users/{id}/identities`,
  `DELETE /users/{id}/identities/{provider}`.
- **Sign people out of *name* too** (D379, D380): a provider's setting, off by default, with the
  second address to register (`signedOutUri`). The app signs out by opening `GET /oauth/sign-out`;
  the browser goes through the provider's sign-out with the ID token the session kept, sealed, and
  back to the sign-in page. Migration `20261105_01`.
- **Keeps local sign-in** is a switch on a person's page (D381); while local sign-in is off, the last
  person who keeps it can neither lose it nor be deactivated (`409 LAST_LOCAL_ADMINISTRATOR`).

### Added (0.12 I3, a sign-in provider)

- **Sign in with the organisation's provider** (D361–D370): an OpenID Connect provider (Entra ID,
  Google, Keycloak and others) added on **Settings › Security › Sign-in** with its issuer, client ID,
  secret and groups claim, checked when saved, with the address to register shown to copy; the
  sign-in page offers **Continue with *name***. A person signing in through it the first time is
  created from the provider's name and e-mail and found by the provider's subject afterwards, never
  by e-mail; sessions record the provider.
- **Provider groups**: the provider's groups become groups listed under it, their members set at
  each sign-in ("Members seen"), renamed and granted like any group, and made ahead of anyone's
  sign-in with **New group › From a sign-in provider**.
- **Local sign-in can be turned off** once a provider has signed someone in; the administrators
  made on the server with `create_admin` keep a password as the way back, through a link on the
  sign-in page. A person's page says how they sign in; Account names the provider.
- API: `GET|POST /sign-in-providers`, `GET|PATCH|DELETE /sign-in-providers/{key}`,
  `GET|PATCH /sign-in-providers/local`; a group's `source` and `POST /groups` with one; a member's
  `seenAt`; a person's `identities` and `localKept`; `signInProvider` on `/me`; the security events'
  `sign-in-provider` aggregate. Migration `20261104_01_sign_in_providers`; people made before 0.12 Z4
  keep local sign-in.

### Fixed (0.12 I3)

- A group's page kept its old name after Rename until it was opened again.
- Two fields side by side in a dialog no longer push one input down when only the other has help
  text.

### Changed (0.12 HM1a, Home)

- A workspace card's tile (its initials) opens the workspace, as its name does.
- **Continue where you left off** stands on a shade of its own, in light and dark.

### Changed (0.12 LS1, a collection's rows scroll on their own)

- A collection's table page fits the window (D371): only its rows scroll; the top bar, the band,
  the header and the toolbar stay, and the table's footer and the rail end on the window's bottom
  line, also with few records and on a phone.
- The wheel over a list that fills its page is the browser's alone (D372); a list nested in a page
  that scrolls (a record's panels, dialogs) keeps carrying the wheel on at its ends, finding the
  scroller around it once per gesture.
- A record list's rows keep to one line once its columns are laid out (D375); a cut value is shown
  whole on hover, focus or a long press.

### Fixed (0.12 LS1)

- Scrolling a collection lagged even with a few hundred records. Rows passing under the pointer
  measured their cells and drew the whole table again, twice, for every cut-off value; every page
  arriving in the background and every draw of the page drew every row again; the wheel waited
  for a script that read the layout at each step; and every scroll frame laid the table out again.
  Now a row on the page is drawn once (D373), and the layout is read only when the list or its size
  changes (D374).

### Added (0.12 SP2, clients and their access)

- **Settings › Security › Clients** (D348–D357): the systems that call the API, each with its
  consumer APIs and roles and when it last obtained a token; a new client's ID and secret shown
  once; a client's page with who created it, Rename, Deactivate and Restore, **Rotate secret**
  keeping the current secret working for 1 hour, 24 hours or 7 days, or stopping it at once,
  secrets told apart by their last four characters and the previous one ended early, its access,
  the webhooks it created, its recent activity and its changes.
- The grant dialog grants **a consumer API** as well as a role, from a client, a person, a group or
  a workspace's Access; its button reads **Grant**.
- **Settings › Security › Signing keys**: the token signing keys and their state; start a new key,
  or retire the current one at once after a leak.
- A webhook's page names who created it.
- `roles`, `consumerApis` and `createdBy` on every read of a client, `hint` (the last four
  characters) on each of its secrets (migration `20261103_01`), and
  `GET /api/v1/workspaces/{workspaceKey}/grant-options`.

### Fixed (0.12 SP2)

- A person holding only Security administrator could not narrow a grant: the grant dialog read the
  workspace's model, which needs Browse; it now reads `grant-options`.
- A segmented choice in the grant dialog was drawn taller than its options (the dialog's label rule
  reached its labels).

### Added (0.12 TV1, a record's parent in its list)

- A table view's **Columns…** and **Filters…** in the model editor's layout editor offer the
  record's relationships, the ones to its parent first (D358–D360): a list of records under a parent
  can show which parent each belongs to and be filtered by it. The engine has listed and filtered
  by relationships since 0.9; only the model file could choose them until now.

### Added (0.12 Z6, one person's changes across workspaces)

- **Changes** (D340–D347): everything a person or client changed, across the workspaces the reader
  may browse, newest first and grouped by day: records and relationships, live or in a change set,
  change sets, publications and model drafts and releases, each naming its workspace, change set and
  what it changed with its type from that workspace's own model, narrowed by workspace, kind and
  period; each title opens what it changed while it exists. A name in a record's history opens it,
  as does "See changes" on a person's page; Home shows **Your recent changes**, the five latest.
- `GET /api/v1/changes` (`actorId`, `workspaceKey`, `kind`, `since`, `until`, paged), filtered to
  what the caller may see; a Security administrator without data roles reads an empty list.
- Every audit entry that belongs to a workspace now names it, also a change set's work, and a change
  set's records and relationships name what they changed; the upgrade places existing entries from
  their change sets (migration `20261102_01`).

### Added (0.12 HM1, a home page after sign-in)

- **Home** (D331–D339): signing in, the bare address and the product name open a home page: a
  greeting with the person's roles and what is open; Continue where you left off, back to the last
  list, record or review opened in this browser; the workspaces they may browse as cards, the
  default first, each with its model, their role, its applications and buttons counting their open
  change sets and, for a publisher, every open change set; their open change sets across workspaces,
  each opening its review. A workspace's name opens the workspace. An address naming a workspace,
  application or record opens it as before.
- `GET /api/v1/me/workspaces` and `GET /api/v1/me/change-sets` (D332, D333); `product` on
  `GET /api/v1/system` (D338).

### Fixed (0.12 HM1)

- A person with no workspace saw the model release's name in the top bar; it is the instance's
  product name, as everyone else sees.
- A browser runner's seed built on an older schema seed was reused after the schema seed was rebuilt,
  so its backend refused the harness client (`401 invalid_client`); such a seed is rebuilt now.

### Added (0.12 Z5, the interface follows permissions)

- **The interface offers only what a person may do** (D321–D330): a Reader sees no way to change
  anything and the data-context band says they can read; a Contributor proposes a change from a
  record into a change set of their own (named the first time, continued afterwards, counted in the
  band) and is not offered Publish; a narrowed writer edits only the permitted record types, named in
  the band; imports, bulk changes, moves, publishing, withdrawals, migrations and Settings' pages
  appear only to whoever holds their groups, and a flow appears only when every step can finish.
- **The first workspace** is the default one the person may read, otherwise the first they may
  read; with none, a page says so with their roles and leads to Settings (People for a Security
  administrator). The workspace selector lists only workspaces the person may read.
- `GET /api/v1/me/action-groups`, `holding=` on `GET /api/v1/workspaces` and `createdBy=` on a
  workspace's change sets (D325, D327, D328).

### Fixed (0.12 Z5)

- The `change-sets` and `test:browser` (navigation) browser runners start again: they ran their own
  servers without the secrets key and token every engine needs since I1, and now use the shared
  harness. `test:browser:wp12` accepts the activation's sentence naming who made it (0.12 Z4).

### Added (0.12 Z4, audit identity)

- **Every change names who made it** (D313): `actor` beside `cause` on a record's history, a feed
  entry and a release's activation: the person or client by their current name, `{"kind":
  "engine"}` for the engine's own changes, `null` for changes from before 0.12 ("Before sign-in").
  A job's changes name its requester, a publish's the publisher. Consumer events name no one (D314).
- `createdBy` on a change set, `publishedBy` and `withdrawnBy` on a publication, `requestedBy` on a
  job (D315).
- **Security events** (D317, D318): `GET /api/v1/security-events` (`principalId=`,
  `aggregateType=`) lists changes to people, groups, roles, grants, clients and signing keys, and
  sign-ins, succeeded or failed, with who made them and never a secret.
- In the interface: "by *name*" in a record's history and the model editor's history, "Created by"
  on a change set, "Published by" and "Withdrawn by" on a publication, "Requested by" on a job and
  in the Jobs list, and a person's **Recent activity** in Settings › Security › People (D319, D320).

### Changed (0.12 Z4)

- `author` on a model draft's and a model mapping's operations is now `{kind, id, name}` (or
  `null`) instead of a string, which was never filled.
- A subscription's `owner` uses the shared `PrincipalResponse` schema (same fields).

### Added (0.12 Z3, consumer APIs per client)

- **Consumer API grants** (D306): `POST /api/v1/grants` with `consumerApi` instead of `role` lets a
  client, person or group read that consumer API in one workspace; a grant reads `role: null` and
  `consumerApi` (`stale: true` once the model drops the API); `GET /api/v1/grants` takes
  `consumerApi=`. A workspace's Access and the Account page show it as "Consumer API: *name*".
- Each consumer API's OpenAPI document declares the OAuth 2.0 client credentials scheme with the
  token URL and scope `consumer`, and `401` and `403` on every operation (D311).
- A subscription reads `owner`, the person or client that created it, and the list takes `ownerId=`
  (D310).

### Changed (0.12 Z3)

- **The consumer data routes need a grant of the API in the workspace read** (D307): `403 FORBIDDEN`
  with `details: {consumerApi, workspaceKey}`, checked after the workspace and before the definition,
  so an unknown API key now answers `403` to a caller without a grant (D309). No role opens them.
  After upgrading, consumer clients read nothing until granted.
- The consumer index lists only the APIs granted to a `consumer` token; with a `management` token
  the index and the OpenAPI documents need Browse in the workspace (D308).

### Added (0.12 SP1, the Security pages)

- Settings › Security › **People**, **Groups** and **Roles**, shown to people holding Security
  administration (D303): people listed with the roles they hold, searched, active or deactivated; a
  person's page to edit them, make a one-time password link shown once (D304), sign them out
  everywhere, deactivate or restore them, and see their roles, directly or through a group, and
  their groups; groups with their roles and members; the matrix of roles by action group, a custom
  role made empty or copied and edited in place (D305 at phone width).
- A workspace's **Access** on its page in Settings › Workspaces: every grant that applies there,
  made in it or for the whole instance (D301). One grant dialog for Access, a person and a group,
  with the narrowing to applications and record types and a sentence of what the grant allows.
- `GET /api/v1/users` and `GET /api/v1/users/{id}` answer the person's `roles` and where (D298);
  `GET /api/v1/users/{id}/grants` lists a person's grants including their groups' (D299); `q` and
  `memberId` on `GET /api/v1/groups`, `q` on `GET /api/v1/clients` (D300).

### Changed (0.12 SP1)

- `POST /api/v1/grants` refuses a workspace grant of a role whose action groups are all held only
  at the instance, such as Security administrator, with `422 GRANT_SCOPE_INVALID` (D302): such a
  grant was stored and allowed nothing.
- Webhooks' "keep the signing key" dialog is the shared "shown once" dialog the password link uses.

### Fixed (0.12 SP1, after delivery)

- New person said only "Request validation failed" for a username with a space: it now says a
  username has no spaces as it is typed, and the engine's refusal of a field is shown under that
  field (New person, Edit) or by the field's name (groups, roles).

### Added (0.12 Z2, record types at the write unit, jobs as their requester)

- A grant narrowed to applications and record types now limits every write its holder makes in the
  workspace (D289–D291): a record may be written when its application or its type is named, grants
  holding the group there add up, and a relationship may be written when either end may. Live
  writes, change sets, restructurings (both the old and the new type), batches, imports, publishing
  a change set and moves into a workspace are checked at the write unit; a refusal is `403
  FORBIDDEN` with `details.recordTypes`. A batch, an import or a move refuses only the items of
  other types; a single write and a publication are refused whole (D293).
- Jobs run with their requester's permissions (D236, D294): checked at confirmation and before
  every worker step; a requester deactivated or without the job's group fails it with `403
  FORBIDDEN` and `details.requestedBy`. The requester reads, follows, cancels and confirms their own
  job and sees it in `GET /api/v1/jobs`.
- An import profile's source files are read, changed and listed for their uploader and for holders
  of Bulk and import in their workspace, `403` for anyone else (D295).
- A grant naming what the workspace's model no longer has reads `stale: true` with
  `scope.missingApplications` and `scope.missingRecordTypes`, and `/me/permissions` marks the group
  `stale`; such names allow nothing (D296). Migration `20261030_01` (`jobs.requested_by_*`,
  `source_files.uploaded_by_*`).

### Changed (0.12 Z2)

- Publish and Copy and move are narrowable action groups (D290).
- `POST /api/v1/moves` with `mode: move` also needs Work in change sets in the source, which it
  writes a change set of; `mode: copy` needs Browse there as before (D297).
- A write the engine cannot attribute to a request or a job is refused with `500 WRITER_UNKNOWN`
  (D292).

### Fixed (0.12 Z2, found in Z1)

- An import naming a stored source file, sent as a URL-encoded form without a file part, failed
  with an internal error: the route check read its body as JSON after the form was read.

### Added (0.12 Z1, roles, groups and grants at the route)

- Authorization (ADR-044): every management operation declares its action, published in the
  OpenAPI document (`x-action`, `x-action-groups`, `x-action-scope`), and a request its caller's
  roles do not allow answers `403 FORBIDDEN` naming the action, the action groups that would allow
  it and the workspace. Record writes check Edit live, or Work in change sets with `changeSetId`.
- Roles made of 13 action groups: nine predefined, read-only roles (Reader, Contributor, Data
  steward, Data owner, Model, Workspace and Integration administrator, Operator, Security
  administrator) and custom roles (`/api/v1/roles`, `GET /api/v1/action-groups`); local groups of
  people (`/api/v1/groups`); grants of a role to a person, client or group at the instance or in a
  workspace, optionally narrowing writes to applications and record types of its model
  (`/api/v1/grants`); who can do what in a workspace (`GET /api/v1/workspaces/{key}/access`); the
  caller's own (`GET /api/v1/me/permissions`, `GET /api/v1/me/grants`). Removing the last active
  Security administrator is refused. Migration `20261029_01`.
- Settings › Account lists the person's roles, where each applies, what it narrows and the group it
  comes through; the account menu names the roles held in the workspace open, and its Account and
  All settings are buttons like Sign out.
- `create_client --role <key>` grants roles to a new client at the instance.

### Changed (0.12 Z1)

- **A principal may do only what its roles allow.** `create_admin` gives the first administrator
  Security administrator, Data owner, Model, Workspace and Integration administrator and Operator at
  the instance; the upgrade gives the same to every person and client that existed before it; new
  people and clients hold nothing until granted. `/metrics` and `/api/v1/system/*` but `GET /system`
  need the Operator role.
- The workspace list, the workspace models, the jobs and the consumer subscriptions list only what
  the caller holds a role for; a named workspace the caller holds nothing in answers `403`.
- Permissions follow a generation number PostgreSQL raises on every change to roles, groups,
  memberships, grants or a principal's `active`, so a change applies on the next request in every
  process.

### Added (0.12 I2, signing in from the browser)

- The engine's sign-in page (`/oauth/authorize`): the browser signs a person in with the
  authorization code flow and PKCE and returns to the page asked for; the access token stays in
  memory and the session in an `HttpOnly`, `SameSite=Strict` cookie that renews it unseen, each
  refresh token used once (a reused one ends the session). Sessions end after `SESSION_IDLE_HOURS`
  (12) idle or `SESSION_DAYS` (14). `POST /oauth/revoke` signs out. Failed sign-ins are slowed per
  account and address, never locked. Migration `20261028_01`.
- The account menu names the person and offers Account, All settings, the theme and Sign out;
  **Settings › Account** shows the person, changes the password and lists where they are signed in,
  with sign out per browser or everywhere (`/api/v1/me/sessions`, `/api/v1/me/password`).
- `POST /api/v1/users/{id}/password-reset`: a one-time link (valid `PASSWORD_RESET_HOURS`, 24) to the
  engine's page that sets the person's password; `DELETE /api/v1/users/{id}/sessions` signs a person
  out everywhere. Deactivating a person ends their sessions.
- `PASSWORD_MIN_LENGTH` (15): a development machine may lower it for a short password (D276).
- Settings › Account reworked: a profile card, the password changed in place, sessions with device
  icons and relative times, and what you can do in each workspace (everything, until roles).

### Changed (0.12 I2)

- `GET /api/v1/me` adds `signedInWith` and `sessionId`. The metadata lists the authorization and
  revocation endpoints and the `authorization_code` and `refresh_token` grants.
- The browser reads a job's progress and downloads exports and consumer OpenAPI documents with
  `fetch` and the access token; the consumer `openapi.json` link on Settings › API reference, refused
  since I1, works again. The browser runners sign in as a test person through the real form.

### Added (0.12 I1, the engine issues tokens; every route authenticated)

- The engine is its own OAuth 2.0 authorization server: `GET /.well-known/oauth-authorization-server`,
  `GET /oauth/jwks` and `POST /oauth/token` with the client credentials grant (`scope` `management`
  or `consumer`), errors in the RFC's shape. Access tokens are ES256 JWTs lasting an hour
  (`ACCESS_TOKEN_MINUTES`); their signing keys live in the database, sealed, replaced after
  `TOKEN_SIGNING_KEY_DAYS` (30) when the next token is issued, and rotated on request, at once after a
  leak (`/api/v1/token-signing-keys`).
- People (`/api/v1/users`: create, change, deactivate, never delete) and OAuth clients
  (`/api/v1/clients`, the secret shown once, a second secret with an overlap); `GET /api/v1/me`.
- `python -m app.cli.create_admin` (the first administrator, with the password rules: 15–128
  characters, not the username, not one of the most common) and `python -m app.cli.create_client`
  (a client's credentials, shown once). Migration `20261027_01`.
- `GET /api/v1/system/configuration`: the database revision and the settings, moved out of
  `GET /api/v1/system`, which keeps what the deployment runs. Settings › Deployment shows the
  migration revision; About no longer does.

### Changed (0.12 I1, breaking)

- **Every route needs an access token** except `/health`, `/health/live`, `/openapi.json`, `/docs`
  and the OAuth endpoints: `401 AUTHENTICATION_REQUIRED` without one, `401 TOKEN_INVALID` with the
  reason otherwise. This includes `/metrics` and the consumer API (a `consumer` token; its index and
  OpenAPI documents take a `management` token too, D266). Until roles
  (Z1) every active client or person may use every route. The browser shows the refusals until
  signing in arrives (I2).
- `SECRETS_ENCRYPTION_KEY` is required on every installation and seals token and webhook signing
  keys; it replaces `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup refuses by name. `PUBLIC_URL`
  names the engine's address, the token issuer. Upgrading: OPERATIONS § Authentication.

### Added (0.12 P0, design only)

- The security design: the engine as its own OAuth 2.0 authorization server (ADR-043), roles made
  of journey-named action groups granted to people, groups and clients per workspace (ADR-044), and
  change-set publication approvals with an inbox (ADR-045); every management operation mapped to its
  action group in API.md § Security; journeys J39–J43; the Security pages (U8) from approved
  mock-ups. Decisions D243–D257. No code changes yet.

## [0.11.0] - 2026-10-22

Base 0.11 is released: each workspace runs a model of its own and moves to another release on its
own (Track M, Track V), data moves between workspaces whose models differ (Track X), and the engine
is hardened for production (several processes and nodes, PostgreSQL at volume, operability, backup
rehearsal, touch drag), accepted by R: a full review of every change since 0.10.0 with an independent
reviewer (12 findings, 10 fixed, R-F7 and R-F11 kept by decision), the full backend suite, the 56
browser runners, J36–J38 by keyboard alone on two models, the accessibility and visual gates with
Settings › Operations, an upgrade from 0.10.0 and the budgets. No schema language is released; the
window stays 0.5–0.10. Licensing, the contribution and security policies and the compatibility
commitment moved to 0.12, the first public release.

Nine migrations since 0.10.0 (`20261018_01` … `20261026_01`; eight since 0.11.0-alpha.1); a database
of 0.10.0 or 0.11.0-alpha.1 upgrades on start.

### Changed (0.11, the first public release moved to 0.12)

- Licensing, contribution and security policies (L1) and the compatibility commitment with the
  supported schema versions and their dates (L2) moved to 0.12, which becomes the first public
  release; the project's name is not chosen yet. 0.11.0 is released as an ordinary release.

### Fixed (found in 0.11 R's review)

- A workspace migration's type mapping naming an attribute's source was ignored when the target type
  also had an attribute of the source's name listed first: that attribute kept the values and the
  named one lost its own (R-F1). Two attributes trading values (`a` from `b`, `b` from `a`) failed
  the preview as an internal error (R-F2).
- A released type moved to another application in the editor (`setContainment` with
  `application`) lost every record of it in the migration its activation needs, unless an API
  client mapped the type onto itself, which the migration page cannot: its records now go to the
  one application listing it (R-F3).
- The relation matrix's and the relationship form's save did not send
  `X-Expected-Model-Release-Id` (R-F4).
- A migration, or a change set's move, confirmed or queued before its workspace was retired still
  ran: it is now refused `409 WORKSPACE_RETIRED` at confirmation and as it runs (R-F5). Activation
  holds the workspace row for key share, so a retirement during its check is seen (R-F12).
- A workspace migration held the unique values' table lock, which every value write of every
  workspace waits for, from its first step to its commit (66–111 s at 100,000 records): it now takes
  it just before the switch (R-F6).
- A change set's move did not hold its workspace's assignment, so an activation committing meanwhile
  left the change set pinned to the release the workspace had just left (R-F8).
- A move's load committed its first step (the target's change set opened) without checking that the
  job was still its worker's; a worker frozen past its lease could leave a second change set (R-F9).
- The FastAPI lower bound is 0.141, the version the engine is tested on: the read guard uses
  `Depends(scope=...)`, which older versions lack (R-F10).

### Fixed (found in 0.11 R's browser runners)

- At 390px a notice with actions (a change set on another release offering to move it or its
  workspace) kept its actions beside its text: the text was a word wide and the page scrolled
  sideways by up to 339 px. A notice's actions now go below its text when they do not fit, and a
  long action wraps its label (`wp13c`, `sc15`).
- A list drawn by row number as tall as its rows, such as the type change dialog's records, could
  stay empty: with no row drawn it had no height, and with no height the virtual range drew no row.
  It now draws the rows it holds whenever that range comes out empty (`c5`).
- After applying a restructuring, focus was meant to move to Done a frame later; on a page busy
  redrawing what the apply changed, Done was not there yet and focus was lost. It moves once Done is
  drawn (`c5`).

### Changed (0.11 R)

- A migration preview holds the live rows it converts while it runs; a write to one of them waits
  for it, which ARCHITECTURE and API.md now say (R-F7, decided by the user). A preview over private
  copies is in TODO.

### Added (0.11 U1, touch drag in the record tree)

- On a touch screen a record in a tree view or the sidebar is dragged by holding it still for half a
  second (D210): moving first scrolls, a short tap opens the record. Once lifted, the finger drags
  instead of scrolling, the list scrolls at its top and bottom edge (56 px for a finger, D211), and
  the preview sits above the finger, inside the screen (D212). Let go where it was lifted, nothing
  opens; in the sidebar the node menu (Move to…) opens, also on iPhones, which had no way to open it
  (D213). Never in a publication or a read-only tree (D214).
- `test:browser:touch-u1`: Chromium with Pixel 7 emulation and real touch input, WebKit with iPhone 15
  emulation (D215).

### Fixed (found in 0.11 U1)

- The drag's edge scroll at desktop widths started its top band under the sticky top bar, so a drag
  upwards could not scroll the page; the band now starts below the bar (`scroll-padding-top`).
- `OperationsPage.tsx` failed lint (`preserve-manual-memoization`).

### Changed (0.11 Q3, attribute sorts over very large parents)

- A change set's list sorted by an attribute reads in value order, as live and publication lists do:
  the base's records it keeps and its own, each through its value index, merged by their first rows
  (`pagination.merged`, D205). At full volume the 20,000-child parent's first page takes 14.5 ms
  (167.9 before).
- A total under an attribute sort counts the records without reading their values, in every context
  (live 94 → 11 ms at full volume).
- Records sorted by an attribute that share a value come by record ID live too, as in change sets
  and publications (D206). A live cursor or anchor of such a list issued before this release is
  refused once as `INVALID_CURSOR`, and the browser restarts the list.
- Migration `20261026_01`: `ix_snapshot_attribute_values_change_set_key_boolean`, so a change set's
  sort by a boolean reads in value order (D207).
- Not changed: a position deep under an attribute sort still grows with the records listed (124 ms
  in a change set at row 15,000 of 20,000, over the budget; stored sort keys in TODO); ancestor sorts,
  measured within the budget (D208).

### Fixed (found in 0.11 Q3)

- `test_build07_wp11` expected the 12-character correlation ID O1 replaced with the request's
  `X-Request-Id`.

### Added (0.11 O2, backup rehearsal and the Operations page)

- `python -m app.cli.restore_check --restored <URL> [--backup <name>]` checks a backup restored into
  a separate database: it prepares the copy as startup would, loads each workspace's release on its
  own, counts each workspace's records, relationships, open change sets and publications beside the
  live records, and records the result, passed or failed with its code, in the instance (table
  `backup_rehearsals`, migration `20261025_01`; J12.16, J12.17, D198–D200). A copy that is the
  instance's own database is refused before anything changes.
- `GET /api/v1/system/backup-rehearsals`, paged newest first, and `GET /api/v1/system/summary`, the
  instance figures of `/metrics` as JSON (D201).
- Settings › Administration › **Operations**: the instance's figures, each workspace served or not
  and by which process, every process with its threads, connections and requests, the last backup
  rehearsal with each workspace of the copy, the earlier ones, how to rehearse and the probe
  addresses; refreshed every 15 seconds while visible (U7, D202, D204).
- `scripts/postgres.sh rehearse [<dump>]` restores a development dump into a scratch database,
  checks it and drops it; `scripts/postgres.sh backup` leaves out the processes' rows (D203).
- OPERATIONS § Backup and restore: taking a backup, rehearsing it, recovering, and what a restore
  is; the rehearsal on the development database recorded.

### Changed (0.11 O2)

- A startup refusal carries a code (`DATABASE_COLLATION`, `DATABASE_EXTENSIONS`,
  `DATABASE_REVISION_UNKNOWN`, `DATABASE_MIGRATION_FAILED`, `DATABASE_UNREACHABLE`), which a failed
  rehearsal records; the messages are unchanged.

### Added (0.11 O1, metrics, logs, health and readiness)

- `GET /health/live`, the liveness probe: `200` whenever the process answers, never asking the
  database, so a database outage restarts no process. `/health` stays the readiness probe (D191).
- Each process reports itself through the database every `PROCESS_HEARTBEAT_SECONDS` (15; table
  `engine_processes`, migration `20261024_01`). `GET /api/v1/system/readiness` names each active
  workspace served or unavailable, with the live processes that cannot serve its release and why
  (`unsupportedSchema`, `invalid`, `notLoaded`); `GET /api/v1/system/processes` lists every process
  live or silent, ready or not, with its threads, pool and counters (J12.13, D192).
- `GET /metrics` in the Prometheus text format, the whole instance in one scrape: requests by route
  template and status, durations, connections in use and missing by reason, failing threads,
  readiness, each labelled by process; jobs, webhook subscriptions, processes and unavailable
  workspaces counted when scraped (J12.14, D193, D194).
- `LOG_FORMAT` (`text`, or `json` lines) and `LOG_LEVEL`; one access line per request from the
  engine instead of uvicorn's; every request carries `X-Request-Id`, the client's when well formed,
  which `INTERNAL_ERROR`'s `correlationId` now is (J12.15, D195, D196).

### Fixed (0.11 O1)

- Processes starting together could collide building the relation matrix states (a unique
  violation logged at ERROR; the API served and derived the cells from records). The build now runs
  under the startup lock, after the bootstrap install. The JSON and text log formats showed it: the
  previous log printed the line without its level.
- The engine's INFO lines (startup builds, recoveries) were not written under uvicorn: nothing
  configured the engine's loggers, so only warnings and errors reached the console.

### Changed (0.11 Q2, value indexes)

- A change set's unique checks and key references on a number, decimal, date or instant seek the
  value instead of reading every value of the attribute in the change set and its base: four partial
  indexes on `snapshot_attribute_values` (migration `20261023_01`). Live checks already sought their
  value. The indexes are the same for every model; what follows a workspace's model is which values
  are looked up (D186).
- A move's match by a unique attribute seeks the target workspace's unique values by digest; it read
  every value of the attribute in every workspace (J38.5).

### Fixed (0.11 Q2)

- The mapping inference counted only unique text values as values the two workspaces share, and
  proposed the match on the first attribute unique on both sides. Unique values of every type count
  now, and the match goes to the unique attribute whose values the records share (J38.1).

### Added (0.11 N3, several processes)

- `DATABASE_IDLE_TRANSACTION_TIMEOUT` (300 s, `0` off), reported by `GET /system`: the database ends
  a transaction a stalled process (frozen, starved of CPU, cut off) left idle that long, so the
  writes waiting for its locks go on. A frozen process held its workspace's writes until it resumed
  (J24.3). The startup lock's connection does not carry it.
- `503 DATABASE_UNAVAILABLE` takes `details.reason` `transactionEnded` when the database's notice
  reaches the resumed process.
- The concurrency and uniqueness invariants are tested across two server processes on one database:
  a unique value, a record's version, a parent cycle, a cardinality limit, feed positions, and a
  background job's item on one node against a live write on the other.
- `tests/test_boundaries.py` finds SQL text that writes record rows outside the write unit; the three
  modules that do are listed with the lock they hold. No database constraint was needed.

### Fixed (0.11 N3)

- A job step whose database connection was lost or ended failed the job with an internal error and
  a traceback. It is rolled back and left to its lease, and the worker reports the outage in one line.

### Added (0.11 Q1, database connections)

- Each process's database connections can be set: `DATABASE_POOL_SIZE` (5), `DATABASE_POOL_MAX_OVERFLOW`
  (10) and `DATABASE_POOL_TIMEOUT` (30 s), reported by `GET /system`; OPERATIONS gives the arithmetic
  per process and per instance. A start whose processes could need more connections than the server
  allows logs a warning naming both figures (J12.11).
- A request that gets no database connection answers `503 DATABASE_UNAVAILABLE` with `Retry-After`
  and `details.reason` `poolExhausted`, `tooManyConnections` or `unreachable`, logged in one line
  naming the cause and the settings. It answered `500 INTERNAL_ERROR` with no cause in the log
  (J12.8, J12.11). The job worker, the event deriver and the webhook dispatcher report an exhausted
  pool or a full server in one plain line, as an unreachable database, not as a failure with a
  traceback.

### Fixed (0.11 Q1)

- A process with a pool of one connection could not start: the startup lock held one pooled
  connection while the bootstrap install waited for another. The lock's connection is outside the
  pool.
- Five `NOT IN` subqueries, which PostgreSQL scans once per row once they outgrow `work_mem`, are
  `NOT EXISTS`: the people export's walk, the mapping list's exclusive targets, the move binding's
  related records, a query's negated relationship criterion and the relation matrix's state filter
  in a change set. Not measured at full volume.
- The move binding's and the people export's working tables are analyzed once filled; PostgreSQL
  never analyzes a temporary table by itself, so their joins were planned on guesses. Not measured
  at full volume.

### Fixed (the model editor's moves)

- A type could not be moved to another application: Move to… and a drop on an application only set
  its parent, so the type stayed where it was, and a parent in the other application left the draft
  invalid. `setContainment` takes `application` (and `fromApplication` for a type in several): the
  type and every type under it move there with their views and detail pages, their containment and
  relations kept, in one step. A drop on another application, or its top level chosen in Move to…,
  sends it (J33.15). Nothing that can stand in the other application is left out: a list moves with
  the type it lists even when a column reaches another application's type, mapping grids and
  matrices that need a moving type follow it, a page the other application has already takes the
  panels it lacks, and what stays keeps its columns. First delivered without these, it dropped a
  list whose language column reached the translations, columns of a staying panel, and mapping
  grids; a sweep of every type to every application over three real models found them. What can
  stand in neither application (a matrix whose types no application lists together, a staying page's
  children panel of a type that moved) goes, and is named: a history entry's new `removed` lists
  it, and the editor says it after the step and in History. History names the application a type
  moved to.
- A tree view's top type given a parent left the draft invalid ("cannot exist without a parent");
  a type moved to the top dropped out of the tree it was a node of. The tree now grows up to the new
  parent, or takes the type as a top of its own, and drops what it can no longer show or offer.
- Merging a type into its parent made the survivor contain itself, and left consumer APIs naming
  the merged-away type. The containment between the two is dropped, and the consumer APIs name the
  survivor.
- Add XREF rule… listed a field several exposed types share under the first of them alone, so
  the others (a model's timetable types) seemed to have no field to match on. A rule weighs a
  field on every exposed type alike, so the list now shows each field once, under "Attributes of the
  exposed types", as the field sources do.
- A list inside a dialog (the relationship dialog's record list) carried the wheel at its first
  or last row on to the page behind the dialog, so the table there moved. A list carries it no
  further than its dialog, and the dialog holds the browser's own carry too.
- The model pane did not scroll while a drag neared its top or bottom, so rows out of view could not
  be reached; it scrolls as the record tree does, through one shared helper.
- The t1 designer runner followed 0.11: a model of its own installs into a new workspace, read
  there by the consumer tier; a wait for an undone attribute no longer trips on two matching cells.
- The Install and activate dialog's buttons fell below its frame when the differences ran long; they
  stay at its foot as Map to…'s do.

### Changed (0.11 N2, the job worker on several nodes)

- A running job keeps its lease by a heartbeat, renewed every third of `JOB_LEASE_SECONDS` whatever
  its step. Before, a step longer than the lease (a move's binding, which renewed nothing; a chunk;
  one long statement of a migration) was taken over by another process and rolled back, and with
  two processes they could take it from each other indefinitely. A job now moves to another worker
  only when its process stops renewing (stopped, crashed, frozen, cut off from the database), no
  longer when its worker waits on a lock (J24.3 revised).
- A job queued through a process whose worker is busy starts at once on an idle process, which
  hears it through `LISTEN`; before, it waited for that process's next poll, up to 60 s.

### Fixed (0.11 N2)

- Two dry runs, inferences, mapping inferences or profile checks of one subject sent at the same
  moment both ran, neither stopping the other, and an older inference finishing last replaced the
  newer one's proposals. They are now decided one after the other; the later one stands.
- A profile, inference, dry run or check asked to stop after its last check still completed and
  wrote its result; it now ends cancelled, writing nothing.
- Two files uploaded to one import profile and profiled on two processes could leave the profile's
  check on the older file, when that file finished last. A file replaced meanwhile is no longer
  checked.
- A cancel sent while a move settled its rows, or deleted in its source, waited for that step; it
  now answers at once, and a cancel during the source's deletion stops it there.
- An export taken over by another process after its first stalled could be served corrupted or
  removed: both wrote one partial file, and the first, finding its lease lost, removed the job's
  files, the new owner's included. Each worker now writes and removes only a partial file of its
  own lease, and renames it into place under the job's lock.

### Added (0.11 N1, several processes)

- Model administration works with several processes on one database: Uvicorn workers
  (`WEB_CONCURRENCY` above 1) or instances on several nodes. Startup no longer refuses
  `MODEL_ADMIN_MUTATIONS_ENABLED` with more than one worker. A release activated or a workspace
  migrated through any process is served by every other from its next request, with no restart.
- Processes starting together on one database check, migrate and install the bootstrap model one at
  a time under a database lock; before, the second could fail its migration and stay in maintenance
  mode. Release installations take a database lock in place of the in-process one, so two processes
  installing the same model at once answer `201` and `200` with one release instead of a `500`.
- A read whose workspace was migrated, or whose change set was moved, to another release while it
  ran answers `409 MODEL_RELEASE_CHANGED` instead of one release's model over the other's data, in
  one process or several; the shell's notice offers Reload. The in-process guard it replaces covered
  only the moment a request resolved its release.

### Fixed (0.11 N1)

- A write whose commit check waited for an activation of its workspace could commit under the
  release it no longer ran, and an activation waiting for another one answered `503` ("runs no
  installed release") instead of `409 ACTIVATION_CONFLICT`. Both locked the workspace's assignment
  joined to its release; after the wait, PostgreSQL rechecked the join against the release read
  before it, and the switched assignment dropped out. They now lock the assignment alone.
- The Settings navigation test still listed the pages before "Copy and move" (X4).

### Fixed (0.11 X6, list reads)

- A table with relation columns opened in seconds: a column showing a value of each related
  record's ancestor built every related record whole (all its values, its path) and kept one value,
  250 ms of a 294 ms read for 200 rows, and the table read 200 rows at once. An expansion that names
  its fields (every relation column does) now reads only those fields, with the ancestor's value
  found by a walk up the parent chain, in the one statement it already ran; the answer is the same in
  live data, a change set and a publication. A 20-row page with relation columns now loads 3 to 4
  database rows per listed row instead of 6.5 to 8.5.
- Identical reads made while the first is still in flight share it: the development build's double
  mount no longer sends every read twice, and a page load reads capabilities, the workspace and the
  rail's lists once each. Nothing is cached.

### Changed (0.11 X6, long lists)

- Every long list (collections, record panels and relationships, the model editor's tables, job,
  migration, move and profile reports, the relation matrix, the mapping grid, change set review, the
  restructuring and tree-move dialogs, the matrix cell dialog and column filter, the record lookup)
  is drawn by row number: the scroll space spans the whole list, sized from its total, and only the
  rows on screen and a screen either side are in the page. A row whose page has not arrived shows as
  a loading row at its place, and pages arriving or rows forgotten move no other row. The browser's
  own scrollbar is the list's; the hand-drawn one is gone. Every read is the reader's page (20 by
  default); a scrollbar drag, a fling or the page field reads once where the list comes to rest. An
  edit in place keeps the list where it was. The record tree keeps its groups as they are.
- A list reads on in the background, a page at a time, until it holds about as much as it keeps
  (600 rows): a list of a few hundred records is held whole a moment after it opens, so scrolling
  never meets a row not read (reported 2026-10-19: grey rows while scrolling 200 records).
- Scrolling a table with relation columns no longer stutters. A relation cell works out how many
  chips fit from their text and its column's width instead of drawing every chip, measuring it and
  drawing again; the edit and remove buttons are drawn in the row the pointer is over or that holds
  focus, the other rows keeping their room (on a touch screen every row still has them); a row
  already drawn is not drawn again while the list scrolls; the visible rows are found from the
  scroll position, not read from the page. In the production build the reported view scrolls at a
  steady 60 frames a second.
- Fixed: a row could move under the reader while scrolling (row heights rounded to whole pixels;
  the first drawn row losing half its border), and Ctrl+End followed at once by Ctrl+Home landed at
  the end.
- Known limits: the browser's find in page finds only the drawn rows (the list's search finds every
  record); a screen reader browsing a table without moving focus meets a row's edit buttons only in
  the row that has focus.

### Fixed (tables)

- Lists drawn by the shared table (collections, record panels, the model editor's preview and the
  rest) scroll without jumping: the columns keep the widths the first rows laid out instead of
  moving as rows come and go; a page read while scrolling is drawn in the background, row by row;
  writing the list's place to the address no longer draws the page again. (The 200-row reads and
  the browser's scroll anchoring of this change were replaced in 0.11 X6 by lists drawn by row
  number.)
- The wheel is no longer held in a table: it first brings the whole table, with its controls, into
  view, and at the table's first or last row the page scrolls on. The table's height leaves room for
  the top bar, the data band and its controls. Carrying one gesture's momentum on from the table to
  the page is in place but not yet smooth (reported 2026-10-19).
- The model editor's issues and history start closed; Show issues opens them without keeping them
  open next time.

### Added (hierarchy browser)

- Expanding a record or type heading in a hierarchy (the rail and the tree lens) opens its child
  when it holds only one that can expand: a record's only heading, a heading's only record. Only
  that one level opens, so the reader sets the depth; with several children all stay collapsed. It
  happens at every expansion, also after the child was collapsed by hand, and the tree's first
  display opens a sole top-level heading. A reveal (the open record's path) or a drag does not.

### Fixed (navigation rail)

- The rail no longer scrolls by itself. A record group finishing its load (its first page, the
  active record's branches, a reload after a write) scrolled the rail to that group, so the rail
  jumped as lists arrived; now only keyboard movement in the tree scrolls it, and only the rail,
  never the page. The tree lens loads the same way, and shows a record it reveals on request.
- The rail keeps its place for one application in one workspace, across pages, records and views,
  and into and out of a change set or publication, which mount the frame afresh. Another application
  or workspace opens the rail at its top, instead of at the offset the previous one had.
- A record chosen in the rail leaves focus in the rail, as a collection or group already did; the
  record page no longer takes it.
- Rows dropped or added above the view (a long group paging on, Show earlier records) no longer
  shift it in a browser without scroll anchoring; scrolling past the rail's end no longer scrolls
  the page.

### Fixed (0.11 X5)

- Publishing a change set into a workspace whose records are newer than the database's statistics
  (a moved workspace, an import into an empty one) took minutes: freezing the publication's
  relationships joined both ends to the records and PostgreSQL paired every record with every
  other, and freezing its records recomputed the workspace's values for each record. A publish of
  11,000 moved records took 9 minutes and now takes 19 s; 110,000 records publish in 3.4 minutes.
  The same copy opens a change set over current live data, so a small move just after a large
  publication no longer waits two minutes (the 13-second wait seen in X3).
- A move's dry run built each record's item by reading every relationship once per record: 63 s of
  an 11,000-record dry run, now under 6 s.
- A move, an import or a publication of more than 65,535 records failed with a database error:
  the unique-value check after the write, the write unit's removals and the publication's merge
  listed every record as a parameter of its own. Each is now one array parameter or a join.
- Moving a whole subtree kept its top record in the source, "with dependants", when those
  dependants were the records the same move deleted: the source's deletions now run in passes, so
  a parent is deleted once its moved children are.
- A move's deletions refused before the copy is published name the copy's change set and workspace
  instead of its ID.
- The copy and move editor answers faster at everyday sizes: a step's figures in 0.3 s at 200
  records and 1.4 s at 2,000, the editor open in 1.1 s and 2.0 s. A dry run of records just written
  read the selection again for every record (4–7 s at 2,000 records, now under 1 s on the server);
  a repeated dry run in a larger workspace compared its own rows with each other (40 s, now 1.7 s);
  the relationships whose records do not move were looked up one by one; and the page redrew every
  mapping row for new figures.
- The mapping grid loads again: since the tables began reading 200 rows at a time it asked the
  coverage route for more than its 100 and showed "Could not load this content".
- The copy and move editor's default buttons say which field they change ("Set a default for
  Steward…"), so they are not two buttons both named "Change…".

### Added (0.11 X5)

- `test:browser:workspace-x5`, the move checkpoint: records copied and moved between workspaces of
  partly compatible models through a proposed and hand-completed mapping, the report, the reviewed
  change sets published, a second copy updating the same records, records moved back to their
  originals, and the editor timed at 200 and 2,000 records.
- The copy and move surfaces are in the accessibility and visual gates.
- `volume_baseline.py --only-move`: a whole volume workspace moved into another model, each step
  timed once, with every statement over half a second named.

### Added (0.11 X4)

- The move editor in the browser. Settings › Data operations › **Copy and move** lists the mappings and the
  recent moves; **New copy or move…** chooses two workspaces and a saved mapping or a new one, proposed by
  the engine and applied before the editor opens. A workspace's page in Settings › Workspaces has
  **Copy or move data…**, the same dialog with that workspace as the source.
- The editor (`/settings/moves/{mapping}?from=&to=`): both workspaces and models, what moves (every
  mapped type, the whole workspace, chosen types with filters, or one record and its subtree), Copy
  or Move, the dry run's figures with their change since the last step, the source's types, the
  mapping by type with every row a step marked **Proposed** while it is as proposed, undo and redo,
  and why a row was proposed with its evidence and alternatives. Each step runs the dry run of every
  item again and cancels the one before; a mapping with problems lists them, linked to their rows.
- **What cannot move**: every item by reason, linked to the mapping row that changes it; **Start the
  move…** opens the change set (and, for Move, the source's deletions) under a name given, and a
  mapping or release changed since the dry run asks to run it again. At 390px the editor is tabs.
- `ui/ProposalNote` and `ui/OutcomeCards`, shared with the workbook editor and the migration page;
  the model editor's undo and redo rules read a mapping's history too.

### Changed (0.11 X4)

- The move editor says what is happening in one status line under its title: the dry run in
  progress and why Start waits, the dry run ready, the copy or move loading with its progress, and
  done with the change set to review. A copy is called a copy throughout; the settings page is
  **Copy and move**.
- The change set bar shows "Change set validation passed" beside its buttons instead of in a notice
  below, so the buttons stay where they are.
- The workspace selector lists active workspaces only; a retired workspace is opened from Settings ›
  Workspaces.

### Fixed (0.11 X4)

- A move's relationship row names its two records (`fromName`, `toName` on `GET
  /api/v1/jobs/{jobId}/rows`), and the report shows each as "‹from› → ‹relationship› → ‹to›"; rows of
  one record looked alike, naming it by ID. A refusal by a relationship end's criteria reads "Record
  not allowed at a relationship's end", saying what it means.
- The jobs list names move and mapping-proposal jobs, which it showed without a kind.

### Added (0.11 X3)

- The move between workspaces whose models differ. A move's dry run (`POST /api/v1/moves`) now waits
  for confirmation, and `POST /api/v1/jobs/{jobId}/confirm` loads what it previewed into a new
  change set of the target workspace, opened for review over current live data; with `stage:
  execute` the move loads at once. Nothing reaches the target's feed or consumers until that change
  set is published.
- Where each record a move created came from (its source workspace and record) is kept: a second
  move updates the records found again, and a record moved back updates its original
  (`updateOriginal`, `foundBy: origin`) or, when a move deleted the original, is created again under
  the original's ID. A created record's row names its `origin`, and a record's history names it on
  every entry a move caused (`cause.origin`).
- `mode: move`: the copy, plus a change set of the source deleting each selected record that loaded
  with its own relationships; a record changed in the source since the dry run (`SOURCE_CHANGED`)
  or one that a record staying depends on (`OBJECT_HAS_DEPENDANTS`) is kept, each row saying what
  became of it in the source. The summary names both change sets, the source's feed position at the
  load and the deleted and kept counts.
- `409 MOVE_COPY_NOT_PUBLISHED`: a move's deletion change set publishes only after its copy;
  `422 MOVE_NOTHING_TO_MOVE`: a confirmation with nothing to create or update. A confirmation is also
  refused, leaving the dry run waiting, when the mapping changed (`MOVE_MAPPING_CHANGED`), either
  workspace runs another release (`MODEL_RELEASE_CHANGED`) or one is retired.
- Migration `20261022_01`: the table `record_origins` and a change set's `waits_for_change_set_id`.

### Changed (0.11 X3)

- A move's dry run ends in `awaiting_confirmation` instead of `completed`, and expires unconfirmed
  after the job retention, as an import's preview. Its rows can be filtered by the outcome
  `updateOriginal`.

### Fixed (0.11 S1)

- The job worker runs one chunk at a time whichever thread drives it: its claims accept its own
  leases, so a second thread of the same worker (a test calling `run_until_idle` while the service's
  thread ran) could run one chunk twice and fail the job.
- Three tests left behind by per-workspace activation (0.11 M1) assert it again: J35 and the J27
  export activate into the workspace they use, and the unique-value rows are checked per workspace.

### Changed (0.11 S1)

- Backend test runs: in a parallel run each journey test goes to a worker on its own, while any
  other test module stays on one worker, so a large journey module spreads over the workers (J34
  with J35, 1 min 10 s; J34 alone took 5 min 3 s). The journey model file is written whole before
  any worker reads it.
- The full backend suite runs with six workers (`pytest -n 6`) under a ceiling of 11 minutes,
  revised from 5 (D126): 10 min 15 s for 5,950 cases with the machine usable, where ten workers
  took 8 min 49 s at a load near 145. A package's checks have a ceiling of 3 minutes, revised from 2
  (D127). The development and test database folders are ignored by git also as links to `.nosync`
  folders.

### Added (0.11 X2)

- The dry run of a move between workspaces whose models differ (`POST /api/v1/moves`), a background
  job of kind `move`: what each selected record and the relationships it holds become in the target
  workspace through a model mapping at the version the client read, read from the source's live
  data or one of its publications. The selection is the whole workspace, types with an export's
  criteria, a subtree, records by ID, or several of these together. Every row is listed at
  `GET /jobs/{jobId}/rows` (filtered by `outcome`, `reason` and `sourceType`): `create` under the
  record's counterpart ID, `update` of a record found by its counterpart or by the mapping's match,
  `refused` with the target's own refusal, or `notMoved` with the mapping's reason and the step that
  changes it; with what a moving record leaves behind (attributes not mapped, values that do not
  convert, read-only attributes, effective periods the target type lacks) and possible duplicates.
  The job's `move` summary counts rows by outcome, type, relation type and reason. Nothing is written
  to either workspace.
- `422 MOVE_MAPPING_HAS_PROBLEMS`: a move whose mapping names what the two workspaces' releases
  lack or do not allow is refused with the problems.
- Migration `20261021_01`: the `pgcrypto` extension, the function `rdm_counterpart` (a counterpart
  ID derived in PostgreSQL, the same as the Python one) and the job kind `move`.

### Changed (0.11 X2)

- RDM Engine requires the `pgcrypto` extension beside `pg_trgm` and `btree_gin`; startup creates it
  or refuses with the instruction to install it, as for the other two.

### Added (0.11 X1)

- Model mappings (`/api/v1/model-mappings`): what each type, attribute, relationship and parent of
  one model becomes in another, with value maps, defaults and how existing target records are
  matched, saved between two workspaces' releases. A mapping changes only through operations
  (`mapType`, `mapAttribute`, `mapRelation`, `setParent`, `setMatch`, `setValueMap`, `setMissing`,
  `setDefault`, `setReleases` and their removals), with history, undo and redo; every read reports
  its problems (what a release lacks or no longer allows) and coverage (what it leaves out),
  against its releases or the releases two named workspaces run.
- The mapping's inference, a background job of kind `mappingInference`: proposals per type and per
  relationship from keys, names, attributes, parents and the records the two workspaces share, each
  with its evidence and alternatives, applied as steps marked as proposed. Two workspaces on one
  model are proposed as identity.
- Migration `20261020_01`: the tables `model_mappings`, `model_mapping_operations` and
  `model_mapping_proposals`, the job kind `mappingInference` and an index of a mapping's jobs.

### Changed (0.11 X1)

- A model draft and a model mapping share one history of steps, undo and redo; a draft's answers
  are unchanged.

### Added (0.11 V4)

- The schema-language window, 0.5–0.10, and the conversion rules between its versions written in
  one place (APPLICATION_MODEL, "Schema versions and the window"): reading, writing, running side by
  side, moving data between releases of different versions (by declarations only, never by version)
  and what happens outside the window. The window is declared once (`SCHEMA_VERSIONS`), held by a
  unit test.

### Changed (0.11 V4)

- Installing a draft of a schema outside the window answers `422 UNSUPPORTED_SCHEMA_VERSION` with
  `draftId`, `schemaVersion`, `supportedSchemaVersions` and `operation: "install"`, as activation
  does, instead of `422 INVALID_MODEL`.

### Fixed (0.11 V4)

- `RDM_MODEL_PATH` naming a model of a schema outside the window stopped startup with a traceback;
  it now refuses with a message naming the setting, the file, its schema and the supported ones.
- A workspace on a release of a schema newer than the window was logged with the schema 0.4 upgrade
  command, which cannot help; the log now says a later RDM Engine wrote the database and is the one
  to run.

### Added (0.11 V3)

- A change set left on a release its workspace no longer runs moves onto the workspace's release
  even when its content does not fit it: `POST /change-sets/{id}/model-migrations`
  (`expectedChangeSetVersion`, optional `targetReleaseId`, `typeMappings`), registered where
  background jobs run, starts a `migration` job (`parameters.moves: "changeSet"`). Its preview
  converts the change set's own content with a migration's rules, lays it over live data as it is
  now and lists every conversion, type change, loss and refusal, changing nothing; a record or
  relationship the change set changed that live data changed since it started is refused
  (`CHANGE_SET_CONFLICT`, `MAPPING_SET_CHANGED`), as is every rule the moved change set breaks.
  Confirmed (the change set's version, the workspace's assignment and feed position), the change
  set's rows, its base (now a capture of live data) and its release change in one transaction; live
  data, the workspace's release and its feed never do. Code `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`.
- The change set bar's notice offers **Move this change set to ‹release›…** beside V2's offer; the
  migration page names the change set, says live data stays as it is, confirms with **Move change
  set** and opens the change set when done.
- `snapshot_values.reindex_change_set`: a change set's typed value index rebuilt from its rows in set
  statements.

### Added (0.11 V2, API)

- A change set on a release its workspace no longer runs (typically one started from an older
  publication) is published by migrating the workspace to the change set's release:
  `POST /workspaces/{key}/model/migrations` takes `changeSetId` and `expectedChangeSetVersion`, and
  `targetReleaseId` is then optional. The preview also lists what would stop the publication as
  refused items (`CHANGE_SET_CONFLICT` and the graph's rules); the confirmation binds the change
  set's version and the active publication; the migration, the switch and the publication happen in
  one transaction, or nothing does. The summary names `changeSetId`, `changeSetVersion`,
  `activePublicationId` and `publicationId`. Code `MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`.

### Added (0.11 V2, browser)

- The change set bar of a change set on another release offers **Move ‹workspace› to ‹release› and
  publish…**; the migration page then says it publishes the change set, lists what would stop the
  publication, confirms with **Migrate and publish** and names the new publication.

### Added (0.11 V1, API)

- `POST /workspaces/{key}/model/migrations`: a workspace's data migrated to another installed
  release, of its model or another, as a `migration` job. Its preview changes nothing and lists, at
  `GET /jobs/{id}/rows`, every value converted, record reclassified, loss and refusal; `typeMappings`
  keeps a renamed type's records under their IDs. `POST /jobs/{id}/confirm` binds the reviewed
  assignment version and feed position and needs `acceptLoss` for a loss; the data and the
  workspace's release then switch in one transaction, each change audited with its feed position.
  Codes `MIGRATION_REVIEW_STALE`, `MIGRATION_HAS_REFUSALS`, `MIGRATION_LOSS_NOT_ACCEPTED`,
  `INVALID_MIGRATION_MAPPING`, `MIGRATION_TARGET_IS_CURRENT`, `MIGRATION_FAILED`.
- A job's `migration` summary; `POST /jobs/{id}/confirm` takes an optional body.
- Migration `20261019_01`: the `migration` job kind, `rdm_convert_value` and an index of a
  migration's items.

### Added (0.11 V1, browser)

- Settings › Model's activation dialog offers **Preview the migration…** when the data does not fit;
  the migration's page (`/settings/model/migrations/{jobId}`) lists what the release no longer has
  with a choice for each missing type and field, the items by outcome, and confirms once the loss is
  accepted; a stale review asks to preview again. `test:browser:workspace-v1`.
- A migration is refused with `409 CONSUMER_CONTRACT_VERSION_REQUIRED` when its target changes a
  consumer API's contract without a new version, as activation is.
- `test_migration_budget` (`budget`): a workspace of 100,000 records migrated once.

### Changed (0.11 V1)

- The compatibility analysis can list the records behind each rule a record breaks, and its scoped
  uniqueness count climbs from the rule's targets to their scope only (over 9 minutes at 100,000
  records before, 5.8 s now); activation shares it.
- A migration's long steps renew the job worker's lease as they run.
- ADR-034 amended (D71): a migration's type mappings change record types in live data.

## [0.11.0-alpha.1] - 2026-10-17

Each workspace runs a model of its own, released on its own (D12): everything since 0.10.0, Base
0.11 packages P0, M1 (with M2), M3, M4, M5, M6 and M6a. Moving a workspace's data to another release
(Track V) and data between workspaces whose models differ (Track X) follow in 0.11.0. One migration
since 0.10.0 (`20261018_01`, a release per workspace); a database of 0.10.0 upgrades on start.

### Added (0.11 M6a)

- `X-Expected-Model-Release-Id`, an optional request header on every management route: a request
  naming a release its workspace, change set or publication no longer resolves is refused with
  `409 MODEL_RELEASE_CHANGED` before anything is read or written. The browser sends it on its data
  writes; a page built before its workspace's model changed shows the refusal and a toast with
  Reload instead of saving under the new release.
- The API exposes `X-Model-Release-Id` to browsers on other origins.

### Added (0.11 M6)

- `test:browser:workspace-m6`: the workspace-model checkpoint, J36 composed in the browser on two
  generated models beside the starter.
- The workspace-model surfaces of M5 and M6 in the accessibility and visual gates, light and dark.

### Changed (0.11 M6)

- Settings › Model is laid out as Settings › Workspaces: the models in a list (the default
  workspace's first) beside the selected model's card with where it runs, its releases and its
  drafts. A redesign is planned for 0.14.
- "Activate a release…" is "Change model…"; its dialog groups the releases by model, the
  workspace's own first, and preselects nothing in another model.
- The top bar shows the default workspace's model's product name on every page, whatever model the
  shown workspace runs.

### Fixed (0.11 M6)

- On a phone, choosing a workspace from the band by tapping did nothing; only the keyboard switched.
- On the "not in this workspace's model" page the sidebar marked a collection as current; a
  workspace switch read the sidebar's collections twice.
- `test_boundaries::test_tiers_hold` failed on an import cycle in the source-file dry run; a model
  lifecycle test passed only after the tests before it.

### Added (0.11 M5)

- The browser follows each workspace's model: switching workspace changes the applications,
  navigation and pages to that workspace's model, with a toast when the model or release differs;
  the workspace selector names each workspace's model and release and marks another model or
  release.
- A page saying what an address asks for that the workspace's model lacks, with the workspaces
  whose model has it; the same for an unknown workspace and one whose release cannot be loaded.
- Settings › Model shows the workspaces with their models and releases, the installed releases by
  model with the workspaces running each, and the drafts; a release is activated into one workspace
  from that workspace's row or the release's page, checked against that workspace's data alone.
- Settings › Workspaces creates a workspace on another installed release; the model editor's
  Install and activate puts the release into an existing or a new workspace.
- `releaseName` on a workspace's model (workspace responses, its model route, `GET /workspace-models`,
  an activation's answer); `workspaceKey` on `GET /model-releases/{id}/diff`, whose `compatibility`
  and `consumerContracts` then describe activating into that workspace.
- `test:browser:workspace-m5`.

### Changed (0.11 M5)

- An address naming an application the workspace's model lacks no longer opens the start page
  silently; it says so.
- A job's page and toasts name types under the job's own workspace's model; the model editor's
  preview reads records only from a workspace running the draft's model; the load into a change set
  compares the draft with the release its chosen workspace runs.
- A release's page shows which workspaces run it and checks it against each workspace of its model;
  its Activate opens the activation dialog. The single "Active" release is gone from Settings › Model.

### Added (0.11 M4)

- `GET /objects` takes `workspaceKey` repeatable: two or more read those workspaces' live records
  in one paged list, each under its own workspace's model. A type or application some of their
  models lack is refused `422 MODEL_ELEMENT_NOT_IN_EVERY_MODEL`, naming those workspaces; a change
  set or publication with several workspaces is `422 WORKSPACE_CONTEXT_MISMATCH`.
- Every item of `GET /objects` names `modelReleaseId`, the release it was read under.

### Changed (0.11 M4)

- Counterparts stand only between workspaces running one model: an item or file row naming a record
  of a workspace running another model is refused `COUNTERPARTS_ACROSS_MODELS` (with the workspace
  and both model keys), and the import's notice says so, instead of loading it as this workspace's
  own record under a model it does not belong to.

### Added (0.11 M3)

- Import profiles belong to a model: `modelKey` on every profile, `workspaceKey` on its create,
  update, read and list, and the list's `modelKey` filter. A profile is refused
  (`422 IMPORT_PROFILE_MODEL_MISMATCH`) when saved, imported with or given a file in a workspace
  running another model, and reads there as not valid with that problem.
- Draft compilation and the release diff report `compatibility.workspaces`: what activating would
  need in each (not retired) workspace running the candidate's model, against its own release.
- The consumer API index and each OpenAPI document take `workspace` and answer `RDM-Workspace` and
  `X-Model-Release-Id`; the index's document links carry the workspace. The API reference page
  (`/docs`) takes `?workspace=`.

### Changed (0.11 M3)

- A draft is compared with its base release, or without one with the newest installed release of
  its own model, or with nothing when it is a new model (every element `added`, no consumer
  contracts, no data impact). A draft-only operation's impact counts only the workspaces running the
  draft's model. The top-level `compatibility` is what activating into the default workspace would
  do.
- Installing a draft whose profile key another model's profile holds is refused before anything is
  installed (`409 IMPORT_PROFILE_MODEL_MISMATCH`); installing no longer runs an unused
  compatibility analysis.

### Added (0.11 M1)

- Each workspace runs a model release of its own (ADR-042): `GET /workspaces/{key}/model`,
  `GET /workspace-models` (by model or release, paged), `modelReleaseId` on `POST /workspaces`, and a
  workspace's `model` on every workspace response. Two workspaces may run two different models.
- `POST /workspaces/{key}/model/activation` activates a release into one workspace: the compatibility
  check counts that workspace's data alone, the contract check compares with its release, only its
  subscriptions are suspended and its matrix states resynchronised; the answer lists its change sets
  left on the previous release (`changeSetsLeftBehind`).
- Every read and write resolves its workspace first, then that workspace's release: `GET /model`
  adds `RDM-Workspace`; a live write naming a record runs under the record's workspace model; jobs,
  batches, source files, consumer reads, subscriptions and webhook delivery under their workspace's.
  Unique values follow each workspace's release (D28).
- `GET /model-releases`: `assigned` and `workspaces` per release and the `assigned` filter (D24);
  activations name their `workspaceKey`.

### Changed (0.11 M1)

- The commit guard checks each workspace a write resolved, under a share lock on that workspace's
  assignment row: `409 MODEL_RELEASE_CHANGED` names `workspaceKey`, `resolvedReleaseId` and
  `currentReleaseId`. `CHANGE_SET_MODEL_RELEASE_CONFLICT` names the workspace.
- A release this version cannot serve makes only the workspaces running it unavailable
  (`503 MODEL_REGISTRY_UNAVAILABLE` with `workspaceKey`, `releaseId`, `schemaVersion`); `/health` is
  503 only when no workspace can be served (D29, D34).
- Settings › Model reads and activates the default workspace's model; Load into a change set
  activates the release into the workspace it loads into.

### Fixed

- Leaving a change set (discard or publish) left its confirmation as a notice above every page until
  the browser reloaded; it is now a toast, shown once and dismissable (reported 2026-10-15).
- Opening Settings reshaped the top bar: a way back was inserted after the product mark, shifting the
  application tabs, and the Settings icon became a wider "Settings" tab. The bar is now the same on
  every page: the Settings icon keeps its place and width and is marked current by the tabs' ink
  underline, and Settings has no way back of its own (the product mark and the application tabs
  leave it) (the user, 2026-10-15).

### Removed (0.11 M1)

- `GET /model-runtime-state`, `POST /model-releases/{id}/activation`, the `active` field and filter
  of `GET /model-releases`. Migration `20261018_01` gives every workspace the release the instance ran
  (version 1) and drops `model_runtime_state` and `model_releases.is_active`.

### Planned (0.11 P0)

- Base 0.11's design pass: each workspace runs a model of its own (ADR-042), with the decisions
  D4–D29 and the inventory of what a move between models meets accepted; the API design for a
  workspace's model, activation into one workspace, migrations, mappings between models and moves
  (API.md § Workspace models); journeys J36–J38; mock-ups of the shell and Settings across workspace
  models and of the move editor.

## [0.10.0] - 2026-10-15

Base 0.10 is released: the model designer and spreadsheet onboarding, accepted by R (a full review
of every change since 0.9.0, the full suites, the 49 browser runners, the accessibility and visual
gates with the spreadsheet and cell surfaces, the schema 0.10 checks and the budgets). Schema 0.10
(an application's `navigation`) is a released schema language; the starter stays content release
0.9.5 on schema 0.9.

Six migrations (`20261012_01`, source files and the `profile` and `dryRun` job kinds;
`20261013_01`, a model draft's import profile; `20261014_01`, a draft's proposals and the
`inference` job kind; `20261015_01`, the `profileCheck` job kind; `20261016_01`, a source file's
column statistics per block; `20261017_01`, indexes on the jobs a draft, a profile or a source file
has); a database of 0.10.0-alpha.1 upgrades on start.

### Fixed (0.10 R)

- An import that deletes the records missing from its file (`missing: delete`) through a source
  keyed by name no longer deletes a record a refused row names (an ambiguous name) (R-F1).
- The dry run's difference from the last one compares each source with its own figures when
  several load one type from one sheet (a list read block by block, translations by language) (R-F2).
- `allowRelation` with `required` to a released type is refused with its impact, as a required
  attribute is (R-F3).
- A list's single-valued relationship cell finds its relationship among every page of the record's
  relationships (R-F4); a relation column's chips use the cell's width again beside the edit icons
  (R-F18).
- A file's profile no longer blocks its owner's next upload and the draft's steps; a file's delete
  stops every job reading it first (R-F5, R-F8); inference and the profile's statistics renew their
  lease and stop for a cancel request (R-F6, R-F7); a dry run or check whose file went fails
  `SOURCE_FILE_NOT_FOUND`; the sweep supersedes a file a concurrent upload left current (R-F9);
  applying proposals locks the draft first (R-F10); a profile-only step's audit entry names the
  profile (R-F11).
- A rename or another step that cannot change the load leaves the running dry run to finish rather
  than stopping it with none to follow (R-F15).
- Checking the next version of a workbook that loads related records (translations) took 56 s at
  200 rows: the related records are found through each row's own relationships (R-F16). At 10,000
  rows a dry run's or a check's recording joined its fresh outcomes row against row: outcomes are
  inserted with their source and row, and the summary analyzes the job tables first; W1′'s check at
  10,000 rows 16 s again (R-F19).
- The dry run's, the check's and the inference's lookups of their earlier jobs use an index
  (migration `20261017_01`) (R-F14).
- Import profiles: an earlier read of the check answering late no longer sets the page back to
  Checking (R-F17).
- History names a renamed element by its name before the step; an editor table's cells break between
  words; Export, Import and both Load dialogs choose their workspace with the shared field, every
  page read; the editor's drawer counts every step of the draft.

### Added

- Base 0.10 A8c: lists of one shape read as one list under their headers (D140–D146; J34.10,
  J27.8). Three lists or more of a sheet laid out for reading under one title (or none) whose
  columns have the same kinds carry, on each list's proposal, the alternative "Read these N lists as
  one list under their headers": one step replacing them by a parent list of the headers and one
  list contained in it, a source per former list fixed to its header. A row under a list's header
  answering none of its yes/no columns is a second header row (a note with `meaning: "heading"`),
  skipped. Import: a source's `parent` (`objectTypeKey`, `matchBy`, `value`, `missing`) sets every
  row's parent, `PARENT_BOUND_TWICE` beside a parent column; a source keyed by name finds a row's
  record among its parent's children, one key under one parent across sources. `addSource` and
  `setSource` take `parent`. `test:browser:authoring-a8` gains the alternative applied from a list.

- Base 0.10 A9: a list's cells edited in place (D131–D139; J02.7, J13.11). In a collection or a
  record's table, the cell under the pointer shows a pencil and, where an optional value or a single
  relationship is set, a trash beside its value (always on touch); a click elsewhere still opens the
  record. A value or name is edited in the cell; a relationship a record holds one of is set,
  changed (among the binding's candidates) or deleted; one it holds several of is edited in a
  dialog of ticked records, saved as one inline atomic batch of the records added and removed. A
  toast says whether a save went to Live or the open change set. Ancestor columns, containment,
  required ownership, read-only bindings, computed fields and publications show no icons. The
  details panel's remove and the relationship panel's delete are one dialog each, shared with the
  cells. No API change. `test:browser:authoring-a9`.

- Base 0.10 A8b: the editor's source pane list by list (D122–D130; J34.10). A sheet laid out for
  reading shows its lists under their titles, each Proposed, Loaded or Not loaded, the open list's
  columns under it (one tree, keyboard operable); a selected list shows its titles, cells, note,
  what it loads, Proposed because and the sheet's cells around it. **Adjust list…** sets its header
  row, last row and columns over the cells (one `setSource`, and Name the list after the new
  header); **Don't load this list** removes its source and, when nothing else needs it, its list
  type, in one step; **Load as a list…** reads a rectangle as a list. API: `GET
  /source-files/{id}/profile/sheets/{sheet}/cells?range=` (paged rows of staged cells), `POST
  /model-drafts/{id}/inference/list` (a rectangle's `listBlock` proposal, not stored), `422
  INVALID_RANGE`; `setSource` moving a header row or narrowing a block keeps each binding on its
  column letter, the rest unmapped. `test:browser:authoring-a8`.

- Base 0.10 A8a: lists of a sheet laid out for reading, through the API (D114–D121; J34.10). A sheet
  holding no table but lists side by side and under each other is read list by list: each column
  run split at empty rows, prose left out, each list's header, the titles above it and a note under
  its header (`multiple answers`, `multiple choice`, `free field`, …); the profile's sheets gain
  `laidOut`, its blocks `titles` and `note`, and column statistics are kept per block (migration
  `20261016_01`; a column holding only its header listed with `filled` 0; an overlap names its
  `block`). The inference proposes a `listBlock` per list: a list type loading its block by name, its
  translations (else "Language k"), a yes/no column as an attribute, two or more as a flag set, the
  note row skipped and the note the type's description; a navigation group per title over two lists
  or more; a free field or a header without values is a warning. A source's key may be `{"field":
  "name"}` (`AMBIGUOUS_NAME_KEY`, `KEY_NOT_BOUND`); `addSource` and `setSource` take it. W3 gains a
  second band of lists with the real workbook's shapes.

- Base 0.10 A7: model-description sheets and matching across files (D106–D113; J34.9). A sheet of a
  field, a type and a target column is read before every other rule: the described type, a list per
  target read from its sheet by its ID and name (a placeholder ID skipped), a list to be defined
  added with nothing to load, a relation per lookup field, an attribute per plain field, one set per
  flag target (`modelDescription`, `describedList`, `describedField`, `describedFlags`). Extend mode
  across files: a sheet matched to a type by its fields, a proposed list to an existing type of its
  name, a code column to a stored unique attribute; missing values and name drift against the stored
  records in the evidence and the warnings, each with an alternative (create on load; load the
  file's names). A source's `rowsWithoutKey` (`refuse`, `skip`, `SKIP_NEEDS_KEY`) and `skippedRows`
  in the binding report and the dry run; `setSource` takes it. The placeholder words gain `tbc`, `to
  be defined`, `to be decided`, `to be confirmed`. The editor: a description sheet's columns read
  Describes the model, the dry run's rows skipped figure, the new evidence words;
  `test:browser:authoring-a7`. W2's generator returns its structures.
- Base 0.10 A5c: the next version of a workbook (D82–D85, D104, D105; J35). A file uploaded to a
  stored import profile is profiled and checked by a job of kind `profileCheck`, writing nothing:
  columns new, missing and renamed (same position, at least half the values shared), the profile
  against the active release, the dry run of the file through the profile as it would read it, new
  values of match columns, name drift and records missing from the file
  (`GET /import-profiles/{key}/check`, its `new-values`, `drift`, `missing-records` and `rows`;
  `POST …/check` checks again). A source's `missing` (`report`, `delete`): records no row names are
  counted by every binding and the dry run, and deleted only into a change set, each with its own
  relationships (`422 MISSING_DELETE_NEEDS_CHANGE_SET` live); the kind `setMissing`.
  **Settings › Data operations › Import profiles** lists the profiles; a profile's page uploads the next
  version, shows the check (Accept a rename, Ignore a new column, keep or delete missing records)
  and loads into a change set whose review holds only the differences. The editor's Load dialog and
  the profile's share their parts (`ChangeSetLoad`). `test:browser:authoring-a5`'s A5c walk.
  Revised the same day after the user's run on the development server: Import profiles is a catalogue
  beside the selected profile, as Workspaces and Webhooks; a profile's answer carries `lastLoad`
  (the latest import naming it and whether its change set is open, published or discarded), shown
  in the catalogue and on the profile's page, where a profile loaded from the editor read "no file
  uploaded"; the record page's breadcrumbs became `ui/Breadcrumbs`, which a job's page uses too
  (Jobs › the job). A settings group **Data operations** holds Import profiles (at
  `/settings/import-profiles`; the old `/settings/imports` still opens it) and Jobs (renamed from Jobs
  and feed; the change feed's retention moved to Consumer APIs), ahead of Integration.

- Base 0.10 A6b: the editor filled by the inference (D94; J34.4, J34.6, J34.8). New from a workbook
  asks what to propose (a new application with its name, additions to the model, or nothing) and the
  workspace the columns are compared with; once the workbook is profiled the editor proposes and
  applies the proposals, one step each, and shows the sheet's type. What is still as proposed reads
  **Proposed** in the model and source panes (a tone of its own) and its centre says **Proposed
  because**, with its evidence and its alternatives as steps; History names each proposal; ⋯ ›
  **Propose again…**; disagreements are Issues with Go to column. Map to… reads a column as a related
  record matched by a unique attribute, or as a value of a related record under its parent; a
  column's centre lists its most frequent values. `test:browser:authoring-a6`.
- Base 0.10 A6a: inference over the table patterns (D86–D98; J34.4–J34.6), through the API.
  `POST /model-drafts/{id}/inference` runs a job of kind `inference` over the draft's source file in
  new-application or extend mode; `GET …/inference` reads its counts, disagreements, warnings and
  the elements still as proposed; `GET …/inference/proposals` lists each proposal with its pattern,
  columns, one-sentence summary, evidence, operations, alternatives and requirements; and
  `POST …/inference/application` writes the open proposals into the draft, one history step each,
  with one dry run after the last. The patterns: a sheet's key and name, a repeated parent with the
  columns constant within it, level columns, a code and name pair with its name drift, flag columns
  with a multi-valued column beside them, multi-valued cells, text lookups with their placeholders,
  references to another sheet, translations by row and by column, GUID columns, every other column
  as an attribute, and a navigation group of a sheet's lists (raising the schema language to 0.10
  when needed). Columns of several sheets with one header and type share an attribute type. Extend
  mode maps sheets, columns and lookups onto the draft's existing types, attributes and records
  first. Proposing again recognises its earlier proposals: what is still the engine's follows a
  newer workbook, what the administrator changed is kept and a column read otherwise is reported
  (`INFERENCE_DISAGREES` also among the profile's warnings); an undone proposal is not applied again.
  W1 goes from upload to a published change set by applying its proposals. The optional assistant
  is an interface only (`INFERENCE_ASSISTANT`, `INFERENCE_ASSISTANT_ROWS`), off by default.
- Base 0.10 A6a: `missing: "create"` on a flag set and on a related record's `parent`, and a
  `record: "existing"` row finding the record another source of the same file creates (D93); the
  kind `unmapColumn`, and `addValuesToList` on flag columns and related records; a profiled column's
  most frequent `values`.

- Base 0.10 A5a: a model draft's import profile, edited by operations (D74–D80; J34.2, J34.7,
  J34.8), through the API. A draft holds one profile, read by `GET /model-drafts/{id}/profile`
  with the import profile it stands for and its warnings against the draft's model. Eleven source
  and mapping kinds on `POST /model-drafts/{id}/operations` edit it (`setProfile`, `addSource`,
  `setSource`, `removeSource`, `ignoreSheet`, `mapColumn`, `setColumnReading`, `splitColumn`,
  `ignoreColumn`, `addValuesToList`, `setValueMap`), each one history step undone exactly. The model
  kinds carry the profile with them: a key change rewrites it, a moved attribute's column moves to
  the target type's source on the same sheet, a split starts a source of the new type joined by the
  split's relation, a merge re-points the merged type's sources, an attribute turned into a list
  type becomes a lookup creating its values, and what a removal takes away is kept as an unmapped
  column with a `COLUMN_UNMAPPED` warning. A step that can change what the load writes queues the
  draft's dry run with its profile (`dryRun` in the answer; not after labels, the release identity,
  layout, navigation or consumer API steps). Installing the draft saves its profile as the instance
  profile of its key, checked against the new release (`importProfile` in the answer).
- Base 0.10 A5a: `missing: "create"` on an import profile's `parent` and `relation` bindings matched
  by name: a cell naming no record creates one by its name, once per value per load, before the
  records naming it (D77); `CREATE_NEEDS_NAME_MATCH` refuses it with any other match.

- Base 0.10 A3: source files, their profiles and the dry run (D65–D71; J34.1, J34.3), through the
  API. `POST /source-files` keeps an XLSX or CSV file for a model draft or an import profile (in
  `JOB_FILE_DIR` as `{id}.upload`, under `IMPORT_MAX_BYTES`, deleted with its owner; an upload
  supersedes the owner's earlier file, deleted `JOB_RETENTION_DAYS` later) and queues a `profile`
  job, which stages every filled cell in PostgreSQL once and profiles it with set statements:
  `GET /source-files/{id}/profile/sheets` lists each sheet's blocks with their header rows (D68),
  `…/sheets/{sheet}/columns` each column's filled and distinct counts, value types, candidate key,
  delimiters, placeholders (D70) and overlaps with other columns and, in a named workspace, with the
  model's record names and unique text attributes (D69). `POST /model-drafts/{id}/dry-run` runs the
  import preview of the draft's file through an inline profile (D65) against the draft's compiled
  model, binding the staged cells (D66), over every item (D67), as a `dryRun` job that writes
  nothing; `GET …/dry-run` reads its summary per source with the difference from the previous one,
  `GET …/dry-run/rows` the rows behind a figure (`source`, `status`, `code`). A dry run of a draft
  changed since is cancelled, as is a running one when another is sent; a draft that does not
  compile is refused `422 INVALID_MODEL` (D71). `POST /imports` takes `sourceFileId` in place of the
  file part. The synthetic workbooks W1, W1′, W2 and W3 are generated by `tests/workbooks.py`.

- Base 0.10 A5b: the model editor with a workbook (D81, D84; J34.1–J34.3, J34.7, J34.8). **New from
  a workbook** on Settings › Model creates a draft with the workbook and opens it; an open draft takes
  one, or a newer one, from its ⋯ menu. A **source pane** left of the model pane shows the sheets as
  tabs and each column with its status and statistics; a selected column shows its mapping in the
  centre (what it feeds, its reading, match, split, created values, value map, key, refused rows and
  statistics), and the type it feeds is marked in the model pane. **Map to…** (from the column, by
  Shift+F10, or by dragging the column onto a type) maps a column to a name, an attribute or a new
  one, the parent, a related record or a flag of a relation, or ignores it, starting the sheet's
  source where needed, in one step. A value map starts from the column's placeholders. The drawer
  gains a **Dry run** tab with each figure and what it was, opening the rows behind it; the Issues
  tab lists the profile's warnings. **Load into a change set…** installs and activates the draft
  when its model changed (installing an unchanged one only saves the profile), opens a change set
  named after the file, loads the stored file through the saved profile and opens the review.
  `test:browser:authoring-a5` walks it on both designer models.

### Changed

- Base 0.10 A5c (D105): a relation column onto a relation its record holds one of (many-to-one from
  its side, or one-to-one) is mapped with `replace: true` by the mapping kinds, Map to… and the
  inference, so the next version's changed value switches the record instead of being refused
  `CARDINALITY_VIOLATION`. The dry run's summary counts `deleted` records and `missingRecords`; the
  binding report `missingRecords`.

- Base 0.10 A6b: an operation of a proposal holds when the binding has what it sets, so proposing
  again no longer re-applies a binding a value map was added to (found by the browser runner: the
  name drift's map was dropped and the dry run refused the drifting rows). The editor's marks name
  the proposal that created an element, not the last one naming it. Add a workbook and New from a
  workbook share one workspace field (`WorkspaceField`); a dialog lays two short fields side by side
  (`dialog-pair`); the model pane scrolls a selection made elsewhere into view.
- Base 0.10 A6a: profiling analyzes the staged cells once they are copied in, so the statements over
  them are planned for their real size: the inference of W1 at 10,000 rows took 54.6 s before and
  0.35 s after (profiling unchanged at 6 s). The step answer of the operation, undo, redo and
  application routes is one function (`management/steps.py`).
- Base 0.10 A5b: the editor keeps the selected element selected after a step that changes its key
  (the address used to keep the old key, and the centre lost it). The target list of Move to… is
  shared with Map to… (`TargetList`), the install dialog's release identity with the load
  (`ReleaseIdentityFields`), and the import job's rows table with the dry run's (`JobRowsTable`).
- Base 0.10 A3: D9's interactive dry-run budget (1 s for 10,000 rows, a sample above it) is replaced
  by D67, at the user's decision: every dry run checks the whole file. Measured once: profiling W1 at
  10,000 rows takes 6.3 s, its dry run about 7 s (19,453 items) after the fix and A3a below.
- Base 0.10 A3a: a trial run (an import's or a batch's preview, a dry run) records no audit entry and
  takes no feed position (D72), and relation sets advance in one array statement per thousand sets
  for every write (D73); the trial run of a 10,000-row workbook takes 5.75 s instead of 11.8 s, and
  holds the workspace's write lock that much shorter.

### Fixed

- Base 0.10 A6 (found by A8b's case 10): an element the administrator created again exactly as a
  proposal had made it (a list removed and loaded again) read as still proposed, and was marked
  Proposed and followed by Propose again. A step other than a proposal's that creates an element
  after its proposal now makes it the administrator's, as D92 says. Regression:
  `test_a_rectangle_is_read_as_a_list_on_request` (J34.10, seen failing without the fix).

- Base 0.10 A5, A6 (found by A8a's real-file smoke): a column whose header begins or ends with a
  space could not be mapped in a draft (`unknownElement`), since the draft's sheets kept the spaces
  the import trims. The draft's sheets name a column as the import reads it.
- Base 0.10 A6 extend mode (found by A7's browser runner): a workbook the editor uploads names no
  workspace, and its columns were then compared with no records, so additions to the model matched
  nothing by value from the editor. A file without a workspace is compared with the default
  workspace's records, as its profile job already ran there.

- Import binding (0.9 J2, found by 0.10 A5c's 10,000-row measurement): finding each row's record by
  its key attribute, and a match by attribute, compared every row with every record of the context
  (21.9 s for 10,000 rows into a workspace holding them); they now join on a table of the values a
  key or a match reads, a hash join (the whole binding of W1′ at 10,000 rows: 2.4 s).

- Base 0.10 A6b (reported on a real workbook): a workbook with nothing to propose got the new
  application alone, which left the draft refusing an application without types; now nothing is
  proposed and the inference says why. Load into a change set and Install and activate on a draft that
  does not compile blanked the page (its compilation has no changes); both now say the draft has
  errors, and Load says when nothing is mapped yet. A sheet with a note or small block beside its
  table is now read by its table. A page part failing while rendering shows what failed and a reload
  under the top bar instead of an empty page.
- Base 0.10 A6b, on the user's own workbooks (D99–D103): the proposed model no longer refuses rows
  of its own workbook. A type gets one parent (a further repeated column is a list it refers to),
  optional where rows leave it empty (`setContainment`'s `parent.optional`), and a source reads no
  record from a row holding nothing in its columns. Lists of a GUID and a name are proposed;
  translations are found by their values whatever their headers; a sheet's yes/no columns form one
  set; descriptions in sentences are long text, never a parent; names are written as words, a type
  named after its key column. A second column with an earlier column's header is left out with a
  warning.
- Base 0.10 A6b: New from a workbook offers **A new model**: the workbook's application in a draft
  that starts empty, without the active model's applications ("A new application" adds it to the
  model the draft starts from).
- Base 0.10 A6b: compiling a draft that does not compile sends `changes` empty instead of leaving it
  out, so the answer matches its type in clients and their test fakes. Browser runners fail on any
  uncaught page error or a page part the error boundary replaced, in every page a run opens.

- Binding an import whose profile has a relationship column grew with rows times links: the record
  items looked up each row's required links in a subquery run per row. They are collected once with
  a grouped join; a 10,000-row file binds in 1.4 s instead of 9.3 s.
- `GET /jobs/{id}/rows` serves a dry run's rows too and takes `source` and `code` internally for the
  dry-run rows route; the job list's `kind` filter takes `profile` and `dryRun`.

## [0.10.0-alpha.1] - 2026-10-12

The model designer, released on its own (D14): everything since 0.9.0, Base 0.10 packages A0, N1,
A2, A4a, A4b, A4c and the designer checkpoint T1. Schema language 0.10. The spreadsheet onboarding
line (A3, A5–A8) follows in 0.10.0. One migration since 0.9.0 (`20261011_01`, the draft operation
history); a database of 0.9.0 upgrades on start.

### Added

- Base 0.10 A0 (design, no product code): decisions D1–D10, D17–D21 and A-D5–A-D9 accepted;
  the model authoring API designed in API.md (draft operations and their kinds, history, undo and
  redo, source files and their profiles, the dry-run summary, inferences); ADR-041, model drafts
  change through recorded operations; journeys J33–J35 and their planned routes in the API
  inventory; the synthetic workbooks W1–W3 defined in test terms; the editor mock-up and the W1
  sample approved.
- Base 0.10 N1: schema language 0.10, opened with navigation groups (D1, D22–D27; J33.9). An
  application may declare `navigation.groups` (key, label, collections, `collapsed`); the sidebar
  shows the collections in no group first, then each group as a foldable section whose fold a
  reader's browser remembers, marks a folded group holding the open collection, and opens a group's
  page (`/apps/{app}/groups/{group}`) listing its collections with a search by name. A group naming
  no collection of its application (`INVALID_REFERENCE`), a collection in two groups
  (`INVALID_MODEL`), a group key twice (`DUPLICATE_KEY`) and `navigation` below schema 0.10
  (`INVALID_MODEL`) are refused at their pointers; a 0.9 model is unchanged, with the same hash. The
  browser runner `test:browser:authoring-n1`.
- Base 0.10 N1, at the user's request: on a phone (below 760px) the data-context band is one line
  whose workspace, application (with its tile) and data context (Live, change sets, publications,
  with the line saying what an edit does) each open their choice; the top bar shows no application
  tabs in any area and the drawer no workspace selector. A group page's rows show a chevron and a
  pressed state.
- Base 0.10 A2: model drafts change through recorded operations (ADR-041, D29–D35; J33.1–J33.8,
  J33.12, J08.9). `POST /model-drafts/{id}/operations` applies a request of typed operations all or
  none at `expectedVersion` as one step of the draft's history, answering the new version, the
  entries with their inverses and the compiler's diagnostics (a draft may be invalid between steps).
  34 model-side kinds: names and keys (every reference rewritten; an element a consumer API names is
  refused, D29), the release identity and schema version, applications, object types (with a
  generated table view and detail page, containment by `parent`, D30), split, merge and conversion to
  a list type, attribute types and bindings, relation types and the relations allowed between types,
  views, panels and their lists, navigation groups. A removal takes what exists only for the removed
  element (D31). `GET …/operations` pages the history; `POST …/undo` (a step, or `steps` together)
  and `POST …/redo` apply stored inverses as new steps (D32); a step later steps build on is refused
  `OPERATION_HAS_DEPENDANTS`. A draft-only change of an element of the draft's base release is
  refused `OPERATION_REQUIRES_MIGRATION` with the records, values and relationships it would touch,
  live and in change sets (D33). A whole-model `PATCH` is recorded as one `replaceModel` step;
  installation makes the installed release the draft's base, leaving its version (D17, D34). New
  codes `INVALID_OPERATION`, `OPERATION_REQUIRES_MIGRATION`, `OPERATION_HAS_DEPENDANTS`,
  `NOTHING_TO_UNDO`, `NOTHING_TO_REDO`, `OPERATION_BATCH_TOO_LARGE`; setting
  `MODEL_OPERATION_MAX_ITEMS` (500); migration `20261011_01` (`model_draft_operations`).
- Base 0.10 A4a: the model editor's model pane (D36–D42; J33 in the browser). A draft opens in the
  editor from Settings › Model (**Open in editor**; **New draft** opens it too), full width under
  the top bar: the model pane (applications with their types in their containment tree, navigation
  groups, relation types, attribute types, each marked new, changed or released), the selected
  element with its operations, the relationship matrix, the issues linked to their elements and the
  history in plain words with undo and redo. Every model-side operation is in a menu, through one
  dialog; Move to… moves an attribute or a type, and a drag in the model pane opens it with its
  target. A released element's draft-only change is refused with what it would affect; a step on a
  draft another editor moved on is held and offered again. Install and activate in one confirmed
  step, with the proposed version, the differences and the compatibility. On a phone the panes are
  tabs. `GET /model-drafts/{id}/outline` serves the draft's structure, the marks against the base
  release and the diagnostics with their elements. **New draft** from an empty model now starts a
  document of the newest schema language with a release identity, instead of `{}`. The browser
  runner `test:browser:authoring-a4a`.
- Base 0.10 A4b: the preview and layout editing (D43–D50; J33.10). **Preview** in a type's header
  shows its record page and table in the editor's centre, drawn by the record screen's own renderers
  from the draft before it is installed, over a record read live in a workspace and record chosen in
  the band (or an empty record for a new type); the page's controls are shown and disabled, and
  nothing the preview shows writes. **Edit layout** opens the layout editor over the whole editor,
  marked by its own band with Undo, Redo and **Back to the model editor**: panels moved within and
  between `main` and `side`, hidden or shown, renamed, their columns and sort; fields moved, grouped
  into new field groups and added; a table view's columns, filters and default sort; by menu and
  keyboard, or by dragging with mouse or pen. Each change is one step of the draft. A draft that does
  not compile is not previewed. `GET /model-drafts/{id}/model` answers a draft compiled as
  `GET /model` serves the active model, with its placements; the operations `addDetailPage` and
  `removeDetailPage` give a type without a declared detail page the page a new type gets. The
  browser runner `test:browser:authoring-a4b`.
- Base 0.10 A4c: the consumer API editor (D51–D59; J33.13, J33.14). The editor's left pane has
  **Model** and **Consumer APIs** tabs, ＋ adding within the open one. A consumer API opens with its
  tabs: the exposed types and public names and the related records it serves; its fields with their
  sources (chosen in order from a picklist of what the exposed types and the types above them hold),
  role and default, edited in place (no field name is typed by hand anywhere in the tab: match
  fields, related fields, XREF fields, sort fields, routes and watched outputs are chosen from what
  is valid there); the operations it offers, its lists, XREF match rules
  and custom events; its filters; and two documents with Copy and Download, the **Schema** of the
  message consumers receive and a **Message example**. Six operation kinds change definitions, each
  step with undo: `addConsumerApi` (a starting definition from the exposed types), `removeConsumerApi`
  and four part verbs naming a part by a JSON pointer (`setConsumerApiPart`,
  `insertConsumerApiPart`, `moveConsumerApiPart`, `removeConsumerApiPart`). The outline lists each
  definition with its contract against the active release, shown as "Needs v2" with a step that raises
  the version; the install dialog lists each consumer API's result and activates only when none needs
  a higher version. `GET /model-drafts/{id}/consumer-apis/{consumerApi}` and its `schema.json`,
  `example.json` and `openapi.json` serve a draft's definition and documents before it is installed.
  `setKey` on an element a consumer API names now rewrites the definition instead of refusing (D54,
  replacing A2's D29). Switching XREF off asks first, since its match rules go with it, and stops
  Resolve too. The browser runner `test:browser:authoring-a4c`.
- Base 0.10 T1, the designer checkpoint (D60–D64): US-P05 walked end to end in the browser on both
  designer models by `test:browser:authoring-t1`. An application designed from an empty draft, and
  the active model extended with a consumer API change that needs a higher contract version, are
  each installed, used on the record screen and served by the consumer tier. Each walk is taken once
  by keyboard alone and once by clicking every button. Each step is checked on the server, and the
  run fails on a console error or a failed request. The designer's surfaces (the editor, the matrix,
  its dialogs, history and install dialog, the preview and layout editor, a consumer API's fields and
  schema, the sidebar's groups, a group page, and the phone band, drawer and editor tabs) join the
  accessibility gate in light and dark and the visual gate.

### Fixed

- After a model draft was installed, the editor marked everything the draft had added, and the
  types and applications around it, as changed against the release just installed from it. The
  release holds each element with its defaults written out, and the outline compared it with the
  draft's authored form; marks now compare both in the release's form (0.10 T1, from A4a).
- The preview of a new type's empty record asked the server for the history of a record that does
  not exist (a 404 in the browser); the record page's History panel now reads through the page's
  client, which answers the preview's empty record itself (0.10 T1, from A4b).
- Every dialog's labelled fields: a label stood further from its own control than from the field
  before it; the label now sits right above its control with a clear step to the next field, and a
  dialog's buttons keep a margin from its bottom edge (0.10 A4a).
- `setRelationRule` refused a change of which records a released relationship may choose
  (`candidates`) as needing a migration; it is compatible (0.9 K7) and now applies (0.10 A4a).
- The model editor can remove a relation type that type pairs still use: the pairs and the type go
  in one step (0.10 A4a); every relation, a parent link included, has Remove relation in its menu.
- A relation allowed on a model draft joined a relations panel set up for other records (a
  translations panel sorted by its language) and made the draft invalid; it now joins only a plain
  relations panel or gets its own (0.10 A4a, A2's generated layout).
- Every table's cut-off cell shows its whole value, wrapped, on hover, focus or a long press (0.10
  A4a).
- Every menu (`⋯` and the like): items show hover, may carry a glyph, a second line and a section
  heading (0.10 A4a).
- Supported schema versions are listed oldest first by number (`0.10` after `0.9`), in
  `GET /system`'s `schemaLanguages`, a refusal's `supportedSchemaVersions` and the startup and
  upgrade messages; a text sort would have put `0.10` first (0.10 N1).

## [0.9.0] - 2026-10-11

Base 0.9, integration-grade APIs, and its schema language 0.9. Build acceptance (R) reviewed every
change since 0.8.0 and ran every gate; its fixes are under Fixed (R-F1–R-F28).

### Added

- Base 0.9 J6a: workbooks people fill in (D191–D199; J27.18–J27.21). `people.ownedColumns` lays an
  owned relationship out as a row per record and a column per parent and field (parents holding
  records plus those added; headers naming the parent and the ancestor the records are unique
  within); a filled cell creates the record under its parent, owned by its row's record, an edited
  one updates it under a version claim. Cells naming one record offer an Excel list from a reference
  sheet of the records the relationship may choose (`people.referenceLists`); every cell has a
  border. Import profiles gain `relatedRecord.versionColumn`. The Export dialog's Advanced offers
  Rows or Columns per parent, the parents to add and the fields, and the lists. Browser runner
  `test:browser:j6a`.
- Base 0.9 J6: a workbook for people (D179–D190; J27.15–J27.17). `POST /exports` takes
  `layout: "people"` with `people` (`columns`, `sheets`, `columnFields`) for one type as XLSX: the
  table's columns and labels, typed cells, relation columns as "; " lists of names or a field,
  hidden ID and version, a sheet per chosen relationship (owned records, or relationships with their
  values), the type hues, a frozen, filtered header, and the import profile that reads it on a hidden
  sheet; `422 INVALID_EXPORT_LAYOUT` otherwise. An XLSX imported without a profile is read through
  the profile it carries (`parameters.profile.embedded`). Import profiles gain `key.versionColumn`,
  `key.nameColumn` and a relation binding's `idColumn`, `versionColumn` and `attributes`. The Export
  dialog offers For people with an Advanced section; the import page names the workbook; the job
  reads "Workbook for people". Browser runner `test:browser:j6`.
- Base 0.9 K7: which records a relationship may choose (D168–D178; J13.9, J13.10, J03.9, J10.11,
  J01.11). A binding may carry `candidates`, criteria for the records at its `from` end, its `to`
  end or both, over their name, any non-JSON attribute, and an ancestor's name or attribute
  (`ancestor:<type>.<field>`), with the list filter's operators. Every picker for the relationship
  offers only those and says so; a record that does not meet its own end is not offered the
  relationship, with the reason. The per-type list takes `candidateFor` with `anchorTypeKey`; the
  relationship view's and matrix's candidates apply the criteria. A new relationship outside them is
  refused with `422 RELATION_CANDIDATE_REFUSED` on every write path (batches check a chunk's targets
  in one statement per restricted end); relationships made before are kept. The model-aware query
  takes `ancestor:<type>.<field>` criteria. Browser runner `test:browser:k7`.
- Base 0.9 K6a: `GET /relations/held`, the records a set of records holds through one relationship,
  each with how many of them hold it (D165; J32.7), which Change relationships' Remove lists.
- Base 0.9 K6: filtering a list by its records' relationships (D153–D159; J01.10, J32.6, J27.6,
  J08.12). A table view's `filterFields` may name `related:<key>`; its Filter menu then keeps the
  records related to any of chosen records (picked with the record search), to none or to any, the
  chip naming the records, also after a reload. The per-type list takes
  `filter.related:<key>.eq=<record ID>` (repeatable) and `.isNull=true|false` for any relationship
  the type has, built by Q3's relationship hop in every context; `INVALID_FILTER` otherwise. The
  selection's "all matching", the bulk actions and Export carry it. The starter is content release
  0.9.5 with these filters on system values and master values. Browser runner `test:browser:k6`.

### Fixed

Found by the 0.9 release review (R step 0, D200):

- A workspace deleted and created again under its key could never be written: its old feed entries
  kept their positions. Deleting a workspace now takes its feed with it: its audit entries stay
  as history without a feed position, and its idempotency keys go (R-F1, D208).
- Activating a release could deadlock with a webhook delivery, a subscription change, or a write of
  an attribute whose `unique` the release changes. Activation now locks the active subscriptions,
  and when `unique` changes the unique values, before the runtime state (R-F2, R-F3).
- A relationship's candidate criteria (K7) treated a record a batch had just created without a value
  as meeting `isNull: false` (R-F4).
- An import column with `replace: true` whose cell was empty left the relationships in place; the
  set is now replaced with none, as in a workbook for people whose relation cell is emptied (R-F5).
- A filter on `createdAt`, `updatedAt` or a date-time attribute takes a day (`YYYY-MM-DD`), compared
  by the whole day in UTC; the collection's date filter sent one and was refused (R-F6).
- A workbook for people whose type or relationship name held `&` or `<` was reported damaged by
  Excel: the list rules are now escaped (R-F7).
- A webhook's `stateAt` and its object are read in one snapshot, as the pull feed reads them (R-F8).
- A preview past its retention was confirmed until the hourly sweep marked it; it is now refused
  `410 JOB_EXPIRED`, and the sweep skips a job a confirmation holds (R-F9).
- A file sweep could remove an import's file before its job was committed; a file of no job is
  kept for ten minutes (R-F10).
- One workspace whose events cannot be derived no longer holds up the others (R-F11).
- An atomic job's chunk, a preview and an export's set statements renew the job's lease while they
  run, so a second process never takes a running job (R-F12).
- The pull feed's `ETag` changes with live data as well as with derived events (R-F13).
- Three route descriptions named error codes in lower case (R-F14).
- An `ancestor:<type>.<field>` value shows the ancestor of that type nearest the root everywhere:
  the workbook for people and consumer API projections now agree with lists and Q3 (R-F15, R-F16,
  D209).
- New webhook offered only the first 100 active workspaces (R-F19).
- Three colours were written outside the tokens, skipping the dark theme's shadows (R-F20).
- Each consumer API's document states the engine's own read limits rather than copies (R-F21).

Found by the 0.9 release's browser runners (R step 3):

- In a relation matrix cell, Create pressed before the cell's containers had loaded did nothing and
  said nothing: once a single container loaded, the notice that none was chosen was not shown. The
  button now waits for the containers (R-F22).

Found by the 0.9 release's deletion timing (R step 8, D124):

- Deleting a large selection, about 100,000 records, could not finish: three statements stopped
  scaling once a run's IDs no longer fit in PostgreSQL's `work_mem`. The run's relationships are
  found through its joins, not `IN (run) OR IN (run)` (R-F23); a change set's matrix walk leaves
  out the rows the change set replaces with `NOT EXISTS`, not `NOT IN` (R-F25); and reading the
  records of a change set takes any number of IDs, a statement at a time, where more than about
  32,000 failed with "number of parameters must be between 0 and 65535" (R-F24). In a change set
  the closure's walk finds a record's required owned records by their keys, where it read every
  record of their type for each record reached (R-F26), and the matrix states' upkeep no longer
  walks the cells under the records the change set just deleted (R-F27). Deleting 100,000 records
  now previews in 49 s live and in a change set, and runs in a change set in 51 s.
- A query's or a list's expansion in a publication counted its total once per row of its page:
  20,000 related records expanded took 103 ms, now 68 ms (R-F28).
- A filter or sort naming an attribute the type does not bind answered `invalid_filter` and
  `invalid_sort` in lower case; they are `INVALID_FILTER` and `INVALID_SORT` (found in 0.9 K6).
- An export with a `related` criterion failed in the worker (`INVALID_QUERY`, "A related criterion
  names no field, operator or value"): the stored request carries every field, null ones too, and
  the check counted a null value as named. It now checks values (found in 0.9 K6).

### Changed

- The record tree's leftovers from UA9's flat scrolling are removed: the windowed version kept in
  comments, the unused wheel routing (`useTreeWheel`, `treeWheel`) and the group frame's glow
  (R-F17). Documentation and comments name no example-model content (R-F18, D210).
- 0.9 R: the accessibility and visual gates cover every 0.9 surface approved by screenshot (D202),
  light and dark, on a harness of their own with webhooks on: Settings › Integration, a webhook's
  configuration and deliveries, relation columns, the filter editor, the selection bar, the three
  bulk dialogs, exporting and importing with their notifications and job pages (36 new baselines).
  34 baselines were re-recorded for changes delivered since UA7 (UA8, UA9, K1, K6a, J1u, J4, U4,
  U5). The browser runners that had drifted from later packages were brought up to date, and the
  comprehensive command set names all 38. `volume_baseline.py --only-deletion` times deleting about
  100,000 records (D124).
- Schema 0.9 is the released schema language from 0.9.0 (D206): APPLICATION_MODEL describes it as
  such, with what it adds to 0.8 and how a 0.8 document using it is refused.

- Base 0.9 K6a: collection filters redesigned (D160–D164): active filters as pills, ＋ Filter's field
  menu, one compact editor per field type, a bottom sheet with "Show N records" on phones. The
  selection bar's actions are icon buttons with an indigo tint on the light theme, and Change values
  and Change relationships were redesigned (D166, D167): Change values as cards per field, Change
  relationships with pills, a segmented action and a checklist whose Remove lists only what the
  selection holds. D133 revised by D167: Add and Remove are separate actions.
- D142 revised (0.9 K6a): the per-type list's `expand` takes as many keys as the type has
  relationships, each once; the fixed maximum of 5 is gone.
- Base 0.9 K5b: a relation column shows as many related records as its width holds (D143 revised by
  the user): whole chips, then "+N more" for the rest, and no "+N more" when they all fit; resizing a
  column shows more or fewer at once without reading the list again. Lists ask for up to 20 related
  records per row (`expandLimit=20`); a 20-row page costs 11–34 ms on the 0.1 volume fixture.

### Added

- Base 0.9 K5a: a field of the related records in a relation column (D148–D152; J01.9, J08.12).
  `related:<key>.<field>` shows each related record's value of a field instead of its name: `name`,
  an attribute the types at the other end bind, or `ancestor:<type>.<field>`, written as in a
  consumer API definition ("Has translation · Language code": `ar` `cs` `en` +4 more). A record
  without a value shows "—"; such a column never sorts. `expand` takes the same text; the entry names
  its `field` and each record carries the value beside its name (`INVALID_EXPAND` for a field that
  does not resolve). Q3's answers are unchanged.

- Base 0.9 K5: relation columns (D140–D147; J01.8, J08.12). A table view's columns, and a children
  or table panel's, may name `related:<key>` in schema 0.9, `<key>` a relation type's key (read
  outgoing) or reverse key (read incoming): each row shows its first three related records as chips
  in name order, then "+N more", kept on one line; a column hidden in the table's display settings is
  not read. Where a row holds at most one (one binding, whose listed end holds one), the column sorts
  by the related name, rows without one last; elsewhere it is refused in `sortFields`, and it is never
  a filter. `GET /objects/{objectTypeKey}` takes `expand` (repeatable, at most 5) and `expandLimit`
  (1–20, default 3), answering each item's `expanded` in Q3's shape, `422 INVALID_EXPAND` otherwise,
  and `sort=related:<key>`; the list's response is now `TypedObjectPage` (`QueryObject` items). The
  starter is content release 0.9.4 with relation columns on system values and master values. Q3's
  expansions read a page in one `LATERAL` statement per expansion (a page of 100 with two keys: 45 ms
  live, was 611 ms). Browser runner `test:browser:k5`.

- Base 0.9 UA9: the record tree scrolled as one list, several records selected and moved together
  (U-D21–U-D28; J14.9). The sidebar's tree and the hierarchy lens scroll with the sidebar or the
  page, their type groups start folded and open like records, and a long group reads more as its
  end comes into view (**Show earlier records** above a group opened partway down; Ctrl+Home and
  Ctrl+End within a group). Records are selected with Cmd/Ctrl, Shift, Ctrl+Space and Shift+arrows,
  without changing the page, and dragged together onto a new parent, in the sidebar as well as the
  lens, or moved with **Move to…**: one confirmation, one atomic batch (`update` items with `parent`
  and each record's version, live or in the change set). A target that cannot take one refuses them
  all, naming it; several records are never moved where their type would change. Browser runner
  `test:browser:ua9`.

- Base 0.9 UA8: actions in place on the record (U-D15–U-D20; J02.6). A record's header edits its
  title (usually the name) and subtitle in place, as its details fields are, on the full page and in
  the inspector, and offers Add for an empty subtitle; one component, `EditableField`, draws and
  edits a field in both places. The header's Edit record button is gone; **Edit record** (was Edit
  all fields) is the first item of the record's ⋯ menu, also on every collection row. A relationship
  row's actions are icon buttons with tooltips (change to another record, edit values, delete,
  `ui/IconButton`), and a row managed through the parent or required shows a lock with the reason.
  Browser runner `test:browser:ua8`.

- Base 0.9 K3a: many-to-one relationships (D136–D139; J08.11, J11.12, J32.5). A binding may declare
  `"cardinality": "many-to-one"` in schema 0.9: each `from` record holds at most one relationship of
  it, and a `to` record serves any number. A second one is `409 CARDINALITY_VIOLATION` on every write
  path; a release tightening a binding to it needs a migration while a `from` record holds more than
  one (`RELATION_CARDINALITY_VIOLATED` at the binding's `cardinality`, with the count). It cannot be
  `required` (D137, in TODO), and is refused in schema 0.8. Which end holds one is one rule in the
  engine and one in the browser (D138); the relation matrix, the mapping grid's candidates and the
  consumer API read it, so a field `via` a many-to-one binding answers one object or `null`. On a
  record, where it may hold only one relationship of a kind, its Relationships panel offers **Set**
  while it holds none and **Change** and **Delete** on the one it holds (D139); Change replaces it in
  one write through the mapping replacement, claiming the set as read, and is refused if the
  relationship changed after the list was read. The selection's Change relationships… offers Set to
  and Clear from that side. The example model 0.9.1 uses it (its `rdm` consumer API at contract
  version 2).

- Base 0.9 K3: changing the relationships of a selection, and relationships named by their ends
  (D127–D135; J11.10, J11.11, J32.4). A batch item **`ensureNoRelation`** (`relationTypeKey`,
  `from`, `to`, optional `expectedVersion`) deletes the relationship of that type joining the two
  records as `DELETE /relations/{id}` does, with its refusals, or answers `unchanged` when there is
  none, so a removal sent again changes nothing (D129). A `replaceRelationSet` in a preview needs no
  `expectedRelationSetVersion`: its outcome names the version it found
  (`previousRelationSetVersion`, also in its refusals' details), and confirming carries it into the
  stored item, so execution refuses `RELATION_SET_VERSION_CONFLICT` only the sets changed since the
  preview (D130). In the browser, **Change relationships…** in the selection bar offers every
  relationship the model allows the type, in both directions, except containment and required
  ownership (D127), with the actions its cardinality allows: Add and Remove together, Replace with,
  Set to, Clear; never Remove or Clear on a required one (D128, D133). The other records are chosen
  with the record picker (`ui/RecordListField`); the dialog states how many changes the selection
  makes and explains a change over `BACKGROUND_JOB_MAX_ITEMS`, or a replacement over
  `JOB_PREVIEW_MAX_ITEMS`, before sending (D131, D134); relationship values are not edited (D132,
  after 1.0 in TODO). A batch's job page says relationship outcomes in a relationship's words.
  Relation columns in collections are K5 (D135).

- Base 0.9 K2b: deleting a selection, and cascading batch delete items (D120–D126; J11.6, J32.3;
  PG-D18). A `delete` item takes `cascade` and `deletionPreviewToken` as the single `DELETE` does:
  without `cascade` a record with dependants is refused `OBJECT_HAS_DEPENDANTS` with its `impact`;
  with it the item deletes the record with its dependants under the impact its token confirms. A
  batch preview gives each delete item's `impact` (records by type, relationships, those reaching
  records that stay, and the token) and the preview's `deletion` totals; confirming carries each
  token into the stored item, so execution deletes exactly what was previewed and refuses only an
  item whose impact changed (`DELETION_PREVIEW_CHANGED`). Items are decided in order: a record an
  earlier item of the job deleted answers `unchanged` with `deletedWithItem` (D122). Deletion is one
  path for the single `DELETE` and a batch's delete items, live and in a change set, as set
  statements in PostgreSQL whatever the impact's size or depth (D123); its token is the same from
  either. In the browser, **Delete…** in the selection bar previews what deleting removes (the
  selected records, those going with them by type, the relationships) before a destructive
  **Delete N records** naming the whole (D126); the deleted records leave the selection, the refused
  ones stay for Preview again, all matching is cleared (D125). A batch's job page shows what
  deleting removes and each delete's impact.

- Base 0.9 K2: changing values of a selection, and previewing a batch (D112–D119). `POST /batches`
  takes `stage: "preview"` for a background batch (inline is refused): its items run without
  writing anything, as an import's preview runs, and the job waits in `awaiting_confirmation` with
  `preview` (no `rows`); `POST /jobs/{id}/confirm` runs the stored items as an execution, which is
  authoritative. In the browser, **Change values…** in the selection bar sets or clears fields of
  the selected records (not read-only or hidden ones; a required one is never cleared), all or
  nothing up to `atomicJobMaxItems` or the records that can change; "all matching" is read with
  progress and Stop; the preview's counts and refused records, each openable, come before Apply;
  the result, Preview again and the selection keeping the versions the change left (D118) follow.
  A batch's job page lists its items' outcomes, linked to their records, and applies or cancels a
  waiting preview. Leaving the dialog before Apply (Back, Cancel, ✕, Escape, a click outside)
  cancels the preview; View job keeps it waiting for its page (D115 amended). Every change is a
  previewed background job (D114, amending D104); deleting a selection moves to K2b (D116).

- Base 0.9 K1: selecting records in a collection (D102–D111). Where the data can be written and jobs
  can be created, a table view has a checkbox column: rows by hand, a Shift range over the loaded
  rows (pointer or Shift+Space), the loaded rows from the header checkbox, then **Select all N
  matching**, also with Cmd+A (Ctrl+A) in the table; a row unchecked under all matching stays an
  exception. A bar above the table states the selection and clears it; a polite status region
  announces each count. A selection over `backgroundJobMaxItems` is refused with an explanation
  naming the count, the limit, `BACKGROUND_JOB_MAX_ITEMS` and what to do. Sorting, scrolling and
  opening records keep it; a new search, filter, scope or data context clears it. No writes yet
  (K2, K3); no backend or contract change.

- Base 0.9 J5: another workspace's export loads as this workspace's own records (D96–D101).
  `otherWorkspaceIds: "counterparts"` on `POST /imports` and `POST /batches` makes an ID held by
  another workspace's record stand for its counterpart here, whose ID is derived from the original
  ID and the workspace key (a name-based UUID in a documented namespace, marked as version 4); the
  same file sent again finds what it created, types load file by file, a change set takes the live
  IDs, and a workspace's own IDs and free IDs are used as given. Every record ID an item names is
  translated, a profile's `matchBy: {"field": "id"}` too; relationship IDs are not. The file's
  versions are ignored on counterparts (`onExisting` decides); outcomes name `sourceId`; the
  notice reads `RECORD_IDS_AS_COUNTERPARTS`; a reference to a counterpart not loaded yet says to load
  its file first. The import dialog offers the choice, loading them by default. Amends D49.

- Base 0.9 J4a: an import says why rows cannot load when the file is another workspace's export.
  Record IDs are unique across the instance, so such a file loads only into the workspace it came
  from (D49); until now every row was refused with no reason a user could act on. The job carries
  `notices` once bound (`RECORD_IDS_OF_ANOTHER_WORKSPACE`, with the workspace and the rows),
  `OBJECT_ALREADY_EXISTS` names the workspace holding the ID (`details.workspaceKey`, live and in a
  change set), and `REFERENCE_NOT_FOUND` names what the reference is for and that workspace. The
  import's page shows the notices above the preview, and a row's reasons wrap instead of being cut
  off. Loading another workspace's export into a workspace is planned separately.

- Base 0.9 J4: the import screen (SC-10 in the browser, D89–D95). **Import** on a collection page
  that can be written loads into its data; **New import** on Settings › Jobs and feed chooses a
  workspace and its live data or a change set. The dialog takes a file, a stored profile (one no
  longer valid listed and not choosable, a keyless one warned) or none, the policy, and whether
  records the file finds are updated (by default with a profile, not without one, D92); it always
  previews (D90) and opens the import's page at once (D91). The job page of an import shows the
  preview with **Load the file** and **Cancel import**, the refused rows paged with every failing cell
  and its column, the binding report per source and column, then the result and how to load refused
  rows (D94); a refused confirmation keeps the preview waiting. Notifications say Preview ready with
  Review, and none shows while the job's own page is open; a waiting preview's stream is closed until
  it is confirmed. A collection reloads after an import this tab started loaded into it. Jobs and
  feed's limits list the import file size and preview items. `ui/FileField` is the one file input
  (the model draft dialog uses it). No backend or contract change. New runner `test:browser:j4`.

- Base 0.9 C18: consumer API definitions written for readers, as schema 0.9 (CONSUMER_API
  C-D132–C-D141). A definition names what it `exposes` (public names default to the key in
  PascalCase), the `operations` it offers (`objects`, `xref`, `resolve`, `lists`, `events`: listed
  means offered), `object.fields` with roles, `related` blocks by a relation's `key` or
  `reverseKey` (role fields may stand anywhere and are output first), `operations.xref.matchOn` and
  `alsoMatchThrough` (`field: "code"` for each code source), `filters` with one verb each (`byType`, `under`, `linkedTo`, `onRelated`), lists `within`
  a filter, events `perType` or `custom` (watching outputs and `related` blocks), and optional descriptions carried into the OpenAPI
  document. Every reader works on one internal form, so for a definition offering every operation
  nothing a consumer reads changes. An operation not offered answers `404 OPERATION_NOT_OFFERED`
  and leaves the OpenAPI document; dropping one needs a new `contractVersion`. Mistakes are refused at
  the pointer the author wrote. `GET /api/v1/model/consumer-apis/{consumerApi}` answers a definition
  with every default written out, for 0.8 and 0.9 releases; the Webhooks page reads it. Install,
  draft compile and `POST /model-validations` refuse a new schema 0.8 document that declares
  `consumerApis` (`UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`), and startup refuses such a file
  named by `RDM_MODEL_PATH`; stored 0.8 releases read and
  activate as stored. The starter is content release 0.9.3 and the example model
  0.9.0, both on schema 0.9.

- Base 0.9 J3: import preview and confirmation. `POST /api/v1/imports` takes `stage: "preview"`:
  the file is bound, its first `IMPORT_PREVIEW_MAX_ITEMS` (10,000) items run independently against
  the data in a transaction rolled back whole, and the job waits in `awaiting_confirmation` with
  `preview` (coverage `complete` or `sample`, items and rows covered, counts by action, the result
  under the request's policy) (D80, D82, D83). `POST /api/v1/jobs/{jobId}/confirm` queues it to
  bind the stored file again and execute (D81); it is idempotent, checks the context again and
  refuses with `409 JOB_NOT_AWAITING_CONFIRMATION` or `410 JOB_EXPIRED`; cancel ends a waiting
  preview at once and retention expires it (D87). Every import carries `bindingReport` per source
  and column (D86); `GET /api/v1/jobs/{jobId}/rows` reads its outcomes by row and `/items` takes
  `ref=` (D84); a row refusal lists every failing cell in `details.cells` (D85). Revision
  `20261007_08` adds `jobs.report`, `jobs.confirmed_at` and the source and row of inputs and
  outcomes; `integrationJobs.limits.importPreviewMaxItems` reports the setting.
- Base 0.9 J2a: the database holds unique attribute values. `unique_attribute_values` keeps each
  live value of an attribute the active release declares `unique` once per workspace, keyed by the
  SHA-256 of its canonical JSON under a deferred unique constraint (D75, D77); PostgreSQL triggers
  on `attribute_values` and `model_runtime_state` keep it, so it follows every write and every
  activation (D76). A write that wrote a duplicate past the rule is refused at its end with the
  rule's `409 DUPLICATE_ATTRIBUTE_VALUE`, and at commit by the database; values handed between
  records within one batch or one publish pass. Live data only (D78). Revision `20261007_07` adds
  the table and fills it from the stored values. No API change.
- Base 0.9 J2: imports. Import profiles (`/api/v1/import-profiles`: create, read, list, replace at a
  version, delete; instance-wide, D65) say how a file's sheets and columns become records and
  relationships, checked against the model with every problem at its JSON pointer and read as no
  longer valid when a release breaks them. `POST /api/v1/imports` takes a file and its request as
  `multipart/form-data` and queues a job of kind `import`: XLSX or CSV through a profile, or JSON
  Lines batch items, or an export's CSV or XLSX tables without one (the records table gains
  `applicationKey`, D71). The worker binds the file in one transaction, converting values through
  the attribute registry and resolving keys, matches (also to records the same file creates),
  hierarchy order and related records (D70) by set statements in PostgreSQL (D68); rejected rows
  are the job's first outcomes, named `{sheet}!{row}` with their column, and the items then run as a
  background batch (D72, D73). Rows repeating a key load as one record when they agree and are all
  refused otherwise (D69). `IMPORT_MAX_BYTES` (200 MB) caps a file. Revision `20261007_06` adds
  `import_profiles`. openpyxl becomes a runtime dependency and `python-multipart` is added (D67).
- Base 0.9 J1u: export in the browser and pushed job notifications. **Export** on a collection page
  opens a dialog prefilled with the page's type, data context, filters and parent narrowing (the
  search is not carried); **New export** on Settings › Integration › Jobs and feed exports any types
  of a workspace. A notification says an export started, and another when it ends: completed with
  Download and View job, failed or cancelled with View job. Each job has its own page
  (`/settings/jobs/{jobId}`) with its state, progress, error, Cancel and, for an export, the file's
  facts and Download. `GET /api/v1/jobs/{jobId}/events` streams a job (server-sent events) at once and
  after each committed change until it ends; a trigger on `jobs` (revision `20261007_05`) notifies
  the engine at commit, so nothing is polled (D57–D63).
- Base 0.9 J1: export jobs. `POST /api/v1/exports` exports a stated scope of one workspace (live, a
  change set or a publication; object types each with their own criteria, a subtree, `asOf`,
  relationships `none`, `withinScope` or `all`) as JSON Lines, CSV or XLSX, in the background from
  one database snapshot. The job's new `output` field states what the file holds (counts per type,
  context, the feed position it equals, model release, format, size, SHA-256), and
  `GET /api/v1/jobs/{jobId}/output` serves the file only once the job is completed. JSON Lines holds
  `upsert` and `ensureRelation` batch items with each record's version, so the file sent back as a
  batch changes nothing; CSV and XLSX share one table layout (D49–D56). Exports run on a worker of
  their own. New setting `JOB_FILE_DIR` (default `var/job-files`); revision `20261007_04` adds
  `jobs.output`. The feed's `410 FEED_POSITION_EXPIRED` names the export route beside the
  publication (`details.export`).
- The example model 0.8.0 declares events on its consumer APIs: one per
  exposed object type (`<type>-changed`), each for
  created, updated and deleted, with no watch, so any change to the object's output counts. The
  contract versions stay, as adding events is compatible.
- Webhooks › Deliveries: an event's object ID opens its record, in the webhook's workspace and the
  first application showing that type (none for a deleted record).
- Base 0.9 U5a revision: resend a delivered event by hand. `POST
  /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}/resend` sends one event of a request
  again exactly as it was sent (a notice as it was), alone in a new request with the same `eventId`
  and the header `RDM-Redelivery: manual`; once, during the call, on any subscription; the new
  request names the one it repeats (`resendOf`). Revision `20261007_02`. In Webhooks › Deliveries,
  the event's dialog has **Resend**, asking first when the event was already delivered. The edit,
  suspend and delete buttons are on the Configuration tab only.
- Base 0.9 U5a: webhook names and the delivery log.
  - A subscription has a `name` (required on create, editable; existing ones are named after their
    URL's host and path). Renaming alone keeps a batch being retried.
  - Every request the dispatcher sends is logged with its events, the body as sent and each
    attempt's start, duration, status code or error and up to 4 KiB of the answer:
    `GET /api/v1/consumer-subscriptions/{id}/deliveries` (a row per event, newest first, narrowed
    by status) and `…/deliveries/{deliveryId}`. Kept for `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`
    (7, in capabilities); a pending batch longer; deleted with its subscription. Revision
    `20261007_01`.
  - The Webhooks page: the new-webhook dialog rebuilt in sections, with events as all or a chosen
    few (a searchable list, chosen ones as chips) and filters added from a menu, their values as
    chips; the webhook's page has **Configuration** and **Deliveries** tabs above its name; an
    event opens with its attempts and the request and response bodies as coloured JSON.
- Base 0.9 U5: Settings › Integration › **Webhooks**. Subscribe a receiver to a consumer API's
  events from the page: the consumer API and workspace, the events (each with what it covers), the
  URL (the allowed hosts named), filters per declared parameter, payload and delivery mode; a
  refusal is shown at its field. The signing key is shown once after creating. Subscriptions are
  listed with Active, Retrying or Suspended beside the selected one, which shows the last delivery,
  a failing batch's attempts, receiver answer and next attempt, and when suspended the reason, its
  details and what fixes it. Edit, suspend, resume (from the first event not acknowledged, or with
  `reset`; a refusal lists what to edit, expired events choose the reset) and delete. With
  subscriptions off, the page names the setting. No API change.
  - A workspace that cannot be deleted because of its webhooks lists them, each linked to its page.
  - `ui/CatalogueLayout` and `CatalogueEntry` replace the catalogue markup Workspaces and Model each
    had; Webhooks uses them too.

- Base 0.9 U4: Settings › Integration. **Consumer APIs** shows each consumer API of the active
  release, read only: its name in the address, contract version, base URL and OpenAPI document
  (with copy buttons), its source in the API reference, exposed types under their public names,
  lists and events, and the release that declares it. **Jobs and feed** lists the jobs of every
  workspace newest first with state, result and counts, cancels a queued or running job after
  confirming, and shows the batch, job and feed limits. **API reference** lists the `/docs` sources
  with their versions and documents. No API change; API.md states the `?api=` slug's form.
  - The starter model is content release 0.9.2: it declares a consumer API `rdm` (domains,
    codelists and values; three lists; the event `values-changed`), so a fresh installation has one
    (U-D5). An existing database installs it beside 0.9.0 without activating it.
  - `ui/SettingsTable`, the shared job-limits list and settings read hook replace Deployment's own
    copies; `CopyValue` can link its value; `ConfirmDialog` takes a label for its dismiss button.

- Base 0.9 U3: the Settings area. `/settings` has its own frame without workspace or data context:
  a top bar reading "{product} / Settings" with **Back to applications** (to the last application
  route of the session) and the account, the settings navigation in the rail (in the navigation
  drawer below 760px, opened from a **Settings: {page}** bar), and pages as wide as the application
  pages, built from new `ui/` components (`SettingsLayout`, `Section`, `DescriptionList`,
  `FormField`, `EmptyState`, `Skeleton`, `Toast`).
  - **About**: engine and management API version, schema languages, the active model release and
    when it was activated, the database revision. **Deployment**: the capability groups on or off
    with their settings and limits, then every setting with its value, default, source and what it
    controls; secrets only as Set or Not set, the cursor-key warning when it is ephemeral. Read only:
    settings change with a restart (U-D2). **Appearance**: theme and the default table density for
    this browser; a view's own density (now with **Default**) overrides it.
  - **Workspaces** and **Model** moved under Administration, as the screens they were: the catalogue
    beside the selected workspace, release or draft, each at its own address (U-D10 as revised).
    `/models` and `/workspaces` addresses redirect. Confirmations are toasts; a workspace with
    webhook subscriptions says why it cannot be deleted.
  - The application top bar has a **Settings** link and an **Account** popover (theme, **All
    settings**) in place of Models, Workspaces, the model version and the settings popover. Only
    built pages are listed (U-D11). The workspace switcher is back at the top of the rail, where it
    was before U2.
  - `GET /api/v1/system` answers the same facts. Settings come from a catalogue in `config.py` (group,
    description, secret) held against `Settings` and OPERATIONS by a unit test; the engine version
    has one home, `config.ENGINE_VERSION`. Journey J31 (operator: check what a deployment runs).
  - Planned next: the **Atlas** visual direction (ADR-040), today's shell with a colour for every
    kind of record, applied to every surface in UA before U4 and U5.

- Base 0.9 C13: the events' acceptance. The CONSUMER_API event scenarios are walked end to end,
  from a write through the deriver and the dispatcher to a receiver, on two generated models: a
  publish delivered in batches exactly as the pull feed has it, work that never reaches live data
  (a rolled-back batch, a refused write, a validated and discarded change set) sending nothing,
  filters scoping deliveries as the lists do, a reset and re-sync after expired events missing
  nothing, and a running application delivering on its own. Webhook delivery has a volume budget
  (C-D113): the dispatcher's claim, a delivered batch and a coalesced round hold their statements
  as the data grows, with full-volume figures in POSTGRESQL_BUDGETS §7. CONSUMER_API, OPERATIONS
  and the journeys now say that a filtered subscription is not told when a record leaves its
  filter's scope, and how a receiver handles it (C-D114).

- Base 0.9 C12: webhook delivery. While `CONSUMER_SUBSCRIPTIONS_ENABLED` is on, a dispatcher thread
  in the API process sends each active subscription's events to its URL, in position order, one
  request at a time per subscription.
  - Per change: up to 100 events and at most 1 MiB of body per request, an event alone over 1 MiB
    sent alone (C-D104); each event as the pull feed has it, with the object as get by ID answers
    it (`full`) or without it (`identity`). Coalesced: one notice per event once the newest
    matching event is `debounceSeconds` old, or the oldest 10 minutes old (C-D105).
  - Every request is signed: `RDM-Signature: sha256=<hex>`, the HMAC-SHA256 of
    `"{RDM-Timestamp}.{body}"` keyed with the subscription's `signingSecret`; `RDM-Delivery-Id`
    stays the same on every retry of a batch (C-D12).
  - Any `2xx` acknowledges. A failed batch (another status, a redirect, which is never followed, no
    answer in 10 s, a connection or TLS failure, a refused address) is retried with the same events
    after 10 s, 30 s, 1, 2, 5, 10 and 30 min, then hourly, each ±20 %, for 24 hours from its first
    failure; then the subscription is suspended `DELIVERY_FAILED` (C-D103). Nothing later is sent
    past a failing batch.
  - The host is resolved at each attempt and the request goes to the address checked: link-local
    addresses are always refused, loopback ones unless the URL names a loopback host (C-D107).
  - A subscription answers `delivery`: `lastDeliveredAt`, and `pending` while a batch fails, with
    its attempts, first failure, last error and next attempt; delivery never changes `version`
    (C-D108). `GET /capabilities` reports the limits in `consumerSubscriptions.delivery`.
  - The dispatcher also suspends a subscription whose host left the allowlist (`HOST_NOT_ALLOWED`),
    one with a filter value no record matches any longer, before sending (`FILTER_MATCHES_NOTHING`,
    C-D109), and one whose next events expired (`EVENTS_EXPIRED`, new, C-D110).
  - Several processes share delivery through a 60 s lease per subscription (C-D106).
  - Migration `20261006_03` adds the delivery state to `consumer_subscriptions`.

- Base 0.9 U2: the UI foundation and the shell (ADR-039, Direction B "Open").
  - Design tokens are in three layers in `styles/tokens.css`: primitives, semantic roles (dark mode
    redefines only these) and component tokens.
  - A contrast test holds every text pair to WCAG AA, and control borders, focus and state
    markers to 3:1 (U-D9).
  - Instrument Sans and JetBrains Mono are bundled and served with the UI (OFL-1.1).
  - A top bar holds the workspace switcher, the applications as underlined tabs, and Settings.
  - A data-context band names the data in view: a green Live pill, an amber band in a change set
    with its Review, Validate and Publish actions, and a violet band in a publication.
  - `ui/PageHeader` now draws all ten page headers; there are also `ui/StatusPill` and `ui/Card`.
  - Every screen takes the new colours and type through the older token names, kept as aliases
    until U6 (U-D7). All visual baselines were re-recorded, and `change-set-editing-dark` was added.

- Base 0.9 C11: webhook subscriptions. With `CONSUMER_SUBSCRIPTIONS_ENABLED` (off by default), an
  operator manages subscriptions at `/api/v1/consumer-subscriptions`: create, list, read, edit with
  `expectedVersion`, suspend, resume and delete. A subscription names a consumer API, a workspace,
  some of its events, filters in the definition's parameters, an HTTPS URL on a host in
  `CONSUMER_WEBHOOK_ALLOWED_HOSTS`, `perChange` or `coalesced` delivery and the `full` or `identity`
  payload. Each filter value must match a record (C-D100). It starts after the feed's head, or after
  an earlier `startAfter` (C-D97). Its signing key is shown once and stored sealed (AES-256-GCM)
  under `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup requires with the capability on;
  `python -m app.cli.generate_key` makes one (C-D96). A subscription is `active` or `suspended`
  with a reason (C-D98). Activating a release that drops what it names suspends it
  `MODEL_CHANGED`, one that raises the contract version `CONTRACT_VERSION_CHANGED`, and retiring
  its workspace `WORKSPACE_RETIRED` (C-D99). A resume checks it again and, after unacknowledged
  events expired, needs `acknowledgeLoss` (C-D93). A workspace with subscriptions cannot be
  deleted (`deleteBlockedBy: subscribed`). `GET /capabilities` gains `consumerSubscriptions`. New
  codes: `FILTER_MATCHES_NOTHING`, `INVALID_WEBHOOK_URL`, `WEBHOOK_HOST_NOT_ALLOWED`,
  `SUBSCRIPTION_NOT_FOUND`, `SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED`,
  `SUBSCRIPTION_NEEDS_EDIT`, `WORKSPACE_HAS_SUBSCRIPTIONS`. Migration `20261006_02`. Nothing is
  delivered yet (C12).

- Base 0.9 C10: consumer events and the pull feed. After a live write commits, a deriver thread in
  the API process turns the workspace's feed entries into the events each consumer API declares,
  without the write waiting: `created`, `updated` naming the watched outputs that changed (also for
  a change to a record the object shows: its parent, an ancestor's name, a projected record, a
  projection's items) and `deleted`; a type change as seen from each event (C-D82, C-D83, C-D87).
  `GET /api/consumer/{consumerApi}/v{contractVersion}/events` reads them in position order from
  `after` or a lasting `cursor`, with `caughtUp`, narrowed by `event` and the definition's
  parameters (C-D90, C-D91); `payload=full` (default) carries each object as get by ID answers it,
  labelled `stateAt`, `payload=identity` leaves it out (C-D7 revised). Every event of the API is
  served, each naming its contract version (C-D88). Events expire with the change feed
  (`410 EVENTS_EXPIRED` naming the publication to re-read) and start, for an existing workspace, at
  its active publication's position (C-D92). New codes: `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`,
  `INVALID_PAYLOAD`, `EVENT_POSITION_AHEAD`, `EVENTS_EXPIRED`. `payload` becomes a reserved parameter
  name. A record's feed entry now also keeps its parent and previous parent, not shown in the feed
  (C-D95). Migration `20261006_01` adds `consumer_events` and `consumer_event_checkpoints`.
  Renaming a group with 20,000 items below it tells 20,001 objects in 0.7 s on the deriver's
  thread.

- Base 0.9 C9: consumer API event definitions. A definition declares `events`: exposed types, change
  kinds (`created`, `updated`, `deleted`) and an optional `watch` of the outputs and projections that
  count as an update, named as consumers read them (C-D81). Each mistake is refused at
  `/consumerApis/<key>/events/<event>/…` (C-D84); an event that tells consumers less needs a higher
  `contractVersion`, one that tells them more is compatible (C-D85). What `updated` means and how a
  type change is reported are settled for C10 (C-D82, C-D83). `event` and `after` become reserved
  parameter names, refusing a definition parameter so named (C-D86). No event is produced yet.

- Base 0.9 C16: business dates on the consumer API. `asOf=YYYY-MM-DD` on get by ID, lists, XREF and
  batch resolve keeps the records effective that day by their type's declared effective period, live
  or pinned to a publication. Types without a period are left unfiltered in a lookup and refused as
  `400 AS_OF_NOT_SUPPORTED` on a list or record; a malformed date is `400 INVALID_AS_OF`. Only the
  returned records are dated, not projection items or ancestors (C-D76). Lists, XREF pages and batch
  resolve carry `asOfApplied`, and every dated answer the `RDM-As-Of-Applied` header (C-D78). Each
  API's OpenAPI document declares `asOf` where it applies. SC-11 passes through the consumer API.

- Base 0.9 C8: consumer API parity acceptance. A test-only fixture shaped like the reference
  deployment (the starter with locations, availability, durations and a one-to-one self relation)
  and CONSUMER_API's definition written out answer the parity scenarios, each answer validated
  against the API's own OpenAPI document. A projection field may read `objectType`, the related
  record's public type name, where the definition exposes every type the projection reaches
  (C-D73). The consumer read budgets are collected in POSTGRESQL_BUDGETS §7 (C-D74).

- Base 0.9 V2: the API reference page `/docs` lists every consumer API of the active release beside
  the management API, labelled `{name} · v{contractVersion}`, built per request. A link to a source
  (Scalar's `?api=<slug>`) opens it; before, the parameter was refused.

- Base 0.9 C6b: the consumer API index `GET /api/consumer` (each API's `consumerApi`, `name`,
  `contractVersion` and `openapi` URL, paged, C-D69) and each API's own OpenAPI 3.1 document at
  `/api/consumer/{consumerApi}/v{contractVersion}/openapi.json`: paths written out with the name and
  version, `info.version` the contract version, schemas from the contract, the limits stated. Both
  answer an `ETag`. Dev dependency `openapi-spec-validator` checks the document and real answers
  against it (C-D70).

- Base 0.9 C6a: consumer API reads pinned to a publication. `publication={id}` or `latest` (the
  workspace's active publication) on get by ID, lists, XREF and batch resolve's URL reads the
  publication's records, values and relationships, with the definition of the release it was
  published under (`409 PUBLICATION_CONTRACT_MISMATCH` when that release declares another contract
  version, C-D60); `404 PUBLICATION_NOT_FOUND` for an unknown publication, another workspace's, or
  `latest` with none current (C-D61, C-D62). `RDM-Publication` and an envelope `publication` field
  name it (C-D63); a cursor keeps its publication, also with `latest` (C-D64).
  `GET /api/consumer/{consumerApi}/v{contractVersion}/publications` lists them newest first with
  `eventSequence` and `status` (C-D66). Every consumer `GET` answers an `ETag` and `304` to a matching
  `If-None-Match` (C-D65). Publication lists sort by an attribute through value-order indexes, on the
  management API too (D47, C-D67). Migration `20261005_03`: publication read indexes (C-D68).

- Base 0.9 C15: consumer API crosswalk. `to.{name}` on get by ID, lists, XREF and batch resolve
  names a `projection` parameter declared `targetable` and a value; the projection shows the items it
  matches, and each object carries them again as `target`, before `matchScore`. It changes no object,
  score, order or total, and cursors do not bind it (C-D54). A read of one object answers one target:
  `404 TARGET_NOT_FOUND` for none, `409 AMBIGUOUS_TARGET` for several, each naming the object; a
  page refuses nothing (C-D55). One `to.` name per read (`400 MULTIPLE_TARGETS`); a `to.` name of
  anything but a targetable parameter is `400 UNKNOWN_PARAMETER` (C-D56, C-D57). Turning
  `targetable` off is `version_required` at `/parameters/<name>/targetable` (C-D58). No migration.
- Base 0.9 C14b: a consumer read's ancestors are walked by ID and read by the walked list
  (170–192 ms to 10 ms at full volume), and contains reads are built without table aliases; a
  1,000-lookup batch resolve takes 236 ms (was 817 ms).
- Base 0.9 C14a: batch resolve resolves each distinct lookup once (same terms and parameters, in
  any order); a batch sending one heavy lookup 100 times fell from 1.7 s to 0.8 s at full volume.
- Base 0.9 C14: consumer API batch resolve:
  `POST /api/consumer/{apiKey}/v{contractVersion}/resolve`.
  - **Items.** Up to 1,000 items (`CONSUMER_RESOLVE_MAX_ITEMS`, reported by `GET /capabilities` as
    `consumerApi`; more are `413 BATCH_TOO_LARGE`), each a `query` or an `id`, with an optional
    `ref` and the definition's parameters over the request's `defaults`; JSON values are never
    split on commas (C-D47, C-D50).
  - **Outcomes.** In item order, each the single read's answer: `found` with the object, or
    `not_found`, `ambiguous` or `rejected` with that read's error, a rejection pointing into the item
    (`QUERY_OR_ID_REQUIRED` for both or neither of `query` and `id`); a body of the wrong shape or a
    wrong name in `defaults` refuses the request (C-D48, C-D49).
  - **One scoring path.** XREF is a batch of one: exact matches of every term are read at once,
    contains matches one select per term with its pattern bound; items group by their parameters,
    each group in a fixed number of statements (C-D51). A single best match is sought with the exact
    rules first, so an `expect=one` lookup its exact matches settle is no longer refused for what its
    contains terms match (C-D52, amends C-D37).
  - **Index.** Migration `20261005_02` adds a trigram index on names holding the workspace and type;
    it needs the `btree_gin` extension, which startup now requires beside `pg_trgm` and creates when
    it may.
  - **Budgets.** 1,000 lookups in 816 ms at full volume (451 ms over three parameter sets); XREF's
    lookups 13–65 ms. `test_consumer_xref_volume` checks equal statements for 10 and 100 items.
- Base 0.9 C5: the consumer API's parameters on XREF.
  - **Parameters.** Every definition parameter (`objectType`, `ancestor`, `related`, `projection`)
    narrows XREF with its list meaning: an object is a result when it scored and every parameter
    keeps it, with its unchanged score; `totalCount`, the pages and `expect=one` follow the narrowed
    set, and the cursor binds the parameter values (C-D42). A definition parameter on XREF is no
    longer `400 PARAMETER_NOT_SUPPORTED`. The 10,000-match limit still counts what the terms match
    before parameters (C-D44).
  - **`scoresFrom`.** A `projection` parameter declaring it limits which related records pass
    weights through its projection when the request gives it; own scores are untouched (C-D43).
    Refused at `/consumerApis/<key>/parameters/<name>/scoresFrom` without a `match.promoted` entry
    over the projection (C-D45); turning it on or off is `version_required` (C-D46).
  - **Budgets.** `test_consumer_xref_volume` adds a lookup narrowed by an ancestor and one with
    `scoresFrom`, with equal statements at two sizes.
- Base 0.9 C4: consumer API XREF lookup:
  `GET /api/consumer/{apiKey}/v{contractVersion}/xref?query=…&expect=any|one`.
  - **Scoring.** The live records of the exposed types, scored by the definition's `match` at read
    time over the existing indexes (no consumer index, C-D34): own exact weights add up, contains
    weights count only without an exact one (C-D35); a related record's first matching `firstMatch`
    weight passes to the objects it relates to through the projection, only to the preferred types
    where it relates to one (C-D36). One statement scores; ordered by score, public type name, name
    and object ID. Each result is the shared object with `matchScore` (C-D41).
  - **Migration** `20261005_01`: `ix_objects_workspace_lower_name` on `objects (workspace_key,
    lower(name))` and `ix_attribute_values_key_lower_text` on `attribute_values (attribute_type_key,
    lower(text_value))`, so an exact match ignoring case is an index seek rather than a recheck of
    every record the trigram index finds.
  - **Terms and limits.** Comma-separated (a comma inside a term as `%2C`) or repeated `query`, at
    most 100 (`400 TOO_MANY_TERMS`), none `400 QUERY_REQUIRED` (C-D38). Contains needs 3 characters;
    a query matching more than 10,000 records is `400 QUERY_TOO_BROAD` (C-D37).
  - **Paging and `expect=one`.** Cursors both ways, `position`, `from=end`, `totalCount` always
    (C-D39); `expect=one` answers the bare object, `404 NO_MATCH` or `409 AMBIGUOUS_MATCH` naming the
    tied objects (C-D40). `400 INVALID_EXPECT` for another `expect`. `query` and `expect` off XREF
    are `400 PARAMETER_NOT_SUPPORTED`. Definition parameters apply to XREF from C5.
  - **Model.** A `contains` weight on `id` or a typed attribute is refused at its
    `/match/…/contains` pointer (schema 0.8).
  - **Budgets.** `test_consumer_xref_volume` holds the statement counts at two sizes. At full volume
    lookups take 34–58 ms; refusing a term found in every item takes 116 ms, recorded in TODO.
- Base 0.9 C3b: consumer API parameters list several values as OpenAPI 3 serialises a list in a query
  (RFC 3986): repeated, or separated by literal commas, with a comma inside a value sent as `%2C`.
  C3's `\,` escape is withdrawn; the raw query is split before it is decoded.
- Base 0.9 C3a: lists sorted by an attribute read in value order. Migration `20261004_04` adds an
  index per typed value column on `(attribute_type_key, value, object_id)`, and a live attribute sort
  pages its records with a value through it, then those without one. Nothing changes for callers.
  At full volume a consumer list by rank pages in 10–12 ms (was 0.5–2.6 s) and the per-type list's
  rank sort under the 20,000-child parent in 9.9 ms (was 104 ms, POSTGRESQL_BUDGETS E3 live). A
  consumer list below a parent or an ancestor reads its containers first. Decisions D46–D48; change
  sets and publications follow in C6.
- Base 0.9 C3: consumer API lists and parameters:
  `GET /api/consumer/{apiKey}/v{contractVersion}/lists/{listKey}`.
  - **Lists.** Every live record of the list's type, or those anywhere below the parent records named
    by object ID (C-D27, C-D28), as the shared object; ordered by the list's new optional `sortBy`
    (records without a value last), then name, then creation order (C-D29). Paged as the management
    lists are: cursors both ways with `anchor`, `position`, `from=end`, `seek` and `includeTotal`,
    `pageSize` 1–100, default 20 (C-D30). The envelope names `workspace`.
  - **Parameters.** Every definition parameter applies to lists and to get by ID (C-D31):
    `objectType`, `ancestor` (any depth), `related` (through a projection, `self` or a shared
    projection) and `projection` (limiting the projection's items; `requireMatch` drops records left
    with none). Several values, repeated or comma-separated (a comma inside a value as `%2C`), are
    alternatives; different parameters combine (C-D32 as amended by C3b, C-D33). Each is a SQL predicate, so totals and position
    jumps stay in the database.
  - **Model.** `sortBy` on a consumer list (schema 0.8), validated at `/lists/<list>/sortBy` and part
    of the contract; `from`, `seek` and `includeTotal` are reserved parameter names.
  - **Refusals.** `404 LIST_NOT_FOUND`, `404 PARENT_NOT_FOUND`, `400 UNKNOWN_OBJECT_TYPE`,
    `400 INVALID_PAGE_SIZE`, `400 INVALID_PAGE_PARAMETER`; the shared paging codes answer `400` on
    the consumer tier. A declared parameter on get by ID is no longer refused; a paging name or a
    list's parent parameter there is `400 PARAMETER_NOT_SUPPORTED`.
  - **Budgets.** `test_consumer_list_volume` holds the statement counts at two sizes. At full volume
    a list by parent reads in 7 ms; reads ordered by `sortBy` take 0.15–2.6 s (the attribute sort's
    known cost, POSTGRESQL_BUDGETS E3; C3a reads it in value order).
- Base 0.9 C2: the consumer API tier at `/api/consumer`, with get by ID:
  `GET /api/consumer/{apiKey}/v{contractVersion}/objects/{id}`.
  - **The shared object.** Exactly the fields the definition declares, built from the definition
    alone: the roles and attributes (first source with a value, then `default`, then `null`; empty
    text is no value), `parent` (or `null`, with `objectType` `null` for a type not exposed),
    `path` and `hierarchy` (the ancestors, top down, without the object) and each projection as an
    object or `null`, or an array ordered by name, by the relationship's cardinality. Values keep
    the management API's encoding. Decisions C-D21–C-D26.
  - **Identity.** `{id}` is the object ID (C-D24); another identifier is found with XREF (C4).
  - **Live, by workspace.** Reads live data from the active release's definition, never a change
    set; `workspace` selects the workspace (default: the deployment's), named in the
    `RDM-Workspace` header.
  - **Refusals.** `404 CONSUMER_API_NOT_FOUND`, `404 CONTRACT_VERSION_NOT_FOUND` (naming the served
    version), `404 WORKSPACE_NOT_FOUND` (unknown or retired), `404 OBJECT_NOT_FOUND`,
    `400 UNKNOWN_PARAMETER`, and `400 PARAMETER_NOT_SUPPORTED` for a declared parameter until C3.
  - **Cost.** One statement for the records and their values, one per projection and one recursive
    CTE for the ancestors, whatever the number of objects. The routes stay out of the management
    OpenAPI document.
- Base 0.9 F2: change feed retention and recovery.
  - **Retention.** `FEED_RETENTION_DAYS` (default 30, reported as `changeFeed.retentionDays` by
    `GET /capabilities`). `earliestPosition` is the first entry within the period. A position below
    it is `410 feed_position_expired`, naming `earliestPosition`, `headPosition` and the active
    publication with its `feedPosition`, the baseline to re-read before following on.
  - **Always a way back.** The earliest position never passes the active publication's, and a
    workspace without one keeps every entry (D40). The audit log is not pruned.
  - **Publications** carry `feedPosition`.
  - **Cost.** A 500-entry page reads in 25–35 ms with 4 statements, at the head and in the middle of
    a 1,000,000-entry feed.
  - **Migration** `20261003_03`: the index the retention floor is found by. Decisions D40–D41.
- Base 0.9 F1: the change feed `GET /api/v1/workspaces/{key}/feed`.
  - **Positions.** Every change to a workspace's live data has a position: per workspace, gapless and
    in commit order. A live write takes positions under the workspace lock it already holds (one
    statement per write), so a refused or rolled-back write leaves no gap. Change-set work takes
    none.
  - **Reading.** A reader passes the last position it processed (`after`) and pages with `pageSize`
    (1–1,000, default 500) until `nextAfter` equals `headPosition`. `kind` and `objectTypeKey`
    (repeatable) filter within a scan of at most ten pages, never an unbounded one.
  - **Entries.** Each entry names the record or relationship, its type, version, the changed fields
    and attribute types (never values), the cause (a user, a job or a publication) and the model
    release.
  - **Publishing.** A publish writes one entry per record and relationship it changed in live data
    (`reclassified` with the previous type for a type change), then its `published` entry.
    Withdrawing adds `withdrawn`.
  - **Refusal.** A position past the head is `409 feed_position_ahead`.
  - **Migration** `20261003_02`; the feed starts empty, with no backfill. Decisions D31–D34.
- Base 0.9 B3: relationship items in `POST /api/v1/batches`.
  - **Items.** `createRelation`, `ensureRelation` (unchanged when the relationship already exists
    with the same values), `updateRelation` and `deleteRelation`, with the ends named by ID or by a
    unique value, and set claims as on the single routes.
  - **Set replacement.** `replaceRelationSet` makes a record's set of one relationship the listed
    records. Kept relationships keep their identity and values, the set's version is claimed (or
    the request declares an overwrite), and an equal set answers `unchanged`.
  - **Bulk.** Relationship items are decided in memory and written in bulk with the object items
    around them: 40–43 statements per chunk of 500 at two data sizes (D35).
  - **Set versions on the anchored read.** `GET /relations?objectId=…` names every set the record
    anchors with its version as `relationSets`, an empty set included (D38).
  - Decisions D35–D39. No migration.

### Changed

- Base 0.9 K2b: a change set's deletions are audited per record (`change-set-object`, `deleted`), as
  its creates and updates are; the single delete's preview token is computed differently (it stays
  opaque), so a token issued before this release is refused `DELETION_PREVIEW_CHANGED` and previewed
  again. The bulk change dialog's flow is shared by every bulk action (`BulkJobDialog`).

- Base 0.9 K2 (D119): `IMPORT_PREVIEW_MAX_ITEMS` is renamed `JOB_PREVIEW_MAX_ITEMS` and
  `integrationJobs.limits.importPreviewMaxItems` `previewMaxItems`, without an alias, since the
  limit now bounds a batch's preview too. The OpenAPI schema `ImportPreview` is `JobPreview`, its
  `rows` an import's only; a batch's `parameters` name its `stage`.

- Base 0.9 C17: webhook delivery choices. A subscription chooses how requests are made, three
  independent choices: `maxEventsPerBatch` (1–1,000, default 1: one event per request; batched, a
  request holds what is waiting, up to that many and 1 MiB), `payload` (`full`, "with the object",
  or `identity`, "notification only") and `format` (`rdm`, default, or `cloudevents`: CloudEvents
  1.0 in structured mode, one event per request as `application/cloudevents+json`, batched as an
  `application/cloudevents-batch+json` array, each with the RDM event as `data`). The coalesced mode,
  `mode` and `debounceSeconds` are removed (C-D105 retired); sending them is `422`. Capabilities'
  `delivery.maxEvents` is now `maxEventsPerBatch` (1,000). The delivery log has no notice rows and
  its detail no `kind`; a resend needs `eventId` and repeats the event in the format it was sent in.
  Revision `20261007_03`: existing subscriptions take the defaults and logged notices are deleted.
  The webhook dialog's Delivery section has the three choices, and a webhook's page shows them.

- Webhook URLs may name any host (C-D101 revised): HTTPS on any host and port, plain HTTP only to
  `localhost`, `127.0.0.1` or `::1`. `CONSUMER_WEBHOOK_ALLOWED_HOSTS` is removed, with
  `consumerSubscriptions.allowedHosts` in capabilities, `WEBHOOK_HOST_NOT_ALLOWED` and the
  `HOST_NOT_ALLOWED` suspension; adding a receiver no longer needs a restart. The dispatcher still
  refuses link-local addresses (cloud metadata) when it connects. The Webhooks dialog and the
  Deployment page drop the allowed hosts.

- Base 0.9 UA1: every application and every kind of record has a colour (ADR-040). Each takes one
  of eight hues by its position in the model, so any model is coloured and no screen knows a key;
  the application tabs and the rail's Collections show it as a tile with the model's icon. The
  hues, their dark values and the context strips are tokens held to the contrast minimums in both
  themes.
- Base 0.9 UA2: the record browser shows what contains what. Every record carries its type's
  tile, an open branch hangs from a guide line, a type's heading is a quiet label with its count
  and never looks like a record, and the selected record is filled with its type's colour.
- Base 0.9 UA3: the collection page in the Atlas look. The page header carries the type's tile,
  Live is a soft green strip with dots of the change-set and publication colours on their switches,
  a column that shows another record (an `ancestor:<type>` column) shows it as a chip in that
  type's colour, the selected row takes its type's colour, booleans read Yes and No in plain text
  everywhere, the first page loads as rows in the table's shape, and an empty collection shows its
  tile and the Add action.
- Base 0.9 UA4: the record in the Atlas look. The record's header is a band tinted in its type's
  colour with the type's tile, the type named in its colour, and the ancestors in the breadcrumb as
  chips in their types' colours that open them; history markers take the type's colour. In the
  inspector beside a tree lens the sections are ruled, fields sit beside their labels, and the
  relationship panels become one **Connected** list of chips in the related types' colours (with
  **Show more** and a way to manage them on the full page); the full page keeps the tables.
- Base 0.9 UA4 revision: one table for every list of records in rows (`ui/DataTable`): collections,
  a record's children and its relationships. Relationship tables gain the Display menu (columns,
  density, page size, widths), table-shaped loading rows, the empty state, row colours and the phone
  layout's three columns with **Show all columns**. Columns resize by dragging the edge of their
  header (it was reachable by keyboard only): a drag starts from the column's drawn width, keeps the
  other columns as they were, and may make a column narrower than its content, which then ends in an
  ellipsis. The look of a table that has not been resized is unchanged.
- Base 0.9 UA4 revision: a record's fields are edited by clicking their value, not by Edit, Remove
  and Add value buttons. The value is a button that reads as text, with a soft fill and a pencil on
  hover and focus (a plus on an empty field, which adds a value); an optional value's trash icon
  shows with the row's hover or focus and always on touch, and removing still asks first. Saving
  stays explicit, a selected text is left for copying, and focus returns to the value after
  editing. Read-only fields and publications show plain values.
- Base 0.9 UA4 revision: Settings › Appearance has **Type colours**: palette B (magenta and olive,
  the default) or A (plum and gold) for the record type colours, saved in this browser.
- Base 0.9 UA4 revision: Settings › Appearance has **Edit pencil**: a record's editable fields show
  their pencil on hover and focus (the default) or faintly all the time, saved in this browser.
- Base 0.9 UA4 revision: the top bar takes a way back (`TopBar`'s `back`), shown after the product
  mark. Settings uses it: **Back to {application}** returns to the exact page Settings was opened
  from, or to the home page when Settings was the first page opened.
- Base 0.9 UA4 revision: the record's header shows its ID (the `id` the management and consumer
  APIs return) under the title, in monospace with a copy button (`ui/CopyValue`), in the inspector
  and on the full page.
- Base 0.9 UA5: change sets and publications in the Atlas look. A change set is the soft amber
  strip and a publication the soft violet one, as Live is green, each with a line saying what an
  edit does there; the pill names the context and the change set's bar gives its name, version,
  source and model with its actions at the end: **Review changes**, **Validate change set**,
  **Publish change set** (the indigo primary action) and a **More change set actions** menu
  (`ui/ActionMenu`, in place of a hand-made one) for **Change model version** and **Discard change
  set**. The change set and publication lists are ruled rows on one card (`ui/RuledList`), grey
  under the pointer as table rows are; a publication's **Start a change set from this publication**
  and **Withdraw publication** moved into its row's menu, beside **Open publication**. An empty
  change set list offers **Start from current live data** as the header does. In **Review changes**
  the kind of change is a pill (Added green, Changed grey, Removed red), a record shows its type's
  tile, and a relationship's two ends are chips in their types' colours.
- Base 0.9 UA2 revision: the record browser's group frames show only while a group scrolls, in the
  sidebar and the hierarchy lens. At rest they are invisible, and the glow on the group under the
  pointer is removed.
- Base 0.9 UA2 revision: a type group's heading in the record browser no longer shows its count;
  screen readers still hear it with the heading's name.
- Base 0.9 UA7: dark mode and the gates. Every surface was checked in dark beside its light
  version. Checkboxes and radios are drawn from the design tokens instead of the browser's own
  controls, which in dark were grey discs where a disabled choice looked like an enabled one. A
  table's column resize handles stand outside the header cells, so a column header is named by its
  label alone (it read "Path Resize Path column"). The visual gate holds 64 baselines, every
  screen in light and dark, adding the mapping grid and its dialog and a collection and a record at
  390px; the accessibility gate checks the same pages (73 checks, no violations).
- Base 0.9 UA6 revision: the settings navigation's group headings are dark and bold, and their pages
  hang one step in from a guide line, so headings and pages no longer look alike. In the 390px
  drawer the navigation keeps the rail's inset and the headings their size (they took the dialog's
  heading size and sat against the screen edge).
- Base 0.9 UA6: the remaining surfaces in the Atlas look. The relation matrix, mapping grid and
  tree lens carry their row type's tile in the page header, as a collection does; a matrix cell's
  record and a mapping's targets (in the grid and in its dialog's **Currently**) are chips in their
  type's colour, and mapping states are pills (Mapped green, Unmapped grey, Ambiguous amber). The
  dialogs that list records to choose (move, mapping target, matrix link and place, restructuring's
  siblings) show each record's type tile, through one `ui/Candidate` row; the matrix cell dialog and
  the restructuring plan show it before each record. Every state tag is a `StatusPill` (release
  and workspace states, capabilities, diagnostics, model changes, refusals), every panel a
  `ui/Card`, every notice `ui/Notice`. Removed: the 51 older token aliases in `base.css` (the
  stylesheets read the roles), the `.surface`, `.pill`, `.compatibility` and mapping badge rules,
  and six rules no screen used.
- Base 0.9 UA2 revision: the record browser's groups sit in frames of their type's colour, nested
  as boxes inside boxes; a group glows in the accent while it scrolls and in teal while the pointer
  is in it; with a pointer, a scrolling group stops at its first and last row; records sit one step
  in from their group's heading. Folding headings is built and switched off (`FOLDING_GROUPS`).
- Record browser: the group under the pointer owns the mouse wheel, its heading included; at its end
  the wheel moves the window around it only until the whole group is in view, so a group partly
  scrolled out of sight can always be brought back from inside it.
- Record browser: a new scroll gesture on a group that is at its end moves the area around it on,
  so the sidebar never gets stuck; scrolling up into a group also shows the record it belongs to;
  the groups' resting frames are fainter.

- Base 0.9 C12: `POST /consumer-subscriptions/{id}/resume` takes `reset` instead of
  `acknowledgeLoss` (C-D93 revised, C-D110). `reset: true` starts delivery after the workspace's
  feed head, whatever happened before; without it a resume after expired events is still
  `409 EVENTS_EXPIRED`, its message naming `reset`. A resume and an edit now also clear a failing
  batch's retries, so the next attempt is at once. A filter value that stops matching suspends
  the subscription without delivering the deletions first (C-D94 revised).
- Base 0.9 C12: the job worker, the event deriver and the new dispatcher log a database they cannot
  reach in one plain ERROR line, with the traceback at DEBUG, then a WARNING a minute; other
  failures keep their traceback. J12's outage case no longer fails when the deriver polls during
  the outage.

- Base 0.9 C8: a consumer object's `parent` keys its fields by the roles' output names, as the
  object's own fields (`masterId`, not `id`, where the `id` role's output is `masterId`; C-D75).
  The reference deployment's parent has these names, and a flow reading a field from an object and
  then from its parent uses one name.

- The example model 0.6.0 declares one consumer API, `rdm`, over every object
  type of the model, so one XREF looks up any ID, code or name across every type, systems and
  translations; `type` narrows it, and `system` and
  `language` resolve and translate codes (crosswalk). Lists per type. It replaces 0.5.0's four
  APIs split by audience, whose XREFs each searched only their own types.
- Base 0.9 CN1: the consumer API's name is written `consumerApi` in public contracts, not
  `apiKey`, which reads as a credential: the route `/api/consumer/{consumerApi}/v{contractVersion}/…`
  and the planned API index, subscriptions, webhook bodies and events (U-D1). No response changes:
  none carried the name, and the not-found errors gain no field (C-D59). The model keeps `key`.
- **Breaking — Base 0.9 C2: a consumer API's identity is the object ID.** The `id` role's source is
  `["id"]`; a `unique` attribute as its source, which C1 accepted, is refused at
  `/consumerApis/<key>/object/id/source`. Publish a former system's ID as an attribute field.
- **Breaking — Base 0.9 T1b: error codes are upper case** on every API: `object_not_found` is now
  `OBJECT_NOT_FOUND`. It covers error bodies, the errors and unprocessed `reason` of batch and job
  item outcomes, and validation diagnostics (D42). Status, action, kind and classification values
  keep their case; a consumer contract's `version_required` classification is unchanged. Revision
  `20261004_03` upper-cases the codes already stored in job results (D43). A check in the
  `contract` group refuses a new lower-case code (D45). Clients comparing codes must compare the
  new spelling.
- Base 0.9 T1a: current-live change-set bases and publications copy records, relationships, typed
  values and matrix states inside PostgreSQL. Publications copy live data after applying the
  change; merge and graph validation remain in Python. Revisions `20261004_01` and `20261004_02` add
  the `rdm_value_json` and `rdm_decimal_text` encoding functions; a decimal at any stored scale
  (1e-16383 answered `500`) encodes as Python does. API behavior is unchanged.

- Base 0.9 B3: the single relationship writes and the mapping save are batches of one through the
  same decide steps as batch items, so they answer with the same codes.
  - A relationship update checks its version before its values, live as in change sets.
  - A change-set relationship delete records an audit entry.
  - A mapping transition's audit payload lists `newTargets`.
- Base 0.9 B3 (D36): replacing a required relationship's only target, through the mapping save or a
  set replacement, is `422 required_relation` when the record losing it has no other.

- Base 0.9 F1 (D15): a publish's changes to live data now show in record history, one entry per
  record with `cause: {"kind": "publication", "id"}`; `AuditCause.kind` gains `publication`.

### Fixed

- Base 0.9 UA0: with a popover open (Account, Display, Filter), the first click on the page only
  closed it, so a tab or link seemed not to respond. `ui/ControlPopover` is now non-modal: a press
  outside, or the user's own wheel or touch scrolling, closes it and the press acts; a scroll the
  layout causes, such as an applied filter shortening the list, keeps it open. Escape and focus
  leaving it still close it. `test:browser:settings` clicks an application tab, a settings link and
  the page heading with Account open.
- Base 0.9 UA0: the workspace switcher, opened before the current workspace had loaded, showed only
  that workspace: its name arriving as the field's value filtered the open list. The switcher is
  disabled until the current workspace is known. This was `test:browser:w4`'s intermittent miss.
- Base 0.9 UA0: the application tabs stood 20px after the product name in the top bar; they start
  36px after it, as ADR-040 says.
- Base 0.9 UA0: Settings had a top bar of its own, whose product mark could not be clicked and
  which had no applications. Every page now has the same top bar (U-D14): on Settings no
  application is current and **Settings** shows as the current tab (gear, name, underline), an application's tab goes back to it (the one last
  looked at, to the same view and query), and the mark goes home. "Back to applications" is gone.
  One frame (`app/ShellFrame`) and one top bar (`app/TopBar`) serve every area, and copied markup
  is replaced by shared components: `ui/SearchField`, `ScopeBanner`, a release picker and a
  change list.

- Base 0.9 C8: the `consumer` test group now selects the J29 journey tests; since C4 it had left
  them out (`JOURNEY_GROUPS` had no `J29`).

- Base 0.9 C6b: a consumer API document was not valid OpenAPI when a list's parent parameter shared a
  definition parameter's name (`Duplicate parameter`); the list's operation now lists the name once,
  as the parent, as the route reads it.

- Base 0.9 C15: a model shape error inside a typed union (a view's or panel's `config`, a consumer
  API parameter) was reported at a path holding Pydantic's type tag, such as
  `/applications/1/views/1/tree/config/pageSize`, which names no node of the document, so the model
  draft editor could not go to it. The tag is left out: `/applications/1/views/1/config/pageSize`.
- Base 0.9 T1: creating a change set from current live data and publishing a change set failed with
  `500` in a workspace holding more than about 65,000 records. Both read every record's values and
  relationships with a list of all the record IDs, one statement parameter each, and PostgreSQL
  refuses more than 65,535. They now select by workspace, and the publish checks each relationship
  end with a primary-key probe.
- Base 0.9 T1: capturing current live data and publishing slowed quadratically with the number of
  records they wrote. The typed value index's flush hook rebuilt SQLAlchemy's set of pending rows
  once per row. At about 10,000 records (4 % of the volume fixture), capture now takes 4.6 s instead
  of 28.1 s, and publish 6.0 s instead of 29.9 s.
- Base 0.9 T1: applying a publish to live data flushed the session once per changed record, with
  the whole workspace loaded. It now writes the changes with explicit flushes, and copies the
  publication and a change set's base in multi-row statements. Publishing 1,000 changes in a
  26,000-record workspace takes 11.3 s instead of 25.0 s.
- Base 0.9 B3: relating the same two records twice with one relationship type answers
  `409 duplicate_relation`. Live, it answered `500`; in a change set, the duplicate was staged.

## [0.9.0-alpha.1] - 2026-10-03

Everything since 0.8.0: Base 0.9 packages Q1–Q4, C1, V1, B1 and B2, and the PostgreSQL runtime
(PG1–PG3b, PG5; PG4 dropped) with the test harness (H1–H4d-1).

### Added

- Base 0.9 Q1: cross-type lookup `GET /api/v1/objects`. It lists records of every object type, or of
  those a repeatable `objectTypeKey` names, in live data, a change set or a publication, with the object
  list's paging, seek and cursors. `applicationKey`, `parentObjectId` or `topLevel` narrow it, `search`
  matches the name, and filters and sorts take built-in fields. A model-declared field is refused
  (`422 invalid_filter` or `invalid_sort`) with the per-type route that answers it. Items have the
  per-type list's shape. Over the 258,000-record volume fixture a first page takes 5–9 ms and a name
  search with its total 72–80 ms in every context.
- Base 0.9 Q2: the workspace edge list. `GET /api/v1/workspaces/{key}/mappings` takes `publicationId`
  (with `changeSetId` it is `422 mutually_exclusive_context`), and the same list is published as
  `GET /api/v1/workspaces/{key}/relations`: every edge of any relation type in live data, a change set
  or a publication, with one response shape. Each route's cursors are its own. A publication's rows
  carry `mappingVersion` 0. `GET /api/v1/relations` is unchanged.
- Base 0.9 Q3: the model-aware query `POST /api/v1/workspaces/{key}/queries/objects`. It lists one
  object type's records in live data, a change set or a publication by criteria combined with AND:
  the object list's field criteria with typed JSON values, `ancestor:<type>` by ID, and one relation
  hop (`related`, inverted with `not`). One `sort`; `select` returns chosen values under `fields`;
  `expand` adds up to 20 related records per item with their `count` and a cursor that continues on
  `GET /relations`, one statement per expansion for the page. Paging by cursor, position or `from`,
  with cursors bound to the body. Model-dependent mistakes are `422 invalid_query` with a JSON
  pointer; `asOf` was refused as `as_of_not_supported` until Q4. Decisions D17–D19. Over the
  100,000-item volume fixture every measured query takes 4–91 ms.
- Base 0.9 C1: schema 0.8 with consumer API definitions (`consumerApis`). A definition declares its
  `key` (the `apiKey`), `contractVersion`, exposed types with public names, the shared object's roles
  and attributes with their sources, projections over relation routes, scoring weights, parameters of
  kind `objectType`, `ancestor`, `related` and `projection`, and lists. Every reference is validated
  against the release and refused at its JSON pointer; a field's sources share one type (C-D19), the
  identity is `id` or a unique attribute, and match fields are searchable or unique (C-D20). Draft
  compile and release diff report `consumerContracts` against the active release, and activation
  refuses a breaking change without a higher `contractVersion` (`409
  consumer_contract_version_required`; C-D17, C-D18). Schema 0.5–0.7 models and their hashes are
  unchanged. Decisions C-D17–C-D20.
- Base 0.9 Q4: effective periods and `asOf`. Schema 0.8 lets an object type declare one
  `effectivePeriod` over two `date` attributes it binds (inclusive start, exclusive end, either open).
  Writes refuse an end not after its start with `422 invalid_effective_period`, live and in a change
  set, and change-set validation reports it. `asOf=YYYY-MM-DD` on `GET /objects/{objectTypeKey}` and in
  the model-aware query keeps the records effective on that date in live data, a change set or a
  publication; a type without a period, and the cross-type lookup, refuse it as
  `as_of_not_supported`. Activating a release that declares a period over records it would refuse is
  `model_migration_required` with their count, and removing a period from a type a consumer API
  exposes needs a higher `contractVersion`. The starter is content release 0.9.0 on schema 0.8, with
  a period on master values. Decisions D20–D22.
- Base 0.9 V1: the API reference at `/docs` is [Scalar](https://github.com/scalar/scalar) (MIT) over
  the management OpenAPI document, replacing Swagger UI and ReDoc (`/redoc` now answers `404`). The
  Scalar script (1.72.2) is bundled with the engine, so the page works without internet access and
  loads nothing from another host; `RDM_API_REFERENCE_SCRIPT=cdn` loads the same version from
  jsDelivr under its integrity hash. The page is outside the OpenAPI document, which is unchanged.
- Base 0.9 B1: bulk object writes as jobs. `POST /api/v1/batches` runs `create`, `update`, `upsert`
  and `delete` items inline, live or in a change set, under a required policy: `atomic` (all or
  nothing) or `independent` (each item alone, in order, seeing earlier applied items). Each item goes
  through its single write and is refused with the same code; records are named by ID or by a unique
  attribute's value, an upsert by an ID or a unique attribute, an item that would change nothing is
  `unchanged`, and an upsert that finds a record needs `expectedVersion` or `onExisting: "overwrite"`.
  The response is the job with its counts and `result` and its outcomes in item order, each with a
  JSON pointer when refused. `Idempotency-Key` answers a retry with the first job. `GET /api/v1/jobs`,
  `/jobs/{id}` and `/jobs/{id}/items` read jobs back; object history names the job as each change's
  `cause`. Limits and retention are settings reported under `integrationJobs` in `GET
  /capabilities`; `INTEGRATION_JOBS_ENABLED=false` removes job creation. Decisions D23–D26; D13
  confirmed: 1,000 upserts take 3.3 s live and 6.8 s in a change set on the volume fixture.
- Base 0.9 B2: background batches. `run: background` queues the batch (up to 1,000,000 items in a
  50 MB body) and answers `202` with the job; a worker in the API process applies it in chunks of
  500, each committing its changes, outcomes and progress together, so a job resumes after a crash or
  restart at its first item without an outcome and never applies one twice. The worker holds a lease
  on the job (`leaseOwner`, `leaseExpiresAt`), which another worker or the restarted process takes
  over once it expires. `POST /api/v1/jobs/{jobId}/cancel` stops a job at its next chunk (an atomic
  job rolls back completely); a model release activated meanwhile, a change set written by someone
  else or an internal error fail it, and the items it did not reach are `unprocessed` with the
  reason. Finished jobs expire after their retention with their summary kept. New settings
  `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`, `JOB_CHUNK_ITEMS` and
  `JOB_LEASE_SECONDS`. Decisions D27–D30. On the volume fixture a
  100,000-item background batch runs at 433 items/s live and 151 in a change set; on SQLite, other
  writes wait until such a job ends.

### Changed

- 0.9.0-alpha.1 PG1: PostgreSQL is the only database. `DATABASE_URL` is required and must name a
  PostgreSQL database with the ICU root collation `und` (PG-D11: a language-independent Unicode order,
  so names sort case- and accent-aware, `Elan, élan, Élan, Emil`, where SQLite sorted by code point).
  Startup refuses a missing or non-PostgreSQL URL, another driver, an unreachable server, another
  collation, an unknown schema revision and a `pg_trgm` it cannot create, each with what to do and
  `/health` 503. The 23 SQLite migrations are one PostgreSQL baseline (`20261001_01`); a migration
  runs in one transaction. `scripts/postgres.sh start|stop|status|backup` runs a development server
  from Homebrew's `postgresql@17`; the backend tests start their own and reuse seeded template
  databases until the migrations, model or seed code change (`python -m tests.seeds list|build`).
  The Docker Compose database and CI use ICU `und`. Existing SQLite databases are carried over in
  PG4.
- 0.9.0-alpha.1 PG1: the relation list's sort by `ancestor:<type>` works on PostgreSQL (it used a
  SQLite-only grouping); the ancestor chosen is unchanged.
- 0.9.0-alpha.1 PG2: the PostgreSQL forms. Starting a change set from current live data
  (`source: currentLive`) works on PostgreSQL: the base is read from one snapshot while share locks
  keep a retirement or an activation from committing, and a change the snapshot cannot hold answers
  `409 change_set_snapshot_retry` (`change_set_snapshot_unsupported` is gone). Activation and
  workspace deletion wait for row locks instead of failing on a busy database, so
  `model_activation_retry` and `workspace_delete_retry` are no longer returned, and the
  `SQLITE_LOCK_WAIT_SECONDS` setting is removed. Search reads `pg_trgm` GIN indexes over text values
  (revision `20261001_02`) with the same results, and case-insensitive search folds every script
  (`ünal` finds `Ünal`). Foreign keys are enforced; every `ondelete` rule is pinned in
  `test_foreign_keys`, and a record written into a workspace deleted meanwhile still answers
  `404 workspace_not_found`. Relation matrix states and pages walk each cell record up to its
  column once, with nothing joined back: building the states of the volume fixture at scale 0.005
  took 14 s and grew about four times per doubling; it now takes 0.3 s, 1.0 s at 0.02 and 7 s at
  0.1, and a matrix page at 0.01 went from about 120 ms to 40 ms. Relation expansions and the restructuring
  planner order names as the database does. The browser runners run on the development server
  (`scripts/postgres.sh start`), each on its own database cloned from a seed built once
  (`tests/browser_seeds.py`).
- 0.9.0-alpha.1 H2: the backend tests run in parallel with `pytest -n auto` (pytest-xdist, a dev
  dependency; each module on one worker, each worker with its own session database). Timing-based
  tests carry a `serial` marker (the `volume` group and two timer-decided tests); a parallel run
  leaves them out and names the command that runs them without `-n`. The 968 parallel tests take
  1 min 49 s on 10 cores.
- 0.9.0-alpha.1 H3: the full-size batch budgets (`test_batch_volume`, `test_background_volume`)
  carry a `budget` marker and run only when `-m` names `budget`. `serial` holds only the three tests
  whose outcome depends on wall time; the counting volume modules run in parallel. The run summary
  lists every test over 10 s and the wall time. The full suite without `budget` takes 2 min 41 s.
- 0.9.0-alpha.1 H4b: tests are of two kinds, journey tests in `backend/tests/journeys/` that name
  the user journeys they walk (`@pytest.mark.journey`, checked against USER_JOURNEYS.md;
  `--journey J02` selects them) and unit tests in `backend/tests/unit/` that mirror the module they
  test. `pytest --testmon` runs only the tests whose code changed, `python -m tests.affected` says
  what a change requires (migrations, the starter model and the harness select everything), and
  `python -m tests.journey_trace` shows the code each journey reaches and the code no test reaches.
  `test_api_journeys` keeps the API inventory (`docs/testing/API_JOURNEYS.md`) complete: every
  operation, parameter, error code and setting with its journeys.
- 0.9.0-alpha.1 H4c: every route refuses a query parameter it does not take with
  `422 unknown_parameter` naming each in `details.parameters` (a misspelt `pagesize` was silently
  ignored, as was a `publicationId` on a write, which then wrote live data). `GET
  /api/v1/workspaces/{key}/mappings` is removed; `GET /api/v1/workspaces/{key}/relations` is the same
  list, and the path keeps the replacement's `PUT`. API.md documents the 32 error codes it lacked.
- 0.9.0-alpha.1 H4c: journey tests for every journey and variant of the catalogue with an API or
  operator side (160 tests, 345 runs on two model configurations each, about 1 minute in parallel),
  written from the catalogue and API.md before the code was read. Each runs on a generated model and
  on the starter model or a second generated one, against a seed built once through the API. The
  operator's journey starts the service on prepared databases and runs its commands as processes.
- 0.9.0-alpha.1 H4c, decided from the journey tests: a stale `expectedVersion` on a record or
  relation write answers `409 version_conflict` with `details.currentVersion`, as a workspace update
  did. A live write naming an unknown relation type is `422 unknown_relation_type` (was 404), and a
  live create whose `initialRelations` repeat one relationship is `422 duplicate_initial_relation`
  (was `409 cardinality_violation` or `duplicate_relation`), as in a change set. The relation matrix
  answers an unknown `applicationKey` with `404 unknown_application`. `/health` asks the database
  and answers `503` while it is unreachable; it recovers without a restart.
- 0.9.0-alpha.1 H4c: a duplicate unique value is refused alike live and in a change set: the message
  names the attribute, `details` carry `attributeTypeKey` and `conflictingObjectId` (live had no
  details). Empty text in a unique attribute is no value in a change set too, so records may share
  it there as live. A change set holds a breach of a binding's ancestor scope written directly (a
  relation create, initial relations, an edit, a move or a set replacement) as it already held one a
  moved container brought: the matrix shows the conflict, validation reports it and publishing
  refuses it, so a change set's edits can come in any order. Live still refuses it at once.
- 0.9.0-alpha.1 H4c: a live relation create or initial relation naming a record that does not
  exist answers `422 relation_endpoint_missing` naming it (was `404 object_not_found`), as a change
  set does.
- 0.9.0-alpha.1 H4d-1: the jobs and batches tests are journey and unit tests. Four old modules
  (73 cases) are removed; their checks are in J11, J12 and J24 or in unit tests of
  `engine/jobs/*`, `records/audit.py`, `models/commands.py`, `config.py` and `main.py` (62 cases),
  which run the engine on a clone of a journey seed without starting the application. 14 faults
  planted in the area's rules were each caught by the tests that remain.
- 0.9.0-alpha.1: no SQLite copy command (PG4 dropped). Starting on a SQLite `DATABASE_URL` is refused
  with the instruction to name a PostgreSQL URL; the message no longer points to a copy command.
- 0.9.0-alpha.1 H4: the testing consolidation stops after H4d-1 (H4d-2 onwards and H4e postponed,
  no dependency for 1.0). Journey tests, unit tests and the older modules form the suite; a package
  selects its checks with testmon and the journeys it touches, and its test work is capped in
  proportion to the feature (AGENTS.md).
- 0.9.0-alpha.1 PG3: live writes of one workspace serialize on its row lock, and workspaces write
  in parallel (PG-D5). Every live write locks its workspace before it reads, so two writes racing
  for one unique value, a parent cycle, a cardinality limit, a required relation, a relation-set
  version or one relation matrix cell no longer both commit: the second reads what the first
  committed and is refused with its single write's code. A relation create and a mapping save on
  one edge no longer deadlock (a 500); the mapping save answers `409 mapping_version_conflict`. A
  workspace deleted or retired while a write waited is refused with `404 workspace_not_found` or
  `409 workspace_retired`, nothing saved. A background job holds the lock for one chunk, so a live
  write in its workspace waits for that chunk only; a cancel request is answered while a chunk runs.
  The cascade deletion no longer locks three whole tables. Retirement, default switching, deletion
  and publishing take their locks in one documented order (ARCHITECTURE). A change-set write now
  locks its workspace against retirement and deletion too: a retirement waits for it instead of
  committing beside it, and a later write is refused `409 workspace_retired`. Publishing no longer
  holds up writes in other change sets of its workspace.
- 0.9.0-alpha.1 PG3b: batch items are decided in memory and written in bulk. The create, update and
  upsert items of an inline batch or a background chunk are checked one after another by their
  single writes' rules, each against what the items before it left, and the accepted ones are
  written together: records, attribute values, relations, relation-set versions and one audit
  event per item, each kind in multi-row statements. A chunk now costs 30–49 statements for 100 or
  500 items, at two dataset sizes (a live upsert item alone cost about 20), and a chunk of 500 items
  takes 0.25–0.46 s; a live write beside a background job waits that long at most. Items are
  refused with the same codes, messages and details as their single writes, and single writes go
  through the same code as a batch of one. Delete items keep their per-item path. A bulk write that
  fails on a row the rules could not see, such as an ID another workspace took meanwhile, is redone
  item by item, so only that item is refused. An `atomic` job looks for a cancel request before
  every 500 items and before it writes, instead of before every item, and still rolls back
  completely. A chunk checks its model release before it writes relation matrix states, so an
  activation that removes a matrix view can no longer deadlock with it; the chunk fails
  `model_release_changed`.
- Base 0.9 B1: a change set write's record lookups probe the change set's own rows by key instead of
  listing all of them on every statement, so a write costs the same however many records the change set
  holds (a lookup took 361 µs at 4,000 own rows, now 39 µs; page reads unchanged or faster). On SQLite,
  a write waits up to `SQLITE_LOCK_WAIT_SECONDS` (60) for another transaction's writer lock instead of
  failing after the driver's 5 s.
- Base 0.9 B2: a live write's unique-value check and a record reference by key seek to the value
  through a new index (`ix_attribute_values_key_text`) instead of reading every value of the
  attribute, so their cost no longer grows with the records holding it (creates into a workspace
  gaining 30,000 records went from 2.3 to 5.2 ms each; now a flat 2.0 to 2.1 ms).

- Backend boundaries (E1–E3, [record](docs/BACKEND_BOUNDARIES_PLAN.md)). `backend/app` is split into
  tiers: `common/`, `engine/` (no FastAPI, no API schemas), `management/` (the `/api/v1` routes,
  schemas, presenters and projections) and the `consumer/` slot, checked by `tests/test_boundaries.py`
  with no exceptions, no import cycles and no function-level imports. The write rules are written once
  (`engine/records/rules.py`) and read live data or a change set through a lookup; where the two
  contexts word a refusal differently the difference is one entry in `engine/records/refusals.py`,
  pinned by `tests/test_rule_parity.py` (31 violations, both contexts, two models). Every record,
  relation and attribute-value row is written through `engine/records/writes.py`, the seam F1's feed
  position goes into. The live and change-set mapping replacement is one flow, and `change_sets` is a
  package. Both OpenAPI documents are unchanged. When one request breaks two parent or relation rules,
  which one is reported can differ from before.
- A live page's ancestor paths read only the columns a path shows, not whole records. A page of deep
  records loaded 163 ORM rows for 20 records and now loads 84, on the per-type list and the lookup alike.

- 0.9.0-alpha.1 PG5: every volume budget re-measured on PostgreSQL. Statement and row budgets hold
  for every read; 143 of the 154 full-volume reads stay within 100 ms. The eleven over it (change-set
  matrix state filters, change-set searches matching nearly every record, the attribute sort under a
  20,000-child parent, the live history-only matrix filter) are deferred to the first fixes after
  1.0; `docs/POSTGRESQL_BUDGETS.md` holds the figures, causes and fix plan. Batches: 1,000 upserts in
  0.8 s, 10,000 atomic creates in 5.4 s live and 17.8 s in a change set, 100,000 background items in
  52 s live and 64 s in a change set (on SQLite 231 s and 663 s), with writes beside the job waiting
  0.35 s at most.
- 0.9.0-alpha.1 PG5: search reads trigram indexes on record names as well as values (revision
  `20261003_01`). The per-type list reads a search's candidates first and, with at most 1,000, reads
  only those records, in live data, a change set or a publication: a name or code search with its
  total over 100,000 records takes 12–23 ms in every context (was 50–226 ms on PostgreSQL before).
  Results are unchanged; a search matching very many records, or of one or two characters, matches
  every record as before. A search costs one statement more.
- 0.9.0-alpha.1 PG5: the relation matrix's state filter sends its matching rows to the database once
  per statement instead of once per part of it (change-set filters 210 → 136–154 ms), and the query
  constructs written to steer SQLite's planner are removed, which made change-set object pages, the
  ancestor criterion and history sorts faster on PostgreSQL (for example the ancestor criterion in a
  change set 141 → 69 ms).
- 0.9.0-alpha.1 PG5: version 0.9.0-alpha.1 (backend, API document, frontend package).

### Fixed

- 0.9.0-alpha.1 PG5: a 20-row relation expansion of a record with 20,000 relations
  (`expand` in the model query) took about 0.4 s on PostgreSQL: it walked the name index over every
  record of the workspace until 20 belonged to the record. It reads the record's relations first and
  their records by ID: about 70 ms.
- 0.9.0-alpha.1 PG5: a change-set read right after the change set was started from current live data
  could take seconds: on rows without statistics yet, PostgreSQL looked up each record's attribute
  value through an index that read every value of the attribute. That redundant index
  (`ix_snapshot_attribute_values_owner_key`) is dropped in revision `20261003_01`.
- The background job worker no longer spins when its database is unreachable. A failed first pass
  left its next sweep in the past, so it retried without waiting and logged a full traceback on
  every pass (3,111 attempts in half a second in the regression test; a 28 GB log overnight). It now
  waits its 2 s between retries, logs the traceback once per outage, then one line a minute, and
  says when the database is reachable again.
- The volume tests' statement counts no longer include the background job worker's own statements,
  which made a restructuring budget test fail when a run was slow.
- `python -m app.cli.model_schema_upgrade --help` names every supported schema (0.5–0.8); it
  named 0.5–0.7 while it also accepted 0.8.
- Startup refused with an unsupported model schema named the supported schemas as 0.5–0.7; it names
  every supported schema (0.5–0.8).

## [0.8.0] - 2026-09-29

### Added

- Base 0.8 R1b and R2 (2026-09-29): build acceptance of B5, B5b and Milestone C in one pass. The full
  backend suite, Vitest, all 22 browser runners and the accessibility and visual gates pass with no fix
  or re-baseline, and no migration is needed, so 0.8.0 is released (D43).
- Base 0.8 S1: a Track S volume fixture and read baseline. `tests/volume_fixture.py` generates a model
  with its own keys and bulk-seeds 10,000 root records, 100,000 contained records (20,000 under one
  parent), a seven-level self-hierarchy, a record with 1,500 relations of one type and a parent with
  children of two types, then records revision 1 and derives a draft with scattered edits, tombstones
  and new records. `tests/volume_baseline.py` measures time, SQL statements and ORM rows per request
  in live, draft and history contexts; the full-volume figures and the budgets are recorded in the
  Base 0.8 plan. The new `volume` test group holds the budgets at two scales: live reads and writes
  meet them, while draft/history reads and draft writes are strict expected failures until S2.
- Base 0.8 S2: draft and history reads in SQL. Migration `20260925_01` adds
  `snapshot_attribute_values`, a typed index of revision, draft-base and draft object values (D1),
  backfilled from existing rows and kept current by an ORM flush hook, plus ordered page indexes on
  revision and draft-base objects. Object pages, single records, attributes, relation pages and draft
  write responses read one base-plus-overlay statement instead of the whole draft or revision; at full
  volume a draft page takes 3–6 ms (was about 3.1 s) and a history page 2–5 ms (was 1.1–2.6 s). Live,
  draft and history share one object query builder, held by a parity test across all four contexts.

- Base 0.8 S3: cursor and position paging on every collection endpoint (ADR-030). Pages add
  `prevCursor`, an `anchor` that reopens the page, and with `includeTotal=true` a `totalCount` and
  `startIndex`; requests add `from=end`, `position=N` and, on object, relation and mapping-coverage
  lists, `seek=<value>`. Selecting a page two ways is refused with `422 conflicting_page_parameters`.
  Existing cursors keep working.
- Base 0.8 S4: `topLevel=true` on object lists pages records without a parent in every context;
  relation lists gain `search` (the related record's name and searchable fields) and `sort` (`name`,
  and `createdAt` live) in live, draft and history. Migration `20260925_02` adds (owner, endpoint,
  relation ID) indexes on revision, draft-base and draft relations, so a draft or history relation page reads the
  record's own relations instead of the whole revision.
- Live object page indexes (migration `20260925_03`): (workspace, type, name, sequence) and
  (workspace, parent, type, name, sequence). Name-ordered live pages past the first, their totals and
  position reads now seek instead of scanning the type: 2–13 ms at full volume (a deep position read
  took about 500 ms).

- Base 0.8 S5: continuous-scroll lists (ADR-030). `useCursorWindow` keeps at most five pages,
  prefetches one page ahead of either edge and evicts the page furthest from the viewport;
  `ui/ScrollWindow` keeps rows still as pages arrive above them, shows quiet start and end markers
  and a loading marker only while the user waits, and offers a proportional scrollbar sized from the
  total (a click or a drag's release sends one position request), a page field, start and end
  buttons, Ctrl+Home/Ctrl+End and, on the collection lens, **Go to** a value. Arrow keys move
  through rows across page boundaries. Adopted by the collection lens, record panels (which gain a
  sort, by name by default), relation panels (which gain search and sort), the mapping lens, the
  mapping candidates and the object picker, now a search field over a listbox.
  `tests/volume_seed.py` seeds the volume fixture for the new `test:browser:s5` runner.
- Base 0.8 S6: the sidebar record tree reads by parent. Each root (`rootCreatable`) type of the
  application pages its top-level records (`topLevel=true`) in its own bounded, scrolling group;
  expanding a record pages each child type separately with `parentObjectId`, headed by the type and
  its count, and collapsing releases the branch. **Load more objects** and the global per-type load
  are gone, and with them the record with an unloaded parent drawn at the top level. The tree is a
  `role="tree"` with one tab stop, `aria-setsize` and `aria-posinset` from totals and arrow keys that
  load across a window's edge. Search lists matching records of every type with their ancestor path.
  `ui/ScrollWindow` reads only its own rows, so windows nest, and gains a `group` role for rows owned
  by an enclosing widget. New runner `test:browser:s6`.
- Base 0.8 S7: composed Track S acceptance. New runner `test:browser:s7` walks one collection-lens
  journey per context (scroll, scrollbar click, seek, end, page number, copied URL) over the volume
  fixture and the starter model, checks each landing against the same context's API read, and opens a
  record deep in the tree; it passes at full volume (`S7_VOLUME_SCALE=1`). The accessibility and
  visual gates gain a `scrolling-list-tree` scenario in light and dark, and every visual baseline was
  refreshed after review. `volume_baseline.py` adds a whole-type name search and a deep record read.
- Base 0.8 S8: indexed search (D25). Migration `20260926_03` adds SQLite FTS5 trigram indexes over
  live and snapshot text values, kept equal to the values by triggers on every write. A search of
  three or more characters looks up values only for the records the index names, and still decides
  with the same case-insensitive "contains" match, so results are unchanged in every context. A
  whole-type name search with its total at 100,000 records takes 37 ms live, 73 ms in a draft and
  40 ms in history (was 0.7–0.9 s). Names stay on the (type, name) index; one- and two-character
  searches, and phrases in more than 10,000 values, read each record as before.
- Base 0.8 W6: delete an unused workspace to correct a mistyped key (ADR-019 amendment, D27).
  `DELETE /workspaces/{key}?expectedVersion=N` removes a workspace that is not the default, was never
  published and has no objects or change sets, active or retired; the key can be created again. It
  refuses with `workspace_is_default`, `workspace_has_publications`, `workspace_not_empty` (with
  counts) or `version_conflict`, changing nothing, and is gated by `WORKSPACE_ADMIN_MUTATIONS_ENABLED`.
  Single-workspace responses add `deletable` and `deleteBlockedBy` (OpenAPI lock re-baselined). The
  Workspaces screen offers **Delete…** with a confirmation naming the key, or says why it cannot.
- Base 0.8 A1: the schema 0.7 `relationMatrix` view contract (D8, D9). Rows are records of one type,
  columns the records of a type that can contain the cell type at some depth, and a cell the row's
  related records through one binding, read from either end (`direction`), required or optional, of
  any cardinality. A view declares `rowColumns`, `columnLabelField`, `cellFields`, `searchFields` and a
  closed `cellActions` set (`create`, `edit`, `link`, `unlink`); an action that could never succeed for
  the model is refused. Each failure points at the failing config node, and schema 0.5 and 0.6 models
  refuse the view at its `type`. The view groups as a lens of its row type's collection and renders a
  placeholder until A4. The starter (still content 0.8.0) configures it three ways: codelist and
  master-value translations by language, codelists by system and master values by system; the
  translations and systems applications now include codelists.
- Base 0.8 A2: `GET /api/v1/workspaces/{workspaceKey}/relation-matrix` reads a `relationMatrix` view in
  live, change-set and publication contexts. Rows page like any collection (cursor, position, seek,
  totals), searching the view's `searchFields`; columns are named with `columnIds` (at most 20) or
  paged by name with their own cursor (D10). Each cell reports `one`, `several` (with `conflict` when
  the binding's uniqueness scope is the column type), `inactive`, `historyOnly` or `none` (D11), with
  counts, up to five records with their `cellFields`, versions and relation IDs, and each row its
  relation-set version. `state` with `columnIds` filters rows across the whole list before paging, by
  one recursive walk down from the selected columns (D12); at full volume the filter is over its time
  budget (seconds), a temporary exception that A3b's stored cell state removes (D12). A page costs a fixed number of statements.
  The volume fixture gains a `vol-matrix` application (30 columns, a three-level container hierarchy,
  150,000 cells at full scale, an outgoing conditioned and an incoming many-to-many matrix), measured
  with the other reads; the generated model is now schema 0.7. Object query builders accept a
  view's search fields and an ID predicate that also narrows a change set's overlay parts.
- Base 0.8 A3: writes from a relation matrix cell, live or in a change set, through the generic
  object and relation APIs. `GET …/relation-matrix/containers` lists where a new cell record can go
  (the column record and the records under it that can directly contain the cell type, with their
  path), naming the column's only container as `defaultContainerId` (D13).
  `GET …/relation-matrix/link-candidates` lists the cell-type records under a column record for a
  row, the ineligible ones with a reason (`alreadyLinked`, `rowCardinality`, `candidateCardinality`,
  `scopeTaken`). Relation create and delete accept an optional relation-set claim
  (`expectedRelationSetVersion`, `relationSetDirection`) and refuse a stale one with
  `409 relation_set_version_conflict`; a claimed create returns the set's new version. Cell records
  carry `relationVersion`. OpenAPI lock re-baselined; the paging inventory counts 20 collections.
- Base 0.8 A3b: stored relation matrix cell states (ADR-033). Migration `20260927_01` adds
  `matrix_cell_states` and `matrix_state_builds`; the application builds every missing owner (live,
  publication, change set base, change set overlay, publication history) and matrix shape at startup,
  on model activation and when change sets and publications are created, and recomputes the rows a
  write touches before it commits. The row state filter reads them by index, once per request, and
  derives cells from records only where a context is not built. The API contract is unchanged.
  `matrix_states.verify` rebuilds and compares every stored state; matrix tests run it after each test.
- Base 0.8 A4: the relation matrix lens replaces the A1 placeholder. Rows scroll as every list does,
  the row header stays pinned with the view's row columns, and columns are the ones chosen in the
  Filter popover or a page of the column type, paged sideways. Each cell shows its state with an icon
  and a label, explained by a legend of the states the binding can produce. The Filter popover chooses
  the columns (searchable) and a cell state; both live in the URL. The grid is keyboard operable
  (arrow keys across cells and pages, Enter to open). A cell's dialog offers only the view's
  `cellActions`: create (the column's only container preselected, otherwise a searchable picker;
  **Create from this** for a history-only cell), edit, link (candidates listed with the reason any
  cannot be linked) and unlink, live or in the selected change set, and read-only in a publication.
  A save re-reads only that cell. `ScrollWindow` keeps a grid cell's column on Up and Down. New
  browser runner `test:browser:a4`.
- Base 0.8 A5: Milestone A acceptance. Browser runner `test:browser:a5` runs SC-09's translation half
  by keyboard (fill a missing translation live, a refused duplicate, restore one from history in a
  change set and publish it from the change set screen), links and unlinks a system value, and fills
  a cell on the generated volume model. The accessibility and visual gates gain the relation matrix,
  its cell dialog and Filter popover in light and dark, with four reviewed baselines. Full-volume
  matrix reads measure 23–82 ms in every context, within the 100 ms budget.
- Base 0.8 B1: the schema 0.7 `tree` view contract (D9). A tree declares its `rootObjectTypeKeys`, the
  node types it shows (`objectTypeKeys`), a `labelField`, an optional `secondaryField`, a `childSort`
  per node type, a `pageSize` and a closed `actions` set (`createChild`, `rename`, `move`,
  `setAvailability`, the last with a boolean `availabilityField`). A node type unreachable from the
  roots through the types the tree shows, a root type that cannot stand without a parent, a field
  missing from a node type and an action that could never succeed are each refused at the failing
  config node; schema 0.5 and 0.6 models refuse the view at its `type`. The view groups as a lens of
  its first root type's collection and renders a placeholder until B3. The starter (still content
  0.8.0) adds a system hierarchy (systems, recursive system groups, system values) and a domain
  hierarchy (domains, codelists, master values); the generated volume model adds one over its groups,
  items and deep node self-hierarchy. The Domains and Systems tables gain a lens switch; four visual
  baselines were updated after inspection.
- Base 0.8 B2: move targets. `GET /api/v1/objects/{type}/{id}/parent-candidates` lists every record of
  a type that can contain the record, in its application and workspace, live or in a change set, in
  name order with search, cursors, positions and totals. A candidate the move would refuse or not
  change stays listed with `eligible: false` and a `reason` (`self`, `descendant`, `currentParent`;
  D14), and every candidate carries its root-first `path`. The generated volume model lets groups
  nest, so a record with 20,000 records under it can move.
- Base 0.8 B3: the tree lens replaces the B1 placeholder. It shows the view's root types, and under
  each record one branch per child type the tree shows, ordered by the view's `childSort` and paged by
  its `pageSize`, with the `labelField`, `secondaryField` and, where declared, the availability field.
  It reuses the sidebar tree (S6): bounded scrolling branches, totals, one tab stop and arrow keys, plus
  type-ahead (a space typed mid-word continues it). A search result, and the record open beside the
  tree (also after a reload, Back or Forward), is revealed where it sits: each branch on its path
  opens at it with `seek`, and unrelated branches stay closed. Records open in the inspector beside
  the tree (the retained split view), full width below 1080px. The view's `actions` come from a node's menu
  (Shift+F10, the context menu key or the row's ⋯): add a child of each type the node can contain (the
  new node appears in its branch with focus), rename in place (F2), set availability (also the row's
  switch) and **Move to…**, a dialog over the B2 candidates where ineligible targets are listed
  disabled with their reason; a move keeps focus on the moved node and refreshes both branches. A
  refused write keeps the user's input and place. Writes go to the selected change set; a
  publication's tree is read-only. New browser runner `test:browser:b3`.
- Base 0.8 B4: Milestone B acceptance. Browser runner `test:browser:b4` runs SC-09's hierarchy half by
  keyboard on the system hierarchy (live, 1440px) and the domain hierarchy's nested master values
  (live, 390px): find a nested record reading only its ancestors' branches, add a child and a
  grandchild, be refused the move beneath the grandchild in the dialog and by the API, move the child
  and see its new path in the tree and breadcrumb with its containment edge changed and unrelated
  branches unchanged. A move staged in a change set reaches live only when the change set is
  published. The accessibility and visual gates gain the tree lens and its move dialog in light and
  dark, with four reviewed baselines. The tree lens's keyboard helpers are shared by both runners
  (`e2e/helpers/tree.mjs`).
- Base 0.8 P2a: change lists. `GET /api/v1/change-sets/{id}/object-changes` and
  `/relation-changes` list only what a change set changes, read against its source: each record or
  relation it touched as `added`, `changed` or `removed` (D31), with `before` (the source's row) and
  `after` (the change set's), typed values in the object read's shape, `changedFields` and, for
  records, the path. A record created and deleted inside the change set is left out, as publishing
  skips it; one edited back to its source values stays listed with no changed fields. Relation
  entries name both ends and mark engine-maintained parent edges with `containment` (D32), so a move
  is a `changed` record with `parent` plus one removed and one added edge. Filters by kind, type and
  containment; every paging mode. The volume fixture gains a review change set touching 12,073
  records and 8,273 relations at full volume, where every measured page takes 3–52 ms in 4–6
  statements.
- Base 0.8 P2b: change set review screen. **Review changes** on the change set bar (and a link in the
  publish confirmation) opens `/apps/{app}/change-sets/{id}/changes`: **Records** and
  **Relationships** tabs, each a continuous list of what the change set adds, changes and removes, with
  a kind badge in words, the type and model labels from the change set's model, the path or both
  ends, and the changed fields. A row expands to a before/after table of those fields with typed
  values as the record screen shows them; a moved record names its old and new parent. Added and
  changed records open in the change set. Filter by kind and type; parent links are hidden from
  Relationships unless asked for (D32). Tab, filters and scroll position live in the URL. The object
  change entry gains `beforePath`, where the source held a moved record, read in the same walk as
  `path`. New runner `test:browser:p2`; the accessibility and visual gates gain the review in light
  and dark.
- Base 0.8 B5: drag and drop in the tree lens, a second way to **Move to…** for mouse and pen where
  the view allows moves, live and in a change set. Drop onto a record, into a gap between rows (the
  branch the gap belongs to; at a branch end the pointer's horizontal position picks the level, shown
  by the drop line's indent) or onto a type heading (its parent). While dragging, the record's row is
  dimmed and a preview names it; an accepted target glows green, a refused one red with its reason as
  text (**The record itself**, **Inside the record**, **Current location**, **Can't contain …**,
  **In another application**) and a no-drop cursor. Resting on a collapsed record opens it, and the
  tree scrolls near its edges. A drop opens the move dialog with the target chosen, so Enter confirms
  the same write as Move to…; Escape or a release elsewhere writes nothing. Touch pointers, the
  sidebar tree and publications never drag (touch drag in 0.11, D35). `test:browser:b3` gains the
  drags; the accessibility and visual gates gain a drag over an accepted and a refused target, light
  and dark.
- Base 0.8 B5b: moving a record to the top level from the tree lens, by both paths (D36). **Move to…**
  lists **Top level** above the candidates, outside the paged list, and confirming writes no parent.
  Dragging onto a top-level heading, into a gap between top-level rows or to the left end of a gap
  that ends branches down to the top level offers it too, and the drop opens the dialog with **Top
  level** chosen. Only a nested record of one of the tree's root types goes there; any other type is
  refused as **Not shown at the top of this tree**, and a record already there as **Current
  location**. A search's matches offer no top level. `test:browser:b3` moves a nested group of the
  generated volume tree to the top live by Move to… and in a change set by a drag.
- Base 0.8 C1: a record's type can change in a change set (ADR-034). `services/type_changes.py`
  changes one record's type, optionally under a new parent, with a given attribute mapping: values
  are kept, mapped (same value type, or `text` to `longText` and `integer` to `decimal`), restored or
  given as inputs, and the rest have no place; the containment edge becomes the relation the model
  allows, and each child's edge the relation the new type contains it by; relationships the new type
  may not have are removed and the others keep their IDs; relationships offered back are restored
  under their former IDs, and required relationships are inputs. Uniqueness, required values and
  relations, uniqueness scopes, cycles and the record version are checked by the change set write
  services, and `check_type_change` runs every check without keeping a write. Each change records a
  `reclassified` audit event with the full before state, which the history read lists with
  `changedFields` and `attributeTypeKeys`. Publishing needed no change: it writes the new type to
  live and refuses a live edit of the record or a live relationship the new type cannot have. The
  restructuring API that exposes the service is C3.
- Base 0.8 C2: the restructuring planner (`services/restructuring.py`) plans a move or a type change
  of one record and its subtree in a change set. It works out the possible types at the target and
  asks once per (type, parent type) pair where several are possible; cascades level by level, each
  child the new parent cannot contain becoming a type it can; suggests each attribute's source by the
  D40 rules, which a choice per type pair overrides; and lists per record what is kept, mapped,
  restored, given or without a place, the inputs still needed and the refusals. Values and
  relationships are offered back from the record's reclassifications in the current change set and in
  published ones, relationships under their former IDs. A ready plan is dry-run through the change set
  write services and rolled back; its digest binds an apply to the previewed plan and the change set
  version. More than 500 records is refused with `restructuring_too_large`: D44 lowers C0's 5,000
  because the dry run takes 48 s at that size and 2.8 s at 500. The routes are C3.
- Base 0.8 C3: the restructuring API. `POST /api/v1/change-sets/{id}/restructurings/preview` plans an
  operation and writes nothing; `POST /api/v1/change-sets/{id}/restructurings` applies it when the
  recomputed plan matches the previewed `planDigest` and the change set is still at
  `expectedChangeSetVersion` (`409 restructuring_plan_changed`, `409 change_set_version_conflict`,
  `422 restructuring_not_ready`). Five kinds: `move` (with a type change where the target needs it),
  `changeType`, `insertLevel` (a new record between a parent and chosen children, its values given
  under the ID `new`, its ID returned as `createdObjectId`), `removeLevel` (a record deleted with its
  relationships, its children moved to its parent, changing type where needed) and `changeTypeUnder`
  (every record of one type under a record). The plan's records page by position in plan order with
  the standard page links, filtered by `outcome`; cursors bind the change set version and the plan.
  Parent candidates take `includeTypeChanges=true` in a change set, listing the records a move with a
  type change could go under, each with `objectTypeKeys`.
- Base 0.8 C4: restructuring in the tree lens, in a change set only. **Move to…** and a drag also
  offer places where the record's type cannot stand but another type of the tree can: the candidate
  and the drag say **Becomes <type>**, and choosing one opens a preview instead of moving. The node
  menu adds **Change type…**, **Insert level above…**, **Remove this level…** and **Change type of all
  <type> in here…**, each only where the model makes it possible. The preview shows the plan by
  record (new type and place, each value's origin, what has no place, what is restored, inputs asked
  in place) and by type pair (each attribute's source changeable in place), answers type questions,
  lists refusals, applies the reviewed plan and links to the change set's review. **Insert level
  above…** lists the record's siblings to choose more records to group under the new level.
- Base 0.8 C4 (D45): `GET /api/v1/model/placements` serves where the context's model lets records
  stand, per application: the types at the top and, per parent type, the types it contains and the
  types a record can become under it. It is the engine's one rule (`services/model/placements.py`);
  the browser loads it with the model and no longer derives containment itself.
- Base 0.8 C4: parent candidates take a repeatable `withinObjectTypeKey`, keeping the candidates and,
  with `includeTypeChanges`, the types the record would become to a set of types; the server filters,
  so totals stay truthful. The tree lens passes its types, so Move to… offers what the drag offers.
- Base 0.8 C5: Milestone C acceptance. `test:browser:c5` runs the restructuring journey on the starter
  model and the generated model against a real backend: a move that reshapes a subtree across two
  levels of types, answering the preview in place, inserting and removing a level, the review,
  publishing from the change set screen, live, the publication and both ends' history, then changing a
  record back in a second change set with its values or its relationship restored. The accessibility
  and visual gates add Move to… with a type change, the preview by record and by type, and the insert,
  remove and change type dialogs, light and dark. User story US-H03 and scenario SC-17.

### Changed
- Base 0.8 C4: the change set review names a record's type change on its row and as **Type** in its
  before/after table. The browser follows a record opened under a type it no longer has to its
  current route (D42), replacing the old route and keeping focus. In a change set, a tree lens record
  dragged to a place its type cannot stand, such as an item to the top level, now becomes a type that
  can (B5b refused it); live, such a place's reason adds that a change set can change the type. A
  cursor list's reload whose anchor went stale reopens at the start instead of failing.
- Base 0.8 C1 (D42): every `/objects/{objectTypeKey}/{objectId}` route answers
  `409 object_type_changed` with the record's current type for a record found under another type in
  the selected context, live, in a change set or in a publication, where it answered `404
  object_not_found`. A change-set `PATCH` now checks the route's type, which it ignored. The change
  lists' object entries carry `objectTypeKey` on `before` and `after`, name `objectType` first in
  `changedFields` when it changed, and the `objectTypeKey` filter matches either side; a relation
  entry is `containment` by the type its `to` end has on either side.

- Design: Base 0.9 integration APIs. Decisions D1–D16 and CONSUMER_API C-D2–C-D16 are accepted. A code
  check revised D5: the feed is positioned by a per-workspace counter taken under the workspace lock
  until commit, so feed order is commit order on PostgreSQL too; and added D15 (a publish writes one
  audit entry per record it applies to live) and D16 (feeds carry keys, never the `reclassified`
  before state). `docs/INTEGRATION_API.md` gains sections B (batches with record references, upsert,
  relation items and relation-set replacement), F (the workspace change feed, position, retention and
  `410` recovery), Q (cross-type lookup, `/workspaces/{key}/relations`, the model-aware query and
  `asOf`) and J (import with preview and confirm, the file contract, the import profile with a generic
  `relatedRecord` binding, and export). APPLICATION_MODEL describes schema 0.8 (`effectivePeriod`,
  `consumerApis`). ADR-036 (a batch is a job), ADR-037 (the audit log orders the feed and consumer
  events) and ADR-038 (effective periods) are accepted.
- Planning: the Base 0.9 plan follows the 0.8 layout: how a package is delivered, a numbered delivery
  queue with dependencies and the D9 cut line, and work packages Q1–Q4, B1–B3, F1–F2, V1–V2 and
  J1–J4 with design references, scope, tests, budgets, test groups and exits, the C1–C16 table and R
  build acceptance. New test groups `jobs`, `feed` and `consumer` and runners `test:browser:v1` and
  `test:browser:j4` are planned. The API reference track is renamed V.
- Design: Product 0.10 is model authoring and spreadsheet onboarding (ADR-035,
  `docs/MODEL_AUTHORING.md`): one editor for the model and the import mapping, where every edit is a
  validated operation on a model draft, inference from an uploaded workbook proposes operations, and
  saved import profiles load the next version as a reviewed upsert. Production hardening moves to
  0.11 and security to 0.12 across the documentation; 1.0 keeps changes to released structure,
  protected publishing and extensions. 0.9 D3 is revised: import runs an import profile, with XLSX.
  New stories US-P09 and US-P10. A-D1–A-D3 decided (one type per list, declared navigation groups,
  profiles stored apart from releases). `docs/BASE_0_10_IMPLEMENTATION_PLAN.md` is the provisional
  0.10 plan: packages A0–A8 and R, synthetic acceptance workbooks, decisions D1–D10.
- Design: Base 0.8 C0. ADR-034 accepts that a record's type can change, keeping its ID, in a change set
  only, within its application. The attribute mapping is derived from the model (same value type or a
  lossless widening), relationships are kept or removed, and descendants follow level by level. An
  operation is previewed, then applied against the change set version and the plan's digest. Each type
  change records a `reclassified` audit event with the full before state, and later type changes offer
  its values and relationships back. A route naming another type than the record's returns
  `409 object_type_changed`. One operation changes at most 5,000 records. API.md gains the restructuring
  API design (`/change-sets/{id}/restructurings[/preview]`). D37–D43 are accepted; 0.8.0 now waits for
  Milestone C and R2 (D43).
- Planning: Base 0.8 Milestone C, structure refactoring (C0–C5, R2 build acceptance), for delivery before
  0.9. A record's type changes when it moves where only another type is allowed. The new type and the
  attribute mapping are derived from the model, with no declarations, and confirmed in a preview.
  Values without a place stay in history and are offered back later. Named refactorings (change type,
  insert or remove a level, change type under a record) run in a change set. D37–D43 are open.
- Planning: Base 0.8 B5, drag and drop in the tree lens, added in the Milestone B review. Records can be
  dropped onto a node, into a gap between rows or onto a type heading. Drops are accepted by the
  model's containment rules, show a green or red glow with the reason, and are confirmed in the
  existing move dialog. D34 decides the targets and the confirmation; D35 defers touch drag to 0.11.
  B5b, an amendment to B5, adds moving a record to the top level in Move to… and by drag, for the
  tree's root types (D36). R1b is added as an amendment to R1: the build acceptance for B5 and B5b,
  required before 0.8.0 releases. One record is moved at a time.
- Documentation: the bundled model is described as an example set. `docs/EXAMPLE_MODEL.md` explains
  how engine, model and application relate, lists the views each example application declares and
  explains why they differ (only the example's declarations, never the application). It also shows
  what each gap would take. README, AGENTS, PRODUCT, APPLICATION_MODEL, UI_MODEL and the functionality
  catalogue state that every application gets the same feature set. Milestone A is named the Relation
  matrix throughout, with ADR-031 and the W1 note amended.
- Base 0.8 B3: the sidebar tree's tab stop returns to the open record once it is drawn, unless the
  user has since focused another item; it also gains type-ahead. A record's inspector re-reads the
  record when the collection beside it writes, and a narrow inspector wraps the record's actions
  below its title.
- Base 0.8 B2: moving a record costs about what a rename does, however much lies under it. A live
  update re-checked ancestor-scoped uniqueness for every relation into the record's whole subtree on
  every write, rename included; it now checks nothing for a rename, the record's own relations for a
  value change, and after a move only the records below whose scope record is above the moved one,
  for bindings that declare a scope. Stored matrix cell states no longer walk down from a moved
  record that can hold no cell below a column, recompute a written relation's ends only in shapes of
  its relation type, and find a cell record's rows by its own endpoint index. Moving the
  20,000-descendant record at full volume takes 6 ms live (was 773 ms) and 13 ms in a change set (was
  53 ms), and a change set rename 8 ms (was 17 ms). Moving a container of about 2,500 matrix cells
  stays seconds in both contexts and is a known 0.8 budget exception (D29).
- Base 0.8 A6: a migrated database now has the schema the ORM declares (D28). Ten single-column
  indexes declared on publication and change set tables were never created by a migration. Migration
  `20260928_01` gives `change_set_objects` the (owner, type, name, object) and (owner, parent, type,
  name, object) indexes the publication and base object tables have, so relation matrix walks through
  a change set seek children by parent instead of building an automatic index per statement; the
  other eight declarations are removed because owner-leading indexes already serve every read, and a
  database built by an earlier `create_all` loses them on upgrade. New `test_schema_drift` fails on
  any difference between a migrated head and the metadata. Volume budgets and statement counts are
  unchanged.
- Base 0.8 A5: a relation matrix cell refused for uniqueness says so in the view's terms, naming the
  row, the column (or the scope) and the condition, for example "Delivery Methods already has a
  translation in cs where Active is Yes, and only one may count there.", instead of the API's generic
  "A related object already exists for this ancestor scope". The API is unchanged.
- Base 0.8 A3: relations an object create adds through `initialRelations` now advance both ends'
  relation-set versions, live and in change sets, like every other relation write (ADR-022); a
  matrix row's `relationSetVersion` therefore counts them. `409 duplicate_relation_scope` on relation
  and object writes names the record already in the scope (`conflictingObjectId`,
  `conflictingRelationId`); the change set diagnostic adds `conflictingObjectId`.

- Base 0.8 W4: a global **Workspaces** screen beside **Models**, in the same list-and-detail layout,
  lists every workspace including retired ones and creates, renames, retires, reactivates and sets
  the default with their version claims; a conflict shows the current state and is never retried.
  It appears in the header, and as **Manage workspaces** in the workspace selector, only when
  `workspaceAdmin.manageWorkspaces` is true. The selector is a read-only label while one workspace
  exists. Models and Workspaces show the deployment capabilities read only, naming the setting of a
  disabled group, which `GET /capabilities` now reports in each group's new `setting` field
  (OpenAPI lock re-baselined). The narrow navigation drawer is titled for its screen. New browser
  runner `test:browser:w4`; the a11y and visual gates gain `workspaces-admin` light and dark, and
  every shell baseline was refreshed for the header entry and the single-workspace label.
- Base 0.8 W3: `WORKSPACE_ADMIN_MUTATIONS_ENABLED` gates only workspace create, rename, retire and
  set default (ADR-031). Change-set create, update, delete, model-release change, validation and
  publish, and publication withdrawal, are always registered and still refused in a retired
  workspace. Their OpenAPI tag is `change-sets`.
- Base 0.8 W2: data drafts are **change sets** and workspace revisions are **publications** in every
  layer (ADR-031), with no aliases. Breaking API changes:
  - Routes: `/workspaces/{key}/drafts` → `/workspaces/{key}/change-sets`,
    `/workspace-drafts/{id}` → `/change-sets/{id}`, `/workspace-drafts/{id}/activation` →
    `/change-sets/{id}/publication`, `/workspaces/{key}/drafts/{id}/model-release` →
    `/change-sets/{id}/model-release`, `/workspaces/{key}/revisions` → `/workspaces/{key}/publications`,
    `/workspace-revisions/{id}` → `/publications/{id}`, and `POST /workspaces/{key}/retirement` with
    `expectedActiveRevisionId` → `POST /publications/{id}/withdrawal` with no body (the path ID is the
    claim). Lists stay under their workspace; single items are flat by global ID.
  - Fields and parameters: `workspaceDraftId` → `changeSetId`, `workspaceRevisionId` →
    `publicationId`, `expectedWorkspaceDraftVersion` and `expectedDraftVersion` →
    `expectedChangeSetVersion`, `workspaceDraftVersion` → `changeSetVersion`,
    `expectedActiveRevisionId` → `expectedActivePublicationId`, `derivedFromRevisionId` →
    `derivedFromPublicationId`, `supersedesRevisionId` → `supersedesPublicationId`, `revisionNumber`
    → `publicationNumber`, `activatedAt` → `publishedAt`, `retiredAt` → `withdrawnAt`, source
    `"revision"` → `"publication"` and publication status `retired` → `withdrawn`. A publication also
    returns `modelReleaseKey` and `modelReleaseVersion`.
  - Error codes: `workspace_draft_*` → `change_set_*` (`change_set_not_found`,
    `change_set_version_conflict`, `change_set_model_release_conflict`, `change_set_required`,
    `change_set_snapshot_retry`, `change_set_snapshot_unsupported`), `draft_content_incompatible` →
    `change_set_content_incompatible`, `workspace_revision_not_found` → `publication_not_found` and
    `workspace_active_revision_conflict` → `workspace_active_publication_conflict`.

  Migration `20260926_04` rebuilds the draft and revision tables as `change_set*` and `publication*`
  with their columns, indexes and constraints, renames `workspaces.active_revision_id` and
  `relation_set_versions.workspace_draft_id`, records snapshot value owners as `publication`, `base`
  and `change_set`, and rewrites stored audit names (`change-set`, `change-set-object`,
  `publication`/`published`, `publication-withdrawn`) and payload keys. It resumes an interrupted run
  on SQLite and refuses another dialect with a recovery instruction. The browser says "Change set ·
  name", "Publish change set", "Publication N" with its model release and date, and "Withdraw
  publication"; its URLs are `/apps/{app}/change-sets` and `/apps/{app}/publications` with
  `changeSetId` and `publicationId`. The OpenAPI lock is re-baselined, the `drafts` test marker is
  `change_sets`, and the WP9 runners are `test:browser:change-sets` and `test:browser:publications`.
- Base 0.8 W1: documentation adopts the ADR-031 terms. The glossary defines workspace, live, change
  set, publication ("Publication N" and its per-workspace number), model draft, model release, and the
  verbs publish, install, activate, withdraw and retire, with a diagram of one workspace's live data,
  change sets and publications and a note on the old names the code keeps until W2. Milestones A and B
  are renamed **Translation editor** and **Hierarchy editor** in the roadmap, TODO, the 0.8 plan and the
  functionality catalogue. The stale "non-default workspace detail gap" notes in PRODUCT, the product
  guide, user journeys, user stories and the functionality catalogue are corrected: 0.6 WP9 repaired
  the context handoff, and the WP9 navigation runner opens detail, children, relationships and
  history in a non-default workspace.
- Base 0.8 S8: a draft list's total counts its base, less the rows the draft replaces, plus its own
  rows, instead of the union (a total at full volume in 19–31 ms, was 45–56 ms); a first or
  position page that reaches the end of its list returns its total without a count.
- Base 0.8 S4R1: relation lists sort and search the related record through the object query
  builder, as object lists do. `sort` takes `name` (now the default in every context), any
  `sortable` attribute of the related type, `ancestor:<type>`, and live only the related record's
  `createdAt`/`updatedAt`; relation creation order is no longer a sort. Attribute and ancestor sorts
  need the listed relations to reach one object type (`422 invalid_sort` otherwise), and
  `relationTypeKey` repeats to list several relation types. Search covers the related types'
  searchable fields instead of every searchable attribute type. Draft and history object and
  relation pages return each record's `path` (it was empty, so ancestor columns were blank), and a
  relation page for a record the context does not hold answers `404` as it does live. Migration
  `20260926_01` rebuilds the draft and history relation endpoint indexes to cover the relation type
  and the other end. Relation cursors issued before the change are refused with `422 invalid_cursor`.
- Base 0.8 S4R2: schema 0.7. The engine accepts `schemaVersion: "0.7"` beside 0.5 and 0.6 in
  validation, the registry, releases, `model_schema_upgrade` and the startup message. Relations
  panels may declare `sortFields` and `defaultSort` (D21), validated against what the relation list
  accepts: `name`, a sortable attribute of the one related type, or an ancestor it can sit under;
  a 0.5 or 0.6 model declaring them is refused at the field's path, and absent fields stay out of the
  canonical document so earlier releases keep their hash. The starter model moves to schema 0.7,
  content release 0.8.0: its system panels sort by system, value code and name, its translation
  panels by language, translated name and name, and `translated-name` becomes sortable.
- Base 0.8 S4R3: one sort element for table-shaped lists (`ui/TableSort`), and one rule: every data
  column sorts. Column headers sort: a quiet sort icon on hover and focus (drawn in the header's
  padding, so columns never widen), an accent up or down arrow on the sorted column, activation toggling
  the direction, `aria-sort`, an accessible name stating the order and a polite announcement. Every
  list with sort fields shows the same icon-only **Sort** menu in its toolbar (radio items per field
  plus the direction, with a tooltip), which also reaches columns collapsed at 390px or hidden through
  Display and fields a view or panel declares without a column. The collection lens, record panels and
  relation panels use it. Removed: the lens toolbar's **Sort** popover and the relation panel's inline
  **Sort** select with its fixed name and creation-time options. `ui/ActionMenu` gains radio sections,
  a trigger icon and a tooltip.
- Sorting no longer depends on the attribute type's `sortable` flag: object and relation lists sort by
  any non-JSON attribute, and a relation list over several related types sorts by an attribute with
  records whose type lacks it last. `objectType` sorts by the type's model name and, on relation
  lists, `relationship` by the label each row shows, both then by name. The only data columns that do
  not sort are the computed path, JSON attributes and, outside live data, the unrecorded timestamps.
  Model validation follows: view and relations-panel sort fields accept any non-JSON attribute plus
  `objectType` and (panels) `relationship`, and a relations panel may declare `defaultSort` alone.
  The OpenAPI lock is re-baselined for the two `sort` descriptions.
- Collection URLs hold one `anchor` cursor for the page at the top of the list instead of a
  `cursor` trail, written as the user scrolls without adding history entries. Older links with
  `cursor` parameters open at the start. Previous/Next page buttons and **Load more** in panels,
  relation lists and pickers are removed.
- Page responses carry the new navigation fields beside `items` and `nextCursor`, so a client that
  compared a whole page body must allow them. Live relation pages build their related records in one
  batch instead of two statements per row.
- Draft and history `search` matches the record name and `searchable` fields, as live search does,
  instead of every attribute's text. Draft and history cursors issued before the upgrade are refused
  with `422 invalid_cursor`; restart from the first page.

- Base 0.8 S4R4: object lists without `sort` order by name in live, draft and history (live used
  creation order, drafts and history record ID), so the object picker and Explorer search results
  list by name and an unsorted list accepts `seek` by name. Mapping coverage and candidates list by
  name, and coverage `seek` takes a source name instead of an ID. Cursors issued for the former
  default orders are refused with `422 invalid_cursor`; reload from the first page.
- Base 0.8 S4R5: every page lists `items` first, then its navigation fields. `totalCount` and
  `startIndex` are omitted unless `includeTotal=true` instead of returned as `null`, and OpenAPI
  documents them as optional integers. Clients that tested them for `null` should test for absence.
- Base 0.8 S4R6: a draft position read resolves in its base's index and corrects for the draft's
  own rows, instead of skipping every earlier row through the base-plus-overlay union. Three quarters
  into a whole 100,000-record type it takes 60 ms (was 175 ms; about 40 ms of it is the total count), and
  its cost no longer grows with the position.

### Fixed

- Base 0.8 C5: change set validation, which publishing also runs, rescanned every record or relation
  for each record or relation in its uniqueness, parent-edge, cardinality, scoped-uniqueness and
  required-relation checks. Over the generated model at 2% volume (about 5,400 records) it took 125 s
  for an unchanged change set; it now reads indexes built once and takes about 1.4 s, with the same
  diagnostics in the same order.
- Base 0.8 C5: a record whose type changed and which was then removed in the same change set was
  listed in `object-changes` with `objectType` among its changed fields although it has no after side,
  and the review showed it as **<type> → Unknown type**. A removed record now names only the fields its
  source holds, in its source type's order, and the review names it by the type its source holds.
- Base 0.8 C5: after a restructuring, the tree lens moved focus to the restructured record once its
  reveal read returned, even when the user had gone on to the lens search meanwhile, so the rest of
  what they typed went to the tree. The record now becomes the tree's tab stop without taking focus
  unless focus is still in the tree.
- Base 0.8 C5: the restructuring preview's needs-input status began its second sentence in lower case,
  and values without a place showed booleans as `true`/`false` instead of Yes/No.

- Base 0.8 R1 review: the change lists (`object-changes`, `relation-changes`) read their page, then
  its paths and relation ends in further statements without holding one snapshot, so a change set
  write committed in between could mix two states in one page (a renamed parent in paths beside its
  own entry under the old name; after a concurrent publish, parent links without their end's type).
  Both routes now read one snapshot, as the relation matrix and parent candidates do.
- Base 0.8 R1: two browser runners no 0.8 package selected had drifted from the 0.8.0 starter model.
  `test:browser:sc15`'s incompatible candidate (a newly required `external-id`) was refused as a model
  because the `codelists-by-system` matrix offers `create` without it; the candidate now also asks for
  the field there, so it is refused for its data again. `test:browser:wp13c` asserted that RDM Systems
  offers no Codelist parent for a new master value, which the 0.8.0 model changes by adding codelists
  to RDM Systems; it now expects exactly the parent types the application contains, read from the model.
- Base 0.8 A review: when a relation matrix cell's edit or unlink was refused as stale and the re-read
  cell no longer held that record, the cell dialog went blank with no way on but Escape. It now shows
  the cell again with its actions and says the record is no longer in it. Starting another action
  from the cell clears the earlier notice.
- Base 0.8 A review: a relation matrix kept showing cells re-read after earlier saves over a page it
  had reloaded, so a cell changed elsewhere since could stay stale. The reloaded rows now replace
  them.
- Base 0.8 A1: a duplicate `mappingGrid` `sourceColumns`, `targetDisplayColumns` or
  `candidateSearchFields` entry was reported at `…/config/config/<field>`, a pointer to no node in
  the model; it is now `…/config/<field>`.
- Base 0.8 W6 review: on the Workspaces screen, creating a workspace after deleting one no longer
  leaves the "was deleted" notice above the new workspace.
- Base 0.8 W6: a live write that resolved its workspace before the workspace was retired, or deleted,
  could still commit into it. It now rereads the workspace inside its transaction and returns
  `409 workspace_retired` or `404 workspace_not_found`, saving nothing.
- Base 0.8 W5: a live write validated under one model release could commit after another release
  was activated, storing data the new release does not allow. The write now rereads the active
  release inside its transaction and returns `409 model_release_changed`, saving nothing; activation
  reserves the database writer before its compatibility check, and returns
  `409 model_activation_retry` if live writes keep it busy. Holds in one process and across
  instances sharing a SQLite database.
- Base 0.8 S8 review: the trigram search index is SQLite-only. Migration `20260926_03` changes
  nothing on another dialect (it stopped a PostgreSQL upgrade), and a search there reads each
  record's values as before S8 instead of naming the missing index table.
- Base 0.8 S2b: a draft write no longer loads the whole draft. Object, attribute, relation and
  mapping writes check only the records and relations they touch: the parent and its ancestors, the
  relations at each end, the draft-wide holders of a unique value through the typed value index, and
  for a deletion the subtree it removes. Renaming one record in a 100,000-record draft takes 7.5 ms
  (was 4.9 s). Migration `20260926_02` adds a value lookup index on `snapshot_attribute_values`. A
  unique attribute without a value no longer conflicts with records that lack it.
- A draft or history single-record read returned an empty `path`, so the record page showed no
  ancestors and the sidebar tree could not open the record's branch in those contexts. It now returns
  the ancestor path, as live reads and draft and history pages do.
- In the dark theme, a list footer's page field and **Go to** field kept the browser's light field
  colours and failed contrast; they now use the shared text-input treatment.
- Paging a list sorted by a boolean field past its first page returned a server error; keyset cursor
  positions are now bound as typed values. Keyset pages also seek to the cursor through the first sort
  key's index instead of scanning every earlier row.

## [0.7.0] - 2026-09-25

### Added

- Base 0.7 WP-9: composed acceptance for SC-07 and SC-15. `test:browser:sc07` resolves unmapped,
  differently mapped and 25-target ambiguous rows (candidates beyond page one, bounded previews with
  continuation), survives a racing generic relation write with the attempted choice kept, proves an
  independent binding with a typed relation attribute is untouched, and refuses draft activation when
  live changed the draft's mapping set. `test:browser:sc15` prepares one draft on an installed candidate
  release while another stays on the active one, refuses incompatible and unavailable releases without
  touching live data, history or another workspace, then publishes the prepared draft after the
  candidate is activated and discards the other. `test_build07_wp9_acceptance.py` adds corrupt and
  unsupported releases at the HTTP boundary. The browser harness accepts a model variant
  (`transformModel`).

- Base 0.7 WP-13C: `docs/testing/UI_ACCEPTANCE.md` names the existing reference pattern for each kind
  of UI element and inventories the states of every 0.7 surface with its evidence. The new browser
  runner `test:browser:wp13c` checks mapping and draft states against a real backend: outages with
  Retry, empty and no-match results, conflict review, the inverse mapping in a draft, a draft on a
  non-active model release, keyboard focus and phone width. UI changes now report functional,
  accessibility and visual evidence separately. Found and scoped WP-10F and WP-10G.

- Base 0.7 WP-13B: `docs/testing/EXECUTION_GUIDE.md` maps each changed production boundary to its
  focused checks and shared-boundary expansion, lists the WP-9 comprehensive command set and records
  measured before/after costs. Backend tests carry contract-group markers (`pytest -m mapping`, …) from
  one manifest in `conftest.py`; an unclassified test module or unknown marker fails collection.
  Vitest runs pure `.test.ts` files in a `unit` project without jsdom and components in `dom`. The
  gate-helper check (now in CI) refuses an unlisted browser runner, and the browser harness prints
  its setup phase timings.

- Base 0.7 WP-13A: `docs/testing/COVERAGE_MAP.md` links product invariants and capability contracts
  to their test evidence, boundary and cost tier, ranks risk and records audit status, residual risk
  and consolidation decisions. New regression evidence: mapping replacement refuses foreign-workspace
  drafts, unknown workspaces, a revision context and retired workspaces without changing data; draft
  relation update/delete advance both draft anchors' set versions only; runtime sources contain no
  starter-model key literal; live `date` values keep their type through write, boundary filters and
  sort; the mapping conflict retry sends the user's attempted target. Two confirmed defects are
  reproduced and fixed as WP-10C and WP-10D, and a third as WP-10E (see Fixed). One relation-set test duplicating stronger evidence was removed.

- Base 0.7 WP-12: `GET /api/v1/model-releases/{releaseId}/activations` reads a release's recorded
  activations (oldest first, with the release each replaced). Models release details move the
  Release ID and content hash into an explained, copyable **Technical details** disclosure; release
  history compares an earlier baseline (Before) with the selected release (After), including the
  active release, defaulting to the recorded predecessor, otherwise the labelled preceding installed
  release of the same key, with an explicit **Compare with** selector and truthful first-release,
  identical-content and unsupported-baseline states. Activation readiness is shown separately and
  always checks the current active release against the candidate.

- Dark mode: a complete dark token set that follows the system preference by default, with an
  explicit System / Light / Dark choice saved per browser and applied before first paint.
- Settings control at the bottom of the navigation rail with the appearance choice and an
  Account placeholder (local single-user session, disabled Sign in) for the planned multi-user
  authentication.
- Dark accessibility scenarios (core pages and the settings menu) and four dark visual baselines.

- Build 0.7 WP-7 browser draft version selection (ADR-028 frontend). Draft creation offers an
  optional model-release selector when multiple releases are installed; default is the active release.
  Draft list cards and detail header show each draft's model release key and version. An informational
  banner explains the state when a draft's version differs from the active release, and activation is
  disabled with a tooltip. A "Change model version" action in secondary draft actions loads available
  releases, attempts the pin change via the WP-6 PATCH endpoint, shows incompatibility diagnostics
  on failure and reloads the model context on success. Dirty-input protection via the existing
  `allowNavigation()` guard before applying version changes. Model-context refresh after pin change
  reloads the draft, pinned model and active release state; external pin change detection via
  `useEffect` + `useRef` in `LoadedDraft`. `WorkspaceDraft` type extended with `modelReleaseKey` and
  `modelReleaseVersion`. 169 frontend tests (5 new), zero lint errors, production build passes.

- Build 0.7 WP-5 atomic mapping replacement API: `PUT /api/v1/workspaces/{workspaceKey}/mappings`
  atomically creates, replaces or removes a mapping for one source in a configured relation binding.
  Supports live and draft contexts with optimistic concurrency via `expectedMappingVersion` and
  `expectedWorkspaceDraftVersion`. Direction-aware cross-cardinality enforcement (one-to-one always,
  one-to-many outgoing only). Retained relation identity when resolving ambiguous→mapped. Typed
  attribute semantics: omitted preserves retained edge values, explicit replaces, `{}` clears. Null
  target with non-empty attributes rejected. Idempotent no-ops with valid tokens produce no version
  increment or audit event. Stale tokens return `409 mapping_version_conflict` with bounded preview.
  Single-direction set version increments avoid double counting. Containment and required-ownership
  bindings rejected. Mapping-transition audit events with old/new targets and relation identities.
  After acceptance follow-up: 73 replacement/activation integration tests; 486 backend tests pass
  on SQLite.

- Build 0.7 mapping list API: `GET /api/v1/workspaces/{workspaceKey}/mappings` returns cursor-paged
  live/draft edges with optional binding, direction and name filters, directional set tokens, stored
  typed relation attributes and optional view-specific projections. Omitting direction returns both
  orientations of each edge; this supplements source-grouped coverage for integration reads.

- Build 0.7 WP-4 mapping query APIs: workspace-scoped coverage, candidate search and version-bound
  target details resolve the selected `mappingGrid` view under the live or draft-pinned model.
  SQL pagination and batched reads return typed projections, mapped/unmapped/ambiguous states,
  exact counts and at most 20 target summaries with explicit continuation. Cursors bind workspace,
  context, model release, view, direction and query configuration.

- Schema 0.6 `mappingGrid` view contract (Build 0.7 WP-2). The model language now accepts
  `schemaVersion: "0.6"` alongside `"0.5"`. `MappingGridViewDefinition` joins `TableViewDefinition`
  in a Pydantic discriminated union on `ViewDefinition.type`. Backend validation checks relation
  binding existence, rejects containment (`parentOf`) and required-ownership bindings, validates
  source/target columns against attached attributes, and verifies candidate search fields are
  searchable target-type attributes. The starter model advances to schema 0.6 / content release 0.7.0
  with two mapping grid views: `system-to-master-mapping` (outgoing) in RDM Systems and
  `master-to-system-mapping` (incoming) in RDM Master. Frontend `ViewDefinition` is a TypeScript
  discriminated union with type-safe narrowing; its initial placeholder was subsequently replaced by
  the WP-8/WP-14 contextual lens. 11 new backend tests cover parse, activation, backward compatibility
  and all validation rejection paths.

- Relation-set version persistence and generic participation (Build 0.7 WP-3). Every generic relation
  write (create, update, delete) now atomically maintains exact-binding set versions in both the
  outgoing and incoming directions. The `relation_set_versions` table tracks the optimistic version
  of each (workspace, optional draft, relation type, from/to object-type pair, anchor object,
  direction) combination. Rows are created lazily on first touch with version 1; untouched sets have
  implicit version 0. Draft-scoped and live-scoped versions are independent. Draft deletion cascades
  set-version rows; draft activation merges draft mutation counts into live set versions. A partial
  unique index protects live-context uniqueness where `workspace_draft_id IS NULL`. 9 focused tests
  cover all mutation paths, independent bindings, draft/live isolation, cascade and activation merge.
  All 379 backend tests pass.

- UI-07 automated accessibility and visual-regression gates (WP-1). `npm run test:a11y` runs
  axe-core WCAG 2.1 AA checks on 9 core page types across two object types; `npm run test:visual`
  compares viewport screenshots against committed baselines using pixelmatch. ~16 color-contrast
  violations fixed, definition-list structure corrected, sidebar landmark added. Two known violations
  allowlisted with tracked references. Light-theme baselines committed; dark baselines followed with
  dark mode.

### Changed

- Backend tests that need a private database copy a once-migrated template instead of running every
  Alembic migration per test; startup and migration tests still migrate for real. The sampled backend
  selection runs in 22.7 s instead of 46.8 s with the same cases. A pagination test that failed when run
  alone now owns its database.

- Models page aligned with the rest of the UI: the release/draft catalogue is now sidebar
  navigation, and the main column uses the shared context bar, page header and surfaces.

- Base 0.7 UX pass over the generic frontend, with routes, data contexts and API contracts unchanged:
  applications as header tabs with model icons; a segmented Live / Drafts / History control;
  collection list plus a collapsed-by-default record tree that opens toward the active record;
  one Filter popover with an applied count; lens tabs, scope banner and page count beside
  pagination; whole-row open; a record header with one breadcrumb line and a visible Edit record
  action; readable record activity without identifiers or concurrency tokens; a compact draft bar;
  and a rewritten design-token stylesheet with a 12–14px minimum text scale.
- Mapping lenses: segmented coverage filter, row-click to map, a searchable radio list of
  candidates, **Save and next**, and an explicit **Remove mapping** action. Selecting nothing no
  longer turns the primary button into a clear operation.

- Build 0.7 WP-14 composes model-defined table and mapping views as lenses of one contextual
  collection. One application browser now presents virtual collection groups alongside runtime
  hierarchy records, replacing the separate Browse hierarchy / Views modes. Direct-parent scope,
  typed field facets and mapping coverage state are visible and URL-backed. Mapping coverage applies
  parent/state filters before cursor pagination in live, draft and immutable-revision contexts, and
  cursor fingerprints bind both values. This remains generic over configured applications, object
  types, relations and renderers; Master, Systems and Translations remain starter examples.

- The WP-8A/WP-8B review retained atomic mapping actions while removing duplicate configured name
  columns and requiring explicit review before retrying after a mapping-version conflict. Historical
  mapping reads now use revision projections and expose no mutation controls. Focused package evidence
  covers both configured mapping directions, direct-parent scope, visible mapping-state filtering,
  live replacement, narrow layout and the composed page's accessibility.

- Extended the planned 0.7 design and delivery documentation after plan review: WP-1–WP-3 remain
  frozen; later packages specify bounded view-based mapping reads, stable retained relation identities,
  typed attributes, direction-aware constraints and atomic whole-candidate draft compatibility.
  Mapping UI is split into WP-8A coverage and WP-8B actions; WP-9 expands integration/a11y/visual
  evidence, with conditional WP-10 for confirmed foundation gaps.

### Fixed

- Base 0.7 WP-10K: records and relations read in a draft or from history no longer show the current
  time as their created and updated times. These are not recorded there, so the API returns `null`
  (the fields are now nullable), filtering or sorting by them is refused with an explanation instead
  of matching nothing, and collection views neither offer nor send them outside live data.
- Base 0.7 WP-10H: the mapping dialog no longer offers **Remove mapping** for a required
  relationship, which the server refuses; it asks for a replacement instead.
- Base 0.7 WP-10I: starting a draft on an incompatible model release lists the records that do not
  fit, as a version change already did, and draft error messages no longer run two sentences together.
- Base 0.7 WP-10J: missing-required and read-only field errors name the fields (“Required fields are
  missing: External ID”) instead of printing a list of keys; the keys are in `details.attributeTypeKeys`.
- Test reliability: the WP-12 and WP-13C browser runners waited too little for clipboard feedback
  and focus restore; a current-live base test read another test's draft from the shared database. The
  Models page visual baselines now show the WP-12 layout.
- Base 0.7 WP-10E: a live `dateTime` write keeps its instant. Values are stored in UTC and every
  context returns them with an explicit offset; decimals read back in one form without trailing
  zeros (live reads were padded to `12.5000000000`), so draft uniqueness compares equal decimals as
  equal. All server timestamps (`createdAt`, `updatedAt`, `occurredAt`, …) now carry an offset on
  SQLite too, and the browser no longer appends one to zone-less times.
- Base 0.7 WP-10F: **Create new …** in a mapping lens asks which application the new target
  belongs to, listing every application that contains its type and defaulting to the lens's own.
  Parent choices are limited to types in that application, and a notice explains when it has none.
  The starter can now create a target in both mapping directions.
- Base 0.7 WP-10G: the mapping dialog's search box keeps its height at phone width, and the draft
  model-mismatch and historical-revision notices name releases by key and version instead of UUID.
- Base 0.7 WP-10C: `date`, `dateTime` and `decimal` values can be written in a workspace draft
  (create, update and the field endpoint returned 500) and are published to live on activation,
  including values captured from live. Draft and revision lists filter and sort these fields and
  integers by their declared type: numbers no longer sort as text (`10` before `5`), date-times sort
  by instant, and a zone-less `dateTime` filter value is read as UTC.
- Base 0.7 WP-10D: renaming or moving a contained record inherited by a draft no longer adds a
  second containment relation with a new ID. An unchanged parent keeps its relation; a move replaces
  it with exactly one. Such drafts now activate instead of refusing with `duplicate_edge` or
  `relation_cardinality_violation`.

- WP1-001: the navigation resize separator is inside the navigation landmark, so its accessibility
  exception is removed. Collection and settings popovers render inside a landmark (or the open
  dialog), and zone-less server timestamps are read as UTC.

- Build 0.7 WP-5 review: enforce ancestor-scoped constraints against the final replacement graph,
  and reject missing required ancestors in generic draft relation writes as in live writes. Reject
  required-ownership replacement irrespective of relation orientation. Explicit empty application/view
  keys fail validation instead of selecting unconfigured reads. Twelve HTTP regressions cover these
  boundaries, preserved tokens and valid replacements within one ancestor scope.

- Build 0.7 WP-10B: draft activation now refuses new, removed or updated live relations in exact
  mutable binding sets the draft touched, including previously unmapped sets. It compares the
  immutable source/live edge identities and versions before applying any rows. Refusals preserve
  the draft, live data and revision designation and include bounded mapping-set diagnostics with
  recovery instructions. Unrelated live mapping work and existing containment/ownership merge
  behavior remain covered. WP-5 acceptance adds independent-binding isolation, required-ownership
  and clearing refusals, and overlapping generic create/update/delete versus mapping saves.

- Build 0.7 WP-10A, found in WP-4 review: confirmed live/draft object cascades now advance both
  directional relation-set versions for removed edges. Stale mapping target continuations return
  `409 mapping_version_conflict` with refresh guidance; previews and rejected deletes leave versions
  unchanged. Regression coverage exercises both directions and contexts.

- Build 0.7 WP-1/WP-2 review fixes: scope accessibility exceptions to known targets and node counts,
  fail visual comparisons on missing baselines outside explicit update mode, reject `mappingGrid`
  under schema 0.5, and allow the documented offline schema 0.4 recovery to select a compatible
  schema 0.5 or 0.6 candidate. The CLI reports expected refusals without a traceback, and the draft
  context regression now checks the current named-draft and version presentation. Visual capture
  waits for loaded panels, and the model-workbench baseline now covers the loaded release detail.

## [0.6.0] - 2026-09-11

### Changed

- Implemented WP8.1-A model authority boundaries. Compatibility now examines all authoritative live
  objects, attributes and relations, including catalogue-retired workspaces. Draft and historical
  reads resolve their pinned supported model before filters, typed responses and relation expansion;
  missing, corrupt or unsupported pins and workspace-context mismatches return structured errors.

- WP8.1-B captures an immutable current-live draft base including post-publication edits, model and
  record versions, with live data that has no prior publication. Historical source remains separate.

- WP8.1-C delivers newest-first revision history with deterministic cursor retry. Designation
  retirement preserves live access and history; catalogue retirement rejects writes.

- Reviewed the uncommitted WP8 implementation against the live/draft API contracts. Corrected
  activation and cascade deletion ordering, association confirmation and ownership checks, atomic
  draft version claims, public relation UUID reads, retired-workspace publication guards, and
  read-only attribute handling, draft containment validation and cross-workspace ID collisions.
  Added request-boundary and audit-migration regression coverage. Cascade confirmation now requires
  the signed token from the exact displayed preview and rejects any intervening hierarchy change with
  no deletion or audit side effects. Missing tokens are rejected before stale-version checks, draft
  deletion verifies the route object type, live deletion serializes against workspace retirement and
  inconsistent cross-workspace graph edges are refused. The frontend adapter carries both live and
  draft confirmation context.

- Reconciled technical documentation and delivery planning with the accepted product stories and
  GAP-01–GAP-08 answers. ADR-027 consolidates live data, optional copied drafts, immutable history,
  truthful publication retirement and newest-first history. Corrected API documentation against
  current payloads and cursor behavior.

- Implemented ADR-026 live active data writes: the active workspace is live-writable for **data**.
  `workspaceDraftId` is optional on record writes — present stages into the design draft; absent
  writes directly to the live active object store (record `expectedVersion` claim + audit, no
  workspace revision). Active reads resolve the live projection; activation is a delta-merge of the
  draft onto current live content with per-record version conflict detection (`version_mismatch` /
  `id_collision` / `duplicate_edge`), merged-graph validation and a merged revision snapshot that
  preserves live-only records. Restored `services/objects.py` CRUD functions, `services/relations.py`
  helpers and `services/deletion.py` as the live write path basis; added the workspace-audit seam and
  a corrective migration widening the audit `aggregate_id` column to host live object/relation ids.
  Amends ADR-024/ADR-025 write-context clauses for data content.

- Corrective Base 0.6 WP6 persistence: workspace drafts and immutable workspace revisions own the
  staged/historical graph; ADR-026 subsequently restores live-row current-data authority. The migration
  converts only unambiguous Base 0.5/rejected-WP4 workspace graphs,
  preserves public object and relation UUIDs, and removes per-object lifecycle persistence.

- The backend now requires Python 3.14. The local version pin, package metadata, Ruff target, CI
  runtime, container base image and development documentation all use 3.14; Python 3.12
  compatibility is no longer maintained.

- Frontend structure refactor, phases 0–4 of `docs/FRONTEND_STRUCTURE_REFACTOR.md`. No API
  contract, model contract or architectural change. `frontend/src` is reorganized into `app/`,
  `features/`, `ui/`, `model/`, `routing/`, `lib/`, `types/` and `styles/`, with every internal
  import going through an `@/` alias. `types.ts` and `utils/model.ts` are split by concern behind a
  barrel, the four overloaded components are split into 28 modules, and `styles.css` becomes four
  layers whose built output is byte-identical.

- The generic view and panel registries are rendered as elements rather than called as functions.
  Nothing was broken, but a panel component gaining state would have made `ObjectDetail`'s hook
  order depend on which panels a model declares as visible. The panel registry is keyed by the
  `PanelDefinition` discriminant, removing its per-entry casts, and both registries now live in
  their own modules.

- Client error handling is consolidated in `api/errors`. `isApiError` replaces five untyped casts
  used to detect optimistic-concurrency conflicts, and `errorMessage` replaces 36 inline
  expressions. Seven messages that reached the UI as `Error: …` now read like every other message.

- Cursor paging and search debouncing are consolidated into `useCursorPages`, `useCursorFeed` and
  `useDebouncedValue`, replacing two incompatible paging implementations across seven components.

- Every dialog shares one modal shell, `ui/Modal`. Five dialogs previously rebuilt the same backdrop
  and disagreed about its behavior. `ObjectFormDialog`, `AttributeValueDialog` and
  `RelationFormDialog` now close on Escape and return focus to whatever opened them; Tab is trapped
  inside an open dialog; the page no longer scrolls behind one; and two dialogs that carried
  hardcoded `aria-labelledby` ids now generate them, so opening two cannot produce duplicate ids.

- Frontend redesign (UI-01–UI-06). Compact neutral sidebar with workspace/application/view
  navigation; Browse hierarchy default with browser-local expand/collapse persistence; accessible
  mobile navigation drawer. Focused collections with search, typed filter popover, sort, display
  controls, sticky headings, comfortable/compact density and mobile-aware column prioritisation.
  Full-width record inspector with collection-origin preservation through reload/Back/Forward,
  contextual action menus, dirty-edit navigation guards and cross-application related-record return.
  Inline typed field editing with explicit save/cancel, null/removal distinction, saved/error
  feedback and retained coherent multi-field forms. Pointer and keyboard resizable navigation rail,
  inspector and table columns with browser-local display preferences. Refined draft catalogue,
  named-draft strip, consistent error/loading/empty/confirmation treatment and composed
  desktop/mobile visual review. UI-07 (automated accessibility and visual-regression gates) is
  deferred to 0.7.

### Added

- WP9 complete generic browser tasks in live, draft and history contexts. Slice A implements live
  workspace navigation with cursor-position restoration and retry/content preservation. Slice B
  implements direct live Add/Edit/Delete with typed fields, ordinary relationships and translations,
  conflict reconciliation and signed deletion confirmation. Slice C implements optional current-live
  drafts, shared draft authoring, validation, activation and discard with aggregate concurrency and
  conflict feedback. Slice D implements newest-first immutable history, pinned-model reads, historical
  draft sources and truthful publication retirement. SC-01–SC-06 and SC-08 have isolated real-backend
  browser evidence with two configured object types at desktop and 390px mobile widths.

- WP10 composed release validation: product scenarios exercised against a real browser and backend,
  including live CRUD without a draft, optional staging, current-live draft bases, concurrency and
  delta merge, whole-graph atomic failure, live-only compatibility and pinned historical typing.
  Keyboard/focus/narrow-layout journeys, migration/lifespan, packaging and public-contract checks.
  Automated accessibility and visual-regression tooling (UI-07) is deferred; manual keyboard and
  focus checks are recorded.

- Base 0.6 WP7 corrective CRUD restoration: the established generic object, attribute, relation and
  translation CRUD contract is restored over WP6 workspace storage. Originally draft-scoped, it was
  extended by ADR-026 to direct live writes plus optional drafts. No per-record lifecycle or nested
  public CRUD resources are introduced, and the
  original CRUD, attribute, cascade and translation suites are restored and enabled.

- Base 0.6 WP8 workspace lifecycle orchestration. Root and
  history-derived workspace drafts, whole-graph validation, atomic activation that writes one immutable
  workspace revision of the merged live graph and applies authored changes in one transaction after the
  ADR-026 correction,
  cursor-paged immutable revision history, and publication retirement under an expected active-revision
  claim. Draft/revision/validation/activation/retirement events use dedicated workspace aggregates with
  bounded identity payloads, kept separate from record-level `object-draft` and `relation` audit
  events. Objects, typed attributes, containment and relations remain ordinary records through the
  canonical generic CRUD routers; no per-object lifecycle or nested workspace-draft CRUD resources
  exist.

- Database migration failures now produce a credential-safe operator message with the current and
  target revisions, recovery command, backup requirement and escalation details. Startup enters
  maintenance mode without a traceback, and the WP4 migration safely retries recognized empty SQLite
  DDL left by an interrupted attempt. Real-database startup, restart and interruption regression tests
  cover the failure that previously left the development application unable to boot.

- Base 0.6 authoritative runtime-object revisions. Stable logical objects now own model-pinned,
  optimistic drafts and immutable active/retired snapshots with separate derivation and supersession
  lineage. Root and historical drafts, explicit activation, cursor-paged history, retired discovery,
  direct retirement and ownership-cascade retirement are public API contracts. Activation publishes
  core fields, typed attributes, containment and required relationships atomically; independent
  associations and published identity survive retirement. The Alembic transition preserves object
  UUIDs, migrates known active/draft/retired rows and rejects unknown legacy states with counts.
  Post-implementation hardening conditionally claims the final draft version during activation,
  prevents compatibility adapters from drifting the lifecycle projection and rejects corrupt
  cross-workspace retirement graphs.
  This pre-release design was subsequently rejected as the wrong publication boundary. ADR-024 and
  corrective WP5 froze workspace-level journeys, fixtures and API design; WP6 supplied the corrected
  persistence, WP7 restored generic CRUD and WP8 completed workspace orchestration, with WP9-WP10
  delivering the UI and release validation. These object-lifecycle APIs are not a compatibility
  commitment.

- Frontend lint and format tooling: ESLint 10 with `typescript-eslint` and
  `eslint-plugin-react-hooks`, and Prettier. `AGENTS.md` listed "linting passes" in the definition
  of done, but the frontend had no linter. Dependencies are pinned instead of `"latest"`, build
  tooling moves to `devDependencies`, and the Dockerfile uses `npm ci`; TypeScript is pinned to 6.x
  because `typescript-eslint` cannot yet parse with the TypeScript 7 native compiler.

- An application-level smoke test covering the extracted router: model-driven shell rendering, deep
  collection URLs, fallback when a URL names a retired application, and returning from an object to
  the collection and workspace it was opened from.

### Fixed

- A detail panel naming an object type that a later release retired now reports it instead of
  crashing the detail screen through a non-null assertion.
- Modals restore focus to their opener even when a form field uses `autoFocus`; cursor feeds ignore
  late load-more responses after their query changes or reloads; and cancelling a failed relationship
  deletion clears its action-specific error without blocking relation paging.

## [0.5.0] - 2026-09-05

### Added

- A global model workbench with always-readable installed releases and capability-gated JSON draft
  creation/import/editing, validation diagnostics, canonical compilation, semantic comparison,
  browser export, immutable installation and guarded activation. Optimistic conflicts preserve local
  input, and mutation controls remain absent by default.

- Base 0.5 generic object-management UI. Workspace context is explicit in the app shell and URLs;
  collection search, repeatable state filters, built-in sorting and page size survive browser
  navigation; generic rows expose existing edit/delete semantics; failed collections, panels and
  lookups are retryable; and object details show bounded, incrementally loaded audit history.

- Base 0.5 object and relation query foundations. Object collections now support repeatable state
  filters and stable built-in sorting through signed, filter-bound keyset cursors. Relation expansion
  is a bounded workspace-checked page, and object history uses an indexed audit-subject projection to
  include object, attribute and connected-relation events without exposing internal sequences or full
  before/after payloads.

- Base 0.5 guarded model activation. Compatible installed releases can be selected with both expected
  runtime version and active-release tokens; incompatible runtime data and stale selections return
  structured conflicts. Activation commits before refreshing the process registry, records old/new
  release IDs and hashes, marks health unhealthy on refresh failure, and rejects mutation enablement
  when `WEB_CONCURRENCY` configures multiple workers.

- Base 0.5 persisted model drafts and immutable installation. Mutation-gated draft APIs support
  optimistic version claims, side-effect-free compilation and atomic content-addressed installation;
  lifecycle audit events retain hashes and identities without copying complete model JSON. The
  capabilities endpoint reports the effective read, draft, installation and activation surface.

- Base 0.5 model compilation and comparison: inline validation returns stable diagnostic codes and
  JSON Pointer paths; installed releases can be compared by semantic, key-based paths; and bounded
  runtime-data checks classify candidates as compatible or migration-required without persisting or
  activating content.

- Base 0.5 model runtime authority: a singleton, versioned database row selects the active immutable
  release; source JSON is bootstrap input only. Requests resolve one cached model/release snapshot,
  `GET /api/v1/model` exposes its hash and release UUID in response headers, and cursor-paged release
  catalogue/detail APIs expose installed snapshots without enabling mutations.

- Complete model-driven Translation CRUD. Translations contain optional translated name, description
  and value fields (with at least one required), belong to a Translation Group, and atomically bind to
  exactly one configured target object. Domain, Codelist and Master Value targets are enabled in the
  starter model; future target types require only another JSON allowed pair. Duplicate active
  target/Language translations are rejected, inactive historical records may coexist, required
  bindings cannot be unlinked, and owner cascade deletes the Translation.

- Optional, model-driven Domain/Codelist-to-System Value representation relationships. Domain and
  Codelist details expose outgoing representations, while System Value details expose their incoming
  reference structures. These associations do not alter system containment and cascade deletion only
  unlinks them. System Value relation tables show the containing System through a generic ancestor
  column and can omit their constant relationship-label column.

- Optional transactional cascade deletion for runtime objects. A non-cascade delete with dependencies
  now returns a structured, non-mutating impact report; the UI renders the affected child objects,
  PK/FK dependents and relationships before allowing explicit cascade confirmation. Cascades delete
  containment descendants, unlink independent relationships and follow directed, required
  single-valued bindings from owner to dependent.

- Model-driven runtime CRUD in the React UI: object create/edit/delete, individual attribute-value
  add/edit/remove, and direction-aware relationship create/edit/delete. Relationship choices come from
  configured panels and allowed object-type triples; candidate lookup is server-side and can cross
  application boundaries within a workspace. Engine-maintained containment edges remain visible but
  immutable.
- A structured frontend `ApiError`, shared typed field renderer, paged object lookup and accessible
  destructive confirmation dialog. Optimistic-concurrency, dependency, uniqueness and cardinality
  failures remain recoverable in their active UI context.

- Standalone object-scoped CRUD for attribute values:
  `GET`/`POST`/`PATCH`/`DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`.
  A single stored value can now be read, set, updated or removed without rewriting the whole object.
  Mutations require the object's `expectedVersion`, return the full object response, and enforce the
  same validation, read-only/required and workspace-uniqueness rules as object writes. Deleting a value
  on a required or read-only attribute is rejected (`422 cannot_delete_required_attribute` /
  `read_only_attributes`).
- Read-one, update and delete for relation instances:
  `GET`/`PATCH`/`DELETE /api/v1/relations/{relationId}`. `PATCH` replaces relation `attributes`
  (relation identity is immutable) and, like `DELETE`, claims an atomic `expectedVersion`
  (`409 version_conflict` on a stale claim). Engine-maintained parent-containment and hierarchy
  relations — those named in the target object type's `behavior.parentRelationTypeKeys` — are rejected
  for direct create/update/delete with `422 immutable_relation`; they stay atomic through object parent
  operations.
- Workspace-scoped attribute uniqueness for attribute types that declare `features.unique`. Create and
  update now reject a colliding value with `409 duplicate_attribute_value`. Uniqueness is enforced per
  attribute type within a workspace, and declaring `unique` on a `json` value type is rejected at model
  load.
- Frontend unit-test setup (Vitest + Testing Library) covering the model helpers and the generic
  renderers with two object types, run locally and in CI via `npm test`.

### Changed

- The bundled starter content release is now `0.5.0`; its model-language `schemaVersion` remains
  `0.4` because Base 0.5 did not change the declarative schema contract. Existing databases retain
  their database-selected active release until an administrator deliberately activates another
  installed release.
- Release operations now have documented backup and rollback boundaries: back up before migrations,
  use activation for compatible model-content rollback, and restore the matching database backup for
  application/schema rollback rather than editing immutable releases or relying on Alembic downgrade.

- Hardened the Base 0.5 WP2/WP3 lifecycle foundation after review: compatibility checks now include
  numeric relation attributes and enforce cardinality across every allowed pair sharing a relation
  type; compiler diagnostics retain stable paths for top-level validation failures; semantic diffs
  preserve real JSON `null` values and ignore ordering in set-like key collections; and concurrent
  installations are serialized in the supported single-process administration topology.

- Metadata collection endpoints now use opaque cursor pagination with a documented page-size limit.
- Attribute-value response items now include their stable public UUID `id`.
- Relation `fromObjectId`/`toObjectId` and object `parentObjectId` are now validated as UUID v4,
  returning `422 request_validation_error` for non-UUID values.
- Alembic migrations are now the single source of schema truth: the initial migration provisions a new
  database and upgrades an existing one, and startup no longer runs `create_all`.
- Object ancestor paths are resolved in level order (one query per depth level) instead of one query per
  object, removing the N+1 traversal on collections.
- Developer tooling: `.python-version` pins Python 3.12, and generated `*.egg-info`/`*.tsbuildinfo`
  artifacts are removed from version control.

### Fixed

- Model release snapshots are recursively immutable, metadata and release cursors are signed and
  filter-bound, model ETags use valid quoted entity-tag syntax, and release timestamps are normalized
  to UTC even when SQLite returns naive datetimes.
- Relation create and update now reject attributes not declared by the matched allowed pair and
  validate declared values through their global attribute types before persistence.
- Duplicate many-to-many edges supplied through atomic object `initialRelations` now return
  `409 duplicate_relation` and roll back the new object instead of escaping as an internal error.
- The initial Alembic revision now owns a frozen schema snapshot rather than importing live ORM
  metadata, keeping fresh-database upgrades reproducible as later revisions are added.
- Object creation preserves `false` for optional boolean attributes without a configured default
  instead of treating that value as absent.
- Object and standalone attribute-value writes now share an atomic expected-version claim, preventing
  concurrent requests from accepting the same object version and silently overwriting one another.
- Standalone attribute-value `GET` responses now include `objectVersion`, allowing clients to obtain
  the concurrency token required by `POST`, `PATCH` and `DELETE` without fetching the full object.
- Objects that have a parent can now be deleted. Deleting such an object removes its parent containment
  relation atomically, while objects with child objects or non-parent relations (mappings, translations)
  still return `409 object_has_dependents`.
- Partial updates no longer let a required attribute be cleared. Providing a required attribute as
  `null` or empty in a `PATCH` returns `422 missing_required_attributes`; omitting it remains allowed.
- `validation.minimum`/`maximum` on a non-numeric attribute type no longer causes a server error. These
  bounds now apply only to `integer`/`decimal`; non-numeric, non-finite, inverted or misplaced bounds
  are rejected at model load.
- The object form's parent picker now pages through all candidate parents instead of truncating at the
  first page, so a parent beyond the first page is no longer silently lost when editing.

## [0.3.0] - 2026-09-02

Baseline executable vertical slice of the generic reference-data engine: the versioned JSON model
(schema 0.3) as the source of truth for applications, object types, global attribute types, relation
types, allowed object-type triples and UI views, with a FastAPI backend, immutable model releases,
typed attribute storage, cursor-paginated APIs and a generic React UI.
