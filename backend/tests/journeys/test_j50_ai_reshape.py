"""J50.46 to J50.52 — Change the model from words, and move the records with it (0.16 AP12).

A person asks in words, from the workspace, for a model change that moves records between types.
Two ways, chosen by what moves: a whole type becoming another goes by migration (the proposal's
``moves`` become ``typeMappings``; one confirmation); part of a type goes by the three steps (a
change set on a release holding both shapes, activating that release, publishing, activating the
final release). The assistant is a stand-in session working through the API with the token the
engine gives it, so every permission and refusal is the engine's.
"""

import copy
import json
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from scenario import ok, refused
from test_j24_job_stream import served  # noqa: F401  (the journey application over HTTP)
from test_j34_onboard import _all
from test_j37_workspace_migration import _confirm, _previewed, _rows
from test_j50_ai_workbook_load import _assistant, _run, _session_of, _task

from app.engine.proposals import fake

STRUCTURES = ("R",)


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


# --- the models --------------------------------------------------------------------------------


def _keys(world):
    r = world.key("R")
    return SimpleNamespace(
        supplier=f"{r}-supplier",
        vendor=f"{r}-vendor",
        partner=f"{r}-partner",
        item=f"{r}-item",
        part=f"{r}-part",
        service=f"{r}-service",
        label=f"{r}-shape-label",
        note=f"{r}-shape-note",
        extra=f"{r}-shape-extra",
        cites=f"{r}-shape-cites",
    )


def _shaped(world, tag, types, cites=True):
    """The configuration's model with ``types`` ((key, name, attribute keys)) added to R's
    application, each citing an R."""
    k = _keys(world)
    model = copy.deepcopy(world.configuration.model)
    model["attributeTypes"] += [
        {"key": key, "name": key.rsplit("-", 1)[-1].title()} for key in (k.label, k.note, k.extra)
    ]
    application = next(a for a in model["applications"] if a["key"] == world.app("R"))
    if cites:
        model["relationTypes"].append(
            {
                "key": k.cites,
                "reverseKey": f"{k.cites}--rev",
                "name": "cites",
                "reverseName": "cited by",
            }
        )
    for key, name, attributes in types:
        model["objectTypes"].append(
            {
                "key": key,
                "name": name,
                "pluralName": f"{name}s",
                "displayAttributeTypeKey": k.label,
                "attributes": [
                    {"attributeTypeKey": a, "order": 10 * (n + 1)} for n, a in enumerate(attributes)
                ],
                "features": {"rootCreatable": True},
            }
        )
        application["objectTypeKeys"].append(key)
        if cites:
            model["objectTypeRelations"].append(
                {
                    "relationTypeKey": k.cites,
                    "fromObjectTypeKey": key,
                    "toObjectTypeKey": world.key("R"),
                    "cardinality": "many-to-many",
                }
            )
    model["release"]["version"] = f"{model['release']['version']}-{tag}-{uuid4().hex[:6]}"
    return model


def _workspace(world, release_id):
    key = f"shape-{uuid4().hex[:8]}"
    ok(
        world.api.post("/workspaces", {"key": key, "label": "Shape", "modelReleaseId": release_id}),
        201,
    )
    return key


def _record(world, workspace, type_key, name, values, parent=None):
    body = {
        "workspaceKey": workspace,
        "applicationKey": world.app("R"),
        "objectTypeKey": type_key,
        "name": name,
        "attributes": [{"attributeTypeKey": key, "value": value} for key, value in values.items()],
    }
    if parent is not None:
        body["parentObjectId"] = parent
    return ok(world.api.post("/objects", body), 201)


def _placed(world, model, kinds, group_key, contains_key):
    """``model`` with a group type holding the records of ``kinds``: each lists the group as its
    parent through the containment relation type, so a record of it is created under a group."""
    application = next(a for a in model["applications"] if a["key"] == world.app("R"))
    if not any(r["key"] == contains_key for r in model["relationTypes"]):
        model["relationTypes"].append(
            {
                "key": contains_key,
                "reverseKey": f"{contains_key}--rev",
                "name": "contains",
                "reverseName": "contained in",
                "features": {"parentOf": True},
            }
        )
    if not any(t["key"] == group_key for t in model["objectTypes"]):
        model["objectTypes"].append(
            {
                "key": group_key,
                "name": "Group",
                "pluralName": "Groups",
                "displayAttributeTypeKey": _keys(world).label,
                "attributes": [{"attributeTypeKey": _keys(world).label, "order": 10}],
                "features": {"rootCreatable": True},
            }
        )
        application["objectTypeKeys"].append(group_key)
    for kind, parent_key in kinds:
        item = next(t for t in model["objectTypes"] if t["key"] == kind)
        item.setdefault("behavior", {})["parentRelationTypeKeys"] = [contains_key]
        model["objectTypeRelations"].append(
            {
                "relationTypeKey": contains_key,
                "fromObjectTypeKey": parent_key,
                "toObjectTypeKey": kind,
                "cardinality": "one-to-many",
            }
        )


def _inventory(world, workspace, type_keys):
    """Every record of the types, by ID: its name, its values and its history length."""
    found = {}
    for type_key in type_keys:
        for item in _all(world, f"/objects/{type_key}", workspaceKey=workspace):
            full = ok(world.api.get(f"/objects/{type_key}/{item['id']}", workspaceKey=workspace))
            history = _all(world, f"/objects/{type_key}/{item['id']}/history", page_size=100)
            found[item["id"]] = {
                "type": type_key,
                "name": full["name"],
                "values": {a["attributeTypeKey"]: a["value"] for a in full["attributes"]},
                "history": len(history),
            }
    return found


def _relations(world, workspace):
    return {
        (r["relationTypeKey"], r["source"]["id"], r["target"]["id"])
        for r in _all(
            world, f"/workspaces/{workspace}/relations", page_size=100, direction="outgoing"
        )
    }


# --- the stand-in session ------------------------------------------------------------------------


