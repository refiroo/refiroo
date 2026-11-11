"""Starter-model variants for tests that need an earlier schema version."""

import copy
import json
from pathlib import Path
from typing import Any

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"


def without_relation_columns(model: dict[str, Any]) -> dict[str, Any]:
    """``model`` without its table views' ``related:<key>`` columns and filters (schema 0.9, K5,
    K6), in place."""
    for application in model["applications"]:
        for view in application["views"]:
            if view["type"] == "table":
                for name in ("columns", "filterFields", "sortFields"):
                    fields = view["config"][name]
                    view["config"][name] = [f for f in fields if not f.startswith("related:")]
    return model


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

    String values naming a key are renamed wherever they appear, as are ``ancestor:<type>``,
    ``ancestor:<type>.<field>`` and ``related:<key>`` references and the keys of maps keyed by a model key; JSON property names are left alone.
    """
    source = copy.deepcopy(source) if source is not None else json.loads(MODEL_PATH.read_text())
    names = {key: f"{prefix}{key}" for key in starter_keys(source)}

    def rename(value: Any, *, keyed: bool = False) -> Any:
        if isinstance(value, str):
            if value in names:
                return names[value]
            head, _, tail = value.partition(":")
            if head == "related" and tail in names:
                return f"{head}:{names[tail]}"
            # A relationships table's places (0.13 RV): ``from:<field>``, ``to:<field>``,
            # ``relation:<attribute>``, a sort with a leading ``-``.
            sign = "-" if head.startswith("-") else ""
            if head.removeprefix("-") in _PLACES and tail in names:
                return f"{value[: len(sign) + len(head.removeprefix('-')) + 1]}{names[tail]}"
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
_PLACES = {"from", "to", "relation"}
# Properties naming something local to a consumer API, never a model key: a field's role, a related
# block or filter a part refers to by name, and a filter's routes (``object.related`` itself is a
# map, renamed within).
_LOCAL_NAMES = {"role", "related", "onRelated", "filter", "through"}
