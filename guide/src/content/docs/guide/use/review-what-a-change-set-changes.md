---
title: Review what a change set changes
description: Inspect record and relationship differences before validation or a publication decision.
reader: steward
---

Compare proposed work with the data the change set started from. See
[Change sets](/docs/use/change-sets/#review-explains-the-differences).

1. From **Change sets**, choose **Open change set** to open **Changes in this change set**.
   If you are already browsing its data, choose **Review changes** in the amber band. Confirm
   its name; open **Details** for its source. If it started from a publication, the earlier values come from that publication,
   not today's Live.
2. Under **Records**, filter by change kind or record type. Open a row to read before/after
   values and paths. A moved record names both parents. A type-change filter can match either
   its old or new type, so check the difference itself.
3. Open **Relationships** and inspect additions, changes and removals separately. A record
   review alone does not account for every changed connection.
4. Scroll or jump through the lists. The address retains the tab, filters and position so
   you can return to the same part of the review.
5. Choose **See the data with these changes** to return to editing for corrections, then
   choose **More change set actions › Validate now**. You can also choose **Publish**, which checks before confirmation. Resolve its named
   problems and validate the new version again before publishing or submitting.

A record created and deleted in the same change set contributes no remaining change and is
omitted. A record edited back to its original values can still count as changed, because
publication still checks the version it claims. A successful validation is not protection
against later Live conflicts; publication checks again.
