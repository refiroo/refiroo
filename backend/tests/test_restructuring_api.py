"""Base 0.8 C3: the restructuring API (ADR-034).

``POST /change-sets/{id}/restructurings/preview`` and ``POST /change-sets/{id}/restructurings``
with each operation kind, over HTTP: the plan's records paged by position in plan order and
filtered by outcome, the claim (a stale version, another plan, a plan that is not ready), a refused
operation leaving nothing behind, and per-record outcomes. Parent candidates gain
``includeTypeChanges``.

The operation kinds run over the generated model (no starter key); the move with a type change and
the parent candidates run over the starter model and the same model with every key renamed.
"""

import pytest
from test_type_changes import (
    WORKSPACE,
    attr,
    create,
    object_changes,
    publish,
    read,
    relate,
    relations_of,
    start_change_set,
    starter,  # noqa: F401 - fixture
    values,
    version,
    volume,  # noqa: F401 - fixture
)
from volume_fixture import (
    ACTIVE,
    APPLICATION,
    CELL,
    CODE,
    COLUMN,
    GROUP,
    GROUP_HAS_CELL,
    ITEM,
    ITEM_CITES_GROUP,
    MATRIX_APPLICATION,
    NODE,
    SHELF,
)


def _group(client, name, parent=None, object_type=GROUP, **context):
    return create(client, APPLICATION, object_type, name, [attr(CODE, name.lower())], parent, **context)


def preview(client, change_set, body, expected=200, **paging):
    response = client.post(
        f"/api/v1/change-sets/{change_set['id']}/restructurings/preview", json={**body, **paging}
    )
    assert response.status_code == expected, response.text
    return response.json() if expected == 200 else response.json()["error"]


def claim(client, change_set, body, plan, expected=200):
    response = client.post(
        f"/api/v1/change-sets/{change_set['id']}/restructurings",
        json={
            **body,
            "expectedChangeSetVersion": plan["changeSetVersion"],
            "planDigest": plan["planDigest"],
        },
    )
    assert response.status_code == expected, response.text
    return response.json() if expected == 200 else response.json()["error"]


def apply(client, change_set, body):
    """Preview every record, then apply the previewed plan; the plan and the result."""
    plan = preview(client, change_set, body, pageSize=500)
    assert plan["status"] == "ready", plan
    result = claim(client, change_set, body, plan)
    assert result["changeSetVersion"] == plan["changeSetVersion"] + 1 == version(client, change_set)
    assert result["summary"] == plan["summary"]
    return plan, result


def by_name(plan) -> dict[str, dict]:
    return {item["name"]: item for item in plan["records"]}


def parent_edges(client, change_set, record) -> list[tuple[str, str]]:
    edges = relations_of(client, record["id"], changeSetId=change_set["id"], direction="incoming")
    return [(edge["relationTypeKey"], edge["fromObjectId"]) for edge in edges]


# --- move: paging, the outcome filter and the claim ---------------------------------------------


