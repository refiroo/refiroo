"""J50 — Load a workbook into a workspace with the assistant (USER_JOURNEYS.md § AI proposals, 0.16
AP6a and AP6).

A person gives a workbook, the workspace it goes into and optionally a few words. The rules read
each table against the workspace's records; the assistant (the deterministic fake provider,
``app.engine.proposals.fake``) designs how the workbook lives in the engine: model operations on a
draft of the workspace's model, the records the structure needs, the import profile and its
questions. The engine applies them, checks the profile against the draft and dry-runs every row of
the workbook; the load installs the draft when the model changed, activates it in the workspace and
imports into a change set; live data is never changed. Every case runs on two configurations
through the public API, each in a workspace of its own; the journey application runs no worker
thread, so a test runs the engine's job worker itself.
"""

import copy
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from openpyxl import Workbook
from scenario import ok, refused
from test_j34_onboard import _all

from app.engine.proposals import fake

FAKE = "app.engine.proposals.fake:provider"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
STRUCTURES = ("R", "R.u", "R.n", "R.q", "R.x1")


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _run(world):
    state = world.api.client.app.state
    chunks = 0
    while ran := state.assistant_worker.run_until_idle() + state.job_worker.run_until_idle():
        chunks += ran
    return chunks


def _workspace(world):
    key = f"load-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Load site"}), 201)
    return key


def _xlsx(sheets):
    book = Workbook()
    book.remove(book.active)
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        for row in rows:
            sheet.append(list(row))
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class Ledgers:
    """Ten stored records of ``R`` in a workspace of their own and the workbook that updates them."""

    def __init__(self, world, count=10):
        self.world = world
        self.tag = uuid4().hex[:6]
        self.workspace = _workspace(world)
        self.key = world.attribute_name("R.u")
        self.owner = world.attribute_name("R.q")
        self.summary = world.attribute_name("R.x1")
        self.score = world.attribute_name("R.n")
        self.header = (self.key, "Name", self.owner, self.summary, self.score)
        self.rows = []
        self.records = {}
        for number in range(count):
            row = [
                f"{self.tag}-{number:02d}",
                f"Ledger {self.tag} {number}",
                "Owner",
                "Sum",
                number * 5,
            ]
            self.rows.append(row)
            self.records[row[0]] = world.made(
                "R",
                row[1],
                workspace=self.workspace,
                values={"R.u": row[0], "R.q": "Owner", "R.x1": "Sum", "R.n": row[4]},
            )

    def book(self, rows=None, extra=None, header=None):
        sheets = {"Records": [header or self.header, *(self.rows if rows is None else rows)]}
        sheets.update(extra or {})
        return _xlsx(sheets)

    def new(self, number):
        return [f"{self.tag}-N{number}", f"Newcomer {self.tag} {number}", "Owner", "Sum", 7]

    def live(self):
        found = _all(
            self.world,
            f"/objects/{self.world.key('R')}",
            workspaceKey=self.workspace,
        )
        return {item["name"]: item for item in found}

    def in_change_set(self, change_set_id):
        found = _all(
            self.world,
            f"/objects/{self.world.key('R')}",
            changeSetId=change_set_id,
        )
        return {item["name"]: item for item in found}


def _create(world, workspace, content, words=None, name="ledgers.xlsx", **request):
    body = {"workspaceKey": workspace, **request}
    if words:
        body["words"] = words
    return world.api.upload(
        "/ai/tasks", {"file": (name, content, XLSX)}, {"request": json.dumps(body)}
    )


def _read(world, ledgers, content=None, accept=True, **request):
    """The workbook given to the assistant and designed for: the task, ``checked``; with
    ``accept``, the proposed model accepted as the steward would and the load stage run."""
    task = ok(
        _create(
            world, ledgers.workspace, ledgers.book() if content is None else content, **request
        ),
        202,
    )
    assert task["state"] == "reading"
    _run(world)
    task = _task(world, task)
    return _accept(world, task) if accept else task


def _accept(world, task):
    """The proposed model accepted (0.16 AP6r): the load stage, run to the end."""
    if task["state"] != "checked" or (task.get("design") or {}).get("stage") != "model":
        return task
    ok(
        world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}),
        202,
    )
    _run(world)
    return _task(world, task)


def _task(world, task):
    return ok(world.api.get(f"/ai/tasks/{task['id']}"))


