"""J50.53 to J50.60 — Always a way out (0.16 AP13, AP-D22, AP-D54 to AP-D60).

At every state of a task the person has a way on, on the page itself: a failed or stopped turn takes
words and goes on in the same session; Stop ends the turn, not the task; a load that is wrong takes
words and loads again; the session lives until the work is in the person's hands for good; a
published task says so. The assistant is a stand-in session working through the API with the token
the engine gives it, so every permission and refusal is the engine's. Each case runs on two
configurations and names no configuration's keys.
"""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from scenario import ok, refused
from test_j24_job_stream import served  # noqa: F401  (the journey application over HTTP)
from test_j34_onboard import _all
from test_j37_workspace_migration import _confirm, _previewed
from test_j50_ai_reshape import Merge, _proposed
from test_j50_ai_workbook_load import (
    Ledgers,
    _accept,
    _create,
    _ledger_values,
    _read,
    _run,
    _task,
)

from app.engine.proposals import fake

STRUCTURES = ("R", "R.u", "R.n", "R.q", "R.x1")

WAY_OUT = """#!/usr/bin/env python3
import json, os, re, sys, time
folder = os.path.dirname(os.path.realpath(__file__))
config = json.load(open(os.path.join(folder, "config.json")))
prompt = sys.argv[sys.argv.index("--") + 1]
open(config["log"], "a").write(json.dumps({
    "prompt": prompt, "args": sys.argv[1:], "files": sorted(os.listdir("."))}) + "\\n")
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "input": {"command": "curl -X POST x/api/v1/model-drafts/d/dry-run"}}]}}))
if not os.path.exists("url.txt") and re.search(r"https?://[\\w.:-]+", prompt):
    open("url.txt", "w").write(re.search(r"https?://[\\w.:-]+", prompt).group(0))

def holding():
    if os.path.exists(os.path.join(folder, "hold")):
        open(os.path.join(folder, "holding"), "w").write("1")
        time.sleep(600)

if "accepted" in prompt or "do the load again" in prompt:
    import httpx
    base = open("url.txt").read() + "/api/v1"
    head = {"Authorization": "Bearer " + os.environ["REFIROO_TOKEN"]}
    def api(method, path, **kw):
        sent = httpx.request(method, base + path, headers=head, timeout=60, **kw)
        assert sent.status_code < 300, (method, path, sent.status_code, sent.text)
        return sent.json()
    made = api("POST", "/workspaces/" + config["workspace"] + "/change-sets",
               json={"name": config.get("name", "Its load"), "source": "currentLive"})
    holding()
    if config.get("die"):
        sys.exit(1)
    api("POST", "/batches", json={
        "changeSetId": made["id"], "expectedChangeSetVersion": made["version"],
        "policy": "independent", "run": "inline", "items": config["batch"]})
    print(json.dumps({"type": "result", "result": "Done.\\nCHANGE_SET: " + made["id"]}))
else:
    holding()
    draft = "no-such-draft" if config.get("fail") else config["draft"]
    json.dump({"draftId": draft, "summary": "A plan.", "questions": []}, open("proposal.json", "w"))
    print(json.dumps({"type": "result", "result": "Ready."}))
"""


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


