# WP10 composed release validation — outcome

Baseline: `main`, `889f45b` (*docs: record ADR-028 draft model-version selection*). The worktree is
otherwise untouched: `git status --short` reports only the pre-existing untracked `review-notes/`,
and `git diff --check` is clean. **No commit was made and no application, test or configuration file
was modified.** This document is the single requested deliverable.

Authority: [WP10](../docs/BASE_0_6_IMPLEMENTATION_PLAN.md), [AGENTS.md](../AGENTS.md),
[project status](../docs/PROJECT_STATUS.md), [acceptance scenarios](../docs/product-functionality/ACCEPTANCE_SCENARIOS.md),
[WP9 browser regressions](../frontend/e2e/README.md).

## What WP10 asks for, and what this run found

WP10 is a composed release gate: it adds no feature scope, runs every required suite and publishes
the evidence. Six requirements apply. Five are met with direct evidence; one is deferred by an
explicit scope decision, not failed.

| WP10 requirement | Status | Basis |
| --- | --- | --- |
| 1. Real-backend/isolated-DB journeys: live CRUD without draft/revision, current-live bases, concurrency/delta merge, whole-graph atomic failure, live-only compatibility, pinned historical typing | **Met (suite level)** | 359 backend tests incl. lifecycle/concurrency; draft + history browser runners |
| 2. Two record types, ownership differences, non-default workspaces, empty/error/retry, deletion impact, availability vs deletion, **complete model-workbench save/check/install/activate** | **Partly met** | All browser journeys pass; **model workbench has no real-browser evidence** — the workbench *UI* exists and is 0.6 scope, only the browser run is missing |
| 3. Real-browser keyboard/focus/narrow layout **plus automated accessibility and visual checks**, recording screen sizes, browser version and manual AT coverage | **Deferred by decision** | Keyboard/focus/narrow pass with real evidence; automated a11y/visual tooling was never assigned a work package — now carried by UI-07 (see Failure 1) |
| 4. Clean bootstrap, preceding-revision and corrective legacy upgrades, restart, interrupted recovery or actionable refusal, **final smoke startup on configured DB** | **Met** | Migration/lifespan tests pass; the configured development database verified booting cleanly and serving readiness (see Failure 2) |
| 5. Wheel build/install with migrations on Python 3.14, OpenAPI inventory/digest, runtime/error contracts | **Met** | Wheel built, installed, digest reproduced exactly |
| 6. Record commit/worktree, data/config variants, commands/results, screenshots, failure outcomes, limitations, before/after flow | **Met** | This document |

Exit criterion: "all named invariants have direct integration evidence; no relevant skipped suite
counted complete; remaining gaps have explicit release ownership." Requirement 3 is deferred to UI-07
by decision rather than failed, and requirement 4 is met — the database failure originally reported
here was a defect in this probe, not in the product (Failure 2). One real gap remains: requirement 2's
model-workbench browser journey. That gap carries explicit ownership below.

## Environment and data/configuration variants

| Variant | Value |
| --- | --- |
| Python | 3.14.7 (`backend/.venv`), used for tests and the wheel |
| Node / npm | v25.2.1 / 11.6.2 |
| Browser actually exercised | **Google Chrome 152.0.7977.83** (system), via `PLAYWRIGHT_EXECUTABLE_PATH` |
| Viewports | 1440×1000 and 390×844 (history: 1440×1000 only) |
| Databases | one fresh isolated SQLite per browser runner; a fresh empty SQLite for bootstrap/restart; real configured development database `backend/rdm-engine.db`, probed **by copy only** for the smoke test |
| Launch directory | `backend/` — **this matters.** `DEFAULT_DATABASE_URL` is the relative `sqlite:///./rdm-engine.db` ([`config.py`](../backend/app/config.py)), so the database actually opened depends on the process working directory. See Failure 2. |
| Model variants | committed `model/rdm-starter.json` (`rdm-starter@0.6.0`, schema language 0.5) plus each runner's temporary starter variant |
| Install target | wheel installed into a clean prefix (`/tmp/wp10-install`), digest read from there, not from source |

The wheel was built to `/tmp` and the frontend check used `format:check` rather than `format`,
because the instruction was *no code change* and both alternatives write files.

## Gate results

### Static and unit gates

