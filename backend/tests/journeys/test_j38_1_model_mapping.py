"""J38.1 — The mapping between two models proposed and completed (USER_JOURNEYS.md, Base 0.11 X1,
D104–D113).

A mapping says what each element of a source model becomes in a target model. It is created between
two workspaces, proposed by an inference over their models and stored records, applied as steps
marked Proposed, corrected by hand with operations, undone and redone, and its drift reported. Each
test runs on one configuration ``X`` in the default workspace with a workspace on ``Y``, the other
generated configuration, beside it: generated A to B, and B to A. The two hold the same structures
under other keys, and in B a dependant stands under the container alone, so the right answer is
known by structure. Naming no configuration key.
"""

import copy
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from test_j36_workspace_models import BOTH, _model, _on, _other

# The relationships the configurations name as structures (configurations.py).
RELATIONS = (
    "B11", "B1n", "Bn1", "Bnn", "Bown", "Bscope", "Ll2k", "Ll1k", "Bh1n", "Breq", "Bsk", "Bassoc",
    "Bone", "Brev", "Bvk", "Bee", "Bcand", "Banc",
)  # fmt: skip


def _run(world):
    world.api.client.app.state.job_worker.run_until_idle()


def _beside(world, model=None):
    """``Y``'s model (or ``model``) installed and a workspace created on it: its world, release and key."""
    other = _other(world)
    release = world.install(model or other.configuration.model, name="Other model")
    return other, release, _on(world, release["id"])


def _create(world, source, target, key=None):
    key = key or f"map-{uuid4().hex[:8]}"
    body = {
        "key": key,
        "name": "Journey mapping",
        "sourceWorkspaceKey": source,
        "targetWorkspaceKey": target,
    }
    return ok(world.api.post("/model-mappings", body), 201)


def _read(world, key, **params):
    return ok(world.api.get(f"/model-mappings/{key}", **params))


def _operate(world, key, *operations):
    current = _read(world, key)
    body = {"expectedVersion": current["version"], "operations": list(operations)}
    return world.api.post(f"/model-mappings/{key}/operations", body)


def _infer(world, key, source, target):
    started = world.api.post(
        f"/model-mappings/{key}/inference",
        {"sourceWorkspaceKey": source, "targetWorkspaceKey": target},
    )
    ok(started, 202)
    _run(world)
    inference = ok(world.api.get(f"/model-mappings/{key}/inference"))
    assert inference["state"] == "completed", inference
    return inference


def _proposals(world, key):
    items, cursor = [], None
    while True:
        page = ok(
            world.api.get(f"/model-mappings/{key}/inference/proposals", pageSize=100, cursor=cursor)
        )
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _apply(world, key, proposals=None):
    body = {"expectedVersion": _read(world, key)["version"]}
    if proposals is not None:
        body["proposals"] = proposals
    return ok(world.api.post(f"/model-mappings/{key}/inference/application", body))


def _types(model):
    return {item["key"] for item in model["objectTypes"]}


def _containment(model):
    return {
        key
        for item in model["objectTypes"]
        for key in (item.get("behavior") or {}).get("parentRelationTypeKeys", [])
    }


def _structure(world, key):
    """The structure ``key`` names in ``world``'s configuration."""
    return next(structure for structure, value in world.configuration.keys.items() if value == key)


def _expected_types(world, other):
    """Every type of X with the type of Y of the same structure."""
    return {key: other.key(_structure(world, key)) for key in _types(world.configuration.model)}


def _entry(mapping, source_type):
    return next(item for item in mapping["types"] if item["source"] == source_type)


def _type_proposal(proposals, source_type):
    return next(p for p in proposals if p["kind"] == "type" and p["sourceType"] == source_type)


def _first(operations, kind, **match):
    return next(
        o for o in operations if o["kind"] == kind and all(o.get(k) == v for k, v in match.items())
    )


