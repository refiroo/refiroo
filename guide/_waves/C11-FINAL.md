# C11: the final coverage check

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`.

Go through `_waves/coverage/*.md` row by row against the pages as they are now. For each row marked covered,
open the page and confirm it says it (correct the row if not). For every row still `uncovered` or
`partly` (except after 0.16), write what is missing on the page where it belongs. Then check the
documentation as a whole: every page reachable from the sidebar, every documentation page linking its
guides and every guide its documentation page, no term used two ways, the glossary terms in
`docs/GLOSSARY.md` used as defined. Update the counts at the top of each coverage file.

## Files you may edit

- `src/content/docs/**/*.md`
- `sidebar/*.mjs`
- `_waves/coverage/*.md`
- `_waves/screens-wanted/C11-FINAL.md`
- `_coverage/notes/C11-FINAL/**` (working notes)

## Report

The counts before and after, the rows corrected, what was written, and every row still open with why.
