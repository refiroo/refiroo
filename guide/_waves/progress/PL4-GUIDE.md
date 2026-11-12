# PL4-GUIDE progress

## 2026-11-12 05:33 CET — Workspaces

Finished `guide/src/content/docs/use/workspaces.md`: added “A workspace from a workbook”, covering entry points, access, file/name and checked-row review, actions, failures and the load notice. No steering file was present; the code allows Model authoring at any scope and Cancel can leave a draft if deletion fails, unlike the changelog's broader wording.

## 2026-11-12 05:34 CET — Importing and exporting

Finished `guide/src/content/docs/use/importing-and-exporting.md`: added one sentence pointing readers with a workbook for a separate workspace to the new section. No steering file was present; no uncertainties for this unit.

## 2026-11-12 05:34 CET — Workspace API

Finished `guide/src/content/docs/integrate/workspaces-contexts-and-models.md`: added two sentences on the draft-based request, 202 response, automatic release/profile clash resolution and the reference's errors. No steering file was present; distinguished a release-version clash from a stale draft version, which still refuses.

## 2026-11-12 05:34 CET — Validation complete

`GUIDE_OUT=_build/PL4-GUIDE npm run build` passed (257 pages); Astro warned that `/404` conflicts with the higher-priority `/404` route. `npm run check:coverage` passed (1,093 items: 1,082 covered, 11 excluded, zero uncovered). No screenshots or image references were changed, and no browser behavior was exercised.

Code/changelog differences: Model authoring is accepted at any scope by the entry's permission check. Cancel only attempts draft deletion after a successful read returns its draft, and ignores deletion failures; a failed read can therefore also leave a draft behind. These are source observations, not reproduced failures.
