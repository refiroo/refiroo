# Correct the four sample guides

Read `guide/AGENTS.md` again: it now separates documentation pages from guides, and asks for generic steps
with the example in screenshot captions, and for more detail.

Rewrite these four guides to match it:

- `src/content/docs/guide/use/find-records.md`
- `src/content/docs/guide/use/correct-a-record.md`
- `src/content/docs/guide/use/prepare-and-publish-a-change-set.md`
- `src/content/docs/guide/use/translate-names.md`

What the person who owns refiroo asked for:

- **Generic steps.** "Open an application in the current workspace", not "Open Network in the Graubünden
  workspace". The Graubünden stops appear only in the captions under the screenshots ("Above: the Network
  application in the Graubünden workspace…") or in a clearly marked example after the general steps.
- **More detail.** For each step: what to do, what the reader then sees, what the options on the screen
  mean, what can go wrong and what to do about it.
- **Guides, not explanations.** The ideas now live on the documentation pages `./records/` and
  `./change-sets/`. Each guide starts with a short line saying what it helps the reader do and links to its
  documentation page for the background; move longer explanations out of the guides (the documentation
  pages already cover them; do not edit those pages). "Translate names" has no documentation page yet:
  keep only the background a reader needs for the task.

## Screenshots

Screens file: `PILOT.screens.json`

The screenshots named in that file are attached and are the real screens. Keep using them, each with a
caption that says what the example shows. List any screenshot you still need.

## Files you may edit

- `src/content/docs/guide/use/find-records.md`
- `src/content/docs/guide/use/correct-a-record.md`
- `src/content/docs/guide/use/prepare-and-publish-a-change-set.md`
- `src/content/docs/guide/use/translate-names.md`

## Report

What changed in each guide, the screenshots still needed, anything you were unsure of, and anything in
refiroo that looked wrong.
