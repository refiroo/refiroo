"""J33.19 — A change that needs a migration, made in the editor (USER_JOURNEYS.md, 0.13 MG).

The editor applies a step that changes what stored data holds, marks it as needing a migration with
its impact, and the draft states the migration it implies at ``GET /model-drafts/{id}/migration``.
Installing the draft and starting the workspace migration with that proposal previews and runs it
with no mapping typed by hand. The tests name structures of the configuration (``R``, ``R2``, ``P``,
``Q``, ``H``, ``K``) and the elements they create themselves under ``j33m-`` keys.
"""

from typing import Any

import pytest
from scenario import ok, refused
from test_j33_operations import _apply, _draft, _draft_of_active, _history, _undo
from test_j37_workspace_migration import _confirm, _previewed, _read, _rows, _run

WORKSPACE = "default"


def _active(world) -> dict[str, Any]:
    release = ok(
        world.api.get(f"/model-releases/{world.workspace_model()['releaseId']}", includeModel=True)
    )
    return release["model"]


def _next_version(world, tag: str) -> dict[str, Any]:
    release = _active(world)["release"]
    return {
        "kind": "setRelease",
        "key": release["key"],
        "name": release["name"],
        "version": f"{release['version']}-{tag}",
    }


def _migration(world, draft: dict[str, Any], **params: Any) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/migration", **params))


def _proposal(migration: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """The workspace migration's request fields a draft's migration states."""
    return {
        "typeMappings": migration["typeMappings"],
        "relationTypeMappings": migration["relationTypeMappings"],
        "splits": migration["splits"],
        "listConversions": migration["listConversions"],
        "draftId": draft["id"],
    }


def _installed(world, draft: dict[str, Any], tag: str) -> dict[str, Any]:
    """The draft with a new release identity, installed; the release."""
    current = _draft(world, draft)
    stepped = ok(_apply(world, draft, current["version"], _next_version(world, tag)))
    assert stepped["valid"] is True, stepped["diagnostics"]
    return ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": stepped["version"]}
        ),
        201,
    )


