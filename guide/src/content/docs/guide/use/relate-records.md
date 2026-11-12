---
title: Relate records
description: Connect records, replace a single connection and remove an optional relationship.
reader: steward
---

Connect two records using a relationship declared by the model. See
[Relationships](/docs/use/relationships/) for candidates, ownership and required connections.

## Open the relationship section

1. Open an application in the current workspace and [find the record](/docs/guide/use/find-records/).
   Check its name, identifying fields and path.
2. Check **Live** for an immediate change, or [open a change set](/docs/guide/use/prepare-and-publish-a-change-set/)
   to prepare work for publication. Check the banner before editing.
3. Scroll to the relationship section you need. Its heading describes the connected records.
   Read existing entries before adding another. **No relationships yet** means the section is
   empty; a loading error needs a retry instead.

![Relationship sections with add, change and delete controls](/docs/screens/relationships-stop.png)

*Above: Chur Wiesental in Network has Modes, Operator and System codes sections. Modes permits
several connections; Operator permits one. Further sections continue below the capture.*

## Connect an existing record

1. Choose **Add relationship**, or **Set** followed by the relationship name when the empty
   section permits just one. The connection form opens in the middle of the window on a desktop.
2. Where the relationship is known, the form says **Add a** followed by the related type **to** this record (or **Add an** where appropriate). Read the relationship named beneath it. If several choices are offered, choose the intended type and relationship under **What to add** before searching.
3. Under the related record type's name, type part of the related record's name or a searchable field. Read any
   hint explaining which records are offered. Select a result, checking its path. Typing alone
   leaves **Nothing selected** and does not enable saving.
4. Fill any fields carried by the relationship. These describe the connection, rather than
   changing the other record's fields.
5. Choose **Add** followed by the related type's name, or **Set** in the single-connection form. On success the dialog closes;
   check that the connected record appears in the section. **Cancel** abandons the connection;
   if asked to discard unsaved changes, confirm only if that is what you intend.

![The Add Mode dialog with the relationship name, candidate search and Add Mode action](/docs/screens/relationship-picker-mode.png)

*Above: Add Mode for Chur Wiesental names Served by mode and offers candidates such as Boat and Bus. Nothing is selected, so Add Mode is unavailable.*

If a record is missing, clear or shorten the search and check the workspace, context, type and
candidate hint. A model can limit candidates by their own or their ancestors' fields. Ask a
model administrator about the rule if the expected record is still unavailable. A refused save
may report a duplicate, a number limit or changed data; resolve that reason before retrying.

## Replace a single connection

1. In a section that allows one related record, choose its **Change** action. Read **Now:**
   to confirm the connection you intend to replace.
2. Search and select the replacement under the related type's name. Check its identifying fields and path.
   The currently connected record is not offered as its own replacement.
3. Choose **Change**. The replacement is saved together; check the section's new entry.
   Choose **Cancel** to keep the existing connection.
4. If the dialog says the relationship changed after the list was read, close it and review
   the refreshed section. Reopen **Change** only if replacement is still appropriate.

![A replacement dialog identifying the current record and offering other candidates](/docs/screens/relationship-picker-operator.png)

*Above: Operated by currently connects Chur Wiesental to Rhätische Bahn. The dialog offers
replacement operators. It was cancelled, leaving Rhätische Bahn connected.*

Where a relationship has its own fields, its **Edit** action opens those fields. Correct them
and choose **Save**; use **Change** when replacing the related record itself. A version refusal
requires reviewing the current saved connection before saving again.

## Remove an optional connection

1. Find the exact relationship row and check both record names, especially where a section contains several connections.
2. Choose **Remove relationship**. It removes the connection immediately, without a confirmation; both records remain.
3. Check the refreshed section. The removal notice offers **Undo** to create the connection again. If removal is refused because it is required, review the intended correction and use a replacement where allowed.

![An empty Modes panel after a relationship removal with Undo in the notice](/docs/screens/relationship-delete-confirm.png)

*Above: Chur Wiesental’s Modes panel is empty after the Train connection was removed. The removal notice offers Undo; the connection was restored after this picture.*

To change containment, [move the record](/docs/guide/use/arrange-records-in-a-tree/).
Deleting a record has a different impact; see [Records](/docs/use/records/#deleting-a-record).

## Create an owned related record

Some sections offer an add action named after the related type rather than connecting an
existing record. Use it when you need a new dependent record.

1. Choose that section's add action. Check the new record form and its already supplied
   connection to the source record.
2. Under **Parent**, search and select the intended container where requested. Check the
   selected path; search text alone does not select it.
3. Fill **Name** and the type's other fields. Set any field that determines whether the record
   counts as current according to the model's rule.
4. Choose **Add** followed by the new record type's name and check the new entry in the original section. Correct any reported
   missing values or duplicate before retrying. **Cancel** leaves without creating the record.

![A new related record form with parent choices and its owner already supplied](/docs/screens/stop-add-translation.png)

*Above: Add Name translation on Chur Wiesental opens a form with Translates already set to
that stop. Parent offers languages; Name, Translated name and Active describe the new record.
The form was cancelled. This is an example of creating an owned record.*

If editing actions are absent, check your context and
[record permissions](/docs/use/records/#who-may-read-and-change-records). A publication is read-only;
a Reader can inspect connections but cannot change them.

A lock on a row explains why it cannot be deleted or changed independently. Parent connections
are maintained by moving the record. Beside a tree, **Connected** chips open related records;
open the full record page to use the relationship tables and their tooltip-labelled icons.

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
