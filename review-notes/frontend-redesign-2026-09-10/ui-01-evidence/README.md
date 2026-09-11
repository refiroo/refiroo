# UI-01 completion — 2026-09-10

Implemented and verified on the working tree based on `889f45b`; no commit created.
Existing untracked review notes were preserved. Backend, APIs, model and persistence are unchanged.
WP9-D was already implemented at execution time; its History navigation remains available.

## Delivered

- Compact white header, 248px neutral sidebar (previously 328px), restrained green selection,
  quieter type and surfaces. Main horizontal padding is 28px instead of 40px: at 1440px,
  the content area gains 104px. Existing configured detail composition and breadcrumbs remain.
- Workspace and application selectors above vertically arranged configured views. Models has a
  separate secondary entry. Information discloses the model version and schema, including the
  pinned version while inspecting a historical snapshot.
- One compact location trail in the shell, with Live, named Draft or historical context. The page
  supplies its own heading. Redundant explorer title/type chips and shell context explanation removed.
- Views/Browse hierarchy switch retains the explorer's search, loaded pages and retry behavior.
- At 760px and below, navigation uses the existing Modal focus/dismissal contract. A persistent
  portal host moves the same navigation tree between sidebar, hidden storage and drawer, preserving
  its state across opening, closing and viewport changes. Close, Escape and touch are exercised.

## Validation

Commands run from the repository root (equivalent to running the package scripts in `frontend/`):

```sh
npm --prefix frontend run format
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:authoring
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:drafts
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:history
git diff --check
```

- Format passed. Lint: zero errors, 12 existing hook warnings; no warning introduced in the new wrapper.
- Tests: 26 files, 121 tests passed, no skips. Focused App tests also passed during iteration.
- Production build passed; Vite warns about the 514.31kB minified JavaScript chunk (152.87kB gzip).
- All four isolated browser runners passed with zero page errors; Chrome **152.0.7977.83**.
- Navigation covers Domain/System, Warehouse/Retail, live and existing named drafts; later-page
  filters/retry/reload/Back, explorer continuation across mode changes, all configured Master/System
  views, mobile touch/keyboard drawer operation, focus restoration, search retention, model
  administration and no page-level horizontal overflow at 390px.
- Authoring and draft runners retain typed writes, concurrency recovery, signed deletion,
  confirmation dialogs and publication behavior. History verifies the pinned version through
  Information and preserves immutable reads, historical derivation and retirement.
- Browser databases and test model variants were created in system temporary folders. The
  configured development database was not used. Local server startup required sandbox escalation.
- Initial browser failures were test-selector assumptions: hidden explorer text and the old
  permanent version chip. Selectors now target the visible collection and Information disclosure.
- Changed browser scripts passed Node syntax checks. Final diff and documentation links checked.

## Reports and representative screens

- [Navigation report](navigation-report.json), [live authoring report](authoring-report.json),
  [draft report](drafts-report.json), [history report](history-report.json).
- Desktop records: [Domain](domain-retail.png), [System](system-retail.png).
- Mobile live collections: [Domain](mobile-domain-live.png), [System](mobile-system-live.png).
- [Mobile hierarchy drawer](narrow-keyboard.png).
- Named drafts: [desktop System](desktop-system-retail-draft.png),
  [mobile Domain](mobile-domain-retail-draft.png).
- Model administration: [desktop](desktop-models.png), [mobile](mobile-models.png).
- [200% layout-equivalent navigation](zoom-equivalent-navigation.png).

## Evidence limits

Navigation viewports were 1440×1000, 390×844 and 720×500 CSS pixels. The last checks the layout
viewport equivalent to a 1440px browser at 200% zoom; no native browser zoom-setting or manual
assistive-technology session was performed. Screenshots were visually inspected, not compared
against automated visual baselines. History's existing runner is desktop-only; navigation, live
and draft runners cover mobile. This package does not establish full accessibility compliance,
UI-07 visual/accessibility gates, a model-workbench redesign or composed WP10 release acceptance.

Next package per the plan: UI-07, followed by UI-02.
