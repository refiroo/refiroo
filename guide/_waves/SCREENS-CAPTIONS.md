# SCREENS-CAPTIONS: place the canvas pictures and bring captions in line with the retaken pictures

On 2026-11-12 the guide's screenshots were retaken on today's interface (see the paragraph about the screenshots
in `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, section "State, 2026-11-12 (morning)", and the screen definitions in
`guide/_waves/*.screens.json`, each with a `shows` text saying what the picture now shows). Do two things; change
nothing else.

1. **Canvas pictures.** Add image references, in the existing pages' image style (look at how other pages
   reference `/screens/<name>.png` with a caption), for the pictures defined in `guide/_waves/CANVAS.screens.json`:
   - on `src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`: canvas-workbook-open,
     canvas-workbook-connect, canvas-workbook-readings, canvas-workbook-columns-as-rows, canvas-workbook-navigation,
     canvas-workbook-refused, canvas-workbook-create-dialog;
   - on `src/content/docs/guide/model/edit-a-model-on-the-canvas.md`: canvas-model-whole, canvas-model-add-menu,
     canvas-model-attribute, canvas-model-relation-rule, canvas-model-navigation, canvas-model-views,
     canvas-model-consumer, canvas-model-issues, canvas-model-history.
   Put each where the page describes what it shows (read its `shows` text and look at the PNG in
   `guide/public/screens/`); write the caption from what the picture shows.
2. **Captions that no longer match their picture.** For every image reference in `src/content/docs`, compare the
   caption with the screen's `shows` text in the `.screens.json` files (and the PNG where unsure). Where the caption
   describes something the picture no longer shows (for example a sign-in page with no provider yet, the old
   Ambiguous filter, "Publication 1" numbering, a Delete confirmation that is now an Undo notice, a side sheet now a
   centred dialog), correct the caption, and the sentence right next to it if it says the same. Do not change file
   names or remove images.

Then run, in `guide/`: `GUIDE_OUT=_build/SCREENS-CAPTIONS npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/**/*.md`
- `src/content/docs/**/*.mdx`

## Report

The canvas pictures placed (page and caption); each caption changed (page, old, new); the build and verify results.
