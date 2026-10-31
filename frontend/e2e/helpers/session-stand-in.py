"""Stands in for Claude Code as AI_AGENT_COMMAND in the assistant's browser runner: it works through the
API with the token and folder the engine gives a session, and stops where a session stops. Three turns:
a proposal on a draft, the person's correction, and on acceptance one release and a change set."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl

TYPES = {"Domains": ("rdm-master", "domain"), "Systems": ("rdm-systems", "system")}
TOKEN = os.environ["REFIROO_TOKEN"]
prompt = sys.argv[sys.argv.index("-p") + 1]
found = re.search(r"the engine at (\S+?),", prompt)
if found:
    Path("engine-address").write_text(found.group(1))
address = Path("engine-address").read_text()


def call(path, body=None):
    request = urllib.request.Request(
        f"{address}/api/v1{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as answer:
            return json.load(answer)
    except urllib.error.HTTPError as error:
        sys.exit(f"{path} answered {error.code}: {error.read().decode()}")


def proposal(draft, summary):
    Path("proposal.json").write_text(json.dumps({"draftId": draft, "summary": summary, "questions": []}))
    print(json.dumps({"type": "result", "result": "Ready."}))


sheet = openpyxl.load_workbook("workbook.xlsx").worksheets[0]
application, type_key = TYPES[sheet.title]

if "The person accepted" in prompt:
    draft = call(f"/model-drafts/{Path('draft').read_text()}")
    call(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]})
    change_set = call("/workspaces/default/change-sets", {"name": f"Load of {sheet.title}", "source": "currentLive"})
    new = [row for row in sheet.iter_rows(min_row=2, values_only=True) if row[0].endswith("-9")]
    for row in new:
        created = call(
            "/objects",
            {
                "applicationKey": application,
                "objectTypeKey": type_key,
                "name": row[1],
                "attributes": [{"attributeTypeKey": f"{type_key}-code", "value": row[0]}],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        change_set["version"] = created.get("changeSetVersion", change_set["version"] + 1)
    print(json.dumps({"type": "result", "result": f"Done.\nCHANGE_SET: {change_set['id']}"}))
elif "The person says" in prompt:
    proposal(Path("draft").read_text(), "A remarks field on the type, as you asked. One new record.")
else:
    model = json.loads(Path("model.json").read_text())
    key = f"remarks-{type_key}"
    model["attributeTypes"].append({"key": key, "name": "Remarks"})
    bound = next(item for item in model["objectTypes"] if item["key"] == type_key)
    bound.setdefault("attributes", []).append({"attributeTypeKey": key, "order": 990})
    model["release"] = {**model["release"], "version": f"{model['release']['version']}-{re.sub(r'[^a-z0-9]', '', Path.cwd().name.lower())[:12]}"}
    base = call("/workspaces/default/model")["releaseId"]
    draft = call("/model-drafts", {"name": f"Assistant: {sheet.title}", "baseReleaseId": base, "model": model})
    Path("draft").write_text(draft["id"])
    proposal(draft["id"], "A remarks field on the type. One new record.")
