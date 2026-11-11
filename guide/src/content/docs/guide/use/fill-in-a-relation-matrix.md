---
title: Fill in a relation matrix
description: Check coverage, find missing cells, create related records and correct existing ones.
reader: steward
---

Use a relation matrix to find empty cells and maintain the records behind its cells. The rows, columns,
fields and actions come from your model. See [Relation matrices](/docs/use/relation-matrices/)
for cell states, limits and permissions.

## Read the matrix

1. Open an application in the current workspace and choose a collection with a relation matrix.
   Select its matrix view where tabs are offered. Check the heading, row type and column headings.
2. Check the banner. Choose **Live** for immediate changes, or
   [open a change set](/docs/guide/use/prepare-and-publish-a-change-set/) to stage them. A publication
   is read-only.
3. Read the legend above the table. **One** and **Several** count related records under the
   model's rule. **Inactive** means records exist but none counts. **None** means no related record is present and no earlier-publication record is available to show; **History
   only** has content from an earlier publication; **Conflict** needs inspection because more
   than one record counts where only one is allowed.
4. Search for a row and check its identifying fields. Open a cell under the intended column.
   The dialog heading combines the row and column, so check both before changing anything.
   You can focus the matrix and use arrow keys between cells, then Enter to open one.

![A relation matrix with operators as rows and languages as columns](/docs/screens/matrix-operator-names.png)

*Above: Operator names in Names has many None cells. French and German contain name records.
The legend explains Active is Yes as the condition for counting in this example.*

The same steps apply when columns represent something else:

![A relation matrix with municipalities as rows and systems as columns](/docs/screens/matrix-municipalities-by-system.png)

*Above: Municipalities by system in Systems compares System codes under their systems. One
means exactly one related record here, without the name matrix's Active condition.*

## Choose which columns to show

A matrix includes all records of its column type by default, even those that do not concern the
rows you are working on. Hide empty columns automatically, or choose specific columns yourself.

### Hide empty columns

1. Set the row search and scope to the rows you want to work on, then turn on **Hide empty columns**
   beside **Filter**. The matrix keeps columns with a related record in at least one of those rows,
   including rows not yet on screen. Use the column navigation to reach more columns; empty columns
   do not take up places on its pages.
2. If the switch says **No effect while columns are chosen in Filter**, open **Filter**, choose
   **Show all** followed by the column type's plural name, then **Done**. This clears the chosen
   columns and any cell-state restriction, allowing the switch to take effect.
3. When columns are hidden, read the **N empty columns hidden** line below the toolbar. Choose
   **Show all** on that line, or turn the switch off, to bring them back.

