"""The ``ai`` area of the management API's reference, recorded from a run on the guide's reference data (see
``test_reference_recording.py``, whose seed, scenario and normaliser this file uses).

The administrator of the Graubünden instance reads how the AI provider is set up, tests it, and asks it
for the four things a provider does: the filters a question in words means on a list, an account of what
activating a model draft and a release would do, and an account of what changed in the workspace and
in one stop. The provider is the harness's deterministic fake (``app.engine.proposals.fake``, which
records what it was sent), never a real one: nothing leaves the process and no key is set. The calls are
read at the end, with their content, which shows what a provider is sent.

An assistant task is given to the assistant: a request in words on the workspace's records. The
assistant runs Claude Code in service. Here it is a stand-in session (a script the harness writes, as
the journeys' stand-ins are) that works through the API with the token the engine gives it, so every
permission and refusal is the engine's; it writes the proposal a session would. The task is followed
from its reading to the change set the load made, and one more is ended. What a task does with a
workbook (its reading per table, its check per sheet and the records a check would change) needs a
session that designs against a workbook: those answers are described in the text and not recorded.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_ai.py -q
"""

import json
import os
import socket
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import seeds
import uvicorn
from test_reference_jobs import BUS_STOPS, WORKBOOK, _upload
from test_reference_jobs import _wait as _wait_job
from test_reference_recording import (
    BASE,
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)
from test_reference_records import _one

from app.engine.proposals import fake

WS = {"workspace_key": "graubuenden"}
DRAFT = "/api/v1/model-drafts/{draft_id}"
RELEASE = "/api/v1/model-releases/{release_id}"
SESSION = [
    (
        "The assistant is the harness's stand-in session, a script that works through the API; "
        "in service Claude Code runs it. The answer is the engine's."
    )
]
SAVED = [
    "A saved layout read the workbook, so no assistant session ran; the answers are the engine's."
]
TASKS = "/api/v1/ai/tasks"
TASK = "/api/v1/ai/tasks/{task_id}"
SETTINGS = {
    "AI_PROVIDER": "app.engine.proposals.fake:provider",
    "AI_LOG_CONTENT": "true",
    "AI_SEND_LEVEL": "values",
    "MODEL_ADMIN_MUTATIONS_ENABLED": "true",
}

STAND_IN = """#!/usr/bin/env python3
import json, os, sys
folder = os.path.dirname(os.path.realpath(__file__))
config = json.load(open(os.path.join(folder, "config.json")))
prompt = sys.argv[sys.argv.index("--") + 1]
open(config["log"], "a").write(json.dumps({"prompt": prompt, "args": sys.argv[1:]}) + "\\n")
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "input": {"command": "curl -X POST x/api/v1/change-sets"}}]}}))
if os.path.exists(os.path.join(folder, "hold")):
    open(os.path.join(folder, "holding"), "w").write("1")
    import time
    time.sleep(600)
if config.get("fail"):
    print(json.dumps({"type": "result", "result": "I could not work this out."}))
    sys.exit(0)
if "accepted" in prompt:
    import httpx
    base = config["url"] + "/api/v1"
    head = {"Authorization": "Bearer " + os.environ["REFIROO_TOKEN"]}
    def api(method, path, **kw):
        sent = httpx.request(method, base + path, headers=head, timeout=60, **kw)
        assert sent.status_code < 300, (method, path, sent.status_code, sent.text)
        return sent.json()
    try:
        made = api("POST", "/workspaces/" + config["workspace"] + "/change-sets",
                   json={"name": config["name"], "source": "currentLive"})
        api("POST", "/batches", json={
            "changeSetId": made["id"], "expectedChangeSetVersion": made["version"],
            "policy": "independent", "run": "inline", "items": config["batch"]})
    except BaseException as error:
        open(config["log"], "a").write(json.dumps({"error": repr(error)}) + "\\n")
        raise
    print(json.dumps({"type": "result", "result": "Done.\\nCHANGE_SET: " + made["id"]}))
else:
    json.dump(config["proposal"], open("proposal.json", "w"))
    print(json.dumps({"type": "result", "result": "Ready."}))
"""


