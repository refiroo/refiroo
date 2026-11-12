# CAPTIONS-CLEAN: captions of the pictures retaken on a fresh reference instance

On 2026-11-12 the reference instance was rebuilt fresh and the pictures that list workspaces, activity and notices
were retaken on it. Some captions and sentences now describe what the old pictures showed. Look at each picture named
below (`public/screens/<name>.png`) and correct only the sentences that no longer match it. The picture wins.

- `use/workspaces.md` (about line 42) and `guide/use/switch-workspace.md` (about line 14) describe an **Other release**
  marker in the workspace switcher. `workspace-switcher.png` now shows only **Other model** (Default runs another model).
  Keep the explanation that a workspace on another release of the same model shows Other release, but the picture's
  caption must say what it shows.
- Pages showing `workspaces-home.png` or `use-home.png`: Graubünden runs 1.8.1 and Default runs RDM Starter Model
  0.10.1 (not 1.0.0 or 0.10.0).
- The page showing `model-moves-list.png`: one mapping ("Guide mapping") and one dry run.
- The page showing `use-history-stop-changed.png`: the Thusis Süd history reads "Record updated" with Abbreviation,
  Latitude, Longitude and Height (m); not a single Abbreviation line.
- The page showing `appr-home-waiting.png`: "Two change sets wait for someone to publish them" (the December change and
  the approval example).

Search the pages for the picture names to find them. Change only what is wrong; keep the guide's words; no time
estimates; add no image references.

Then run, in `guide/`: `GUIDE_OUT=_build/CAPTIONS-CLEAN npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/model/*.md`
- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`

## Report

Each sentence before and after; build and verify results.