def test_a_move_pages_its_plan_and_apply_claims_it(volume):  # noqa: F811
    """A > B > C and A > J under Z as a node: every level becomes a node."""
    client = volume
    target = _group(client, "Z")
    top = _group(client, "A")
    middle = _group(client, "B", top)
    _group(client, "C", middle)
    _group(client, "J", top, object_type=ITEM)
    change_set = start_change_set(client)
    body = {"operation": {"kind": "move", "objectId": top["id"], "parentObjectId": target["id"], "objectTypeKey": NODE}}

    first = preview(client, change_set, body, pageSize=2, includeTotal=True)
    assert first["status"] == "ready"
    assert first["summary"]["recordCount"] == 4 and first["summary"]["typeChangeCount"] == 4
    assert [item["name"] for item in first["records"]] == ["A", "B"]
    assert (first["totalCount"], first["startIndex"], first["prevCursor"]) == (4, 0, None)
    second = preview(client, change_set, body, pageSize=2, cursor=first["nextCursor"])
    assert [item["name"] for item in second["records"]] == ["J", "C"]
    assert second["nextCursor"] is None and "totalCount" not in second
    back = preview(client, change_set, body, pageSize=2, cursor=second["prevCursor"])
    assert [item["name"] for item in back["records"]] == ["A", "B"]
    assert [item["name"] for item in preview(client, change_set, body, position=3)["records"]] == ["C"]
    # The filter: only A moves; each record changes type.
    moved = preview(client, change_set, body, outcome=["moved"], includeTotal=True)
    assert [item["name"] for item in moved["records"]] == ["A"] and moved["totalCount"] == 1
    record = moved["records"][0]
    assert record["outcomes"] == ["typeChanged", "moved"]
    assert record["before"] == {"objectTypeKey": GROUP, "parentObjectId": None}
    assert record["after"] == {"objectTypeKey": NODE, "parentObjectId": target["id"]}
    assert [part["name"] for part in record["path"]] == ["Z", "A"]
    assert {item["attributeTypeKey"]: (item["outcome"], item["from"]) for item in record["attributes"]}[
        CODE
    ] == ("kept", CODE)
    # A cursor is bound to its filter.
    assert preview(client, change_set, body, 422, outcome=["refused"], cursor=first["nextCursor"])["code"] == "invalid_cursor"
    # Paging parameters are one at a time.
    assert preview(client, change_set, body, 422, position=1, cursor=first["nextCursor"])["code"] == "conflicting_page_parameters"

    # The claim: another plan, a stale version.
    changed = claim(client, change_set, body, {**first, "planDigest": "0" * 64}, 409)
    assert changed["code"] == "restructuring_plan_changed"
    assert changed["details"] == {"planDigest": first["planDigest"]}
    plan, result = apply(client, change_set, body)
    assert plan["planDigest"] == first["planDigest"]
    assert result["changeSetId"] == change_set["id"] and result["operationId"]
    assert result["createdObjectId"] is None
    assert claim(client, change_set, body, plan, 409)["code"] == "change_set_version_conflict"
    # The plan's cursors belong to the change set's version the plan read.
    assert preview(client, change_set, body, 422, cursor=first["nextCursor"])["code"] == "invalid_cursor"
    assert preview(client, change_set, body, 409, expectedChangeSetVersion=plan["changeSetVersion"])["code"] == (
        "change_set_version_conflict"
    )
    assert read(client, NODE, top["id"], changeSetId=change_set["id"])["parentObjectId"] == target["id"]
    # The review lists what the operation touched.
    assert {item["objectId"] for item in object_changes(client, change_set)} >= {top["id"], middle["id"]}


def test_a_refused_operation_leaves_nothing_behind(volume):  # noqa: F811
    client = volume
    top = _group(client, "A", _group(client, "Z"))
    items = [_group(client, f"I{index}", top, object_type=ITEM) for index in range(2)]
    change_set = start_change_set(client)
    body = {"operation": {"kind": "changeType", "objectId": top["id"], "objectTypeKey": ITEM}}
    before = version(client, change_set)

    plan = preview(client, change_set, body, outcome=["refused"])
    assert plan["status"] == "refused"
    assert sorted((item["code"], item["objectId"]) for item in plan["refusals"]) == sorted(
        ("noPossibleType", item["id"]) for item in items
    )
    assert [item["refusals"][0]["code"] for item in plan["records"]] == ["noPossibleType"] * 2
    not_ready = claim(client, change_set, body, plan, 422)
    assert not_ready["code"] == "restructuring_not_ready"
    assert not_ready["details"]["summary"]["refusalCount"] == 2
    assert version(client, change_set) == before
    assert object_changes(client, change_set) == []
    # A request the planner cannot read is an error, not a plan.
    same = {"operation": {"kind": "changeType", "objectId": top["id"], "objectTypeKey": GROUP}}
    assert preview(client, change_set, same, 422)["code"] == "object_type_unchanged"
    unknown = {"operation": {"kind": "changeType", "objectId": top["id"], "objectTypeKey": "nothing"}}
    assert preview(client, change_set, unknown, 422)["code"] == "unknown_object_type"
    bad_kind = {"operation": {"kind": "reshape", "objectId": top["id"]}}
    preview(client, change_set, bad_kind, 422)
    missing = {"operation": {"kind": "removeLevel", "objectId": top["id"]}}
    response = client.post(
        "/api/v1/change-sets/00000000-0000-4000-8000-000000000000/restructurings/preview", json=missing
    )
    assert response.status_code == 404 and response.json()["error"]["code"] == "change_set_not_found"


# --- insertLevel --------------------------------------------------------------------------------


