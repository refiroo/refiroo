# UI model

## Principle

The interface is generated from model semantics and optional view configuration. It should feel like
a deliberate RDM product, not a generic JSON editor. Configuration selects high-value components; it
does not prescribe pixels or expose API implementation details.

Visual consistency is necessary but not sufficient. The interface is designed and accepted through
complete stewardship tasks: locating data, editing a valid object, understanding relationships,
recovering from conflicts and completing specialist mapping, translation and hierarchy work. A new
theme without improved task flow is not a usability release.

## Interaction and visual foundation

The frontend owns a small coherent system of semantic primitives for navigation, typography, fields,
buttons, menus, tables, dialogs, notices and asynchronous states. ADR-023 implements difficult
composite-widget behavior with React Aria Components behind RDM-owned wrappers; native semantic HTML
remains preferred for simple controls. RDM owns the wrapper APIs, product behavior, tokens and plain
CSS. Lucide is available only through one RDM icon wrapper. The model continues to choose semantic
components, not their library, DOM, CSS or icon implementation.

The foundation must:

- use readable default text and control sizes rather than relying on uppercase micro-labels;
- reserve pills, color and icons for information that has a stable meaning;
- distinguish primary, secondary, contextual and destructive actions consistently;
- preserve visible actions and essential information without hover-only discovery;
- provide deliberate dense-table and narrow-layout behavior;
- contain and restore focus in modal interactions and protect dirty forms from accidental dismissal;
- render structured field errors together with a task-level error summary; and
- use an intentional icon system with accessible names instead of decorative text glyphs.

### Implemented Base 0.6 foundation

`frontend/src/ui/` is the application-facing component boundary. Feature and application modules are
lint-prohibited from importing `react-aria-components`, `lucide-react` or their subpaths directly.
React Aria currently supplies dialog/overlay focus and dismissal, combobox/listbox selection, menus
and tabs behind RDM wrappers. Simple inputs, buttons, links, forms and tables remain native HTML.
Lucide is exposed only through `ui/Icon.tsx`, which hides decorative icons and requires a label when
the icon itself conveys information.

The CSS token contract is defined in `frontend/src/styles/base.css` and grouped by semantic role:

- `--color-*` describes canvas, surface, text, border, accent and feedback roles;
- `--space-*` supplies the shared spacing scale;
- `--text-*` supplies readable small, body and heading sizes;
- `--radius-*`, `--focus-ring` and `--shadow-overlay` define shape, keyboard focus and elevation.

Plain component CSS consumes those tokens; the application model never contains a CSS token or
primitive-library name. The shell exposes product, workspace, application, collection/lens and object
context separately, includes a skip link and exposes the context trail as a labelled ordered list,
then collapses application navigation behind a labelled control at narrow widths. Tables retain native
table semantics inside a labelled horizontal-scroll region. Contextual row actions use a
keyboard-operated menu while `Open` remains directly visible. Newly mounted task-level error notices
receive focus so their preserved-input and recovery message is announced immediately.

WP1 initially preserved Base 0.5 custom-key entry as an interaction boundary. WP2 replaces that
temporary behavior with the authoritative, searchable workspace catalogue. The selector displays
workspace labels while retaining stable keys in URLs, identifies retired selections and does not
accept arbitrary keys.

## Component registry

Each supported stable view type must map to a tested generic component. The planned semantic registry
is:

- `table`: searchable, filterable, sortable and pageable objects; selection appears only with a
  supported bounded bulk action
- `form`: grouped fields, relations and validation
- `mappingGrid`: source values, selected targets, coverage filters and atomic mapping; bounded bulk
  mapping is a later integration capability
- `tree`: hierarchy browsing, contextual child creation and safe parent selection; sibling ordering
  has no separately accepted contract
- `dashboard`: unscheduled concept, not a release commitment

In Base 0.6, only `table` is an implemented schema 0.5 top-level view. A semantic view never resolves
to an unrelated component; `mappingGrid`, `form`, `dashboard` and `tree` declarations are rejected
until their contracts and renderers exist. Product 0.7 adds `mappingGrid` through schema 0.6. Schema
0.4 releases remain inspectable historical JSON but are not runnable in Base 0.6; the project has no
production compatibility commitment requiring a legacy view adapter.

