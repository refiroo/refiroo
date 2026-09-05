# Frontend structure refactor

Structural reorganization of `frontend/src` following the review recorded as eighteen findings
(FE-01 … FE-18). Counterpart to `docs/BACKEND_STRUCTURE_REFACTOR.md`, which describes the
equivalent pass over `backend/app`.

**Status:** Phases 0–4 planned for immediate execution. Phase 5 approved, scheduled after review.
Phase 6 deferred to Base 0.6 decision D3.

## Scope

No API contract change, no change to the declarative model contract, and no architectural change.
The application keeps its hand-rolled history router, its registry-based generic renderers and its
plain-CSS styling. Every runtime code path stays unaware of application and object-type keys.

Phases 0–4 are behavior-preserving with two deliberate exceptions, both recorded below: FE-05 makes
five error messages more readable, and FE-01 changes how React identifies the generic renderers.
Phase 5 changes dialog keyboard behavior on purpose.

Verification for every phase is `npm run lint && npm run test && npm run build`.

## Baseline

Recorded before any change, on `refactor/backend-structure` at 665c530:

- 12 test files, 51 tests passing.
- Production build succeeds: 38 modules, 265.43 kB JS, 21.29 kB CSS.
- No lint step exists.

## Target layout

```
frontend/src/
├── main.tsx
├── app/
│   ├── App.tsx                  composition and route dispatch only
│   ├── AppShell.tsx             header, application nav, view nav, sidebar
│   └── useRouter.ts             route state, navigate, popstate, return-to-list memory
├── routing/
│   └── routes.ts                parseRoute, routePath, defaultRoute, viewRoute   (FE-08)
├── api/
│   ├── client.ts                request and the api surface
│   └── errors.ts                ApiError, isApiError, errorMessage               (FE-05)
├── model/
│   ├── lookup.ts                objectTypeFor, applicationFor, relationChoices
│   ├── fields.ts                attributeName, fieldValue, formatValue           (FE-04)
│   └── defaults.ts              fallbackDetail, DEFAULT_COLLECTION_QUERY
├── features/
│   ├── objects/
│   │   ├── CollectionView.tsx
│   │   ├── ObjectDetail.tsx
│   │   ├── DeleteImpactSummary.tsx                                               (FE-04)
│   │   ├── ObjectFormDialog.tsx
│   │   ├── ObjectToolbar.tsx
│   │   ├── Explorer.tsx
│   │   ├── views/registry.ts    view type → component                            (FE-02)
│   │   └── panels/
│   │       ├── registry.ts      panel type → component                           (FE-02)
│   │       ├── AttributesPanel.tsx / AttributeValueDialog.tsx                    (FE-03)
│   │       ├── RelationsPanel.tsx / RelationFormDialog.tsx                       (FE-03)
│   │       ├── ChildrenPanel.tsx / TablePanel.tsx / HierarchyPanel.tsx           (FE-03)
│   │       ├── CollectionPanelTable.tsx                                          (FE-03)
│   │       └── HistoryPanel.tsx
│   ├── model-admin/
│   │   ├── ModelWorkbench.tsx / CreateDraftDialog.tsx                            (FE-03)
│   │   ├── ModelDraftEditor.tsx / ModelReleaseDetail.tsx
│   │   └── ModelSummary.tsx / ModelDiff.tsx / ModelDiagnostics.tsx
│   └── workspaces/
│       └── WorkspaceSelector.tsx
├── ui/                          feature-agnostic primitives
│   ├── ConfirmDialog.tsx  Pagination.tsx  InlineError.tsx
│   ├── ObjectTable.tsx  ObjectLookup.tsx
│   └── AttributeField.tsx  attributeForm.ts                                      (FE-04)
├── lib/
│   ├── download.ts                                                               (FE-04)
│   └── hooks/
│       ├── useDebouncedValue.ts                                                  (FE-09)
│       ├── useAsyncResource.ts                                                   (FE-10)
│       ├── useCursorPages.ts                                                     (FE-11)
│       └── useCursorFeed.ts                                                      (FE-11)
├── types/
│   ├── index.ts                 barrel; `src/types.ts` moves here                (FE-07)
│   ├── model.ts     declarative model contracts
│   ├── runtime.ts   objects, relations, pages, audit, delete impact
│   ├── modelAdmin.ts drafts, releases, diagnostics, compilation, capabilities
│   └── ui.ts        RouteState, CollectionQueryState
├── styles/
│   ├── base.css  layout.css  components.css                                      (FE-16)
└── test/
    ├── fixtures.ts  setup.ts
```