def _answers(world, task, answers):
    """The person's answers to the design's questions: another round, run to the end."""
    ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/answers",
            {"expectedVersion": task["version"], "answers": answers},
        ),
        202,
    )
    _run(world)
    return _accept(world, _task(world, task))


def _load(world, task, **body):
    ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/run",
            {"expectedVersion": task["version"], "changeSetName": "Ledger load", **body},
        ),
        202,
    )
    _run(world)
    return _task(world, task)


def _changed(world, change_set_id, kind):
    found = _all(world, f"/change-sets/{change_set_id}/object-changes", page_size=100, kind=kind)
    return {
        item["after"]["name"] if item["after"] else item["before"]["name"]: item for item in found
    }


def _table(task, number=1):
    return next(t for t in task["reading"]["tables"] if t["table"] == f"t{number}")


def _script(design):
    """The assistant's design: ``design(context)`` answers each design turn (a value is the answer
    itself, an exception is raised by the provider)."""
    if isinstance(design, BaseException):
        fake.script("workbookLoad", design)
        return

    def answer(c):
        found = design(c) if callable(design) else design
        if isinstance(found, dict) and c.get("stage") == "load" and "modelOperations" in found:
            # The model was proposed and accepted: the load stage does not add it again.
            found = {k: v for k, v in found.items() if k != "modelOperations"}
        return found

    fake.script(
        "workbookLoad",
        lambda c: answer(c) if c.get("turn") == "design" else fake.DEFAULTS["workbookLoad"](c),
    )


def _designs(stage=None):
    """The context of each design call the provider was sent (of one stage, when named)."""
    return [
        r.context
        for r in fake.seen
        if r.context.get("turn") == "design" and (stage is None or r.context.get("stage") == stage)
    ]


def _rules(context):
    """The profile the rules' reading gives, to edit into a design."""
    return copy.deepcopy(context["rulesProfile"])


def _records_source(world, ledgers, **changes):
    """The source that updates the ledgers from the workbook's Records sheet: what the assistant
    sends to change how a table the rules read quietly (nothing to decide) is loaded."""
    source = {
        "sheet": "Records",
        "headerRow": 1,
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "record": "upsert",
        "key": {"attributeTypeKey": world.key("R.u")},
        "columns": [
            {"column": ledgers.key, "attributeTypeKey": world.key("R.u")},
            {"column": "Name", "field": "name"},
            {"column": ledgers.owner, "attributeTypeKey": world.key("R.q")},
            {"column": ledgers.summary, "attributeTypeKey": world.key("R.x1")},
            {"column": ledgers.score, "attributeTypeKey": world.key("R.n")},
        ],
        "missing": "report",
    }
    return {**source, **changes}


def _design(profile, **answer):
    return {"profile": profile, "done": True, "summary": "Designed for the test", **answer}


def _sheet(task, sheet, structure=False):
    assert task["check"], (task["notes"], task["design"]["outcome"])
    assert task["check"]
    return next(
        s for s in task["check"]["sheets"] if s["sheet"] == sheet or (structure and s["structure"])
    )


def _release(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/model"))


def _value(record, attribute_key):
    return next(
        (a["value"] for a in record["attributes"] if a["attributeTypeKey"] == attribute_key), None
    )


# --- J50.1 to J50.5: the workbook updates what the workspace holds --------------------------------


# --- J50.6: the model changes -------------------------------------------------------------------


def _region_design(world, ledgers):
    """Additions (case B): a column the type lacks becomes an attribute type attached to it, and
    the profile loads it."""

    def design(context):
        profile = _rules(context)
        profile["sources"][0]["columns"].append(
            {"column": "Region", "attributeTypeKey": "ledger-region"}
        )
        return _design(
            profile,
            modelOperations=[
                {
                    "kind": "addAttributeType",
                    "key": "ledger-region",
                    "name": "Region",
                    "valueType": "text",
                },
                {
                    "kind": "attachAttribute",
                    "objectType": world.key("R"),
                    "attributeType": "ledger-region",
                },
            ],
        )

    _script(design)
    rows = [[*row, f"Region {number % 3}"] for number, row in enumerate(ledgers.rows)]
    return ledgers.book(rows, header=(*ledgers.header, "Region"))


# --- J50.7 to J50.9: reading, fixing and failing ------------------------------------------------


@pytest.mark.journey("J50.10")
@pytest.mark.structures(*STRUCTURES)
def test_without_a_provider_the_task_is_refused(world):
    """Given no provider, then a task is refused with 409 AI_NOT_CONFIGURED and the feature is not
    offered."""
    ledgers = Ledgers(world)
    refused(_create(world, ledgers.workspace, ledgers.book()), 409, "AI_NOT_CONFIGURED")
    status = ok(world.api.get("/ai/status"))
    assert {f["purpose"]: f["available"] for f in status["features"]}["workbookLoad"] is False


@pytest.mark.journey("J50.10")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="samples")
def test_below_the_level_values_the_task_is_refused(world):
    """Given a send level below values, then a task is refused with 409 AI_SEND_LEVEL_TOO_LOW and
    the feature is not offered."""
    ledgers = Ledgers(world)
    refused(_create(world, ledgers.workspace, ledgers.book()), 409, "AI_SEND_LEVEL_TOO_LOW")
    status = ok(world.api.get("/ai/status"))
    assert {f["purpose"]: f["available"] for f in status["features"]}["workbookLoad"] is False


