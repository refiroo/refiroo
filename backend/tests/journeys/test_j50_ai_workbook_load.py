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
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from openpyxl import Workbook, load_workbook
from scenario import ok, refused
from test_j24_job_stream import served  # noqa: F401  (the journey application over HTTP)
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
    """The workers run until nothing is left; the job worker runs beside a session, as it does in
    service, since the jobs a session queues must be done for it to end."""
    state = world.api.client.app.state
    chunks = 0
    while True:
        with ThreadPoolExecutor(1) as pool:
            session = pool.submit(state.assistant_worker.run_until_idle)
            ran = 0
            while not session.done():
                ran += state.job_worker.run_until_idle()
                time.sleep(0.1)
            ran += session.result() + state.job_worker.run_until_idle()
        if not ran:
            return chunks
        chunks += ran


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
def test_without_the_assistant_command_the_task_is_refused(world):
    """Given no AI_AGENT_COMMAND, then a task is refused with 409 AI_NOT_CONFIGURED and the assistant
    is not offered."""
    ledgers = Ledgers(world)
    refused(_create(world, ledgers.workspace, ledgers.book()), 409, "AI_NOT_CONFIGURED")
    assert ok(world.api.get("/ai/status"))["assistant"] is False


@pytest.mark.journey("J50.10")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true", AI_SEND_LEVEL="samples")
def test_below_the_level_values_the_task_is_refused(world):
    """Given a send level below values, then a task is refused with 409 AI_SEND_LEVEL_TOO_LOW; the
    assistant is set up, as the level is a separate matter."""
    ledgers = Ledgers(world)
    refused(_create(world, ledgers.workspace, ledgers.book()), 409, "AI_SEND_LEVEL_TOO_LOW")
    assert ok(world.api.get("/ai/status"))["assistant"] is True


@pytest.mark.journey("J50.10", "J50.19")
@pytest.mark.structures(*STRUCTURES)
def test_only_the_requester_and_an_administrator_see_a_task_and_the_group_is_needed(
    world, tmp_path, monkeypatch
):
    """Given a task, then another person holding Bulk and AI proposals who is neither its requester
    nor the workspace's administrator gets 404 AI_TASK_NOT_FOUND (answering it included), an
    administrator sees it, a reader gets 403 FORBIDDEN, and the file is not served as a source
    file."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world)
    _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    task = _read(world, ledgers, accept=False)
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
@pytest.mark.settings(AI_AGENT_COMMAND="true")
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
@pytest.mark.settings(AI_TASK_RETENTION_DAYS="30")
def test_a_task_and_its_workbook_go_once_the_retention_is_over(world, tmp_path, monkeypatch):
    """Given a checked task kept 30 days, when the worker sweeps before and after them, then the task
    is there and then gone, its workbook with it."""
    ledgers = Ledgers(world)
    _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    task = _read(world, ledgers, accept=False)
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
def test_a_column_the_followed_profile_always_left_out_needs_no_decision(
    world, tmp_path, monkeypatch
):
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

    _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    known = _read(world, ledgers, before, accept=False)
    table = _table(known)
    assert table["owner"] == "profile"
    assert [c["header"] for c in table["columns"] if c["leftOut"]] == ["Remarks"]
    assert table["attention"] == [] and known["reading"]["summary"]["needDecision"] == 0

    after = ledgers.book(
        [[r[0], r[1], r[4], "seen", "new"] for r in ledgers.rows], header=(*header, "Comment")
    )
    # A new column does not fit the saved layout: a session starts, with the reading beside it.
    table = _table(_read(world, ledgers, after, accept=False))
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
prompt = sys.argv[sys.argv.index("--") + 1]
config = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")))
log = config["log"]
open(log, "a").write(json.dumps({"prompt": prompt, "args": sys.argv[1:], "files": sorted(os.listdir("."))}) + "\\n")
call = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "input": {"command": "curl -X POST x/api/v1/model-drafts/d/dry-run"}}]}}
print(json.dumps(call))
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
if config.get("api"):
    # What a test asks of the API with the token and the address the engine gave this session.
    import re, time, httpx
    if not os.path.exists("url.txt"):
        open("url.txt", "w").write(re.search(r"https?://[\\w.:-]+", prompt).group(0))
    base = open("url.txt").read() + "/api/v1"
    head = {"Authorization": "Bearer " + os.environ["REFIROO_TOKEN"]}
    def api(method, path, **kw):
        sent = httpx.request(method, base + path, headers=head, timeout=60, **kw)
        assert sent.status_code < 300, (method, path, sent.status_code, sent.text)
        return sent.json()
    def until(path, done):
        for _ in range(300):
            found = api("GET", path)
            if done(found):
                return found
            time.sleep(0.2)
        raise SystemExit("never ready: " + path)
    def workbook():
        return {"file": ("ledgers.xlsx", open("workbook.xlsx", "rb"), XLSX)}
if "accepted" in prompt:
    if config.get("api"):
        change_set = config["changeSet"]
        if config.get("releases"):
            model = json.load(open("model.json"))
            made = []
            for name in ("used", "unused"):
                model["release"]["version"] += "-" + name
                draft = api("POST", "/model-drafts", json={"name": name, "model": model})
                made.append(api("POST", "/model-drafts/" + draft["id"] + "/installation",
                                json={"expectedVersion": draft["version"]}))
                model["release"]["version"] = model["release"]["version"][: -len(name) - 1]
            version = api("GET", "/change-sets/" + change_set)["version"]
            api("PATCH", "/change-sets/" + change_set + "/model-release",
                json={"modelReleaseId": made[0]["id"], "expectedChangeSetVersion": version})
        if config.get("live"):
            # A batch and an import that name no change set write live data: refused to a session.
            live = {"workspaceKey": config["workspace"], "policy": "independent"}
            sent = {
                "batch": httpx.request("POST", base + "/batches", headers=head, timeout=60, json={
                    **live, "run": "inline", "items": config["live"]["items"]}),
                "import": httpx.request("POST", base + "/imports", headers=head, timeout=60,
                    files=workbook(), data={"request": json.dumps({
                        **live, "stage": "execute", "profile": config["live"]["profile"]})}),
            }
            open(config["live"]["out"], "w").write(json.dumps(
                {name: [r.status_code, r.json().get("code")] for name, r in sent.items()}))
        if config.get("profile"):
            version = api("GET", "/change-sets/" + change_set)["version"]
            api("POST", "/imports", files=workbook(), data={"request": json.dumps({
                "changeSetId": change_set,
                "expectedChangeSetVersion": version, "profile": config["profile"],
                "policy": "independent", "stage": "execute"})})
        if config.get("batch"):
            version = api("GET", "/change-sets/" + change_set)["version"]
            api("POST", "/batches", json={
                "changeSetId": change_set,
                "expectedChangeSetVersion": version, "policy": "independent", "run": "inline",
                "items": config["batch"]})
    print(json.dumps({"type": "result", "result": "Done.\\nCHANGE_SET: " + config["changeSet"]}))
else:
    if config.get("api") and config.get("dryRun"):
        source = api("POST", "/source-files", files=workbook(), data={"request": json.dumps({
            "owner": {"draftId": config["draft"]}, "workspaceKey": config["workspace"]})})
        until("/source-files/" + source["id"], lambda f: f["profile"]["state"] == "completed")
        api("POST", "/model-drafts/" + config["draft"] + "/dry-run", json={
            "sourceFileId": source["id"], "workspaceKey": config["workspace"],
            "profile": config["profile"]})
        until("/model-drafts/" + config["draft"] + "/dry-run", lambda f: f["state"] == "completed")
    draft_id = config["draft"]
    turned = os.path.exists("turned")
    open("turned", "w").close()
    if config.get("api") and (config.get("ownDraft") or (config.get("ownOnSecond") and turned)):
        draft_id = api("POST", "/model-drafts", json={"name": "Its own", "model": {}})["id"]
    json.dump({"draftId": draft_id, "summary": "A plan.",
               "questions": [{"text": "Which?", "options": ["A", "B"], "assumed": "A"}]},
              open("proposal.json", "w"))
    print(json.dumps({"type": "result", "result": "Ready."}))
"""


