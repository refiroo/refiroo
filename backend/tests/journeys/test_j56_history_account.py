"""J56 — An account of what changed in a period (USER_JOURNEYS.md § What changed, 0.16 AO2).

A data owner picks a period on a workspace, or on one record's history, and asks for a short account.
The engine writes the facts in the database over every live change of the period (records, fields,
relationships, sources, people, change sets, withdrawals, model activations); the provider, the
deterministic fake, only words them, each statement citing the facts it rests on. Every case runs on
two configurations through the public API.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from scenario import W1, W2, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j05_j06_publish import _update_in
from test_j11_bulk_change import _batch
from test_j34_onboard import _all
from test_j40_authorization import _client
from test_j44_who_changed_what import IN_W1
from test_j51_agent_access import ON
from test_j52_assistant_reads import _answer, _reader, _refusal

from app.engine.proposals import fake
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"
STRUCTURES = ("R", "R.n", "K", "B1n", "R2")
FAR = timedelta(days=1)


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _now() -> datetime:
    return datetime.now(UTC)


def _account(world, since, until=None, path=None, **body):
    return world.api.post(
        path or f"/workspaces/{W1}/history/account",
        {
            "since": since.isoformat(),
            "until": (until or _now() + FAR).isoformat(),
            **body,
        },
    )


def _facts(answer, kind, **keys):
    return [
        fact
        for fact in answer["facts"]
        if fact["kind"] == kind and keys.items() <= fact["keys"].items()
    ]


def _one(answer, kind, **keys):
    (fact,) = _facts(answer, kind, **keys)
    return fact


def _last_call(world):
    return _all(world, "/ai/calls")[0]


def _period(world):
    """Seven records, then a period in which two are changed directly (one by another client), three
    renamed by a batch job, and a change set that changes one and adds one is published. Returns what
    the later cases need."""
    base = [world.made("R", f"Base {uuid4().hex[:6]}") for _ in range(7)]
    ana_name = f"Ana {uuid4().hex[:6]}"
    ana, as_ana = _client(world, ana_name, ("steward", IN_W1))
    since = _now()
    ok(world.update("R", base[0]["id"], base[0]["version"], values={"R.n": 11}))
    ok(as_ana.update("R", base[1]["id"], base[1]["version"], values={"R.n": 12}))
    items = [
        {
            "op": "update",
            "target": {"id": item["id"]},
            "expectedVersion": item["version"],
            "name": f"Job rename {number}",
        }
        for number, item in enumerate(base[2:5])
    ]
    job = ok(_batch(world, items))["job"]
    change_set = world.change_set(name=f"Spring work {uuid4().hex[:6]}")
    ok(_update_in(world, change_set, "R", base[5]["id"], values={"R.n": 5}))
    added = world.made("R", "Added in the set", change_set=world.current(change_set))
    publication = world.publish(change_set)
    return {
        "base": base,
        "since": since,
        "job": job,
        "ana": ana,
        "ana_name": ana_name,
        "change_set": change_set,
        "publication": publication,
        "added": added,
    }


@pytest.mark.journey("J56.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="values")
def test_the_account_counts_what_was_changed_by_type_field_and_source(world):
    """Given direct changes, a job and a change set published in the period, when a holder of Browse
    and Use AI proposals asks, then each statement cites facts, and the counts per type, field and
    source equal the counts of the changes made."""
    made = _period(world)
    answer = ok(_account(world, made["since"]))
    ids = {fact["id"] for fact in answer["facts"]}
    assert answer["statements"] and answer["failure"] is None and answer["cached"] is False
    assert all(item["factIds"] and set(item["factIds"]) <= ids for item in answer["statements"])
    type_key = world.key("R")
    # Two direct, three by the job and one published; one record added by the publication.
    assert _one(answer, "records", objectTypeKey=type_key, action="updated")["count"] == 6
    assert _one(answer, "records", objectTypeKey=type_key, action="created")["count"] == 1
    attribute = world.key("R.n")
    assert _one(answer, "fields", objectTypeKey=type_key, attributeTypeKey=attribute)["count"] == 3
    direct = _one(answer, "source", causeKind="direct")
    job = _one(answer, "source", causeKind="job", causeId=made["job"]["id"])
    published = _one(answer, "source", causeKind="publication")
    assert (direct["count"], job["count"], published["count"]) == (2, 3, 2)
    assert published["keys"]["causeId"] == made["publication"]["id"]
    (people,) = _facts(answer, "people")
    counts = {item["id"]: item["changes"] for item in people["keys"]["people"]}
    assert counts[made["ana"]["id"]] == 1 and sum(counts.values()) == 2 + 3 + 2
    assert made["ana_name"] in people["text"]
    assert _last_call(world)["purpose"] == "historyAccount"
    assert _last_call(world)["id"] == answer["callId"]


@pytest.mark.journey("J56.2")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_record_staged_then_published_counts_once_and_an_open_set_is_only_its_events(world):
    """Given a record changed in a change set that is published, and another record changed in a set
    left open, when the account is asked, then the published record counts once (its field once),
    the open set's edit is not counted and its creation is a change set fact."""
    first, second = (world.made("R", f"Staged {uuid4().hex[:6]}") for _ in range(2))
    since = _now()
    done = world.change_set(name="Published set")
    ok(_update_in(world, done, "R", first["id"], values={"R.n": 1}))
    ok(_update_in(world, done, "R", first["id"], values={"R.n": 2}))
    world.publish(done)
    open_name = f"Left open {uuid4().hex[:6]}"
    left = world.change_set(name=open_name)
    ok(_update_in(world, left, "R", second["id"], values={"R.n": 9}))
    answer = ok(_account(world, since))
    type_key = world.key("R")
    assert _one(answer, "records", objectTypeKey=type_key, action="updated")["count"] == 1
    assert (
        _one(answer, "fields", objectTypeKey=type_key, attributeTypeKey=world.key("R.n"))["count"]
        == 1
    )
    sets = {fact["keys"]["changeSetId"]: fact for fact in _facts(answer, "changeSet")}
    assert left["id"] in sets and open_name in sets[left["id"]]["text"]
    assert sets[left["id"]]["keys"]["events"][0]["action"] == "created"


