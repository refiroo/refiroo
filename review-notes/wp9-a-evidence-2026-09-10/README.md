# WP9-A completion evidence — 2026-09-10

Implemented on `main` over `b38aadc`; changes are uncommitted. Existing review notes
were preserved. WP9-A is complete; WP9-B through D and WP10 remain open.

- Explicit workspace on object/relationship reads, including retry and conflict refresh.
- Cursor trail in collection URLs; query/page restoration across detail, parent,
  cross-application navigation, browser Back and collection reload.
- Workspace/query changes reset paging; old workspace content is hidden.
- Failed page reads retain successful content and retry the same continuation.
  Failed initial collection/panel reads do not masquerade as empty results.
- Explicit Back to list control; workspace labels remain visible.

Validation of final implementation:

| Command | Result |
| --- | --- |
| `backend/.venv/bin/python -m ruff check backend/app backend/tests` | Passed |
| `backend/.venv/bin/python -m pytest backend/tests -q` | 359 passed, 136 dependency/deprecation warnings, 25.13s |
| `npm --prefix frontend run format` | Passed |
| `npm --prefix frontend run lint` | 0 errors, 12 warnings at existing sites |
| `npm --prefix frontend run test` | 103 passed across 22 files, 6.06s |
| `npm --prefix frontend run build` | Passed TypeScript and Vite production build |
| `PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser` | Passed, Chrome 152.0.7977.83, zero page errors |
| `node --check frontend/e2e/wp9-navigation.mjs` | Passed |
| `git diff --check` | Passed |

The browser runner uses an isolated SQLite database and real API-seeded model/data.
Domain numeric and System date filters were exercised in Warehouse and Retail;
Domain/Codelist and System/System-value containment plus a cross-application link
were followed. It verified later-page failures and retry, initial detail failures
and retry, independent relationship failures and retry, empty translations, audit,
query/page restoration, browser Back, reload and workspace switching.

Screenshots and machine-readable browser results are stored beside this note.
Viewports: 1440x1000 and 390x844. The narrow check used the keyboard to operate
application navigation. This is bounded functional browser evidence, not a full
accessibility audit, assistive-technology pass or visual regression baseline.
The fixture adds two declarative typed fields without changing the production model.

Earlier browser attempts exposed harness issues (missing bundled browser, React
StrictMode duplicate reads and locator assumptions), which were corrected before
the passing run. No application failure was suppressed to obtain a passing result.

No backend implementation/public API changes, migration changes or commits were
made. WP10 packaging, release-wide accessibility/visual and composed CRUD/draft/
historical-publication acceptance are not claimed by this slice.
