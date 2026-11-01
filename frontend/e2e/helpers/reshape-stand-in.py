"""Stands in for Claude Code as AI_AGENT_COMMAND in the reshaping runner (0.16 AP12): it works through the API
with the token and folder the engine gives a session. The runner's plan is the file named by the first argument
(read at each turn, so the runner changes it between tasks): `mode` is `merge` (the proposal's moves turn whole
types into one, and on acceptance the draft is installed as one release) or `parts` (on acceptance the final
release and a release holding both shapes are installed, and part of a type is restructured in a change set on
the second)."""

import json
import re
import sys
from pathlib import Path

import httpx

plan = json.loads(Path(sys.argv[1]).read_text())
prompt = sys.argv[sys.argv.index("-p") + 1]
found = re.search(r"the engine at (\S+?),", prompt)
if found:
    Path("engine-address").write_text(found.group(1))
address = Path("engine-address").read_text()
import os  # noqa: E402

http = httpx.Client(headers={"Authorization": f"Bearer {os.environ['REFIROO_TOKEN']}"}, timeout=120, trust_env=False)


def call(method, path, body=None, **kw):
    sent = http.request(method, f"{address}/api/v1{path}", json=body, **kw)
    if sent.status_code >= 300:
        sys.exit(f"{method} {path} answered {sent.status_code}: {sent.text}")
    return sent.json()


def install(draft_id):
    version = call("GET", f"/model-drafts/{draft_id}")["version"]
    return call("POST", f"/model-drafts/{draft_id}/installation", {"expectedVersion": version})["id"]


def result(words):
    usage = {"input_tokens": 10, "output_tokens": 20}
    print(json.dumps({"type": "assistant", "message": {"id": "m-" + words[:6], "usage": usage, "content": []}}))
    print(json.dumps({"type": "result", "result": words, "total_cost_usd": 0.1}))


if "The person accepted" in prompt:
    draft = Path("draft").read_text()
    if plan["mode"] == "merge":
        result("Done.\nRELEASE: " + install(draft))
    else:
        final = install(draft)
        both_draft = call("POST", "/model-drafts", {"name": "Both shapes", "model": plan["both"]})["id"]
        both = install(both_draft)
        made = call(
            "POST",
            f"/workspaces/{plan['workspace']}/change-sets",
            {"name": "Split items", "source": "currentLive", "modelReleaseId": both},
        )
        params = {"workspaceKey": plan["workspace"], "pageSize": 100}
        for item in call("GET", f"/objects/{plan['from']}", params=params)["items"]:
            full = call("GET", f"/objects/{plan['from']}/{item['id']}", params={"workspaceKey": plan["workspace"]})
            note = next(a["value"] for a in full["attributes"] if a["attributeTypeKey"] == plan["note"])
            body = {"operation": {"kind": "changeType", "objectId": item["id"], "objectTypeKey": plan["targets"][note]}}
            path = f"/change-sets/{made['id']}/restructurings"
            shown = call("POST", path + "/preview", body)
            call(
                "POST",
                path,
                {**body, "expectedChangeSetVersion": shown["changeSetVersion"], "planDigest": shown["planDigest"]},
            )
        result(f"Done.\nCHANGE_SET: {made['id']}\nTHEN_RELEASE: {final}")
else:
    base = call("GET", f"/workspaces/{plan['workspace']}/model")["releaseId"]
    body = {"name": "Assistant: change this model", "baseReleaseId": base, "model": plan["final"]}
    draft = call("POST", "/model-drafts", body)["id"]
    Path("draft").write_text(draft)
    proposal = {"draftId": draft, "summary": plan["summary"], "questions": []}
    if plan.get("moves"):
        proposal["moves"] = plan["moves"]
    Path("proposal.json").write_text(json.dumps(proposal))
    result("Ready.")
