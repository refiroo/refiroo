---
title: Change relationships of many records
description: Add, remove, replace or clear one kind of relationship across selected records.
reader: steward
---

Use this when several records need the same connection changes. See
[Changing many records](/docs/use/changing-many-records/) and [Relationships](/docs/use/relationships/).

1. Select records in an editable collection and choose **Change relationships**. Select the
   relationship's pill. Only relationships allowed for that record type appear; parent and
   owner connections are managed elsewhere.
2. Choose the offered action. **Add** adds the ticked records; **Remove** removes those ticked.
   **Replace with** makes the ticked records the complete set. **Set to** chooses the one record
   for a single-valued connection. **Clear** removes the set where optional. Required
   connections cannot be removed or cleared.
3. Search and tick the other records. **Remove** lists records the selection already holds and
   how many hold each. **Add** marks connections already held. Candidate rules may limit this
   list; read its explanation if an expected record is missing.
4. Read the number of changes. If it exceeds the deployment limit, reduce the selection or
   split the work. Choose **Change the rest** or, where available, **Change none**.
5. Choose **Preview**. Review additions, removals, unchanged connections and refused records.
   Use **Back** to revise, or **Apply** to proceed.
6. Read the actual result. Connections changed since preview are refused, preserving the
   newer work. Use **Preview again** after checking them, then **Done**.

The fields on each connection are not changed here. Open the record's relationship panel to
edit those fields. A replace operation removes connections you leave unticked, so review the
whole chosen set before applying.
