---
title: Rename or re-key an element
description: Rename a label or change an identifying key with a reviewed migration after release.
reader: model-admin
---

A name is what people read. A key identifies a definition across releases. Changing a released
key needs a migration, even when there are no records; integrations naming it must change too. See [Types, attributes and relations](/docs/model/types-attributes-relations/).

1. Open the element in a draft with **Model authoring**. Read **Key editable until released**
   or **Released: a key change needs a migration** in its facts.
2. To change the displayed words, choose **Rename…** or select the editable title. Enter **Name**;
   a record type also offers **Plural name**. Save, then check navigation and views using it.
   A shared attribute rename appears on every type that attaches it.
3. To change identity, choose **Change key…** and enter the new key. Relation types offer
   **Change keys…**. Save and inspect the affected definitions and **Issues**. The editor follows
   references in the draft; check documents and external systems you maintain separately.
4. For a released key, read **Needs a migration when installed: integrations naming the key must change**.
   The step applies and **History** marks it **Needs a migration**. When installing, review the key
   change and the consumer APIs of the base release naming it. Coordinate integrations before
   confirming the [migration](/docs/guide/model/migrate-a-workspace/). A label-only rename does
   not change the key.
5. If a save is refused, read **Not applied**. A key already in use needs a different key;
   for a newer draft, review [concurrent changes](/docs/guide/model/work-on-a-draft-with-others/).

![Rename a type with separate singular and plural names](/docs/screens/model-type-rename-dialog.png)

![Change key dialog for an unreleased type](/docs/screens/model-type-change-key-dialog.png)

![Install review naming a changed released key, its consumer API and a blocking contract-version finding](/docs/screens/model-install-key-change.png)

*Above: the key change for Stop number (UIC) names Stops API among the consumers that must change. The Consumer APIs check needs version 2, so installation cannot continue from this review.*

New keys are suggested from labels: lower-case words separated by hyphens, with accents removed.
A clash adds a number such as -2 or -3. Review the suggestion while it is editable; changing a
label after release does not generate a new identity.
