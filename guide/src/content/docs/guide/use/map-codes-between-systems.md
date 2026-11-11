---
title: Map codes between systems
description: Find unmapped or ambiguous rows and choose, replace or remove a mapping.
reader: steward
---

Connect each source record to the intended target using a mapping grid. Codes from another
system are one example. See [Mapping grids](/docs/use/mapping-grids/) for states, limits and
permissions.

## Find the rows that need attention

1. Open an application in the current workspace and choose a collection with a mapping grid.
   Select the mapping tab. Check the heading and the source and target types in its description.
2. Check the banner. Choose **Live** for immediate changes, or
   [open a change set](/docs/guide/use/prepare-and-publish-a-change-set/) to prepare them together.
3. Search for the source records you need. Read their codes and other identifying fields.
   Select **Unmapped** for rows without a connection, **Mapped** for rows with a
   target, or, on a view where a source may hold only one, **Ambiguous** for rows with several. **All** removes the state restriction.
4. Inspect each target's name and identifying fields. Select a source name or target chip to
   open that record's page for a closer look. Decide whether the current state needs changing.
   Clear search and select **All** if an expected row is absent. A read error needs
   a retry; it does not mean a row is unmapped.

## Choose or replace a target

1. Choose **Map** on an unmapped row or **Change** on a filled row. **Change mapping** opens
   with the source name in its heading and the current targets, or **Not mapped**, under
   **Currently**. Check these before searching.
2. Search for the intended target and inspect its identifying fields. Select its radio button.
   If nothing matches, shorten the search and check the model's candidate rules. Do not select
   a similar name merely to fill the row.
3. Choose **Save mapping**. This sets the row to the selected target, replacing any previous
   targets, including all targets of an ambiguous row. Check the refreshed target and state.
   If the row no longer matches the active state filter, switch to **All** and find it again.
4. Choose **Cancel** if no correction is needed. Where **Save and next** is offered, it saves
   this choice and opens the next row; check that new source before choosing again.

![A mapping dialog for an unmapped row with target radio choices and a creation action](/docs/screens/mapping-grid-map-dialog.png)

*Above: T-9999, the fictional special day pass, is deliberately unmapped. The dialog shows
Not mapped and offers stop candidates and Create new stop. It was cancelled; the screenshot
does not suggest that this pass needs a stop mapping.*

To retain several valid targets, use the record's [relationship controls](/docs/guide/use/relate-records/).
Saving one selection in this dialog resolves the row to one target.

## If the target does not exist

1. Search carefully first. If a new record is needed, choose **Create new** followed by its
   type name. The target creation form opens.
2. Check its application and parent where offered, then fill **Name** and the required fields.
   Choose **Create**, or **Cancel** to return without creating a target.
3. After creation, review the selected target in the mapping dialog and choose **Save mapping**.
   Creating a record does not itself finish the mapping. If you cancel now, the new record remains.

## Remove a mapping

1. Choose **Change** on the row and review **Currently**.
2. Choose **Remove mapping** where offered. This clears the row's mapping and keeps the source
   and target records. Check **Unmapped**, using **All** if your previous filter hides the row.
3. If the dialog says the mapping is required, choose an allowed replacement instead of clearing
   it. **Cancel** keeps the current mapping.

## Handle a refused save

If **Mapping conflict** appears, read **Current mapping** and compare it with your intended
selection. Choose **Cancel** to leave it as it now stands. Choose **Continue with my selection**
only after reviewing the other change, then save again. A further intervening change can cause
another refusal. Other **Save failed** messages name a rule to resolve before retrying.

If editing actions are missing, check your context and permissions. Reader can inspect; Contributor
works in change sets; direct Live writes need **Edit live**. Publishing proposed mappings has its
own conflict checks; see [Change sets](/docs/use/change-sets/).

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