def _trust_stand_in(monkeypatch):
    """The stand-in's draft and change set are made by the test's client, not the task's own, which
    the engine would refuse; so it takes the stand-in's word for them (R-F3, R-F4 have cases of their
    own that do not)."""
    from sqlalchemy import select

    from app.engine.tasks import agent
    from app.models.database import ChangeSet

    monkeypatch.setattr(agent, "_openapi", lambda url: b"{}")
    monkeypatch.setattr(agent, "_drafted_by", lambda session, task, draft: True)
    monkeypatch.setattr(
        agent,
        "_change_set_of",
        lambda session, task, change_set_id: (
            session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
            if change_set_id
            else None
        ),
    )


def _assistant(
    world, tmp_path, monkeypatch, workspace, script=STAND_IN, model=None, verified=False, **settings
):
    """``script`` as the assistant's command, with a draft of its own for the proposal and a change
    set of its own for the load; ``config.json`` is what the script reads, so a test changes it
    between tasks. Returns the settings written, with the ``log`` of what the script was asked."""
    from app.engine.tasks import agent

    path = tmp_path / "stand_in.py"
    path.write_text(script)
    path.chmod(0o755)
    found = {
        "log": str(tmp_path / "log.jsonl"),
        "workspace": workspace,
        "draft": ok(
            world.api.post("/model-drafts", {"name": "A proposal", "model": model or {}}), 201
        )["id"],
        "changeSet": ok(
            world.api.post(
                f"/workspaces/{workspace}/change-sets",
                {"name": "Its load", "source": "currentLive"},
            ),
            201,
        )["id"],
        **settings,
    }
    (tmp_path / "config.json").write_text(json.dumps(found))
    monkeypatch.setenv("AI_AGENT_COMMAND", str(path))
    if verified:
        monkeypatch.setattr(agent, "_openapi", lambda url: b"{}")
    else:
        _trust_stand_in(monkeypatch)
    return found


