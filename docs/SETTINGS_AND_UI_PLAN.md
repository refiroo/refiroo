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

### Type palettes A and B

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
  Seen on the operators-and-timetables model: B's magenta (Master values) sits close to rose
  (Operators); A's gold and plum read as amber and violet only beside the Live chip, since no change
  set or publication was open.
  _Switched to B by the user (2026-10-06)_ after seeing both beside a change set: slots 3 and 4
  are magenta and olive in the tokens, with their dark values, under the same contrast test; the
  gold and plum primitives are removed (they are in commit `226beb2` if A is wanted back).
- **Hues repeat** after eight types: the operators-and-timetables model has 18, and RDM Master's 12
  collections show Domains and Timetable types both teal, Codelists and Durations both blue. This
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

- **The case.** On the dev server (operators and timetables), the type headings ("Timetable
  categories 15"), the folders and the records all drew one grey icon at nearly one weight, and
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
  longer headings are cut off ("Timetable catalog…"). A is in the code; both screenshots were
  sent.
- **Generic.** One tree for the sidebar and the tree lens; no key is read. Checked on the
  operators-and-timetables model (dev server) and the starter and volume models (runners).
- **Tests.** `Explorer.test`: a record's tile and its selected fill carry its own type's slot, a
  heading has no tile, a branch's guide sits below its toggle.
- **Checks.** `vitest related`: 6 files, 119 tests passed. `format`, `lint` (0 errors), `build`
  passed. Runners passed: `test:browser` (keyboard expansion at desktop and 390px), `s6`, `wp14`.
  `test:browser:b3` failed twice at B5b, differently (TODO); before UA2 it stopped at the drag of
  Sodium, which now passes. Screenshots at 1440px and 390px (drawer), light. **Not run:**
  `test:a11y`, `test:visual` (UA7).

#### UA2 revision: framed groups (2026-10-06)

Asked by the user after UA3, from the timetable hierarchy lens: nested scrolling groups ran into
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
- **Type groups fold** (asked by the user, 2026-10-07, after seeing why the timetable
  hierarchy's "Durations 6" looked like a stray label beside folding categories; the model was
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

- **The table column (decided by the user, 2026-10-06).** The canvas's Timetable types table had a
  Category column. No collection table in either example model declares a column that shows a
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
  relation tables use it, so a value's System and Language columns show chips (seen on an
  timetable type's System mappings and Translations). A row carries its record's hue; the
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
  Seen on the operators-and-timetables model (dev server); the runners use the starter model.
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
