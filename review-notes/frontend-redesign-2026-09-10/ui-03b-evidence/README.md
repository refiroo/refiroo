# UI-03B completion — 2026-09-11

UI-03B is complete. Selecting a record through Browse hierarchy opens its full record view,
with its own properties and configured panels. It clears the previous collection origin, so
an unrelated domain/codelist collection does not remain in the middle. Reload preserves this
behavior. This corrects the regression reported during implementation.

Collection-row selection opens the shared record detail beside the collection above 1080px.
Expand opens full detail; Back to list restores the collection, query, page and selected-row focus.
Narrow screens show one record screen. Properties/supporting panels precede main panels when
stacked, while wide full detail retains the model's main and side regions. All configured panels
remain available, with order preserved inside each region.

The shared action menu supports Edit all fields, Copy link and Delete record from visible triggers,
keyboard and right-click. Existing forms, conflict handling and signed deletion previews remain in
use. Saves refresh collection content; deleting the last record on a later page recovers to the
preceding page. Dirty edits guard selection/close/history changes. Read-only records expose no
mutation menu actions. Runtime rendering remains generic; no API or model-contract changes.

## Validation

- `npm run format`: passed.
- `npm run lint`: zero errors; 12 existing warnings, no added warning sites.
- `npm run test`: 28 files, 141 tests passed.
- `npm run build`: passed; existing large-chunk warning (537.22 kB JavaScript).
- `git diff --check`: passed.

All four isolated browser runners passed against the final frontend with Chrome 152.0.7977.83
and temporary SQLite databases. Reports contain no browser page errors:

| Runner | Evidence and exercised scope |
| --- | --- |
| Navigation | [Report](navigation-report.json): Domain/System in Live/Draft, filtered later-page selection, expansion, close, reload, Back/Forward, cross-application and workspace navigation, query changes during inspection, save refresh, row/menu keyboard behavior, clipboard, retained panels, deletion page recovery, and hierarchy-to-value regression. Viewports include 1440×1000, 390×844 and 720×500. |
| Authoring | [Report](authoring-report.json): real creates/edits, typed zero/false, conflicts, fields, containment, relationships, translations, keyboard/focus and signed/stale deletion previews. |
| Drafts | [Report](drafts-report.json): isolated draft edits and aggregate conflicts, activation preserving unrelated live changes, publication refusal, discard, containment deletion and narrow confirmation focus. |
| History | [Report](history-report.json): pinned immutable reads, historical draft derivation, publication retirement and catalogue read-only behavior. |

The history runner's revision-card selector now matches its heading, avoiding collisions with
revision references elsewhere in a card. Only successful final runs are included here.

## Screenshots

- Reported hierarchy regression: [desktop value](ui03b-hierarchy-value-1440.png), [mobile value](ui03b-hierarchy-value-390.png).
- Collection selection: [Domain inspector](ui03b-domain-live-inspector.png), [full detail](ui03b-domain-live-full.png), [mobile detail](ui03b-domain-live-390-record.png).
- Second structure and draft context: [System inspector](ui03b-system-draft-inspector.png), [mobile](ui03b-system-draft-390-record.png).
- Actions and recovery: [row menu](ui03b-domain-live-row-menu.png), [last-row deletion](ui03b-domain-deleted-last-row.png).

Desktop/mobile hierarchy screenshots and the desktop inspector were visually inspected. These are
bounded journey checks, not whole-release acceptance. UI-07 and composed WP10 accessibility/visual
acceptance remain deferred. Inline editing and persistent/resizable layouts remain separate packages.
No commit was created; existing unrelated working-tree changes were preserved.