@pytest.mark.journey("J56.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_publication_names_the_job_and_the_people_who_prepared_it_and_who_published(world):
    """Given a change set loaded by a job, edited by a second person and published by a third, when
    the account is asked, then the source fact of the publication names the job and the two who
    prepared it, and the publisher."""
    records = [world.made("R", f"Prepared {uuid4().hex[:6]}") for _ in range(3)]
    tag = uuid4().hex[:6]
    editor, as_editor = _client(world, f"Editor {tag}", ("steward", IN_W1))
    publisher, as_publisher = _client(world, f"Publisher {tag}", ("steward", IN_W1))
    since = _now()
    change_set = world.change_set(name=f"Loaded {tag}")
    items = [
        {
            "op": "update",
            "target": {"id": item["id"]},
            "expectedVersion": item["version"],
            "name": f"Loaded {number} {tag}",
        }
        for number, item in enumerate(records[:2])
    ]
    job = ok(
        _batch(
            world,
            items,
            context={"changeSetId": change_set["id"]},
            expectedChangeSetVersion=change_set["version"],
        )
    )["job"]
    ok(_update_in(as_editor, change_set, "R", records[2]["id"], values={"R.n": 4}))
    publication = as_publisher.publish(change_set)
    answer = ok(_account(world, since))
    source = _one(answer, "source", causeKind="publication")
    keys = source["keys"]
    requester = ok(world.api.get(f"/jobs/{job['id']}"))["requestedBy"]
    assert keys["causeId"] == publication["id"] and keys["jobIds"] == [job["id"]]
    assert set(keys["preparedBy"]) == {requester["id"], editor["id"]}
    assert keys["publishedBy"] == publisher["id"]
    for name in (editor["name"], publisher["name"]):
        assert name in source["text"]
    assert source["count"] == 3


@pytest.mark.journey("J56.4")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_records_account_holds_its_values_relationships_and_moves_and_no_other_records(world):
    """Given a record whose value changed twice, that gained a relationship, and a child that moved,
    and another record changed in the same period, when the account of each is asked, then the
    record's facts count its own changes only."""
    record, other, token = (world.made(s, f"{s} {uuid4().hex[:6]}") for s in ("R", "R", "K"))
    parent, elsewhere = (world.made("R", f"Parent {uuid4().hex[:6]}") for _ in range(2))
    child = world.made("R2", f"Child {uuid4().hex[:6]}", parent=parent["id"])
    since = _now()
    current = ok(world.update("R", record["id"], record["version"], values={"R.n": 1}))
    ok(world.update("R", record["id"], current["version"], values={"R.n": 2}))
    ok(world.relate("B1n", record["id"], token["id"]), 201)
    ok(world.update("R", other["id"], other["version"], values={"R.n": 7}))
    ok(world.update("R2", child["id"], child["version"], parent=elsewhere["id"]))
    path = f"/objects/{world.key('R')}/{record['id']}/history/account"
    answer = ok(_account(world, since, path=path))
    assert answer["scope"] == "record"
    assert _one(answer, "fields", attributeTypeKey=world.key("R.n"))["count"] == 2
    relation = _one(answer, "relationships", relationTypeKey=world.key("B1n"), action="created")
    assert relation["count"] == 1
    assert not _facts(answer, "records", action="moved")
    assert _one(answer, "records", action="updated")["count"] == 2
    assert all(fact["kind"] != "changeSet" for fact in answer["facts"])
    moved = ok(
        _account(world, since, path=f"/objects/{world.key('R2')}/{child['id']}/history/account")
    )
    assert _one(moved, "records", action="moved")["count"] == 1
    assert ok(_account(world, since, path=path, timeZone="Europe/Prague"))["facts"]


@pytest.mark.journey("J56.5")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="values")
def test_names_reach_the_provider_only_at_values_and_as_data(world):
    """Given a period with a planted record name, person, change set and file name, when the account
    is asked at `structure`, then none of them is in what the provider receives, though the facts
    hold the person's, change set's and file's names; at `values` they are, as data."""
    tag = uuid4().hex[:8]
    record_name = f"Record-{tag}"
    person, as_person = _client(world, f"Person-{tag}", ("steward", IN_W1))
    record = world.made("R", f"Pre {tag}")
    since = _now()
    ok(as_person.update("R", record["id"], record["version"], name=record_name))
    change_set = world.change_set(name=f"Set-{tag}")
    job = ok(
        _batch(
            world,
            [
                {
                    "op": "update",
                    "target": {"id": record["id"]},
                    "expectedVersion": record["version"] + 1,
                    "name": f"Again-{tag}",
                }
            ],
        )
    )["job"]
    # An import keeps the name of its file in its parameters; a batch has none, so it is written as
    # an import's job would hold it (state that arrives from outside the API).
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE jobs SET parameters = jsonb_set(parameters::jsonb, '{file}', :f)::json WHERE id = :i"
            ),
            {"f": json.dumps({"name": f"File-{tag}.xlsx"}), "i": job["id"]},
        )
    engine.dispose()
    planted = (person["name"], f"Set-{tag}", f"File-{tag}", f"Again-{tag}", record_name)

    answer = ok(_account(world, since, sendLevel="structure"))
    sent = json.dumps(fake.seen[-1].context)
    assert not [name for name in planted if name in sent]
    shown = json.dumps(answer["facts"])
    assert person["name"] in shown and f"Set-{tag}" in shown and f"File-{tag}" in shown

    fake.reset()
    ok(_account(world, since, sendLevel="values", language="de"))
    sent = fake.seen[-1].context
    data = json.dumps([fact.get("data") for fact in sent["facts"]])
    assert person["name"] in data and f"Set-{tag}" in data and f"File-{tag}" in data
    assert all(name not in json.dumps([f["text"] for f in sent["facts"]]) for name in planted)
    assert "data" in fake.seen[-1].instructions and change_set["id"] not in json.dumps(sent)