Tests stay co-located with the module they cover and move with it.

## Phases

Each phase is a separate commit so that mechanical diffs never hide behavioral ones.

| Phase | Findings | Behavior change |
| --- | --- | --- |
| 0 — Tooling | FE-12 … FE-15 | none |
| 1 — Registry rendering | FE-01, FE-02 | React component identity only |
| 2 — Error handling | FE-05, FE-06 | five error messages become readable |
| 3 — Shared hooks | FE-09 … FE-11 | none |
| 4 — Structure | FE-03, FE-04, FE-07, FE-08, FE-16, FE-17 | none |
| 5 — Modal primitive | FE-18 | **yes** — Escape and focus restore become consistent |
| 6 — View-type honesty | (deferred) | **yes** — requires Base 0.6 decision D3 |

## Phase 0 — Tooling

### FE-12 — no lint step exists

`AGENTS.md` lists "linting passes" in the definition of done, but `frontend/` has no linter and no
`lint` script. The backend half of that requirement is enforced by `ruff`; the frontend half has
never been enforceable.

Add ESLint 10 with `typescript-eslint` and `eslint-plugin-react-hooks`, and an `npm run lint`
script. `react-hooks/rules-of-hooks` is what makes FE-01 a checked invariant rather than a
convention, and `react-hooks/exhaustive-deps` covers the hand-maintained dependency arrays in
`CollectionView` and `Explorer`.

### FE-13 — dependencies are unpinned, and build tooling sits in `dependencies`

`package.json` declares `react`, `react-dom`, `typescript`, `vite` and `@vitejs/plugin-react` as
`"latest"`. `frontend/Dockerfile` runs `npm install`, so a container rebuild resolves those afresh
and can pick up a new major without any change to the repository.

This is not hypothetical. Adding `typescript-eslint` during this refactor re-resolved `"latest"`
and moved TypeScript from 7.0.2 to 6.0.3 as a side effect of an unrelated install.

Pin all five to caret ranges taken from the working lockfile, and move `typescript`, `vite` and
`@vitejs/plugin-react` to `devDependencies` where build tooling belongs.

**TypeScript version decision.** `typescript-eslint` 8 declares `typescript: ">=4.8.4 <6.1.0"`.
TypeScript 7 ships the native compiler with no JavaScript API, which that parser requires, so the
two cannot be combined today. The project pins `typescript@^6.0.3` and keeps the standard ESLint
stack. Revisit when `typescript-eslint` admits TypeScript 7. The production build passes under
both compilers; only the linter constrains the choice.

### FE-14 — no formatter, and lines reach 2158 characters

The longest single line is the inlined create-draft dialog in `ModelWorkbench.tsx` at 2158
characters; `RelationsPanel.tsx` has an 846-character line and four more files exceed 500.

Add Prettier at `printWidth: 120` and apply it in one isolated commit before any other change, so
that the reformat does not obscure the phases that follow.

### FE-15 — `tsconfig.json` omits the checks Vite's own template enables

Add `noUnusedLocals`, `noUnusedParameters` and `verbatimModuleSyntax`. Add the `@/*` path alias
here and in `vite.config.ts`, needed once `features/objects/panels/` makes relative imports three
levels deep.

Also switch `frontend/Dockerfile` to `npm ci` so the image installs the locked tree.

## Phase 1 — Registry rendering

### FE-01 — the generic renderers are called as functions, not rendered as elements

`CollectionView` resolves a component from `viewComponentRegistry` and calls it:

```tsx
const Component = viewComponentRegistry[props.view.type];
return <>{Component(props)}</>;
```

`ObjectDetail.renderPanel` does the same for `panelComponentRegistry`. The consequence is that
`ObjectCollectionView`'s twelve `useState` calls execute as part of `CollectionView`'s own hook
list rather than their own.

This is not currently broken. The three panel components reached this way — `ChildrenPanel`,
`TablePanel` and `HierarchyPanel` — hold no hooks themselves, and `App.tsx` remounts
`CollectionView` through its `key`. It is latent: adding one `useState` to any panel component
makes `ObjectDetail`'s hook order depend on which panels are `visible` and how they sort, which is
a rules-of-hooks violation and a crash.

Render as elements instead. This is also what restores per-panel names in React DevTools, and what
lets a panel be wrapped in `React.memo`, an error boundary or a Suspense boundary later.

**Behavior note.** React begins treating each panel and view as its own component instance. State
inside a panel now survives its parent re-rendering, and is discarded when the panel unmounts,
which is the intended semantics. No panel currently holds state at that level, so no observable
behavior changes today.

