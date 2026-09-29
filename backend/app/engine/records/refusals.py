"""How live data and a change set word the refusals the write rules share.

The rules in ``rules.py`` are one implementation for both contexts. Where the two contexts have
answered the same violation differently (another status, code or message), each context's answer is
an entry here, so the difference is stated once and settled by changing one entry (decision E-D4 in
``docs/BACKEND_BOUNDARIES_PLAN.md``). ``tests/test_rule_parity.py`` pins both columns.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ...errors import ApiError, api_error


@dataclass(frozen=True)
class Refusals:
    unknown_object_type: Callable[[str], ApiError]
    # (application key, object type key)
    unknown_application: Callable[[str, str], ApiError]
    type_not_in_application: Callable[[str, str], ApiError]
    unknown_relation_type: Callable[[str], ApiError]
    # A parent ID that names no record the context holds.
    missing_parent: Callable[[str], ApiError]
    # With ``deleting``: the refused operation is a delete.
    immutable_relation: Callable[[bool], ApiError]
    required_relation: Callable[[], ApiError]
    # (attribute type key, attribute name, the record holding the value)
    duplicate_value: Callable[[str, str, str], ApiError]
    object_exists: Callable[[str], ApiError]
    # Whether an empty string is a value a unique attribute must not repeat.
    blank_values_are_unique: bool


LIVE = Refusals(
    unknown_object_type=lambda key: api_error(
        404, "unknown_object_type", f"Object type '{key}' not found"
    ),
    unknown_application=lambda application, _type: api_error(
        404, "unknown_application", f"Application '{application}' not found"
    ),
    type_not_in_application=lambda application, type_key: api_error(
        422,
        "invalid_object_type_for_application",
        f"Object type '{type_key}' is not available in application '{application}'",
    ),
    unknown_relation_type=lambda key: api_error(
        404, "unknown_relation_type", f"Relation type '{key}' not found"
    ),
    missing_parent=lambda object_id: api_error(
        404, "object_not_found", f"Object '{object_id}' not found"
    ),
    immutable_relation=lambda _deleting: api_error(
        422,
        "immutable_relation",
        "Engine-maintained relation cannot be created, updated or deleted directly",
    ),
    required_relation=lambda: api_error(
        422, "required_relation", "A required relationship cannot be deleted independently"
    ),
    duplicate_value=lambda _key, name, _holder: api_error(
        409, "duplicate_attribute_value", f"Attribute '{name}' must be unique"
    ),
    object_exists=lambda object_id: api_error(
        409, "object_already_exists", f"An object with ID '{object_id}' already exists"
    ),
    blank_values_are_unique=False,
)

CHANGE_SET = Refusals(
    unknown_object_type=lambda key: api_error(
        422, "unknown_object_type", f"Object type '{key}' is not in the pinned model"
    ),
    unknown_application=lambda application, type_key: api_error(
        422,
        "object_type_not_in_application",
        f"Object type '{type_key}' is not enabled in application '{application}'",
    ),
    type_not_in_application=lambda application, type_key: api_error(
        422,
        "object_type_not_in_application",
        f"Object type '{type_key}' is not enabled in application '{application}'",
    ),
    unknown_relation_type=lambda key: api_error(
        422, "unknown_relation_type", f"Relation type '{key}' is not in the pinned model"
    ),
    missing_parent=lambda _object_id: api_error(
        422, "parent_wrong_scope", "Parent must be in the same application and workspace"
    ),
    immutable_relation=lambda deleting: api_error(
        422,
        "immutable_relation",
        "Engine-maintained containment relations cannot be deleted directly"
        if deleting
        else "Engine-maintained containment relations are changed through object edits",
    ),
    required_relation=lambda: api_error(
        422, "required_relation", "Required relationships cannot be deleted directly"
    ),
    duplicate_value=lambda key, _name, holder: api_error(
        409,
        "duplicate_attribute_value",
        f"Attribute '{key}' must be unique in the change set",
        {"attributeTypeKey": key, "conflictingObjectId": holder},
    ),
    object_exists=lambda object_id: api_error(
        409, "object_already_exists", f"Object '{object_id}' already exists"
    ),
    blank_values_are_unique=True,
)
