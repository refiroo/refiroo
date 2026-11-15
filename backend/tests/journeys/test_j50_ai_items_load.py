"""J50.67 to J50.70 — The assistant loads a file as one checked batch (0.13 AB).

The assistant's session reads a file itself and sends the records it makes of it, as the batch API's
items, to its draft's dry run. The engine previews every item against the draft's model and says,
per type, what the load does; the person reads that, and accepting loads exactly those items with
no further assistant turn: one release, one change set, one atomic batch. The session is a
stand-in working through the API with the token the engine gives it, so every permission and
refusal is the engine's.
"""

import json
from uuid import uuid4

import pytest
from scenario import ok, refused
from test_j24_job_stream import served  # noqa: F401  (the journey application over HTTP)
from test_j34_onboard import _all
from test_j40_authorization import _client
from test_j46_mail import _database_write
from test_j50_ai_reshape import _ask, _keys, _record, _shaped, _workspace
from test_j50_ai_workbook_load import _assistant, _run, _task

from app.engine.proposals import fake

STRUCTURES = ("R",)

SESSION = """#!/usr/bin/env python3
import json, os, re, sys, time, httpx
prompt = sys.argv[sys.argv.index("--") + 1]
config = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")))
print(json.dumps({"type": "system", "subtype": "init", "model": "claude-test-1"}), flush=True)
if not os.path.exists("url.txt"):
    open("url.txt", "w").write(re.search(r"https?://[\\w.:-]+", prompt).group(0))
base = open("url.txt").read() + "/api/v1"
head = {"Authorization": "Bearer " + os.environ["REFIROO_TOKEN"]}
def api(method, path, **kw):
    sent = httpx.request(method, base + path, headers=head, timeout=120, **kw)
    assert sent.status_code < 300, (method, path, sent.status_code, sent.text)
    return sent.json()
log = open(config["log"], "a")
log.write(json.dumps({"prompt": prompt}) + "\\n")
log.close()
if "accepted" not in prompt:
    checking = api("POST", "/model-drafts/" + config["draft"] + "/dry-run",
        json={"workspaceKey": config["workspace"], "items": config["items"]})
    # The job's event stream sends it at each change: the wait ends when the check does.
    # timeout=120 is per read and the stream keeps alive, so the whole wait has a deadline too.
    deadline, last = time.monotonic() + 120, None
    with httpx.stream("GET", base + "/jobs/" + checking["jobId"] + "/events", headers=head,
                      timeout=120) as sent:
        for line in sent.iter_lines():
            if line.startswith("data:"):
                last = json.loads(line[5:])["state"]
                if last in ("completed", "failed", "cancelled", "expired"):
                    break
            if time.monotonic() > deadline:
                raise SystemExit("job " + checking["jobId"] + " still " + str(last) + " after 120 s")
    for _ in range(300):
        found = api("GET", "/model-drafts/" + config["draft"] + "/dry-run")
        if found["state"] != "checking":
            break
        time.sleep(0.2)
    json.dump({"draftId": config["draft"], "summary": "A plan.", "questions": []},
              open("proposal.json", "w"))
print(json.dumps({"type": "result", "result": "Done."}))
"""


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


