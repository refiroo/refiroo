"""J10 — Review and replace a record's related records (USER_JOURNEYS.md).

UI-only parts: keeping the attempted choice for review after a conflict (J10.4, runner
``sc07-mapping-acceptance``) and cancelling the in-place create form (J10.8, ``wp13c-ui-states``).
"""

from uuid import uuid4

import pytest
from scenario import W1, ok, refused


def _view(world, structure):
    key = world.key(structure)
    for application in world.configuration.model["applications"]:
        for view in application["views"]:
            if view["key"] == key:
                return application["key"], view["config"]
    raise KeyError(structure)


def _binding(world, structure):
    _application, config = _view(world, structure)
    return {
        name: config[name]
        for name in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey", "direction")
    }


def _view_identity(world, structure):
    """The view a candidate search runs for (API.md: the view and context identity)."""
    application, _config = _view(world, structure)
    return {"applicationKey": application, "viewKey": world.key(structure)}


def _identity(world, structure):
    application, _config = _view(world, structure)
    return {
        "applicationKey": application,
        "viewKey": world.key(structure),
        **_binding(world, structure),
    }


def _coverage(world, structure, **params):
    return ok(
        world.api.get(f"/workspaces/{W1}/mapping-coverage", **_identity(world, structure), **params)
    )


def _row(world, structure, source, **params):
    rows = _coverage(world, structure, search=source["name"], **params)["items"]
    return next(row for row in rows if row["source"]["id"] == source["id"])


def _replace(world, binding, source, target, version, **extra):
    """``PUT /mappings`` for ``binding`` (the binding fields), replacing ``source``'s set."""
    body = {
        **binding,
        "sourceObjectId": source,
        "targetObjectId": target,
        "expectedMappingVersion": version,
        **extra,
    }
    return world.api.put(f"/workspaces/{W1}/mappings", body)


def _targets(row):
    return {target["object"]["id"] for target in row["targets"]}


