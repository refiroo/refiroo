# Composable domains — MDM-lite and small product catalogues

**Status:** Direction, recorded 2026-09-26 ([ADR-032](DECISIONS.md#adr-032--reach-other-domains-only-through-generic-composable-capabilities)).
Nothing here is scheduled. RDM remains the design centre ([ADR-001](DECISIONS.md#adr-001--focus-on-rdm),
[product boundaries](PRODUCT.md#boundaries)).

## Purpose

The engine's model-driven core — typed objects, reusable attributes, typed relations, containment,
views, live editing, change sets, publications and immutable model releases — also fits two
neighbouring domains:

- **MDM-lite:** consolidating moderate-volume master domains (suppliers, locations, legal entities,
  a product master) where records from several source systems are mapped to one master record.
- **Small product catalogues:** a specific, configurable catalogue with a fixed schema per product
  type, a category tree, product relations and staged launches.

The combination of model releases, change sets pinned to a chosen release (ADR-028), delta-merge
publishing (ADR-026) and immutable publications is uncommon in both domains. A new season or master
domain usually needs new attributes *and* new data; the engine can prepare both, validate them and
publish them in order while live editing continues.

This document records how the engine may grow toward these domains without becoming a different
product, and which current design choices must stay open so that it can.

## Principle

**These domains are modelled, not built.** An MDM-lite or catalogue application is a model — object
types, attribute bindings, relations and views — composed from generic engine capabilities. The engine
gains no feature that only one domain can use, and no runtime branch on MDM or catalogue concepts, just
as it has none on `master-value` or `system-value` today.

Every new capability must combine with everything that already exists: live writes, change sets,
publications, history, model-release pinning, optimistic concurrency, cursor paging, the consumer API
and the generic renderers.

## Out of scope

- High-volume party/customer MDM (millions of records, continuous high write rates, probabilistic
  matching at scale).
- A full PIM: variant axes with inherited values, per-channel and per-locale attribute scoping,
  category-driven attribute sets maintained as data, channel completeness scoring.
- Data-quality and enrichment services (address standardization, external reference lookups) beyond
  model-declared validation.
- A general rules or scripting language in the model.

A later product decision may revisit these; until then they are not design targets.

## Admission tests for a new capability

A capability motivated by MDM-lite or a catalogue is admitted only when all of these hold:

1. **Nameable without the domain word.** It can be described without saying "MDM", "golden record",
   "product" or "catalogue". "Merge two records and redirect the retired ID" passes; "golden record"
   does not.
2. **Two real cases.** It has one concrete use in the motivating domain and another elsewhere,
   preferably in RDM itself (the existing [AGENTS.md](../AGENTS.md) rule for generalization).
3. **Closed declarative vocabulary.** Configuration picks from a small, named set of behaviours
   validated at model load. When a need goes beyond that set, it waits for the 1.0 extension point
   rather than growing the model grammar into a programming language.
4. **Composes with the lifecycle.** It behaves correctly live, in a change set, in a publication, under
   a pinned model release, under concurrency and across the consumer API — with tests at each of those
   boundaries.
5. **Shown by a starter model.** A starter model demonstrates it, so the combination is documented by
   configuration, not prose.

## Candidate generic capabilities

Candidates only; none is scheduled. Each is listed with its non-domain use so admission test 2 can be
checked when it is proposed.

| Capability | RDM / generic use | MDM-lite use | Catalogue use | Nearest existing mechanism |
| --- | --- | --- | --- | --- |
| Asset value type (file or image reference) | Code-list documents, flag icons | Supporting documents | Product images, data sheets | Attribute value types ([APPLICATION_MODEL.md](APPLICATION_MODEL.md)) |
| Quantity and money value types | Needs a second case | Credit limits | Price, dimensions, weight | Attribute value types |
| Derived attributes from a closed function set (first non-empty by priority, most recent, count, concatenation) | Computed display labels, coverage counts | Survivorship: master value picked from source records by priority | Values a child takes from its parent | ADR-003 anticipated inheritance |
| Value source (provenance) per attribute value | Which system supplied a code | Trust and lineage per value | Supplier-provided vs. edited | Audit events, record versions |
| Record merge with a retired-ID redirect, reversible | Duplicate codes | Consolidating duplicate masters | Duplicate products | Cascade preview (ADR-012), stable identities (ADR-024) |
| Similarity candidates from a declarative scoring vocabulary | Suggested targets in the mapping lens | Match candidates | Duplicate detection on import | Consumer API `match` declaration ([CONSUMER_API.md](CONSUMER_API.md)) |
| State-based review lens (unmatched / ambiguous / resolved) | Mapping coverage | Match review queue | Import review | `mappingGrid` coverage states (ADR-029) |
| Keyed inbound upsert for recurring feeds | Periodic system code loads | Source-system feeds | Supplier updates | 0.9 bulk upsert |
| Redaction of stored values in history | Mistakenly entered sensitive text | Personal-data erasure | — | Immutable publications (ADR-024) |

A domain concept such as "golden record" is then a model pattern: a master object type, source-record
object types mapped to it through an ordinary relation, and derived attributes that pick each value from
the sources by priority.

## Doors to keep open

These constraints apply to current and planned work now, even though nothing above is scheduled. A
design that closes one of these doors needs an explicit product decision.

### Identity

Public IDs stay stable and are never reused. Do not assume a lookup by public ID only ever returns the
record or "not found": a later retired-ID redirect (a merged record pointing to its survivor) must be
addable to object reads, relation endpoints, the consumer API and cursors without breaking their
contracts. Do not build deletion or merge logic that would make an undo impossible to add later.

### Provenance

Do not assume every attribute value has exactly one author, or that the audit actor is the only origin
worth recording. A value-source field on attribute values, change-set rows and publication snapshots
should be an additive change.

### Derived values

`engine/records/attributes.apply_attribute_values` is the only write path for stored values and must stay
so. Do not assume every displayed or exported value is stored; leave room for read-only values computed
from related records and declared in the model. Consumer API projections already compute values from
related objects and are the nearest pattern.

Decided in 0.11 Q2 (D190): a derived value is indexed, sorted, filtered and checked for uniqueness
when it is stored as a value row through that write path, marked by `attribute_values.value_source`;
every value index and `unique_attribute_values` follow value rows, the same for every model (D186).
A value computed only when read can be shown and exported, but not sorted, filtered or checked in the
database: that would need an index per expression, generated from a model.

### History and erasure

Publications stay immutable in meaning and shape. Do not make targeted redaction impossible by design:
keep stored values in places a redaction can reach (value rows, `snapshot_attribute_values`, search
indexes) and keep complete before/after value blobs out of audit event payloads, as Base 0.5 already
requires. A redaction would replace a value and record an audit event; it would not remove the record,
the publication or the history entry.

### Inbound flow

0.9 bulk create, update and upsert should be keyed by stable model keys or declared unique attributes,
idempotent and resumable, so the same contract serves recurring feeds from source systems and not only
one-off loads.

### Matching and review

The consumer API `match` scoring declaration and the mapping coverage states are the two existing
seeds of similarity search and review queues. Keep their vocabulary independent of the consumer API
and of `mappingGrid` where it costs nothing, so a later lens can reuse them instead of introducing a
parallel grammar. The model-to-model mapping's coverage (0.11 X1, D110: source elements not
mapped, target requirements nothing fills, parents not allowed) is computed from model metadata in
`engine/moves/mapping_check.py`, apart from `mappingGrid`'s states. A move's dry run (0.11 X2)
counts per record what that coverage leaves out (types, attributes, relationships, parents), with
the same reason codes for every domain. A move (0.11 X3) records where each record it created came
from in `record_origins`, a lookup beside the record's ID: the ID itself is never changed, so a
later retired-ID redirect stays possible.

### Value types

A new attribute value type should be an additive schema change: one registry entry, validation,
conversion in `engine/records/values.py` and a renderer. Do not hard-code the list of value types
outside those registries.
A migration converts values by pairs of value types in the SQL function `rdm_convert_value`; a new
type's pairs are added there by a database migration, and until they are, a value converting to or
from the new type is reported as loss, never dropped (0.11 V4, D102). A model mapping refuses a pair
`rdm_convert_value` never converts (`values.conversion`, held to the function by a unit test), so
the new type's pairs are mapped once written (0.11 X1).

## Design-review checklist

When a work package touches identity, attribute storage, audit or history, bulk APIs, the consumer API
`match` declaration or mapping coverage, its plan states in one line whether any door above is
affected and, if so, how it stays open.

## Open questions

- Whether assets are stored by the engine or referenced externally.
- Whether derived attributes are materialized (indexed, sortable, filterable) or computed on read.
- The minimum function set for derived attributes and the minimum scoring vocabulary for similarity.
- Whether MDM-lite changes the [product boundaries](PRODUCT.md#boundaries) or stays within "generic
  applications where the model is genuinely useful".
- Which catalogue and MDM-lite starter models to add, and in which release.