class Partners:
    """A workspace running a model with suppliers, a supplier and an anchor stored in it, and the
    draft that adds partners; the items a session makes of a file: three partners (two named
    alike), a relationship from one to the anchor, and the supplier renamed."""

    def __init__(self, world, tmp_path, monkeypatch):
        self.world = world
        k = self.k = _keys(world)
        first = _shaped(world, "ab-1", [(k.supplier, "Supplier", [k.label, k.note])])
        self.final = _shaped(
            world,
            "ab-2",
            [(k.supplier, "Supplier", [k.label, k.note]), (k.partner, "Partner", [k.label])],
        )
        x1 = world.install(first, name="Suppliers")
        self.workspace = _workspace(world, x1["id"])
        self.release = x1["id"]
        self.anchor = world.made("R", "Anchor", workspace=self.workspace)
        self.supplier = _record(
            world, self.workspace, k.supplier, "Supplier 0", {k.label: "S0", k.note: "n"}
        )
        self.ids = [str(uuid4()) for _ in range(3)]
        self.items = self.make_items()
        self.settings = _assistant(
            world,
            tmp_path,
            monkeypatch,
            self.workspace,
            script=SESSION,
            model=self.final,
            api=True,
            items=self.items,
        )
        self.log = tmp_path / "log.jsonl"

    def make_items(self):
        k, world = self.k, self.world
        alpha, twin, twin_again = self.ids

        def partner(id_, name, ref):
            return {
                "op": "create",
                "id": id_,
                "applicationKey": world.app("R"),
                "objectTypeKey": k.partner,
                "name": name,
                "attributes": [{"attributeTypeKey": k.label, "value": name[:3]}],
                "ref": ref,
            }

        return [
            partner(alpha, "Alpha", "Sheet!A2:B2"),
            partner(twin, "Twin", "Sheet!A3:B3"),
            partner(twin_again, "Twin", "Sheet!A4:B4"),
            {
                "op": "createRelation",
                "relationTypeKey": k.cites,
                "from": {"id": alpha},
                "to": {"id": self.anchor["id"]},
                "ref": "Sheet!C2",
            },
            {
                "op": "update",
                "target": {"id": self.supplier["id"]},
                "expectedVersion": self.supplier["version"],
                "name": "Supplier 0 renamed",
                "ref": "Sheet!A6:B6",
            },
        ]

    def proposed(self):
        task = _ask(self.world, self.workspace, "Load this file, add partners.")
        _run(self.world)
        return _task(self.world, task)

    def accept(self, task):
        ok(
            self.world.api.post(
                f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}
            ),
            202,
        )
        _run(self.world)
        return _task(self.world, task)

    def turns(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]