def _migrate(
    world, draft: dict[str, Any], release: dict[str, Any], accept_loss: bool = False
) -> dict[str, Any]:
    """The draft's proposal previewed against the default workspace and confirmed: the completed job."""
    migration = _migration(world, draft)
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(migration, draft))
    assert job["state"] == "awaiting_confirmation", job
    assert job["migration"]["counts"]["refused"] == 0, _rows(world, job["id"], status="refused")
    ok(_confirm(world, job, **({"acceptLoss": True} if accept_loss else {})), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed", done
    return done


def _related(world, record: dict[str, Any], relation_key: str) -> list[str]:
    """The records ``record`` is related to by ``relation_key``, as their IDs."""
    found = ok(
        world.api.get("/relations", objectId=record["id"], workspaceKey=WORKSPACE, pageSize=100)
    )["items"]
    return sorted(
        item["relation"]["toObjectId"]
        for item in found
        if item["relation"]["relationTypeKey"] == relation_key
        and item["relation"]["fromObjectId"] == record["id"]
    )


def _other_application(world, structure: str) -> str:
    return next(
        a["key"] for a in _active(world)["applications"] if a["key"] != world.app(structure)
    )


@pytest.mark.journey("J33.19")
@pytest.mark.structures("P", "C", "H.code", "A1", "A2")
def test_a_type_under_a_parent_moves_with_its_records_to_another_applications_top_level(world):
    """Given C records under a P record. When the editor moves C to the top level of the other
    application, the step applies and is marked as needing a migration with C's records counted;
    the draft states the migration (C goes to that application, to the top level), and an undo
    takes the mark away. Installed and previewed with that proposal, the records are reclassified,
    none refused. Confirmed, they are the same records in the other application with no parent, and
    the P record is as it was."""
    other = _other_application(world, "C")
    parent = world.made("P", "Parent", values={"H.code": "MG-P1"})
    children = [
        world.made("C", name, parent=parent["id"], values={"H.code": f"MG-C{index}"})
        for index, name in enumerate(("Child one", "Child two"))
    ]
    draft = _draft_of_active(world, "Move C")
    move = {
        "kind": "setContainment",
        "objectType": world.key("C"),
        "parent": None,
        "application": other,
    }

    answer = ok(_apply(world, draft, draft["version"], move))
    assert answer["valid"] is True, answer["diagnostics"]
    entry = _history(world, draft)["items"][0]
    marked = {
        tuple(item["element"].items()): item["impact"]["records"] for item in entry["migration"]
    }
    assert marked == {(("objectType", world.key("C")),): 2}

    migration = _migration(world, draft)
    assert migration["required"] is True and migration["baseReleaseId"] == draft["baseReleaseId"]
    rows = {row["fromObjectTypeKey"]: row for row in migration["rows"]}
    assert rows[world.key("C")]["parent"] == "topLevel"
    assert rows[world.key("C")]["toApplicationKey"] == other
    assert rows[world.key("C")]["records"]["records"] == 2
    # The type under it moves with it, below it as it was.
    assert (
        rows[world.key("C2")]["parent"] == "unchanged"
        and rows[world.key("C2")]["toApplicationKey"] == other
    )
    assert {
        item["fromObjectTypeKey"]: item.get("toApplicationKey")
        for item in migration["typeMappings"]
    } == {
        world.key("C"): other,
        world.key("C2"): other,
    }

    landing = _migration(world, draft, workspaceKey=WORKSPACE)["landing"]
    assert landing["moved"] == 2 and landing["refused"] == [] and landing["createdRecords"] == 0

    undone = ok(_undo(world, draft, answer["version"]))
    assert _migration(world, draft)["required"] is False
    ok(_apply(world, draft, undone["version"], move))

    stated = _migration(world, draft)
    release = _installed(world, draft, "moved")
    refused(world.activate(release["id"]), 409, "MODEL_MIGRATION_REQUIRED")
    # Installing bases the draft on the release it installed, so the migration read now names where it
    # starts and where it goes; the page reads it so when it opens.
    assert _migration(world, draft)["typeMappings"] == []
    again = _migration(
        world,
        draft,
        againstReleaseId=draft["baseReleaseId"],
        toReleaseId=release["id"],
        workspaceKey=WORKSPACE,
    )
    assert again["typeMappings"] == stated["typeMappings"] and again["rows"] == stated["rows"]
    assert again["required"] is True and again["landing"]["moved"] == 2
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(again, draft))
    assert job["migration"]["counts"] == {
        "conversion": 0,
        "reclassified": 2,
        "loss": 0,
        "refused": 0,
    }
    assert job["parameters"]["draftId"] == draft["id"]
    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    assert world.workspace_model()["releaseId"] == release["id"]
    for child in children:
        moved = _read(world, WORKSPACE, child)
        assert moved["id"] == child["id"]
        assert moved["applicationKey"] == other
        assert moved.get("parentObjectId") is None
    assert _read(world, WORKSPACE, parent)["name"] == "Parent"


@pytest.mark.journey("J33.19")
@pytest.mark.structures("P", "Q", "C", "H.code")
def test_a_key_change_and_a_merge_install_with_no_mapping_typed_by_hand(world):
    """Given P and Q records, a C record under a Q record. When the editor renames the attribute H.code,
    renames the type C and merges Q into P, each step applies; the draft names C's new key and the
    attribute as the migration's mappings, each key change with the consumer APIs naming the old key,
    and the merge's from and into. Installed and run, every record is under its new type, the Q
    records are P records, and the renamed attribute holds the values it held: nothing is lost."""
    p_record = world.made("P", "Estate", values={"H.code": "MG-CODE-P"})
    q_record = world.made("Q", "Venue", values={"H.code": "MG-CODE-Q"})
    c_record = world.made("C", "Room", parent=q_record["id"], values={"H.code": "MG-CODE-C"})
    draft = _draft_of_active(world, "Rename and merge")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "setKey",
                "element": {"attributeType": world.key("H.code")},
                "key": "j33m-code",
            },
            {"kind": "setKey", "element": {"objectType": world.key("C")}, "key": "j33m-room"},
            {"kind": "mergeObjectTypes", "into": world.key("P"), "from": world.key("Q")},
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    entry = _history(world, draft)["items"]
    assert [bool(item["migration"]) for item in entry] == [True, True, True]
    assert entry[0]["migration"][0]["keyChange"] is True

    migration = _migration(world, draft)
    mappings = {item["fromObjectTypeKey"]: item for item in migration["typeMappings"]}
    assert mappings[world.key("C")]["toObjectTypeKey"] == "j33m-room"
    assert mappings[world.key("Q")]["toObjectTypeKey"] == world.key("P")
    assert {"attributeTypeKey": "j33m-code", "from": world.key("H.code")} in mappings[
        world.key("P")
    ]["attributes"]
    changed = {change["from"]: change for change in migration["keyChanges"]}
    assert changed[world.key("H.code")]["to"] == "j33m-code"
    assert changed[world.key("H.code")]["element"] == {"attributeType": world.key("H.code")}
    assert changed[world.key("C")]["consumerApis"] == []

    release = _installed(world, draft, "renamed")
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(migration, draft))
    assert job["migration"]["counts"]["loss"] == 0 and job["migration"]["counts"]["refused"] == 0
    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    moved = ok(world.api.get(f"/objects/j33m-room/{c_record['id']}", workspaceKey=WORKSPACE))
    assert moved["parentObjectId"] == q_record["id"]
    merged = ok(
        world.api.get(f"/objects/{world.key('P')}/{q_record['id']}", workspaceKey=WORKSPACE)
    )
    assert merged["name"] == "Venue"
    assert (
        next(a["value"] for a in merged["attributes"] if a["attributeTypeKey"] == "j33m-code")
        == "MG-CODE-Q"
    )
    own = ok(world.api.get(f"/objects/{world.key('P')}/{p_record['id']}", workspaceKey=WORKSPACE))
    assert (
        next(a["value"] for a in own["attributes"] if a["attributeTypeKey"] == "j33m-code")
        == "MG-CODE-P"
    )


