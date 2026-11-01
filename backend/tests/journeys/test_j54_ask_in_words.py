"""J54 — Ask in words (USER_JOURNEYS.md § Natural-language search, 0.16 AG4).

A steward types a question about a list; the provider turns it into the list's own filters, the
engine finds the records the question names in words, and the person sees ordinary filters to change
or remove. The provider is the deterministic fake (``app.engine.proposals.fake``), which records what
it was sent. The list is the table of a type, filtered by what it is related to and under which
ancestor; every case runs on two configurations through the public API.
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j27_export import _finished, _lines
from test_j34_onboard import _all
from test_j40_authorization import _client

from app.engine.proposals import fake
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"
STRUCTURES = ("R", "G", "D", "D.active", "Bown", "Bassoc")


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _related(world) -> str:
    return f"related:{world.key('Bassoc')}"


def _view(world) -> dict[str, str]:
    return {"applicationKey": world.app("R"), "viewKey": f"{world.key('R')}--list"}


def _ask(world, question="values changed today without a webshop mapping", **body):
    return world.api.post(
        f"/workspaces/{W1}/query-translations", {**_view(world), "question": question, **body}
    )


def _answer(world, filters=(), *, search="", not_expressed=()):
    return {
        "filters": [
            {"field": field, "condition": condition, "value": value}
            for field, condition, value in filters
        ],
        "search": search,
        "notExpressed": [{"part": part, "reason": reason} for part, reason in not_expressed],
    }


def _permit(world, region):
    owner = world.made("R", f"Holder {uuid4().hex[:8]}")
    return world.made(
        "D",
        f"Permit {uuid4().hex[:6]}",
        parent=world.dependant_parent(region["id"]),
        values={"D.active": True},
        relations=[world.owner("Bown", owner["id"])],
    )


def _scene(world):
    """Two regions, a permit under each, and four records: related to none, to a permit under the
    first, under the second, and under both."""
    tag = uuid4().hex[:6]
    web = world.made("G", f"Webshop {tag}")
    store = world.made("G", f"Storefront {tag}")
    in_web, in_store = _permit(world, web), _permit(world, store)
    records = {name: world.made("R", f"{name} {tag}") for name in ("none", "web", "store", "both")}
    for name, permits in (("web", [in_web]), ("store", [in_store]), ("both", [in_web, in_store])):
        for permit in permits:
            ok(world.relate("Bassoc", records[name]["id"], permit["id"]), 201)
    return tag, web, store, {"web": in_web, "store": in_store}, records


def _listed(world, tag, filters, **context):
    """The names (without the tag) the list gives for these filters, as the browser reads it."""
    params = {}
    for item in filters:
        params.setdefault(f"filter__{item['field']}__{item['operator']}", []).append(item["value"])
    page = ok(
        world.api.get(
            f"/objects/{world.key('R')}",
            search=tag,
            pageSize=100,
            workspaceKey=W1,
            **params,
            **context,
        )
    )
    return {row["name"].removesuffix(f" {tag}") for row in page["items"]}


def _last_call(world) -> dict:
    return _all(world, "/ai/calls")[0]


@pytest.mark.journey("J54.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_a_question_becomes_filters_the_list_applies_and_no_record_value_is_sent(world):
    """Given records related to permits under two regions and a provider, when a steward asks for
    the records changed today without a mapping under the first region, then the answer holds the
    date filter and the none-under filter with the region found by its name, nothing is left
    unexpressed and applying the filters lists exactly the records without one under that region.
    The call is recorded as answered; the provider was sent no record name, and no transaction was
    held while it answered."""
    tag, web, _store, _permits, _records = _scene(world)
    idle = []
    engine = create_engine(world.database, poolclass=NullPool)

    def provider(context):
        with engine.connect() as connection:
            idle.append(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                        " AND state = 'idle in transaction' AND pid <> pg_backend_pid()"
                    )
                )
            )
        return _answer(
            world,
            [("updatedAt", "gte", _today()), (_related(world), "notUnder", f"Webshop {tag}")],
        )

    fake.script("queryTranslation", provider)
    answer = ok(_ask(world))
    engine.dispose()
    assert answer["applied"] is True and answer["notExpressed"] == [] and answer["search"] == ""
    assert answer["filters"] == [
        {"field": "updatedAt", "operator": "gte", "value": _today()},
        {"field": _related(world), "operator": "notUnder", "value": web["id"]},
    ]
    assert idle == [0]
    assert _listed(world, tag, answer["filters"]) == {"none", "store"}
    call = _last_call(world)
    assert (call["purpose"], call["outcome"]) == ("queryTranslation", "answered")
    sent = fake.seen[-1]
    assert sent.context["question"] == "values changed today without a webshop mapping"
    assert sent.context["today"] == _today()
    asked = json.dumps([sent.context, sent.instructions])
    assert tag not in asked and "Holder" not in asked and "Permit" not in asked
    related = next(f for f in sent.context["fields"] if f["field"] == _related(world))
    assert set(related["conditions"]) == {"eq", "isNull", "under", "notUnder"}
    assert {f["field"] for f in sent.context["fields"]} >= {
        "createdAt",
        "updatedAt",
        _related(world),
    }


@pytest.mark.journey("J54.2")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_one_filter_of_the_answer_can_be_changed_and_the_list_follows(world):
    """Given the answer to a question, when the person changes the region of the none-under filter
    to the other region and then removes the date filter, then each list is the records the filters
    left stand for: the answer is only the list's own filters."""
    tag, _web, store, _permits, _records = _scene(world)
    fake.script(
        "queryTranslation",
        _answer(
            world, [("updatedAt", "gte", _today()), (_related(world), "notUnder", f"Webshop {tag}")]
        ),
    )
    filters = ok(_ask(world))["filters"]
    assert _listed(world, tag, filters) == {"none", "store"}
    changed = [filters[0], {**filters[1], "value": store["id"]}]
    assert _listed(world, tag, changed) == {"none", "web"}
    assert _listed(world, tag, [changed[1]]) == {"none", "web"}
    assert _listed(world, tag, [{**filters[0], "value": "2999-01-01"}, filters[1]]) == set()


