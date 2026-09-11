# Hierarchy navigation correction — 2026-09-11

Browse hierarchy appears first, followed by Views. Hierarchy is selected on the first visit;
subsequent visits and refreshes restore the selected mode from browser storage before navigation
renders, without changing the current record/collection URL. Separate branch buttons expand/collapse children without
selecting a record. Branch choices persist in this browser per workspace/application using stable
record IDs, including nested collapsed branches when a parent is reopened. Live, draft and history
contexts share these navigation preferences. Branches initially start expanded. Views remains
available; switching modes does not discard the hierarchy's state.

Unit coverage exercises nested Domain/Codelist branches, collapsed and expanded restoration after
remount, workspace/application isolation, malformed or blocked storage, and continuation retry.
The App regression verifies the default mode and standalone hierarchy record navigation.

The [isolated Chrome navigation report](navigation-report.json) verifies actual storage across
reloads at 1440px and 390px for both navigation modes and branch choices, keyboard expansion, unchanged selected-record URL while collapsing,
and the existing collection/inspector and live/draft navigation journeys. No browser page errors.

Final frontend validation: format, lint (zero errors, 12 existing warnings), 144 tests in 28 files,
production build (existing large-chunk warning), and git diff whitespace validation passed.

Preferences are browser-local, not account-synced. Existing search/paging behavior is retained;
this change persists branch choices rather than fetched result pages. UI-07 remains deferred.

## Hierarchy record return correction

Records opened through Browse hierarchy no longer show Back to list, including error/retry states.
A history-entry marker preserves this behavior across reload and browser Back/Forward and when
following related records. Collection-origin records keep their return action; direct record links
keep their fallback collection return. Application and ancestor breadcrumbs remain explicit navigation.

Validation: 145 frontend tests passed, including two object types through error/retry, App navigation,
and router reload/history/related-record regression coverage. Format, lint (zero errors, 12 existing
warnings), build (existing chunk-size warning) and diff whitespace validation passed.

The [final isolated browser run](hierarchy-return-report.json) passed at desktop/mobile widths,
asserting absence of Back to list before and after hierarchy-record reload while the existing
collection return journeys pass. No browser page errors.
