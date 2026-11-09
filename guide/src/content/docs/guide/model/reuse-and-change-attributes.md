---
title: Reuse and change attributes
description: Attach a shared field and change its local rules or shared definition.
reader: model-admin
---

Work in a draft with **Model authoring**. Read
[Types, attributes and relations](/docs/model/types-attributes-relations/) before changing a shared field.

1. Select the receiving type and open **Attributes**. Choose **Attach an existing attribute…**
   and select the field. Already attached fields are not offered. Choose **Required** only if
   every record of this type must supply it, then apply the attachment.
2. Check **Shared with**. A shared attribute's name, value type and uniqueness are used by all
   attached types. Open **Attribute types** to inspect the common definition and its attachments.
3. In the type's table, select an editable **Required** or **Read-only** cell, choose **Yes**
   or **No**, then **Save**. The menu also offers **Make required** / **Make optional** and
   **Make read-only** / **Make editable**. These choices apply to this type's attachment.
4. To change the shared field, use **Rename…**, **Value type…**, **Make unique** or **Allow
   repeated values**. On the attribute type, **Features…** chooses **Searchable**, **Filterable**,
   **Sortable** and **Unique**. Inspect every attached type before applying a shared change.
5. Use **Move up** or **Move down** to order attributes. **Move to…**, or dragging a field onto
   a type in the model pane, moves the attachment; its columns and panel placement move with it.
   Check the destination rather than creating a duplicate attribute definition. For a released
   field, read **Needs a migration when installed**: moving the attachment removes its values
   from the original type's records. They cannot be carried onto a different type's records.
6. Review **Issues** and **History**. A released field change that affects stored data applies
   and is marked **Needs a migration**, with affected records, values and relationships.
   Installing the draft shows the migration to review. Check conversions, loss and records that
   break tighter rules before [confirming it](/docs/guide/model/migrate-a-workspace/).
   Use **Undo** if the draft change is unwanted.

![Attach an existing shared attribute to a type](/docs/screens/model-attribute-attach-existing.png)

![Attribute operations including value type, local rules and list conversion](/docs/screens/model-attribute-menu.png)

**Detach from …** removes the attachment and its uses in that type's views and panels; it does
not mean remove the attribute from every type. Read the confirmation, or cancel to keep it.
