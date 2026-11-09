---
title: Turn an attribute into a list
description: Replace a field definition with a relationship to a reusable list type.
reader: model-admin
---

Use a list type when people should choose maintained records instead of entering a free value.
For example, a stop's operator may be a relationship to operator records. This is a modelling
choice, not a special value type. See [Types, attributes and relations](/docs/model/types-attributes-relations/).

1. In a draft, select the type and open **Attributes**. Open the attribute's menu and choose
   **Turn into a list type…**. You need **Model authoring**.
2. Enter **List type’s name** and **Plural name**. Enter **Relation name** from the original
   type and **Reverse name** from the list records back to it.
3. Review **Which records may be chosen**. Leave it unrestricted to offer any list record,
   or add the offered criteria. A new list type initially offers criteria on its name.
4. Apply and inspect the new type and relationship. Check the original type's fields and
   layouts and resolve **Issues** before previewing or installing.
5. If the released attachment holds values, the step applies and **History** marks it
   **Needs a migration**. Saving the draft does not populate live list records. Use **Undo**
   to reverse an unwanted draft step.
6. When installing, review **Activation needs a migration** and choose **Install … and preview
   the migration…**. The preview includes the proposed list conversion. Open **Created** to
   inspect the list records and relationships it creates: one record per distinct value,
   named by the value, connected to every source record holding it. The values leave the
   source records. Review any loss or items to fix, then
   [confirm the migration](/docs/guide/model/migrate-a-workspace/) when acceptable.

![List conversion dialog with list names and relationship names](/docs/screens/model-attribute-list-type-dialog.png)

![Migration preview with split and list-conversion proposals and the Created outcome selected](/docs/screens/model-migration-created.png)

*Above: the draft splits Code system from Stop code and turns Code kind values into list records. Created lists 28 new records and relationships across both changes; nothing has changed in the workspace yet.*