def _serve(app: Any) -> Iterator[str]:
    """The application over HTTP on a free local port for the stand-in session, which reaches the API as
    a client does; it stops with the run."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_level="warning",
            timeout_graceful_shutdown=2,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the local server did not start"
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)


class Assistant:
    """The stand-in session's command and what it reads: ``config.json`` in its folder."""

    def __init__(self, folder: Path, url: str) -> None:
        self.folder = folder
        self.script = folder / "stand_in.py"
        self.script.write_text(STAND_IN)
        self.script.chmod(0o755)
        self.config: dict[str, Any] = {"log": str(folder / "log.jsonl"), "url": url}

    def says(self, **changes: Any) -> None:
        self.config.update(changes)
        (self.folder / "config.json").write_text(json.dumps(self.config))

    def prompts(self) -> list[str]:
        path = self.folder / "log.jsonl"
        return [json.loads(line)["prompt"] for line in path.read_text().splitlines()]


@pytest.fixture(scope="module")
def ai(tmp_path_factory) -> Iterator[tuple[Scenario, Assistant]]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    folder = tmp_path_factory.mktemp("assistant")
    script = folder / "stand_in.py"
    wanted = {**SETTINGS, "AI_AGENT_COMMAND": str(script)}
    saved = {key: os.environ.get(key) for key in (*wanted, "AI_AGENT_API_URL")}
    os.environ.update(wanted)
    fake.reset()
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            for address in _serve(client.app):
                os.environ["AI_AGENT_API_URL"] = address
                yield scenario, Assistant(folder, address)
            if RECORDING:
                scenario.write_examples()
    finally:
        fake.reset()
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        seeds.drop(url.database)


def _wait(s: Scenario, task_id: str, *states: str, seconds: float = 120) -> dict:
    deadline = time.monotonic() + seconds
    while True:
        task = s.call("GET", TASK, path={"task_id": task_id}, status=200)
        if task["state"] in states:
            return task
        assert time.monotonic() < deadline, task
        time.sleep(0.25)