### FE-02 — registries live inside the screens they serve, and cast their own props

Both registries are exported from the component file that first needed them, and each entry casts
`props.panel as XPanelDefinition`. `PanelDefinition` is already a discriminated union on `type`, so
a registry typed per key gives each panel exact props with no cast.

Move `viewComponentRegistry` to `features/objects/views/registry.ts` and `panelComponentRegistry`
to `features/objects/panels/registry.ts`. This is the seam where Base 0.6 decision D3 will be
expressed (see Phase 6), and it should be a module boundary before that work starts.

## Phase 2 — Error handling

### FE-05 — error-message extraction is duplicated 30 times and inconsistent at 5 more sites

`cause instanceof Error ? cause.message : String(cause)` appears 30 times. Five other sites call
bare `String(cause)`, which renders `Error: Request failed with 500` to the user instead of the
message: `App.tsx:24`, `ObjectDetail.tsx:93`, `ModelDraftEditor.tsx:55`, and
`ModelReleaseDetail.tsx:32` and `:35`.

Add `errorMessage(cause)` to `api/errors.ts` and use it at all 35 sites.

**Behavior note.** This is the one user-visible change in Phases 0–4: those five messages lose
their `Error: ` prefix and read the same as everywhere else in the application.

### FE-06 — version-conflict detection bypasses the typed error class

Five sites test `(cause as { code?: string }).code === "version_conflict"`:
`AttributesPanel.tsx:70`, `ObjectDetail.tsx:123`, `RelationsPanel.tsx:87` and `:140`, and
`ObjectFormDialog.tsx:80`. Four other sites correctly use `cause instanceof ApiError && cause.code
=== …`.

The cast form defeats the `ApiError` class that `api/client.ts` exists to provide, and would match
any thrown value carrying a `code` field. Optimistic concurrency is a product invariant; its
client-side detection needs one implementation.

Add `isApiError(cause, code?)` to `api/errors.ts` and use it at all nine sites.

## Phase 3 — Shared hooks

Three cross-cutting behaviors are re-implemented across the codebase, each with small unintended
variations. All three extractions are mechanical.

### FE-09 — debounced search, 3 copies

`Explorer`, `ObjectLookup` and `CollectionPanelTable` each hold a 250 ms debounce over a search
input, with three different variable names. Extract `useDebouncedValue(value, delay)`.

### FE-10 — cancellable async load, 7 copies

The `let active = true; … active && setState(); return () => { active = false; }` pattern appears
seven times under two names (`active`, `cancelled`), with `setError("")` placed inconsistently
before or after the request. Extract `useAsyncResource(fn, deps)` returning
`{ data, loading, error, reload }`.

### FE-11 — cursor pagination, 2 incompatible implementations

A cursor stack with a page index, supporting forward and backward movement, appears in
`CollectionView` and `CollectionPanelTable`. A separate append-on-demand feed appears in
`Explorer`, `ObjectLookup`, `RelationsPanel`, `HistoryPanel` and `ModelWorkbench`.

Both shapes are legitimate against the cursor-paged API. Extract `useCursorPages` for the first and
`useCursorFeed` for the second. `CollectionView` additionally encodes its reset key as
`JSON.stringify([...])`; the hook takes ownership of that.

## Phase 4 — Structure

### FE-03 — four files carry too many responsibilities

| File | Lines | `useState` | Contains |
| --- | --- | --- | --- |
| `ObjectDetail.tsx` | 292 | 19 | detail screen, panel registry, 4 panels, embedded paginated table, delete-impact renderer |
| `RelationsPanel.tsx` | 157 | 16 | panel, relation table, relation form dialog |
| `ModelWorkbench.tsx` | 146 | 15 | workbench, catalogue, inlined create-draft dialog |
| `ObjectFormDialog.tsx` | 118 | 9 | parent selection, required relations, attribute form |

Split per the target layout. Extracting `CreateDraftDialog` alone removes 7 of `ModelWorkbench`'s
15 state hooks.

`ObjectDetail` also duplicates its object-load-and-ownership-check logic at lines 76–82 and 85–95;
the extraction collapses those into one function.

### FE-04 — utilities exported from whichever screen first needed them

