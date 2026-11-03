---
title: Find who changed something
description: Follow data history to its author, filter their changes and inspect security activity separately.
reader: access-admin
---

Start with the record or workspace when you do not know the author. Start with People or
Clients when you do. You need permission to read the affected workspace to inspect its data;
Security administration alone does not grant that. See [Who changed what](/docs/administer/audit/)
for the scope of each history view.

## Start from the changed data

1. Open the affected record and its **History**. Find the change by time and read the
   before and after values and the named person or client. For a broader search, open
   **Settings › Workspaces**, select the workspace and choose **Activity**.
2. Filter the workspace's activity to the relevant work and period. Use the entry's
   workspace, change set and publication context to distinguish authored changes from
   changes applied by publication. Follow [History](/docs/use/history/) for those controls.
3. Follow the author's name where it is linked to open their Changes page. If you already
   know the person, use the route below instead.

## Start from a person or client

1. Open **Settings › Security › People** or **Clients**. Search and select the identity.
   Check their username or client ID if similar names exist. For a deactivated identity,
   use the **Deactivated** list.
2. Choose **See changes**. The page names that person or client and lists their visible
   changes, newest first, grouped by day. It can cover several workspaces.
3. Set **Workspace** to the relevant workspace, or keep **All workspaces**.
   Under **What**, choose **Records**, **Relationships**, **Change sets**, **Publications**
   or **Model**, or keep **Everything**.
4. Choose **Period**: **Last 24 hours**, **Last 7 days**, **Last 30 days** or **Any time**.
   If no result matches, widen the filters. Use **Load more** to retrieve older entries.
5. Read the action, subject, changed-field summary, time and workspace. Open a linked title
   to inspect the surviving subject. Use the record's own History for the changed values;
   the person's Changes page is a summary.

![Person's changes with workspace, kind and period filters and dated entries](/docs/screens/admin-audit-person.png)

*Above: fictional Rita Approver's page shows her publication and the Davos Platz height
change applied by it in Graubünden. These are related entries, not proof of two separate manual edits.*

An empty list does not prove there were no changes outside your access. Check that you
can read the workspace. If the changed record was removed, its history entry can remain
without an openable record. A renamed person is shown by their current name.

## Find an account or access change

1. Return to the person's or client's security page and scroll to **Recent activity**.
   This is separate from their data changes.
2. Choose **Signing in**, **Roles and groups** or **Account** to narrow the events,
   or **All** to include every security kind associated with that identity.
3. Read the event, time and named actor. Use **Load more** for older activity and
   **Show fewer** to reduce the displayed list.
4. If loading fails, choose **Retry** after reading the error. A failed load is not an
   empty audit result. Do not look for passwords or secrets in this history; they are not shown.

![Person detail at the Recent activity section with its four filters](/docs/screens/admin-grants-person.png)

*Above: Guide Admin's security activity follows their roles and groups. A one-time password
link creation appears as an event without revealing the link itself.*

There is no separate instance-wide audit page to open. Use these identity views and the
workspace's Activity for the question at hand.
