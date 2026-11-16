# UI1 guide: the banner of a change set under another model version

Read `guide/AGENTS.md`. Readers: people who prepare and publish change sets, and model administrators. Write plain
prose; no package or decision numbers.

Screens file: `UI1.screens.json`

## Why

A change set can work under another model version than live data. The page then shows a banner. Until now it was a
long paragraph with two very long buttons ("Move this change set to …", "Move … to … and publish…"), the Publish
button still showed and was refused, and Discard was only in the menu. The banner is redesigned; no behaviour of the two
moves changes. The code wins over this text wherever they differ:
- the banner: `frontend/src/features/workspaces/ChangeSets.tsx` (the section `model-mismatch`), its styles in
  `frontend/src/styles/components.css`;
- the two moves are unchanged: `moveChangeSet` (previews moving the change set onto the live version; the move does not
  publish, the migration page ends with "Open the change set to publish it") and `migrateAndPublish` (previews moving the
  workspace to the change set's version and publishing the change set with it).

## What the product does now (check each point in the code)

- The banner is titled **This change set cannot be published yet** with the sentence "It was made under a different model
  version than live data. Bring the two onto the same version, then publish." Beside it, two chips: **This change set**
  (the model and version the change set works under) and **Live data** (the model and version live data runs), with a `≠`
  between them.
- Each way out is a card with a heading, a direction chip (for example 0.3.42 → 0.3.48) and a short button:
  - **Update change set** (card "Update the change set", from the change set's version to the live one): "Its content is
    converted where the live version differs. You review every item before the move is saved. Then you publish it as
    usual." It previews the move; it does not publish. It needs background jobs and the rights to change the change set.
  - **Move workspace and publish** (card "Move the workspace back", from the live version to the change set's): the
    workspace goes to the change set's version and the change set is published with it. It needs model-release and
    publication rights and model administration, and follows the same approval policy as publication.
  Neither button ends in "…". A card appears only when the person can run it; when only one card is left, its button is the
  primary one. The banner no longer explains that background jobs or model administration are missing.
- Below the cards, **Don’t need these changes?** and a **Discard change set** button: it opens the same confirmation as
  **Discard** in the **More change set actions** menu, which stays.
- Someone who only views the change set sees the title, a sentence ("It was made under a different model version than
  live data. The people working on it can update it to the live version or discard it.") and the two chips: no cards, no
  Discard.
- While the versions differ the bar has no **Publish** and no **Submit for publication**; they return when the versions
  match. (Before, they showed and the publication was refused.)

## What to do

Update the pages that name the old banner. Keep every other sentence; change only what names the old buttons, the old
title or the old behaviour of Publish. Neutral wording.
- `src/content/docs/guide/use/prepare-under-the-next-model-version.md`: steps 3 to 5 (the banner's title, the two buttons,
  the missing Publish).
- `src/content/docs/use/change-sets.md`: the section "Model-version actions on the banner" (the banner is no longer a
  menu thing: the two cards and Discard are on the banner itself; the menu keeps Change model version and Discard).
- `src/content/docs/model/migrations.md`: the section "Change sets on another release".
- `src/content/docs/guide/use/load-a-workbook-with-the-assistant.md`, `src/content/docs/guide/model/review-an-assistants-workbook-design.md`,
  `src/content/docs/use/loading-with-the-assistant.md`, `src/content/docs/journeys/work-with-an-assistant.md`: where they
  name the button "Move … and publish…", name it **Move workspace and publish** (and say it is on the banner of a change
  set that uses another version); keep what they say about previewing and **Migrate and publish**.

## Pictures (taken, in `guide/public/screens/`; look at it, then reference it as `![…](/docs/screens/<name>.png)`)

- `change-set-model-banner`: the banner with both ways out (the two chips, the two cards with their direction chips, Discard
  change set), the bar above it without a Publish button. Use it in `use/change-sets.md` and in
  `guide/use/prepare-under-the-next-model-version.md`, where the steps describe the banner, with a caption that says what to
  look at.
No older picture shows the banner.

## Files you may edit
- `src/content/docs/guide/use/prepare-under-the-next-model-version.md`
- `src/content/docs/use/change-sets.md`
- `src/content/docs/model/migrations.md`
- `src/content/docs/guide/use/load-a-workbook-with-the-assistant.md`
- `src/content/docs/guide/model/review-an-assistants-workbook-design.md`
- `src/content/docs/use/loading-with-the-assistant.md`
- `src/content/docs/journeys/work-with-an-assistant.md`