| Gate | Command | Result |
| --- | --- | --- |
| Backend lint | `backend/.venv/bin/python -m ruff check backend/app backend/tests` | clean |
| Backend tests | `backend/.venv/bin/python -m pytest backend/tests -q` | **359 passed, 0 failed, 0 skipped** (26.12s) |
| Frontend format | `npm --prefix frontend run format:check` | clean |
| Frontend lint | `npm --prefix frontend run lint` | **0 errors**, 12 pre-existing warnings |
| Frontend unit | `npm --prefix frontend run test` | **121 passed / 26 files** |
| Frontend build | `npm --prefix frontend run build` | success — `index-DYUD5lpX.js` 514.05 kB (gzip 152.69 kB) |
| Whitespace | `git diff --check` | clean |

The 12 lint warnings are all `react-hooks/set-state-in-effect`, deliberately left as warnings by
[`eslint.config.js`](../frontend/eslint.config.js); the worktree carries no frontend changes, so none
are new. The 136 pytest warnings are pre-existing SQLAlchemy/Starlette deprecations.

### Browser journeys — real backend, isolated data

Each runner starts its own Vite and FastAPI servers on temporary ports with a fresh SQLite database,
seeds through real APIs, and writes a `report.json` plus screenshots. All four exited 0 with
`pageErrors: []`.

| Runner | Checks | Viewports | Screenshots | Extra recorded |
| --- | --- | --- | --- | --- |
| `test:browser` (navigation) | 4 | 1440×1000, 390×844 | 3 | — |
| `test:browser:authoring` | 9 | 1440×1000, 390×844 | 2 | — |
| `test:browser:drafts` | 4 | 1440×1000, 390×844 | 2 | 15 canonical draft writes |
| `test:browser:history` | 4 | **1440×1000 only** | 2 | 19 historical reads |

Coverage reached: SC-01 navigation with typed filters, later-page retry/reload, detail retry, audit
and Back; SC-02/SC-03 and live SC-04 authoring with zero/false, concurrent correction, containment,
ordinary relationships, translation ownership, individual fields and signed deletion with
stale-preview refusal; SC-05/SC-06 drafts with current-live capture, aggregate and touched-record
conflict, invalid merged graph publishing nothing, discard and signed deletion; SC-08 newest-first
history, pinned-model typing, labelled historical derivation, publication retirement and catalogue
retirement as a separate read-only state. Keyboard/focus and narrow layout were exercised at 390×844
by the navigation, authoring and drafts runners.

Evidence directories (OS temporary, see Limitations): navigation `rdm-wp9-navigation-mRRGaY`,
authoring `rdm-wp9-authoring-B05DIj`, drafts `rdm-wp9-drafts-hARVkX`, history `rdm-wp9-history-P7oJzC`
under `$TMPDIR`. Nine screenshots total: `domain-retail.png`, `system-retail.png`,
`narrow-keyboard.png`, `deletion-impact.png`, `narrow-authoring.png`, `draft-narrow.png`,
`merged-graph-refusal.png`, `historical-snapshot.png`, `publication-retired.png`.

### Migration / lifespan

The 359 backend tests include `test_migrations.py` (12) and `test_startup.py` (2), covering fresh
provisioning, interrupted-run DDL recovery, refusal on unknown partial DDL, current-live base
preserving drafts, Base 0.5 graph upgrade to one workspace revision with stable IDs, public-ID
upgrade, runtime-state adoption and rejection, mixed lifecycle refusal, duplicate legacy identity
rejection, audit-subject backfill, unknown legacy state rejection with counts, and lifespan boot and
restart.

Independently re-verified directly against a real SQLite file, on the correct readiness path
(`/health`):

```
fresh empty DB                                    -> health=200  {"status":"ok"}
                                                     (first boot and restart; zero startup errors)
copy of backend/rdm-engine.db  (cwd=backend/)      -> health=200  {"status":"ok"}, workspaces=200
```

The fresh database installed exactly one release (`rdm-starter 0.6.0`, hash `5088391fd53db617…`,
active) and adopted runtime state `(1, 1, 1)` on both boots. The configured development database
holds that **same** active release identity and hash, so it boots and serves readiness normally —
see Failure 2 for why an earlier run of this probe reported the opposite.

### Packaging and public contract

Wheel built from `backend/` with `.venv/bin/python -m pip wheel .` on Python 3.14.7:

- `/tmp/wp10-wheel/rdm_engine_backend-0.3.0-py3-none-any.whl` — 142,691 bytes,
  sha256 `8ec967262ba4767d1f58d394e2d065797afaa72937cc9158460a8d83439c50cc`