@pytest.mark.journey("J10")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_filter_coverage_find_a_candidate_beyond_page_one_and_replace_the_set(world):
    """Given a relationship view with sources in every state. When the steward lists the sources
    without related records, searches candidates past the first page and replaces one source's set.
    Then the list holds only those sources and its total counts them all; the candidate is reached by
    cursor; the save maps the source at its next version, coverage and the edge list show exactly
    that record; replacing one record by another records one transition and leaves other sources'
    sets alone."""
    mapped = world.made("H", "Mapped source")
    ok(world.relate("Bnn", mapped["id"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    source = world.made("H", "Unmapped source")

    every, cursor = [], None
    while True:
        page = _coverage(world, "Vnn", pageSize=100, cursor=cursor)
        every += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    unmapped = _coverage(world, "Vnn", state="unmapped", includeTotal=True, pageSize=3)
    assert {row["state"] for row in unmapped["items"]} == {"unmapped"}
    assert unmapped["totalCount"] == sum(row["state"] == "unmapped" for row in every)
    assert {row["state"] for row in every} == {"unmapped", "mapped", "ambiguous"}

    wanted, pages, cursor = world.ids["k12"], 0, None
    while True:
        page = ok(
            world.api.get(
                f"/workspaces/{W1}/mapping-candidates",
                **_view_identity(world, "Vnn"),
                objectTypeKey=world.key("K"),
                search="Token",
                pageSize=5,
                cursor=cursor,
            )
        )
        pages += 1
        if wanted in {item["id"] for item in page["items"]}:
            break
        cursor = page["nextCursor"]
    assert pages > 1

    before = _row(world, "Vnn", source)
    saved = ok(
        _replace(world, _binding(world, "Vnn"), source["id"], wanted, before["mappingVersion"])
    )
    assert saved["state"] == "mapped" and saved["mappingVersion"] == before["mappingVersion"] + 1
    assert _targets(_row(world, "Vnn", source)) == {wanted}
    edges = ok(
        world.api.get(
            f"/workspaces/{W1}/relations",
            relationTypeKey=world.key("Bnn"),
            direction="outgoing",
            search="Unmapped source",
        )
    )["items"]
    assert [(e["source"]["id"], e["target"]["id"]) for e in edges] == [(source["id"], wanted)]

    history = f"/objects/{world.key('H')}/{source['id']}/history"
    transitions = sum(e["action"] == "transition" for e in ok(world.api.get(history))["items"])
    other = _row(world, "Vnn", mapped)
    ok(
        _replace(
            world, _binding(world, "Vnn"), source["id"], world.ids["k13"], saved["mappingVersion"]
        )
    )
    after = ok(world.api.get(history))["items"]
    assert sum(e["action"] == "transition" for e in after) == transitions + 1
    assert _targets(_row(world, "Vnn", source)) == {world.ids["k13"]}
    assert _row(world, "Vnn", mapped)["mappingVersion"] == other["mappingVersion"]


@pytest.mark.journey("J10.1")
@pytest.mark.structures("H", "K", "Bnn", "Vnn", "Vnnr")
def test_replace_from_either_end(world):
    """Given a view of the same relationship read from its other end. When a K record's set is
    replaced from the K side. Then the K row shows the H record, the H record's view shows the K
    record, and each end's version advanced once."""
    k = world.made("K", "Other end")
    h = world.made("H", "This end")
    k_before = _row(world, "Vnnr", k)["mappingVersion"]
    h_before = _row(world, "Vnn", h)["mappingVersion"]

    ok(_replace(world, _binding(world, "Vnnr"), k["id"], h["id"], k_before))
    assert _targets(_row(world, "Vnnr", k)) == {h["id"]}
    assert _targets(_row(world, "Vnn", h)) == {k["id"]}
    assert _row(world, "Vnnr", k)["mappingVersion"] == k_before + 1
    assert _row(world, "Vnn", h)["mappingVersion"] == h_before + 1


@pytest.mark.journey("J10.2")
@pytest.mark.structures("H", "K", "Bnn", "Bh1n", "Bh1n.qty", "Vnn", "V2")
def test_an_independent_relationship_with_its_own_names_and_values(world):
    """Given two views over different relationships from the same H record. When its set in the
    second is replaced with a typed value. Then the second view shows the K record of the other
    application with the value; the first view's set and version are unchanged; each relationship
    type has its own names."""
    h = world.made("H", "Two views")
    ok(world.relate("Bnn", h["id"], world.ids["k02"], {"Bnn.weight": 1}), 201)
    first = _row(world, "Vnn", h)
    second = _row(world, "V2", h)

    ok(
        _replace(
            world,
            _binding(world, "V2"),
            h["id"],
            world.ids["k03"],
            second["mappingVersion"],
            attributes={world.key("Bh1n.qty"): 3},
        )
    )
    row = _row(world, "V2", h)
    (target,) = row["targets"]
    assert target["object"]["id"] == world.ids["k03"]
    assert target["attributes"][world.key("Bh1n.qty")] == 3
    assert world.record("K", world.ids["k03"])["applicationKey"] == world.app("K") != world.app("H")
    assert _row(world, "Vnn", h) == first
    names = {key: ok(world.api.get(f"/relation-types/{world.key(key)}")) for key in ("Bnn", "Bh1n")}
    assert (names["Bnn"]["name"], names["Bnn"]["reverseName"]) != (
        names["Bh1n"]["name"],
        names["Bh1n"]["reverseName"],
    )


@pytest.mark.journey("J10.3")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_a_large_set_is_previewed_and_continued(world):
    """Given an H record with 25 related records. When its ambiguous row is read, then continued.
    Then the row counts 25 and shows 20 with a continuation that returns the other 5; a stale version
    is refused with the current one, and a continuation from an older version is refused."""
    h = world.made("H", "Many links")
    for index in range(1, 26):
        ok(world.relate("Bnn", h["id"], world.ids[f"k{index:02d}"], {"Bnn.weight": 1}), 201)
    row = _row(world, "Vnn", h, state="ambiguous")
    assert row["targetCount"] == 25 and len(row["targets"]) == 20 and row["targetsNextCursor"]

    params = {**_identity(world, "Vnn"), "sourceObjectId": h["id"]}
    rest = ok(
        world.api.get(
            f"/workspaces/{W1}/mapping-targets",
            **params,
            mappingVersion=row["mappingVersion"],
            cursor=row["targetsNextCursor"],
        )
    )
    seen = _targets(row) | {item["object"]["id"] for item in rest["items"]}
    assert len(rest["items"]) == 5 and len(seen) == 25

    error = refused(
        world.api.get(
            f"/workspaces/{W1}/mapping-targets", **params, mappingVersion=row["mappingVersion"] + 7
        ),
        409,
        "mapping_version_conflict",
    )
    assert error["details"]["mappingVersion"] == row["mappingVersion"]
    ok(world.relate("Bnn", h["id"], world.ids["k26"], {"Bnn.weight": 1}), 201)
    old_cursor = world.api.get(
        f"/workspaces/{W1}/mapping-targets",
        **params,
        mappingVersion=row["mappingVersion"] + 1,
        cursor=row["targetsNextCursor"],
    )
    refused(old_cursor, 422, "invalid_cursor")


@pytest.mark.journey("J10.4")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_someone_changed_the_set_first(world):
    """Given clients A and B who read an H record's set at version m. When A replaces it with t1, then
    B with t2 claiming m. Then B is refused with the current version, count and records naming t1,
    and the set holds only t1."""
    h = world.made("H", "Contested set")
    m = _row(world, "Vnn", h)["mappingVersion"]
    t1, t2 = world.ids["k07"], world.ids["k08"]
    ok(_replace(world, _binding(world, "Vnn"), h["id"], t1, m))

    error = refused(
        _replace(world, _binding(world, "Vnn"), h["id"], t2, m), 409, "mapping_version_conflict"
    )
    assert error["details"]["mappingVersion"] == m + 1 and error["details"]["targetCount"] == 1
    assert [t["object"]["id"] for t in error["details"]["targets"]] == [t1]
    assert _targets(_row(world, "Vnn", h)) == {t1}


@pytest.mark.journey("J10.5")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_a_single_relationship_write_racing_a_set_replacement(world):
    """Given H record s holding one related record at version m. When actor A replaces the set and
    actor B adds a relationship from s, both claiming m and both in flight at once. Then one succeeds
    and the other is refused with its set's conflict, and s's set is the winner's."""
    s = world.made("H", "Raced set")
    t0, ta, tb = world.ids["k09"], world.ids["k10"], world.ids["k11"]
    ok(world.relate("Bnn", s["id"], t0, {"Bnn.weight": 1}), 201)
    m = _row(world, "Vnn", s)["mappingVersion"]

    responses = world.race(
        W1,
        lambda: _replace(world, _binding(world, "Vnn"), s["id"], ta, m),
        lambda: world.relate(
            "Bnn",
            s["id"],
            tb,
            {"Bnn.weight": 1},
            expectedRelationSetVersion=m,
            relationSetDirection="outgoing",
        ),
    )
    replaced, added = responses
    assert sorted(r.status_code for r in responses) in ([200, 409], [201, 409])
    if replaced.status_code == 200:
        refused(added, 409, "relation_set_version_conflict")
        assert _targets(_row(world, "Vnn", s)) == {ta}
    else:
        refused(replaced, 409, "mapping_version_conflict")
        assert _targets(_row(world, "Vnn", s)) == {t0, tb}


@pytest.mark.journey("J10.6")
@pytest.mark.structures("H", "K", "Bnn", "Vnn", "R")
def test_live_changing_a_staged_set_refuses_the_publication(world):
    """Given a change set from current live in which H record s's set was replaced. When live replaces
    the same set, then the change set is published. Then publishing is refused with a changed-set
    conflict naming s and the counts; no publication is created, the change set stays, live keeps its
    replacement and an unrelated live edit made meanwhile is untouched."""
    s = world.made("H", "Staged set")
    ok(world.relate("Bnn", s["id"], world.ids["k14"], {"Bnn.weight": 1}), 201)
    cs = world.change_set()
    staged_version = _row(world, "Vnn", s, changeSetId=cs["id"])["mappingVersion"]
    ok(
        _replace(
            world,
            _binding(world, "Vnn"),
            s["id"],
            world.ids["k15"],
            staged_version,
            changeSetId=cs["id"],
            expectedChangeSetVersion=world.current(cs)["version"],
        )
    )
    live_version = _row(world, "Vnn", s)["mappingVersion"]
    ok(_replace(world, _binding(world, "Vnn"), s["id"], world.ids["k16"], live_version))
    unrelated = world.made("R", "Unrelated live edit")
    publications = ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]

    body = {
        "expectedChangeSetVersion": world.current(cs)["version"],
        "expectedActivePublicationId": None,
    }
    error = refused(
        world.api.post(f"/change-sets/{cs['id']}/publication", body), 409, "version_conflict"
    )
    (conflict,) = [
        c
        for c in error["details"]["conflicts"]
        if c["code"] == "mapping_set_changed" and c["anchorObjectId"] == s["id"]
    ]
    assert {"expectedTargetCount", "actualTargetCount"} <= set(conflict)
    assert ok(world.api.get(f"/workspaces/{W1}/publications"))["items"] == publications
    assert world.current(cs)["id"] == cs["id"]
    assert _targets(_row(world, "Vnn", s)) == {world.ids["k16"]}
    assert world.record("R", unrelated["id"])["version"] == unrelated["version"]


@pytest.mark.journey("J10.7")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_a_publication_is_read_only(world):
    """Given P1 holding H record s with t1, and live later replacing it with t2. When coverage and the
    edge list are read in P1. Then s shows t1 at version 0 there and t2 live; a replacement naming
    P1 is refused and nothing changes."""
    s = world.made("H", "Published set")
    t1, t2 = world.ids["k17"], world.ids["k18"]
    ok(world.relate("Bnn", s["id"], t1, {"Bnn.weight": 1}), 201)
    p1 = world.publish(world.change_set())
    live = _row(world, "Vnn", s)
    ok(_replace(world, _binding(world, "Vnn"), s["id"], t2, live["mappingVersion"]))

    published = _row(world, "Vnn", s, publicationId=p1["id"])
    assert _targets(published) == {t1} and published["mappingVersion"] == 0
    edges = ok(
        world.api.get(
            f"/workspaces/{W1}/relations",
            publicationId=p1["id"],
            relationTypeKey=world.key("Bnn"),
            direction="outgoing",
            search="Published set",
        )
    )["items"]
    assert [e["target"]["id"] for e in edges] == [t1]
    assert _targets(_row(world, "Vnn", s)) == {t2}

    current = _row(world, "Vnn", s)
    refused(
        _replace(
            world,
            _binding(world, "Vnn"),
            s["id"],
            t1,
            current["mappingVersion"],
            publicationId=p1["id"],
        ),
        422,
        "request_validation_error",
    )
    assert _row(world, "Vnn", s) == current


@pytest.mark.journey("J10.8")
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_create_a_missing_related_record_in_place(world):
    """Given an H record without related records and no suitable K record. When a K record is
    created, coverage re-read and the set replaced with it. Then creating the record leaves the
    source's state and version unchanged, and the save maps the source to it."""
    s = world.made("H", "Waiting source")
    before = _row(world, "Vnn", s)
    created = world.made("K", "Created in place")
    after = _row(world, "Vnn", s)
    assert (after["state"], after["mappingVersion"]) == (before["state"], before["mappingVersion"])
    ok(_replace(world, _binding(world, "Vnn"), s["id"], created["id"], after["mappingVersion"]))
    assert _targets(_row(world, "Vnn", s)) == {created["id"]}


@pytest.mark.journey("J10.9")
@pytest.mark.structures("H", "K", "Bnn", "Vnn", "R", "D", "Bown", "N", "Breq", "Bsk", "P", "Q", "C")
def test_a_required_or_owning_relationship_cannot_be_replaced_or_cleared(world):
    """When the set of an owning relationship is replaced; of a containment; a required relationship
    is cleared; a set is cleared with values; and a scoped relationship is given a record without its
    scope ancestor. Then each is refused with its code, and no set version changes."""
    h = world.made("H", "Guarded source")
    world.made(
        "N",
        "Needed notice",
        relations=[
            {
                "relationTypeKey": world.key("Breq"),
                "direction": "incoming",
                "otherObjectId": h["id"],
            }
        ],
    )
    room = world.made("C", "Room without estate", parent=world.made("Q", "Venue")["id"])
    before = _row(world, "Vnn", h)

    def binding(relation, source, target):
        return {
            "relationTypeKey": world.key(relation),
            "fromObjectTypeKey": world.key(source),
            "toObjectTypeKey": world.key(target),
            "direction": "outgoing",
        }

    refused(
        _replace(world, binding("Bown", "R", "D"), str(uuid4()), None, 0),
        422,
        "required_ownership_binding",
    )
    refused(
        _replace(world, binding("Hparent", "H", "H"), h["id"], world.ids["h1"], 0),
        422,
        "immutable_relation",
    )
    refused(_replace(world, binding("Breq", "H", "N"), h["id"], None, 1), 422, "required_relation")
    refused(
        _replace(
            world,
            _binding(world, "Vnn"),
            h["id"],
            None,
            before["mappingVersion"],
            attributes={world.key("Bnn.weight"): 1},
        ),
        422,
        "invalid_clear_attributes",
    )
    refused(
        _replace(world, binding("Bsk", "H", "C"), h["id"], room["id"], 0),
        422,
        "relation_ancestor_required",
    )
    assert _row(world, "Vnn", h)["mappingVersion"] == before["mappingVersion"]
