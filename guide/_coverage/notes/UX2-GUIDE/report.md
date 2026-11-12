# UX2-GUIDE report

22 pages changed. Existing image references, alt text and screenshot files are unchanged. Several-field forms retain Save and Cancel. No commits or state-changing git commands were used.

## Checks

- `GUIDE_OUT=_build/UX2-GUIDE npm run build`: passed. The final `verify` also rebuilt the final text successfully: 257 pages.
- `GUIDE_OUT=_build/UX2-GUIDE npm run verify`: failed at coverage, with 11 uncovered workbook-canvas screen entries. Build, terms, brand, sidebar and inventory freshness passed first.
- `GUIDE_OUT=_build/UX2-GUIDE npm run check:links`: passed separately after the verification chain stopped: 76,039 local links and sources in 257 pages.
- A coverage comparison using the starting page text produced the identical 11 uncovered entries (see `before-uncovered.md` and `uncovered.md`). These concern ModelEditor’s Open as canvas and WorkbookCanvas menus, not single-field editing.
- Verification used TMPDIR under this wave’s notes and a Node preload (`redirect-generated.mjs`) that redirects only the generated uncovered report into these notes. No checker logic, inventory input or application source was changed.
- Source review and inspection of existing screenshots only; no browser behavior was exercised.

## Differences between the changelog and code

1. Settings text fields choose their own notices: client and group names use “Renamed.”, workspaces use “Workspace renamed.”, and `TextInPlace` offers Undo only when its caller supplies the undo action. Model editor cells save draft steps rather than a field-named notice. The pages retain their applicable Settings notice wording instead of promising “‹Field› saved” everywhere.
2. The existing direct Yes/No controls do not all use the new input save path. `RecordFlagCell` in `frontend/src/features/objects/EditableField.tsx` shows “‹Field›: Yes/No”, and offers Undo only for a value already present. The floating boolean branch of `RelationValueCell` calls `edit.save` instead of `saveValue` and does not emit the new field notice or Undo action. Non-boolean relationship inputs use `saveValue` and do offer Undo, including first values. The guide’s notice wording is scoped to inputs.
3. `InlineAttributeEditor.valueOf` still parses structured input through `attributeValueFromForm`; the JSON parser accepts literal null (and a quoted empty string). The changelog’s claim that the interface cannot set explicit empty values is therefore broader than the input code establishes. The guide describes what emptying a text input does and the removal of No value, without asserting that no structured input can express null. The persistence result for these JSON literals was not exercised.
4. When a record input has already unmounted, `InlineAttributeEditor` reports a failed save in a notice (“‹Field› was not saved: …”) because there is no field to keep open. The changelog’s under-field recovery describes an input that remains mounted.

## Screens to retake

- `stop-edit-field.png`: currently shows Cancel and Save below a normal numeric field. Retake the same numeric edit with the input alone, before saving.
- `save-conflict.png`: currently shows the No value tick and a Save button. Retake the version refusal with attempted input, current saved value, reason, Cancel and Save again, without No value.
- `model-type-required-edit.png`: currently shows Cancel and Save beneath the Required selection. Retake the opened choice without those buttons; selecting Yes or No saves immediately.

Also inspected `model-attribute-inline-edit.png`: it shows the old Save/Cancel selection, but no current guide page references it. It needs a retake if reused. The two matrix images already show a button-free input or a table without an open input; their Enter/Esc hint remains in the code, so no UX2 retake is required for them.

## Pages and exact changed passages

Before and after are folded onto one line each; unchanged surrounding text is omitted.

### `guide/src/content/docs/use/appearance-and-devices.md`

Before: Menus offer keyboard choices; Escape closes a menu or dialog. Enter saves a single-line inline edit and Escape cancels it. Escape also clears the tree search or Notifications search. Dialogs keep Tab within them and

After: Menus offer keyboard choices; Escape closes a menu or dialog. Leaving a single-value input with Tab saves it, as does Enter for a single-line field. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. A choice or a tick saves as it changes. Escape puts the old value back; an unchanged input closes without saving. Escape also clears the tree search or Notifications search. Dialogs keep Tab within them and


### `guide/src/content/docs/use/account.md`

Before: Select the passkey's name where it stands to edit it. Choose **Save** after changing it; the notice offers **Undo**. **Remove …**

After: Select the passkey's name where it stands to edit it. Leave the field or press Enter to save; Escape puts the old name back. An unchanged input saves nothing. The save notice offers **Undo**. If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it. **Remove …**


