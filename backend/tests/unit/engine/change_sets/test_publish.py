"""``engine/change_sets/publish.py``: what a publish changes in live data, as feed entries.

J26.2 and J26.3 publish through the API. Here the comparison itself: a row equal to live has no
entry, a version alone is an update naming no field, a type change reads as reclassified, a
containment relation is the record's parent and never an entry, and the order is records changed,
relations removed, relations changed, records removed (D15, D32).
"""

from types import SimpleNamespace

from app.engine.change_sets.access import EffectiveChangeSetMembership
from app.engine.change_sets.publish import (
    LiveMerge,
    MergedObject,
    MergedRelation,
    publish_entries,
)

HOLDS = "holds"
MODEL = SimpleNamespace(
    containment_relation_keys=lambda key: frozenset({HOLDS}) if key == "child" else frozenset()
)


def _object(object_id, *, type_key="item", name="A", parent=None, values=None, version=1):
    return MergedObject(object_id, "app", type_key, name, parent, values or {}, version)


def _relation(relation_id, *, type_key="links", ends=("a", "b"), values=None, version=1):
    return MergedRelation(relation_id, type_key, *ends, values or {}, version)


def _entries(live_objects, merged_objects, live_relations=(), merged_relations=()):
    live = {item.object_id: item for item in live_objects}
    merged = {item.object_id: item for item in merged_objects}
    live_rel = {item.relation_id: item for item in live_relations}
    merged_rel = {item.relation_id: item for item in merged_relations}
    merge = LiveMerge(
        membership=EffectiveChangeSetMembership(
            change_set=None, objects=tuple(merged.values()), relations=tuple(merged_rel.values())
        ),
        authored_object_ids={i for i in merged if live.get(i) is not merged[i]},
        authored_relation_ids={i for i in merged_rel if live_rel.get(i) is not merged_rel[i]},
        removed_object_ids=set(live) - set(merged),
        removed_relation_ids=set(live_rel) - set(merged_rel),
        live_objects=live,
        live_relations=live_rel,
    )
    return [
        (e.aggregate_type, e.action, e.aggregate_id, e.changes["changedFields"])
        for e in publish_entries(merge, MODEL)
    ]


def test_an_authored_row_equal_to_live_has_no_entry_and_a_version_alone_names_no_field():
    a = _object("a", values={"code": "A"})
    assert _entries([a], [_object("a", values={"code": "A"})]) == []
    assert _entries([a], [_object("a", values={"code": "A"}, version=2)]) == [
        ("object", "updated", "a", [])
    ]


def test_changed_fields_name_what_differs_and_a_type_change_reads_as_reclassified():
    before = _object("a", name="Old", values={"code": "A", "gone": 1})
    renamed = _object("a", name="New", parent="p", values={"code": "B"}, version=2)
    retyped = _object("a", type_key="other", name="Old", values={"code": "A", "gone": 1})
    assert _entries([before], [renamed]) == [
        ("object", "updated", "a", ["name", "parentObjectId", "attributes"])
    ]
    assert _entries([before], [retyped]) == [("object", "reclassified", "a", ["objectType"])]


def test_entries_come_in_publish_order_and_leave_containment_out():
    kept, gone, new = _object("a"), _object("g"), _object("n")
    child = _object("c", type_key="child")
    live_relations = [
        _relation("old", ends=("a", "g")),
        _relation("parent", type_key=HOLDS, ends=("a", "c")),
    ]
    merged_relations = [
        _relation("added", ends=("a", "n")),
        _relation("parent2", type_key=HOLDS, ends=("n", "c")),
    ]
    assert _entries(
        [kept, gone, child], [kept, new, child], live_relations, merged_relations
    ) == [
        ("object", "created", "n", ["name", "parentObjectId", "attributes"]),
        ("relation", "deleted", "old", []),
        ("relation", "created", "added", ["attributes"]),
        ("object", "deleted", "g", []),
    ]
