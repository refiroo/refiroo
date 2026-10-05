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
| API settings | No authentication (0.12, C-D1). Webhook subscriptions arrive with C11 as an API, and their UI administration is planned for 0.12 | No integration page exists |
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
  per consumer API, webhook signing keys) in 0.12.

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
   signing key, and in 0.12 client secrets and signing keys after creation, are never returned by
   any read.

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
| Integration | Consumer APIs | Per definition: name, namespace, contract version, base URL with copy, OpenAPI URL, a link to its source on `/docs`, exposed types, lists, events. The model release that declares it, with a link to the model | `GET /api/consumer` (C6), the active release | U4 (0.9) |
| Integration | Webhooks | Subscriptions: create, edit, suspend, resume, delete; delivery state, last error, next attempt. Unsigned until 0.12, which adds the signing-key column | `/api/v1/consumer-subscriptions` (C11–C12) | U5 (0.9) |
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
(`/api/consumer/{namespace}/v{contractVersion}/openapi.json`):

- `paths` are written literally: `/api/consumer/rdm/v2/xref`, `/api/consumer/rdm/v2/lists/products`.
  Neither the namespace nor the version is a path parameter. Lists are separate paths, not
  `{listKey}`.
- `info.title` is the definition's `name`, and `info.version` is the contract version as a string
  (`"2"`). `info.description` names the model release that declares it.
- `servers` follows the deployment's root path, as the management source does (V1).
- With one installed version per definition (C-D3), there is one document per definition. A model
  release that raises the version changes the document at its new URL. The old URL answers
  `404 CONTRACT_VERSION_NOT_FOUND` naming the current version.

V2's sources on `/docs`: one per definition, labelled `{name} · v{contractVersion}`, built per
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
| U2 | 0.9 | U1 | Foundation: the token layers, the type and spacing scale, the components above, the rail and header, the data-context bar. Applied to the shell. Contrast test over the tokens. Shell baselines re-recorded |
| U3 | 0.9 | U2 | Settings area: `/settings` routes and layout; About, Appearance and Deployment; Workspaces and Model moved under Administration (old URLs redirect); the popover reduced to account and theme with a link to Settings; `GET /api/v1/system` |
| U4 | 0.9 | U3, C6, V2 | Integration pages: Consumer APIs, Jobs and feed, API reference. Starter consumer API per U-D5 |
| U5 | 0.9 | U4, C12 | Webhooks page over the subscriptions API |
| U6 | 0.10 (first) | U2 | The remaining surfaces on the foundation: record browser and inspector, relation matrix, tree, change sets and review, publications, model workbench. Before 0.10's editor (A4), which is built on it |
| U7 | 0.11 | U3 | Operations page over 0.11's health, readiness, metrics and backup routes |
| U8 | 0.12 | U5 | Security pages: sign-in and account; users and roles; OAuth clients and their access per consumer API; webhook signing keys (shown once, rotate). Replaces 0.12's "UI administration" items with pages in this area |

Order in the 0.9 queue (U-D4): CN1 right after C15; U1 any time as a filler; U2 and U3 after C13
and before J4, so the import screen is built on the foundation; U4 after V2; U5 after C12. All
above the cut line (D9): they are UI work and do not lengthen the API lines.

### Exit by 1.0

- Every administrative, integration and security object a route manages has a settings page, and
  every deployment setting is visible on one.
- Every consumer API's namespace, contract version and base URL is visible in the UI, and its
  documentation shows that version with no placeholder.
- Every surface uses the token layers and `ui/` components. The contrast test and the
  accessibility and visual gates pass in light and dark at desktop and 390px.

## Decisions

All decided by the user on 2026-10-05.

| # | Question | Recommendation | Why |
| --- | --- | --- | --- |
| U-D1 | Rename `apiKey` in public contracts? | **Decided 2026-10-05: yes.** Before C6. The JSON field becomes `consumerApi` (in the API index, subscriptions, events and error details), and the route placeholder is written `{consumerApi}` in docs. The model keeps `key`, as every model element does. Error codes stay (`CONSUMER_API_NOT_FOUND` already says it) | "API key" means a credential to every integrator, and 0.12 forbids credentials in URLs, so the name invites the very misreading C-D1 rules out. Today only the route carries it (no error does, C-D59). After C6 and C11 it would sit in three more contracts |
| U-D2 | Deployment settings: environment only, or editable in the UI? | **Decided 2026-10-05: read-only for now**, to revisit once 0.11 and 0.12 make runtime changes safe. Environment only; the UI shows them read-only with the variable name | They govern startup, limits and capability gates. Changing them at runtime needs propagation across processes (0.11) and authorization (0.12). Runtime objects (subscriptions, clients, keys) are data and are edited in the UI |
| U-D3 | Webhook subscription UI in 0.9 or 0.12? | **Decided 2026-10-05:** 0.9 (U5), unsigned like the API; 0.12 adds keys | The API arrives in C11. A page over it is cheap, and integrators need to see delivery state while testing |
| U-D4 | Where the UI foundation lands | **Decided 2026-10-05:** U1–U5 in 0.9 above the cut line; U6 first in 0.10 | The settings pages and the 0.9 import screen are new surfaces and should be built once, on the foundation. U6 must precede the 0.10 editor |
| U-D5 | Should the starter model declare a consumer API? | **Decided 2026-10-05: yes**, a small one in U4, as a starter content release | Without one, the Consumer APIs page and `/docs` show nothing on a fresh install. Tests keep their own definitions |
| U-D6 | Visual direction | **Decided 2026-10-05: Direction B, "Open", for now** ([ADR-039](DECISIONS.md#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state)). Chosen by the user in U1 from two mockups | It is a product decision, not an engineering one |
