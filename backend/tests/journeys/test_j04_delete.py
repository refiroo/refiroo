"""J04 — Delete a record and what depends on it (USER_JOURNEYS.md)."""

import pytest
from scenario import ok, refused


def _delete(world, structure, object_id, version, **params):
    return world.api.delete(
        f"/objects/{world.key(structure)}/{object_id}", expectedVersion=version, **params
    )


def _preview(world, structure, object_id, **params):
    """The impact a delete without cascade reports, refused with its token."""
    version = world.record(
        structure, object_id, **{k: v for k, v in params.items() if k == "changeSetId"}
    )["version"]
    error = refused(
        _delete(world, structure, object_id, version, **params), 409, "OBJECT_HAS_DEPENDANTS"
    )
    return version, error["details"]


def _owned_dependant(world, owner, name="Dependant", children=0):
    """A D record owned by ``owner`` under a new G record, with ``children`` D2 records."""
    g = world.made("G", f"Scope of {name}")
    d = world.made(
        "D", name, parent=world.dependant_parent(g["id"]), relations=[world.owner("Bown", owner)]
    )
    kids = [world.made("D2", f"{name} child {i}", parent=d["id"]) for i in range(children)]
    return g, d, kids


@pytest.mark.journey("J04")
@pytest.mark.structures("R", "K", "B1n", "G", "D", "D2", "Bown")
def test_preview_then_confirm_a_cascading_delete(world):
    """Given R record r owning D record d (with a child) and related to K record k by an optional
    relationship. When r is deleted without cascade. Then nothing is deleted and the impact names d
    and its child, the relationships, three records, the associations kept and a token. When
    confirmed with the token. Then r, d and its child are gone, k survives and k's history shows
    the relationship removed."""
    r = world.made("R", "Owner")
    k = world.made("K", "Kept token")
    ok(world.relate("B1n", r["id"], k["id"]), 201)
    _g, d, (d2,) = _owned_dependant(world, r["id"], children=1)

    version, impact = _preview(world, "R", r["id"])
    assert {item["id"] for item in impact["objectsToDelete"]} == {d["id"], d2["id"]}
    assert impact["relationshipsToRemove"]
    # Kept: the optional relationship to k, and the dependant's link to the container it stood in
    # (API.md: every incident relationship with an end outside the deletion set).
    assert impact["objectCount"] == 3 and impact["retainedAssociationCount"] == 2
    assert world.record("R", r["id"])["version"] == version

    confirmed = _delete(
        world,
        "R",
        r["id"],
        version,
        cascade=True,
        deletionPreviewToken=impact["deletionPreviewToken"],
    )
    assert confirmed.status_code == 204, confirmed.text
    for structure, record in (("R", r), ("D", d), ("D2", d2)):
        refused(world.read(structure, record["id"]), 404, "OBJECT_NOT_FOUND")
    assert world.record("K", k["id"])["id"] == k["id"]
    history = ok(world.api.get(f"/objects/{world.key('K')}/{k['id']}/history"))["items"]
    assert ("relation", "deleted") in {(e["aggregateType"], e["action"]) for e in history}


@pytest.mark.journey("J04.1")
@pytest.mark.structures("R")
def test_a_record_with_nothing_depending_on_it_is_deleted_at_once(world):
    """Given R records with no children and no relationships. When one is deleted with its version,
    another with a stale version. Then the first is gone with no preview; the second is refused."""
    lone = world.made("R", "Lone")
    assert _delete(world, "R", lone["id"], lone["version"]).status_code == 204
    refused(world.read("R", lone["id"]), 404, "OBJECT_NOT_FOUND")

    other = world.made("R", "Other")
    ok(world.update("R", other["id"], other["version"], name="Other, changed"))
    refused(_delete(world, "R", other["id"], other["version"]), 409, "VERSION_CONFLICT")
    assert world.record("R", other["id"])["name"] == "Other, changed"


