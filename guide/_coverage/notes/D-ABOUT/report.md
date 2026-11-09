# D-ABOUT completion report

19 content pages changed. Word counts below count whitespace-separated Markdown words consistently before and after this run.

| Page | Before | After |
| --- | ---: | ---: |
| `src/content/docs/about/accessibility.md` | 495 | 544 |
| `src/content/docs/about/compatibility-and-licence.md` | 534 | 558 |
| `src/content/docs/about/data-quality-rules.md` | 512 | 623 |
| `src/content/docs/about/how-it-is-built.md` | 739 | 905 |
| `src/content/docs/about/how-it-works.md` | 655 | 838 |
| `src/content/docs/about/people-and-access.md` | 598 | 824 |
| `src/content/docs/about/security-and-trust.md` | 1252 | 1307 |
| `src/content/docs/about/sharing-data-with-other-systems.md` | 664 | 889 |
| `src/content/docs/about/three-kinds-of-change.md` | 625 | 716 |
| `src/content/docs/about/what-is-refiroo.md` | 928 | 1301 |
| `src/content/docs/journeys/change-with-approval.md` | 807 | 923 |
| `src/content/docs/journeys/index.md` | 697 | 889 |
| `src/content/docs/journeys/integrate-a-system.md` | 1574 | 1966 |
| `src/content/docs/journeys/look-after-data.md` | 1215 | 1705 |
| `src/content/docs/journeys/manage-access.md` | 706 | 1112 |
| `src/content/docs/journeys/receive-notices.md` (reviewed; unchanged) | 532 | 532 |
| `src/content/docs/journeys/run-the-service.md` | 490 | 1049 |
| `src/content/docs/journeys/shape-a-model.md` | 1500 | 1974 |
| `src/content/docs/journeys/work-with-an-assistant.md` | 1625 | 1783 |
| `src/content/docs/index.md` | 591 | 728 |

Changed pages: **16,207 → 20,634 words**.
All 20 scoped content pages reviewed: **16,739 → 21,166 words**.

## Coverage and depth

45 About source-record rows: 44 reader-facing covered, one existing non-reader test-matrix exclusion (C0038), zero open. No new exclusions. All nine code inventories contain zero About entries. The current checker reports 911 entries: 902 covered, nine existing exclusions, zero uncovered across the site.

All ten About pages and all nine journey pages were reviewed; receive-notices.md needed no change. The landing page and journey index now expose the added capability/task paths. No new page or sidebar reorganisation was needed. Setup, literal errors, recovery and removal procedures remain with the existing reader-specific pages; About explains their capability and links to them. Per-page depth notes are in depth.md.

No unresolved evaluator-depth question was found. Production workload sizing and recovery time remain explicitly unmeasured, and accessibility prose retains the absence of recorded screen-reader user testing. This writing pass performed no new runtime, browser or assistive-technology validation.

## Screenshots

No new screenshot requested. screens-wanted/D-ABOUT.md lists the four existing screenshot assets and workspace diagram retained; all exist. No images were captured or visually accepted.

## Validation

- `GUIDE_OUT=_build/D-ABOUT npm run verify`: build passes (252 pages); term and brand checks pass; link check fails on 10 references to eight missing screenshot assets outside this wave. There are no failed About, journey or landing-page links. Exact output is in verify.log.
- The coverage checker was run as `node --require ./_coverage/notes/D-ABOUT/coverage-output.cjs tools/check.mjs coverage`. The preload redirects only its generated uncovered report into this wave's notes, preserving the out-of-scope shared inventory file. Checker logic is unchanged; it passes. See coverage.log and coverage-uncovered.md.
- Read-only scoped `git diff --check` passes. Final About, landing, index and journey diffs reviewed.
- No server or database process was started. No commits or git state-changing commands were run.

## Remaining shared-site failures

The following existing Use-section screenshot references need their owning wave's assets. They are outside D-ABOUT's permitted files, so no substitute image or source-page edit was made:

- `/docs/screens/use-appearance-themes.png`
- `/docs/screens/use-copy-dry-run.png`
- `/docs/screens/use-import-file-delete-confirm.png`
- `/docs/screens/use-import-profile-delete-actions.png`
- `/docs/screens/use-import-profile-delete-confirm.png`
- `/docs/screens/use-move-review-change-sets.png`
- `/docs/screens/use-notification-email-digest-settings.png`
- `/docs/screens/use-sign-in-second-step.png`

## Corrections and product findings

- Appearance wording corrected against `frontend/src/features/settings/AppearancePage.tsx`: Theme chooses Normal/Website purple; Light or dark is separate.
- Automatic HTTPS wording corrected against `compose.acme.yml` and `caddy/Caddyfile`: 443 is required, 80 is optional for redirects.
- Saved-layout loading distinguished from assistant sessions; `backend/app/management/routers/ai_tasks.py:194` verifies the changed-draft activation checks.
- Transfer review/publication order verified against `backend/app/engine/moves/move_load.py:262`; role and retained-local-access safeguards checked in `backend/app/engine/authorization/administration.py` and `backend/app/engine/identity/providers.py`.
- No new product defect established. The ten missing-image references are documentation assembly defects, not evidence of a runtime failure.
