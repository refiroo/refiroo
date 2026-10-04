"""Base 0.8 C5: whole-graph validation is linear in the graph.

Found in C5: validating a change set over the generated model at 2% volume (about 5,400 records and
12,000 relations) took 125 s, even with nothing changed, because the uniqueness, parent-edge,
cardinality, scoped-uniqueness and required-relation checks each scanned every record or relation
once per record or relation. Publishing runs the same checks, so the milestone journey could not
publish there. The checks now read indexes built once.

The first part pins what the indexes must answer exactly as the scans did, on a small graph over the
generated model; the second measures validating and publishing at 2% volume through the API.
"""

import time
from types import SimpleNamespace

import pytest
from volume_fixture import (
    ACTIVE,
    APPLICATION,
    CELL,
    CODE,
    COLUMN,
    COLUMN_CONTAINS_SHELF,
    GROUP,
    GROUP_CONTAINS_ITEM,
    GROUP_HAS_CELL,
    ITEM,
    ITEM_CITES_GROUP,
    MATRIX_APPLICATION,
    SHELF,
    SHELF_CONTAINS_CELL,
    WORKSPACE,
    scaled_shape,
    volume_app,
    volume_model,
)

from app.engine.change_sets.access import EffectiveChangeSetMembership
from app.engine.change_sets.validation import graph_diagnostics
from app.engine.model.compiler import parse_model


def _model():
    """The generated model, with a citation one-to-one so the source side's cardinality is checked."""
    source = volume_model()
    for pair in source["objectTypeRelations"]:
        if pair["relationTypeKey"] == ITEM_CITES_GROUP:
            pair["cardinality"] = "one-to-one"
    return parse_model(source)


def _record(object_id, object_type_key, parent=None, application=APPLICATION, **attributes):
    return SimpleNamespace(
        object_id=object_id,
        object_type_key=object_type_key,
        application_key=application,
        parent_object_id=parent,
        attributes=attributes,
    )


def _edge(relation_id, relation_type_key, source, target, **attributes):
    return SimpleNamespace(
        relation_id=relation_id,
        relation_type_key=relation_type_key,
        from_object_id=source,
        to_object_id=target,
        attributes=attributes,
    )


def _details(diagnostics, code):
    return [item.get("details") for item in diagnostics if item["code"] == code]


