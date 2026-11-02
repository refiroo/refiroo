"""Stands in for Claude Code as AI_AGENT_COMMAND in the way-out runner (0.16 AP13): it works through the API with
the token and folder the engine gives a session. The runner's plan is the file named by the first argument (read at
each turn, so the runner changes it between tasks): `final` is the model the proposal's draft holds (the workspace's
model under a new version, with one extra type), `workspace` and `batch` the change set a load fills, `fail` makes a
turn end with no proposal, and `hold` ("propose" or "load") makes that turn wait until the person stops it. Every
load installs a release of its own, so a second load is not refused for the first one's version."""

import copy
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

plan = json.loads(Path(sys.argv[1]).read_text())
prompt = sys.argv[sys.argv.index("-p") + 1]
found = re.search(r"the engine at (\S+?),", prompt)
if found:
    Path("engine-address").write_text(found.group(1))
# A turn the person stopped at once may not have written it: the plan names the engine as well.
address = Path("engine-address").read_text() if Path("engine-address").exists() else plan["address"]
http = httpx.Client(headers={"Authorization": f"Bearer {os.environ['REFIROO_TOKEN']}"}, timeout=120, trust_env=False)


def call(method, path, body=None, **kw):
    sent = http.request(method, f"{address}/api/v1{path}", json=body, **kw)
    if sent.status_code >= 300:
        sys.exit(f"{method} {path} answered {sent.status_code}: {sent.text}")
    return sent.json()


def result(words):
    usage = {"input_tokens": 10, "output_tokens": 20}
    print(json.dumps({"type": "assistant", "message": {"id": "m-" + words[:6], "usage": usage, "content": []}}))
    print(json.dumps({"type": "result", "result": words, "total_cost_usd": 0.1}))


def hold(kind):
    if plan.get("hold") == kind:
        time.sleep(600)


def install(version_suffix):
    model = copy.deepcopy(plan["final"])
    model["release"]["version"] = f"{model['release']['version']}-{version_suffix}"
    draft = call("POST", "/model-drafts", {"name": "A release", "model": model})["id"]
    version = call("GET", f"/model-drafts/{draft}")["version"]
    return call("POST", f"/model-drafts/{draft}/installation", {"expectedVersion": version})["id"]


if "The person accepted" in prompt:
    loads = Path("loads")
    count = int(loads.read_text()) + 1 if loads.exists() else 1
    loads.write_text(str(count))
    release = install(f"{os.urandom(3).hex()}-load{count}")
    made = call(
        "POST",
        f"/workspaces/{plan['workspace']}/change-sets",
        {"name": plan.get("name", "Its load"), "source": "currentLive", "modelReleaseId": release},
    )
    hold("load")
    call(
        "POST",
        "/batches",
        {
            "changeSetId": made["id"],
            "expectedChangeSetVersion": made["version"],
            "policy": "independent",
            "run": "inline",
            "items": plan["batch"],
        },
    )
    result("Done.\nCHANGE_SET: " + made["id"])
else:
    hold("propose")
    if plan.get("fail"):
        result("I could not build a model from these words: the one type they name already exists with other fields.")
        sys.exit(0)
    if Path("draft").exists():
        draft = Path("draft").read_text()
    else:
        base = call("GET", f"/workspaces/{plan['workspace']}/model")["releaseId"]
        body = {"name": "Assistant: change this model", "baseReleaseId": base, "model": plan["final"]}
        draft = call("POST", "/model-drafts", body)["id"]
        Path("draft").write_text(draft)
    Path("proposal.json").write_text(
        json.dumps({"draftId": draft, "summary": plan.get("summary", "One new type."), "questions": []})
    )
    result("Ready.")
