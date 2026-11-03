# Finish "Use refiroo"

Read `guide/AGENTS.md` again (documentation pages and guides; capabilities, not applications; generic
steps with the example only in captions; detail). Keep the standard of the existing pages in
`src/content/docs/use/` and `src/content/docs/guide/use/`.

What the person who owns refiroo asked for:

1. **Applications and workspaces: one group, two documentation pages, each with its guide.** Replace
   `use/workspaces-and-applications.md` with:
   - `use/applications.md`: what an application is, that a model defines it and the views it offers, the
     four kinds of view; guide `guide/use/open-an-application.md` (exists; adjust links).
   - `use/workspaces.md`: what a workspace is, that each runs a model of its own, switching, managing
     workspaces as far as a steward meets it; guide `guide/use/switch-workspace.md` (new).
   Move what is right in the old page into the two new ones. Leave the old file's content as is; it will be
   removed after your run. Update every link to it in the pages you may edit.
2. **A page about the home page** (`use/home.md`) and **a page about your account** (`use/account.md`):
   what is on the screen and what the person can do there. No guides of their own: where a button or card
   starts a task, link to that task's guide (for example an open change set → "Prepare and publish a change
   set", a workspace card → "Switch workspace"). Where a part has no guide, explain it on the page.
3. **The missing capabilities**, each a documentation page and a guide:
   - Publications: `use/publications.md`, `guide/use/browse-a-publication.md`.
   - History: `use/history.md` (a record's history, and any view across records a steward can use),
     `guide/use/see-who-changed-what.md`. "About records" may then shorten its history section to a link.
   - Loading a workbook: `use/loading-a-workbook.md` (what happens when a workbook is loaded: source file,
     draft, the proposed steps, issues, the dry run, applying; what is kept as it is in the file),
     `guide/use/load-a-workbook.md`. The example workbook is the fictional operator file in
     `samples/Haltestellen_Busbetrieb_Nord.xlsx`; say in its caption that it is fictional.
   - Inbox and approvals: `use/inbox-and-approvals.md` (notifications, when a change set needs approval, who
     approves), `guide/use/approve-a-change-set.md`. If the screenshots show that approvals are not
     configured on the example instance, describe them from the code and documents and say in your report
     which screenshots are missing.
4. **Correct "About records"**: its section "Translations are related records" presents translation as a
   refiroo feature. Translation is an application (see `examples/translations.md`); rewrite that section as
   the general capability (records that belong to another record, shown for example in a relation matrix)
   and link to the Translations example.

## Screenshots

Screens file: `USE2.screens.json`

Those screenshots are attached and are the real screens; earlier ones (`PILOT.screens.json`,
`CAPABILITIES.screens.json`) may also be referenced. Use `/docs/screens/<name>.png` with captions saying what
the example shows. List any screenshot still needed.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/examples/*.md`

## Report

The pages written or changed, the screenshots used and still needed, anything you were unsure of, and
anything in refiroo that looked wrong.