def test_the_administrator_reads_the_provider_and_asks_it_for_words(ai):
    s, _ = ai
    status = s.call(
        "GET",
        "/api/v1/ai/status",
        status=200,
    )
    assert status["configured"] is True and status["keySet"] is False
    assert status["sendLevel"] == "values" and status["assistant"] is True
    tested = s.call(
        "POST",
        "/api/v1/ai/test",
        status=200,
        record="connection",
        summary="A fixed request that holds no data: the call it made, answered",
    )
    assert tested["outcome"] == "answered" and tested["purpose"] == "connectionTest"

    # What a question means on a list: the filters it became, or the parts that cannot be expressed.
    asked = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/query-translations",
        path=WS,
        body={
            "applicationKey": "network",
            "viewKey": "stops",
            "question": "stops with Post in the name",
        },
        status=200,
        record="stops",
        summary="A question in words on the stops list, at the instance's send level",
    )
    assert asked["applied"] is True
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/query-translations",
        path=WS,
        body={
            "applicationKey": "network",
            "viewKey": "stops",
            "question": "stops with Post in the name",
            "sendLevel": "structure",
        },
        status=200,
    )
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/query-translations",
        path=WS,
        body={
            "applicationKey": "network",
            "viewKey": "geography",
            "question": "anything",
        },
        status=422,
        code="QUERY_TRANSLATION_VIEW_UNSUPPORTED",
    )
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/query-translations",
        path=WS,
        body={"applicationKey": "network", "viewKey": "no-such", "question": "x"},
        status=404,
        code="VIEW_NOT_FOUND",
    )

    # A live change for the accounts to count.
    zuoz = _one(s, "municipality", "Zuoz")
    stop = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": zuoz["id"], "sort": "name", "pageSize": 1},
        status=200,
    )["items"][0]
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    s.call(
        "PATCH",
        "/api/v1/objects/{object_type_key}/{object_id}",
        path={"object_type_key": "stop", "object_id": stop["id"]},
        body={"name": stop["name"] + " (Post)", "expectedVersion": stop["version"]},
        status=200,
    )
    until = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    account = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/history/account",
        path=WS,
        body={"since": since, "until": until, "timeZone": "Europe/Zurich"},
        status=200,
        record="today",
        summary="What changed in the workspace over a period: the facts the engine counted and the words for them",
    )
    assert account["facts"] and account["statements"] and account["cached"] is False
    again = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/history/account",
        path=WS,
        body={"since": since, "until": until, "timeZone": "Europe/Zurich"},
        status=200,
    )
    assert again["cached"] is True
    # At the lowest send level the facts go as counts and labels: no record, person or file name.
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/history/account",
        path=WS,
        body={"since": since, "until": until, "sendLevel": "structure"},
        status=200,
    )
    accounts = [r.context for r in fake.seen if r.purpose == "historyAccount"]
    assert "Test harness person" in json.dumps(accounts[0]) and '"data"' in json.dumps(accounts[0])
    assert "Test harness person" not in json.dumps(accounts[-1])
    assert '"data"' not in json.dumps(accounts[-1])
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/history/account",
        path=WS,
        body={"since": until, "until": since},
        status=422,
        code="HISTORY_PERIOD_INVALID",
    )
    s.call(
        "POST",
        "/api/v1/objects/{object_type_key}/{object_id}/history/account",
        path={"object_type_key": "stop", "object_id": stop["id"]},
        body={"since": since, "until": until, "language": "de"},
        status=200,
        record="oneStop",
        summary="The same for one stop's own changes, worded in German",
    )

    # A step in a draft of the model, and what installing it as a release would do.
    draft = s.call("POST", "/api/v1/workspaces/{workspace_key}/model/draft", path=WS, status=201)
    step = s.call(
        "POST",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        body={
            "expectedVersion": draft["version"],
            "operations": [
                {
                    "kind": "addAttributeType",
                    "key": "step-free",
                    "name": "Step-free access",
                    "valueType": "boolean",
                },
                {"kind": "attachAttribute", "objectType": "stop", "attributeType": "step-free"},
                {"kind": "setRelease", "version": "1.9.0"},
            ],
        },
        status=200,
    )
    summary = s.call(
        "POST",
        DRAFT + "/impact-summary",
        path={"draft_id": draft["id"]},
        body={"workspaceKey": "graubuenden", "expectedVersion": step["version"]},
        status=200,
        record="graubuenden",
        summary="What activating the draft would do in the workspace, in the engine's facts and words",
    )
    assert summary["facts"] and summary["failure"] is None
    s.call(
        "POST",
        DRAFT + "/impact-summary",
        path={"draft_id": draft["id"]},
        body={"workspaceKey": "graubuenden", "expectedVersion": step["version"] + 5},
        status=409,
        code="VERSION_CONFLICT",
    )
    release = s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": step["version"]},
        status=201,
    )
    s.call(
        "POST",
        RELEASE + "/impact-summary",
        path={"release_id": release["id"]},
        body={"workspaceKey": "graubuenden", "sendLevel": "structure"},
        status=200,
        record="secondRelease",
        summary="The same for an installed release, at the lowest send level",
    )

    # A workspace that does not exist, and a release or record that does not.
    for route, path, body in (
        (RELEASE + "/impact-summary", {"release_id": release["id"]}, {"workspaceKey": "nothing"}),
        (
            "/api/v1/workspaces/{workspace_key}/query-translations",
            {"workspace_key": "nothing"},
            {"applicationKey": "network", "viewKey": "stops", "question": "x"},
        ),
    ):
        got = s.client.post(
            route.format(**path), json=body, headers={"Authorization": "Bearer " + s.api.token}
        )
        assert got.status_code == 404 and got.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"
    # What the provider was sent is read from the calls, with their content.
    page = s.call(
        "GET",
        "/api/v1/ai/calls",
        query={"pageSize": 3},
        status=200,
        record="newest",
        summary="The calls to the provider, newest first, with what was sent and answered",
    )
    s.call(
        "GET",
        "/api/v1/ai/status",
        status=200,
        record="fakeProvider",
        summary="How the provider is set up, what each feature needs sent, the last call and the totals of the last 30 days",
    )
    assert page["items"][0]["purpose"] == "impactSummary"
    assert page["items"][0]["content"] is not None
    # The fake keeps what it was sent: a send level of structure holds no record name.
    sent = [r for r in fake.seen if r.purpose == "queryTranslation"]
    assert len(sent) == 2
    assert "Davos" not in json.dumps(sent[1].context)
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/query-translations",
        path=WS,
        body={
            "applicationKey": "network",
            "viewKey": "stops",
            "question": "x",
            "sendLevel": "values",
        },
        status=200,
    )