### `guide/src/content/docs/use/relation-matrices.md`

Before: one click. Other fields open a small editor over the cell, keeping the table in place. Enter submits an ordinary single-line value; Escape cancels. A click outside closes an unchanged record-field editor. Relationship-value editors also attempt a save when focus leaves them. Review any error before closing. A save refreshes the cell and leaves the table open.

After: one click. Other values become their input over the cell, keeping the table in place, without **Save** or **Cancel** buttons. Leaving a field by clicking elsewhere or pressing Tab saves it; Enter also saves a single-line value. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back; an unchanged input closes without saving or showing a notice. A saved input shows **‹Field› saved** with **Undo**, including for a relationship's value or a value set for the first time. Emptying an optional input and leaving it removes the value and shows **‹Field› removed** with **Undo**. A refusal keeps the input open with the reason and **Cancel** and **Save again** beneath it; leaving it again retries only after its input changes. Review any error before closing. A save refreshes the cell and leaves the table open.


### `guide/src/content/docs/use/relationship-tables.md`

Before: cell; Enter submits a single-line value, leaving the editor attempts a save, and Escape cancels. A Yes or no value saves when changed. A stale save shows the current saved relationship so you can review it before retrying. Tick existing relationships to set one attribute across them;

After: cell, without **Save** or **Cancel** buttons. Leaving the field by clicking elsewhere or pressing Tab saves it; Enter also saves a single-line value. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back. An unchanged input closes without saving or showing a notice. A Yes or no value saves when changed. A saved input shows **‹Field› saved** with **Undo**, including for a value set for the first time. Emptying an optional input and leaving it removes its value; **‹Field› removed** offers **Undo**. A refusal keeps the input open with the reason and **Cancel** and **Save again** beneath it. Leaving it again retries only after its input changes. A stale save shows the current saved relationship so you can review it before retrying. Tick existing relationships to set one attribute across them;

Before: a small editor over the cell: Enter submits a single-line value, Escape cancels, and leaving the editor attempts a save. The row refreshes after saving. If another person saved first,

After: their input over the cell: leaving it saves, as does Enter for a single-line value. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back; leaving an unchanged input saves nothing. A saved input offers **Undo** in **‹Field› saved**, or **‹Field› removed** when emptied. The row refreshes after saving. If a save is refused, the input and reason stay with **Cancel** and **Save again** beneath; leaving it again retries only after its input changes. If another person saved first,


### `guide/src/content/docs/use/records.md`

Before: text to copy does not start an edit. Choose **Save** or press Enter to save where offered; Escape cancels. The value becomes its field where it stands. Click an empty field to add a value. An editable Yes/No value in the details is a switch: changing it saves immediately. After saving a name or changing a field that already had a value, the save notice offers **Undo**. If the record changed again in the meantime, Undo is refused with “Undo was not possible: the record changed again in the meantime.” A field set for the first time has no previous value to restore. An optional value's trash button clears it immediately and offers **Undo** in the notice. Read-only fields have no editing control.

After: text to copy does not start an edit. The value becomes its field where it stands, without **Save** or **Cancel** buttons. Leaving the field, by clicking elsewhere or pressing Tab, saves it; Enter also saves a single-line value. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back. An unchanged input closes without saving or showing a notice. Click an empty field to add a value. An editable Yes/No value in the details is a switch: changing it saves immediately; in a list cell, the tick saves as soon as it changes. A choice from a list saves when selected. You can open another field while one is open; the first saves as you leave it.  Saving through an input shows **‹Field› saved** with **Undo**, including a value set for the first time: Undo makes that field **Not set** again. If the record changed again in the meantime, Undo is refused with “Undo was not possible: the record changed again in the meantime.” An optional value's trash button removes it immediately and offers **Undo** in the notice. Read-only fields have no editing control.  If a save is refused, the field stays open with your input and the reason beneath it. **Cancel** and **Save again** then appear under the reason. Correct the input or review the current saved value before choosing **Save again**; **Cancel** abandons the correction. Leaving a refused field again retries only after its input has changed.

Before: still opens the record. A success notice says whether you saved in Live or the open change set.

After: still opens the record. A saved value shows one **‹Field› saved** notice with **Undo**; the context band shows whether you are in Live or a change set. A relationship picker’s save notice names that context.