Object detail uses a second registry. Its stable panel types are `attributes`, `children`, `relations`,
`table` and `hierarchy`. A panel definition selects its region, order, visibility and type-specific
configuration. The registry owns rendering and accessibility; the JSON model never supplies component
imports, markup or API URLs.

Field types map to suitable editors. Model-provided `ui` hints may refine widgets, grouping, width,
help text and visibility. The renderer supplies accessible defaults when hints are absent.

## Contextual collection workspace

ADR-029 makes the model-driven application browser the single data-navigation surface. It combines
virtual collection entries with runtime containment records instead of asking users to switch between
`Browse hierarchy` and `Views`. The browser works for contained, recursive and flat application
models; the starter applications supply examples, not reserved navigation sections.

The main workspace distinguishes:

- **context:** workspace, application, Live/Draft/History and optional containing object;
- **collection:** the row/source object type;
- **lens:** one configured semantic view over that source type;
- **query:** scope, search, filters, sort and cursor trail; and
- **detail:** one object's application-defined composition.

For schema 0.5/0.6 the view source type groups lenses without changing the model contract. A table and
one or more mapping declarations over the same source type therefore share one collection destination.
Lens controls use the configured names. An application with no mapping declaration receives no mapping
control, and a flat application still exposes its root collections.

Filters are visible model-labelled facets. Direct-parent scope is a removable contextual facet;
declared table filters use typed controls; mapping lenses add a coverage-state facet. Search remains
server-side. Query changes reset cursor continuation, and compatible scope/search survive lens and
detail navigation. An unscoped collection remains explicit and should include configured path or
ancestor fields when its rows otherwise lack administrative identity.

## Interaction priorities

- Workspace, application, containing-object scope, collection/lens and object detail have distinct roles.
- Creation is available in the context where the new value will be used.
- Create and edit present all mutable parts of one object coherently: core fields, parent, typed
  attributes and required relationships.
- Selectors offer existing values and, when permissions and model behavior allow it, create-new.
- Mapping screens show both sides and the mapping state without navigating through object detail pages.
- Search never silently restricts itself to objects already loaded in the browser.
- Large datasets use server-side search and cursor pagination.
- Recoverable validation and concurrency failures preserve user input and explain the required action.
- Model lifecycle presentation distinguishes draft save, validation, immutable installation and
  activation.

## Established CRUD UI contract and WP9 recovery target

The behaviors in this section existed before the WP5/WP6 transition. They are the required generic UI
contract, and WP7 restored the backend contract over the workspace-revision runtime. WP9 must
restore/reuse these controls for normal live writes and explicitly selected optional drafts under
ADR-026/027. Current disconnected controls and lost non-default detail context are implementation
gaps, not read-only product rules.

The UI renders one application browser from the model and keeps stable routes for configured lenses
and objects. Its searchable explorer combines virtual collection groups, configured source types,
parent semantics and server-returned runtime paths. Collection lenses use server-side scope/search/
filter queries and cursor pagination.

Generic detail pages render configured breadcrumbs, headers, main panels and optional side panels via
the panel registry. Attribute, child, relation, table and hierarchy panels are reusable across object
types. Child and table panels reuse the same collection table and cursor controls as list views.
The restored runtime object CRUD must use those generated screens. Root-creatable object types expose a
collection create action; contained types are created from parent-filtered panels. Object detail edits
core fields with optimistic concurrency and provides a two-stage delete action. The first request is
non-cascading; when dependencies exist, the dialog renders the returned child objects, PK/FK
dependents and relationships in model-derived language. Only a second explicit confirmation sends the
cascade option.

When a contained object also has a required non-parent relationship, the generated create form derives
the permitted source object types from the allowed relation triples and includes cross-application
lookup. The object, its containment relation and required relationship are submitted together. This is
used by Translation creation to select a Domain, Codelist or Master Value without a key-specific UI.
Required outgoing one-to-many panels also expose dependent-object creation. Consequently a Translation
can be created from its Translation Group or directly from the translated object's Translations panel;
the latter preselects and locks the target while retaining model-derived parent selection.

