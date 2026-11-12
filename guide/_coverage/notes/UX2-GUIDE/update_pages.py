from pathlib import Path
from datetime import datetime

def update(name, changes, summary, uncertainty='None.'):
    steer=Path('guide/_waves/steer/UX2-GUIDE.md')
    if steer.exists():
        raise SystemExit('Read and apply steering before continuing: '+steer.read_text())
    p=Path('guide/src/content/docs')/name
    s=p.read_text()
    for a,b in changes:
        assert a in s,(name,a)
        s=s.replace(a,b,1)
    p.write_text(s)
    with Path('guide/_waves/progress/UX2-GUIDE.md').open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{p}`: {summary} No steer file exists. Uncertainties: {uncertainty}\n')

update('use/relationship-tables.md',[
('''cell; Enter submits a single-line value, leaving the editor attempts a save, and Escape cancels.
A Yes or no value saves when changed. A stale save shows the current saved relationship so you
can review it before retrying.''','''cell, without **Save** or **Cancel** buttons. Leaving the field by clicking elsewhere or pressing
Tab saves it; Enter also saves a single-line value. In text of several lines, Enter adds a new
line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back. An unchanged
input closes without saving or showing a notice. A Yes or no value saves when changed.
A saved input shows **‹Field› saved** with **Undo**, including for a value set for the first
time. Emptying an optional input and leaving it removes its value; **‹Field› removed** offers
**Undo**. A refusal keeps the input open with the reason and **Cancel** and **Save again**
beneath it. Leaving it again retries only after its input changes. A stale save shows the
current saved relationship so you can review it before retrying.'''),
('''a small editor over the cell: Enter submits a single-line value, Escape cancels, and leaving
the editor attempts a save. The row refreshes after saving. If another person saved first,''','''their input over the cell: leaving it saves, as does Enter for a single-line value. In text
of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts
the old value back; leaving an unchanged input saves nothing. A saved input offers **Undo**
in **‹Field› saved**, or **‹Field› removed** when emptied. The row refreshes after saving.
If a save is refused, the input and reason stay with **Cancel** and **Save again** beneath;
leaving it again retries only after its input changes. If another person saved first,''')],
'Unified row and grid field-saving instructions, removal and refusal recovery; added relationship-value Undo.',
'The grid’s direct Yes/No control bypasses the input save notice and Undo; reported separately.')

update('use/relation-matrices.md',[
('''one click. Other fields open a small editor over the cell, keeping the table in place. Enter
submits an ordinary single-line value; Escape cancels. A click outside closes an unchanged
record-field editor. Relationship-value editors also attempt a save when focus leaves them.
Review any error before closing. A save refreshes the cell and leaves the table open.''','''one click. Other values become their input over the cell, keeping the table in place, without
**Save** or **Cancel** buttons. Leaving a field by clicking elsewhere or pressing Tab saves it;
Enter also saves a single-line value. In text of several lines, Enter adds a new line and
Ctrl+Enter (Cmd+Enter on a Mac) saves. Escape puts the old value back; an unchanged input
closes without saving or showing a notice. A saved input shows **‹Field› saved** with **Undo**,
including for a relationship's value or a value set for the first time. Emptying an optional
input and leaving it removes the value and shows **‹Field› removed** with **Undo**.
A refusal keeps the input open with the reason and **Cancel** and **Save again** beneath it;
leaving it again retries only after its input changes. Review any error before closing.
A save refreshes the cell and leaves the table open.''')],
'Applied the same saving and retry rules to record and relationship inputs in the cell table, with removal and Undo.',
'The direct Yes/No controls retain different notices; existing matrix editor screenshots need retakes.')

update('guide/use/fill-in-a-relation-matrix.md',[
('''   field, open its small editor and enter the value; Enter saves an ordinary single-line field,
   and Escape cancels. Clicking outside an unchanged record-field editor closes it. Leaving
   a relationship-value editor also attempts to save. Check the refreshed value and any error.''','''   field, open its input and enter the value. Click elsewhere or press Tab to save; Enter also
   saves a single-line field. In text of several lines, Enter adds a new line and Ctrl+Enter
   (Cmd+Enter on a Mac) saves. Escape puts the old value back; an unchanged input closes
   without saving or showing a notice. A saved input shows **‹Field› saved** with **Undo**,
   including for a relationship's value or a value set for the first time. To remove an
   optional value, empty its input and leave it; **‹Field› removed** offers **Undo**.
   A refused input stays open with the reason and **Cancel** and **Save again** beneath it.
   Correct the input before leaving it to retry, or choose **Save again** after reviewing
   the reason. Check the refreshed value and any error.'''),
('''full name record. Cancel leaves its fields unchanged.''','''full name record. This earlier editor shows Cancel; in the current cell table, leaving a
changed field saves it and Escape puts the old value back.''')],
'Corrected the cell-editing steps and the old editor caption while preserving its image reference.',
'Both existing cell-editor images need retakes for their earlier controls.')

update('use/appearance-and-devices.md',[
('''Menus offer keyboard choices; Escape closes a menu or dialog. Enter saves a single-line inline
edit and Escape cancels it. Escape also clears the tree search or Notifications search.''','''Menus offer keyboard choices; Escape closes a menu or dialog. Leaving a single-value input
with Tab saves it, as does Enter for a single-line field. In text of several lines, Enter adds
a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves. A choice or a tick saves as it changes.
Escape puts the old value back; an unchanged input closes without saving. Escape also clears
the tree search or Notifications search.''')],
'Updated keyboard saving, multiline input, immediate choices and Escape behavior.')

update('about/accessibility.md',[
('''Editors guard against leaving unsaved input behind.''','''Leaving a single-value input with Tab saves it, as does Enter for a single-line field.
In text of several lines, Enter adds a new line and Ctrl+Enter (Cmd+Enter on a Mac) saves.
Escape puts the old value back. An unchanged input closes without saving. A refused input
stays open with the reason and **Cancel** and **Save again** beneath it. Forms with several
fields keep **Save** and **Cancel** and guard against leaving unsaved input behind.''')],
'Replaced the general editor statement with the current single-field keyboard behavior and retained the form distinction.')