Before: To clear an optional field, use its remove-value button. It makes the value **Not set** and keeps the record, without asking for confirmation. The removal notice offers **Undo** to put it back. **No value** in the inline editor instead stores an explicit cleared value; it does not remove the field's stored entry. After any refusal or refresh problem, inspect the current saved state before another edit.

After: To clear an optional field, empty its input and leave the field, or use its remove-value button. Either removes the value without asking for confirmation and keeps the record. The field reads **Not set**, and **‹Field› removed** offers **Undo** to put it back. Leaving a required field empty is refused beneath it: **‹Field› needs a value.** **Cleared** and **Empty text** still appear when already stored. There is no **No value** choice in the input: emptying a text input removes its value rather than setting either state. After any refusal or refresh problem, inspect the current saved state before another edit.


### `guide/src/content/docs/guide/use/correct-a-record.md`

Before: that field where the value stands. Enter the verified replacement using the text, number or date control. A Yes/No value is a switch that saves as soon as you change it. Where **No value** is offered, it stores an explicit cleared value. To make an optional field **Not set** instead, cancel this edit and use its remove-value button. Removal saves immediately and offers **Undo**. 4. Choose **Save**. On success, the editor closes and the saved value appears. Check it before leaving. The save notice offers **Undo** for a name or a field that had a value before. If the record changed again in the meantime, Undo is refused with “Undo was not possible: the record changed again in the meantime.” Choose **Cancel** instead to abandon an unsaved correction.

After: that field where the value stands. Enter the verified replacement using the text, number or date control. A Yes/No value is a switch that saves as soon as you change it. To make an optional field **Not set**, empty its input and leave it, or use its remove-value button. The removal notice says **‹Field› removed** and offers **Undo**. A required field left empty stays open with **‹Field› needs a value.** beneath it. 4. Click elsewhere or press Tab to save. Enter also saves a single-line field; in text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back. There are no **Save** or **Cancel** buttons unless a save is refused. An unchanged input closes without saving or showing a notice. On success, the saved value appears and **‹Field› saved** offers **Undo**, including for a field set for the first time: Undo makes it **Not set** again. If the record changed again in the meantime, Undo is refused with “Undo was not possible: the record changed again in the meantime.” Check the result before leaving. You can open another field while one is open; the first saves as you leave it.

Before: trying again. A refused save has not applied your input.

After: trying again. A refused save has not applied your input. The field stays open with your input and the reason beneath it, followed by **Cancel** and **Save again**. Leaving it again retries only after its input has changed.

Before: 2. Decide whether your correction still applies. Adjust the input if needed. Choose **Save** again only after reviewing the current values, or **Cancel** to abandon your correction. than repeatedly pressing Save. If **Reload current value** appears, use it to load the

After: 2. Decide whether your correction still applies. Adjust the input if needed. Choose **Save again** only after reviewing the current values, or **Cancel** to abandon your correction. than repeatedly choosing **Save again**. If **Reload current value** appears, use it to load the


### `guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md`

Before: field, open its small editor and enter the value; Enter saves an ordinary single-line field, and Escape cancels. Clicking outside an unchanged record-field editor closes it. Leaving a relationship-value editor also attempts to save. Check the refreshed value and any error.

After: field, open its input and enter the value. Click elsewhere or press Tab to save; Enter also saves a single-line field. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back; an unchanged input closes without saving or showing a notice. A saved input shows **‹Field› saved** with **Undo**, including for a relationship's value or a value set for the first time. To remove an optional value, empty its input and leave it; **‹Field› removed** offers **Undo**. A refused input stays open with the reason and **Cancel** and **Save again** beneath it. Correct the input before leaving it to retry, or choose **Save again** after reviewing the reason. Check the refreshed value and any error.

Before: full name record. Cancel leaves its fields unchanged.*

After: full name record. Each field saves on its own; **Close** returns to the matrix.*


### `guide/src/content/docs/guide/model/arrange-applications-and-views.md`

Before: one of its views, then **Save**. To remove a non-matrix view, choose **Remove view**. Read

After: one of its views. Selecting it saves immediately. To remove a non-matrix view, choose **Remove view**. Read


### `guide/src/content/docs/guide/model/rename-or-re-key-an-element.md`

Before: 2. To change the displayed words, choose **Rename…** or select the editable title. The short form opens beneath the control. Enter **Name**; a record type also offers **Plural name**. Save, then check navigation and views using it. A shared attribute rename appears on every type that attaches it.

