"""What a feed entry changes for a consumer API definition (Base 0.9 C10, ``engine/events/plan.py``).

The plan is read from ``Capi`` of the generated journey model: its roles, ``parent``, ``path`` and
``hierarchy``, and its projections ``B11`` (items read by name and ``K.code``) and ``Bown`` (its items'
``G`` ancestor's name). A change is described as the feed records it, by name only (C-D87).
"""

import copy

from configurations import all_configurations

from app.engine.events.plan import (
    CHILDREN,
    DESCENDANTS,
    SELF,
    SELF_AND_DESCENDANTS,
    EventPlan,
    FeedChange,
    Own,
    Reach,
)
from app.engine.model.compiler import parse_model
from app.engine.model.consumer_definitions import consumer_apis

CONFIGURATION = all_configurations()["generated-a"]


def _plan(change=None):
    document = copy.deepcopy(CONFIGURATION.model)
    (definition,) = document["consumerApis"]
    definition["operations"]["events"] = {
        "custom": [{"key": "every", "objectTypes": definition["exposes"], "changes": ["created", "updated", "deleted"]}]
    }
    if change is not None:
        change(document, definition)
    model = parse_model(document)
    return EventPlan(model, consumer_apis(model)[0])


def k(structure):
    return CONFIGURATION.key(structure)


def _object(action="updated", type_key="R", **fields):
    return FeedChange(position=7, kind="object", action=action, record_id="x", object_type_key=k(type_key), **fields)


def test_a_records_own_change_names_the_outputs_its_sources_feed():
    """A value names the outputs that read its attribute (``R.u`` feeds ``code``, ``R.n`` the score);
    a rename the name; a move the parent, path and hierarchy. A value no output reads makes no own
    event; a creation and a deletion of an exposed type are told whatever changed."""
    plan = _plan()
    owns, _ = plan.seeds([_object(names=frozenset({k("R.u"), k("R.n"), "name"}))])
    assert owns == [Own(7, "x", "updated", k("R"), None, tuple(sorted({k("Capi.code"), k("Capi.n"), k("Capi.name")})))]
    owns, _ = plan.seeds([_object(moved=True, parent_id="p", previous_parent_id="q")])
    assert owns[0].outputs == tuple(sorted({k("Capi.parent"), k("Capi.path"), k("Capi.hierarchy")}))
    assert plan.seeds([_object(names=frozenset({k("R.q")}))])[0] == []
    assert plan.seeds([_object("created"), _object("deleted")])[0] == [
        Own(7, "x", "created", k("R"), None, ()),
        Own(7, "x", "deleted", k("R"), None, ()),
    ]
    assert plan.seeds([_object("created", type_key="K")]) == ([], [])


def test_a_rename_reaches_children_descendants_and_the_owners_of_a_projected_record():
    """Renaming a record changes its children's ``parent`` and its descendants' ``path`` and
    ``hierarchy``; renaming a K that ``B11`` projects reaches the projection's owners (outgoing:
    the relation's from end); renaming a G reaches the owners of the D records below it through
    ``Bown``'s ancestor field; moving a record reaches the owners of itself and the items below it."""
    plan = _plan()
    _, reaches = plan.seeds([_object(type_key="K", names=frozenset({"name"}))])
    b11, bown = k("B11"), k("Bown")
    assert Reach(7, "x", CHILDREN, None, None, (k("Capi.parent"),)) in reaches
    assert Reach(7, "x", DESCENDANTS, None, None, tuple(sorted((k("Capi.path"), k("Capi.hierarchy"))))) in reaches
    assert Reach(7, "x", SELF, b11, "outgoing", (k("Capi.B11"),)) in reaches
    _, reaches = plan.seeds([_object(type_key="G", names=frozenset({"name"}))])
    assert Reach(7, "x", DESCENDANTS, bown, "outgoing", (k("Capi.Bown"),)) in reaches
    _, reaches = plan.seeds([_object(type_key="D", moved=True)])
    assert Reach(7, "x", SELF_AND_DESCENDANTS, bown, "outgoing", (k("Capi.Bown"),)) in reaches
    # A value a projection does not read reaches no owner.
    _, reaches = plan.seeds([_object(type_key="K", names=frozenset({k("K.rank")}))])
    assert not any(reach.relation == b11 for reach in reaches)


def test_a_relation_of_a_projections_type_reaches_its_owner_end():
    """Creating or deleting a ``B11`` relation updates its from end (the projection is outgoing);
    an update of its values changes no projection that reads none of them, and reaches the owner of one
    that reads the relationship's own values (``relation:<attribute>``), whichever value changed."""
    plan = _plan()
    for action in ("created", "deleted"):
        change = FeedChange(7, "relation", action, "rel", relation_type_key=k("B11"), from_id="r", to_id="t")
        assert plan.seeds([change]) == ([], [Reach(7, "r", SELF, None, None, (k("Capi.B11"),))])
    change = FeedChange(7, "relation", "updated", "rel", relation_type_key=k("B11"), from_id="r", to_id="t")
    assert plan.seeds([change]) == ([], [])
    change = FeedChange(7, "relation", "updated", "rel", relation_type_key=k("Bscope"), from_id="r", to_id="d")
    assert plan.seeds([change]) == ([], [Reach(7, "r", SELF, None, None, (k("Capi.Bscope"),))])


