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
buttons, menus, tables, dialogs, drawers, notices and asynchronous states. Whether those primitives are
implemented internally or adopted from a focused accessible library is a Base 0.6 decision. The model
continues to choose semantic components, not their DOM, CSS or icon implementation.

The foundation must:

- use readable default text and control sizes rather than relying on uppercase micro-labels;
- reserve pills, color and icons for information that has a stable meaning;
- distinguish primary, secondary, contextual and destructive actions consistently;
- preserve visible actions and essential information without hover-only discovery;
- provide deliberate dense-table and narrow-layout behavior;
- contain and restore focus in modal interactions and protect dirty forms from accidental dismissal;
- render structured field errors together with a task-level error summary; and
- use an intentional icon system with accessible names instead of decorative text glyphs.

## Component registry

Each implemented stable view type maps to a tested generic component:

- `table`: searchable, filterable, sortable and pageable objects; selection appears only with a
  supported bounded bulk action
- `form`: grouped fields, relations and validation
- `mappingGrid`: source values, selected targets, coverage filters and atomic mapping; bounded bulk
  mapping is a later integration capability
- `tree`: hierarchy browsing, parent selection and safe reordering
- `dashboard`: panels composed from queries and entry-point actions

The declarative contract and TypeScript types are discriminated by view type as each renderer becomes
supported. A semantic view must not silently resolve to an unrelated component. During the pre-1.0
transition, an older release containing a declared but unimplemented view follows an explicit
compatibility behavior and is never presented as though the specialist interaction exists.

Object detail uses a second registry. Its stable panel types are `attributes`, `children`, `relations`,
`table` and `hierarchy`. A panel definition selects its region, order, visibility and type-specific
configuration. The registry owns rendering and accessibility; the JSON model never supplies component
imports, markup or API URLs.

Field types map to suitable editors. Model-provided `ui` hints may refine widgets, grouping, width,
help text and visibility. The renderer supplies accessible defaults when hints are absent.

## Interaction priorities

- Workspace, application, view and object context have distinct navigation roles.
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

## Current implementation

The UI renders all application and view navigation from the model and keeps stable routes for
application views and objects. Its searchable explorer combines configured object types, parent
semantics and server-returned runtime paths. Collection views use server-side search and cursor
pagination.

Generic detail pages render configured breadcrumbs, headers, main panels and optional side panels via
the panel registry. Attribute, child, relation, table and hierarchy panels are reusable across object
types. Child and table panels reuse the same collection table and cursor controls as list views.
Runtime object CRUD is available from those generated screens. Root-creatable object types expose a
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
renderer and individual attribute writes carry the containing object's current version.

Relation panels preserve relation identity, attributes, direction and version. They derive valid
incoming and outgoing creation choices from the panel configuration and allowed object-type triples,
and use server-side, cursor-paged lookup across applications within the current workspace. Mutable
relationships can be created, edited and deleted; engine-maintained containment relationships remain
visible and direct users to the object's Parent editor. A panel can omit a constant relationship-label
column, and `ancestor:<objectTypeKey>` columns expose model-labelled containment context such as the
System owning a related System Value.

When an object type has no explicit detail entry, the engine derives a minimal attribute-and-hierarchy
composition from its bindings. Explicit details are preferred for task-oriented screens. Dedicated
mapping-grid and tree interactions remain future components; Base 0.5 currently resolves those view
types to the generic collection renderer as a known compatibility gap.

The model itself is an immutable installed release. Editing object-type, attribute-type and relation-
type definitions is model administration and is not part of runtime CRUD.

## Base 0.5 usability gaps

Base 0.5 proves the contracts but not yet the intended experience:

- complete object editing is split between a core-fields dialog and individual attribute actions;
- workspace and runtime object state are entered as free text;
- model-declared attribute filtering and sorting are not consumed by collection queries;
- all top-level view types currently resolve to the collection renderer;
- application/view navigation and the always-visible object explorer compete for attention;
- typography, surfaces, badges and status treatments come from one ad hoc stylesheet rather than a
  documented visual system; and
- component tests exist, but browser-level task, automated accessibility and visual-regression gates
  do not.

These are the Base 0.6 starting conditions, not reasons to replace the underlying model-driven
architecture.

## Base 0.6 direction

Base 0.6 first establishes the task flows and UI primitives, then delivers workspace discovery,
typed collection semantics and coherent object editing. The mapping grid is the first specialist view
implemented on that foundation. The existing JSON model workbench receives navigation, diagnostics,
provenance and dirty-input improvements, while a full model designer remains deferred.

The structured designer should eventually use reference-aware catalogues, forms, relationship
matrices and live preview. A dependency graph may help users understand a model, but a node-and-edge
canvas is not the default authoring surface.

See `BASE_0_6_IMPLEMENTATION_PLAN.md` for the decision gates, acceptance journeys and work packages.