SESSION = """#!/usr/bin/env python3
import json, os, re, sys, httpx
prompt = sys.argv[sys.argv.index("--") + 1]
config = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")))
print(json.dumps({"type": "system", "subtype": "init", "model": "claude-test-1"}), flush=True)
if not os.path.exists("url.txt"):
    open("url.txt", "w").write(re.search(r"https?://[\\w.:-]+", prompt).group(0))
base = open("url.txt").read() + "/api/v1"
head = {"Authorization": "Bearer " + os.environ["REFIROO_TOKEN"]}
def api(method, path, ok=True, **kw):
    sent = httpx.request(method, base + path, headers=head, timeout=120, **kw)
    if ok:
        assert sent.status_code < 300, (method, path, sent.status_code, sent.text)
    return sent
def install(model=None, draft=None, name="Session"):
    if draft is None:
        draft = api("POST", "/model-drafts", json={"name": name, "model": model}).json()["id"]
    version = api("GET", "/model-drafts/" + draft).json()["version"]
    return api("POST", "/model-drafts/" + draft + "/installation", json={"expectedVersion": version}).json()["id"]
import traceback
def failed(kind, value, trace):
    open(config["log"], "a").write(json.dumps({"error": "".join(traceback.format_exception(kind, value, trace))}) + "\\n")
sys.excepthook = failed
log = open(config["log"], "a")
log.write(json.dumps({"prompt": prompt}) + "\\n")
log.close()
if "accepted" not in prompt:
    if config.get("early"):
        install(config["both"], name="Early")
    if "refuses the draft" in prompt and config.get("repair"):
        held = api("GET", "/model-drafts/" + config["draft"]).json()["version"]
        api("PATCH", "/model-drafts/" + config["draft"], json={"expectedVersion": held, "model": config["repair"]})
    again = "refuses the draft" in prompt and config.get("fixed")
    proposal = {"draftId": config["fixed"] if again else config["draft"], "summary": "A plan.", "questions": []}
    if config.get("moves") is not None:
        proposal["moves"] = config["moves"]
    if config.get("removals") is not None:
        proposal["removals"] = config["removals"]
    if config.get("title"):
        proposal["title"] = config["title"]
    if not config.get("silent"):
        json.dump(proposal, open("proposal.json", "w"))
    print(json.dumps({"type": "result", "result": "Ready."}))
elif config["mode"] == "merge":
    release = install(draft=config.get("fixed") or config["draft"])
    print(json.dumps({"type": "result", "result": "Done.\\nRELEASE: " + release}))
else:
    workspace = config["workspace"]
    final = install(draft=config["draft"])
    both = install(config["both"], name="Both")
    if config.get("extra"):
        install(config["extra"], name="Extra")
    made = api("POST", "/workspaces/" + workspace + "/change-sets", json={"name": "Split", "source": "currentLive", "modelReleaseId": both}).json()
    items = []
    cursor = None
    while True:
        page = api("GET", "/objects/" + config["from"], params={"workspaceKey": workspace, "pageSize": 100, **({"cursor": cursor} if cursor else {})}).json()
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    for item in items:
        full = api("GET", "/objects/" + config["from"] + "/" + item["id"], params={"workspaceKey": workspace}).json()
        note = next(a["value"] for a in full["attributes"] if a["attributeTypeKey"] == config["note"])
        body = {"operation": {"kind": "changeType", "objectId": item["id"], "objectTypeKey": config["targets"][note]}}
        plan = api("POST", "/change-sets/" + made["id"] + "/restructurings/preview", json=body).json()
        api("POST", "/change-sets/" + made["id"] + "/restructurings", json={**body, "expectedChangeSetVersion": plan["changeSetVersion"], "planDigest": plan["planDigest"]})
    activation = api("POST", "/workspaces/" + workspace + "/model/activation", ok=False, json={"releaseId": both, "expectedVersion": 1, "expectedReleaseId": "x"})
    json.dump({"activation": activation.status_code}, open(config["report"], "w"))
    print(json.dumps({"type": "result", "result": "Done.\\nCHANGE_SET: " + made["id"] + ("" if config.get("omit_then") else "\\nTHEN_RELEASE: " + final)}))
"""


def _ask(world, workspace, words):
    return ok(
        world.api.upload(
            "/ai/tasks", {}, {"request": json.dumps({"workspaceKey": workspace, "words": words})}
        ),
        202,
    )


def _accept(world, task):
    ok(world.api.post(f"/ai/tasks/{task['id']}/accept", {"expectedVersion": task["version"]}), 202)
    _run(world)
    return _task(world, task)


def _release_status(world, release_id):
    return ok(world.api.get(f"/model-releases/{release_id}"))["status"]


# --- whole types: one release and one migration ------------------------------------------------------