The switch is remembered for this view in this browser. Before checking for missing connections,
turn it off or choose the columns to check explicitly, so wholly empty columns are included.
See [Filters and coverage](/docs/use/relation-matrices/#filters-and-coverage) for how the setting
works with search, scope, change sets and publications.

### Choose specific columns

1. Choose **Filter**. In the section named after the column type followed by **to show**,
   search for and select the columns you need. You can select up to 20; deselect one before
   adding another if you reach the limit.
2. Leave **Cell state** on **Any state**, or choose it to remove an existing state restriction.
   Choose **Done**. The matrix shows only your selected columns.
3. To clear your selection, open **Filter** and choose **Show all** followed by the column
   type's plural name, then **Done**. Use the column navigation if they do not all fit on one page.
   This also clears any cell-state restriction. If **Hide empty columns** is on, it takes effect
   again; turn it off to bring every column back.

Your choice belongs to the page you have open; it is not saved as a setting for the view and
does not change what other people see. Bookmark or share the page's address to reopen the same
column selection. Opening the view again from the navigation clears that selection, but keeps
your **Hide empty columns** setting.

## Find empty cells across the list

1. Clear the row search if you intend to check the whole list, then choose **Filter**.
2. In the section named after the column type followed by **to show**, search for and select
   the columns to check. The chooser can show up to 20 selected columns at once.
3. Under **Cell state**, choose **None**, then **Done**. Rows remain when at least one chosen
   column has that state, across the whole list. If you choose a state without selecting
   columns first, it applies to the columns currently shown.
4. Inspect the result. **No rows match these filters** means no matches within this search
   and column selection. Check omitted columns separately before concluding coverage is complete.
5. To inspect existing records that do not count, choose **Inactive** where offered. Choose
   **Any state** or remove the state pill with **×** to remove the state restriction. Clearing
   the column selection also clears that restriction.

![The Filter panel with cell-state choices and a column search](/docs/screens/matrix-filter-panel.png)

*Above: Municipality names offers Languages to show, with English, French, German, Italian
and Romansh. The state filter tests the chosen or shown languages, not hidden languages.*

## Fill an empty cell

1. Open the intended **None** cell. Check the row and column in the heading and the message
   that no related record exists yet.
2. Choose **Create** followed by the related type's name, where offered. The form identifies
   the row and column under **For** and **under**.
3. Check **Name**, which identifies the new record. Review the proposed name rather than
   treating it as the field content. Under **Goes in**, check where it will belong. The relationship's rules can fix a group;
   otherwise refiroo selects the group already holding the most records used by this view
   in this column. A tie leaves the choice open. An unused group is never selected just
   because it is the only one. Use **Search places…** to choose another offered group.
4. Fill the type's content fields. Set any checkbox or field that determines whether it counts
   according to the legend. Fill **Attributes of the relationship**, if shown: these describe
   the new connection rather than the record itself. Choose the form's **Create** action. On success, the dialog closes
   and the cell refreshes; check its state and displayed content.
5. Use **Back** to abandon the creation form and return to the cell, then **Close** to leave
   without creating anything. If creation is refused, correct the named problem before retrying.

![A searched matrix showing one missing cell beside four filled cells](/docs/screens/matrix-missing-name.png)

*Above: Bonaduz in Municipality names has One in four languages and None in Romansh. The empty cell
was prepared for these captures and filled again afterwards; it is not the reference data's current state.*

![An empty cell dialog offering creation of the missing related record](/docs/screens/matrix-missing-name-cell.png)

*Above: Bonaduz · rm says None · no name translation yet and offers Create name translation.*

![A creation form with a proposed name, selected container, content field and current flag](/docs/screens/matrix-missing-name-add.png)

*Above: For Bonaduz under rm fixes the cell. Name is proposed as Bonaduz rm; Goes in is Romansh.
Translated name is empty and Active is selected. Back was used without saving this form.*

If **Link existing** followed by a type name is offered, use it when the desired record already
exists. Search, inspect the candidate and any refusal reason, select an eligible record, fill
**Attributes of the relationship** if offered, and choose **Link**. This adds a connection instead of creating another record.

## When a new group is proposed

If the relationship's rules identify one group and it is missing, **Goes in** says **(will be
created)**. Saving creates that group, the record and its connection together.

When neither the rules nor existing records give a place, refiroo can propose a new group
named like the groups this view uses in other columns. Review **Name of the new …** and change
it if needed. Submit the creation form once to create both group and record. Where offered,
**Use an existing group instead** opens the group choices. Only places compatible with the
relationship's rules are offered. If no proposal or suitable place is available, resolve the
missing place in the app before creating the record. No model change is needed to accept a
proposed group.

## Add another record or reuse one

1. Open a filled cell and inspect the records already connected to the row. If the cell allows
   several records and the view permits creation, **Create** appears beside **Link existing**.
2. Choose **Create** when this is a new record. Choose its **Goes in** container and fill its
   fields as for an empty cell. The record is also listed in that container; it is not stored
   only inside the matrix.
3. Choose **Link existing** when the record already exists under this column. Search the
   candidates and read any reason beside a disabled choice. An existing link or a relationship
   limit can prevent selection. Select an eligible record, fill any **Attributes of the
   relationship**, then choose **Link**.
4. Check the refreshed cell. Linking adds a relationship to the existing record. Where the
   relationship permits reuse, that record can appear under several rows. Editing its own
   fields affects that shared record; each connection keeps its own relationship values.

