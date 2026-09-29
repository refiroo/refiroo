"""Where a model lets records stand (Base 0.8 C4): the one rule for which object types a place can
hold, used by the engine and served to clients (``GET /model/placements``) so a browser reads it
instead of re-deriving it.

A place is the top level or a record of a parent type, within one application (a parent is always in
its child's application). Two questions are answered per place:

- the types the parent contains: those whose parent relations the model binds from the parent's
  type (``parent_type_keys``), which Add child, a move and the move targets use;
- the types a record can become there (ADR-034, D40): those contained through exactly one parent
  relation, or those ``rootCreatable`` at the top, which the restructuring planner uses.
"""

from collections.abc import Iterable
from typing import Any

from ...models.schema import EngineModel
from .traversal import parent_type_keys


def application_type_keys(model: EngineModel, application_key: str) -> tuple[str, ...]:
    application = next((item for item in model.applications if item.key == application_key), None)
    return tuple(application.objectTypeKeys) if application else ()


def possible_types(
    model: EngineModel, application_types: Iterable[str], parent_type: str | None
) -> tuple[str, ...]:
    """The application's types a parent of ``parent_type`` may contain (``None``: the top level):
    those it contains through exactly one parent relation, or those ``rootCreatable``."""
    result = []
    for key in application_types:
        object_type = model.object_type(key)
        if object_type is None:
            continue
        if parent_type is None:
            if object_type.features.get("rootCreatable", False):
                result.append(key)
            continue
        keys = set((object_type.behavior or {}).get("parentRelationTypeKeys", []))
        matches = [
            item
            for item in model.objectTypeRelations
            if item.relationTypeKey in keys
            and item.fromObjectTypeKey == parent_type
            and item.toObjectTypeKey == key
        ]
        if len(matches) == 1:
            result.append(key)
    return tuple(result)


def contained_types(
    model: EngineModel, application_types: Iterable[str], parent_type: str
) -> tuple[str, ...]:
    """The application's types a record of ``parent_type`` contains, in the application's order."""
    return tuple(key for key in application_types if parent_type in parent_type_keys(model, key))


def model_placements(model: EngineModel) -> dict[str, Any]:
    """Every application's places: the types at the top, and per type of the application as a
    parent, the types it contains and the types a record can become under it."""
    applications = []
    for application in model.applications:
        types = tuple(application.objectTypeKeys)
        applications.append(
            {
                "applicationKey": application.key,
                "topLevelObjectTypeKeys": list(possible_types(model, types, None)),
                "parents": [
                    {
                        "objectTypeKey": key,
                        "childObjectTypeKeys": list(contained_types(model, types, key)),
                        "possibleObjectTypeKeys": list(possible_types(model, types, key)),
                    }
                    for key in types
                ],
            }
        )
    return {"applications": applications}