- contains all 12 migration revisions plus `env.py` and `script.py.mako` (the
  `app.migrations` package data ships correctly)
- installed into `/tmp/wp10-install` and the OpenAPI document read from the installed package
  reproduces the locked digest **exactly**: `46d6b98ddabb9087f27edfbeec32c0dcbf3318ab4947fac5929caad5496d81d7`,
  34 paths, 58 schemas — matching
  [`test_openapi_contract.py`](../backend/tests/test_openapi_contract.py) from a
  non-source location.

## Failure outcomes

**Failure 1 — no work package ever owned automated accessibility or visual tooling (deferred to
UI-07, not a release blocker).** There is no `axe`/`@axe-core`, `pa11y`, `lighthouse` or
pixel-comparison dependency anywhere in `frontend`, and no runner makes an accessibility assertion.
The repository *captures* screenshots and never *compares* them: because it depends on bare
`playwright` rather than `@playwright/test`, `toHaveScreenshot` is unavailable, and the 12
`page.screenshot()` calls in `e2e/*.mjs` write PNGs that nothing diffs.

This is a scoping gap, not a defect in the shipped product, and it is **not a release blocker**. The
forensics are recorded in [UI-07](frontend-redesign-2026-09-10/README.md): the
promise in [`FRONTEND_STRUCTURE_REFACTOR.md`](../docs/FRONTEND_STRUCTURE_REFACTOR.md) that "Base 0.6
WP6 adds the browser, accessibility and visual-regression gates" lost its owner when WP4 was rejected
and WP6 was redefined into backend persistence; ADR-023 declares those gates release gates without
naming an owner; and WP10's own header names "accessibility/visual checks" as a primary area in the
same paragraph that promises "no new feature scope hides in this gate" — requiring a suite that no
package was scoped to build. The capability is now carried by **UI-07**
(*Automated accessibility and visual-regression gates*), recorded as a **deferred optional
enhancement**: it is not the current priority, but it is scheduled in the package. Manual
assistive-technology coverage was also not performed, so there is nothing to record there.

**Failure 2 — this probe's own database finding was wrong (probe defect, withdrawn).** An earlier
version of this document reported that the configured development database "cannot boot" with
`Bootstrap model release identity conflict: rdm-starter@0.6.0 has different installed content`, and
recommended an operator re-bootstrap. **That finding was an artifact of where the probe was launched,
not a product problem, and it is withdrawn.**

`DEFAULT_DATABASE_URL` is the **relative** `sqlite:///./rdm-engine.db`
([`config.py`](../backend/app/config.py)), so the file actually opened depends on the process working
directory. The probe ran from the repository root and therefore opened a stale leftover
`./rdm-engine.db` (root level, Sep 6) still holding the superseded release content
`6c5dbc8c…` — the "installed 2026-09-06 09:02:36" timestamp originally quoted came from that file. The
application is launched from `backend/`, which opens the live `backend/rdm-engine.db`; its active
release is `rdm-starter 0.6.0` with hash
`5088391fd53db6172dd00775d49d3be0a669af889f4368ce4b6dc78d0a32c6ed` — **exactly** what the committed
[`model/rdm-starter.json`](../model/rdm-starter.json) compiles to today. Verified by booting both by
copy: the `backend/` database returns `health: 200 {"status":"ok"}` and `workspaces: 200`, while the
stale root-level file reproduces the conflict error. Same code, same app, opposite results, decided
solely by working directory.

The restart-and-test experience reported by the operator is therefore correct, and **WP10
requirement 4's final smoke startup on the configured development database is met.** No re-bootstrap
and no operator data action is needed; the invariant behaved exactly as designed, on a file that
should not have been consulted. The one residual item is a diagnostics nit, not a release defect:
a relative default URL silently resolves against the process working directory, so an application
launched from an unexpected directory can open an unintended database and report a confusing
release-identity conflict. Worth an explicit path, a startup log line naming the resolved database
file, or both. Diagnostic only; not scheduled.

**Failure 3 — Playwright's pinned browser is not installed (environment note, not a release
blocker).** Playwright 1.56.1 requests `chromium_headless_shell-1194`; this machine has revision 1200,
so all four runners failed with `Executable doesn't exist`. Resolved with the documented
`PLAYWRIGHT_EXECUTABLE_PATH` override. Every browser result above therefore reflects **system Chrome
152.0.7977.83**, not Playwright's bundled Chromium. This is a harness-environment mismatch with a
documented workaround; it affects neither the application nor the evidence obtained.