@pytest.mark.journey("J50.67")
@pytest.mark.structures(*STRUCTURES)
def test_a_session_sends_items_to_its_drafts_dry_run_and_the_proposal_shows_what_they_do(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session that turns a file into items and sends them to its draft's dry run, when it
    proposes, then the task shows per type what the load does (new, matched, changed, refused), the
    relationship, examples with the cells they came from, the rows read and the engine's finding
    that one name appears twice in a type; nothing is written."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    design = task["design"]
    assert design["itemsLoad"] is True and task["check"]["mode"] == "items"
    load = design["load"]
    assert load["figures"] == {
        "recordsNew": 3,
        "recordsMatched": 1,
        "recordsChanged": 1,
        "recordsRemoved": 0,
        "relationshipsNew": 1,
        "parentLinksNew": 0,
        "relationshipsMatched": 0,
        "refused": 0,
        "rowsRead": 4,
    }
    types = {t["objectTypeKey"]: t for t in load["types"]}
    assert (types[k.partner]["new"], types[k.partner]["matched"]) == (3, 0)
    assert (types[k.supplier]["matched"], types[k.supplier]["changed"]) == (1, 1)
    assert types[k.partner]["linkedTo"] == [world.key("R")]
    refs = {e["ref"] for e in types[k.partner]["examples"]}
    assert refs <= {"Sheet!A2:B2", "Sheet!A3:B3", "Sheet!A4:B4"} and len(refs) == 3
    (example,) = [e for e in types[k.partner]["examples"] if e["name"] == "Alpha"]
    assert example["action"] == "created"
    assert [(link["relationTypeKey"], link["name"]) for link in example["links"]] == [
        (k.cites, "Anchor")
    ]
    assert [r["relationTypeKey"] for r in load["relationships"]] == [k.cites]
    assert load["relationships"][0]["new"] == 1
    (finding,) = load["findings"]
    assert (finding["kind"], finding["objectTypeKey"], finding["name"], finding["count"]) == (
        "nameTwice",
        k.partner,
        "Twin",
        2,
    )
    assert finding["parents"] == [None, None]
    assert {p["sheet"] for p in load["parts"]} == {"Sheet"}
    # The old check's counts read from the same run; the page shows both.
    assert (
        task["check"]["summary"]["created"] == 3 and task["check"]["summary"]["relationships"] == 1
    )
    # Nothing was written: the partners are not stored, and the workspace still runs its release.
    assert (
        ok(world.api.get(f"/workspaces/{partners.workspace}/model"))["releaseId"]
        == partners.release
    )
    assert len(partners.turns()) == 1


@pytest.mark.journey("J50.68")
@pytest.mark.structures(*STRUCTURES)
def test_accepting_runs_the_previewed_items_with_no_assistant_turn(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a proposal whose items were previewed, when the person accepts, then the engine installs
    the draft as a release, makes a change set on it and loads exactly the previewed records and
    relationship, with no further session turn; the task is loaded with the change set's counts,
    live data is as it was, and the workspace still runs its release."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    task = partners.accept(task)
    assert task["state"] == "loaded", task["notes"]
    assert len(partners.turns()) == 1, "accepting asked the session for another turn"
    result = task["result"]
    assert result["counts"]["created"] == 3 and result["counts"]["updated"] == 1
    assert result["counts"]["relationsCreated"] == 1 and result["importJobId"]
    change_set = ok(world.api.get(f"/change-sets/{result['changeSetId']}"))
    found = {
        item["name"] for item in _all(world, f"/objects/{k.partner}", changeSetId=change_set["id"])
    }
    assert found == {"Alpha", "Twin"}  # two records are named Twin: one name, two records
    stored = _all(world, f"/objects/{k.partner}", changeSetId=change_set["id"])
    assert len(stored) == 3
    renamed = _all(world, f"/objects/{k.supplier}", changeSetId=change_set["id"])
    assert [item["name"] for item in renamed] == ["Supplier 0 renamed"]
    # Live data and the workspace's model are untouched until the person publishes.
    assert _all(world, f"/objects/{k.supplier}", workspaceKey=partners.workspace)[0]["name"] == (
        "Supplier 0"
    )
    assert (
        ok(world.api.get(f"/workspaces/{partners.workspace}/model"))["releaseId"]
        == partners.release
    )
    assert change_set["modelReleaseId"] != partners.release
    release = ok(
        world.api.get(f"/model-releases/{change_set['modelReleaseId']}", includeModel=True)
    )
    assert any(t["key"] == k.partner for t in release["model"]["objectTypes"])


@pytest.mark.journey("J50.69")
@pytest.mark.structures(*STRUCTURES)
def test_an_item_the_data_has_moved_away_from_fails_the_accept_and_writes_nothing(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a proposal whose items were previewed, when a stored record an item updates changes
    before the person accepts, then the atomic batch is refused: the task fails naming the item and
    its cells, no change set is left, nothing was written, and the person may give the assistant
    other words."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    ok(
        world.api.patch(
            f"/objects/{k.supplier}/{partners.supplier['id']}",
            {"expectedVersion": partners.supplier["version"], "name": "Changed by someone"},
        )
    )
    releases = len(_all(world, "/model-releases"))
    task = partners.accept(task)
    assert task["state"] == "failed", task["notes"]
    warning = next(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "nothing was loaded" in warning and "Sheet!A6:B6" in warning
    # The release the accept installed went with the refused load.
    assert len(_all(world, "/model-releases")) == releases
    assert task["result"] is None and task["canTell"] is True
    assert len(partners.turns()) == 1
    # The only change set is the one the test made for the stand-in; the load's own was discarded.
    changes = _all(world, f"/workspaces/{partners.workspace}/change-sets")
    assert [c["id"] for c in changes] == [partners.settings["changeSet"]]
    live = _all(world, f"/objects/{k.supplier}", workspaceKey=partners.workspace)
    assert [item["name"] for item in live] == ["Changed by someone"]


@pytest.mark.journey("J50.70")
@pytest.mark.structures(*STRUCTURES)
def test_an_items_dry_run_refuses_an_item_with_its_cells_and_takes_exactly_one_form(
    world, tmp_path, monkeypatch
):
    """Given a draft, when an items dry run holds an item the draft's model refuses, then the
    summary counts it refused and lists it with its ref and the engine's code; a request with both a
    source file and items, or with neither, is refused."""
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    draft = partners.settings["draft"]
    bad = {
        "op": "create",
        "applicationKey": world.app("R"),
        "objectTypeKey": k.partner,
        "name": "Broken",
        "attributes": [{"attributeTypeKey": f"{k.partner}-no-such-attribute", "value": "x"}],
        "ref": "Sheet!A9:B9",
    }
    sent = ok(
        world.api.post(
            f"/model-drafts/{draft}/dry-run",
            {"workspaceKey": partners.workspace, "items": [*partners.items, bad]},
        ),
        202,
    )
    assert sent["state"] == "checking" and sent["sourceFileId"] is None
    world.api.client.app.state.job_worker.run_until_idle()
    done = ok(world.api.get(f"/model-drafts/{draft}/dry-run"))
    assert done["state"] == "completed" and done["summary"] is None
    summary = done["items"]
    assert summary["figures"]["refused"] == 1 and summary["figures"]["recordsNew"] == 3
    (refusal,) = summary["refused"]
    assert refusal["ref"] == "Sheet!A9:B9" and refusal["code"] and refusal["key"] == k.partner
    assert summary["refusedByCode"] == [{"code": refusal["code"], "items": 1}]
    types = {t["objectTypeKey"]: t for t in summary["types"]}
    assert types[k.partner]["refused"] == 1
    refused_example = types[k.partner]["examples"][0]
    assert refused_example["action"] == "refused" and refused_example["ref"] == "Sheet!A9:B9"
    # Exactly one form.
    both = {"workspaceKey": partners.workspace, "items": partners.items, "sourceFileId": "x"}
    refused(world.api.post(f"/model-drafts/{draft}/dry-run", both), 422, "REQUEST_VALIDATION_ERROR")
    neither = {"workspaceKey": partners.workspace}
    refused(
        world.api.post(f"/model-drafts/{draft}/dry-run", neither), 422, "REQUEST_VALIDATION_ERROR"
    )


@pytest.mark.journey("J50.69")
@pytest.mark.structures(*STRUCTURES)
def test_a_draft_changed_after_the_check_is_checked_again_before_anything_is_installed(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a proposal whose items were previewed, when the person edits the draft so that an item
    is refused and accepts, then the engine checks every item again first: the task fails naming
    the cells, and no release is installed and no change set made."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    draft = partners.settings["draft"]
    version = ok(world.api.get(f"/model-drafts/{draft}"))["version"]
    step = {
        "expectedVersion": version,
        "operations": [
            {
                "kind": "disallowRelation",
                "relationType": k.cites,
                "from": k.partner,
                "to": world.key("R"),
            }
        ],
    }
    ok(world.api.post(f"/model-drafts/{draft}/operations", step))
    releases = len(_all(world, "/model-releases"))
    task = partners.accept(task)
    assert task["state"] == "failed", task["notes"]
    warning = next(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "nothing was installed or loaded" in warning and "Sheet!C2" in warning
    assert len(_all(world, "/model-releases")) == releases
    changes = _all(world, f"/workspaces/{partners.workspace}/change-sets")
    assert [c["id"] for c in changes] == [partners.settings["changeSet"]]


@pytest.mark.journey("J50.71")
@pytest.mark.structures(*STRUCTURES)
def test_a_file_already_in_the_workspace_is_checked_and_accepting_it_loads_nothing_new(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a file whose every record is stored already (items naming the existing supplier by its
    ID with the values it holds) and a draft that does not change the model, when the session
    sends them and proposes, then the task is checked and the summary shows every item matched, none
    new or refused; accepting installs no release, ends the task loaded with nothing new and changes
    no live data."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    k = partners.k
    same = [
        {
            "op": "update",
            "target": {"id": partners.supplier["id"]},
            "expectedVersion": partners.supplier["version"],
            "name": "Supplier 0",
            "ref": "Sheet!A2:B2",
        }
    ]
    draft = ok(
        world.api.post(
            "/model-drafts",
            {
                "name": "Unchanged",
                "model": ok(
                    world.api.get(f"/model-releases/{partners.release}", includeModel=True)
                )["model"],
                "baseReleaseId": partners.release,
            },
        ),
        201,
    )["id"]
    config = tmp_path / "config.json"
    config.write_text(json.dumps({**json.loads(config.read_text()), "draft": draft, "items": same}))
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    load = task["design"]["load"]
    assert load["figures"]["recordsNew"] == 0 and load["figures"]["refused"] == 0
    assert load["figures"]["recordsMatched"] == 1 and load["figures"]["recordsChanged"] == 0
    releases = len(_all(world, "/model-releases"))
    task = partners.accept(task)
    assert task["state"] == "loaded", task["notes"]
    counts = task["result"]["counts"]
    assert counts["created"] == counts["updated"] == counts["deleted"] == 0
    assert counts["relationsCreated"] == 0 and counts["unchanged"] == 1
    assert not task["result"].get("releaseId")
    assert len(_all(world, "/model-releases")) == releases
    live = _all(world, f"/objects/{k.supplier}", workspaceKey=partners.workspace)
    assert [item["name"] for item in live] == ["Supplier 0"]
    assert len(partners.turns()) == 1


@pytest.mark.journey("J50.70")
@pytest.mark.structures(*STRUCTURES)
def test_an_items_dry_run_needs_read_access_to_its_workspace_and_a_check_of_another_workspace_is_no_check(
    world,
    tmp_path,
    monkeypatch,
):
    """Given a draft, when a caller who may author models but may not read records in a workspace
    sends an items dry run against it, then it is refused as FORBIDDEN (R13-F6), and one who may
    read there is accepted; and an accepted task whose check was made against another workspace than
    its own loads nothing: the task fails and no release or change set is made."""
    partners = Partners(world, tmp_path, monkeypatch)
    draft = partners.settings["draft"]
    other = _workspace(world, partners.release)
    authors = ok(
        world.api.post("/roles", {"name": "Item authors", "actionGroups": ["model-authoring"]}),
        201,
    )
    readers = ok(
        world.api.post("/roles", {"name": "Item readers", "actionGroups": ["browse"]}), 201
    )
    _row, holder = _client(
        world,
        "Item author",
        (authors["key"], {"instance": True}),
        (readers["key"], {"workspaceKey": partners.workspace}),
    )
    body = {"workspaceKey": other, "items": partners.items[:3]}
    error = refused(holder.api.post(f"/model-drafts/{draft}/dry-run", body), 403, "FORBIDDEN")
    assert error["details"]["workspaceKey"] == other and error["details"]["groups"] == ["browse"]
    ok(
        holder.api.post(
            f"/model-drafts/{draft}/dry-run", {**body, "workspaceKey": partners.workspace}
        ),
        202,
    )


@pytest.mark.journey("J50.69")
@pytest.mark.structures(*STRUCTURES)
def test_accepting_a_check_made_against_another_workspace_loads_nothing(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    other = _workspace(world, partners.release)
    # The check the task holds is from a workspace that is not its own.
    _database_write(
        world,
        f"UPDATE jobs SET workspace_key = '{other}' WHERE id = '{task['check']['dryRunJobId']}'",
    )
    releases = len(_all(world, "/model-releases"))
    task = partners.accept(task)
    assert task["state"] == "failed", task["notes"]
    warning = next(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "another workspace" in warning and task["result"] is None
    assert len(_all(world, "/model-releases")) == releases
    changes = _all(world, f"/workspaces/{partners.workspace}/change-sets")
    assert [c["id"] for c in changes] == [partners.settings["changeSet"]]


@pytest.mark.journey("J50.68")
@pytest.mark.structures(*STRUCTURES)
def test_a_second_accept_after_words_loads_against_the_release_the_items_were_checked_on(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given an accepted load that installed the draft's release (the draft is then based on it and
    the workspace is not), when the person gives words and accepts again, then the new change set is
    on that release, not on the workspace's, and the items load (R13-F7)."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    task = partners.proposed()
    first = partners.accept(task)
    assert first["state"] == "loaded", first["notes"]
    installed = ok(world.api.get(f"/change-sets/{first['result']['changeSetId']}"))[
        "modelReleaseId"
    ]
    assert installed != partners.release
    # The draft now holds exactly the release it was installed as: no model change to find.
    _database_write(
        world,
        "UPDATE model_drafts SET model_json = r.model_json FROM model_releases r"
        f" WHERE r.public_id = '{installed}' AND model_drafts.base_model_release_id = r.id",
    )
    ok(
        world.api.post(
            f"/ai/tasks/{first['id']}/model",
            {"expectedVersion": first["version"], "correction": "Keep the same records."},
        ),
        202,
    )
    _run(world)
    again = _task(world, first)
    assert again["state"] == "checked", again["notes"]
    second = partners.accept(again)
    assert second["state"] == "loaded", second["notes"]
    change_set = ok(world.api.get(f"/change-sets/{second['result']['changeSetId']}"))
    assert change_set["modelReleaseId"] == installed
    assert second["result"]["counts"]["created"] == 3


@pytest.mark.journey("J50.69")
@pytest.mark.structures(*STRUCTURES)
def test_stopping_the_load_leaves_no_change_set_and_no_release(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given an accepted load that the person stops while it runs, then the change set it made is
    discarded and the release it installed is withdrawn, as the task's note says (R13-F8)."""
    from app.engine.tasks import items_load

    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    releases = len(_all(world, "/model-releases"))
    monkeypatch.setattr(items_load, "_stopped", lambda ctx: True)
    stopped = partners.accept(task)
    assert stopped["state"] == "checked", stopped["notes"]
    assert stopped["result"] is None
    assert any("discarded" in n["text"] for n in stopped["notes"])
    changes = _all(world, f"/workspaces/{partners.workspace}/change-sets")
    assert [c["id"] for c in changes] == [partners.settings["changeSet"]]
    assert len(_all(world, "/model-releases")) == releases


@pytest.mark.journey("J50.69")
@pytest.mark.structures(*STRUCTURES)
def test_a_new_check_cannot_take_the_items_away_from_an_accept(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given an accepted task waiting to load, when another items dry run of its draft is sent, then
    it is refused (the checked items stay); and if the items are gone anyway, the load fails naming
    that, with no release and no change set left (R13-F11)."""
    from app.engine.tasks import items_load

    monkeypatch.setenv("AI_AGENT_API_URL", served)
    partners = Partners(world, tmp_path, monkeypatch)
    task = partners.proposed()
    assert task["state"] == "checked", task["notes"]
    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    error = refused(
        world.api.post(
            f"/model-drafts/{partners.settings['draft']}/dry-run",
            {"workspaceKey": partners.workspace, "items": partners.items},
        ),
        409,
        "AI_TASK_STATE",
    )
    assert "being loaded" in error["message"]
    # The items vanish after the load read them (a check that slipped in): the load says so.
    items = items_load.inputs_of
    job_id = task["check"]["dryRunJobId"]

    def stale(session, previewed):
        found = items(session, previewed)
        session.execute(
            items_load.text("DELETE FROM job_inputs WHERE job_id = :job"),
            {"job": previewed.sequence_id},
        )
        session.commit()
        return found

    monkeypatch.setattr(items_load, "inputs_of", stale)
    releases = len(_all(world, "/model-releases"))
    _run(world)
    task = _task(world, task)
    assert task["state"] == "failed", task["notes"]
    warning = next(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "checked records are gone" in warning and job_id
    assert len(_all(world, "/model-releases")) == releases
    changes = _all(world, f"/workspaces/{partners.workspace}/change-sets")
    assert [c["id"] for c in changes] == [partners.settings["changeSet"]]
