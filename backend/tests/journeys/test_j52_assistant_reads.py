"""J52 — An assistant reads (USER_JOURNEYS.md § AI, Product 0.16 AG2).

Through ``/mcp`` with the protocol's own client: a value's code from a tool generated from a consumer
API definition, unmapped values from a mapping view, and the model as tools and resources. Each answer
is the API's own. Every case runs on two configurations, whose definitions differ, through the public
API.
"""

import copy
from typing import Any

import pytest
from pydantic import AnyUrl
from scenario import W1, W2, consumer_list, consumer_object, consumer_xref, ok
from test_j10_replace import _binding, _identity
from test_j41_consumer_grants import _as, _consumer
from test_j51_agent_access import ON, _agent_client, _call, _client_token, _grant, _tools, _use

CAPI = ("Capi", "R", "R2", "D", "K", "G", "B11", "Bown", "R.n")


def _reader(world, name: str = "Reading assistant", role: str = "reader", **scope: Any) -> str:
    client = _agent_client(world, name)
    _grant(world, "client", client["id"], role, **(scope or {"workspaceKey": W1}))
    return ok(_client_token(world, client))["access_token"]


def _answer(world, token: str, tool: str, **arguments: Any) -> dict[str, Any]:
    result = _call(world, token, tool, arguments)
    assert not result.isError, result.content
    return result.structuredContent


def _refusal(world, token: str, tool: str, **arguments: Any) -> str:
    result = _call(world, token, tool, arguments)
    assert result.isError, result.structuredContent
    return result.content[0].text


def _lookup(world) -> str:
    return f"lookup_{world.key('Capi')}"


def _granted_only(world) -> str:
    client = _agent_client(world, "Only a consumer API")
    ok(
        world.api.post(
            "/grants",
            {
                "principal": {"kind": "client", "id": client["id"]},
                "consumerApi": world.key("Capi"),
                "scope": {"workspaceKey": W1},
            },
        ),
        201,
    )
    return ok(_client_token(world, client))["access_token"]


@pytest.mark.journey("J52.1")
@pytest.mark.settings(**ON)
@pytest.mark.structures(*CAPI)
def test_a_value_is_looked_up_as_the_consumer_api_answers_it(world):
    """Given a client holding Browse and a client holding only the consumer API's grant. Each reads a
    record by terms, a list and one by ID from the generated tool, and each answer equals the consumer
    route's. The client with only the grant lists nothing else, and neither reads an API it may not."""
    record = world.made("R", "Findable ledger")
    world.publish(world.change_set())
    _, caller = _consumer(world, "The route", (world.key("Capi"), W1))
    route = _as(world, caller)
    tool = _lookup(world)
    browse = _reader(world)
    granted = _granted_only(world)
    assert _tools(world, granted) == ["describe_access", tool]
    assert tool in _tools(world, browse)

    for token in (browse, granted):
        found = _answer(
            world, token, tool, workspace=W1, operation="xref", query=["Findable"], pageSize=20
        )
        assert found == ok(consumer_xref(route, query="Findable", pageSize=20))
        one = _answer(world, token, tool, workspace=W1, operation="objects", objectId=record["id"])
        assert one == ok(consumer_object(route, record["id"]))
        listed = _answer(
            world,
            token,
            tool,
            workspace=W1,
            operation="lists",
            list=world.key("Capi.all"),
            pageSize=20,
        )
        assert listed == ok(consumer_list(route, world.key("Capi.all"), pageSize=20))

    assert "not one of" in _refusal(
        world, granted, tool, workspace=W2, operation="xref", query=["Findable"]
    )
    assert "needs objectId" in _refusal(world, browse, tool, workspace=W1, operation="objects")
    assert "needs list" in _refusal(world, browse, tool, workspace=W1, operation="lists")
    # The check is the route's, so it refuses in the route's words.
    assert "not supported on this read" in _refusal(
        world, browse, tool, workspace=W1, operation="objects", objectId=record["id"], pageSize=5
    )


