---
title: Types, attributes and relations
description: Define kinds of record, shared fields, allowed connections and containment.
reader: model-admin
---

Define a type for each kind of record people maintain. Its attributes hold values; its
relationships connect records. You need **Model authoring** to change these definitions in a draft.
[Models](/docs/model/models/) explains when changes reach a workspace.

## Types and where records stand

The editor calls a record type an **Object type**. **Name** is singular; **Plural name** labels
its collection. **Stands** places it at the top level or under another type. A child is joined
to its parent by a containment relation, with names in both directions. Containment is not an
extra label on an ordinary relationship: it defines the record hierarchy too.

A type may be listed in several applications while keeping one definition and one set of rules.
Removing a listing differs from removing the type. Follow
[Add a record type and fields](/docs/guide/model/add-a-record-type-and-fields/) or
[Split, merge and move types](/docs/guide/model/split-merge-and-move-types/).

## Attributes and shared definitions

An attribute type defines a reusable field, including its name, value type and features.
The value types offered are **Text**, **Long text**, **Whole number**, **Decimal number**, **Yes or no**, **Date**,
**Date and time** and **JSON**.
Choose the type for the value people hold, rather than storing every value as text.

An attachment to a record type determines **Required** and **Read-only** there. **Unique** belongs
to the shared attribute definition. Changing a shared name, value type or feature affects every
attached type; **Shared with** identifies them. A required field needs a value; a read-only field
cannot be changed through the ordinary record form. **Searchable** includes the field in search and **Filterable** permits filtering. Views choose
which filter controls they offer. **Sortable** is shown, but ordinary non-JSON fields can sort
from list headers regardless of that checkbox. These features do not select table columns.
JSON fields cannot be made unique, sorted, filtered or used as ordinary view fields.

![Type attributes with value types, required, unique, read-only and shared states](/docs/screens/model-type-fields.png)

[Reuse and change attributes](/docs/guide/model/reuse-and-change-attributes/) explains the controls.
The visual editor has no attribute default-value, format, length or effective-period control.
A list of reference choices is modelled as related records, rather than as another value type:
[Turn an attribute into a list](/docs/guide/model/turn-an-attribute-into-a-list/).

## Relationships and permitted pairs

A relation type supplies the forward and reverse meanings. Permitted pairs separately say which
types it may join. Their **Cardinality** limits the number of connections at each end;
**Required** declares dependent ownership: the target is created with its owner connection.
It is supported for one-to-one or one-to-many relationships; **Many to one** cannot be required. **Which records** can narrow candidates by name,
attached attributes or ancestor. Criteria can apply to the records chosen and the records choosing.
Do not confuse a candidate rule with a filter that hides rows in one view.

**Relationship matrix** shows all permitted type pairs. Rows are the from end. Each cell lists
the relation types and number limits, with **contains** for containment. Select a pair to inspect
or change its permissions. This design grid differs from a relation matrix that people use for data.

![Relationship matrix with a selected from and to pair](/docs/screens/model-matrix-pair.png)

Follow [Add a relationship](/docs/guide/model/add-a-relationship/).

## Released elements and refusals

A released element's key is fixed. Labels can change while identity stays the same. Operations
that remove or restructure released elements check use by records, values and relationships,
including change sets. A refusal reports the impact. Zero impact can allow a structural change;
a fixed key remains fixed even with no data. Changes that affect stored data need a reviewed
[migration](/docs/model/migrations/), rather than an assumption that saving the draft converted it.

See [Rename or re-key an element](/docs/guide/model/rename-or-re-key-an-element/) and
[Remove an element](/docs/guide/model/remove-an-element/).

## Rules beyond the visual forms

Specialist authors can declare display fields, name-editing rules, effective periods, value
validation and relationship attributes through the [JSON view](/docs/model/json-view/). A display
field must be attached to its type. An effective period uses appropriately typed fields and
requires a valid date order. Relationship attributes retain their types just as record fields do.

A uniqueness rule can also be limited by a declared ancestor scope or condition. Those references
must resolve to the appropriate type and field. Such rules apply to writes through all clients;
a hidden field or filtered view does not bypass them. The visual candidate editor offers
**Which records may be chosen** and **Which records may choose**, with names, fields and ancestor
fields. Candidate criteria govern new choices; a later value change does not automatically remove
an existing relationship.

A mapping grid's relation cannot be containment or required ownership. Resolve the named model
issue by selecting a suitable relationship, rather than treating an application name as a special
permission to use the view. For the visual relation controls, select a **Relation type** to edit
**Names** and **Reverse name** and inspect **Allowed between**. **Allow between two types…**
chooses the From and To pair; **Change keys…** applies only before those keys are released.