class Way:
    """A stand-in session for one workspace: ``config.json`` is what it reads, so a test changes it
    between turns; ``hold`` in its directory makes a turn wait until the person stops it."""

    def __init__(self, world, tmp_path, monkeypatch, ledgers):

        self.world, self.dir, self.ledgers = world, tmp_path, ledgers
        path = tmp_path / "stand_in.py"
        path.write_text(WAY_OUT)
        path.chmod(0o755)
        self.path = str(path)
        self.config = {
            "log": str(tmp_path / "log.jsonl"),
            "workspace": ledgers.workspace,
            "batch": [
                {
                    "op": "create",
                    "applicationKey": world.app("R"),
                    "objectTypeKey": world.key("R"),
                    "name": f"Way ledger {ledgers.tag}",
                    "attributes": [
                        {"attributeTypeKey": world.key(key), "value": value}
                        for key, value in _ledger_values(ledgers, f"{ledgers.tag}-W1").items()
                    ],
                }
            ],
        }
        monkeypatch.setenv("AI_AGENT_COMMAND", self.path)
        from test_j50_ai_workbook_load import _trust_stand_in

        _trust_stand_in(monkeypatch)
        self.draft()

    def draft(self, **changes):
        """A draft of its own for the next proposal: a session may not take one another task holds."""
        self.config["draft"] = ok(
            self.world.api.post("/model-drafts", {"name": "A proposal", "model": {}}), 201
        )["id"]
        self.set(**changes)

    def set(self, **changes):
        self.config.update(changes)
        (self.dir / "config.json").write_text(json.dumps(self.config))

    def log(self):
        return [json.loads(line) for line in (self.dir / "log.jsonl").read_text().splitlines()]

    def stop(self, task, start):
        """``start()`` queues a turn the stand-in holds; the person stops it."""
        state = self.world.api.client.app.state
        (self.dir / "hold").touch()
        (self.dir / "holding").unlink(missing_ok=True)
        start()
        with ThreadPoolExecutor(1) as pool:
            session = pool.submit(state.assistant_worker.run_until_idle)
            deadline = time.monotonic() + 60
            while not (self.dir / "holding").exists():
                assert time.monotonic() < deadline and not session.done()
                time.sleep(0.1)
            ok(self.world.api.post(f"/ai/tasks/{task['id']}/cancel", {}), 202)
            session.result(timeout=120)
        (self.dir / "hold").unlink()
        return _task(self.world, task)


def _words(world, task, words, route="model", **body):
    payload = {"expectedVersion": task["version"], **body}
    if words:
        payload["correction" if route == "model" else "words"] = words
    ok(world.api.post(f"/ai/tasks/{task['id']}/{route}", payload), 202)
    _run(world)
    return _task(world, task)


