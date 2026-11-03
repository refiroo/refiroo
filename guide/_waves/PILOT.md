# Pilot: four pages for data stewards

Read `guide/AGENTS.md` first; it is how this guide is written.

Write four pages in the "Use refiroo" section for a data steward who works only in the browser. They are
the first pages of the guide; the person who owns refiroo reads them to judge whether the guide is right.

1. **Find records**: open an application, find a stop by name or number, filter and sort a list, open a
   record and see its details and relationships.
2. **Correct a record**: change a value and save; what happens when someone else changed it first; where
   to see who changed what.
3. **Prepare and publish a change set**: when to use one instead of a direct correction; open one, make the
   changes, review them, publish; what happens to live data meanwhile.
4. **Translate names**: see which names are missing in a language, add or correct a translation.

Use the Graubünden stops in every example (a stop such as Chur Wiesental, the municipality Chur and its
names Coire, Coira and Cuira). Name buttons, fields and menus exactly as the screens in `frontend/src/` show
them.

## Screenshots

Screens file: `PILOT.screens.json`

The screenshots named in that file are attached to this assignment. They are real screens of the reference
instance (the Graubünden stops data); the file says what each one shows. Reference them on the pages as
`/docs/screens/<name>.png`. There is no screen of a missing translation: every municipality has a name in
every language, so describe that case in words and ask for a screenshot in your report.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/use/*.mdx`

## Report

The four pages, the screenshots each needs (screen, state, what must be visible), anything you were unsure
of, and anything in refiroo that looked wrong.
