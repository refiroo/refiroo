# NAV-GROUPS screenshots and findings

## Capture afterwards from the Graubünden reference instance

- `model-navigation-group-panel.png`: model editor, group selected; show a collection and the Municipalities by system relation matrix, all Entries columns, a collection opening view and the matrix's Itself, plus Add to group…, Rename… and the starting-state button.
- `model-group-add-entries-dialog.png`: Add to group… dialog with a collection and a matrix ticked, Search collections and matrices, current-location notes and Add with its selected count. Include a selected entry moving from another group if the reference configuration permits it.
- `app-navigation-matrix-entry.png`: application sidebar with the group expanded, Municipalities by system as a named matrix entry in its row type's colour, and the row collection still present. Open the matrix so its entry is highlighted.
- Refresh `model-application-groups.png` for the application's Navigation groups table: Entries now lists both collections and matrices, group names open their panels, and In no group: offers Add to a group… when applicable.
- Review existing `model-group-menu.png` and `model-application-panel.png` against the current reference instance; this wave did not capture or inspect images. Other existing screenshots on these pages are unchanged.

## Evidence and limits

Read guide/AGENTS.md and the wave brief first. No previous wave progress or steering file existed. Checked current frontend ElementPanel.tsx, operations.ts, outline.ts, OperationDialog.tsx, model/collections.ts, Explorer.tsx and NavigationGroupPage.tsx; checked docs/APPLICATION_MODEL.md Navigation groups, relevant docs/API.md operations, CHANGELOG.md and backend remove_navigation_group.

Opens on is editable only when a collection has several views. Choosing the natural fallback clears its separate choice. The fallback is the application default if it belongs to the collection, then its table, then its first view. A matrix entry opens itself. Taking an entry out and removing its group preserve the views and records.

The group page search includes matrix names but its placeholder and empty messages still say collection. The Remove group confirmation only explains collections returning to the sidebar and omits matrices losing their separate entries. The pages quote existing labels and explain both outcomes; these are wording gaps, not unverified claims of behavior.

No browser run or screenshots were produced; the wave calls for later reference-instance capture. The coverage checker writes _coverage/inventory/uncovered.md by default, outside this wave's allowed edits. Run it with the local coverage-output.cjs preload to redirect only that generated report into these notes; its coverage logic and exit status are unchanged.

## Validation

- `GUIDE_OUT=_build/NAV-GROUPS npm run build` in `guide/`: passed, 253 pages, 5.13 seconds. Output: `build.log`.
- `NODE_OPTIONS="--require=$PWD/_coverage/notes/NAV-GROUPS/coverage-output.cjs" npm run check:coverage` in `guide/`: passed, 911 entries, 902 covered, 9 excluded, none uncovered. Output: `coverage.log`; generated report: `uncovered.md`. The shared inventory report was not written by this run.
- `npm run check` in `guide/`: passed terms and brand checks across 253 pages. Output: `static-checks.log`.
- Checked local page-link targets from the four assigned files and exact presence of all seven requested operation ids plus the opening-view model path in both documentation-page comments.
- No screenshot capture, browser acceptance or whole-site link check was performed. Three intentional new screenshot references are placeholders for later capture. No outstanding uncertainty about the documented behavior was found in the inspected execution paths.
