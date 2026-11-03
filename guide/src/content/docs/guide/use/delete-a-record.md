---
title: Delete a record
description: Review dependent records and relationships before confirming a permanent removal.
reader: steward
---

Delete only when the record should be removed. To keep it for history and stop offering it,
see [Stop offering a value](/docs/guide/use/stop-offering-a-value/). Read
[Records](/docs/use/records/#deleting-a-record) for ownership rules.

1. Open the record and check its workspace and Live or change-set band. Open **⋯** and choose
   **Delete record**. You need permission for the record and dependants the deletion removes.
2. Read **Delete …?**. Choose **Delete** to request removal. If it has dependants or
   relationships, refiroo shows their impact before another confirmation.
3. Review the record count, dependent records with their types, **Relationships to remove**
   and the count of connections leading to independent records. Children and owned dependants
   go with the record, including owned records in another application. Independent records
   and their hierarchies remain.
4. Choose **Confirm deletion** only if that is the intended impact. Cancel to leave it in place.
   If there are no dependants, the first Delete can complete the removal.
5. After success, the list opens. In Live the removal is immediate; in a change set it stays
   proposed until publication. Earlier publications and history are not erased.

If someone changes the record or adds a dependant before confirmation, the stale deletion
is refused. Choose **Retry** to obtain the current record, then request deletion and review
the fresh impact. Retry does not silently confirm a larger cascade.

![Single-record deletion impact showing dependent names/types, relationships removed, independent connections retained and Confirm deletion.](/docs/screens/record-delete-impact.png)