def _next_draft(world, tmp_path, found):
    """A draft of its own for the next task: a session may not propose one another task holds."""
    found["draft"] = ok(world.api.post("/model-drafts", {"name": "Another", "model": {}}), 201)[
        "id"
    ]
    (tmp_path / "config.json").write_text(json.dumps(found))


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_proposes_on_a_draft_goes_on_with_the_persons_words_and_loads_when_accepted(
    world, tmp_path, monkeypatch
):
    """Given Claude Code as the assistant, when a steward gives a workbook, then the session works in
    a folder with the workbook, the model and the API and stops at a draft, nothing installed; the
    steward's words continue the same session; acceptance ends in the change set it names; and a
    proposal can be thrown away with its draft."""
    ledgers = Ledgers(world)
    settings = _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    draft = {"id": settings["draft"]}
    change_set = {"id": settings["changeSet"]}
    log = Path(settings["log"])
    config = tmp_path / "config.json"

    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked" and task["design"]["stage"] == "model"
    assert task["draftId"] == draft["id"] and task["design"]["summary"] == "A plan."
    assert task["design"]["questions"][0]["text"] == "Which?" and task["result"] is None
    first = json.loads(log.read_text().splitlines()[0])
    assert first["prompt"].startswith("Make it so")
    assert "holds 10 records" in first["prompt"] and "types of its own" in first["prompt"]
    # The draft keeps none of the workspace's types: the person is told, and may still accept.
    assert [item["kind"] for item in task["design"]["checks"]] == ["leftOut"]
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
    # Another task proposes on a draft of its own: a session may not take the first task's.
    _next_draft(world, tmp_path, settings)
    stopped = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    config.write_text(json.dumps({**settings, "draft": "no-such-draft"}))
    _run(world)
    stopped = _task(world, stopped)
    assert stopped["state"] == "failed"
    config.write_text(json.dumps(settings))
    ok(
        world.api.post(f"/ai/tasks/{stopped['id']}/retry", {"expectedVersion": stopped["version"]}),
        202,
    )
    _run(world)
    stopped = _task(world, stopped)
    assert stopped["state"] == "checked"
    assert "--resume" in json.loads(log.read_text().splitlines()[-1])["args"]

    # Words alone start a session too, with no file in its folder.
    _next_draft(world, tmp_path, settings)
    alone = ok(
        world.api.upload(
            "/ai/tasks",
            {},
            {
                "request": json.dumps(
                    {"workspaceKey": ledgers.workspace, "words": "Rename the ledgers"}
                )
            },
        ),
        202,
    )
    _run(world)
    alone = _task(world, alone)
    assert alone["state"] == "checked" and alone["draftId"] == settings["draft"]
    said = json.loads(log.read_text().splitlines()[-1])
    assert said["prompt"].startswith("Rename the ledgers") and "There is no file" in said["prompt"]
    assert "types of its own" not in said["prompt"]
    assert "workbook.xlsx" not in said["files"]

    gone = ok(world.api.post(f"/ai/tasks/{stopped['id']}/discard", {}), 200)
    assert gone["state"] == "cancelled" and gone["draftId"] is None


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_never_writes_live_data_by_a_batch_or_an_import(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session whose grants include bulk, when it posts a batch and an import that name no
    change set, then both are refused 403 and the workspace's records are as they were."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    out = tmp_path / "live.json"
    items = [
        {
            "op": "update",
            "target": {"id": record["id"]},
            "expectedVersion": record["version"],
            "name": "Taken live",
        }
        for record in ledgers.records.values()
    ]
    settings = _assistant(
        world,
        tmp_path,
        monkeypatch,
        ledgers.workspace,
        api=True,
        live={"items": items, "profile": {"sources": []}, "out": str(out)},
    )
    key = world.key("R")

    def records():
        page = ok(world.api.get(f"/objects/{key}", workspaceKey=ledgers.workspace, pageSize=500))
        return sorted((item["id"], item["version"], item["name"]) for item in page["items"])

    before = records()
    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    _run(world)
    answers = json.loads(out.read_text())
    assert (answers["batch"][0], answers["import"][0]) == (403, 403), answers
    assert records() == before and settings["workspace"] == ledgers.workspace


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_is_taken_at_its_word_for_neither_a_draft_nor_a_change_set_it_did_not_make(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session that names, in its own words, a draft and a change set another client made,
    when its turns end, then the draft is not proposed (and stays, for discarding it would delete a
    person's), and the change set is not handed over as the load; a draft it made itself is
    proposed."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    settings = _assistant(world, tmp_path, monkeypatch, ledgers.workspace, verified=True, api=True)
    config = tmp_path / "config.json"

    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "failed" and task["draftId"] is None
    assert any("not its own" in note["text"] for note in task["notes"]), task["notes"]
    assert ok(world.api.get(f"/model-drafts/{settings['draft']}"))["id"] == settings["draft"]

    # A proposal on a person's draft goes back to the session, which makes its own and lands.
    config.write_text(json.dumps({**settings, "ownOnSecond": True}))
    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked" and task["draftId"] != settings["draft"], task["notes"]

    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    _run(world)
    task = _task(world, task)
    # The change set it names was made by the test's client: not a load of the task's.
    assert task["state"] == "failed" and task["result"] is None
    assert ok(world.api.get(f"/change-sets/{settings['changeSet']}"))["id"] == settings["changeSet"]


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
def test_a_job_the_session_queues_runs_under_its_grants_even_when_the_session_has_stopped(
    world, tmp_path, monkeypatch
):
    """Given a session that uploads a workbook to its draft and stops before the profile ran, when
    the job worker reaches the job, then it completes: the session does not hold that worker, and
    its grants stay until the job is done, ending after that."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import AiTask, Job

    ledgers = Ledgers(world)
    state = world.api.client.app.state
    script = tmp_path / "stand_in.py"
    script.write_text(WAITING_STAND_IN)
    script.chmod(0o755)
    draft = ok(world.api.post("/model-drafts", {"name": "A proposal", "model": {}}), 201)
    (tmp_path / "config.json").write_text(json.dumps({"draft": draft["id"]}))
    monkeypatch.setenv("AI_AGENT_COMMAND", str(script))
    _trust_stand_in(monkeypatch)
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
        # The checklist follows what the engine recorded, for this client since the turn began.
        with SessionLocal() as db:
            since = datetime.now(UTC) - timedelta(minutes=1)
            client = db.scalar(select(AiTask.client_id).where(AiTask.public_id == task["id"]))
            done = lambda: {
                step["key"]: step["done"]
                for step in agent._reached(db, client, False, False, ledgers.workspace, since)[0]
            }
            assert done() == {"draft": False, "operations": False, "check": False}
            created = world.api.client.post(
                "/api/v1/model-drafts",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Its own", "model": {}},
            )
            assert created.status_code == 201, created.text
            db.rollback()
            assert done() == {"draft": True, "operations": False, "check": False}
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
        f"/api/v1/workspaces/{ledgers.workspace}/model",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert answer.status_code == 403


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true")
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
            f"/workspaces/{ledgers.workspace}/change-sets",
            {"name": "Its load", "source": "currentLive"},
        ),
        201,
    )
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    with SessionLocal() as session:
        job = session.scalar(select(Job).where(Job.id == task["jobId"]))
        token, _, grants = agent._access(session, job, agent.load_task(session, task["id"]))
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


# --- AP9: who did it ----------------------------------------------------------------------------


def _session_of(world, task):
    """The session's own token for the task's turn, as the engine issues it, and the world as the
    session sees it; with its client's id and its grants, to end them."""
    from sqlalchemy import select
    from test_j40_authorization import _as

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import Job

    with SessionLocal() as session:
        job = session.scalar(select(Job).where(Job.id == task["jobId"]))
        token, client, grants = agent._access(session, job, agent.load_task(session, task["id"]))
        session.commit()
    return _as(world, token), client, grants


def _ledger_values(ledgers, key, number=7):
    return {"R.u": key, "R.q": "Owner", "R.x1": "Sum", "R.n": number}


def _staged_in(world, change_set):
    return {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
    }


@pytest.mark.journey("J50.31")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true", AI_TASK_RETENTION_DAYS="30")
def test_what_a_session_proposes_is_marked_to_the_publication_and_after_the_task_is_gone(world):
    """Given a steward whose session writes into a change set (a new record and a removal), when the
    steward edits one value and publishes, then every row the session wrote names the AI, the task
    and who asked (and no confidence or reason), the edit adds who edited, the record's history
    names both beside the steward as the actor, and it reads the same once the task has expired."""
    from sqlalchemy import select, update

    from app.db import SessionLocal
    from app.models.database import AiTask, ChangeSetObject

    ledgers = Ledgers(world)
    me = ok(world.api.get("/me"))
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    agent_world, _, _ = _session_of(world, task)
    change_set = agent_world.change_set(ledgers.workspace)
    key = f"{ledgers.tag}-AI"
    created = agent_world.made(
        "R",
        "Proposed ledger",
        workspace=ledgers.workspace,
        change_set=change_set,
        values=_ledger_values(ledgers, key),
    )
    removed = ledgers.records[f"{ledgers.tag}-00"]
    ok(
        agent_world.api.delete(
            f"/objects/{world.key('R')}/{removed['id']}",
            **_staged_in(world, change_set),
            expectedVersion=removed["version"],
        ),
        204,
    )

    with SessionLocal() as session:
        rows = session.scalars(
            select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set["id"])
        ).all()
        assert {row.object_id for row in rows} >= {created["id"], removed["id"]}
        assert any(row.is_deleted and row.object_id == removed["id"] for row in rows)
        for row in rows:
            assert row.origin["kind"] == "ai" and row.origin["proposedBy"] == me["id"], row.origin
            assert row.origin["taskId"] == task["id"]
            assert "confidence" not in row.origin and "reason" not in row.origin

    proposed = world.record("R", created["id"], changeSetId=change_set["id"])
    assert proposed["origin"]["kind"] == "ai" and proposed["origin"]["taskId"] == task["id"]
    assert proposed["origin"]["proposedByName"] == me["name"]
    assert "editedBy" not in proposed["origin"] and "confidence" not in proposed["origin"]

    # The steward changes one value: the mark stays and says who.
    body = {
        "expectedVersion": proposed["version"],
        "attributes": [{"attributeTypeKey": world.key("R.n"), "value": 99}],
        **_staged_in(world, change_set),
    }
    ok(world.api.patch(f"/objects/{world.key('R')}/{created['id']}", body))
    edited = world.record("R", created["id"], changeSetId=change_set["id"])
    assert edited["origin"]["taskId"] == task["id"]
    assert (
        edited["origin"]["editedBy"] == me["id"] and edited["origin"]["editedByName"] == me["name"]
    )

    world.publish(change_set, ledgers.workspace)

    def trail(record_id):
        history = ok(world.api.get(f"/objects/{world.key('R')}/{record_id}/history"))["items"]
        return [item for item in history if item.get("origin")]

    [entry] = trail(created["id"])
    assert entry["actor"]["id"] == me["id"]
    assert entry["origin"]["kind"] == "ai" and entry["origin"]["taskId"] == task["id"]
    assert (
        entry["origin"]["proposedByName"] == me["name"]
        and entry["origin"]["proposedBy"] == me["id"]
    )
    assert entry["origin"]["editedByName"] == me["name"]
    assert "confidence" not in entry["origin"] and "reason" not in entry["origin"]

    # The task goes with its retention; what was recorded of it does not.
    with SessionLocal() as session:
        session.execute(
            update(AiTask)
            .where(AiTask.public_id == task["id"])
            .values(expires_at=datetime.now(UTC) - timedelta(days=1))
        )
        session.commit()
    world.api.client.app.state.job_worker.sweep()
    refused(world.api.get(f"/ai/tasks/{task['id']}"), 404, "AI_TASK_NOT_FOUND")
    assert trail(created["id"]) == [entry]


@pytest.mark.journey("J50.32")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true")
def test_two_tasks_at_once_each_have_a_client_of_their_own_and_reach_only_their_own(world):
    """Given two tasks in two workspaces, then each has its own client of the kind session, one's
    token is refused in the other's workspace, one's steps and wait do not count the other's draft
    and queued job, and the clients are listed only when asked for and take no secret."""
    import types

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import AiTask, Job, OAuthClient

    one, two = Ledgers(world, 2), Ledgers(world, 2)
    first = ok(_create(world, one.workspace, one.book()), 202)
    second = ok(_create(world, two.workspace, two.book()), 202)
    a, client_a, _ = _session_of(world, first)
    b, client_b, _ = _session_of(world, second)

    with SessionLocal() as session:
        clients = {
            task: session.scalar(select(AiTask.client_id).where(AiTask.public_id == task))
            for task in (first["id"], second["id"])
        }
        assert clients[first["id"]] == client_a != client_b == clients[second["id"]]
        rows = {
            client.id: client
            for client in session.scalars(
                select(OAuthClient).where(OAuthClient.id.in_([client_a, client_b]))
            )
        }
        assert {row.kind for row in rows.values()} == {"session"}
        public = [rows[client_a].public_id, rows[client_b].public_id]

    assert a.api.get(f"/workspaces/{one.workspace}/model").status_code == 200
    assert a.api.get(f"/workspaces/{two.workspace}/model").status_code == 403
    assert b.api.get(f"/workspaces/{one.workspace}/model").status_code == 403

    # B starts a draft and queues a job; A's steps and A's wait do not see them.
    since = datetime.now(UTC) - timedelta(minutes=1)
    draft = ok(b.api.post("/model-drafts", {"name": "B's own", "model": {}}), 201)
    upload = b.api.client.post(
        "/api/v1/source-files",
        files={"file": ("ledgers.xlsx", two.book(), XLSX)},
        data={
            "request": json.dumps(
                {"owner": {"draftId": draft["id"]}, "workspaceKey": two.workspace}
            )
        },
    )
    assert upload.status_code == 201, upload.text
    with SessionLocal() as session:
        queued = session.scalars(
            select(Job).where(Job.requested_by_client_id == client_b, Job.state == "queued")
        ).all()
        assert queued
        steps = lambda client, workspace: {
            step["key"]: step["done"]
            for step in agent._reached(session, client, False, False, workspace, since)[0]
        }
        assert steps(client_a, one.workspace)["draft"] is False
        assert steps(client_b, two.workspace)["draft"] is True
        began = time.monotonic()
        agent._await_its_jobs(session, types.SimpleNamespace(check=lambda: None), began, client_a)
        assert time.monotonic() - began < 1.5

    listed = {item["id"] for item in _all(world, "/clients")}
    assert not listed & set(public)
    sessions = {item["id"] for item in _all(world, "/clients", kind="session")}
    assert set(public) <= sessions
    version = ok(world.api.get(f"/clients/{public[0]}"))["version"]
    refused(
        world.api.post(f"/clients/{public[0]}/secrets", {"expectedVersion": version}),
        409,
        "CLIENT_HAS_NO_SECRETS",
    )


@pytest.mark.journey("J50.33")
@pytest.mark.structures(*STRUCTURES, "G")
@pytest.mark.settings(AI_AGENT_COMMAND="true")
def test_a_session_holds_no_more_than_the_person_who_asked(world):
    """Given a person whose writes are narrowed to one record type and who also holds publishing
    and model activation, when they start a task, then its session writes that type, is refused
    another with 403, and is refused publishing and activation, as the engine keeps those from every
    session."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world, 2)
    scope = {"workspaceKey": ledgers.workspace}
    _, person = _client(
        world,
        "narrowed",
        ("steward", {**scope, "recordTypes": [world.key("R")]}),
        ("model-admin", scope),
    )
    task = ok(_create(person, ledgers.workspace, ledgers.book()), 202)
    session_world, _, _ = _session_of(person, task)
    change_set = session_world.change_set(ledgers.workspace)
    session_world.made(
        "R",
        "Allowed",
        workspace=ledgers.workspace,
        change_set=change_set,
        values=_ledger_values(ledgers, f"{ledgers.tag}-OK"),
    )
    refused(
        session_world.create(
            "G",
            "Not allowed",
            workspace=ledgers.workspace,
            change_set=session_world.current(change_set),
        ),
        403,
        "FORBIDDEN",
    )
    current = session_world.current(change_set)
    publication = session_world.api.post(
        f"/change-sets/{change_set['id']}/publication",
        {"expectedChangeSetVersion": current["version"]},
    )
    assert publication.status_code == 403, publication.text
    activation = session_world.api.post(
        f"/workspaces/{ledgers.workspace}/model/activation",
        {"releaseId": "x", "expectedVersion": 1, "expectedReleaseId": "y"},
    )
    assert activation.status_code == 403, activation.text


@pytest.mark.journey("J50.34")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true")
def test_a_session_cannot_get_the_person_who_asked_to_be_the_second_person(world):
    """Given a workspace that requires a second person, when a session submits its change set, then
    the submitter is the person who asked, their own approval is refused 403 ownApproval, and
    another person's approval publishes it."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world, 2)
    me = ok(world.api.get("/me"))
    policy = f"/workspaces/{ledgers.workspace}/approval-policy"
    ok(
        world.api.put(
            policy,
            {
                "requireApproval": True,
                "secondPerson": True,
                "expectedVersion": ok(world.api.get(policy))["version"],
            },
        )
    )
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    session_world, _, _ = _session_of(world, task)
    change_set = session_world.change_set(ledgers.workspace)
    session_world.made(
        "R",
        "Awaiting a second person",
        workspace=ledgers.workspace,
        change_set=change_set,
        values=_ledger_values(ledgers, f"{ledgers.tag}-4E"),
    )
    ok(
        session_world.api.post(
            f"/change-sets/{change_set['id']}/submission",
            {"expectedChangeSetVersion": session_world.current(change_set)["version"]},
        ),
        201,
    )
    requests = f"/workspaces/{ledgers.workspace}/publication-requests"
    [request] = ok(world.api.get(requests))["items"]
    assert request["state"] == "submitted" and request["submitter"]["id"] == me["id"]

    def decide(actor):
        publications = ok(
            actor.api.get(f"/workspaces/{ledgers.workspace}/publications", pageSize=1)
        )
        active = [item["id"] for item in publications["items"] if item.get("status") == "active"]
        return actor.api.post(
            f"/change-sets/{change_set['id']}/decisions",
            {
                "outcome": "approve",
                "expectedChangeSetVersion": world.current(change_set)["version"],
                "expectedActivePublicationId": active[0] if active else None,
            },
        )

    own = refused(decide(world), 403, "FORBIDDEN")
    assert own["details"]["reason"] == "ownApproval"
    _, other = _client(world, "second person", ("owner", {"workspaceKey": ledgers.workspace}))
    ok(decide(other))
    [request] = ok(world.api.get(requests))["items"]
    assert request["state"] == "approved"


CALLS_STAND_IN = """#!/usr/bin/env python3
import json, os, sys
config = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")))
def line(**event):
    print(json.dumps(event), flush=True)
line(type="system", subtype="init", model="claude-test-1")
usage = {"input_tokens": 10, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 5,
         "output_tokens": 20}
for message_id in ("msg_1", "msg_1", "msg_2"):
    line(type="assistant", message={"id": message_id, "usage": usage,
                                    "content": [{"type": "text", "text": "Working."}]})
if config.get("proposal", True):
    json.dump({"draftId": config["draft"], "summary": "A plan.", "questions": []},
              open("proposal.json", "w"))
if "cost" in config:
    line(type="result", result="Ready.", total_cost_usd=config["cost"])
"""


@pytest.mark.journey("J50.35")
@pytest.mark.structures(*STRUCTURES)
def test_every_turn_of_a_session_leaves_one_call_with_its_tokens_and_cost(
    world, tmp_path, monkeypatch
):
    """Given a session whose stream repeats a message and reports a running cost, then a finished
    turn leaves one call with the tokens counted once and its cost, the next turn only the
    difference, a worker that died leaves its call from the log at the next turn, a cancelled turn
    and a turn with no answer fail with their kind, no content is kept unless AI_LOG_CONTENT is on,
    and the totals carry the cost."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import AiTask

    ledgers = Ledgers(world)
    script = tmp_path / "stand_in.py"
    script.write_text(CALLS_STAND_IN)
    script.chmod(0o755)
    draft = ok(world.api.post("/model-drafts", {"name": "A proposal", "model": {}}), 201)
    settings = {"draft": draft["id"], "cost": 0.4}
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    monkeypatch.setenv("AI_AGENT_COMMAND", str(script))
    _trust_stand_in(monkeypatch)
    files = world.api.client.app.state.job_worker.files

    def calls(task):
        return [c for c in _all(world, "/ai/calls") if c.get("taskId") == task["id"]]

    def spent():
        return ok(world.api.get("/ai/status"))["totals"]["costUsd"]

    def turn(task, words, **changes):
        config.write_text(json.dumps({**settings, **changes}))
        ok(
            world.api.post(
                f"/ai/tasks/{task['id']}/model",
                {"expectedVersion": _task(world, task)["version"], "correction": words},
            ),
            202,
        )
        _run(world)

    before = spent()
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    _run(world)
    [first] = calls(task)
    assert first["purpose"] == "assistantSession" and first["outcome"] == "answered"
    assert first["model"] == "claude-test-1"
    assert (first["tokensIn"], first["tokensOut"]) == (2 * 115, 2 * 20)
    assert first["costUsd"] == 0.4 and first["content"] is None

    turn(task, "Again", cost=1.26)
    [second, same] = calls(task)
    assert same["id"] == first["id"] and second["costUsd"] == 0.86
    assert round(spent() - before, 4) == 1.26

    # A worker that died leaves a log and its process record; the next turn writes its call.
    folder = Path(files.directory) / "agent" / task["id"]
    (folder.parent / f"{task['id']}.dead.log").write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {"id": "m9", "usage": {"input_tokens": 7, "output_tokens": 3}},
            }
        )
        + "\n"
    )
    with SessionLocal() as session:
        row = agent.load_task(session, task["id"], for_update=True)
        row.design = {
            **row.design,
            "agentProcess": {
                "pid": 2**22 + 1,
                "session": "gone",
                "log": f"{task['id']}.dead.log",
                "startedAt": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                "job": None,
            },
        }
        session.commit()
    turn(task, "Once more", cost=1.5)
    [latest, *_] = calls(task)
    [died] = [c for c in calls(task) if c["failureKind"] == "interrupted"]
    assert died["failureKind"] == "interrupted" and died["outcome"] == "failed"
    assert (died["tokensIn"], died["tokensOut"], died["costUsd"]) == (7, 3, None)
    assert latest["outcome"] == "answered" and latest["costUsd"] == 0.24

    # A turn a person cancelled, with the content kept as the setting says.
    content_on = agent.get_settings().model_copy(update={"ai_log_content": True})
    monkeypatch.setattr(agent, "get_settings", lambda: content_on)
    with SessionLocal() as session:
        agent._record_turn(
            session,
            task["id"],
            None,
            agent._Progress(tmp_path / "none.log"),
            datetime.now(UTC),
            "Why?",
            ("cancelled", "Cancelled by a person."),
        )
    [cancelled] = [c for c in calls(task) if c["failureKind"] == "cancelled"]
    assert cancelled["failureKind"] == "cancelled" and cancelled["outcome"] == "failed"
    assert cancelled["content"]["instructions"] == "Why?"

    # A session that ends with no result line has failed, and reports no cost.
    other = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    config.write_text(json.dumps({"draft": draft["id"], "proposal": False}))
    _run(world)
    [ended] = calls(other)
    assert ended["outcome"] == "failed" and ended["failureKind"] == "failed"
    assert ended["costUsd"] is None and ended["tokensIn"] == 230
    with SessionLocal() as session:
        assert (
            session.scalar(select(AiTask.state).where(AiTask.public_id == other["id"])) == "failed"
        )


@pytest.mark.journey("J50.36")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true")
def test_a_tasks_folder_and_transcript_go_with_it_and_the_sweep_removes_what_no_task_holds(
    world, tmp_path, monkeypatch
):
    """Given two tasks with a folder and a transcript each, when one task's folder is removed, then
    its folder and transcript go and the other's stay; the sweep removes a folder no task holds and
    a transcript of this instance's folders whose folder is gone, and leaves another path's."""
    from app.db import SessionLocal
    from app.engine.tasks import agent

    ledgers = Ledgers(world, 2)
    config_dir = tmp_path / "claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config_dir))
    projects = config_dir / "projects"
    files = world.api.client.app.state.job_worker.files
    tasks = [ok(_create(world, ledgers.workspace, ledgers.book()), 202) for _ in range(2)]

    def keep(folder):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "workbook.xlsx").write_bytes(b"x")
        transcript = projects / agent._transcript_name(folder)
        transcript.mkdir(parents=True, exist_ok=True)
        (transcript / "session.jsonl").write_text("{}")
        return folder, transcript

    with SessionLocal() as session:
        held = [agent.load_task(session, task["id"]) for task in tasks]
        mine, theirs = [keep(agent.folder_of(files, task)) for task in held]
        agent.remove_folder(files, held[0])
    assert not mine[0].exists() and not mine[1].exists()
    assert theirs[0].is_dir() and theirs[1].is_dir()

    root = Path(files.directory) / "agent"
    stray = root / str(uuid4())
    stray.mkdir()
    orphan = projects / f"{agent._transcript_name(root)}-{uuid4()}"
    orphan.mkdir()
    foreign = projects / f"-somewhere-else-{uuid4()}"
    foreign.mkdir()
    with SessionLocal() as session:
        agent.sweep(session, files)
    assert not stray.exists() and not orphan.exists()
    assert foreign.is_dir() and theirs[0].is_dir() and theirs[1].is_dir()


# --- AP10: one switch, the profile a load leaves, the warning and the leftovers ---------------------


def _profile_of(world, ledgers, **source):
    return {"name": "Ledgers", "sources": [_records_source(world, ledgers, **source)]}


def _lines(settings):
    return len(Path(settings["log"]).read_text().splitlines())


def _keys(world):
    return {item["key"] for item in _all(world, "/import-profiles")}


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
def test_the_command_alone_turns_the_assistant_on(world, tmp_path, monkeypatch):
    """Given only AI_AGENT_COMMAND and no AI_PROVIDER, then the system says the assistant is on
    and no provider is set, and a task runs to a proposal."""
    ledgers = Ledgers(world)
    _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    system = ok(world.api.get("/system"))["ai"]
    assert system["assistant"] is True and system["configured"] is False
    assert ok(world.api.get("/ai/status"))["assistant"] is True
    task = _read(world, ledgers, accept=False)
    assert task["state"] == "checked" and task["design"]["stage"] == "model"


@pytest.mark.journey("J50.30")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_provider_alone_does_not_turn_the_assistant_on(world):
    """Given only AI_PROVIDER, then a task is refused with 409 AI_NOT_CONFIGURED and the system
    says the assistant is off while the provider is set."""
    ledgers = Ledgers(world)
    refused(_create(world, ledgers.workspace, ledgers.book()), 409, "AI_NOT_CONFIGURED")
    system = ok(world.api.get("/system"))["ai"]
    assert system["assistant"] is False and system["configured"] is True
    assert ok(world.api.get("/ai/tasks"))["items"] == []


@pytest.mark.journey("J50.37")
@pytest.mark.structures(*STRUCTURES)
def test_a_load_leaves_a_profile_and_the_same_file_then_needs_no_assistant(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session that runs a real import with an inline profile keyed by the type's unique
    attribute into its change set, when the steward accepts, then the task names a saved profile
    that validates; after the change set is published the same file given as a new task takes the
    saved layout's path (no session is asked) and its load changes nothing."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    book = ledgers.book([*ledgers.rows, ledgers.new(1)])
    settings = _assistant(
        world,
        tmp_path,
        monkeypatch,
        ledgers.workspace,
        api=True,
        profile=_profile_of(world, ledgers),
    )
    task = _accept(world, _read(world, ledgers, book, accept=False))
    assert task["state"] == "loaded", task["notes"]
    result = task["result"]
    assert result["counts"]["created"] == 1 and result["profileNotSaved"] is None
    stored = ok(world.api.get(f"/import-profiles/{result['profileKey']}"))
    assert stored["valid"] is True
    world.publish({"id": settings["changeSet"]}, ledgers.workspace)
    asked = _lines(settings)

    again = _read(world, ledgers, book, accept=False)
    # The design carries no session (the field is null): the saved layout's path, no assistant.
    assert again["state"] == "checked" and again["design"].get("agentSession") is None
    again = _load(world, _accept(world, again))
    assert again["state"] == "loaded", again["notes"]
    assert again["result"]["counts"]["created"] == 0 and again["result"]["counts"]["updated"] == 0
    assert _lines(settings) == asked
    assert f"Newcomer {ledgers.tag} 1" in ledgers.live() and len(ledgers.live()) == 11


@pytest.mark.journey("J50.37")
@pytest.mark.structures(*STRUCTURES)
def test_a_sheet_the_profile_left_out_does_not_ask_the_assistant_again_and_a_new_one_does(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a load of a workbook with a helper sheet its profile does not read, when the same file
    comes again, then no session is asked; when a sheet the earlier file did not have comes, one is.
    Found on a real workbook, whose helper sheets kept every repeat from the saved layout's path."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)

    def with_sheets(*names):
        book = load_workbook(BytesIO(ledgers.book([*ledgers.rows, ledgers.new(1)])))
        for name in names:
            book.create_sheet(name).append(["Note"])
            book[name].append(["for reading only"])
        out = BytesIO()
        book.save(out)
        return out.getvalue()

    settings = _assistant(
        world,
        tmp_path,
        monkeypatch,
        ledgers.workspace,
        api=True,
        profile=_profile_of(world, ledgers),
    )
    task = _accept(world, _read(world, ledgers, with_sheets("Helper"), accept=False))
    assert task["result"]["profileKey"], task["result"]
    world.publish({"id": settings["changeSet"]}, ledgers.workspace)
    asked = _lines(settings)

    again = _read(world, ledgers, with_sheets("Helper"), accept=False)
    assert again["state"] == "checked" and again["design"].get("agentSession") is None
    assert _lines(settings) == asked

    _next_draft(world, tmp_path, settings)
    grown = _read(world, ledgers, with_sheets("Helper", "Another"), accept=False)
    assert grown["design"].get("agentSession") is not None and _lines(settings) > asked


@pytest.mark.journey("J50.38")
@pytest.mark.structures(*STRUCTURES)
def test_a_load_says_why_it_left_no_profile(world, tmp_path, monkeypatch, served):  # noqa: F811
    """Given a session whose upsert source has no key, then the task says which sheet and saves no
    profile; given a session that changed the records only through batches, it says so too."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    before = _keys(world)
    _assistant(
        world,
        tmp_path,
        monkeypatch,
        ledgers.workspace,
        api=True,
        profile=_profile_of(world, ledgers, key=None),
    )
    keyless = _accept(world, _read(world, ledgers, ledgers.book([ledgers.new(1)]), accept=False))
    assert keyless["state"] == "loaded", keyless["notes"]
    assert keyless["result"]["profileKey"] is None
    assert "“Records”" in keyless["result"]["profileNotSaved"]
    assert "key" in keyless["result"]["profileNotSaved"]
    assert _keys(world) == before

    batch = [
        {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": f"Batch ledger {ledgers.tag}",
            "attributes": [
                {"attributeTypeKey": world.key(key), "value": value}
                for key, value in _ledger_values(ledgers, f"{ledgers.tag}-B1").items()
            ],
        }
    ]
    other = Ledgers(world, 2)
    tmp = tmp_path / "batches"
    tmp.mkdir()
    _assistant(world, tmp, monkeypatch, other.workspace, api=True, batch=batch)
    batches = _accept(world, _read(world, other, other.book(), accept=False))
    assert batches["state"] == "loaded", batches["notes"]
    assert batches["result"]["profileKey"] is None
    assert "did not import the workbook" in batches["result"]["profileNotSaved"]
    assert _keys(world) == before


@pytest.mark.journey("J50.39")
@pytest.mark.structures(*STRUCTURES)
def test_new_rows_beside_the_records_held_are_warned_of_and_may_still_be_accepted(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session whose dry run creates rows of a type the workspace holds records of, then
    the proposal carries an open check of kind besideHeld naming both figures, and Accept loads."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    model = copy.deepcopy(world.configuration.model)
    _assistant(
        world,
        tmp_path,
        monkeypatch,
        ledgers.workspace,
        model=model,
        api=True,
        dryRun=True,
        profile=_profile_of(world, ledgers),
    )
    book = ledgers.book([ledgers.new(1), ledgers.new(2)])
    task = _read(world, ledgers, book, accept=False)
    assert task["state"] == "checked", task["notes"]
    [warning] = [c for c in task["design"]["checks"] if c["kind"] == "besideHeld"]
    assert warning["open"] is True
    assert "2 new" in warning["text"] and "10 held" in warning["text"]
    task = _accept(world, task)
    assert task["state"] == "loaded", task["notes"]
    assert task["result"]["counts"]["created"] == 2


@pytest.mark.journey("J50.39")
@pytest.mark.structures(*STRUCTURES)
def test_an_empty_cell_is_no_skipped_row_and_a_value_nothing_holds_is(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a workbook whose every row one source writes, and a second source keyed by a column
    empty on one row. When the second reads only columns the first holds, then nothing is skipped
    and no relationship reads as unchanged. When it also reads a column of its own, then that row's
    value is held by nothing and the row is counted skipped."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    book = ledgers.book([ledgers.new(1), [*ledgers.new(2)[:3], "", 7]])
    whole = _records_source(world, ledgers)
    whole["columns"] = [c for c in whole["columns"] if c["column"] != ledgers.score]
    whole["rowsWithoutKey"] = "skip"
    summary = {"column": ledgers.summary, "attributeTypeKey": world.key("R.x1")}
    sparse = {
        **whole,
        "key": {"attributeTypeKeys": [world.key("R.x1"), world.key("R.q")]},
        "columns": [
            {"column": "Name", "field": "name"},
            summary,
            {"column": ledgers.owner, "attributeTypeKey": world.key("R.q")},
        ],
    }

    def checked(name, second):
        tmp = tmp_path / name
        tmp.mkdir()
        _assistant(
            world,
            tmp,
            monkeypatch,
            ledgers.workspace,
            model=copy.deepcopy(world.configuration.model),
            api=True,
            dryRun=True,
            profile={"name": "Ledgers", "sources": [whole, second]},
        )
        task = _read(world, ledgers, book, accept=False)
        assert task["state"] == "checked", task["notes"]
        return task["check"]

    check = checked("empty", sparse)
    assert check["summary"]["skipped"] == 0, check
    assert not [r for r in check["refused"] if r["code"] == "ROWS_SKIPPED"]

    score = {"column": ledgers.score, "attributeTypeKey": world.key("R.n")}
    check = checked("lost", {**sparse, "columns": [*sparse["columns"], score]})
    assert check["summary"]["skipped"] == 1, check


@pytest.mark.journey("J50.40")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_may_not_take_the_draft_another_task_holds(world, tmp_path, monkeypatch):
    """Given a task holding a draft, when a second task's session client writes that draft, then it
    is refused with 409 AI_TASK_DRAFT_HELD and goes on with a draft of its own; and when the
    second task's session proposes the held draft, that task fails."""
    ledgers = Ledgers(world)
    settings = _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    first = _read(world, ledgers, accept=False)
    assert first["draftId"] == settings["draft"]
    held = ok(world.api.get(f"/model-drafts/{settings['draft']}"))

    second = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    session, _, _ = _session_of(world, second)
    error = refused(
        session.api.patch(
            f"/model-drafts/{settings['draft']}",
            {"expectedVersion": held["version"], "name": "Taken"},
        ),
        409,
        "AI_TASK_DRAFT_HELD",
    )
    assert error["details"]["draftId"] == settings["draft"]
    own = ok(session.api.post("/model-drafts", {"name": "Its own", "model": {}}), 201)
    ok(
        session.api.patch(
            f"/model-drafts/{own['id']}", {"expectedVersion": own["version"], "name": "Mine"}
        )
    )
    assert ok(world.api.get(f"/model-drafts/{settings['draft']}"))["name"] == held["name"]

    _run(world)
    second = _task(world, second)
    assert second["state"] == "failed" and "another task holds" in second["notes"][-1]["text"]
    assert _task(world, first)["state"] == "checked"


@pytest.mark.journey("J50.41")
@pytest.mark.structures(*STRUCTURES)
def test_a_release_the_session_installed_and_nothing_uses_is_retired_when_its_session_ends(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session that installs two releases and puts its change set on one, when the task
    loads, then both stay while the session lives (AP-D56); when the task ends, the one nothing
    runs is retired."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    batch = [
        {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": f"Batch ledger {ledgers.tag}",
            "attributes": [
                {"attributeTypeKey": world.key(key), "value": value}
                for key, value in _ledger_values(ledgers, f"{ledgers.tag}-B1").items()
            ],
        }
    ]
    settings = _assistant(
        world, tmp_path, monkeypatch, ledgers.workspace, api=True, releases=True, batch=batch
    )
    task = _accept(world, _read(world, ledgers, accept=False))
    assert task["state"] == "loaded", task["notes"]
    version = world.configuration.model["release"]["version"]
    status = {
        item["version"]: item["status"]
        for item in _all(world, "/model-releases")
        if item["version"].startswith(version)
    }
    assert status[f"{version}-used"] == "active" and status[f"{version}-unused"] == "active"
    used = ok(world.api.get(f"/change-sets/{settings['changeSet']}"))["modelReleaseId"]
    assert ok(world.api.get(f"/model-releases/{used}"))["version"] == f"{version}-used"
    ok(world.api.post(f"/ai/tasks/{task['id']}/discard", {}), 200)
    status = {
        item["version"]: item["status"]
        for item in _all(world, "/model-releases")
        if item["version"].startswith(version)
    }
    assert status[f"{version}-unused"] == "retired"


@pytest.mark.journey("J50.41")
@pytest.mark.structures(*STRUCTURES)
def test_a_load_that_only_adds_relationships_is_a_load_and_an_empty_one_says_why(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session whose change set only links records that already exist, when the task is
    accepted, then it is loaded and the result counts the new relationships; given a session whose
    change set holds nothing, then the task fails with a note that says so."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    token = world.made(
        "K", f"Token {ledgers.tag}", workspace=ledgers.workspace, values={"K.code": ledgers.tag}
    )
    ledger = ledgers.records[f"{ledgers.tag}-00"]
    batch = [
        {
            "op": "createRelation",
            "relationTypeKey": world.key("B1n"),
            "from": {"id": ledger["id"]},
            "to": {"id": token["id"]},
        }
    ]
    _assistant(world, tmp_path, monkeypatch, ledgers.workspace, api=True, batch=batch)
    task = _accept(world, _read(world, ledgers, accept=False))
    assert task["state"] == "loaded", task["notes"]
    counts = task["result"]["counts"]
    assert (counts["created"], counts["updated"], counts["relationsCreated"]) == (0, 0, 1), counts

    # A change set holding nothing is no load, and the person is told.
    empty = tmp_path / "empty"
    empty.mkdir()
    _assistant(world, empty, monkeypatch, ledgers.workspace, api=True)
    task = _accept(world, _read(world, ledgers, accept=False))
    assert task["state"] == "failed" and task["result"] is None
    assert any("nothing was loaded" in note["text"] for note in task["notes"]), task["notes"]


# --- AP11: a session's log lies beside its folder ---------------------------------------------------


@pytest.mark.journey("J50.44")
@pytest.mark.structures(*STRUCTURES)
def test_a_sessions_folder_holds_no_log_and_a_discarded_task_leaves_neither(
    world, tmp_path, monkeypatch
):
    """Given a session turn on the test command, when it runs, then the folder holds the workbook,
    model and OpenAPI and no log, the turn is in the call record, and a discarded task leaves
    neither the folder nor the log."""
    ledgers = Ledgers(world)
    settings = _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    files = world.api.client.app.state.job_worker.files
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked"
    seen = json.loads(Path(settings["log"]).read_text().splitlines()[0])["files"]
    assert {"workbook.xlsx", "model.json", "openapi.json"} <= set(seen)
    assert not [name for name in seen if name.endswith(".log")]
    root = Path(files.directory) / "agent"
    folder = root / task["id"]
    assert folder.is_dir() and not list(folder.glob("*.log"))
    assert [c["outcome"] for c in _all(world, "/ai/calls") if c.get("taskId") == task["id"]] == [
        "answered"
    ]
    ok(world.api.post(f"/ai/tasks/{task['id']}/discard", {}), 200)
    assert not folder.exists() and not list(root.glob(f"{task['id']}.*"))


@pytest.mark.journey("J50.45")
@pytest.mark.structures(*STRUCTURES)
def test_a_turn_a_worker_stopped_in_is_recorded_from_its_log_in_the_new_place(
    world, tmp_path, monkeypatch
):
    """Given a worker stopped during a turn, when the job comes back, then the turn is recorded as
    interrupted from its log, which lies beside the session's folder."""
    from app.db import SessionLocal
    from app.engine.tasks import agent

    ledgers = Ledgers(world)
    _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    files = world.api.client.app.state.job_worker.files
    task = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked"
    name = f"{task['id']}.session-dead.log"
    folder = Path(files.directory) / "agent" / task["id"]
    (folder.parent / name).write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {"id": "m9", "usage": {"input_tokens": 7, "output_tokens": 3}},
            }
        )
        + "\n"
    )
    with SessionLocal() as session:
        row = agent.load_task(session, task["id"], for_update=True)
        row.design = {
            **row.design,
            "agentProcess": {
                "pid": 2**22 + 1,
                "session": "gone",
                "log": name,
                "startedAt": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                "job": None,
            },
        }
        session.commit()
    ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/model",
            {"expectedVersion": task["version"], "correction": "Again"},
        ),
        202,
    )
    _run(world)
    [died] = [
        c
        for c in _all(world, "/ai/calls")
        if c.get("taskId") == task["id"] and c["failureKind"] == "interrupted"
    ]
    assert died["outcome"] == "failed" and (died["tokensIn"], died["tokensOut"]) == (7, 3)


