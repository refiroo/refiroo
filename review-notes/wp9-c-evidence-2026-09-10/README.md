# WP9 slice C completion evidence — 2026-09-10

Implemented on the existing uncommitted slice A/B tree. No commit requested or created.

## Delivered

- Explicit current-live draft creation, source labels, cursor-paged draft discovery and Live/Drafts routes.
- Pinned draft model, shared canonical record/field/relationship/translation controls and lookups.
- Aggregate tokens from the draft resource, preservation of entered fields after aggregate/record
  conflicts, explicit retry, and truthful recovery when a save succeeds but token refresh fails.
- Whole-draft validation, reviewed-version activation confirmation, per-record/graph conflict feedback,
  publication result, discard confirmation and return to independently editable Live.
- Signed draft deletion and stale-preview recovery across containment/ownership cases.

## Validation actually run

- Focused adapters, draft aggregate controller, routes and app tests: **33 passed** at that iteration.
- Final frontend suite: **114 passed across 24 files**, no skips.
- Frontend formatting passed; lint: **0 errors, 12 existing warnings**, no added warning sites.
- Production build passed. A TypeScript error in two new test-query options was corrected;
  the build was rerun. Those unsupported options had no runtime matching effect. The passing
  application test suite and lint were not unnecessarily repeated.
- Build reports a 505.53 kB main chunk warning; no bundling/configuration scope was added.
- `git diff --check`, package JSON syntax and changed documentation link checks passed.
- Real-browser SC-05/SC-06/draft SC-04: **passed**, Chrome 152.0.7977.83, 1440×1000 and 390×844,
  **15 canonical draft mutations**, zero page errors. See [report](report.json),
  [merged-graph refusal](merged-graph-refusal.png) and [narrow draft view](draft-narrow.png).

Reproduce from the repository root:

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:drafts
```

The browser runner starts temporary Vite/FastAPI processes and seeds a fresh temporary SQLite
store through actual APIs. It never uses the configured development database. Initial attempts
resolved sandbox local-port permissions, unavailable bundled Chromium and fixture selectors;
the uniqueness case was corrected to use the starter's existing unique Domain code. No failing
attempt is counted as acceptance evidence. The final complete run passed all named checks.

## Evidence boundary

E1: named browser tasks passed with real APIs, including no-publication and post-publication bases,
atomic translation ownership, staged invisibility, preserved unrelated live work, touched-record
refusal, merged-graph refusal, and stale signed deletion previews. Two object types and Master/System
containment are exercised; translation deletion follows its owned target while independent System
records remain. Browser navigation/reload retain draft identity; cancellation and narrow focus work.

E2: direct frontend adapter/controller/app regressions cover propagation, aggregate-resource tokens,
non-replayed conflicts and successful-save/failed-refresh recovery. The real backend run exercises
existing endpoints; backend code/public contracts were unchanged, so backend unit, migration and
wheel suites were not rerun.

E3: immutable history and historical source selection remain slice D. Full accessibility/visual
regression and composed release, multi-session, migration/lifespan and installed-wheel evidence
remain WP10. This slice does not claim completion of all WP9 or release 0.6.