def _kept(world, task):
    """Whether the task's session folder is on disk and its client is active."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import AiTask, OAuthClient

    with SessionLocal() as db:
        row = db.scalar(select(AiTask).where(AiTask.public_id == task["id"]))
        client = db.get(OAuthClient, row.client_id)
        files = world.api.client.app.state.job_files
        return agent.folder_of(files, row).exists(), client.active


def _loaded(world, way, ledgers, **request):
    task = _accept(world, _read(world, ledgers, accept=False, **request))
    assert task["state"] == "loaded", task["notes"]
    return task


@pytest.mark.journey("J50.53")
@pytest.mark.structures(*STRUCTURES)
def test_a_failed_turn_shows_its_reason_and_the_persons_words_go_on_in_the_same_session(
    world, tmp_path, monkeypatch
):
    """Given a session that ended without a usable proposal, then the task is failed with its reason
    in the notes and takes words; the words go to the same session. Given a session that never
    started, the words start it again on the same task, file and words."""
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    way.set(fail=True)
    task = _read(world, ledgers, accept=False, words="Make it so")
    assert task["state"] == "failed" and task["canTell"] is True
    assert any(n["kind"] == "warning" and n["text"] for n in task["notes"])
    first = way.log()[0]["args"]
    session_id = first[first.index("--session-id") + 1]

    way.set(fail=False)
    task = _words(world, task, "Keep the names as they are")
    assert task["state"] == "checked" and task["design"]["summary"] == "A plan."
    second = way.log()[-1]
    assert "Keep the names as they are" in second["prompt"]
    assert second["args"][second["args"].index("--resume") + 1] == session_id

    # A session that could not start has no conversation to go on in: the words start it again.
    way.draft()
    monkeypatch.setenv("AI_AGENT_COMMAND", str(tmp_path / "missing"))
    never = _read(world, ledgers, accept=False, words="Make it so")
    assert never["state"] == "failed" and never["canTell"] is True
    assert any("could not start" in n["text"] for n in never["notes"])
    monkeypatch.setenv("AI_AGENT_COMMAND", way.path)
    never = _words(world, never, "Go on, please", route="retry")
    assert never["state"] == "checked"
    last = way.log()[-1]
    assert "--session-id" in last["args"] and "--resume" not in last["args"]
    assert last["prompt"].startswith("Make it so") and "Go on, please" in last["prompt"]
    assert "workbook.xlsx" in last["files"]


@pytest.mark.journey("J50.53")
@pytest.mark.structures(*STRUCTURES)
def test_words_that_need_no_model_change_are_a_proposal_without_a_draft_and_load_on_the_live_release(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given an instruction in words about the stored records, when the session names no draft because
    the model does not change, then the task waits with its summary and no draft; when the person
    accepts, the change set is made on the release the workspace runs, with no new release; a
    workbook task whose session names no draft still fails."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    way.set(draft=None, name="Its change")
    live = ok(world.api.get(f"/workspaces/{ledgers.workspace}/model"))["releaseId"]
    releases = ok(world.api.get("/model-releases"))["items"]

    asked = ok(
        world.api.upload(
            "/ai/tasks",
            {},
            {"request": json.dumps({"workspaceKey": ledgers.workspace, "words": "Rename it"})},
        ),
        202,
    )
    _run(world)
    task = _task(world, asked)
    assert task["state"] == "checked", task["notes"]
    assert task["draftId"] is None and task["design"]["stage"] == "model"
    assert task["design"]["modelUnchanged"] is True and task["design"]["summary"] == "A plan."

    task = _accept(world, task)
    assert task["state"] == "loaded", task["notes"]
    assert "install no release" in way.log()[-1]["prompt"]
    change_set = ok(world.api.get(f"/change-sets/{task['result']['changeSetId']}"))
    assert change_set["modelReleaseId"] == live and change_set["source"] == "currentLive"
    assert ok(world.api.get("/model-releases"))["items"] == releases

    way.draft(draft=None)
    failed = _read(world, ledgers, accept=False)
    assert failed["state"] == "failed" and failed["draftId"] is None


@pytest.mark.journey("J50.54")
@pytest.mark.structures(*STRUCTURES)
def test_stopping_returns_to_the_last_proposal_and_before_any_proposal_gives_stopped(
    world, tmp_path, monkeypatch
):
    """Given a proposal, when the person sends words and stops the turn, then the task is back at the
    proposal as it was, with a note; given a turn stopped before any proposal, then the task is
    stopped, takes words and is discarded by Discard."""
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    task = _read(world, ledgers, accept=False)
    assert task["state"] == "checked"
    summary = task["design"]["summary"]

    def correct():
        ok(
            world.api.post(
                f"/ai/tasks/{task['id']}/model",
                {"expectedVersion": task["version"], "correction": "Another way"},
            ),
            202,
        )

    back = way.stop(task, correct)
    assert back["state"] == "checked" and back["design"]["stage"] == "model"
    assert back["design"]["summary"] == summary and back["draftId"] == task["draftId"]
    assert any("You stopped the assistant" in n["text"] for n in back["notes"])
    assert back["canTell"] is True and back["version"] > task["version"]
    back = _words(world, back, "Go on in another way")
    assert back["state"] == "checked" and "Go on in another way" in way.log()[-1]["prompt"]

    way.draft()
    started = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    stopped = way.stop(started, lambda: None)
    assert stopped["state"] == "stopped" and stopped["canTell"] is True
    assert stopped["draftId"] is None
    assert any("You stopped the assistant" in n["text"] for n in stopped["notes"])
    went_on = _words(world, stopped, "Try it with these words", route="retry")
    assert went_on["state"] == "checked" and went_on["design"]["summary"] == summary
    assert "Try it with these words" in way.log()[-1]["prompt"]

    way.draft()
    again = ok(_create(world, ledgers.workspace, ledgers.book()), 202)
    again = way.stop(again, lambda: None)
    assert again["state"] == "stopped"
    gone = ok(world.api.post(f"/ai/tasks/{again['id']}/discard", {}), 200)
    assert gone["state"] == "cancelled" and gone["canTell"] is False


@pytest.mark.journey("J50.63")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_over_the_limit_ends_as_a_stop_with_its_own_note_and_no_traceback(
    world, tmp_path, monkeypatch, caplog
):
    """Given a session that outlasts AI_AGENT_TIMEOUT_SECONDS, then the turn is stopped as a person's
    Stop is: before any proposal the task is stopped and takes words; after a proposal it is back at
    that proposal, its draft kept; the note says the session took longer than the limit; the job is
    cancelled, never failed; the log has one warning line and no traceback."""
    from app.engine.tasks import agent

    monkeypatch.setattr(agent, "timeout_seconds", lambda: 3)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)

    def over_the_limit(start):
        (way.dir / "hold").touch()
        caplog.clear()
        try:
            start()
            _run(world)
        finally:
            (way.dir / "hold").unlink()
        slow = [r for r in caplog.records if "longer than" in r.getMessage()]
        assert len(slow) == 1 and slow[0].levelname == "WARNING"
        assert not [r for r in caplog.records if r.exc_info]

    started = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    over_the_limit(lambda: None)
    stopped = _task(world, started)
    assert stopped["state"] == "stopped" and stopped["canTell"] is True
    assert any("longer than the limit" in n["text"] for n in stopped["notes"])
    assert not any("internal error" in n["text"] for n in stopped["notes"])
    job = ok(world.api.get(f"/jobs/{started['jobId']}"))
    assert job["state"] == "cancelled" and job["error"] is None

    way.draft()
    proposed = _words(world, stopped, "Make it so", route="retry")
    assert proposed["state"] == "checked"
    summary = proposed["design"]["summary"]

    def correct():
        ok(
            world.api.post(
                f"/ai/tasks/{proposed['id']}/model",
                {"expectedVersion": proposed["version"], "correction": "Another way"},
            ),
            202,
        )

    over_the_limit(correct)
    back = _task(world, proposed)
    assert back["state"] == "checked" and back["design"]["summary"] == summary
    assert back["draftId"] == proposed["draftId"]
    assert any("longer than the limit" in n["text"] for n in back["notes"])
    assert not any("You stopped" in n["text"] for n in back["notes"])
    assert ok(world.api.get(f"/jobs/{back['jobId']}"))["state"] == "cancelled"
    went_on = _words(world, back, "Go on in another way")
    assert went_on["state"] == "checked"


@pytest.mark.journey("J50.65")
@pytest.mark.structures(*STRUCTURES)
def test_a_task_queued_behind_a_running_one_says_how_many_are_ahead_until_it_runs(
    world, tmp_path, monkeypatch
):
    """Given one task whose session is running and a second queued behind it, then the second reads
    ahead 1 and the first null; once the first is stopped and the second runs, ahead is null."""
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    state = world.api.client.app.state
    (way.dir / "hold").touch()
    first = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    second = ok(_create(world, ledgers.workspace, ledgers.book(), words="Make it so"), 202)
    assert first["ahead"] == 0 and second["ahead"] == 1
    with ThreadPoolExecutor(1) as pool:
        session = pool.submit(state.assistant_worker.run_until_idle)
        deadline = time.monotonic() + 60
        while not (way.dir / "holding").exists():
            assert time.monotonic() < deadline and not session.done()
            time.sleep(0.1)
        assert _task(world, first)["ahead"] is None
        waiting = _task(world, second)
        assert waiting["state"] == "reading" and waiting["ahead"] == 1
        listed = {t["id"]: t for t in _all(world, "/ai/tasks")}
        assert listed[second["id"]]["ahead"] == 1
        ok(world.api.post(f"/ai/tasks/{first['id']}/cancel", {}), 202)
        (way.dir / "hold").unlink()
        session.result(timeout=120)
    done = _task(world, second)
    assert done["state"] == "checked" and done["ahead"] is None
    assert _task(world, first)["ahead"] is None


@pytest.mark.journey("J50.55")
@pytest.mark.structures(*STRUCTURES)
def test_stopping_a_load_leaves_no_change_set_and_returns_to_the_accepted_proposal(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a load in progress with a change set already made, when the person stops it, then the
    change set is discarded, nothing is loaded and the task is back at the proposal, which loads
    when accepted again."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    way.set(name="Made then stopped")
    task = _read(world, ledgers, accept=False)

    def accept():
        ok(
            world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}),
            202,
        )

    back = way.stop(task, accept)
    assert back["state"] == "checked" and back["design"]["stage"] == "model"
    assert back["result"] is None
    assert any("undone" in n["text"] for n in back["notes"])
    named = [c["name"] for c in _all(world, f"/workspaces/{ledgers.workspace}/change-sets")]
    assert "Made then stopped" not in named
    way.set(name="Loaded for good")
    loaded = _accept(world, back)
    assert loaded["state"] == "loaded" and loaded["result"]["counts"]["created"] == 1


@pytest.mark.journey("J50.56")
@pytest.mark.structures(*STRUCTURES)
def test_a_correction_of_a_loaded_change_set_that_fails_leaves_no_change_set_without_a_task(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a loaded change set, when the person corrects it in words and the session makes the
    replacement change set and then ends without an answer, then the task is failed with its reason
    and takes words, and the empty replacement is not left in the workspace, linked to nothing."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    way.set(name="First load")
    task = _loaded(world, way, ledgers)

    way.set(name="Empty replacement", die=True)
    failed = _words(world, task, "Leave out the newcomers")
    assert failed["state"] == "failed" and failed["canTell"] is True, failed["notes"]
    assert failed["result"] is None
    named = [c["name"] for c in _all(world, f"/workspaces/{ledgers.workspace}/change-sets")]
    assert "Empty replacement" not in named and "First load" not in named


@pytest.mark.journey("J50.56")
@pytest.mark.structures(*STRUCTURES)
def test_words_on_a_loaded_change_set_discard_it_and_the_same_session_loads_again(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a loaded change set, when the person tells the assistant what is wrong, then the change
    set is discarded and the same session loads again with the words; its folder and client stay
    until the second change set is published, then both go and the task says it was published."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    way.set(name="First load")
    task = _loaded(world, way, ledgers)
    first = task["result"]["changeSetId"]
    assert task["canTell"] is True and _kept(world, task) == (True, True)
    session_id = way.log()[0]["args"][way.log()[0]["args"].index("--session-id") + 1]

    way.set(name="Second load")
    again = _words(world, task, "Leave out the newcomers")
    assert again["state"] == "loaded", again["notes"]
    second = again["result"]["changeSetId"]
    assert second != first and again["result"]["changeSetName"] == "Second load"
    refused(world.api.get(f"/change-sets/{first}"), 404, "CHANGE_SET_NOT_FOUND")
    last = way.log()[-1]
    assert "Leave out the newcomers" in last["prompt"]
    assert last["args"][last["args"].index("--resume") + 1] == session_id
    assert _kept(world, again) == (True, True) and again["canTell"] is True

    world.publish({"id": second}, ledgers.workspace)
    done = _task(world, again)
    assert done["state"] == "loaded" and done["result"]["published"] is True
    assert done["result"]["publicationId"] and done["canTell"] is False
    assert _kept(world, done) == (False, False)
    refused(
        world.api.post(
            f"/ai/tasks/{done['id']}/model",
            {"expectedVersion": done["version"], "correction": "Too late"},
        ),
        409,
        "AI_TASK_STATE",
    )


@pytest.mark.journey("J50.56")
@pytest.mark.structures(*STRUCTURES)
def test_a_loaded_task_whose_folder_went_at_its_load_takes_no_words_and_can_be_discarded(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a task recorded before AP13 (the state arrives from outside the API: its session folder
    was removed at the load), when it is read, then it takes no words, keeps its change set, and
    Discard still ends it."""
    import shutil

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.engine.tasks import agent
    from app.models.database import AiTask

    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    task = _loaded(world, way, ledgers)
    assert task["canTell"] is True
    with SessionLocal() as db:
        row = db.scalar(select(AiTask).where(AiTask.public_id == task["id"]))
        shutil.rmtree(agent.folder_of(world.api.client.app.state.job_files, row))
    read = _task(world, task)
    assert read["state"] == "loaded" and read["canTell"] is False
    ok(world.api.get(f"/change-sets/{read['result']['changeSetId']}"))
    refused(
        world.api.post(
            f"/ai/tasks/{read['id']}/model",
            {"expectedVersion": read["version"], "correction": "Again"},
        ),
        409,
        "AI_TASK_STATE",
    )
    assert ok(world.api.post(f"/ai/tasks/{read['id']}/discard", {}), 200)["state"] == "cancelled"


