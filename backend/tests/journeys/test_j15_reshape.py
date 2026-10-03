"""J15 — Reshape a hierarchy across types, and change a record back (USER_JOURNEYS.md)."""

import pytest
from scenario import ok, refused

LADDER = ("L1", "L2", "L3", "K", "Ll1k", "Ll2k", "L.only1", "L.extra")


def _restructure(world, change_set, operation, *, apply=False, **body):
    body = {"operation": operation, **body}
    if apply:
        body.setdefault("expectedChangeSetVersion", world.current(change_set)["version"])
    path = f"/change-sets/{change_set['id']}/restructurings" + ("" if apply else "/preview")
    return world.api.post(path, body)


def _plan(world, change_set, operation, **body):
    return ok(_restructure(world, change_set, operation, **body))


def _record(plan, object_id):
    return next(item for item in plan["records"] if item["objectId"] == object_id)


def _ladder(world, name, depth=3, related=None):
    """A top-level L1 record with one record per level below it (L2, then L3s); its L1 relates to
    ``related`` K records through the relationship only L1 has."""
    top = world.made(
        "L1",
        name,
        values={"L.code": f"{name}-1", "L.only1": "kept for later"},
        relations=[
            {"relationTypeKey": world.key("Ll1k"), "direction": "outgoing", "otherObjectId": k}
            for k in (related or [])
        ],
    )
    records, parent = [top], top["id"]
    for level in range(2, depth + 1):
        record = world.made(
            "L2" if level == 2 else "L3",
            f"{name} {level}",
            parent=parent,
            values={"L.code": f"{name}-{level}"},
        )
        records.append(record)
        parent = record["id"]
    return records


def _inputs(world, *object_ids):
    return [
        {
            "objectId": object_id,
            "attributes": [{"attributeTypeKey": world.key("L.extra"), "value": "given"}],
        }
        for object_id in object_ids
    ]


@pytest.mark.journey("J15")
@pytest.mark.structures(*LADDER)
def test_move_with_a_type_change_answer_the_plan_apply_and_publish(world):
    """Given in a change set a top-level L1 record t with a subtree, and another top-level L1 record
    t2. When t is previewed under t2, then again with the input the plan asks for. Then the first plan
    needs input: t becomes L2 and its child L3, with each value's source and outcome, what has no
    place and what is needed; nothing is written. The second is ready. When applied and published,
    t is L2 under the same ID, its history names the reclassification, and the old type's route says
    the type changed. A plan not ready, a change to the same type and a mapping from an attribute the
    old type lacks are refused."""
    t, child, _grandchild = _ladder(world, "Moving")
    t2 = world.made("L1", "Receiving", values={"L.code": "R-1"})
    csr = world.change_set()
    version = world.current(csr)["version"]
    operation = {"kind": "move", "objectId": t["id"], "parentObjectId": t2["id"]}

    first = _plan(world, csr, operation)
    assert first["status"] == "needsInput"
    planned = _record(first, t["id"])
    assert planned["after"]["objectTypeKey"] == world.key("L2")
    assert _record(first, child["id"])["after"]["objectTypeKey"] == world.key("L3")
    assert all({"from", "outcome"} <= set(a) for a in planned["attributes"])
    assert world.key("L.only1") in {
        a["attributeTypeKey"] for a in planned["withoutPlace"]["attributes"]
    }
    assert world.key("L.extra") in {
        n.get("attributeTypeKey") or n.get("key") for n in planned["inputsNeeded"]
    }
    assert world.current(csr)["version"] == version
    refused(
        _restructure(world, csr, operation, apply=True, planDigest=first["planDigest"]),
        422,
        "restructuring_not_ready",
    )

    mappings = [
        {"fromObjectTypeKey": world.key("L1"), "toObjectTypeKey": world.key("L2"), "attributes": []}
    ]
    ready = _plan(
        world, csr, operation, inputs=_inputs(world, t["id"]), choices={"mappings": mappings}
    )
    assert ready["status"] == "ready" and ready["planDigest"]
    applied = ok(
        _restructure(
            world,
            csr,
            operation,
            apply=True,
            planDigest=ready["planDigest"],
            inputs=_inputs(world, t["id"]),
            choices={"mappings": mappings},
        )
    )
    assert applied["changeSetVersion"] == version + 1
    changes = ok(world.api.get(f"/change-sets/{csr['id']}/object-changes", pageSize=100))["items"]
    assert next(c for c in changes if c["objectId"] == t["id"])["changedFields"][0] == "objectType"

    world.publish(csr)
    assert world.record("L2", t["id"])["parentObjectId"] == t2["id"]
    history = ok(world.api.get(f"/objects/{world.key('L2')}/{t['id']}/history"))["items"]
    assert "reclassified" in {event["action"] for event in history}
    error = refused(world.read("L1", t["id"]), 409, "object_type_changed")
    assert error["details"]["objectTypeKey"] == world.key("L2")

    again = world.change_set()
    same = {"kind": "changeType", "objectId": t["id"], "objectTypeKey": world.key("L2")}
    refused(_restructure(world, again, same), 422, "object_type_unchanged")
    unbound = [
        {
            "fromObjectTypeKey": world.key("L2"),
            "toObjectTypeKey": world.key("L1"),
            "attributes": [{"attributeTypeKey": world.key("L.only1"), "from": "no-such-source"}],
        }
    ]
    back = {
        "kind": "move",
        "objectId": t["id"],
        "parentObjectId": None,
        "objectTypeKey": world.key("L1"),
    }
    refused(
        _restructure(world, again, back, choices={"mappings": unbound}), 422, "invalid_type_mapping"
    )


