"""0.9 Q2: the workspace edge list in live data, a change set and a publication, under two names."""

import pytest
from test_mapping_coverage import BASE, OUT, get, masters, relation
from test_mapping_coverage import client as mapping_client  # noqa: F401 - the client fixture
from test_relation_set_versions import _create_system_value, _suffix

ROUTES = ("/mappings", "/relations")


@pytest.fixture
def client(mapping_client):  # noqa: F811 - the imported fixture
    """The mapping tests' client: the starter model with its mapping views."""
    return mapping_client


def change_set_version(client, change_set_id):
    return client.get(f"/api/v1/change-sets/{change_set_id}").json()["version"]


def seed(client):
    """Edges that differ in each context.

    The publication holds e1 and e2. Live data then removes e1 and adds e3. A later change set
    removes e2 and adds e4, so live data is {e2, e3} and the change set {e3, e4}.
    """
    master, other = masters(client, 2)
    s1, s2, s3 = (_create_system_value(client, _suffix()) for _ in range(3))
    e1, e2 = relation(client, s1, master), relation(client, s2, master)

    published = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    publication = client.post(
        f"/api/v1/change-sets/{published['id']}/publication",
        json={"expectedChangeSetVersion": published["version"], "expectedActivePublicationId": None},
    )
    assert publication.status_code == 200, publication.text

    removed = client.delete(f"/api/v1/relations/{e1['id']}", params={"expectedVersion": e1["version"]})
    assert removed.status_code == 204, removed.text
    e3 = relation(client, s3, master)

    change_set = client.post(BASE + "/change-sets", json={"source": "currentLive"}).json()
    e4 = relation(
        client,
        s1,
        other,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    removed = client.delete(
        f"/api/v1/relations/{e2['id']}",
        params={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set_version(client, change_set["id"]),
            "expectedVersion": e2["version"],
        },
    )
    assert removed.status_code == 204, removed.text
    return {
        "edges": {name: edge["id"] for name, edge in zip(("e1", "e2", "e3", "e4"), (e1, e2, e3, e4))},
        "contexts": {
            "live": {},
            "changeSet": {"changeSetId": change_set["id"]},
            "publication": {"publicationId": publication.json()["id"]},
        },
    }


def walk(client, route, params):
    items, cursor = [], None
    while True:
        page = get(client, route, {**params, "pageSize": 2, **({"cursor": cursor} if cursor else {})})
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


EXPECTED = {"live": {"e2", "e3"}, "changeSet": {"e3", "e4"}, "publication": {"e1", "e2"}}


def test_each_context_lists_its_own_edges_under_both_routes(client):
    seeded = seed(client)
    names = {relation_id: name for name, relation_id in seeded["edges"].items()}
    for context_name, context in seeded["contexts"].items():
        pages = {route: walk(client, route, context) for route in ROUTES}
        assert pages["/mappings"] == pages["/relations"], context_name
        edges = [row for row in pages["/relations"] if row["relationId"] in names]
        # Without a direction each edge appears once per direction.
        assert sorted((names[row["relationId"]], row["direction"]) for row in edges) == sorted(
            (name, direction)
            for name in EXPECTED[context_name]
            for direction in ("incoming", "outgoing")
        ), context_name
        totals = {
            route: get(client, route, {**context, "includeTotal": True})["totalCount"]
            for route in ROUTES
        }
        assert totals["/mappings"] == totals["/relations"] == len(pages["/relations"])


@pytest.mark.parametrize("route", ROUTES)
def test_publication_reads_its_projection_with_version_zero(client, route):
    seeded = seed(client)
    publication = seeded["contexts"]["publication"]
    rows = get(client, route, {**OUT, **publication})["items"]
    published = {seeded["edges"]["e1"], seeded["edges"]["e2"]}
    rows = [row for row in rows if row["relationId"] in published]
    assert {row["relationId"] for row in rows} == published
    assert all(row["direction"] == "outgoing" and row["mappingVersion"] == 0 for row in rows)
    # The view's columns come from the publication's stored attributes.
    assert all(row["source"]["fields"] and row["target"]["fields"] for row in rows)
    live = get(client, route, OUT)["items"]
    assert all(row["mappingVersion"] >= 1 for row in live)


@pytest.mark.parametrize("route", ROUTES)
def test_context_refusals(client, route):
    seeded = seed(client)
    both = {**seeded["contexts"]["changeSet"], **seeded["contexts"]["publication"]}
    response = client.get(BASE + route, params=both)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "mutually_exclusive_context"
    response = client.get(BASE + route, params={"publicationId": "missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "publication_not_found"


def test_cursors_bind_route_and_context(client):
    seeded = seed(client)
    contexts = seeded["contexts"]
    for context_name, context in contexts.items():
        for route in ROUTES:
            cursor = get(client, route, {**context, "pageSize": 1})["nextCursor"]
            assert cursor, (context_name, route)
            other_route = next(row for row in ROUTES if row != route)
            refused = client.get(BASE + other_route, params={**context, "cursor": cursor})
            assert refused.status_code == 422, (context_name, route)
            assert refused.json()["error"]["code"] == "invalid_cursor"
            for other_name, other in contexts.items():
                if other_name == context_name:
                    continue
                refused = client.get(BASE + route, params={**other, "cursor": cursor})
                assert refused.status_code == 422, (context_name, other_name, route)
                assert refused.json()["error"]["code"] == "invalid_cursor"