@pytest.mark.journey("J50.39")
@pytest.mark.structures(*STRUCTURES)
def test_a_filled_column_no_source_reads_is_said_before_the_person_accepts(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a design whose only source leaves one filled column of the table unbound (found on the
    real walk-through, where a column under an empty header lost eleven cells and nothing said so),
    then the proposal carries an open check naming the sheet, the count and the first cells; a design
    that reads every column carries none."""
    from test_j50_ai_workbook_load import _assistant, _records_source

    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)

    def proposal(name, source):
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
            profile={"name": "Ledgers", "sources": [source]},
        )
        return _read(world, ledgers, accept=False)

    whole = _records_source(world, ledgers)
    task = proposal("whole", whole)
    assert task["state"] == "checked", task["notes"]
    assert [c for c in task["design"]["checks"] if c["kind"] == "cellsLeftOut"] == []
    short = {**whole, "columns": [c for c in whole["columns"] if c["column"] != ledgers.score]}
    task = proposal("short", short)
    assert task["state"] == "checked", task["notes"]
    [found] = [c for c in task["design"]["checks"] if c["kind"] == "cellsLeftOut"]
    assert found["open"] is True and "11 filled cells of “Records”" in found["text"]
    assert "E1, E2, E3" in found["text"]


@pytest.mark.journey("J50.58")
@pytest.mark.structures(*STRUCTURES)
def test_a_discarded_load_ends_the_task_and_says_so_wherever_it_was_discarded(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a loaded task, when the person discards it from the task, the change set goes and the
    task is cancelled with a note and no session; when the change set is discarded elsewhere, the
    next read of the task ends it the same way."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    task = _loaded(world, way, ledgers)
    change_set = task["result"]["changeSetId"]
    gone = ok(world.api.post(f"/ai/tasks/{task['id']}/discard", {}), 200)
    assert gone["state"] == "cancelled" and gone["canTell"] is False
    assert any("discarded the change set" in n["text"] for n in gone["notes"])
    refused(world.api.get(f"/change-sets/{change_set}"), 404, "CHANGE_SET_NOT_FOUND")
    assert _kept(world, gone) == (False, False)

    way.draft()
    way.set(name="Discarded elsewhere")
    other = _loaded(world, way, ledgers)
    held = ok(world.api.get(f"/change-sets/{other['result']['changeSetId']}"))
    assert world.api.delete(
        f"/change-sets/{held['id']}", expectedVersion=held["version"]
    ).status_code in (200, 204)
    ended = _task(world, other)
    assert ended["state"] == "cancelled" and ended["canTell"] is False
    assert any("was discarded" in n["text"] for n in ended["notes"])
    assert _kept(world, ended) == (False, False)


@pytest.mark.journey("J50.57")
@pytest.mark.structures(*STRUCTURES)
def test_a_saved_layouts_load_stage_takes_words_by_a_session_and_goes_back_to_its_proposal(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a file read by a saved layout (no session) and checked, when the person goes back, the
    task shows the layout's proposal again; when the person sends words there, a session starts on
    the same task and file with the words and proposes."""
    from test_j50_ai_workbook_load import _assistant, _profile_of

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
    first = _accept(world, _read(world, ledgers, book, accept=False))
    assert first["state"] == "loaded", first["notes"]
    world.publish({"id": settings["changeSet"]}, ledgers.workspace)

    again = _read(world, ledgers, book, accept=False)
    assert again["state"] == "checked" and again["design"].get("agentSession") is None
    checked = _accept(world, again)
    assert checked["state"] == "checked" and checked["design"]["stage"] == "load"
    assert checked["canTell"] is True
    back = ok(
        world.api.post(
            f"/ai/tasks/{checked['id']}/proposal", {"expectedVersion": checked["version"]}
        )
    )
    assert back["state"] == "checked" and back["design"]["stage"] == "model"
    refused(
        world.api.post(f"/ai/tasks/{back['id']}/proposal", {"expectedVersion": back["version"]}),
        409,
        "AI_TASK_STATE",
    )
    # Words need a session; it starts on the same file, with the words added to the original.
    settings["draft"] = ok(world.api.post("/model-drafts", {"name": "Another", "model": {}}), 201)[
        "id"
    ]
    (tmp_path / "config.json").write_text(json.dumps(settings))
    spoken = _words(world, back, "Treat the empty owner as unknown")
    assert spoken["state"] == "checked" and spoken["design"].get("agentSession")
    log = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    last = log[-1]
    assert "--session-id" in last["args"] and "Treat the empty owner as unknown" in last["prompt"]
    assert "workbook.xlsx" in last["files"]


@pytest.mark.journey("J50.59")
@pytest.mark.structures(*STRUCTURES)
def test_accepting_needs_the_loading_permission_and_the_refusal_names_it(
    world, tmp_path, monkeypatch
):
    """Given a person who may use the assistant and import but does not hold Work in change sets,
    when they accept a proposal that loads, then the engine refuses naming the group; the proposal
    stays and takes words."""
    from test_j40_authorization import _client

    ledgers = Ledgers(world)
    Way(world, tmp_path, monkeypatch, ledgers)
    role = ok(
        world.api.post(
            "/roles",
            {"name": "Readers who ask", "actionGroups": ["bulk", "browse", "ai-proposals"]},
        ),
        201,
    )
    _, asker = _client(world, "asker", (role["key"], {"workspaceKey": ledgers.workspace}))
    task = ok(_create(asker, ledgers.workspace, ledgers.book()), 202)
    _run(world)
    task = _task(asker, task)
    assert task["state"] == "checked"
    error = refused(
        asker.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}),
        403,
        "FORBIDDEN",
    )
    assert error["details"]["groups"] == ["change-sets"]
    assert _task(asker, task)["canTell"] is True


@pytest.mark.journey("J50.60")
@pytest.mark.structures(*STRUCTURES)
def test_a_migration_task_keeps_its_session_until_the_migration_is_confirmed(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a task whose proposal moves whole types and was accepted, then the session lives and the
    task takes words while the migration waits; when the person confirms the migration, the next read
    ends the session."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch)
    task = _accept_merge(world, _proposed(world, merge.workspace))
    assert task["state"] == "loaded", task["notes"]
    migration = task["result"]["migration"]
    assert task["canTell"] is True and _kept(world, task) == (True, True)
    job = _previewed(
        world, merge.workspace, migration["releaseId"], typeMappings=migration["typeMappings"]
    )
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    done = _task(world, task)
    assert done["state"] == "loaded" and done["canTell"] is False
    assert _kept(world, done) == (False, False)


def _accept_merge(world, task):
    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    _run(world)
    return _task(world, task)
