---
title: How workbook proposals are made
description: Understand the patterns behind proposed types, lists, keys and relationships, and check their limits.
reader: model-admin
---

With **Model authoring**, use the evidence behind a workbook proposal to decide whether it describes
your data correctly. The rules look at column values, repetition, headings and shared identifiers. They do not know
what a stop, municipality or operator means. Choosing to propose from a workbook applies the
suggestions as draft steps; it does not install a model or load records.

Select a **Proposed** element, read **Proposed because**, then open **Evidence**. Use
[Map a column](/docs/guide/model/map-a-column/) to change its interpretation, or
[Propose again](/docs/guide/model/propose-again-with-a-newer-workbook/) to reconsider the file.
Your manual edits are retained. The percentages below are recognition rules, not confidence
scores, and cannot be tuned in the mapping form.

## Keys and names

The first suitable fully filled, distinct column is proposed as the key. Text without spaces
and whole numbers take precedence over a GUID. A GUID is the fallback when every row has a
different one. The proposed name is another text column filled on at least 95% of rows, excluding
code-like columns and lookups; a heading containing “name” takes precedence. If a text key would
leave no name beside a GUID, the GUID becomes the key and the text becomes the name.

Check that the proposed key stays stable between files. A different value on every row is not
proof that a column identifies the same real record next month.

## Lists, parents and connections

| Shape in the workbook | What refiroo proposes and what to check |
| --- | --- |
| A code and its name | A list with code and name, or the row's own identifying fields. The rule allows at most 1.5 names per code on average and expects each name to belong to one code in at least 98% of groups. |
| Different names for one code | A value map from less frequent names to the most frequent one. Check the correct spelling before accepting a majority choice. |
| A repeated text column | A parent when there are at most a third as many distinct values as rows and other columns stay constant in at least 98% of its groups. A constant code or GUID can identify the parent. |
| More than one repeated parent candidate | The first becomes the parent; further ones become related lists. A record has one parent. Empty parent cells allow records at the top level. |
| Numbered level headings, or references to the same sheet's keys | A hierarchy. A parent-code column needs at least 90% of its values to match the sheet's keys; empty parent codes identify roots. |
| A few repeated text values | A lookup list when there are at most 50 distinct values and no more than 20% as many values as filled cells. An ordinary text field remains an alternative. |
| Values matching another sheet | A relationship when at least 90% of distinct values match the other sheet's keys or names. One referenced record per row can still be shared by many rows. |
| Several values in one cell | A many-valued relationship when a delimiter occurs in at least 10% of cells and at least 80% of its parts also occur as whole values. Check the delimiter before splitting. |
| Several Yes/No columns | One relationship to a list whose members come from the headings. Recognised sets are Y/N, yes/no, X/empty, true/false and 1/0. The columns need not be adjacent. A nearby multi-valued column can join the set. A lone Yes/No column becomes a field with a value map. |
| A GUID column left over | An external identifier. Check which related record and system it describes rather than relying on its shape alone. |

Text averaging more than 60 characters is treated as description text, not a parent, lookup or
code's name. Remaining columns become typed attributes; a candidate key can make one unique.
Placeholder suggestions map values such as N/A, ?, TBC and a dash to empty. Read the affected
counts: an intentional value must not disappear because it resembles a placeholder.

Matching headers and value types across sheets can share an attribute definition. It is proposed
as unique only when the sheets do not share its values. Two or more lists proposed from a sheet
can be gathered into a navigation group. Generated labels come from headings and sheet names,
with underscores and joined capitals separated; you can rename them all. When table headings repeat,
the proposal leaves a later same-named column out and reports a warning. Review those columns
manually; the mapping and loading facilities can distinguish repeated headings by numbered names.

## Names in several languages

A sheet with no key can describe names for another sheet's records when it has at least two
ISO 639-1 language codes or English language names and at least 90% of the reference column's
distinct values match that sheet's keys, once per language. Columns such as Name (de) and Name FR
can also be recognised as language variants of a name column.

Repeated base values can reveal translated columns even without useful headings. The translation
must have 80%–125% as many distinct values as the base, at least 80% correspondence in each
direction, and at most half its rows identical to the base. A recognised language in the heading
names it; otherwise the proposal uses **Language 1**, **Language 2**, and so on. Rename these
before loading. A translation of a type's name becomes a related name record; translations of
other base fields remain attributes. Similar-looking columns alone do not establish their language.

## Sheets that describe fields

