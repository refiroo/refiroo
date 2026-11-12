# UX1, PL1, PL2, PL5, PL6: the interface changed

On 2026-11-12 the application's interface changed in many places (0.17 packages UX1, PL1, PL2, PL5, PL6 and the
e-mail template). What changed is written, in the application's own words, in `CHANGELOG.md` under
`[Unreleased]`: the entries headed **0.17 UX1**, **0.17 PL1 and PL2**, **0.17 PL5 and PL6** and **0.17 MT1**.
Read those entries first, then the code they name, and bring the guide in line.

## What to do

1. **Correct every sentence the changes made wrong** on the pages listed below: a button's or a dialog's name, a
   step that no longer exists, a place where something moved. Change only what is wrong or incomplete; do not
   restructure pages or rewrite correct text. Do not touch screenshots or their file names.
2. **Add what a reader cannot find otherwise**, briefly, on the page where they would look:
   - Themes (Current, Hearth, Studio, Instrument, Website purple; each in light and dark; what a theme changes;
     that Studio and Instrument arrange the frame differently and where the applications, the search and the
     data context are in each) on the page about appearance.
   - The workspace's page: the shelf (bring lists and other views, drag or use the tile's menu to order them,
     kept in the browser), the search, the applications with their lists, what needs you, what changed.
   - Home's search across workspaces, and ⌘K or Ctrl+K.
   - A row opening beside its list, and Expand to full page.
   - Changing a value where it stands, the switch for a yes or no, Undo after a save.
   - Forms opening beside the page.
   - The e-mail template (a page of its own under the administration or running section, where the mail pages
     are): what it is, the placeholders, the logo, preview, sending a test, who may use it.
3. Check each fact against the code before you write it. The code wins over the changelog; if they differ, write
   what the code does and list the difference in your report.

## Words the application now uses

One word per action: **Save**, **Add ‹thing›**, **Delete ‹thing›** (the thing is gone), **Remove ‹thing›** (a link
or membership goes), **Move**, **Publish**, **Cancel**. A new thing's form is titled **New ‹thing›**. "Record",
not "object", on the pages a steward uses. The theme formerly called Normal is **Current**.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/use/*.mdx`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/use/*.mdx`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/guide/model/*.mdx`
- `src/content/docs/model/*.md`
- `src/content/docs/model/*.mdx`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/guide/administer/*.mdx`
- `src/content/docs/administer/*.md`
- `src/content/docs/administer/*.mdx`
- `src/content/docs/guide/integrate/*.md`
- `src/content/docs/integrate/*.md`
- `src/content/docs/run/*.md`
- `src/content/docs/run/*.mdx`
- `src/content/docs/journeys/*.md`
- `src/content/docs/examples/*.md`
- `src/content/docs/about/*.md`

A new page needs its entry in the sidebar: if adding one would need a file outside this list, put the text on the
nearest existing page instead and say so in the report.

## How to find the sentences

Search the listed pages for the old words: "Rename…", "Create group", "Create role", "Create workspace", "Create
webhook", "Register an assistant", "Make a new secret", "Make a new key", "Start from current live data",
"Create change set", "Validate change set", "Publish change set", "Discard change set", "Connect an object",
"Create relationship", "Set null", "Please confirm", "Normal" (the theme), "Apply" (model editor forms), "Save
changes", "Save name", "Confirm deletion", "Back to list", "dialog" (where a form is meant). Read each hit in its
paragraph and decide by the changelog and the code; many hits need no change.

## Report

Per page: the sentences changed (old and new), or "no change"; pages or sections added; the screenshots that now
show an outdated interface, by file name, without changing them; anything where the code contradicts the
changelog.
