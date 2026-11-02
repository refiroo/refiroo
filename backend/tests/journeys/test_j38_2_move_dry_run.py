"""J38.2, J38.4, J38.5, J38.7 — Selection and the dry run of a move (USER_JOURNEYS.md, Base 0.11 X2,
D114–D123).

A move takes records of a source workspace through a mapping into a workspace of another model. Its
dry run (``POST /moves``, a job of kind ``move``) reads what is selected, decides what each record
and relationship becomes in the target and checks every item against the target's rules, writing
nothing: one row per record and relationship, ``create``, ``update``, ``refused`` (the target's
rule) or ``notMoved`` (the mapping's reason). Each test runs on one configuration ``X`` in the
default workspace with a workspace on ``Y``, the other generated configuration, beside it, the
mapping proposed and applied as in J38.1: generated A to B, and B to A. Naming no configuration key.
"""

import copy
from uuid import UUID, uuid4, uuid5

import pytest
from scenario import W1, numbered, ok, plan_reads, planned, refused
from test_j36_workspace_models import BOTH, _on, _other
from test_j38_1_model_mapping import _apply, _beside, _create, _infer, _operate, _read, _run

# The namespace of counterpart IDs, as API.md documents it, so a client computes where a record goes.
NAMESPACE = UUID("2218e355-f627-4a22-a009-bebe5423891c")


def _counterpart(workspace, object_id):
    return str(UUID(bytes=uuid5(NAMESPACE, f"{workspace}/{object_id}").bytes, version=4))


def _mapped(world):
    """Y beside X and the mapping between them proposed and applied: Y's world, its workspace and
    the mapping's key."""
    other, _release, target = _beside(world)
    key = _create(world, W1, target)["key"]
    _infer(world, key, W1, target)
    _apply(world, key)
    return other, target, key


def _start(world, key, target, selection=None, source=W1, version=None, **extra):
    body = {
        "sourceWorkspaceKey": source,
        "targetWorkspaceKey": target,
        "mapping": {
            "key": key,
            "expectedVersion": version if version is not None else _read(world, key)["version"],
        },
        "selection": selection or {},
        **extra,
    }
    return world.api.post("/moves", body)


def _dry_run(world, key, target, selection=None, **extra):
    """The move's dry run, run to its end: the job and every row."""
    job = ok(_start(world, key, target, selection, **extra), 202)
    assert job["kind"] == "move"
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "awaiting_confirmation", job
    return job, _rows(world, job["id"])


def _rows(world, job_id, **params):
    rows, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job_id}/rows", pageSize=500, cursor=cursor, **params))
        rows += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return rows


def _records(rows):
    """The record rows by their source record; a parent the mapping names has none."""
    return {row["sourceId"]: row for row in rows if row["kind"] == "record" and "sourceId" in row}


def _relationships(rows, relation=None):
    return [
        row
        for row in rows
        if row["kind"] == "relationship" and relation in (None, row["relationTypeKey"])
    ]


def _codes(row):
    return {reason["code"] for reason in row.get("reasons") or []}


def _left_behind(row):
    return {item["code"] for item in row.get("leftBehind") or []}


def _count(world, structure, workspace):
    page = world.api.get(
        f"/objects/{world.key(structure)}", includeTotal=True, pageSize=1, workspaceKey=workspace
    )
    return ok(page)["totalCount"]