@pytest.mark.journey("J54.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_part_the_list_cannot_express_is_named_and_nothing_is_applied(world):
    """Given a question with a part no filter can say (who changed a record), when it is asked, then
    applied is false, notExpressed names the part and the reason, and the filters that could be built
    are still returned for the person to take."""
    _scene(world)
    fake.script(
        "queryTranslation",
        _answer(
            world,
            [("updatedAt", "gte", _today())],
            not_expressed=[("by Anna", "This list has no filter for who changed a record")],
        ),
    )
    answer = ok(_ask(world, "values changed today by Anna"))
    assert answer["applied"] is False
    assert answer["notExpressed"] == [
        {"part": "by Anna", "reason": "This list has no filter for who changed a record"}
    ]
    assert answer["filters"] == [{"field": "updatedAt", "operator": "gte", "value": _today()}]
    # Asking for an order is not expressed either: the instructions say so, and nothing sorts.
    assert "sort" in fake.seen[-1].instructions.lower()


@pytest.mark.journey("J54.4")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_record_not_found_or_ambiguous_is_said_so_and_never_guessed(world):
    """Given regions named alike, when the question names a region that does not exist, one that
    several match by a part of the name, then the same by its whole name in other letters and one
    that a single region contains, then the first two are not expressed with the reason and the
    last two are found: the exact name first, a single partial match otherwise."""
    tag, web, store, _permits, _records = _scene(world)
    world.made("G", f"Shared one {tag}")
    world.made("G", f"Shared two {tag}")
    relation = _related(world)
    fake.script(
        "queryTranslation",
        _answer(
            world,
            [
                (relation, "notUnder", f"Nowhere {tag}"),
                (relation, "under", "Shared"),
                (relation, "under", f"webshop {tag}".upper()),
                (relation, "notUnder", f"front {tag}"),
            ],
        ),
    )
    answer = ok(_ask(world))
    assert answer["applied"] is False
    assert answer["filters"] == [
        {"field": relation, "operator": "under", "value": web["id"]},
        {"field": relation, "operator": "notUnder", "value": store["id"]},
    ]
    nowhere, several = answer["notExpressed"]
    assert nowhere["part"] == f'"Nowhere {tag}"' and "No " in nowhere["reason"]
    assert several["part"] == '"Shared"' and "Several" in several["reason"]
    assert f"Shared one {tag}" in several["reason"] and f"Shared two {tag}" in several["reason"]


@pytest.mark.journey("J54.5")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_an_invented_field_or_condition_or_a_failing_provider_is_a_failed_call(world):
    """Given a provider that answers with a field the list does not offer, a condition a field does
    not take, a value the list refuses, then fails, when it is asked, then each is a recorded failed
    call (502 QUERY_TRANSLATION_FAILED naming the call) and nothing comes back to apply."""
    _scene(world)
    attempts = [
        _answer(world, [("invented-field", "eq", "x")]),
        _answer(world, [("updatedAt", "startsWith", "2026")]),
        _answer(world, [("updatedAt", "gte", "last month")]),
        _answer(world, [(_related(world), "contains", "x")]),
        ProviderError("unreachable", "The provider could not be reached"),
    ]
    for answer in attempts:
        fake.script("queryTranslation", answer)
        error = refused(_ask(world), 502, "QUERY_TRANSLATION_FAILED")
        call = _last_call(world)
        assert (call["purpose"], call["outcome"]) == ("queryTranslation", "failed")
        assert error["details"] == {"callId": call["id"]}
        assert error["message"].startswith("The question could not be turned into filters")
    assert _last_call(world)["failureKind"] == "unreachable"


@pytest.mark.journey("J54.6")
@pytest.mark.structures(*STRUCTURES, "Massoc")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_asking_is_refused_without_use_ai_proposals_and_on_a_view_that_is_not_a_table(world):
    """Given a client who may browse but does not hold Use AI proposals, when it asks, then it is
    refused 403 naming the group and no call is made; and when the view is a relation matrix or does
    not exist, then it is refused with its code."""
    role = ok(world.api.post("/roles", {"name": "Readers", "actionGroups": ["browse"]}), 201)
    _, reader = _client(world, "Readers", (role["key"], {"instance": True}))
    before = len(_all(world, "/ai/calls"))
    error = refused(_ask(reader), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["ai-proposals"]
    assert len(_all(world, "/ai/calls")) == before == 0
    matrix = {"applicationKey": world.key("A3"), "viewKey": world.key("Massoc")}
    error = refused(
        world.api.post(f"/workspaces/{W1}/query-translations", {**matrix, "question": "all"}),
        422,
        "QUERY_TRANSLATION_VIEW_UNSUPPORTED",
    )
    assert error["details"]["viewType"] == "relationMatrix"
    refused(_ask(world, viewKey="no-such-view"), 404, "VIEW_NOT_FOUND")
    assert fake.seen == []


@pytest.mark.journey("J54.6")
@pytest.mark.structures(*STRUCTURES)
def test_without_a_provider_asking_is_refused(world):
    """Given no provider, then asking is refused 409 AI_NOT_CONFIGURED."""
    refused(_ask(world), 409, "AI_NOT_CONFIGURED")


@pytest.mark.journey("J54.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_a_send_level_above_the_ceiling_is_refused_and_the_lowest_level_is_enough(world):
    """Given a ceiling of structure, then the feature is offered and answers, and a request choosing
    a higher level is refused 409 AI_SEND_LEVEL_TOO_LOW naming the ceiling."""
    status = ok(world.api.get("/ai/status"))
    assert {f["purpose"]: f["available"] for f in status["features"]}["queryTranslation"] is True
    ok(_ask(world))
    error = refused(_ask(world, sendLevel="values"), 409, "AI_SEND_LEVEL_TOO_LOW")
    assert error["details"] == {"sendLevel": "values", "ceiling": "structure"}
    assert _last_call(world)["sendLevel"] == "structure"


@pytest.mark.journey("J54.7")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_in_a_change_set_the_date_is_not_expressed_and_the_other_filters_read_the_change_set(world):
    """Given a change set in which a record without a permit is related to one under the first
    region and a region exists only there, when a question with a date part is asked in it, then the
    stamps are not offered to the provider and an answer using one is a failed call; with the date
    part not expressed the other filters name the region, found in the change set, and listing the
    change set with them reads the change set while live data does not."""
    tag, web, _store, permits, records = _scene(world)
    change_set = world.change_set(name=f"{tag} staged")
    claim = {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
    }
    ok(world.relate("Bassoc", records["none"]["id"], permits["web"]["id"], **claim), 201)
    draft = world.made("G", f"Draft region {tag}", change_set=world.current(change_set))
    relation = _related(world)
    context = {"changeSetId": change_set["id"]}

    fake.script("queryTranslation", _answer(world, [("updatedAt", "gte", _today())]))
    refused(_ask(world, **context), 502, "QUERY_TRANSLATION_FAILED")
    offered = {f["field"] for f in fake.seen[-1].context["fields"]}
    assert "updatedAt" not in offered and "createdAt" not in offered and relation in offered

    fake.script(
        "queryTranslation",
        _answer(
            world,
            [(relation, "notUnder", f"Webshop {tag}"), (relation, "under", f"Draft region {tag}")],
            not_expressed=[("changed last month", "A change set records no change times")],
        ),
    )
    answer = ok(_ask(world, **context))
    assert answer["applied"] is False
    assert answer["notExpressed"][0]["part"] == "changed last month"
    assert answer["filters"] == [
        {"field": relation, "operator": "notUnder", "value": web["id"]},
        {"field": relation, "operator": "under", "value": draft["id"]},
    ]
    # The region that exists only in the change set is not found live.
    live = ok(_ask(world))
    assert live["filters"] == [{"field": relation, "operator": "notUnder", "value": web["id"]}]
    assert [item["part"] for item in live["notExpressed"]] == [
        "changed last month",
        f'"Draft region {tag}"',
    ]
    # The list reads the change set: there the first record has a permit under the region.
    only = [answer["filters"][0]]
    assert _listed(world, tag, only) == {"none", "store"}
    assert _listed(world, tag, only, changeSetId=change_set["id"]) == {"store"}


@pytest.mark.journey("J54.8")
@pytest.mark.structures(*STRUCTURES)
def test_the_list_filters_by_records_under_an_ancestor_live_in_a_change_set_and_in_an_export(world):
    """Given records related to permits under two regions, when the list is filtered to those with
    some related record under a region, with none under it, and with both regions, then each is the
    records that hold; in a change set the same filters read the change set; an unknown condition or
    an empty record is refused INVALID_FILTER; and an export of the type with the same condition as
    a related hop holds exactly the records the list gives."""
    tag, web, store, permits, records = _scene(world)
    relation = _related(world)

    def under(operator, region):
        return {"field": relation, "operator": operator, "value": region["id"]}

    assert _listed(world, tag, [under("under", web)]) == {"web", "both"}
    assert _listed(world, tag, [under("notUnder", web)]) == {"none", "store"}
    assert _listed(world, tag, [under("under", web), under("under", store)]) == {"both"}
    assert _listed(world, tag, [under("notUnder", web), under("notUnder", store)]) == {"none"}
    assert _listed(world, tag, [under("under", web), under("notUnder", store)]) == {"web"}

    change_set = world.change_set(name=f"{tag} staged")
    ok(
        world.relate(
            "Bassoc",
            records["none"]["id"],
            permits["store"]["id"],
            changeSetId=change_set["id"],
            expectedChangeSetVersion=world.current(change_set)["version"],
        ),
        201,
    )
    context = {"changeSetId": change_set["id"]}
    assert _listed(world, tag, [under("notUnder", store)], **context) == {"web"}
    assert _listed(world, tag, [under("under", store)], **context) == {"none", "store", "both"}
    assert _listed(world, tag, [under("notUnder", store)]) == {"web", "none"}

    path = f"/objects/{world.key('R')}"
    refused(
        world.api.get(path, **{f"filter__{relation}__within": web["id"]}), 422, "INVALID_FILTER"
    )
    refused(world.api.get(path, **{f"filter__{relation}__under": " "}), 422, "INVALID_FILTER")

    hop = {
        "relationTypeKey": world.key("Bassoc"),
        "direction": "outgoing",
        "where": [{"field": f"ancestor:{world.key('G')}", "op": "eq", "value": web["id"]}],
    }
    job = _finished(
        world,
        W1,
        [{"objectTypeKey": world.key("R"), "where": [{"related": hop, "not": True}]}],
    )
    exported = {line["key"]["id"] for line in _lines(world, job) if line["op"] == "upsert"}
    listed = ok(
        world.api.get(
            path,
            pageSize=500,
            includeTotal="true",
            workspaceKey=W1,
            **{f"filter__{relation}__notUnder": web["id"]},
        )
    )
    assert exported == {item["id"] for item in listed["items"]}
    assert {records["none"]["id"], records["store"]["id"]} <= exported
    assert not {records["web"]["id"], records["both"]["id"]} & exported


def _names(world, tag, count):
    """Regions to make a list long, named with the tag."""
    for index in range(count):
        world.made("G", f"Region {index} {tag}")


def _field(world, relation=None):
    relation = relation or _related(world)
    return next(f for f in fake.seen[-1].context["fields"] if f["field"] == relation)


@pytest.mark.journey("J54.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="values")
def test_at_values_a_short_lists_names_are_sent_and_records_are_chosen_by_name(world):
    """Given records related to permits under two regions and a send level of values, when a
    question is asked, then the provider is sent the names of the permits and of the regions and no
    ID; when it answers with one eq filter per chosen permit, then the filters hold the permits' IDs
    and the list is exactly the records related to either of them; the call records the level."""
    tag, _web, _store, permits, _records = _scene(world)
    relation = _related(world)
    fake.script(
        "queryTranslation",
        _answer(
            world,
            [(relation, "eq", permits["web"]["name"]), (relation, "eq", permits["store"]["name"])],
        ),
    )
    answer = ok(_ask(world, "records with the first or the second permit"))
    sent = _field(world)
    assert (
        permits["web"]["name"] in sent["recordNames"]
        and permits["store"]["name"] in sent["recordNames"]
    )
    assert (
        f"Webshop {tag}" in sent["ancestorNames"] and f"Storefront {tag}" in sent["ancestorNames"]
    )
    assert permits["web"]["id"] not in json.dumps(fake.seen[-1].context)
    assert answer["applied"] is True
    assert {item["value"] for item in answer["filters"]} == {
        permits["web"]["id"],
        permits["store"]["id"],
    }
    assert _listed(world, tag, answer["filters"]) == {"web", "store", "both"}
    assert _last_call(world)["sendLevel"] == "values"


@pytest.mark.journey("J54.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="values")
def test_at_structure_and_for_a_long_list_no_name_is_sent(world):
    """Given a ceiling of values, when the request chooses structure, then no record name is sent
    and the call records structure; and when the types of a relationship hold more than 50 records,
    then none is sent at values either, while the relationship is still offered."""
    tag, *_ = _scene(world)
    ok(_ask(world, sendLevel="structure"))
    sent = _field(world)
    assert "recordNames" not in sent and "ancestorNames" not in sent
    assert tag not in json.dumps(fake.seen[-1].context)
    assert _last_call(world)["sendLevel"] == "structure"
    ok(_ask(world))
    assert "recordNames" in _field(world)
    _names(world, tag, 50)
    ok(_ask(world))
    sent = _field(world)
    assert "recordNames" not in sent and "ancestorNames" not in sent
    assert set(sent["conditions"]) == {"eq", "isNull", "under", "notUnder"}
    assert tag not in json.dumps(sent)


@pytest.mark.journey("J54.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_relationship_the_view_does_not_declare_can_be_asked_and_filtered(world):
    """Given a type with a relationship its list does not declare in filterFields, when a question
    needs it, then it is offered, a none-under answer is accepted and the list filtered by it is the
    records that hold, as with a declared one."""
    tag = uuid4().hex[:6]
    web, store = world.made("G", f"Webshop {tag}"), world.made("G", f"Storefront {tag}")
    owners = {name: world.made("R", f"{name} {tag}") for name in ("web", "store", "none")}
    for name, region in (("web", web), ("store", store)):
        world.made(
            "D",
            f"Permit {name} {tag}",
            parent=world.dependant_parent(region["id"]),
            values={"D.active": True},
            relations=[world.owner("Bown", owners[name]["id"])],
        )
    undeclared = f"related:{world.key('Bown')}"
    fake.script("queryTranslation", _answer(world, [(undeclared, "notUnder", f"Webshop {tag}")]))
    answer = ok(_ask(world, "records with a permit not under the webshop"))
    assert undeclared in {f["field"] for f in fake.seen[-1].context["fields"]}
    assert answer["applied"] is True and answer["filters"][0]["field"] == undeclared
    assert _listed(world, tag, answer["filters"]) == {"store", "none"}
