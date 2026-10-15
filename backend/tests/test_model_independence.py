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
    # Inference's own words for a sheet pattern (0.10 A6, D98): a translation sheet and its language
    # columns, and the roles of the types it proposes for them. A proposal's keys are generated from
    # its labels and never take a key the model holds (``key_from_label``), and extend mode finds
    # the draft's translation types by its profile's structure, never by key (0.10 R step 2).
    "language": "inference's role and evidence name for a language column (A6)",
    "languages": "inference's evidence field: a translation sheet's languages (A6)",
    "translation": "inference's role and pattern name for a translation sheet (A6)",
    "translations": "inference's name for a list block's translation columns (A8a)",
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