def test_a_type_change_is_an_own_change_naming_object_type():
    """A record whose type changed is told from its previous and new types, with ``objectType``
    among its outputs, when either is exposed (C-D83); the deriver sees it from each event. Its
    children's ``parent`` shows its type, so they are reached."""
    plan = _plan()
    change = _object("reclassified", type_key="R2", previous_object_type_key=k("R"))
    owns, reaches = plan.seeds([change])
    assert owns == [Own(7, "x", "reclassified", k("R2"), k("R"), ("objectType",))]
    assert Reach(7, "x", CHILDREN, None, None, (k("Capi.parent"),)) in reaches
    unexposed = _object("reclassified", type_key="K", previous_object_type_key=k("H"))
    assert plan.seeds([unexposed])[0] == []


def test_a_projection_over_a_containment_relation_reaches_both_parents():
    """A projection over a parent–child relation has no relation entries: a child created, deleted
    or moved reaches the parents whose projection gains or loses it, before and after (C-D95)."""
    model = parse_model(copy.deepcopy(CONFIGURATION.model))
    (containment,) = model.containment_relation_keys(k("R2"))

    def children(_document, definition):
        definition["object"]["related"]["entries"] = {"via": containment, "fields": {"entryName": "name"}}

    plan = _plan(children)
    created = _object("created", type_key="R2", parent_id="p")
    moved = _object(type_key="R2", moved=True, parent_id="p", previous_parent_id="q")
    _, reaches = plan.seeds([created])
    assert Reach(7, "p", SELF, None, None, ("entries",)) in reaches
    _, reaches = plan.seeds([moved])
    assert {(r.record_id, r.outputs) for r in reaches if r.relation is None and r.base == SELF} == {
        ("p", ("entries",)),
        ("q", ("entries",)),
    }


def test_a_feed_entry_is_read_by_name():
    """An entry's subject and changed names become the change: a live move's parents from its
    changes when the subject predates C-D95; a publish's names; a publication's entry is none."""
    from app.models.database import AuditEvent

    live = AuditEvent(
        aggregate_type="object",
        aggregate_id="x",
        action="updated",
        version=2,
        changes={"name": {"from": "a", "to": "b"}, "parentObjectId": {"from": "q", "to": "p"}},
        feed_position=3,
        subject={"objectTypeKey": k("R")},
    )
    change = FeedChange.of(live)
    assert (change.names, change.moved, change.parent_id, change.previous_parent_id) == (
        frozenset({"name"}),
        True,
        "p",
        "q",
    )
    published = AuditEvent(
        aggregate_type="object",
        aggregate_id="x",
        action="updated",
        version=2,
        changes={"changedFields": ["attributes"], "attributeTypeKeys": [k("R.n")]},
        feed_position=4,
        subject={"objectTypeKey": k("R"), "parentObjectId": "p"},
    )
    assert FeedChange.of(published).names == frozenset({k("R.n")})
    withdrawal = AuditEvent(aggregate_type="workspace", aggregate_id="w", action="publication-withdrawn", feed_position=5)
    assert FeedChange.of(withdrawal) is None


def _shown_parent(document, definition):
    """Capi's parent also shows ``R.u`` and a block over ``B11`` (its items read by name)."""
    parent = definition["object"]["parent"]
    parent["fields"] = {"kind": "objectType", "parentId": "id", "parentRef": k("R.u")}
    parent["related"] = {"token": {"via": k("B11"), "fields": {"tokenName": "name"}}}


def test_what_the_parent_shows_reaches_its_children():
    """An attribute the parent shows, an item of one of its blocks and a relationship it gains or
    loses each reach the children of the owner, naming the parent output; a record's own attribute
    changes only its own outputs."""
    plan = _plan(_shown_parent)
    parent = k("Capi.parent")
    _owns, reaches = plan.seeds([_object(names=frozenset({k("R.u")}))])
    assert Reach(7, "x", CHILDREN, None, None, (parent,)) in reaches
    _owns, reaches = plan.seeds([_object(type_key="K", names=frozenset({"name"}))])
    assert Reach(7, "x", SELF, k("B11"), "outgoing", (parent,), True) in reaches
    relation = FeedChange(
        position=7, kind="relation", action="created", record_id="r", relation_type_key=k("B11"), from_id="o", to_id="t"
    )
    _owns, reaches = plan.seeds([relation])
    assert Reach(7, "o", CHILDREN, None, None, (parent,)) in reaches
    _owns, reaches = plan.seeds([_object(names=frozenset({k("R.n")}))])
    assert all(not item.children for item in reaches)