After: 2. To change the displayed words in place, select the editable title and enter the name. Leave the field or press Enter to save; Escape puts the old name back. An unchanged input saves nothing. If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it. The menu's **Rename…** instead opens a short form beneath its control: enter **Name** and, for a record type, **Plural name**, then choose **Save**. Check navigation and views using the name. A shared attribute rename appears on every type that attaches it.


### `guide/src/content/docs/guide/model/stop-serving-an-earlier-contract-version.md`

Before: enter the agreed calendar date and choose **Save**. Clear it and save to withdraw the announcement; the table shows a dash when no day is set. A date that is not a valid calendar day stays in the form with **Not saved** and the reason; the previously saved value remains unchanged. Correct it and save, or **Cancel**. The date announces the end

After: enter the agreed calendar date, then leave the field or press Enter to save. Escape puts the old date back; an unchanged input saves nothing. Clear it and leave the field to withdraw the announcement; the table shows a dash when no day is set. A date that is not a valid calendar day stays in the input with **Not saved** and the reason; the previously saved value remains unchanged. **Cancel** and **Save again** appear beneath the reason. Correct the date before leaving it to retry, or choose **Save again** after reviewing it. The date announces the end


### `guide/src/content/docs/guide/model/define-a-consumer-api.md`

Before: no value. Save the value or cancel. Use the served type: a text fallback cannot stand

After: no value. Leave the input or press Enter to save; Escape puts the old value back. An unchanged input saves nothing. If refused, review the reason beneath it and use **Save again** to retry or **Cancel** to abandon the edit. Use the served type: a text fallback cannot stand


### `guide/src/content/docs/guide/model/reuse-and-change-attributes.md`

Before: or **No**, then **Save**. The menu also offers **Make required** / **Make optional** and

After: or **No**. The choice saves immediately. The menu also offers **Make required** / **Make optional** and

Before: 2. Edit **Hidden** or **Help text** in the same Settings table and **Save**. These are shared presentation choices. Hidden leaves the field off record forms without deleting its data.

After: 2. Edit **Hidden** or **Help text** in the same Settings table. A Hidden choice saves as soon as you select it. Help text saves when you leave its input or press Enter; Escape puts the old text back. An unchanged input saves nothing. These are shared presentation choices. Hidden leaves the field off record forms without deleting its data.


### `guide/src/content/docs/guide/model/group-collections-in-navigation.md`

Before: should see when they open that collection, then **Save**. **Cancel** leaves it unchanged.

After: should see when they open that collection; the choice saves immediately. Escape closes an unchanged input without saving.


### `guide/src/content/docs/guide/model/add-a-record-type-and-fields.md`

Before: Select an editable setting cell, choose the value and use **Save**, or **Cancel** to leave it unchanged. A refusal on a released field means you must review its existing data and the migration

After: Select an editable setting cell. A choice from a list saves as soon as you select it; a text input saves when you leave it or press Enter. Escape puts the old value back. An unchanged input closes without saving. A refusal keeps your input and the reason open, with **Cancel** and **Save again** beneath it. A refusal on a released field means you must review its existing data and the migration


### `guide/src/content/docs/model/applications-and-views.md`

Before: page. Edit the cell in the group panel when the collection has more than one view, then **Save**. The choice belongs to that collection in this application; it does not change

After: page. Edit the cell in the group panel when the collection has more than one view; selecting a view saves immediately. The choice belongs to that collection in this application; it does not change

Before: view and Save. A collection's **Opens on** choice takes precedence when opening that collection.

After: view; selecting it saves immediately. A collection's **Opens on** choice takes precedence when opening that collection.


### `guide/src/content/docs/model/the-model-editor.md`

Before: change it with **Save**, or leave it with **Cancel**. Menus offer operations such as **Rename…**, A short operation, such as renaming or choosing a value type, opens beneath its control in a small popover. Pick several items there with **Apply**; save a single setting with **Save**. Longer forms and forms needing a preview open beside the page as sheets. Adding uses **Add** followed by the thing's name; moving uses **Move**. Confirmations remain small centred dialogs. The same validation and draft **Undo** apply whichever form is shown.

After: change its value. A choice from a list saves as soon as it is selected; a text input saves when you leave it or press Enter. Escape puts the old value back. An unchanged input closes without saving. Names edited in their headings save the same way. A refused input stays open with the reason and **Cancel** and **Save again** beneath it; leaving it again retries only after its input changes. Menus offer operations such as **Rename…**, A short operation, such as renaming or choosing a value type, opens beneath its control in a small popover. Pick several items there with **Apply**; use **Save** for a popover's settings. A value edited directly in its cell saves as described above. Longer forms and forms needing a preview open beside the page as sheets. Adding uses **Add** followed by the thing's name; moving uses **Move**. Confirmations remain small centred dialogs. The same validation and draft **Undo** apply whichever form is shown.

