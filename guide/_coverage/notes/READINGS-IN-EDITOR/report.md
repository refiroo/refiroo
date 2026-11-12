# READINGS-IN-EDITOR report

## guide/src/content/docs/use/importing-and-exporting.md

Before:

A model administrator sets these readings on the
[canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#correct-how-the-sheet-is-read).
The model editor shares the saved profile, but has no dedicated controls for these three
readings; switch to **Canvas** to set them.

After:

A model administrator sets these readings on the
[canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#correct-how-the-sheet-is-read)
or in the model editor. In the editor, a column's **Readings** row offers
**Fill blanks from the cell above**, **Rows holding only this column are headings…** and
**Read these columns as rows…**, with a **Stop…** entry for each reading that is on.
A loaded list's **Readings** row also offers **Read these columns as rows…**.
The **Source** pane marks columns that have a reading.

## guide/src/content/docs/guide/use/load-the-next-version-of-a-workbook.md

Before:

These readings are set on
the [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#correct-how-the-sheet-is-read);
the model editor has no dedicated controls for them.

After:

These readings are set on
the [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#correct-how-the-sheet-is-read)
or in the model editor, under **Readings** in a column's panel; a loaded list's panel also
offers **Read these columns as rows…**.

## guide/src/content/docs/guide/model/map-a-column.md

Before:

how the file is read before matching or conversion.

After:

how the file is read before matching or conversion. For a sheet that loads records, the
column panel's **Readings** row also offers **Fill blanks from the cell above**,
**Rows holding only this column are headings…** and **Read these columns as rows…**.
For columns read as rows, select at least two columns, name the two added columns and choose
**Read as rows**. For headings, name the added column, choose the parent object type and
choose **Read headings**. A reading that is on has its corresponding **Stop…** entry.
The **Source** pane marks columns that have a reading; check the refreshed dry run after changing one.

## guide/src/content/docs/guide/model/read-lists-in-a-sheet.md

Before:

the board and choose how to read columns and heading rows.

After:

the board and choose how to read columns and heading rows. In the model editor, a loaded
list's **Readings** row also offers **Read these columns as rows…**: select at least two
columns, name the two added columns and choose **Read as rows**. When it is on,
**Stop reading these columns as rows** reverses it. A column's **Readings** row also offers
**Fill blanks from the cell above** and **Rows holding only this column are headings…**;
see [Map a workbook column](/docs/guide/model/map-a-column/).

## guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md

Before:

These are saved reading instructions, used by the dry run and the eventual load alike.

After:

These are saved reading instructions, used by the dry run and the eventual load alike.
You can also set them in the model editor: a column's **Readings** row offers
**Fill blanks from the cell above**, **Rows holding only this column are headings…** and
**Read these columns as rows…**, with the corresponding **Stop…** entry while a reading is on.
A loaded list's **Readings** row also offers **Read these columns as rows…**; there you select
the columns before naming the two added columns. The **Source** pane marks columns that have a reading.

## Validation

- `GUIDE_OUT=_build/READINGS-IN-EDITOR npm run build`: passed, 259 pages.
- `GUIDE_OUT=_build/READINGS-IN-EDITOR npm run verify`: passed, including its build, terminology, branding, sidebar, inventory, coverage and local links checks. The output directory was set for verify too because it invokes build.
- Build warning: the catch-all route could not render `/404` because the explicit `/404` route has priority.

No new screenshots or image references. No uncertainties or application defects found in this scope. The integration page needed no change: it already describes the shared readings without limiting them to the canvas. No steering file was present.
