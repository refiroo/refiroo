---
title: Rename or re-key an element
description: Change a displayed label while preserving identity, or choose a key before release.
reader: model-admin
---

A name is what people read. A key identifies a definition across releases. Released keys are
fixed even when there are no records. See [Types, attributes and relations](/docs/model/types-attributes-relations/).

1. Open the element in a draft with **Model authoring**. Read **Key editable until released**
   or **Key fixed: released** in its facts.
2. To change the displayed words, choose **Rename…** or select the editable title. Enter **Name**;
   a record type also offers **Plural name**. Save, then check navigation and views using it.
   A shared attribute rename appears on every type that attaches it.
3. Only for an unreleased element, choose **Change key…** and enter the new key. Save and
   inspect the affected definitions and **Issues**. The editor follows references in the draft;
   check any documents or external systems you maintain separately.
4. If the key is fixed, keep it and rename the label instead. Do not remove and recreate a
   released element just to change its identity. If a save is refused, read **Not applied**;
   for a newer draft, review [concurrent changes](/docs/guide/model/work-on-a-draft-with-others/).

![Rename a type with separate singular and plural names](/docs/screens/model-type-rename-dialog.png)

![Change key dialog for an unreleased type](/docs/screens/model-type-change-key-dialog.png)