def _renamed(model):
    """``model`` as a release whose type names say nothing: only keys and records remain."""
    renamed = copy.deepcopy(model)
    renamed["release"]["version"] += "-renamed"
    for index, item in enumerate(renamed["objectTypes"]):
        item["name"] = f"Kind {index}"
        item["pluralName"] = f"Kinds {index}"
    return renamed


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_a_mapping_created_between_two_workspaces(world):
    """Given the default workspace on X and a workspace on Y. When a mapping is created between
    them. Then it names both models and releases at version 1, holds no type, and its coverage lists
    every type of X; a second mapping of the key is refused; a retired or unknown workspace is
    refused; the list filtered by the two models finds it."""
    other, y, target = _beside(world)
    x = _model(world)
    mapping = _create(world, W1, target)

    assert mapping["sourceModelKey"] == world.configuration.model["release"]["key"]
    assert mapping["targetModelKey"] == other.configuration.model["release"]["key"]
    assert (mapping["sourceReleaseId"], mapping["targetReleaseId"]) == (x["releaseId"], y["id"])
    assert mapping["version"] == 1
    assert mapping["types"] == [] and mapping["problems"] == []
    assert set(mapping["coverage"]["types"]) == _types(world.configuration.model)

    again = {
        "key": mapping["key"],
        "name": "Again",
        "sourceWorkspaceKey": W1,
        "targetWorkspaceKey": target,
    }
    refused(world.api.post("/model-mappings", again), 409, "MODEL_MAPPING_EXISTS")
    unknown = {
        **again,
        "key": f"map-{uuid4().hex[:8]}",
        "targetWorkspaceKey": f"none-{uuid4().hex[:6]}",
    }
    refused(world.api.post("/model-mappings", unknown), 404, "WORKSPACE_NOT_FOUND")
    retired = _on(world, y["id"])
    version = ok(world.api.get(f"/workspaces/{retired}"))["version"]
    ok(world.api.patch(f"/workspaces/{retired}", {"expectedVersion": version, "status": "retired"}))
    refused(
        world.api.post("/model-mappings", {**unknown, "targetWorkspaceKey": retired}),
        409,
        "WORKSPACE_RETIRED",
    )

    listed = ok(
        world.api.get(
            "/model-mappings",
            sourceModelKey=mapping["sourceModelKey"],
            targetModelKey=mapping["targetModelKey"],
        )
    )
    assert mapping["key"] in {item["key"] for item in listed["items"]}
    elsewhere = ok(
        world.api.get(
            "/model-mappings", sourceModelKey=mapping["targetModelKey"], targetModelKey="none"
        )
    )
    assert mapping["key"] not in {item["key"] for item in elsewhere["items"]}


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_a_mapping_proposed_with_evidence(world):
    """Given a workspace on Y beside X. When the mapping is inferred. Then every type of X is
    proposed to the type of Y of the same structure, its attributes to the attributes of the same
    structure, the dependant's parent to Y's container, and every relationship to the relationship of
    the same structure. Given instead Y released with type names that say nothing and R records
    sharing unique values in both workspaces, R is still proposed to R from the stored records, with
    alternatives."""
    other, _y, target = _beside(world)
    mapping = _create(world, W1, target)
    _infer(world, mapping["key"], W1, target)
    proposals = _proposals(world, mapping["key"])

    for source_type, target_type in _expected_types(world, other).items():
        proposal = _type_proposal(proposals, source_type)
        assert proposal["target"] == target_type, proposal
        assert proposal["status"] == "open" and proposal["evidence"]
        for operation in proposal["operations"]:
            if operation["kind"] == "mapAttribute":
                assert operation["target"] == other.key(_structure(world, operation["attribute"]))
    d = _type_proposal(proposals, world.key("D"))
    [parent] = [o for o in d["operations"] if o["kind"] == "setParent"]
    y_model = other.configuration.model
    containers = {
        item["relationTypeKey"]
        for item in y_model["objectTypeRelations"]
        if item["fromObjectTypeKey"] == other.key("M") and item["toObjectTypeKey"] == other.key("D")
    }
    assert parent["parent"]["from"] == "source"
    assert parent["parent"]["relationTypeKey"] in containers & _containment(y_model)

    relations = [p for p in proposals if p["kind"] == "relation"]
    x_model = world.configuration.model
    for binding in x_model["objectTypeRelations"]:
        if binding["relationTypeKey"] in _containment(x_model):
            continue
        proposal = next(
            p
            for p in relations
            if (p["sourceType"], p["relation"])
            == (binding["fromObjectTypeKey"], binding["relationTypeKey"])
        )
        structure = _structure(world, binding["relationTypeKey"])
        assert structure in RELATIONS
        assert proposal["target"] == other.key(structure), proposal

    value = f"U-{uuid4().hex[:6]}"
    names = _renamed(other.configuration.model)
    other_renamed, _release, renamed_target = _beside(world, names)
    for index in range(3):
        world.made("R", f"Shared {index}", values={"R.u": f"{value}-{index}"})
        other_renamed.made(
            "R", f"Shared {index}", workspace=renamed_target, values={"R.u": f"{value}-{index}"}
        )
    renamed = _create(world, W1, renamed_target)
    _infer(world, renamed["key"], W1, renamed_target)
    r = _type_proposal(_proposals(world, renamed["key"]), world.key("R"))
    assert r["target"] == other.key("R")
    assert "sameName" not in {item["kind"] for item in r["evidence"]}
    stored = next(item for item in r["evidence"] if item["kind"] == "storedRecords")
    assert stored["matched"] >= 3
    assert r["alternatives"] and all(a["target"] != r["target"] for a in r["alternatives"])


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_proposals_applied_as_steps_marked_proposed(world):
    """Given the mapping inferred. When its proposals are applied. Then each becomes one step of
    origin ``proposal``, the version rises, a new inference reads every proposal applied, and the
    mapping covers every type, attribute and relationship of X: what is left are the parents Y does
    not allow."""
    other, _y, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    proposals = _proposals(world, key)

    step = _apply(world, key)
    assert step["version"] > 1
    steps = {entry["step"] for entry in step["entries"]}
    assert len(steps) == len(proposals)
    assert {entry["origin"]["type"] for entry in step["entries"]} == {"proposal"}
    assert {entry["origin"]["proposalId"] for entry in step["entries"]} == {
        p["id"] for p in proposals
    }

    inference = _infer(world, key, W1, target)
    assert inference["counts"]["applied"] == len(proposals) and inference["counts"]["open"] == 0
    mapping = _read(world, key)
    assert {item["source"]: item["target"] for item in mapping["types"]} == _expected_types(
        world, other
    )
    coverage = mapping["coverage"]
    assert coverage["types"] == [] and coverage["attributes"] == [] and coverage["relations"] == []
    assert coverage["required"] == [] and coverage["requiredRelations"] == []
    # In B a dependant stands under the container alone: from A, one under the region stays behind.
    expected = (
        [{"sourceType": world.key("D"), "parentType": world.key("G")}]
        if world.configuration.name == "generated-a"
        else []
    )
    assert [
        {k: v for k, v in item.items() if k in ("sourceType", "parentType")}
        for item in coverage["parents"]
    ] == expected
    assert mapping["problems"] == []


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_a_mapping_corrected_by_hand(world):
    """Given the proposals applied. When attributes are mapped otherwise, a required attribute
    nothing fills gets a default, records are matched by Y's unique attribute, a value map is used
    and a relationship unmapped. Then each applies and the mapping says so; mapping onto an
    attribute Y's type does not bind, across value types that never convert, or onto a relationship
    Y does not allow is refused at its pointer; a new inference holds the corrected proposal."""
    other, _y, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    _apply(world, key)
    r, y_r = world.key("R"), other.key("R")

    ok(
        _operate(
            world,
            key,
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.q"),
                "ignore": True,
            },
        )
    )
    assert {"targetType": y_r, "attributeTypeKey": other.key("R.q")} in _read(world, key)[
        "coverage"
    ]["required"]
    ok(
        _operate(
            world,
            key,
            {
                "kind": "setDefault",
                "sourceType": r,
                "attribute": other.key("R.q"),
                "value": "Unknown owner",
            },
        )
    )
    ok(_operate(world, key, {"kind": "setValueMap", "name": "blanks", "values": {"N/A": None}}))
    ok(
        _operate(
            world,
            key,
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.x1"),
                "target": other.key("R.x2"),
            },
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.x2"),
                "target": other.key("R.x1"),
                "valueMap": "blanks",
            },
            {"kind": "setMatch", "sourceType": r, "match": {"attributeTypeKey": other.key("R.u")}},
            {"kind": "unmapRelation", "sourceType": r, "relation": world.key("B11")},
        )
    )
    mapping = _read(world, key)
    entry = _entry(mapping, r)
    attributes = {item["source"]: item for item in entry["attributes"]}
    assert attributes[world.key("R.q")] == {"source": world.key("R.q"), "ignore": True}
    assert attributes[world.key("R.x2")] == {
        "source": world.key("R.x2"),
        "target": other.key("R.x1"),
        "valueMap": "blanks",
    }
    assert entry["defaults"] == {other.key("R.q"): "Unknown owner"}
    assert entry["match"] == {"attributeTypeKey": other.key("R.u")}
    assert world.key("B11") not in {item["source"] for item in entry["relations"]}
    assert mapping["valueMaps"] == {"blanks": {"N/A": None}}
    assert mapping["coverage"]["required"] == []
    assert {"sourceType": r, "relationTypeKey": world.key("B11")} in mapping["coverage"][
        "relations"
    ]

    for operation, reason in (
        (
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.u"),
                "target": other.key("H.code"),
            },
            "bindingNotAllowed",
        ),
        (
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.b"),
                "target": other.key("R.dt"),
            },
            "valueTypesNotConvertible",
        ),
        (
            {
                "kind": "mapRelation",
                "sourceType": r,
                "relation": world.key("B1n"),
                "target": other.key("Bnn"),
            },
            "bindingNotAllowed",
        ),
    ):
        refusal = refused(_operate(world, key, operation), 422, "INVALID_OPERATION")
        assert refusal["details"]["reason"] == reason
        assert refusal["details"]["pointer"] == "/operations/0/target"
    assert _read(world, key)["version"] == mapping["version"]

    _infer(world, key, W1, target)
    assert _type_proposal(_proposals(world, key), r)["status"] == "held"


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_a_mapping_undone_and_redone(world):
    """Given the proposals applied and a hand step. When the hand step is undone and redone, the
    last proposal step undone, an operation sent at a stale version and a proposal step undone that a
    later step depends on. Then undo restores the mapping exactly and redo applies the step again;
    the undone proposal reads rejected on the next inference; the stale operation is a version
    conflict naming the newer entries; the depended-on step is refused with its dependants."""
    other, _y, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    applied = _apply(world, key)
    last_proposal = applied["entries"][-1]["origin"]["proposalId"]
    r = world.key("R")

    before = _read(world, key)
    hand = ok(
        _operate(
            world,
            key,
            {
                "kind": "mapAttribute",
                "sourceType": r,
                "attribute": world.key("R.x1"),
                "target": other.key("R.x2"),
            },
        )
    )
    changed = _read(world, key)
    undone = ok(
        world.api.post(f"/model-mappings/{key}/undo", {"expectedVersion": changed["version"]})
    )
    assert _read(world, key)["types"] == before["types"]
    ok(world.api.post(f"/model-mappings/{key}/redo", {"expectedVersion": undone["version"]}))
    assert _read(world, key)["types"] == changed["types"]

    stale = refused(_operate_at(world, key, before["version"]), 409, "VERSION_CONFLICT")
    assert hand["entries"][0]["sequence"] in {
        entry["sequence"] for entry in stale["details"]["operations"]
    }

    r_step = next(
        e["step"]
        for e in applied["entries"]
        if e["origin"]["proposalId"] == _type_proposal(_proposals(world, key), r)["id"]
    )
    current = _read(world, key)["version"]
    dependants = refused(
        world.api.post(f"/model-mappings/{key}/undo", {"expectedVersion": current, "step": r_step}),
        409,
        "OPERATION_HAS_DEPENDANTS",
    )
    assert dependants["details"]["steps"] == [r_step] and dependants["details"]["dependants"]

    last_step = next(
        e["step"] for e in applied["entries"] if e["origin"]["proposalId"] == last_proposal
    )
    ok(
        world.api.post(
            f"/model-mappings/{key}/undo", {"expectedVersion": current, "step": last_step}
        )
    )
    _infer(world, key, W1, target)
    rejected = [p["id"] for p in _proposals(world, key) if p["status"] == "rejected"]
    assert rejected == [last_proposal]