@pytest.mark.journey("J50.10", "J50.19")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_only_the_requester_and_an_administrator_see_a_task_and_the_group_is_needed(world):
    """Given a task, then another person holding Bulk and AI proposals who is neither its requester
    nor the workspace's administrator gets 404 AI_TASK_NOT_FOUND (answering it included), an
    administrator sees it, a reader gets 403 FORBIDDEN, and the file is not served as a source
    file."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world)
    task = _read(world, ledgers)
    scope = {"workspaceKey": ledgers.workspace}
    _, other = _client(world, "other", ("steward", scope))
    refused(other.api.get(f"/ai/tasks/{task['id']}"), 404, "AI_TASK_NOT_FOUND")
    refused(
        other.api.post(
            f"/ai/tasks/{task['id']}/answers",
            {"expectedVersion": task["version"], "answers": {"Any": "Thing"}},
        ),
        404,
        "AI_TASK_NOT_FOUND",
    )
    assert ok(other.api.get("/ai/tasks"))["items"] == []
    _, admin = _client(world, "admin", ("steward", scope), ("workspace-admin", scope))
    assert ok(admin.api.get(f"/ai/tasks/{task['id']}"))["id"] == task["id"]
    _, reader = _client(world, "reader", ("reader", scope))
    refused(reader.api.get(f"/ai/tasks/{task['id']}"), 403, "FORBIDDEN")
    refused(world.api.get(f"/source-files/{task['sourceFileId']}"), 404, "SOURCE_FILE_NOT_FOUND")
    assert [t["id"] for t in ok(world.api.get("/ai/tasks"))["items"]] == [task["id"]]


@pytest.mark.journey("J50.10")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_caller_who_may_import_but_not_use_ai_proposals_is_refused_naming_the_group(world):
    """Given a client who may import into the workspace (Bulk) but does not hold Use AI proposals,
    when it gives a workbook to the assistant, then it is refused with 403 naming the group and no
    task exists; the ordinary import stays its way in."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world)
    role = ok(
        world.api.post("/roles", {"name": "Importers", "actionGroups": ["bulk", "browse"]}), 201
    )
    _, importer = _client(world, "importer", (role["key"], {"workspaceKey": ledgers.workspace}))
    error = refused(_create(importer, ledgers.workspace, ledgers.book()), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["ai-proposals"]
    assert ok(importer.api.get("/ai/tasks"))["items"] == []


@pytest.mark.journey("J50.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_TASK_RETENTION_DAYS="30")
def test_a_task_and_its_workbook_go_once_the_retention_is_over(world):
    """Given a checked task kept 30 days, when the worker sweeps before and after them, then the task
    is there and then gone, its workbook with it."""
    ledgers = Ledgers(world)
    task = _read(world, ledgers)
    worker = world.api.client.app.state.job_worker
    worker.sweep(datetime.now(UTC) + timedelta(days=29))
    assert _task(world, task)["id"] == task["id"]
    worker.sweep(datetime.now(UTC) + timedelta(days=31))
    refused(world.api.get(f"/ai/tasks/{task['id']}"), 404, "AI_TASK_NOT_FOUND")
    assert ok(world.api.get("/ai/tasks"))["items"] == []


# --- J50.18, J50.19: who may change the model, and when the person may answer ---------------------


# --- the revision (0.16 AP6a): real workbooks read well ------------------------------------------


def _cells_book(sheets):
    """A workbook from ``{sheet: {(row, column): value}}``, for lists laid out side by side."""
    book = Workbook()
    book.remove(book.active)
    for title, cells in sheets.items():
        sheet = book.create_sheet(title)
        for (row, column), value in cells.items():
            sheet.cell(row=row, column=column, value=value)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _bare(value):
    """A JSON value without its nulls: a design's profile and a stored profile compared."""
    if isinstance(value, dict):
        return {k: _bare(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_bare(v) for v in value]
    return value


def _list_at(cells, row, column, header, rows):
    """A list whose header starts at (row, column), its rows under it."""
    for offset, title in enumerate(header):
        cells[(row, column + offset)] = title
    for down, values in enumerate(rows, 1):
        for offset, value in enumerate(values):
            if value not in (None, ""):
                cells[(row + down, column + offset)] = value


@pytest.mark.journey("J50.12")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_column_the_followed_profile_always_left_out_needs_no_decision(world):
    """Given a saved profile that does not read a 'Remarks' column, and the file it read before had
    that column too, when the next file of the layout (with 'Remarks' and a new 'Comment' column) is
    given to the assistant, then both are listed left out, only 'Comment' needs the person, and a
    reading with nothing else to decide says nothing needs them. Found on the user's real workbook,
    where 22 lists 'needed' them for columns their profile had always left out."""
    from test_j34_onboard import _profiled

    ledgers = Ledgers(world)
    key = f"ledger-layout-{uuid4().hex[:6]}"
    ok(
        world.api.post(
            "/import-profiles",
            {
                "key": key,
                "name": "Ledger layout",
                "workspaceKey": ledgers.workspace,
                "sources": [
                    {
                        "sheet": "Records",
                        "applicationKey": world.app("R"),
                        "objectTypeKey": world.key("R"),
                        "key": {"attributeTypeKey": world.key("R.u")},
                        "columns": [
                            {"column": ledgers.key, "attributeTypeKey": world.key("R.u")},
                            {"column": "Name", "field": "name"},
                            {"column": ledgers.score, "attributeTypeKey": world.key("R.n")},
                        ],
                    }
                ],
            },
        ),
        201,
    )
    header = (ledgers.key, "Name", ledgers.score, "Remarks")
    before = ledgers.book([[r[0], r[1], r[4], "seen"] for r in ledgers.rows], header=header)
    _profiled(
        world, {"profileKey": key}, "ledgers-before.xlsx", before, workspaceKey=ledgers.workspace
    )

    known = _read(world, ledgers, before)
    table = _table(known)
    assert table["owner"] == "profile"
    assert [c["header"] for c in table["columns"] if c["leftOut"]] == ["Remarks"]
    assert table["attention"] == [] and known["reading"]["summary"]["needDecision"] == 0

    after = ledgers.book(
        [[r[0], r[1], r[4], "seen", "new"] for r in ledgers.rows], header=(*header, "Comment")
    )
    table = _table(_read(world, ledgers, after))
    assert sorted(c["header"] for c in table["columns"] if c["leftOut"]) == ["Comment", "Remarks"]
    assert table["attention"] == ["leftOutColumns"]


# --- J50.21, J50.22: relationships where a condition holds ----------------------------------------


def _relations(world, workspace):
    """The relationships live in the workspace."""
    return _all(world, f"/workspaces/{workspace}/relations", page_size=100)


# --- J50.23 to J50.25: the model is proposed before the load (0.16 AP6r) ---------------------------


def _outline(world, text):
    return [{"objectTypeKey": world.key("R"), "text": text}]


# --- the assistant's session: propose on a draft, go on with the person's words, then load ---------


STAND_IN = """#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
config = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")))
log = config["log"]
open(log, "a").write(json.dumps({"prompt": prompt, "args": sys.argv[1:], "files": sorted(os.listdir("."))}) + "\\n")
call = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "input": {"command": "curl -X POST x/api/v1/model-drafts/d/dry-run"}}]}}
print(json.dumps(call))
if "accepted" in prompt:
    print(json.dumps({"type": "result", "result": "Done.\\nCHANGE_SET: " + config["changeSet"]}))
else:
    json.dump({"draftId": config["draft"], "summary": "A plan.",
               "questions": [{"text": "Which?", "options": ["A", "B"], "assumed": "A"}]},
              open("proposal.json", "w"))
    print(json.dumps({"type": "result", "result": "Ready."}))
"""


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_session_proposes_on_a_draft_goes_on_with_the_persons_words_and_loads_when_accepted(
    world, tmp_path, monkeypatch
):
    """Given Claude Code as the assistant, when a steward gives a workbook, then the session works in
    a folder with the workbook, the model and the API and stops at a draft, nothing installed; the
    steward's words continue the same session; acceptance ends in the change set it names; and a
    proposal can be thrown away with its draft."""
    from app.engine.tasks import agent

    ledgers = Ledgers(world)
    script = tmp_path / "stand_in.py"
    script.write_text(STAND_IN)
    script.chmod(0o755)
    log = tmp_path / "log.jsonl"
    draft = ok(world.api.post("/model-drafts", {"name": "A proposal", "model": {}}), 201)
    change_set = ok(
        world.api.post(
            f"/workspaces/{ledgers.workspace}/change-sets",
            {"name": "Its load", "source": "currentLive"},
        ),
        201,
    )
    monkeypatch.setenv("AI_AGENT_COMMAND", str(script))
    config = tmp_path / "config.json"
    settings = {"log": str(log), "draft": draft["id"], "changeSet": change_set["id"]}
    config.write_text(json.dumps(settings))
    monkeypatch.setattr(agent, "_openapi", lambda url: b"{}")

    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked" and task["design"]["stage"] == "model"
    assert task["draftId"] == draft["id"] and task["design"]["summary"] == "A plan."
    assert task["design"]["questions"][0]["text"] == "Which?" and task["result"] is None
    first = json.loads(log.read_text().splitlines()[0])
    assert first["prompt"].startswith("Make it so")
    assert {"workbook.xlsx", "model.json", "openapi.json"} <= set(first["files"])
    # The engine's guards go with every session, whatever the command says.
    assert first["args"][first["args"].index("--permission-mode") + 1] == "dontAsk"
    assert "--restricted" in first["args"]
    session_id = first["args"][first["args"].index("--session-id") + 1]

    ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/model",
            {"expectedVersion": task["version"], "correction": "Two types, please"},
        ),
        202,
    )
    _run(world)
    task = _task(world, task)
    second = json.loads(log.read_text().splitlines()[1])
    assert "Two types, please" in second["prompt"]
    assert second["args"][second["args"].index("--resume") + 1] == session_id

    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    _run(world)
    task = _task(world, task)
    # An empty change set is no load, whatever the session says; tried again once it holds the rows.
    assert task["state"] == "failed" and task["result"] is None
    world.create("R", "Loaded", change_set=world.current(change_set), workspace=ledgers.workspace)
    ok(world.api.post(f"/ai/tasks/{task['id']}/retry", {"expectedVersion": task["version"]}), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "loaded" and task["result"]["changeSetId"] == change_set["id"]
    assert task["result"]["counts"]["created"] == 1

    # A session that stops can be tried again, from where it was.
    stopped = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    config.write_text(json.dumps({**settings, "draft": "no-such-draft"}))
    _run(world)
    stopped = _task(world, stopped)
    assert stopped["state"] == "failed"
    config.write_text(json.dumps(settings))
    ok(
        world.api.post(
            f"/ai/tasks/{stopped['id']}/retry", {"expectedVersion": stopped["version"]}
        ),
        202,
    )
    _run(world)
    stopped = _task(world, stopped)
    assert stopped["state"] == "checked"
    assert "--resume" in json.loads(log.read_text().splitlines()[-1])["args"]

    # Words alone start a session too, with no file in its folder.
    alone = ok(
        world.api.upload(
            "/ai/tasks",
            {},
            {"request": json.dumps({"workspaceKey": ledgers.workspace, "words": "Rename the ledgers"})},
        ),
        202,
    )
    _run(world)
    alone = _task(world, alone)
    assert alone["state"] == "checked" and alone["draftId"] == draft["id"]
    said = json.loads(log.read_text().splitlines()[-1])
    assert said["prompt"].startswith("Rename the ledgers") and "There is no file" in said["prompt"]
    assert "workbook.xlsx" not in said["files"]

    gone = ok(world.api.post(f"/ai/tasks/{stopped['id']}/discard", {}), 200)
    assert gone["state"] == "cancelled" and gone["draftId"] is None


WAITING_STAND_IN = """#!/usr/bin/env python3
import json, os, time
folder = os.path.dirname(os.path.realpath(__file__))
config = json.load(open(os.path.join(folder, "config.json")))
open(os.path.join(folder, "token"), "w").write(os.environ["REFIROO_TOKEN"])
while not os.path.exists(os.path.join(folder, "go")):
    time.sleep(0.1)
json.dump({"draftId": config["draft"], "summary": "A plan."}, open("proposal.json", "w"))
print(json.dumps({"type": "result", "result": "Ready."}))
"""


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_job_the_session_queues_runs_under_its_grants_even_when_the_session_has_stopped(
    world, tmp_path, monkeypatch
):
    """Given a session that uploads a workbook to its draft and stops before the profile ran, when
    the job worker reaches the job, then it completes: the session does not hold that worker, and
    its grants stay until the job is done, ending after that."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import Job

    ledgers = Ledgers(world)
    state = world.api.client.app.state
    script = tmp_path / "stand_in.py"
    script.write_text(WAITING_STAND_IN)
    script.chmod(0o755)
    draft = ok(world.api.post("/model-drafts", {"name": "A proposal", "model": {}}), 201)
    (tmp_path / "config.json").write_text(json.dumps({"draft": draft["id"]}))
    monkeypatch.setenv("AI_AGENT_COMMAND", str(script))
    monkeypatch.setattr(agent, "_openapi", lambda url: b"{}")
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)

    with ThreadPoolExecutor(1) as pool:
        session = pool.submit(state.assistant_worker.run_until_idle)
        deadline = time.monotonic() + 30
        while not (tmp_path / "token").exists():
            assert time.monotonic() < deadline and not session.done()
            time.sleep(0.1)
        token = (tmp_path / "token").read_text()
        upload = world.api.client.post(
            "/api/v1/source-files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("ledgers.xlsx", ledgers.book(), XLSX)},
            data={
                "request": json.dumps(
                    {"owner": {"draftId": draft["id"]}, "workspaceKey": ledgers.workspace}
                )
            },
        )
        assert upload.status_code == 201, upload.text
        (tmp_path / "go").touch()
        with SessionLocal() as db:
            queued = select(Job).where(
                Job.parameters["sourceFileId"].as_string() == upload.json()["id"]
            )
            job_id = db.scalar(queued).id
        time.sleep(3)
        assert not session.done()
        state.job_worker.run_until_idle()
        session.result(timeout=30)

    with SessionLocal() as db:
        job = db.scalar(select(Job).where(Job.id == job_id))
        assert job.state == "completed", job.error
    assert _task(world, task)["state"] == "checked"
    answer = world.api.client.get(
        f"/api/v1/workspaces/{ledgers.workspace}/model", headers={"Authorization": f"Bearer {token}"}
    )
    assert answer.status_code == 403


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_session_cannot_publish_activate_or_reach_another_workspace(world, monkeypatch):
    """Given the session's own token, then the engine refuses publishing, activating a model and
    reading another workspace, whatever the session tries, and the grants end with the turn."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import Job

    ledgers = Ledgers(world)
    other = _workspace(world)
    change_set = ok(
        world.api.post(
            f"/workspaces/{ledgers.workspace}/change-sets", {"name": "Its load", "source": "currentLive"}
        ),
        201,
    )
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    with SessionLocal() as session:
        job = session.scalar(select(Job).where(Job.id == task["jobId"]))
        token, grants = agent._access(session, job, ledgers.workspace)
        session.commit()
    headers = {"Authorization": f"Bearer {token}"}
    client = world.api.client

    assert (
        client.get(f"/api/v1/workspaces/{ledgers.workspace}/model", headers=headers).status_code
        == 200
    )
    assert client.get(f"/api/v1/workspaces/{other}/model", headers=headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            headers=headers,
            json={"expectedChangeSetVersion": change_set["version"]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/workspaces/{ledgers.workspace}/model/activation",
            headers=headers,
            json={"releaseId": "x", "expectedVersion": 1, "expectedReleaseId": "y"},
        ).status_code
        == 403
    )
    with SessionLocal() as session:
        agent._end(session, grants)
        session.commit()
    assert (
        client.get(f"/api/v1/workspaces/{ledgers.workspace}/model", headers=headers).status_code
        == 403
    )
