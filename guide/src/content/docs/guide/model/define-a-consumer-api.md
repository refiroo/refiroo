---
title: Define a consumer API
description: Choose what other systems read and review how each editor choice changes their answers.
reader: model-admin
---

Define a consumer API when another system needs an agreed view of your workspace's data.
Open a model draft with **Model authoring** and agree the required information with the
consuming team. You choose the public record shape, the operations and the filters;
a security administrator separately grants a client access in each workspace.

See [Consumer APIs in the model](/docs/model/consumer-apis/) for the rules. The marked
examples below use the reference Stops API. Requests and response excerpts show the result
of your choices; they are not instructions to type into the editor or live API captures.

## Choose the records and their public shape

1. Select **Consumer APIs** in the model pane, then the add button's **Consumer API…**.
   Enter **Name**, review **Key** and choose **Types to expose**. A blank key is made from
   the name. Create the API. The initial definition includes identifiers, names, attached
   attributes, Get by ID and a list per type. Inspect these starting choices before sharing
   the contract: exposing a type does not mean every attached field belongs in a public API.
2. On **Types and related**, inspect each type's public name. Use **Expose a type…** to add
   another type. Consumers receive that public name as the object's type. Choose only the
   types they need as business objects; related blocks can carry information from other
   types without exposing those records as business objects in their own right.
3. Open **Parent, path and hierarchy…** if consumers need containment information. The
   parent is the immediate containing record; a path or hierarchy names ancestors from
   the root down, excluding the current record. Review those outputs as part of the contract.
4. Use **Add related…** to include information reached through a relationship. Set
   **Output name**, **Via** and **Fields**. Each related field pairs a public name with a
   value on the related record. Check the relationship's direction and whether it serves
   one record or several: the answer is respectively an object or an array. A missing
   relationship gives null or an empty array, rather than an invented related record.

![New consumer API dialog with name, key and types to expose](/docs/screens/model-consumer-add-dialog.png)

Above: creating a consumer API in the reference model.

