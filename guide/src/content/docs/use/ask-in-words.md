---
title: Asking a list in words
description: Turn a question into ordinary list filters and understand what the list can express.
reader: steward
---

Use **Ask** when you know which records you want but are unsure how to set their filters.
The answer becomes search text and ordinary filter pills. It changes which records you see;
it does not change any record. Follow [Ask a list in words](/docs/guide/use/ask-a-list-in-words/).

## Where Ask is offered

A table collection offers **Search** and **Ask** beside its search box when an AI provider is
enabled and you have **Browse** and **Use AI proposals** in the workspace. Ask works in Live,
a change set and a publication. It is absent from mapping grids, trees and the Changes page.
You can always use the list's ordinary [search and filters](/docs/use/lists-and-filters/).

## What a question can become

Ask can use the view's filter fields and every relationship of the listed record type,
including relationships absent from **＋ Filter**. In Live it also offers **Created** and
**Updated**. Those two times are unavailable in change sets and publications.

You can ask for field values, missing relationships, or records with a relationship below a
named ancestor at any depth. The result uses the list's existing conditions. Ask cannot
choose a sort order or find who changed a record. Use the sort controls or record History
for those tasks. Questions are limited to 500 characters.

When you name a related record, refiroo looks for an exact name, ignoring letter case, then
for a single name containing your words. No match or several matches means that part is not
expressed; it does not pick a record for you. Use a more complete name and ask again.
Choosing records by the meaning of their names needs the short-list names described below.
For larger lists, give an exact or unambiguous partial name.

## Read the result before relying on it

A complete answer applies its search and filters to the list, replacing the previous search
and filters. The line **Your question became these filters. Change or remove any of them.**
appears. Check each pill: the provider can misunderstand your intent. Open a pill to edit it,
remove it with **×**, or return to Search. The current sort stays as it was.

If any part cannot be expressed, the list stays as it was. A warning names the missing part
and shows **What it could do:** as dashed pills. **Use these filters** applies only that
partial answer. Review what was left out before choosing it. A failed request applies
nothing and keeps your question, so you can correct it, retry or use Search instead.

![Ask showing a part it cannot express and the filters available for review](/docs/screens/use-ask-partial.png)

## What is sent and kept

Your question, today's date, field names and relationship definitions go to the configured
provider when you press Enter, not as you type. At structure, no stored record names are
included. At samples or values, related-record and ancestor names are also included when
their type's list contains at most 50 records in this context. That short list is sent whole.
Your own words are sent at every level, so include only information you are allowed to send.

Requests can incur provider costs and are recorded with their outcome. Request and answer
text is kept in the call log only if the operator enables it. Read
[AI and your data](/docs/use/ai-and-your-data/) for permissions, retention and provider privacy.
