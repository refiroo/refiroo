#!/usr/bin/env python3
"""States a screenshot needs that the reference instance does not hold on its own. screens.mjs runs them
through the {"state": "<name>"} action: set one in a screen's actions, the matching restore in its "after".
Everything goes through the public API as the reference administrator; nothing is written to the database.

  groups-empty      keep the groups (name, description, members) in _waves/runs/screen-states.json and delete them
  groups-restore    make them again, with the same members (new IDs); changes nothing when none was kept
  bonaduz-gap       delete the name translation Bonaduz (rm), so the names matrix has a None cell
  bonaduz-restore   load it again with its own ID, as guide/samples/load.py does (idempotent)
  thusis-change-set     put Thusis Süd's Abbreviation back to THSS and open a fresh change set "Correct Thusis Süd
                        abbreviation" that changes it to THSD (the publication screens publish it)
  approval-scenario     switch approval on (second person on, so the submitter submits), put Davos Platz's Height back to 1540.192 and open a
                        fresh change set "Guide approval example" (Height 1540.2), validated and submitted
  approval-second-on / approval-second-off / approval-off   the workspace's approval policy
  draft-ghost <name> / draft-ghost-off <name>   the deliberate error in a model draft: a column ghost-field in the
                        Municipalities view of Network (as a person would add it in the draft's JSON), and its removal
  draft-delete <name>   delete the newest model draft of that name (a draft nobody installs)
  banner-mismatch-on / banner-mismatch-off   the empty workspace "Guide model banner" on Graubünden's release with the change
                        set "Guide model version banner", then another installed release of the model activated in the
                        workspace, so the change set differs from live data (UI1: the banner offers both ways out); off
                        deletes the workspace
  draft-concurrent <name>::<type key>   a second person's change to the newest draft of that name: the type is renamed
                        'Renamed elsewhere' through the draft's operations (the draft's version moves on while a page
                        still holds the old one: the conflict and newer-version screens)
  draft-copy <from>::<to>   a new model draft <to> with the model and base release of the newest draft <from>
  workbook-workspace    make the workspace "Guide workbook test" (key guide-workbook-test) on the release Graubünden runs,
                        deleting an earlier one first (the workbook-load screens read it)
  hierarchy-change-set  make the change set "C10 hierarchy screenshot preparation" in Graubünden when it is not there
  import-workbook       make _waves/runs/import-invalid-height.xlsx: an export of the stops of Graubünden for people, its first Height (m)
                        cell set to text, 200 rows (the import-preview-columns screen uploads it)
  jobs-hold / jobs-release   a running and a queued job held for the run-jobs picture (a lock of at most 100 seconds on
                        the workspace row, taken through docker exec psql), and the release that waits for both to finish
  export-job            start the export of all Stops as a technical Excel workbook and wait for it
                        (the job screens read the newest export job)
  contributor-account  the same for the person Guide Contributor (GUIDE_CONTRIBUTOR_* in reference/.env) with the role Contributor
  approver-account  make the person Rita Approver (e-mail and password from GUIDE_APPROVER_* in reference/.env) with the role Data owner
                        in Graubünden, when she is not there (a fresh reference instance has only the administrator)
  person-id <name>  print the ID of the person of that name (for {person:name} in a screen's address)
  release-id <key>@<version>   print the ID of an installed release (for {release:key@version})
  draft-id <name>   print the ID of the newest model draft of that name (for {draft:name} in a screen's address)

Usage: python3 guide/tools/screen-states.py <state>
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "guide" / "samples"))
import load  # noqa: E402

KEPT = ROOT / "guide" / "_waves" / "runs" / "screen-states.json"


def api():
    env = load.read_env(ROOT / "guide" / "reference" / ".env")
    base = env.get("PUBLIC_URL", "http://localhost:8480")
    a = load.Api(
        load.urllib_send(base),
        base,
        env["GUIDE_ADMIN_EMAIL"],
        env["GUIDE_ADMIN_PASSWORD"],
    )
    a.login()
    return a


def kept():
    return json.loads(KEPT.read_text()) if KEPT.exists() else {}


def save(state):
    KEPT.parent.mkdir(parents=True, exist_ok=True)
    KEPT.write_text(json.dumps(state, indent=1))


def groups_empty(a):
    state = kept()
    if state.get("groups"):  # already emptied and not restored: keep what was saved
        return
    groups = []
    for g in a.call("GET", "/api/v1/groups?pageSize=200")["items"]:
        if g.get("source"):
            continue  # a provider group is made by sign-ins; the reference instance has none
        members = a.call("GET", f"/api/v1/groups/{g['id']}/members?pageSize=200")[
            "items"
        ]
        groups.append(
            {
                "name": g["name"],
                "description": g["description"],
                "members": [m["id"] for m in members],
            }
        )
    state["groups"] = groups
    save(state)
    for g in a.call("GET", "/api/v1/groups?pageSize=200")["items"]:
        if not g.get("source"):
            a.call("DELETE", f"/api/v1/groups/{g['id']}")


def groups_restore(a):
    state = kept()
    for g in state.pop("groups", []):
        made = a.call(
            "POST",
            "/api/v1/groups",
            {"name": g["name"], "description": g["description"]},
        )
        for user_id in g[
            "members"
        ]:  # one by one: the batch refuses a deactivated person, the single add keeps them
            a.call("POST", f"/api/v1/groups/{made['id']}/members", {"userId": user_id})
    save(state)


def draft_id(a, name):
    drafts = [
        d
        for d in a.call("GET", "/api/v1/model-drafts?pageSize=100")["items"]
        if d["name"] == name
    ]
    if not drafts:
        sys.exit(f"no model draft named {name!r}")
    print(max(drafts, key=lambda d: d["createdAt"])["id"])


def person_id(a, name):
    found = [
        u
        for u in a.call("GET", "/api/v1/users?pageSize=100")["items"]
        if u["name"] == name
    ]
    if not found:
        sys.exit(f"no person named {name!r}")
    print(found[0]["id"])


def _signs_in(base, email, password):
    """Whether the sign-in form accepts the e-mail address and password (a fresh Api per try)."""
    try:
        load.Api(load.urllib_send(base), base, email, password).login()
        return True
    except SystemExit:
        return False


def approver_account(a):
    _account(a, "APPROVER", "Rita Approver", "owner")


def contributor_account(a):
    _account(a, "CONTRIBUTOR", "Guide Contributor", "contributor")


def _account(a, prefix, person, role):
    env = load.read_env(ROOT / "guide" / "reference" / ".env")
    email, password = env[f"GUIDE_{prefix}_EMAIL"], env[f"GUIDE_{prefix}_PASSWORD"]
    users = [
        u
        for u in a.call("GET", "/api/v1/users?pageSize=100")["items"]
        if u["email"].lower() == email.lower()
    ]
    user = (
        users[0]
        if users
        else a.call("POST", "/api/v1/users", {"name": person, "email": email})
    )
    if not _signs_in(a.base, email, password):
        link = a.call("POST", f"/api/v1/users/{user['id']}/password-reset")
        token = urllib.parse.parse_qs(urllib.parse.urlparse(link["url"]).query)[
            "token"
        ][0]
        # the one-time link's own form, as a person would use it
        form = urllib.parse.urlencode(
            {"token": token, "password": password, "repeat": password}
        ).encode()
        request = urllib.request.Request(
            a.base + "/oauth/password",
            data=form,
            headers={"Origin": a.base},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60):
            pass
    grants = a.call("GET", f"/api/v1/users/{user['id']}/grants")["items"]
    if not any(
        (g.get("role") or {}).get("key") == role
        and g["scope"].get("workspaceKey") == WS
        for g in grants
    ):
        a.call(
            "POST",
            "/api/v1/grants",
            {
                "principal": {"kind": "user", "id": user["id"]},
                "role": role,
                "scope": {"workspaceKey": WS},
            },
        )


def change_set_id(a, name):
    name, _, workspace = name.partition(
        "@"
    )  # "name@workspace-key" for a change set outside Graubünden
    found = [
        c
        for c in a.call(
            "GET", f"/api/v1/workspaces/{workspace or WS}/change-sets?pageSize=100"
        )["items"]
        if (c["name"] or "").startswith(name)
    ]
    if not found:
        sys.exit(f"no change set named {name!r}")
    print(max(found, key=lambda c: c["createdAt"])["id"])


def _draft(a, name):
    found = [
        d
        for d in a.call("GET", "/api/v1/model-drafts?pageSize=100")["items"]
        if d["name"] == name
    ]
    if not found:
        sys.exit(f"no model draft named {name!r}")
    d = max(found, key=lambda x: x["createdAt"])
    return a.call("GET", f"/api/v1/model-drafts/{d['id']}")


def draft_ghost(a, name, on):
    d = _draft(a, name)
    model = d["model"]
    view = next(
        v
        for app in model["applications"]
        if app["key"] == "network"
        for v in app["views"]
        if v["key"] == "municipalities"
    )
    columns = [c for c in view["config"]["columns"] if c != "ghost-field"]
    view["config"]["columns"] = columns + (["ghost-field"] if on else [])
    a.call(
        "PATCH",
        f"/api/v1/model-drafts/{d['id']}",
        {"expectedVersion": d["version"], "model": model},
    )


def draft_copy(a, spec):
    src, _, name = spec.partition("::")
    d = _draft(a, src)
    a.call(
        "POST",
        "/api/v1/model-drafts",
        {"name": name, "baseReleaseId": d["baseReleaseId"], "model": d["model"]},
    )


def draft_delete(a, name):
    d = _draft(a, name)
    a.call("DELETE", f"/api/v1/model-drafts/{d['id']}?expectedVersion={d['version']}")


def draft_concurrent(a, spec):
    name, _, type_key = spec.partition("::")
    d = _draft(a, name)
    a.call(
        "POST",
        f"/api/v1/model-drafts/{d['id']}/operations",
        {
            "expectedVersion": d["version"],
            "operations": [
                {
                    "kind": "setLabel",
                    "element": {"objectType": type_key},
                    "name": "Renamed elsewhere",
                    "pluralName": "Renamed elsewhere",
                }
            ],
        },
    )


IMPORT_FILE = ROOT / "guide" / "_waves" / "runs" / "import-invalid-height.xlsx"


def import_workbook(a):
    """Export the first stops of Graubünden for people (kept in _waves/runs/), set the first Height (m) cell to
    text and keep 200 rows: the workbook the import-preview-columns screen uploads. Needs openpyxl, taken from
    backend/.venv."""
    import subprocess
    import time

    job = a.call(
        "POST",
        "/api/v1/exports",
        {
            "workspaceKey": WS,
            "context": {},
            "scope": {"types": [{"objectTypeKey": "stop", "where": []}]},
            "include": {"relations": "none"},
            "format": "xlsx",
            "layout": "people",
            "people": {
                "columns": ["name", "designation", "stop-number", "height"],
                "sheets": [],
            },
        },
    )
    while job["state"] not in ("completed", "failed", "cancelled"):
        time.sleep(2)
        job = a.call("GET", f"/api/v1/jobs/{job['id']}")
    if job["state"] != "completed":
        sys.exit(f"export {job['state']}")
    request = urllib.request.Request(
        a.base + f"/api/v1/jobs/{job['id']}/output",
        headers={"Authorization": "Bearer " + a.token},
    )
    IMPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPORT_FILE.write_bytes(urllib.request.urlopen(request, timeout=120).read())
    edit = (
        "import openpyxl,sys;wb=openpyxl.load_workbook(sys.argv[1]);ws=wb['Stops'];"
        "ws.cell(2,4).value='not a number';ws.delete_rows(202,ws.max_row);wb.save(sys.argv[1])"
    )
    subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "bin" / "python"),
            "-c",
            edit,
            str(IMPORT_FILE),
        ],
        check=True,
    )


HOLD = "old54-hold"
DB = [
    "docker",
    "exec",
    "-i",
    "refiroo-guide-ref-database-1",
    "psql",
    "-U",
    "rdm",
    "-d",
    "rdm",
    "-tA",
]


def _psql(sql):
    import subprocess

    return subprocess.run(
        DB + ["-c", sql], capture_output=True, text=True, check=True
    ).stdout.strip()


def jobs_hold(a):
    """A real running job and a real queued one, for a photograph (run-jobs): a transaction locks the row of the
    workspace Graubünden for at most 100 seconds (it ends by itself and jobs-release ends it earlier), two background batches
    each write Chur Wiesental's own values back unchanged (the first blocks at the lock, the second waits behind it)."""
    import subprocess
    import time
    import uuid

    sql = (
        f"/* {HOLD} */ BEGIN; SET LOCAL idle_in_transaction_session_timeout='120s'; "
        f"SELECT key FROM workspaces WHERE key='{WS}' FOR NO KEY UPDATE; SELECT pg_sleep(100); ROLLBACK;"
    )
    subprocess.Popen(
        DB + ["-c", sql],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(30):
        time.sleep(1)
        if (
            _psql(
                f"SELECT count(*) FROM pg_stat_activity WHERE query LIKE '%{HOLD}%' AND pid <> pg_backend_pid()"
            )
            != "0"
        ):
            break
    else:
        sys.exit("the lock was not taken")
    o = _stop(a, "Chur Wiesental")
    item = {
        "op": "upsert",
        "applicationKey": "network",
        "objectTypeKey": "stop",
        "key": {"id": o["id"]},
        "name": o["name"],
        "attributes": [
            {"attributeTypeKey": x["attributeTypeKey"], "value": x["value"]}
            for x in o["attributes"]
        ],
    }
    if o.get("parent"):
        item["parent"] = {"id": o["parent"]["id"]}
    body = {
        "workspaceKey": WS,
        "policy": "independent",
        "run": "background",
        "onExisting": "overwrite",
        "items": [item],
    }
    ids = []
    for _ in range(2):
        job = a.call(
            "POST",
            "/api/v1/batches",
            body,
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        ids.append(job["id"])
        time.sleep(4)
    KEPT_JOBS.parent.mkdir(parents=True, exist_ok=True)
    KEPT_JOBS.write_text(json.dumps(ids))
    print("jobs", [a.call("GET", f"/api/v1/jobs/{i}")["state"] for i in ids])


KEPT_JOBS = ROOT / "guide" / "_waves" / "runs" / "screen-jobs.json"


def jobs_release(a):
    import time

    _psql(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%{HOLD}%' AND pid <> pg_backend_pid()"
    )
    ids = json.loads(KEPT_JOBS.read_text()) if KEPT_JOBS.exists() else []
    for i in ids:
        while True:
            j = a.call("GET", f"/api/v1/jobs/{i}")
            if j["state"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(1)
        print("job", j["state"], j.get("counts"))


def job_id(a, kind):
    jobs = [
        j
        for j in a.call("GET", "/api/v1/jobs?pageSize=100")["items"]
        if j["kind"] == kind and j["state"] == "completed"
    ]
    if not jobs:
        sys.exit(f"no completed {kind} job")
    print(max(jobs, key=lambda j: j["createdAt"])["id"])


def release_id(a, spec):
    key, _, version = spec.partition("@")
    for r in a.call("GET", "/api/v1/model-releases?pageSize=200")["items"]:
        if r["key"] == key and r["version"] == version:
            print(r["id"])
            return
    sys.exit(f"no release {spec!r}")


BONADUZ = "4a730744-64b8-4929-be99-44ca5021ab54"


def bonaduz_gap(a):
    try:
        row = a.call("GET", f"/api/v1/objects/name-translation/{BONADUZ}")
    except SystemExit:
        return  # already gone
    impact = a.call(
        "GET", f"/api/v1/objects/name-translation/{BONADUZ}/deletion-impact"
    )
    a.call(
        "DELETE",
        f"/api/v1/objects/name-translation/{BONADUZ}?expectedVersion={row['version']}&cascade=true"
        f"&deletionPreviewToken={impact['deletionPreviewToken']}",
    )


def bonaduz_restore(a):
    t = next(
        x
        for x in json.loads(
            (ROOT / "guide/samples/data/reference/translations.json").read_text()
        )
        if x["id"] == BONADUZ
    )
    item = {
        "op": "upsert",
        "applicationKey": "names",
        "objectTypeKey": "name-translation",
        "key": {"id": t["id"]},
        "name": t["name"],
        "parent": {"id": t["language"]},
        "attributes": [
            {"attributeTypeKey": "translated-name", "value": t["text"]},
            {"attributeTypeKey": "active", "value": True},
        ],
        "initialRelations": [
            {
                "relationTypeKey": "object-has-translation",
                "direction": "incoming",
                "object": {"id": t["object"]},
            }
        ],
    }
    a.batch("name translation", [item], {"workspaceKey": load.WORKSPACE}, None)


WS = "graubuenden"


def _stop(a, name):
    q = urllib.parse.quote_plus(name)
    found = a.call(
        "GET",
        f"/api/v1/objects?workspaceKey={WS}&objectTypeKey=stop&search={q}&pageSize=20",
    )["items"]
    return next(o for o in found if o["name"] == name)


def _attr(o, key):
    return next(
        (x["value"] for x in o["attributes"] if x["attributeTypeKey"] == key), None
    )


def _live_set(a, name, key, value):
    o = _stop(a, name)
    if _attr(o, key) != value:
        a.call(
            "PATCH",
            f"/api/v1/objects/stop/{o['id']}",
            {
                "expectedVersion": o["version"],
                "attributes": [{"attributeTypeKey": key, "value": value}],
            },
        )


def _discard_all(a, name):
    for c in a.call("GET", f"/api/v1/workspaces/{WS}/change-sets?pageSize=100")[
        "items"
    ]:
        if c["name"] == name:
            a.call(
                "DELETE",
                f"/api/v1/change-sets/{c['id']}?expectedVersion={c['version']}",
            )


def _change_set(a, name, stop, key, value):
    _discard_all(a, name)
    cs = a.call(
        "POST",
        f"/api/v1/workspaces/{WS}/change-sets",
        {"name": name, "source": "currentLive"},
    )
    o = _stop(a, stop)
    item = {
        "op": "upsert",
        "applicationKey": "network",
        "objectTypeKey": "stop",
        "key": {"id": o["id"]},
        "name": o["name"],
        # the model asks for these two on a record written into a change set
        "attributes": [
            {"attributeTypeKey": k, "value": _attr(o, k)}
            for k in ("designation", "stop-number")
            if k != key
        ]
        + [{"attributeTypeKey": key, "value": value}],
    }
    a.batch(
        "change set",
        [item],
        {"changeSetId": cs["id"], "expectedChangeSetVersion": cs["version"]},
        None,
        "overwrite",
    )
    return a.call("GET", f"/api/v1/change-sets/{cs['id']}")


def thusis_change_set(a):
    _live_set(a, "Thusis Süd", "abbreviation", "THSS")
    _change_set(
        a, "Correct Thusis Süd abbreviation", "Thusis Süd", "abbreviation", "THSD"
    )


def _policy(a, require, second):
    cur = a.call("GET", f"/api/v1/workspaces/{WS}/approval-policy")
    a.call(
        "PUT",
        f"/api/v1/workspaces/{WS}/approval-policy",
        {
            "requireApproval": require,
            "secondPerson": second,
            "expectedVersion": cur["version"],
        },
    )


def approval_scenario(a):
    _policy(
        a, True, True
    )  # a person who may approve publishes at once unless a second person must decide
    _live_set(a, "Davos Platz", "height", "1540.192")
    cs = _change_set(a, "Guide approval example", "Davos Platz", "height", "1540.2")
    a.call("POST", f"/api/v1/change-sets/{cs['id']}/validation")
    cs = a.call("GET", f"/api/v1/change-sets/{cs['id']}")
    a.call(
        "POST",
        f"/api/v1/change-sets/{cs['id']}/submission",
        {
            "expectedChangeSetVersion": cs["version"],
            "comment": "Height of Davos Platz rounded to one decimal, as in the national register.",
        },
    )


def workbook_workspace(a):
    key = "guide-workbook-test"
    found = [
        w
        for w in a.call("GET", "/api/v1/workspaces?status=all&pageSize=100")["items"]
        if w["key"] == key
    ]
    for w in found:
        if w["status"] == "active":
            a.call(
                "PATCH",
                f"/api/v1/workspaces/{key}",
                {"expectedVersion": w["version"], "status": "retired"},
            )
            w = a.call("GET", f"/api/v1/workspaces/{key}")
        a.call("DELETE", f"/api/v1/workspaces/{key}?expectedVersion={w['version']}")
    ws = a.call("GET", f"/api/v1/workspaces/{WS}")
    a.call(
        "POST",
        "/api/v1/workspaces",
        {
            "key": key,
            "label": "Guide workbook test",
            "modelReleaseId": ws["model"]["releaseId"],
        },
    )


BANNER_WS = "guide-model-banner"
BANNER_CHANGE_SET = "Guide model version banner"


def _banner_workspace_delete(a):
    for w in a.call("GET", "/api/v1/workspaces?status=all&pageSize=100")["items"]:
        if w["key"] != BANNER_WS:
            continue
        if w["status"] != "active":
            w = a.call(
                "PATCH",
                f"/api/v1/workspaces/{BANNER_WS}",
                {"expectedVersion": w["version"], "status": "active"},
            )
        for c in a.call("GET", f"/api/v1/workspaces/{BANNER_WS}/change-sets?pageSize=100")["items"]:
            a.call("DELETE", f"/api/v1/change-sets/{c['id']}?expectedVersion={c['version']}")
        w = a.call(
            "PATCH",
            f"/api/v1/workspaces/{BANNER_WS}",
            {"expectedVersion": w["version"], "status": "retired"},
        )
        a.call("DELETE", f"/api/v1/workspaces/{BANNER_WS}?expectedVersion={w['version']}")


def banner_mismatch_on(a):
    """An empty workspace on the release Graubünden runs, a change set on it, and then another installed
    release of the same model activated in the workspace: the change set keeps the first release."""
    _banner_workspace_delete(a)
    live = a.call("GET", f"/api/v1/workspaces/{WS}/model")
    other = [
        r
        for r in a.call("GET", "/api/v1/model-releases?pageSize=200")["items"]
        if r["key"] == live["releaseKey"] and r["id"] != live["releaseId"]
    ]
    if not other:
        sys.exit(f"no other installed release of {live['releaseKey']!r}")
    a.call(
        "POST",
        "/api/v1/workspaces",
        {"key": BANNER_WS, "label": "Guide model banner", "modelReleaseId": live["releaseId"]},
    )
    a.call(
        "POST",
        f"/api/v1/workspaces/{BANNER_WS}/change-sets",
        {"name": BANNER_CHANGE_SET, "source": "currentLive"},
    )
    assignment = a.call("GET", f"/api/v1/workspaces/{BANNER_WS}/model")
    a.call(
        "POST",
        f"/api/v1/workspaces/{BANNER_WS}/model/activation",
        {
            "releaseId": other[0]["id"],
            "expectedVersion": assignment["version"],
            "expectedReleaseId": assignment["releaseId"],
        },
    )


def hierarchy_change_set(a):
    name = "C10 hierarchy screenshot preparation"
    if not any(
        c["name"] == name
        for c in a.call("GET", f"/api/v1/workspaces/{WS}/change-sets?pageSize=100")[
            "items"
        ]
    ):
        a.call(
            "POST",
            f"/api/v1/workspaces/{WS}/change-sets",
            {"name": name, "source": "currentLive"},
        )


def export_job(a):
    body = {
        "workspaceKey": WS,
        "context": {},
        "scope": {"types": [{"objectTypeKey": "stop", "where": []}]},
        "include": {"relations": "none"},
        "format": "xlsx",
        "layout": "technical",
    }
    job = a.call("POST", "/api/v1/exports", body)
    a.wait_job(job["id"], "export")


STATES = {
    "banner-mismatch-on": banner_mismatch_on,
    "banner-mismatch-off": _banner_workspace_delete,
    "approver-account": approver_account,
    "contributor-account": contributor_account,
    "hierarchy-change-set": hierarchy_change_set,
    "export-job": export_job,
    "jobs-hold": jobs_hold,
    "jobs-release": jobs_release,
    "import-workbook": import_workbook,
    "workbook-workspace": workbook_workspace,
    "thusis-change-set": thusis_change_set,
    "approval-scenario": approval_scenario,
    "approval-second-on": lambda a: _policy(a, True, True),
    "approval-second-off": lambda a: _policy(a, True, False),
    "approval-off": lambda a: _policy(a, False, False),
    "bonaduz-gap": bonaduz_gap,
    "bonaduz-restore": bonaduz_restore,
    "groups-empty": groups_empty,
    "groups-restore": groups_restore,
}

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "draft-id":
        draft_id(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] in ("draft-ghost", "draft-ghost-off"):
        draft_ghost(api(), sys.argv[2], sys.argv[1] == "draft-ghost")
    elif len(sys.argv) == 3 and sys.argv[1] == "draft-copy":
        draft_copy(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "draft-concurrent":
        draft_concurrent(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "draft-delete":
        draft_delete(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "job-id":
        job_id(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "person-id":
        person_id(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "cs-id":
        change_set_id(api(), sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "release-id":
        release_id(api(), sys.argv[2])
    elif len(sys.argv) != 2 or sys.argv[1] not in STATES:
        sys.exit(__doc__)
    else:
        STATES[sys.argv[1]](api())
