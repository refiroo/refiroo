# WP9-B completion evidence — 2026-09-10

Slice B implements direct live authoring on top of the existing uncommitted slice A.
The slice A changes and unrelated review notes are preserved. No commit was requested or made.
No backend implementation, public API contract, schema or model source was changed.

## Delivered behavior

- Reachable generic collection Add, detail Edit/Delete, child creation, individual fields,
  ordinary relationships and translations. Catalogue retirement makes them read-only.
- One edit form covers name, parent and writable typed fields. Saves preserve zero/false.
  Conflict feedback shows current saved content beside preserved input. Explicitly edited
  fields compare against the refreshed version; untouched fields preserve concurrent work.
- Required parent/target connections are sent in one object-create request. Validation
  failures retain input and leave no incomplete translation.
- Deletion first confirms the root request, then displays any returned dependency impact.
  Cascade confirmation sends only the exact displayed signed token. A stale preview is
  refused; retry requires a fresh displayed impact and another explicit confirmation.
- Field and relationship forms retain input, show current values on conflicts and guard
  busy/dirty dismissal. Optional field removal remains distinct from record deletion.

## Validation

E1: [real-browser report](report.json), Chrome 152.0.7977.83, isolated SQLite database,
1440×1000 and 390×844. Run from the repository root:

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:authoring
```

The successful final run exercised SC-02/SC-03 and live SC-04 through the real backend:
Domain/System root creates and conflicting edits; zero/false and availability filtering;
Master/System child containment and parent moves; ordinary relationship add/edit/delete
with a typed-value conflict; translation creation from both target and group using two
target types; missing-content and duplicate rejection without partial records; individual
field add/edit/remove and last-meaningful-content refusal; deletion cancellation and stale
dependent-change refusal; fresh signed confirmation and preservation of independent
System and Translation hierarchies. It verified no drafts/revisions were created and
catalogue retirement removed tested mutation controls. No browser page errors occurred.

Keyboard checks opened Edit with Enter, verified focus containment and restoration,
cancelled with Escape, and checked no horizontal page overflow at 390×844. Screenshots:
[narrow form](narrow-authoring.png), [deletion impact](deletion-impact.png).

E2: The E1 runner also read the real API after writes to check persisted types, parents,
relationships, rejection atomicity, deleted/retained records and absent drafts/revisions.
Standalone backend pytest/Ruff, migration and packaging gates were not run: this slice
changed no backend or public contract.

E3 and final frontend gates:

| Check | Result |
| --- | --- |
| `npm run format` | Passed |
| `npm run lint` | 0 errors, 12 existing warnings; [log](lint.log) |
| `npm run test` | 23 files, 108 tests passed; no skips; [log](tests.log) |
| `npm run build` | Passed; [log](build.log) |
| `git diff --check` | Passed |

New component regressions cover complete typed forms, explicit original-value restoration
after conflicts, preserving unrelated concurrent values, authoring/read-only details for
two object types, signed deletion confirmation, cancellation and stale-preview retry.
The app retirement assertions now name the actual Add/Edit controls.

During iteration the browser fixture was corrected to supply the required Master ID and
avoid reading a 204 response body. The build found and prompted removal of an unsupported
Testing Library role-query option. Following the final reconciliation correction, the
frontend gates and real-backend browser journey above passed. No independent agent review
or unrelated application test suites were run.

## Remaining evidence boundaries

- E1: slices C/D (draft/history) and WP10 composed release, full accessibility and visual
  acceptance remain open. This is bounded live authoring evidence, not WP9 completion.
- E1/E2: the browser verified missing-content and duplicate-target rejection; it did not
  forge a disallowed target payload or exhaust every model validation rule. Candidate
  types are derived from permitted model relationships. Standalone backend suites were
  not refreshed in this frontend-only slice.
- E3: component evidence covers the changed paths; it does not replace E1 acceptance for
  future draft/history journeys.

The temporary database remains at the path in report.json. Review notes intentionally
remain visible and untracked.
