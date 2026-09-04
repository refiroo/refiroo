# UI model

## Principle

The interface is generated from model semantics and optional view configuration. It should feel like
a deliberate RDM product, not a generic JSON editor. Configuration selects high-value components; it
does not prescribe pixels or expose API implementation details.

## Component registry

Each stable view type maps to a tested generic component:

- `table`: searchable, sortable, pageable objects with bulk selection
- `form`: grouped fields, relations and validation
- `mappingGrid`: source values, master matches, unmapped filter and bulk mapping
- `tree`: hierarchy browsing, parent selection and safe reordering
- `dashboard`: panels composed from queries and entry-point actions

Object detail uses a second registry. Its stable panel types are `attributes`, `children`, `relations`,
`table` and `hierarchy`. A panel definition selects its region, order, visibility and type-specific
configuration. The registry owns rendering and accessibility; the JSON model never supplies component
imports, markup or API URLs.

Field types map to suitable editors. Model-provided `ui` hints may refine widgets, grouping, width,
help text and visibility. The renderer supplies accessible defaults when hints are absent.

## Interaction priorities

- Creation is available in the context where the new value will be used.
- Selectors offer existing values and, when permissions and model behavior allow it, create-new.
- Mapping screens show both sides and the mapping state without navigating through object detail pages.
- Search never silently restricts itself to objects already loaded in the browser.
- Large datasets use server-side search and cursor pagination.

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
mapping-grid and tree interactions remain future components; those view types intentionally resolve
to the generic collection renderer in this slice.

The model itself is an immutable installed release. Editing object-type, attribute-type and relation-
type definitions is model administration and is not part of runtime CRUD.
