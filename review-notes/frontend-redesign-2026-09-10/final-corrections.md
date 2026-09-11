# Final corrections — 2026-09-11

- Views records now use the full-width detail layout used by hierarchy records. The collection
  stays hidden and retains its return state. Back to list remains for collection navigation.
- Browse hierarchy appears first, defaults on the first visit, and remembers the chosen mode.
  Branch expansion/collapse is stored per workspace/application. Hierarchy records omit Back to list.
- Unconfigured detail views now derive child tables and incoming/outgoing relationships from the
  active model. System groups and Translation groups therefore expose their nested content and
  relationships, with properties and hierarchy in the side region. Explicit detail configurations
  remain authoritative. No starter-key branches or backend/model changes were introduced.

Validation: frontend formatting, lint (zero errors, 12 existing warnings), and production build
passed. The full 146-test run exposed two stale last-request assertions after child-panel requests
were introduced; these now verify the collection request independently of child requests and the
App suite was rerun. The other 27 test files passed. Focused fallback model/component coverage
checks child parent filtering and relationship loading.

Earlier browser evidence remains scoped to its recorded version. The latest full-width browser
run completed live Domain/System and Domain draft journeys, then stopped at a viewport-transition
width assertion. The assertion now waits for layout to settle; the full browser matrix was not
repeated, following the user's request to avoid redundant retesting. Final group changes have
component coverage, not a new real-backend browser run. UI-07 remains deferred.
