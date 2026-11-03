---
title: The model editor
description: Find definitions, edit their structure, preview layouts and review the draft history.
reader: model-admin
---

Use the model editor to change a draft through named actions. Each saved action becomes a step
in its history. You need **Model authoring**; applying the result also needs release access.
See [Models](/docs/model/models/) for the stages and permissions.

## Find your way around

The header identifies the draft, its base release, draft version and validation state. **Undo**
and **Redo** act on saved steps. **Close** keeps the draft and its proposals. The main confirmation
is **Install and activate…**, or **Apply to this workspace…** when you came from a workspace.

The model pane lists applications and their types in a hierarchy, followed by **Relation types**,
**Attribute types** and **Relationship matrix**. A type listed in several applications still has
one definition. Select an element to see its details in the centre. Use the plus button to add
an element, or the selected element's menu for its operations.

![Draft editor with its header, model pane and Issues and history bar](/docs/screens/model-editor-overview.png)

*Above: Guide draft starts from the Graubünden release. The model pane lists Network, Systems and
Names; no element is selected in the centre.*

An application shows its types, where they stand, field and relationship counts, views and
navigation groups. A type shows **Attributes** and **Relations**. Select an editable cell to
change it with **Save**, or leave it with **Cancel**. Menus offer operations such as **Rename…**,
**Move to…**, adding fields and allowing relationships.

| Mark | Meaning |
| --- | --- |
| Released | The element is unchanged from the draft's base release. |
| New | The draft adds the element. |
| Changed | The element, or something within it, differs from the base release. |
| Proposed | The element still reflects the engine's suggestion from a source. Review it before relying on it. |

Released keys are fixed. Renaming a label does not change that identity. Removing, moving,
splitting or merging a type can be refused when stored data uses it; read the impact reported by
the server. Changing a draft does not move live records.

## When there is a workbook

A workbook adds a **Source** pane with sheets, columns, mapping states and statistics. Select a
column to see what it feeds; select a type to see the columns that feed it. **Map to…** in the
column menu provides an alternative to dragging it onto the model. A proposal's **Proposed because**
explains the suggestion; **Evidence** opens the supporting observations. You can change or undo
proposals. The original workbook is not rewritten.

While profiling is running, wait for the sheets and columns. If profiling fails, read the reason
and upload the workbook again from the draft menu. Once columns are mapped, the **Dry run** tab
checks their rows after edits. Narrow screens present the panes as tabs.

For source selection, mapping and loading, follow
[Load a workbook](/docs/guide/model/start-a-draft-from-a-workbook/). The source pane is absent from a draft with
no attached workbook.

## Preview and layout

**Preview** on a type shows the draft's layout over records read live from a workspace running
its model. Its data controls are disabled: previewing writes nothing. Check the workspace and
record selectors; an empty preview for a new model does not mean the draft failed.

![Type preview with a workspace selector and disabled record controls](/docs/screens/model-type-preview.png)

*Above: Stop's draft layout is shown over a live Graubünden record. Step-free access is still a
draft addition, with no live value.*

**Edit layout** opens the layout editor. **Record page** arranges panels and fields in the main
and side regions. **Table** chooses columns, filters and the default sort. Layout changes are
saved draft steps too; they reach the workspace's record screens after activation.

Follow [Add a record type and fields](/docs/guide/model/add-a-record-type-and-fields/),
[Add a relationship](/docs/guide/model/add-a-relationship/) and
[Arrange applications and views](/docs/guide/model/arrange-applications-and-views/) for the actions.

## History, undo and other editors

Expand **Issues and history** and choose **History**. Steps appear newest first, with the action,
author, time and whether they are applied or undone. A single step may contain related actions,
such as creating an attribute and attaching it to a type.

![History showing two applied steps and their Undo actions](/docs/screens/model-history.png)

*Above: Guide draft records adding Step-free access and allowing Inspected by as two saved steps.*

**Undo** reverses a step in the draft; **Redo** restores an undone step. A new edit clears what
can be redone. If later steps depend on the step you undo, refiroo names them and offers to undo
them together. Read that list before confirming. Undoing a draft step never rewrites an installed
release or reverses already published record changes.

