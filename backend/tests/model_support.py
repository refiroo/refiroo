"""Starter-model variants for tests that need an earlier schema version."""

import copy
import json
from pathlib import Path
from typing import Any

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"

# The starter content release that each schema version shipped with.
_STARTER_RELEASES = {"0.5": "0.6.0", "0.6": "0.7.0", "0.7": "0.8.0", "0.8": "0.9.2"}


def starter_at_schema(schema_version: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    """The starter (or ``source``) without the features ``schema_version`` predates.

    Schema 0.9 wrote consumer API definitions in their present syntax, and a new 0.8 document may no
    longer declare them (C18; ``tests/fixtures/consumer_08`` keeps the 0.8 starter as it was). Schema
    0.8 added effective periods, 0.7 relations-panel sort options and the ``relationMatrix`` and
    ``tree`` view types, and 0.6 the ``mappingGrid`` view type.
    """
    result = copy.deepcopy(source) if source is not None else json.loads(MODEL_PATH.read_text())
    if schema_version in _STARTER_RELEASES:
        result["release"]["version"] = _STARTER_RELEASES[schema_version]
    result["schemaVersion"] = schema_version
    if schema_version < "0.9":
        result.pop("consumerApis", None)
    if schema_version < "0.8":
        for object_type in result["objectTypes"]:
            object_type.pop("effectivePeriod", None)
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


def starter_keys(source: dict[str, Any]) -> set[str]:
    """Every key the model declares: applications, views, details, types and reverse keys."""
    keys = set()
    for application in source["applications"]:
        keys.add(application["key"])
        keys.update(view["key"] for view in application.get("views", []))
        keys.update(detail["key"] for detail in application.get("details", []) if "key" in detail)
    for collection in ("objectTypes", "relationTypes", "attributeTypes"):
        for item in source[collection]:
            keys.add(item["key"])
            if item.get("reverseKey"):
                keys.add(item["reverseKey"])
    return keys


def renamed_model(
    source: dict[str, Any] | None = None, prefix: str = "zq-"
) -> tuple[dict[str, Any], dict[str, str]]:
    """The starter (or ``source``) with every declared key renamed, and the old-to-new key map.

    String values naming a key are renamed wherever they appear, as are ``ancestor:<type>`` and
    ``ancestor:<type>.<field>`` references and the keys of maps keyed by a model key; JSON property names are left alone.
    """
    source = copy.deepcopy(source) if source is not None else json.loads(MODEL_PATH.read_text())
    names = {key: f"{prefix}{key}" for key in starter_keys(source)}

    def rename(value: Any, *, keyed: bool = False) -> Any:
        if isinstance(value, str):
            if value in names:
                return names[value]
            head, _, tail = value.partition(":")
            if head == "ancestor":
                # ``ancestor:<type>`` or, in a consumer projection, ``ancestor:<type>.<field>``.
                type_key, dot, field = tail.partition(".")
                if type_key in names:
                    return f"{head}:{names[type_key]}{dot}{names.get(field, field)}"
            return value
        if isinstance(value, list):
            return [rename(item) for item in value]
        if isinstance(value, dict):
            return {
                (names.get(key, key) if keyed else key): (
                    item
                    if key in _LOCAL_NAMES and not isinstance(item, dict)
                    else rename(item, keyed=key in _KEYED_MAPS)
                )
                for key, item in value.items()
            }
        return value

    return rename(source), names


# Properties whose value is a map keyed by model keys: a sort per child type, and a consumer API's
# public names.
_KEYED_MAPS = {"childSort", "publicNames"}
# Properties naming something local to a consumer API, never a model key: a field's role, a related
# block or filter a part refers to by name, and a filter's routes (``object.related`` itself is a
# map, renamed within).
_LOCAL_NAMES = {"role", "related", "onRelated", "filter", "through"}
