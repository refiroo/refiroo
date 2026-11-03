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
   treating it as the field content. Under **Goes in**, check the selected parent; if several
   places are offered, select the correct container under this column.
4. Fill the type's content fields. Set any checkbox or field that determines whether it counts
   according to the legend. Choose the form's **Create** action. On success, the dialog closes
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
exists. Search, inspect the candidate and any refusal reason, select an eligible record and
choose **Link**. This adds a connection instead of creating another record.

## Correct an existing cell record

1. Remove a missing-cell filter before searching for an existing record. Find the row and open
   the cell under the intended column.
2. A single editable record can open directly in its form. If several records are listed,
   inspect them and choose **Edit** beside the intended one. Follow **Open** and the record
   name if you need its full fields, relationships or history.
3. Correct the displayed fields. Check the condition for counting before changing an availability
   checkbox: switching it off can make the cell Inactive rather than remove its record.
4. Choose **Save** and check the refreshed cell. **Cancel**, or **Back** from a multi-record
   list, abandons the form. If a cell disappears from a state-filtered result after saving,
   select **Any state** and find the row again to inspect it.

![An existing cell record open for editing with a content field and Active checkbox](/docs/screens/matrix-cell-editor.png)

*Above: Chur · rm opens the Romansh name Cuira with Active selected. Open Chur (rm) leads to the
full name record. Cancel leaves its fields unchanged.*

For an **Inactive** cell, review existing records before adding another. For **Several** or
**Conflict**, inspect all counting records and decide which should count. Where **Unlink** is
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
