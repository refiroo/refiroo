# D-USE report

Reviewed all 68 Use documentation pages and task guides. Changed 26 pages,
including two new pages: `use/copying-and-moving.md` and `guide/use/copy-or-move-records.md`.
Word counts use whitespace-separated words including front matter, captions and link targets,
consistently before and after. Section total: **49,229 → 52,023 words**.

## Pages written or changed

| Page (relative to guide/) | Before | After |
| --- | ---: | ---: |
| `src/content/docs/guide/use/add-a-record.md` | 289 | 317 |
| `src/content/docs/guide/use/change-how-refiroo-looks.md` | 197 | 227 |
| `src/content/docs/guide/use/continue-an-assistant-task.md` | 775 | 820 |
| `src/content/docs/guide/use/copy-or-move-records.md` | 0 | 429 |
| `src/content/docs/guide/use/correct-a-record.md` | 913 | 929 |
| `src/content/docs/guide/use/delete-many-records.md` | 247 | 255 |
| `src/content/docs/guide/use/edit-in-excel-and-import-back.md` | 303 | 338 |
| `src/content/docs/guide/use/follow-and-cancel-a-job.md` | 246 | 276 |
| `src/content/docs/guide/use/import-a-file.md` | 346 | 381 |
| `src/content/docs/guide/use/load-the-next-version-of-a-workbook.md` | 519 | 647 |
| `src/content/docs/guide/use/prepare-and-publish-a-change-set.md` | 985 | 1,092 |
| `src/content/docs/guide/use/set-up-email-notices.md` | 256 | 272 |
| `src/content/docs/use/account.md` | 1,710 | 1,934 |
| `src/content/docs/use/appearance-and-devices.md` | 792 | 870 |
| `src/content/docs/use/applications.md` | 670 | 713 |
| `src/content/docs/use/changing-many-records.md` | 513 | 628 |
| `src/content/docs/use/copying-and-moving.md` | 0 | 715 |
| `src/content/docs/use/history.md` | 1,814 | 1,815 |
| `src/content/docs/use/home.md` | 662 | 700 |
| `src/content/docs/use/importing-and-exporting.md` | 1,935 | 2,316 |
| `src/content/docs/use/inbox-and-approvals.md` | 1,704 | 1,715 |
| `src/content/docs/use/jobs.md` | 981 | 1,064 |
| `src/content/docs/use/loading-with-the-assistant.md` | 2,036 | 2,081 |
| `src/content/docs/use/mapping-grids.md` | 1,381 | 1,386 |
| `src/content/docs/use/notifications-settings.md` | 738 | 806 |
| `src/content/docs/use/records.md` | 2,578 | 2,658 |

The changes cover exact import-profile/source-file deletion confirmations and retained data;
hidden fields and form help; second-step sign-in; current Appearance controls and defaults;
null versus unset; bulk limits and deletion policies; assistant-to-manual import entry;
file/preview/retention limits; failed assistant loads that leave proposals; change-set discard;
notification confirmations and unavailable-email messages; and steward copy/move review.

The existing sidebar groups and order are retained. Both new pages are in Applications and
workspaces. All section pages have `reader: steward` metadata and a sidebar entry.

## Coverage and depth

- Code inventory: **159 Use entries: 153 covered, six excluded, zero uncovered**.
  The covered count includes 100 management operations handled by the generated API reference,
  as the checker defines. The other 53 are screen entries.
- Newly resolved gaps: the notification deletion confirmation is now named and explained;
  five internal route discriminators and one reusable dialog component identifier are excluded.
  Their actual capabilities remain documented. The six exact reasons are in
  `guide/_coverage/exclusions.md`, only for Use entries.
- Existing ledger: **917 rows: 812 covered, 105 not for readers, zero deferred/open**.
  All 185 earlier AI resolutions were stored in Source while Covered by still said deferred.
  Restored source references and moved those resolutions into Covered by. Five saved row groups
  preserve each resolution under this notes directory.
- Every page has a depth entry in `depth.md`. Questions about server backup/restore and
  model/access administration link to those readers' pages; rotation/renewal questions that
  do not apply to data operations are marked inapplicable. No unresolved textual depth question.
- Existing coverage exclusions about obsolete planning designs remain exclusions, rather than
  being written as capabilities. Current assistant pages describe Claude Code sessions.

## Screenshots wanted

Eight new screenshots, with precise page/screen/state/visible details in
`guide/_waves/screens-wanted/D-USE.md`:

1. `use-import-profile-delete-actions.png` — selected profile with separate deletion actions.
2. `use-import-file-delete-confirm.png` — uploaded-file confirmation and retained-data explanation.
3. `use-import-profile-delete-confirm.png` — profile confirmation and replacement-profile consequence.
4. `use-sign-in-second-step.png` — passkey, authenticator and recovery-code choices.
5. `use-appearance-themes.png` — Normal/Website purple and separate light/dark mode controls.
6. `use-copy-dry-run.png` — reference-data transfer scope, counts, omissions and refusals.
7. `use-move-review-change-sets.png` — completed load with both proposals and target-first publication.
8. `use-notification-email-digest-settings.png` — enabled email, delivery choices and digest schedule.

No screenshots captured or fabricated. Existing screenshots reused where they fit. New screenshot
placeholders are present as the writing instructions require. Their appearance remains unverified.

## Checks actually run

From `guide/`, `GUIDE_OUT=_build/D-USE npm run verify`:

- **Build passes:** 252 pages, final build 3.03 seconds, output `_build/D-USE`.
- **Terms and brand pass.**
- **Links do not pass yet:** 72,452 local links/sources checked; ten failures are the eight
  requested image files above, some reused on two pages. No other link failures were reported.
  `guide/public/screens/` is outside this assignment's editable paths, and the writing rules say
  screenshots are taken afterwards. Full verify remains pending capture, not claimed passing.
- Existing non-fatal build warnings concern the unsupported `caddyfile` highlighter and the
  duplicate 404 route. Neither prevents the build; configuration is outside this wave.

`node --check sidebar/use.mjs` passes. Metadata, sidebar membership and per-page depth entries
checked for all 68 pages.

The current `node tools/check.mjs coverage` logic was run with only its write to shared
`_coverage/inventory/uncovered.md` redirected to
`_coverage/notes/D-USE/inventory-uncovered.md`, using the Node filesystem binding. This leaves
the shared generated inventory unchanged, as the edit scope requires. Its table reports zero
Use gaps. Its global exit is nonzero for 13 Integrate gaps (12 consumer API, one MCP tool),
which belong to another wave. The saved wave-local report has no Use section.

No application test suites or live browser journeys run: this is documentation work and the
screenshots are assigned to later capture. Text was checked against targeted current source,
not presented as live behavioral or accessibility acceptance.

## Uncertainties and defects

No confirmed product defect found. Corrected documentation drift in Theme labels, null handling,
manual import entry, cancellation labels and failure recovery. Runtime behavior and requested
screenshots have not been demonstrated on a live instance in this wave. Full verification cannot
pass until the eight requested screenshots are supplied. No other unresolved writing question.

No commits, state-changing git commands, application code, tests or other sections edited.
Working notes remain under this wave's notes directory. No steer file existed at unit boundaries.