def test_insert_level_creates_a_record_and_moves_the_chosen_children(volume):  # noqa: F811
    """Z holds P (a group), I1 and I2 (items); a group inserted under Z takes P and I1."""
    client = volume
    target = _group(client, "Z")
    held = _group(client, "P", target)
    first = _group(client, "I1", target, object_type=ITEM)
    second = _group(client, "I2", target, object_type=ITEM)
    elsewhere = _group(client, "Q")
    change_set = start_change_set(client)
    operation = {
        "kind": "insertLevel",
        "parentObjectId": target["id"],
        "childObjectIds": [first["id"], held["id"]],
        "objectTypeKey": GROUP,
        "name": "Level",
    }

    plan = preview(client, change_set, {"operation": operation})
    assert plan["status"] == "needsInput"
    created = by_name(plan)["Level"]
    assert created["objectId"] == "new" and created["before"] is None
    assert created["after"] == {"objectTypeKey": GROUP, "parentObjectId": target["id"]}
    assert created["outcomes"] == ["created"]
    assert created["inputsNeeded"] == [{"kind": "attribute", "key": CODE, "reason": "required"}]
    assert [item["name"] for item in plan["records"]] == ["Level", "I1", "P"]
    assert by_name(plan)["P"]["outcomes"] == ["moved"]
    assert [part["id"] for part in by_name(plan)["P"]["path"]] == [target["id"], "new", held["id"]]
    assert plan["summary"]["createdCount"] == 1 and plan["summary"]["moveCount"] == 2

    # A child that is not under the parent is refused.
    stray = {**operation, "childObjectIds": [elsewhere["id"]]}
    assert [(item["code"], item["objectId"]) for item in preview(client, change_set, {"operation": stray})["refusals"]] == [
        ("notUnderParent", elsewhere["id"])
    ]
    # A node level: a node holds only nodes here, so the item becomes one.
    as_node = {**operation, "objectTypeKey": NODE, "childObjectIds": [second["id"]]}
    node_plan = preview(client, change_set, {"operation": as_node, "inputs": [{"objectId": "new", "attributes": [attr(CODE, "n")]}]})
    assert by_name(node_plan)["I2"]["after"]["objectTypeKey"] == NODE
    assert by_name(node_plan)["I2"]["outcomes"] == ["typeChanged", "moved"]

    body = {"operation": operation, "inputs": [{"objectId": "new", "attributes": [attr(CODE, "lvl")]}]}
    plan, result = apply(client, change_set, body)
    assert {item["attributeTypeKey"]: item["outcome"] for item in by_name(plan)["Level"]["attributes"]}[CODE] == "input"
    level_id = result["createdObjectId"]
    level = read(client, GROUP, level_id, changeSetId=change_set["id"])
    assert level["parentObjectId"] == target["id"] and values(level)[CODE] == "lvl"
    assert read(client, GROUP, held["id"], changeSetId=change_set["id"])["parentObjectId"] == level_id
    assert read(client, ITEM, first["id"], changeSetId=change_set["id"])["parentObjectId"] == level_id
    assert read(client, ITEM, second["id"], changeSetId=change_set["id"])["parentObjectId"] == target["id"]
    assert parent_edges(client, change_set, held) == [("vol-group-has-child", level_id)]
    assert parent_edges(client, change_set, first) == [("vol-group-contains-item", level_id)]
    added = [item for item in object_changes(client, change_set) if item["kind"] == "added"]
    assert [item["objectId"] for item in added] == [level_id]
    publish(client, change_set)
    assert read(client, ITEM, first["id"], workspaceKey=WORKSPACE)["parentObjectId"] == level_id


# --- removeLevel --------------------------------------------------------------------------------