@pytest.mark.journey("J52.2")
@pytest.mark.settings(**ON)
@pytest.mark.structures("H", "K", "Bnn", "Vnn")
def test_unmapped_values_are_paged_as_the_route_lists_them(world):
    """Given a mapping view with three sources, one of them mapped. Then ``mapping_coverage`` with
    ``state=unmapped`` pages through the other two, naming only the view, and equals the route."""
    sources = [world.made("H", f"Source {index}") for index in range(3)]
    target = world.made("K", "Target")
    binding = _binding(world, "Vnn")
    source_end = binding["direction"] == "outgoing"
    ok(
        world.api.post(
            "/relations",
            {
                "relationTypeKey": binding["relationTypeKey"],
                "fromObjectId": sources[0]["id"] if source_end else target["id"],
                "toObjectId": target["id"] if source_end else sources[0]["id"],
            },
        ),
        201,
    )
    identity = _identity(world, "Vnn")
    wanted = {
        row["source"]["id"]
        for row in ok(
            world.api.get(
                f"/workspaces/{W1}/mapping-coverage",
                **identity,
                state="unmapped",
                pageSize=100,
            )
        )["items"]
    }
    assert sources[0]["id"] not in wanted and {sources[1]["id"], sources[2]["id"]} <= wanted

    token = _reader(world)
    arguments = {
        "workspace": W1,
        "application": identity["applicationKey"],
        "view": identity["viewKey"],
        "state": "unmapped",
        "pageSize": 1,
    }
    seen: list[str] = []
    while True:
        page = _answer(world, token, "mapping_coverage", **arguments)
        seen.extend(row["source"]["id"] for row in page["items"])
        if not page.get("nextCursor"):
            break
        arguments["cursor"] = page["nextCursor"]
    assert len(seen) == len(set(seen)) and set(seen) == wanted


@pytest.mark.journey("J52.3")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R", "R.n")
def test_an_assistant_finds_its_way_from_the_model_to_a_record_and_its_changes(world):
    """Given a Browse client: the model names the type, the type its attributes, a query finds the
    record, the record reads with its relationships, its history and the workspace's changes. A
    workspace it cannot read is refused in the words of one that does not exist, on every tool."""
    record = world.made("R", "Traced ledger")
    token = _reader(world)
    model = _answer(world, token, "describe_model", workspace=W1)
    assert world.key("R") in {item["key"] for item in model["objectTypes"]}
    assert model["applications"][0]["views"]

    described = _answer(world, token, "describe_type", workspace=W1, objectType=world.key("R"))
    assert described["key"] == world.key("R")

    found = _answer(
        world,
        token,
        "find_records",
        workspace=W1,
        objectTypeKey=world.key("R"),
        where=[{"field": "name", "op": "eq", "value": "Traced ledger"}],
    )
    assert [item["id"] for item in found["items"]] == [record["id"]]

    read = _answer(
        world, token, "read_record", workspace=W1, objectType=world.key("R"), id=record["id"]
    )
    assert read["record"] == world.record("R", record["id"])
    assert read["relations"]["items"] == []

    history = _answer(
        world, token, "record_history", workspace=W1, objectType=world.key("R"), id=record["id"]
    )
    assert history["items"]
    assert "ISO 8601" in _refusal(world, token, "list_changes", workspace=W1, since="yesterday")
    changes = _answer(world, token, "list_changes", workspace=W1, kind=["record"])
    assert changes["items"]

    for tool, more in (
        ("describe_model", {}),
        ("describe_type", {"objectType": world.key("R")}),
        ("find_records", {"objectTypeKey": world.key("R")}),
        ("read_record", {"objectType": world.key("R"), "id": record["id"]}),
        ("mapping_coverage", {"application": "a", "view": "v"}),
        ("record_history", {"objectType": world.key("R"), "id": record["id"]}),
        ("list_changes", {}),
    ):
        closed = _refusal(world, token, tool, workspace=W2, **more)
        missing = _refusal(world, token, tool, workspace="no-such", **more)
        assert closed == f"WORKSPACE_NOT_FOUND: Workspace '{W2}' not found"
        assert missing == "WORKSPACE_NOT_FOUND: Workspace 'no-such' not found"


