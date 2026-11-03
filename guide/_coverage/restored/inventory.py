#!/usr/bin/env python3
"""The coverage inventory: everything the guide must account for (plan 0.13, "Coverage").

    backend/.venv/bin/python guide/tools/inventory.py            # write guide/_coverage/inventory.json
    backend/.venv/bin/python guide/tools/inventory.py --totals   # print the totals only

Run from the repository root (or `npm run inventory` in guide/). It reads the sources of truth, never a
hand-kept list, so a new function, setting, error code, command, role, event type or model field shows up
in the next run. The check against the pages is `npm run check:coverage` (tools/check.mjs).

Kinds and their item IDs (what a page lists under `covers`):

  F01      capability, a `## Fnn` heading of docs/product-functionality/CURRENT_FUNCTIONALITY.md
  J01      journey, a `### Jnn` heading of docs/product-functionality/USER_JOURNEYS.md
  setting:NAME      a setting or capability flag, the engine's settings catalogue (app/config.py)
  error:CODE        an error code the backend raises (the extraction tests/test_api_journeys.py uses)
  command:NAME      a command, a module of app/cli/ (`python -m app.cli.NAME`)
  role:KEY          a predefined role (app/engine/authorization/catalogue.py)
  permission:KEY    an action group a role is made of (the same catalogue)
  event:NAME        an event type: a workspace event, a consumer record change, an inbox notice kind
  field:Type.name   a field of the model language (app/models/schema.py)

Items of 0.16 (J48 onward, the F entries of the AI integration, and the IDs in
_coverage/wave-g-items.txt) carry `"owner": "DOC9A"`: wave G's
pages own them, and their briefs are written after 0.16's release step (DOC-D21).
"""

from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
OUT = Path(__file__).resolve().parent / "inventory.json"
sys.path.insert(0, str(BACKEND))

WAVE_G = "DOC9A"
# 0.16's capabilities: the AI integration (CURRENT_FUNCTIONALITY F29, F30).
WAVE_G_CAPABILITIES = {"F29", "F30"}
WAVE_G_FIRST_JOURNEY = 48
# The other 0.16 items (settings, error codes, a command, a role, permissions, an event) are listed in
# guide/_coverage/wave-g-items.txt, one ID per line.
WAVE_G_ITEMS_FILE = Path(__file__).resolve().parent / "wave-g-items.txt"


def wave_g_items() -> set[str]:
    lines = (line.split("#", 1)[0].strip() for line in WAVE_G_ITEMS_FILE.read_text().splitlines())
    return {line for line in lines if line}


def capabilities() -> list[dict]:
    text = (ROOT / "docs/product-functionality/CURRENT_FUNCTIONALITY.md").read_text()
    items = []
    for number, title in re.findall(r"^## (F\d+) — (.+)$", text, re.MULTILINE):
        item = {"id": number, "title": title.strip()}
        if number in WAVE_G_CAPABILITIES:
            item["owner"] = WAVE_G
        items.append(item)
    return items


def journeys() -> list[dict]:
    text = (ROOT / "docs/product-functionality/USER_JOURNEYS.md").read_text()
    items = []
    for number, title in re.findall(r"^### (J\d+) — (.+)$", text, re.MULTILINE):
        item = {"id": number, "title": title.strip()}
        if int(number[1:]) >= WAVE_G_FIRST_JOURNEY:
            item["owner"] = WAVE_G
        items.append(item)
    return sorted(items, key=lambda item: int(item["id"][1:]))


def settings() -> list[dict]:
    from app.config import SETTINGS_CATALOGUE

    return [
        {
            "id": f"setting:{entry.name}",
            "title": entry.description,
            "group": entry.group,
        }
        for entry in SETTINGS_CATALOGUE
    ]


def error_codes() -> list[dict]:
    patterns = (
        re.compile(
            r"(?:[Ee]rror|[Rr]efusal|_refuse)\(\s*(?:status_code=)?\d{3}\s*,\s*(?:code=)?[\"']([A-Z][A-Z_]+)[\"']"
        ),
        re.compile(r"\bcode=[\"']([A-Z][A-Z_]+)[\"']"),
        re.compile(r"^\s*[\"']([A-Z][A-Z_]+)[\"']\s*:\s*\(\s*\d{3}", re.MULTILINE),
    )
    codes: set[str] = set()
    for path in (BACKEND / "app").rglob("*.py"):
        source = path.read_text()
        for pattern in patterns:
            codes.update(pattern.findall(source))
    return [{"id": f"error:{code}"} for code in sorted(codes)]


def commands() -> list[dict]:
    items = []
    for path in sorted((BACKEND / "app" / "cli").glob("*.py")):
        if path.stem == "__init__":
            continue
        doc = re.match(r'\s*"""(.+?)(?:\n|""")', path.read_text())
        items.append(
            {"id": f"command:{path.stem}", "title": doc.group(1).strip() if doc else ""}
        )
    return items


def roles_and_permissions() -> tuple[list[dict], list[dict]]:
    from app.engine.authorization.catalogue import GROUPS, PREDEFINED_ROLES

    roles = [
        {"id": f"role:{key}", "groups": list(groups)}
        for key, groups in PREDEFINED_ROLES.items()
    ]
    groups = [
        {"id": f"permission:{key}", "title": group.name}
        for key, group in GROUPS.items()
    ]
    return roles, groups


def event_types() -> list[dict]:
    from app.engine.events.workspace_events import EVENT_KEYS
    from app.engine.notifications.kinds import NOTICE_KINDS

    names: dict[str, str] = {}
    for key in EVENT_KEYS:
        names[key] = "workspace event"
    for change in ("created", "updated", "deleted"):  # ConsumerEvent.changes
        names[f"consumer.{change}"] = "consumer record change"
    for key, label in NOTICE_KINDS:
        names[key] = (
            f"inbox notice: {label}"
            if key not in names
            else f"{names[key]}; inbox notice"
        )
    return [{"id": f"event:{name}", "title": what} for name, what in names.items()]


def model_fields() -> list[dict]:
    from app.models import schema
    from pydantic import BaseModel

    items = []
    for name, cls in sorted(vars(schema).items()):
        if not (
            inspect.isclass(cls)
            and issubclass(cls, BaseModel)
            and cls.__module__ == schema.__name__
        ):
            continue
        if not issubclass(cls, schema.ModelDefinition) or cls is schema.ModelDefinition:
            continue
        for field, info in cls.model_fields.items():
            items.append({"id": f"field:{name}.{info.alias or field}"})
    return items


def build() -> dict:
    roles, permissions = roles_and_permissions()
    inventory = {
        "capabilities": capabilities(),
        "journeys": journeys(),
        "settings": settings(),
        "errors": error_codes(),
        "commands": commands(),
        "roles": roles,
        "permissions": permissions,
        "events": event_types(),
        "fields": model_fields(),
    }
    owned = wave_g_items()
    known = {item["id"] for items in inventory.values() for item in items}
    if owned - known:
        raise SystemExit(f"wave-g-items.txt names items that do not exist: {sorted(owned - known)}")
    for items in inventory.values():
        for item in items:
            if item["id"] in owned:
                item["owner"] = WAVE_G
    return inventory


def main() -> int:
    inventory = build()
    totals = {kind: len(items) for kind, items in inventory.items()}
    if "--totals" not in sys.argv:
        OUT.write_text(json.dumps(inventory, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    owned = sum(
        1 for items in inventory.values() for item in items if item.get("owner")
    )
    print(
        json.dumps(totals),
        f"total {sum(totals.values())}",
        f"owned by {WAVE_G}: {owned}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