def test_the_indexed_checks_answer_as_the_scans_did():
    objects = [
        _record("g1", GROUP, **{CODE: "A"}),
        _record("g2", GROUP, **{CODE: "A"}),
        # A record without the key and one holding None hold no value, so they share it (E-D4, H4c).
        _record("g3", GROUP),
        _record("g4", GROUP, **{CODE: None}),
        # JSON values are compared by equality, not identity.
        _record("g5", GROUP, **{CODE: ["x", 1]}),
        _record("g6", GROUP, **{CODE: ["x", 1]}),
        _record("i1", ITEM, "g1", **{CODE: "I1"}),
        _record("i2", ITEM, "g1", **{CODE: "I2"}),  # no parent edge
        _record("c1", COLUMN, application=MATRIX_APPLICATION, **{CODE: "C1"}),
        _record("s1", SHELF, "c1", application=MATRIX_APPLICATION, **{CODE: "S1"}),
        _record("gm", GROUP, application=MATRIX_APPLICATION, **{CODE: "GM"}),
        _record("x1", CELL, "s1", application=MATRIX_APPLICATION, **{CODE: "X1", ACTIVE: True}),
        _record("x2", CELL, "s1", application=MATRIX_APPLICATION, **{CODE: "X2", ACTIVE: True}),
        _record("x3", CELL, "s1", application=MATRIX_APPLICATION, **{CODE: "X3", ACTIVE: False}),
        _record("x4", CELL, "s1", application=MATRIX_APPLICATION, **{CODE: "X4", ACTIVE: True}),
    ]
    relations = [
        _edge("p-i1", GROUP_CONTAINS_ITEM, "g1", "i1"),
        # A second group containing i1: one-to-many allows one source per target.
        _edge("p-i1-again", GROUP_CONTAINS_ITEM, "g2", "i1"),
        # One-to-one: i1 may cite one group (each group is cited once, so only the source side).
        _edge("cite-1", ITEM_CITES_GROUP, "i1", "g1"),
        _edge("cite-2", ITEM_CITES_GROUP, "i1", "g2"),
        _edge("p-s1", COLUMN_CONTAINS_SHELF, "c1", "s1"),
        *(_edge(f"p-{cell}", SHELF_CONTAINS_CELL, "s1", cell) for cell in ("x1", "x2", "x3", "x4")),
        # One active cell per group and column: x1 and x2 collide; the later id names the earlier.
        _edge("s-b", GROUP_HAS_CELL, "gm", "x1"),
        _edge("s-a", GROUP_HAS_CELL, "gm", "x2"),
        _edge("s-c", GROUP_HAS_CELL, "gm", "x3"),  # inactive: outside the scope rule
        # x4 has no incoming GROUP_HAS_CELL, which the model requires.
    ]
    diagnostics = graph_diagnostics(
        EffectiveChangeSetMembership(None, tuple(objects), tuple(relations)), _model()
    )

    unique = {
        item["objectId"]: item["conflictingObjectIds"]
        for item in _details(diagnostics, "DUPLICATE_ATTRIBUTE_VALUE")
    }
    assert unique == {
        "g1": ["g2"],
        "g2": ["g1"],
        "g5": ["g6"],
        "g6": ["g5"],
    }
    assert _details(diagnostics, "CONTAINMENT_RELATION_MISSING") == [
        {"objectId": "i2", "parentObjectId": "g1"}
    ]
    assert _details(diagnostics, "RELATION_CARDINALITY_VIOLATION") == [
        {"relationId": "p-i1"},
        {"relationId": "p-i1-again"},
        {"relationId": "cite-1"},
        {"relationId": "cite-2"},
    ]
    assert [item["message"] for item in diagnostics if item["code"] == "RELATION_CARDINALITY_VIOLATION"] == [
        f"Relation '{GROUP_CONTAINS_ITEM}' exceeds target cardinality",
        f"Relation '{GROUP_CONTAINS_ITEM}' exceeds target cardinality",
        f"Relation '{ITEM_CITES_GROUP}' exceeds source cardinality",
        f"Relation '{ITEM_CITES_GROUP}' exceeds source cardinality",
    ]
    assert _details(diagnostics, "DUPLICATE_RELATION_SCOPE") == [
        {
            "relationId": "s-b",
            "conflictingRelationId": "s-a",
            "conflictingObjectId": "x2",
            "objectId": "gm",
            "ancestorObjectId": "c1",
        }
    ]
    assert _details(diagnostics, "MISSING_REQUIRED_RELATION") == [
        {"objectId": "x4", "relationTypeKey": GROUP_HAS_CELL}
    ]


# About 5,400 records and 12,000 relations; the scans took 125 s to validate an unchanged change set.
LARGE = scaled_shape(0.02)
VALIDATE_SECONDS, PUBLISH_SECONDS = 10, 20


@pytest.fixture(scope="module")
def large(tmp_path_factory):
    with volume_app(tmp_path_factory.mktemp("graph-validation"), LARGE) as app:
        yield app


def test_validating_and_publishing_a_large_workspace_stay_within_budget(large):
    client, dataset = large
    response = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/change-sets",
        json={"source": "currentLive"},
    )
    assert response.status_code == 201, response.text
    change_set = response.json()

    started = time.perf_counter()
    validation = client.post(f"/api/v1/change-sets/{change_set['id']}/validation")
    validating = time.perf_counter() - started
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid"] is True
    assert validating <= VALIDATE_SECONDS, f"validation took {validating:.1f} s"

    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    started = time.perf_counter()
    published = client.post(
        f"/api/v1/change-sets/{change_set['id']}/publication",
        json={"expectedChangeSetVersion": version, "expectedActivePublicationId": dataset.publication_id},
    )
    publishing = time.perf_counter() - started
    assert published.status_code == 200, published.text
    assert publishing <= PUBLISH_SECONDS, f"publishing took {publishing:.1f} s"
