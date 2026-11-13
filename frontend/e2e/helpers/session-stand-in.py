"""Stands in for Claude Code as AI_AGENT_COMMAND in the assistant's browser runner: it works through the
API with the token and folder the engine gives a session, and stops where a session stops. Three turns:
a proposal on a draft, the person's correction, and on acceptance one release and a change set.

The first turn reads the person's words for a mode and keeps it in the folder for the turns after:

- no marker: the proposal is a draft and nothing else, and the load writes records one by one through
  `/objects`, so the engine has no import to repeat and the loaded task says why no profile was saved;
- `KEYED`: the proposal's check is a dry run of the workbook through a profile whose source has a key, and
  the load imports the workbook through that profile into the change set, so the engine saves it;
- `BESIDE`: the proposal's check is a dry run through a profile with no key, so its rows do not find their
  records and are created beside them (those whose code is held are refused as duplicates), which the engine
  warns of on the proposal.

Either way the profile is stored on the draft before the check, which reads the draft's own (0.17 PL3b)."""

import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
import openpyxl

TYPES = {"Domains": ("rdm-master", "domain"), "Systems": ("rdm-systems", "system")}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TOKEN = os.environ["REFIROO_TOKEN"]
prompt = sys.argv[sys.argv.index("--") + 1]
found = re.search(r"the engine at (\S+?),", prompt)
if found:
    Path("engine-address").write_text(found.group(1))
address = Path("engine-address").read_text()
http = httpx.Client(headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60, trust_env=False)


def call(path, body=None, **parts):
    """GET without a body; POST with a JSON body or the multipart `parts` (files, data)."""
    method = "GET" if body is None and not parts else "POST"
    sent = http.request(method, f"{address}/api/v1{path}", json=body, **parts)
    if sent.status_code >= 300:
        sys.exit(f"{path} answered {sent.status_code}: {sent.text}")
    return sent.json()


def until(path, done):
    for _ in range(300):
        found = call(path)
        if done(found):
            return found
        time.sleep(0.2)
    sys.exit(f"{path} never got ready")


def result(words, total):
    """A turn's usage and its result line: the cost is a running total over the session's turns."""
    usage = {"input_tokens": 10, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 5, "output_tokens": 20}
    print(json.dumps({"type": "assistant", "message": {"id": f"msg-{total}", "usage": usage, "content": []}}))
    print(json.dumps({"type": "result", "result": words, "total_cost_usd": total}))


def proposal(draft, summary, total):
    Path("proposal.json").write_text(json.dumps({"draftId": draft, "summary": summary, "questions": []}))
    result("Ready.", total)


sheet = openpyxl.load_workbook("workbook.xlsx").worksheets[0]
application, type_key = TYPES[sheet.title]


def profile(keyed):
    """The workbook's one sheet as a source: its code and name columns, with a key finding the record by
    its code when `keyed`."""
    source = {
        "sheet": sheet.title,
        "applicationKey": application,
        "objectTypeKey": type_key,
        "columns": [
            {"column": sheet.cell(1, 1).value, "attributeTypeKey": f"{type_key}-code"},
            {"column": sheet.cell(1, 2).value, "field": "name"},
        ],
    }
    if keyed:
        source["key"] = {"attributeTypeKey": f"{type_key}-code"}
    return {"sources": [source]}


def checked_by_dry_run(draft, keyed):
    """The proposal's check: the workbook is the draft's source file and every row is dry-run against the
    draft through the profile, as a session checks its work."""
    upload = call(
        "/source-files",
        files={"file": ("workbook.xlsx", open("workbook.xlsx", "rb"), XLSX)},
        data={"request": json.dumps({"owner": {"draftId": draft}, "workspaceKey": "default"})},
    )
    until(f"/source-files/{upload['id']}", lambda found: found["profile"]["state"] == "completed")
    # The profile is stored on the draft and the dry run is given the profile the draft answers with: the engine refuses a design whose
    # check no stored profile reproduces (0.17 PL3b).
    held = call(f"/model-drafts/{draft}")
    call(
        f"/model-drafts/{draft}/operations",
        {"expectedVersion": held["version"], "operations": [{"kind": "setProfile", **profile(keyed)}]},
    )
    stored = call(f"/model-drafts/{draft}/profile")["definition"]
    call(
        f"/model-drafts/{draft}/dry-run",
        {"sourceFileId": upload["id"], "workspaceKey": "default", "profile": stored, "onExisting": "overwrite"},
    )
    until(f"/model-drafts/{draft}/dry-run", lambda found: found["state"] == "completed")


mode_file = Path("mode")

if "The person accepted" in prompt:
    mode = mode_file.read_text() if mode_file.exists() else "plain"
    draft = call(f"/model-drafts/{Path('draft').read_text()}")
    call(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]})
    change_set = call("/workspaces/default/change-sets", {"name": f"Load of {sheet.title}", "source": "currentLive"})
    if mode == "keyed":
        # The whole workbook through the keyed profile: the engine saves it for the next file.
        call(
            "/imports",
            files={"file": ("workbook.xlsx", open("workbook.xlsx", "rb"), XLSX)},
            data={
                "request": json.dumps(
                    {
                        "changeSetId": change_set["id"],
                        "expectedChangeSetVersion": change_set["version"],
                        "profile": profile(True),
                        "policy": "independent",
                        "onExisting": "overwrite",
                        "stage": "execute",
                    }
                )
            },
        )
    else:
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
    result(f"Done.\nCHANGE_SET: {change_set['id']}", 0.86)
elif "The person says" in prompt:
    proposal(Path("draft").read_text(), "A remarks field on the type, as you asked. One new record.", 0.55)
else:
    mode = "keyed" if "KEYED" in prompt else "beside" if "BESIDE" in prompt else "plain"
    mode_file.write_text(mode)
    model = json.loads(Path("model.json").read_text())
    key = f"remarks-{type_key}"
    model["attributeTypes"].append({"key": key, "name": "Remarks"})
    bound = next(item for item in model["objectTypes"] if item["key"] == type_key)
    bound.setdefault("attributes", []).append({"attributeTypeKey": key, "order": 990})
    model["release"] = {**model["release"], "version": f"{model['release']['version']}-{re.sub(r'[^a-z0-9]', '', Path.cwd().name.lower())[:12]}"}
    base = call("/workspaces/default/model")["releaseId"]
    draft = call("/model-drafts", {"name": f"Assistant: {sheet.title}", "baseReleaseId": base, "model": model})
    Path("draft").write_text(draft["id"])
    if mode != "plain":
        checked_by_dry_run(draft["id"], keyed=mode == "keyed")
    proposal(draft["id"], "A remarks field on the type. One new record.", 0.3)