A workbook can describe a model rather than contain its records. refiroo checks this shape first,
then excludes the description and the referenced list sheets from ordinary table interpretation.
It looks for a filled, distinct text column naming fields, a column with at least 80% recognised
field-type words and a target column with at least half its cells naming other sheets. The
recognition uses values, rather than requiring particular headings. Automatic description detection
checks sheets with up to 1,000 data rows; type-word and target columns must each have at most
200 distinct values to be considered. Outside these bounds, map the file deliberately rather
than expecting this proposal.

| Field-type words | Meaning |
| --- | --- |
| lookup, list, reference, select | Choose one record from the target list. |
| multi, multiple, multi-select, multi-lookup | Choose several records. |
| flag, yes/no, boolean, checkbox | A member of a target flag set; a Yes/No field without a target. |
| text, string | Text field. |
| long text, description | Long text field. |
| number, integer | Whole number field. |
| decimal | Decimal field. |
| date | Date field. |

An unrecognised word produces a text field and a warning. The described type takes the sheet's
name. Target sheets supply lists using their IDs and names. Placeholder IDs are skipped; a sheet
holding only placeholders produces a list to define, with no loaded records and a warning. A target
without a sheet produces an empty list too. Placeholder recognition here also includes “to be
defined”, “to be decided” and “to be confirmed”.

Review the resulting type and empty lists before installing. A description does not create
instances of the type it describes.

## Extend a model using another file

Files meet through the stored model and records. Install and load the first file before using
**Additions to the model** for a second file that refers to its records. Choose the comparison
workspace deliberately; without an explicit workspace the comparison uses the default workspace.

A sheet can match a type by its name, by at least 50% overlap between its keys and stored unique
values or names, or by headings matching at least half of the type's field and relationship names
(at least two). Name comparison ignores case, accents, punctuation and ordinary plural endings.
A same-named attribute is reused when at least 95% of cells fit its value type; a shared global
attribute is preferred to a new one. Existing allowed relationships are reused.

A code column matching at least half of a stored unique field's values takes precedence over name
matching. Missing IDs are reported with their rows; creating missing records is an alternative,
not an assumed repair. If an ID has a different name in the file, the stored name stands by default;
loading the new name is an alternative. Resolve drift explicitly before loading.

## Sheets laid out as lists

When a sheet has several blocks, a block with at least three columns and 60% of the sheet's
cells is treated as its main table. Other blocks are named in warnings. Without a main table,
a sheet laid out for reading can be interpreted list by list when no more than 2,000 rows hold
cells. This also covers several lists stacked in a block of at most two columns. Colour, bold
text and merged-cell formatting do not determine the structure.

Empty columns and rows separate ranges. A row above a range can be its header; a single cell
above several neighbouring lists can be their shared title. Text averaging over 60 characters
is treated as prose rather than list data. Inspect **Under**, **Cells** and **Note** to confirm
the inferred titles and boundaries. **Proposed**, **Loaded** and **Not loaded** distinguish
interpretations in the source pane; Loaded here means a source reads the list, not that its
records have already been published.

The first column supplies names and identifies list items. Within the range, a Yes/No column
becomes a field; several such columns form a flag set. A text column filled on at least 80%
of the rows with names can be proposed as translated names. A language word in its heading
names that language; otherwise you must rename the proposed language. Columns containing only
a heading are reported and not read; remaining columns become fields.

English note words such as “multiple answers”, “multiple choice”, “multi-select” or “several”
indicate several choices. “Single answer”, “single choice” and “one answer” indicate one.
“Free field” or “free text” identifies free answers rather than a list. A header with no values
or a free-answer range proposes no list and raises a warning. Recognised note rows are skipped,
and their note becomes the type's description. An extra heading row in a flag list can also be
recognised and skipped; it does not become a record.

Two or more lists beneath one innermost title can form a navigation group. At least three with
the same column kinds under one title, or none, also offer **Read these N lists as one list under
their headers**. The initial proposal keeps them separate because shape alone cannot tell
whether their headings are categories or independent lists.

Follow [Read lists in a sheet](/docs/guide/model/read-lists-in-a-sheet/) to adjust a range or
choose that alternative. Adjusting a range keeps column bindings by their column letters.
**Don't load this list** removes its source and can remove its proposed type when nothing else
loads, relates to or contains it. Review History and Issues after that choice. Always finish
with the [current dry run](/docs/guide/model/check-a-workbook-with-a-dry-run/).