@pytest.mark.journey("J33.19")
@pytest.mark.structures("K", "K.rank")
def test_a_split_creates_the_new_records_and_their_relationships(world):
    """Given K records, three holding a rank, two of them the same. When the editor splits K, moving
    K.rank to a new type related many to one, the draft states the split; the preview lists the
    records and relationships it creates (one new record for the shared rank, one for the other) and
    removes no value as a loss. Confirmed, each K with a rank is related to the new record holding it, the
    shared one is one record, and the K without a rank has none."""
    first = world.made("K", "K one", values={"K.rank": 7})
    second = world.made("K", "K two", values={"K.rank": 7})
    third = world.made("K", "K three", values={"K.rank": 9})
    bare = world.made("K", "K bare")
    draft = _draft_of_active(world, "Split K")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "splitObjectType",
                "objectType": world.key("K"),
                "key": "j33m-class",
                "name": "Weight class",
                "attributes": [world.key("K.rank")],
                "relationType": {
                    "key": "j33m-has-class",
                    "name": "Has class",
                    "reverseName": "Class of",
                },
                "cardinality": "many-to-one",
            },
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    migration = _migration(world, draft)
    assert migration["splits"] == [
        {
            "fromObjectTypeKey": world.key("K"),
            "toObjectTypeKey": "j33m-class",
            "attributes": [world.key("K.rank")],
            "relationTypeKey": "j33m-has-class",
            "cardinality": "many-to-one",
        }
    ]

    release = _installed(world, draft, "split")
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(migration, draft))
    counts = job["migration"]["counts"]
    assert counts["loss"] == 0 and counts["refused"] == 0 and counts["created"] >= 5
    created = _rows(world, job["id"], status="created")
    assert {row["code"] for row in created} == {"RECORD_CREATED", "RELATION_CREATED"}
    assert {first["id"], second["id"], third["id"]} <= {
        row["objectId"] for row in created if row["code"] == "RELATION_CREATED"
    }
    assert bare["id"] not in {row["objectId"] for row in created}
    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    related = {
        record["name"]: _related(world, record, "j33m-has-class")
        for record in (first, second, third, bare)
    }
    assert related["K one"] == related["K two"] and len(related["K one"]) == 1
    assert len(related["K three"]) == 1 and related["K three"] != related["K one"]
    assert related["K bare"] == []
    new = ok(world.api.get(f"/objects/j33m-class/{related['K one'][0]}", workspaceKey=WORKSPACE))
    assert (
        next(a["value"] for a in new["attributes"] if a["attributeTypeKey"] == world.key("K.rank"))
        == 7
    )
    assert _read(world, WORKSPACE, first)["attributes"] == [
        a
        for a in _read(world, WORKSPACE, first)["attributes"]
        if a["attributeTypeKey"] != world.key("K.rank")
    ]


