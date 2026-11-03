# C10: the screenshots the pages ask for

Read `guide/AGENTS.md` and `guide/tools/CODEX_TOOL.md` (section Screenshots). This wave writes no page text.

This wave runs more than once, as sections are finished: each time, take only the images still missing
(append to `_waves/C10.screens.json`, keep entries already there).

1. List every image the pages reference (`/docs/screens/<name>.png` in `src/content/docs/**`) whose file
   is not in `public/screens/`; `_waves/screens-wanted/*.md` say what each must show.
2. Write `_waves/C10.screens.json` in the format of `_waves/USE2.screens.json` (read `tools/screens.mjs`
   for the actions it supports): for each missing image, how to reach the screen on the reference instance
   (`http://localhost:8480`, the Graubünden example) and the texts that must be visible (`expect`). Take
   routes and labels from `frontend/src/`. Dialogs are opened and cancelled, never confirmed. The reference
   instance exists for these pictures: where a screen needs a state (a model draft with a migration, a
   change set, a running job, records selected), add the steps that create it as earlier entries, and
   record each change in `_waves/C10.data-changes.md` (as `USE2.data-changes.md` does). Never confirm a
   step that deletes data, activates or rolls back a release, or changes access or security settings; take
   such a screen with its confirmation dialog open, then cancel.
3. You cannot reach the instance from your sandbox. After you stop, the screens are captured and you get
   the result and the images in a second turn: then correct the entries that failed, and check each image
   shows what its page says; where an image cannot show it, change the page's caption or image reference to
   what exists.

## Files you may edit

- `_waves/C10.screens.json`
- `_waves/C10.data-changes.md`
- `src/content/docs/**/*.md`
- `_coverage/notes/C10-SCREENS/**` (working notes)

## Report

The screens listed, those left out and why, and in the second turn what was corrected.