# --- AQ: answers that keep the defaults cost nothing ------------------------------------------------


@pytest.mark.journey("J50.64")
@pytest.mark.structures(*STRUCTURES)
def test_answers_that_keep_the_assumed_choices_queue_no_turn_and_any_other_answer_does(
    world, tmp_path, monkeypatch
):
    """Given a proposal with a question and its assumed answer, when the person answers with the
    assumed option, then the answer is recorded, the task stays checked and no turn is queued; when
    the person answers otherwise, a turn is queued as before."""
    ledgers = Ledgers(world)
    settings = _assistant(world, tmp_path, monkeypatch, ledgers.workspace)
    log = Path(settings["log"])
    task = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    _run(world)
    task = _task(world, task)
    assert task["state"] == "checked" and task["design"]["questions"][0]["assumed"] == "A"
    turns = len(log.read_text().splitlines())

    kept = ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/answers",
            {"expectedVersion": task["version"], "answers": {"Which?": "A"}},
        ),
        202,
    )
    assert kept["state"] == "checked" and kept["jobId"] == task["jobId"]
    assert kept["version"] > task["version"] and kept["design"]["answers"] == {"Which?": "A"}
    _run(world)
    assert len(log.read_text().splitlines()) == turns
    assert _task(world, task)["state"] == "checked"

    _next_draft(world, tmp_path, settings)
    other = ok(
        world.api.post(
            f"/ai/tasks/{task['id']}/answers",
            {"expectedVersion": kept["version"], "answers": {"Which?": "B"}},
        ),
        202,
    )
    assert other["state"] == "checking" and other["jobId"] != task["jobId"]
    _run(world)
    assert len(log.read_text().splitlines()) == turns + 1
    assert "Which? B" in json.loads(log.read_text().splitlines()[-1])["prompt"]