**Example: a mapping matrix.** A code already connected to one row can also be linked to another
where the model permits it. Reuse keeps the same record identity. Create makes a separate record
and a new connection. After publication, connected systems see the corresponding connections
where their access includes them.

A filled cell that may hold only one record does not offer **Create**. Inspect or edit the
record already there. Empty, inactive and history-only cells can still offer creation where
configured. For example, a translation matrix may permit one counting name per language:
create a missing name, and edit an existing one rather than adding another counting name.
Publishing makes the new record and its connection available to connected systems that expose them.

## Correct an existing cell record

1. Remove a missing-cell filter before searching for an existing record. Find the row and open
   the cell under the intended column.
2. The cell opens a table with one row per linked record. Use its filter box to narrow record
   names and displayed record fields. Read the record's columns first, then the tinted
   **Attributes of the relationship** columns. Choose **Open** for its full page and history.
3. Edit the intended value in place. A Yes or no checkbox saves with one click. For another
   field, open its small editor and enter the value; Enter saves an ordinary single-line field,
   and Escape cancels. Clicking outside an unchanged record-field editor closes it. Leaving
   a relationship-value editor also attempts to save. Check the refreshed value and any error.
4. Check the condition for counting before switching an availability checkbox off: the cell
   can become Inactive without removing the record. Successful inline saves leave the table
   open. If a row disappears from a state-filtered matrix, select **Any state** to find it again.
5. To remove a permitted connection, choose **Unlink** on its row. Read the confirmation there:
   **Keep** cancels, **Unlink** confirms and keeps the related record. Choose **Close** when done.

![Cell table separating record fields from relationship values, with a value editor open](/docs/screens/matrix-cell-relationship-table-editor.png)

*Above: the Schmitten (GR) cell under wikidata-municipalities in Municipalities by system in
the Graubünden workspace. One code, Q65399, has Confirmed ticked and the Note editor open
with “Merged municipality, old code kept”. These values belong to its connection to the municipality.*

![An existing cell record open for editing with a content field and Active checkbox](/docs/screens/matrix-cell-editor.png)

*Above: Chur · rm opens the Romansh name Cuira with Active selected. Open Chur (rm) leads to the
full name record. Cancel leaves its fields unchanged.*

In a one-per-column counting rule, a change set can temporarily hold two counting records
for one cell. It shows **Conflict** with the count. Open it and inspect both records. Correct
which records meet the counting condition, or **Unlink** an unintended connection where
permitted. Unlink keeps the record. Validate the change set again before publishing; resolve
any remaining refusal through the affected record's full page. Live writes refuse a second
counting record. A conflict in proposed work is not a published extra value.
See [Cell states](/docs/use/relation-matrices/#cell-states).

For an **Inactive** cell, review existing records before adding another. For **Several**,
inspect the records before deciding whether anything needs changing; several may be allowed.
For **Conflict**, resolve the extra counting records before publication. Where **Unlink** is
offered, it asks for confirmation and keeps the related record; required ownership cannot be
removed this way. To add an owned record from its owner's full page instead, follow
[Create an owned related record](/docs/guide/use/relate-records/#create-an-owned-related-record).

For **History only**, inspect the read-only content from the named earlier publication.
Where **Create from this** is offered, it opens creation with those values supplied. Review
Name, container and fields before creating a new record; it does not undo a deletion or restore
the old record's identity and history.

## When a save or read fails

A duplicate refusal can offer **Open the … already here**. Inspect that record instead of
creating another. If **Changed elsewhere** appears, review the refreshed cell and your retained
input before retrying. If the record moved out of the cell, inspect the current contents first.
A loading failure needs a retry, not a new record to fill an apparently empty cell.

If actions are missing, check that the context is editable, you have **Edit live** or **Work
in change sets** as appropriate, and the model offers the intended action. Reader can inspect
cells. A matrix is not a promise that every visible cell can be edited.

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
