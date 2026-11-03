---
title: Split, merge and move types
description: Reshape draft types and their containment without confusing definitions with records.
reader: model-admin
---

Use these actions to reshape definitions in a draft. You need **Model authoring**. They do not
move live records merely by saving. Read [Types, attributes and relations](/docs/model/types-attributes-relations/).

## Split a type

1. Select the type and choose **Split…** from its menu. It needs attributes to split.
2. Enter **New type’s name** and, where needed, **Plural name**. Choose **Attributes that move
   to it**. The selected attachments belong to the new type after the split.
3. Enter **Relation name** from the original type, **Reverse name** and **Cardinality** for the
   connection between them. Apply and inspect both types, their relationship and layouts.

![Split dialog with moved attributes and the connecting relationship](/docs/screens/model-type-split-dialog.png)

## Merge definitions

1. Select the type to absorb and choose **Merge into…**.
2. Choose **Into** carefully. Its attributes, relations and layout join the chosen type.
3. Apply and inspect the combined type and **Issues**. Use **Undo** if the result is unwanted.

![Merge dialog choosing the receiving type](/docs/screens/model-type-merge-dialog.png)

## Move a type

1. Choose **Move to…**. In **Find a target**, type a name, move with Up/Down and select with
   Enter. A destination can put the type under another type or at an application's top level.
2. For a contained destination, choose **Containment relation**, either a new relation or a
   suitable existing one. When several applications list the type, inspect **Take it out of**.
3. Confirm and check the type and the types under it. Dragging a type onto a type, an application
   or the space beside the tree opens the same decision. Use **Move to…** on a phone or by keyboard.

![Move dialog with target search and containment relation](/docs/screens/model-type-move-to-dialog.png)

**Not moved** or **Not applied** explains a refusal. Released structure with data may require a
[migration](/docs/model/migrations/). **Stop listing in this application** only removes a listing;
**Remove type** removes its definition, views, page and relations at either end. Neither is a
shortcut for moving existing data between models; use [Copy and move](/docs/model/model-mappings/).