@pytest.mark.journey("J52.4")
@pytest.mark.settings(**ON)
@pytest.mark.structures(*CAPI)
def test_equal_definitions_share_a_tool_and_differing_ones_do_not(world):
    """Given a caller reading two workspaces on one model, one tool lists both. With the definition
    changed in one workspace only, the key gives two tools, each listing its own workspace, within the
    length an assistant's name can take; a long key too."""
    client = _agent_client(world, "Everywhere")
    for workspace in (W1, W2):
        _grant(world, "client", client["id"], "reader", workspaceKey=workspace)
    token = ok(_client_token(world, client))["access_token"]

    async def lookups(session):
        return [
            tool for tool in (await session.list_tools()).tools if tool.name.startswith("lookup_")
        ]

    [shared] = [tool for tool in _use(world, token, lookups) if tool.name == _lookup(world)]
    assert {W1, W2} <= set(shared.inputSchema["properties"]["workspace"]["enum"])
    assert shared.annotations.readOnlyHint is True

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-differs"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["name"] = "The same key, another contract"
    long_key = "a-very-long-consumer-api-key-that-no-assistant-could-carry-as-a-name"
    model["consumerApis"].append({**copy.deepcopy(definition), "key": long_key})
    release = world.install(model)
    ok(world.activate(release["id"], W2))

    tools = _use(world, token, lookups)
    assert all(len(tool.name) <= 48 for tool in tools)
    same_key = [tool for tool in tools if tool.name.startswith(_lookup(world) + "_")]
    assert len(same_key) == 2
    workspaces = [set(tool.inputSchema["properties"]["workspace"]["enum"]) for tool in same_key]
    assert W2 in workspaces[0] ^ workspaces[1]
    assert any("a-very-long" in tool.name for tool in tools)


@pytest.mark.journey("J52.5")
@pytest.mark.settings(**ON, MCP_ANSWER_BYTES="6000")
@pytest.mark.structures("R", "R.n")
def test_a_long_page_comes_back_smaller_and_every_row_is_read_once(world):
    """Given more records than fit the answer size. Asking for a large page gives a smaller one with
    a cursor, and reading on gives every record exactly once."""
    made = {world.made("R", f"Long {index:02}")["id"] for index in range(40)}
    token = _reader(world)
    arguments: dict[str, Any] = {"workspace": W1, "objectTypeKey": world.key("R"), "pageSize": 500}
    seen: list[str] = []
    first = True
    while True:
        page = _answer(world, token, "find_records", **arguments)
        if first:
            assert page["nextCursor"] and len(page["items"]) < 40
            first = False
        seen.extend(item["id"] for item in page["items"])
        if not page.get("nextCursor"):
            break
        arguments["cursor"] = page["nextCursor"]
    assert len(seen) == len(set(seen)) and made <= set(seen)


@pytest.mark.journey("J52.5")
@pytest.mark.settings(**ON, MCP_ANSWER_BYTES="100")
@pytest.mark.structures("R")
def test_a_long_answer_that_is_no_page_is_refused_and_says_where_to_read(world):
    """Given an answer that cannot shrink, it is refused and names the resource instead."""
    refusal = _refusal(world, _reader(world), "describe_model", workspace=W1)
    assert "100 bytes" in refusal and "resource" in refusal


@pytest.mark.journey("J52.6")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R")
def test_resources_are_listed_and_read_only_where_the_caller_may_read(world):
    """Given a Browse client in one workspace: its resources name that workspace only, each reads, and
    the read is recorded by argument name. Another workspace's address is refused, and a client without
    Browse has none."""
    token = _reader(world)

    async def listed(session):
        return (await session.list_resources()).resources

    resources = _use(world, token, listed)
    addresses = [str(item.uri) for item in resources]
    model_address = f"refiroo://workspaces/{W1}/model"
    assert model_address in addresses
    assert not any(f"/{W2}/" in address for address in addresses)
    type_address = f"refiroo://workspaces/{W1}/object-types/{world.key('R')}"
    assert type_address not in addresses

    async def templates(session):
        return (await session.list_resource_templates()).resourceTemplates

    assert len(_use(world, token, templates)) == 3

    def reading(uri: str):
        async def use(session):
            return await session.read_resource(AnyUrl(uri))

        return _use(world, token, use)

    assert world.key("R") in reading(model_address).contents[0].text
    assert world.key("R") in reading(type_address).contents[0].text
    with pytest.raises(ExceptionGroup) as closed:
        reading(f"refiroo://workspaces/{W2}/model")
    assert f"Workspace '{W2}' not found" in repr(closed.value.exceptions)

    with pytest.raises(ExceptionGroup) as nothing:
        reading(f"refiroo://workspaces/{W1}/nothing")
    assert "No resource at" in repr(nothing.value.exceptions)

    rows = ok(world.api.get("/agent-access/calls"))["items"]
    row = next(item for item in rows if item["tool"] == "read_resource")
    assert row["arguments"] == ["uri"]

    assert (
        _use(world, ok(_client_token(world, _agent_client(world, "None")))["access_token"], listed)
        == []
    )