def _give(
    s: Scenario,
    request: dict,
    *,
    status: int,
    record: str | None = None,
    summary: str = "",
    code: str | None = None,
) -> dict:
    """A task given as the form the operation takes: the ``request`` part alone, with no file. The
    example records the answer and names the part in its notes, since the document shows a JSON body only."""
    response = s.client.post(
        TASKS,
        data={"request": json.dumps(request)},
        headers={"Origin": BASE, "Authorization": "Bearer " + s.api.token},
    )
    out = response.json() if response.content else None
    assert response.status_code == status, (
        f"POST {TASKS}: {response.status_code} {response.text[:600]}"
    )
    if code is not None:
        assert out["error"]["code"] == code, out
    if record:
        shown = [
            f"The request part: `{json.dumps(request)}`.",
            "No file part: the words are the instruction.",
        ]
        s._record("POST", TASKS, record, summary, {}, {}, None, status, out, shown)
        if RECORDING:
            time.sleep(1.1)
    return out


def _run_to(s: Scenario, task: dict, *states: str) -> dict:
    return _wait(s, task["id"], *states)


def test_an_assistant_task_is_given_answered_accepted_and_loaded(ai):
    s, assistant = ai
    davos = _one(s, "municipality", "Davos")
    stop = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": davos["id"], "sort": "name", "pageSize": 1},
        status=200,
    )["items"][0]
    assistant.says(
        workspace="graubuenden",
        name="Davos stop names",
        proposal={
            "draftId": None,
            "title": "Add Bahnhof to a Davos stop's name",
            "summary": "One Davos stop's name gets the word Bahnhof.",
            "questions": [
                {
                    "text": "Should the stop keep its abbreviation?",
                    "options": ["Yes", "No"],
                    "assumed": "Yes",
                }
            ],
        },
        batch=[
            {
                "op": "update",
                "target": {"id": stop["id"]},
                "expectedVersion": stop["version"],
                "name": stop["name"] + " Bahnhof",
            }
        ],
    )
    _give(s, {"workspaceKey": "graubuenden"}, status=422, code="AI_TASK_NEEDS_WORDS")
    _give(
        s,
        {"workspaceKey": "graubuenden", "words": "x", "sendLevel": "structure"},
        status=409,
        code="AI_SEND_LEVEL_TOO_LOW",
    )
    started = _give(
        s,
        {
            "workspaceKey": "graubuenden",
            "words": f"Add Bahnhof to the name of the stop {stop['name']}",
        },
        status=202,
    )
    assert started["state"] in ("reading", "checking")
    task = _wait(s, started["id"], "checked", "failed")
    assert task["state"] == "checked" and task["design"]["modelUnchanged"] is True
    where = {"task_id": task["id"]}
    s.call(
        "GET",
        TASK,
        path=where,
        status=200,
    )
    s.call(
        "GET",
        TASK + "/changes",
        path=where,
        status=409,
        code="AI_TASK_STATE",
    )
    s.call(
        "POST",
        TASK + "/run",
        path=where,
        body={"expectedVersion": task["version"]},
        status=409,
        code="AI_TASK_NOTHING_TO_LOAD",
    )
    s.call(
        "POST",
        TASK + "/answers",
        path=where,
        body={"expectedVersion": task["version"] - 1, "answers": {"x": "y"}},
        status=409,
        code="VERSION_CONFLICT",
    )
    answered = s.call(
        "POST",
        TASK + "/answers",
        path=where,
        body={
            "expectedVersion": task["version"],
            "answers": {"Should the stop keep its abbreviation?": "No"},
        },
        status=202,
        record="oneQuestion",
        notes=SESSION,
        summary="Answer the question with an option other than the assumed one: the assistant designs again",
    )
    assert answered["state"] == "checking"
    task = _wait(s, task["id"], "checked", "failed")
    assert task["state"] == "checked"
    told = s.call(
        "POST",
        TASK + "/model",
        path=where,
        body={"expectedVersion": task["version"], "correction": "Write Bahnhof in full, not Bf."},
        status=202,
        record="inWords",
        notes=SESSION,
        summary="Tell the assistant something: it proposes again, the words winning over its own choices",
    )
    assert told["state"] == "checking"
    task = _wait(s, task["id"], "checked", "failed")
    s.call(
        "POST",
        TASK + "/proposal",
        path=where,
        body={"expectedVersion": task["version"]},
        status=409,
        code="AI_TASK_STATE",
    )
    accepted = s.call(
        "POST",
        TASK + "/accept",
        path=where,
        body={"expectedVersion": task["version"]},
        status=202,
    )
    assert accepted["state"] == "checking" and accepted["design"]["stage"] == "load"
    task = _wait(s, task["id"], "loaded", "failed")
    assert task["state"] == "loaded" and task["result"]["counts"]["updated"] == 1
    change_set = task["result"]["changeSetId"]
    held = s.call(
        "GET", "/api/v1/change-sets/{change_set_id}", path={"change_set_id": change_set}, status=200
    )
    assert held["name"] == "Davos stop names"
    s.call(
        "GET",
        TASK,
        path=where,
        status=200,
    )
    assert (
        "Bahnhof"
        not in s.call(
            "GET",
            "/api/v1/objects/{object_type_key}/{object_id}",
            path={"object_type_key": "stop", "object_id": stop["id"]},
            status=200,
        )["name"]
    )


