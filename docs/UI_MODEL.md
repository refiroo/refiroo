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
Creation and optimistic-concurrency editing share one typed form renderer generated from global
attribute definitions and object-type bindings.

When an object type has no explicit detail entry, the engine derives a minimal attribute-and-hierarchy
composition from its bindings. Explicit details are preferred for task-oriented screens. Dedicated
mapping-grid and tree interactions remain future components; those view types intentionally resolve
to the generic collection renderer in this slice.
