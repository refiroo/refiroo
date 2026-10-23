# Settings, integration administration and UI foundation

**Status:** Approved 2026-10-05: the user took [U-D1–U-D5](#decisions) as recommended (U-D2 "for
now"). U-D6: Direction B, "Open", chosen "for now" on 2026-10-05 ([ADR-039](DECISIONS.md#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state)). Track U runs from 0.9 to 0.12, so the product
reaches 1.0 with a settings area that covers administration, integration and security.

## Why

The user asked five questions on 2026-10-05: where the consumer API's `apiKey` is set, where
administrative settings live, where API settings (authentication, webhooks, the `apiKey`) live,
where a user reads the current contract version that appears in consumer URLs, and when the API
reference shows that version as a fixed value instead of a placeholder. They also asked for a
professional UI fixup. The answers below were checked against the code on 2026-10-05.

### What exists today

| Question | Today (checked) | Gap |
| --- | --- | --- |
| The `apiKey` | The `key` of a `consumerApis` entry in the model (`models/schema.py`, `ConsumerApiDefinition.key`). A route matches it against the active release's definitions (`engine/reads/consumer_objects.consumer_definition`). It is validated as lowercase letters, digits and hyphens, unique in the release. It is a **namespace**: it selects which definition a request reads. It is not a credential and grants nothing. The backend has no authentication code at all. The starter model declares no consumer API. Only test models do | The name reads as a credential (`apiKey` is the industry term for one). Nothing in the UI shows it. It can be set only by editing model JSON in the model workbench |
| Administrative settings | Every deployment setting is an environment variable (`config.py`, OPERATIONS.md). `GET /api/v1/capabilities` reports the capability groups and limits. The UI has two administration pages, Models and Workspaces, as rail entries | No page shows deployment settings or the engine's version |
| API settings | No authentication (0.12, C-D1). Webhook subscriptions arrive with C11 as an API, signed from 0.9 (C-D12 revised 2026-10-05), and their UI administration is planned for 0.12 | No integration page exists |
| Current contract version | `contractVersion` in the model. The only API that tells a caller is a `404 CONTRACT_VERSION_NOT_FOUND` with `details.contractVersion`. The API index (`GET /api/consumer`, C6) is not built yet | Nothing in the UI or API shows it before C6 |
| Version in the documentation | The consumer router is excluded from OpenAPI (`include_in_schema=False`), so `/docs` shows no consumer route. C6 plans "per-definition OpenAPI" and V2 lists them on `/docs`, but neither says how paths and versions are written | Must be specified before C6 |
| Settings menu | `app/SettingsMenu.tsx` is a popover at the bottom of the rail: a disabled "Sign in", and the theme choice | No settings area and no settings pages |
| Appearance | `styles/base.css` defines four page and panel surfaces within a few percent of white (`#fff`, `#f8faf9`, `#fafbfb`, `#f5f7f6`) and one accent hue (`#17604f`). Components are styled in one 3,295-line `components.css` | Regions do not separate, and colour carries no meaning (see [UI foundation](#ui-foundation)) |

## Answers in one place

- **Where the namespace (`apiKey`) is set:** in the model, as the `key` of a consumer API
  definition. It is part of the contract's identity in an immutable release: changing it creates a
  different API, and callers of the old one get `404`. So it is never a setting on a page. It is
  edited where the model is edited: the model workbench today, the 0.10 editor later. It is shown,
  read-only with a link to the model, on **Settings › Integration › Consumer APIs**. The public name
  changes per [U-D1](#decisions).
- **Where the current contract version is read:** the API index `GET /api/consumer` (C6) for
  clients, and **Settings › Integration › Consumer APIs** for people. That page shows each API's base
  URL with the version filled in, for example `/api/consumer/rdm/v2`, with a copy button.
- **Fixed version in the documentation:** C6 and V2 are amended ([below](#versions-in-the-documentation)).
  Each consumer API's OpenAPI document writes its paths with the namespace and version filled in
  (`/api/consumer/rdm/v2/xref`). It has no `{apiKey}` or `{contractVersion}` placeholders, and its
  `info.version` is the contract version. When a model release raises the version, the next page
  load of `/docs` shows the new one.
- **Administrative settings:** **Settings › Administration** (Workspaces, Model, Deployment; and
  Operations in 0.11).
- **Data operations:** **Settings › Data operations** (Import profiles, Jobs), grouped so in 0.10 A5c (the
  user, 2026-10-14): work on the data, not settings, to move out of Settings together later.
- **API settings:** **Settings › Integration** (Consumer APIs, Webhooks, API reference; Jobs until
  0.10 A5c) in 0.9, and **Settings › Security** (users and roles, OAuth clients and their access
  per consumer API, webhook signing-key rotation) in 0.12. A webhook's signing key is shown once, on
  the Webhooks page when the subscription is created (0.9, C-D12 revised 2026-10-05).

## Principles

1. **Each fact is edited where it lives.** What the model declares (namespace, contract version,
   exposed types, events) changes only through a model draft and release. A settings page shows it
   and links to the model. Runtime objects (workspaces, webhook subscriptions, and later OAuth
   clients and signing keys) are created and changed on their pages. Deployment settings come from
   the environment and are shown read-only ([U-D2](#decisions)).
2. **API first.** Every page reads and writes through a public route. A page needing data no route
   gives adds the route first. The only new management route in this plan is `GET /api/v1/system`
   (U3).
3. **Generic.** No page names an application, object type or consumer API key. The Consumer APIs
   page renders whatever definitions the active release declares.
4. **One settings area, separate from the applications.** Applications stay in the rail.
   Administration, integration, security and appearance move into **Settings**, one page per item
   with its own URL. The rail's popover keeps only what is personal (account, theme) and links to
   Settings.
5. **Secrets are never displayed.** `DATABASE_URL` is shown without its password. The cursor
   signing key, webhook signing keys after creation (0.9), and in 0.12 client secrets, are never
   returned by any read.

## Settings area

`/settings/…`, opened from a gear entry in the rail. A two-level side navigation; each leaf is a
page with its own URL, page header, sections and keyboard order. At 390px the side navigation
becomes a select at the top of the page.

| Group | Page | Content | Reads / writes | Package |
| --- | --- | --- | --- | --- |
| General | About | Engine version; management API version (`v1`); supported schema-language versions; the active model release (name, version, activated at); database migration revision | `GET /api/v1/system` (new) | U3 (0.9) |
| General | Appearance | Theme (system, light, dark), table density; saved in the browser | — | U3 (0.9) |
| Administration | Workspaces | The current workspace page, moved | existing routes | U3 (0.9) |
| Administration | Model | The current model workbench (releases, drafts, diff), moved | existing routes | U3 (0.9) |
| Administration | Deployment | Every operator setting: name, environment variable, value, default, what it controls; capability groups on or off with the setting that switches them | `GET /api/v1/system`, `GET /api/v1/capabilities` | U3 (0.9) |
| Administration | Operations | Health, readiness, metrics summary, last backup rehearsal | 0.11 routes | U7 (0.11) |
| Integration | Consumer APIs | Per definition: name, namespace, contract version, base URL with copy, OpenAPI URL, a link to its source on `/docs`, exposed types, lists, events (each with its types, change kinds and watched outputs, read-only). The model release that declares it, with a link to the model | `GET /api/consumer` (C6), the active release | U4 (0.9) |
| Integration | Webhooks | Subscriptions: create (the signing key shown once), edit, suspend, resume (after expired events: the lost range and the publication to re-sync from, and resume with `reset`, starting after the feed's head, with the order "reset, then re-sync" explained, C-D93 revised, C-D110; a resume that needs an edit lists what to fix, C-D98), delete; the suspension reason with its message and findings; the allowed hosts from capabilities (C-D101); a workspace's subscriptions named where deleting it is refused (`deleteBlockedBy: subscribed`); events chosen from the definition's declared events, each linked to its declaration on Consumer APIs; payload (`full` or `identity`); delivery state from the subscription's `delivery` (C12, C-D108): last delivered, and while a batch fails its attempts, first failure, last error by kind and next attempt; the dispatcher's reasons (`DELIVERY_FAILED`, `FILTER_MATCHES_NOTHING`, `EVENTS_EXPIRED`) each with its fix; the delivery limits from capabilities. Signed from 0.9 (C-D12 revised 2026-10-05); 0.12 adds rotation | `/api/v1/consumer-subscriptions` (C11–C12) | U5 (0.9) |
| Data operations | Import profiles | Stored import profiles as a catalogue: a profile's last load, the next version uploaded and checked, loaded into a change set (0.10 A5c) | `/import-profiles`, its check, `/source-files`, `/imports` | 0.10 A5c |
| Data operations | Jobs | Recent jobs with status and outcome counts; cancel; batch and job limits (the feed's retention moved to Consumer APIs, 0.10 A5c) | job routes (B1–B2), `GET /api/v1/capabilities` | U4 (0.9) |
| Integration | API reference | Links to `/docs`, one per source, with its version | `GET /api/consumer` | U4 (0.9) |
| General | Account | The person, their password, where they are signed in (sign out one or everywhere), what they can do per workspace (until Z1 "Everything", then their roles) | `/me`, `/me/sessions`, `/me/password`, `/me/permissions` | 0.12 I2 (built 2026-10-23), Z1 |
| Security | People | List and detail: create, a one-time reset link, deactivate, sign out everywhere, last sign-in; roles by workspace with their narrowing and where they come from; groups; recent activity | `/users`, `/grants` | 0.12 SP1 |
| Security | Groups | Local and provider groups; members (a provider group's as seen at sign-in); roles | `/groups`, `/grants` | 0.12 SP1 |
| Security | Roles | The matrix of roles and action groups; predefined read-only; a custom role created, copied, edited | `/roles`, `/action-groups` | 0.12 SP1 |
| Security | Clients | List and detail: create (secret shown once), rotate with an overlap, end a secret, deactivate; management roles and consumer API grants per workspace; last use | `/clients`, `/grants` | 0.12 SP2 |
| Security | Sign-in | Sign-in providers; local accounts on or off | `/sign-in-providers` | 0.12 I3 |
| Security | Signing keys | Token signing keys by age; rotate now | `/token-signing-keys` | 0.12 I1, SP2 |
| Administration | Workspaces › a workspace › Access | Who can do what here, the grant dialog (who, role, narrowing of writes); Approvals tab with the four-eyes policy (Track A) | `/workspaces/{key}/access`, `/grants`, `/approval-policy` | 0.12 SP1, A3 |

### `GET /api/v1/system` (U3)

```json
{
  "engine": { "version": "0.9.0", "managementApi": "v1" },
  "schemaLanguages": ["0.7", "0.8"],
  "activeModelRelease": { "id": "…", "name": "…", "version": "0.9.0", "activatedAt": "…" },
  "database": { "revision": "20261005_02", "url": "postgresql://rdm@localhost:5432/rdm" },
  "settings": [
    { "name": "FEED_RETENTION_DAYS", "value": 30, "default": 30, "source": "default" }
  ]
}
```

`settings` lists every setting `config.Settings` reads, with `source` `environment` or `default`.
`DATABASE_URL` loses its password, and `CURSOR_SIGNING_KEY` appears with `value: null` and
`source` only. Journey: an operator checks what a deployment runs and how it is configured
(added to USER_JOURNEYS with U3).

## Versions in the documentation

Amends C6 and V2 (0.9). C6's per-definition OpenAPI document
(`/api/consumer/{namespace}/v{contractVersion}/openapi.json`; **delivered in C6b, 2026-10-05**, with
the API index `GET /api/consumer`; V2's sources follow):

- `paths` are written literally: `/api/consumer/rdm/v2/xref`, `/api/consumer/rdm/v2/lists/products`.
  Neither the namespace nor the version is a path parameter. Lists are separate paths, not
  `{listKey}`.
- `info.title` is the definition's `name`, and `info.version` is the contract version as a string
  (`"2"`). `info.description` names the model release that declares it.
- `servers` follows the deployment's root path, as the management source does (V1).
- With one installed version per definition (C-D3), there is one document per definition. A model
  release that raises the version changes the document at its new URL. The old URL answers
  `404 CONTRACT_VERSION_NOT_FOUND` naming the current version.

V2's sources on `/docs` (**delivered in V2, 2026-10-05**): one per definition, labelled `{name} · v{contractVersion}`, built per
request from the active release. A release that adds, removes or re-versions a definition shows on
the next page load. Test (added to V2's): a release raising a definition from 1 to 2 shows `v2` in
the source label, in every path and in `info.version`, and the v1 document answers `404`.

The management API's `/api/v1` is its own contract version. The product version (`0.9.0`) is
`info.version` of the management document and is shown on **About**.

## UI foundation

### Diagnosis

The pages work but do not read well. The cause is the token set and the missing components, not
individual screens:

- **Regions do not separate.** Rail, canvas, panels and tables use four near-white surfaces, so
  the eye finds no structure.
- **Colour has no meaning.** One green accent marks primary actions, links, the current navigation
  entry, selection and focus. A user cannot tell which of these a green element is.
- **The data context is easy to miss.** Live data, a change set and a publication look the same
  apart from a label. In this product that is the most consequential thing to know before editing.
- **Missing elements.** Pages lack a common page header, section and card structure, status badges,
  a description list for record facts, a segmented control for lenses, empty states with an action,
  skeleton loading and confirmation toasts. Each screen improvises these in `components.css`.

### Direction

[ADR-023](DECISIONS.md#adr-023--build-rdm-ui-components-on-react-aria-behavior) stays: React Aria behind `ui/` wrappers, and RDM owns every style through
tokens (no pre-styled design system). The fixup works within it:

1. **Three token layers.** Primitive scales (neutral, brand and status hues, 50–900) feed semantic
   roles (`surface.app`, `surface.nav`, `surface.raised`, `surface.sunken`, `text.primary`,
   `text.secondary`, `border.subtle`, `border.strong`, `action.primary`, `state.selected`,
   `status.{draft, live, published, conflict, error, warning, success}`, `context.{live,
   changeSet, publication}`), and the semantic roles feed component tokens. Dark mode redefines the
   semantic layer only.
2. **Distinct regions.** The rail sits on its own toned surface, the content on the canvas, and
   panels and the record inspector are raised (border and shadow). The header carries the
   workspace and data context.
3. **Colour carries meaning.** The brand accent is used only for the primary action and the current
   location. Selection has its own tint. Status hues appear only for states. The data context gets
   a persistent coloured bar: live, change set and publication are distinguishable at a glance and
   by text.
4. **Type and spacing scale.** Six type steps. Hierarchy comes from weight and size, not colour.
   Tabular numbers in tables. A 4px spacing scale, with compact and comfortable table density.
5. **Components** in `ui/`: `PageHeader`, `Section`, `Card`, `Toolbar`, `Badge`/`StatusPill`,
   `DescriptionList`, `SegmentedControl`, `EmptyState`, `Skeleton`, `Toast`, `Breadcrumbs`,
   `FormField` (label, help, error), `SettingsLayout`. Screens use them and drop their improvised
   CSS.
6. **Checks.** Every semantic text and border pair meets WCAG AA in light and dark, verified by a
   test over the token file. Visual baselines are re-recorded surface by surface, with each changed
   screenshot inspected.

The user chose Direction B, "Open" (U-D6, ADR-039), which sets the values for points 1–4.

## Packages (Track U)

| Package | Release | Needs | Scope |
| --- | --- | --- | --- |
| CN1 | 0.9 | C15 | **Delivered 2026-10-05** ([plan](BASE_0_9_IMPLEMENTATION_PLAN.md#cn1-the-consumer-apis-name-in-public-contracts)). Rename the namespace in public contracts per U-D1 before C6 publishes it in the API index and C9–C11 put it in events and subscriptions: route placeholder, error details, docs, journey tests. Model field `key` unchanged |
| U1 | 0.9 | — | **Mockups delivered 2026-10-05** ([canvas](https://claude.ai/artifact/GmafaZfJ6PxbXs8rGVysMc): today's baselines with the audit, Direction A "Framed" and Direction B "Open", three screens each, light and dark); **Direction B chosen 2026-10-05 (U-D6, ADR-039).** Visual direction. A screenshot audit of today's surfaces against the diagnosis, then two alternative directions (tokens, rail, page header, a table page, a record page, a settings page, light and dark) as clickable mockups. The user chooses, and the choice is recorded as an ADR. No product code. A filler, any time |
| U2 | 0.9 | U1 | **Delivered 2026-10-06** ([record](#u2-delivery-record)). Foundation: the token layers, the type and spacing scale, the components above, the rail and header, the data-context bar. Applied to the shell. Contrast test over the tokens. Shell baselines re-recorded |
| U3 | 0.9 | U2 | **Delivered 2026-10-06** ([record](#u3-delivery-record); U-D10 and U-D11). Settings area: `/settings` routes and layout; About, Appearance and Deployment; Workspaces and Model moved under Administration (old URLs redirect); the popover reduced to account and theme with a link to Settings; `GET /api/v1/system` |
| UA | 0.9 | U3 | **Planned 2026-10-06** ([plan](#ua-the-atlas-redesign); ADR-040, U-D12, U-D13). The Atlas redesign of every surface in one pass, the record browser first, each surface approved by the user from screenshots; replaces the older styles; folds in U6 |
| UA8 | 0.9 | UA, K3a | **Implemented 2026-10-09** ([plan](#ua8-actions-in-place-on-the-record), [record](#ua8-record-2026-10-09); U-D15–U-D20), screenshots approved by the user 2026-10-10. A relationship row's actions as icon buttons; the record header's title and subtitle edited in place, through the one field editor the details panel uses; the header's Edit record button removed, the menu's Edit all fields renamed Edit record |
| UA9 | 0.9 | UA8 | **Implemented 2026-10-09** ([plan](#ua9-the-record-tree-scrolled-as-one-several-records-selected-and-dragged), [record](#ua9-record-2026-10-09); U-D21–U-D28), screenshots approved by the user 2026-10-10. The record tree (sidebar and hierarchy lens) scrolls as one list and starts folded; several records selected with Cmd/Ctrl and Shift and dragged together; the sidebar drags |
| U4 | 0.9 | UA, C6b, V2 | **Implemented 2026-10-07** ([plan](#u4-the-integration-pages), [record](#u4-record-2026-10-07)), screenshots approved by the user 2026-10-10. Integration pages: Consumer APIs, Jobs and feed, API reference. Starter consumer API per U-D5 |
| U5 | 0.9 | U4, C12 | **Implemented 2026-10-07** ([plan](#u5-the-webhooks-page), [record](#u5-record-2026-10-07)), screenshots approved by the user 2026-10-07. Webhooks page over the subscriptions API (C12 delivered 2026-10-06: `delivery`, the four dispatcher reasons, `reset`) |
| U5a | 0.9 | U5 | **Implemented 2026-10-07** ([plan](#u5a-webhook-names-the-delivery-log-and-the-webhooks-page-revised), [record](#u5a-record-2026-10-07)), screenshots approved by the user 2026-10-07. Webhook names, the delivery log and its routes, the dialog rebuilt, the Configuration and Deliveries tabs |
| U6 | — | — | **Folded into UA (2026-10-06):** the remaining surfaces are redesigned in UA, in 0.9. 0.10's editor (A4) builds on UA |
| U7 | 0.11 | U3 | Operations page over 0.11's health, readiness, metrics and backup routes. **Delivered in 0.11 O2 (2026-10-22)**, screenshots approved |
| U8 | 0.12 | U5 | Security pages: sign-in and account; users and roles; OAuth clients and their access per consumer API; webhook signing-key rotation (keys are generated and shown once from 0.9, U5). Replaces 0.12's "UI administration" items with pages in this area |

Order in the 0.9 queue (U-D4): CN1 right after C15; U1 any time as a filler; U2 and U3 after C13
and before J4, so the import screen is built on the foundation; U4 after V2; U5 after C12. All
above the cut line (D9): they are UI work and do not lengthen the API lines. _Revised 2026-10-06
(user):_ U2 is delivered alongside C10 rather than after C13. It needs only U1, and the two share
no code ([U2, running beside C10](#running-beside-c10)).

### U2: the foundation and the shell

**Planned and delivered 2026-10-06** ([record](#u2-delivery-record)). Needs U1 (delivered). [U-D7–U-D9](#decisions) are decided (2026-10-06).

**Outcome.** The product looks like Direction B on every screen, because the old token names now
resolve to the new semantic roles. The shell (top bar, rail, data-context band) is rebuilt to
ADR-039, and its contrast is checked by a test. Screens keep their markup until U6 (U-D7). A user
can tell live data, a change set and a publication apart at a glance and by text.

**Reference.** The [U1 canvas](https://claude.ai/artifact/GmafaZfJ6PxbXs8rGVysMc), Direction B
(`B-Collection`, `B-Record`), and [ADR-039](DECISIONS.md#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state).
`B-Settings` belongs to U3.

#### What exists (checked 2026-10-06)

- `styles/base.css` holds about 60 flat tokens (`--ink`, `--muted`, `--accent`, `--surface`, …) in
  one layer, with a dark block for `[data-theme="dark"]` and one for `prefers-color-scheme`. The
  other style files hold no hex values and read only these tokens: 409 uses in `components.css`,
  101 in `layout.css`. So changing what the tokens resolve to re-colours every screen.
- `app/AppShell.tsx` renders a global header (product mark, application tabs, model version, the
  Models and Workspaces links). The rail (`aside`) holds the workspace selector, the explorer and
  `SettingsMenu` (the theme popover). `main` starts with `.context-bar`, which shows the context
  status and the Live / Change sets / Publications switch.
- `app/App.tsx` renders `ChangeSetActions` (Review, Validate, Publish, More) and
  `PublicationBanner` above every page in their contexts. These are the band's actions today. U2
  moves and restyles them and does not change their behaviour.
- Ten screens write their own `<header className="page-header">` with an `h1`.
- All 41 visual baselines (`e2e/baselines/`, 24 light and 17 dark) include the shell.
- Fonts: the system stack with Inter first. No font is bundled.
- Contrast of the mockup's values (light / dark, WCAG): every text pair passes, from 5.3:1
  (`ink-3` on the rail) up. The control border (`#cfccc4` on white) is 1.6:1 and the light-mode
  change-set dot on its band is 2.9:1. Both are below the 3:1 that WCAG 1.4.11 asks of a boundary
  or marker that is the only way to see a control or state (U-D9).

#### Scope

1. **Token layers** in a new `styles/tokens.css`, imported first:
   - *Primitives*: neutral (warm grey), indigo (brand), green, amber, violet and red scales,
     50–900, taken from the mockup's values.
   - *Semantic roles* (light, then dark, which redefines this layer only): `surface.{app, nav, top,
     sunken, raised}`, `text.{primary, secondary, tertiary, on-action}`, `border.{subtle, strong,
     control}`, `action.primary`, `link`, `state.selected` and `state.selected-text`,
     `status.{draft, live, published, conflict, error, warning, success}`, `context.{live,
     changeSet, publication}` (each with surface, text, marker and line), and `focus.ring`. Written
     as `--surface-app` and so on.
   - *Component tokens* for the shell and the two new components only (`--topbar-*`, `--rail-*`,
     `--band-*`, `--pill-*`).
   - *Old names as aliases.* Each of `base.css`'s tokens becomes an alias of one semantic role,
     listed once in a mapping block marked for removal in U6. `--accent-soft` becomes
     `state.selected`; `--success*` becomes `status.success`; and so on. No other style file
     changes for colour.
2. **Type and spacing.** Instrument Sans (400, 500, 600) and JetBrains Mono (400, 500) from
   `@fontsource/instrument-sans` and `@fontsource/jetbrains-mono` (OFL-1.1, checked on npm). They
   are imported in `main.tsx`, so Vite bundles them into `dist` and they are served from the
   engine with no internet access (ADR-039). Six type steps: 12 (column headers), 13 (meta), 14
   (body), 15 (section headings), 19 (sub-page headings), 30 (page titles). A 4px spacing scale,
   `--space-1` to `--space-10`. Mono for codes, keys and URLs through `--font-mono`, which existing
   code classes already read. Table density tokens arrive in U3 with the Appearance control that
   switches them.
3. **Shell** (`AppShell`), to ADR-039:
   - The *top bar* holds the product mark, then the workspace switcher (moved from the rail; it
     keeps its label, "Manage workspaces" entry and capability rule, and is hidden on admin
     routes as today), then the applications as underlined tabs (ink underline on the current
     one, `aria-current` kept; the model's icon stays in the text colour, with no colour, since
     colour is kept for state). At the right: the model version (tertiary text, until U3's About
     page takes it), **Models** and **Workspaces** (until U3 moves them into Settings), and a gear
     button named **Settings** that opens today's popover (theme, the disabled Sign in). U3 turns
     the gear into the link to `/settings`.
   - The *rail* uses `surface.nav` with a 1px rule and holds only the explorer. Its width,
     resizer and drawer are unchanged.
   - At *390px*, the top bar keeps the mark, the workspace switcher and Settings. The application
     tabs move into the navigation drawer above the explorer. There is no horizontal scroll.
     _Amended in delivery:_ the tabs stay in the top bar, on a second row that scrolls sideways,
     beside Models and Workspaces. Runners and users reach them as before; the drawer keeps only
     the explorer.
4. **Data-context band** (`app/DataContextBand.tsx`): one region at the top of `main` replaces
   `.context-bar` and hosts `ChangeSetActions` and `PublicationBanner`, which App stops rendering
   separately. It is sticky while the page scrolls.
   - *Live*: a green **Live** pill and "Edits apply immediately in the {workspace} workspace".
   - *Change set*: an amber band across the content's width with the change set's name, version,
     source and model; then Review changes, Validate change set, Publish change set, More change
     set actions; then **Back to live**. _Amended in delivery:_ no separate **Back to live**; the
     switch's **Live** is the way back. "Changes here remain private…" became "Private until
     published" in the meta line, so the band is two lines.
   - *Publication*: the same band in violet with "Viewing Publication {n}", the pinned-model text
     and **Back to publications**.
   - The Live / Change sets / Publications switch stays at the band's right end in all three
     contexts. _Amended in delivery:_ below 760px the band scrolls with the page instead of
     staying visible, since on a phone it would cover much of the screen.
   - Behaviour, accessible names and roles do not change ("Change set publication", the buttons,
     "Workspace data context", "Current context"). The retired-workspace notice stays below the
     band.
5. **Components** in `ui/` (U-D8):
   - `PageHeader` (eyebrow, title with its ref and `tabIndex`, description, actions) replaces the
     ten hand-written page headers. Markup only: the existing classes go, and the output is the
     same apart from the type scale.
   - `StatusPill` (tone `live | changeSet | publication | draft | success | warning | error |
     neutral`, a marker plus text, never colour alone) is used by the band and by the
     `.context-status` sites.
   - `Card` (a titled block on `surface.raised` with a `border.subtle` outline, no shadow) is kept
     to be judged in the product (U-D8). Today's `.surface` panels take the same tokens, so U2's
     screenshots show how cards read in Direction B; U6 moves them onto `Card` or `Section`.
     The other listed components arrive with the package that first uses them (U3 or U6).
6. **Contrast test** (`src/styles/tokens.test.ts`, vitest node project). It reads `tokens.css`,
   resolves each role through the alias chain for light and dark, and checks a list of pairs
   written as role names:
   - every text role on each surface it is used on, at 4.5:1 (3:1 for the 30px title);
   - `border.control`, `focus.ring` and each `context.*` and `status.*` marker on its surface, at
     3:1 (U-D9);
   - `border.subtle` and `border.strong`, which are decorative rules (U-D9), are listed as exempt
     so that the exemption is visible.

   A failing pair names both roles, both values and the ratio.
7. **Open source.** The two fonts, their versions, OFL-1.1 and where they ship are added to
   [OPEN_SOURCE.md](OPEN_SOURCE.md), as ADR-039 asks.

**Not in U2:** Settings routes and pages and `GET /api/v1/system` (U3). Restructuring any screen
beyond its page header (U6). Density and theme controls beyond today's popover (U3). Any backend
change.

#### Checks

- **Focused unit tests:** `App.test.tsx`, `SettingsMenu.test.tsx` (the popover now opens from the
  top bar), `UIFoundation.test.tsx` (PageHeader, StatusPill, Card), a new `DataContextBand.test.tsx`
  (each of the three contexts: text, actions and the switch's `aria-current`),
  `ChangeSets.test.tsx` and `ChangeSetReview.test.tsx` (unchanged behaviour inside the band), and
  the contrast test. Then `npm run format`, `npm run lint` (no errors) and `npm run build`.
- **Browser, real backend:**
  - `test:browser` (wp9-navigation: shell, applications, explorer, 390px, keyboard order: skip
    link, then the top bar, the band, then content);
  - `test:browser:change-sets` (the band's actions in a change set, two applications);
  - `test:browser:publications` (the publication band).
- **Gates, run once each (U-D7):** `test:a11y` (light and dark), and `test:visual
  --update-baselines`. All 41 baselines are re-recorded, and each new screenshot is inspected
  against the U1 reference before it is kept. A screen whose re-colour reads wrong (for example,
  indigo where the old green meant status) goes to TODO against U6 with the screenshot named,
  unless it is a contrast or legibility failure, which is fixed in U2. A dark baseline of the band
  in a change set is added (`change-set-editing-dark`), so that the new surface has light and dark
  evidence.
- **UI acceptance:** [UI_ACCEPTANCE](testing/UI_ACCEPTANCE.md) gets a "Shell and data-context band"
  reference row and its state-inventory row. Its "Page surface" row now names `PageHeader`.
- **Reported separately:** functional, accessibility and visual evidence, with any surface whose
  appearance was not inspected marked unverified.

#### Running beside C10

C10 is backend work (event deriver, event store, pull feed: `backend/`, a migration, its `feed`
tests). U2 changes `frontend/` and documentation only, so they share no code. They can interfere
in three places, each with a rule:

1. **The backend the browser runners start.** The harness boots `backend/` from the working tree
   and clones its seeds by migration and model. While C10's migration or deriver is half written,
   that backend may not start, or it may rebuild seeds from an unfinished schema. **Rule:** U2's
   unit tests, lint, build and contrast test run at any time. Its browser runners and the two
   gates run only on a backend that starts cleanly with C10's focused checks passing, at the
   latest once C10 is delivered. If C10 is mid-change, U2 waits for it. It does not stash, revert
   or work around C10's files.
2. **Shared documents.** CHANGELOG, PROJECT_STATUS, TODO, the 0.9 plan's queue and
   EXECUTION_GUIDE are edited by both. **Rule:** each package edits only its own lines, by
   targeted edits and never by rewriting a file. U2's queue edit is its row (27a) and the Track U
   note. Nothing is committed by either package unless the user asks, and then by path, so each
   commit holds one package.
3. **The machine.** The visual and accessibility gates are the heaviest runs in U2. **Rule:** they
   are not started while C10 runs its own database-heavy checks, and each runs once. Runners use
   their own ports and database clones, and every clone and server they start is dropped when they
   end.

#### Exit

- The tokens are in three layers, and the old names are only aliases.
- The contrast test passes in light and dark.
- The fonts are bundled and listed in OPEN_SOURCE.
- The shell and the band match Direction B at 1440px and 390px, in light and dark.
- The ten page headers use `PageHeader`.
- The three browser runners and both gates pass, and all 41 or more baselines are re-recorded and
  inspected.
- The U2 record is written here, and the 0.9 plan's row is marked delivered.

#### U2 delivery record

**Delivered 2026-10-06.** C10 was delivered first the same day, so the browser runs used a clean
backend; nothing in `backend/` changed.

**Built:**
- **Tokens** (`frontend/src/styles/tokens.css`):
  - Primitives: warm neutrals for light, cool neutrals for dark; indigo, green, amber, violet and
    red scales; the type steps 12, 13, 14, 15, 19 and 30; `--space-1` to `--space-10`.
  - Semantic roles for light, with dark redefining only that layer, written once per dark trigger.
  - Component tokens for the top bar, rail, band, pill and card.
  - `base.css` keeps the ~60 older names, each an alias of one role, marked for removal in U6.
  - `border.control` (3:1) now draws every control's outline: buttons, fields, the search box,
    combo boxes, inline editors, the tree switch, "Load more", the window scrollbar.
- **Fonts:** `@fontsource-variable/instrument-sans` and `@fontsource-variable/jetbrains-mono`
  5.3.0, imported in `main.tsx` and bundled into `dist`. They are the variable versions, so the
  existing 550/650 weights render without synthesis. `code`, `kbd` and the JSON fields use
  `--font-mono`.
- **Shell** (`app/AppShell.tsx`):
  - The top bar holds the mark, the workspace switcher (moved from the rail; label read by
    assistive technology), the application tabs (ink underline, no model colour), the model
    version, Models, Workspaces, and the gear named **Settings**, which opens the existing popover
    (`app/SettingsMenu.tsx`).
  - The rail holds the explorer only.
- **Band** (`app/DataContextBand.tsx`):
  - Live, change set and publication. `App` passes `ChangeSetActions` or `PublicationBanner` in
    as `contextActions`, and their behaviour is unchanged.
  - The change set's reports (validation, refusals, model mismatch) render just below the band
    through `ui/ContextBandSlot.tsx`, so the band stays short while it is visible.
  - The publication bar is a labelled section in the violet band.
- **Components:** `ui/PageHeader` (the ten page headers, including the record header with its
  context menu), `ui/StatusPill` (the band, the change set cards, and the Models and Workspaces
  context lines), and `ui/Card` (with `.surface` panels on the same card tokens, per U-D8).
- **Contrast test** (`src/styles/tokens.test.ts`, `unit` project): 6 tests.
  - The unit project now keeps `tokens.css` for `?raw` reads (`vite.config.ts`).
  - The test caught one value: the dark draft marker was 2.97:1 and now uses a lighter step.
- **Visual gate:** adds `change-set-editing-dark`, so there are 42 baselines.
- **Open source:** both fonts are listed in [OPEN_SOURCE.md](OPEN_SOURCE.md).

**Differs from the plan** (each amended above):
- The application tabs stay in the top bar at 390px.
- No separate **Back to live** in the band.
- The band is not sticky below 760px.
- The model's application colour no longer tints the application glyphs or the record header icon,
  since colour is kept for state.
- The tree's drag preview is now opaque, and its type label takes the status ink. Its 0.94 opacity
  let the row behind pull the label to below 4.5:1, which was the only `test:a11y` failure.

**Checks:**
- **Unit** (`vitest related` over every changed source): 14 files, 186 tests passed.
- **Contrast test:** 6 passed.
- **Static:** `format:check` clean; `lint` 0 errors (the 8 warnings are the existing ones in files
  this package did not change at those lines); `build` passed.
- **Browser, real backend:**
  - `test:browser` (wp9-navigation: two object types, live and change set, keyboard, 1440 and
    390px) passed, then failed once and passed on the run after. The failure was a 10 s
    `waitForURL` in the 390px change-set record-return step (`ui03a-navigation.mjs:144`), after
    the band became static on phones. It did not repeat and is recorded in TODO.
  - `test:browser:change-sets` and `test:browser:publications` passed.
- **Gates** (U-D7):
  - `test:a11y`: 50 checks. The first run failed on the drag preview (above). The rerun after the
    fix passed with no violations, light and dark.
  - `test:visual --update-baselines`: all 42 baselines re-recorded, then compared (passed).

**Evidence, reported separately:**
- *Functional:* the shell, band and page headers in the three runners above.
- *Accessibility:* the axe gate and the token test. Keyboard order (skip link, top bar, band,
  content) is exercised by wp9-navigation.
- *Visual:* 26 of the 42 baselines were opened and inspected against the U1 reference, plus two
  390px screenshots from the navigation runner. They cover every surface in at least one theme:
  collection (both applications), record, change-set record and band (light and dark), review
  (light and dark), change sets, publications, models, workspaces (light and dark), relation matrix
  and its cell dialog, tree lens, tree drag (accepted and refused), move dialogs, restructuring
  previews and the scrolling list. The other 16 are the other theme of a screen that was opened.
  They were compared, and they are covered by the contrast test and the dark axe scenarios, but not
  opened one by one.

**Not run:** the other browser runners and both full suites (R), and the backend (unchanged).

**For U6** (in TODO):
- Boolean and other values still render as green "Yes" pills. ADR-039 asks for plain text.
- The `.surface` panels are to move onto `Card` or a ruled section.
- The older token names are to be removed.

### U3: the settings area

**Delivered 2026-10-06** ([record](#u3-delivery-record)). Planned 2026-10-06; [U-D10](#decisions)
and U-D11 decided the same day. U3 depends on no C-track package; its
place after C13 (27b, before J4) is the order the user chose on 2026-10-06, not a dependency. If it
is moved forward, as U2 was, the rules in [Running beside C12](#running-beside-c12) apply.

**Outcome.** One **Settings** area at `/settings`, with its own top bar and a grouped side
navigation (ADR-039, `B-Settings`). An operator reads what the deployment runs (engine, API, schema
languages, active model release, database revision) and how it is configured (every setting, where
its value came from, and the capability groups) on **About** and **Deployment**. The same facts come
from one new route, `GET /api/v1/system`. A user picks the theme and table density on
**Appearance**. **Workspaces** and **Model** move under Administration. The old URLs redirect, and
the pages behave as before.

**Reference.** The [U1 canvas](https://claude.ai/artifact/GmafaZfJ6PxbXs8rGVysMc), `B-Settings`:
the top bar reads "{product} / Settings" with **Back to applications** and the account at the right.
The rail holds the navigation, with group headings in tertiary ink and the current page in
`state.selected`. Content is at most 1040px wide, with a 30px title and ruled sections. The settings
table [above](#settings-area) and [`GET /api/v1/system`](#get-apiv1system-u3) are the scope.

**Composable domains (ADR-032):** no door is affected. U3 adds a read of the deployment and moves
two pages. It does not touch identity, attribute storage, audit, bulk APIs, `match` or mapping
coverage.

#### What exists (checked 2026-10-06)

- **Settings.** `config.Settings` reads 22 environment variables (`config.py`, `from_env`). Their
  meanings are written once, in [OPERATIONS § Settings](OPERATIONS.md#settings), in four tables:
  runtime, capability groups, batch and job limits, and webhook subscriptions. Nothing in the code
  links a setting to its group or description. Two are secrets: `RDM_CURSOR_SIGNING_KEY` and
  `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`. `DATABASE_URL` carries a password. `VITE_API_URL` is the
  frontend's build setting, not the engine's.
- **Versions.**
  - The engine version `0.9.0-alpha.1` is written twice: `backend/pyproject.toml`, and `main.py`
    as the management document's `info.version`.
  - Schema languages: `engine/model/compiler.SUPPORTED_SCHEMA_VERSIONS`.
  - The migration revision is read only at startup (`db._check_revision`, through Alembic's
    `MigrationContext`).
  - The active release is in `GET /model-runtime-state` (`activeReleaseId`; `updatedAt` is set when
    a release is activated or its schema is upgraded, `engine/model/releases.py:161`). Its name and
    version are in `GET /model-releases/{id}`.
- **Capabilities.** `GET /api/v1/capabilities` reports six groups. Each names the `setting` that
  switches it, along with the limits.
- **Shell.**
  - `AppShell` renders the top bar: mark, workspace switcher, application tabs, the model version
    ("Model 0.9.0 · Schema 0.8"), **Models**, **Workspaces**, and the gear. The gear opens
    `SettingsMenu`, a popover with the Account placeholder and the theme radio group.
  - On `models` and `workspaces` routes (`isAdminRoute`), the shell hides the workspace switcher
    and the band, and the rail becomes a `SidebarSlot`.
  - The workspace switcher's **Manage workspaces** opens `/workspaces/{key}`.
- **Models and Workspaces put their catalogue in the rail.**
  - `ModelWorkbench` (295 lines) portals the release and draft lists into the rail
    (`SidebarPortal`) and shows the selected release or draft in `main`. Its URLs are `/models`,
    `?releaseId=` and `?draftId=`.
  - `WorkspaceAdmin` (702 lines) does the same with the workspace list, at `/workspaces` and
    `/workspaces/{key}`.
  - ADR-039 gives the rail to the settings navigation, so the catalogues need another place
    (U-D10).
- **Routing.** `parseRoute` reads the URL, and the router writes the canonical URL back with
  `replaceState` on first load (`app/useRouter.ts:76`). So an old URL parsed to a settings route is
  rewritten without a second history entry. The backend does not serve the SPA, so deep links need
  no server change.
- **Theme and density.**
  - The theme is stored per browser (`lib/theme.ts`, `rdm:theme:v1`) and is read by an inline
    script in `index.html` before first paint.
  - Density is already a per-view choice: `TableDisplay` stores `compact: boolean` with column
    visibility and widths per view, and `ObjectTable` adds `density-compact`. A stored `false`
    cannot be told apart from "never chosen".
- **Tests on these surfaces.**
  - `w4-workspace-admin` and `wp12-release-identity` open `/workspaces` and `/models` directly, and
    so do the accessibility and visual gates.
  - Four baselines show the two pages: `model-workbench` and `workspaces-admin`, light and dark.
  - `test_openapi_contract` locks the management document. `test_api_journeys` refuses a route the
    [API inventory](testing/API_JOURNEYS.md) does not map to a journey.
- **Open item from C11** ([TODO](TODO.md)): the Workspaces page gives no reason when delete is
  disabled by `deleteBlockedBy: subscribed`.

#### Scope

1. **`GET /api/v1/system`**, in a new `management/routers/system.py`. It is read-only and not
   behind a capability, like `/capabilities`.
   - The **engine version** has one home: `app/__init__.py` `ENGINE_VERSION`. `main.py` reads it
     for `info.version`, and a unit test holds it equal to `pyproject.toml`.
   - A **settings catalogue** in `config.py`. Each entry has the environment variable, its group
     (`runtime`, `capabilities`, `limits`, `webhooks`, the four OPERATIONS tables), a one-line
     description of what it controls, the default, and whether it is secret.
     - OPERATIONS keeps the runbook detail. The catalogue's line is the API's text. A unit test
       holds that every `Settings` field has exactly one entry and that every entry's variable
       appears in OPERATIONS, so neither can drift.
     - A setting C12 adds fails that test until it has an entry.
   - **Response.** It follows the [shape above](#get-apiv1system-u3), with four changes:
     - `activeModelRelease` adds `key` and `schemaVersion`. Its `activatedAt` is the runtime
       state's `updatedAt`.
     - `database` carries only `revision`, read from `alembic_version` on the request's session.
       `DATABASE_URL` appears once, in `settings`.
     - Each setting has `name` (the variable), `group`, `description`, `value`, `default` and
       `source` (`environment` or `default`). Values keep their types: integers, booleans, and
       lists for `CORS_ORIGINS` and the allowed hosts.
     - `DATABASE_URL`'s value drops its password, and keeps the user, host, port and database.
       Both secrets have `value: null` and `default: null`, and only `source` tells whether they
       are set. Nothing else in the response is secret.
   - **Engine side.** The engine reads the revision and the active release (`engine/reads/system.py`).
     The router presents them, with no model logic in the handler. One read, one session.
   - **0.12:** this route is for administrators once roles exist (U8). Until then it is as open as
     `/capabilities`, which already reports the allowlist.
2. **Settings shell** (`app/SettingsShell.tsx`). `App` renders it for every settings route in place
   of `AppShell`.
   - **Top bar.** The mark, a separator, then **Settings**. At the right: **Back to applications**
     and the account button. Back to applications returns to the last application route of the
     session, or the default route when there is none.
   - **No data context.** No workspace switcher, application tabs or data-context band, since
     settings are not workspace data.
   - **Rail.** The rail on `surface.nav` holds `nav aria-label="Settings"`, with the groups as
     headings and the pages as links with `aria-current="page"`. Its width and resizer are the
     application rail's.
   - **At 390px** the rail is replaced by a labelled select at the top of the content (as the
     settings table says), and the top bar keeps the mark, Settings and the account.
   - **Keyboard order:** skip link, top bar, settings navigation, content.
3. **Application shell changes** (`AppShell`, `SettingsMenu`).
   - The gear becomes a link named **Settings** to `/settings`. The **Models** and **Workspaces**
     links and the model-version text leave the top bar, since About shows the version.
   - The account button (initials on `surface.sunken`, named "Account") opens the popover from
     `SettingsMenu`. It keeps Account and the theme radio group and adds an **All settings** link.
   - **Manage workspaces** opens `/settings/workspaces/{key}`.
   - The `isAdminRoute` branches and the rail's `SidebarSlot` leave `AppShell`.
4. **Routes** (`routing/routes.ts`, `types/ui.ts`): one route kind, `settings`, with a `page` and
   the page's own selection.
   - `/settings` redirects to `/settings/about`. The pages are `/settings/about`,
     `/settings/appearance`, `/settings/deployment`, `/settings/workspaces`,
     `/settings/workspaces/{key}`, `/settings/model`, `/settings/model/releases/{id}` and
     `/settings/model/drafts/{id}`.
   - **Old URLs** parse to the new routes, and the router's first-load `replaceState` rewrites
     them: `/models` (with `releaseId` or `draftId`) and `/workspaces[/{key}]`. Their routes and
     tests go. Each redirect is held by a routes test.
   - **Navigation entries** list only built pages (U-D11). U4 and U5 add Integration's pages.
5. **Pages**, each `SettingsLayout` with `PageHeader` (the group as eyebrow) and `Section`s:
   - **About**: engine and management API version; schema languages; the active model release
     (name, key, version, schema language, activated at) with a link to its page under Model; the
     database revision. These are `DescriptionList`s over `GET /system`.
   - **Appearance**: Theme (System, Light, Dark) and Table density (Comfortable, Compact), as radio
     groups in `FormField`s. Both are saved in this browser, and the page says so.
     - Theme writes the same preference as the account popover.
     - Density is the default for every table. A view's own choice (the table display popover)
       overrides it. That popover gains **Default** and shows which density the default currently
       is.
     - Stored per-view preferences are read as `compact: true` → Compact and `false` → Default,
       since a stored `false` was never a deliberate choice that can be told apart.
   - **Deployment**: one `Section` per group, in OPERATIONS' order. Each is a ruled table: setting
     (variable in mono), value, default, source, what it controls.
     - A secret reads "Set" or "Not set".
     - An ephemeral `RDM_CURSOR_SIGNING_KEY` carries a warning line: cursors stop working on
       restart and differ between instances.
     - The capability groups lead the page, from `/capabilities`: on or off with the setting that
       switches them, and the limits under each.
     - A note says the values come from the environment and change only on restart (U-D2), and
       names the API address this UI calls (`VITE_API_URL`).
   - **Workspaces** and **Model**, as a list page and a detail page each (U-D10). Their behaviour, dialogs, capability
     rules, errors and paging (cursors with Load more) do not change. The release diff, draft
     editor and workspace detail keep their markup inside the page; U6 restyles them.
     - Workspace delete, when blocked by `subscribed`, gives the reason: "Delete its webhook
       subscriptions first, or retire it" (C11's TODO).
6. **Components** in `ui/`, each with its first uses (U-D8):
   - `SettingsLayout`: the settings pages.
   - `Section`: a titled block with a rule under its heading, no card. Every settings page uses it.
   - `DescriptionList`: About, and the workspace and release facts.
   - `FormField` (label, help, error): Appearance, and the create and rename workspace dialogs.
   - `EmptyState` (message and an action): no drafts, and no workspaces matching a filter.
   - `Skeleton`: About and Deployment while `/system` loads.
   - `Toast`: the confirmation after workspace create, delete or default change, and after draft
     install or release activation, in place of the pages' inline success notices. It uses
     `role="status"` and stays until dismissed or until it has been visible for 8 s without hover
     or focus. Errors stay inline.

**Not in U3:** Integration and Security pages (U4, U5, U8). Editing any deployment setting (U-D2).
Restyling the content of the release diff, the draft editor or the record screens (U6). Removing the
old token aliases (U6).

#### Checks

Test work stays within about a quarter of the package. Journey cases are written first, from this
plan, and seen to fail.

- **Journeys and inventory.** [USER_JOURNEYS](product-functionality/USER_JOURNEYS.md) gets **J31 —
  Check what a deployment runs and how it is configured** (operator; API and UI). Its variants:
  - J31.1 a setting from the environment against one left at its default;
  - J31.2 secrets and the database password never returned;
  - J31.3 the active release after an activation.

  J08 and J19 name the settings pages as their UI path.
  [API_JOURNEYS](testing/API_JOURNEYS.md) maps `GET /api/v1/system` to J31.
- **Backend** (`startup` and `contract` groups only, per the
  [execution guide](testing/EXECUTION_GUIDE.md)):
  - `test_j31_system` (in `startup`): defaults with `source: default`; two variables set in the
    environment and reported with `source: environment` and typed values; `DATABASE_URL` without
    its password; both secrets `null`, set and unset; the revision equal to Alembic's head; the
    active release and `activatedAt` after an activation.
  - Unit (`tests/unit/test_config.py`): the catalogue covers every `Settings` field once and
    matches OPERATIONS; the URL masking (with a password, without one, user only);
    `ENGINE_VERSION` equals `pyproject.toml`.
  - `contract`: the OpenAPI lock regenerated for the one new route; `test_api_journeys` and
    `test_boundaries` pass.
- **Frontend unit** (`vitest related` over the changed sources): `routes.test.ts` (every settings
  URL both ways, and each old-URL redirect), `App.test.tsx`, `SettingsMenu.test.tsx` (account
  popover and its link), a new `Settings.test.tsx` (navigation, `aria-current`, the 390px select,
  About and Deployment over a fixture response, secrets shown as Set or Not set, Appearance writing
  both preferences), `localPreference.test.tsx` (density default and override),
  `ModelWorkbench.test.tsx`, `ModelReleaseDetail.test.tsx`, `WorkspaceAdmin.test.tsx` (the new
  layout, behaviour unchanged, and the `subscribed` reason), and `UIFoundation.test.tsx` for the
  seven components. Then `format`, `lint` (no errors) and `build`.
- **Browser, real backend:**
  - A new runner, `e2e/u3-settings.mjs` (`test:browser:settings`), at 1440 and 390px:
    1. Open Settings from the gear in two applications, and come back to each with Back to
       applications.
    2. Visit every page.
    3. Load each old URL and land on its page.
    4. Choose Compact on Appearance and see it in two views of different object types. A view's
       own choice wins.
    5. Keyboard order.
  - `test:browser:w4` and `test:browser:wp12`, moved to the new URLs. `test:browser:wp11`.
    `test:browser` (wp9-navigation: the top bar without Models and Workspaces).
- **Gates, run once each.** `test:a11y`, with the settings pages added in light and dark. Then
  `test:visual --update-baselines`.
  - The four Models and Workspaces baselines are replaced by `settings-model` and
    `settings-workspaces` (light and dark), `settings-release-detail` and
    `settings-workspace-detail` (light).
  - Added: `settings-about` and `settings-deployment` (light and dark) and `settings-appearance`
    (light). The gate holds 49.
  - Every baseline whose top bar changed is re-recorded. Each new or moved screenshot is opened and
    checked against `B-Settings`. The others are compared, and the record says which were opened.
  - This repeats U-D7's exception for the reason ADR-039 gives: "baselines re-recorded surface by
    surface (U3 settings)". The moved pages' baselines fail at their old URLs whichever way it is
    run.
- **Documentation.**
  - [PRODUCT](PRODUCT.md) and [CURRENT_FUNCTIONALITY](product-functionality/CURRENT_FUNCTIONALITY.md):
    the settings area.
  - [API](API.md): `/system`.
  - [OPERATIONS](OPERATIONS.md): the Deployment page, and the catalogue rule for new settings.
  - [ARCHITECTURE](ARCHITECTURE.md): the two shells.
  - [UI_ACCEPTANCE](testing/UI_ACCEPTANCE.md): a "Settings layout" reference row and its state
    inventory.
  - [EXECUTION_GUIDE](testing/EXECUTION_GUIDE.md): the runner and `test_j31_system`.
  - CHANGELOG, PROJECT_STATUS, and TODO (C11's item closed).

#### Running beside C12

If the user runs U3 beside C12, U2's three rules ([Running beside C10](#running-beside-c10)) apply
unchanged: browser runs on a cleanly starting backend, own lines in shared documents, heavy gates
not beside C12's database checks. U3 changes `backend/` (`config.py`, `main.py`, a router, an
engine read, the OpenAPI lock), so two more rules apply:

- **Settings.** C12 is likely to add delivery settings to `config.py`. Whichever package lands
  second adds their catalogue entries; the catalogue test fails until it does. Neither package
  edits the other's fields.
- **The OpenAPI lock and the API inventory.** They are regenerated or edited after the other
  package's last change to them, never merged by hand mid-change.

#### Exit

- `GET /api/v1/system` answers as specified, in OpenAPI and the API inventory, with J31's cases
  passing.
- Every setting is in the catalogue and on Deployment, and no secret is returned.
- The settings shell, navigation and the five pages work at 1440px and 390px, in light and dark.
- The old URLs redirect, and the Workspaces and Model pages behave as before.
- The seven components exist, each with its first uses.
- The runners and both gates pass, and the baselines are re-recorded and inspected.
- The U3 record is written here, and the 0.9 plan's row is marked delivered.

#### U3 delivery record

**Delivered 2026-10-06.** C12 and C13 were delivered first, so nothing ran beside them.

**Built:**
- **`GET /api/v1/system`** (`management/routers/system.py`, `engine/reads/system.py`,
  `management/schemas/system.py`), as specified. The settings come from `config.SETTINGS_CATALOGUE`
  (22 entries: variable, field, group, description, secret) through `config.describe_settings`,
  computed once in `create_app`, since values change only with a restart.
- **Settings shell** (`app/SettingsShell.tsx`, `app/SettingsArea.tsx`): top bar, rail with
  `nav aria-label="Settings"` and the rail's resize handle, the 390px page select with Back to
  applications beside it. `App` renders it for every `settings` route; the application content no
  longer branches on administration routes. `useRouter` remembers the last application route.
- **Pages:** About, Appearance and Deployment (`features/settings/`); Workspaces and Model rebuilt as
  list and detail pages (`WorkspaceAdmin`, `ModelWorkbench`) with their dialogs, rules and errors
  unchanged.
- **Routes:** one `settings` kind with a `page`; `/models[?releaseId|draftId]` and
  `/workspaces[/{key}]` parse to it. `isAdminRoute` and `AdminRoute` are gone.
- **Top bar:** a **Settings** link (the gear) and the **Account** popover (`AccountMenu` in
  `app/SettingsMenu.tsx`) with Account, Theme and **All settings**; Models, Workspaces and the model
  version left it. **Manage workspaces** opens `/settings/workspaces/{key}`.
- **Components** (U-D8): `SettingsLayout`, `Section`, `DescriptionList`, `FormField` (create and
  rename workspace dialogs, Appearance), `EmptyState` (no drafts, no workspace matching the filter),
  `Skeleton` (About, Deployment, the detail pages), `Toast` (create, rename, default, retire,
  reactivate and delete a workspace; install and activate a release; delete a draft). Plus
  `ui/RouteLink` for links that navigate in place, and `lib/tableDensity.ts`.
- **Density:** the default every table starts from (Appearance); the Display popover offers
  **Default (Compact|Comfortable)**, Comfortable and Compact. A stored `compact: true` reads as
  Compact, `false` as Default.
- **Removed:** `features/administration/CapabilityStatus.tsx` (Deployment's capability groups and a
  notice on a disabled page replace it), `ui/SidebarSlot.tsx`, and their CSS.
- C11's TODO is closed: a workspace blocked by `subscribed` says "Delete its webhook subscriptions
  first, or retire it".

**Differs from the plan** (each found during the work):
- `ENGINE_VERSION` lives in `config.py`, not `app/__init__.py`: the tier rules
  (`test_boundaries`) let `management/` import `app.config` but not the package root.
- `source` is `environment` when the variable is set to a non-empty value. `DATABASE_URL` also loses a
  `password` query parameter, and reads `null` if it cannot be parsed as a URL.
- The account button shows a person glyph, not initials: single-user mode has no name to take
  them from.
- A detail page's title (h1) is the workspace's, release's or draft's name. The name heading inside
  the release and draft details was dropped, and their section headings moved from h3 to h2. The
  accessibility gate's heading-order rule found the gap.
- Workspaces gained a filter (server search), which gives `EmptyState` its "no match" use. The
  Workspaces entry is listed when workspace administration is off, since the page is read only, not
  missing.
- Settings tables are labelled, focusable groups (axe `scrollable-region-focusable`) and stack row
  by row below 760px. The new `EmptyState` uses its own class (`empty-message`). The older
  `.empty-state` on the record screens is U6's.
- The visual gate's `compareScreenshot` takes `mask` locators, covering values that differ between
  runs (times, the harness's ports and paths).
- `wp9-publications` checked the pinned model in the top bar's version text. It now checks the
  publication bar, which names it.

**Checks:**
- **Backend:**
  - J31's 12 cases (two configurations) were written first and failed with `404`, then passed.
  - `tests/unit/test_config.py`: catalogue coverage, each setting in its OPERATIONS table, typed
    values and source, secrets, five URL-masking cases, and the version against `pyproject.toml`.
  - `startup` and `contract` groups: 220 passed in 41 s; their serial part selects nothing.
  - OpenAPI lock regenerated: removing `/system` and its five schemas gives the previous hash.
  - `ruff check` clean.
- **Frontend unit:** `vitest related` over the 33 changed sources: 35 files, 360 tests passed.
  Then `format`, `lint` (0 errors; the 7 warnings are older ones, two of them carried unchanged into
  `ModelWorkbench`), `tsc`, `build`.
- **Browser, real backend:**
  - `test:browser:settings` (new, 9 checks, 1440 and 390px). Its first runs found the resize handle
    outside a landmark, an unfocusable scrolling table and an overflowing Runtime table; all fixed.
  - `test:browser:w4` (21 checks, moved to the new pages), `test:browser:wp12` (7, new URLs, the
    activation toast), `test:browser:wp11` (5).
  - `test:browser` (wp9-navigation) failed at 390px on the Model page: the disabled notice's flex
    layout and an unbreakable setting name. Fixed (`Notice`), then passed.
  - `test:browser:publications` passed.
- **Gates:**
  - `test:a11y`: the first run failed on `settings-release-detail` light and dark (heading order,
    above). The rerun passed, 61 scenarios with no violations. They include the six settings pages
    light and dark and the 390px page select.
  - `test:visual --update-baselines`, then a compare: 49 baselines, passed. The last re-record
    followed the workspace page's alignment fix and the narrowed Model masks.

**Evidence, reported separately:**
- *Functional:* the runners and unit tests above.
- *Accessibility:* the axe gate and the runners' axe scans. Keyboard order (skip link, top bar,
  settings navigation and its resize handle, content) is checked in `u3-settings`.
- *Visual:* all 11 new baselines were opened and checked against `B-Settings`: `settings-about`,
  `-model`, `-workspaces`, `-deployment` (light and dark), `-appearance`, `-release-detail` and
  `-workspace-detail`. Also the runner's 1440 and 390px screenshots of About, Deployment and Model.
  - The 38 changed shell baselines differ only in the top bar. `collection-table-domain-light` was
    opened. The others were compared but not opened one by one.
  - Release and draft details keep their card look inside the page until U6.

**Not run:** the full suites and the other browser runners (build acceptance, R).

#### U3 revisions after delivery (2026-10-06)

The user looked at U3 in the running app the same day and asked for changes. Each was made and
checked before UA was planned.

- **Workspaces and Model** (U-D10 revised by the user): the list pages with tables and plain links
  read as bare hypertext. Both are back to the screens they were before U3: the catalogue (entries
  with icon, name, key and pill, the current one highlighted) beside the selected entry's card,
  with the old capability cards and detail markup. The catalogue now sits in the page, beside the
  settings navigation. Each entry keeps its own address (`/settings/workspaces/{key}`,
  `/settings/model/releases/{id}`, `/settings/model/drafts/{id}`); without one, the default
  workspace or the active release is shown. Below 760px the catalogue and the selection take
  turns, with **All workspaces** or **All releases and drafts** to go back.
  The tables, `RouteLink` rows, filter and list `EmptyState` of the first version are gone; toasts
  and the `subscribed` reason stay.
- **Width:** every settings page uses the application pages' width (1440px), not 1040px.
- **Phones:** the settings page select is replaced by the application pages' pattern, a
  **Settings: {page}** bar that opens the settings navigation in the navigation drawer. Back to
  applications keeps its icon in the top bar.
- **About:** **Open release** is a button.
- **Workspace switcher back in the rail** (revises ADR-039's shell and U2): at the top of the rail,
  above the application browser, with its pre-U2 styles; on phones it is in the Browse application
  drawer again.
- **Checks:** related unit tests 358 passed. One relation-matrix test failed once under the parallel
  run and passed three times alone, so it is listed in TODO as a flake. Lint 0 errors; build passed.
  Runners: `test:browser:settings` (9), `test:browser:w4` (21; one earlier run missed the re-created
  workspace in the switcher and passed on the rerun, also in TODO), `test:browser:wp12` (7) and
  `test:browser` passed. `test:a11y` 61 scenarios, no violations. `test:visual` re-recorded (49) and
  compared.
- **Found, not fixed:** with a popover open (Account, Display, Filter), the first click on the page
  only closes the popover; the user saw navigation that did not respond. No runner clicks the page
  with a popover open. Fixed first in UA (UA0).

### Atlas (ADR-040)

The direction the user chose on 2026-10-06 from five looks on the same screen with real data
([look canvas](https://claude.ai/artifact/P4BpxdQdyVYTAaQMRGnRFB), look **E**, "the mixture"; the
canvas holds the exact values). Today's calm shell and shapes, with colour that means something.

**Kept as it is now:** the top bar; the rail (workspace switcher, Collections, Browse records);
Instrument Sans and JetBrains Mono; 6px radius on controls, chips and tiles, 8px on cards; the
indigo accent for the primary action and links; ruled tables on a white card.

**Colour for kinds of record.**
- Every object type gets one hue from a fixed palette of eight: a soft fill, a dark ink of the same
  hue (4.5:1 on the fill and on white) and a marker. The canvas uses six of the hues for its six types; the other two
  complete the palette.
- How a type gets its hue is U-D13 (decided: automatically from the model's order, so any model
  is coloured and no renderer knows a type key; whether the palette uses other shades of the
  context colours or leaves them out is shown on the real app in UA1).
- Where the hue appears: a 22px tile with the type's icon in Collections; an 18px tile in the
  tree; the record header's 36–40px tile and a tinted header band in the inspector; chips for a
  related or parent record (table columns that show a record, breadcrumbs, the inspector's
  **Connected** list); the page header's tile on a collection.
- Values stay plain text; pills stay for states (ADR-039).

**Colour for where you are.** Live is a soft green strip with the Live chip and "Edits apply
immediately"; a change set is amber and a publication violet, in the same place, with a dot of
their colour on the Change sets and Publications tabs. The exact hues are the existing context
tokens. The palette in U-D13 must keep type hues distinguishable from these three.

**The record browser.** Every row shows the type tile; containment is shown by indentation with a
guide line; a group's count sits at the right; the selected record is filled with its type's
soft colour; type groups and records never look alike.

**The top bar.** Each application carries a small tile of its own colour (the application
palette follows the same rule as types, from the model's order), and the tabs start 36px after
the product name.

**Dark mode.** Every fill, ink and marker has a dark value; the contrast test covers the palette in
both themes.

### Type palettes A and B

_Their rework, so that they differ visibly, is [Base 0.14 UP1](BASE_0_14_IMPLEMENTATION_PLAN.md#up1-type-palettes-a-and-b-reworked) (2026-10-10)._

The eight type hues (U-D13) differ between the two palettes only in slots 3 and 4. **B is in the
tokens** (chosen by the user, 2026-10-06, after seeing both beside a change set); **A** keeps both
slots in the amber and violet families, at shades unlike the change-set and publication colours.
Both pass the contrast test (`tokens.test.ts`) in light and dark. Slots 1, 2 and 5–8 (teal, blue,
rose, coral, cyan, slate) are the same in both.

| Slot | A | B |
| --- | --- | --- |
| 3 | plum | magenta |
| 4 | gold | olive |

**To switch** (since the UA4 revision, 2026-10-07): Settings › Appearance › **Type colours**, saved
in this browser (`lib/palette`, `rdm:palette:v1`, applied before the first paint by `index.html`).
Both palettes are in `tokens.css`: B is the default mapping, and A is an override on
`:root[data-palette="a"]` with its own dark blocks, one step more specific than the light one. The
contrast test checks A in light and dark as it does B, and its two dark blocks for sameness. To make
A the default for everyone, swap which family the base blocks and the override name.

Palette A (commit `226beb2`):

```css
  --plum-50: #f5e8f8;
  --plum-500: #ac5cc0;
  --plum-800: #7b2d8e;
  --plum-dark-50: #2e1935;
  --plum-dark-400: #bf78d2;
  --plum-dark-100: #e3b8ee;
  --gold-50: #faf1c8;
  --gold-500: #a17f00;
  --gold-800: #6a5200;
  --gold-dark-50: #2c2510;
  --gold-dark-400: #c9a21a;
  --gold-dark-100: #ecd78a;
```

Palette B (in the tokens since 2026-10-06, commit `6db248a`):

```css
  --magenta-50: #fbe6f6;
  --magenta-500: #cf4fae;
  --magenta-800: #972178;
  --magenta-dark-50: #361630;
  --magenta-dark-400: #de6cc0;
  --magenta-dark-100: #f2b0e0;
  --olive-50: #eef2d4;
  --olive-500: #7a8c18;
  --olive-800: #525d10;
  --olive-dark-50: #252a12;
  --olive-dark-400: #9fb236;
  --olive-dark-100: #d2dc95;
```

The slot mapping, light (dark: the `-dark-` shades in the same three roles):

```css
  /* A */                                /* B */
  --hue-3-fill: var(--plum-50);          --hue-3-fill: var(--magenta-50);
  --hue-3-ink: var(--plum-800);          --hue-3-ink: var(--magenta-800);
  --hue-3-marker: var(--plum-500);       --hue-3-marker: var(--magenta-500);
  --hue-4-fill: var(--gold-50);          --hue-4-fill: var(--olive-50);
  --hue-4-ink: var(--gold-800);          --hue-4-ink: var(--olive-800);
  --hue-4-marker: var(--gold-500);       --hue-4-marker: var(--olive-500);
```

### UA: the Atlas redesign

**Planned 2026-10-06** for a later session. Needs U3 (delivered and revised). U4 and U5 wait for
UA, so new pages land in the new look. U6 is folded into UA.

**Outcome.** Every surface in the Atlas look, coherent from the top bar to the dialogs, light and
dark, desktop and phone, with the older stylesheet layers removed instead of overridden.

**Revert point.** Today's design (U3 with its revisions) is committed and tagged
`ui-before-atlas` (2026-10-06), because the user asked for an easy way back to it. Each UA slice is
committed on its own, so one slice can be reverted without the others.
- See what UA changed: `git diff ui-before-atlas -- frontend/src`.
- Run the previous design beside the current one, without touching the working copy:
  `git worktree add ../rdm-engine-before-atlas ui-before-atlas`, then start its frontend there
  (`npm install`, `npm run dev -- --port 5174`) against the same backend. Remove it with
  `git worktree remove ../rdm-engine-before-atlas`.
- Its screenshots: `frontend/e2e/baselines/` at that tag (49, light and dark).
- Bring one surface back: `git checkout ui-before-atlas -- <its files>` and commit.

**How the user judges it** (the lesson of U2 and U3: tests showed the code worked, not that it
looked or felt right):
- Each slice ends with screenshots of its surfaces at 1440 and 390px, light (and dark in UA7),
  sent to the user, and a few minutes of the user using it on the dev server.
- The next slice starts only after the user says the surface is right. Changes asked for are made
  in the same slice.
- Where the canvas does not decide something, the slice shows two small variants on the real app
  and the user picks; no new rule is invented in writing alone.

**Slices**, in order:
- **UA0: popovers.** (The revert point `ui-before-atlas` exists since 2026-10-06.) Fix the popover click:
  a click on the page while a popover is open closes it and acts (React Aria `isNonModal` or an
  equivalent), with a regression test that clicks the application tabs and the settings navigation
  with the Account popover open. Look at the two flakes in TODO. Done only when the user has
  checked on the dev server that the settings navigation and the application tabs respond to the
  first click with a popover open (the user reported it twice, 2026-10-06).
- **UA1: tokens and type colours.** The eight-hue palette (fill, ink, marker; light and dark) and
  the context strips as tokens; the contrast test extended to them; `model/` gains the read that
  gives a type or an application its hue (U-D13), tested on two models. The top bar's application
  tiles and the rail's Collections tiles use it. (The tabs' 36px after the product name, asked by
  the user on 2026-10-06, was done in UA0.)
- **UA2: the record browser.** The tree as described above, on two models, by keyboard and at
  390px (drawer). The user's screenshot of the example model's tree (type groups, folders and records
  alike) is the case to fix.
- **UA3: the collection page.** Page header tile, the context strip, the table (a column showing a
  record as a chip in its type's colour), toolbar, empty and loading states.
- **UA4: the record.** Inspector and full page: tinted header with the type tile, breadcrumb chips,
  fields, the **Connected** list grouping related records by relation with type-coloured chips,
  history.
- **UA5: change sets and publications.** The amber and violet strips, the change set bar and its
  actions, the review screen, publications.
- **UA6: the rest.** Relation matrix, tree lens, mapping grid, dialogs, settings pages; the
  remaining `.surface` panels, the ~60 older token aliases and the unused rules in
  `components.css` removed.
- **UA7: dark mode and the gates.** Every surface in dark; `test:a11y` and `test:visual` with all
  baselines re-recorded; a screenshot of every screen in both themes for the user.

**Generic.** Every rule is driven by the model: hues by position, icons from the model's `icon`,
relation labels from relation types. Each slice is checked on the starter model and a generated
one; no renderer branches on a type or application key.

**Checks per slice:** `vitest related`, `format`, `lint`, `build`; the runners of the surfaces the
slice changes; the contrast test. `test:a11y` and `test:visual` once, in UA7, unless a slice asks.

**Not in UA:** new features, new routes or API changes; U4 and U5's pages (they come after, in the
new look).

#### UA0 record (2026-10-06)

Implemented; done when the user has checked it on the dev server (above).

- **Cause.** `ui/ControlPopover` used React Aria's modal `Popover`, which makes the rest of the page
  `inert` and lays a full-screen underlay over it while open. The first press landed on the
  underlay and only closed the popover.
- **Fix.** The popover is non-modal (`isNonModal`). React Aria leaves two things to its owner, done
  in `ControlPopover`: closing on a press outside (and on the user's wheel or touch scrolling,
  which the modal version prevented), and ignoring its own close-on-scroll for scrolls the layout
  causes. Without the second, applying a filter closed the Filter popover: the shorter list scrolls
  the document (found by `test:browser`). Escape and focus leaving close it as before. Focus is no
  longer trapped: Tab past the last control leaves the popover and closes it. The other popovers
  (`ActionMenu`, `Selection`, `AnchoredMenu`: menus and selects) stay modal, like native menus.
- **Flakes.** `test:browser:w4` step 11 was a real defect: opening the workspace switcher before the
  current workspace resolved left only that workspace in the list, since its label arriving as the
  input's value made React Aria's ComboBox filter by it. Reproduced by delaying
  `GET /workspaces/default` by 1.2 s (options: Default only; without the delay: all four). The
  switcher is disabled until the workspace resolves. `RelationMatrixView.test` "lets a reload replace
  cells…" did not reproduce: 30 repeats under a parallel `vitest related` run passed, it takes
  92 ms, and the code orders the cell patch before the dialog closes. It stays in TODO as observed
  once.
- **Tests.** `test:browser:settings` step 6: with Account open, one click on another application's
  tab and one on the Deployment link each close it and navigate, a click on the heading closes it,
  and axe runs with it open (0 violations). It failed before the fix ("app-shell intercepts pointer
  events"). Unit: `SettingsMenu.test` (outside press reaches its target and the page is not inert;
  inside press and Escape; layout scroll keeps it, wheel closes it) and `WorkspaceSelector.test`
  (opened before the workspace resolves, all workspaces listed), each failing before its fix.
- **Checks.** `vitest related` on the three changed files: 13 files, 176 tests passed. `format`,
  `lint` (0 errors), `build` passed. Runners passed: `test:browser:settings` (10), `test:browser:w4`,
  `test:browser` and `test:browser:a4`. `test:browser` failed once after the scroll fix and passed
  twice after; the failing step was not captured. `test:browser:a4` failed once at the matrix cell
  dialog's reopen after an unlink (line 383, `ui/Modal`, which UA0 does not touch) and passed on
  the rerun. Both are in TODO. No surface looks different, so there are no screenshots.
- **Top bar spacing** (the user, from another session the same day): the application tabs started
  20px after "RDM Engine" (the header's gap; about 28px before U2). They now start 36px after it,
  as ADR-040 says (`layout.css`); at 390px the tabs have their own row and are unchanged. Measured
  on the dev server: the mark ends at 143px, the first tab starts at 179px; no page overflow at
  either width. Every `test:visual` baseline shows the top bar, so they differ until UA7
  re-records them.
- **The header click on the dev server** (checked when the user said it was still the same): with
  Account open, and with Display open, one click on **RDM Systems** closed the popover and switched
  the application. This was checked on an application page only. The user meant the Settings
  page, whose top bar was a different one: its product mark was text, not a button, and it had no
  applications, so neither the click nor the spacing fix reached it. Reported as fixed when it
  was not; corrected below.
- **One top bar and one frame (U-D14).** `app/TopBar` (mark to home, application tabs, Settings,
  Account) and `app/ShellFrame` (skip link, top bar, resizable rail, drawer below 760px, main) are
  the only ones; `AppShell` and `SettingsShell` only fill the rail and the content. Exactly one
  item in the bar is current, marked the same way (ink underline, semibold): the application's
  tab, or on Settings the Settings link, which there reads as a tab with the gear and its name
  (asked by the user after U-D14 left Settings without a name in the bar; at 390px it sits in the
  first row, the applications below); the tab of the application last
  looked at returns to that route, another tab to its last collection or default view, the mark
  home. "Back to applications" and the "{product} / Settings" bar are gone with their CSS.
- **Copies removed** (jscpd over `src`, blocks of 6 lines or more; 0.32% duplicated lines after):
  the search box written five times is `ui/SearchField`, and the URL-backed search with its 250 ms
  timer written three times is `DebouncedSearchField` (collection toolbar, mapping grid, relation
  matrix; the matrix's column chooser and the tree use `SearchField`); the narrowed collection's
  banner written three times is `ScopeBanner`; the model-release picker written twice in
  `ChangeSets` is `ReleasePicker`; the change-review list frame written twice is `ChangeList`; the
  unused `.header-link` rules are gone; shadow and backdrop tokens moved from `base.css` into
  `tokens.css`, so their dark values sit in the two dark blocks `tokens.test` holds equal. What
  remains: the two dark blocks themselves (CSS cannot share one block between the media query and
  the attribute selector), and the mapping grid's and the matrix's page openings, which are now the
  same shared components called with different content.
- **Checks for the frame and the copies.** `vitest related` on the 18 changed source files: 14
  files, 186 tests passed. `format`, `lint` (0 errors), `build` passed. Runners passed:
  `test:browser:settings` (10; now also the same tabs and height as the application bar, the tabs
  36px after the mark on Settings, no tab current, the application's tab returning to its view, and
  the keyboard order home, tabs, Settings, Account), `wp14`, `a4`, `p2`, `change-sets`, `wp11`,
  `wp13c`, `w4`, `wp12`. `test:browser` passed 6 of 10 runs; the 4 failures are the intermittent
  record return in TODO (`ui03a-navigation.mjs:144`, waiting for the list URL after **Back to
  list**), which passed 2 of 2 runs without this session's changes, so a link to them is not ruled
  out; the cause is not found. `test:browser:b3` fails at the drag of Sodium
  (`helpers/tree.mjs:189`, no drag preview) with and without this session's changes.
- **Not run:** `test:a11y` and `test:visual` (UA7).

#### UA1 record (2026-10-06)

Implemented; the next slice waits for the user's pick between the two palettes (U-D13) and their
approval of the screenshots.

- **Tokens** (`styles/tokens.css`). Eight hue families as primitives, each a fill, a marker and an
  ink, with dark values. The semantic roles `--hue-1` … `--hue-8` (`-fill`, `-ink`, `-marker`) are
  slots, not colour names, so a palette change touches token values only; `[data-hue="n"]` maps a
  slot onto `--hue-fill`, `--hue-ink` and `--hue-marker` for a component. Teal, blue, rose and coral
  carry the canvas's fill and ink; the markers are a shade darker than the canvas where they fell
  under 3:1 on the rail. The context strips are `--context-{live,change-set,publication}-strip` and
  `-strip-line`, look E's green strip and its amber and violet counterparts, lighter than the
  context chip they carry; UA3 and UA5 put them on the page.
- **Contrast test** (`tokens.test.ts`), both themes: a hue's ink at 4.5:1 on its fill, on the page
  and on the rail; its marker at 3:1 on the page and the rail; the page's text, a link and the
  context's own text at 4.5:1 on each strip and the context marker at 3:1; strip lines exempt as
  separators. The dark-mode check now also covers the new primitive families.
- **The read** (`model/hues.ts`): `objectTypeHue` and `applicationHue` give slot
  `position mod 8 + 1` from `objectTypes` or `applications`; an undeclared key has none. Unit
  tests on the starter model and a generated 19-type model, plus the wrap, the order and an
  unknown key.
- **One component** (`ui/HueTile`): the model icon in the hue's ink on its fill, 18, 20 or 22px,
  neutral without a hue. The top bar's application tabs (20px) and the rail's Collections (22px)
  use it; UA2 uses the 18px tile in the tree. No renderer reads a key.
- **The two palettes for U-D13.** Slots 1–8 are teal, blue, ·, ·, rose, coral, cyan, slate in both;
  they differ in slots 3 and 4. **A, other shades:** plum and gold, the violet and amber families
  at shades unlike the publication and change-set colours. **B, left out:** magenta and olive,
  outside the three context families. A is in the tokens; B was shown by overriding the slot-3 and
  slot-4 roles on the dev server (light values `#fbe6f6`/`#972178`/`#cf4fae` and
  `#eef2d4`/`#525d10`/`#7a8c18`, all passing the same pairs; dark values follow when B is chosen).
  Seen on the example model: B's magenta (Master values) sits close to rose
  (another type's hue); A's gold and plum read as amber and violet only beside the Live chip, since no change
  set or publication was open.
  _Switched to B by the user (2026-10-06)_ after seeing both beside a change set: slots 3 and 4
  are magenta and olive in the tokens, with their dark values, under the same contrast test; the
  gold and plum primitives are removed (they are in commit `226beb2` if A is wanted back).
- **Hues repeat** after eight types: the example model has 18, and RDM Master's 12
  collections show two pairs of types in one hue (Domains with another type in teal, Codelists with
  another in blue). This
  is U-D13's rule (position over eight hues); a later schema may let a model name a hue.
- **Checks.** `vitest related` on the changed files: 5 files, 55 tests passed. `format`, `lint`
  (0 errors, the 7 recorded warnings), `build` passed. Runners passed: `test:browser:settings`
  (top bar: tabs, keyboard order, 36px after the mark, popover clicks, axe 0 violations) and
  `test:browser` (19 checks; the rail at 1440 and 390px, keyboard expansion). Screenshots at 1440px
  and 390px (drawer), light, both palettes, sent to the user. **Not run:** `test:a11y`,
  `test:visual` (UA7; every baseline now differs in the top bar).

#### UA2 record (2026-10-06)

Implemented; waiting for the user's approval of the screenshots. The tokens hold UA1's palette B
(magenta and olive), to which the user switched.

- **The case.** On the dev server (the example model), the type headings ("Codelists
  15"), the folders and the records all drew one grey icon at nearly one weight, and
  nothing showed what contains what.
- **Records** show their type's 18px `ui/HueTile` (`model/hues`); the selected record is filled
  with its type's soft colour in its ink, its tile turning white so it stays visible. The drag
  preview of the tree lens shows the same tile.
- **Type group headings** are quiet labels: no icon, 12px semibold in the tertiary text colour,
  the count at the right, 26px high. They still open their collection and keep their tree role.
- **Containment:** an open branch hangs from a 1px guide line below its record's toggle
  (`--tree-guide` on the branch's group); hover uses `--surface-hover`.
- **The variant not taken.** The canvas drew groups with their type's tile in bold, like records.
  Shown on the dev server as variant B: groups and records then differ only by weight, and the
  longer headings are cut off. A is in the code; both screenshots were
  sent.
- **Generic.** One tree for the sidebar and the tree lens; no key is read. Checked on the
  example model (dev server) and the starter and volume models (runners).
- **Tests.** `Explorer.test`: a record's tile and its selected fill carry its own type's slot, a
  heading has no tile, a branch's guide sits below its toggle.
- **Checks.** `vitest related`: 6 files, 119 tests passed. `format`, `lint` (0 errors), `build`
  passed. Runners passed: `test:browser` (keyboard expansion at desktop and 390px), `s6`, `wp14`.
  `test:browser:b3` failed twice at B5b, differently (TODO); before UA2 it stopped at the drag of
  Sodium, which now passes. Screenshots at 1440px and 390px (drawer), light. **Not run:**
  `test:a11y`, `test:visual` (UA7).

#### UA2 revision: framed groups (2026-10-06)

Asked by the user after UA3, from the example model's hierarchy lens: nested scrolling groups ran into
each other with no sign of which part scrolls, and a scrolled window could line up rows of
different groups as if they were one. The user keeps the nested windows and asked for frames.

- **Frames.** Every type group (heading and window) sits in a 1px frame of its type's marker at
  26%, radius 8, in the sidebar and the lens alike. While the group's own window scrolls, the frame
  glows in the accent (border, a 3px ring and a soft 16px glow, 700 ms after the last scroll; no
  transition under reduced motion). The glow is a state, not a kind, so it is the accent for every
  type; a nested group's scroll does not light its parent (`useScrolling` in `RecordTree`).
- **The area under the pointer** (asked by the user the next day, 2026-10-07). The innermost group
  under the pointer glows in `--active-area` (teal; its dark value in both dark blocks), a second
  colour beside the accent's scrolling glow, since the area the pointer is in may be a
  non-scrolling part of a scrolling one. While any group scrolls, only the scrolling one glows; the
  hover glow returns when it stops. CSS only (`:has`, under `@media (hover: hover)`).
- **Boxes inside boxes.** An open branch's frames start below its record's toggle, where the guide
  line ran, and the frame's edge replaces the guide line. Rows are indented from the box they are
  drawn in (`indent`, `boxStart`, `branchInset`) rather than from the tree's edge; groups have 8px
  between them at the top and 6px in a branch. The drag measures levels from the tree's edge
  (`useTreeDrag`), since nested rows now start further in.
- **Stops at a window's ends** (asked by the user, 2026-10-07: the nested windows felt wobbly
  because a flick that reached a window's end carried on into the area around it). With a pointer
  (`@media (pointer: fine)`), a window that scrolls stops at its first and last row
  (`overscroll-behavior: contain`); the area around it scrolls with the pointer outside the window.
  Touch keeps the carry-on, so a finger starting inside a window that fills the drawer can still
  move the page. A window that does not scroll passes the wheel on as before. Checked on the dev
  server: twelve wheel flicks inside the categories window scrolled it to its end, and neither the
  window around it nor the page moved. `s6` and `b3` (30 checks) passed.
- **Gestures, the parent row, fainter frames** (asked by the user after UA6, 2026-10-07). In the
  sidebar a group's window could fill the visible tree, so after its end every step stopped and the
  rail could not be scrolled on. Steps less than `GESTURE_GAP_MS` (400 ms) apart are now one gesture,
  which keeps the scroller it started with; a new gesture that starts on a group at its end, in
  full view, moves the nearest enclosing scroller that can still move (`outwardIndex`). Going up,
  the area brought into view includes the row of the record the group belongs to, so a heading is
  never shown without its owner. The DOM side moved from `RecordTree` into `useTreeWheel`. A
  group's resting frame is 14% of its type's marker (was 26%). Checked on the dev server: in the
  sidebar the first gesture scrolled the catalogues window to its end and brought it into view,
  each later gesture moved the rail on until Durations and Roles showed; in the lens one upward
  gesture showed the categories' heading and the catalogue row above it (120px, exactly the parent
  row's top); a step over a heading and steps over rows behaved as before. `src/features/objects`
  178 tests, `lint` (0 errors), `build`, `s6`, `wp14`, `b3` (30 checks) passed.
- **Frames only while scrolling** (asked by the user after UA7, 2026-10-07). A group's frame is
  transparent at rest, in the sidebar and the lens alike, and shows only as the accent glow while
  the group's own window scrolls, fading 700 ms after the last scroll. The border keeps its 1px, so
  nothing moves when it lights up. The teal glow on the group under the pointer (the item below on
  the area under the pointer) is removed with its `--active-area` token: only scrolling shows a
  frame. Nesting now shows by indentation alone, since the frame's edge had replaced the guide
  line. Checked on the dev server (the example model's hierarchy lens, light and dark): no frame at rest, the
  categories window's frame while it scrolled and gone a second later. The contrast test, `format`,
  `lint` (0 errors), `build` passed; `test:visual` passed (the resting frames were under its
  tolerance) and its baselines were re-recorded, 48 of them showing a tree.
- **No count on a group's heading** (asked by the user, 2026-10-07). A type group's heading shows
  its name only, in the sidebar and the lens; the count stays in the heading's accessible name
  ("Domains, 3"), and records keep their `aria-setsize`. `src/features/objects` (178 tests),
  `lint` (0 errors), `s6` passed; the visual baselines were re-recorded.
- **The group under the pointer owns the wheel** (two defects found by the user after UA4,
  2026-10-07). Over a group's heading the wheel scrolled the window around the group, since the
  heading sits outside the group's own window, while the hover glow named the group. And with the
  stops above, a group whose top had been scrolled out of its parent window could not be scrolled
  back into view from inside it. A wheel handler on the tree (`treeWheel.planWheel`, wired in
  `RecordTree`) now gives each step to the innermost group whose window scrolls, heading included.
  The owner scrolls first (over its own rows the browser does it, smoothly); at its end the step
  moves the nearest enclosing window, or the page, only as far as the owner's frame is still
  hidden, then stops. Touch and keyboard are unaffected. Checked on the dev server with wheel
  events: a step over the categories heading scrolled the categories (120px) and nothing else; with
  72px of the categories' top hidden, scrolling up inside them reached their top and then moved the
  catalogues back by exactly 72px; scrolling inside the rows moved only the categories. Unit tests
  for the decision (`treeWheel.test`); `src/features/objects` 163 tests, `lint` (0 errors), `build`,
  `s6`, `wp14` passed; `b3` passed (30 checks) on its second run (TODO).
- **Folding turned off the same day, by the user, kept to turn back on.** `FOLDING_GROUPS` in
  `RecordTree` is `false`: every group stays open, its heading has no chevron and its name starts
  at the heading's own indent (`.tree-row-plain`), left of its records' toggles; the heading stays
  an open parent for assistive technology (`aria-expanded="true"`; Left goes to the record above,
  Right into its rows). The records' extra step in, the frames, the glows and the stops stay.
  Setting it to `true` brings back everything described in the next item. Checks: 151 tests in
  `src/features/objects`, `lint` (0 errors), `build`, `s6`, `wp14`, `b3` (30 checks) passed.
- **Type groups fold** (asked by the user, 2026-10-07, after seeing why a type group heading
  in the example model's hierarchy looked like a stray label beside folding categories; the model was
  kept as it is). Every type group's heading has a chevron and folds like a record; groups start
  open and a fold persists per browser like a record's. The heading now holds its records, which
  sit one step in from it, so a record's chevron starts inside the heading's line (headings at
  4 + 28px per record level, records 14px further). Accessibility: headings are odd levels and
  records even ones (a top-level record is level 2), a record's set no longer counts the heading,
  Left from a record returns to its heading and Left again folds it, Right on a folded heading
  opens it. A reveal through a folded group opens it once. The drag counts record levels and
  record parents only (`useTreeDrag`). The lens's second line (`secondaryField: "objectType"`) is
  unchanged.
- **Tests.** `Explorer.test`: a branch's box starts below its record's toggle (29px since the
  fold), its group carries its type's slot, a heading folds and unfolds by keyboard. The level,
  position and set-size expectations in `Explorer.test`, `TreeView.test` (the drop line at 68px),
  `s6` and `b3` follow the heading level; `wp14` clicks a heading's own node. `helpers/tree.mjs`
  brings the dragged row and the drop target to the middle of the view first (TODO). `s6` opens a
  record by Right only when it is closed: an open heading now takes a further Right into its rows.
- **Checks.** `vitest run src/features/objects`: 151 tests passed. `format`, `lint` (0 errors),
  `build` passed. Runners: `s6`, `wp14` and `b3` (30 checks, B5b included) passed;
  `test:browser` failed at the record return in TODO; `c4` failed at its own API call (TODO).
  Screenshots of the lens at 1440 and 390px: framed, scrolling, hovered, headings open and folded.

#### UA3 record (2026-10-06)

Implemented; waiting for the user's approval of the screenshots.

- **The table column (decided by the user, 2026-10-06).** The canvas's table had a
  column showing each row's parent record. No collection table in either example model declares a column that shows a
  record, and table views cannot: model validation allows only built-in fields and the type's own
  attributes there (`application_rules.py`), while record panels and matrix rows take
  `ancestor:<type>`. Adding such columns would change the models and the engine's rule only to
  make room for colour, so the user chose no model or backend change. The chip is a rendering of
  any column that shows a record, wherever a view already declares one.
- **Header.** A collection's page header carries its type's `ui/HueTile` at 40px (radius 8, 20px
  icon), also at 390px; the other page icons still hide on a phone.
- **The Live strip.** Live is the soft green strip (`--context-live-strip`, its line below) with
  the Live pill outlined in `--context-live-line`; the Change sets and Publications switches carry
  a 7px dot of their context's marker. The change-set and publication lists, which are about a
  context rather than in one, have a neutral band. The amber and violet strips stay UA5's.
- **The table.** `ui/FieldValue` renders a record's field as a cell shows it: an `ancestor:<type>`
  column as `ui/RecordChip` (the parent's name on its type's fill, in its ink, after a 6px marker;
  ellipsis when long), anything else through `formatValue`. `ObjectTable` and the record panels'
  relation tables use it, so a value's System and Language columns show chips (seen on a
  record's System mappings and Translations). A row carries its record's hue; the
  selected row is filled with it, its marker as a 3px line at the left. Cells have 10px of
  vertical padding, as in the canvas.
- **Values.** `formatValue` renders booleans as plain Yes and No everywhere, as ADR-039 says;
  pills stay for states and versions (TODO's U6 item updated).
- **Loading and empty.** The first page loads as six rows in the table's shape (`.skeleton-line`
  per cell) with one status ("Loading records…"). The empty row is `ui/EmptyState`, which gained a
  decorative icon: the type's tile, the message, and **Add {type}** when nothing exists and the
  user may write. A narrowed list's empty row has no action, since the toolbar's **Clear filters**
  is right above it.
- **Toolbar.** Unchanged; it already matched the canvas (search, Filter, Display, Sort on the
  card's ruled top). The canvas's quick filter by parent is a new feature, not in UA.
- **Not done here.** A table row is selected only while its record is open beside it in the
  inspector, which today only the tree lens does; the selected row's screenshot set the state in
  the browser, and the unit test covers it.
- **Generic.** Hues come from `model/hues` by position; no renderer reads a key.
- **Tests.** `ObjectTable.test`: on two model configurations (the type order reversed), a parent
  column's chip carries the parent type's slot and the selected row its own, booleans are not
  pills; no parent of the column's type shows a dash; loading rows with one status; the empty
  state's icon and action. `DataContextBand.test`: the change-set list's band is neutral.
- **Checks.** `vitest related` on the changed files: 19 files, 231 tests passed. `format`, `lint`
  (0 errors, the 7 recorded warnings), `build` and the contrast test passed. Runners:
  `test:browser:wp13c` (12 checks) and `test:browser:wp14` passed; `test:browser` passed 1 of 3
  runs, failing twice at the record return in TODO (`ui03a-navigation.mjs:144`, change-set call
  site), which UA3 does not touch. Screenshots at 1440 and 390px, light (and the record panel's
  chips in dark), sent to the user. **Not run:** `test:a11y`, `test:visual` (UA7).

#### UA4 record (2026-10-07)

Implemented; waiting for the user's approval of the screenshots.

- **The header** (inspector and full page). The breadcrumb and `PageHeader` sit in a band tinted
  in the record type's hue (`--hue-N-band`, half the fill over the raised surface, so the type's
  40px `ui/HueTile` stands out on it), with a 1px line of its marker at 24%. The eyebrow names the
  type in its ink. The ancestors in the breadcrumb are `ui/RecordChip`s in their own types' hues
  and open their records (`RecordChip` gained `onOpen`, rendering a button); the application stays
  a quiet text link and the type plain text, since chips mean records. **Back to list** stays above
  the band. The history's markers take the record type's marker.
- **The inspector** (beside a tree lens; also the record view at 390px). Its sections are ruled,
  not cards, with small capital headings as in the canvas. A one-column field list at least 340px
  wide puts each label beside its value with Edit and Remove at the row's end (a container query,
  so a widened side column on the full page does the same); narrower, the label stays above.
- **Connected** (`panels/ConnectedList`). The inspector shows the record's declared relations
  panels (main and side) as one list: a row per panel, its title as the label, its related records
  as chips in their types' hues that open them, first page of 12 by name, **Show N more** appending
  the next. Where the panel declares an `ancestor:<type>` column, the chip names that ancestor
  before the record (a system value reads "CRM · …", a translation "Arabic · …"), since the
  model's author chose it as what tells them apart. The tables, with search, sort, add, edit and
  delete, stay on the full page; **Manage relationships on the full page** opens it. The canvas
  showed a read-only list and did not say where the writes go; this is the choice to judge on the
  dev server. Children, table and hierarchy panels stay as they were.
- **Generic.** Hues come from `model/hues`; labels from the panels' titles; nothing reads a key.
  Seen on the example model (dev server); the runners use the starter model.
- **Contrast.** `tokens.test.ts` resolves `color-mix` and checks the eight bands in both themes:
  primary, secondary and tertiary text, a link and the type's ink at 4.5:1; its marker, the focus
  colour and a control's border at 3:1.
- **Tests.** `ObjectDetail.test`, on two model configurations (the type order reversed): the header
  carries the record type's slot and an ancestor chip its own and opens it; the inspector lists a
  relation as a Connected chip in the related type's slot that opens it, offers the full page, and
  has no relation table, while the full page has the table and no Connected list; **Show 1 more**
  appends the next page.
- **Checks.** `vitest related`: 10 files, 152 tests passed. `format`, `lint` (0 errors, the 7
  recorded warnings), `build` and the contrast test passed. Runners passed: `test:browser:b3` (30
  checks, axe on the inspector), `s6`, `wp14`, `wp12`. `test:browser` failed once at the record
  return in TODO (`wp9-navigation.mjs:383`); `test:browser:b4` failed at its cycle refusal check,
  a runner pattern that misses the upper-case error code (TODO); its breadcrumb checks passed.
  Screenshots of the inspector (top and Connected) and the full page at 1440 and 390px, light and
  dark. **Not run:** `test:a11y`, `test:visual` (UA7).

#### UA4 revision: one table, resizable columns (2026-10-07)

Asked by the user after UA4: resizable columns that leave the tables' look as it is (an earlier
version had made them look worse), and whether every table of records is one piece of code. It
was not: `RelationsPanel` drew its own copy of the table. The user chose a shared table that keeps
the record list and the relationship list apart, and columns that may be narrower than their
content.

- **`ui/DataTable`** owns the table: sortable, resizable headers; cells as the caller gives them;
  the scroll window, aria row counts and positions; six loading rows; `EmptyState`; the row's type
  colour; the phone layout's three columns with **Show all columns**. The caller says what a row is:
  its key, an optional filter that keeps positions, its hue, its own attributes and its actions
  column (header, cell, the width it needs).
- **`ui/ObjectTable`** is the record list over it (key and selection by record, row click, the
  record menu by button, right click or Shift+F10); its callers are unchanged except
  `onColumnWidths`. **`RelationsPanel`** keeps its fetch, filters, sort, toolbar and dialogs and
  draws its rows with `DataTable`, keyed by relationship, so one record reached by two relationships
  is two rows; the Relationship column is a column of its own and its widths are kept
  (`useTableDisplay`'s `otherColumns`). It gains the Display menu (widths and columns per record and
  panel, as a record's child tables have them), loading rows, the empty state and row colours.
- **Resizing.** The handle is an 8px strip inside its header's right edge (it hung 5px past it, under
  the next header, so a pointer never reached it; only the keyboard worked). A drag or key starts
  from the column's drawn width (`ResizeHandle`'s `start`), not 180px. The first resize stores every
  column's drawn width (rounded up, so no cell starts to clip), so only the dragged column changes;
  from then on the table uses fixed layout, a column may go down to 48px with an ellipsis, and the
  actions column (or the table's own width, which scrolls) takes the difference. Below 760px the
  handles are off and the table lays out by content. Measured on the dev server: Master ID 134→64px
  and Value code +90px with the other columns unchanged; a translation table's Translated name
  234→124px likewise. A table that was never resized looks as before.
- **Changed for phones:** relationship tables show three columns with **Show all columns** at 390px,
  as record tables do. `s5` sorted a relationship table from its Value code header at 390px; it now
  opens all columns first (`s5-continuous-lists.mjs`).
- **Tests.** `ObjectTable.test`: the first resize keeps the other column's width; a sized table is
  fixed and takes a width below the old 120px minimum. `RelationsPanel.test`: one record on two rows
  by two relationships, the Relationship and field columns resize, Display is offered; header-name
  expectations match the start of the name, since the header's name includes its handle's (TODO).
  `localPreference.test`: `setWidths`.
- **Checks.** `vitest run` over `ui`, `features/objects`, `lib`, `app`: 28 files, 264 tests passed.
  `format`, `lint` (0 errors, the 7 recorded warnings), `build` passed. Runners passed:
  `test:browser`, `wp13c`, `wp14`, `change-sets`, `sc07`, `b3` (30), `s5` (after the 390px change
  above). `test:browser:authoring` failed on two **Add Domain** buttons, from UA3's empty state
  (TODO). **Not run:** `test:a11y`, `test:visual` (UA7).

#### UA4 revision: fields edited in place (2026-10-07)

Asked by the user: edit a record's fields by clicking them instead of the Edit, Remove and Add value
buttons, with a delete icon on hover. Recommended with conditions, which the user accepted, and two
variants of the pencil to pick from on the dev server.

- **The value is the control** (`AttributesPanel`). An editable field's value is a button that reads
  as text (`.attribute-edit`): a soft fill and a pencil on hover and keyboard focus; an empty field
  shows **Not set** with a plus and adds a value. Its name says the action and the value ("Edit
  Value code: 16-BUS-002", "Add Description: Not set"). Its text can be selected; a click that ends a
  selection inside it is left for copying, as table rows do.
- **Saving stays explicit.** The editor is unchanged: Save or Enter, Escape cancels, a click elsewhere
  does nothing, null and conflict handling as before. Focus returns to the value afterwards.
- **Remove** is a trash icon (`Remove {field}`) at the row's end, shown with the row's hover or
  focus, always on touch (`hover: none`), hidden while another field is edited; required fields have
  none; the confirmation is unchanged. On phones it keeps the row's top right with a 40px target.
- **Read-only** (a publication, a read-only binding, a computed field) shows the plain value.
- **Two variants, both kept (decided by the user, 2026-10-07):** the pencil only on hover and focus,
  or faint at rest. Recommended: hover and focus, since whether a field can be edited follows the
  context (Live, a change set, a publication) more than the field, so a mark on every row says
  little and costs calm. The user kept both as a choice: Settings › Appearance › **Edit pencil**
  (**On hover and focus**, the default, or **Always, faintly**), saved in this browser
  (`lib/editHint`, `rdm:edit-hint:v1`), as the table density is. `Settings.test` writes it;
  `AttributesPanel.test` shows the panel following it. `test:browser:settings` (10 checks) passed.
- **Tests.** `AttributesPanel.test`: on two record types, a value opens its editor and focus returns
  to it after Escape; an empty field adds; only an optional field has Remove, which asks first; a
  click that selected the value's text does not open the editor. `ObjectDetail.test` follows the new
  name. Runners `wp9-authoring` and `wp9-change-sets` find a row's control by the start of its name,
  and `wp9-authoring` waits for focus on the edited value.
- **Checks.** `vitest run` over `ui`, `features/objects`, `lib`, `app`: 29 files, 274 tests passed.
  `format`, `lint` (0 errors, the 7 recorded warnings), `build` passed. `test:browser:change-sets`
  passed. `test:browser:authoring` stops at UA3's two **Add Domain** buttons (TODO) before its field
  steps; run once with that click pointed at the first button (not kept), it passed end to end,
  editing, adding and removing fields at 1440 and 390px. Screenshots of both variants at rest and on
  hover, in the inspector and on the page, the editor open, and a touch phone.
- **The record's ID** (asked by the user the same day: the consumer API returns each record's `id`,
  and the record page showed it nowhere). The header band shows it under the title (`.record-meta`)
  with `ui/CopyValue`: the label, the ID in the monospace face, selectable, and **Copy ID**, which
  announces "ID copied." or how to copy by hand. On the inspector, the full page and at 390px. The
  model's **Master ID** field is a different value (`master-id`); in the dev data it is empty for
  every record (checked: no stored value, no write in the history, none in the SQLite file it came
  from; the API returns all 6,993 stored values exactly). `ObjectDetail.test`: the ID shows and
  copies. Checks: 29 files, 276 tests; `format`, `lint`, `build`; `test:browser` failed once at the
  known record return (TODO) and passed on the next run.

#### UA4 revision: the top bar's way back (2026-10-07)

Asked by the user: a back button in the top bar for Settings, returning to the page Settings was
opened from, built into the one top bar so other areas can use it later.

- **`TopBar`'s `back`** (`TopBarBack`: label, address, action) draws a quiet link with an arrow after
  the product mark (`.topbar-back`); the bar knows nothing else about it. On phones it takes the
  first row's middle, between the mark and Settings.
- **Settings** passes **Back to {application}** to `SettingsShell`: the router's last application
  route of the session (`lastApplicationRoute`, which settings pages never replace), so moving
  between settings pages keeps the target; opened first, it is the home route. Checked on the dev
  server at 1440 and 390px: from a record, into Settings, to Appearance, Back returns to the same
  record address.
- **The 36px rule** (UA0, the user's) now reads: the tabs start 36px after the item before them,
  the mark or the way back. `u3-settings.mjs` measures it so, has the link in the keyboard order
  after the mark, and checks that Back names the application and leads to the exact page it left.
- **Tests.** `Settings.test`: the shell's Back link carries its address and acts. `vitest run`
  over `ui`, `features`, `lib`, `app`: 38 files, 368 tests. `format`, `lint` (0 errors), `build`;
  `test:browser:settings` (10 checks) passed.

#### UA4 revision: the type palette in Settings (2026-10-07)

Asked by the user: switch between palettes A and B from Settings › Appearance instead of editing the
tokens. **Type colours** offers **B: magenta and olive** (the default) and **A: plum and gold**; A
sets `data-palette="a"`, which remaps slots 3 and 4 in light and dark; the bands follow the fills.
The plum and gold primitives are back in the tokens (from `226beb2`). `tokens.test.ts` covers A in
both themes (11 tests); `Settings.test` switches and saves it. Checked on the dev server: the
Translations tile (slot 3) turns plum at once, the choice survives a reload, and dark mode takes the
dark shades. `vitest` over `features`, `app`, `ui`, `lib`, `styles`: 380 tests, one known
intermittent `RelationMatrixView.test` failure (TODO; passed alone, 14 of 14). `format`, `lint`,
`build`, `test:browser:settings` (10 checks) passed.

#### UA4 revision: the empty collection's Add kept (2026-10-07)

An empty collection shows **Add {type}** twice: in the page header and in its empty state (UA3).
Recommended keeping only the header's; the user kept both. `wp9-authoring` now clicks the header's
button (`.page-header`), and `test:browser:authoring` passes without the workaround the earlier
runs needed.

#### UA5 record (2026-10-07)

Implemented; waiting for the user's approval of the screenshots. The canvas shows only Live, so the
change set and publication follow ADR-040's "in the same place" and the rules UA1–UA4 settled (soft
strips, the indigo primary, pills for states, ruled rows on a white card, type colours on records).

- **The strips.** A change set is the soft amber strip and a publication the soft violet one
  (`--context-*-strip`, made in UA1 and unused until now), drawn by one rule with Live's; each
  context's pill is outlined in its line. Each has a line in Live's place: "Edits stay in this
  change set until it is published." and "Read-only. A publication's records never change." The
  strong amber and violet fills are gone, and the page's text and controls keep their own colours on
  the strip, so the band-tinted buttons and the muddy disabled Publish are gone too.
- **The change set bar** sits under the context line, ruled off by the strip's line: the change
  set's name (the pill now says only "Change set", so the name is not said twice), version, source
  and model, then **Review changes**, **Validate change set**, **Publish change set** (indigo) and
  **More change set actions**, now `ui/ActionMenu` (it gained disabled items) in place of a
  hand-made `<details>` menu. **The publication bar** names the publication and its model release,
  with **Back to publications**.
- **The lists** (`ui/RuledList`, new): change sets and publications are ruled rows on one card, a
  dot of the context's colour before the name, the facts in one secondary line, actions at the end.
  The "Change set" pill on every card is gone (the page says it). A publication's **Current** is a
  `StatusPill`; **Open publication** stays a button and **Start a change set from this publication**
  and **Withdraw publication** moved into the row's menu, as Discard is in the change set's. Rows
  take table rows' grey under the pointer (`--surface-subtle`, asked by the user during the slice);
  so do the review's change rows. The empty lists use `EmptyState`; an empty change set list repeats
  **Start from current live data**, following the user's decision for empty collections (above).
- **Review changes.** The kind of change is a `StatusPill` (Added success, Changed neutral, Removed
  error), replacing `.change-kind`'s own colours; a record row starts with its type's 18px tile; a
  relationship's ends are `RecordChip`s in their types' colours; **Parent link** is a neutral pill.
- **Generic.** Hues come from `model/hues`; nothing reads a key.
- **Contrast.** `tokens.test.ts` adds a control's border, the focus colour and the primary action on
  each strip at 3:1, in both themes and both palettes.
- **Tests.** `ChangeSetReview.test`, on two model orders: a record's tile and a relationship's chips
  carry their types' slots. `ChangeSets.test`: the empty list says so and repeats the start action
  only when writable; the menu opens Change model version and Discard. `Publications.test`: start
  and withdraw through the row's menu. `DataContextBand.test` and `App.test` follow the pill and the
  notes. Runners follow the menu (`wp9-change-sets`, `wp9-publications`, `wp11`, `sc15`), the
  header's start button (`wp9-change-sets`, `sc15`, `wp13c`), the name in the bar
  (`wp9-navigation`), the publication bar's wording (`wp9-publications`), and focus returning to the
  menu's button after Escape on the discard confirmation (`wp9-change-sets`).
- **Checks.** `vitest run` over `features/workspaces`, `app/App`, `app/DataContextBand`, `ui`,
  `styles`: 14 files, 152 tests passed. `format`, `lint` (0 errors, the 7 recorded warnings),
  `build` passed. Runners passed: `test:browser:change-sets`, `publications`, `p2`, `test:browser`,
  `wp11`, `sc15`, `wp13c`. `test:browser:c5` passed its change set steps and stopped later at its own
  history call with `workspaceKey` (TODO, known). Screenshots of the change set list (and a row under
  the pointer), a collection and the review (records and relationships) in a change set, publications
  and a record in a publication at 1440 and 390px, light, and the change set strip in dark.
  **Not run:** `test:a11y`, `test:visual` (UA7).

#### UA6 record (2026-10-07)

Implemented; waiting for the user's approval of the screenshots. No new rule: each surface takes
the rules UA1–UA5 settled (a type's tile in the page header, a record inside other data as a chip in
its type's colour, pills only for states, panels on a card).

- **Relation matrix, mapping grid, tree lens.** The page header carries a 40px `ui/HueTile` of the
  row type (the matrix's rows, the grid's sources, the lens's first root type), as a collection's
  header does, so switching lenses of one collection keeps the tile. A matrix cell's first record is
  a `ui/RecordChip` in the cell type's colour, "+N" beside it. A mapping's targets are chips in the
  target type's colour, their display fields beside them, in the grid and in the dialog's
  **Currently**; the state is a `StatusPill` (Mapped success, Unmapped neutral, Ambiguous warning),
  replacing `.mapping-state-badge`. The matrix's "Saves to change set" is the change set's pill.
- **Dialogs.** The five lists of records to choose from (move, mapping target, matrix link, matrix
  place, restructuring's siblings) repeated one label's markup; they are now `ui/Candidate`, which
  shows the record's 18px type tile (`model/hues.objectTypeTile`), keeps the tile's room for a
  choice that is not a record (**Top level**), and lets a long note wrap instead of the name (found
  on b3's screenshot: the refusal pill squeezed "Top level" to a few letters a line). The matrix cell
  dialog's records and the restructuring plan's records show their tile before the name. Dialog
  shapes are unchanged.
- **Settings pages.** Already in the look (U3); the Workspaces and Model details move onto
  `ui/Card`, and their states onto `StatusPill`.
- **One component, no copies.** Every `.surface` panel (13 and `RuledList`'s) is `ui/Card`, which
  gained `as` (a `section` its caller names) and `flush` (no padding). The 18 hand-made `.pill`s and
  the `.compatibility` pills are `StatusPill` (states with their marker; notes such as a refusal
  without); `ModelDiff` exports `CompatibilityPill` for both its users. Ten hand-made notices in
  the model screens are `ui/Notice`.
- **Removed.** The 51 older token aliases in `base.css`: their 423 uses read the roles directly
  (a mechanical mapping, one alias to one role), and every `var(--…)` resolves (checked by script).
  `base.css`'s remaining shell tokens (`--sidebar`, `--control-height`, `--radius-control`,
  `--focus-ring`) moved to `tokens.css`'s component layer; `--header-height` and `--radius-surface`
  were copies of `--topbar-height` and `--card-radius`. Rules for six classes no code renders
  (`collection-meta`, `model-workbench`, `model-page-header`, `settings-search`, `sidebar-slot`,
  `without-sidebar`), and the `.surface`, `.pill`, `.active-pill`, `.danger-pill`, `.compatibility`
  and mapping badge rules. The other unmatched selectors are built at run time
  (`${size}-dialog`, `${variant}-header`, `${tone}-notice`).
- **Generic.** Hues and icons come from `model/hues`; no renderer reads a key.
- **Tests.** `MappingGridView.test` on two model orders: the header tile, a target's chip and the
  dialog's choices carry their types' slots, the states their tones. `RelationMatrixView.test` on two
  views of different row types: the header tile and a cell's chip; the cell dialog's records carry
  the cell type's tile. All five failed on the previous code. `UIFoundation.test`: an untitled
  `Card` as a named, flush section. Runners follow the pills: `wp12` (the release's Active and
  Inactive pills) and `sc07` (a target is a chip).
- **Checks.** `vitest run` over `ui`, `features`, `app`, `styles`, `model`: 39 files, 407 tests
  passed. `format`, `lint` (0 errors, the 7 recorded warnings), `build` passed. Runners passed:
  `a4` (10), `sc07` (9), `b3` (30, twice; the second after the candidate fix), `wp12` (7),
  `settings`, `w4`, `wp14`, `change-sets`. `c4` failed at its own history call (TODO, known) and
  once at the volume drag's preview, which passed on the next run (TODO). Screenshots at 1440 and
  390px, light, of the matrix (live, change set, link dialog), the mapping grid and its dialog, the
  lens, the move and restructuring dialogs and the settings pages. **Not run:** `test:a11y`,
  `test:visual` (UA7).

#### UA6 revision: the settings navigation's groups (2026-10-07)

Asked by the user: the group headings in the settings navigation looked like its pages (both grey,
both at the rail's edge). Two variants were shown on the dev server; the user chose A. Headings are
dark and bold (12px, 700, capitals), and the pages hang one step in from a 1px guide line
(`--border-strong`), as nesting does in the record browser; framed groups (B) were not taken. Only
the settings navigation changes; the application rail's **Collections** heading is as it was.
Found on the way: in the 390px drawer the headings took the dialog's `h2` size and sat against the
screen edge, since the drawer dropped the rail's padding assuming the dialog padded it, which it
does not. The drawer now keeps the rail's inset. Checks: `Settings.test` and `app` (60 tests),
`format`, `build`, `test:browser:settings` (10 checks, axe 0 violations). Screenshots at 1440px
(light and dark) and 390px (drawer).

#### UA7 record (2026-10-07)

Implemented; waiting for the user's approval of the screenshots and of the drawn checkboxes and
radios. Every surface was checked in dark against its light twin: the tokens already had a dark
value for every role (the bands and the focus ring are mixed from roles that do), no stylesheet
holds a literal colour, and the 32 screens below match their light versions in structure, tiles,
chips, bands and pills.

- **Found in dark: checkboxes and radios.** They were the browser's own controls, which follow
  `color-scheme` and in dark are grey discs and squares; in the move dialogs the disabled **Top
  level** looked like the enabled records beside it. They are now drawn from the tokens in
  `base.css` in both themes: the control border (held to 3:1 by the contrast test), the primary
  action and `--text-on-action` when checked, a dash when indeterminate, 40% when disabled, the
  focus colour's outline. Light looks as before (compared side by side); dark now shows rings and a
  faded disabled choice. Shown to the user for approval, since the canvas did not decide it.
- **A column header's name is its label alone** (TODO from the UA4 revision). The resize handles
  left the header cells: `ui/DataTable` draws them in one zero-height layer before the table,
  sticky at the top of the scroll window, each at its column's right edge measured against the
  layer (a `ResizeObserver` on the headers), so they stay with the sticky header row and scroll
  sideways with the table. `ResizeHandle` takes a `style`. Checked in the browser: every handle on
  its column's edge and at the header's height before and after a drag, after a horizontal scroll
  and after the rows scroll; the headers named "Name", "Description"… The header no longer
  contains the handle (`ObjectTable.test`, failed on the previous code).
- **The gates cover every screen in both themes.** `test:visual`: the seven light-only screens
  gained dark twins (system collection and record, change set record, publications, release,
  workspace, Appearance); the mapping grid and its change dialog and a collection and a record at
  390px were added, light and dark: 64 baselines (32 screens), all re-recorded and inspected. The
  Workspaces page's capture now masks the selected workspace's times, as the workspace's own page
  does (it would have failed on the clock on the next run). `test:a11y` gained the same pages: 73
  checks. `seedMappingData` takes `alignment: false` for the gates, whose model has no alignment
  relation.
- **Checks.** `test:a11y`: 73 checks, 0 violations, nothing allowlisted, its 3 planted faults
  rejected (111 s), run again after the controls changed: the same. `test:visual
  --update-baselines`, then a compare against the fresh baselines: 64 passed (60 s each).
  `test:browser:sc07` (9 checks: the keyboard-only mapping save over the drawn radios).
  `vitest run src/ui src/styles` (56 tests), `format`, `lint` (0 errors, the 7 recorded warnings),
  `build`. Not run: the other browser runners (no surface of theirs changed beyond the controls'
  drawing, which `test:a11y` and `test:visual` cover in their dialogs).
- **Not changed.** The gates' dark captures follow the light ones in one run, so the tree keeps
  the branch an earlier step opened (Domain 04 in several dark screens); this is the gate's order,
  not the theme.

### UA8: actions in place on the record

**Asked by the user 2026-10-09**, after K3a's screenshots: the text buttons in a relationship row
(Edit, Change, Delete) should look like the rest of the record; the header's title and subtitle
should be edited in place as the details panel's fields are; the header's **Edit record** button
goes and the menu's **Edit all fields** becomes **Edit record**. Every change is made once, in the
shared component, and every view that shows it follows. **Planned 2026-10-09; U-D15–U-D17 decided by
the user the same day; U-D18–U-D20 and the test cases accepted with the user's instruction to
deliver UA8, the same day.** Checked against the code at
`d4a8ff2`.

**What exists.**

- **Relationship rows** (`panels/RelationsPanel`) end in text buttons: **Edit** (the
  relationship's own values, where the binding declares attributes), **Change** (K3a, where the
  record holds one of the kind) and **Delete**; a containment row says "Managed through Parent" and
  a required one "Required relationship" in muted text. No other table in the record uses text
  buttons in its rows.
- **Fields edited in place** ([UA4 revision](#ua4-revision-fields-edited-in-place-2026-10-07)): in
  `panels/AttributesPanel` an editable value is the control, with a pencil (or a plus when empty)
  shown as Settings › Appearance › **Edit pencil** says, `panels/InlineAttributeEditor` as the
  editor, and a trash icon to remove an optional value. The logic is written inside the panel, so
  nothing else can reuse it, and the editor saves attributes only.
- **The record header** is one component, `ObjectDetail`, on the full page and in the inspector
  beside a tree lens. Its title and subtitle are the detail view's `header.titleField` and
  `subtitleField`: the title usually the built-in `name` (saved by `PATCH /objects/{type}/{id}` with
  the record's version), the subtitle an attribute or a computed field. Its actions are the version,
  **Edit record** (opens the all-fields form), **Expand to full page** in the inspector, and
  `RecordActionMenu` (⋯, also opened by a right click on the header) with **Edit all fields**,
  **Copy link** and **Delete record**. The same `RecordActionMenu` is every collection row's ⋯.
- Icons come from `ui/Icon` (lucide); there is no icon-button component. `ui/ActionMenu` is the ⋯ menu.

**Behaviour.**

1. **Relationship rows** (U-D15): the actions column holds icon buttons, in this order:
   **Change** (two arrows, "Change to another record"), **Edit values** (pencil) and **Delete**
   (trash, danger on hover), each only where it applies today. Each has a tooltip and an accessible
   name naming the record ("Change Kept by: K3a System B"), keyboard focus and a 32px target (40px
   on touch). A containment or required row shows a lock with the same reason as its tooltip and
   accessible text (U-D19).
2. **The header's title and subtitle** (U-D16) are edited in place exactly as a details-panel
   field: the value is the control, the pencil or plus as the Edit pencil setting says, Save or
   Enter, Escape cancels, focus returns, a conflict reloads and says so. The title's editor keeps
   the title's size. A field that cannot be edited (a publication, a read-only binding, a computed
   or built-in field other than `name`) reads as plain text. An empty editable subtitle shows
   **Add {field}** (U-D20); the header never removes a value (removal stays in the details panel).
3. **The header's actions** (U-D17): **Edit record** is no longer a button; the ⋯ menu's first item
   is **Edit record** (was Edit all fields), on the header and on every collection row, since both
   are `RecordActionMenu`. The version, Expand to full page and the right click stay.
4. Everything else about editing (the all-fields form, the details panel's remove, saving to Live or
   a change set, the publication's read-only view) is unchanged.

**Design** (U-D18).

- **`ui/IconButton`** (new): an icon, a label (the accessible name and the tooltip), a tone
  (`default`, `danger`), the 32/40px target; no copy of button markup anywhere else. The details
  panel's trash moves onto it.
- **`features/objects/EditableField`** (new, extracted from `AttributesPanel`): one field of one
  record, shown and edited in place. It takes the field key and how it is laid out (a details row or
  the header's title or subtitle), decides from the model whether it can be edited, and saves `name`
  through `updateObject` and an attribute through `InlineAttributeEditor`'s routes, with the
  version claim and conflict handling they have today. `AttributesPanel` renders its rows with it;
  `ObjectDetail` renders the title and subtitle with it. The pencil setting (`lib/editHint`) is read
  in this one place.
- `RecordActionMenu`: the item renamed. `ObjectDetail`: the Edit record button removed.
  `RelationsPanel`: the actions column over `ui/IconButton`. `ui/Icon` gains the two-arrows and
  lock icons.
- **Not changed:** the API, the model, the all-fields form, `ui/ActionMenu`, the collection table.

**Decisions:**

| # | Question | Decision or recommendation |
| --- | --- | --- |
| U-D15 | How a relationship row offers its actions | **Decided 2026-10-09 by the user: icon buttons** (the user's choice over a ⋯ menu per row, recommended for consistency with collection rows, and over a mix of the two) |
| U-D16 | Which header fields are edited in place | **Decided 2026-10-09 by the user, as recommended: the title and the subtitle**, whatever fields the detail view declares for them, each only where it can be edited |
| U-D17 | The header's edit actions | **Decided 2026-10-09 by the user:** the Edit record button removed; Edit all fields renamed Edit record and kept in the ⋯ menu only |
| U-D18 | Where the in-place editing lives | **Accepted 2026-10-09 (the user's instruction to deliver): one component, `features/objects/EditableField`, extracted from `AttributesPanel`, which the details panel and the header both render; and `ui/IconButton` for every icon action.** The user asked for one component that every view follows (U-D14). The alternative, a header editor written beside the panel's, would be a copy |
| U-D19 | A containment or required row's label | **Accepted 2026-10-09 (the user's instruction to deliver): a lock icon whose tooltip and accessible name give today's reason.** The column then holds only icons. The alternative keeps the muted text, which is longer than the icons and wraps at 390px |
| U-D20 | An empty editable subtitle, and removing a value in the header | **Accepted 2026-10-09 (the user's instruction to deliver): an empty editable subtitle shows Add {field} with a plus; the header has no remove.** Without it a record with no code could not get one from the header, which is the point of the change; clearing an identity field from the header would be easy to do by accident, and the details panel keeps remove with its confirmation |

**Journeys.** J02 (correct a record) gains a variant: the name and the header's subtitle corrected
in place from the header. J13's relationship rows change look only. USER_JOURNEYS records both. UI_ACCEPTANCE
row UA8-1 (the record header) and K3a-1 (the row's icons).

**Test cases** (accepted with U-D18–U-D20):

1. `EditableField.test` (new): on two record types, the name edited in place saves through the
   record update with its version and the title shows the new name; an attribute subtitle saves
   through the attribute route; Escape cancels and returns focus; a conflict reloads and says so; a
   computed subtitle and a publication show plain text; an empty editable subtitle offers Add.
2. `ObjectDetail.test`: no Edit record button; the ⋯ menu's first item is Edit record and opens the
   form; the same in the inspector. `RecordActionMenu.test` follows the rename.
3. `AttributesPanel.test` still passes on the extracted component (its cases unchanged).
4. `RelationsPanel.test`: a row's icon buttons by their accessible names (Change, Edit values,
   Delete) open what the text buttons opened; a containment row's lock names its reason.
5. Browser: `test:browser:k3` scenario 9 by the new names; the runners that press Edit record or
   Edit all fields (`wp9-authoring`, `wp9-change-sets`, `wp9-publications`, `sc15`, `ui03a`) by the
   menu item; screenshots of the header (rest, hover, editing the title, an empty subtitle) and a
   relationship row, on the full page and in the inspector, at 1440px and 390px, light and dark; axe
   on both.

**Checks.** Vitest `related` over the changed files, `format`, `lint`, `build`; the five runners
above and `test:browser:k3`. Not run: the full suites, `test:a11y`, `test:visual` (R).

#### UA8 record (2026-10-09)

Implemented; screenshots approved by the user 2026-10-10. Delivered as planned, with these differences:

- **The screenshots and axe have a runner of their own**, `ua8-record-in-place` (`test:browser:ua8`),
  rather than a scenario in another: it adds K3a's Kept by binding to the starter for the run, with
  a relationship value, so one row shows all three icons, and covers domains and systems, the full
  page and the inspector, 390px and dark.
- **The pencil setting** is read by `EditableField` for every field it draws; the details panel's
  `<dl>` keeps its own `data-edit-hint`, which `AttributesPanel.test` pins, so the panel reads it in
  two places. Both say the same value.
- **`ui/IconButton`** is used by the relationship rows and the details panel's remove. The other
  icon-only buttons (the ⋯ trigger in `ui/ActionMenu`, `ScrollWindow`, `SettingsMenu`, the webhook
  dialog, the change-set review) keep the existing `.icon-button` class with their own markup; moving
  them onto the component was not in the plan.
- **`InlineAttributeEditor`** takes a `save` for a built-in field, so the name uses the same editor
  and conflict handling as every attribute; nothing was copied.

**Built.** `features/objects/EditableField` (with `fieldEditing`, which says whether and how a field
is edited); `AttributesPanel` renders its rows with it and keeps removal; `ObjectDetail` renders the
header's title and subtitle with it (the subtitle shown when it has a value or can be edited) and
drops the Edit record button; `ui/PageHeader` gains `titleLabel` and `titleEditor`, and a non-text
description renders in a `div`; `RecordActionMenu`'s item is **Edit record**; `RelationsPanel`'s
actions column is Change (two arrows), Edit values (pencil) and Delete (trash) over `ui/IconButton`
(quiet, red on Delete's hover), with a lock and its reason where a row cannot be changed; `ui/Icon`
gains `swap` and `lock`.

**Tests.** `EditableField.test` (new, 12 on two record types), `ObjectDetail.test` (the header's
actions on the page and in the inspector), `RecordActionMenu.test` and `App.test` (the item's name),
`RelationsPanel.test` (the icon buttons by name and tooltip; the K3a cases by the new names);
`AttributesPanel.test` unchanged and passing. The runners `wp9-authoring`, `wp9-change-sets`,
`wp9-publications`, `sc15` and `ui03a-navigation` press Edit record in the menu, and
`wp9-authoring` a relationship row's Edit values and Delete by their new names; `k3-bulk-relations`
the same for Kept by.

**Checks.** `vitest related` over the changed files: 40 files, 425 passed. `format`; `lint`, 0
errors (the 7 recorded warnings); `build`. Runners: `test:browser:ua8` (7 checks, axe 0 violations
on the record page light and dark and on the inspector), `test:browser:k3` (16 checks), and
`authoring`, `change-sets`, `publications`, `sc15`, `ui03a-navigation`, each passed. Screenshots
inspected: the header at rest, on hover, editing the title, with Add Description, at 1440px and
390px and in the inspector; a system's header; the Kept by row at rest and hovered, light and dark.
A first look showed the row icons in the action colour: `.row-actions button`, the old text-button
rule, outranked the quiet icon's; the icon rules now name both classes, and the details panel's
remove keeps its red. Not run: the full suites, `test:a11y`, `test:visual` (R).

### UA9: the record tree scrolled as one, several records selected and dragged

**Asked by the user 2026-10-09.** First as an experiment: the sidebar's record browser and the
hierarchy lens scroll as one list, without a window per type group, and start folded; the user
kept it the same day. Then: drag and drop in the sidebar too, and several records selected with the
usual controls (Cmd or Ctrl to add or remove one, Shift for a range) and dragged together. Selecting
in the sidebar does not change the record on the main page; the selection is only for the tree's
drag. **Planned 2026-10-09; U-D21–U-D25 decided by the user the same day, U-D26–U-D28 and the test
cases approved by the user the same day.** Checked against the code at `8b6d482` with the experiment in the working tree.

**What exists.**

- **One tree, two places.** `RecordTree` is the sidebar's browser (`Explorer`) and, configured, the
  hierarchy lens (`TreeView`). A record row opens its record; the tree follows the WAI-ARIA tree
  pattern with one tab stop and one active record, the one the page shows.
- **The flat-scroll experiment** (2026-10-09, in the working tree): each type group's rows are drawn
  in the sidebar's or the page's own scroll (`FlatRows`, loading the next or previous page as an end
  comes near) instead of a `ScrollWindow`; type headings fold again (`FOLDING_GROUPS`, turned off
  on 2026-10-07) and start folded, except in search results; the open path to the active record
  still opens; the wheel routing between windows (`useTreeWheel`) is off; its open branches are
  saved under a key of their own (`v2-flat`). The replaced code is kept as comments, at the user's
  request. 33 Vitest cases (`Explorer.test`, `TreeView.test`, `App.test`) still expect open groups.
- **Drag in the lens** (0.8 B5, D34–D36, C4): `useTreeDrag` with a configuration from `TreeView`
  (whether a row drags, why a target refuses, `model/treeDrop`'s `moveRefusal` over the engine's
  placements, D45; in a change set what a record becomes); a drop opens `TreeMoveDialog` with the
  target, which sends the record's `PATCH` with `parentObjectId`, or in a change set the
  restructuring preview where the type changes. Near a window's edge the window scrolls. Move to…
  in the node menu (Shift+F10) is the keyboard path. One record at a time. The sidebar passes no
  drag (0.8 B5's scope: "the sidebar tree is for navigation only").
- **Batches** take `update` items with `parent` and `expectedVersion` (B1), live or in a change set,
  `atomic` or `independent`: several records move in one request with no new route.

**Behaviour.**

1. **Scrolling and folding** (U-D21): the experiment as it stands, kept. Its tests are rewritten
   for groups that start folded; the commented `ScrollWindow` code stays, as the user asked.
2. **Selecting several records** (U-D23, U-D26), in the sidebar and in the lens alike:
   - a click on a record opens it, as today, and makes it the selection's only record;
   - **Cmd** (macOS) or **Ctrl** with a click adds or removes that record; **Shift** with a click
     selects the loaded rows from the last record clicked to this one, within one group; neither
     opens a record nor changes the main page;
   - by keyboard: **Shift+↑/↓** extends the selection, **Ctrl/Cmd+Space** adds or removes the
     focused record, **Escape** clears it;
   - selected rows are filled in their type's soft colour, as the active record is, with a check
     mark; the tree says how many are selected (a polite announcement, and `aria-selected` on each
     row with `aria-multiselectable` on the tree);
   - the selection lasts while the tree scrolls, pages and opens branches; it is cleared by Escape,
     a plain click, a new search or another context; a record hidden by folding its branch leaves
     it.
3. **Dragging** (U-D22, U-D24, U-D25, U-D27): in the sidebar as in the lens, with mouse or pen,
   live and in a change set, never in a publication or from touch (D35; touch added in 0.11 U1). Dragging a selected
   record drags the whole selection, shown beside the pointer as "3 records"; dragging an
   unselected record drags that one alone, as today. A target accepts only if it takes **every**
   dragged record (D34's rule for each); otherwise it glows red and names the first record it
   cannot take and why, and nothing moves. With several records, a target that would change a
   record's type (C4) refuses with "Move records that change type one at a time". One record keeps
   today's flow exactly (`TreeMoveDialog`, the restructuring preview).
4. **Moving several** (U-D27): the drop opens a confirmation naming the target and the records
   (all, or the first ten and how many more), and Move sends one `atomic` batch of `update` items,
   each with `parent` and the version its row was read at, live or in the change set. A record
   someone changed meanwhile refuses the whole move by name (`VERSION_CONFLICT`), and the tree
   reads again; nothing is half moved. After a move the moved records stay selected in their new
   place.
5. **The keyboard path** (U-D28, WCAG 2.5.7): Move to… moves the whole selection where one is
   made: in the lens from the node menu as today, and in the sidebar from the same node menu,
   which the sidebar gains (right click, Shift+F10) with Move to… only.
6. While dragging, nearing the top or bottom edge of the sidebar, or of the page for the lens,
   scrolls it, faster towards the edge (today's rule, now on the enclosing scroll).

**Design.**

- `RecordTree`: a selection beside the active record (`Set` of IDs, the anchor for Shift), the
  click and key handling above, `aria-multiselectable`; it does not route. `useTreeDrag` drags a
  list of records: `refusal` and `note` are asked per record and the first refusal names the
  target's; the drag image counts. Its edge scrolling finds the nearest scrolling ancestor instead
  of a group's window.
- **One drag rule for both trees:** the configuration `TreeView` builds today (`canDrag`,
  `refusal`, `note`, the context's read-only state, placements) moves into a hook both `TreeView`
  and `Explorer` use; the lens adds its view's `move` action, the sidebar allows a move wherever the
  context allows writes.
- `TreeMoveDialog` stays for one record; `TreeMoveManyDialog` (new) confirms several and sends the
  batch through the data API (live or the change set's context), with the batch's per-item
  refusals shown as K2's are.
- The node menu (`TreeView`'s) is extracted so the sidebar renders it with Move to… only; Move to…
  takes the selection.
- **Not changed:** the engine and API, the single-record move and restructuring, the collection
  table's selection (K1), touch (D35).

**Decisions:**

| # | Question | Decision or recommendation |
| --- | --- | --- |
| U-D21 | The record tree's scrolling | **Decided 2026-10-09 by the user: one list**, the flat-scroll experiment kept, its groups starting folded; the windowed code stays commented in the source |
| U-D22 | Drag in the sidebar | **Decided 2026-10-09 by the user: yes.** Revises 0.8 B5's scope ("the sidebar tree is for navigation only") |
| U-D23 | Several records selected in the tree | **Decided 2026-10-09 by the user: yes, in the sidebar and the lens**, for dragging; selecting does not change the main page. Revises the tree's single selection (S6, B3) |
| U-D24 | A target that takes only some of the dragged records | **Decided 2026-10-09 by the user, as recommended: the whole drop is refused**, naming the first record it cannot take |
| U-D25 | Several records whose type a target would change | **Decided 2026-10-09 by the user, as recommended: one at a time**; a multi-record drop that changes a type is refused. Restructuring several records together would be an engine capability of its own |
| U-D26 | The selection's controls | **Accepted 2026-10-09 by the user:** as behaviour 2 (Finder's and the collection table's conventions: click opens and selects one, Cmd/Ctrl toggles, Shift selects a range, Shift+arrows, Ctrl/Cmd+Space, Escape). A range stays within one group, since rows of different groups and levels are not one ordered list |
| U-D27 | How several records move | **Accepted 2026-10-09 by the user: a confirmation, then one atomic batch of `update` items with each row's version.** All or nothing matches U-D24 and needs no new route; an `independent` batch could leave half a selection moved |
| U-D28 | The keyboard path to move several | **Accepted 2026-10-09 by the user: Move to… takes the selection, and the sidebar gains the lens's node menu with Move to… only.** WCAG 2.5.7 asks for a single-pointer path wherever dragging is offered; the sidebar has none today |

**Journeys.** J14 (build and change a hierarchy) gains J14.x *Move several records at once*: by
dragging in the sidebar or the lens, or Move to…, live and in a change set; a target refusing one
refuses all; a type-changing target refuses several. USER_JOURNEYS, UI_ACCEPTANCE (the tree row
gains the selection and the sidebar's drag).

**Test cases** (approved by the user 2026-10-09):

1. Vitest, `RecordTree` on two trees (sidebar and lens): click opens and selects one; Cmd/Ctrl+click
   toggles without routing; Shift+click selects a range within a group; Shift+↓, Ctrl+Space and
   Escape; `aria-selected` and the count announced; a folded branch's records leave the selection.
2. Vitest, the drag: several selected records dropped on a target taking them all open the
   confirmation, and Move sends one atomic batch of `update` items with `parent` and each version;
   a target refusing one glows red naming it and sends nothing; a type-changing target refuses
   several; one record keeps `TreeMoveDialog`; the sidebar now drags, never in a publication or
   from touch (replacing `Explorer.test`'s "never starts a drag").
3. The experiment's 33 cases rewritten for groups that start folded, by opening the group first; no
   case dropped.
4. Browser: `test:browser:b3` (lens) and `test:browser:s6` (sidebar) gain: three records selected
   with Cmd/Ctrl and Shift and dragged onto another parent, live and in a change set; a refusing
   target; Move to… by keyboard for a selection; the sidebar scrolling while dragging; 390px keeps
   selection with no drag; axe and screenshots of the selection and the drag, light and dark.

**Checks.** Vitest `related`, `format`, `lint`, `build`; `test:browser:b3`, `s6`, `b4`, `c4` and
`test:browser` (the tree runners); `test:browser:ua8`. Not run: the full suites, `test:a11y`,
`test:visual` (R).

#### UA9 record (2026-10-09)

Implemented; screenshots approved by the user 2026-10-10. Delivered as planned, with these differences and
findings:

- **The browser evidence has a runner of its own**, `ua9-tree-selection` (`test:browser:ua9`),
  rather than scenarios added to `b3` and `s6`; those two were rewritten for the folded, flat tree.
- **The sidebar does not change types.** A move there never offers a place where a record's type
  would change (live or in a change set); the lens keeps that, with its preview. U-D25 already keeps
  several records from changing type; for one record the sidebar refuses such a place with its
  reason, and the lens does it.
- **Flat scrolling needed four fixes found by the runners** (each in `RecordTree`, the old lines
  kept commented as the user asked for this change):
  - a group that opens reports its rows, so a record waiting for focus (just created, revealed) is
    reached once its group opens (before, focus was lost after Add child under a folded group);
  - opening and folding build on the latest choices, so a reveal opening several groups at once no
    longer drops all but one, and a focus request saves the type groups on its path with its
    branches, so the path shows again when the tree returns;
  - earlier rows load only from **Show earlier records** (or by keyboard): loading upward by itself
    ran on from a revealed record until the window dropped the record's page; later rows load as
    the end comes into view, telling the window where the reader is, so a sixth page drops the far
    one;
  - the keyboard behaviour a `ScrollWindow` gave is back: a jump (crossing a page edge, End) focuses
    the row it lands on, and Ctrl/Cmd+Home and +End move within the record's own group.
- **Runner fixes beside UA9**, stale before it: `c4` read history with a `workspaceKey` the route
  refuses; `b4` matched the error code in lower case (T1b made it upper case); `s7` expected the
  levels before the UA2 revision put records at even levels. `b3`'s volume pass now scrolls down to
  the record after returning, since a flat list reads its next page as its end comes into view
  (the windowed version read a page ahead).
- **Measured at HEAD in a throwaway worktree** (the nested version, `8b6d482`): `b3` passed three
  times out of three. With UA9, b3 sometimes lost focus after a move to the top level in a change
  set; explained and fixed in the revision below (the moved record's old row). The volume pass's check after returning at 390px is decided by the
  record's own top-level group, since the record can show for a moment from the view that is
  leaving.

**Built.** `RecordTree`: the selection (by ID, kept per search, workspace and application; read
from the rows as drawn so a move claims current versions), the click and key handling,
`aria-multiselectable` and `aria-selected`, the count announced, folding pruning the selection, the
drag of the selection, the selected rows' fill, outline and check mark, `onSelectionChange`, a row
`onItemContextMenu`; `useTreeDrag`: several records, judged together (U-D24, U-D25), the edge
scrolling the nearest scroller; `useTreeMoves` (new): the move rule extracted from `TreeView`, used
by it and by `Explorer`; `TreeMoveDialog`: `others` and `refusalOf`, one atomic batch
(`api.runBatch`, new); `Explorer`: the drag, the Move to… menu and dialog, `onChanged` up to `App`.

**Tests.** `Explorer.test`: the selection by pointer and keyboard (U-D26), the sidebar's drag and
batch, no drag from touch or in a publication, the Move to… menu; `TreeView.test`: several dragged
and moved in one batch, a refusing target naming the record, a change set refusing several that
change type, Move to… for a selection; the 33 cases written for open groups rewritten by opening
the group first (`src/test/tree.ts`: `findTreeItem`, `openFoldedGroups`), none dropped.

**Checks.** `vitest related` over the changed files: 42 files, 429 passed. `format`; `lint`, 0
errors (the 7 recorded warnings); `build`. Runners, each passing: `test:browser:ua9` (8 checks, axe
0 violations light and dark), `s6` (10), `b3` (30), `b4`
(13), `c4` (12), `s7` (14), `wp14`, `test:browser`, `test:browser:ua8` (7); `b3` four clean runs in a row on the final
code. Screenshots inspected:
the selection light and dark, a drag of three accepted, a refused drop naming its record, the
drawer at 390px. Not run: the full suites, `test:a11y`, `test:visual` (R).

#### UA9 revision: no text selected by Shift+click (2026-10-09)

Reported by the user: Shift+click selected the page's text between the two records as well, as a
browser does. A press on a record with Shift, Cmd or Ctrl no longer starts a text selection
(`RecordTree`, the record's `mousedown`); a plain press and drag still selects a name to copy.
`Explorer.test` asserts the press is prevented with each modifier and not without; `ua9-tree-selection`
asserts no text is selected after Shift+click. Checks: `Explorer.test`, `TreeView.test` (45 passed),
`format`, `lint` (0 errors), `build`, `test:browser:ua9` (8 checks).

#### UA9 revision: no flicker on a click, focus at a moved record's new place (2026-10-09)

- **Reported by the user:** every click on a record in an open branch showed "Loading…" under the
  branch for half a second, moving the list down a row and back. A branch the user had not opened
  stood open only as an ancestor of the record on the page; when another record was clicked, its path
  was read first, and meanwhile no record's ancestors counted, so the branch closed and opened again,
  reading its groups anew. While the next record's path is read, the branches of the one revealed
  last now stay open (`RecordTree`, `activeAncestors`; with no active record none stays). The old
  line is kept commented. `Explorer.test` holds it: a second active record under the same branch,
  its path held back, leaves the branch open with no "Loading…" and no list read; it failed before.
  Checked on the user's dev server: clicking four records under one branch, no
  "Loading…" and no row moving.
- **Found in `b3`:** after a move, the record's reveal could finish before the lists were read
  again; it focused the record's old row, still drawn under its old parent, and focus was lost when
  that row went. A focus request now waits for the record's row under the parent its revealed path
  names (or at the top of the tree). `TreeView.test` holds it: during the move the old row is not
  focused, and the new one is; it failed before.
- **Checks.** `vitest related` (6 files, 137 passed), `format`, `lint` (0 errors), `build`;
  `test:browser:s6` (10), `ua9` (8), `b3` three runs in a row (30 each, no focus lost).

### U4: the integration pages

**Planned and approved 2026-10-07** (the user: as written, with the starter's one event, and the
selected backend groups rather than the full suite). Needs UA (UA7 awaiting approval), C6b and V2
(delivered).

**Outcome.** A new **Integration** group in the settings navigation, after Administration, with
three pages. An integrator or operator reads, without opening the model JSON, which consumer APIs
the active release declares, at which contract version and base URL, and what each exposes
(**Consumer APIs**); follows and cancels jobs and reads the batch, job and feed limits (**Jobs and
feed**); and opens each API's reference on `/docs` (**API reference**). A fresh install declares a
small consumer API, so these pages and `/docs` show something (U-D5).

**Reference.** The settings layout (U3, restyled in UA6): `SettingsLayout`, ruled `Section`s,
`DescriptionList`, settings tables as on Deployment, `StatusPill`, `EmptyState`, `Skeleton`,
`CopyValue`, `HueTile` for object types (U-D13).

**Composable domains (ADR-032):** no door is affected. U4 adds pages over existing reads and one
starter content release; it does not touch identity, attribute storage, audit, bulk APIs, `match`
or mapping coverage.

#### What exists (checked 2026-10-07)

- **No route is missing.** `GET /api/consumer` (C6b) lists each definition's `consumerApi`, name,
  description, contract version and `openapi` URL (with the root path), paged. `GET /api/v1/model`
  returns the active release's model, `consumerApis` included (exposed types, lists, events).
  `GET /api/v1/jobs` pages jobs newest first (all workspaces without `workspaceKey`), each with
  state, result, counts and times; `POST /jobs/{id}/cancel` exists while `INTEGRATION_JOBS_ENABLED`.
  `GET /capabilities` has the job limits (`integrationJobs.limits`) and `changeFeed.retentionDays`.
  `GET /system` has the engine version and the active release's id.
- **`/docs`** opens a source with `?api=<slug>`: `management`, or `consumer-{key}-v{version}`
  (`management/reference`). API.md says the address keeps the slug but not its form.
- **Deployment** already lists the job limits and feed retention under "Integration jobs"
  (`DeploymentPage.capabilityGroups`).
- **The starter** (`model/rdm-starter.json`, content 0.9.0, schema 0.8) declares no consumer API.
  Startup installs the bundled file as a release; a changed file under the same version stops
  startup (`ReleaseIdentityConflict`), so the content needs a new version. On an existing database
  the new release is installed but not activated; a fresh one starts on it. Tests that need a
  consumer API set their own (`model_support` removes `consumerApis`; the journey configurations
  and `v1-api-reference` replace them). `tests.affected` selects the full backend suite for any
  `model/*.json` change.

#### Scope

1. **Routes and navigation.** `SettingsRoute` gains `consumer-apis`, `jobs` and `api-reference`
   (`/settings/consumer-apis`, `/settings/jobs`, `/settings/api-reference`). The navigation's
   **Integration** group lists them in that order; U5 inserts Webhooks after Consumer APIs.
2. **Consumer APIs** (`features/settings/ConsumerApisPage.tsx`), over `GET /api/consumer` (every
   page) and `GET /model`, with the release from `GET /system`.
   - A lead line names the active release that declares them, with **Open release** (its page under
     Model), and says the definitions change only through a model release.
   - One `Section` per definition, in index order, titled with its name: description; a
     `DescriptionList` of the namespace (`consumerApi`), contract version, **base URL**
     (`{API_URL}/api/consumer/{consumerApi}/v{version}`, with copy), OpenAPI document (link and
     copy) and **Reference** (a link to its source on `/docs`).
   - **Exposed types**: the model's type name with its `HueTile`, and the public name.
   - **Lists**: key, type, the parent parameter (name and types) and the sort attribute.
   - **Events** (when declared): key, types, changes, and what an update watches (outputs and
     projections), or "Any output".
   - Empty: `EmptyState` "The active release declares no consumer API", with **Open model**.
3. **Jobs and feed** (`features/settings/JobsPage.tsx`).
   - **Jobs**: a ruled table over `GET /jobs` with `useCursorFeed` and Load more (newest first):
     kind, workspace, state (`StatusPill`), result, counts (applied, rejected, unprocessed),
     progress, created and finished. **Refresh** reloads. **Cancel** on a queued or running job
     without a cancel request, when `createJobs` is on; it confirms, posts the cancel, and the row
     shows "Cancel requested" (`409 JOB_FINISHED` is shown inline and the list reloads). Empty:
     `EmptyState` "No jobs yet" naming `POST /api/v1/batches`.
   - **Limits**: the job limits and the feed's retention, as Deployment shows them. The items move
     to one shared function that both pages call (U-D14), and Deployment keeps them.
4. **API reference** (`features/settings/ApiReferencePage.tsx`), over `GET /system` and
   `GET /api/consumer`: one row per `/docs` source, as the page lists them: **Management API ·
   {managementApi}** (engine version) and each **{name} · v{contractVersion}**, each with **Open
   reference** (`{API_URL}/docs?api=<slug>`) and its OpenAPI document. API.md gains the slug's form,
   so the link is a documented address, not a copy of a private rule.
5. **Starter consumer API** (U-D5): content release **0.9.1**, one definition `rdm`, "RDM API",
   contract version 1. Exposed: domains, codelists and their values (`Domain`, `Codelist`,
   `CodelistValue`); the object roles `id`, `code`, `name`, `isActive`, `validFrom`, `validTo`,
   `parent`, `path`, and the attributes `description`, `masterId`, `valueName`, `sortOrder`.
   Lists `domains`, `codelists` (parent `domain`) and `values` (parent `codelist`, sorted by
   `sort-order`). One event, `values-changed`: codelist values created, updated or deleted,
   watching `code`, `name`, `isActive`, `validFrom` and `validTo`, so U5's Webhooks page has an
   event to subscribe to on a fresh install. No projections, `match` or `parameters` beyond the
   lists' own.

**Not in U4:** Webhooks (U5). A job's detail page or item outcomes (the API pages them; no journey
needs them on a page yet). Editing a definition (the model, through a release). Any backend route
or contract change.

#### Checks

- **Journeys.** No API journey changes, so no journey test is added. J20 (Discover) names Settings
  › Integration › Consumer APIs and API reference as its UI channel; J24 (background job) names
  Jobs and feed for following and cancelling; J25 names Consumer APIs as where a declared
  definition is read. API_JOURNEYS is unchanged.
- **Backend.** The starter change selects the full suite (`tests.affected`), which AGENTS forbids
  in a package; instead the groups that load the starter as data and the consumer, model and
  startup groups the execution guide selects for `model/*.json`, within the 2-minute ceiling, and
  the starter's own compile (`test_model_diagnostics`). The full suite stays at build acceptance.
- **Frontend unit** (`vitest related`): `routes.test.ts` (the three URLs both ways),
  `Settings.test.tsx` (the Integration group; Consumer APIs over a fixture index and model with two
  definitions, one with events and one without, and the empty state; Jobs: a page, Load more,
  cancel and its refusal, cancel hidden when `createJobs` is off; API reference's links), then
  `format`, `lint`, `build`.
- **Browser, real backend:** a new `e2e/u4-integration.mjs` (`test:browser:integration`) at 1440
  and 390px, on two model configurations (the starter's API, and a second definition with other
  keys installed by the runner):
  1. Open each Integration page from the navigation.
  2. Consumer APIs shows both definitions' versions and base URLs, and a base URL read from the page
     answers on the consumer API; the reference link opens `/docs` on that source.
  3. A background batch submitted through the API appears on Jobs and feed; cancelling it from the
     page leaves the job cancelled in `GET /jobs/{id}`.
  4. Keyboard order and axe on the three pages.
- **Gates.** Not run in the package (build acceptance). Screenshots of the three pages, light and
  dark and at 390px, are shown to the user for approval, as UA's surfaces were.
- **Documentation.** PRODUCT and CURRENT_FUNCTIONALITY (the Integration pages, the starter API);
  API.md (the `?api=` slug's form); EXAMPLE_MODEL (the starter's consumer API); UI_ACCEPTANCE
  (state rows); EXECUTION_GUIDE (the runner); CHANGELOG, PROJECT_STATUS, the 0.9 plan's row.

#### Exit

- The three pages work at 1440px and 390px, in light and dark, over the real backend.
- A fresh install declares the starter consumer API; `/docs` lists it.
- The focused checks pass, and the U4 record is written here.

#### U4 record (2026-10-07)

Implemented as planned; the screenshots (the three pages at 1440px, 390px and dark, and the cancel
dialog) approved by the user 2026-10-10.

- **Pages.** `features/settings/ConsumerApisPage`, `JobsPage` and `ApiReferencePage`, under a new
  **Integration** group (`/settings/consumer-apis`, `/settings/jobs`, `/settings/api-reference`).
  No backend route or contract changed: the pages read `GET /api/consumer` (every page),
  `GET /model`, `GET /system`, `GET /jobs`, `GET /capabilities` and post the cancel.
- **One component, no copies (U-D14).** Extracted and reused: `ui/SettingsTable` (Deployment's table
  frame, now used by the three pages and Deployment), `features/settings/limits.jobLimitItems`
  (Deployment's job limits, now also on Jobs and feed), `useSettingsRead` (behind `useSystem` and a
  new `useCapabilities`; Deployment's own capability read went), `consumerAddresses` (base URL,
  document and `/docs?api=` addresses, shared by two pages). `CopyValue` gained `labelled` and
  `href`; `ConfirmDialog` a `dismissLabel` (the cancel dialog reads **Keep the job** / **Cancel
  job**, not Cancel / Cancel job). Links in settings facts, notes and tables take `--link`.
- **Starter content 0.9.2** declares `rdm` as planned. On an existing database the release is
  installed at startup beside 0.9.0 and not activated; activate it in Settings › Model to see it.
  API.md now states the `?api=` slug's form.
- **Tests the starter change made wrong**, changed: the starter version in `test_model` and
  `test_effective_periods`; `model_support.renamed_model` renames a consumer API's exposed-type map
  (`objectTypes` as a keyed map); `test_consumer_api_model`'s base drops the starter's own API, and
  its activation test declares its definition as `c1` beside the starter's (with `rdm` already
  active, the test's different `rdm` v1 is, correctly, refused as a contract break); the 0.7 copy in
  `test_effective_periods` drops `consumerApis`. `u3-settings`' keyboard order includes the three
  new links.
- **Checks.** Backend: `-m "model or startup or consumer or contract"` in parallel (810 tests, 1 min
  37 s; the 10 failures above, fixed), then the changed modules, every user of `renamed_model` and
  the journeys J08, J20, J25, J26, J28–J31 (501 passed, 1 min 25 s); `ruff check` clean. The full
  suite was not run (the user's choice; build acceptance). Frontend: `vitest run src/features/settings
  src/ui src/routing/routes.test.ts` (unit tests in a new `IntegrationPages.test.tsx` rather than
  `Settings.test.tsx`, 8 cases), `format`, `lint` (0 errors, the 7 recorded warnings), `build`.
  Browser: `test:browser:integration` (13 checks, axe 0 violations on the three pages light and
  dark) and `test:browser:settings` (10 checks). Not run: `test:a11y`, `test:visual` (build
  acceptance; the new pages have no baselines yet).
- **Found, not changed.** `/docs` opened with `?api=<slug>` shows that source, then Scalar rewrites
  the address to `#<slug>`; the runner checks the source by its title, as V1's does. In full-page
  captures of a long settings page the rail's background stops at the viewport's height (Deployment
  too, so not new).

### U5: the Webhooks page

**Planned 2026-10-07** and implemented the same day on the user's request ("implement build 0.9
u5"); the plan was not approved separately. Needs U4 (implemented) and C12 (delivered).

**Outcome.** **Settings › Integration › Webhooks**, after Consumer APIs. An integrator or operator
subscribes a receiver to a consumer API's events without writing a request, keeps the signing key
shown once, and later reads whether delivery is going, why a subscription stopped and what to do
about it, then edits, suspends, resumes (with or without `reset`) or deletes it.

**Reference.** The list-and-detail settings pattern of Workspaces and Model (U-D10 as revised): the
catalogue beside the selected entry, each entry at its own address, taking turns below 760px.
`Section`, `DescriptionList`, `StatusPill`, `Notice`, `Modal`, `ConfirmDialog`, `CopyValue`, `Toast`,
`EmptyState`, `Skeleton`.

**Composable domains (ADR-032):** no door is affected. U5 adds a page over existing routes; it does
not touch identity, attribute storage, audit, bulk APIs, `match` or mapping coverage.

#### What exists (checked 2026-10-07)

- **No route is missing.** `/api/v1/consumer-subscriptions` (C11, C12) creates (answering
  `signingSecret` once), pages newest first, reads, edits (`PATCH` with `expectedVersion`),
  suspends, resumes (`reset`) and deletes. The answer carries `suspension` (reason, message, details)
  and `delivery` (`lastDeliveredAt`, `pending`). `GET /capabilities` has `consumerSubscriptions`
  (on or off, the delivery limits); with it off every route answers `404`.
  `GET /model` has each definition's `events` and `parameters`, which the create form needs.
- **Workspaces** already refuses a delete with "This workspace has webhook subscriptions" (U3), but
  does not name them.
- **Consumer APIs** (U4, reworked after its record; TODO "Document the starter's consumer API
  lookups and the reworked Consumer APIs page") lists each definition's routes from its OpenAPI
  document, not its events one by one. So a subscription's events cannot link to an event's
  declaration there; U5 shows each event's declaration (types, changes, what an update watches) in
  place, from the active model, and links the consumer API to Consumer APIs.
- The catalogue layout (`catalogue-layout`, the catalogue `nav`, the back button and the detail
  card) is copied in `WorkspaceAdmin` and `ModelWorkbench`. U5 would be the third copy.

#### Scope

1. **One catalogue component (U-D14).** `ui/CatalogueLayout` (the layout, the way back below 760px
   and the detail card) and `ui/CatalogueEntry` (an entry button with icon, title, subtitle and
   pill). Workspaces and Model move onto them; their markup and styles stay as they are.
2. **Routes and navigation.** `/settings/webhooks` and `/settings/webhooks/{id}`; Webhooks after
   Consumer APIs in the Integration group.
3. **Off.** With `manageSubscriptions` off the page reads nothing else and says that webhooks are
   off, naming `CONSUMER_SUBSCRIPTIONS_ENABLED` (and that it needs
   `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`), linking Deployment.
4. **Catalogue.** Subscriptions newest first with Load more: the URL's host and path, the consumer
   API and workspace, and a pill: Active, Retrying (a batch is failing) or Suspended. Without a
   selection the detail asks to choose one; with none, an `EmptyState` with **New webhook**.
5. **Detail.**
   - **Status**: when suspended, a `Notice` with the reason in words, its message, when, its details
     and the fix for that reason: `SUSPENDED_BY_USER` (resume); `MODEL_CHANGED` (each finding with its
     pointer; edit, then resume); `CONTRACT_VERSION_CHANGED` (accepted and served versions; a resume
     accepts the served one); `WORKSPACE_RETIRED` (reactivate the workspace, then resume, or delete);
     `DELIVERY_FAILED` (attempts, failing since, the last error; fix the receiver, then resume);
     `FILTER_MATCHES_NOTHING` (the parameter and values; edit the filter);
     `EVENTS_EXPIRED` (the lost positions and the publication; resume with reset, then re-sync from
     the publication).
   - **Delivery**: last delivered; while a batch fails, its delivery ID, attempts, failing since,
     last attempt, next attempt and last error (kind, status, message); delivery continues after
     position `acknowledgedThrough`.
   - **Subscription**: URL, consumer API (name and contract version, linked to Consumer APIs),
     workspace, events each with its declaration, filters, payload, mode (and debounce), signing key
     created, created, last changed.
   - **Actions**: Edit…, Suspend, Resume…, Delete…. Resume opens a dialog that explains continuing
     from the first event not acknowledged against `reset` (start after the feed's head, then re-sync
     from a publication, in that order); `409 SUBSCRIPTION_NEEDS_EDIT` lists each finding, and
     `409 EVENTS_EXPIRED` names the lost range and the publication and offers the reset. A
     `VERSION_CONFLICT` reloads and says so, as Workspaces does.
6. **New webhook** (a dialog): consumer API (definitions of the active release that declare
   events), workspace (active ones, the default first), events (checkboxes, each with its
   declaration), URL (with the allowed hosts; when none is allowed, a notice naming the setting),
   payload (`full`, `identity`), mode (`perChange`, `coalesced` with debounce seconds) and a filter
   field per declared parameter (values separated by commas, its match fields named). A refusal is
   shown with its message. On success a dialog shows the signing key once, with copy, and says it
   is never shown again; then the new subscription is selected.
7. **Edit** (the same form): events, filters, URL, payload and mode; the consumer API and workspace
   are shown, not edited (the API does not edit them). Only changed fields are sent.
8. **Workspaces.** A workspace refused deletion for its subscriptions lists them, each linked to
   its page.

**Not in U5:** a delivery log per attempt (C-D108 left it to U5 or later; no route keeps one, and
the receiver has the delivery IDs). `startAfter` on create (API only). Signing-key rotation (U8).
Any backend route or contract change.

#### Checks

- **Journeys.** No API journey changes, so no journey test is added. J-catalogue entries for
  subscriptions name Settings › Integration › Webhooks as their UI channel.
- **Backend.** None changed; not run.
- **Frontend unit** (`vitest run` on the changed areas): `routes.test.ts` (the two URLs both ways),
  a `WebhooksPage.test.tsx` (off; catalogue and empty state; create with the key shown once; each
  suspension reason's fix; resume with `SUBSCRIPTION_NEEDS_EDIT` and with `EVENTS_EXPIRED` then
  reset; edit sending only changes; conflict), the Workspaces and Model tests for the extraction;
  then `format`, `lint`, `build`.
- **Browser, real backend:** `e2e/u5-webhooks.mjs` (`test:browser:webhooks`) at 1440 and 390px on
  two consumer API configurations (the starter's `rdm` and a second definition with other keys and
  an event), with subscriptions on and `localhost` allowed: create from the page and read the key;
  the subscription in `GET /consumer-subscriptions/{id}`; a receiver that refuses, the retrying
  batch shown; suspend and resume by keyboard; delete; axe; screenshots light and dark.
- **Gates.** Not run (build acceptance).

#### Exit

- Webhooks works at 1440px and 390px, light and dark, over the real backend.
- The focused checks pass, and the U5 record is written here.

#### U5 record (2026-10-07)

Implemented as planned; waiting for the user's approval of the screenshots (the list and detail at
1440px, 390px and dark, the new-webhook dialog, the signing key, a retrying batch and the resume
dialog).

- **Page.** `features/settings/WebhooksPage` (catalogue, detail, the key dialog, suspension notice,
  resume dialog), `WebhookDialog` (new and edit) and `webhookText` (states, reasons, fixes, a failed
  attempt, an event's declaration). `/settings/webhooks[/{id}]`; Webhooks after Consumer APIs. No
  backend route or contract changed; the client gained the seven subscription calls, and the model
  type its `consumerApis` (the parts the page reads).
- **One component, no copies (U-D14).** `ui/CatalogueLayout` and `CatalogueEntry` replace the
  catalogue markup copied in Workspaces and Model, which moved onto them; Webhooks is the third
  user. A `webhook` icon joins `ui/Icon`. The harness takes `backendEnv` for a runner that turns a
  capability on.
- **Wording.** A failed attempt shows the engine's message as written (it already names the status,
  host or cause), prefixed "The receiver answered" for a status. A catalogue address wraps only after
  a slash or a dot.
- **Workspaces.** A workspace refused deletion for its subscriptions lists them
  (`GET /consumer-subscriptions?workspaceKey=`), each linked to its page.
- **Tests the change made wrong**, changed: the settings navigation's list (`Settings.test`) gained
  Webhooks; the subscribed workspace's case in `WorkspaceAdmin.test` became its own case, the
  webhooks named and linked.
- **Checks.** Frontend: `vitest run src/features/settings src/features/workspaces/WorkspaceAdmin.test.tsx
  src/features/model-admin src/routing/routes.test.ts src/app/App.test.tsx src/ui` (13 files, 172
  tests; the new `WebhooksPage.test` has 10), `format`, `lint` (0 errors, the 7 recorded warnings),
  `build`. Browser: `test:browser:webhooks` (12 checks, axe 0 violations on the list, detail and
  dialog, light and dark; the delivery's `RDM-Signature` verified with the key read from the page),
  and, for the extraction, `test:browser:w4` (21 checks) and `test:browser:wp12` (7 checks).
  Backend: no change, not run. Not run: `test:a11y`, `test:visual` (build acceptance; the page has no
  baselines yet).
- **Not seen.** The lower half of the new-webhook dialog (Delivery, the wait, the buttons) is below
  the fold in its screenshot; it is exercised by the unit tests and the runner, not inspected. The
  off state and the suspension reasons other than `SUSPENDED_BY_USER` are covered by unit tests
  only; no runner produces them on a real backend.
- **Found, not changed.** U4's CHANGELOG entry and record say Consumer APIs shows exposed types,
  lists and events; the page now lists routes (TODO above). The runner's first signature check keyed
  the HMAC with the decoded key bytes and failed: the key is the `signingSecret` text as answered,
  as API.md says; the runner was wrong, not the engine.

### U5a: webhook names, the delivery log and the Webhooks page revised

**Planned 2026-10-07** after the user reviewed U5 on the dev server, and implemented the same day on
their request ("plan and implement"); the four questions below were answered by the user, the journey
cases were not approved separately. Amends C-D108 ("No delivery history is kept").

**Outcome.** A webhook has a **name** of its own, beside its URL. Its page has two tabs above the
name: **Configuration** (today's detail) and **Deliveries**: every event the subscription delivered
or is delivering, newest first, with its event ID, event, object ID, status, attempts, the
receiver's status code and when it was sent. Opening one shows the same facts, the next attempt
while one is due, each attempt with its start, duration and answer, the **request body** as sent
and the **response body**, both as formatted, coloured JSON. The new-webhook dialog is rebuilt for
consumer APIs with many events and parameters: a searchable multi-select with chips for events, and
filters added one at a time from a menu, each with its values as chips.

**The question asked: do we track when a send starts and completes?** Not before U5a. The
subscription kept only its latest state (`last_attempt_at` and `last_delivered_at`, both the time
the dispatcher's round began, before the request; while a batch failed, its attempts, first failure,
next attempt and a 200-character error). Nothing marked a request in flight or measured its
duration, the request body was never stored, and only the first 4 KiB of a failing answer was read.
U5a records each attempt's start and completion.

**Composable domains (ADR-032):** the audit/history door is not affected: the delivery log is an
operational record of requests to receivers, kept for days, separate from record history and audit.

#### Decisions

| ID | Question | Decision | Why |
| --- | --- | --- | --- |
| C-D115 | Does a subscription have a name? | **The user, 2026-10-07:** required on create (1–200 characters, not unique), edited with `PATCH`; existing subscriptions are named after their URL's host and path by the migration. An edit of the name alone keeps a batch being retried | The URL no longer says which integration a webhook serves. Renaming changes nothing the receiver sees, so it does not drop a batch as other edits do |
| C-D116 | What is kept of a delivery? | **The user, 2026-10-07: every attempt.** One log entry per request (its delivery ID, the batch, the events or the notice it carries, its status and the body of its latest attempt) and one per attempt (start, completion, the receiver's status, or the error's kind and message, and up to 4 KiB of the answer). Amends C-D108 | Integrators need to see what was sent and answered while testing; the latest state alone loses earlier failures |
| C-D117 | Which request body does an event's detail show? | **The user, 2026-10-07: the whole request** as the receiver got it, with all the events in it (up to 100, at most 1 MiB): the latest attempt's body, since each attempt composes its objects anew (C-D111) | It is what the signature covers and what the receiver saw |
| C-D118 | How long is the log kept? | **The user, 2026-10-07: 7 days**, `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`, reported in capabilities. The dispatcher deletes older entries by a set statement at most hourly; a request of a batch still pending is kept | Bodies reach 1 MiB a request; a week covers testing an integration |
| C-D119 | What does the deliveries list list? | One row per event in a per-change request, one per notice in a coalesced one (no event or object ID). Rows of one request share its status, attempts, answer and time: delivery is per request, not per event. Statuses: `queued` (built, not sent yet), `sending`, `retrying` (failed, will be tried again or waits for a resume), `succeeded`, `failed` (the subscription was suspended `DELIVERY_FAILED`), `dropped` (an edit or resume dropped the batch, or its events left the subscription) | The user asked for events; the request is the unit that succeeds or fails |

#### Contract

- **Name.** `name` in the create body (required), in `PATCH` and in every subscription answer.
- **`GET /api/v1/consumer-subscriptions/{id}/deliveries`** (paging, `status`): newest first.
  Each item: `deliveryId` (the request's, as `RDM-Delivery-Id`), `eventId`, `event`, `change`,
  `objectType`, `objectId` (`null` for a notice), `position`, `status`, `attempts`,
  `responseStatus` (the latest attempt's, `null` before an answer or for an error without one),
  `sentAt` (the latest attempt's start), `nextAttemptAt` (while the batch waits for a retry).
- **`GET /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}`**: the request: `deliveryId`,
  `batchId`, `kind` (`events`, `notice`), `status`, `events` (each as in the list), `requestBody`
  (the JSON sent, `null` before the first attempt), `requestBytes`, `createdAt`, `nextAttemptAt`,
  `attempts` (each `number`, `startedAt`, `completedAt`, `durationMs`, `responseStatus`, `error`
  `{kind, message}` or `null`, `responseBody`, text up to 4 KiB). `404 DELIVERY_NOT_FOUND`.
- **Capabilities.** `consumerSubscriptions.logRetentionDays`.
- **Storage.** `consumer_webhook_requests`, `consumer_webhook_request_events` and
  `consumer_webhook_attempts`, removed with their subscription (`CASCADE`); revision `20261007_01`
  adds them and `consumer_subscriptions.name`.

#### Journey cases (J30.6 amended, J30.10 new)

Each runs on two model configurations with the receiver of `test_j30_delivery`.

1. **Named.** Given the capability on, when an operator creates a subscription without `name`, then
   `422 REQUEST_VALIDATION_ERROR`; with a name, the answer and every read carry it; a `PATCH` of
   the name alone changes it and keeps a batch being retried (its `delivery.pending` unchanged).
2. **Delivered.** Given a receiver answering `200`, when two records change and the dispatcher runs,
   then `/deliveries` lists one row per event newest first, each `succeeded`, 1 attempt, `200`,
   `sentAt` set, with the event IDs, events and object IDs the receiver got; the request's detail
   has `requestBody` equal to the body the receiver got and one attempt with `startedAt` ≤
   `completedAt`, `durationMs` ≥ 0 and the receiver's answer as `responseBody`.
3. **Retried.** Given a receiver answering `503` then `200`, after the first round the rows are
   `retrying`, 1 attempt, `503`, with `nextAttemptAt` equal to the subscription's
   `delivery.pending.nextAttemptAt`; after the retry they are `succeeded` with 2 attempts, the
   detail listing `503` then `200`.
4. **Dropped and failed.** An edit of the URL while a batch is retried leaves its rows `dropped`,
   and the next batch has a new `deliveryId`; a receiver failing for 24 hours leaves the batch's rows
   `failed` and the subscription suspended `DELIVERY_FAILED`.
5. **Coalesced.** A coalesced subscription's rows are its notices: the event key, no event or object
   ID, `succeeded`.
6. **Kept for the retention.** Rows older than `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` are gone after
   the dispatcher's next round, a batch still retried keeps its rows, and capabilities report the
   retention.
7. **Refusals.** An unknown delivery ID is `404 DELIVERY_NOT_FOUND`, an unknown subscription `404
   SUBSCRIPTION_NOT_FOUND`; a deleted subscription's deliveries go with it.

Plus the migration's checks (AGENTS.md): upgrade from `20261006_03` with a subscription (named after
its URL), two starts, an interrupted run recovering.

#### UI

- **The dialog** (`ui/Modal` wide), in sections: **Webhook** (name, URL), **Source** (consumer API
  and workspace side by side), **Events** (all, or chosen in a searchable list whose choices show as
  removable chips, each option with its declaration), **Filters** (**Add filter** opens a searchable
  menu of the parameters not yet used; each added filter is a row of its name, its values as chips
  typed with Enter or a comma, and a remove button), **Delivery** (payload and mode side by side, the
  wait when coalesced). New components: `ui/MultiSelect`, `ui/TokenField` on React Aria (ADR-023).
- **The detail.** `ui/Tabs` gains a header between the tab list and the panels: the tab list where
  the "Webhook" eyebrow was, then the name with the URL and API below it, then the panel.
  `/settings/webhooks/{id}` is Configuration, `/settings/webhooks/{id}/deliveries` Deliveries, and
  `/settings/webhooks/{id}/deliveries/{deliveryId}/{eventId}` an opened event (a notice without the
  last part).
- **Deliveries**: a settings table, Load more and Refresh. A row opens the event (a wide `Modal`):
  the row's facts and the next attempt; **Attempts** (start, duration, status or error), choosing
  one shows its response; **Request** and **Response** in `ui/JsonView` (formatted, coloured from
  existing text tokens; plain text when the answer is not JSON), each with copy.
- The catalogue and the header show the name, with the URL below it.

#### Checks

Backend: the new journey cases and the J30 groups (`--journey J30`), `test_startup` for the
migration, the unit tests of the changed client, `test_foreign_keys`, the event volume budget
(`test_consumer_event_volume`, the delivery's statements must still hold), `ruff`. Frontend: the
Webhooks unit tests, `format`, `lint`, `build`; `test:browser:webhooks` extended to the name, the
tabs, the deliveries and an opened event; screenshots. Not run: the full suites (build acceptance).

#### U5a record (2026-10-07)

Implemented as planned; waiting for the user's approval of the screenshots (the dialog with the
events picker and the filter menu, the Configuration and Deliveries tabs at 1440px, 390px and
dark, an opened event).

- **Worked beside another session.** While U5a was planned, another session removed the webhook
  host allowlist (C-D101 revised) in the same files; U5a waited until it finished and builds on
  it, so the dialog has no allowed-hosts hint. That session then planned C17 (C-D120–C-D128),
  which will retire the coalesced mode and with it the notice rows; nothing in U5a changed for it.
- **Backend.** `models/database.py` gains `ConsumerSubscription.name` and the three log tables
  (revision `20261007_01`, which names existing subscriptions after their URL's host and path);
  `engine/events/delivery_log.py` writes and reads the log; the dispatcher logs each batch when it
  is committed, each attempt's start in the lease renewal before the send and its answer after,
  marks a given-up batch `failed`, and prunes at most hourly from `run_once`; `clear_delivery`
  marks a dropped batch `dropped`; a rename alone keeps a batch being retried. `webhook_client`'s
  `Answer` keeps up to 4 KiB of every answer, not only a failing one.
  `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` joins the settings catalogue and capabilities.
- **Frontend.** `ui/MultiSelect`, `ui/SearchMenu`, `ui/TokenField` and `ui/JsonView` (React Aria,
  ADR-023); `ui/Tabs` takes a `header` between the tab list and the panels; `CopyValue` a
  `buttonOnly`. `WebhookDialog` rebuilt; `WebhookDeliveries` (the tab and the opened event); the
  routes `/settings/webhooks/{id}/deliveries[/{deliveryId}[/{eventId}]]`. The catalogue and the
  workspace page name webhooks by their name, the URL below.
- **Tests the change made wrong**, changed: the create bodies of `test_j30_subscriptions`,
  `test_j30_delivery` and `volume_baseline` gained a `name`; the two J30.6 capability cases gained
  `logRetentionDays`; `test_j30_delivery`'s receiver can answer with a body; `test_startup`'s head
  moved to `20261007_01`; `test_foreign_keys` pins the three cascades; the OpenAPI lock was
  re-baselined (removing `logRetentionDays` gives the previous hash exactly, checked); the
  Webhooks, Workspaces and route unit tests follow the name and the new controls.
- **Checks.** Backend: the new `test_j30_delivery_log` (7 cases × 2 configurations, confirmed
  failing first), then in parallel every J30 module, `tests/unit/engine/events`, `test_startup`
  (two new migration cases: upgrade with a subscription and two starts, interrupted run and
  recovery), `test_foreign_keys`, `test_openapi_contract` and `tests/unit/test_config.py` (201
  passed after the capability fix, 41 s); `test_consumer_event_volume` (the delivery's statements
  still equal at both sizes, 20 s); `ruff check`. The full suite was not run (a migration selects
  it; build acceptance). Frontend: `vitest run` on settings, workspaces, model admin, routing,
  `App.test` and `ui` (176 passed, then `WebhooksPage.test`'s 12th case for `sending` and notice rows), `format`, `lint` (0 errors, the 7
  recorded warnings), `build`. Browser: `test:browser:webhooks` (15 checks; axe 0 violations on the
  list, detail, deliveries with an opened event and the dialog, light and dark; the opened event's
  request body equal to the body the receiver got).
- **Closed after the first report (the user, 2026-10-07).** A `sending` row and a notice row are
  rendered in a unit test (a request in flight lasts milliseconds, so no runner catches it on a
  real backend; no test observes `sending` at the API, which the dispatcher replaces once the
  answer arrives). The runner now creates a coalesced webhook with a one-second wait and checks its
  notice row and body on the page, and takes the dialog scrolled to its buttons with the coalesced
  wait showing (16 checks). The first report had said tests covered both states; for `sending`
  that was not so.
- **Revised the same day (the user).** Edit, Suspend and Delete, with the notices their actions
  raise, moved into the Configuration tab; the header above both tabs keeps the name, the state and
  a suspension notice. The resume dialog no longer says it checks the allowed hosts, which the
  allowlist removal took away.
- **Found, not changed.** The request body kept is the latest attempt's: each attempt composes its
  objects anew (C-D111), so an earlier attempt may have sent other object states.

#### U5a revision: resending an event (2026-10-07)

**Asked by the user, 2026-10-07:** a **Resend** button in the delivered event's dialog that sends
the event again by hand, whatever its status; for a `succeeded` event only after a confirmation that
it was already delivered. The user also asked what `dropped` means and who drops a request: no
one does it directly. An edit (other than a rename) or a resume discards a request waiting for a
retry, and the same events go out again in a new request, unless the resume used `reset` or the
events no longer belong to the subscription. No "drop" action is added: it would repeat resume with
`reset`.

| ID | Question | Decision | Why |
| --- | --- | --- | --- |
| C-D129 | What does a resend send? | **The user, 2026-10-07: the opened event as it was sent**, taken from the stored body of its request (the object as it was then), alone in a new request with a new `deliveryId` and a fresh signature; a notice is resent as it was. A request never sent (`queued`) has no body to resend: `409 DELIVERY_NOT_SENT` | What the receiver got is what is repeated; resending the whole request would repeat up to 99 other events |
| C-D130 | How is a resend told apart? | **The user, 2026-10-07: the same `eventId`**, and the header `RDM-Redelivery: manual` on the request; the log's request names the delivery it repeats (`resendOf`) | It is the same change: a new ID would make a repeat look like a new change. A receiver that deduplicates by `eventId` decides with the header whether to process it again |
| C-D131 | When is it sent, and on which subscriptions? | **The user, 2026-10-07: during the call, on any subscription**, suspended ones included: one attempt, no retry, within the receiver timeout, its result in the answer (`succeeded` or `failed`). It moves no position and leaves a batch being retried alone | An operator testing a receiver wants the answer at once, and may test one before resuming |

**Contract.** `POST /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}/resend` with
`{"eventId": "…"}` for an events request (an empty body for a notice) answers `201` with the new
request's detail; `404 SUBSCRIPTION_NOT_FOUND`, `404 DELIVERY_NOT_FOUND`, `404 EVENT_NOT_IN_DELIVERY`
(the event is not in that request, or a notice was given one), `409 DELIVERY_NOT_SENT`. Rows and
details gain `resendOf`. Revision `20261007_02` adds `consumer_webhook_requests.resend_of`
(C17's migration follows as `_03`).

**Journey cases (J30.10).** (1) Given a delivered event, a resend sends one request with a new
delivery ID, the event exactly as before, `RDM-Redelivery: manual` and a valid signature; the answer
and a new newest row are `succeeded` with `resendOf`; the subscription's position and delivery state
are unchanged. (2) To a receiver answering `500`, a resend of a suspended subscription's event is
`failed` after one attempt, and the dispatcher does not retry it. (3) A notice is resent as it was.
(4) An event not in the request is `404 EVENT_NOT_IN_DELIVERY`; a queued request is `409
DELIVERY_NOT_SENT`.

**UI.** The dialog's **Resend** (always shown; disabled for a request never sent, with the reason);
for a `succeeded` event a confirmation, "Resend a delivered event?", first. The result shows in the
dialog with a link to the new delivery, and the list reloads; a resend's row says "resent".

**Record (2026-10-07).** Implemented as planned; screenshots (the confirmation and the result)
approved by the user 2026-10-07. `engine/events/resend.py` (the route's work, in the API request), `delivery_log`'s
`finish_attempt` takes the status of a failed attempt (`failed` for a resend), revision
`20261007_02` (C17's migration renumbered to `_03` by its session). Checks: the three journey cases
× 2 configurations confirmed failing first, then `test_j30_delivery_log` (20 passed); in parallel
`test_startup` (a new case: upgrade from `20261007_01`, two starts, an interrupted run recovering),
`test_openapi_contract` (the gated route listed; the lock unchanged, the routes being off by
default), `test_foreign_keys`, `test_boundaries`, the other J30 modules and the event unit tests
(135 passed, 38 s); `ruff check`. Frontend: the Webhooks unit tests (14, two new: confirmation for a
delivered event, none for a failed one; disabled for a request never sent), `vitest run` on settings
and `ui` (79), `format`, `lint` (0 errors), `build`; `test:browser:webhooks` (17 checks: the resend
through the confirmation reaching the receiver with the same event, a new delivery ID and
`RDM-Redelivery: manual`). Not run: the full suites, `test:a11y`, `test:visual`.

**Revision: the object's record (2026-10-07, the user).** The object ID in the deliveries list and
in the opened event links to the record: the type found from the event's public name through the
consumer API's `objectTypes`, the first application showing that type, the webhook's workspace.
No link for a notice, a deleted record or a type the active release no longer exposes. Checks: the
Webhooks unit tests (14, the link's route and its absence for a deleted record), settings and `ui`
(79), `lint`, `build`. The runner's new check (the link opening the record) could not run: the
backend under test was mid-change by C17's session. It ran in C17's run of `test:browser:webhooks`
the same day and passed (19 checks).

### Exit by 1.0

- Every administrative, integration and security object a route manages has a settings page, and
  every deployment setting is visible on one.
- Every consumer API's namespace, contract version and base URL is visible in the UI, and its
  documentation shows that version with no placeholder.
- Every surface uses the token layers and `ui/` components. The contrast test and the
  accessibility and visual gates pass in light and dark at desktop and 390px.

### U8: the Security pages (0.12, designed)

Designed in the [0.12 P0 plan](BASE_0_12_IMPLEMENTATION_PLAN.md#p0-plan-2026-10-22); the user
approved the [mock-ups](https://claude.ai/artifact/CiHGaobpx8jsqaNZvmfXXo) on 2026-10-23. The
packages build on those shapes: I2 (sign-in, account), SP1, SP2, I3, Z5, A3.

- **The sign-in page** is the engine's (`/oauth/authorize`), not the frontend's: the product name,
  username and password, the provider's button, "Forgotten your password? Ask a security
  administrator", and the source link with the licence. Its messages: a wrong username or password
  (never which), slowed after repeated failures with the wait, and "your session ended" with the page
  the person returns to. At 390px it is one column.
- **The account menu** replaces "Local session": the person, their e-mail and main role,
  "Account", "All settings", the theme, "Sign out", and the source link. **Account** is a General
  page. _Built by I2 (2026-10-23)_ without the role (Z1) and the source link (L1), D273; the sign-in
  page without the provider's button (I3) and the source link. _Z1 (2026-10-23):_ the role line
  names the roles held in the workspace open ("Data steward in Herbarium"; the default workspace in
  Settings), Account, All settings and Sign out are buttons alike (the user), and Account's **What
  you can do** lists the person's grants from the approved "Account with roles" boards.
- **Security pages** use the list-and-detail pattern (U-D10): the list beside the selected entry,
  inside the page; at 390px the list alone, a row opening the detail. No page names an application or
  record type; narrowing shows the model's names as data.
- **Roles** is a matrix of roles by action group, each group with a one-line description;
  predefined columns read-only, a custom role edited in place with its holders counted.
- **A workspace's Access** tab lists every grant that applies, with "From" (this workspace, the whole
  instance) and "Through" (directly, a group); the grant dialog takes who (a person, group or
  client), the role, and "Narrow what they may change" (everything, or chosen record types), states
  that reading is never narrowed and says in a sentence what the grant allows.
- **Secrets** are shown once in a dialog with "Copy" and "I have copied it"; the previous one's end
  is stated and can be brought forward from the Secrets table.
- **The interface follows permissions** (Z5): a Reader's record view has no edit affordance and a
  note "You can read this workspace" with whom to ask; a Contributor sees "Propose a change" and a
  note that changes go to their change set, whose name and count sit in the top bar.
- **Approvals** (A3): the change set's review shows "Waiting for approval", the submitter and
  version; the approver's side panel holds the comment ("required to send back"), "Approve and
  publish" and "Send back", and the history of decisions. The **inbox** is a top-bar button with an
  unread count opening a list (requests, decisions, finished jobs); at 390px the two actions sit in
  a bar at the bottom.

U-D11 holds: each Security entry appears in the navigation only when its page is built.

## Decisions

U-D1–U-D6 were decided by the user on 2026-10-05; U-D7–U-D9 on 2026-10-06. U-D10 and U-D11 on 2026-10-06 (U-D10 revised by the user the same day), U-D12 and U-D13 on 2026-10-06, U-D14 on 2026-10-06.

| # | Question | Recommendation | Why |
| --- | --- | --- | --- |
| U-D1 | Rename `apiKey` in public contracts? | **Decided 2026-10-05: yes.** Before C6. The JSON field becomes `consumerApi` (in the API index, subscriptions, events and error details), and the route placeholder is written `{consumerApi}` in docs. The model keeps `key`, as every model element does. Error codes stay (`CONSUMER_API_NOT_FOUND` already says it) | "API key" means a credential to every integrator, and 0.12 forbids credentials in URLs, so the name invites the very misreading C-D1 rules out. Today only the route carries it (no error does, C-D59). After C6 and C11 it would sit in three more contracts |
| U-D2 | Deployment settings: environment only, or editable in the UI? | **Decided 2026-10-05: read-only for now**, to revisit once 0.11 and 0.12 make runtime changes safe. Environment only; the UI shows them read-only with the variable name | They govern startup, limits and capability gates. Changing them at runtime needs propagation across processes (0.11) and authorization (0.12). Runtime objects (subscriptions, clients, keys) are data and are edited in the UI |
| U-D3 | Webhook subscription UI in 0.9 or 0.12? | **Decided 2026-10-05:** 0.9 (U5), unsigned like the API; 0.12 adds keys. _Amended 2026-10-05 (C-D12 revised):_ signed from 0.9, the key shown once on create; 0.12 adds rotation | The API arrives in C11. A page over it is cheap, and integrators need to see delivery state while testing |
| U-D4 | Where the UI foundation lands | **Decided 2026-10-05:** U1–U5 in 0.9 above the cut line; U6 first in 0.10 | The settings pages and the 0.9 import screen are new surfaces and should be built once, on the foundation. U6 must precede the 0.10 editor |
| U-D5 | Should the starter model declare a consumer API? | **Decided 2026-10-05: yes**, a small one in U4, as a starter content release. _Done in U4 (2026-10-07):_ content 0.9.2, `rdm` with one event (the user chose the event) | Without one, the Consumer APIs page and `/docs` show nothing on a fresh install. Tests keep their own definitions |
| U-D6 | Visual direction | **Decided 2026-10-05: Direction B, "Open", for now** ([ADR-039](DECISIONS.md#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state)). Chosen by the user in U1 from two mockups | It is a product decision, not an engineering one |
| U-D7 | How much does U2 re-colour? | **Decided 2026-10-06: all of it.** The old token names become aliases of the new roles, so every screen takes Direction B's colours, type and rules in U2. Screens keep their markup until U6. All 41 baselines are re-recorded and inspected in U2, and `test:a11y` and `test:visual` run once in the package, as an exception to AGENTS' "gates at build acceptance" | Every baseline contains the shell, so the visual gate fails on all 41 whichever option is taken. The other option, new tokens for the shell only, would ship 0.9.0 with an indigo shell around green screens until U6 in 0.10. ADR-039's "U2 the shell, U6 the rest" then means structure, not colour |
| U-D8 | Which `ui/` components does U2 build? | **Decided 2026-10-06 (the user): `Card` is kept**, because the UI is not final and how a card looks and works is judged in the product. U2 builds `PageHeader` (the ten page headers), `StatusPill` (the band and the context statuses) and `Card`, styled from Direction B's tokens. Today's `.surface` panels resolve to the same tokens, so U2's screenshots show the card look; U6 moves those panels onto `Card`, or onto `Section` where a card looks wrong. `SettingsLayout`, `Section`, `DescriptionList`, `FormField`, `EmptyState`, `Skeleton` and `Toast` come with U3, and `Toolbar`, `Breadcrumbs` and `SegmentedControl` with U6 | UI_ACCEPTANCE §1: a shared component comes with the surfaces that use it. `Card` already has those surfaces in today's panels. ADR-039's "content on the page, not in cards" is held for now and tested against the product, not ruled out in advance |
| U-D9 | Which pairs does the contrast test hold to which ratio? | **Decided 2026-10-06, to be reviewed on U2's screenshots** (the user: "let's see how it looks"): text at 4.5:1 (3:1 for the 30px title). A control's border, the focus ring and any status or context marker that is the only sign of a state at 3:1, with `border.control` added as its own darker role. Separator rules (`border.subtle`, `border.strong`) are decorative and exempt, listed as such in the test | The mockup's control border is 1.6:1 and the light change-set dot is 2.9:1, both below WCAG 1.4.11's 3:1 for a boundary or state marker. The ruled look in ADR-039 needs light separators, which 1.4.11 does not cover. So "every border pair at AA" in this plan's §UI foundation is narrowed to borders that identify something |
| U-D10 | Where do the Workspaces and Model catalogues go, now that the rail holds the settings navigation? | **Revised 2026-10-06 by the user:** the screens as they were before U3, the catalogue beside the selected entry, inside the page next to the settings navigation; each entry keeps its address ([revisions](#u3-revisions-after-delivery-2026-10-06)). _Was: decided 2026-10-06 (the user): a list page and a detail page._ `/settings/workspaces` is a ruled table of workspaces (label, key, status, default) with New workspace, and `/settings/workspaces/{key}` is the workspace's page, with "Workspaces" as its eyebrow link back. `/settings/model` shows the active release, then the releases and the drafts as tables; a release or draft opens at its own URL. Paging stays cursors with Load more | U5's Webhooks and U8's users and clients have the same shape, so the settings area needs one list-and-detail pattern, and these two pages are its first uses. The detail keeps the content's full width, which the release diff needs. The alternative, a list column beside the detail inside the page, keeps today's side-by-side browsing but costs the detail about 280px on top of the settings rail, and the 390px layout stacks either way. Nesting the lists under their entries in the settings navigation would crowd it with paged lists |
| U-D11 | Does the settings navigation show pages not built yet? | **Decided 2026-10-06 by the user: no**, as recommended. Only built pages are listed. U4 and U5 add Integration's, and U7 and U8 add theirs. The mockup's Security entries tagged "0.12" are left out | An entry with nothing behind it is a dead end, and a disabled one says nothing a user can act on. What is planned is in ROADMAP |
| U-D12 | Which visual direction replaces Direction B, and how is it built? | **Decided 2026-10-06 (the user): Atlas, look E** ([ADR-040](DECISIONS.md#adr-040--the-atlas-visual-direction-todays-calm-shell-a-colour-for-every-kind-of-record)): today's shell and shapes with a colour for every kind of record and for the data context. Built in one pass (UA) before U4 and U5, each surface approved by the user from screenshots, with today's design tagged `ui-before-atlas` to switch back | The user found the product incoherent after U2 and U3, liked the current navigation, sidebar and shapes, and liked Atlas's colours; look E combined them and was accepted. Building slice by slice from written rules had drifted from the mockups |
| U-D13 | How does an object type (and an application) get its colour? | **Decided 2026-10-06 by the user, as recommended:** automatically, by its position in the model (`objectTypes`, `applications`) over the eight-hue palette, so any model is coloured and stays stable while its order does; a later schema version may let a model name a palette hue. The palette's hues are kept apart from the three context colours (green, amber, violet) by shade, or those three are left out of the type palette; the user picks from the two on the real app in UA1 | ADR-040 needs colour per type without the engine knowing type keys. Position needs no model change; naming a hue would change the model schema. The canvas used amber for categories and violet for the catalogue, the same hues as change sets and publications, which ADR-039's "one meaning per colour" warns against |
| U-D14 | Does Settings keep a top bar of its own? | **Decided 2026-10-06 by the user: no.** One navigation bar across the application, and every component reused rather than copied. Every area renders in `app/ShellFrame` under `app/TopBar`; on a settings page no tab is current and Settings is. The application's tab replaces "Back to applications" and returns to the same route. Revises U3's settings top bar and ADR-039's shell | The user found the settings bar different and not clickable (its product mark was text, it had no applications), and asked for one bar and no redundant code |