**Failure 4 — first browser attempt exited 1** because my wrapper constructed invalid npm script
names (`test:browserauthoring`). Corrected by passing the four script names explicitly; not a
product defect.

## Limitations

- **No automated accessibility or visual tooling exists yet** (Failure 1). There is no `axe`/
  `@axe-core`, `pa11y`, `lighthouse` or pixel-comparison dependency anywhere in `frontend`, and no
  runner makes an accessibility assertion. This is a **deferred optional enhancement** carried by
  UI-07, which supplies the tooling; running it as a composed release gate remains WP10's. It does not
  block this release.
- **Manual assistive-technology coverage: none performed.** No screen reader or other AT session was
  used, so the requirement to record actual AT coverage has nothing to record. Nothing here should be
  read as an accessibility-conformance claim.
- **The model workbench is not exercised in a real browser.** `wp9-history.mjs` reaches
  `/model-drafts` and `/model-runtime-state` only through its direct API helper, not the workbench UI.
  The workbench is covered only by `ModelWorkbench.test.tsx` and backend `test_model_lifecycle.py`,
  so requirement 2's "complete model-workbench save/check/install/activate" has no browser evidence,
  and the "installation alone must not select the model" assertion was not re-tested end to end here.
  This is **not** a deferred feature: the workbench UI is 0.6 scope and only its browser run is
  missing. The *redesign* of the workbench is what later releases own — structured authoring in 1.0,
  with information-architecture redesign and graph-canvas authoring explicitly not planned for 0.6.
- **History ran at one viewport only** (1440×1000); no narrow-screen pass, unlike the other three.
- **Browser evidence is ephemeral.** Each directory lives under `$TMPDIR` and is OS-cleaned; the
  links above may not resolve later. Making this durable needs a committed evidence location.
- Non-fatal build warning: one chunk exceeds 500 kB (514.05 kB). No functional impact.
- Documentation drift: the `eslint.config.js` comment says ten `set-state-in-effect` sites; the actual
  count is six.

## Before/after flow comparison

Before the ADR-026 correction, every reference-data edit was routed through a draft-and-release
ceremony and the browser exposed records read-only. After this baseline:

| Flow | Before | Now (evidenced) |
| --- | --- | --- |
| Ordinary edit | draft → validate → release | direct live save; creates **no** draft and **no** revision (authoring runner asserts this) |
| Coordinated change | the only path | *optional* current-live draft, delta-merged over live content with touched-record and whole-graph atomic refusal |
| Conflicting concurrent edit | last write wins | explicit conflict with current content shown and input preserved |
| Deletion | immediate | signed impact preview; stale dependent change refused without deleting |
| Past content | not reachable | newest-first immutable history under its pinned model; derivation labelled as derivation, not restore |
| Retiring a publication | withdrew data / read-only | removes only the designation; live data and history remain readable; catalogue retirement is the separate read-only control |

## Ownership of the remaining gaps

| Gap | Owner |
| --- | --- |
| Automated accessibility and visual tooling (requirement 3) — **deferred optional enhancement**; UI-07 supplies the capability, WP10 runs it as a composed release gate | UI-07 (build) → WP10 (gate) — not a release blocker |
| Recorded manual assistive-technology coverage | Unassigned; no AT session performed |
| Real-browser model-workbench journey incl. "installation alone must not select the model" (requirement 2). **0.6 scope, not deferred:** the workbench UI already exists — only a browser runner for it is missing, and WP10's header lists "browser harness" as a primary area. The *redesign* of the workbench is separate and later (structured authoring 1.0; information-architecture redesign and graph-canvas authoring explicitly not planned for 0.6). | WP10 / release owner |
| Narrow-viewport pass in the history runner; durable evidence location | WP10 |
| Diagnostics: relative `DEFAULT_DATABASE_URL` silently resolves per working directory (Failure 2) | Unassigned — diagnostic only, not a release defect |
| `eslint.config.js` comment drift (ten vs six) | Documentation owner |

Nothing in this document claims a test that was not executed. Prior green totals elsewhere in the
repository cannot close requirement 2's model-workbench browser journey, which has no real-browser
coverage. Requirement 3 is deferred by decision to UI-07 and is not a release blocker; requirement 4
is met — the configured development database boots and serves readiness, and the failure previously
reported against it was a defect in this probe (Failure 2), now withdrawn.