@pytest.mark.journey("J04.2")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_deep_subtree_with_relationships_at_several_levels(world):
    """Given H record h2 with descendants to level 6, relationships inside the subtree and from
    levels 3 and 5 to K records outside it. When previewed, then confirmed. Then the preview counts
    the subtree, every relationship touching it and those reaching outside it; afterwards the subtree
    is gone and the K records and the other branch are unchanged."""
    ok(world.relate("Bnn", world.ids["h3"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    subtree = [world.ids[f"h{level}"] for level in range(2, 7)]
    links = []
    for h in subtree:
        links += ok(world.api.get("/relations", objectId=h, pageSize=100))["items"]
    incident = {item["relation"]["id"]: item for item in links}
    outside = [item for item in incident.values() if item["object"]["id"] not in subtree]
    tokens = {key: world.record("K", world.ids[key]) for key in ("k01", "k02")}
    south = world.record("H", world.ids["j1"])

    version, impact = _preview(world, "H", world.ids["h2"])
    assert impact["objectCount"] == len(subtree)
    assert impact["relationshipCount"] == len(incident)
    assert impact["retainedAssociationCount"] == len(outside)

    confirmed = _delete(
        world,
        "H",
        world.ids["h2"],
        version,
        cascade=True,
        deletionPreviewToken=impact["deletionPreviewToken"],
    )
    assert confirmed.status_code == 204, confirmed.text
    for h in subtree:
        refused(world.read("H", h), 404, "OBJECT_NOT_FOUND")
    for key, before in tokens.items():
        assert world.record("K", world.ids[key])["version"] == before["version"]
    assert world.record("H", world.ids["j1"])["version"] == south["version"]


@pytest.mark.journey("J04.3")
@pytest.mark.structures("R", "G", "D", "D2", "Bown")
def test_an_owner_across_applications_takes_its_dependants(world):
    """Given R record r owning D records of the other application, one with children. When r is
    deleted with preview and confirmation. Then the preview lists the dependants and their children
    with their application; afterwards they are all gone."""
    r = world.made("R", "Owner")
    _g, first, kids = _owned_dependant(world, r["id"], "First", children=2)
    _g, second, _none = _owned_dependant(world, r["id"], "Second")

    version, impact = _preview(world, "R", r["id"])
    listed = {item["id"]: item["applicationKey"] for item in impact["objectsToDelete"]}
    assert set(listed) == {first["id"], second["id"], *(kid["id"] for kid in kids)}
    assert listed[first["id"]] == world.app("D") != world.app("R")

    confirmed = _delete(
        world,
        "R",
        r["id"],
        version,
        cascade=True,
        deletionPreviewToken=impact["deletionPreviewToken"],
    )
    assert confirmed.status_code == 204, confirmed.text
    for structure, record in (("D", first), ("D", second), *(("D2", kid) for kid in kids)):
        refused(world.read(structure, record["id"]), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J04.4")
@pytest.mark.structures("R", "G", "D", "Bown")
def test_delete_in_a_change_set(world):
    """Given P1 and change set CS1 holding R record r with a dependant. When the delete is previewed
    and confirmed in CS1. Then CS1 holds neither, live and P1 still hold both; after publishing live
    holds neither and P1 still does."""
    r = world.made("R", "Owner")
    _g, d, _none = _owned_dependant(world, r["id"])
    p1 = world.publish(world.change_set())
    cs1 = world.change_set()

    version, impact = _preview(
        world,
        "R",
        r["id"],
        changeSetId=cs1["id"],
        expectedChangeSetVersion=world.current(cs1)["version"],
    )
    confirmed = _delete(
        world,
        "R",
        r["id"],
        version,
        changeSetId=cs1["id"],
        expectedChangeSetVersion=world.current(cs1)["version"],
        cascade=True,
        deletionPreviewToken=impact["deletionPreviewToken"],
    )
    assert confirmed.status_code == 204, confirmed.text

    for structure, record in (("R", r), ("D", d)):
        refused(world.read(structure, record["id"], changeSetId=cs1["id"]), 404, "OBJECT_NOT_FOUND")
        assert world.record(structure, record["id"])["id"] == record["id"]
        assert world.record(structure, record["id"], publicationId=p1["id"])["id"] == record["id"]
    world.publish(cs1)
    for structure, record in (("R", r), ("D", d)):
        refused(world.read(structure, record["id"]), 404, "OBJECT_NOT_FOUND")
        assert world.record(structure, record["id"], publicationId=p1["id"])["id"] == record["id"]


@pytest.mark.journey("J04.5")
@pytest.mark.structures("H")
def test_a_change_after_the_preview_refuses_the_confirmation(world):
    """Given a preview of H record h2's subtree. When another writer adds a child under a descendant,
    or changes a descendant's value, and the confirmation is sent. Then it is refused and every
    record remains, the new child included; a confirmation without its token is refused."""
    h2, h4 = world.ids["h2"], world.ids["h4"]
    version, impact = _preview(world, "H", h2)
    child = world.made("H", "Late child", parent=h4)
    late = _delete(
        world, "H", h2, version, cascade=True, deletionPreviewToken=impact["deletionPreviewToken"]
    )
    refused(late, 409, "DELETION_PREVIEW_CHANGED")
    assert world.record("H", child["id"])["parentObjectId"] == h4

    version, impact = _preview(world, "H", h2)
    h5 = world.record("H", world.ids["h5"])
    ok(world.update("H", h5["id"], h5["version"], values={"H.rank": 99}))
    changed = _delete(
        world, "H", h2, version, cascade=True, deletionPreviewToken=impact["deletionPreviewToken"]
    )
    refused(changed, 409, "DELETION_PREVIEW_CHANGED")
    refused(_delete(world, "H", h2, version, cascade=True), 409, "DELETION_PREVIEW_REQUIRED")
    for level in range(2, 7):
        assert world.record("H", world.ids[f"h{level}"])["id"] == world.ids[f"h{level}"]


@pytest.mark.journey("J04.6", "J13.6")
@pytest.mark.structures("R", "G", "D", "Bown")
def test_a_dependants_required_relationship_cannot_be_removed_alone(world):
    """Given D record d whose owning relationship from r is required. When that relationship is
    deleted directly. Then it is refused and the relationship and d remain; deleting d removes both.
    (J04.6 and J13.6 describe the same request.)"""
    r = world.made("R", "Owner")
    _g, d, _none = _owned_dependant(world, r["id"])
    relation = ok(world.api.get("/relations", objectId=d["id"], relationTypeKey=world.key("Bown")))[
        "items"
    ][0]["relation"]

    removed = world.api.delete(f"/relations/{relation['id']}", expectedVersion=relation["version"])
    refused(removed, 422, "REQUIRED_RELATION")
    assert ok(world.api.get(f"/relations/{relation['id']}"))["id"] == relation["id"]

    version, impact = _preview(world, "D", d["id"])
    confirmed = _delete(
        world,
        "D",
        d["id"],
        version,
        cascade=True,
        deletionPreviewToken=impact["deletionPreviewToken"],
    )
    assert confirmed.status_code == 204, confirmed.text
    refused(world.read("D", d["id"]), 404, "OBJECT_NOT_FOUND")
    refused(world.api.get(f"/relations/{relation['id']}"), 404, "RELATION_NOT_FOUND")
