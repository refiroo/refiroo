# Worked examples

These examples show how the product behaves in everyday situations. The product overview, its users
and its capabilities are in [PRODUCT.md](../PRODUCT.md); the detailed catalogue is
[CURRENT_FUNCTIONALITY.md](CURRENT_FUNCTIONALITY.md). The examples are fictional, not customer
research or preloaded data.

## Three different kinds of change

### Correct today's data

A steward notices “Collecton” in Delivery Methods, opens the record, corrects it to “Collection” and
saves. The correction is immediately available. Its identity and connections stay the same. If someone
else has changed the record, the product keeps the attempted correction and asks the steward to review
the newer information before trying again.

No release, change set name or publication action is needed. Marking a model-defined availability field
false is also an ordinary edit. Whether a consuming system hides unavailable values depends on its
agreed query; the engine must not silently invent that business policy.

### Prepare several related changes

A steward is reorganizing delivery options and related system mappings. The team chooses a design
change set, makes the changes away from live users, checks the result and publishes the coordinated change.
Before publishing, **Review changes** lists exactly what the change set adds, changes and removes,
record by record, with each changed field's value before and after; a moved record names where it came
from and where it goes.
Another steward can still correct an unrelated live value. That correction survives publishing.
If both change the same record, publishing stops without losing either person's work.

This change set changes data. It does not by itself change the application definition. It starts from
current live data, including edits made since the last publication, or from an earlier publication.

### Change what the application allows

An administrator needs a new field or relationship rule. They edit a proposed application definition,
check it against existing data and make a new definition available before selecting it for use.
Existing released definitions remain inspectable. An incompatible change needs a migration; since 0.11 the flow
previews affected data and potential loss, then allows explicit confirmation of that migration or cancellation,
and since 0.13 the model editor makes such changes (a rename, a split, a merge, a key change) and marks them with
the migration they imply. Confirmation applies to the reviewed change, not to invalid data
or an unsupported model language. Ordinary activation does not offer this override.

Since 0.11 each workspace runs a definition of its own: a model is installed and activated into one workspace the
administrator chooses or creates in the same step, and a workspace is moved to another release by a migration
that is previewed and confirmed. Since 0.17 a workbook can be shaped into a definition on a canvas and made into a
workspace in one step.

## History answers different questions

- Record history answers “what changes were made to this item?” Since 0.12 a change names the signed-in
  person or system that made it (changes from before sign-in name nobody).
- A workspace snapshot answers “what did this coordinated publication contain?” Later live edits do
  not rewrite it. A snapshot is not a complete archive of every moment between publications.
- A released application definition answers “what fields and rules did this version define?”
- An effective-date read (`asOf`) answers “which values were valid on this business date?” It works only
  for a record type that declares an effective period; a field that merely contains a date does not
  provide it (Base 0.9).

Starting a change set from old history is not a one-click undo of today's dataset. Publishing preserves
untouched live records and checks conflicts. Withdrawing a publication also does not remove
live data from normal reads or make the workspace read only; retiring the workspace does that.

Read next: [user stories](USER_STORIES.md), [acceptance scenarios](ACCEPTANCE_SCENARIOS.md),
[roadmap coverage](ROADMAP_COVERAGE.md).
