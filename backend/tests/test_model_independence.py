"""Runtime code must stay unaware of the starter applications' model keys (AGENTS.md invariant)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SOURCES = (
    (ROOT / "backend" / "app", {".py"}),
    (ROOT / "frontend" / "src", {".ts", ".tsx", ".css"}),
)
# Starter keys that are also ordinary vocabulary of the engine itself, not starter references.
GENERIC_WORDS = {
    "active": "workspace, draft and release status value",
    "description": "OpenAPI and model metadata field name",
    "hierarchical": "model-schema relation property",
    "system": "appearance preference that follows the operating system",
}


def _starter_keys() -> set[str]:
    model = json.loads((ROOT / "model" / "rdm-starter.json").read_text())
    keys = set()
    for application in model["applications"]:
        keys.add(application["key"])
        keys.update(view["key"] for view in application.get("views", []))
    for collection in ("objectTypes", "relationTypes", "attributeTypes"):
        for item in model[collection]:
            keys.add(item["key"])
            if item.get("reverseKey"):
                keys.add(item["reverseKey"])
    return keys - GENERIC_WORDS.keys()


def _runtime_files():
    for root, suffixes in RUNTIME_SOURCES:
        for path in root.rglob("*"):
            if path.suffix not in suffixes or "__pycache__" in path.parts:
                continue
            if ".test." in path.name or "test" in path.relative_to(root).parts[:1]:
                continue
            yield path


def test_runtime_sources_contain_no_starter_model_key_literal():
    keys = _starter_keys()
    assert "master-value" in keys and "codelist" in keys
    pattern = re.compile(r"[\"'`](" + "|".join(map(re.escape, sorted(keys))) + r")[\"'`]")
    files = list(_runtime_files())
    assert any(path.suffix == ".py" for path in files) and any(
        path.suffix == ".tsx" for path in files
    )
    found = [
        f"{path.relative_to(ROOT)}: {match.group(1)}"
        for path in files
        for match in pattern.finditer(path.read_text())
    ]
    assert found == [], "Runtime code must read these keys from the model:\n" + "\n".join(found)