@pytest.mark.journey("J15.1")
@pytest.mark.structures(*LADDER)
def test_change_a_record_back_restores_what_had_no_place(world):
    """Given t published as L2 after a type change that left a value and a relationship without a
    place. When a new change set changes it back to L1 (to the top level, where L1 stands). Then the
    plan offers back the value and the relationship with its former ID; after apply the relationship
    reads under that ID; the earlier publication still holds t as L2."""
    k = world.ids["k06"]
    t, _child, _grandchild = _ladder(world, "Round trip", related=[k])
    lost = ok(world.api.get("/relations", objectId=t["id"], relationTypeKey=world.key("Ll1k")))
    lost_id = lost["items"][0]["relation"]["id"]
    t2 = world.made("L1", "Receiving", values={"L.code": "R-1"})
    first = world.change_set()
    down = {"kind": "move", "objectId": t["id"], "parentObjectId": t2["id"]}
    plan = _plan(world, first, down, inputs=_inputs(world, t["id"]))
    ok(
        _restructure(
            world,
            first,
            down,
            apply=True,
            planDigest=plan["planDigest"],
            inputs=_inputs(world, t["id"]),
        )
    )
    publication = world.publish(first)

    second = world.change_set()
    back = {
        "kind": "move",
        "objectId": t["id"],
        "parentObjectId": None,
        "objectTypeKey": world.key("L1"),
    }
    plan = _plan(world, second, back)
    record = _record(plan, t["id"])
    restored = {
        a["attributeTypeKey"]: a for a in record["attributes"] if a["outcome"] == "restored"
    }
    assert restored[world.key("L.only1")]["value"] == "kept for later"
    assert [r["relationId"] for r in record["restoredRelationships"]] == [lost_id]
    ok(_restructure(world, second, back, apply=True, planDigest=plan["planDigest"]))

    assert ok(world.api.get(f"/relations/{lost_id}", changeSetId=second["id"]))["id"] == lost_id
    assert world.record("L2", t["id"], publicationId=publication["id"])[
        "objectTypeKey"
    ] == world.key("L2")


@pytest.mark.journey("J15.2")
@pytest.mark.structures(*LADDER)
def test_a_type_change_cascades_over_several_levels(world):
    """Given an L1 subtree several levels deep. When it moves under another L1 record, forcing each
    level down. Then the plan lists each changed level in order with its types before and after, the
    summary counts the type changes, and after apply every level reads its new type under its ID."""
    top, middle, bottom, lowest = _ladder(world, "Cascade", depth=4)
    receiver = world.made("L1", "Receiver", values={"L.code": "RC-1"})
    cs = world.change_set()
    operation = {"kind": "move", "objectId": top["id"], "parentObjectId": receiver["id"]}

    plan = _plan(world, cs, operation, inputs=_inputs(world, top["id"]))
    order = [item["objectId"] for item in plan["records"]]
    assert order[:2] == [top["id"], middle["id"]]
    types = {
        item["objectId"]: (item["before"]["objectTypeKey"], item["after"]["objectTypeKey"])
        for item in plan["records"]
    }
    assert types[top["id"]] == (world.key("L1"), world.key("L2"))
    assert types[middle["id"]] == (world.key("L2"), world.key("L3"))
    changed = [key for key, (before, after) in types.items() if before != after]
    assert plan["summary"]["typeChangeCount"] == len(changed)

    ok(
        _restructure(
            world,
            cs,
            operation,
            apply=True,
            planDigest=plan["planDigest"],
            inputs=_inputs(world, top["id"]),
        )
    )
    for structure, record in (("L2", top), ("L3", middle), ("L3", bottom), ("L3", lowest)):
        assert world.record(structure, record["id"], changeSetId=cs["id"])["id"] == record["id"]


