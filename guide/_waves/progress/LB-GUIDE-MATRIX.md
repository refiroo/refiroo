
## 2026-11-11T02:24:46+01:00 — Capability page

Finished `guide/src/content/docs/use/relation-matrices.md`: documented Hide empty columns, whole-search/scope checks, column paging, browser persistence, change-set/publication values, the hidden count and Show all, and Filter precedence. Qualified the existing navigation/all-columns wording; no steering file was present and no uncertainty remains about these documented rules after checking the frontend and backend code.

## 2026-11-11T02:25:14+01:00 — Task guide

Finished `guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md`: added steps to hide empty columns, clear an explicit selection when it overrides the switch, and restore hidden columns. Clarified the remembered setting when reopening the view and advised including wholly empty columns when checking missing connections; no steering file was present and no uncertainty remains about the added steps.

## 2026-11-11T02:25:37+01:00 — Review and build

Reviewed both pages against RelationMatrixView, RelationMatrixFilter, TableDisplay, the matrix projection and cell-read helpers, plus the current-functionality, journey and API passages. Left the selected-column limit, Any state, automatic use of shown columns for a state filter, and clearing the state with the column selection unchanged; preserved the pre-existing width/preview/narrow-screen text. `GUIDE_OUT=_build/LB-GUIDE-MATRIX npm run build` passed (257 pages, 3.53 seconds); it warned of competing /404 routes. No steering file was present.

Pictures needed for both pages: when retaking the existing matrix overview pictures, show Hide empty columns beside Filter; include an on state with omitted columns, the hidden-column count and Show all. The Filter capture should also show chosen columns and the switch's No effect while columns are chosen in Filter message. No pictures were added or changed. All assigned product points were supported by source inspection; no browser behavior was exercised in this documentation wave.
