from pathlib import Path
from datetime import datetime
root = Path('guide')
changes = []
def replace(file, before, after):
 p = root / file
 text = p.read_text()
 assert text.count(before) == 1, (file, before)
 p.write_text(text.replace(before, after))
 changes.append((file, before, after))
replace('src/content/docs/use/workspaces.md',
'''**Adjust** keeps the draft and opens it in the model editor so you can change the structure
or how the workbook is read. If no list was found, or checking did not finish successfully,
**Create workspace** is unavailable; read any explanation and use **Adjust** to inspect the
draft.''',
'''**Adjust** keeps the draft and opens its [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
so you can change the structure or how the workbook is read. If no list was found, or checking
did not finish successfully, **Create workspace** is hidden; read any explanation and use
**Adjust** to inspect the draft.''')
replace('src/content/docs/guide/model/find-your-way-around-the-editor.md',
'''**Model authoring**. See [The model editor](/docs/model/the-model-editor/) for saved steps and states.''',
'''**Model authoring**. See [The model editor](/docs/model/the-model-editor/) for saved steps and states.
Choose **Editor** in the **Editor | Canvas** switch for the panes described here, or
[edit the same draft on the canvas](/docs/guide/model/edit-a-model-on-the-canvas/).''')
replace('src/content/docs/guide/model/find-your-way-around-the-editor.md',
'''4. Use **Add** for **Application…**, **Object type…**, **Attribute type…**, **Relation type…**''',
'''4. Use the **+** Add menu for **Application…**, **Object type…**, **Attribute type…**, **Relation type…**''')
replace('src/content/docs/guide/model/map-a-column.md',
'''[Workbook onboarding](/docs/model/workbook-onboarding/) for the source and profile.''',
'''[Workbook onboarding](/docs/model/workbook-onboarding/) for the source and profile.
You can also [map columns on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#make-object-types-and-map-columns)
by dragging them onto object types or attributes.''')
replace('src/content/docs/guide/model/read-lists-in-a-sheet.md',
'''Open its draft with **Model authoring**. See [Workbook onboarding](/docs/model/workbook-onboarding/).''',
'''Open its draft with **Model authoring**. See [Workbook onboarding](/docs/model/workbook-onboarding/).
On the [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/), you can also drag sheets onto
the board and choose how to read columns and heading rows.''')
replace('src/content/docs/model/models.md',
'''Continue with [The model editor](/docs/model/the-model-editor/) or
[Workbook onboarding](/docs/model/workbook-onboarding/) if your starting point is a spreadsheet.''',
'''Continue with [The model editor](/docs/model/the-model-editor/),
[edit a model on the canvas](/docs/guide/model/edit-a-model-on-the-canvas/), or
[shape a workbook on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
if your starting point is a spreadsheet.''')
replace('src/content/docs/model/models.md',
'''[model editor](/docs/model/the-model-editor/). [Consumer APIs](/docs/model/consumer-apis/) shapes''',
'''[model editor](/docs/model/the-model-editor/) or
[canvas](/docs/guide/model/edit-a-model-on-the-canvas/). [Consumer APIs](/docs/model/consumer-apis/) shapes''')
replace('src/content/docs/model/the-model-editor.md',
'''See [Models](/docs/model/models/) for the stages and permissions.''',
'''See [Models](/docs/model/models/) for the stages and permissions.
The **Editor | Canvas** switch offers two views of this same saved draft: the panes described
here, or a [board of object types and relationships](/docs/guide/model/edit-a-model-on-the-canvas/).
A draft opens in the view last used for it in this browser, or **Editor** if none is remembered;
workbook flows open **Canvas**.''')
replace('src/content/docs/model/the-model-editor.md',
'''The **Add** menu offers **Application…**, **Object type…**, **Attribute type…**,''',
'''The **+** Add menu offers **Application…**, **Object type…**, **Attribute type…**,''')
replace('src/content/docs/model/workbook-onboarding.md',
'''for the screen-by-screen task.''',
'''for the screen-by-screen task.
You can also [shape the workbook on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
by dragging sheets and columns onto the board; **Editor | Canvas** switches between views
of the same draft. For a separate workspace, **New workspace from a workbook** offers
**Adjust** to open that canvas before creating anything.''')
replace('sidebar/model.mjs',
'''      "guide/model/find-your-way-around-the-editor",''',
'''      "guide/model/find-your-way-around-the-editor",
      "guide/model/edit-a-model-on-the-canvas",''')
replace('sidebar/model.mjs',
'''      "guide/model/read-lists-in-a-sheet",''',
'''      "guide/model/read-lists-in-a-sheet",
      "guide/model/shape-a-workbook-on-the-canvas",''')
report = root / '_coverage/notes/CANVAS-GUIDE/page-changes.md'
report.write_text('# Existing page and sidebar changes\n\n' + '\n\n'.join(
 f'## {file}\n\nBefore:\n\n```text\n{before}\n```\n\nAfter:\n\n```text\n{after}\n```'
 for file, before, after in changes))
with (root / '_waves/progress/CANVAS-GUIDE.md').open('a') as f:
 f.write('\n'+datetime.now().astimezone().isoformat(timespec='seconds')+' — Finished the existing-page and sidebar unit: `use/workspaces.md`, `guide/model/find-your-way-around-the-editor.md`, `guide/model/map-a-column.md`, `guide/model/read-lists-in-a-sheet.md`, `model/models.md`, `model/the-model-editor.md`, `model/workbook-onboarding.md`, and `sidebar/model.mjs` under the guide content/sidebar roots. Corrected Adjust and the hidden creation action, added short canvas links and the shared switch/Add control, and placed both guides beside the related tasks. Exact before/after text is in `_coverage/notes/CANVAS-GUIDE/page-changes.md`; no steering file exists.\n')