Before: For a collection with several views, edit **Opens on** in place and **Save** the choice.

After: For a collection with several views, edit **Opens on** in place; selecting a view saves the choice immediately.


### `guide/src/content/docs/model/managing-workspaces.md`

Before: 4. To change its displayed name later, select the name where it stands, enter the new name and choose **Save**. The save notice offers **Undo**.

After: 4. To change its displayed name later, select the name where it stands, enter the new name, then leave the field or press Enter to save. Escape puts the old name back; an unchanged input saves nothing. The save notice offers **Undo**. If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it.


### `guide/src/content/docs/model/consumer-apis.md`

Before: **Sunset day (YYYY-MM-DD)**, enter the calendar date and choose **Save**. Emptying it and saving withdraws the announcement; the table then shows a dash. A refused date stays in the form with **Not saved** and its reason; the saved date is unchanged. Correct it and save again, or **Cancel**. The day is announced to consumers in the response's Sunset

After: **Sunset day (YYYY-MM-DD)**, enter the calendar date, then leave the field or press Enter to save. Escape puts the old date back; an unchanged input saves nothing. Emptying it and leaving the field withdraws the announcement; the table then shows a dash. A refused date stays in the input with **Not saved** and its reason; the saved date is unchanged. **Cancel** and **Save again** appear beneath the reason. Correct the date before leaving it to retry, or choose **Save again** after reviewing the reason. The day is announced to consumers in the response's Sunset


### `guide/src/content/docs/guide/administer/manage-a-group.md`

Before: 1. Find the group by name and select it. Select its name or description where it stands, edit it and choose **Save**. The save notice offers **Undo**. This does not change who belongs or the group's grants.

After: 1. Find the group by name and select it. Select its name or description where it stands, edit it, then leave the field or press Enter to save. Escape puts the old text back; an unchanged input saves nothing. The save notice offers **Undo**. If refused, read the reason under the input, then correct it and choose **Save again**, or **Cancel** to abandon the edit. This does not change who belongs or the group's grants.


### `guide/src/content/docs/administer/clients.md`

Before: A client has a stable **Client ID**, a display name and a secret. Select the name where it stands and choose **Save** to rename it. The save notice offers **Undo**. Its ID stays the same, so the connected system needs no new configuration. **New client** asks for **Name**. **Add client** opens **Copy the client's secret**. Store the ID and secret securely before **I have copied it**; the secret is shown once. A new client starts

After: A client has a stable **Client ID**, a display name and a secret. Select the name where it stands, edit it, then leave the field or press Enter to save. Escape puts the old name back; an unchanged input saves nothing. The save notice offers **Undo**. If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it. Its ID stays the same, so the connected system needs no new configuration. **New client** asks for **Name**. **Add client** opens **Copy the client's secret**. Store the ID and secret securely before **I have copied it**; the secret is shown once. A new client starts


### `guide/src/content/docs/administer/people-and-groups.md`

Before: Select a group's name or description where it stands, then choose **Save**. The save notice offers **Undo**. **Delete group** asks for confirmation,

After: Select a group's name or description where it stands, edit it, then leave the field or press Enter to save. Escape puts the old text back; an unchanged input saves nothing. The save notice offers **Undo**. A refusal keeps the input and reason open with **Cancel** and **Save again**. **Delete group** asks for confirmation,


### `guide/src/content/docs/about/accessibility.md`

Before: A **Skip to main content** link bypasses repeated navigation. Labelled regions, semantic tables and trees, and named controls provide structure. Menus and dialogs support keyboard operation; dialogs keep focus inside while open and restore it when closed. Editors guard against leaving unsaved input behind.

After: A **Skip to main content** link bypasses repeated navigation. Labelled regions, semantic tables and trees, and named controls provide structure. Menus and dialogs support keyboard operation; dialogs keep focus inside while open and restore it when closed. Leaving a single-value input with Tab saves it, as does Enter for a single-line field. In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back. An unchanged input closes without saving. A refused input stays open with the reason and **Cancel** and **Save again** beneath it. Forms with several fields keep **Save** and **Cancel** and guard against leaving unsaved input behind.

