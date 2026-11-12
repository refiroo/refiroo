# Existing page and sidebar changes

## src/content/docs/use/workspaces.md

Before:

```text
**Adjust** keeps the draft and opens it in the model editor so you can change the structure
or how the workbook is read. If no list was found, or checking did not finish successfully,
**Create workspace** is unavailable; read any explanation and use **Adjust** to inspect the
draft.
```

After:

```text
**Adjust** keeps the draft and opens its [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
so you can change the structure or how the workbook is read. If no list was found, or checking
did not finish successfully, **Create workspace** is hidden; read any explanation and use
**Adjust** to inspect the draft.
```

## src/content/docs/guide/model/find-your-way-around-the-editor.md

Before:

```text
**Model authoring**. See [The model editor](/docs/model/the-model-editor/) for saved steps and states.
```

After:

```text
**Model authoring**. See [The model editor](/docs/model/the-model-editor/) for saved steps and states.
Choose **Editor** in the **Editor | Canvas** switch for the panes described here, or
[edit the same draft on the canvas](/docs/guide/model/edit-a-model-on-the-canvas/).
```

## src/content/docs/guide/model/find-your-way-around-the-editor.md

Before:

```text
4. Use **Add** for **Application…**, **Object type…**, **Attribute type…**, **Relation type…**
```

After:

```text
4. Use the **+** Add menu for **Application…**, **Object type…**, **Attribute type…**, **Relation type…**
```

## src/content/docs/guide/model/map-a-column.md

Before:

```text
[Workbook onboarding](/docs/model/workbook-onboarding/) for the source and profile.
```

After:

```text
[Workbook onboarding](/docs/model/workbook-onboarding/) for the source and profile.
You can also [map columns on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/#make-object-types-and-map-columns)
by dragging them onto object types or attributes.
```

## src/content/docs/guide/model/read-lists-in-a-sheet.md

Before:

```text
Open its draft with **Model authoring**. See [Workbook onboarding](/docs/model/workbook-onboarding/).
```

After:

```text
Open its draft with **Model authoring**. See [Workbook onboarding](/docs/model/workbook-onboarding/).
On the [canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/), you can also drag sheets onto
the board and choose how to read columns and heading rows.
```

## src/content/docs/model/models.md

Before:

```text
Continue with [The model editor](/docs/model/the-model-editor/) or
[Workbook onboarding](/docs/model/workbook-onboarding/) if your starting point is a spreadsheet.
```

After:

```text
Continue with [The model editor](/docs/model/the-model-editor/),
[edit a model on the canvas](/docs/guide/model/edit-a-model-on-the-canvas/), or
[shape a workbook on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
if your starting point is a spreadsheet.
```

## src/content/docs/model/models.md

Before:

```text
[model editor](/docs/model/the-model-editor/). [Consumer APIs](/docs/model/consumer-apis/) shapes
```

After:

```text
[model editor](/docs/model/the-model-editor/) or
[canvas](/docs/guide/model/edit-a-model-on-the-canvas/). [Consumer APIs](/docs/model/consumer-apis/) shapes
```

## src/content/docs/model/the-model-editor.md

Before:

```text
See [Models](/docs/model/models/) for the stages and permissions.
```

After:

```text
See [Models](/docs/model/models/) for the stages and permissions.
The **Editor | Canvas** switch offers two views of this same saved draft: the panes described
here, or a [board of object types and relationships](/docs/guide/model/edit-a-model-on-the-canvas/).
A draft opens in the view last used for it in this browser, or **Editor** if none is remembered;
workbook flows open **Canvas**.
```

## src/content/docs/model/the-model-editor.md

Before:

```text
The **Add** menu offers **Application…**, **Object type…**, **Attribute type…**,
```

After:

```text
The **+** Add menu offers **Application…**, **Object type…**, **Attribute type…**,
```

## src/content/docs/model/workbook-onboarding.md

Before:

```text
for the screen-by-screen task.
```

After:

```text
for the screen-by-screen task.
You can also [shape the workbook on the canvas](/docs/guide/model/shape-a-workbook-on-the-canvas/)
by dragging sheets and columns onto the board; **Editor | Canvas** switches between views
of the same draft. For a separate workspace, **New workspace from a workbook** offers
**Adjust** to open that canvas before creating anything.
```

## sidebar/model.mjs

Before:

```text
      "guide/model/find-your-way-around-the-editor",
```

After:

```text
      "guide/model/find-your-way-around-the-editor",
      "guide/model/edit-a-model-on-the-canvas",
```

## sidebar/model.mjs

Before:

```text
      "guide/model/read-lists-in-a-sheet",
```

After:

```text
      "guide/model/read-lists-in-a-sheet",
      "guide/model/shape-a-workbook-on-the-canvas",
```