def test_remove_level_deletes_a_record_and_moves_its_children_up(volume):  # noqa: F811
    """Z > A > (B > I, J), with K citing A: removing A moves B and J under Z and takes the
    citation with it. At the top level, a removed group's item becomes a group."""
    client = volume
    target = _group(client, "Z")
    level = _group(client, "A", target)
    inner = _group(client, "B", level)
    leaf = _group(client, "I", inner, object_type=ITEM)
    beside = _group(client, "J", level, object_type=ITEM)
    citing = _group(client, "K", _group(client, "Y"), object_type=ITEM)
    cited = relate(client, ITEM_CITES_GROUP, citing, level)
    change_set = start_change_set(client)
    body = {"operation": {"kind": "removeLevel", "objectId": level["id"]}}

    plan, _result = apply(client, change_set, body)
    assert [item["name"] for item in plan["records"]] == ["A", "B", "J"]
    removed = by_name(plan)["A"]
    assert removed["outcomes"] == ["removed"] and removed["after"] is None
    assert removed["before"] == {"objectTypeKey": GROUP, "parentObjectId": target["id"]}
    assert [(item["relationId"], item["objectId"]) for item in removed["withoutPlace"]["relationships"]] == [
        (cited["id"], citing["id"])
    ]
    assert by_name(plan)["B"]["outcomes"] == ["moved"]
    assert by_name(plan)["B"]["after"] == {"objectTypeKey": GROUP, "parentObjectId": target["id"]}
    assert plan["summary"]["removedCount"] == 1 and plan["summary"]["relationshipsWithoutPlaceCount"] == 1
    assert read(client, GROUP, level["id"], 404, changeSetId=change_set["id"])["code"] == "object_not_found"
    assert read(client, GROUP, inner["id"], changeSetId=change_set["id"])["parentObjectId"] == target["id"]
    assert read(client, ITEM, leaf["id"], changeSetId=change_set["id"])["parentObjectId"] == inner["id"]
    assert parent_edges(client, change_set, beside) == [("vol-group-contains-item", target["id"])]
    assert relations_of(client, citing["id"], changeSetId=change_set["id"], direction="outgoing") == []
    removed_changes = [item for item in object_changes(client, change_set) if item["kind"] == "removed"]
    assert [item["objectId"] for item in removed_changes] == [level["id"]]
    publish(client, change_set)
    assert read(client, GROUP, level["id"], 404, workspaceKey=WORKSPACE)["code"] == "object_not_found"

    # At the top level only groups may stand: the item becomes one.
    top = _group(client, "T")
    _group(client, "O", top, object_type=ITEM)
    change_set = start_change_set(client)
    plan = preview(client, change_set, {"operation": {"kind": "removeLevel", "objectId": top["id"]}})
    assert by_name(plan)["O"]["after"] == {"objectTypeKey": GROUP, "parentObjectId": None}
    assert by_name(plan)["O"]["outcomes"] == ["typeChanged", "moved"]

    # A matrix row a cell requires cannot be removed: the cell would lose its row.
    row = create(client, MATRIX_APPLICATION, GROUP, "Row", [attr(CODE, "row")])
    column = create(client, MATRIX_APPLICATION, COLUMN, "Col", [attr(CODE, "col")])
    shelf = create(client, MATRIX_APPLICATION, SHELF, "Shelf", [attr(CODE, "shelf")], column)
    cell = create(
        client,
        MATRIX_APPLICATION,
        CELL,
        "Cell",
        [attr(CODE, "cell"), attr(ACTIVE, True)],
        shelf,
        [{"relationTypeKey": GROUP_HAS_CELL, "direction": "incoming", "otherObjectId": row["id"]}],
    )
    change_set = start_change_set(client)
    body = {"operation": {"kind": "removeLevel", "objectId": row["id"]}}
    plan = preview(client, change_set, body)
    assert plan["status"] == "refused"
    ((refusal),) = plan["refusals"]
    assert (refusal["code"], refusal["objectId"], refusal["conflictingObjectId"]) == (
        "requiredRelationWithoutPlace",
        row["id"],
        cell["id"],
    )
    assert claim(client, change_set, body, plan, 422)["code"] == "restructuring_not_ready"
    assert object_changes(client, change_set) == []


# --- changeTypeUnder ----------------------------------------------------------------------------


def test_change_type_under_changes_every_record_of_a_type(volume):  # noqa: F811
    """Z > A > B > I and Z > C: every group under Z becomes a node, and B's item a node too."""
    client = volume
    target = _group(client, "Z")
    upper = _group(client, "A", target)
    lower = _group(client, "B", upper)
    leaf = _group(client, "I", lower, object_type=ITEM)
    beside = _group(client, "C", target)
    change_set = start_change_set(client)
    operation = {"kind": "changeTypeUnder", "objectId": target["id"], "fromObjectTypeKey": GROUP, "objectTypeKey": NODE}

    plan, _result = apply(client, change_set, {"operation": operation})
    assert [item["name"] for item in plan["records"]] == ["A", "C", "B", "I"]
    assert all(item["outcomes"] == ["typeChanged"] for item in plan["records"])
    assert [part["name"] for part in by_name(plan)["I"]["path"]] == ["Z", "A", "B", "I"]
    assert {(item["fromObjectTypeKey"], item["toObjectTypeKey"]): item["recordCount"] for item in plan["pairs"]} == {
        (GROUP, NODE): 3,
        (ITEM, NODE): 1,
    }
    for record, parent, relation in (
        (upper, target, "vol-group-contains-node"),
        (beside, target, "vol-group-contains-node"),
        (lower, upper, "vol-node-has-child"),
        (leaf, lower, "vol-node-has-child"),
    ):
        assert read(client, NODE, record["id"], changeSetId=change_set["id"])["objectTypeKey"] == NODE
        assert parent_edges(client, change_set, record) == [(relation, parent["id"])]
    # Z itself is not under Z; a group at the top cannot become a node.
    assert read(client, GROUP, target["id"], changeSetId=change_set["id"])["objectTypeKey"] == GROUP
    same = {**operation, "objectTypeKey": GROUP}
    assert preview(client, change_set, {"operation": same}, 422)["code"] == "object_type_unchanged"
    nothing = preview(client, change_set, {"operation": operation})
    assert nothing["status"] == "ready" and nothing["records"] == []