def _head(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/feed"))["headPosition"]


def _every_type(world):
    """Records of every structure in the default workspace, where both models allow them: a D
    under a container and owned by an R, an N needed by an H, a room under an estate."""
    r = world.made("R", f"Ledger {uuid4().hex[:6]}", values={"R.u": f"U-{uuid4().hex[:8]}"})
    r2 = world.made("R2", "Entry", parent=r["id"])
    g = world.made("G", "Region north")
    m = world.made("M", "Zone one", parent=g["id"])
    d = world.made("D", "Permit one", parent=m["id"], relations=[world.owner("Bown", r["id"])])
    n = world.made(
        "N",
        "Notice one",
        relations=[{**world.owner("Breq", world.ids["h1"])}],
    )
    p = world.made("P", "Estate one")
    c = world.made("C", "Room one", parent=p["id"])
    return {"R": r, "R2": r2, "G": g, "M": m, "D": d, "N": n, "P": p, "C": c}


def _types(world):
    return [item["key"] for item in world.configuration.model["objectTypes"]]


def _mapped_type(other, world, source_type):
    structure = next(s for s, value in world.configuration.keys.items() if value == source_type)
    return other.key(structure)


@pytest.mark.journey("J38.2")
@pytest.mark.structures(*BOTH)
def test_the_dry_run_of_a_whole_workspace(world):
    """Given the default workspace with records of every structure and the mapping applied. When a
    move with an empty selection is started. Then it is accepted, and once run its job completes
    with one row per record and relationship of the workspace: every record a create under its
    counterpart ID and its mapped type, as many per type as the workspace holds. The target's
    records, feed and change sets are unchanged."""
    other, target, key = _mapped(world)
    _every_type(world)
    held = {
        key_: ok(world.api.get(f"/objects/{key_}", includeTotal=True, pageSize=1, workspaceKey=W1))[
            "totalCount"
        ]
        for key_ in _types(world)
    }
    head, change_sets = _head(world, target), ok(world.api.get(f"/workspaces/{target}/change-sets"))

    job, rows = _dry_run(world, key, target)

    records = _records(rows)
    assert len(records) == sum(held.values())
    for source_id, row in records.items():
        assert row["outcome"] == "create", row
        assert row["targetId"] == _counterpart(target, source_id)
        assert row["targetType"] == _mapped_type(other, world, row["sourceType"])
    by_type = {}
    for row in records.values():
        by_type[row["sourceType"]] = by_type.get(row["sourceType"], 0) + 1
    assert by_type == {type_: count for type_, count in held.items() if count}
    assert _relationships(rows) and all(r["outcome"] == "create" for r in _relationships(rows))
    summary = job["move"]
    assert summary["coverage"] == "complete"
    assert summary["mapping"] == {"key": key, "version": _read(world, key)["version"]}
    assert {t["sourceType"]: t["counts"]["create"] for t in summary["types"]} == by_type

    for structure in ("R", "H", "K"):
        assert _count(other, structure, target) == 0
    assert _head(world, target) == head
    assert ok(world.api.get(f"/workspaces/{target}/change-sets")) == change_sets


@pytest.mark.journey("J38.2")
@pytest.mark.structures(*BOTH)
def test_what_a_selection_moves(world):
    """Given the mapping applied. When a dry run selects records of a type by a criterion, a subtree,
    records by ID, and the records of a publication. Then each holds exactly those records: the
    subtree its top record and every record under it; the publication's not the record created
    after it. The job keeps the selection and the mapping's version."""
    _other_world, target, key = _mapped(world)
    k = world.key("K")
    ids = world.ids

    job, rows = _dry_run(
        world,
        key,
        target,
        {
            "types": [
                {
                    "objectTypeKey": k,
                    "where": [{"field": world.key("K.code"), "op": "startsWith", "value": "K0"}],
                }
            ]
        },
    )
    assert set(_records(rows)) == {ids[f"k{index:02d}"] for index in range(1, 10)}
    assert job["parameters"]["selection"]["types"][0]["objectTypeKey"] == k
    assert job["parameters"]["mapping"] == {"key": key, "version": _read(world, key)["version"]}

    _job, rows = _dry_run(world, key, target, {"parentObjectId": ids["h3"]})
    assert set(_records(rows)) == {ids["h3"], ids["h4"], ids["h5"], ids["h6"]}

    _job, rows = _dry_run(world, key, target, {"objectIds": [ids["k03"], ids["h2"]]})
    assert set(_records(rows)) == {ids["k03"], ids["h2"]}

    change_set = world.change_set()
    published = world.made("R", "Published ledger", change_set=change_set)
    publication = world.publish(change_set)
    later = world.made("R", "Later ledger")
    r = {"types": [{"objectTypeKey": world.key("R")}]}
    _job, rows = _dry_run(world, key, target, r, sourceAt=publication["id"])
    assert published["id"] in _records(rows) and later["id"] not in _records(rows)
    _job, rows = _dry_run(world, key, target, r)
    assert {published["id"], later["id"]} <= set(_records(rows))


@pytest.mark.journey("J38.7")
@pytest.mark.structures(*BOTH)
def test_what_cannot_move_and_why(world):
    """Given the mapping applied. When a type is unmapped, an attribute is unmapped, and the required
    text attribute is carried into a number instead, which its values do not parse as. Then the
    type's records are not moved with the count and the records under them not moved either; the
    unmapped attribute is listed per attribute with its count while its records still move; the
    value that does not convert is left behind at its pointer; the records lacking the required
    value are refused, and created once the mapping gives a default."""
    other, target, key = _mapped(world)
    records = _every_type(world)
    r_type, g_type = world.key("R"), world.key("G")
    q = world.key("R.q")
    words = world.made("R", "Wordy ledger", values={"R.q": "not a number", "R.n": 5})
    ok(_operate(world, key, {"kind": "unmapType", "sourceType": g_type}))
    ok(
        _operate(
            world,
            key,
            {"kind": "unmapAttribute", "sourceType": r_type, "attribute": world.key("R.n")},
            {
                "kind": "mapAttribute",
                "sourceType": r_type,
                "attribute": q,
                "target": other.key("R.n"),
            },
        )
    )

    job, rows = _dry_run(world, key, target)
    found = _records(rows)
    assert found[records["G"]["id"]]["outcome"] == "notMoved"
    assert _codes(found[records["G"]["id"]]) == {"TYPE_NOT_MAPPED"}
    for structure in ("M", "D"):
        assert found[records[structure]["id"]]["outcome"] == "notMoved"
        assert _codes(found[records[structure]["id"]]) == {"RECORD_NOT_MOVED"}
    reasons = {item["code"]: item["count"] for item in job["move"]["reasons"]}
    assert reasons["TYPE_NOT_MAPPED"] == sum(
        1 for row in found.values() if row["sourceType"] == g_type
    )

    r_rows = [row for row in found.values() if row["sourceType"] == r_type]
    assert r_rows and all(row["outcome"] == "refused" for row in r_rows)
    assert all("MISSING_REQUIRED_ATTRIBUTES" in _codes(row) for row in r_rows)
    unmapped = {
        (item["sourceType"], item["attributeTypeKey"]): item["count"]
        for item in job["move"]["attributesNotCarried"]
    }
    with_n = sum(1 for row in r_rows if "ATTRIBUTE_NOT_MAPPED" in _left_behind(row))
    assert unmapped[(r_type, world.key("R.n"))] == with_n > 0
    [loss] = [
        item for item in found[words["id"]]["leftBehind"] if item["code"] == "VALUE_NOT_CONVERTIBLE"
    ]
    assert loss["pointer"] == f"/attributes/{q}"
    assert loss["value"] == "not a number"

    default = {"kind": "setDefault", "sourceType": r_type, "attribute": other.key("R.q")}
    ok(_operate(world, key, {**default, "value": "Nobody"}))
    _job, rows = _dry_run(world, key, target)
    found = _records(rows)
    assert all(found[row["sourceId"]]["outcome"] == "create" for row in r_rows)
    assert "VALUE_NOT_CONVERTIBLE" in _left_behind(found[words["id"]])


@pytest.mark.journey("J38.4")
@pytest.mark.structures(*BOTH)
def test_a_relationship_whose_other_end_stays_behind(world):
    """Given the mapping applied and a ledger related to a token. When only ledgers are selected.
    Then the relationship is not moved, its other end left behind, while the ledger is created; with
    the token in the target, found by the mapping's match by name, the relationship is carried to
    it. When permits are selected without the ledgers owning them, which the target requires, each
    permit is refused for the missing relationship. A relationship row names its two records."""
    other, target, key = _mapped(world)
    records = _every_type(world)
    r = records["R"]
    ok(world.relate("B1n", r["id"], world.ids["k01"]), 201)
    ledgers = {"types": [{"objectTypeKey": world.key("R")}]}

    _job, rows = _dry_run(world, key, target, ledgers)
    [link] = [row for row in _relationships(rows, world.key("B1n")) if row["fromId"] == r["id"]]
    assert link["outcome"] == "notMoved" and _codes(link) == {"RELATION_TARGET_LEFT_BEHIND"}
    assert _records(rows)[r["id"]]["outcome"] == "create"
    # A relationship row names both its records (0.11 X4), so the report can say which.
    k01 = ok(world.read("K", world.ids["k01"]))
    assert (link["fromName"], link["toName"]) == (r["name"], k01["name"])

    token = other.made("K", "Token 01", workspace=target)
    ok(
        _operate(
            world,
            key,
            {"kind": "setMatch", "sourceType": world.key("K"), "match": {"field": "name"}},
        )
    )
    _job, rows = _dry_run(world, key, target, ledgers)
    [link] = [row for row in _relationships(rows, world.key("B1n")) if row["fromId"] == r["id"]]
    assert link["outcome"] == "create", link
    assert link["targetToId"] == token["id"]
    assert link["targetFromId"] == _counterpart(target, r["id"])

    placed = {"types": [{"objectTypeKey": world.key(s)} for s in ("G", "M", "D")]}
    _job, rows = _dry_run(world, key, target, placed)
    permit = _records(rows)[records["D"]["id"]]
    assert permit["outcome"] == "refused" and "MISSING_REQUIRED_RELATIONS" in _codes(permit)
    [owner] = _relationships(rows, world.key("Bown"))
    assert owner["outcome"] == "notMoved" and _codes(owner) == {"RELATION_TARGET_LEFT_BEHIND"}


@pytest.mark.journey("J38.4")
@pytest.mark.structures(*BOTH)
def test_the_jobs_page_reads_what_the_move_did_from_the_job(world):
    """Given a dry run of permits and their owners' relationship, a permit refused and the
    relationship not moved. When the job is read. Then its ``move`` summary counts the relationship
    type with its not-moved row beside the record types' counts, and the rows filtered by outcome
    return the refused permits and the relationship (0.16: the job page's one call and its filters)."""
    _other, target, key = _mapped(world)
    _every_type(world)
    placed = {"types": [{"objectTypeKey": world.key(s)} for s in ("G", "M", "D")]}
    job, _rows_all = _dry_run(world, key, target, placed)

    summary = ok(world.api.get(f"/jobs/{job['id']}"))["move"]
    [owned] = [
        item for item in summary["relationships"] if item["relationTypeKey"] == world.key("Bown")
    ]
    assert owned["counts"]["notMoved"] >= 1
    assert (
        sum(item["counts"]["refused"] for item in summary["types"]) == summary["counts"]["refused"]
    )
    assert summary["counts"]["refused"] >= 1

    refused_rows = _rows(world, job["id"], outcome="refused")
    assert refused_rows and all(row["outcome"] == "refused" for row in refused_rows)
    unmoved = _rows(world, job["id"], outcome="notMoved")
    assert any(
        row["kind"] == "relationship" and row["relationTypeKey"] == world.key("Bown")
        for row in unmoved
    )
    assert len(refused_rows) == summary["counts"]["refused"]


@pytest.mark.journey("J38.5")
@pytest.mark.structures(*BOTH)
def test_a_unique_value_already_held_in_the_target(world):
    """Given the mapping applied, a ledger whose unique value a ledger in the target holds, and a
    ledger whose name only a target ledger shares. When both are selected. Then the first is refused
    naming the holder, the second created and listed with its possible duplicate. Once the mapping
    matches ledgers by the unique attribute, the first updates the holder."""
    other, target, key = _mapped(world)
    value = f"U-{uuid4().hex[:8]}"
    held = world.made("R", "Held ledger", values={"R.u": value})
    holder = other.made("R", "Holder", workspace=target, values={"R.u": value})
    twin = world.made("R", "Twin ledger", values={"R.u": f"U-{uuid4().hex[:8]}"})
    namesake = other.made(
        "R", "Twin ledger", workspace=target, values={"R.u": f"V-{uuid4().hex[:8]}"}
    )
    chosen = {"objectIds": [held["id"], twin["id"]]}

    _job, rows = _dry_run(world, key, target, chosen)
    found = _records(rows)
    refusal = found[held["id"]]
    assert refusal["outcome"] == "refused"
    [reason] = [r for r in refusal["reasons"] if r["code"] == "DUPLICATE_ATTRIBUTE_VALUE"]
    assert reason["details"]["conflictingObjectId"] == holder["id"]
    assert found[twin["id"]]["outcome"] == "create"
    assert found[twin["id"]]["possibleDuplicates"] == [namesake["id"]]

    match = {"attributeTypeKey": other.key("R.u")}
    ok(_operate(world, key, {"kind": "setMatch", "sourceType": world.key("R"), "match": match}))
    _job, rows = _dry_run(world, key, target, chosen)
    found = _records(rows)
    assert found[held["id"]]["outcome"] == "update", found[held["id"]]
    assert found[held["id"]]["targetId"] == holder["id"]
    assert found[held["id"]]["matchedBy"] == match
    assert found[twin["id"]]["outcome"] == "create"


@pytest.mark.journey("J38.5")
@pytest.mark.structures(*BOTH, "R.n")
def test_a_record_matched_by_a_unique_number(world):
    """Given two workspaces whose models make R.n (a number) unique, the mapping applied and
    matching R by R.n, a source R whose number a target R holds and one whose number none holds.
    When both are moved in a dry run. Then the first updates the holder, matched by the number, and
    the second is created. The match seeks the target's unique values by their index and reads no
    attribute value (0.11 Q2, D188)."""
    other = _other(world)
    source = _on(world, world.install(numbered(world.configuration), name="Numbered")["id"])
    target = _on(world, world.install(numbered(other.configuration), name="Other numbered")["id"])
    key = _create(world, source, target)["key"]
    _infer(world, key, source, target)
    _apply(world, key)
    match = {"attributeTypeKey": other.key("R.n")}
    ok(_operate(world, key, {"kind": "setMatch", "sourceType": world.key("R"), "match": match}))
    held = world.made("R", "Held", workspace=source, values={"R.n": 7})
    holder = other.made("R", "Holder", workspace=target, values={"R.n": 7})
    fresh = world.made("R", "Fresh", workspace=source, values={"R.n": 8})

    with planned(lambda statement: "WITH candidates AS" in statement) as plans:
        _job, rows = _dry_run(
            world, key, target, {"objectIds": [held["id"], fresh["id"]]}, source=source
        )
    found = _records(rows)
    assert found[held["id"]]["outcome"] == "update", found[held["id"]]
    assert found[held["id"]]["targetId"] == holder["id"]
    assert found[held["id"]]["matchedBy"] == match
    assert found[fresh["id"]]["outcome"] == "create"
    [plan] = plans
    assert "attribute_values" not in plan_reads(plan), plan
    assert "uq_unique_attribute_values" in plan_reads(plan), plan


@pytest.mark.journey("J38.2")
@pytest.mark.structures(*BOTH)
def test_where_a_record_stands_in_the_target(world):
    """Given the mapping applied. When a permit moves with its region, container and owner, it stands
    under its container's counterpart. When it moves without its container, which the target does
    not hold, it is not moved for want of its parent. When rooms are placed under one estate named by
    the mapping that the target lacks, with missing records created, the estate is created first and
    the rooms stand under it."""
    other, target, key = _mapped(world)
    records = _every_type(world)
    d, m = records["D"], records["M"]

    everything = {"types": [{"objectTypeKey": world.key(s)} for s in ("R", "G", "M", "D")]}
    _job, rows = _dry_run(world, key, target, everything)
    permit = _records(rows)[d["id"]]
    assert permit["outcome"] == "create", permit
    assert permit["targetParentId"] == _counterpart(target, m["id"])

    alone = {"types": [{"objectTypeKey": world.key(s)} for s in ("R", "D")]}
    _job, rows = _dry_run(world, key, target, alone)
    permit = _records(rows)[d["id"]]
    assert permit["outcome"] == "notMoved" and _codes(permit) == {"PARENT_NOT_FOUND"}

    fixed = {"objectTypeKey": other.key("P"), "value": "Holding estate", "missing": "create"}
    ok(_operate(world, key, {"kind": "setParent", "sourceType": world.key("C"), "parent": fixed}))
    rooms = {"types": [{"objectTypeKey": world.key("C")}]}
    _job, rows = _dry_run(world, key, target, rooms)
    created = [row for row in rows if row["kind"] == "record" and not row["selected"]]
    [estate] = created
    assert estate["outcome"] == "create" and estate["name"] == "Holding estate"
    assert estate["targetType"] == other.key("P")
    room = _records(rows)[records["C"]["id"]]
    assert room["outcome"] == "create", room
    assert room["targetParentId"] == estate["targetId"]
    assert rows.index(estate) < rows.index(room)


@pytest.mark.journey("J38")
@pytest.mark.structures(*BOTH)
def test_a_move_refused_before_it_starts(world):
    """Given the mapping applied. When a move names one workspace on both sides, a mapping of other
    models, an unknown mapping, a stale mapping version, a retired target, a target whose release
    lacks an attribute the mapping names, or an unknown type in its selection. Then each is refused
    with its code and no job is created."""
    other, target, key = _mapped(world)
    y = ok(world.api.get(f"/workspaces/{target}/model"))
    before = ok(world.api.get("/jobs", kind="move", includeTotal=True, pageSize=1))["totalCount"]

    refused(_start(world, key, W1), 422, "MOVE_SAME_WORKSPACE")
    back = _create(world, target, W1)["key"]
    mismatch = refused(_start(world, back, target), 422, "MODEL_MAPPING_MODEL_MISMATCH")
    assert {"sourceModelKey", "targetModelKey"} <= set(mismatch["details"])
    refused(
        _start(world, f"none-{uuid4().hex[:6]}", target, version=1), 404, "MODEL_MAPPING_NOT_FOUND"
    )
    stale = refused(_start(world, key, target, version=1), 409, "MOVE_MAPPING_CHANGED")
    assert stale["details"]["currentVersion"] == _read(world, key)["version"]

    retired = _on(world, y["releaseId"])
    version = ok(world.api.get(f"/workspaces/{retired}"))["version"]
    ok(world.api.patch(f"/workspaces/{retired}", {"expectedVersion": version, "status": "retired"}))
    refused(_start(world, key, retired), 409, "WORKSPACE_RETIRED")

    unknown = {"types": [{"objectTypeKey": f"none-{uuid4().hex[:6]}"}]}
    invalid = refused(_start(world, key, target, unknown), 422, "INVALID_QUERY")
    assert invalid["details"]["path"] == "/selection/types/0/objectTypeKey"

    gone = other.key("L.only1")
    smaller = copy.deepcopy(other.configuration.model)
    smaller["release"]["version"] += "-smaller"
    smaller["attributeTypes"] = [item for item in smaller["attributeTypes"] if item["key"] != gone]
    for item in smaller["objectTypes"]:
        item["attributes"] = [b for b in item["attributes"] if b["attributeTypeKey"] != gone]
    release = world.install(smaller, name="Smaller")
    ok(world.activate(release["id"], target))
    problems = refused(_start(world, key, target), 422, "MOVE_MAPPING_HAS_PROBLEMS")
    assert {p["code"] for p in problems["details"]["problems"]} == {"ELEMENT_NOT_IN_RELEASE"}
    assert all(p["pointer"].startswith("/types/") for p in problems["details"]["problems"])

    after = ok(world.api.get("/jobs", kind="move", includeTotal=True, pageSize=1))["totalCount"]
    assert after == before