def _operate_at(world, key, version):
    body = {
        "expectedVersion": version,
        "operations": [{"kind": "setValueMap", "name": "late", "values": {}}],
    }
    return world.api.post(f"/model-mappings/{key}/operations", body)


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_drift_reported_and_the_mapping_re_pointed(world):
    """Given the proposals applied. When the target workspace activates a release of Y without an
    attribute the mapping names. Then the read naming that workspace lists the entry in its problems
    and the plain read does not; once the mapping is re-pointed to that release every read does;
    unmapping the attribute clears it; the mapping deleted at its version is not found."""
    other, _y, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    _apply(world, key)
    l1, gone = world.key("L1"), other.key("L.only1")

    smaller = copy.deepcopy(other.configuration.model)
    smaller["release"]["version"] += "-smaller"
    smaller["attributeTypes"] = [item for item in smaller["attributeTypes"] if item["key"] != gone]
    for item in smaller["objectTypes"]:
        item["attributes"] = [b for b in item["attributes"] if b["attributeTypeKey"] != gone]
    release = world.install(smaller, name="Smaller")
    ok(world.activate(release["id"], target))

    mapping = _read(world, key)
    entry_index = next(i for i, item in enumerate(mapping["types"]) if item["source"] == l1)
    attribute_index = next(
        i
        for i, item in enumerate(mapping["types"][entry_index]["attributes"])
        if item.get("target") == gone
    )
    pointer = f"/types/{entry_index}/attributes/{attribute_index}/target"
    assert mapping["problems"] == []
    [problem] = _read(world, key, targetWorkspaceKey=target)["problems"]
    assert (problem["code"], problem["pointer"], problem["side"]) == (
        "ELEMENT_NOT_IN_RELEASE",
        pointer,
        "target",
    )

    ok(_operate(world, key, {"kind": "setReleases", "targetReleaseId": release["id"]}))
    re_pointed = _read(world, key)
    assert re_pointed["targetReleaseId"] == release["id"]
    assert [p["pointer"] for p in re_pointed["problems"]] == [pointer]
    ok(
        _operate(
            world,
            key,
            {"kind": "unmapAttribute", "sourceType": l1, "attribute": world.key("L.only1")},
        )
    )
    assert _read(world, key)["problems"] == []
    assert _read(world, key, targetWorkspaceKey=target)["problems"] == []

    version = _read(world, key)["version"]
    refused(
        world.api.delete(f"/model-mappings/{key}", expectedVersion=version - 1),
        409,
        "VERSION_CONFLICT",
    )
    assert world.api.delete(f"/model-mappings/{key}", expectedVersion=version).status_code == 204
    refused(world.api.get(f"/model-mappings/{key}"), 404, "MODEL_MAPPING_NOT_FOUND")


@pytest.mark.journey("J38.1")
@pytest.mark.structures(*BOTH)
def test_the_same_model_on_both_sides(world):
    """Given a second workspace on X. When a mapping between the default workspace and it is
    inferred. Then every type and relationship is proposed to itself, with the evidence that both
    sides run one model."""
    x = _model(world)
    target = _on(world, x["releaseId"])
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    proposals = _proposals(world, key)
    types = [p for p in proposals if p["kind"] == "type"]
    assert {p["sourceType"] for p in types} == _types(world.configuration.model)
    for proposal in proposals:
        same = proposal["sourceType"] if proposal["kind"] == "type" else proposal["relation"]
        assert proposal["target"] == same, proposal
        assert "sameModel" in {item["kind"] for item in proposal["evidence"]}
        for operation in proposal["operations"]:
            if operation["kind"] == "mapAttribute":
                assert operation["target"] == operation["attribute"]
