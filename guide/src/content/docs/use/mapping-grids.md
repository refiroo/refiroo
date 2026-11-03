---
title: Mapping grids
description: Understand source-to-target mappings, unmapped and ambiguous rows, replacement and removal.
reader: steward
---

Use a mapping grid to connect records on one side of a relationship to records on the other.
One use is connecting codes from another system to the records whose meaning they represent.
The model chooses both sides, their fields and the relationship; neither side has a fixed role
in refiroo. Follow [Map codes between systems](/docs/guide/use/map-codes-between-systems/) for the steps.

## Reading a mapping

Each row identifies a source record, its mapping state and its connected targets. Target chips use the target type’s colour and
show names with identifying fields chosen by the model. Read those fields before deciding that
two similar names mean the same thing.

| State | Meaning |
| --- | --- |
| Unmapped | No target is connected through this view's relationship. |
| Mapped | Exactly one target is connected. |
| Ambiguous | More than one target is connected; the count says how many. |

**Ambiguous** describes multiple stored connections, rather than uncertainty about a suggested
match. It can be valid for a relationship that allows several targets. Decide whether one or
several is correct for the data before replacing anything. An unmapped row can be intentional.

![A mapping grid showing mapped, ambiguous and unmapped source codes](/docs/screens/mapping-grid-codes-to-stops.png)

*Above: Codes to stops in Systems, searched for FICTIONAL, shows the invented Regional ticketing
system. T-0300 connects to Chur West and Chur; T-0412 connects to Chur Wiesental; T-9999 is deliberately
unmapped. These fictional codes demonstrate the three states.*

**All**, **Unmapped**, **Mapped** and **Ambiguous** narrow the whole list, together with search.
An empty result says nothing about rows excluded by these conditions. A loading failure is not
an unmapped state; retry the read before editing.

## Choosing or clearing targets

**Map** on an unmapped row and **Change** on a filled row open **Change mapping**. Choosing a
target and saving sets that row's mapping to the chosen target. If several were connected,
the selection replaces them with one; it does not add another target alongside them.

Where offered, **Create new** followed by the target type opens a record creation form.
Creating a target and saving its mapping are distinct steps: review the selected target and
finish **Save mapping**. Cancelling the mapping does not undo a target already created.

**Remove mapping**, where available, clears the connection rather than deleting either record.
A required connection cannot be cleared. Changes are saved together or refused, so an unsuccessful
replacement does not leave a half-changed mapping. See [Relationships](/docs/use/relationships/)
for candidate restrictions and number limits.

A mapping grid works with voluntary associations, not parent containment or required ownership.
To create owned related records across columns, use a [relation matrix](/docs/use/relation-matrices/).
To keep several targets, use the record's relationship controls rather than replacing the set
with one selection in the grid.

## Permissions, context and conflicts

Reading needs **Browse**. Saving needs **Edit live** or **Work in change sets** for the relevant
data. Reader can inspect; Contributor can prepare change-set work; Data steward and Data owner
can also edit Live. Scoped grants can restrict the types you change. Publications and retired
workspaces are read-only. See [Record permissions](/docs/use/records/#who-may-read-and-change-records).

In Live, a saved mapping applies immediately. In a change set it remains proposed until publication.
If someone changes the mapping after you read it, **Mapping conflict** shows the current mapping.
Review it before continuing with your selection or cancelling. Publishing also checks intervening
live changes; see [Change sets](/docs/use/change-sets/).

The counts and **All**, **Unmapped**, **Mapped** and **Ambiguous** state choices describe the
whole matching list. Use them with search to find work beyond the visible rows. Target chips
preview the connected records so you can inspect identifying fields before replacing them.
An atomic replacement retains the existing relationship's identity and fields. Publishing a
change set refuses mappings that diverged from Live; review the current connections before
preparing another attempt.

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*

## More targets and newly created records

**Mapping status** groups **All**, **Unmapped**, **Mapped** and **Ambiguous**. A mapping row
counts eligible sources plus sources already connected, so changing candidate conditions does
not hide existing mappings. **Show all … targets for …** expands a row's remaining targets.

Creating a missing target asks for its application. Parent choices belong to that application;
if no required parent can stand there, creation is refused. Create or select a suitable parent
rather than choosing one from another application. Creating the target selects it in the mapping
form but does not save the mapping: finish **Save mapping** separately.

A replacement keeps the values of connections it retains when no new relationship values are
supplied. Explicit replacement values replace the whole collection of fields, and clearing
all is allowed only if the model accepts it. In the ordinary mapping picker, choosing a target
alone does not clear its existing relationship fields.

## Empty results and an unavailable view

**No results match these filters** means the mapping-state filter has no matching rows.
Choose **All** and clear other conditions to widen the list. **No results match this search**
means the search has no matches; change or clear it. **No … in this workspace yet** names the
source record type when there are no rows and neither a state filter nor search is applied.
Check that you are in the intended workspace and context before adding records.

**This mapping view references an object type that does not exist in the active model.**
means the view cannot be drawn. Reload after a model change. If it persists, give a model
administrator the view name and message so they can correct the model; changing mappings
cannot repair a missing type.

## Targets proposed by AI

**Propose targets** asks the configured AI provider to choose targets for unmapped sources.
It needs **Use AI proposals**, **Work in change sets**, a writable workspace and the send level
values. It is unavailable in a publication. Follow [Propose targets](/docs/guide/use/propose-targets/)
to prepare and review them.

Search and the chosen parent narrow which sources are considered. The provider receives source
and candidate target names and the fields this view shows. Only targets the grid permits are
candidates: all eligible targets when there are at most 100, otherwise each source's 20 closest
by name and searchable fields. Requests normally group 25 sources, or fewer for a small model
context. This shortlist can miss a good target; the proposal is help, not proof of a match.
Requests can cost money and their outcome is kept. See [AI and your data](/docs/use/ai-and-your-data/)
for sending, access and retention.

Each accepted answer becomes an ordinary mapping in the chosen change set. Live data stays as
it was. **Proposed** under **Mapping status** shows sources with AI-proposed targets in that
change set. **Proposed by the AI** shows the confidence and reason; on a phone, open **Why?**
to read the reason. Confidence is the provider's estimate, not a guarantee. The operator sets
a minimum confidence; lower answers and invented or missing targets are left unmapped.

![A change-set mapping grid narrowed to Proposed with AI confidence and reasons](/docs/screens/use-mapping-proposed.png)

Correct a wrong target through **Change** and **Save mapping**, or remove the mapping if allowed.
Changing the target removes its AI mark because the replacement is your choice. Publishing
uses the usual approval and conflict checks. The published relationship's history keeps the
proposal's origin and model, and separately names the person who published it.

The job's result counts **Proposed**, **Left unmapped: no likely target** and **Changed meanwhile,
not touched**. It also reports refused or unanswered rows when present. Concurrently mapped
sources are left alone. Failed calls produce warnings; their rows are not proposed. Earlier
successful batches can remain after a later failure. **Stop** likewise keeps proposals already
written. Inspect the change set before publishing even when the job ended early.
