# Cover what the pages did not yet cover

Read `guide/AGENTS.md`, then `guide/_waves/OUTLINE.md` (the complete outline of the documentation, built
from refiroo's product documents, changelog and the model editor inventory) and `guide/_waves/NOT-YET-COVERED.md` (what
each existing page misses or states differently, with sources).

For every existing page under `use/`, `guide/use/`, `model/`, `guide/model/`, `administer/`,
`guide/administer/` and `examples/`:

1. Add what NOT-YET-COVERED.md and the outline say the page must cover and it does not, from the cited sources.
2. Correct what it states differently from the sources or the screens (for example "refresh the draft"
   where the screen offers **Apply mine again**; the claim that the default workspace cannot be retired or
   deleted, unless the code says so).
3. Make the moves the outline names: the workbook pages become the model section's workbook onboarding
   (create the outline's model paths, move the content there, and leave the old files' content unchanged;
   they are removed after your run); "Manage workspaces" content goes to the model section's page for it;
   approval-policy content goes to `administer/approval-policies.md`. Fix every link to moved content.
4. Respect the outline's must-not notes (what the UI does not have).

Do not write the outline's new pages in this run, except where a move needs its target page. Keep each
page's structure, standard and screenshots; the screenshot files are in `public/screens/`, described in
`_waves/*.screens.json`, and may be referenced as `/docs/screens/<name>.png` with captions.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/model/*.md`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/examples/*.md`

## Report

Per page: what was added, corrected or moved; files that can now be removed; anything you could not
confirm; anything in refiroo that looked wrong.
