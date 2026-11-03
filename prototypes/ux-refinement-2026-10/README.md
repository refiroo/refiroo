# refiroo · A calmer workspace

**Superseded for design review:** use the [real dev-data revision](../ux-refinement-dev-data/README.md)
and its [clickable prototype](../ux-refinement-dev-data/index.html). This first exploration used an
invented minimal dataset and does not establish feasibility for the populated development application.

Clickable UX exploration 01 · 26 October 2026

## Open the prototype

Open **[index.html](index.html)** in a browser. It works directly from disk, offline, with no build,
installation or server. On macOS, from the repository root:

```sh
open prototypes/ux-refinement-2026-10/index.html
```

Use made-up details in the sign-in preview. It does not authenticate or send information anywhere.
All edits live in memory in the current tab. Reloading restores the samples.

## Design proposal

**Refine the existing interface rather than replace it.** refiroo already has a coherent shell,
useful context indicators, a sound table/inspector workflow, reusable components and a restrained
visual foundation. The opportunity is to help people understand where they are, focus on their
current work, and complete everyday tasks with less visual and interaction overhead.

The preceding review inspected eight committed screenshots, current frontend source, and the
running sign-in screen at desktop and 390px. Authenticated screens were assessed through source
and committed screenshots; some screenshots predate current branding and Home. The findings are
design hypotheses, not results from user research or a complete live authenticated walkthrough.

| Priority       | Review finding                                                                                                                      | Proposed direction                                                                          | Demonstrated here                                                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| High           | Application, workspace, collection, view and record navigation compete for attention. A hierarchy view can repeat the sidebar tree. | Distinguish location, data context and view. Make the individual-record browser optional.   | One workspace rail, a compact data-context band, table/hierarchy tabs, collapsed record browser. The browser is omitted while the hierarchy is open.             |
| High           | Record headers spend space on repeated context, UUIDs and version numbers before useful content.                                    | Put the record name and working fields first; retain technical information in a disclosure. | Compact inspector and full-page record, with ID/version collapsed under Technical details and a copy action.                                                     |
| High on mobile | A wide table and stacked navigation/actions leave little first-screen working space.                                                | Offer a concise identity-first mobile presentation while keeping the full desktop table.    | At 760px and below: name, code and status in a list; selecting a record shows its details in place; navigation moves into a native dialog.                       |
| Medium         | Table values open a record while detail values edit it; users need cues to discover both.                                           | Make these two actions recognisable and retain keyboard alternatives.                       | Clear record links, an opening hint, labelled field edit buttons, visible pencils and explicit Save/Cancel. Editing occurs in a small dialog for this prototype. |
| Medium         | The live sign-in fields looked comparatively small and plain, with no password visibility control.                                  | Improve control sizing, spacing and password visibility without adding clutter.             | Branded sign-in preview with 46px fields, Show/Hide and a password-reset preview.                                                                                |
| Medium         | Some sign-in failures expose settings such as `CORS_ORIGINS` to ordinary users.                                                     | State what happened and the next safe action; keep configuration detail in diagnostics.     | Wording direction documented below. A deployment failure is not simulated.                                                                                       |

Visual direction: warm neutral surfaces, the existing Instrument Sans family, restrained indigo
actions, smaller coloured type tiles and a clear hierarchy of title, working content and metadata.
Green, amber and violet still describe Live, Change set and Publication. Brand colour never replaces
the meaning of those states. Dark appearance is available from the moon button.

Example sign-in failure wording: “Sign-in isn't configured for this address. Contact your
administrator and share the page address.” Controlled diagnostic detail can name the setting.