def test_a_task_that_fails_is_tried_again_stopped_and_discarded(ai):
    s, assistant = ai
    assistant.says(
        fail=True,
        proposal={
            "draftId": None,
            "title": "Check the abbreviations",
            "summary": "Every stop keeps its abbreviation.",
            "questions": [],
        },
    )
    started = _give(
        s,
        {"workspaceKey": "graubuenden", "words": "Check that every Davos stop has an abbreviation"},
        status=202,
    )
    failed = _wait(s, started["id"], "failed", "checked")
    assert failed["state"] == "failed" and failed["canTell"] is True
    where = {"task_id": failed["id"]}
    s.call(
        "POST",
        TASK + "/retry",
        path=where,
        body={"expectedVersion": failed["version"] - 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    assistant.says(fail=False)
    retried = s.call(
        "POST",
        TASK + "/retry",
        path=where,
        body={
            "expectedVersion": failed["version"],
            "words": "Try again; the abbreviations may be empty",
        },
        status=202,
        record="afterAFailure",
        notes=SESSION,
        summary="Go on with a task that failed, with a few words: the same session tries again",
    )
    assert retried["state"] == "checking"
    task = _wait(s, failed["id"], "checked", "failed")
    assert task["state"] == "checked"
    s.call(
        "POST",
        TASK + "/retry",
        path=where,
        body={"expectedVersion": task["version"]},
        status=409,
        code="AI_TASK_STATE",
    )

    # A turn that takes long is stopped: the task goes back to its proposal.
    (assistant.folder / "hold").touch()
    (assistant.folder / "holding").unlink(missing_ok=True)
    s.call(
        "POST",
        TASK + "/model",
        path=where,
        body={"expectedVersion": task["version"], "correction": "Also list the stops without one"},
        status=202,
    )
    deadline = time.monotonic() + 60
    while not (assistant.folder / "holding").exists():
        assert time.monotonic() < deadline, "the turn did not start"
        time.sleep(0.1)
    stopping = s.call(
        "POST",
        TASK + "/cancel",
        path=where,
        status=202,
        record="mid-turn",
        notes=SESSION,
        summary="Stop what the assistant is doing: the turn ends, the task goes back to its proposal",
    )
    assert stopping["state"] in ("checking", "checked")
    (assistant.folder / "hold").unlink()
    task = _wait(s, failed["id"], "checked", "stopped")
    assert task["state"] == "checked"
    listed = s.call(
        "GET",
        TASKS,
        query={"pageSize": 5},
        status=200,
        record="newest",
        notes=SESSION,
        summary="The caller's tasks, newest first",
    )
    assert listed["items"][0]["id"] == task["id"] and len(listed["items"]) == 2
    discarded = s.call(
        "POST",
        TASK + "/discard",
        path=where,
        status=200,
        record="checked",
        notes=SESSION,
        summary="End the task: it is cancelled and its working folder goes; nothing else is undone",
    )
    assert discarded["state"] == "cancelled"
    s.call("POST", TASK + "/discard", path=where, status=409, code="AI_TASK_STATE")
    s.call(
        "GET",
        TASK,
        path={"task_id": "00000000-0000-4000-8000-000000000001"},
        status=404,
        code="AI_TASK_NOT_FOUND",
    )


def _stops_workbook(s: Scenario, folder: Path) -> Path:
    """The bus company's workbook as its next version comes: its layout, with three stops the workspace
    holds (two with another valid-from date) and one it does not."""
    import openpyxl

    davos = _one(s, "municipality", "Davos")
    stops = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": davos["id"], "sort": "name", "pageSize": 3},
        status=200,
    )["items"]
    dates = ["13.10.2025", "01.04.2021", "01.04.2021"]
    book = openpyxl.load_workbook(WORKBOOK)
    sheet = book["Haltestellen"]
    sheet.delete_rows(4, sheet.max_row)
    rows = [
        (
            stop["name"],
            "Davos",
            "",
            next(a["value"] for a in stop["attributes"] if a["attributeTypeKey"] == "stop-number"),
            date,
        )
        for stop, date in zip(stops, dates, strict=True)
    ]
    rows.append(("Davos Bahnhof Nord", "Davos", "", 8599001, "01.04.2021"))
    for number, row in enumerate(rows, start=4):
        for column, value in zip("ABCDE", row, strict=True):
            sheet[f"{column}{number}"] = value
    target = folder / "Haltestellen_Busbetrieb_Nord_Winter.xlsx"
    book.save(target)
    return target


def test_a_workbook_task_follows_the_saved_layout_and_is_loaded(ai, tmp_path):
    s, _ = ai
    # The bus company's earlier workbook was loaded through a saved layout (an import profile), which
    # finds a stop by its name.
    profile = {
        **BUS_STOPS,
        "valueMaps": {
            **BUS_STOPS["valueMaps"],
            "dates": {**BUS_STOPS["valueMaps"]["dates"], "13.10.2025": "2025-10-13"},
        },
        "sources": [{**BUS_STOPS["sources"][0], "key": {"field": "name"}}],
    }
    s.call("POST", "/api/v1/import-profiles", body=profile, status=201)
    stored = _upload(
        s,
        "/api/v1/source-files",
        {"owner": {"profileKey": "bus-stops-north"}, "workspaceKey": "graubuenden"},
        WORKBOOK,
        status=201,
    )
    _wait_job(s, stored["profile"]["jobId"])

    edited = _stops_workbook(s, tmp_path)
    started = _upload(
        s,
        TASKS,
        {"workspaceKey": "graubuenden", "words": "The next version of the bus company's stop list"},
        edited,
        status=202,
        record="workbook",
        notes=SAVED,
        summary="A workbook with a few words: the task starts reading the file",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert started["state"] == "reading" and started["fileName"] == edited.name
    task = _wait(s, started["id"], "checked", "failed")
    assert task["state"] == "checked" and task["design"]["stage"] == "model"
    assert task["design"]["agentSession"] is None, "the saved layout needs no session"
    where = {"task_id": task["id"]}
    read = s.call(
        "GET",
        TASK,
        path=where,
        status=200,
        record="savedLayout",
        notes=SAVED,
        summary="A task the saved layout read, with no assistant asked: the table it found and the profile it followed",
    )
    assert read["reading"]["profile"]["key"] == "bus-stops-north"
    accepted = s.call(
        "POST",
        TASK + "/accept",
        path=where,
        body={"expectedVersion": task["version"]},
        status=202,
        record="savedLayout",
        notes=SAVED,
        summary="Accept the proposal: every row is checked in a dry run, and nothing is loaded yet",
    )
    assert accepted["state"] == "checking"
    task = _wait(s, task["id"], "checked", "failed")
    assert task["design"]["stage"] == "load"
    assert task["check"]["summary"] == {
        "created": 1,
        "updated": 2,
        "unchanged": 1,
        "refused": 0,
        "skipped": 0,
    }
    changes = s.call(
        "GET",
        TASK + "/changes",
        path=where,
        query={"source": 0, "pageSize": 10},
        status=200,
        record="winterList",
        notes=SAVED,
        summary="The records the check would change in the Haltestellen sheet, with each field now and after",
    )
    assert [item["name"] for item in changes["items"]] == ["Davos Frauenkirch", "Davos Glaris"]
    s.call(
        "GET",
        TASK + "/changes",
        path=where,
        query={"source": 9},
        status=422,
        code="AI_TASK_TABLE_UNKNOWN",
    )
    back = s.call(
        "POST",
        TASK + "/proposal",
        path=where,
        body={"expectedVersion": task["version"]},
        status=200,
        record="backToTheProposal",
        notes=SAVED,
        summary="Back from the load stage to the proposal; no job runs",
    )
    assert back["design"]["stage"] == "model"
    s.call(
        "POST",
        TASK + "/accept",
        path=where,
        body={"expectedVersion": back["version"]},
        status=202,
    )
    task = _wait(s, task["id"], "checked", "failed")
    s.call(
        "POST",
        TASK + "/run",
        path=where,
        body={"expectedVersion": task["version"] - 1, "changeSetName": "Bus stops, winter"},
        status=409,
        code="VERSION_CONFLICT",
    )
    run = s.call(
        "POST",
        TASK + "/run",
        path=where,
        body={"expectedVersion": task["version"], "changeSetName": "Bus stops, winter"},
        status=202,
        record="intoAChangeSet",
        notes=SAVED,
        summary="Load the checked plan into a new change set; live data is unchanged",
    )
    assert run["state"] == "loading"
    task = _wait(s, task["id"], "loaded", "failed")
    assert task["result"]["counts"]["created"] == 1 and task["result"]["counts"]["updated"] == 2
    held = s.call(
        "GET",
        "/api/v1/change-sets/{change_set_id}",
        path={"change_set_id": task["result"]["changeSetId"]},
        status=200,
    )
    assert held["name"] == "Bus stops, winter"