Attribute panels distinguish an unset value from a stored falsy or null value. Editable bindings expose
model-driven add/edit actions, while optional stored values can be removed with confirmation. Required,
read-only and hidden bindings retain their declared behavior. All eight value types use one typed field
renderer. Individual attribute writes claim the containing object’s current version; only explicitly
draft-scoped writes additionally claim the draft’s current version.

Relation panels preserve relation identity, attributes, direction and version. They derive valid
incoming and outgoing creation choices from the panel configuration and allowed object-type triples,
and use server-side, cursor-paged lookup across applications within the current workspace. Mutable
relationships can be created, edited and deleted; engine-maintained containment relationships remain
visible and direct users to the object's Parent editor. A panel can omit a constant relationship-label
column, and `ancestor:<objectTypeKey>` columns expose model-labelled containment context such as the
System owning a related System Value.

When an object type has no explicit detail entry, the engine derives a minimal attribute-and-hierarchy
composition from its bindings. Explicit details are preferred for task-oriented screens. Schema 0.6
mapping grids are implemented as contextual collection lenses. Dedicated tree interactions remain a
future renderer; schema 0.5 rejects unsupported view types instead of resolving them to a misleading
generic collection renderer.

The model itself is an immutable installed release. Editing object-type, attribute-type and relation-
type definitions is model administration and is not part of runtime CRUD.

## Base 0.5 usability gaps

Before Base 0.6 work began, Base 0.5 proved the contracts but not yet the intended experience:

- complete object editing is split between a core-fields dialog and individual attribute actions;
- workspace and runtime object state are entered as free text, and the mutable workspace dataset
  cannot represent the immutable publication lineage accepted in ADR-024;
- model-declared attribute filtering and sorting are not consumed by collection queries;
- all top-level view types currently resolve to the collection renderer;
- application/view navigation and the always-visible object explorer compete for attention;
- typography, surfaces, badges and status treatments come from one ad hoc stylesheet rather than a
  documented visual system; and
- component tests exist, but browser-level task, automated accessibility and visual-regression checks
  do not.

These are the Base 0.6 starting conditions, not reasons to replace the underlying model-driven
architecture.

## Base 0.6 direction

Base 0.6 completes daily live maintenance using model-driven tables, forms and detail panels. The
visible context distinguishes **Live**, an explicitly selected **Draft**, and immutable **History**.
A catalogue-retired workspace is read-only. Model-defined availability is an ordinary field; it is not
an object publication state. Publication retirement removes the current-publication designation while
live data stays available.

A draft starts from actual current live data, including edits since the latest publication, or from
an explicitly selected historical snapshot. Empty-root creation is a development/bootstrap mechanism,
not the normal user workflow. WP8.1 supplies the missing current-live base and pinned historical model
interpretation before the dependent browser flows can be accepted.

Activation applies only authored changes over current live content, checks touched-record conflicts,
preserves unrelated live work and validates the final combined graph. History is newest first and
presents source separately from supersession. Starting a draft from history is not restoring the active
dataset. Cancel, validation failure and version conflicts preserve input and persisted draft/live data.

A model-mismatched historical draft cannot activate through the Base 0.6 data flow. Show the source and
current models and explain the migration requirement. Product 0.10 adds a separate reviewed migration:
preview affected schema/data and potential loss, confirm the exact plan or cancel, then apply an atomic
workspace model/data change. Do not enable a fake override control or change other workspaces’ models.
Application-model drafts and workspace data drafts remain separate resources and concepts.

The [interaction specification](BASE_0_6_INTERACTION_SPEC.md) and product scenarios are the current
acceptance baseline. Earlier WP0/WP5 fixtures remain implementation evidence for the behaviors they
actually cover; update them alongside code rather than declaring the new flows proven by old fixtures.
Mapping 0.7 and translation/tree 0.8 preserve generic maintenance while adding specialist interactions.

The structured designer should eventually use reference-aware catalogues, forms, relationship
matrices and live preview. A dependency graph may help users understand a model, but a node-and-edge
canvas is not the default authoring surface.

See `BASE_0_6_IMPLEMENTATION_PLAN.md` for the accepted decisions, acceptance journeys and work packages.