@pytest.mark.journey("J33.19")
@pytest.mark.structures("P", "H.code")
def test_an_attribute_converted_to_a_list_type_becomes_records_linked_to_their_owners(world):
    """Given three P records, two with the same code. When the editor converts P's H.code into a list
    type, the draft states the conversion; the preview creates one list record per distinct code
    and one relationship per owner, with no loss. Confirmed, the records are linked to the record
    of their code and no longer hold the attribute."""
    one = world.made("P", "Estate one", values={"H.code": "MG-AAA"})
    two = world.made("P", "Estate two", values={"H.code": "MG-AAA"})
    three = world.made("P", "Estate three", values={"H.code": "MG-BBB"})
    draft = _draft_of_active(world, "Convert code")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "convertAttributeToListType",
                "objectType": world.key("P"),
                "attributeType": world.key("H.code"),
                "key": "j33m-codes",
                "name": "Codes",
                "relationType": {
                    "key": "j33m-has-code",
                    "name": "Has code",
                    "reverseName": "Code of",
                },
            },
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    migration = _migration(world, draft)
    assert [item["toObjectTypeKey"] for item in migration["listConversions"]] == ["j33m-codes"]

    release = _installed(world, draft, "listed")
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(migration, draft))
    counts = job["migration"]["counts"]
    assert counts["loss"] == 0 and counts["refused"] == 0 and counts["created"] >= 5
    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    targets = {
        record["name"]: _related(world, record, "j33m-has-code") for record in (one, two, three)
    }
    assert targets["Estate one"] == targets["Estate two"] and len(targets["Estate one"]) == 1
    code = ok(
        world.api.get(f"/objects/j33m-codes/{targets['Estate one'][0]}", workspaceKey=WORKSPACE)
    )
    assert code["name"] == "MG-AAA"
    assert not [
        a
        for a in _read(world, WORKSPACE, one)["attributes"]
        if a["attributeTypeKey"] == world.key("H.code")
    ]


@pytest.mark.journey("J33.19")
@pytest.mark.structures("R", "R.n")
def test_a_tighter_rule_is_applied_and_the_preview_lists_the_records_that_break_it(world):
    """Given R records, one without R.n. When the editor makes R.n required, the step applies and is
    marked as needing a migration; the migration proposes no mapping. The preview refuses exactly the
    record without a value, listed with its code, and the migration cannot be confirmed until that
    record is fixed."""
    held = world.made("R", "With a number", values={"R.n": 5})
    bare = world.made("R", "Without")
    draft = _draft_of_active(world, "Require R.n")
    ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "setAttributeBinding",
                "objectType": world.key("R"),
                "attributeType": world.key("R.n"),
                "required": True,
            },
        )
    )
    entry = _history(world, draft)["items"][0]
    assert entry["migration"][0]["element"] == {
        "objectType": world.key("R"),
        "attributeType": world.key("R.n"),
    }
    migration = _migration(world, draft)
    assert migration["required"] is True and migration["typeMappings"] == []

    release = _installed(world, draft, "required")
    job = _previewed(world, WORKSPACE, release["id"], **_proposal(migration, draft))
    refusals = _rows(world, job["id"], status="refused")
    assert job["migration"]["counts"]["refused"] == len(refusals) >= 1
    assert bare["id"] in {row["objectId"] for row in refusals}
    assert held["id"] not in {row["objectId"] for row in refusals}
    refused(_confirm(world, job), 409, "MIGRATION_HAS_REFUSALS")


@pytest.mark.journey("J33.19")
@pytest.mark.structures("Capi", "R", "R.u")
def test_a_key_change_lists_the_consumer_apis_naming_the_old_key(world):
    """Given a consumer API that reads R.u. When the editor changes R.u's key, the step applies and
    the migration names the key change with the consumer API of the base release that names the old
    key, so the integrations reading it can change with it."""
    draft = _draft_of_active(world, "Rename R.u")
    ok(
        _apply(
            world,
            draft,
            draft["version"],
            {"kind": "setKey", "element": {"attributeType": world.key("R.u")}, "key": "j33m-code"},
        )
    )
    changes = {change["from"]: change for change in _migration(world, draft)["keyChanges"]}
    named = [api["key"] for api in changes[world.key("R.u")]["consumerApis"]]
    assert named == [world.key("Capi")]
    assert changes[world.key("R.u")]["to"] == "j33m-code"
