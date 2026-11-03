---
title: Remove an element
description: Review the scope and stored-data impact before removing a model definition.
reader: model-admin
---

Remove unused definitions in a draft with **Model authoring**. See
[Types, attributes and relations](/docs/model/types-attributes-relations/) for released-element limits.

1. Select the element, inspect its uses, then open its operations menu. Choose the specific
   removal: **Remove type**, **Remove application**, an attribute's **Detach from …**, or the
   removal offered for that definition. These actions have different scopes.
2. Read the confirmation. Removing a type removes its views, detail page and relationships
   at either end. Detaching an attribute removes its use in that type's views and panels.
   Removing a navigation group leaves its collections available outside the group.
3. Cancel if any named effect is unwanted. Otherwise confirm, inspect the remaining model
   and open **Issues** for references that now need repair. Use **Undo** for an unwanted draft step.
4. If released structure is in use, read the refusal's records, values and relationships counts.
   The check includes relevant workspaces and change sets. A zero-impact removal may be allowed;
   an in-use removal needs a reviewed [migration](/docs/model/migrations/).

![Type removal confirmation naming the views, page and relationships removed](/docs/screens/model-type-remove-confirm.png)

To hide a collection in one application, use **Stop listing in this application** where offered.
That is different from removing its type and records. A released listing can also need migration.
No removal in a saved draft alone changes the active workspace's records.