**Example result.** Stops API exposes Stop, Municipality, Operator and Mode. Its Stop
object includes an `operator` object and a `modes` array. The parent names the municipality;
the path is `Graubünden/Plessur/Chur` for the Chur stop. These are outputs chosen in
**Types and related**, not extra records copied into the stop. Compare the
[complete business object](/docs/model/consumer-apis/#the-business-object-consumers-read).

## Choose the fields and fallbacks

1. On **Fields**, inspect **Output name**, **Role**, **Sources (first non-empty)**,
   **Served type** and **Default**. Output names are the names consumers receive;
   sources are where their values come from. Use **Add field…** to add a public field.
2. Use **Sources…** on an existing field to order its fallbacks. The first non-empty
   value wins. Zero and false count as values. **Move up** and **Move down** order
   supported items; **Remove** takes an item out.
3. Choose **Role** for an identity, code, name or validity output where needed. The identity
   reads the record's stable ID. Keep any business identifier as a separate field. Check
   **Served type** after changing sources; incompatible types or conflicting roles appear
   in **Issues** and need correction.
4. Select an editable **Default** cell to provide a fallback only when all sources have
   no value. Save the value or cancel. Use the served type: a text fallback cannot stand
   in for a number. A default changes the consumer answer, not the stored record.

![Public field dialog with output name, sources and role](/docs/screens/model-consumer-add-field.png)

Above: adding a public field to a consumer API in the reference model.

**Example result.** The reference field `code` reads `sloid`, then `operator-code`, then
`mode-code`. The same Get by ID operation returns these response excerpts for two records:

| Record read | Response excerpt |
| --- | --- |
| Chur stop | `{"objectType": "Stop", "code": "ch:1:sloid:9000"}` |
| Its operator | `{"objectType": "Operator", "code": "SBB"}` |

The field `stopNumber` reads stop-number and returns `8509000` as an integer for Chur.
A missing abbreviation is null unless you supply a default; Chur's existing `CH` value
still takes precedence. See [Sources and defaults](/docs/model/consumer-apis/#sources-and-defaults).

## Offer the operations and filters

1. On **Operations**, review **Get by ID**, **XREF** and **Resolve**. Get by ID reads a
   stable record ID; XREF matches values such as a code or name. Resolve performs many
   such reads in a batch and needs both Get by ID and XREF. Leave off operations the
   contract does not need: consumers cannot use an undeclared operation.
2. Use **Add list…** and set **Key**, **Of**, **Within the filter** and **Sorted by**.
   **Of** selects a type; sorting selects its order. None for Within gives the list no
   special parent parameter. With an Under filter, a consumer can supply a parent ID to
   list records below it. Omitting that parameter still returns the whole type.
3. Enable XREF if needed, then use **Add XREF rule…**. Review the fields with
   **Matches on…** and **Fields…** where offered. **Exact** and **Contains** are numeric
   weights, not mutually exclusive modes. Give reliable identifiers stronger weights
   than broad name fragments. Contains applies to text terms of at least three characters.
4. Use **Add a match through a related block…** when related data should help identify an
   exposed record. Review **Also match through**, **First of** and **Prefers**. A match
   through a system code can identify its owning record; a shared code can identify several.
   Review ties with the consuming team rather than relying on the first result.
5. On **Filters**, choose **Add filter…**, **Name** and **Verb**. **By type** selects types;
   **Under** reads containment; **Linked to** selects **Through**; **On related** selects
   **Related block**. Review **Matches on** and the offered **Options**. **Keep only
   matching records** narrows the returned records. A related filter also narrows the
   related block's items; **Score only matching items** limits which items contribute
   lookup scores. **Crosswalk** lets consumers ask for a target representation from
   that block. Enable only the choices the contract needs.

![Filter dialog with verb-specific matching options](/docs/screens/model-consumer-add-filter.png)

Above: adding a filter to a consumer API in the reference model.

**Example results to review with an integrator.** The reference API offers these requests:

| Editor choice | Request an integrator can make | Result |
| --- | --- | --- |
| List all-stops, Of Stop, no Within filter | `GET /api/consumer/stops/v1/lists/all-stops?workspace=graubuenden&municipality=3901` | A page of stops below the municipality matched by FSO number. Each item has the chosen business-object shape. |
| List stops, Within municipality | `GET /api/consumer/stops/v1/lists/stops?workspace=graubuenden&municipality=05fd46a2-964a-4870-9d40-8bec6b4822dd` | A page below this parent ID. Here municipality is the list's parent parameter and accepts IDs only. |
| XREF rule stop-number, Exact 900 | `GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=8509000&expect=one` | Chur's object with `matchScore: 900`. A tied top score is an ambiguity, not an automatic selection. |
| Related match through systemCodes | `GET /api/consumer/stops/v1/xref?workspace=graubuenden&query=Q663869&expect=one` | Chur's object with `matchScore: 90`, found through its Wikidata station code. |

The ordinary municipality filter accepts ID, name or FSO number. Its special use as the
stops list's parent parameter accepts only IDs. A filter name is part of the public
contract even when it does not add a response field. The reference mode filter additionally
lets the consumer narrow these reads with `mode=TRAIN`.

Resolve returns one outcome per input: found, not found, ambiguous or rejected. Shared
request defaults and per-item overrides choose filter values; they are different from
field defaults. See [the batch example](/docs/model/consumer-apis/#lookups-and-batch-answers)
and [Looking up and resolving](/docs/integrate/looking-up-and-resolving/) for full payloads.

## Define notifications and review the contract

1. If every exposed type needs standard notifications for creation, update and deletion,
   enable **Events per type**. For a named event, use **Add custom event…**, then choose
   **Key**, **Types**, **Changes** and **Watches**. No Watches means any change to what
   consumers read, including related blocks. This defines an event, not a delivery subscription.
2. Use **Describe…** to explain the API's purpose to consuming teams. Review **Issues**,
   **Schema**, **Message example** and the compatibility result. A **Not applied** notice
   means the attempted step was refused: correct its named problem, then review again.
   Specialist editing does not bypass validation.
3. If the editor says **Needs contract version …**, inspect the contract changes and
   [raise the contract version](/docs/guide/model/raise-a-contract-version/). The contract
   version is separate from the model release version. Renaming a public field, changing
   a related block's shape, removing an operation or reducing event coverage can require
   a higher version.
4. [Review and share the generated documents](/docs/guide/model/see-a-consumer-apis-documents/)
   before installing and activating the release. Draft edits do not change the live API.
   Agree changes with integrators and ask a security administrator to grant the consuming
   client this API in the workspaces it needs. Model authoring and other roles do not
   substitute for that grant.

**Example result.** The reference event stops-changed watches code, name and the validity
dates. A name change produces an event with `event: "stops-changed"`, `change: "updated"`
and `changed: ["name"]`; changing latitude alone does not. See
[the event example](/docs/model/consumer-apis/#events-describe-changes-to-the-output).
The reference contract version 1 gives consumers an address ending in `stops/v1`.
Raising it to 2 changes that address to `stops/v2` after activation; the older live
version does not remain as a parallel endpoint.

## Refine a released API safely

Turning XREF off can ask **Stop offering XREF?** because its rules are removed and Resolve
stops too. Cancel to retain them, or confirm and inspect the contract difference. **Undo**
restores the step; switching XREF on again alone does not restore the old match rules.

Use **Rename…** for a display-name change. A new API's key is editable until released;
a released API shows **Key fixed: released**. Its key is the stable access point consumers
already use. Removing the API stops those reads after activation. Coordinate any deliberate
replacement and its access grants with the consuming team.
