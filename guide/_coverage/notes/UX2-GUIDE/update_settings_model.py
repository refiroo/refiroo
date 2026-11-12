from helpers import update

update('use/account.md',[
('''Select the passkey's name where it stands to edit it. Choose **Save** after changing it; the notice offers **Undo**.''','''Select the passkey's name where it stands to edit it. Leave the field or press Enter to save;
Escape puts the old name back. An unchanged input saves nothing. The save notice offers **Undo**.
If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it.''')],
'Corrected passkey rename saving and refusal controls; retained Undo and removal instructions.')

update('administer/people-and-groups.md',[
('''Select a group's name or description where it stands, then choose **Save**. The save notice offers **Undo**.''','''Select a group's name or description where it stands, edit it, then leave the field or press
Enter to save. Escape puts the old text back; an unchanged input saves nothing. The save notice
offers **Undo**. A refusal keeps the input and reason open with **Cancel** and **Save again**.''')],
'Corrected group name and description saving and retry; retained group deletion behavior.')

update('guide/administer/manage-a-group.md',[
('''1. Find the group by name and select it. Select its name or description where it stands, edit it and choose **Save**. The save notice offers **Undo**. This does not change who belongs or the group's grants.''','''1. Find the group by name and select it. Select its name or description where it stands,
   edit it, then leave the field or press Enter to save. Escape puts the old text back;
   an unchanged input saves nothing. The save notice offers **Undo**. If refused, read the
   reason under the input, then correct it and choose **Save again**, or **Cancel** to abandon
   the edit. This does not change who belongs or the group's grants.''')],
'Corrected the group rename task and refusal recovery; membership and grant steps stay unchanged.')

update('administer/clients.md',[
('''Select the name where it stands and choose **Save** to rename it. The save notice offers **Undo**.''','''Select the name where it stands, edit it, then leave the field or press Enter to save.
Escape puts the old name back; an unchanged input saves nothing. The save notice offers **Undo**.
If refused, the input stays open with the reason and **Cancel** and **Save again** beneath it.''')],
'Corrected client renaming and refusal recovery while preserving client creation instructions.')

update('model/managing-workspaces.md',[
('''4. To change its displayed name later, select the name where it stands, enter the new name and choose **Save**. The save notice offers **Undo**.''','''4. To change its displayed name later, select the name where it stands, enter the new name,
   then leave the field or press Enter to save. Escape puts the old name back; an unchanged
   input saves nothing. The save notice offers **Undo**. If refused, the input stays open
   with the reason and **Cancel** and **Save again** beneath it.''')],
'Corrected workspace renaming and refusal recovery without altering creation or model activation.')

update('model/the-model-editor.md',[
('''change it with **Save**, or leave it with **Cancel**.''','''change its value. A choice from a list saves as soon as it is selected; a text input saves
when you leave it or press Enter. Escape puts the old value back. An unchanged input closes
without saving. Names edited in their headings save the same way. A refused input stays open
with the reason and **Cancel** and **Save again** beneath it; leaving it again retries only
after its input changes.'''),
('''save a single setting with **Save**.''','''use **Save** for a popover's settings. A value edited directly in its cell saves as described above.'''),
('''For a collection with several views, edit **Opens on** in place and **Save** the choice.''','''For a collection with several views, edit **Opens on** in place; selecting a view saves the choice immediately.''')],
'Updated model cell and heading saving, refusal controls and immediate opening-view selection; kept operation popover Save.')

update('guide/model/add-a-record-type-and-fields.md',[
('''Select an editable setting cell, choose the value and use **Save**, or **Cancel** to leave it
unchanged.''','''Select an editable setting cell. A choice from a list saves as soon as you select it;
a text input saves when you leave it or press Enter. Escape puts the old value back.
An unchanged input closes without saving. A refusal keeps your input and the reason open,
with **Cancel** and **Save again** beneath it.''')],
'Corrected editing setting cells and refusals; kept the add-field and effective-period forms.',
'model-type-required-edit.png shows the former Save and Cancel controls and needs a retake.')

update('guide/model/reuse-and-change-attributes.md',[
('''   or **No**, then **Save**.''','''   or **No**. The choice saves immediately.'''),
('''2. Edit **Hidden** or **Help text** in the same Settings table and **Save**. These are shared
   presentation choices.''','''2. Edit **Hidden** or **Help text** in the same Settings table. A Hidden choice saves as
   soon as you select it. Help text saves when you leave its input or press Enter; Escape
   puts the old text back. An unchanged input saves nothing. These are shared presentation choices.''')],
'Corrected immediate Required, Read-only and Hidden choices and Help text saving; retained the bounds popover Save.')

update('guide/model/arrange-applications-and-views.md',[
('''one of its views, then **Save**.''','''one of its views. Selecting it saves immediately.''')],
'Corrected immediate Default view selection; kept view forms and menus.')

update('model/applications-and-views.md',[
('''page. Edit the cell in the group panel when the collection has more than one view, then
**Save**.''','''page. Edit the cell in the group panel when the collection has more than one view;
selecting a view saves immediately.'''),
('''view and Save.''','''view; selecting it saves immediately.''')],
'Corrected Opens on and Default view selection saving; retained other view configuration forms.')

update('guide/model/group-collections-in-navigation.md',[
('''   should see when they open that collection, then **Save**. **Cancel** leaves it unchanged.''','''   should see when they open that collection; the choice saves immediately. Escape closes
   an unchanged input without saving.''')],
'Corrected immediate Opens on selection and removed obsolete Save/Cancel instructions.')

update('model/consumer-apis.md',[
('''   **Sunset day (YYYY-MM-DD)**, enter the calendar date and choose **Save**. Emptying it and
   saving withdraws the announcement; the table then shows a dash. A refused date stays in
   the form with **Not saved** and its reason; the saved date is unchanged. Correct it and
   save again, or **Cancel**.''','''   **Sunset day (YYYY-MM-DD)**, enter the calendar date, then leave the field or press Enter
   to save. Escape puts the old date back; an unchanged input saves nothing. Emptying it and
   leaving the field withdraws the announcement; the table then shows a dash. A refused date
   stays in the input with **Not saved** and its reason; the saved date is unchanged.
   **Cancel** and **Save again** appear beneath the reason. Correct the date before leaving
   it to retry, or choose **Save again** after reviewing the reason.''')],
'Corrected single-date editing, emptying and refused-save recovery for earlier contract versions.')

update('guide/model/stop-serving-an-earlier-contract-version.md',[
('''   enter the agreed calendar date and choose **Save**. Clear it and save to withdraw the
   announcement; the table shows a dash when no day is set. A date that is not a valid
   calendar day stays in the form with **Not saved** and the reason; the previously saved
   value remains unchanged. Correct it and save, or **Cancel**.''','''   enter the agreed calendar date, then leave the field or press Enter to save. Escape puts
   the old date back; an unchanged input saves nothing. Clear it and leave the field to
   withdraw the announcement; the table shows a dash when no day is set. A date that is not
   a valid calendar day stays in the input with **Not saved** and the reason; the previously
   saved value remains unchanged. **Cancel** and **Save again** appear beneath the reason.
   Correct the date before leaving it to retry, or choose **Save again** after reviewing it.''')],
'Corrected announcing and withdrawing a sunset date and recovering after an invalid date; retained stop-serving confirmation.')
