
## 2026-11-11T02:14:11+01:00 — applications page

Finished `guide/src/content/docs/use/applications.md`: added the sidebar list search, its threshold, counts, group behavior, keyboard shortcuts and recovery; distinguished it from record and group-page searches. Checked Explorer and navigation matching code; no steering file exists. Search matches a contiguous phrase, not separate words; new screenshots await a suitable reference instance.

## 2026-11-11T02:14:34+01:00 — lists and filters page

Finished `guide/src/content/docs/use/lists-and-filters.md`: explained the inactive mark, field-dependent wording, count, switch, address/pill behavior and unchanged editing permissions across data contexts. No steering file exists. The implementation filters for Yes, so unset values also disappear but do not contribute to the No count; the page makes this limit explicit.

## 2026-11-11T02:14:50+01:00 — find records task

Finished `guide/src/content/docs/guide/use/find-records.md`: added finding the correct list through the sidebar and using/removing the inactive filter, with links to the owning explanations. Kept the existing record search, relationship conditions, sorting and navigation steps; no steering file exists. No additional uncertainties beyond the unset-value behavior recorded above.

## 2026-11-11T02:15:07+01:00 — record pages and tables explanation

Finished `guide/src/content/docs/model/record-pages-and-tables.md`: documented the per-table Inactive records setting, eligible fields and refusal, None, reader behavior, read-only fields and data contexts. Verified labels against the layout form and eligibility against backend model validation; no steering file exists. Record-page panel settings remain unchanged because this setting belongs to table views.

## 2026-11-11T02:15:30+01:00 — table layout task

Finished `guide/src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`: added the Inactive records dialog steps, eligible choices, refusal recovery and checks after activation. Existing column, filter, initial-sort and reading-size instructions remain applicable; no steering file exists. The table-layout screenshot needs a refresh and the new dialog and reader states need reference-instance captures; no image files were invented.

## 2026-11-11T02:16:19+01:00 — final page review and screenshot handoff

Reviewed all five changes, moved the sidebar-search subsection after the existing group/record-page text to preserve its structure, and saved the evidence, retained passages and four screenshot requests in `guide/_coverage/notes/LB-GUIDE/review.md`. No steering file exists. Existing conditional sidebar/table pictures remain valid; `model-layout-table-tab.png` needs a toolbar refresh.

## 2026-11-11T02:17:07+01:00 — validation complete

`GUIDE_OUT=_build/LB-GUIDE npm run build` in `guide/` passed after the final page edit: 257 pages, 3.36 seconds. Scoped `git diff --check` passed; 11 local fragment links across the five built pages resolved. The build emitted a /404 route-conflict warning; browser appearance remains unverified and screenshots await the missing reference configurations. An initial build invocation from the repository root found no package.json; it was corrected to guide/. No commits or state-changing git commands were run.