If another administrator edits the draft first, your older edit can be refused. The **Another change came first** notice lists the steps applied since you opened it, and the
model below shows the newer version. Read those steps, then choose **Apply mine again** if your
change still belongs, or **Discard mine** to leave it out. A further intervening edit can refuse
the retry too.

## Compare before releasing

The install confirmation summarises changed applications, types, fields and relationships against
the draft's base release. A draft without a base is compared with the newest release of its own
model, if one exists; a wholly new model has no earlier definitions to compare.

Read those differences together with validation, stored-data compatibility and **Consumer APIs**.
A comparison of definitions does not prove that the workspace's existing records fit. The separate
checks are explained in [Issues and dry runs](/docs/model/issues-and-dry-run/).

## Header, keyboard and phone controls

Open **About this draft** for its base release (or **A new model**), edit version and validity.
The version increases with each saved step. Change the editable draft title to rename the draft;
this does not rename a release. **Saved as you go** means closing keeps the draft and proposals.

The **Add** menu offers **Application…**, **Object type…**, **Attribute type…**,
**Relation type…** and **Navigation group…**. In an empty draft, add an application first.
An operation opens a dialog; **Not applied** means the attempted step did not save. Correct its
reported cause, or cancel. **Delete draft…** in **More actions** asks for confirmation and removes
only the editable draft, its steps and attached source, leaving installed releases unchanged.

In the model pane, Up/Down and Home/End move focus; Enter or Space selects. Right and Left unfold
and fold sections. Shift+F10 or the context-menu key opens the selected row's operations.
On a phone, tabs replace the panes. Use the menus: model-editor drags are off on phones.
**Earlier steps** in History reads more than the initial saved-step list.

**Relationship matrix** shows every type as a row and column, with rows as the from end.
Cells list permitted relationships and their number limits; containment reads **contains**.
Move with arrow keys and select a pair with Enter. The selected pair's panel offers its existing
relations' menus and an action to allow another. It can be resized.

## Consumer contracts and the structured-document view

The **Consumer APIs** tab holds the contracts other systems read. Add a consumer API with its
name and the types to expose, then inspect **Types and related**, **Fields**, **Operations**,
**Filters**, **Schema** and **Message example**. Fields and related lists shape the public data;
operations choose what consumers can read. The compatibility status says whether a higher
contract version is needed. Raising that version is separate from numbering the model release.
Review breaking changes with the consuming teams before activation.

The header also offers **Open as JSON** for specialist model authors who maintain the complete
structured model document. Normal screen-based editing does not need it. Both routes edit the
same draft and record saved steps; document edits appear as **JSON edit** in History. Use
**Export JSON** there, or on an installed release, to download its document. If that view reports
a newer saved draft, preserve your local work with **Copy local JSON** before
**Reload saved version**. Reloading does not merge the two versions.

## Next tasks

Use [Find your way around](/docs/guide/model/find-your-way-around-the-editor/) for keyboard and phone
navigation, [Undo and review history](/docs/guide/model/undo-and-review-the-draft-history/) for saved
steps, and [Work on a draft with others](/docs/guide/model/work-on-a-draft-with-others/) for version
conflicts. [Delete a draft](/docs/guide/model/delete-a-draft/) removes only editable work.

[Types, attributes and relations](/docs/model/types-attributes-relations/),
[Applications and views](/docs/model/applications-and-views/),
[Record pages and tables](/docs/model/record-pages-and-tables/) and
[Consumer APIs](/docs/model/consumer-apis/) explain each part of the editor.
The specialist [JSON view](/docs/model/json-view/) exposes the complete model document.

Draft comparison uses the base release where there is one, otherwise the latest installed
release of that model, otherwise an empty model. There is no automatic rebase or merge of a
draft onto a newer release. To start from different definitions, create a new draft from the
intended release and review the changes you carry across. A refused grouped operation applies
none of that step. Intermediate invalid drafts may be saved; Issues identifies what still needs work.

A navigation group's initial folded state is a model default; each browser can remember a
different state. A group page gathers its collections with search. During a drag in the model
pane, moving near its upper or lower edge scrolls the pane. Keyboard and phone users use
**Move to…** and the ordering menus instead.

## Describe a change in words

You can also [ask the assistant to propose a model change](/docs/model/ai-model-changes/)
and open its draft in this editor. Review the proposal before accepting; direct edits here
are read again when the assistant continues.