The approach follows [recognition over recall](https://www.nngroup.com/articles/recognition-and-recall/)
and [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/).

## Suggested walkthrough

1. Start in **Delivery methods**. Search for `home`, then clear the search. Press **Status** to toggle
   active-only filtering. Click the **Name** heading to reverse sorting.
2. Open **Home delivery**. Edit Code or Description, save, and see the updated table, version and
   sample activity. Cancel an edit or use Escape to leave it unchanged.
3. Expand **Technical details** to see and copy the ID. Use the inspector's expand button for the
   full-page record; return with **Back to delivery methods**.
4. Follow **Commerce platform** under **Used by**. The same record presentation renders a second
   object type, with its own labels and sample fields. Navigate back through its related record.
5. Choose **Hierarchy**. There is one hierarchy, without a second record browser in the rail.
   This is a shallow grouping preview, not an implementation of the engine's hierarchy editor.
6. Switch the context to **Change set · Autumn tidy-up**, edit a field, and open **Review changes**.
   Switch to Live to confirm its sample data did not change. **Publication #12** has no edit/add
   actions and retains its own snapshot.
7. Add a record with the primary button. Required fields and duplicate codes are checked. The
   download icon exports the currently matching sample records as CSV.
8. Open Home through the refiroo mark. Try **Continue where you left off** and both collection cards.
9. Open the **AM** account button and **Preview sign-in**. Use Show/Hide, the reset preview and
   made-up credentials to return to Home. Nothing is authenticated or mailed.
10. Resize to **390 × 844**. Open the navigation drawer, choose either collection, open a record,
    edit a field and return to the list. Try the same operations by keyboard.

## Scope and boundaries

- Everything is isolated in this directory. No application source, route, model, API, data or
  canonical functionality document is changed. The prototype is a proposal, not shipped behavior.
- Both sample types use one configuration-driven renderer. Their example domain does not define
  the capabilities of any refiroo application.
- This is plain HTML/CSS/JavaScript so it can be opened independently. It references the current
  `ShellFrame`, `TopBar`, `DataContextBand`, `ObjectTable`, `ObjectDetail`, `Modal` and `EmptyState`
  patterns conceptually; it does not duplicate them into the production frontend. A production
  implementation must modify/reuse those shared React components and the existing tokens.
- The Home/Reference data top navigation is a one-application example. Application switching,
  workspace switching, administration, permissions, approvals and model authoring are outside scope.
- The prototype simplifies view controls and the mobile collection. It does not implement Display,
  full mapping, full hierarchy operations, cursor windows, bulk actions, backend validation,
  concurrency, migrations, asynchronous jobs or publication. These capabilities are not proposed
  for removal from refiroo. API-first behavior and model-defined views remain requirements.
- The change-set review is a list of in-memory edits, not a semantic diff or publish implementation.
  Activity, account identity and snapshot date are labelled samples. Authentication and reset are
  navigation previews only. Reload discards all edits and appearance choices.
- Composable-domain doors (ADR-032): unaffected. No identity, attribute storage, audit/history,
  bulk API, consumer `match` declaration or mapping-coverage contract changes are made.
- Native `<dialog>` supplies focus containment and Escape in this standalone experiment. A real
  implementation must use `ui/Modal`; the prototype is not a replacement component library.
- Fonts and brand assets are local copies. The Instrument Sans licence is in
  [assets/FONT-LICENSE.txt](assets/FONT-LICENSE.txt). No external services, analytics or dependencies
  are loaded. The CSV export includes only the fabricated records displayed here.

## Acceptance and state inventory

This is a bounded prototype check, not production UI acceptance. The reference patterns are the
existing shell/context band, collection table, inspector, disclosure, field, dialog and empty state
in [UI_ACCEPTANCE.md](../../docs/testing/UI_ACCEPTANCE.md#1-reference-patterns).

| Surface                               | Applicable states and checks                                                                                                              | Not modelled                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Collection, both types                | Populated, search, filtered empty with recovery, active filter, sorting, selected record, add, duplicate-code refusal, export, 390px list | Loading and network failure: no network; cursor paging and volume: small static dataset |
| Inspector and full record, both types | Open/close, relationship navigation, edit/save/cancel, required value and duplicate code refusal, technical disclosure, keyboard focus    | Pending and conflict: no asynchronous writes or concurrency                             |
| Data context                          | Live and draft edits isolated; review summary; publication read-only                                                                      | Validation, approval and publish: no engine connection                                  |
| Home and navigation                   | Collection cards, continue, drawer, light/dark                                                                                            | Permission variants, multiple workspaces and applications                               |
| Sign-in preview                       | Larger controls, password visibility, reset acknowledgement, entry to Home                                                                | Real identity, session, MFA, provider and operational failure                           |

Production accessibility, visual regression and real-backend journey gates are not run for this
independent mock-up.

## Verification record · 26 October 2026

Functional evidence: focused Playwright scripts opened the prototype directly from disk in
headless Google Chrome at **1440 × 1000** and **390 × 844**. The following passed:

- Search, active-only filtering and name-sort reversal on both object types; filtered-empty
  recovery; downloading the sample CSV.
- Record opening, full-page expansion/return, related-record navigation and an edit on each type.
- Field save, duplicate-code refusal, Cancel, Escape and focus restoration. Add-record flow on
  the second type. Required fields use native browser validation; exhaustive validation variants
  were not exercised.
- Independent Live/change-set/snapshot values, draft review, and no Add/Edit controls in a
  publication.
- Hierarchy selection without the duplicate sidebar browser and arrow-key view-tab switching.
- Phone navigation and both record types without page-level horizontal overflow; phone editing
  entirely by keyboard; native dialog Escape/focus restoration and no focus on background controls.
  Native dialogs may temporarily move focus into browser chrome during Tab traversal.
- Home/Continue navigation, password visibility, reset acknowledgement and mock sign-in entry.
- No uncaught browser errors during the main walkthrough.

Accessibility evidence: focused axe-core checks reported **zero automated WCAG A/AA violations**
for the desktop inspector, the second object type, dark inspector, phone collection, phone
inspector, sign-in and dark phone sign-in. These checks are not a complete accessibility audit or
screen-reader evaluation. The contrast of the prototype badge and the mobile Add button's
accessible name were corrected during verification.

Visual evidence: the screenshots below were manually inspected for hierarchy, readable content,
clipping, spacing and the mobile presentation against the existing reference patterns. They are
review artefacts, not committed regression baselines. The samples include edits made during the
walkthrough; opening the prototype starts with the original sample data.

| Screen                      | Screenshot                                  |
| --------------------------- | ------------------------------------------- |
| Collection, desktop         | [01](screenshots/01-collection-desktop.png) |
| Record inspector, desktop   | [02](screenshots/02-inspector-desktop.png)  |
| Single hierarchy            | [03](screenshots/03-hierarchy-desktop.png)  |
| Change-set context          | [04](screenshots/04-change-set-desktop.png) |
| Home, desktop               | [05](screenshots/05-home-desktop.png)       |
| Second type, dark inspector | [06](screenshots/06-inspector-dark.png)     |
| Collection, phone           | [07](screenshots/07-collection-phone.png)   |
| Record inspector, phone     | [08](screenshots/08-inspector-phone.png)    |
| Sign-in, phone              | [09](screenshots/09-sign-in-phone.png)      |
| Sign-in, desktop            | [10](screenshots/10-sign-in-desktop.png)    |
| Home, phone                 | [11](screenshots/11-home-phone.png)         |

Static commands, from the repository root:

```sh
node --check prototypes/ux-refinement-2026-10/prototype.js
frontend/node_modules/.bin/prettier --check prototypes/ux-refinement-2026-10/index.html prototypes/ux-refinement-2026-10/styles.css prototypes/ux-refinement-2026-10/prototype.js prototypes/ux-refinement-2026-10/README.md
git diff --check
```

Browser checks used disposable Node/Playwright scripts and the installed Google Chrome executable;
no test infrastructure or production tests were added. No server or database was started. Temporary
browser processes were closed. Full application lint/build/test suites were not required because
the production frontend was not modified.

## What to decide from this prototype

Compare finding a record, correcting a value and following a relationship against the current app.
Evaluate both object types, desktop and mobile. Check whether users can explain which data they
are changing before they save. Prefer an incremental delivery only if those tasks become clearer.

Likely implementation order: compact record header and metadata disclosure; collection/mobile
presentation and optional record browsing; sign-in polish. Keep that work separate from engine
changes and validate each implemented surface through the existing acceptance process.
