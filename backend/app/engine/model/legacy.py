"""CLI-only parsing of historical schema 0.4 content for transition analysis."""

from copy import deepcopy
from typing import Any

from ...models.schema import BUILT_IN_COLUMNS, EngineModel
from .compiler import parse_model


def parse_schema_04_for_transition(source: dict[str, Any]) -> EngineModel:
    """Adapt only presentation fields needed to compare persisted data offline.

    This is intentionally not exported through the runtime compiler or registry. Schema 0.4 remains
    unsupported for requests; the one-shot transition command needs its structural definitions only
    so the existing compatibility analyser can compare them with the schema 0.5 candidate.
    """
    if source.get("schemaVersion") != "0.4":
        return parse_model(source)
    adapted = deepcopy(source)
    adapted["schemaVersion"] = "0.5"
    object_fields = {
        item["key"]: BUILT_IN_COLUMNS
        | {binding["attributeTypeKey"] for binding in item.get("attributes", [])}
        for item in adapted.get("objectTypes", [])
    }
    for application in adapted.get("applications", []):
        tables = []
        for view in application.get("views", []):
            if view.get("type") != "table":
                continue
            columns = [
                field
                for field in view.get("config", {}).get("columns", [])
                if field in object_fields.get(view["objectTypeKey"], set())
            ]
            table = {
                "key": view["key"],
                "name": view["name"],
                "type": "table",
                "objectTypeKey": view["objectTypeKey"],
                "config": {
                    "columns": columns or ["name"],
                    "filterFields": ["name"],
                    "sortFields": ["name"],
                    "defaultSort": "name",
                    "pageSize": 20,
                },
            }
            tables.append(table)
        application["views"] = tables
        if application.get("defaultView") not in {view["key"] for view in tables}:
            if not tables:
                raise ValueError(
                    f"Schema 0.4 application '{application.get('key')}' has no table view for transition analysis"
                )
            application["defaultView"] = tables[0]["key"]
    return parse_model(adapted)