# --- AT: a draft's dry run reads its own profile -----------------------------------------------------


@pytest.mark.journey("J50.62")
@pytest.mark.structures("K")
def test_a_drafts_dry_run_reads_the_profile_the_draft_holds(world):
    """Given a draft whose profile the inference built from W1, when its dry run is sent without a
    profile, then every row is read with the draft's own; and the profile the draft's profile read
    answered, sent back unchanged, gives the same figures."""
    import workbooks
    from test_j34_onboard import (
        _application,
        _draft_profile,
        _empty_draft,
        _infer,
        _profiled,
        _run,
    )
    from test_j34_onboard import _workspace as _onboarding

    workspace = _onboarding(world)
    draft = _empty_draft(world)
    book = workbooks.w1(rows=50)
    source = _profiled(
        world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace
    )
    _infer(world, draft)
    assert ok(_application(world, draft))["valid"] is True

    def dry_run(**profile):
        body = {"sourceFileId": source["id"], "workspaceKey": workspace, **profile}
        ok(world.api.post(f"/model-drafts/{draft['id']}/dry-run", body), 202)
        _run(world)
        done = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
        assert done["state"] == "completed", done["error"]
        return done["summary"]["rows"], [
            (s["sheet"], s["rows"], s["records"], s["rejections"])
            for s in done["summary"]["sources"]
        ]

    own = dry_run()
    assert own[0]["total"] >= 50 and own[0]["run"] == own[0]["total"]
    read = _draft_profile(world, draft)["profile"]
    # The read carries the editor's key, name and each source's id: sent back, they are ignored.
    assert read["key"] and read["sources"][0]["id"]
    assert dry_run(profile=read) == own