class Merge:
    """A workspace holding suppliers and vendors, and the model that makes them one type."""

    def __init__(
        self,
        world,
        tmp_path,
        monkeypatch,
        *,
        moves="both",
        consumer=False,
        parented=False,
        additive=False,
        elsewhere=False,
        shared=None,
        lossy=None,
        drops=None,
    ):
        self.world = world
        k = self.k = _keys(world)
        first = _shaped(
            world,
            "merge-1",
            [
                (k.supplier, "Supplier", [k.label, k.note]),
                (k.vendor, "Vendor", [k.label, k.extra]),
            ],
        )
        self.final = _shaped(world, "merge-2", [(k.partner, "Partner", [k.label, k.note, k.extra])])
        if additive:
            # The model only grows: the old types stay and a new one is added beside them.
            self.final = _shaped(
                world,
                "merge-2",
                [
                    (k.supplier, "Supplier", [k.label, k.note]),
                    (k.vendor, "Vendor", [k.label, k.extra]),
                    (k.partner, "Partner", [k.label, k.note, k.extra]),
                ],
            )
        if elsewhere:
            # The types keep their keys and stand in another application.
            self.final = _shaped(
                world,
                "merge-2",
                [
                    (k.supplier, "Supplier", [k.label, k.note]),
                    (k.vendor, "Vendor", [k.label, k.extra]),
                ],
            )
            home = next(a for a in self.final["applications"] if a["key"] == world.app("R"))
            moved = [key for key in (k.supplier, k.vendor)]
            home["objectTypeKeys"] = [x for x in home["objectTypeKeys"] if x not in moved]
            self.final["applications"].append(
                {
                    "key": f"{k.item}-moved",
                    "name": "Moved lists",
                    "objectTypeKeys": moved,
                    "defaultView": f"{k.supplier}--list",
                    "views": [
                        {
                            "key": f"{k.supplier}--list",
                            "name": "Suppliers",
                            "type": "table",
                            "objectTypeKey": k.supplier,
                            "config": {
                                "columns": ["name", k.label],
                                "filterFields": ["name"],
                                "sortFields": ["name", k.label],
                                "defaultSort": "name",
                                "pageSize": 20,
                            },
                        }
                    ],
                }
            )
        removals = None
        if drops:
            # The words ask to delete the vendors; ``drops="more"`` also drops suppliers' note field,
            # which the words never mention.
            self.final = _shaped(
                world,
                "merge-2",
                [(k.supplier, "Supplier", [k.label] if drops == "more" else [k.label, k.note])],
            )
            removals = [
                {
                    "kind": "objectType",
                    "key": k.vendor,
                    "words": "Delete the vendors, I do not need them",
                }
            ]
        if shared:
            # An application beside them lists both types in the current model and the target (a
            # translations-like one), so the types the target lists in the moved application also
            # stand in two applications. ``ambiguous`` adds a second new application listing them.
            for model in (first, self.final):
                model["applications"].append(self.listing(f"{k.item}-all", (k.supplier, k.vendor)))
            if shared == "ambiguous":
                self.final["applications"].append(
                    self.listing(f"{k.item}-also", (k.supplier, k.vendor))
                )
        if lossy == "proposal":
            self.final = self.without_extra(self.final)
        fixed = None
        group, contains, other = f"{k.item}-group", f"{k.item}-contains", f"{k.item}-other"
        if parented:
            # Suppliers and vendors sit under a group. The session's first draft puts the merged type
            # under another group type, which holds no records; the corrected draft under theirs.
            _placed(world, first, [(k.supplier, group), (k.vendor, group)], group, contains)
            _placed(world, self.final, [], group, contains)
            _placed(world, self.final, [(k.partner, other)], other, contains)
            fixed = copy.deepcopy(self.final)
            fixed["objectTypeRelations"] = [
                {**pair, "fromObjectTypeKey": group}
                if pair["toObjectTypeKey"] == k.partner and pair["relationTypeKey"] == contains
                else pair
                for pair in fixed["objectTypeRelations"]
            ]
            fixed["release"]["version"] += "-placed"
        if consumer:
            # A consumer API exposes the types that become one; the proposal's draft exposes the new
            # type without raising the version, then (the fixed draft) with it raised.
            first["consumerApis"].append(self.api([k.supplier, k.vendor], 1))
            self.final["consumerApis"].append(self.api([k.partner], 1))
            fixed = copy.deepcopy(self.final)
            fixed["consumerApis"][-1]["contractVersion"] = 2
            fixed["release"]["version"] += "-raised"
        x1 = world.install(first, name="Suppliers and vendors")
        self.workspace = _workspace(world, x1["id"])
        anchor = world.made("R", "Anchor", workspace=self.workspace)
        parent = (
            _record(world, self.workspace, group, "Group", {k.label: "G"})["id"]
            if parented
            else None
        )
        self.records = {}
        for n in range(3):
            self.records[f"s{n}"] = _record(
                world,
                self.workspace,
                k.supplier,
                f"Supplier {n}",
                {k.label: f"S{n}", k.note: f"note {n}"},
                parent,
            )
        for n in range(2):
            self.records[f"v{n}"] = _record(
                world,
                self.workspace,
                k.vendor,
                f"Vendor {n}",
                {k.label: f"V{n}", k.extra: f"extra {n}"},
                parent,
            )
        for name in ("s0", "v0"):
            ok(
                world.api.post(
                    "/relations",
                    {
                        "relationTypeKey": k.cites,
                        "fromObjectId": self.records[name]["id"],
                        "toObjectId": anchor["id"],
                        "attributes": {},
                    },
                ),
                201,
            )
        self.moves = (
            [
                {"from": k.supplier, "to": k.partner},
                {"from": k.vendor, "to": k.partner, "attributes": []},
            ]
            if moves == "both"
            else moves
        )
        self.settings = _assistant(
            world,
            tmp_path,
            monkeypatch,
            self.workspace,
            script=SESSION,
            model=self.final,
            api=True,
            mode="merge",
            moves=self.moves,
            removals=removals,
            fixed=(
                ok(world.api.post("/model-drafts", {"name": "Raised", "model": fixed}), 201)["id"]
                if fixed
                else None
            ),
        )
        if drops:
            # The session's draft is based on the release the workspace runs, as the prompt tells it.
            self.settings["draft"] = ok(
                world.api.post(
                    "/model-drafts",
                    {"name": "Drops", "model": self.final, "baseReleaseId": x1["id"]},
                ),
                201,
            )["id"]
            (tmp_path / "config.json").write_text(json.dumps(self.settings))
        if lossy == "installed":
            # The proposal is whole; the release the session installs on accepting is not.
            drops = self.without_extra(self.final)
            drops["release"]["version"] += "-drops"
            self.settings["fixed"] = ok(
                world.api.post("/model-drafts", {"name": "Drops", "model": drops}), 201
            )["id"]
            (tmp_path / "config.json").write_text(json.dumps(self.settings))

    def without_extra(self, model):
        """The model with the merged type no longer holding the attribute vendors have."""
        model = copy.deepcopy(model)
        for item in model["objectTypes"]:
            if item["key"] == self.k.partner:
                item["attributes"] = [
                    b for b in item["attributes"] if b["attributeTypeKey"] != self.k.extra
                ]
        return model

    @staticmethod
    def listing(key, types):
        return {
            "key": key,
            "name": key,
            "objectTypeKeys": list(types),
            "defaultView": f"{key}--list",
            "views": [
                {
                    "key": f"{key}--list",
                    "name": "All",
                    "type": "table",
                    "objectTypeKey": types[0],
                    "config": {
                        "columns": ["name"],
                        "filterFields": ["name"],
                        "sortFields": ["name"],
                        "defaultSort": "name",
                        "pageSize": 20,
                    },
                }
            ],
        }

    @staticmethod
    def api(types, version):
        return {
            "key": "merge-api",
            "name": "Merge API",
            "contractVersion": version,
            "exposes": types,
            "publicNames": {key: key.rsplit("-", 1)[-1].title() for key in types},
            "object": {"fields": {"id": {"role": "id"}, "name": {"role": "name", "from": "name"}}},
            "operations": {"objects": {}},
        }

    def before(self):
        return _inventory(self.world, self.workspace, (self.k.supplier, self.k.vendor))