| Symbol | Currently in | Imported by | Moves to |
| --- | --- | --- | --- |
| `formatValue` | `ObjectTable.tsx` | AttributesPanel, RelationsPanel | `model/fields.ts` |
| `Pagination` | `ObjectTable.tsx` | CollectionView, ObjectDetail | `ui/Pagination.tsx` |
| `DeleteImpactSummary` | `ObjectDetail.tsx` | CollectionView | own file |
| `downloadJson` | `ModelDraftEditor.tsx` | ModelReleaseDetail | `lib/download.ts` |
| `parseAttributeValue`, `attributeValueFromForm` | `AttributeField.tsx` | 3 dialogs | `ui/attributeForm.ts` |

The two worst are `DeleteImpactSummary` and `downloadJson`: the collection screen imports the
entire 292-line detail screen to render a confirmation summary, and the release detail imports the
entire draft editor to trigger a file download.

### FE-07 — `types.ts` is one 393-line file mixing four contracts

Split into `types/model.ts`, `types/runtime.ts`, `types/modelAdmin.ts` and `types/ui.ts`.

**This touches a stated convention.** `AGENTS.md` says "Keep model contracts in `src/types.ts`".
`types/index.ts` is therefore a barrel re-exporting all four modules, so every existing
`from "../types"` import keeps working and the convention holds as written. `AGENTS.md` is updated
to name the directory and to record that `RouteState` and `CollectionQueryState` are UI state
rather than model contracts.

### FE-08 — `utils/model.ts` mixes four concerns

Model lookup, field projection and labelling, URL routing, and view defaults. `parseRoute` and
`routePath` have nothing to do with the model beyond checking that a key exists. Split into
`model/lookup.ts`, `model/fields.ts`, `model/defaults.ts` and `routing/routes.ts`.

### FE-16 — `styles.css` is one 291-line file with no layering

Split into `styles/base.css` (reset and tokens), `styles/layout.css` (shell, header, sidebar) and
`styles/components.css`. The `:root` token block defines six custom properties while several
hundred hardcoded hex values sit below it; the token set is extended so the Base 0.6 visual
foundation has something to build on. No rule is added, removed or reordered, so rendering is
unchanged.

### FE-17 — type-safety cleanups

- `objectTypeFor(model, …)!` in `AttributesPanel.tsx:13` and `CollectionPanelTable` throws if a
  release removes an object type that a stale route still references. Return the existing
  unavailable state instead.
- `fieldValue(item, key, model?)` declares `model` optional then dereferences `model!` for the
  `objectType` key. Every caller passes it; make it required.
- `binding!` and `attribute!` are asserted six times inside one JSX expression in
  `AttributesPanel.tsx:41-43`. Narrow once above the return.

## Phase 5 — Modal primitive (approved, scheduled after Phase 0–4 review)

### FE-18 — four hand-rolled dialogs with divergent keyboard behavior

`ObjectFormDialog`, `AttributeValueDialog`, `RelationFormDialog` and the inlined create-draft
dialog each rebuild the same backdrop markup. Their behavior differs:

| | Escape closes | Focus restored | Focus trapped | Title id |
| --- | --- | --- | --- | --- |
| `ConfirmDialog` | yes | yes | no | static, single instance |
| create-draft dialog | yes | yes | no | static |
| `AttributeValueDialog` | no | no | no | derived |
| `ObjectFormDialog` | no | no | no | **hardcoded** |
| `RelationFormDialog` | no | no | no | **hardcoded** |

`AGENTS.md` requires that keyboard operation and semantic HTML are preserved; this is the one place
the codebase does not hold that line. The two hardcoded ids also collide if two dialogs are ever
open at once.

Introduce `ui/Modal.tsx` owning the backdrop, `role`/`aria-modal`, a generated `aria-labelledby`,
Escape, focus restore, focus trap and scroll lock, and rebuild `ConfirmDialog` on it.

**Behavior change, intended.** Three dialogs that currently ignore Escape start closing on it, and
focus returns to the element that opened them. Existing dialog tests are reviewed rather than
merely re-run.

## Phase 6 — View-type honesty (deferred to Base 0.6 decision D3)

`viewComponentRegistry` maps all five declared view types to the same component:

```tsx
table: ObjectCollectionView,  tree: ObjectCollectionView,  mappingGrid: ObjectCollectionView,
form: ObjectCollectionView,   dashboard: ObjectCollectionView,
```

A model declaring `type: "tree"` renders a flat table, labelled "tree" in the UI chrome. This
contradicts Base 0.6 release principle 4: the UI must not silently present a different semantic
view under the requested view-type label.

This is a functionality change requiring decision D3, not a refactor, so it stays out of this pass.
FE-02 exists to make it a registry edit rather than surgery inside `CollectionView`.

## Verification

Recorded on completion of Phases 0–4.
