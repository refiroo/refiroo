# UI-04–UI-06 consolidated completion record

Completed 2026-09-11 with one deliberately small validation pass, as requested by the user.

## Delivered behavior

- UI-04 replaces the attribute-value modal with an inline typed editor. Explicit save/cancel/null/removal,
  live or named-draft feedback, conflict reconciliation, input retention and saved-but-refresh-failed blocking
  remain at the mutation boundary. The coherent full-record form remains available.
- UI-05 adds pointer and keyboard resizing for the navigation rail, optional desktop inspector and configured
  data columns. Each has bounded sizes. Rail/inspector preset buttons were subsequently removed at the user's
  request; visible dividers support arrow keys and double-click/Enter reset. The default full record page now
  includes a properties divider, with widths remembered per application/object type. Column visibility, density and widths are
  stored per view or embedded table; inspector widths are view-scoped. Invalid, blocked or stale browser storage
  falls back safely, record identity stays visible, and resize controls disappear in single-screen layouts.
- UI-06 gives the draft catalogue and current named draft a consistent presentation. Validation and activation
  form a clear two-step workflow, while discard remains in a secondary disclosure. Existing model mismatch,
  validation, conflict and retry messages retain their actionable behavior through shared notice components.

No backend, public API or model contract changed. Display preferences contain layout values only; they never
store record values, draft input, query state, workspace selection or draft context. UI-07 remains deferred.

## Validation

- `npm run format`: passed.
- `npm run lint`: passed with the repository's 12 pre-existing configured warnings and zero errors.
- Focused Vitest selection: 4 files, 19 tests passed. It covers inline typed values and conflicts, attribute
  actions for two object types, keyboard column resizing, preference corruption/blocking, scoping, reload,
  reset, identity protection and removed columns.
- `npm run build`: passed. Vite reported its existing bundle-size advisory.
- `git diff --check`: passed.

The full frontend suite and real-backend browser runners were intentionally not run. Consequently this record
does not claim exhaustive composed browser, screenshot, accessibility, mobile-keyboard or assistive-technology
acceptance. Those expensive checks remain available for WP10 or a later explicit validation request.

## Properties resizing correction

The previous handle only appeared in the optional collection-side inspector. The full record page now has a
visible divider beside its configured properties area (Codelist details, Value details, etc.). Rail and inspector
preset button rows are removed. Double-click or Enter resets a divider; arrow keys resize it. Narrow layouts
stack the panels and hide the divider. Two focused regressions verify properties resizing, persistence and reset
without losing inline input for two object types. Formatting, ESLint with zero errors, production build and
whitespace checks passed for the correction; no browser suite was run.
