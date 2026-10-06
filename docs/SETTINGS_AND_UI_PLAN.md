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
- **API settings:** **Settings › Integration** (Consumer APIs, Webhooks, Jobs and feed, API
  reference) in 0.9, and **Settings › Security** (users and roles, OAuth clients and their access
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
| Integration | Webhooks | Subscriptions: create (the signing key shown once), edit, suspend, resume (after expired events: the lost range and the publication to re-sync from, and resume with `reset`, starting after the feed's head, with the order "reset, then re-sync" explained, C-D93 revised, C-D110; a resume that needs an edit lists what to fix, C-D98), delete; the suspension reason with its message and findings; the allowed hosts from capabilities (C-D101); a workspace's subscriptions named where deleting it is refused (`deleteBlockedBy: subscribed`); events chosen from the definition's declared events, each linked to its declaration on Consumer APIs; payload (`full` or `identity`); delivery state from the subscription's `delivery` (C12, C-D108): last delivered, and while a batch fails its attempts, first failure, last error by kind and next attempt; the dispatcher's reasons (`DELIVERY_FAILED`, `HOST_NOT_ALLOWED`, `FILTER_MATCHES_NOTHING`, `EVENTS_EXPIRED`) each with its fix; the delivery limits from capabilities. Signed from 0.9 (C-D12 revised 2026-10-05); 0.12 adds rotation | `/api/v1/consumer-subscriptions` (C11–C12) | U5 (0.9) |
| Integration | Jobs and feed | Recent jobs with status and outcome counts; cancel; batch and job limits; feed retention | job routes (B1–B2), `GET /api/v1/capabilities` | U4 (0.9) |
| Integration | API reference | Links to `/docs`, one per source, with its version | `GET /api/consumer` | U4 (0.9) |
| Security | Users and roles; OAuth clients and their access per consumer API; signing keys; sign-in | 0.12 routes | U8 (0.12) |

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

1. **Three token layers.** Primitive scales (neutral, operator and status hues, 50–900) feed semantic
   roles (`surface.app`, `surface.nav`, `surface.raised`, `surface.sunken`, `text.primary`,
   `text.secondary`, `border.subtle`, `border.strong`, `action.primary`, `state.selected`,
   `status.{draft, live, published, conflict, error, warning, success}`, `context.{live,
   changeSet, publication}`), and the semantic roles feed component tokens. Dark mode redefines the
   semantic layer only.
2. **Distinct regions.** The rail sits on its own toned surface, the content on the canvas, and
   panels and the record inspector are raised (border and shadow). The header carries the
   workspace and data context.
3. **Colour carries meaning.** The operator accent is used only for the primary action and the current
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
| U4 | 0.9 | UA, C6b, V2 | Integration pages: Consumer APIs, Jobs and feed, API reference. Starter consumer API per U-D5 |
| U5 | 0.9 | U4, C12 | Webhooks page over the subscriptions API (C12 delivered 2026-10-06: `delivery`, the four dispatcher reasons, `reset`) |
| U6 | — | — | **Folded into UA (2026-10-06):** the remaining surfaces are redesigned in UA, in 0.9. 0.10's editor (A4) builds on UA |
| U7 | 0.11 | U3 | Operations page over 0.11's health, readiness, metrics and backup routes |
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
   - *Primitives*: neutral (warm grey), indigo (operator), green, amber, violet and red scales,
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
  switches it, along with the limits and the webhook host allowlist.
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
  hue (4.5:1 on the fill and on white) and a marker. The canvas uses teal (timetable type), amber
  (category), blue (duration), rose (role), violet (catalogue) and coral (system value); cyan and
  slate complete the palette.
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
  390px (drawer). The user's screenshot of the timetables tree (type groups, folders and records
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
  the only ones; `AppShell` and `SettingsShell` only fill the rail and the content. On Settings no
  tab is current and the Settings link is (styled as current); the tab of the application last
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

### Exit by 1.0

- Every administrative, integration and security object a route manages has a settings page, and
  every deployment setting is visible on one.
- Every consumer API's namespace, contract version and base URL is visible in the UI, and its
  documentation shows that version with no placeholder.
- Every surface uses the token layers and `ui/` components. The contrast test and the
  accessibility and visual gates pass in light and dark at desktop and 390px.

## Decisions

U-D1–U-D6 were decided by the user on 2026-10-05; U-D7–U-D9 on 2026-10-06. U-D10 and U-D11 on 2026-10-06 (U-D10 revised by the user the same day), U-D12 and U-D13 on 2026-10-06, U-D14 on 2026-10-06.

| # | Question | Recommendation | Why |
| --- | --- | --- | --- |
| U-D1 | Rename `apiKey` in public contracts? | **Decided 2026-10-05: yes.** Before C6. The JSON field becomes `consumerApi` (in the API index, subscriptions, events and error details), and the route placeholder is written `{consumerApi}` in docs. The model keeps `key`, as every model element does. Error codes stay (`CONSUMER_API_NOT_FOUND` already says it) | "API key" means a credential to every integrator, and 0.12 forbids credentials in URLs, so the name invites the very misreading C-D1 rules out. Today only the route carries it (no error does, C-D59). After C6 and C11 it would sit in three more contracts |
| U-D2 | Deployment settings: environment only, or editable in the UI? | **Decided 2026-10-05: read-only for now**, to revisit once 0.11 and 0.12 make runtime changes safe. Environment only; the UI shows them read-only with the variable name | They govern startup, limits and capability gates. Changing them at runtime needs propagation across processes (0.11) and authorization (0.12). Runtime objects (subscriptions, clients, keys) are data and are edited in the UI |
| U-D3 | Webhook subscription UI in 0.9 or 0.12? | **Decided 2026-10-05:** 0.9 (U5), unsigned like the API; 0.12 adds keys. _Amended 2026-10-05 (C-D12 revised):_ signed from 0.9, the key shown once on create; 0.12 adds rotation | The API arrives in C11. A page over it is cheap, and integrators need to see delivery state while testing |
| U-D4 | Where the UI foundation lands | **Decided 2026-10-05:** U1–U5 in 0.9 above the cut line; U6 first in 0.10 | The settings pages and the 0.9 import screen are new surfaces and should be built once, on the foundation. U6 must precede the 0.10 editor |
| U-D5 | Should the starter model declare a consumer API? | **Decided 2026-10-05: yes**, a small one in U4, as a starter content release | Without one, the Consumer APIs page and `/docs` show nothing on a fresh install. Tests keep their own definitions |
| U-D6 | Visual direction | **Decided 2026-10-05: Direction B, "Open", for now** ([ADR-039](DECISIONS.md#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state)). Chosen by the user in U1 from two mockups | It is a product decision, not an engineering one |
| U-D7 | How much does U2 re-colour? | **Decided 2026-10-06: all of it.** The old token names become aliases of the new roles, so every screen takes Direction B's colours, type and rules in U2. Screens keep their markup until U6. All 41 baselines are re-recorded and inspected in U2, and `test:a11y` and `test:visual` run once in the package, as an exception to AGENTS' "gates at build acceptance" | Every baseline contains the shell, so the visual gate fails on all 41 whichever option is taken. The other option, new tokens for the shell only, would ship 0.9.0 with an indigo shell around green screens until U6 in 0.10. ADR-039's "U2 the shell, U6 the rest" then means structure, not colour |
| U-D8 | Which `ui/` components does U2 build? | **Decided 2026-10-06 (the user): `Card` is kept**, because the UI is not final and how a card looks and works is judged in the product. U2 builds `PageHeader` (the ten page headers), `StatusPill` (the band and the context statuses) and `Card`, styled from Direction B's tokens. Today's `.surface` panels resolve to the same tokens, so U2's screenshots show the card look; U6 moves those panels onto `Card`, or onto `Section` where a card looks wrong. `SettingsLayout`, `Section`, `DescriptionList`, `FormField`, `EmptyState`, `Skeleton` and `Toast` come with U3, and `Toolbar`, `Breadcrumbs` and `SegmentedControl` with U6 | UI_ACCEPTANCE §1: a shared component comes with the surfaces that use it. `Card` already has those surfaces in today's panels. ADR-039's "content on the page, not in cards" is held for now and tested against the product, not ruled out in advance |
| U-D9 | Which pairs does the contrast test hold to which ratio? | **Decided 2026-10-06, to be reviewed on U2's screenshots** (the user: "let's see how it looks"): text at 4.5:1 (3:1 for the 30px title). A control's border, the focus ring and any status or context marker that is the only sign of a state at 3:1, with `border.control` added as its own darker role. Separator rules (`border.subtle`, `border.strong`) are decorative and exempt, listed as such in the test | The mockup's control border is 1.6:1 and the light change-set dot is 2.9:1, both below WCAG 1.4.11's 3:1 for a boundary or state marker. The ruled look in ADR-039 needs light separators, which 1.4.11 does not cover. So "every border pair at AA" in this plan's §UI foundation is narrowed to borders that identify something |
| U-D10 | Where do the Workspaces and Model catalogues go, now that the rail holds the settings navigation? | **Revised 2026-10-06 by the user:** the screens as they were before U3, the catalogue beside the selected entry, inside the page next to the settings navigation; each entry keeps its address ([revisions](#u3-revisions-after-delivery-2026-10-06)). _Was: decided 2026-10-06 (the user): a list page and a detail page._ `/settings/workspaces` is a ruled table of workspaces (label, key, status, default) with New workspace, and `/settings/workspaces/{key}` is the workspace's page, with "Workspaces" as its eyebrow link back. `/settings/model` shows the active release, then the releases and the drafts as tables; a release or draft opens at its own URL. Paging stays cursors with Load more | U5's Webhooks and U8's users and clients have the same shape, so the settings area needs one list-and-detail pattern, and these two pages are its first uses. The detail keeps the content's full width, which the release diff needs. The alternative, a list column beside the detail inside the page, keeps today's side-by-side browsing but costs the detail about 280px on top of the settings rail, and the 390px layout stacks either way. Nesting the lists under their entries in the settings navigation would crowd it with paged lists |
| U-D11 | Does the settings navigation show pages not built yet? | **Decided 2026-10-06 by the user: no**, as recommended. Only built pages are listed. U4 and U5 add Integration's, and U7 and U8 add theirs. The mockup's Security entries tagged "0.12" are left out | An entry with nothing behind it is a dead end, and a disabled one says nothing a user can act on. What is planned is in ROADMAP |
| U-D12 | Which visual direction replaces Direction B, and how is it built? | **Decided 2026-10-06 (the user): Atlas, look E** ([ADR-040](DECISIONS.md#adr-040--the-atlas-visual-direction-todays-calm-shell-a-colour-for-every-kind-of-record)): today's shell and shapes with a colour for every kind of record and for the data context. Built in one pass (UA) before U4 and U5, each surface approved by the user from screenshots, with today's design tagged `ui-before-atlas` to switch back | The user found the product incoherent after U2 and U3, liked the current navigation, sidebar and shapes, and liked Atlas's colours; look E combined them and was accepted. Building slice by slice from written rules had drifted from the mockups |
| U-D13 | How does an object type (and an application) get its colour? | **Decided 2026-10-06 by the user, as recommended:** automatically, by its position in the model (`objectTypes`, `applications`) over the eight-hue palette, so any model is coloured and stays stable while its order does; a later schema version may let a model name a palette hue. The palette's hues are kept apart from the three context colours (green, amber, violet) by shade, or those three are left out of the type palette; the user picks from the two on the real app in UA1 | ADR-040 needs colour per type without the engine knowing type keys. Position needs no model change; naming a hue would change the model schema. The canvas used amber for categories and violet for the catalogue, the same hues as change sets and publications, which ADR-039's "one meaning per colour" warns against |
| U-D14 | Does Settings keep a top bar of its own? | **Decided 2026-10-06 by the user: no.** One navigation bar across the application, and every component reused rather than copied. Every area renders in `app/ShellFrame` under `app/TopBar`; on a settings page no tab is current and Settings is. The application's tab replaces "Back to applications" and returns to the same route. Revises U3's settings top bar and ADR-039's shell | The user found the settings bar different and not clickable (its product mark was text, it had no applications), and asked for one bar and no redundant code |