@pytest.mark.journey("J56.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_period_includes_its_start_excludes_its_end_and_reads_days_in_the_time_zone(world):
    """Given one change, when the account is asked from its moment, it holds it; until its moment, it
    does not; a day boundary is read in the given time zone; a reversed period or an unknown time
    zone is 422 HISTORY_PERIOD_INVALID; an empty period gives no facts and no call."""
    record = world.made("R", f"Timed {uuid4().hex[:6]}")
    items = [
        {
            "op": "update",
            "target": {"id": record["id"]},
            "expectedVersion": record["version"],
            "name": "Timed again",
        }
    ]
    job = ok(_batch(world, items))["job"]
    entry = ok(world.api.get("/changes", workspaceKey=W1, kind="record", pageSize=1))["items"][0]
    moment = datetime.fromisoformat(entry["occurredAt"])
    inside = ok(_account(world, moment, moment + timedelta(seconds=1)))
    assert _facts(inside, "records", action="updated")
    before = ok(_account(world, moment - timedelta(seconds=1), moment))
    assert not _facts(before, "records", action="updated")
    fake.reset()
    empty = ok(_account(world, moment - timedelta(days=3), moment - timedelta(days=2)))
    assert empty["facts"] == [] and empty["statements"] == [] and fake.seen == []
    for zone in ("Pacific/Kiritimati", "Pacific/Pago_Pago"):
        local = moment.astimezone(ZoneInfo(zone))
        answer = ok(_account(world, moment, moment + timedelta(seconds=1), timeZone=zone))
        source = _one(answer, "source", causeKind="job", causeId=job["id"])
        assert f"{local:%A} {local.day} {local:%b}" in source["text"]
    reversed_period = _account(world, moment, moment - timedelta(seconds=1))
    refused(reversed_period, 422, "HISTORY_PERIOD_INVALID")
    refused(_account(world, moment, moment), 422, "HISTORY_PERIOD_INVALID")
    refused(_account(world, moment, timeZone="Mars/Olympus"), 422, "HISTORY_PERIOD_INVALID")


@pytest.mark.journey("J56.7")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_every_fact_reaches_the_person_forty_a_kind_the_provider_and_show_them_equals_the_fact(
    world,
):
    """Given more than 40 change sets in the period, the response holds a fact for each, the provider
    40 with the true total; and the narrowing a fact links to, read through GET /changes, returns
    exactly what the fact counted."""
    made = _period(world)
    for number in range(44):
        world.change_set(name=f"Many {number}")
    fake.script(
        "historyAccount",
        lambda context: {"statements": [{"text": "More sets.", "factIds": ["more-changeSet"]}]},
    )
    answer = ok(_account(world, made["since"]))
    sets = _facts(answer, "changeSet")
    assert len(sets) >= 45
    context = fake.seen[-1].context
    assert len([f for f in context["facts"] if f["kind"] == "changeSet"]) == 40
    assert context["totals"]["changeSet"] == len(sets)
    assert context["more"][0]["id"] == "more-changeSet"
    assert answer["statements"][0]["factIds"] == ["more-changeSet"]
    linked = [fact for fact in answer["facts"] if (fact["link"] or {}).get("kind") == "changes"]
    assert {fact["kind"] for fact in linked} >= {"records", "fields", "source"}
    for fact in linked:
        query = {**fact["link"]["query"], "workspaceKey": W1, "pageSize": 500}
        query.update(since=made["since"].isoformat(), until=answer["until"])
        listed = ok(world.api.get("/changes", **query))["items"]
        assert len(listed) == fact["count"], fact["text"]
        if fact["kind"] == "records":
            assert {item["action"] for item in listed} == {fact["keys"]["action"]}


@pytest.mark.journey("J56.8")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_uncited_statements_are_dropped_a_failure_leaves_the_facts_and_the_same_facts_are_cached(
    world,
):
    """As J55.4 to J55.6: an uncited statement is dropped and counted, a failing provider is a 200
    with the facts and a failed call and no transaction held, and a second request is cached."""
    made = _period(world)
    until = _now() + FAR
    fake.script(
        "historyAccount",
        lambda context: {
            "statements": [
                {"text": "Cited.", "factIds": [context["facts"][0]["id"]]},
                {"text": "Unknown.", "factIds": ["re-00000000"]},
                {"text": "Uncited.", "factIds": []},
            ]
        },
    )
    answer = ok(_account(world, made["since"], until))
    assert [item["text"] for item in answer["statements"]] == ["Cited."]
    assert answer["removedStatements"] == 2 and answer["facts"]
    again = ok(_account(world, made["since"], until))
    assert again["cached"] is True and again["callId"] == answer["callId"] and len(fake.seen) == 1

    idle = []
    engine = create_engine(world.database, poolclass=NullPool)

    def failing(context):
        with engine.connect() as connection:
            idle.append(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                        " AND state = 'idle in transaction' AND pid <> pg_backend_pid()"
                    )
                )
            )
        raise ProviderError("unreachable", "The provider could not be reached")

    fake.script("historyAccount", failing)
    failed = ok(_account(world, made["since"], language="fr"))
    engine.dispose()
    assert idle == [0] and failed["statements"] == [] and failed["facts"] == answer["facts"]
    assert failed["failure"] == "The provider could not be reached"
    assert (_last_call(world)["outcome"], _last_call(world)["id"]) == ("failed", failed["callId"])
    fake.script("historyAccount", {"statements": "none"})
    assert ok(_account(world, made["since"], language="it"))["failure"]


