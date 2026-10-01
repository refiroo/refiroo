"""Base 0.8 P2a: a change set's object and relation change lists.

``GET /change-sets/{id}/object-changes`` and ``/relation-changes`` list the change set's own rows
read against its source: ``added``, ``changed`` or ``removed``, with before and after (D31). The
starter model's systems (values under systems) and master data (a mapped master value) are edited
in a current-live change set with every kind, a move, an edit reverted and a record created then
deleted; the lists are checked against what publishing then does to live. A publication-sourced
and an empty-root change set cover the other sources.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from postgres_server import collated
from sqlalchemy import create_engine, text
from wp8_support import create_change_set, publish_change_set

from app.config import reload_settings
from app.db import get_engine
from app.engine.model.registry import model_registry
from app.engine.reads import change_lists
from app.main import create_app

STARTER = Path(__file__).resolve().parents[2] / "model/rdm-starter.json"
LIVE = {"workspaceKey": "default"}
SYSTEMS, VALUE, SYSTEM = "rdm-systems", "system-value", "system"
MAPS_TO = "system-value-maps-to-master"


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database):
    model_path = tmp_path / "model.json"
    model_path.write_text(STARTER.read_text())
    monkeypatch.setenv("DATABASE_URL", migrated_database("change-lists.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def attr(key, value):
    return {"attributeTypeKey": key, "value": value}


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json() if response.content else None


class Editor:
    """Writes live, or in one change set while tracking its version."""

    def __init__(self, client, change_set=None):
        self.client, self.change_set = client, change_set

    def context(self) -> dict:
        if self.change_set is None:
            return dict(LIVE)
        return {
            "changeSetId": self.change_set["id"],
            "expectedChangeSetVersion": self.change_set["version"],
        }

    def track(self, body):
        if self.change_set is not None and body and body.get("changeSetVersion"):
            self.change_set["version"] = body["changeSetVersion"]
        return body

    def refresh(self) -> None:
        if self.change_set is not None:
            self.change_set["version"] = ok(
                self.client.get(f"/api/v1/change-sets/{self.change_set['id']}")
            )["version"]

    def create(self, object_type, name, parent=None, attributes=None, application=SYSTEMS):
        payload = {
            "applicationKey": application,
            "objectTypeKey": object_type,
            "name": name,
            "attributes": attributes or [],
            **self.context(),
        }
        if parent:
            payload["parentObjectId"] = parent["id"]
        return self.track(ok(self.client.post("/api/v1/objects", json=payload), 201))

    def value(self, name, parent, **extra):
        attributes = [
            attr("value-code", f"{name}-{uuid4().hex[:6]}"),
            attr("value-name", name),
            *(attr(key, value) for key, value in extra.items()),
        ]
        return self.create(VALUE, name, parent, attributes)

    def read(self, object_type, object_id):
        params = {"changeSetId": self.change_set["id"]} if self.change_set else LIVE
        return ok(self.client.get(f"/api/v1/objects/{object_type}/{object_id}", params=params))

    def update(self, record, **fields):
        current = self.read(record["objectTypeKey"], record["id"])
        body = {**fields, "expectedVersion": current["version"], **self.context()}
        body.pop("workspaceKey", None)
        return self.track(
            ok(self.client.patch(f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", json=body))
        )

    def delete(self, record):
        current = self.read(record["objectTypeKey"], record["id"])
        params = {"expectedVersion": current["version"], **self.context()}
        params.pop("workspaceKey", None)
        path = f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}"
        response = self.client.delete(path, params=params)
        if response.status_code == 409:
            # Its relations go with it, as the deletion preview lists them.
            token = response.json()["error"]["details"]["deletionPreviewToken"]
            response = self.client.delete(
                path, params={**params, "cascade": True, "deletionPreviewToken": token}
            )
        ok(response, 204)
        self.refresh()

    def relate(self, from_record, to_record, relation_type=MAPS_TO):
        body = {
            "relationTypeKey": relation_type,
            "fromObjectId": from_record["id"],
            "toObjectId": to_record["id"],
            "attributes": {},
            **self.context(),
        }
        body.pop("workspaceKey", None)
        return self.track(ok(self.client.post("/api/v1/relations", json=body), 201))

    def relation(self, from_record, relation_type=MAPS_TO) -> dict:
        params = {
            "objectId": from_record["id"],
            "direction": "outgoing",
            "relationTypeKey": relation_type,
            **({"changeSetId": self.change_set["id"]} if self.change_set else LIVE),
        }
        items = ok(self.client.get("/api/v1/relations", params=params))["items"]
        assert len(items) == 1, items
        return items[0]["relation"]

    def touch_relation(self, relation):
        body = {"attributes": {}, "expectedVersion": relation["version"], **self.context()}
        body.pop("workspaceKey", None)
        return self.track(ok(self.client.patch(f"/api/v1/relations/{relation['id']}", json=body)))

    def unrelate(self, relation):
        params = {"expectedVersion": relation["version"], **self.context()}
        params.pop("workspaceKey", None)
        ok(self.client.delete(f"/api/v1/relations/{relation['id']}", params=params), 204)
        self.refresh()


def changes(client, change_set_id, records="object", **params):
    return ok(client.get(f"/api/v1/change-sets/{change_set_id}/{records}-changes", params=params))


def every(client, change_set_id, records="object", **params) -> list[dict]:
    items, cursor = [], None
    while True:
        body = changes(
            client, change_set_id, records, pageSize=500, **params, **({"cursor": cursor} if cursor else {})
        )
        items += body["items"]
        cursor = body["nextCursor"]
        if cursor is None:
            return items


def by_id(items, key="objectId") -> dict[str, dict]:
    return {item[key]: item for item in items}


@pytest.fixture
def edited(client):
    """Live systems, values and a mapped master value, then a current-live change set touching them."""
    live = Editor(client)
    system_1 = live.create(SYSTEM, "System 1", attributes=[attr("system-code", f"S1-{uuid4().hex[:6]}")])
    system_2 = live.create(SYSTEM, "System 2", attributes=[attr("system-code", f"S2-{uuid4().hex[:6]}")])
    domain = live.create(
        "domain", "Domain", attributes=[attr("domain-code", f"D-{uuid4().hex[:6]}")], application="rdm-master"
    )
    codelist = live.create(
        "codelist", "Codelist", domain, [attr("codelist-code", f"C-{uuid4().hex[:6]}")], application="rdm-master"
    )
    master = live.create(
        "master-value",
        "Master",
        codelist,
        [
            attr("master-id", f"M-{uuid4().hex[:6]}"),
            attr("value-code", "M"),
            attr("value-name", "Master"),
            attr("sort-order", 3),
            attr("valid-from", "2026-01-01"),
        ],
        application="rdm-master",
    )
    renamed = live.value("Value renamed", system_1, active=True)
    moved = live.value("Value moved", system_1)
    removed = live.value("Value removed", system_1)
    live.relate(renamed, master)
    live.relate(moved, master)

    change_set = create_change_set(client, "default", source="currentLive").json()
    edit = Editor(client, change_set)
    added = edit.value("Value added", system_2, active=False)
    edit.relate(added, master)
    edit.update(renamed, name="Value renamed (edited)", attributes=[attr("active", False)])
    edit.update(moved, parentObjectId=system_2["id"])
    edit.delete(removed)
    transient = edit.value("Value created then deleted", system_1)
    edit.delete(transient)
    edit.update(system_2, name="System 2 (edited)")
    edit.update(system_2, name="System 2")
    edit.update(master, attributes=[attr("sort-order", 4), attr("valid-from", "2026-02-01")])
    edit.unrelate(edit.relation(renamed))
    edit.touch_relation(edit.relation(moved))
    return {
        "client": client,
        "change_set": change_set,
        "edit": edit,
        "records": {
            "system_1": system_1,
            "system_2": system_2,
            "master": master,
            "renamed": renamed,
            "moved": moved,
            "removed": removed,
            "added": added,
            "transient": transient,
        },
    }


def test_object_changes_list_every_kind_with_before_and_after(edited):
    client, change_set, records = edited["client"], edited["change_set"], edited["records"]
    entries = every(client, change_set["id"])
    listed = by_id(entries)
    # Created then deleted inside the change set never reaches live: it is left out.
    assert records["transient"]["id"] not in listed
    kinds = {name: listed[record["id"]]["kind"] for name, record in records.items() if record["id"] in listed}
    assert kinds == {
        "system_2": "changed",
        "master": "changed",
        "renamed": "changed",
        "moved": "changed",
        "removed": "removed",
        "added": "added",
    }
    # Ordered by type, then name, then ID, as the database orders names.
    assert [(item["objectTypeKey"], item["path"][-1]["name"]) for item in entries] == collated(
        (item["objectTypeKey"], item["path"][-1]["name"]) for item in entries
    )

    added = listed[records["added"]["id"]]
    assert added["before"] is None and added["after"]["version"] == 1
    assert added["applicationKey"] == SYSTEMS and added["objectTypeKey"] == VALUE
    assert added["changedFields"][:2] == ["name", "parent"]
    assert {"value-code", "value-name", "active"} <= set(added["changedFields"])
    assert [part["name"] for part in added["path"]] == ["System 2", "Value added"]

    renamed = listed[records["renamed"]["id"]]
    assert renamed["changedFields"] == ["name", "active"]
    assert renamed["before"]["name"] == "Value renamed"
    assert renamed["after"]["name"] == "Value renamed (edited)"
    assert renamed["after"]["version"] == renamed["before"]["version"] + 1
    # Typed values keep their types on both sides.
    before = {item["attributeTypeKey"]: item for item in renamed["before"]["attributes"]}
    after = {item["attributeTypeKey"]: item for item in renamed["after"]["attributes"]}
    assert before["active"]["value"] is True and after["active"]["value"] is False
    assert after["active"]["valueType"] == "boolean"
    master = listed[records["master"]["id"]]
    assert master["changedFields"] == ["sort-order", "valid-from"]
    values = {item["attributeTypeKey"]: item["value"] for item in master["after"]["attributes"]}
    assert values["sort-order"] == 4 and values["valid-from"] == "2026-02-01"
    assert {item["attributeTypeKey"]: item["value"] for item in master["before"]["attributes"]}[
        "sort-order"
    ] == 3

    # A move is a parent change, with the path where the change set puts the record.
    moved = listed[records["moved"]["id"]]
    assert moved["changedFields"] == ["parent"]
    assert moved["before"]["parentObjectId"] == records["system_1"]["id"]
    assert moved["after"]["parentObjectId"] == records["system_2"]["id"]
    assert [part["name"] for part in moved["path"]] == ["System 2", "Value moved"]
    # ...and where its source held it, so a review names both parents (P2b).
    assert [part["name"] for part in moved["beforePath"]] == ["System 1", "Value moved"]
    assert renamed["beforePath"] is None

    # Edited back: its version advanced and publishing claims it, so it stays with no fields.
    reverted = listed[records["system_2"]["id"]]
    assert reverted["changedFields"] == []
    assert reverted["after"]["version"] > reverted["before"]["version"]

    # A removed record's path is where its source held it.
    removed = listed[records["removed"]["id"]]
    assert removed["after"] is None and removed["before"]["name"] == "Value removed"
    assert removed["changedFields"][:2] == ["name", "parent"]
    assert [part["name"] for part in removed["path"]] == ["System 1", "Value removed"]
    assert removed["beforePath"] is None


def test_relation_changes_list_every_kind_and_mark_containment(edited):
    client, change_set, records = edited["client"], edited["change_set"], edited["records"]
    entries = every(client, change_set["id"], "relation")
    assert [(item["relationTypeKey"], item["relationId"]) for item in entries] == sorted(
        (item["relationTypeKey"], item["relationId"]) for item in entries
    )
    summary = sorted(
        (
            item["kind"],
            item["relationTypeKey"],
            item["containment"],
            item["fromObject"]["name"],
            item["toObject"]["name"],
        )
        for item in entries
    )
    assert summary == sorted(
        [
            ("added", "system-contains-value", True, "System 2", "Value added"),
            ("added", MAPS_TO, False, "Value added", "Master"),
            # The move: the old edge removed and a new one added.
            ("removed", "system-contains-value", True, "System 1", "Value moved"),
            ("added", "system-contains-value", True, "System 2", "Value moved"),
            ("removed", "system-contains-value", True, "System 1", "Value removed"),
            ("removed", MAPS_TO, False, "Value renamed (edited)", "Master"),
            ("changed", MAPS_TO, False, "Value moved", "Master"),
        ]
    )
    touched = next(item for item in entries if item["kind"] == "changed")
    assert touched["changedFields"] == [] and touched["after"]["version"] == touched["before"]["version"] + 1
    added = next(item for item in entries if item["kind"] == "added" and not item["containment"])
    assert added["before"] is None and added["after"] == {"attributes": {}, "version": 1}
    # A removed end is read in the source.
    removed_end = next(
        item for item in entries if item["toObject"]["objectId"] == records["removed"]["id"]
    )
    assert removed_end["toObject"] == {
        "objectId": records["removed"]["id"],
        "objectTypeKey": VALUE,
        "name": "Value removed",
    }
    assert removed_end["after"] is None and removed_end["before"]["version"] == 1


def test_filters_narrow_each_list(edited):
    client, change_set_id, records = edited["client"], edited["change_set"]["id"], edited["records"]
    removed = every(client, change_set_id, kind=["removed"])
    assert [item["objectId"] for item in removed] == [records["removed"]["id"]]
    both = every(client, change_set_id, kind=["added", "removed"])
    assert {item["kind"] for item in both} == {"added", "removed"} and len(both) == 2
    systems = every(client, change_set_id, objectTypeKey=[SYSTEM])
    assert [item["objectId"] for item in systems] == [records["system_2"]["id"]]
    two_types = every(client, change_set_id, objectTypeKey=[SYSTEM, "master-value"])
    assert {item["objectTypeKey"] for item in two_types} == {SYSTEM, "master-value"}

    edges = every(client, change_set_id, "relation", containment=True)
    assert len(edges) == 4 and all(item["containment"] for item in edges)
    mappings = every(client, change_set_id, "relation", containment=False)
    assert len(mappings) == 3 and not any(item["containment"] for item in mappings)
    by_type = every(client, change_set_id, "relation", relationTypeKey=[MAPS_TO], kind=["changed"])
    assert [item["kind"] for item in by_type] == ["changed"]
    assert every(client, change_set_id, "relation", relationTypeKey=["system-contains-value"], containment=False) == []


def test_pages_walk_both_ways_jump_and_count(edited):
    client, change_set_id = edited["client"], edited["change_set"]["id"]
    for records in ("object", "relation"):
        identity = "objectId" if records == "object" else "relationId"
        reference = [item[identity] for item in every(client, change_set_id, records)]
        assert len(reference) >= 6
        assert {item["kind"] for item in every(client, change_set_id, records)} == {"added", "changed", "removed"}

        forward, cursor = [], None
        while True:
            body = changes(
                client, change_set_id, records, pageSize=2, includeTotal=True, **({"cursor": cursor} if cursor else {})
            )
            assert body["totalCount"] == len(reference)
            assert body["startIndex"] == len(forward)
            forward += [item[identity] for item in body["items"]]
            cursor = body["nextCursor"]
            if cursor is None:
                break
        assert forward == reference

        backward, body = [], changes(client, change_set_id, records, pageSize=2, **{"from": "end"})
        while True:
            backward = [item[identity] for item in body["items"]] + backward
            if body["prevCursor"] is None:
                break
            body = changes(client, change_set_id, records, pageSize=2, cursor=body["prevCursor"])
        assert backward == reference

        for position in (0, 1, 3, len(reference) - 1, len(reference)):
            body = changes(client, change_set_id, records, pageSize=2, position=position, includeTotal=True)
            assert [item[identity] for item in body["items"]] == reference[position : position + 2]
            assert (body["startIndex"], body["totalCount"]) == (position, len(reference))
            anchor = body["anchor"]
            if anchor:
                again = changes(client, change_set_id, records, pageSize=2, cursor=anchor)
                assert again["items"] == body["items"]

    # A cursor is bound to its filters.
    cursor = changes(client, change_set_id, pageSize=1)["nextCursor"]
    refused = client.get(
        f"/api/v1/change-sets/{change_set_id}/object-changes",
        params={"pageSize": 1, "cursor": cursor, "kind": "added"},
    )
    assert refused.status_code == 422 and refused.json()["error"]["code"] == "invalid_cursor"


def test_the_lists_agree_with_what_publishing_does_to_live(edited):
    client, change_set, records = edited["client"], edited["change_set"], edited["records"]
    objects = by_id(every(client, change_set["id"]))
    relations = every(client, change_set["id"], "relation")
    edited["edit"].refresh()
    publish_change_set(client, change_set["id"], expected_change_set_version=change_set["version"])

    for object_id, entry in objects.items():
        response = client.get(f"/api/v1/objects/{entry['objectTypeKey']}/{object_id}", params=LIVE)
        if entry["kind"] == "removed":
            assert response.status_code == 404, entry
            continue
        live = ok(response)
        assert live["name"] == entry["after"]["name"]
        assert live["parentObjectId"] == entry["after"]["parentObjectId"]
        assert {item["attributeTypeKey"]: item["value"] for item in live["attributes"]} == {
            item["attributeTypeKey"]: item["value"] for item in entry["after"]["attributes"]
        }
    assert (
        client.get(f"/api/v1/objects/{VALUE}/{records['transient']['id']}", params=LIVE).status_code
        == 404
    )
    for entry in relations:
        params = {"objectId": entry["fromObject"]["objectId"], "direction": "outgoing", **LIVE}
        response = client.get("/api/v1/relations", params={**params, "pageSize": 500})
        live_ids = (
            {item["relation"]["id"] for item in response.json()["items"]}
            if response.status_code == 200
            else set()
        )
        assert (entry["relationId"] in live_ids) == (entry["kind"] != "removed"), entry


def test_a_publication_sourced_change_set_reads_before_from_the_publication(edited):
    client, change_set, records = edited["client"], edited["change_set"], edited["records"]
    edited["edit"].refresh()
    publication = ok(
        publish_change_set(client, change_set["id"], expected_change_set_version=change_set["version"])
    )
    live = Editor(client)
    # Live moves on after the publication; the list still reads the publication.
    live.update(records["added"], name="Value added (live)")

    derived = create_change_set(client, "default", derived_from_publication_id=publication["id"]).json()
    edit = Editor(client, derived)
    edit.update(records["added"], name="Value added (derived)")
    edit.delete(records["moved"])
    fresh = edit.value("Value new", records["system_1"])
    listed = by_id(every(client, derived["id"]))
    assert {object_id: item["kind"] for object_id, item in listed.items()} == {
        records["added"]["id"]: "changed",
        records["moved"]["id"]: "removed",
        fresh["id"]: "added",
    }
    assert listed[records["added"]["id"]]["before"]["name"] == "Value added"
    assert listed[records["added"]["id"]]["changedFields"] == ["name"]
    assert [part["name"] for part in listed[records["moved"]["id"]]["path"]] == ["System 2", "Value moved"]
    relations = every(client, derived["id"], "relation")
    assert sorted((item["kind"], item["containment"]) for item in relations) == [
        ("added", True),
        ("removed", False),
        ("removed", True),
    ]


def test_an_empty_root_change_set_lists_only_additions(client):
    change_set = create_change_set(client, "default").json()
    edit = Editor(client, change_set)
    system = edit.create(SYSTEM, "Root system", attributes=[attr("system-code", f"R-{uuid4().hex[:6]}")])
    value = edit.value("Root value", system)
    transient = edit.value("Root transient", system)
    edit.delete(transient)
    edit.update(value, name="Root value (edited)")
    objects = every(client, change_set["id"])
    assert [(item["kind"], item["objectId"]) for item in objects] == [
        ("added", system["id"]),
        ("added", value["id"]),
    ]
    assert objects[1]["after"]["name"] == "Root value (edited)" and objects[1]["before"] is None
    relations = every(client, change_set["id"], "relation")
    assert [(item["kind"], item["containment"], item["toObject"]["name"]) for item in relations] == [
        ("added", True, "Root value (edited)")
    ]
    assert every(client, change_set["id"], kind=["changed", "removed"]) == []


def test_a_page_and_its_paths_read_one_snapshot(edited, monkeypatch):
    """A write committed between the page's statement and its path walk does not reach the page.

    The page reads at REPEATABLE READ: a rename another connection commits between the page's
    statement and its path walk is not seen, so the renamed parent never appears in paths beside
    that parent's own entry under its old name.
    """
    client, change_set, records = edited["client"], edited["change_set"], edited["records"]
    attempts: list[str] = []
    walk = change_lists._paths

    def rename_between_statements(*args, **kwargs):
        if not attempts:
            other = create_engine(get_engine().url)
            try:
                with other.begin() as connection:
                    connection.execute(
                        text(
                            "UPDATE change_set_objects SET name = 'Renamed meanwhile'"
                            " WHERE change_set_id = :change_set AND object_id = :record"
                        ),
                        {"change_set": change_set["id"], "record": records["system_2"]["id"]},
                    )
                attempts.append("committed")
            finally:
                other.dispose()
        return walk(*args, **kwargs)

    monkeypatch.setattr(change_lists, "_paths", rename_between_statements)
    listed = by_id(changes(client, change_set["id"], pageSize=500)["items"])
    # The rename committed while the page was read, and the page did not see it.
    assert attempts == ["committed"]
    assert listed[records["system_2"]["id"]]["after"]["name"] == "System 2"
    for record in ("added", "moved"):
        assert [part["name"] for part in listed[records[record]["id"]]["path"]] == [
            "System 2",
            records[record]["name"],
        ]


def test_refusals(client):
    missing = str(uuid4())
    for records in ("object", "relation"):
        response = client.get(f"/api/v1/change-sets/{missing}/{records}-changes")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "change_set_not_found"
    change_set = create_change_set(client, "default", source="currentLive").json()
    base = f"/api/v1/change-sets/{change_set['id']}"
    unknown_object = client.get(f"{base}/object-changes", params={"objectTypeKey": [SYSTEM, "no-such-type"]})
    assert unknown_object.status_code == 422
    assert unknown_object.json()["error"]["code"] == "unknown_object_type"
    assert unknown_object.json()["error"]["details"]["path"] == "/query/objectTypeKey"
    unknown_relation = client.get(f"{base}/relation-changes", params={"relationTypeKey": "no-such-type"})
    assert unknown_relation.status_code == 422
    assert unknown_relation.json()["error"]["code"] == "unknown_relation_type"
    assert client.get(f"{base}/object-changes", params={"kind": "moved"}).status_code == 422
    assert client.get(f"{base}/object-changes", params={"position": 1, "from": "end"}).status_code == 422
    empty = ok(client.get(f"{base}/object-changes", params={"includeTotal": True}))
    assert empty["items"] == [] and empty["totalCount"] == 0 and empty["nextCursor"] is None


@pytest.fixture
def mixed_client(tmp_path, monkeypatch, migrated_database):
    """The starter model with ``system-contains-value`` also permitted, as a plain relation, from a
    system to a master value, whose type does not declare it a parent relation."""
    model = json.loads(STARTER.read_text())
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": "system-contains-value",
            "fromObjectTypeKey": SYSTEM,
            "toObjectTypeKey": "master-value",
            "cardinality": "many-to-many",
        }
    )
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", migrated_database("change-lists-mixed.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def test_a_relation_type_used_both_ways_is_containment_only_to_a_child_type(mixed_client):
    client = mixed_client
    change_set = create_change_set(client, "default").json()
    edit = Editor(client, change_set)
    system = edit.create(SYSTEM, "System", attributes=[attr("system-code", f"S-{uuid4().hex[:6]}")])
    value = edit.value("Value", system)
    domain = edit.create(
        "domain", "Domain", attributes=[attr("domain-code", f"D-{uuid4().hex[:6]}")], application="rdm-master"
    )
    codelist = edit.create(
        "codelist", "Codelist", domain, [attr("codelist-code", f"C-{uuid4().hex[:6]}")], application="rdm-master"
    )
    master = edit.create(
        "master-value",
        "Master",
        codelist,
        [attr("master-id", f"M-{uuid4().hex[:6]}"), attr("value-code", "M"), attr("value-name", "Master")],
        application="rdm-master",
    )
    edit.relate(system, master, "system-contains-value")

    def ends(**params) -> set[tuple[str, bool]]:
        items = every(client, change_set["id"], "relation", relationTypeKey="system-contains-value", **params)
        return {(item["toObject"]["name"], item["containment"]) for item in items}

    assert ends() == {("Value", True), ("Master", False)}
    assert ends(containment=True) == {("Value", True)}
    assert ends(containment=False) == {("Master", False)}
    assert value["id"] in {item["toObject"]["objectId"] for item in every(client, change_set["id"], "relation", containment=True)}
