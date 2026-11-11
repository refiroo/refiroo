# MAPVIEWS3 guide: drop the Ambiguous-filter picture

Read `guide/AGENTS.md`.

## Why
`public/screens/mapping-grid-filter-ambiguous.png` shows an **Ambiguous** filter the reference view no longer offers,
so it cannot be retaken. The page text marks it as an outdated illustration.

## What to do
- In `src/content/docs/guide/use/map-codes-between-systems.md` remove that picture, its caption and the outdated
  mark; keep every step and sentence that is still true (the conditional Ambiguous filter explanation in words stays
  where it applies). If any other page under `src/content/docs` shows the picture, remove it there too (list those
  pages in the report; you may edit only the files below plus any such page).
- Delete nothing else. Do not touch the image file (the caller removes it).

## Files you may edit
- `src/content/docs/guide/use/map-codes-between-systems.md`
- `src/content/docs/use/mapping-grids.md`
- `_waves/progress/MAPVIEWS3.md`