def _audit_entries(world) -> int:
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.connect() as connection:
        count = connection.scalar(text("SELECT count(*) FROM audit_events"))
    engine.dispose()
    return count


@pytest.mark.journey("J56.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_only_those_who_may_browse_and_use_ai_proposals_may_ask(world):
    """Given a client with Browse only, one with Use AI proposals only, and one with both, when they
    ask, then the first two are refused 403 naming the missing group, the third is answered; a level
    above the ceiling is 409 AI_SEND_LEVEL_TOO_LOW; asking changes no record and adds no audit entry.
    (The tool is the next case: an assistant's token is cut to Browse and Work in change sets.)"""
    record = world.made("R", f"Asked {uuid4().hex[:6]}")
    since = _now()
    ok(world.update("R", record["id"], record["version"], values={"R.n": 3}))
    roles = {
        name: ok(world.api.post("/roles", {"name": name, "actionGroups": groups}), 201)
        for name, groups in (
            ("Readers", ["browse"]),
            ("Askers", ["ai-proposals"]),
            ("Both", ["browse", "ai-proposals"]),
        )
    }
    clients = {name: _client(world, name, (role["key"], IN_W1))[1] for name, role in roles.items()}
    error = refused(_account(clients["Readers"], since), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["ai-proposals"]
    refused(_account(clients["Askers"], since), 403, "FORBIDDEN")
    assert fake.seen == []
    entries = _audit_entries(world)
    answer = ok(_account(clients["Both"], since))
    assert answer["facts"] and _audit_entries(world) == entries
    path = f"/objects/{world.key('R')}/{record['id']}/history/account"
    assert ok(_account(clients["Both"], since, path=path))["facts"]
    error = refused(_account(world, since, sendLevel="values"), 409, "AI_SEND_LEVEL_TOO_LOW")
    assert error["details"] == {"sendLevel": "values", "ceiling": "structure"}


@pytest.mark.journey("J56.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(**ON, AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_an_assistant_reads_the_facts_with_browse_and_no_provider_call(world):
    """Given an assistant with Browse, when it asks history_facts, then the tool is offered, the
    facts are the route's for the same period (workspace and record), no provider is called and no
    audit entry or call row is added; a workspace it cannot read, a missing record and a reversed
    period are refused as the route refuses them."""
    from test_j51_agent_access import _tools

    made = _period(world)
    record = made["base"][0]
    token = _reader(world)
    assert "history_facts" in _tools(world, token)
    until = _now() + FAR
    window = {"since": made["since"].isoformat(), "until": until.isoformat()}
    calls, entries = len(_all(world, "/ai/calls")), _audit_entries(world)

    facts = _answer(world, token, "history_facts", workspace=W1, **window)
    one = _answer(
        world, token, "history_facts", workspace=W1, objectType=world.key("R"), id=record["id"],
        timeZone="Europe/Budapest", **window,
    )  # fmt: skip
    closed = _refusal(world, token, "history_facts", workspace=W2, **window)
    assert closed == f"WORKSPACE_NOT_FOUND: Workspace '{W2}' not found"
    assert "OBJECT_NOT_FOUND" in _refusal(
        world, token, "history_facts", workspace=W1, objectType=world.key("R"), id="nope", **window
    )
    assert "HISTORY_PERIOD_INVALID" in _refusal(
        world, token, "history_facts", workspace=W1, since=window["until"], until=window["since"]
    )
    assert "HISTORY_PERIOD_INVALID" in _refusal(
        world, token, "history_facts", workspace=W1, timeZone="Mars/Base", **window
    )
    assert fake.seen == []
    assert (len(_all(world, "/ai/calls")), _audit_entries(world)) == (calls, entries)

    route = ok(_account(world, made["since"], until))
    # The assistant's reader may not see the batch job, so its fact has no link to it (R-F15).
    unlinked = [
        {**fact, "link": None} if (fact["link"] or {}).get("kind") == "job" else fact
        for fact in route["facts"]
    ]
    assert facts["scope"] == "workspace" and facts["facts"] == unlinked != []
    assert {key: facts[key] for key in ("since", "until", "timeZone")} == {
        key: route[key] for key in ("since", "until", "timeZone")
    }
    path = f"/objects/{world.key('R')}/{record['id']}/history/account"
    route_one = ok(_account(world, made["since"], until, path=path, timeZone="Europe/Budapest"))
    assert one["scope"] == "record" and one["facts"] == route_one["facts"] != []
    assert one["timeZone"] == "Europe/Budapest"


@pytest.mark.journey("J56.9")
@pytest.mark.structures(*STRUCTURES)
def test_without_a_provider_the_account_is_refused(world):
    """Given no provider, then asking is 409 AI_NOT_CONFIGURED."""
    refused(_account(world, _now() - timedelta(days=1)), 409, "AI_NOT_CONFIGURED")


@pytest.mark.journey("J56.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_withdrawal_and_each_model_activation_are_facts_of_their_own(world):
    """Given a publication withdrawn and a model activated, then activated back and again in the
    period, when the account is asked, then the withdrawal is a publication fact, and each activation
    is a model fact with an ID of its own, the same release activated twice included."""
    first = world.workspace_model()["releaseId"]
    model, _key = world.candidate("compatible")
    second = world.install(model)["id"]
    since = _now()
    world.made("R", f"Withdrawn {uuid4().hex[:6]}")
    publication = world.publish(world.change_set())
    assert world.api.post(f"/publications/{publication['id']}/withdrawal").status_code == 204
    for release in (second, first, second):
        ok(world.activate(release))
    answer = ok(_account(world, since))
    withdrawal = _one(answer, "publication", publicationId=publication["id"])
    assert "withdrawn" in withdrawal["text"]
    models = _facts(answer, "model")
    assert [(f["keys"]["oldReleaseId"], f["keys"]["newReleaseId"]) for f in models] == [
        (first, second),
        (second, first),
        (first, second),
    ]
    assert len({fact["id"] for fact in models}) == 3


@pytest.mark.journey("J56.9")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_reader_who_may_not_see_a_job_is_told_neither_its_file_nor_given_its_link(world):
    """Given a job that kept the name of its file, when a holder of Browse and Use AI proposals
    only asks, then the job is "Batch job" with no file and no link; the person who may see the
    job reads its file and a link to it."""
    record = world.made("R", f"Filed {uuid4().hex[:6]}")
    since = _now()
    items = [
        {
            "op": "update",
            "target": {"id": record["id"]},
            "expectedVersion": record["version"],
            "name": "Filed again",
        }
    ]
    job = ok(_batch(world, items))["job"]
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE jobs SET parameters = jsonb_set(parameters::jsonb, '{file}', :f)::json "
                "WHERE id = :i"
            ),
            {"f": json.dumps({"name": "Private-file.xlsx"}), "i": job["id"]},
        )
    engine.dispose()
    role = ok(
        world.api.post(
            "/roles", {"name": "Account readers", "actionGroups": ["browse", "ai-proposals"]}
        ),
        201,
    )
    reader = _client(world, "Account reader", (role["key"], IN_W1))[1]

    seen = _one(ok(_account(world, since)), "source", causeKind="job", causeId=job["id"])
    assert "Private-file.xlsx" in seen["text"] and (seen["link"]["kind"], seen["link"]["id"]) == (
        "job",
        job["id"],
    )
    hidden = _one(ok(_account(reader, since)), "source", causeKind="job", causeId=job["id"])
    assert "Private-file" not in json.dumps(hidden) and hidden["link"] is None
    assert hidden["text"].startswith("Batch job")
