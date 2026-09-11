# UI-03A — Navigation preservation

Completed 2026-09-11 on the existing UI-01/UI-02 working tree, following the user's approval of
UI-03A as an independent slice. No commit created. UI-03B (inspector/actions) and UI-07 remain deferred;
UI-03 as a whole is not complete.

## Delivered

- Each record history entry retains its originating collection URL, including typed filters, search,
  sort, page size and cursor trail. Related records retain that origin across applications within
  the same workspace/draft/revision context. Reload and Back/Forward restore the entry's own origin.
- Browser-owned origin state is validated against the model, route and data context. Copied record
  URLs and invalid/obsolete origins use the existing full detail page and matching collection return.
  Workspace changes clear incompatible origin/continuation; refused navigation does not change
  remembered workspace state.
- Record, attribute-value and relationship editors protect dirty input on router navigation and
  native unload. Cancelled Back/Forward restores the record URL and retains editable input; explicit
  discard permits navigation. Lookup selections also mark their form dirty.
- In-flight editor and record-deletion requests refuse router navigation with an explanation.
  Successful writes release their guard before calling completion/navigation handlers; failures keep
  input protected. Existing coherent forms, concurrency reconciliation and signed deletion remain.
- No backend, API, model or persistence-contract changes. No inspector, selection UI or action menu
  was introduced in this slice.

## Validation

After the final frontend source changes, from `frontend/`:

- `npm run format` — passed.
- `npm run lint` — zero errors, 12 existing warnings; no new warning sites.
- `npm run test` — **27 files, 135 tests passed**.
- `npm run build` — passed; existing >500 kB bundle warning (522.79 kB JS).
- `git diff --check` — passed.

Focused tests cover per-entry origins after remount/history, live/draft context separation, corrupt
origins, copied links, multi-entry Back, refused Forward, busy/native unload protection, successful
save navigation and failed-save input preservation. App tests exercise reload/return with Domain
and Codelist detail/parent paths.

Chrome **152.0.7977.83**, isolated SQLite databases and temporary Vite/FastAPI servers:

- `test:browser` — passed, no page errors. [Navigation report](navigation-report.json).
  Domain/System in Live and Draft at **1440×1000** and **390×844**: filtered later-page return after
  record reload, Back/Forward cancel/discard, native reload cancellation, retained editable input,
  delayed real save protection, and cross-application related-record reload/return. Existing two-
  workspace, retry, typed-filter, hierarchy and 720px reflow checks also pass.
- `test:browser:authoring` — passed, no page errors. [Authoring report](authoring-report.json).
  Real creation, coherent/individual edits, parent/relationship/translation writes, conflict
  reconciliation, focus restoration, retirement and signed/stale deletion review remain functional.
- `test:browser:drafts` — passed, no page errors, 15 canonical draft writes.
  [Draft report](drafts-report.json). Two-type draft editing, publication preserving unrelated live
  work, record/aggregate conflicts, invalid merged-graph refusal, discard and signed deletion pass.

Commands used `PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'`
with `npm --prefix frontend run <runner>`. Local-server execution required sandbox escalation after
`listen EPERM`; configured development data was not accessed. Runner fixes addressed Playwright
waiting for a deliberately cancelled reload, an omitted draft sort in the fixture URL, and an
immediate assertion before asynchronous focus restoration. Final behavior assertions remain intact.

## Representative screenshots and limits

- [Desktop retained live input](ui03a-domain-live-1440-retained.png)
- [Mobile retained live input](ui03a-domain-live-390-retained.png)
- [Desktop retained draft input](ui03a-system-draft-1440-retained.png)
- [Mobile retained draft input](ui03a-system-draft-390-retained.png)
- [Restored live collection](ui03a-domain-live-restored.png)
- [Restored draft collection](ui03a-system-draft-restored.png)

Representative desktop/mobile screenshots were visually inspected. This is bounded Chrome interaction
evidence, not an accessibility audit or visual-regression baseline. Native unload prompts depend on
browser support/user interaction; form input is not persisted. Older history entries without origin
metadata cannot recover a missing original query and use the collection fallback. UI-03B, UI-07 and
WP10 remain open. Model-admin editing and draft-name forms were outside this record-navigation slice.