@pytest.mark.journey("J15.3")
@pytest.mark.structures(*LADDER)
def test_a_relationship_the_new_type_cannot_have_is_kept_in_history(world):
    """Given L2 record m related to K record k of the other application, a relationship L1 cannot
    hold. When m moves to the top level as L1. Then the plan lists the relationship without a place
    with k's ID and type; after apply the change set holds no such relationship and k's history names
    the reclassification; moving m back offers the relationship back."""
    top = world.made("L1", "Holder", values={"L.code": "H-1"})
    k = world.made("K", "Linked token")
    m = world.made(
        "L2",
        "Movable",
        parent=top["id"],
        values={"L.code": "M-2"},
        relations=[
            {
                "relationTypeKey": world.key("Ll2k"),
                "direction": "outgoing",
                "otherObjectId": k["id"],
            }
        ],
    )
    cs = world.change_set()
    up = {
        "kind": "move",
        "objectId": m["id"],
        "parentObjectId": None,
        "objectTypeKey": world.key("L1"),
    }

    plan = _plan(world, cs, up)
    lost = _record(plan, m["id"])["withoutPlace"]["relationships"]
    assert [(r["objectId"], r["objectTypeKey"]) for r in lost] == [(k["id"], world.key("K"))]
    ok(_restructure(world, cs, up, apply=True, planDigest=plan["planDigest"]))
    left = ok(
        world.api.get(
            "/relations", objectId=m["id"], changeSetId=cs["id"], relationTypeKey=world.key("Ll2k")
        )
    )["items"]
    assert left == []
    history = ok(
        world.api.get(f"/objects/{world.key('K')}/{k['id']}/history", changeSetId=cs["id"])
    )["items"]
    assert "reclassified" in {event["action"] for event in history}

    down = {
        "kind": "move",
        "objectId": m["id"],
        "parentObjectId": top["id"],
        "objectTypeKey": world.key("L2"),
    }
    back = _plan(world, cs, down, inputs=_inputs(world, m["id"]))
    assert [r["relationId"] for r in _record(back, m["id"])["restoredRelationships"]] == [
        lost[0]["relationId"]
    ]


@pytest.mark.journey("J15.4")
@pytest.mark.structures(*LADDER)
def test_a_change_after_the_preview_refuses_the_apply(world):
    """Given a ready plan and its digest at change set version v. When another write in the change
    set changes a planned record's value, then the plan is applied with v, then with the current
    version and the old digest. Then the first is a change set conflict, the second a changed plan
    with the current digest; the change set shows no restructuring."""
    t, _child, _grandchild = _ladder(world, "Contested")
    t2 = world.made("L1", "Receiving", values={"L.code": "R-1"})
    cs = world.change_set()
    version = world.current(cs)["version"]
    operation = {"kind": "move", "objectId": t["id"], "parentObjectId": t2["id"]}
    plan = _plan(world, cs, operation, inputs=_inputs(world, t["id"]))
    assert plan["status"] == "ready"

    staged = world.record("L1", t["id"], changeSetId=cs["id"])
    body = {
        "attributes": [{"attributeTypeKey": world.key("L.code"), "value": "changed"}],
        "expectedVersion": staged["version"],
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": version,
    }
    ok(world.api.patch(f"/objects/{world.key('L1')}/{t['id']}", body))

    stale = _restructure(
        world,
        cs,
        operation,
        apply=True,
        planDigest=plan["planDigest"],
        inputs=_inputs(world, t["id"]),
        expectedChangeSetVersion=version,
    )
    refused(stale, 409, "change_set_version_conflict")
    changed = _restructure(
        world,
        cs,
        operation,
        apply=True,
        planDigest=plan["planDigest"],
        inputs=_inputs(world, t["id"]),
    )
    error = refused(changed, 409, "restructuring_plan_changed")
    assert error["details"]["planDigest"] != plan["planDigest"]
    assert world.record("L1", t["id"], changeSetId=cs["id"])["parentObjectId"] is None


@pytest.mark.journey("J15.5")
@pytest.mark.structures(*LADDER)
def test_too_large_a_subtree_is_refused_with_the_limit(world):
    """Given a subtree of more than 500 records a type change would touch. When previewed. Then it is
    refused with the limit and nothing is planned or written; type changes are not offered live."""
    receiver = world.made("L1", "Receiver", values={"L.code": "RC-1"})
    cs = world.change_set()
    version = world.current(cs)["version"]
    operation = {"kind": "move", "objectId": world.ids["large"], "parentObjectId": receiver["id"]}
    error = refused(_restructure(world, cs, operation), 422, "restructuring_too_large")
    assert error["details"]["limit"] == 500
    assert world.current(cs)["version"] == version

    path = f"/objects/{world.key('L1')}/{world.ids['large']}/parent-candidates"
    refused(world.api.get(path, includeTypeChanges=True), 422, "type_changes_need_change_set")