# --- the starter model: a move with a type change and the parent candidates --------------------


def test_parent_candidates_include_type_changes_and_the_move_applies(starter):  # noqa: F811
    client, k = starter
    systems = k("rdm-systems")
    target = create(client, systems, k("system"), "S", [attr(k("system-code"), "s")])
    moved = create(client, systems, k("system"), "T", [attr(k("system-code"), "t")])
    change_set = start_change_set(client)
    url = f"/api/v1/objects/{k('system')}/{moved['id']}/parent-candidates"

    # A system stands at the top: nothing contains it without a type change.
    plain = client.get(url, params={"changeSetId": change_set["id"]}).json()
    assert plain["items"] == []
    widened = client.get(url, params={"changeSetId": change_set["id"], "includeTypeChanges": "true"})
    assert widened.status_code == 200, widened.text
    by_id = {item["id"]: item for item in widened.json()["items"]}
    assert by_id[target["id"]]["objectTypeKeys"] == [k("system-group"), k("system-value")]
    assert by_id[target["id"]]["eligible"] is True
    assert by_id[moved["id"]]["reason"] == "self"
    live = client.get(url, params={"workspaceKey": WORKSPACE, "includeTypeChanges": "true"})
    assert live.status_code == 422 and live.json()["error"]["code"] == "type_changes_need_change_set"
    # Without the flag a candidate names no types.
    value = create(
        client,
        systems,
        k("system-value"),
        "V",
        [attr(k("value-code"), "v"), attr(k("value-name"), "V")],
        target,
    )
    value_url = f"/api/v1/objects/{k('system-value')}/{value['id']}/parent-candidates"
    assert all(
        "objectTypeKeys" not in item
        for item in client.get(value_url, params={"workspaceKey": WORKSPACE}).json()["items"]
    )

    body = {"operation": {"kind": "move", "objectId": moved["id"], "parentObjectId": target["id"]}}
    plan = preview(client, change_set, body)
    assert plan["status"] == "needsInput"
    assert plan["typeQuestions"][0]["options"] == [k("system-group"), k("system-value")]
    body["choices"] = {
        "types": [
            {
                "objectTypeKey": k("system"),
                "parentObjectTypeKey": k("system"),
                "newObjectTypeKey": k("system-group"),
            }
        ],
        "mappings": [
            {
                "fromObjectTypeKey": k("system"),
                "toObjectTypeKey": k("system-group"),
                "attributes": [{"attributeTypeKey": k("group-code"), "from": k("system-code")}],
            }
        ],
    }
    plan, _result = apply(client, change_set, body)
    (pair,) = plan["pairs"]
    code = next(item for item in pair["attributes"] if item["attributeTypeKey"] == k("group-code"))
    assert (code["from"], code["rule"], code["mapped"]) == (k("system-code"), "choice", 1)
    group = read(client, k("system-group"), moved["id"], changeSetId=change_set["id"])
    assert group["parentObjectId"] == target["id"] and values(group)[k("group-code")] == "t"
    # D42: the old type in the route says where the record is.
    stale = read(client, k("system"), moved["id"], 409, changeSetId=change_set["id"])
    assert stale["code"] == "object_type_changed"
    assert stale["details"]["objectTypeKey"] == k("system-group")


@pytest.mark.parametrize("field", ["childObjectIds", "inputs"])
def test_requests_that_repeat_a_record_are_refused(volume, field):  # noqa: F811
    client = volume
    target = _group(client, "Z")
    child = _group(client, "A", target)
    change_set = start_change_set(client)
    operation = {
        "kind": "insertLevel",
        "parentObjectId": target["id"],
        "childObjectIds": [child["id"]],
        "objectTypeKey": GROUP,
        "name": "Level",
    }
    body = {"operation": operation}
    if field == "childObjectIds":
        operation["childObjectIds"] = [child["id"], child["id"]]
    else:
        body["inputs"] = [{"objectId": "new"}, {"objectId": "new"}]
    response = client.post(f"/api/v1/change-sets/{change_set['id']}/restructurings/preview", json=body)
    assert response.status_code == 422, response.text
