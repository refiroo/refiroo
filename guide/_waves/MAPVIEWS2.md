# MAPVIEWS2 guide: the retaken mapping picture

Read `guide/AGENTS.md`.

## Why

`public/screens/mapping-grid-codes-to-stops.png` was retaken from the reference instance (1440 px, search FICTIONAL).
It now shows **Codes to stops** with the filter **All / Unmapped / Mapped** only (no **Ambiguous**: this view's
relationship lets a code hold several stops), T-0300 as **Mapped (2)** with Chur and Chur West, many T-04xx/T-05xx
codes as **Mapped**, and T-9999 **Unmapped** with **Map**. Names in the first column are links that open the record.

## What to do

- In `src/content/docs/use/mapping-grids.md`, make the text and caption around that picture match what it shows
  (the picture no longer shows an Ambiguous row; the state table and the paragraph on Ambiguous stay correct).
- In `src/content/docs/guide/use/map-codes-between-systems.md`, the picture `mapping-grid-filter-ambiguous.png`
  shows an **Ambiguous** filter this reference view no longer offers and cannot be retaken: say so in your report
  and, if its surrounding text promises what the view cannot show, make the text honest without removing steps
  that still hold. Do not edit other pages.
- No new pages or pictures. Report what you changed and any point you cannot describe honestly.

## Files you may edit

- `src/content/docs/use/mapping-grids.md`
- `src/content/docs/guide/use/map-codes-between-systems.md`
- `_waves/progress/MAPVIEWS2.md`