def _proposed(
    world, workspace, words="Suppliers and vendors are the same thing: make them one type."
):
    task = _ask(world, workspace, words)
    _run(world)
    return _task(world, task)


@pytest.mark.journey("J50.45")
@pytest.mark.structures(*STRUCTURES)
def test_a_draft_the_session_corrects_in_place_is_checked_as_corrected(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a refused draft, when the session corrects that same draft through the API during its
    next turn, then the engine checks the corrected draft and the task lands instead of failing."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, parented=True)
    fixed = ok(world.api.get(f"/model-drafts/{merge.settings['fixed']}"))["model"]
    merge.settings["repair"] = fixed
    merge.settings["fixed"] = None
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    task = _proposed(world, merge.workspace)
    assert task["state"] == "checked", task["notes"]
    prompts = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    sent = [p["prompt"] for p in prompts if "prompt" in p and "refuses the draft" in p["prompt"]]
    assert len(sent) == 1


@pytest.mark.journey("J50.46")
@pytest.mark.structures(*STRUCTURES)
def test_a_merge_from_words_moves_every_record_by_one_migration(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a workspace with records of two types, when a session proposes them as one and the
    person accepts and confirms the migration, then every record is under the new type with its ID,
    values, relationships and history, the old types are gone, and the workspace runs the release."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch)
    k = merge.k
    before = merge.before()
    relations_before = _relations(world, merge.workspace)
    task = _accept(world, _proposed(world, merge.workspace))
    assert task["state"] == "loaded", task["notes"]
    assert task["result"].get("changeSetId") is None
    migration = task["result"]["migration"]
    assert [(m["fromObjectTypeKey"], m["toObjectTypeKey"]) for m in migration["typeMappings"]] == [
        (k.supplier, k.partner),
        (k.vendor, k.partner),
    ]
    # Nothing has moved: the migration is the person's to confirm.
    assert _inventory(world, merge.workspace, (k.supplier, k.vendor)) == before

    job = _previewed(
        world, merge.workspace, migration["releaseId"], typeMappings=migration["typeMappings"]
    )
    assert job["state"] == "awaiting_confirmation", job
    assert job["migration"]["counts"]["refused"] == 0 and job["migration"]["counts"]["loss"] == 0
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    assert (
        ok(world.api.get(f"/workspaces/{merge.workspace}/model"))["releaseId"]
        == migration["releaseId"]
    )
    after = _inventory(world, merge.workspace, (k.partner,))
    assert set(after) == set(before)
    for record_id, was in before.items():
        now = after[record_id]
        assert now["name"] == was["name"]
        assert now["values"] == was["values"], record_id
        assert now["history"] > was["history"]
        gone = world.api.get(f"/objects/{was['type']}/{record_id}", workspaceKey=merge.workspace)
        assert gone.status_code == 404
    moved = {(t, f, o) for t, f, o in _relations(world, merge.workspace)}
    assert {(f, o) for _, f, o in moved} == {(f, o) for _, f, o in relations_before}
    assert all(t == k.cites for t, _, _ in moved)


@pytest.mark.journey("J50.66")
@pytest.mark.structures(*STRUCTURES)
def test_a_model_only_request_ends_in_a_migration_with_no_type_mappings(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a request that changes only the model, when the person accepts and the session installs
    a release without a change set, then the task is loaded with a migration of no mappings, nothing
    has moved, and confirming the migration puts the workspace on the release with every record."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, moves=None, additive=True)
    k = merge.k
    before = merge.before()
    task = _accept(world, _proposed(world, merge.workspace))
    assert task["state"] == "loaded", task["notes"]
    assert task["result"].get("changeSetId") is None
    migration = task["result"]["migration"]
    assert migration["typeMappings"] == []
    assert merge.before() == before

    job = _previewed(world, merge.workspace, migration["releaseId"], typeMappings=[])
    assert job["state"] == "awaiting_confirmation", job
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    assert (
        ok(world.api.get(f"/workspaces/{merge.workspace}/model"))["releaseId"]
        == migration["releaseId"]
    )
    assert merge.before() == before
    assert _all(world, f"/objects/{k.partner}", workspaceKey=merge.workspace) == []


@pytest.mark.journey("J50.66")
@pytest.mark.structures(*STRUCTURES)
def test_types_moved_to_another_application_are_handed_to_the_migration_with_it(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a model whose types keep their keys and stand in another application, when the person
    accepts, then the task is a migration naming the application each type goes to and the proposal
    says the types move and how many records; the preview loses nothing and confirming moves the
    records with their IDs."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, moves=None, elsewhere=True)
    k = merge.k
    before = merge.before()
    proposed = _proposed(world, merge.workspace)
    moves = {m["from"]: m for m in proposed["design"]["moves"]}
    assert {key: (m["to"], m["toApplication"], m["records"]) for key, m in moves.items()} == {
        k.supplier: (k.supplier, f"{k.item}-moved", 3),
        k.vendor: (k.vendor, f"{k.item}-moved", 2),
    }
    task = _accept(world, proposed)
    assert task["state"] == "loaded", task["notes"]
    migration = task["result"]["migration"]
    assert {m["fromObjectTypeKey"]: m["toApplicationKey"] for m in migration["typeMappings"]} == {
        k.supplier: f"{k.item}-moved",
        k.vendor: f"{k.item}-moved",
    }
    job = _previewed(
        world,
        merge.workspace,
        migration["releaseId"],
        typeMappings=migration["typeMappings"],
    )
    assert job["state"] == "awaiting_confirmation", job
    assert job["migration"]["counts"]["loss"] == 0 and job["migration"]["counts"]["refused"] == 0
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    assert set(merge.before()) == set(before)


def _read_application(world, workspace, record):
    return ok(
        world.api.get(f"/objects/{record['objectTypeKey']}/{record['id']}", workspaceKey=workspace)
    )["applicationKey"]


@pytest.mark.journey("J50.66")
@pytest.mark.structures(*STRUCTURES)
def test_records_of_a_type_the_target_still_lists_are_moved_never_lost(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given types that move to another application while a third application lists every one of
    them, when the migration is previewed with no mapping at all, then nothing is lost: the records
    go to the application that lists the types newly, with their relationships. When two new
    applications list them and nothing names one, the preview refuses the records, naming the
    candidates, and loses none."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, moves=None, elsewhere=True, shared="listed")
    k = merge.k
    relations_before = _relations(world, merge.workspace)
    task = _accept(world, _proposed(world, merge.workspace))
    assert task["state"] == "loaded", task["notes"]
    release_id = task["result"]["migration"]["releaseId"]

    job = _previewed(world, merge.workspace, release_id, typeMappings=[])
    assert job["state"] == "awaiting_confirmation", job
    counts = job["migration"]["counts"]
    assert counts["loss"] == 0 and counts["refused"] == 0 and counts["reclassified"] == 5
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    for record in merge.records.values():
        assert _read_application(world, merge.workspace, record) == f"{k.item}-moved"
    assert sorted(_relations(world, merge.workspace)) == sorted(relations_before)

    crowded = Merge(world, tmp_path, monkeypatch, moves=None, elsewhere=True, shared="ambiguous")
    task = _accept(world, _proposed(world, crowded.workspace))
    # The draft's migration names no application for records two own ones could take (R13-F12), so
    # the assistant offers no migration to confirm and says which records the engine would refuse;
    # the release it installed is still previewed, and refuses them by name.
    assert task["state"] == "failed" and task["result"] is None, task["notes"]
    warning = " ".join(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "APPLICATION_TARGET_AMBIGUOUS" in warning and f"{crowded.k.item}-also" in warning
    release_id = re.search(r"RELEASE: (\S+)", " ".join(n["text"] for n in task["notes"])).group(1)
    job = _previewed(world, crowded.workspace, release_id, typeMappings=[])
    counts = job["migration"]["counts"]
    assert counts["loss"] == 0 and counts["refused"] == 5, job["migration"]
    refusals = _rows(world, job["id"], status="refused")
    assert {row["code"] for row in refusals} == {"APPLICATION_TARGET_AMBIGUOUS"}
    assert f"{crowded.k.item}-also" in refusals[0]["message"]


@pytest.mark.journey("J50.66")
@pytest.mark.structures(*STRUCTURES)
def test_a_merge_that_would_lose_values_is_never_offered(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a merge whose target type has no place for an attribute vendors hold, when the session
    keeps proposing it, then the engine's finding goes back to the session and the task ends with a
    warning naming what would be lost per type, offering no migration and changing nothing. The same
    when the release the session installs on accepting loses what the proposal did not."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, lossy="proposal")
    before = merge.before()
    task = _proposed(world, merge.workspace)
    assert task["state"] == "failed", task
    warning = " ".join(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "Vendor: 2 values" in warning and "Nothing was changed" in warning, warning
    assert not task.get("result")
    prompts = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert any("would lose the person's data" in p.get("prompt", "") for p in prompts)
    assert merge.before() == before

    later = Merge(world, tmp_path, monkeypatch, lossy="installed")
    before = later.before()
    task = _accept(world, _proposed(world, later.workspace))
    assert task["state"] == "failed", task
    warning = " ".join(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "Vendor: 2 values" in warning and "No data was changed" in warning, warning
    assert not (task.get("result") or {}).get("migration")
    assert later.before() == before


ASKED = "Please delete the vendors, I do not need them, and keep the rest."


@pytest.mark.journey("J50.66")
@pytest.mark.structures(*STRUCTURES)
def test_what_the_words_ask_to_remove_is_offered_as_a_deletion_and_nothing_more(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given words that ask to delete the vendors, a type holding records, when the session lists the
    removal with the person's words, then the task is offered with the deletion stated in plain words
    with its counts, and the handover carries it. A draft that also drops a field the words never
    mention is not offered: the loss beyond the removal is named and nothing is changed."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, moves=None, drops="vendor")
    before = merge.before()
    task = _proposed(world, merge.workspace, ASKED)
    assert task["state"] == "checked", task["notes"]
    [removal] = task["design"]["removals"]
    assert removal["text"] == (
        "As you asked, Vendor is deleted, deleting 2 records, 1 relationship."
    ), removal
    assert removal["words"] == "Delete the vendors, I do not need them"
    assert any(n["text"] == removal["text"] for n in task["notes"])
    task = _accept(world, task)
    assert task["state"] == "loaded", task["notes"]
    assert task["result"]["migration"]["typeMappings"] == []
    assert any(n["text"] == removal["text"] for n in task["notes"])
    assert set(merge.before()) == set(
        before
    )  # nothing is deleted before the migration is confirmed

    beyond = Merge(world, tmp_path, monkeypatch, moves=None, drops="more")
    kept = beyond.before()
    task = _proposed(world, beyond.workspace, ASKED)
    assert task["state"] == "failed", task
    warning = " ".join(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "Supplier: 3 values" in warning and "Vendor" not in warning, warning
    assert beyond.before() == kept

    # Words the person never wrote are no ask: the session's quote is dropped, so deleting the
    # vendors is a loss nobody asked for and blocks.
    unwritten = Merge(world, tmp_path, monkeypatch, moves=None, drops="vendor")
    task = _proposed(world, unwritten.workspace, "Tidy the model up a little.")
    assert task["state"] == "failed", task
    warning = " ".join(n["text"] for n in task["notes"] if n["kind"] == "warning")
    assert "Vendor: 2 records" in warning, warning
    assert not task["design"].get("removals")
    # Case, spacing and quote marks do not matter, and a quote may be part of a sentence.
    loose = Merge(world, tmp_path, monkeypatch, moves=None, drops="vendor")
    task = _proposed(
        world, loose.workspace, "Please  “DELETE the vendors”, i do not need them. Thanks!"
    )
    assert task["state"] == "checked", task["notes"]


@pytest.mark.journey("J50.46")
@pytest.mark.structures(*STRUCTURES)
def test_a_merge_the_consumers_would_notice_is_sent_back_until_the_version_is_raised(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a consumer API that exposes the types that become one, when the session's draft does not
    raise its contractVersion, then the engine sends the contract error back and the session raises
    it; the proposal says the version change, and the migration the task ends with previews."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, consumer=True)
    task = _proposed(world, merge.workspace)
    assert task["state"] == "checked", task["notes"]
    prompts = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    sent = [p["prompt"] for p in prompts if "prompt" in p and "refuses the draft" in p["prompt"]]
    assert len(sent) == 1 and "Merge API" not in sent[0] and "merge-api" in sent[0]
    (change,) = task["design"]["consumerChanges"]
    assert (change["api"], change["from"], change["to"]) == ("merge-api", 1, 2)
    assert any("Supplier" in text or merge.k.supplier in text for text in change["changes"])

    task = _accept(world, task)
    assert task["state"] == "loaded", task["notes"]
    migration = task["result"]["migration"]
    job = _previewed(
        world, merge.workspace, migration["releaseId"], typeMappings=migration["typeMappings"]
    )
    assert job["state"] == "awaiting_confirmation", job


@pytest.mark.journey("J50.46")
@pytest.mark.structures(*STRUCTURES)
def test_a_draft_that_keeps_breaking_the_consumers_fails_the_task_naming_the_api(
    world, tmp_path, monkeypatch
):
    """Given a session that never raises the version, then the task fails with a warning naming the
    consumer API, and nothing is installed."""
    merge = Merge(world, tmp_path, monkeypatch, consumer=True)
    merge.settings["fixed"] = None
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    releases = len(_all(world, "/model-releases"))
    task = _proposed(world, merge.workspace)
    assert task["state"] == "failed"
    assert any("merge-api" in note["text"] for note in task["notes"])
    assert len(_all(world, "/model-releases")) == releases


@pytest.mark.journey("J50.46")
@pytest.mark.structures(*STRUCTURES)
def test_a_merge_that_leaves_the_records_no_place_is_sent_back_and_then_moves_them(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given records under a group, when the session's draft gives the merged type a place only under
    a type that holds none, then the engine sends the refusal back with the counts and example
    names, the corrected draft lands, the migration preview refuses nothing, and confirming moves
    every record with its ID."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, parented=True)
    k = merge.k
    before = merge.before()
    task = _proposed(world, merge.workspace)
    assert task["state"] == "checked", task["notes"]
    prompts = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    sent = [p["prompt"] for p in prompts if "prompt" in p and "refuses the draft" in p["prompt"]]
    assert len(sent) == 1
    assert "PARENT_RELATION_SEMANTICS_CHANGED" in sent[0] and "5 records" in sent[0]
    assert "Supplier 0" in sent[0] and k.partner in sent[0]

    task = _accept(world, task)
    assert task["state"] == "loaded", task["notes"]
    migration = task["result"]["migration"]
    job = _previewed(
        world, merge.workspace, migration["releaseId"], typeMappings=migration["typeMappings"]
    )
    assert job["state"] == "awaiting_confirmation", job
    assert job["migration"]["counts"]["refused"] == 0
    ok(_confirm(world, job), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    after = _inventory(world, merge.workspace, (k.partner,))
    assert set(after) == set(before)


@pytest.mark.journey("J50.46")
@pytest.mark.structures(*STRUCTURES)
def test_a_merge_the_session_never_places_fails_the_task_with_the_engines_reason(
    world, tmp_path, monkeypatch
):
    """Given a session that never gives the merged type the records' place, then the task fails with a
    warning carrying the engine's reason and count, and nothing is installed."""
    merge = Merge(world, tmp_path, monkeypatch, parented=True)
    merge.settings["fixed"] = None
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    releases = len(_all(world, "/model-releases"))
    task = _proposed(world, merge.workspace)
    assert task["state"] == "failed"
    assert any(
        "PARENT_RELATION_SEMANTICS_CHANGED" in note["text"] and "5 records" in note["text"]
        for note in task["notes"]
    ), task["notes"]
    assert len(_all(world, "/model-releases")) == releases


# --- the proposal says what moves -------------------------------------------------------------------


@pytest.mark.journey("J50.47")
@pytest.mark.structures(*STRUCTURES)
def test_the_proposal_says_what_moves_and_a_move_the_draft_lacks_fails_the_task(
    world, tmp_path, monkeypatch
):
    """Given moves, the proposal holds each type's record count and no left-out warning for those
    types. Given a move naming a type the draft lacks, the task fails with the reason and nothing is
    installed."""
    merge = Merge(world, tmp_path, monkeypatch)
    k = merge.k
    task = _proposed(world, merge.workspace)
    assert task["state"] == "checked"
    moves = {m["from"]: m for m in task["design"]["moves"]}
    assert {key: (m["to"], m["records"]) for key, m in moves.items()} == {
        k.supplier: (k.partner, 3),
        k.vendor: (k.partner, 2),
    }
    assert moves[k.supplier]["fromName"] == "Supplier" and moves[k.supplier]["toName"] == "Partner"
    assert [c for c in task["design"]["checks"] if c["kind"] == "leftOut"] == []

    releases = len(_all(world, "/model-releases"))
    merge.settings["moves"] = [{"from": k.supplier, "to": f"{k.partner}-nowhere"}]
    merge.settings["draft"] = ok(
        world.api.post("/model-drafts", {"name": "Another", "model": merge.final}), 201
    )["id"]
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    task = _proposed(world, merge.workspace)
    assert task["state"] == "failed"
    assert any(f"{k.partner}-nowhere" in note["text"] for note in task["notes"])
    assert len(_all(world, "/model-releases")) == releases


# --- part of a type: three steps ---------------------------------------------------------------------


class Split:
    """A workspace holding items, and the models that split them by a value into parts and services."""

    def __init__(self, world, tmp_path, monkeypatch, **config):
        self.world = world
        k = self.k = _keys(world)
        x1 = world.install(
            _shaped(world, "split-1", [(k.item, "Item", [k.label, k.note])]), name="Items"
        )
        self.workspace = _workspace(world, x1["id"])
        two = [(k.part, "Part", [k.label, k.note]), (k.service, "Service", [k.label, k.note])]
        self.final = _shaped(world, "split-3", two)
        self.both = _shaped(world, "split-2", [(k.item, "Item", [k.label, k.note]), *two])
        self.records = {}
        for n in range(4):
            kind = "part" if n % 2 == 0 else "service"
            self.records[n] = _record(
                world, self.workspace, k.item, f"Item {n}", {k.label: f"I{n}", k.note: kind}
            )
        self.report = tmp_path / "report.json"
        self.settings = _assistant(
            world,
            tmp_path,
            monkeypatch,
            self.workspace,
            script=SESSION,
            model=self.final,
            api=True,
            mode="parts",
            both=self.both,
            report=str(self.report),
            **{"from": k.item, "note": k.note, "targets": {"part": k.part, "service": k.service}},
            **config,
        )

    def before(self):
        return _inventory(self.world, self.workspace, (self.k.item,))

    def live(self, *types):
        return _inventory(self.world, self.workspace, types)

    def unchanged(self, before):
        """The items as they were: the history is not compared, as a restructuring in a change set
        records its event on the record before it is published."""
        now = self.live(self.k.item)

        def strip(found):
            return {i: {**v, "history": None} for i, v in found.items()}

        return strip(now) == strip(before)


def _split_loaded(world, split):
    task = _accept(world, _proposed(world, split.workspace))
    assert task["state"] == "loaded", task["notes"]
    return task


@pytest.mark.journey("J50.48")
@pytest.mark.structures(*STRUCTURES)
def test_part_of_a_type_waits_in_a_change_set_on_a_release_the_workspace_does_not_run(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given records of one type, when a session restructures part into a new type on an installed
    release the workspace does not run, then live data is unchanged, the change set holds them with
    their IDs, and the session is refused activation."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    split = Split(world, tmp_path, monkeypatch)
    k = split.k
    before = split.before()
    running = ok(world.api.get(f"/workspaces/{split.workspace}/model"))["releaseId"]
    task = _split_loaded(world, split)
    assert task["state"] == "loaded" and task["result"]["thenReleaseId"]
    assert split.unchanged(before)
    assert ok(world.api.get(f"/workspaces/{split.workspace}/model"))["releaseId"] == running
    change_set = ok(world.api.get(f"/change-sets/{task['result']['changeSetId']}"))
    assert change_set["modelReleaseId"] != running
    held = {
        i["id"]: i
        for t in (k.part, k.service)
        for i in _all(world, f"/objects/{t}", changeSetId=change_set["id"])
    }
    assert set(held) == set(before)
    assert {item["objectTypeKey"] for item in held.values()} == {k.part, k.service}
    assert json.loads(split.report.read_text())["activation"] == 403


@pytest.mark.journey("J50.49")
@pytest.mark.structures(*STRUCTURES)
def test_the_three_steps_activate_both_publish_and_activate_the_final_release(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Continuing J50.48: the person activates the release with both and nothing moves; publishes,
    and the records are live under the new type; activates the final release, and the old type is
    gone. Before the publication that last activation is refused, nothing changed."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    split = Split(world, tmp_path, monkeypatch)
    k = split.k
    before = split.before()
    task = _split_loaded(world, split)
    both = ok(world.api.get(f"/change-sets/{task['result']['changeSetId']}"))["modelReleaseId"]
    final = task["result"]["thenReleaseId"]
    assert task["result"]["changeSetReleaseId"] == both

    ok(world.activate(both, split.workspace))
    assert split.unchanged(before)
    refused_final = world.activate(final, split.workspace)
    assert refused_final.status_code in (409, 422), refused_final.text
    assert ok(world.api.get(f"/workspaces/{split.workspace}/model"))["releaseId"] == both
    assert split.unchanged(before)

    world.publish({"id": task["result"]["changeSetId"]}, split.workspace)
    after = split.live(k.part, k.service)
    assert set(after) == set(before)
    for record_id, was in before.items():
        assert after[record_id]["name"] == was["name"]
        assert after[record_id]["values"] == was["values"]
    assert split.live(k.item) == {}

    ok(world.activate(final, split.workspace))
    assert ok(world.api.get(f"/workspaces/{split.workspace}/model"))["releaseId"] == final
    gone = world.api.get(f"/objects/{k.item}", workspaceKey=split.workspace)
    assert gone.status_code in (404, 422)
    assert split.live(k.part, k.service) == after


# --- approval and permission -------------------------------------------------------------------------


@pytest.mark.journey("J50.50")
@pytest.mark.structures(*STRUCTURES)
def test_part_of_a_type_goes_through_approval_and_a_migration_needs_model_release(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Part of a type goes through approval as any change set. A whole-type migration confirms as a
    migration does, by a holder of Model release; without it, FORBIDDEN."""
    from test_j40_authorization import _client

    monkeypatch.setenv("AI_AGENT_API_URL", served)
    split = Split(world, tmp_path, monkeypatch)
    policy = f"/workspaces/{split.workspace}/approval-policy"
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
    task = _split_loaded(world, split)
    change_set = {"id": task["result"]["changeSetId"]}
    both = ok(world.api.get(f"/change-sets/{change_set['id']}"))["modelReleaseId"]
    ok(world.activate(both, split.workspace))
    publication = world.api.post(
        f"/change-sets/{change_set['id']}/publication",
        {"expectedChangeSetVersion": world.current(change_set)["version"]},
    )
    refused(publication, 409, "APPROVAL_REQUIRED")
    ok(
        world.api.post(
            f"/change-sets/{change_set['id']}/submission",
            {"expectedChangeSetVersion": world.current(change_set)["version"]},
        ),
        201,
    )
    _, other = _client(world, "approver", ("owner", {"workspaceKey": split.workspace}))
    ok(
        other.api.post(
            f"/change-sets/{change_set['id']}/decisions",
            {
                "outcome": "approve",
                "expectedChangeSetVersion": world.current(change_set)["version"],
                "expectedActivePublicationId": None,
            },
        )
    )
    assert split.live(split.k.part, split.k.service)

    # A whole-type migration: the person without Model release is refused.
    merge = Merge(world, tmp_path, monkeypatch)
    task = _accept(world, _proposed(world, merge.workspace))
    migration = task["result"]["migration"]
    _, steward = _client(world, "steward", ("steward", {"workspaceKey": merge.workspace}))
    current = ok(world.api.get(f"/workspaces/{merge.workspace}/model"))
    refused(
        steward.api.post(
            f"/workspaces/{merge.workspace}/model/migrations",
            {
                "targetReleaseId": migration["releaseId"],
                "expectedVersion": current["version"],
                "typeMappings": migration["typeMappings"],
            },
        ),
        403,
        "FORBIDDEN",
    )


@pytest.mark.journey("J50.51")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_AGENT_COMMAND="true")
def test_a_person_without_model_release_or_authoring_gets_a_session_with_no_model_grant(world):
    """A person without Model release or Model authoring: a task can still be read, but the session
    holds no model grant and nothing is installed."""
    from test_j40_authorization import _client

    workspace = _workspace(world, world.workspace_model()["releaseId"])
    _, person = _client(world, "steward", ("steward", {"workspaceKey": workspace}))
    task = ok(
        person.api.upload(
            "/ai/tasks",
            {},
            {"request": json.dumps({"workspaceKey": workspace, "words": "Merge two types"})},
        ),
        202,
    )
    releases = len(_all(world, "/model-releases"))
    session_world, _, _ = _session_of(person, task)
    assert ok(person.api.get(f"/ai/tasks/{task['id']}"))["id"] == task["id"]
    refused(
        session_world.api.post("/model-drafts", {"name": "Not allowed", "model": {}}),
        403,
        "FORBIDDEN",
    )
    assert len(_all(world, "/model-releases")) == releases


@pytest.mark.journey("J50.48")
@pytest.mark.structures(*STRUCTURES)
def test_the_final_release_of_a_part_move_is_found_when_the_session_does_not_name_it(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a session that restructures part of a type and ends its answer without the final
    release's line (0.13 DOC11 14), then the engine finds the final release it recorded as installed
    by the task, so the steps are still the person's to take."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    split = Split(world, tmp_path, monkeypatch, omit_then=True)
    task = _split_loaded(world, split)
    assert task["state"] == "loaded", task["notes"]
    result = task["result"]
    assert result["thenReleaseId"] and result["thenReleaseId"] != result["changeSetReleaseId"]
    assert not [n for n in task["notes"] if n["kind"] == "warning"]


@pytest.mark.journey("J50.52")
@pytest.mark.structures(*STRUCTURES)
def test_what_stays_out_a_discarded_task_retires_its_release_and_the_final_release_survives(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """The release with both is retired if the task is discarded before the change set; while a loaded
    task's session lives (AP-D56) nothing it installed is retired, and when the task ends
    thenReleaseId survives and any other release the session installed is retired."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    early = Split(world, tmp_path, monkeypatch, early=True)
    before = {r["id"] for r in _all(world, "/model-releases")}
    task = _proposed(world, early.workspace)
    assert task["state"] == "checked"
    installed = {r["id"]: r for r in _all(world, "/model-releases")}
    [both] = [i for i in installed if i not in before]
    ok(world.api.post(f"/ai/tasks/{task['id']}/discard", {}), 200)
    assert _release_status(world, both) == "retired"

    other = Split(world, tmp_path, monkeypatch, extra=_shaped(world, "split-extra", []))
    task = _split_loaded(world, other)
    assert _release_status(world, task["result"]["thenReleaseId"]) != "retired"
    change_set = ok(world.api.get(f"/change-sets/{task['result']['changeSetId']}"))
    assert _release_status(world, change_set["modelReleaseId"]) != "retired"
    extra = [r for r in _all(world, "/model-releases") if "-split-extra-" in r["version"]]
    assert extra and all(r["status"] != "retired" for r in extra)
    ok(world.api.post(f"/ai/tasks/{task['id']}/discard", {}), 200)
    assert _release_status(world, task["result"]["thenReleaseId"]) != "retired"
    extra = [r for r in _all(world, "/model-releases") if "-split-extra-" in r["version"]]
    assert all(r["status"] == "retired" for r in extra)


# --- a task named by what it asks (0.13 TN) --------------------------------------------------------


@pytest.mark.journey("J50.72")
@pytest.mark.structures(*STRUCTURES)
def test_a_words_task_is_titled_by_its_session_and_its_draft_carries_the_title(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given a words task whose session states a title with its first answer, then the task carries
    the title and its draft is named after it; given a task whose session ends before any answer, then
    the task has no title and the words stay what it is named by."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    merge = Merge(world, tmp_path, monkeypatch, parented=True)
    words = "can you make suppliers and vendors one type, i dont mind what it is called, thanks"
    merge.settings["title"] = "Merge suppliers and vendors"
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    task = _proposed(world, merge.workspace, words)
    assert task["state"] == "checked", task["notes"]
    assert task["title"] == "Merge suppliers and vendors"
    assert task["words"] == words
    draft = ok(world.api.get(f"/model-drafts/{task['draftId']}"))
    assert draft["name"] == "Assistant: Merge suppliers and vendors"

    merge.settings.update({"title": None, "silent": True})
    (tmp_path / "config.json").write_text(json.dumps(merge.settings))
    early = _proposed(world, merge.workspace, words)
    assert early["state"] == "failed"
    assert early["title"] is None
    assert early["words"] == words
