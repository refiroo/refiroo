"""Starter-model variants for tests that need an earlier schema version."""

import copy
import json
from pathlib import Path
from typing import Any

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"

# The starter content release that each schema version shipped with.
_STARTER_RELEASES = {"0.5": "0.6.0", "0.6": "0.7.0"}


def starter_at_schema(schema_version: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    """The starter (or ``source``) without the features ``schema_version`` predates.

    Schema 0.7 added relations-panel sort options and the ``relationMatrix`` and ``tree`` view types,
    and 0.6 the ``mappingGrid`` view type.
    """
    result = copy.deepcopy(source) if source is not None else json.loads(MODEL_PATH.read_text())
    if schema_version in _STARTER_RELEASES:
        result["release"]["version"] = _STARTER_RELEASES[schema_version]
    result["schemaVersion"] = schema_version
    for application in result["applications"]:
        if schema_version < "0.7":
            for detail in application.get("details", []):
                for panel in detail["panels"]:
                    if panel["type"] == "relations":
                        panel["config"].pop("sortFields", None)
                        panel["config"].pop("defaultSort", None)
            application["views"] = [
                view
                for view in application["views"]
                if view["type"] not in {"relationMatrix", "tree"}
            ]
        if schema_version < "0.6":
            application["views"] = [
                view for view in application["views"] if view["type"] == "table"
            ]
    return result
